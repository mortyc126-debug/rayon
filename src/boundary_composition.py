"""
BOUNDARY COMPOSITION LAW: How does |∂f| change through AND/OR?

∂f = edge boundary of f⁻¹(1) in the Boolean hypercube.
|∂f| = number of edges (x, x⊕eᵢ) where f(x) ≠ f(x⊕eᵢ).

AND: f = g ∧ h. f⁻¹(1) = g⁻¹(1) ∩ h⁻¹(1).
OR:  f = g ∨ h. f⁻¹(1) = g⁻¹(1) ∪ h⁻¹(1).

QUESTION: What is |∂(g∧h)| in terms of |∂g| and |∂h|?

If the composition law is: |∂(g∧h)| ≈ |∂g|^a × |∂h|^b
with a+b < 2 but a,b > 0: this is BETWEEN additive and multiplicative!

Then: starting from |∂(xᵢ)| = 2^{n-1} (each variable has half boundary):
After s AND/OR gates: |∂f| ≤ (2^{n-1})^{(a+b)^s/2} or similar.

And: s ≥ some function of |∂f| that's between log and linear.

EXPERIMENT: Measure the actual composition law for |∂|.
"""

import itertools
from collections import defaultdict
import random
import math
import sys


def compute_boundary(n, tt):
    """Compute |∂f| = number of boundary edges."""
    total = 2**n
    count = 0
    for bits in range(total):
        for j in range(n):
            nb = bits ^ (1 << j)
            if bits < nb and tt[bits] != tt[nb]:
                count += 1
    return count


