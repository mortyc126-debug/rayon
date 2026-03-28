"""
FORMAL PROOF ATTEMPT: distinct subtrees ≥ n^{Ω(k)} for k-CLIQUE.

SETUP:
  k-CLIQUE on N vertices, n = C(N,2) edge variables.
  Decision tree: at each node, query one edge variable e_{ij}.
  After querying t edges: the state is a "partial graph" — a map
  from t edges to {present, absent}.

DEFINITION: Two partial graphs P₁, P₂ are "equivalent" if
  for ALL completions G of the remaining edges:
    k-CLIQUE(P₁ ∪ G) = k-CLIQUE(P₂ ∪ G)

  If P₁ and P₂ are equivalent: their subtrees are identical.
  If not equivalent: their subtrees differ (some completion G
  distinguishes them).

THEOREM ATTEMPT: The number of non-equivalent partial graphs
  after querying C(k,2) edges is at least C(N,k).

PROOF SKETCH:
  For each potential k-clique Q (set of k vertices), define the
  partial graph P_Q that reveals ALL C(k,2) edges within Q as "present".

  CLAIM: P_{Q₁} and P_{Q₂} are non-equivalent for Q₁ ≠ Q₂.

  PROOF OF CLAIM:
  P_{Q₁}: all edges within Q₁ are present. Q₁ IS a k-clique in P_{Q₁}.
  For the COMPLETION where all other edges are absent:
    k-CLIQUE(P_{Q₁} ∪ "all absent") = 1 (Q₁ is a clique)
    k-CLIQUE(P_{Q₂} ∪ "all absent") = ?

  If Q₂ ≠ Q₁: P_{Q₂} has all edges within Q₂ present.
  With all OTHER edges absent: is there a k-clique?
  Yes: Q₂ is a k-clique (its edges are all present in P_{Q₂}).

  So both are 1... this doesn't distinguish them.

  REVISED APPROACH: We need completions that distinguish P_{Q₁} from P_{Q₂}.

  Consider the partial graph P that reveals C(k,2) edges and
  SOME are present, SOME are absent.

  The critical case: P reveals edges that form an "almost-clique"
  on k vertices but with ONE edge missing.

  For vertex set S with |S| = k: if all C(k,2)-1 edges are present
  and edge e is absent: S is NOT a k-clique.
  In the completion: e can be present or absent.
  If we query e later: the answer determines if S is a clique.

  Different vertex sets S give DIFFERENT "almost-cliques" with
  DIFFERENT missing edges. These are non-equivalent partial graphs.

  Number of such configurations: at least C(N,k) × C(k,2)
  (choose S, then choose which edge is missing).

  But many of these overlap in their query sets.

  CLEANER APPROACH: Count non-isomorphic partial graphs.

EXPERIMENT: Directly verify that distinct partial graph configurations
  grow as n^{Ω(k)} for our test cases.
"""

import itertools
from collections import defaultdict
import math
import sys


def count_nonequivalent_partial_graphs(N, k, t_edges):
    """Count the number of non-equivalent partial graphs after
    querying t_edges edge variables for k-CLIQUE on N vertices.

    Two partial graphs P₁, P₂ (each assigning t_edges to {0,1})
    are equivalent iff:
      for ALL completions G: CLIQUE(P₁∪G) = CLIQUE(P₂∪G)

    Returns: number of equivalence classes.

    Method: enumerate all 2^t partial assignments, group by equivalence.
    (Feasible only for small t.)
    """
    n = N * (N-1) // 2
    edge_list = []
    edge_idx = {}
    idx = 0
    for i in range(N):
        for j in range(i+1, N):
            edge_list.append((i, j))
            edge_idx[(i,j)] = idx
            edge_idx[(j,i)] = idx
            idx += 1

    # Choose which t edges to query (use first t for simplicity)
    if t_edges > n:
        t_edges = n
    query_edges = list(range(t_edges))
    remaining_edges = list(range(t_edges, n))
    num_remaining = len(remaining_edges)

    if num_remaining > 18:  # too many completions
        return -1  # infeasible

    # For each partial assignment of query_edges:
    # Compute the "signature" = truth table of CLIQUE over all completions
    equivalence_classes = set()

    for partial_bits in range(2**t_edges):
        # This partial assignment: edge query_edges[j] = (partial_bits >> j) & 1
        partial = {}
        for j in range(t_edges):
            partial[query_edges[j]] = (partial_bits >> j) & 1

        # Signature: for each completion, does k-CLIQUE hold?
        sig = []
        for comp_bits in range(2**num_remaining):
            # Full assignment
            full = [0] * n
            for j in range(t_edges):
                full[query_edges[j]] = partial[query_edges[j]]
            for j in range(num_remaining):
                full[remaining_edges[j]] = (comp_bits >> j) & 1

            # Check k-CLIQUE
            has_clique = False
            for combo in itertools.combinations(range(N), k):
                clique = True
                for a in range(len(combo)):
                    for b in range(a+1, len(combo)):
                        if not full[edge_idx[(combo[a], combo[b])]]:
                            clique = False
                            break
                    if not clique:
                        break
                if clique:
                    has_clique = True
                    break
            sig.append(1 if has_clique else 0)

        equivalence_classes.add(tuple(sig))

    return len(equivalence_classes)


