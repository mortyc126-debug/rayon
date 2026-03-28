"""
Refined boundary analysis: distinguish between different definitions of |∂f|.

The document claims |∂f| ~ 1.795^n, but our initial experiment shows max ~ 2^n.
This could mean:
  (a) |∂f| counts distinct boundary NON-solutions (not pairs)
  (b) |∂f| is for specific random instances, not the max over all formulas
  (c) |∂f| counts anti-chain elements only (Dilworth argument)
  (d) |∂f| is for a specific NP-complete encoding, not arbitrary MONO-3SAT

This module computes ALL these variants to identify which is ~1.795^n.
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


def full_boundary_analysis(n, clauses):
    """Compute all variants of boundary measure."""
    solutions = set()
    non_solutions = set()

    for bits in range(2**n):
        assignment = tuple((bits >> i) & 1 for i in range(n))
        if evaluate_mono3sat(assignment, clauses):
            solutions.add(assignment)
        else:
            non_solutions.add(assignment)

    if not solutions:
        return None

    # Variant 1: Total boundary pairs (x_b, j, x_b⁺)
    boundary_pairs = []
    # Variant 2: Distinct boundary non-solutions
    boundary_nonsol = set()
    # Variant 3: Distinct boundary solutions
    boundary_sol = set()
    # Variant 4: "Minimal" solutions (no proper subset of 1-bits is also a solution)
    # Variant 5: "Maximal" non-solutions (no superset in non-solutions has more 1-bits)

    for x_b in non_solutions:
        for j in range(n):
            if x_b[j] == 0:
                flipped = list(x_b)
                flipped[j] = 1
                flipped_t = tuple(flipped)
                if flipped_t in solutions:
                    boundary_pairs.append((x_b, j, flipped_t))
                    boundary_nonsol.add(x_b)
                    boundary_sol.add(flipped_t)

    # Variant 4: Minimal solutions (in the component-wise order)
    minimal_sols = set()
    for s in solutions:
        is_minimal = True
        for j in range(n):
            if s[j] == 1:
                smaller = list(s)
                smaller[j] = 0
                if tuple(smaller) in solutions:
                    is_minimal = False
                    break
        if is_minimal:
            minimal_sols.add(s)

    # Variant 5: Maximal non-solutions
    maximal_nonsol = set()
    for ns in non_solutions:
        is_maximal = True
        for j in range(n):
            if ns[j] == 0:
                larger = list(ns)
                larger[j] = 1
                if tuple(larger) in non_solutions:
                    is_maximal = False
                    break
        if is_maximal:
            maximal_nonsol.add(ns)

    # Variant 6: Anti-chain size in boundary non-solutions
    # (component-wise incomparable elements)
    # Use greedy anti-chain extraction
    bp_list = sorted(boundary_nonsol, key=lambda x: sum(x))
    antichain = []
    for x in bp_list:
        compatible = True
        for a in antichain:
            if all(xi <= ai for xi, ai in zip(x, a)) or \
               all(ai <= xi for ai, xi in zip(x, a)):
                compatible = False
                break
        if compatible:
            antichain.append(x)

    # Also compute the width (max anti-chain) of boundary_nonsol
    # For small sets, exact computation
    max_antichain_size = len(antichain)  # greedy approximation

    return {
        'total_pairs': len(boundary_pairs),
        'distinct_nonsol': len(boundary_nonsol),
        'distinct_sol': len(boundary_sol),
        'minimal_sol': len(minimal_sols),
        'maximal_nonsol': len(maximal_nonsol),
        'greedy_antichain': max_antichain_size,
        'solutions': len(solutions),
        'non_solutions': len(non_solutions),
    }


def generate_all_mono3sat_clauses(n):
    return list(itertools.combinations(range(n), 3))


def find_max_boundary_instances(n, num_trials=300):
    """Find instances maximizing each boundary variant."""
    all_clauses = generate_all_mono3sat_clauses(n)

    best = {}
    metrics = ['total_pairs', 'distinct_nonsol', 'minimal_sol',
               'maximal_nonsol', 'greedy_antichain']

    for m in metrics:
        best[m] = {'value': 0, 'clauses': None, 'full': None}

    for trial in range(num_trials):
        k = random.randint(1, min(len(all_clauses), 4*n))
        clauses = random.sample(all_clauses, k)

        result = full_boundary_analysis(n, clauses)
        if result is None:
            continue

        for m in metrics:
            if result[m] > best[m]['value']:
                best[m]['value'] = result[m]
                best[m]['clauses'] = clauses[:]
                best[m]['full'] = result.copy()

    return best


def main():
    random.seed(42)
    print("=" * 80)
    print("  REFINED BOUNDARY ANALYSIS: Which |∂f| definition gives 1.795^n?")
    print("=" * 80)

    all_results = {}

    for n in range(3, 17):
        if 2**n > 200000:
            break

        trials = max(100, 1000 // n)
        if n >= 12:
            trials = 50
        if n >= 14:
            trials = 30

        best = find_max_boundary_instances(n, trials)
        all_results[n] = best

        # Print summary
        print(f"\nn={n:2d} (2^n={2**n})")
        print(f"  {'Metric':<20} {'Max value':>10} {'base':>8} {'log₂/n':>8}")
        print(f"  {'-'*50}")

        for m in ['total_pairs', 'distinct_nonsol', 'minimal_sol',
                   'maximal_nonsol', 'greedy_antichain']:
            val = best[m]['value']
            if val > 1:
                base = val ** (1.0/n)
                logr = math.log2(val) / n
            else:
                base = 0
                logr = 0
            print(f"  {m:<20} {val:10d} {base:8.4f} {logr:8.4f}")

        sys.stdout.flush()

    # Growth rate comparison
    print(f"\n\n{'='*80}")
    print("  GROWTH RATE COMPARISON")
    print(f"{'='*80}")

    metrics = ['total_pairs', 'distinct_nonsol', 'minimal_sol',
               'maximal_nonsol', 'greedy_antichain']

    ns = sorted(all_results.keys())

    for m in metrics:
        print(f"\n  {m}:")
        print(f"  {'n':>4} {'value':>10} {'base':>8} {'base trend':>12}")
        prev_base = 0
        for n in ns:
            val = all_results[n][m]['value']
            if val > 1:
                base = val ** (1.0/n)
                trend = f"{base - prev_base:+.4f}" if prev_base > 0 else "   ---"
                prev_base = base
            else:
                base = 0
                trend = "   ---"
            print(f"  {n:4d} {val:10d} {base:8.4f} {trend:>12}")

    # Identify which metric ~ 1.795^n
    print(f"\n\n{'='*80}")
    print("  CONCLUSION: Which metric gives base ≈ 1.795?")
    print(f"{'='*80}")

    for m in metrics:
        # Get bases for last few n values
        recent_ns = [n for n in ns if n >= 8]
        if len(recent_ns) < 2:
            recent_ns = ns[-3:]

        bases = []
        for n in recent_ns:
            val = all_results[n][m]['value']
            if val > 1:
                bases.append(val ** (1.0/n))

        if bases:
            avg = sum(bases) / len(bases)
            diff_from_1795 = abs(avg - 1.795)
            diff_from_2 = abs(avg - 2.0)
            closest = "1.795" if diff_from_1795 < diff_from_2 else "2.0"
            print(f"  {m:<20}: avg base = {avg:.4f} (closest to {closest})")


if __name__ == "__main__":
    main()
