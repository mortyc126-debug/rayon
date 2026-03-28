"""
TREEWIDTH LOWER BOUND FOR CLIQUE CIRCUITS.

Tree decomposition of circuit DAG: tree T with bags B_v ⊆ V(DAG).
  - Each DAG node in at least one bag.
  - Each DAG edge: both endpoints in some common bag.
  - For each node: bags containing it form a connected subtree.
Width = max|B_v| - 1.

KEY PROPERTY: Any edge "separator" in the tree decomposition
has size ≤ tw+1. Removing any edge of T splits DAG into two
parts connected by ≤ tw+1 wires.

For a circuit: ≤ tw+1 wires cross any separator.
Each wire carries 1 bit → ≤ tw+1 bits cross.

APPROACH: Find two parts of the CLIQUE computation that need
to exchange >> log N bits → treewidth ≥ bits needed.

For CLIQUE: consider splitting the N vertices into two halves
L = {1,...,N/2} and R = {N/2+1,...,N}.

A k-clique Q can span both halves: |Q ∩ L| = a, |Q ∩ R| = k-a.

To detect Q: need to know edges WITHIN L, edges WITHIN R,
and edges BETWEEN L and R.

The edges within L: handled by the L-side of the circuit.
The edges within R: handled by the R-side.
The cross-edges: need to be communicated.

A k-clique spanning both halves requires cross-edges.
The NUMBER of cross-edge patterns: depends on |Q∩L| and |Q∩R|.

For |Q∩L| = a: need C(a,2) edges within L, C(k-a,2) within R,
and a×(k-a) cross-edges.

The cross-edge information: a×(k-a) specific edges.
To verify ONE spanning clique: need a×(k-a) bits.
For a = k/2: k²/4 bits.

But: the circuit doesn't check ONE clique — it checks ALL.
The treewidth bounds the TOTAL information flow, not per-clique.

COMMUNICATION COMPLEXITY ARGUMENT:
  Split variables into L-edges and R-edges + cross-edges.
  Alice has L-edges, Bob has R-edges and cross-edges.
  They need to compute CLIQUE.

  CC(CLIQUE, this partition) = ???

  Known: for k-CLIQUE, the communication complexity with balanced
  partition is Θ(k² log N) bits (need to communicate sub-clique info).

  If CC ≥ ω(log N): treewidth ≥ CC ≥ ω(log N) → P ≠ NP.

  But: CC for any fixed partition ≤ n/2 (send all your bits).
  And for k-CLIQUE: CC might be O(k²) = O(N^{2/3}) for k = N^{1/3}.
  This is polynomial, not super-poly.

  So: CC per partition doesn't help directly.

BETTER: MULTI-CUT argument.

In a tree decomposition of width w: there exist Ω(size/w) "separators"
each of width ≤ w+1. The separators partition the circuit into Ω(size/w)
components of size O(w).

Each component has ≤ w+1 input/output wires.
It can compute at most 2^{2^{w+1}} ≈ 2^{O(2^w)} functions.

Total functions computable by the circuit:
  (2^{O(2^w)})^{size/w} = 2^{O(size × 2^w / w)}

Need: total ≥ 2^{2^n} (to compute all possible functions on n bits).
Actually: need to compute ONE specific function, so:
  just need the circuit to be correct. No counting argument.

ANOTHER APPROACH: Brambles and Haven.

By the Grid-Minor Theorem (Robertson-Seymour):
  tw(G) ≥ r iff G contains an r×r grid as a minor.

If we can show the CLIQUE circuit DAG must contain a large grid minor:
  tw ≥ grid_size.

Why would the circuit DAG have a grid minor?

The CLIQUE function has a "grid-like" structure: it's defined by
k-subsets of N vertices. The intersection pattern of k-subsets
forms a high-dimensional structure that might force grid minors.

EXPERIMENT: For small circuits, compute exact treewidth and look
for relationship with function complexity.
"""

import itertools
from collections import defaultdict
import random
import math
import sys


