"""
IDEA B: Computation Spacetime Curvature.

Compute Ollivier-Ricci curvature of the CIRCUIT DAG
(not the solution space — the circuit itself).

Circuit DAG: nodes = input wires + gates. Edges = wire connections.
Curvature at each edge: κ(u,v) via optimal transport on neighborhoods.

HIGH negative curvature: "expanding" computation (each gate creates diversity).
ZERO curvature: "flat" computation (linear processing).
POSITIVE curvature: "converging" computation (gates merge streams).

Hypothesis: CLIQUE circuits have MORE NEGATIVE curvature than OR circuits.
If negative curvature = complexity: lower bound.
"""

import random
import math
from collections import defaultdict


def build_circuit_graph(n, gates):
    """Build undirected graph of circuit DAG for curvature computation."""
    adj = defaultdict(set)
    for gtype, inp1, inp2, out in gates:
        adj[out].add(inp1); adj[inp1].add(out)
        if inp2 >= 0:
            adj[out].add(inp2); adj[inp2].add(out)
    return adj


def ollivier_ricci_curvature(adj, u, v):
    """Simplified Ollivier-Ricci curvature for edge (u,v).
    κ(u,v) = 1 - W₁(μ_u, μ_v) / d(u,v).
    For graph: d(u,v) = 1 (adjacent).
    μ_u = uniform on neighbors of u.
    W₁ = earth mover's distance.

    Simplified: κ ≈ (|common_neighbors| + 2) / max(|N(u)|, |N(v)|) - 1
    (Lin-Lu-Yau approximation).
    """
    nu = adj[u]
    nv = adj[v]
    common = nu & nv
    du = len(nu)
    dv = len(nv)

    if du == 0 or dv == 0:
        return 0

    # Lin-Lu-Yau lower bound
    kappa = (len(common) + 2) / max(du, dv) - 1
    return kappa


def compute_circuit_curvature(n, gates):
    """Compute average Ollivier-Ricci curvature of circuit DAG."""
    adj = build_circuit_graph(n, gates)

    curvatures = []
    for gtype, inp1, inp2, out in gates:
        k1 = ollivier_ricci_curvature(adj, inp1, out)
        curvatures.append(k1)
        if inp2 >= 0:
            k2 = ollivier_ricci_curvature(adj, inp2, out)
            curvatures.append(k2)

    if not curvatures:
        return 0, 0, 0

    avg_k = sum(curvatures) / len(curvatures)
    min_k = min(curvatures)
    max_k = max(curvatures)
    return avg_k, min_k, max_k


def build_or_circuit(n):
    gates = []; nid = n; cur = 0
    for i in range(1, n):
        out = nid; gates.append(('OR', cur, i, out)); cur = out; nid += 1
    return gates

def build_and_circuit(n):
    gates = []; nid = n; cur = 0
    for i in range(1, n):
        out = nid; gates.append(('AND', cur, i, out)); cur = out; nid += 1
    return gates

def build_msat_circuit(n, clauses):
    gates = []; nid = n; c_outs = []
    for cl in clauses:
        v0,v1,v2 = cl
        a=nid; gates.append(('OR',v0,v1,a)); nid+=1
        b=nid; gates.append(('OR',a,v2,b)); nid+=1
        c_outs.append(b)
    cur = c_outs[0]
    for ci in c_outs[1:]:
        g=nid; gates.append(('AND',cur,ci,g)); nid+=1; cur=g
    return gates

def build_triangle_circuit(N):
    n = N*(N-1)//2
    eidx = {}; idx = 0
    for i in range(N):
        for j in range(i+1, N):
            eidx[(i,j)] = idx; idx += 1
    gates = []; nid = n; touts = []
    for i in range(N):
        for j in range(i+1, N):
            for k in range(j+1, N):
                a=nid; gates.append(('AND',eidx[(i,j)],eidx[(i,k)],a)); nid+=1
                b=nid; gates.append(('AND',a,eidx[(j,k)],b)); nid+=1
                touts.append(b)
    cur = touts[0]
    for t in touts[1:]:
        g=nid; gates.append(('OR',cur,t,g)); nid+=1; cur=g
    return gates, n


def main():
    random.seed(42)
    print("=" * 60)
    print("  COMPUTATION SPACETIME CURVATURE (Ollivier-Ricci on Circuit DAG)")
    print("=" * 60)

    from mono3sat import generate_all_mono3sat_clauses

    print(f"\n  {'Circuit':<20} {'n':>4} {'s':>5} {'avg κ':>8} {'min κ':>8} {'max κ':>8}")
    print("  " + "-" * 50)

    for n in range(5, 16):
        # OR
        gates = build_or_circuit(n)
        avg, mn, mx = compute_circuit_curvature(n, gates)
        print(f"  {'OR-'+str(n):<20} {n:>4} {len(gates):>5} {avg:>8.3f} {mn:>8.3f} {mx:>8.3f}")

    print()
    for n in range(5, 16):
        # MSAT
        all_cl = generate_all_mono3sat_clauses(n)
        clauses = random.sample(all_cl, min(len(all_cl), 3*n))
        gates = build_msat_circuit(n, clauses)
        avg, mn, mx = compute_circuit_curvature(n, gates)
        print(f"  {'MSAT-'+str(n):<20} {n:>4} {len(gates):>5} {avg:>8.3f} {mn:>8.3f} {mx:>8.3f}")

    print()
    for N in range(4, 8):
        gates, n = build_triangle_circuit(N)
        avg, mn, mx = compute_circuit_curvature(n, gates)
        print(f"  {'TRI-K'+str(N):<20} {n:>4} {len(gates):>5} {avg:>8.3f} {mn:>8.3f} {mx:>8.3f}")

    print(f"\n  IF avg κ differs between P and NP-hard circuits:")
    print(f"  → curvature of computation spacetime = complexity measure")
    print(f"  → lower bound via curvature → circuit lower bound")


if __name__ == "__main__":
    main()
