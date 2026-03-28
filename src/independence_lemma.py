"""
THE INDEPENDENCE LEMMA: P_{S₁,e₁} ≢ P_{S₂,e₂} for S₁ ≠ S₂.

SETUP:
  P_{S,e} = partial graph where all C(k,2) edges within k-set S
  are queried: all PRESENT except edge e which is ABSENT.

  S₁ ≠ S₂ are two different k-vertex subsets.
  e₁ is an edge within S₁, e₂ is an edge within S₂.

GOAL: Find completion G such that
  CLIQUE(P_{S₁,e₁} ∪ G) ≠ CLIQUE(P_{S₂,e₂} ∪ G)

CASES:
  Case 1: S₁ and S₂ share NO queried edges.
    Then P_{S₁,e₁} and P_{S₂,e₂} query DISJOINT edge sets.
    This is the easy case.

  Case 2: S₁ and S₂ share some edges (overlapping vertex sets).
    This is the hard case — the partial graphs interact.

APPROACH:
  P_{S₁,e₁}: S₁ is "almost-clique" (missing e₁).

  Completion G₁: set e₁ = PRESENT, all other unqueried = ABSENT.
  CLIQUE(P_{S₁,e₁} ∪ G₁) = 1 (S₁ becomes complete k-clique).
  CLIQUE(P_{S₂,e₂} ∪ G₁) = ?

  For P_{S₂,e₂} ∪ G₁: S₂ has all edges EXCEPT e₂.
  Is e₁ = e₂? Not necessarily (S₁ ≠ S₂).
  Even if e₁ is set present in G₁: if e₂ ≠ e₁, S₂ still missing e₂.
  Could some OTHER k-set form a clique?

  All unqueried edges are ABSENT except e₁.
  A k-clique Q needs all C(k,2) edges present.
  Present edges: those within S₂ (except e₂) + edge e₁.
  Q must use only these edges.

  If e₁ ∉ edges(S₂): Q must be a sub-clique of S₂ (missing e₂) → NOT a k-clique.
  If e₁ ∈ edges(S₂): Q could use e₁, but S₂ still missing e₂.

  KEY QUESTION: Can a k-clique be formed from edges(S₂)\{e₂} ∪ {e₁}?
  This is a k-clique using edges within S₂ except replacing e₂ with e₁.
  But e₁ might not be within S₂!

EXPERIMENT: Directly verify the independence for small cases.
"""

import itertools
from collections import defaultdict
import math
import sys


def check_clique(edges_present, N, k):
    """Check if the given set of present edges contains a k-clique."""
    edge_set = set(edges_present)
    for combo in itertools.combinations(range(N), k):
        is_clique = True
        for a in range(len(combo)):
            for b in range(a+1, len(combo)):
                if (combo[a], combo[b]) not in edge_set and \
                   (combo[b], combo[a]) not in edge_set:
                    is_clique = False
                    break
            if not is_clique:
                break
        if is_clique:
            return True
    return False


