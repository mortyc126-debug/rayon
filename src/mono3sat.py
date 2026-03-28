"""
P vs NP Research: Computational Framework for MONO-3SAT Solution Boundaries

Core question: Is |∂f| ~ 1.795^n tight, or does it grow faster?
If |∂f| ≥ 2^n / poly(n), then Z₂-orbit argument covers ALL circuits → P ≠ NP.

Objects:
- MONO-3SAT: SAT where all literals are positive (no negation)
- G(φ): graph where nodes = partial assignments, edges = Hamming distance 1
- ∂f: solution boundary = {(x_b, x_b⁺) : x_b ∉ SAT, x_b⁺ ∈ SAT, Hamming(x_b, x_b⁺)=1}
  where x_b⁺ = x_b with one bit flipped 0→1 (monotone: flipping 0→1 can only help)
"""

import itertools
from collections import defaultdict
import random
import math
import sys


def generate_all_mono3sat_clauses(n):
    """Generate all possible monotone 3-SAT clauses over n variables."""
    clauses = []
    for combo in itertools.combinations(range(n), 3):
        clauses.append(combo)
    return clauses


def evaluate_mono3sat(assignment, clauses):
    """Check if assignment satisfies all monotone 3-SAT clauses.
    A clause (i,j,k) is satisfied if x_i OR x_j OR x_k = 1."""
    for clause in clauses:
        if not any(assignment[v] for v in clause):
            return False
    return True


def compute_solution_set(n, clauses):
    """Compute the full set of satisfying assignments."""
    solutions = set()
    for bits in range(2**n):
        assignment = tuple((bits >> i) & 1 for i in range(n))
        if evaluate_mono3sat(assignment, clauses):
            solutions.add(assignment)
    return solutions


def compute_boundary(n, clauses):
    """Compute the solution boundary ∂f.

    ∂f = {(x_b, bit_j) : x_b ∉ SAT, x_b with bit j flipped 0→1 ∈ SAT}

    For monotone functions, only 0→1 flips can cross the boundary
    (flipping 1→0 can only break clauses, never fix them).

    Returns list of (x_b, j, x_b_plus) triples.
    """
    solutions = compute_solution_set(n, clauses)
    boundary = []

    for bits in range(2**n):
        assignment = tuple((bits >> i) & 1 for i in range(n))
        if assignment in solutions:
            continue  # x_b must be non-solution

        for j in range(n):
            if assignment[j] == 0:  # can only flip 0→1 for monotone
                flipped = list(assignment)
                flipped[j] = 1
                flipped = tuple(flipped)
                if flipped in solutions:
                    boundary.append((assignment, j, flipped))

    return boundary, solutions


def generate_random_mono3sat(n, clause_ratio):
    """Generate random monotone 3-SAT instance with m = clause_ratio * n clauses."""
    m = int(clause_ratio * n)
    all_clauses = generate_all_mono3sat_clauses(n)
    if m > len(all_clauses):
        m = len(all_clauses)
    return random.sample(all_clauses, m)


def generate_critical_mono3sat(n):
    """Generate MONO-3SAT near the satisfiability threshold.

    For monotone 3-SAT, the threshold is around α_c ≈ 1.0 * C(n,3)/n
    We want instances that are satisfiable but barely so (maximum boundary).
    """
    all_clauses = generate_all_mono3sat_clauses(n)
    random.shuffle(all_clauses)

    # Start with no clauses, add until we're near threshold
    clauses = []
    best_clauses = []
    best_boundary_size = 0

    for clause in all_clauses:
        clauses.append(clause)
        solutions = compute_solution_set(n, clauses)
        if len(solutions) == 0:
            clauses.pop()  # too many clauses, skip this one
            continue
        boundary, _ = compute_boundary(n, clauses)
        if len(boundary) > best_boundary_size:
            best_boundary_size = len(boundary)
            best_clauses = clauses.copy()

    return best_clauses, best_boundary_size


