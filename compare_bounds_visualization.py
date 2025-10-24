# -*- coding: utf-8 -*-
"""
Capacity-optimized nonperturbative bounds vs. uniform-theta baseline (tau)
- Optimize y to minimize final bound constant C(y) subject to gamma>0
- Compare against baseline at y=0 (theta_uniform, cap=tau)
- Visualize improvements and graph-level geometry (theta/gamma/alpha*)

Graphs: 2L planar/nonplanar double box, 2L sunrise, 3L banana, double ladder, wheel
"""

import os, time, math, warnings
warnings.filterwarnings("ignore", message=".*alltrue.*", category=DeprecationWarning)

# Use non-interactive backend to avoid Qt/DBus errors; set to "TkAgg" if you want interactive windows.
import matplotlib
matplotlib.use("Agg")

import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
from scipy.linalg import cholesky, cho_solve
from scipy.optimize import minimize
from scipy.special import gammaln

# ---------------------------
# Graph builders (MultiGraph)
# ---------------------------

def graph_sunrise():
    G = nx.MultiGraph()
    G.add_nodes_from([0, 1])
    for k in range(3):
        G.add_edge(0, 1, key=k)
    return G

def graph_banana(M=4):
    G = nx.MultiGraph()
    G.add_nodes_from([0, 1])
    for k in range(M):
        G.add_edge(0, 1, key=k)
    return G

def graph_planar_double_box():
    G = nx.MultiGraph()
    G.add_nodes_from(range(6))  # TL=0, BL=1, MT=2, MB=3, TR=4, BR=5
    edges = [(0,2),(0,1),(2,4),(1,3),(2,3),(3,5),(4,5)]
    for k,(u,v) in enumerate(edges):
        G.add_edge(u,v,key=k)
    return G

def graph_nonplanar_double_box_like():
    G = nx.MultiGraph()
    G.add_nodes_from(range(6))  # TL=0, BL=1, TR=2, BR=3, ML=4, MR=5
    edges = [(0,4),(1,4),(2,5),(3,5),(4,5),(0,3),(1,2)]
    for k,(u,v) in enumerate(edges):
        G.add_edge(u,v,key=k)
    return G

def graph_double_ladder(n_rungs=4):
    base = nx.ladder_graph(n_rungs)
    G = nx.MultiGraph()
    G.add_nodes_from(base.nodes())
    for (u,v) in base.edges():
        G.add_edge(u,v)
    return G

def graph_wheel(n_rim=6):
    base = nx.wheel_graph(n_rim + 1)  # node 0 hub
    G = nx.MultiGraph()
    G.add_nodes_from(base.nodes())
    for (u,v) in base.edges():
        G.add_edge(u,v)
    return G

def get_graphs_and_params():
    # Each entry: (name, G, D, note)
    eps = 0.1
    D_phen = 4.0 - 2.0*eps  # 3.8
    D_2d = 2.0
    graphs = [
        ("2L Sunrise (D=2)", graph_sunrise(), D_2d, "Convergent in D=2"),
        ("3L Banana (D=2)", graph_banana(M=4), D_2d, "M=4 banana in D=2"),
        ("2L Planar Double Box", graph_planar_double_box(), D_phen, "2->2 planar box"),
        ("2L Nonplanar-like Double Box", graph_nonplanar_double_box_like(), D_phen, "2->2 nonplanar-like box"),
        ("Double Ladder (4 rungs)", graph_double_ladder(4), D_phen, "L=3 ladder"),
        # Wheel is UV-challenging at D=3.8 with nu=1; pick D=3.2 for feasible demo
        ("Wheel (rim=6, D=3.2)", graph_wheel(6), 3.2, "Wheel feasible demo at D=3.2"),
    ]
    return graphs

# ---------------------------
# Laplacian / U, grad, capacity
# ---------------------------

def build_weighted_laplacian(n, eu, ev, w):
    L = np.zeros((n,n), dtype=np.float64)
    for u,v,wi in zip(eu,ev,w):
        if u==v: continue
        L[u,u] += wi
        L[v,v] += wi
        L[u,v] -= wi
        L[v,u] -= wi
    return L