def compute_influence_vector(n, tt):
    """Compute influence of each variable."""
    total = 2**n
    inf = [0] * n
    for bits in range(total):
        for j in range(n):
            nb = bits ^ (1 << j)
            if tt[bits] != tt[nb]:
                inf[j] += 1
    # Each edge counted twice (from both endpoints)
    return [i // 2 for i in inf]


def measure_composition(n, num_trials=200):
    """Measure how |∂| changes through AND/OR gates on random functions."""
    total = 2**n

    results = {'AND': [], 'OR': [], 'NOT': []}

    for _ in range(num_trials):
        tt_g = {b: random.randint(0, 1) for b in range(total)}
        tt_h = {b: random.randint(0, 1) for b in range(total)}

        bg = compute_boundary(n, tt_g)
        bh = compute_boundary(n, tt_h)

        # AND
        tt_and = {b: tt_g[b] & tt_h[b] for b in range(total)}
        b_and = compute_boundary(n, tt_and)

        # OR
        tt_or = {b: tt_g[b] | tt_h[b] for b in range(total)}
        b_or = compute_boundary(n, tt_or)

        # NOT
        tt_not = {b: 1 - tt_g[b] for b in range(total)}
        b_not = compute_boundary(n, tt_not)

        if bg > 0 and bh > 0:
            results['AND'].append((bg, bh, b_and))
            results['OR'].append((bg, bh, b_or))
            results['NOT'].append((bg, 0, b_not))

    return results


def fit_composition_law(results, gate_type):
    """Fit: |∂(g OP h)| ≈ C × |∂g|^a × |∂h|^b.

    In log space: log(∂_out) = log C + a × log(∂g) + b × log(∂h).
    Linear regression.
    """
    data = results[gate_type]
    if not data or gate_type == 'NOT':
        return None

    # Filter valid
    valid = [(bg, bh, bo) for bg, bh, bo in data if bg > 0 and bh > 0 and bo > 0]
    if len(valid) < 10:
        return None

    # Log transform
    X = [(math.log(bg), math.log(bh)) for bg, bh, _ in valid]
    Y = [math.log(bo) for _, _, bo in valid]

    # Fit: Y = c + a*X1 + b*X2
    n_pts = len(X)
    sx1 = sum(x[0] for x in X)
    sx2 = sum(x[1] for x in X)
    sy = sum(Y)
    sx1x1 = sum(x[0]**2 for x in X)
    sx2x2 = sum(x[1]**2 for x in X)
    sx1x2 = sum(x[0]*x[1] for x in X)
    sx1y = sum(x[0]*y for x, y in zip(X, Y))
    sx2y = sum(x[1]*y for x, y in zip(X, Y))

    # Solve normal equations (simplified: assume symmetric a ≈ b)
    # Y ≈ c + a*(X1 + X2)/2 + ...
    # Just fit Y = c + a*X1 (ignore X2 correlation)
    sxx = sx1x1
    sxy = sx1y
    sx = sx1

    denom = n_pts * sxx - sx**2
    if denom == 0:
        return None

    a = (n_pts * sxy - sx * sy) / denom
    c = (sy - a * sx) / n_pts

    # Also try symmetric fit: Y = c + a*(X1+X2)
    s_sum = sum(x[0] + x[1] for x in X)
    s_sum2 = sum((x[0]+x[1])**2 for x in X)
    s_sumy = sum((x[0]+x[1])*y for x, y in zip(X, Y))

    denom2 = n_pts * s_sum2 - s_sum**2
    if denom2 != 0:
        a_sym = (n_pts * s_sumy - s_sum * sy) / denom2
        c_sym = (sy - a_sym * s_sum) / n_pts
    else:
        a_sym = a
        c_sym = c

    return a, c, a_sym, c_sym


def main():
    random.seed(42)
    print("=" * 70)
    print("  BOUNDARY COMPOSITION LAW")
    print("  How does |∂f| change through AND/OR gates?")
    print("=" * 70)

    for n in range(4, 12):
        if 2**n > 100000:
            break

        results = measure_composition(n, 300)

        print(f"\n  n = {n}:")

        for gate in ['AND', 'OR']:
            data = results[gate]
            if not data:
                continue

            # Statistics
            ratios = [bo / max(bg, bh) for bg, bh, bo in data if max(bg, bh) > 0]
            sum_ratios = [bo / (bg + bh) for bg, bh, bo in data if bg + bh > 0]
            prod_ratios = [bo / (bg * bh) for bg, bh, bo in data
                          if bg > 0 and bh > 0]

            avg_r = sum(ratios) / len(ratios) if ratios else 0
            avg_sr = sum(sum_ratios) / len(sum_ratios) if sum_ratios else 0
            avg_pr = sum(prod_ratios) / len(prod_ratios) if prod_ratios else 0

            print(f"    {gate}:")
            print(f"      ∂_out / max(∂g, ∂h):  avg = {avg_r:.4f}")
            print(f"      ∂_out / (∂g + ∂h):    avg = {avg_sr:.4f}")
            print(f"      ∂_out / (∂g × ∂h):    avg = {avg_pr:.6f}")

            # Fit power law
            fit = fit_composition_law(results, gate)
            if fit:
                a, c, a_sym, c_sym = fit
                print(f"      Fit log(∂out) = {c:.2f} + {a:.4f} × log(∂g)")
                print(f"      Symmetric: log(∂out) = {c_sym:.2f} + {a_sym:.4f} × log(∂g + ∂h)")
                print(f"      Exponent a = {a_sym:.4f}")

                if 0.5 < a_sym < 1.0:
                    print(f"      >>> FRACTIONAL EXPONENT! Between additive and multiplicative!")
                elif a_sym >= 1.0:
                    print(f"      >>> Linear or super-linear → additive regime")
                else:
                    print(f"      >>> Sub-square-root → strong compression")

        # NOT
        not_data = results['NOT']
        if not_data:
            ratios = [bo / bg for bg, _, bo in not_data if bg > 0]
            avg = sum(ratios) / len(ratios)
            print(f"    NOT: ∂_out / ∂_in = {avg:.4f} (should be 1.0)")

        sys.stdout.flush()

    # Summary
    print(f"\n\n{'='*70}")
    print("  COMPOSITION LAW SUMMARY")
    print(f"{'='*70}")
    print("""
    QUESTION: |∂(g OP h)| ≈ f(|∂g|, |∂h|)?

    If f = max:     s ≥ 1 (trivial)
    If f = sum:     s ≥ |∂f| / max_∂ (potentially useful if max_∂ < |∂f|)
    If f = product: s ≥ log |∂f| (logarithmic — weak)
    If f = |∂g|^a × |∂h|^b with a+b < 2, a,b > 0:
      s ≥ |∂f|^{1/c} for some c > 1. BETWEEN log and linear!

    The EXPONENT a from the fit tells us which regime we're in.
    """)


if __name__ == "__main__":
    main()
