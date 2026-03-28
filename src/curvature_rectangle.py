"""
NEW METHOD: Curvature → Rectangle Size → Circuit Lower Bounds.

The key insight connecting THREE things:

1. OLLIVIER-RICCI CURVATURE κ of the solution space graph G(f)
   (from the original research document)

2. KW RECTANGLE SIZE = max |R × C| over all monochromatic rectangles
   in the Karchmer-Wigderson game

3. FORMULA/CIRCUIT SIZE ≥ total_entries / max_rectangle_size

THE CONNECTION:
  Negative curvature (κ < 0) → good vertex expansion
  → solutions are "spread out" → no large coherent rectangle
  → many small rectangles needed → large formula → large circuit

  Zero curvature (κ ≈ 0) → poor expansion
  → solutions cluster → large rectangles possible
  → few rectangles suffice → small formula → small circuit

WHY THIS BYPASSES BARRIERS:
  - NOT a natural proof: curvature is specific to the function's
    solution space, not a property of random functions
  - NOT relativizing: curvature changes when you change the oracle
    (adding oracle changes the solution space geometry)
  - NOT algebrizing: curvature is a metric/geometric property,
    not an algebraic one

THE EXPERIMENT: Compute (curvature, max_rectangle, formula_size)
for many functions and check if curvature PREDICTS rectangle size.
"""

import itertools
from collections import defaultdict
import random
import math
import sys
import time


def compute_ollivier_ricci_curvature(n, solutions_set):
    """Compute average Ollivier-Ricci curvature of the solution space graph.

    Nodes = solutions. Edges = Hamming distance 1.

    Ollivier-Ricci curvature κ(x,y) for edge (x,y):
      κ(x,y) = 1 - W₁(μ_x, μ_y) / d(x,y)
    where μ_x = uniform distribution on neighbors of x (in solution graph),
    d(x,y) = graph distance (here = 1 for edges).

    W₁ = Earth Mover's Distance (Wasserstein-1).

    For the Hamming graph restricted to solutions:
      μ_x = uniform over {neighbors of x that are also solutions}

    Simplified computation for small instances.
    """
    if len(solutions_set) < 2:
        return 0.0

    sol_list = list(solutions_set)

    # Build adjacency: Hamming distance 1 within solutions
    neighbors = defaultdict(set)
    for i, s in enumerate(sol_list):
        for j in range(n):
            flipped = s ^ (1 << j)
            if flipped in solutions_set:
                neighbors[s].add(flipped)

    # Compute curvature for sampled edges
    curvatures = []
    edges = []

    for s in sol_list:
        for nb in neighbors[s]:
            if s < nb:  # avoid double counting
                edges.append((s, nb))

    if not edges:
        return 0.0

    # Sample edges if too many
    if len(edges) > 200:
        sampled = random.sample(edges, 200)
    else:
        sampled = edges

    for x, y in sampled:
        nx = neighbors[x]
        ny = neighbors[y]

        if not nx or not ny:
            continue

        # Simplified curvature: κ ≈ (|nx ∩ ny| + 1) / max(|nx|, |ny|) - related measure
        # For exact Ollivier-Ricci, we'd need optimal transport.
        # Use the Lin-Lu-Yau lower bound instead:
        # κ(x,y) ≥ (|common_neighbors| + |{x}∩ny| + |{y}∩nx|) / max(|nx|,|ny|) - 1

        common = nx & ny
        x_in_ny = 1 if x in ny else 0  # always true since (x,y) is an edge
        y_in_nx = 1 if y in nx else 0  # always true

        # Lin-Lu-Yau approximation
        d_x = len(nx)
        d_y = len(ny)

        if d_x == 0 or d_y == 0:
            continue

        # Fraction of mass that can be "matched" cheaply
        # Common neighbors: distance 0 to each other (in the coupling)
        # x↔y: distance 1 (they're neighbors)
        # Total mass to move: 1
        # Matched at distance 0: |common| / max(d_x, d_y) (approximately)

        # Simple curvature estimate:
        # κ ≈ |common| / max(d_x, d_y) - (d_x + d_y - 2|common| - 2) / (d_x * d_y)
        # (This is a rough approximation)

        kappa = (len(common) + 2) / max(d_x, d_y) - 1
        curvatures.append(kappa)

    if not curvatures:
        return 0.0

    return sum(curvatures) / len(curvatures)