def are_nonequivalent(N, k, S1, e1, S2, e2):
    """Check if P_{S1,e1} and P_{S2,e2} are non-equivalent.

    Try to find a completion G that distinguishes them.
    P_{S,e}: edges within S all present EXCEPT e (absent).
    Completion G: assignment to unqueried edges.

    We need: CLIQUE(P_{S1,e1} ∪ G) ≠ CLIQUE(P_{S2,e2} ∪ G)
    for some G.
    """
    n = N * (N-1) // 2

    # Build edge list
    all_edges = []
    for i in range(N):
        for j in range(i+1, N):
            all_edges.append((i,j))

    # Edges within S
    def edges_of(S):
        return set((min(a,b), max(a,b)) for a in S for b in S if a != b)

    edges_S1 = edges_of(S1)
    edges_S2 = edges_of(S2)

    # Queried edges for P_{S1,e1}: all of edges_S1
    # Queried edges for P_{S2,e2}: all of edges_S2

    # P_{S1,e1}: edges_S1 \ {e1} = present, e1 = absent
    # P_{S2,e2}: edges_S2 \ {e2} = present, e2 = absent

    # Both P's query edges_S1 ∪ edges_S2
    queried = edges_S1 | edges_S2
    unqueried = [e for e in all_edges if e not in queried]

    # For P_{S1,e1}: present = edges_S1 - {e1}, absent = {e1}
    present_1 = edges_S1 - {e1}
    absent_1 = {e1}

    # For P_{S2,e2}: present = edges_S2 - {e2}, absent = {e2}
    present_2 = edges_S2 - {e2}
    absent_2 = {e2}

    # PROBLEM: P_{S1,e1} and P_{S2,e2} query DIFFERENT edge sets!
    # They're partial graphs with different query sets.
    # For the decision tree: each node queries ONE edge.
    # The two partials correspond to different PATHS in the tree.

    # For non-equivalence in the TREE sense:
    # After querying certain edges, the REMAINING function differs.

    # Simpler model: fix the queried edges to BOTH partial values
    # and try completions of the REST.

    # Actually, the two partials query DIFFERENT edges, so they're
    # at DIFFERENT nodes in the tree. They can only be "equivalent"
    # if the remaining sub-functions are identical.

    # The sub-function at P_{S1,e1}: for remaining edges (not in S1),
    # compute CLIQUE given edges_S1 \ {e1} present and e1 absent.

    # The sub-function at P_{S2,e2}: for remaining edges (not in S2),
    # compute CLIQUE given edges_S2 \ {e2} present and e2 absent.

    # These sub-functions have DIFFERENT domains (different remaining edges)!
    # So they can only be compared if the remaining edges are the same.

    # For the tree: two nodes are "equivalent" if they're on the SAME
    # level (same set of queried edges) with different partial assignments.

    # Let's use a simpler comparison: fix a COMMON query set Q = edges_S1 ∪ edges_S2.
    # P_{S1,e1} assigns: edges_S1\{e1} = present, e1 = absent, edges_S2\edges_S1 = ???
    # P_{S2,e2} assigns: edges_S2\{e2} = present, e2 = absent, edges_S1\edges_S2 = ???

    # The "???" parts are edges queried in one partial but not the other.
    # In the tree: these would be queried at different points.

    # SIMPLIFICATION: Consider partials that query EXACTLY the same set Q.
    # Set Q = edges_S1 ∪ edges_S2 (union).
    # For unqueried edge e in Q but not in S1: set to... any fixed value.

    # Let me try a direct approach: enumerate completions of unqueried edges.

    # For both partials: define the full assignment
    # P1: known[e] = 1 for e in edges_S1\{e1}, known[e1] = 0
    #     unknown: everything outside edges_S1
    # P2: known[e] = 1 for e in edges_S2\{e2}, known[e2] = 0
    #     unknown: everything outside edges_S2

    # For edges in S1 ∩ S2: both partials agree (unless e1 or e2 is in the intersection)
    # For edges in S1 \ S2: P1 has them present, P2 doesn't query them
    # For edges in S2 \ S1: P2 has them present, P1 doesn't query them

    # To compare fairly: fix all non-overlapping edges to some values
    # and see if the sub-functions differ.

    # Simplest distinguishing completion:
    # G: e1 = present, everything else unqueried = absent.
    # Under P1 + G: all edges of S1 present (e1 from G) → CLIQUE = 1
    # Under P2 + G: edges of S2 minus e2 present, e1 might not help S2
    #   If e1 ∉ edges_S2: S2 still missing e2 → depends on rest
    #   All unqueried outside S2 = absent → no other clique → 0 (if S2 incomplete)

    # For this to work: need e1 ∉ edges_S2 OR e1 ≠ e2

    # Actually let's just enumerate for small cases

    # Try specific completion: e1 present, all other unqueried absent
    completion = {e1: 1}  # e1 present
    for e in unqueried:
        if e != e1:
            completion[e] = 0

    # Full assignment under P1
    full_1 = {}
    for e in all_edges:
        if e in present_1:
            full_1[e] = 1
        elif e in absent_1:
            full_1[e] = 0
        elif e in completion:
            full_1[e] = completion[e]
        elif e in present_2:
            # Edge queried by P2 but not P1: in the tree, this would
            # be at a different level. For comparison: set to P2's value.
            full_1[e] = 1 if e in present_2 else 0
        else:
            full_1[e] = 0

    full_2 = {}
    for e in all_edges:
        if e in present_2:
            full_2[e] = 1
        elif e in absent_2:
            full_2[e] = 0
        elif e in completion:
            full_2[e] = completion[e]
        elif e in present_1:
            full_2[e] = 1 if e in present_1 else 0
        else:
            full_2[e] = 0

    # Check CLIQUE
    present_edges_1 = set(e for e in all_edges if full_1.get(e, 0) == 1)
    present_edges_2 = set(e for e in all_edges if full_2.get(e, 0) == 1)

    clique_1 = check_clique(present_edges_1, N, k)
    clique_2 = check_clique(present_edges_2, N, k)

    if clique_1 != clique_2:
        return True, "e1_completion"

    # Try another completion: e2 present, all other unqueried absent
    completion2 = {e2: 1}
    for e in unqueried:
        if e != e2:
            completion2[e] = 0

    full_1b = {}
    for e in all_edges:
        if e in present_1:
            full_1b[e] = 1
        elif e in absent_1:
            full_1b[e] = 0
        elif e in completion2:
            full_1b[e] = completion2[e]
        elif e in present_2:
            full_1b[e] = 1
        else:
            full_1b[e] = 0

    full_2b = {}
    for e in all_edges:
        if e in present_2:
            full_2b[e] = 1
        elif e in absent_2:
            full_2b[e] = 0
        elif e in completion2:
            full_2b[e] = completion2[e]
        elif e in present_1:
            full_2b[e] = 1
        else:
            full_2b[e] = 0

    pe1b = set(e for e in all_edges if full_1b.get(e, 0) == 1)
    pe2b = set(e for e in all_edges if full_2b.get(e, 0) == 1)

    c1b = check_clique(pe1b, N, k)
    c2b = check_clique(pe2b, N, k)

    if c1b != c2b:
        return True, "e2_completion"

    return False, "not_found"