def compute_boundary_stats(n, num_trials=50):
    """Compute boundary statistics for various clause densities."""
    print(f"\n{'='*70}")
    print(f"  MONO-3SAT Boundary Analysis: n = {n}")
    print(f"{'='*70}")

    # Try different clause ratios
    ratios = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0, 10.0]

    max_boundary_overall = 0
    max_boundary_ratio = 0

    print(f"\n{'Ratio':>8} {'|Sol|':>8} {'|∂f|':>8} {'|∂f|/2^n':>10} "
          f"{'log₂|∂f|/n':>12} {'base':>8}")
    print("-" * 60)

    for ratio in ratios:
        boundaries = []
        sol_sizes = []

        for _ in range(num_trials):
            clauses = generate_random_mono3sat(n, ratio)
            if not clauses:
                continue
            boundary, solutions = compute_boundary(n, clauses)
            if len(solutions) > 0:  # only count satisfiable instances
                boundaries.append(len(boundary))
                sol_sizes.append(len(solutions))

        if not boundaries:
            continue

        avg_boundary = sum(boundaries) / len(boundaries)
        max_boundary = max(boundaries)
        avg_sols = sum(sol_sizes) / len(sol_sizes)

        if max_boundary > max_boundary_overall:
            max_boundary_overall = max_boundary
            max_boundary_ratio = ratio

        base = max_boundary ** (1.0/n) if max_boundary > 0 else 0
        log_ratio = math.log2(max_boundary) / n if max_boundary > 1 else 0

        print(f"{ratio:8.1f} {avg_sols:8.1f} {max_boundary:8d} "
              f"{max_boundary/2**n:10.4f} {log_ratio:12.4f} {base:8.4f}")

    print(f"\nMax |∂f| = {max_boundary_overall} at ratio = {max_boundary_ratio}")
    return max_boundary_overall


