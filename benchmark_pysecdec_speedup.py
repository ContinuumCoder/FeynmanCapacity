# -*- coding: utf-8 -*-
"""
Momentum-dependent bounds and speedup (2x2, fast end-to-end)
- Keeps strong speedup at larger S, but cuts planning overhead and reference cost.
- Key speedups:
  * Shared epsabs (baseline), baseline points=100k
  * T3 per (s,t,u) with warm-start, fewer restarts (curves), smaller grid for curves
  * Vectorized effective resistances
  * Disk cache for T3 curves and |I| references

Run:
  python pysecdec_momentum_bounds_speedup_2x2_fast.py
"""

import os
import sys
import time
import math
import json
import warnings
import gc
import subprocess
import hashlib
import numpy as np
import networkx as nx
from itertools import combinations
from scipy.linalg import cholesky, cho_solve
from scipy.optimize import minimize, minimize_scalar
from scipy.special import gammaln

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import LogLocator, ScalarFormatter, AutoMinorLocator
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

# ---------------------------- configuration ----------------------------
# epsabs strategy: "fixed_baseline" (recommended) or "loose"
EPSABS_MODE = "fixed_baseline"   # or "loose"
LOOSE_EPSABS_VALUE = 1e9         # used only if EPSABS_MODE == "loose"

# Baseline and reference sampling
BASE_POINTS = 100000
REF_POINTS  = 50000
SHIFTS = 32
epsrel = 1e-3

# Euclidean/Minkowski points scaling
EXPO_E, MIN_RATIO_E, SAFETY_E, FLOOR_PTS = 1.9, 0.08, 1.01, 2000
EXPO_M, MIN_RATIO_M, SAFETY_M            = 1.7, 0.15, 1.01

# T3 optimization settings
T3_CURVE_GRID   = 200   # a-grid for curves (fast)
T3_CURVE_REST   = 2     # restarts for curves
T3_CURVE_ITERS  = 220   # NM iters for curves

T3_SCEN_GRID    = 360   # a-grid for scenario points
T3_SCEN_REST    = 5     # restarts for scenario
T3_SCEN_ITERS   = 350   # NM iters for scenario

# Diagnostics and cache
DIAG = True
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)
CACHE_T3_FILE  = os.path.join(CACHE_DIR, "t3_cache.json")
CACHE_REF_FILE = os.path.join(CACHE_DIR, "ref_cache.json")

# ---------------------------- system soft limit helper ----------------------------
def bump_nofile_limit(target=4096):
    try:
        import resource
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        new_soft = min(max(soft, target), hard)
        if new_soft > soft:
            resource.setrlimit(resource.RLIMIT_NOFILE, (new_soft, hard))
            print(f"[rlimit] Raised RLIMIT_NOFILE: {soft} -> {new_soft} (hard={hard})")
    except Exception:
        pass

# ---------------------------- cache helpers ----------------------------
def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=2)
    os.replace(tmp, path)

T3_CACHE = load_json(CACHE_T3_FILE)
REF_CACHE = load_json(CACHE_REF_FILE)

def key_hash(d):
    s = json.dumps(d, sort_keys=True, separators=(",",":")).encode("utf-8")
    return hashlib.md5(s).hexdigest()

# ---------------------------- graph + Symanzik U setup ----------------------------
def graph_nonplanar_double_box_like():
    # TL=0, BL=1, TR=2, BR=3, ML=4, MR=5
    G = nx.MultiGraph()
    G.add_nodes_from(range(6))
    edges = [(0,4),(1,4),(2,5),(3,5),(4,5),(0,3),(1,2)]
    for k,(u,v) in enumerate(edges):
        G.add_edge(u,v,key=k)
    ext_map = {1:0, 2:1, 3:3, 4:2}  # legs -> nodes
    return G, ext_map

def extract_edge_list(G: nx.MultiGraph):
    nodes = list(G.nodes())
    idx = {v:i for i,v in enumerate(nodes)}
    edges = []
    for (u,v,k) in G.edges(keys=True):
        edges.append((idx[u], idx[v], k))
    eu = np.array([e[0] for e in edges], dtype=int)
    ev = np.array([e[1] for e in edges], dtype=int)
    return nodes, eu, ev, edges

def build_weighted_laplacian(n, eu, ev, w):
    L = np.zeros((n,n), dtype=np.float64)
    for u,v,wi in zip(eu,ev,w):
        if u==v: continue
        L[u,u]+=wi; L[v,v]+=wi
        L[u,v]-=wi; L[v,u]-=wi
    return L

def log_det_cofactor(L):
    n=L.shape[0]; sub=np.arange(n-1); Lh=L[np.ix_(sub,sub)]
    try:
        c=cholesky(Lh, lower=True, check_finite=False)
        return 2.0*np.sum(np.log(np.diag(c)))
    except:
        sign,ld=np.linalg.slogdet(Lh)
        if sign<=0: raise RuntimeError("cofactor not SPD")
        return ld