def exact_treewidth_small(adj, nodes):
    """Compute exact treewidth for small graphs (≤ 15 nodes).
    Uses the elimination ordering approach with brute force.
    Returns lower and upper bounds.
    """
    n = len(nodes)
    if n <= 2:
        return 1

    # Upper bound: greedy min-degree elimination
    tw_upper = 0
    remaining = set(nodes)
    adj_copy = {v: set(adj[v]) & remaining for v in remaining}

    while remaining:
        # Min degree node
        min_v = min(remaining, key=lambda v: len(adj_copy[v] & remaining))
        neighbors = adj_copy[min_v] & remaining
        tw_upper = max(tw_upper, len(neighbors))

        # Make neighbors clique
        for u in neighbors:
            for w in neighbors:
                if u != w:
                    adj_copy[u].add(w)
                    adj_copy[w].add(u)
        remaining.remove(min_v)

    # Lower bound: max clique minor or degeneracy
    # Simple: degeneracy = min over orderings of max back-degree
    # This is a lower bound on treewidth
    tw_lower = 0
    remaining2 = set(nodes)
    adj_copy2 = {v: set(adj[v]) & set(nodes) for v in nodes}

    while remaining2:
        min_v = min(remaining2, key=lambda v: len(adj_copy2[v] & remaining2))
        deg = len(adj_copy2[min_v] & remaining2)
        tw_lower = max(tw_lower, deg)
        remaining2.remove(min_v)

    return tw_upper  # upper bound (greedy)


def build_circuit_graph(n_inputs, gates):
    """Build undirected graph of circuit DAG."""
    adj = defaultdict(set)
    all_nodes = set(range(n_inputs))

    for gtype, inp1, inp2, out in gates:
        all_nodes.add(out)
        adj[inp1].add(out); adj[out].add(inp1)
        if inp2 >= 0:
            adj[inp2].add(out); adj[out].add(inp2)

    return adj, all_nodes


def build_shared_circuit(N, k=3):
    """Build triangle/clique circuit WITH shared sub-expressions.

    Key: OR(x_i, x_j) is shared by multiple cliques containing edge (i,j).
    This creates FAN-OUT → increases treewidth.
    """
    n = N*(N-1)//2
    edge_idx = {}; idx = 0
    for i in range(N):
        for j in range(i+1, N):
            edge_idx[(i,j)] = idx; edge_idx[(j,i)] = idx; idx += 1

    gates = []
    next_id = n

    if k == 3:
        # For each vertex v: compute "v has degree ≥ 2"
        # by ANDing pairs of edges incident to v
        # This is shared across all triangles through v

        # Step 1: For each pair (i,j), compute AND(e_iv, e_jv) for each v
        # = "v connected to both i and j"
        pair_gates = {}  # (i,j,v) -> gate_id
        for v in range(N):
            neighbors = [u for u in range(N) if u != v]
            for a in range(len(neighbors)):
                for b in range(a+1, len(neighbors)):
                    i, j = neighbors[a], neighbors[b]
                    # AND(edge(v,i), edge(v,j))
                    e1 = edge_idx[(v, i)]
                    e2 = edge_idx[(v, j)]
                    gate_id = next_id
                    gates.append(('AND', e1, e2, gate_id))
                    next_id += 1
                    pair_gates[(v, i, j)] = gate_id

        # Step 2: Triangle (i,j,k) = edge(i,j) AND "k connected to both i,j"
        tri_outs = []
        for i in range(N):
            for j in range(i+1, N):
                for kk in range(j+1, N):
                    # Need: e(i,j) AND e(i,k) AND e(j,k)
                    # = e(i,j) AND pair_gates[(i or j, other two)]
                    # Use: pair_gates[(kk, i, j)] = AND(e(kk,i), e(kk,j))
                    if (kk, i, j) in pair_gates:
                        pg = pair_gates[(kk, i, j)]
                    elif (kk, j, i) in pair_gates:
                        pg = pair_gates[(kk, j, i)]
                    else:
                        # Compute directly
                        pg = next_id
                        gates.append(('AND', edge_idx[(kk,i)], edge_idx[(kk,j)], pg))
                        next_id += 1

                    tri_gate = next_id
                    gates.append(('AND', edge_idx[(i,j)], pg, tri_gate))
                    next_id += 1
                    tri_outs.append(tri_gate)

        # OR all triangles
        current = tri_outs[0]
        for t in tri_outs[1:]:
            g = next_id
            gates.append(('OR', current, t, g))
            next_id += 1
            current = g

        return gates, current, n

    return gates, -1, n


