# -*- coding: utf-8 -*-
"""
Capacity-optimized nonperturbative bounds vs. uniform-theta baseline (tau)
- Optimize y to minimize final bound constant C(y) subject to gamma>0
- Compare against baseline at y=0 (theta_uniform, cap=tau)

This version outputs only two consolidated figures for:
- Double Ladder (4 rungs)
- Wheel (rim=6, D=3.2)

Each figure shows per-graph mosaics:
  Row 1: θ baseline, θ optimized, Δθ (red: +, blue: -)
  Row 2: γ baseline, γ optimized, Δγ (green: +, purple: -)
- Edge values are labeled in white boxes offset from edges to avoid overlap
- Nodes are white with dark borders and black text for better readability
- Figure size scaled to 0.85x; enlarged top header area for title/info; legend moved to dedicated header axis
"""

import os, time, math, warnings
warnings.filterwarnings("ignore", message=".*alltrue.*", category=DeprecationWarning)

# Non-interactive backend by default
import matplotlib
matplotlib.use("Agg")

import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib import lines as mlines
from matplotlib.cm import ScalarMappable
from matplotlib.gridspec import GridSpec
from scipy.linalg import cholesky, cho_solve
from scipy.optimize import minimize
from scipy.special import gammaln

# ---------------------------
# Graph builders (MultiGraph)
# ---------------------------

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

def get_graphs_and_params_only_two():
    eps = 0.1
    D_phen = 4.0 - 2.0*eps  # 3.8
    graphs = [
        ("Double Ladder (4 rungs)", graph_double_ladder(4), D_phen, "L=3 ladder"),
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
    for k in range(len(eu)):
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
    if logtau < 50:
        tau = float(round(tau))
    return tau, logtau

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
    cap, logcap, theta = solverU.cap_from_y(y)
    theta = np.asarray(theta, dtype=np.float64)
    gamma = nus - 0.5*D*theta
    viol = np.maximum(0.0, delta - gamma)
    penalty = mu * np.sum(viol*viol)
    logC = (-0.5*D)*logcap + np.sum(gammaln(gamma)) - 2.0*np.sum(gamma*np.log(masses))
    return logC + penalty, logC, penalty, theta, gamma, cap

# ---------------------------
# Optimization over y (m-1 free vars)
# ---------------------------

def optimize_y(solverU: USolver, D, nus, masses, n_restarts=6, maxiter=300, seed=0):
    rng = np.random.default_rng(seed)
    m = solverU.m
    inits = [np.zeros(m-1, dtype=np.float64)]
    for _ in range(n_restarts-1):
        x0 = 0.5 * rng.standard_normal(m-1)
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
# Drawing helpers (labels, styles, layout)
# ---------------------------

def default_positions(name, G):
    name_l = name.lower()
    if "wheel" in name_l:
        return nx.circular_layout(G)
    if "ladder" in name_l:
        return nx.spring_layout(G, seed=1)
    return nx.spring_layout(G, seed=0)

def _pair_edges(G: nx.MultiGraph):
    pair_to_edges = {}
    for (u,v,k) in G.edges(keys=True):
        a,b = (u,v) if u<=v else (v,u)
        pair_to_edges.setdefault((a,b), []).append((u,v,k))
    return pair_to_edges

def _layout_scale(pos):
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    return max(max(xs)-min(xs), max(ys)-min(ys), 1.0)

def draw_graph_values(ax, G: nx.MultiGraph, values, pos,
                      cmap="viridis", vmin=None, vmax=None,
                      width_scale=3.2, show_nodes=True,
                      show_labels=True, label_fmt="{:.2f}",
                      label_box=True, node_face="#ffffff",
                      node_edge="#333333", node_text="#111111"):
    nodes, eu, ev, edges = extract_edge_list(G)
    vals = np.asarray(values, dtype=float)
    if vmin is None: vmin = float(np.nanmin(vals))
    if vmax is None: vmax = float(np.nanmax(vals))
    norm = plt.Normalize(vmin=vmin, vmax=vmax)
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)

    if show_nodes:
        nx.draw_networkx_nodes(G, pos, node_color=node_face, node_size=320, ax=ax,
                               linewidths=1.0, edgecolors=node_edge)
        nx.draw_networkx_labels(G, pos, font_size=9, font_color=node_text, ax=ax)

    pair_to_edges = _pair_edges(G)
    scale = _layout_scale(pos)

    for pair, el in pair_to_edges.items():
        K = len(el)
        rads = [0.0] if K==1 else np.linspace(-0.28, 0.28, K)
        for i,(u,v,k) in enumerate(el):
            idx = None
            for j,(uu,vv,kk) in enumerate(edges):
                if uu==u and vv==v and kk==k:
                    idx = j; break
            val = vals[idx]
            color = sm.to_rgba(val)
            width = 1.0 + width_scale*(0 if vmax==vmin else (val - vmin)/(vmax - vmin + 1e-12))
            nx.draw_networkx_edges(
                G, pos, edgelist=[(u,v)], ax=ax,
                edge_color=[color], width=width,
                connectionstyle=f"arc3,rad={rads[i]}",
                alpha=0.95
            )
            if show_labels:
                x1,y1 = pos[u]; x2,y2 = pos[v]
                mx, my = (x1+x2)/2.0, (y1+y2)/2.0
                dx, dy = (x2-x1), (y2-y1)
                elen = math.hypot(dx, dy)
                if elen < 1e-12:
                    nx_, ny_ = 0.0, 1.0
                else:
                    nx_, ny_ = -dy/elen, dx/elen
                base_off = 0.06 * scale
                extra_off = 0.10 * scale * (1.0 if rads[i] >= 0 else -1.0) * abs(rads[i]) / 0.28
                ox = (base_off + extra_off) * nx_
                oy = (base_off + extra_off) * ny_
                txt = label_fmt.format(val)
                bbox = dict(facecolor="white", edgecolor="#aaaaaa", alpha=0.85, pad=1.0) if label_box else None
                ax.text(mx+ox, my+oy, txt, fontsize=8, color="#222", ha="center", va="center",
                        bbox=bbox, clip_on=False)

    ax.axis("off")
    return sm

