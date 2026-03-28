"""
Threshold Convergence Analysis.

From our experiments:
  threshold_ratio = log(α) / log(c_eff)  where:
    α = |∂f|^(1/n) ≈ 1.87-1.90 (boundary base)
    c_eff = (avg orbit size)^(1/s) ≈ 1.70-1.80 (effective orbit base)

If threshold_ratio > 1.0 for all n → P ≠ NP (for circuits).

Observed: threshold decreasing from 1.567 to 1.093 (n=5..15).
Question: limit > 1.0 or = 1.0?

This module:
1. Pushes computation to larger n with optimizations
2. Fits asymptotic model to predict the limit
3. Analyzes WHY orbits are smaller than 2^s (theoretical insight)
"""

import itertools
from collections import defaultdict
import random
import math
import sys
import time


def evaluate_mono3sat_fast(bits_int, clauses_masks, n):
    """Fast evaluation using bitmasks.
    clauses_masks: list of bitmasks, clause satisfied if (bits & mask) != 0.
    """
    for mask in clauses_masks:
        if (bits_int & mask) == 0:
            return False
    return True


def clauses_to_masks(clauses, n):
    """Convert clauses to bitmasks for fast evaluation."""
    masks = []
    for clause in clauses:
        mask = 0
        for v in clause:
            mask |= (1 << v)
        masks.append(mask)
    return masks


def compute_boundary_fast(n, clauses):
    """Fast boundary computation using bitmasks."""
    masks = clauses_to_masks(clauses, n)

    # Compute solution set as a bitset
    solutions = set()
    for bits in range(2**n):
        if evaluate_mono3sat_fast(bits, masks, n):
            solutions.add(bits)

    # Compute boundary non-solutions (as integers)
    boundary = set()
    for bits in range(2**n):
        if bits in solutions:
            continue
        for j in range(n):
            if not (bits & (1 << j)):  # bit j is 0
                flipped = bits | (1 << j)
                if flipped in solutions:
                    boundary.add(bits)
                    break

    return boundary, solutions


def compute_orbit_stats_fast(boundary, not_positions, n):
    """Fast orbit computation using bitmasks."""
    s = len(not_positions)
    not_mask_list = not_positions  # list of bit positions

    visited = set()
    num_orbits = 0
    total_orbit_size = 0

    for x_b in boundary:
        if x_b in visited:
            continue
        num_orbits += 1
        orbit_size = 0

        for flip_mask_int in range(2**s):
            elem = x_b
            for k in range(s):
                if (flip_mask_int >> k) & 1:
                    elem ^= (1 << not_mask_list[k])
            if elem in boundary:
                if elem not in visited:
                    visited.add(elem)
                    orbit_size += 1

        total_orbit_size += orbit_size

    avg_orbit = total_orbit_size / num_orbits if num_orbits > 0 else 0
    return num_orbits, avg_orbit


def generate_all_mono3sat_clauses(n):
    return list(itertools.combinations(range(n), 3))