def log_det_cofactor(L):
    n = L.shape[0]
    idx = np.arange(n-1)
    L_hat = L[np.ix_(idx,idx)]
    try:
        c = cholesky(L_hat, lower=True, check_finite=False)
        return 2.0*np.sum(np.log(np.diag(c)))
    except np.linalg.LinAlgError:
        sign, ld = np.linalg.slogdet(L_hat)
        if sign<=0:
            raise RuntimeError("Cofactor not SPD.")
        return ld

def effective_resistance_all_edges(n, eu, ev, w):
    L = build_weighted_laplacian(n, eu, ev, w)
    n1 = n-1; keep = np.arange(n1)
    L_hat = L[np.ix_(keep,keep)]
    try:
        c = cholesky(L_hat, lower=True, check_finite=False)
    except np.linalg.LinAlgError:
        L_hat = L_hat + 1e-12*np.eye(n1)
        c = cholesky(L_hat, lower=True, check_finite=False)
    def solve_hat(b):
        return cho_solve((c,True), b, check_finite=False)
    def to_hat_vec(u,v):
        b = np.zeros(n1, dtype=np.float64)
        if u < n-1: b[u]+=1
        if v < n-1: b[v]-=1
        return b
    R = np.zeros(len(eu), dtype=np.float64)
    for k,(u,v) in enumerate(zip(eu,ev)):
        if eu[k]==ev[k]:
            R[k]=0.0; continue
        b = to_hat_vec(eu[k], ev[k])
        x = solve_hat(b)
        R[k] = float(np.dot(b,x))
    return R

class USolver:
    def __init__(self, n, eu, ev):
        self.n = n
        self.eu = np.array(eu, dtype=int)
        self.ev = np.array(ev, dtype=int)
        self.m = len(self.eu)

    def logU(self, y):
        alpha = np.exp(-y)
        L = build_weighted_laplacian(self.n, self.eu, self.ev, alpha)
        logK = log_det_cofactor(L)
        return float(np.sum(y) + logK)

    def grad_logU(self, y):
        alpha = np.exp(-y)
        R = effective_resistance_all_edges(self.n, self.eu, self.ev, alpha)
        Pin = np.clip(alpha*R, 1e-15, 1-1e-15)
        return 1.0 - Pin  # theta(y)

    def cap_from_y(self, y):
        theta = self.grad_logU(y)
        g = self.logU(y) - float(np.dot(theta, y))
        return float(np.exp(g)), float(g), theta

# ---------------------------
# Utilities
# ---------------------------

def extract_edge_list(G: nx.MultiGraph):
    nodes = list(G.nodes())
    idx = {v:i for i,v in enumerate(nodes)}
    edges = []
    for (u,v,k) in G.edges(keys=True):
        edges.append((idx[u], idx[v], k))
    eu = np.array([e[0] for e in edges], dtype=int)
    ev = np.array([e[1] for e in edges], dtype=int)
    return nodes, eu, ev, edges

def spanning_tree_count(G: nx.MultiGraph):
    nodes, eu, ev, edges = extract_edge_list(G)
    n = len(nodes); m = len(edges)
    w = np.ones(m, dtype=np.float64)
    L = build_weighted_laplacian(n, eu, ev, w)
    logtau = log_det_cofactor(L)
    tau = np.exp(logtau)
    # round for small graphs
    if logtau < 50:
        tau = float(round(tau))
    return tau, logtau

def param_project(x):
    # map x in R^{m-1} to y in R^m with sum(y)=0
    # y_i = x_i for i=0..m-2, y_{m-1} = -sum_{i=0}^{m-2} x_i
    return None

def y_from_free_vars(x):
    m1 = len(x)
    y = np.zeros(m1+1, dtype=np.float64)
    y[:-1] = x
    y[-1] = -np.sum(x)
    return y

def free_vars_from_y(y):
    return np.array(y[:-1], dtype=np.float64)

# ---------------------------
# Objective: logC(y) with barrier on gamma>0
# ---------------------------