def draw_graph_delta(ax, G: nx.MultiGraph, delta, pos,
                     inc_color="#d62728", dec_color="#1f77b4",
                     width_scale=6.0, zero_thresh=1e-12,
                     show_nodes=True, node_face="#ffffff",
                     node_edge="#333333", node_text="#111111"):
    nodes, eu, ev, edges = extract_edge_list(G)
    dv = np.asarray(delta, dtype=float)
    if show_nodes:
        nx.draw_networkx_nodes(G, pos, node_color=node_face, node_size=320, ax=ax,
                               linewidths=1.0, edgecolors=node_edge)
        nx.draw_networkx_labels(G, pos, font_size=9, font_color=node_text, ax=ax)

    pair_to_edges = _pair_edges(G)
    mag = np.abs(dv)
    maxmag = float(np.max(mag)) if np.any(np.isfinite(mag)) else 1.0
    for pair, el in pair_to_edges.items():
        K = len(el)
        rads = [0.0] if K==1 else np.linspace(-0.28, 0.28, K)
        for i,(u,v,k) in enumerate(el):
            idx = None
            for j,(uu,vv,kk) in enumerate(edges):
                if uu==u and vv==v and kk==k:
                    idx = j; break
            d = dv[idx]
            m = abs(d)
            if m <= zero_thresh or maxmag == 0:
                color = "#bfbfbf"; width = 0.9; alpha = 0.8
            else:
                color = inc_color if d > 0 else dec_color
                width = 0.9 + width_scale*(m / (maxmag + 1e-15))
                alpha = 0.95
            nx.draw_networkx_edges(
                G, pos, edgelist=[(u,v)], ax=ax,
                edge_color=[color], width=width,
                connectionstyle=f"arc3,rad={rads[i]}",
                alpha=alpha
            )
    ax.axis("off")

# ---------------------------
# Per-graph mosaic figure with enlarged header and legend axis
# ---------------------------