def find_maximum_boundary(n, num_trials=200):
    """Find the maximum possible |∂f| over many random instances.
    This is the key measurement: what is the tightest lower bound?"""

    max_boundary = 0
    max_clauses = None
    max_boundary_list = []

    all_possible_clauses = generate_all_mono3sat_clauses(n)
    total_possible = len(all_possible_clauses)

    for trial in range(num_trials):
        # Try different strategies to maximize boundary
        strategy = trial % 4

        if strategy == 0:
            # Random subset
            m = random.randint(1, min(total_possible, 3*n))
            clauses = random.sample(all_possible_clauses, m)
        elif strategy == 1:
            # Greedy: add clauses that maximize boundary
            clauses = []
            remaining = list(all_possible_clauses)
            random.shuffle(remaining)
            for c in remaining:
                test_clauses = clauses + [c]
                sols = compute_solution_set(n, test_clauses)
                if len(sols) > 0:
                    boundary, _ = compute_boundary(n, test_clauses)
                    if len(boundary) >= max_boundary * 0.8 or not clauses:
                        clauses.append(c)
        elif strategy == 2:
            # Near threshold: add until barely satisfiable
            clauses = []
            remaining = list(all_possible_clauses)
            random.shuffle(remaining)
            for c in remaining:
                test_clauses = clauses + [c]
                sols = compute_solution_set(n, test_clauses)
                if len(sols) >= 2:  # at least 2 solutions
                    clauses.append(c)
        else:
            # Single clause analysis
            m = random.randint(n//2, min(total_possible, 2*n))
            clauses = random.sample(all_possible_clauses, m)

        solutions = compute_solution_set(n, clauses)
        if len(solutions) == 0:
            continue

        boundary, _ = compute_boundary(n, clauses)
        bsize = len(boundary)
        max_boundary_list.append(bsize)

        if bsize > max_boundary:
            max_boundary = bsize
            max_clauses = clauses[:]

    return max_boundary, max_clauses, max_boundary_list


def analyze_boundary_growth():
    """Main analysis: compute max |∂f| for increasing n and fit growth rate."""
    print("=" * 70)
    print("  KEY EXPERIMENT: Growth Rate of max |∂f| for MONO-3SAT")
    print("  Question: Is base 1.795 tight, or does |∂f| grow faster?")
    print("  If base → 2.0, then Z₂ argument proves P ≠ NP")
    print("=" * 70)

    results = {}
    max_n = 16  # Feasible for exact computation

    # For small n, we can be exhaustive
    for n in range(3, max_n + 1):
        if 2**n > 500000:  # ~n=19
            break

        num_trials = max(500, 2000 // n)
        if n >= 12:
            num_trials = 100
        if n >= 14:
            num_trials = 50

        max_b, best_clauses, all_b = find_maximum_boundary(n, num_trials)

        if max_b > 0:
            base = max_b ** (1.0 / n)
            log2_ratio = math.log2(max_b) / n
        else:
            base = 0
            log2_ratio = 0

        results[n] = {
            'max_boundary': max_b,
            'base': base,
            'log2_ratio': log2_ratio,
            'num_clauses': len(best_clauses) if best_clauses else 0,
        }

        print(f"n={n:2d}: max|∂f|={max_b:8d}, base={base:.4f}, "
              f"log₂(|∂f|)/n={log2_ratio:.4f}, "
              f"#clauses={results[n]['num_clauses']}")
        sys.stdout.flush()

    # Analysis of growth rate trend
    print(f"\n{'='*70}")
    print("  GROWTH RATE ANALYSIS")
    print(f"{'='*70}")

    ns = sorted(results.keys())
    if len(ns) >= 3:
        # Look at consecutive ratios
        print(f"\n{'n':>4} {'base':>8} {'Δbase':>8} {'→2.0?':>8}")
        print("-" * 32)
        for i, n in enumerate(ns):
            base = results[n]['base']
            delta = base - results[ns[i-1]]['base'] if i > 0 else 0
            gap_to_2 = 2.0 - base
            print(f"{n:4d} {base:8.4f} {delta:+8.4f} {gap_to_2:8.4f}")

    # Extrapolation
    if len(ns) >= 4:
        recent_bases = [results[n]['base'] for n in ns[-4:]]
        avg_recent = sum(recent_bases) / len(recent_bases)
        print(f"\nAverage base (last 4): {avg_recent:.4f}")
        print(f"Gap to 2.0: {2.0 - avg_recent:.4f}")

        if avg_recent > 1.85:
            print("\n*** PROMISING: Base appears to be growing toward 2.0 ***")
            print("*** This would mean Z₂ argument covers all circuits ***")
        elif avg_recent > 1.795:
            print("\n** Base exceeds 1.795 — the threshold can be improved **")
        else:
            print(f"\nBase ≈ {avg_recent:.3f}, consistent with 1.795 claim.")
            print("Need different approach to close the NOT gap.")

    return results


def analyze_boundary_structure(n, clauses):
    """Deep analysis of the boundary structure.

    Key question: does the boundary have algebraic structure
    that could yield a C-independent order?
    """
    boundary, solutions = compute_boundary(n, clauses)

    print(f"\nBoundary structure analysis (n={n}, |∂f|={len(boundary)}):")

    # 1. Which bits are "critical" (appear in boundary transitions)?
    bit_counts = defaultdict(int)
    for x_b, j, x_bp in boundary:
        bit_counts[j] += 1

    print(f"\nCritical bit distribution:")
    for j in sorted(bit_counts.keys()):
        print(f"  bit {j}: {bit_counts[j]} transitions ({bit_counts[j]/len(boundary)*100:.1f}%)")

    # 2. How many distinct x_b (non-solution boundary points)?
    boundary_points = set(x_b for x_b, _, _ in boundary)
    print(f"\nDistinct boundary non-solutions: {len(boundary_points)}")
    print(f"Total non-solutions: {2**n - len(solutions)}")
    print(f"Boundary fraction: {len(boundary_points)/(2**n - len(solutions)):.4f}")

    # 3. Hamming weight distribution of boundary points
    weight_dist = defaultdict(int)
    for x_b in boundary_points:
        w = sum(x_b)
        weight_dist[w] += 1

    print(f"\nHamming weight distribution of boundary x_b:")
    for w in sorted(weight_dist.keys()):
        print(f"  weight {w}: {weight_dist[w]} points")

    # 4. Pairwise Hamming distances between boundary points
    bp_list = list(boundary_points)
    if len(bp_list) <= 200:
        distances = defaultdict(int)
        for i in range(len(bp_list)):
            for j2 in range(i+1, len(bp_list)):
                d = sum(a != b for a, b in zip(bp_list[i], bp_list[j2]))
                distances[d] += 1

        print(f"\nPairwise Hamming distance distribution:")
        for d in sorted(distances.keys()):
            print(f"  distance {d}: {distances[d]} pairs")

    # 5. Anti-chain analysis (for Dilworth argument)
    # In the Dilworth argument, we need boundary points that are incomparable
    # under the component-wise order
    comparable_pairs = 0
    incomparable_pairs = 0

    if len(bp_list) <= 200:
        for i in range(len(bp_list)):
            for j2 in range(i+1, len(bp_list)):
                a, b = bp_list[i], bp_list[j2]
                a_leq_b = all(ai <= bi for ai, bi in zip(a, b))
                b_leq_a = all(bi <= ai for ai, bi in zip(a, b))
                if a_leq_b or b_leq_a:
                    comparable_pairs += 1
                else:
                    incomparable_pairs += 1

        total = comparable_pairs + incomparable_pairs
        if total > 0:
            print(f"\nOrder structure (component-wise ≤):")
            print(f"  Comparable pairs: {comparable_pairs} ({comparable_pairs/total*100:.1f}%)")
            print(f"  Incomparable pairs: {incomparable_pairs} ({incomparable_pairs/total*100:.1f}%)")

    return boundary, solutions


def analyze_not_gate_effect(n, clauses):
    """Analyze how NOT gates interact with the boundary.

    Key insight from document: AND(x_i, x_j) = 0 on ALL x_b ∈ ∂f.
    But NOT(x_i) can split orbits.

    Question: how many boundary points can a single NOT gate "merge"?
    """
    boundary, solutions = compute_boundary(n, clauses)
    boundary_points = set(x_b for x_b, _, _ in boundary)

    print(f"\n{'='*70}")
    print(f"  NOT Gate Analysis (n={n})")
    print(f"{'='*70}")

    # For each variable x_i, analyze the effect of NOT(x_i)
    # NOT(x_i) creates equivalence classes: x and x⊕eᵢ are in same class

    for i in range(n):
        # Z₂ action on boundary: flip bit i
        orbits = {}
        orbit_id = 0
        visited = set()

        for x_b in boundary_points:
            if x_b in visited:
                continue
            # Flip bit i
            flipped = list(x_b)
            flipped[i] = 1 - flipped[i]
            flipped = tuple(flipped)

            orbits[orbit_id] = [x_b]
            visited.add(x_b)

            if flipped in boundary_points and flipped not in visited:
                orbits[orbit_id].append(flipped)
                visited.add(flipped)

            orbit_id += 1

        num_orbits = len(orbits)
        merged = len(boundary_points) - num_orbits

        print(f"NOT(x_{i}): {len(boundary_points)} points → {num_orbits} orbits "
              f"(merged {merged}, reduction {merged/len(boundary_points)*100:.1f}%)")

    # Multi-NOT analysis: what if we apply NOT to s variables?
    print(f"\nMulti-NOT analysis:")
    print(f"{'s NOT gates':>12} {'min orbits':>12} {'max orbits':>12} {'|∂f|/2^s':>12}")

    for s in range(1, min(n+1, 8)):
        min_orbits = len(boundary_points)
        max_orbits = 0

        # Sample subsets of size s
        if s <= n // 2 + 1:
            combos = list(itertools.combinations(range(n), s))
            if len(combos) > 100:
                combos = random.sample(combos, 100)
        else:
            combos = [tuple(random.sample(range(n), s)) for _ in range(100)]

        for subset in combos:
            # Z₂^s action: flip each combination of bits in subset
            visited = set()
            num_orbits = 0

            for x_b in boundary_points:
                if x_b in visited:
                    continue
                num_orbits += 1
                # Generate all 2^s elements in the orbit
                for mask in range(2**s):
                    elem = list(x_b)
                    for k, idx in enumerate(subset):
                        if (mask >> k) & 1:
                            elem[idx] = 1 - elem[idx]
                    elem_t = tuple(elem)
                    if elem_t in boundary_points:
                        visited.add(elem_t)

            min_orbits = min(min_orbits, num_orbits)
            max_orbits = max(max_orbits, num_orbits)

        theoretical = len(boundary_points) / (2**s)
        print(f"{s:12d} {min_orbits:12d} {max_orbits:12d} {theoretical:12.1f}")


def exhaustive_max_boundary(n):
    """For small n, exhaustively find the formula φ that maximizes |∂f|.
    Tests ALL possible subsets of clauses (feasible for n ≤ 6)."""

    all_clauses = generate_all_mono3sat_clauses(n)
    total = len(all_clauses)

    if total > 20:
        print(f"Too many clauses ({total}) for exhaustive search, using sampling")
        return find_maximum_boundary(n, 500)

    max_boundary = 0
    max_clause_set = None

    # Try all 2^total subsets
    for mask in range(1, 2**total):
        clauses = [all_clauses[i] for i in range(total) if (mask >> i) & 1]
        solutions = compute_solution_set(n, clauses)
        if len(solutions) == 0:
            continue
        boundary, _ = compute_boundary(n, clauses)
        if len(boundary) > max_boundary:
            max_boundary = len(boundary)
            max_clause_set = clauses[:]

    return max_boundary, max_clause_set, []


if __name__ == "__main__":
    random.seed(42)

    # Phase 1: Growth rate analysis
    results = analyze_boundary_growth()

    # Phase 2: Deep structural analysis on a good instance
    print(f"\n\n{'='*70}")
    print("  PHASE 2: Structural Analysis")
    print(f"{'='*70}")

    for n in [6, 8, 10]:
        if 2**n > 100000:
            break
        max_b, best_clauses, _ = find_maximum_boundary(n, 200)
        if best_clauses:
            analyze_boundary_structure(n, best_clauses)
            analyze_not_gate_effect(n, best_clauses)