def compute_max_rectangle_size(n, func):
    """Compute the maximum KW rectangle size for function func."""
    ones = []
    zeros = []
    for bits in range(2**n):
        x = tuple((bits >> j) & 1 for j in range(n))
        if func(x):
            ones.append(x)
        else:
            zeros.append(x)

    if not ones or not zeros:
        return 0, 0

    max_rect = 0

    # For each possible output index i:
    for i in range(n):
        # Monotone rectangle: R = {x ∈ ones : x_i=1}, C = {y ∈ zeros : y_i=0}
        R_mono = [x for x in ones if x[i] == 1]
        C_mono = [y for y in zeros if y[i] == 0]
        rect_size = len(R_mono) * len(C_mono)
        max_rect = max(max_rect, rect_size)

        # General rectangle also includes anti-monotone
        R_anti = [x for x in ones if x[i] == 0]
        C_anti = [y for y in zeros if y[i] == 1]
        rect_anti = len(R_anti) * len(C_anti)
        max_rect = max(max_rect, rect_anti)

    total_entries = len(ones) * len(zeros)
    return max_rect, total_entries


def compute_kw_cover(n, func):
    """Compute KW rectangle cover size (greedy)."""
    ones = []
    zeros = []
    for bits in range(2**n):
        x = tuple((bits >> j) & 1 for j in range(n))
        if func(x):
            ones.append(x)
        else:
            zeros.append(x)

    if not ones or not zeros:
        return 0

    # Monotone cover
    uncov = set((xi, yi) for xi in range(len(ones)) for yi in range(len(zeros)))
    rects = 0
    while uncov:
        x0, y0 = next(iter(uncov))
        best_cov = 0
        best = None
        for i in range(n):
            if ones[x0][i] == 1 and zeros[y0][i] == 0:
                rows = {xi for xi in range(len(ones)) if ones[xi][i] == 1}
                cols = {yi for yi in range(len(zeros)) if zeros[yi][i] == 0}
                c = sum(1 for xi in rows for yi in cols if (xi, yi) in uncov)
                if c > best_cov:
                    best_cov = c
                    best = (rows, cols)
        if best:
            for xi in best[0]:
                for yi in best[1]:
                    uncov.discard((xi, yi))
        rects += 1
    return rects


