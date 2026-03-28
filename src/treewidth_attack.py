"""
TREEWIDTH OF COMPUTATION: A topological measure.

NOT counting — measuring SHAPE.

Treewidth tw(G) of a graph G: minimum width of a tree decomposition.
  tw = 1: G is a tree (formula)
  tw = w: G is "w edges away from a tree"

For a circuit C with DAG D:
  tw(D) measures the "structural complexity" of the circuit.

KEY RELATIONSHIP:
  formula_size(f) ≤ circuit_size(f) × 2^{tw(D)}

  (Each gate is duplicated at most 2^{tw} times when unfolding
   the circuit into a formula, because the tree decomposition
   has bags of size ≤ tw+1.)

  Actually more precisely:
  formula_size(f) ≤ circuit_size(f) × circuit_size(f)^{tw}
                  = circuit_size^{tw+1}

  So: circuit_size^{tw+1} ≥ formula_size
      circuit_size ≥ formula_size^{1/(tw+1)}

  For formula ≥ 2^{Ω(N^{1/6})} (CLIQUE):
      circuit_size ≥ 2^{Ω(N^{1/6}/(tw+1))}

  For tw = O(1): size ≥ 2^{Ω(N^{1/6})} — EXPONENTIAL!
  For tw = O(N^{1/6}): size ≥ 2^{O(1)} — trivial.
  For tw = O(log N): size ≥ 2^{Ω(N^{1/6}/log N)} — still super-poly!

  THE QUESTION: Is tw(optimal CLIQUE circuit) = Ω(N^{1/6})?
  Or is it O(log N)?

  If tw = O(log N): size ≥ super-poly. P ≠ NP!
  If tw = Ω(N^{1/6}): formula bound absorbed. No conclusion.

  Wait, I have this backwards. Let me reconsider.

  We KNOW: formula(CLIQUE) ≥ 2^{Ω(N^{1/6})}.
  We want to PROVE: circuit(CLIQUE) = super-poly.

  If the optimal circuit has treewidth tw:
    formula ≤ size^{tw+1}
    2^{Ω(N^{1/6})} ≤ size^{tw+1}
    size ≥ 2^{Ω(N^{1/6})/(tw+1)}

  For size = poly(N) = N^c:
    N^c ≥ 2^{Ω(N^{1/6})/(tw+1)}
    c log N ≥ Ω(N^{1/6})/(tw+1)
    tw+1 ≥ Ω(N^{1/6})/(c log N)
    tw ≥ Ω(N^{1/6}/log N)

  So: if circuit_size = poly: tw ≥ Ω(N^{1/6}/log N).

  Can a polynomial circuit have treewidth Ω(N^{1/6}/log N)?
  YES! A circuit of size s can have treewidth up to s.
  For s = N^c: tw ≤ N^c >> N^{1/6}/log N. Easily satisfiable.

  So: treewidth alone doesn't give contradiction.

  BUT: If we can prove tw(any circuit for CLIQUE) = O(polylog(N)):
    Then size ≥ 2^{Ω(N^{1/6}/polylog N)} = super-poly.
    P ≠ NP!

  Is there a reason CLIQUE circuits should have small treewidth?

  CLIQUE has symmetry S_N. A symmetric circuit can be decomposed
  along the symmetry. The treewidth of a symmetric circuit is
  related to the "representation complexity" of S_N.

  For S_N: the representation theory involves partitions of N.
  The number of irreducible representations = p(N) (partition number).
  The largest representation has dimension ≈ N!/√(2πN). Huge.

  But the relevant representation for CLIQUE is specific:
  it corresponds to the partition related to k-subsets.

EXPERIMENT: Compute treewidth of actual circuits for small functions.
Measure: does treewidth grow with function complexity?
"""

import itertools
from collections import defaultdict
import random
import math
import sys


def compute_treewidth_upper_bound(n, gates):
    """Upper bound on treewidth via elimination ordering.

    Build the undirected graph of the circuit DAG.
    Use greedy elimination to get upper bound on treewidth.
    """
    # Build adjacency from gates
    adj = defaultdict(set)
    all_nodes = set(range(n))  # inputs

    for gi, (gtype, inp1, inp2, out) in enumerate(gates):
        all_nodes.add(out)
        adj[inp1].add(out)
        adj[out].add(inp1)
        if inp2 >= 0:
            adj[inp2].add(out)
            adj[out].add(inp2)

    # Greedy elimination: remove node with min degree, add edges between neighbors
    nodes = set(all_nodes)
    tw = 0

    while nodes:
        # Find min degree node
        min_deg = float('inf')
        min_node = None
        for v in nodes:
            deg = len(adj[v] & nodes)
            if deg < min_deg:
                min_deg = deg
                min_node = v

        # Eliminate: connect all neighbors
        neighbors = adj[min_node] & nodes
        tw = max(tw, len(neighbors))

        for u in neighbors:
            for w in neighbors:
                if u != w:
                    adj[u].add(w)
                    adj[w].add(u)

        nodes.remove(min_node)

    return tw