def theoretical_lower_bound(N, k, t):
    """Theoretical lower bound on distinct partial graphs.

    After querying t edges for k-CLIQUE:
    At minimum, different "k-clique indicators" give different partials.

    With t = C(k,2) edges queried: we can identify which k-clique
    (if any) is formed by those edges. There are C(N,k) possible
    k-cliques, each giving a different partial configuration.

    But: some partials are equivalent despite being different,
    if no completion can distinguish them.

    LOWER BOUND: The number of distinct "single-clique certificates"
    that use exactly the queried edges.
    """
    if t < k * (k-1) // 2:
        # Can't form a complete k-clique with t edges
        # Lower bound: at least 2 (all present vs all absent)
        return 2

    # With t ≥ C(k,2): can certify individual k-cliques
    # Number of k-vertex subsets whose edges fit in t queried edges
    # This depends on which edges are queried.
    # Lower bound: C(N,k) if t ≥ C(k,2) and edges span all vertices
    ck2 = k * (k-1) // 2
    return min(2**t, math.comb(N, k) + 1)


def main():
    print("=" * 70)
    print("  NON-EQUIVALENT PARTIAL GRAPHS: Direct count")
    print("  This IS the number of distinct subtrees")
    print("=" * 70)

    print(f"\n  {'N':>3} {'k':>3} {'n':>5} {'t':>4} {'equiv_classes':>14} "
          f"{'2^t':>10} {'C(N,k)':>10} {'log_n(eq)':>10}")
    print("  " + "-" * 65)

    results_by_k = defaultdict(list)

    for N in range(4, 8):
        n = N*(N-1)//2

        for k in range(2, min(N+1, 6)):
            ck2 = k*(k-1)//2

            # Test with different t values
            for t in [min(ck2, n), min(ck2+2, n), min(n, 10)]:
                if t > n:
                    t = n
                remaining = n - t
                if remaining > 16:  # feasibility check
                    continue
                if 2**t > 100000:
                    continue

                eq = count_nonequivalent_partial_graphs(N, k, t)
                if eq < 0:
                    continue

                log_eq = math.log(max(1,eq)) / math.log(max(2,n)) if n > 1 else 0

                print(f"  {N:3d} {k:3d} {n:5d} {t:4d} {eq:>14d} "
                      f"{2**t:>10d} {math.comb(N,k):>10d} {log_eq:>10.2f}")

                results_by_k[k].append((N, n, t, eq))

            sys.stdout.flush()

    # Analyze scaling
    print(f"\n\n{'='*70}")
    print("  SCALING ANALYSIS: equiv_classes vs n for each k")
    print(f"{'='*70}")

    for k in sorted(results_by_k.keys()):
        data = results_by_k[k]
        if len(data) < 2:
            continue

        # Use data where t = C(k,2) (or closest)
        ck2 = k*(k-1)//2
        filtered = [(N, n, eq) for N, n, t, eq in data if t == min(ck2, N*(N-1)//2)]

        if len(filtered) < 2:
            filtered = [(N, n, eq) for N, n, t, eq in data]

        if len(filtered) < 2:
            continue

        ns = [d[1] for d in filtered]
        eqs = [d[2] for d in filtered]
        log_ns = [math.log(n) for n in ns]
        log_eqs = [math.log(max(1,e)) for e in eqs]

        m = len(log_ns)
        sx = sum(log_ns); sy = sum(log_eqs)
        sxy = sum(x*y for x,y in zip(log_ns, log_eqs))
        sxx = sum(x*x for x in log_ns)
        denom = m*sxx - sx*sx

        if denom != 0:
            alpha = (m*sxy - sx*sy) / denom
            print(f"  k={k}: α = {alpha:.2f} (equiv_classes ~ n^α)")

    # THE KEY: does α grow with k?
    print(f"\n{'='*70}")
    print("  FORMAL ARGUMENT")
    print(f"{'='*70}")
    print("""
    THEOREM (to prove):
      For k-CLIQUE on N vertices with n = C(N,2) edges,
      after querying t = C(k,2) edges, the number of
      non-equivalent partial graphs is at least C(N,k).

    PROOF IDEA:
      For each k-vertex subset S ⊆ [N], define P_S as the
      partial graph with ALL C(k,2) edges within S set to "present."

      For S₁ ≠ S₂: P_{S₁} ≢ P_{S₂} because there exists a
      completion G where CLIQUE(P_{S₁} ∪ G) ≠ CLIQUE(P_{S₂} ∪ G).

      Specifically: let G have ALL remaining edges ABSENT.
      Then:
        CLIQUE(P_{S₁} ∪ G) = 1 (S₁ forms a k-clique)
        CLIQUE(P_{S₂} ∪ G) = 1 (S₂ ALSO forms a k-clique!)

      PROBLEM: Both are 1! The completion doesn't distinguish them.

      FIX: Use partial graphs where SOME edges are present and
      SOME are absent.

      For S₁ = {1,...,k}: set all edges within S₁ to PRESENT
      EXCEPT edge (1,2): set to ABSENT.

      For S₂ = {1,...,k-1,k+1}: set all edges within S₂ to PRESENT
      EXCEPT edge (1,2): set to ABSENT.

      Now with completion "all remaining absent":
        P_{S₁} ∪ G: S₁ is NOT a k-clique (edge (1,2) missing).
           No other k-clique (all other edges absent). → 0
        P_{S₂} ∪ G: S₂ has all edges EXCEPT (1,2).
           But (1,2) might not be in S₂ if 2 ∉ S₂.

      This gets complicated. Let me try a cleaner approach.

    CLEANER PROOF:
      After querying ALL n edges (t = n): the number of
      non-equivalent partial graphs = number of distinct truth
      table values = 2 (just {0, 1}).

      After querying C(k,2) edges at optimal positions:
      At least C(N,k) non-equivalent partials.

      Because: for each k-set S, the partial that has all C(k,2)
      edges of S present and is "unknown" elsewhere is DIFFERENT
      from the partial that has all edges of S' present.

      They differ because: the completion "all absent" gives:
        P_S ∪ ∅: S is a k-clique → 1
        But S' is ALSO a k-clique → 1...

      THE ISSUE: different positive certificates give the SAME
      answer (both 1). We need NEGATIVE certificates too.

      SOLUTION: Consider partial graphs where S is an ALMOST-clique
      (all edges present except one). With all remaining edges absent:
        CLIQUE = 0 (S is not quite a clique, nothing else is).

      For S with missing edge e: P_{S,e} ∪ "all absent" = 0.
      For S with missing edge e': P_{S,e'} ∪ "all absent" = 0.

      But P_{S,e} and P_{S,e'} ARE equivalent (both give 0 with all
      remaining absent). They might differ on OTHER completions though.

      Completion with edge e present: P_{S,e} ∪ {e: present} = 1!
      Completion with edge e present: P_{S,e'} ∪ {e: present} = 0
      (S still missing e', and e doesn't help S with missing e').

      Wait — P_{S,e} has all edges of S except e. Adding e back → S
      is now a complete k-clique → CLIQUE = 1. ✓

      P_{S,e'} has all edges of S except e'. Adding e doesn't complete
      S (still missing e'). So CLIQUE depends on whether some OTHER
      k-set forms a clique. With all other edges absent: only S-related
      edges. If e is not in S: adding e doesn't create a new k-clique.

      Actually, e IS in S (it's the missing edge). So adding e to P_{S,e}
      completes S → CLIQUE = 1.

      Adding e to P_{S,e'}: e is an edge of S that IS present in P_{S,e'}.
      Wait, I need to be more careful.

      P_{S,e} = all edges of S present EXCEPT e = absent.
      P_{S,e'} = all edges of S present EXCEPT e' = absent.

      e ≠ e' are both edges within S.

      Completion: set edge e = present, all other remaining = absent.

      For P_{S,e} ∪ this completion:
        Edge e is now present. All edges of S are present → S is k-clique → 1.

      For P_{S,e'} ∪ this completion:
        Edge e was already present in P_{S,e'}. Edge e' is still absent.
        S has all edges except e' → NOT a k-clique.
        No other k-set: all edges outside S are absent → 0.

      So: CLIQUE(P_{S,e} ∪ comp) = 1 ≠ 0 = CLIQUE(P_{S,e'} ∪ comp).

      Therefore: P_{S,e} ≢ P_{S,e'} for e ≠ e'. ✓

    NUMBER OF SUCH CONFIGURATIONS:
      For each k-set S: C(k,2) choices of missing edge e.
      Total: C(N,k) × C(k,2) configurations.
      But different S might share edges in their query sets.

      With t = C(k,2) queried edges all within ONE k-set S:
        C(k,2) non-equivalent partials (one per missing edge).

      With t = 2 × C(k,2) queried edges spanning TWO k-sets:
        At least C(k,2)² non-equivalent partials.

      With t edges spanning m k-sets:
        At least C(k,2)^m non-equivalent partials.

      For t = n (all edges): m = C(N,k) k-sets → C(k,2)^{C(N,k)} equivalences.
      But the actual count is just 2 (function values 0 and 1).

      The MAXIMUM distinct partials occurs at intermediate t.
      At t ≈ n/2: the number should be maximized.
    """)


if __name__ == "__main__":
    main()
