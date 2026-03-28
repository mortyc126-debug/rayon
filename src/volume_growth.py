"""
DISCRETE VOLUME GROWTH from Ollivier-Ricci curvature.

Ollivier (2009): κ(x,y) = 1 - W₁(μ_x, μ_y)/d(x,y).
If κ ≤ -c: W₁(μ_x^t, μ_y^t) ≥ (1+c)^t × d(x,y).

This means: random walks from adjacent vertices DIVERGE exponentially.
Divergence → volume growth: more vertices reachable at each step.

FORMAL CLAIM:
For graph G with ORC κ(e) ≤ -c for all edges e:
  |B_r(v)| ≥ min((1+c)^r, |V(G)|)
where B_r(v) = ball of radius r around v.

PROOF ATTEMPT:
  By induction on r.
  B_0 = {v}. |B_0| = 1. (1+c)^0 = 1. ✓

  B_{r+1} = B_r ∪ {neighbors of B_r not in B_r}.
  New vertices at step r+1: N_{r+1} = |B_{r+1}| - |B_r|.

  CLAIM: N_{r+1} ≥ c × |B_r|.

  Why? Negative curvature → each vertex on the BOUNDARY of B_r
  has neighbors OUTSIDE B_r (expansion). The number of outside
  neighbors ≥ c × boundary size.

  If boundary ≈ |B_r| (for expanding sets): N_{r+1} ≥ c × |B_r|.
  Then: |B_{r+1}| = |B_r| + N_{r+1} ≥ |B_r| × (1+c). ✓

  But: "boundary ≈ |B_r|" is NOT always true. For highly connected
  graphs: boundary might be SMALL relative to interior.

  WEAKER CLAIM: N_{r+1} ≥ c × |∂B_r| where ∂B_r = boundary.
  With vertex expansion h(G): |∂S| ≥ h × |S| for |S| ≤ |V|/2.
  Negative curvature → h ≥ c' > 0 (Ollivier 2010).

  Then: N_{r+1} ≥ c × c' × |B_r| for |B_r| ≤ |V|/2.
  |B_{r+1}| ≥ (1 + cc') × |B_r|. Exponential growth.

EXPERIMENT: Verify volume growth in our circuit DAGs.
"""

from collections import defaultdict
import math
import random


def compute_ball_sizes(adj, start, max_r):
    """BFS from start, recording |B_r| for each r."""
    visited = {start}
    frontier = {start}
    balls = [1]  # |B_0| = 1

    for r in range(1, max_r + 1):
        new_frontier = set()
        for v in frontier:
            for u in adj[v]:
                if u not in visited:
                    visited.add(u)
                    new_frontier.add(u)
        frontier = new_frontier
        balls.append(len(visited))
        if not frontier:
            break

    return balls


def build_circuit_adj(n, gates):
    adj = defaultdict(set)
    for gtype, inp1, inp2, out in gates:
        adj[out].add(inp1); adj[inp1].add(out)
        if inp2 >= 0:
            adj[out].add(inp2); adj[inp2].add(out)
    return adj


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
    print("=" * 60)
    print("  VOLUME GROWTH in circuit DAGs")
    print("  |B_r| vs r: exponential growth = negative curvature")
    print("=" * 60)

    for label, builder in [
        ("OR-10", lambda: ([(('OR', i, i+1, 10+i)) for i in range(9)], 10)),
        ("OR-15", lambda: ([(('OR', i, i+1, 15+i)) for i in range(14)], 15)),
        ("TRI-K5", lambda: build_triangle_circuit(5)),
        ("TRI-K6", lambda: build_triangle_circuit(6)),
        ("TRI-K7", lambda: build_triangle_circuit(7)),
    ]:
        gates, n = builder()
        s = len(gates)
        adj = build_circuit_adj(n, gates)
        output = gates[-1][3] if gates else 0

        balls = compute_ball_sizes(adj, output, 20)

        print(f"\n  {label} (n={n}, s={s}, total wires={n+s}):")
        print(f"  {'r':>4} {'|B_r|':>8} {'growth':>8} {'(1+0.5)^r':>10}")

        for r in range(len(balls)):
            growth = balls[r] / balls[r-1] if r > 0 and balls[r-1] > 0 else 1
            expected = 1.5**r
            print(f"  {r:>4} {balls[r]:>8} {growth:>8.2f} {expected:>10.1f}")
            if balls[r] >= n + s:
                print(f"  (saturated at r={r})")
                break

    print(f"\n{'='*60}")
    print("  ANALYSIS: Does |B_r| grow as (1+c)^r?")
    print("  If growth factor ≈ constant > 1: EXPONENTIAL GROWTH. ✓")
    print("  If growth factor → 1: linear/sub-exponential. ✗")
    print()
    print("  For circuit size bound: s + n ≥ |B_D| ≥ (1+c)^D.")
    print("  With D ≥ n^{1/4}: s ≥ (1+c)^{n^{1/4}} - n = SUPER-POLY.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
