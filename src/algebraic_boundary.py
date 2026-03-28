"""
Algebraic Boundary Structure Analysis.

The natural proofs barrier (Razborov-Rudich 1997) says:
  Any proof technique that uses only "largeness" (property true for
  many functions) cannot prove circuit lower bounds if OWF exist.

To bypass this barrier, we need to use SPECIFIC algebraic structure
of the function, not just statistical properties.

For MONO-3SAT with clauses C₁,...,C_m:
  f(x) = AND_j (OR_{i∈C_j} x_i)

The boundary ∂f has structure determined by the HYPERGRAPH of clauses.
This is specific to f, not a generic property.

KEY IDEA: The boundary structure is determined by "minimal corrections" —
for each unsatisfying assignment x_b, the set of variables that can be
flipped to satisfy it forms a TRANSVERSAL of unsatisfied clauses.

The structure of these transversals is governed by the clause hypergraph,
which is a SPECIFIC algebraic object.

If we can show that the transversal structure is inherently complex
(requires many gates to compute), we get a non-natural lower bound.
"""

import itertools
from collections import defaultdict
import random
import math
import sys


def evaluate_mono3sat(assignment, clauses):
    for clause in clauses:
        if not any(assignment[v] for v in clause):
            return False
    return True


def compute_transversal_structure(n, clauses):
    """For each non-solution x_b, compute:
    1. Which clauses are unsatisfied
    2. The "correction set" = variables that can be flipped to satisfy

    The correction set forms a HITTING SET of the unsatisfied clauses
    (must hit at least one variable in each unsatisfied clause).

    The MINIMUM correction set = minimum hitting set = NP-hard in general.
    But for boundary points (distance 1 from solution), it's size 1.
    """
    solutions = set()
    non_solutions = []

    for bits in range(2**n):
        assignment = tuple((bits >> i) & 1 for i in range(n))
        if evaluate_mono3sat(assignment, clauses):
            solutions.add(assignment)
        else:
            non_solutions.append(assignment)

    boundary_data = []

    for x_b in non_solutions:
        # Find unsatisfied clauses
        unsat = []
        for ci, clause in enumerate(clauses):
            if not any(x_b[v] for v in clause):
                unsat.append(ci)

        # Find correction variables (bits that when flipped fix ALL unsat clauses)
        corrections = []
        for j in range(n):
            if x_b[j] == 0:  # can only flip 0→1 for monotone
                flipped = list(x_b)
                flipped[j] = 1
                if tuple(flipped) in solutions:
                    # Variable j is a correction: flipping it satisfies everything
                    # This means j appears in ALL unsatisfied clauses
                    corrections.append(j)

        if corrections:
            boundary_data.append({
                'x_b': x_b,
                'unsat_clauses': unsat,
                'corrections': corrections,
                'num_unsat': len(unsat),
                'weight': sum(x_b),
            })

    return boundary_data, solutions