def logC_with_barrier(y, solverU: USolver, D, nus, masses, delta=1e-3, mu=1e4):
    # Compute theta(y), cap(y), and log of bound constant with barrier if gamma<=delta
    cap, logcap, theta = solverU.cap_from_y(y)
    theta = np.asarray(theta, dtype=np.float64)
    gamma = nus - 0.5*D*theta
    # barrier: quadratic penalty for gamma below delta
    viol = np.maximum(0.0, delta - gamma)
    penalty = mu * np.sum(viol*viol)
    # log C
    logC = (-0.5*D)*logcap + np.sum(gammaln(gamma)) - 2.0*np.sum(gamma*np.log(masses))
    return logC + penalty, logC, penalty, theta, gamma, cap

# ---------------------------
# Optimization over y (m-1 free vars)
# ---------------------------

def optimize_y(solverU: USolver, D, nus, masses, n_restarts=6, maxiter=300, seed=0):
    rng = np.random.default_rng(seed)
    m = solverU.m
    # initial points: include zero vector, plus random small vectors
    inits = [np.zeros(m-1, dtype=np.float64)]
    for _ in range(n_restarts-1):
        x0 = 0.5 * rng.standard_normal(m-1)  # moderate tilt; adjust scale if needed
        inits.append(x0)

    best = None
    for x0 in inits:
        def fun(x):
            y = y_from_free_vars(x)
            f, logC, pen, theta, gamma, cap = logC_with_barrier(y, solverU, D, nus, masses)
            return f

        res = minimize(fun, x0, method="Nelder-Mead",
                       options={"maxiter": maxiter, "xatol":1e-4, "fatol":1e-4, "disp": False})
        x_star = res.x
        y_star = y_from_free_vars(x_star)
        f, logC, pen, theta, gamma, cap = logC_with_barrier(y_star, solverU, D, nus, masses)
        feasible = np.all(gamma > 1e-8)
        item = dict(x=x_star, y=y_star, f=f, logC=logC, penalty=pen,
                    theta=theta, gamma=gamma, cap=cap, feasible=feasible, nit=res.nit)
        if (best is None) or (item["f"] < best["f"]):
            best = item
    return best

# ---------------------------
# Drawing helpers
# ---------------------------

def default_positions(name, G):
    name = name.lower()
    if "planar double box" in name:
        return {0:(-2,1), 2:(0,1), 4:(2,1), 1:(-2,-1), 3:(0,-1), 5:(2,-1)}
    if "sunrise" in name or "banana" in name:
        return {0:(-1,0), 1:(1,0)}
    if "wheel" in name:
        return nx.circular_layout(G)
    if "ladder" in name:
        return nx.spring_layout(G, seed=1)
    if "nonplanar" in name:
        return nx.spring_layout(G, seed=2)
    return nx.spring_layout(G, seed=0)