def robust_minmax(arr, low=2, high=98):
    arr = np.asarray(arr, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return 0.0, 1.0
    return float(np.percentile(arr, low)), float(np.percentile(arr, high))

def make_graph_mosaic(r, save_dir, scale=0.85):
    name = r["name"]; G = r["G"]; pos = r["pos"]
    theta0 = r["theta0"]; thetaS = r["theta_star"]
    gamma0 = r["gamma0"]; gammaS = r["gamma_star"]
    D_use = r["D"]

    # Ranges (per-graph unified)
    th_min = float(min(np.min(theta0), np.min(thetaS)))
    th_max = float(max(np.max(theta0), np.max(thetaS)))
    gmin, gmax = robust_minmax(np.concatenate([gamma0, gammaS]), 5, 95)
    if not np.isfinite(gmin) or not np.isfinite(gmax) or gmin>=gmax:
        gmin = float(min(np.min(gamma0), np.min(gammaS)))
        gmax = float(max(np.max(gamma0), np.max(gammaS)))
        if gmin == gmax:
            gmin, gmax = 0.0, 1.0

    # Figure layout: add a top header row with dedicated legend axis at col 3
    base_w, base_h = 12.0, 9.0  # slightly taller base to allow header
    fig_w, fig_h = base_w*scale, base_h*scale
    fig = plt.figure(figsize=(fig_w, fig_h), constrained_layout=True)
    gs = GridSpec(
        3, 4, figure=fig,
        width_ratios=[1, 1, 1, 0.12],   # last col for colorbars + header legend axis
        height_ratios=[0.70, 1, 1]      # enlarged header area
    )

    # Header axes
    ax_header = fig.add_subplot(gs[0, 0:3])
    ax_header.set_axis_off()
    ax_leg = fig.add_subplot(gs[0, 3])
    ax_leg.set_axis_off()

    # Row 1: theta panels + cbar
    ax_th0 = fig.add_subplot(gs[1,0]); ax_th1 = fig.add_subplot(gs[1,1]); ax_dth = fig.add_subplot(gs[1,2]); ax_cbar_th = fig.add_subplot(gs[1,3])
    # Row 2: gamma panels + cbar
    ax_g0 = fig.add_subplot(gs[2,0]); ax_g1 = fig.add_subplot(gs[2,1]); ax_dg = fig.add_subplot(gs[2,2]); ax_cbar_g = fig.add_subplot(gs[2,3])

    # Header content: title + left/right info blocks
    title = f"{name} — capacity-optimized vs baseline"
    # Left block (baseline info)
    left1 = f"D = {D_use:g}   τ = {r['tau']}"
    left2 = f"Baseline: min γ = {np.min(gamma0):.3f}   C_base = {r['C_baseline']:.3e}"
    # Right block (optimized + improvement)
    right1 = f"Optimized: cap* = {r['cap_opt']:.3g}   min γ = {np.min(gammaS):.3f}"
    imp_str = f"×{(r['improve'] if np.isfinite(r['improve']) else np.nan):.2f}"
    right2 = f"C_opt = {r['C_opt']:.3e}   Improve {imp_str}"

    ax_header.text(0.01, 0.92, title, ha="left", va="top", fontsize=14, fontweight="bold")
    ax_header.text(0.01, 0.62, left1, ha="left", va="top", fontsize=11)
    ax_header.text(0.01, 0.40, left2, ha="left", va="top", fontsize=11)
    ax_header.text(0.99, 0.62, right1, ha="right", va="top", fontsize=11)
    ax_header.text(0.99, 0.40, right2, ha="right", va="top", fontsize=11)

    # Legend in dedicated header axis (no overlap with plots)
    inc_th = mlines.Line2D([], [], color="#d62728", lw=3, label="Δθ > 0")
    dec_th = mlines.Line2D([], [], color="#1f77b4", lw=3, label="Δθ < 0")
    inc_g  = mlines.Line2D([], [], color="#2ca02c", lw=3, label="Δγ > 0")
    dec_g  = mlines.Line2D([], [], color="#9467bd", lw=3, label="Δγ < 0")
    leg = ax_leg.legend(handles=[inc_th, dec_th, inc_g, dec_g],
                        loc="center", frameon=True, framealpha=0.95, fontsize=9, ncol=1,
                        borderpad=0.6, labelspacing=0.5, handlelength=2.4)
    for lh in leg.legendHandles:
        lh.set_alpha(0.95)

    # Draw θ panels
    draw_graph_values(ax_th0, G, theta0, pos, cmap="viridis", vmin=th_min, vmax=th_max,
                      show_labels=True, label_fmt="{:.2f}")
    ax_th0.set_title("θ baseline", fontsize=11)
    draw_graph_values(ax_th1, G, thetaS, pos, cmap="viridis", vmin=th_min, vmax=th_max,
                      show_labels=True, label_fmt="{:.2f}")
    ax_th1.set_title("θ optimized", fontsize=11)
    draw_graph_delta(ax_dth, G, thetaS-theta0, pos, inc_color="#d62728", dec_color="#1f77b4")
    ax_dth.set_title("Δθ (opt − base)", fontsize=11)
    sm_th = ScalarMappable(norm=plt.Normalize(vmin=th_min, vmax=th_max), cmap="viridis")
    cbar_th = fig.colorbar(sm_th, cax=ax_cbar_th)
    cbar_th.ax.set_ylabel("θ", rotation=90)

    # Draw γ panels
    draw_graph_values(ax_g0, G, gamma0, pos, cmap="plasma", vmin=gmin, vmax=gmax,
                      show_labels=True, label_fmt="{:.3f}")
    ax_g0.set_title("γ baseline", fontsize=11)
    draw_graph_values(ax_g1, G, gammaS, pos, cmap="plasma", vmin=gmin, vmax=gmax,
                      show_labels=True, label_fmt="{:.3f}")
    ax_g1.set_title("γ optimized", fontsize=11)
    draw_graph_delta(ax_dg, G, gammaS-gamma0, pos, inc_color="#2ca02c", dec_color="#9467bd")
    ax_dg.set_title("Δγ (opt − base)", fontsize=11)
    sm_g = ScalarMappable(norm=plt.Normalize(vmin=gmin, vmax=gmax), cmap="plasma")
    cbar_g = fig.colorbar(sm_g, cax=ax_cbar_g)
    cbar_g.ax.set_ylabel("γ", rotation=90)

    # Final save
    os.makedirs(save_dir, exist_ok=True)
    out_name = f"{name.replace(' ','_').replace('(','').replace(')','')}_mosaic.png"
    out_path = os.path.join(save_dir, out_name)
    fig.savefig(out_path, dpi=240, bbox_inches="tight", pad_inches=0.10)
    plt.close(fig)
    return out_path

# ---------------------------
# End-to-end: only two graphs (Double Ladder, Wheel)
# ---------------------------

def run_two_graphs(save_dir="figs", show_figs=False):
    os.makedirs(save_dir, exist_ok=True)
    results = []
    graphs = get_graphs_and_params_only_two()

    for name, G, D_use, note in graphs:
        print(f"\n== {name} | {note} ==")
        nodes, eu, ev, edges = extract_edge_list(G)
        n, m = len(nodes), len(edges)
        solver = USolver(n, eu, ev)

        # physics params
        nus = np.ones(m, dtype=np.float64)
        masses = np.ones(m, dtype=np.float64)

        # Baseline
        y0 = np.zeros(m, dtype=np.float64)
        theta0 = solver.grad_logU(y0)
        tau, logtau = spanning_tree_count(G)
        logcap0 = math.log(tau)
        gamma0 = nus - 0.5*D_use*theta0
        feasible0 = bool(np.all(gamma0 > 0))
        logC0 = (-0.5*D_use)*logcap0 + np.sum(gammaln(gamma0)) - 2.0*np.sum(gamma0*np.log(masses))
        C0 = float(np.exp(logC0)) if abs(logC0) < 700 else float('inf')
        print(f"baseline: tau={tau:g}, feasible={feasible0}, min γ={gamma0.min():.4f}")

        # Optimize
        t0 = time.perf_counter()
        best = optimize_y(solver, D_use, nus, masses, n_restarts=8, maxiter=600, seed=42)
        t1 = time.perf_counter()
        y_star = best["y"]; theta_star = best["theta"]; gamma_star = best["gamma"]
        cap_star = best["cap"]; logC_star = best["logC"]; C_star = float(np.exp(logC_star)) if abs(logC_star) < 700 else float('inf')
        feasible_star = best["feasible"]
        print(f"optimized: cap={cap_star:.6g}, feasible={feasible_star}, min γ={gamma_star.min():.4f}, runtime={t1-t0:.3f}s")

        pos = default_positions(name, G)

        r = {
            "name": name, "note": note, "n": n, "m": m, "D": D_use,
            "G": G, "pos": pos, "eu": eu, "ev": ev, "edges": edges,
            "tau": tau, "cap_opt": cap_star,
            "C_baseline": C0, "C_opt": C_star,
            "improve": C0 / C_star if (C_star>0 and np.isfinite(C_star)) else np.nan,
            "feasible_baseline": feasible0, "feasible_opt": feasible_star,
            "theta0": theta0, "theta_star": theta_star,
            "gamma0": gamma0, "gamma_star": gamma_star,
            "y_star": y_star
        }
        results.append(r)

        # Make figure for this graph
        out_path = make_graph_mosaic(r, save_dir, scale=0.85)
        if show_figs:
            try:
                from PIL import Image
                Image.open(out_path).show()
            except Exception:
                pass
        print(f"Saved: {out_path}")

    # Print compact table for record
    print("\n=== Table (compact) ===")
    for r in results:
        print(f"{r['name']}: C_base={r['C_baseline']:.4e}, C_opt={r['C_opt']:.4e}, "
              f"improve={r['improve']:.3f}, feasible(base/opt)={r['feasible_baseline']}/{r['feasible_opt']}")

if __name__ == "__main__":
    run_two_graphs(save_dir="figs", show_figs=False)