"""
Z₂ Orbit Analysis: The heart of the NOT-gate barrier.

The Z₂-orbit argument:
  Circuit with s NOT gates → group H ≅ Z₂^s acts on boundary
  → #orbits ≥ |∂f| / 2^s → circuit size ≥ |∂f| / 2^s

The loss factor is 2^s (max orbit size). But ACTUAL orbit sizes
might be much smaller if many Z₂-flipped versions of a boundary
point are NOT themselves boundary points.

KEY EXPERIMENT: Compute actual average orbit sizes and see if
the factor is c^s with c < 2. If c ≈ 1.5, then the threshold
moves from 0.844n to log₁.₅(1.795) ≈ 1.44n — which covers ALL circuits!

This would prove P ≠ NP (for circuits).
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


def compute_boundary_set(n, clauses):
    """Compute set of boundary non-solutions."""
    solutions = set()
    for bits in range(2**n):
        assignment = tuple((bits >> i) & 1 for i in range(n))
        if evaluate_mono3sat(assignment, clauses):
            solutions.add(assignment)

    boundary = set()
    for bits in range(2**n):
        assignment = tuple((bits >> i) & 1 for i in range(n))
        if assignment in solutions:
            continue
        for j in range(n):
            if assignment[j] == 0:
                flipped = list(assignment)
                flipped[j] = 1
                if tuple(flipped) in solutions:
                    boundary.add(assignment)
                    break

    return boundary, solutions


def compute_orbit_sizes(boundary_set, not_positions, n):
    """Compute actual Z₂^s orbit sizes for boundary points.

    NOT gates at positions not_positions define a Z₂^s action:
    for each subset S of not_positions, flip all bits in S.

    An orbit of x_b is {x_b ⊕ mask : mask ∈ all subsets of not_positions}
    intersected with the boundary set.
    """
    visited = set()
    orbit_sizes = []

    s = len(not_positions)

    for x_b in boundary_set:
        if x_b in visited:
            continue

        # Generate all 2^s elements in the orbit
        orbit = set()
        for mask_int in range(2**s):
            elem = list(x_b)
            for k, pos in enumerate(not_positions):
                if (mask_int >> k) & 1:
                    elem[pos] = 1 - elem[pos]
            elem_t = tuple(elem)
            if elem_t in boundary_set:
                orbit.add(elem_t)
                visited.add(elem_t)

        orbit_sizes.append(len(orbit))

    return orbit_sizes


def analyze_orbit_structure(n, num_trials=100):
    """Main experiment: how do actual orbits compare to theoretical max?"""

    print(f"\n{'='*80}")
    print(f"  Z₂ ORBIT ANALYSIS: n = {n}")
    print(f"  Theoretical max orbit size = 2^s. Actual average?")
    print(f"{'='*80}")

    from mono3sat import generate_all_mono3sat_clauses

    all_clauses = generate_all_mono3sat_clauses(n)

    # Find a good boundary instance
    best_boundary = set()
    best_clauses = None

    for _ in range(num_trials):
        k = random.randint(1, min(len(all_clauses), 4*n))
        clauses = random.sample(all_clauses, k)
        boundary, solutions = compute_boundary_set(n, clauses)
        if len(boundary) > len(best_boundary):
            best_boundary = boundary
            best_clauses = clauses[:]

    boundary = best_boundary
    print(f"\nBest instance: |∂f| = {len(boundary)} (distinct boundary non-solutions)")
    print(f"  base = {len(boundary)**(1/n):.4f}")

    # For each s from 1 to n-1, compute orbit statistics
    print(f"\n{'s':>3} {'2^s':>6} {'avg orbit':>10} {'max orbit':>10} "
          f"{'#orbits':>8} {'|∂f|/2^s':>10} {'effective c':>12} {'threshold':>10}")
    print("-" * 85)

    for s in range(1, min(n, 12)):
        # Sample different subsets of NOT positions
        all_combos = list(itertools.combinations(range(n), s))
        if len(all_combos) > 50:
            combos = random.sample(all_combos, 50)
        else:
            combos = all_combos

        all_avg_orbits = []
        all_max_orbits = []
        all_num_orbits = []

        for not_pos in combos:
            orbit_sizes = compute_orbit_sizes(boundary, not_pos, n)
            if orbit_sizes:
                avg = sum(orbit_sizes) / len(orbit_sizes)
                all_avg_orbits.append(avg)
                all_max_orbits.append(max(orbit_sizes))
                all_num_orbits.append(len(orbit_sizes))

        if not all_avg_orbits:
            continue

        # Statistics over all NOT-position choices
        avg_avg_orbit = sum(all_avg_orbits) / len(all_avg_orbits)
        avg_max_orbit = sum(all_max_orbits) / len(all_max_orbits)
        avg_num_orbits = sum(all_num_orbits) / len(all_num_orbits)
        min_num_orbits = min(all_num_orbits)

        theoretical = len(boundary) / (2**s)

        # Effective base c: avg_orbit ≈ c^s
        if avg_avg_orbit > 1:
            effective_c = avg_avg_orbit ** (1.0/s)
        else:
            effective_c = 1.0

        # Threshold: s < n * log_c(alpha) where alpha is boundary base
        alpha = len(boundary) ** (1.0/n)
        if effective_c > 1:
            threshold_ratio = math.log(alpha) / math.log(effective_c)
        else:
            threshold_ratio = float('inf')

        print(f"{s:3d} {2**s:6d} {avg_avg_orbit:10.2f} {avg_max_orbit:10.2f} "
              f"{min_num_orbits:8d} {theoretical:10.2f} {effective_c:12.4f} "
              f"{threshold_ratio:10.4f}")

    # KEY ANALYSIS: Does c converge to something < 2?
    print(f"\n  INTERPRETATION:")
    print(f"  If 'effective c' < 2.0, orbits are smaller than theoretical maximum.")
    print(f"  If 'threshold' > 1.0 for large s, Z₂ argument covers all circuits.")


def analyze_orbit_scaling():
    """How does orbit structure scale with n?"""
    print("=" * 80)
    print("  ORBIT SCALING ANALYSIS")
    print("  Does effective c decrease with n?")
    print("=" * 80)

    results = {}

    for n in range(5, 16):
        if 2**n > 100000:
            break

        from mono3sat import generate_all_mono3sat_clauses
        all_clauses = generate_all_mono3sat_clauses(n)

        # Find good boundary instance
        best_boundary = set()
        best_clauses = None
        trials = max(50, 500 // n)

        for _ in range(trials):
            k = random.randint(1, min(len(all_clauses), 4*n))
            clauses = random.sample(all_clauses, k)
            boundary, _ = compute_boundary_set(n, clauses)
            if len(boundary) > len(best_boundary):
                best_boundary = boundary
                best_clauses = clauses[:]

        boundary = best_boundary

        # Compute orbit stats for s = n//2 (midpoint)
        s = max(1, n // 2)
        all_combos = list(itertools.combinations(range(n), s))
        if len(all_combos) > 30:
            combos = random.sample(all_combos, 30)
        else:
            combos = all_combos

        avg_orbits = []
        for not_pos in combos:
            orbit_sizes = compute_orbit_sizes(boundary, not_pos, n)
            if orbit_sizes:
                avg_orbits.append(sum(orbit_sizes) / len(orbit_sizes))

        if avg_orbits:
            avg_avg = sum(avg_orbits) / len(avg_orbits)
            c_eff = avg_avg ** (1.0/s) if avg_avg > 1 else 1.0
            alpha = len(boundary) ** (1.0/n)
            threshold = math.log(alpha) / math.log(c_eff) if c_eff > 1 else float('inf')
        else:
            c_eff = 0
            alpha = 0
            threshold = 0

        results[n] = {
            'boundary': len(boundary),
            'alpha': alpha,
            'c_eff': c_eff,
            's': s,
            'threshold': threshold
        }

        print(f"n={n:2d}: |∂f|={len(boundary):6d}, α={alpha:.4f}, "
              f"s={s}, c_eff={c_eff:.4f}, threshold_ratio={threshold:.4f}")
        sys.stdout.flush()

    print(f"\n{'='*80}")
    print("  CRITICAL QUESTION: Is threshold_ratio > 1.0 for all n?")
    print("  If yes: Z₂ argument with actual orbit sizes → P ≠ NP")
    print(f"{'='*80}")

    # Check trend
    ns = sorted(results.keys())
    thresholds = [results[n]['threshold'] for n in ns if results[n]['threshold'] > 0]
    c_effs = [results[n]['c_eff'] for n in ns if results[n]['c_eff'] > 0]

    if thresholds:
        print(f"\nThreshold trend: {', '.join(f'{t:.3f}' for t in thresholds)}")
        if all(t > 1.0 for t in thresholds):
            print(">>> ALL thresholds > 1.0 — PROMISING!")
        elif thresholds[-1] > 1.0:
            print(f">>> Latest threshold = {thresholds[-1]:.3f} > 1.0 — needs more data")
        else:
            print(f">>> Latest threshold = {thresholds[-1]:.3f} ≤ 1.0 — Z₂ insufficient alone")

    if c_effs:
        print(f"Effective c trend: {', '.join(f'{c:.3f}' for c in c_effs)}")
        if c_effs[-1] < 1.5:
            print(">>> c_eff < 1.5 — orbits much smaller than 2^s!")
        elif c_effs[-1] < 1.8:
            print(">>> c_eff < 1.8 — moderate orbit size reduction")


def analyze_orbit_by_weight(n, clauses):
    """Analyze orbit structure stratified by Hamming weight.

    Monotone functions have structure related to Hamming weight.
    Boundary points at different weights might have very different orbit behavior.
    """
    boundary, solutions = compute_boundary_set(n, clauses)

    print(f"\nOrbit-by-weight analysis (n={n}, |∂f|={len(boundary)}):")

    # Stratify boundary by weight
    by_weight = defaultdict(list)
    for x_b in boundary:
        by_weight[sum(x_b)].append(x_b)

    print(f"  {'Weight':>6} {'Count':>6} {'Fraction':>10}")
    for w in sorted(by_weight.keys()):
        count = len(by_weight[w])
        print(f"  {w:6d} {count:6d} {count/len(boundary):10.4f}")

    # For each weight level, compute orbit sizes with random NOT positions
    s = n // 2
    combos = list(itertools.combinations(range(n), s))
    if len(combos) > 20:
        combos = random.sample(combos, 20)

    print(f"\n  Orbit analysis at s={s} NOT gates:")
    print(f"  {'Weight':>6} {'Avg orbit':>10} {'Max orbit':>10} {'c_eff':>8}")

    for w in sorted(by_weight.keys()):
        if len(by_weight[w]) < 3:
            continue

        weight_set = set(by_weight[w])
        all_avg = []

        for not_pos in combos:
            orbit_sizes = compute_orbit_sizes(weight_set, not_pos, n)
            if orbit_sizes:
                all_avg.append(sum(orbit_sizes) / len(orbit_sizes))

        if all_avg:
            avg = sum(all_avg) / len(all_avg)
            c_eff = avg ** (1.0/s) if avg > 1 else 1.0
            max_avg = max(all_avg)
            print(f"  {w:6d} {avg:10.2f} {max_avg:10.2f} {c_eff:8.4f}")


if __name__ == "__main__":
    random.seed(42)

    # Phase 1: Scaling analysis
    analyze_orbit_scaling()

    # Phase 2: Detailed orbit structure for specific n values
    for n in [8, 10, 12]:
        if 2**n > 100000:
            break
        analyze_orbit_structure(n, num_trials=100)

    # Phase 3: Weight-stratified analysis
    print(f"\n\n{'='*80}")
    print("  WEIGHT-STRATIFIED ORBIT ANALYSIS")
    print(f"{'='*80}")

    for n in [8, 10]:
        from mono3sat import generate_all_mono3sat_clauses
        all_clauses = generate_all_mono3sat_clauses(n)
        best_boundary = set()
        best_clauses = None

        for _ in range(200):
            k = random.randint(1, min(len(all_clauses), 4*n))
            clauses = random.sample(all_clauses, k)
            boundary, _ = compute_boundary_set(n, clauses)
            if len(boundary) > len(best_boundary):
                best_boundary = boundary
                best_clauses = clauses[:]

        if best_clauses:
            analyze_orbit_by_weight(n, best_clauses)