def effective_resistance_all_edges(n, eu, ev, w):
    # Vectorized: single Cholesky, solve for all edge RHS at once
    L=build_weighted_laplacian(n,eu,ev,w); n1=n-1; Lh=L[:n1,:n1]
    try:
        c=cholesky(Lh, lower=True, check_finite=False)
    except:
        Lh=Lh+1e-12*np.eye(n1)
        c=cholesky(Lh, lower=True, check_finite=False)
    m = len(eu)
    B = np.zeros((n1, m), dtype=np.float64)
    for k in range(m):
        u, v = eu[k], ev[k]
        if u < n-1: B[u, k] += 1.0
        if v < n-1: B[v, k] -= 1.0
    X = cho_solve((c, True), B, check_finite=False)  # solve Lh X = B
    R = np.sum(B * X, axis=0)
    return R

class USolver:
    def __init__(self, n, eu, ev): self.n=n; self.eu=eu; self.ev=ev; self.m=len(eu)
    def logU(self, y):
        alpha=np.exp(-y)
        L=build_weighted_laplacian(self.n,self.eu,self.ev,alpha)
        return float(np.sum(y)+log_det_cofactor(L))
    def grad_logU(self, y):
        alpha=np.exp(-y)
        Pin=np.clip(alpha*effective_resistance_all_edges(self.n,self.eu,self.ev,alpha), 1e-15, 1-1e-15)
        return 1.0 - Pin
    def cap_from_y(self, y):
        th=self.grad_logU(y)
        g=self.logU(y)-float(np.dot(th,y))
        return float(np.exp(g)), float(g), th  # capU, logcapU, theta

# ---------------------------- Symanzik F setup ----------------------------
def enumerate_spanning_trees_masks(n, m, eu, ev):
    masks=[]
    for comb in combinations(range(m), n-1):
        parent=list(range(n))
        def find(a):
            while parent[a]!=a:
                parent[a]=parent[parent[a]]; a=parent[a]
            return a
        def union(a,b):
            ra,rb=find(a),find(b)
            if ra==rb: return False
            parent[rb]=ra; return True
        ok=True
        for e in comb:
            if not union(eu[e], ev[e]): ok=False; break
        if not ok: continue
        root=find(0)
        if all(find(i)==root for i in range(n)):
            mask=0
            for e in comb: mask|=(1<<e)
            masks.append(mask)
    return masks

def enumerate_two_forests_from_trees(n,m,tree_masks):
    Fs=set()
    for t in tree_masks:
        for e in range(m):
            if ((t>>e)&1)==1: Fs.add(t & (~(1<<e)))
    return sorted(Fs)

def comp_labels_from_mask(n, eu, ev, mask):
    parent=list(range(n))
    def find(a):
        while parent[a]!=a:
            parent[a]=parent[parent[a]]; a=parent[a]
        return a
    def union(a,b):
        ra,rb=find(a),find(b)
        if ra!=rb: parent[rb]=ra
    for e in range(len(eu)):
        if ((mask>>e)&1)==1: union(eu[e], ev[e])
    root_map={}; clabel=np.zeros(n,dtype=int); cid=0
    for i in range(n):
        r=find(i)
        if r not in root_map:
            root_map[r]=cid; cid+=1
        clabel[i]=root_map[r]
    return clabel, cid

def build_F_data_for_4pt(G, ext_map):
    nodes, eu, ev, edges=extract_edge_list(G)
    n=len(nodes); m=len(edges)
    trees=enumerate_spanning_trees_masks(n,m,eu,ev)
    Fmasks=enumerate_two_forests_from_trees(n,m,trees)
    rows=[]; pairs=[]
    for fmask in Fmasks:
        clabel, cc = comp_labels_from_mask(n, eu, ev, fmask)
        if cc!=2: continue
        c = {leg: clabel[ext_map[leg]] for leg in [1,2,3,4]}
        pair=None
        if (c[1]==c[2]) and (c[3]==c[4]) and (c[1]!=c[3]): pair='s'
        elif (c[2]==c[3]) and (c[1]==c[4]) and (c[2]!=c[1]): pair='t'
        elif (c[1]==c[3]) and (c[2]==c[4]) and (c[1]!=c[2]): pair='u'
        else: continue
        b=np.zeros(m, dtype=np.float64)
        for e in range(m):
            if ((fmask>>e)&1)==0: b[e]=1.0
        rows.append(b); pairs.append(pair)
    return np.array(rows, dtype=np.float64), pairs

class FSolver:
    def __init__(self, bmat, pair_list):
        self.bmat=bmat; self.pairs=pair_list; self.m=bmat.shape[1]
    def logF_and_grad(self, y, s_val, t_val, u_val):
        coeff=np.array([s_val if p=='s' else t_val if p=='t' else u_val for p in self.pairs], dtype=float)
        z=self.bmat @ y
        w=coeff*np.exp(z)
        F=float(np.sum(w))+1e-300
        grad=(w[:,None]*self.bmat).sum(axis=0)/F
        return float(np.log(F)), grad
    def cap_from_y(self, y, s_val, t_val, u_val):
        logF, phi=self.logF_and_grad(y,s_val,t_val,u_val)
        g=logF - float(np.dot(phi,y))
        return float(np.exp(g)), float(g), phi  # capF, logcapF, phi