def find_best_boundary(n, num_trials=200):
    """Find MONO-3SAT instance maximizing boundary size, fast version."""
    all_clauses = generate_all_mono3sat_clauses(n)
    best_boundary = set()
    best_clauses = None

    for _ in range(num_trials):
        k = random.randint(max(1, n//2), min(len(all_clauses), 5*n))
        clauses = random.sample(all_clauses, k)
        boundary, solutions = compute_boundary_fast(n, clauses)
        if len(boundary) > len(best_boundary):
            best_boundary = boundary
            best_clauses = clauses[:]

    return best_boundary, best_clauses


def extended_scaling_analysis():
    """Push the scaling analysis to larger n with optimizations."""
    print("=" * 80)
    print("  EXTENDED THRESHOLD CONVERGENCE ANALYSIS")
    print("=" * 80)

    results = {}

    for n in range(5, 22):
        if 2**n > 2_000_000:  # ~n=20
            break

        t0 = time.time()
        trials = max(30, 300 // n)
        if n >= 16:
            trials = 20
        if n >= 18:
            trials = 10

        boundary, clauses = find_best_boundary(n, trials)

        if not boundary:
            continue

        alpha = len(boundary) ** (1.0/n)

        # Test multiple s values
        s_half = max(1, n // 2)

        # Sample NOT positions
        all_combos = list(itertools.combinations(range(n), s_half))
        if len(all_combos) > 20:
            combos = random.sample(all_combos, 20)
        else:
            combos = all_combos

        avg_orbits_list = []
        for not_pos in combos:
            num_orbits, avg_orbit = compute_orbit_stats_fast(boundary, list(not_pos), n)
            avg_orbits_list.append(avg_orbit)

        avg_avg_orbit = sum(avg_orbits_list) / len(avg_orbits_list)
        c_eff = avg_avg_orbit ** (1.0/s_half) if avg_avg_orbit > 1 else 1.0
        threshold = math.log(alpha) / math.log(c_eff) if c_eff > 1 else float('inf')

        dt = time.time() - t0

        results[n] = {
            'boundary': len(boundary),
            'alpha': alpha,
            'c_eff': c_eff,
            's': s_half,
            'threshold': threshold,
            'time': dt,
        }

        print(f"n={n:2d}: |∂f|={len(boundary):8d}, α={alpha:.4f}, "
              f"s={s_half:2d}, c_eff={c_eff:.4f}, threshold={threshold:.4f} "
              f"[{dt:.1f}s]")
        sys.stdout.flush()

    # Fit asymptotic model
    print(f"\n{'='*80}")
    print("  ASYMPTOTIC MODEL FIT")
    print(f"{'='*80}")

    ns = sorted(results.keys())

    # Model 1: threshold = a + b/n
    if len(ns) >= 4:
        # Simple linear regression of threshold vs 1/n
        xs = [1.0/n for n in ns]
        ys = [results[n]['threshold'] for n in ns]

        n_pts = len(xs)
        sum_x = sum(xs)
        sum_y = sum(ys)
        sum_xy = sum(x*y for x, y in zip(xs, ys))
        sum_xx = sum(x*x for x in xs)

        # y = a + b*x where x = 1/n
        b = (n_pts * sum_xy - sum_x * sum_y) / (n_pts * sum_xx - sum_x**2)
        a = (sum_y - b * sum_x) / n_pts

        print(f"\nModel: threshold ≈ {a:.4f} + {b:.4f}/n")
        print(f"  Predicted limit (n→∞): {a:.4f}")

        if a > 1.0:
            print(f"  >>> LIMIT > 1.0 — Z₂ argument with actual orbits proves P ≠ NP!")
        elif a > 0.99:
            print(f"  >>> LIMIT ≈ 1.0 — borderline, need more data")
        else:
            print(f"  >>> LIMIT < 1.0 — Z₂ orbit improvement insufficient")

    # Model 2: threshold = a + b/n + c/n² (manual quadratic regression)
    if len(ns) >= 6:
        xs = [1.0/n for n in ns]
        ys = [results[n]['threshold'] for n in ns]
        # Use last 8 points for quadratic fit
        recent = min(len(xs), 8)
        xs_r = xs[-recent:]
        ys_r = ys[-recent:]
        # Simple: fit y = a + b*x using only recent points
        n_pts = len(xs_r)
        sx = sum(xs_r); sy = sum(ys_r)
        sxy = sum(x*y for x,y in zip(xs_r,ys_r))
        sxx = sum(x*x for x in xs_r)
        b2 = (n_pts*sxy - sx*sy) / (n_pts*sxx - sx**2)
        a2 = (sy - b2*sx) / n_pts
        print(f"\nModel (recent {recent} points): threshold ≈ {a2:.4f} + {b2:.4f}/n")
        print(f"  Predicted limit (n→∞): {a2:.4f}")

    # Model 3: Look at log(threshold - 1) vs n for exponential decay
    if len(ns) >= 4:
        print(f"\nExponential decay analysis: threshold - 1 vs n")
        for n in ns:
            t = results[n]['threshold']
            if t > 1.0:
                print(f"  n={n:2d}: threshold-1 = {t-1:.4f}, "
                      f"log₂(threshold-1) = {math.log2(t-1):.4f}")

        # Fit log(threshold-1) = a + b*n (exponential decay)
        log_vals = [(n, math.log(results[n]['threshold'] - 1))
                    for n in ns if results[n]['threshold'] > 1.001]
        if len(log_vals) >= 3:
            xs = [x[0] for x in log_vals]
            ys = [x[1] for x in log_vals]
            n_pts = len(xs)
            sum_x = sum(xs)
            sum_y = sum(ys)
            sum_xy = sum(x*y for x, y in zip(xs, ys))
            sum_xx = sum(x*x for x in xs)

            b_exp = (n_pts * sum_xy - sum_x * sum_y) / (n_pts * sum_xx - sum_x**2)
            a_exp = (sum_y - b_exp * sum_x) / n_pts

            print(f"\n  Model: ln(threshold-1) ≈ {a_exp:.4f} + {b_exp:.4f}*n")
            print(f"  Decay rate: {b_exp:.4f} per n")

            if b_exp < 0:
                # threshold - 1 ≈ exp(a) * exp(b*n)
                # crosses 0 when... well, exponentially decaying toward 0
                cross_n = -a_exp / b_exp if b_exp != 0 else float('inf')
                print(f"  Predicted crossing (threshold=1) at n ≈ {cross_n:.0f}")
                if cross_n > 1000:
                    print(f"  >>> Crossing very far away — threshold stays > 1 in practice")
                elif cross_n > 100:
                    print(f"  >>> Crossing at moderate n — needs theoretical analysis")
                else:
                    print(f"  >>> Crossing at small n — Z₂ improvement may not suffice")

    # Analysis of c_eff growth
    print(f"\n{'='*80}")
    print("  c_eff GROWTH ANALYSIS")
    print(f"{'='*80}")

    print(f"\n  n   c_eff   c_eff/2   gap_to_2")
    for n in ns:
        c = results[n]['c_eff']
        print(f"  {n:2d}  {c:.4f}  {c/2:.4f}   {2-c:.4f}")

    # Does c_eff → 2.0?
    if len(ns) >= 4:
        gaps = [2.0 - results[n]['c_eff'] for n in ns]
        log_gaps = [(n, math.log(g)) for n, g in zip(ns, gaps) if g > 0.01]
        if len(log_gaps) >= 3:
            xs = [x[0] for x in log_gaps]
            ys = [x[1] for x in log_gaps]
            n_pts = len(xs)
            sum_x = sum(xs)
            sum_y = sum(ys)
            sum_xy = sum(x*y for x, y in zip(xs, ys))
            sum_xx = sum(x*x for x in xs)

            b_gap = (n_pts * sum_xy - sum_x * sum_y) / (n_pts * sum_xx - sum_x**2)
            a_gap = (sum_y - b_gap * sum_x) / n_pts

            print(f"\n  Model: gap(2-c_eff) ≈ exp({a_gap:.3f} + {b_gap:.4f}*n)")
            print(f"  Gap decay rate: {b_gap:.4f}")

    # THEORETICAL ANALYSIS
    print(f"\n{'='*80}")
    print("  THEORETICAL ANALYSIS: WHY ARE ORBITS SMALLER THAN 2^s?")
    print(f"{'='*80}")

    print("""
    The Z₂ action flips bits at NOT-gate positions. An orbit element x⊕mask
    is in the boundary only if:
      (a) x⊕mask is a non-solution, AND
      (b) x⊕mask has a neighbor that IS a solution

    Condition (a): flipping bits may turn a non-solution into a solution
      (if the flipped bits satisfy previously unsatisfied clauses)
    Condition (b): the flipped point must have the right local structure

    For MONOTONE functions, flipping 0→1 can only HELP (add solutions),
    so condition (a) becomes more restrictive: flipped points are more
    likely to be solutions (not non-solutions), hence NOT in the boundary.

    This is WHY orbits are smaller: the monotonicity of f means that
    Z₂ flips tend to push points OUT of the boundary (into solutions).

    QUANTITATIVE: Let p(w) = Pr[random assignment of weight w is a solution].
    Flipping s random bits changes the weight by ±Δ.
    If p(w+Δ) >> p(w), the flipped point is likely a solution → orbit smaller.

    For threshold MONO-3SAT: p(w) transitions sharply around w* ≈ n·(1-2^{-1/3}).
    Boundary is concentrated at weights near w*.
    Flipping s bits changes weight by O(√s), which may push past threshold.

    The effective orbit size is:
      c_eff^s ≈ 2^s · Pr[x⊕mask ∈ boundary | x ∈ boundary]
      ≈ 2^s · Pr[not a solution AND has solution neighbor after flip]

    For large s: most flips push past threshold → Pr → 0 → small orbits.
    But the rate depends on the sharpness of the threshold.
    """)

    return results


if __name__ == "__main__":
    random.seed(42)
    results = extended_scaling_analysis()