def analyze_transversal_hypergraph(n, clauses):
    """Analyze the hypergraph of corrections.

    Build a bipartite graph: boundary points × variables
    Edge (x_b, j) exists if j is a correction for x_b.

    The structure of this bipartite graph determines:
    - How many gates are needed to "route" corrections
    - Whether NOT gates can help
    """
    boundary_data, solutions = compute_transversal_structure(n, clauses)

    if not boundary_data:
        return None

    print(f"\n{'='*70}")
    print(f"  TRANSVERSAL STRUCTURE ANALYSIS (n={n})")
    print(f"  |∂f| = {len(boundary_data)} boundary points")
    print(f"{'='*70}")

    # 1. Correction degree distribution
    # For each variable j: how many boundary points does it correct?
    var_degree = defaultdict(int)
    for bd in boundary_data:
        for j in bd['corrections']:
            var_degree[j] += 1

    print(f"\n  Variable correction degrees:")
    for j in range(n):
        print(f"    x_{j}: corrects {var_degree[j]} boundary points "
              f"({var_degree[j]/len(boundary_data)*100:.1f}%)")

    # 2. Boundary point correction degree
    # How many variables correct each boundary point?
    bp_degrees = [len(bd['corrections']) for bd in boundary_data]
    avg_deg = sum(bp_degrees) / len(bp_degrees)
    print(f"\n  Boundary point correction degrees:")
    print(f"    Average: {avg_deg:.2f}, Min: {min(bp_degrees)}, Max: {max(bp_degrees)}")

    # Distribution
    deg_dist = defaultdict(int)
    for d in bp_degrees:
        deg_dist[d] += 1
    for d in sorted(deg_dist.keys()):
        print(f"    Degree {d}: {deg_dist[d]} points")

    # 3. Co-occurrence analysis
    # For each pair of variables (i,j): how often do they BOTH correct the same boundary point?
    cooccur = defaultdict(int)
    for bd in boundary_data:
        for i in range(len(bd['corrections'])):
            for j in range(i+1, len(bd['corrections'])):
                pair = (bd['corrections'][i], bd['corrections'][j])
                cooccur[pair] += 1

    if cooccur:
        print(f"\n  Variable co-occurrence (both correct same boundary point):")
        for (i, j), count in sorted(cooccur.items(), key=lambda x: -x[1])[:10]:
            print(f"    (x_{i}, x_{j}): {count} times")

    # 4. Clause-induced structure
    # For each boundary point, the number of unsatisfied clauses
    unsat_dist = defaultdict(int)
    for bd in boundary_data:
        unsat_dist[bd['num_unsat']] += 1

    print(f"\n  Unsatisfied clause distribution:")
    for k in sorted(unsat_dist.keys()):
        print(f"    {k} unsat clauses: {unsat_dist[k]} boundary points")

    # 5. KEY METRIC: Independence number of the correction bipartite graph
    # This relates to circuit size: if corrections are "spread out",
    # more gates are needed
    # Compute: for each variable j, the set of boundary points it corrects
    var_sets = {}
    for j in range(n):
        var_sets[j] = set()
    for i, bd in enumerate(boundary_data):
        for j in bd['corrections']:
            var_sets[j].add(i)

    # Pairwise overlap between variable correction sets
    print(f"\n  Variable correction set overlaps:")
    max_union = 0
    best_cover = []

    # Greedy set cover: how many variables needed to cover all boundary points?
    uncovered = set(range(len(boundary_data)))
    cover = []
    while uncovered:
        best_var = max(range(n), key=lambda j: len(var_sets[j] & uncovered))
        covered = var_sets[best_var] & uncovered
        if not covered:
            break
        uncovered -= covered
        cover.append((best_var, len(covered)))

    print(f"    Greedy set cover: {len(cover)} variables needed")
    for var, count in cover:
        print(f"      x_{var}: covers {count} new boundary points")

    return {
        'boundary_size': len(boundary_data),
        'avg_correction_degree': avg_deg,
        'set_cover_size': len(cover),
        'var_degrees': dict(var_degree),
    }