# ---------------------------- convex programs for bounds ----------------------------
def y_from_free_vars(x):
    y=np.zeros(len(x)+1); y[:-1]=x; y[-1]=-np.sum(x); return y
def free_vars_from_y(y):
    return np.array(y[:-1], dtype=float)

def optimize_y_for_U(solverU: USolver, D, nus, masses, n_restarts=6, maxiter=500, seed=42):
    rng=np.random.default_rng(seed); m=solverU.m
    inits=[np.zeros(m-1)]
    for _ in range(n_restarts-1): inits.append(0.5*rng.standard_normal(m-1))
    best=None
    for x0 in inits:
        def fun(x):
            y=y_from_free_vars(x)
            _, logcap, theta=solverU.cap_from_y(y)
            gamma=nus - 0.5*D*theta
            pen=0.0
            if np.any(gamma<=1e-4): pen=1e6*np.sum(np.maximum(0.0, 1e-3-gamma)**2)
            return float((-0.5*D)*logcap + np.sum(gammaln(gamma)) - 2.0*np.sum(gamma*np.log(masses)) + pen)
        res=minimize(fun, x0, method="Nelder-Mead",
                     options={"maxiter":maxiter,"xatol":1e-4,"fatol":1e-4,"disp":False})
        ystar=y_from_free_vars(res.x)
        _, logcap, theta=solverU.cap_from_y(ystar)
        gamma=nus - 0.5*D*theta
        logC=float((-0.5*D)*logcap + np.sum(gammaln(gamma)) - 2.0*np.sum(gamma*np.log(masses)))
        item=dict(y=ystar, logC=logC, logcap=logcap, theta=theta, gamma=gamma)
        if (best is None) or (item["logC"]<best["logC"]): best=item
    return best

def bound_U_log(D, nus, masses, logcapG, theta):
    gamma = nus - 0.5*D*theta
    if np.any(gamma <= 0.0): return float('inf')
    return float((-0.5*D)*logcapG + np.sum(gammaln(gamma)) - 2.0*np.sum(gamma*np.log(masses)))

def bound_T3_log(D, nus, masses, logcapG, theta, logcapF, phi, a, eps=1e-9):
    if not (eps < a < 0.5*D - eps): return float('inf')
    gamma = nus - ((0.5*D - a)*theta + a*phi)
    if np.any(gamma <= 0.0): return float('inf')
    logC = a*(math.log(a) - 1.0) - (0.5*D - a)*logcapG - a*logcapF
    logC += np.sum(gammaln(gamma)) - 2.0*np.sum(gamma*np.log(masses))
    return float(logC)

def find_best_a_grid_refine(D, nus, masses, logcapG, theta, logcapF, phi, n_grid=200, eps=1e-9):
    a_lo=eps; a_hi=0.5*D - eps
    a_grid=np.linspace(a_lo, a_hi, n_grid)
    vals=np.array([bound_T3_log(D, nus, masses, logcapG, theta, logcapF, phi, float(a), eps) for a in a_grid])
    if not np.any(np.isfinite(vals)): return None, float('inf')
    k=int(np.nanargmin(vals)); a_star=float(a_grid[k]); f_star=float(vals[k])
    # bracket refine
    i0=max(0,k-1); i1=min(n_grid-1,k+1)
    lo=float(a_grid[i0]); hi=float(a_grid[i1])
    if hi - lo > 1e-12:
        def f(a): return bound_T3_log(D, nus, masses, logcapG, theta, logcapF, phi, float(a), eps)
        try:
            res = minimize_scalar(f, method="bounded", bounds=(lo, hi), options={"xatol":1e-5, "maxiter":120})
            if res.success and np.isfinite(res.fun):
                a_star=float(res.x); f_star=float(res.fun)
        except Exception:
            pass
    return a_star, f_star

def optimize_y_for_T3(Uslv, Fslv, D, nus, masses, s_val, t_val, u_val,
                      n_restarts=2, maxiter=220, seed=123, n_grid=200, y_init=None):
    rng = np.random.default_rng(seed)
    m = Uslv.m
    inits = []
    if y_init is not None and len(y_init)==m:
        inits.append(free_vars_from_y(y_init))
    inits.append(np.zeros(m-1))
    for _ in range(max(0, n_restarts-1 - len(inits)+1)):
        inits.append(0.5*rng.standard_normal(m-1))
    best = None
    for x0 in inits:
        def fun(x):
            y = y_from_free_vars(x)
            _, logcapG, theta = Uslv.cap_from_y(y)
            _, logcapF, phi   = Fslv.cap_from_y(y, s_val, t_val, u_val)
            a_star, logC = find_best_a_grid_refine(D, nus, masses, logcapG, theta, logcapF, phi, n_grid=n_grid)
            if not np.isfinite(logC): return 1e9
            return logC
        res = minimize(fun, x0, method="Nelder-Mead",
                       options={"maxiter":maxiter,"xatol":1e-4,"fatol":1e-4,"disp":False})
        y = y_from_free_vars(res.x)
        _, logcapG, theta = Uslv.cap_from_y(y)
        _, logcapF, phi   = Fslv.cap_from_y(y, s_val, t_val, u_val)
        a_star, logC = find_best_a_grid_refine(D, nus, masses, logcapG, theta, logcapF, phi, n_grid=n_grid)
        item = dict(y=y, a=a_star, logC=logC)
        if (best is None) or (logC < best["logC"]): best = item
    return best  # contains best["logC"] (=> C_UF = exp(logC))