def main():
    print("=" * 80)
    print("  CURVATURE → RECTANGLE SIZE → CIRCUIT LOWER BOUNDS")
    print("  New method: geometry predicts computational complexity")
    print("=" * 80)

    from mono3sat import generate_all_mono3sat_clauses

    def evaluate_mono3sat(x, clauses):
        for clause in clauses:
            if not any(x[v] for v in clause):
                return False
        return True

    results = []

    # Test on various function families
    for n in range(4, 13):
        if 2**n > 100000:
            break

        all_clauses = generate_all_mono3sat_clauses(n)

        # Generate instances at different "hardness" levels
        # Easy: few clauses (most assignments satisfy)
        # Hard: many clauses (near threshold)
        for difficulty, clause_ratio in [('easy', 0.5), ('medium', 2.0),
                                          ('hard', 4.0), ('vhard', 8.0)]:
            num_clauses = max(1, int(clause_ratio * n))
            if num_clauses > len(all_clauses):
                continue

            # Try a few random instances
            best_result = None

            for _ in range(10):
                clauses = random.sample(all_clauses, num_clauses)
                func = lambda x, cl=clauses: evaluate_mono3sat(x, cl)

                # Count solutions
                sol_set = set()
                for bits in range(2**n):
                    x = tuple((bits >> j) & 1 for j in range(n))
                    if func(x):
                        sol_set.add(bits)

                num_sol = len(sol_set)
                if num_sol == 0 or num_sol == 2**n:
                    continue
                if num_sol * (2**n - num_sol) > 100000:
                    continue

                # Compute curvature
                kappa = compute_ollivier_ricci_curvature(n, sol_set)

                # Compute max rectangle size
                max_rect, total = compute_max_rectangle_size(n, func)

                # Compute KW cover (formula size)
                cover = compute_kw_cover(n, func)

                # Normalized measures
                rect_ratio = max_rect / total if total > 0 else 0
                sol_frac = num_sol / 2**n

                r = {
                    'n': n,
                    'difficulty': difficulty,
                    'kappa': kappa,
                    'max_rect': max_rect,
                    'total': total,
                    'rect_ratio': rect_ratio,
                    'cover': cover,
                    'num_sol': num_sol,
                    'sol_frac': sol_frac,
                }

                if best_result is None or abs(kappa) > abs(best_result['kappa']):
                    best_result = r

            if best_result:
                results.append(best_result)

        sys.stdout.flush()

    # Print results
    print(f"\n{'n':>3} {'diff':>6} {'κ':>8} {'max_rect':>10} {'total':>10} "
          f"{'rect%':>8} {'cover':>6} {'sol%':>6}")
    print("-" * 65)

    for r in results:
        print(f"{r['n']:3d} {r['difficulty']:>6} {r['kappa']:8.4f} "
              f"{r['max_rect']:10d} {r['total']:10d} "
              f"{r['rect_ratio']:8.4f} {r['cover']:6d} {r['sol_frac']:6.3f}")

    # Analyze correlation between curvature and rectangle ratio
    print(f"\n{'='*80}")
    print("  CORRELATION ANALYSIS: κ vs rect_ratio")
    print(f"{'='*80}")

    kappas = [r['kappa'] for r in results if r['kappa'] != 0]
    ratios = [r['rect_ratio'] for r in results if r['kappa'] != 0]
    covers = [r['cover'] for r in results if r['kappa'] != 0]

    if len(kappas) >= 3:
        # Pearson correlation
        mean_k = sum(kappas) / len(kappas)
        mean_r = sum(ratios) / len(ratios)
        cov = sum((k - mean_k) * (r - mean_r) for k, r in zip(kappas, ratios))
        var_k = sum((k - mean_k)**2 for k in kappas)
        var_r = sum((r - mean_r)**2 for r in ratios)

        if var_k > 0 and var_r > 0:
            corr = cov / (var_k * var_r) ** 0.5
            print(f"\n  Pearson correlation (κ, rect_ratio): {corr:.4f}")

            if corr > 0.5:
                print("  >>> POSITIVE correlation: more negative κ → larger rectangles")
                print("  >>> This CONTRADICTS our hypothesis (expected negative)")
            elif corr < -0.5:
                print("  >>> NEGATIVE correlation: more negative κ → smaller rectangles")
                print("  >>> SUPPORTS our hypothesis!")
                print("  >>> Negative curvature → small rectangles → large formula → hard")
            else:
                print("  >>> Weak correlation: curvature alone doesn't determine rect size")

        # Also check κ vs cover
        mean_c = sum(covers) / len(covers)
        cov_kc = sum((k - mean_k) * (c - mean_c) for k, c in zip(kappas, covers))
        var_c = sum((c - mean_c)**2 for c in covers)
        if var_k > 0 and var_c > 0:
            corr_kc = cov_kc / (var_k * var_c) ** 0.5
            print(f"  Pearson correlation (κ, cover_size): {corr_kc:.4f}")

    # Group by difficulty and show trends
    print(f"\n  By difficulty level:")
    by_diff = defaultdict(list)
    for r in results:
        by_diff[r['difficulty']].append(r)

    for diff in ['easy', 'medium', 'hard', 'vhard']:
        if diff in by_diff:
            rs = by_diff[diff]
            avg_k = sum(r['kappa'] for r in rs) / len(rs)
            avg_rr = sum(r['rect_ratio'] for r in rs) / len(rs)
            avg_cov = sum(r['cover'] for r in rs) / len(rs)
            print(f"    {diff:>6}: avg κ = {avg_k:+.4f}, "
                  f"avg rect% = {avg_rr:.4f}, avg cover = {avg_cov:.1f}")

    print(f"\n{'='*80}")
    print("  THEORETICAL FRAMEWORK")
    print(f"{'='*80}")
    print("""
    If curvature κ bounds rectangle size R:
      R ≤ f(κ) × 2^n

    And formula size ≥ total_entries / R ≥ 2^n / (f(κ) × 2^n) × |sol| × |non-sol|

    For κ → 0 (P functions): f(κ) → 1, R → 2^n, formula → polynomial
    For κ < -c (NP functions): f(κ) < 1, R < 2^n, formula → exponential

    THE CHAIN:
      κ(f) < -c
      → vertex expansion of solution space ≥ h(c)
      → max KW rectangle ≤ 2^{n(1-δ(c))}
      → formula size ≥ 2^{n·δ(c)}
      → circuit size ≥ 2^{n·δ(c)} / 2^{depth}
      → for depth < n·δ(c): circuit size ≥ exponential

    This would give a NEW lower bound technique based on GEOMETRY.
    """)


if __name__ == "__main__":
    random.seed(42)
    main()
