"""
LOCAL CURVATURE CONSTRAINTS on circuit gates.

Hypothesis: for a circuit computing CLIQUE, gates at specific
positions MUST have curvature ≤ -c(position).

If c(position) grows: those gates need high fan-out (expanding neighborhood).
High fan-out at many positions → many edges → many gates.

MEASUREMENT: How does per-gate curvature depend on gate's DEPTH
and ROLE in the circuit?

Separate curvatures by:
  - Gate type (AND vs OR)
  - Gate depth (from inputs)
  - Gate's "centrality" (how important for output)
"""

import random
import math
from collections import defaultdict


def build_circuit_graph(n, gates):
    adj = defaultdict(set)
    for gtype, inp1, inp2, out in gates:
        adj[out].add(inp1); adj[inp1].add(out)
        if inp2 >= 0:
            adj[out].add(inp2); adj[inp2].add(out)
    return adj


def compute_depth(n, gates):
    depth = {i: 0 for i in range(n)}
    for gtype, inp1, inp2, out in gates:
        d1 = depth.get(inp1, 0)
        d2 = depth.get(inp2, 0) if inp2 >= 0 else 0
        depth[out] = max(d1, d2) + 1
    return depth


def ollivier_ricci(adj, u, v):
    nu = adj[u]; nv = adj[v]
    common = nu & nv
    du = len(nu); dv = len(nv)
    if du == 0 or dv == 0: return 0
    return (len(common) + 2) / max(du, dv) - 1


def per_gate_curvature(n, gates):
    """Compute curvature for each gate, annotated with depth and type."""
    adj = build_circuit_graph(n, gates)
    depth = compute_depth(n, gates)
    max_depth = max(depth.values()) if depth else 0

    results = []
    for gi, (gtype, inp1, inp2, out) in enumerate(gates):
        k1 = ollivier_ricci(adj, inp1, out)
        d = depth[out]
        gtype_name = ['AND', 'OR', 'NOT'][gtype] if isinstance(gtype, int) else gtype

        results.append({
            'gate': gi, 'type': gtype_name, 'depth': d,
            'depth_frac': d / max_depth if max_depth > 0 else 0,
            'curvature': k1,
            'degree_out': len(adj[out]),
            'degree_in1': len(adj[inp1]),
        })

        if inp2 >= 0:
            k2 = ollivier_ricci(adj, inp2, out)
            results.append({
                'gate': gi, 'type': gtype_name, 'depth': d,
                'depth_frac': d / max_depth if max_depth > 0 else 0,
                'curvature': k2,
                'degree_out': len(adj[out]),
                'degree_in1': len(adj[inp2]),
            })

    return results


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
    print("=" * 65)
    print("  LOCAL CURVATURE vs DEPTH in computation spacetime")
    print("=" * 65)

    from mono3sat import generate_all_mono3sat_clauses

    for label, circuit_builder in [
        ("OR-10", lambda: ([(('OR', i, i+1, 10+i)) for i in range(9)], 10)),
        ("TRI-K5", lambda: build_triangle_circuit(5)),
        ("TRI-K6", lambda: build_triangle_circuit(6)),
        ("TRI-K7", lambda: build_triangle_circuit(7)),
    ]:
        gates, n = circuit_builder()
        results = per_gate_curvature(n, gates)

        if not results:
            continue

        # Bin by depth fraction
        bins = defaultdict(list)
        for r in results:
            b = int(r['depth_frac'] * 4)  # 5 bins: 0-0.2, 0.2-0.4, ...
            b = min(b, 4)
            bins[b].append(r['curvature'])

        print(f"\n  {label} (n={n}, s={len(gates)}):")
        print(f"  {'Depth bin':<15} {'avg κ':>8} {'min κ':>8} {'count':>6}")
        print(f"  {'-'*40}")

        for b in sorted(bins.keys()):
            kvs = bins[b]
            avg_k = sum(kvs) / len(kvs)
            min_k = min(kvs)
            depth_range = f"{b*0.25:.2f}-{(b+1)*0.25:.2f}"
            print(f"  {depth_range:<15} {avg_k:>8.3f} {min_k:>8.3f} {len(kvs):>6}")

        # By gate type
        by_type = defaultdict(list)
        for r in results:
            by_type[r['type']].append(r['curvature'])

        print(f"  By type:")
        for t in sorted(by_type.keys()):
            kvs = by_type[t]
            print(f"    {t}: avg κ = {sum(kvs)/len(kvs):.3f}, n={len(kvs)}")

    print(f"\n{'='*65}")
    print("  KEY QUESTION: Does curvature at BOTTOM differ from TOP?")
    print("  If bottom more negative (expanding): fan-out region.")
    print("  If top more negative: convergence to output.")
    print("  The GRADIENT κ(depth) = new structural invariant of circuit.")
    print(f"{'='*65}")


if __name__ == "__main__":
    main()