# ---------------------------- pySecDec: build & disteval cache ----------------------------
def build_loop_pkg_nonplanar(name='doublebox_nonplanar', method="geometric"):
    import pySecDec as psd
    internal_lines = [['m',[1,5]], ['m',[2,5]], ['m',[3,6]], ['m',[4,6]], ['m',[5,6]], ['m',[1,4]], ['m',[2,3]]]
    external_lines = [['p1',1], ['p2',2], ['p3',4], ['p4',3]]
    li = psd.LoopIntegralFromGraph(
        internal_lines = internal_lines,
        external_lines = external_lines,
        replacement_rules = [
            ('p4', '-p1-p2-p3'),
            ('p1*p1', 0), ('p2*p2', 0), ('p3*p3', 0),
            ('p1*p2', 's/2'), ('p1*p3', 't/2'), ('p2*p3', '-(s+t)/2'),
            ('m**2', 'msq')
        ]
    )
    psd.loop_package(
        name = name,
        loop_integral = li,
        real_parameters = ['s','t','msq'],
        requested_orders = [0],
        decomposition_method = method
    )
    return True

def list_jsons(datadir):
    try:
        return sorted([f for f in os.listdir(datadir) if f.endswith(".json")])
    except Exception:
        return []

def find_disteval_spec(pkgname):
    datadir = os.path.join(pkgname, "disteval")
    if not os.path.isdir(datadir): return None
    files = list_jsons(datadir)
    preferred = f"{pkgname}_integral.json"
    if preferred in files: return os.path.join(datadir, preferred)
    candidate = f"{pkgname}.json"
    if candidate in files: return os.path.join(datadir, candidate)
    if len(files) == 1:   return os.path.join(datadir, files[0])
    for f in files:
        fpath = os.path.join(datadir, f)
        try:
            with open(fpath, "r") as h:
                data = json.load(h)
            if isinstance(data, dict) and (("sums" in data) or ("integrals" in data) or ("workers" in data) or ("version" in data)):
                return fpath
        except Exception:
            continue
    return None

def run_make_disteval(pkgname, jobs=None, clean=False):
    if jobs is None:
        jobs = max(1, os.cpu_count() or 2)
    if clean:
        try:
            print(f"[build] make -C {pkgname} clean_disteval")
            subprocess.run(["make", "clean_disteval"], cwd=pkgname, check=False)
        except Exception:
            pass
    print(f"[build] make -C {pkgname} disteval -j{jobs}")
    subprocess.run(["make", "disteval", f"-j{jobs}"], cwd=pkgname, check=True, stdout=sys.stdout, stderr=sys.stderr)

def ensure_disteval_spec(pkgname, jobs=None, rebuild_if_incomplete=True):
    datadir = os.path.join(pkgname, "disteval")
    spec = find_disteval_spec(pkgname)
    need_rebuild = spec is None
    if need_rebuild and rebuild_if_incomplete:
        run_make_disteval(pkgname, jobs=jobs, clean=False)
        spec = find_disteval_spec(pkgname)
        if spec is None:
            run_make_disteval(pkgname, jobs=jobs, clean=True)
            spec = find_disteval_spec(pkgname)
    if spec is None:
        raise FileNotFoundError(f"Cannot locate disteval spec JSON in '{datadir}'")
    return spec

LIB_CACHE = {}  # pkgname -> (lib, json)

def get_disteval_library(pkgname, jobs=None):
    from pySecDec.integral_interface import DistevalLibrary
    if pkgname in LIB_CACHE: return LIB_CACHE[pkgname]
    json_path = ensure_disteval_spec(pkgname, jobs=jobs, rebuild_if_incomplete=True)
    lib = DistevalLibrary(json_path, verbose=False)
    LIB_CACHE[pkgname] = (lib, json_path)
    return lib, json_path

def close_all_libs():
    for pkg, (lib, _) in list(LIB_CACHE.items()):
        try:
            if hasattr(lib, "close"): lib.close()
        except Exception:
            pass
        try:
            del LIB_CACHE[pkg]
        except Exception:
            pass
    gc.collect()

def first_sum_key(jres, pkgname):
    sums = jres.get("sums", None)
    if not isinstance(sums, dict) or not sums:
        raise KeyError("Result JSON missing 'sums' dict.")
    return next(iter(sums.keys()))

def pick_eps0(series_dict):
    if (0,) in series_dict:
        v, e = series_dict[(0,)]
    else:
        ks = [k for k in series_dict.keys() if isinstance(k, tuple) and len(k)==1]
        ks.sort()
        v, e = series_dict[ks[-1]]
    return v, e