def build_msat_circuit(n, clauses):
    """Build MSAT circuit and return gates list."""
    gates = []
    next_id = n

    clause_outs = []
    for clause in clauses:
        v0, v1, v2 = clause
        or1 = next_id
        gates.append(('OR', v0, v1, or1))
        next_id += 1
        or2 = next_id
        gates.append(('OR', or1, v2, or2))
        next_id += 1
        clause_outs.append(or2)

    current = clause_outs[0]
    for i in range(1, len(clause_outs)):
        new_id = next_id
        gates.append(('AND', current, clause_outs[i], new_id))
        current = new_id
        next_id += 1

    return gates, current


def build_triangle_circuit(N):
    """Build triangle detection circuit."""
    n = N*(N-1)//2
    edge_idx = {}; idx = 0
    for i in range(N):
        for j in range(i+1, N):
            edge_idx[(i,j)] = idx; idx += 1

    gates = []
    next_id = n
    tri_outs = []
    for i in range(N):
        for j in range(i+1, N):
            for k in range(j+1, N):
                a = next_id; gates.append(('AND', edge_idx[(i,j)], edge_idx[(i,k)], a)); next_id += 1
                b = next_id; gates.append(('AND', a, edge_idx[(j,k)], b)); next_id += 1
                tri_outs.append(b)

    current = tri_outs[0]
    for t in tri_outs[1:]:
        c = next_id; gates.append(('OR', current, t, c)); next_id += 1; current = c

    return gates, current, n


def main():
    random.seed(42)
    print("=" * 70)
    print("  TREEWIDTH OF COMPUTATION")
    print("  Topological measure of circuit structure")
    print("=" * 70)

    from mono3sat import generate_all_mono3sat_clauses

    print(f"\n  {'Function':<20} {'n':>4} {'size':>6} {'tw_upper':>9} "
          f"{'tw/size':>8} {'tw/n':>6}")
    print("  " + "-" * 55)

    # MSAT
    for n_val in range(5, 16):
        all_cl = generate_all_mono3sat_clauses(n_val)
        clauses = random.sample(all_cl, min(len(all_cl), 3*n_val))
        gates, output = build_msat_circuit(n_val, clauses)
        tw = compute_treewidth_upper_bound(n_val, gates)
        size = len(gates)
        print(f"  {'MSAT-'+str(n_val):<20} {n_val:>4} {size:>6} {tw:>9} "
              f"{tw/size:>8.3f} {tw/n_val:>6.2f}")

    # Triangle
    for N in range(4, 8):
        n = N*(N-1)//2
        gates, output, n_bits = build_triangle_circuit(N)
        tw = compute_treewidth_upper_bound(n_bits, gates)
        size = len(gates)
        print(f"  {'TRI-K'+str(N):<20} {n:>4} {size:>6} {tw:>9} "
              f"{tw/size:>8.3f} {tw/n:>6.2f}")

    print(f"\n{'='*70}")
    print("  ANALYSIS")
    print(f"{'='*70}")
    print("""
    Treewidth measures the "topological complexity" of the circuit.

    For FORMULA-LIKE circuits (no fan-out): tw = 1.
    For circuits WITH fan-out: tw > 1.

    The formula-circuit relationship:
      formula ≤ size^{tw+1}
      size ≥ formula^{1/(tw+1)}

    For CLIQUE: formula ≥ 2^{Ω(N^{1/6})}.
    If tw = O(log N): size ≥ 2^{Ω(N^{1/6}/log N)} = SUPER-POLY!

    KEY QUESTION: Can CLIQUE be computed by circuits with tw = O(log N)?

    If YES: this doesn't help (size bound trivializes).
    If NO: proving tw ≥ ω(log N) for CLIQUE circuits gives P ≠ NP!

    Proving treewidth lower bounds for circuits is a TOPOLOGICAL
    question — not counting. It asks about the SHAPE of computation,
    not the number of components.

    This is a concrete, non-counting approach to P ≠ NP.
    """)


if __name__ == "__main__":
    main()