def correction_complexity_analysis(n, clauses):
    """Analyze the computational complexity of the correction function.

    The correction function: given x_b ∈ ∂f, output the correction variable j.
    This is the SEARCH version of MONO-3SAT near the boundary.

    For the circuit to compute f(x):
    - On boundary non-solutions, it must output 0
    - On boundary solutions, it must output 1
    - The "hardness" comes from distinguishing x_b from x_b⁺

    The correction function g(x_b) = j such that x_b⊕e_j ∈ solutions
    contains all the "information" about the boundary.

    If g has high circuit complexity → f has high circuit complexity.

    KEY INSIGHT: g maps from a set of size |∂f| to [n].
    By pigeonhole, at least |∂f|/n boundary points map to the same j.
    A circuit computing g must distinguish all of these.

    For monotone circuits: g is monotone (higher weight → fewer corrections)
    and the anti-chain argument works.

    For general circuits with NOT: g can use inversions to "compress"
    the mapping. But HOW MUCH compression is possible?
    """
    boundary_data, solutions = compute_transversal_structure(n, clauses)

    if not boundary_data:
        return

    print(f"\n{'='*70}")
    print(f"  CORRECTION FUNCTION COMPLEXITY (n={n})")
    print(f"{'='*70}")

    # Group boundary points by their correction variable(s)
    by_correction = defaultdict(list)
    for bd in boundary_data:
        for j in bd['corrections']:
            by_correction[j].append(bd['x_b'])

    # For each correction group: how "diverse" are the boundary points?
    print(f"\n  Correction groups:")
    for j in sorted(by_correction.keys()):
        group = by_correction[j]
        if len(group) < 2:
            continue

        # Pairwise Hamming distances within group
        if len(group) <= 50:
            dists = []
            for i in range(len(group)):
                for k in range(i+1, len(group)):
                    d = sum(a != b for a, b in zip(group[i], group[k]))
                    dists.append(d)
            avg_dist = sum(dists) / len(dists) if dists else 0
        else:
            # Sample
            dists = []
            for _ in range(100):
                i, k = random.sample(range(len(group)), 2)
                d = sum(a != b for a, b in zip(group[i], group[k]))
                dists.append(d)
            avg_dist = sum(dists) / len(dists) if dists else 0

        # Weight distribution within group
        weights = [sum(x) for x in group]
        avg_w = sum(weights) / len(weights)

        print(f"    Correction x_{j}: {len(group)} points, "
              f"avg Hamming dist={avg_dist:.2f}, avg weight={avg_w:.2f}")

    # Multi-correction points
    multi = [bd for bd in boundary_data if len(bd['corrections']) > 1]
    print(f"\n  Multi-correction points: {len(multi)}/{len(boundary_data)} "
          f"({len(multi)/len(boundary_data)*100:.1f}%)")

    if multi:
        # These are "easy" points — multiple variables can fix them
        # The "hard" points are those with exactly one correction
        single = [bd for bd in boundary_data if len(bd['corrections']) == 1]
        print(f"  Single-correction (hardest) points: {len(single)} "
              f"({len(single)/len(boundary_data)*100:.1f}%)")

        # Key question: do single-correction points form a large anti-chain?
        if single:
            single_points = [bd['x_b'] for bd in single]
            # Check anti-chain property (component-wise incomparable)
            if len(single_points) <= 200:
                antichain = []
                for x in single_points:
                    compatible = True
                    for a in antichain:
                        if all(xi <= ai for xi, ai in zip(x, a)) or \
                           all(ai <= xi for ai, xi in zip(x, a)):
                            compatible = False
                            break
                    if compatible:
                        antichain.append(x)

                print(f"  Anti-chain among single-correction points: {len(antichain)}")
                if len(antichain) > 0:
                    base = len(antichain) ** (1.0/n) if len(antichain) > 1 else 0
                    print(f"  Anti-chain base: {base:.4f}")


def scaling_analysis():
    """Scale the transversal analysis and look for growth patterns."""
    print("=" * 80)
    print("  TRANSVERSAL STRUCTURE SCALING")
    print("=" * 80)

    from mono3sat import generate_all_mono3sat_clauses

    for n in range(5, 16):
        if 2**n > 200000:
            break

        all_clauses = generate_all_mono3sat_clauses(n)
        trials = max(20, 200 // n)
        if n >= 12:
            trials = 10

        best_result = None
        best_boundary = 0

        for _ in range(trials):
            k = random.randint(max(1, n//2), min(len(all_clauses), 4*n))
            clauses = random.sample(all_clauses, k)

            result = analyze_transversal_hypergraph(n, clauses)
            if result and result['boundary_size'] > best_boundary:
                best_boundary = result['boundary_size']
                best_result = result

        if best_result:
            base = best_boundary ** (1.0/n) if best_boundary > 1 else 0
            print(f"\n>>> n={n}: |∂f|={best_boundary}, base={base:.4f}, "
                  f"set_cover={best_result['set_cover_size']}, "
                  f"avg_deg={best_result['avg_correction_degree']:.2f}")


if __name__ == "__main__":
    random.seed(42)

    # Phase 1: Detailed analysis for small n
    from mono3sat import generate_all_mono3sat_clauses

    for n in [6, 8, 10]:
        if 2**n > 100000:
            break

        all_clauses = generate_all_mono3sat_clauses(n)

        # Find instance with largest boundary
        best_boundary = []
        best_clauses = None

        for _ in range(100):
            k = random.randint(max(1, n//2), min(len(all_clauses), 4*n))
            clauses = random.sample(all_clauses, k)
            data, sols = compute_transversal_structure(n, clauses)
            if len(data) > len(best_boundary):
                best_boundary = data
                best_clauses = clauses[:]

        if best_clauses:
            analyze_transversal_hypergraph(n, best_clauses)
            correction_complexity_analysis(n, best_clauses)

    # Phase 2: Scaling
    print(f"\n\n")
    scaling_analysis()