def run_pysecdec_once(pkgname, s, t, msq, epsrel, epsabs, points, shifts=32):
    lib, _ = get_disteval_library(pkgname, jobs=None)
    kwargs = dict(parameters={"s": float(s), "t": float(t), "msq": float(msq)},
                  epsrel=float(epsrel), epsabs=float(epsabs), format="json",
                  points=int(points), shifts=int(shifts))
    t0=time.perf_counter()
    jres = lib(**kwargs)
    t1=time.perf_counter()
    key = first_sum_key(jres, pkgname)
    val, err = pick_eps0(jres["sums"][key])
    return {"val": val, "err": err, "time_sec": t1-t0}

# ---------------------------- budgets + scaling ----------------------------
def choose_epsabs(mode, C_U_base, epsrel, loose_value=1e9, safety=2.0):
    if mode == "fixed_baseline":
        return float(epsrel * max(C_U_base, 1e-300) / safety)
    elif mode == "loose":
        return float(loose_value)
    else:
        return float(epsrel * max(C_U_base, 1e-300) / safety)

def calc_points_opt(baseline_points, C_base, C_opt,
                    exponent=1.9, min_ratio=0.08, safety=1.01, floor_points=2000):
    if not (np.isfinite(C_base) and C_base>0 and np.isfinite(C_opt) and C_opt>0):
        return int(baseline_points)
    r = float(C_opt / C_base)
    ratio = np.clip(r**exponent, 0.0, 1.0)
    pts = int(max(floor_points, math.floor(baseline_points * ratio * safety)))
    return min(pts, int(baseline_points))