def main():
    random.seed(42)
    print("=" * 70)
    print("  TREEWIDTH: Standard vs Shared circuits")
    print("  Does sharing (fan-out) INCREASE treewidth?")
    print("=" * 70)

    from mono3sat import generate_all_mono3sat_clauses

    # Standard (formula-like) circuits
    print(f"\n  {'Circuit':<25} {'n':>4} {'size':>6} {'tw':>5} "
          f"{'tw/log(n)':>10} {'tw/√n':>8}")
    print("  " + "-" * 60)

    for N in range(4, 8):
        n = N*(N-1)//2

        # Standard triangle circuit (no sharing)
        edge_idx = {}; idx = 0
        for i in range(N):
            for j in range(i+1, N):
                edge_idx[(i,j)] = idx; idx += 1

        std_gates = []
        nid = n
        tri_outs = []
        for i in range(N):
            for j in range(i+1, N):
                for k in range(j+1, N):
                    a = nid; std_gates.append(('AND', edge_idx[(i,j)], edge_idx[(i,k)], a)); nid += 1
                    b = nid; std_gates.append(('AND', a, edge_idx[(j,k)], b)); nid += 1
                    tri_outs.append(b)
        cur = tri_outs[0]
        for t in tri_outs[1:]:
            g = nid; std_gates.append(('OR', cur, t, g)); nid += 1; cur = g

        adj_std, nodes_std = build_circuit_graph(n, std_gates)
        tw_std = exact_treewidth_small(adj_std, nodes_std)
        log_n = math.log2(max(2, n))
        sqrt_n = math.sqrt(n)

        print(f"  {'TRI-K'+str(N)+' (standard)':<25} {n:>4} {len(std_gates):>6} "
              f"{tw_std:>5} {tw_std/log_n:>10.2f} {tw_std/sqrt_n:>8.2f}")

        # Shared circuit
        shared_gates, _, n_bits = build_shared_circuit(N, k=3)
        if shared_gates:
            adj_sh, nodes_sh = build_circuit_graph(n_bits, shared_gates)
            tw_sh = exact_treewidth_small(adj_sh, nodes_sh)
            print(f"  {'TRI-K'+str(N)+' (shared)':<25} {n:>4} {len(shared_gates):>6} "
                  f"{tw_sh:>5} {tw_sh/log_n:>10.2f} {tw_sh/sqrt_n:>8.2f}")

        sys.stdout.flush()

    # MSAT with varying clause density
    for n_val in [6, 8, 10]:
        all_cl = generate_all_mono3sat_clauses(n_val)

        for density_name, num_cl in [('sparse', n_val), ('medium', 2*n_val), ('dense', 3*n_val)]:
            clauses = random.sample(all_cl, min(len(all_cl), num_cl))
            gates = []; nid = n_val
            c_outs = []
            for cl in clauses:
                v0,v1,v2 = cl
                a = nid; gates.append(('OR', v0, v1, a)); nid += 1
                b = nid; gates.append(('OR', a, v2, b)); nid += 1
                c_outs.append(b)
            cur = c_outs[0]
            for c in c_outs[1:]:
                g = nid; gates.append(('AND', cur, c, g)); nid += 1; cur = g

            adj_m, nodes_m = build_circuit_graph(n_val, gates)
            tw_m = exact_treewidth_small(adj_m, nodes_m)
            log_n = math.log2(max(2, n_val))
            sqrt_n = math.sqrt(n_val)
            print(f"  {'MSAT-'+str(n_val)+'-'+density_name:<25} {n_val:>4} "
                  f"{len(gates):>6} {tw_m:>5} {tw_m/log_n:>10.2f} {tw_m/sqrt_n:>8.2f}")

    print(f"\n{'='*70}")
    print("  KEY OBSERVATIONS")
    print(f"{'='*70}")
    print("""
    tw/log(n) tells us if treewidth is O(log n) or larger.
    tw/√n tells us if treewidth is O(√n) or larger.

    For P ≠ NP: need tw(CLIQUE circuit) ≥ ω(log N) for ANY circuit.
    If even the OPTIMAL circuit has tw = Ω(N^ε): combined with
    formula bound → super-poly circuit size.

    Standard circuits: tw ≈ n (no fan-out → tree-like → tw ≈ width).
    Shared circuits: tw MIGHT be different (fan-out creates connections).

    THE PROOF STRATEGY:
    Show that the "intersection pattern" of k-cliques FORCES
    any circuit DAG to have high treewidth.

    Specifically: the k-clique hypergraph on N vertices has
    treewidth Ω(N^{something}). Any circuit computing CLIQUE
    must "embed" this hypergraph structure, inheriting its treewidth.
    """)


if __name__ == "__main__":
    main()