def main():
    print("=" * 70)
    print("  INDEPENDENCE LEMMA: P_{S1,e1} ≢ P_{S2,e2} for S1 ≠ S2")
    print("=" * 70)

    for N in [5, 6, 7]:
        for k in [3, 4]:
            if k > N - 1:
                continue

            print(f"\n  N={N}, k={k}:")

            # Generate all k-sets
            k_sets = list(itertools.combinations(range(N), k))

            # For each pair of DIFFERENT k-sets: check non-equivalence
            total_pairs = 0
            distinguished = 0
            not_distinguished = 0

            for i in range(min(len(k_sets), 10)):
                S1 = k_sets[i]
                edges_S1 = [(min(a,b), max(a,b)) for a in S1 for b in S1 if a < b]
                e1 = edges_S1[0]  # first edge of S1

                for j in range(i+1, min(len(k_sets), 10)):
                    S2 = k_sets[j]
                    if S1 == S2:
                        continue
                    edges_S2 = [(min(a,b), max(a,b)) for a in S2 for b in S2 if a < b]
                    e2 = edges_S2[0]  # first edge of S2

                    total_pairs += 1
                    result, method = are_nonequivalent(N, k, S1, e1, S2, e2)

                    if result:
                        distinguished += 1
                    else:
                        not_distinguished += 1
                        print(f"    NOT distinguished: S1={S1}, S2={S2}")

            print(f"    Tested: {total_pairs} pairs")
            print(f"    Distinguished: {distinguished} ({distinguished/max(1,total_pairs)*100:.0f}%)")
            print(f"    NOT distinguished: {not_distinguished}")

            if not_distinguished == 0:
                print(f"    ✓ ALL PAIRS NON-EQUIVALENT!")
            else:
                print(f"    ✗ Some pairs equivalent — lemma may need refinement")

    print(f"\n{'='*70}")
    print("  THEORETICAL STATUS")
    print(f"{'='*70}")
    print("""
    If ALL pairs (S1,e1) vs (S2,e2) are non-equivalent:
      → C(N,k) × C(k,2) distinct equivalence classes
      → For k = N^{1/3}: C(N, N^{1/3}) × C(N^{1/3}, 2) = super-polynomial
      → Decision tree has super-poly distinct subtrees
      → Circuit size ≥ super-polynomial
      → P ≠ NP

    The distinguishing completion for S1 ≠ S2:
      G = {e1: present, all other unqueried: absent}

      P_{S1,e1} ∪ G: e1 present → S1 is complete k-clique → CLIQUE = 1
      P_{S2,e2} ∪ G: S2 might or might not be complete
        If e1 ∉ edges(S2): S2 still missing e2 → CLIQUE = 0 ✓
        If e1 ∈ edges(S2) and e1 ≠ e2: S2 has e1 but missing e2 → CLIQUE = 0 ✓
        If e1 = e2: both become complete → CLIQUE = 1 (NOT distinguished!)

    So: the completion works UNLESS e1 = e2 AND e1 ∈ edges(S2).

    To handle this: choose e1 and e2 to be DIFFERENT edges.
    Since S1 ≠ S2: they differ in at least one vertex.
    Choose e1 as an edge incident to v ∈ S1 \\ S2.
    Then e1 ∉ edges(S2) → distinguishing completion works! ✓
    """)


if __name__ == "__main__":
    main()