# ---------------------------- main workflow ----------------------------
def main():
    wall0 = time.perf_counter()
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    bump_nofile_limit(4096)

    # Global physics settings
    D = 4.0
    msq = 1.0
    nus = None
    if nus is None: nus = np.ones(7)  # #edges=7

    # Scenarios (third uses T=0.1)
    scenarios = [
        dict(name="S=50, T=1",   S=50.0,  T=1.0),
        dict(name="S=100, T=1",  S=100.0, T=1.0),
        dict(name="S=50, T=0.1", S=50.0,  T=0.1),
    ]

    # Build graph and solvers
    G, ext_map = graph_nonplanar_double_box_like()
    nodes, eu, ev, edges = extract_edge_list(G); m=len(edges)
    U = USolver(len(nodes), eu, ev)
    bmat, plist = build_F_data_for_4pt(G, ext_map)
    F = FSolver(bmat, plist)
    masses = msq*np.ones(m)

    # U-only optimization
    t_prep0 = time.perf_counter()
    bestU = optimize_y_for_U(U, D, nus, masses, n_restarts=6, maxiter=500, seed=42)
    ystar   = bestU["y"]
    theta   = bestU["theta"]
    logcapG = float(bestU["logcap"])
    logC_U  = bound_U_log(D, nus, masses, logcapG, theta)
    C_U     = math.exp(logC_U) if logC_U < 700 else float('inf')

    epsabs_common = choose_epsabs(EPSABS_MODE, C_U, epsrel, loose_value=LOOSE_EPSABS_VALUE, safety=2.0)

    # Top-row: Bound vs s curves (Euclidean/Minkowski share same bound family)
    S_grid = [0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0]
    T_list  = [1.0, 0.1]
    C_UF_curves = {}
    # Cache key for curves
    curve_tag = dict(D=D, msq=msq, epsrel=epsrel, T3_grid=T3_CURVE_GRID,
                     restarts=T3_CURVE_REST, iters=T3_CURVE_ITERS, algo="warmstart+refine")
    for T_fixed in T_list:
        key = key_hash(dict(tag="t3_curve", T=T_fixed, S_grid=S_grid, **curve_tag))
        if key in T3_CACHE:
            C_UF_curves[T_fixed] = np.array(T3_CACHE[key]["C_UF_list"], dtype=float)
            if DIAG: print(f"[cache] loaded T3 curve for T={T_fixed}")
            continue
        C_list=[]
        y_prev = ystar  # warm-start from U-only optimum
        for S in S_grid:
            best_T3 = optimize_y_for_T3(U, F, D, nus, masses, S, T_fixed, S+T_fixed,
                                        n_restarts=T3_CURVE_REST, maxiter=T3_CURVE_ITERS,
                                        seed=42, n_grid=T3_CURVE_GRID, y_init=y_prev)
            logC = best_T3["logC"]; y_prev = best_T3["y"]
            C_UF = math.exp(logC) if np.isfinite(logC) and (logC < 700) else np.inf
            C_list.append(C_UF)
            if DIAG:
                print(f"[curve] T={T_fixed:g}, s={S:g}: factor={C_U/max(C_UF,1e-300):.2f}")
        C_UF_curves[T_fixed] = np.array(C_list, dtype=float)
        T3_CACHE[key] = {"C_UF_list": C_list}
        save_json(CACHE_T3_FILE, T3_CACHE)

    # |I| dashed references (geometric) with cache
    from pySecDec import __version__ as _psdver  # force import
    pkg_geom = "doublebox_nonplanar_geom"
    if not os.path.isdir(pkg_geom):
        build_loop_pkg_nonplanar(name=pkg_geom, method="geometric")
    ensure_disteval_spec(pkg_geom, jobs=None, rebuild_if_incomplete=True)

    ref_tag = dict(epsrel=epsrel, epsabs=epsabs_common, points=REF_POINTS, shifts=SHIFTS)
    key_eu = key_hash(dict(tag="ref_eu", S_grid=S_grid, **ref_tag))
    key_mi = key_hash(dict(tag="ref_mi", S_grid=S_grid, **ref_tag))

    if key_eu in REF_CACHE:
        I_eu = np.array(REF_CACHE[key_eu]["vals"], dtype=float)
        if DIAG: print("[cache] loaded Euclidean reference |I|")
    else:
        I_eu=[]
        for S in S_grid:
            out = run_pysecdec_once(pkg_geom, s=S, t=1.0, msq=msq,
                                    epsrel=epsrel, epsabs=epsabs_common,
                                    points=REF_POINTS, shifts=SHIFTS)
            val = out["val"]
            I_eu.append(max(abs(np.real(val)), abs(np.imag(val))))
        REF_CACHE[key_eu] = {"vals": I_eu}
        save_json(CACHE_REF_FILE, REF_CACHE)
        I_eu = np.array(I_eu, dtype=float)

    if key_mi in REF_CACHE:
        I_mi = np.array(REF_CACHE[key_mi]["vals"], dtype=float)
        if DIAG: print("[cache] loaded Minkowski reference |I|")
    else:
        I_mi=[]
        for S in S_grid:
            out = run_pysecdec_once(pkg_geom, s=-S, t=-1.0, msq=msq,
                                    epsrel=epsrel, epsabs=epsabs_common,
                                    points=REF_POINTS, shifts=SHIFTS)
            val = out["val"]
            I_mi.append(max(abs(np.real(val)), abs(np.imag(val))))
        REF_CACHE[key_mi] = {"vals": I_mi}
        save_json(CACHE_REF_FILE, REF_CACHE)
        I_mi = np.array(I_mi, dtype=float)

    # Iterative package too
    pkg_iter = "doublebox_nonplanar_iter"
    if not os.path.isdir(pkg_iter):
        build_loop_pkg_nonplanar(name=pkg_iter, method="iterative")
        ensure_disteval_spec(pkg_iter, jobs=None, rebuild_if_incomplete=True)

    # Bottom-row timings
    methods = [("geometric", pkg_geom), ("iterative", pkg_iter)]
    timing_E = []
    timing_M = []

    # Cache per-scenario T3
    scen_tag = dict(D=D, msq=msq, epsrel=epsrel, T3_grid=T3_SCEN_GRID,
                    restarts=T3_SCEN_REST, iters=T3_SCEN_ITERS, algo="warmstart+refine")
    for sc in scenarios:
        S = sc["S"]; T = sc["T"]
        k_scen = key_hash(dict(tag="t3_scen", S=S, T=T, **scen_tag))
        if k_scen in T3_CACHE:
            C_UF_e = float(T3_CACHE[k_scen]["C_UF"])
            y_warm = np.array(T3_CACHE[k_scen]["y"], dtype=float)
            if DIAG: print(f"[cache] loaded T3 scenario {sc['name']}")
        else:
            # warm-start from nearest S in curve
            s_idx = int(np.argmin([abs(S - s) for s in S_grid]))
            y_warm = None  # For simplicity; you can also store y along curves.
            best_T3_e = optimize_y_for_T3(U, F, D, nus, masses, S, T, S+T,
                                          n_restarts=T3_SCEN_REST, maxiter=T3_SCEN_ITERS,
                                          seed=123, n_grid=T3_SCEN_GRID, y_init=y_warm)
            logC_UF_e = best_T3_e["logC"]
            C_UF_e = math.exp(logC_UF_e) if np.isfinite(logC_UF_e) and (logC_UF_e < 700) else np.inf
            T3_CACHE[k_scen] = {"C_UF": C_UF_e, "y": best_T3_e["y"].tolist()}
            save_json(CACHE_T3_FILE, T3_CACHE)

        C_UF_m = C_UF_e

        pts_opt_E = calc_points_opt(BASE_POINTS, C_U, C_UF_e,
                                    exponent=EXPO_E, min_ratio=MIN_RATIO_E, safety=SAFETY_E, floor_points=FLOOR_PTS)
        pts_opt_M = calc_points_opt(BASE_POINTS, C_U, C_UF_m,
                                    exponent=EXPO_M, min_ratio=MIN_RATIO_M, safety=SAFETY_M, floor_points=FLOOR_PTS)

        if DIAG:
            rE = C_UF_e / C_U if (np.isfinite(C_UF_e) and C_U>0) else np.nan
            print(f"[diag] Euclid {sc['name']}: r=C_UF/C_U={rE:.3e}, points_opt={pts_opt_E}/{BASE_POINTS} ({pts_opt_E/BASE_POINTS:.3f})")

        for method, pkg in methods:
            # Euclidean timing (same epsrel, same epsabs_common)
            out_b = run_pysecdec_once(pkg, s=S, t=T, msq=msq,
                                      epsrel=epsrel, epsabs=epsabs_common,
                                      points=BASE_POINTS, shifts=SHIFTS)
            out_o = run_pysecdec_once(pkg, s=S, t=T, msq=msq,
                                      epsrel=epsrel, epsabs=epsabs_common,
                                      points=pts_opt_E, shifts=SHIFTS)
            timing_E.append(dict(
                scenario=sc["name"], method=method,
                t_base=out_b["time_sec"], t_opt=out_o["time_sec"],
                pts_base=BASE_POINTS, pts_opt=pts_opt_E
            ))
            # Minkowski timing
            out_bm = run_pysecdec_once(pkg, s=-S, t=-T, msq=msq,
                                       epsrel=epsrel, epsabs=epsabs_common,
                                       points=BASE_POINTS, shifts=SHIFTS)
            out_om = run_pysecdec_once(pkg, s=-S, t=-T, msq=msq,
                                       epsrel=epsrel, epsabs=epsabs_common,
                                       points=pts_opt_M, shifts=SHIFTS)
            timing_M.append(dict(
                scenario=sc["name"], method=method,
                t_base=out_bm["time_sec"], t_opt=out_om["time_sec"],
                pts_base=BASE_POINTS, pts_opt=pts_opt_M
            ))

    t_prep1 = time.perf_counter()
    if DIAG:
        print(f"[timing] planning+refs time = {t_prep1 - t_prep0:.2f} s")
        



    # ---------------------------- Plot (2x2) ----------------------------
    plt.rcParams.update({
        "font.size": 12,
        "axes.titlesize": 13,
        "axes.labelsize": 12,
        "legend.fontsize": 11,
        "figure.dpi": 170
    })
    fig, axes = plt.subplots(2, 2, figsize=(11.0, 10.0))
    axEU, axMI = axes[0]
    axEB, axMB = axes[1]

    # Colors
    method_colors = {"geometric": "#4e79a7", "iterative": "#f28e2b"}
    def lighten(rgb_hex, amt=0.5):
        c = np.array(matplotlib.colors.to_rgb(rgb_hex))
        return matplotlib.colors.to_hex(np.clip(c + (1 - c) * amt, 0, 1))
    colors_T = {1.0: "#d62728", 0.1: "#e377c2"}

    # TL: Euclidean Bound vs s
    s_arr = np.array(S_grid, dtype=float)
    axEU.set_title("Bound vs s (Euclidean)")
    axEU.plot(s_arr, [C_U]*len(s_arr), color="#1f77b4", lw=2.3)
    axEU.plot(s_arr, C_UF_curves[1.0], color=colors_T[1.0], lw=2.2)
    axEU.plot(s_arr, C_UF_curves[0.1], color=colors_T[0.1], lw=2.2)
    axEU.plot(s_arr, I_eu, color="black", lw=2.0, ls="--", alpha=0.9)
    # annotate improvement at s=50,100 (T=1)
    def annotate_improv(ax, S_annot):
        if S_annot in S_grid:
            idx = S_grid.index(S_annot)
            CUF = C_UF_curves[1.0][idx]
            if np.isfinite(C_U) and np.isfinite(CUF) and CUF>0:
                factor = C_U / CUF
                ax.annotate(f"×{factor:.2f} @ s={S_annot:g}",
                            xy=(S_annot, CUF),
                            xytext=(S_annot*0.8, CUF*1.8),
                            arrowprops=dict(arrowstyle='->', color="#333"),
                            fontsize=11, color="#333", clip_on=False)
    annotate_improv(axEU, 50.0)
    annotate_improv(axEU, 100.0)
    axEU.set_xscale("log"); axEU.set_yscale("log")
    axEU.set_xlabel("Mandelstam s"); axEU.set_ylabel("Bound / |I| (log scale)")
    axEU.set_xticks(S_grid); axEU.get_xaxis().set_major_formatter(ScalarFormatter())
    axEU.get_xaxis().set_minor_locator(LogLocator(base=10, subs=np.arange(2, 10) * 0.1))
    axEU.grid(True, which='both', ls='--', alpha=0.3)
    axEU.margins(x=0.06, y=0.18)

    # TR: Minkowski Bound vs s
    axMI.set_title("Bound vs s (Minkowski)")
    axMI.plot(s_arr, [C_U]*len(s_arr), color="#1f77b4", lw=2.3)
    axMI.plot(s_arr, C_UF_curves[1.0], color=colors_T[1.0], lw=2.2)
    axMI.plot(s_arr, C_UF_curves[0.1], color=colors_T[0.1], lw=2.2)
    axMI.plot(s_arr, I_mi, color="black", lw=2.0, ls="--", alpha=0.9)
    axMI.set_xscale("log"); axMI.set_yscale("log")
    axMI.set_xlabel("Mandelstam s"); axMI.set_ylabel("Bound (log scale)")
    axMI.set_xticks(S_grid); axMI.get_xaxis().set_major_formatter(ScalarFormatter())
    axMI.get_xaxis().set_minor_locator(LogLocator(base=10, subs=np.arange(2, 10) * 0.1))
    axMI.grid(True, which='both', ls='--', alpha=0.3)
    axMI.margins(x=0.06, y=0.18)

    # Helper: grouped bars without overlap, scenario labels only (legend conveys method & scheme)
    def draw_speed_grouped(ax, timing_list, title):
        ax.set_title(title)
        scen_names = [sc["name"] for sc in scenarios]
        methods_order = ["geometric", "iterative"]
        by_scen = {s: [] for s in scen_names}
        max_h = 0.0
        for scn in scen_names:
            for mname in methods_order:
                row = [r for r in timing_list if r["scenario"]==scn and r["method"]==mname]
                if row:
                    r = row[0]
                    by_scen[scn].append(r)
                    max_h = max(max_h, r["t_base"], r["t_opt"])
        # Geometry
        n_scen = len(scen_names)
        bar_w = 0.22
        delta = bar_w + 0.10
        method_block = 2*bar_w + 0.28
        group_gap = 0.70
        group_centers = np.arange(n_scen) * (2*method_block + group_gap)
        for gi, scn in enumerate(scen_names):
            xg = group_centers[gi]
            for mj, r in enumerate(by_scen[scn]):
                mname = r["method"]
                base_c = method_colors[mname]
                opt_c  = lighten(base_c, 0.45)
                m_center = xg + (mj - 0.5)*method_block
                xb = m_center - delta/2
                xo = m_center + delta/2
                ax.bar(xb, r["t_base"], width=bar_w, color=base_c, hatch="///",
                       edgecolor="black", linewidth=0.6)
                ax.bar(xo, r["t_opt"], width=bar_w, color=opt_c,
                       edgecolor="black", linewidth=0.6)
                sp = r["t_base"]/max(r["t_opt"],1e-12)
                offset = 0.04 * max_h
                
                        ha='center', va='bottom', fontsize=11, color="#333", clip_on=False)
                        
        ax.set_ylabel("time (s)")
        ax.set_xticks(group_centers)
        ax.set_xticklabels(scen_names)
        ax.set_ylim(0, max_h*1.5)
        ax.margins(x=0.05)
        ax.grid(True, axis='y', ls='--', alpha=0.3)
        ax.yaxis.set_minor_locator(AutoMinorLocator(2))

    # BL/BR
    draw_speed_grouped(axEB, timing_E, "Euclidean: time to reach same epsrel (lower is better)")
    draw_speed_grouped(axMB, timing_M, "Minkowski: time to reach same epsrel (lower is better)")

    # Figure-level legends (two rows)
    method_handles = [Patch(facecolor=method_colors["geometric"], edgecolor="black", label="geometric"),
                      Patch(facecolor=method_colors["iterative"], edgecolor="black", label="iterative")]
    scheme_handles = [Patch(facecolor="white", edgecolor="black", hatch="///", label="baseline (U-only)"),
                      Patch(facecolor="white", edgecolor="black", label="optimized (momentum-sensitive)")]
    leg_methods = fig.legend(handles=(method_handles + scheme_handles),
                             loc="upper center", bbox_to_anchor=(0.5, 0.99), ncol=4, frameon=False)
    fig.add_artist(leg_methods)
    line_handles = [
        Line2D([0], [0], color="#1f77b4", lw=2.3, label="U-only bound"),
        Line2D([0], [0], color=colors_T[1.0], lw=2.2, label="Momentum-sensitive (T=1)"),
        Line2D([0], [0], color=colors_T[0.1], lw=2.2, label="Momentum-sensitive (T=0.1)"),
        Line2D([0], [0], color="black", lw=2.0, ls="--", label="|I| (reference, T=1)")
    ]
    fig.legend(handles=line_handles,
               loc="upper center", bbox_to_anchor=(0.5, 0.955), ncol=4, frameon=False)

    fig.suptitle("   Improvement from momentum-dependent bounds (nonplanar double-box)", y=0.88, fontsize=18)
    fig.tight_layout(rect=[0.02, 0.05, 1, 0.88])

    fig.savefig("momentum_bounds_speedup_2x2_fast.png", dpi=200, bbox_inches="tight")
    fig.savefig("momentum_bounds_speedup_2x2_fast.pdf", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("[plot] saved momentum_bounds_speedup_2x2_fast.png/pdf")

    # Save raw timing
    with open("timing_euclidean.json", "w") as f:
        json.dump(timing_E, f, indent=2)
    with open("timing_minkowski.json", "w") as f:
        json.dump(timing_M, f, indent=2)

    # Release handles
    close_all_libs()
    wall1 = time.perf_counter()
    print(f"[total] end-to-end time: {wall1 - wall0:.2f} s")

if __name__ == "__main__":
    main()