def draw_graph_edge_values(ax, G: nx.MultiGraph, values, title, pos=None,
                           cmap="viridis", width_scale=4.0, fmt="{:.2f}"):
    if pos is None:
        pos = nx.spring_layout(G, seed=0)
    nodes, eu, ev, edges = extract_edge_list(G)
    vals = np.asarray(values, dtype=float)
    vmin, vmax = float(vals.min()), float(vals.max())
    norm = plt.Normalize(vmin=vmin, vmax=vmax)
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    nx.draw_networkx_nodes(G, pos, node_color="#444", node_size=300, ax=ax)
    # group parallel edges for curvature
    pair_to_edges = {}
    for (u,v,k) in G.edges(keys=True):
        a,b = (u,v) if u<=v else (v,u)
        pair_to_edges.setdefault((a,b), []).append((u,v,k))
    # rebuild list with index mapping
    edge_list = list(edges)
    for pair, el in pair_to_edges.items():
        K = len(el)
        rads = [0.0] if K==1 else np.linspace(-0.4, 0.4, K)
        for i,(u,v,k) in enumerate(el):
            # find this edge idx
            idx = None
            for j,(uu,vv,kk) in enumerate(edge_list):
                if uu==u and vv==v and kk==k:
                    idx = j; break
            val = vals[idx]
            color = sm.to_rgba(val)
            width = 0.5 + width_scale*(val - vmin)/(vmax - vmin + 1e-12)
            nx.draw_networkx_edges(G, pos, edgelist=[(u,v)], ax=ax,
                                   edge_color=[color], width=width,
                                   connectionstyle=f"arc3,rad={rads[i]}")
            # label
            x = (pos[u][0] + pos[v][0]) / 2.0
            y = (pos[u][1] + pos[v][1]) / 2.0 + 0.1*rads[i]
            ax.text(x, y, fmt.format(val), fontsize=8, color="#222", ha="center", va="center")
    nx.draw_networkx_labels(G, pos, font_size=9, font_color="#000", ax=ax)
    ax.set_title(title); ax.axis("off")
    cbar = plt.colorbar(sm, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.set_ylabel("value", rotation=90)

# ---------------------------
# End-to-end comparison + visualization
# ---------------------------

def run_compare(save_dir="figs", show_figs=False):
    os.makedirs(save_dir, exist_ok=True)
    results = []
    graphs = get_graphs_and_params()

    for name, G, D_use, note in graphs:
        print(f"\n== {name} | {note} ==")
        nodes, eu, ev, edges = extract_edge_list(G)
        n, m = len(nodes), len(edges)
        L = m - n + 1
        solver = USolver(n, eu, ev)

        # physics params
        nus = np.ones(m, dtype=np.float64)  # ν_e = 1
        masses = np.ones(m, dtype=np.float64)

        # Baseline (uniform θ at y=0): cap=U(1)=τ(G)
        y0 = np.zeros(m, dtype=np.float64)
        theta0 = solver.grad_logU(y0)
        tau, logtau = spanning_tree_count(G)
        logcap0 = math.log(tau)  # cap0 = tau
        gamma0 = nus - 0.5*D_use*theta0
        feasible0 = bool(np.all(gamma0 > 0))
        logC0 = (-0.5*D_use)*logcap0 + np.sum(gammaln(gamma0)) - 2.0*np.sum(gamma0*np.log(masses))
        C0 = float(np.exp(logC0)) if abs(logC0) < 700 else float('inf')

        print(f"baseline: tau={tau:g}, feasible={feasible0}, min gamma={gamma0.min():.4f}")

        # Optimize y to minimize logC with barrier
        t0 = time.perf_counter()
        best = optimize_y(solver, D_use, nus, masses, n_restarts=8, maxiter=600, seed=42)
        t1 = time.perf_counter()
        y_star = best["y"]; theta_star = best["theta"]; gamma_star = best["gamma"]
        cap_star = best["cap"]; logC_star = best["logC"]; C_star = float(np.exp(logC_star)) if abs(logC_star) < 700 else float('inf')
        feasible_star = best["feasible"]

        print(f"optimized: cap={cap_star:.6g}, feasible={feasible_star}, "
              f"min gamma={gamma_star.min():.4f}, runtime={t1-t0:.3f}s")

        # Collect
        results.append({
            "name": name, "note": note, "n": n, "m": m, "L": L, "D": D_use,
            "tau": tau, "cap_opt": cap_star,
            "C_baseline": C0, "C_opt": C_star,
            "improve": C0 / C_star if (C_star>0 and np.isfinite(C_star)) else np.nan,
            "feasible_baseline": feasible0, "feasible_opt": feasible_star,
            "theta0": theta0, "theta_star": theta_star,
            "gamma0": gamma0, "gamma_star": gamma_star,
            "y_star": y_star
        })

        # Geometry figure for this graph
        pos = default_positions(name, G)
        alpha0 = np.exp(-y0)
        alpha_star = np.exp(-y_star)

        fig, axes = plt.subplots(2, 2, figsize=(11, 9))
        draw_graph_edge_values(axes[0,0], G, theta0, f"{name}\nθ baseline (y=0)", pos=pos, cmap="viridis")
        draw_graph_edge_values(axes[0,1], G, gamma0, f"{name}\nγ baseline", pos=pos, cmap="plasma")
        draw_graph_edge_values(axes[1,0], G, theta_star, f"{name}\nθ optimized", pos=pos, cmap="viridis")
        draw_graph_edge_values(axes[1,1], G, gamma_star, f"{name}\nγ optimized", pos=pos, cmap="plasma")
        fig.suptitle(f"Edge-wise θ and γ on {name}", fontsize=13)
        fig.tight_layout(rect=[0,0.03,1,0.97])
        fig.savefig(os.path.join(save_dir, f"{name.replace(' ','_')}_theta_gamma.png"), dpi=200)
        if show_figs: plt.show(); plt.close(fig)
        else: plt.close(fig)

        fig2, axes2 = plt.subplots(1, 2, figsize=(11, 4.5))
        draw_graph_edge_values(axes2[0], G, alpha0, f"{name}\nα* baseline (y=0)", pos=pos, cmap="cividis")
        draw_graph_edge_values(axes2[1], G, alpha_star, f"{name}\nα* optimized", pos=pos, cmap="cividis")
        fig2.tight_layout()
        fig2.savefig(os.path.join(save_dir, f"{name.replace(' ','_')}_alpha.png"), dpi=200)
        if show_figs: plt.show(); plt.close(fig2)
        else: plt.close(fig2)

        # 1D path plot between y=0 and y=y_star
        ts = np.linspace(-0.2, 1.2, 141)
        g0 = []; g1 = []
        for t in ts:
            y_t = (1-t)*y0 + t*y_star
            y_t = y_t - np.mean(y_t)
            cap_t, logcap_t, theta_t = solver.cap_from_y(y_t)
            gamma_t = nus - 0.5*D_use*theta_t
            # only plot where gamma>0 to avoid inf
            if np.all(gamma_t > 0):
                gval = (-0.5*D_use)*logcap_t + np.sum(gammaln(gamma_t)) - 2.0*np.sum(gamma_t*np.log(masses))
                g1.append(gval)
            else:
                g1.append(np.nan)
            # baseline θ fixed but evaluate g along line for cap term only (illustrative)
            g0.append((-0.5*D_use)*logtau)  # flat line for cap part under baseline θ; full bound not path-dependent
        plt.figure(figsize=(7,4))
        plt.plot(ts, g1, label="log C(y) along path", lw=2)
        plt.axvline(0, color="#888", ls="--"); plt.axvline(1, color="#888", ls="--")
        plt.xlabel("t in y(t)=(1−t)·0 + t·y*"); plt.ylabel("log C(y)")
        plt.title(f"Path-wise objective on {name}")
        plt.legend(); plt.tight_layout()
        plt.savefig(os.path.join(save_dir, f"{name.replace(' ','_')}_path_logC.png"), dpi=200)
        if show_figs: plt.show()
        plt.close()

    # Summary bar plots
    names = [r["name"] for r in results]
    Cb = np.array([r["C_baseline"] for r in results])
    Co = np.array([r["C_opt"] for r in results])
    imp = np.array([r["improve"] for r in results])

    x = np.arange(len(names)); w=0.36
    plt.figure(figsize=(12,5))
    plt.subplot(1,2,1)
    plt.bar(x - w/2, Cb, w, label="Baseline (θ@y=0, cap=τ)", color="#ff7f0e")
    plt.bar(x + w/2, Co, w, label="Optimized (θ(y), cap from y*)", color="#1f77b4")
    plt.yscale("log")
    plt.xticks(x, names, rotation=15, ha="right")
    plt.ylabel("Upper-bound constant C (log scale)")
    plt.title("Our capacity-optimized bound vs uniform-θ baseline")
    plt.legend()

    plt.subplot(1,2,2)
    plt.bar(x, imp, width=0.6, color="#2ca02c")
    plt.xticks(x, names, rotation=15, ha="right")
    plt.ylabel("Improvement factor C_baseline / C_optimized")
    plt.title("Improvement factor (higher is better)")
    plt.tight_layout()
    out = os.path.join(save_dir, "summary_improvement.png")
    plt.savefig(out, dpi=220)
    if show_figs: plt.show()
    plt.close()
    print(f"\nSaved summary figure to {out}")

    # Print table for paper
    print("\n=== Table (for manuscript) ===")
    for r in results:
        print(f"{r['name']}: "
              f"C_base={r['C_baseline']:.4e}, C_opt={r['C_opt']:.4e}, "
              f"improve={r['improve']:.3f}, feasible(base/opt)={r['feasible_baseline']}/{r['feasible_opt']}")

if __name__ == "__main__":
    run_compare(save_dir="figs", show_figs=False)