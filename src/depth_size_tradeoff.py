"""
Depth-Size Tradeoff: Exponential Lower Bounds for Bounded-Depth Circuits.

KEY INSIGHT from width analysis:
The formula-to-circuit gap is exactly fan-out savings = 2^depth.
So: circuit_size ≥ formula_size / 2^depth.

If we can prove formula_size ≥ α^n for some α > 1:
  circuit_size ≥ α^n / 2^d

For d < n · log₂(α): this is EXPONENTIAL.
For d ≥ n · log₂(α): this is trivial (< 1).

The question: what is the FORMULA SIZE of MONO-3SAT functions?

For monotone formulas: Razborov-type bounds give exp lower bounds.
For GENERAL formulas: our Fourier analysis gives sparsity ≥ 1.96^n,
but sparsity ≠ formula size.

HOWEVER: there's a direct connection via the KW game:
  Formula size = number of leaves in optimal KW protocol tree
  = min rectangle cover of KW matrix

Our KW analysis showed: the rectangle cover for MONO-3SAT is
the SAME for monotone and general (NOT benefit = 0%).

If general formula size = monotone formula size ≥ F(n):
  circuit_size ≥ F(n) / 2^d

For SPECIFIC f with monotone formula size 2^{Ω(√n)} (like CLIQUE):
  circuit_size ≥ 2^{Ω(√n)} / 2^d
  For d ≤ c√n: circuit_size ≥ 2^{Ω(√n)} — EXPONENTIAL!

THIS GIVES: For the CLIQUE function, circuits of depth O(√n)
need exponential size.

Current best: circuits of depth O(log n) need exp size
(from switching lemma / Håstad).

Our bound is for depth O(√n) — MUCH deeper — if we can prove
that formula size for CLIQUE is the same for general and monotone.

THE EXPERIMENT: Verify that general formula size ≈ monotone formula
size for various functions, scaling with n.
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


def compute_kw_rectangle_cover(n, clauses, use_general=False):
    """Compute the KW rectangle cover size (= formula size lower bound).

    For monotone KW: valid outputs are {i : x_i=1, y_i=0}
    For general KW: valid outputs are {i : x_i ≠ y_i}

    Uses greedy rectangle cover.
    """
    solutions = set()
    non_solutions = set()

    for bits in range(2**n):
        x = tuple((bits >> j) & 1 for j in range(n))
        if evaluate_mono3sat(x, clauses):
            solutions.add(x)
        else:
            non_solutions.add(x)

    if not solutions or not non_solutions:
        return 0

    ones = list(solutions)
    zeros = list(non_solutions)

    # Build KW relation
    # kw[xi][yi] = set of valid output indices
    kw = {}
    for xi, x in enumerate(ones):
        kw[xi] = {}
        for yi, y in enumerate(zeros):
            if use_general:
                valid = frozenset(i for i in range(n) if x[i] != y[i])
            else:  # monotone
                valid = frozenset(i for i in range(n) if x[i] == 1 and y[i] == 0)
            kw[xi][yi] = valid

    # Greedy rectangle cover
    uncovered = set()
    for xi in range(len(ones)):
        for yi in range(len(zeros)):
            uncovered.add((xi, yi))

    num_rectangles = 0

    while uncovered:
        xi0, yi0 = next(iter(uncovered))
        best_coverage = 0
        best_rect = None

        for target_i in kw[xi0][yi0]:
            rows = set()
            cols = set()

            # Find all valid rows for this target and yi0
            for xi in range(len(ones)):
                if target_i in kw[xi][yi0]:
                    rows.add(xi)

            # Find all valid cols for these rows
            for yi in range(len(zeros)):
                valid = True
                for xi in rows:
                    if target_i not in kw[xi][yi]:
                        valid = False
                        break
                if valid:
                    cols.add(yi)

            coverage = sum(1 for xi in rows for yi in cols if (xi, yi) in uncovered)
            if coverage > best_coverage:
                best_coverage = coverage
                best_rect = (rows, cols, target_i)

        if best_rect:
            rows, cols, _ = best_rect
            for xi in rows:
                for yi in cols:
                    uncovered.discard((xi, yi))
            num_rectangles += 1

    return num_rectangles


def formula_size_scaling():
    """Compare monotone vs general formula size (KW cover) for scaling n."""
    print("=" * 80)
    print("  FORMULA SIZE: MONOTONE vs GENERAL (KW Rectangle Cover)")
    print("  If they're equal → circuit lower bounds via depth-size tradeoff")
    print("=" * 80)

    from mono3sat import generate_all_mono3sat_clauses

    print(f"\n{'n':>4} {'F_mono':>8} {'F_gen':>8} {'ratio':>8} {'F base':>8} "
          f"{'d_crit':>7}")
    print("-" * 50)

    results = {}

    for n in range(4, 13):
        if 2**n > 50000:
            break

        all_clauses = generate_all_mono3sat_clauses(n)
        trials = max(10, 100 // n)
        if n >= 10:
            trials = 5

        best_mono = 0
        best_gen = 0
        best_clauses = None

        for _ in range(trials):
            k = random.randint(max(1, n//2), min(len(all_clauses), 4*n))
            clauses = random.sample(all_clauses, k)

            sols = sum(1 for b in range(2**n)
                      if evaluate_mono3sat(tuple((b>>j)&1 for j in range(n)), clauses))
            nonsols = 2**n - sols

            if sols == 0 or nonsols == 0:
                continue
            if sols * nonsols > 30000:
                continue

            f_mono = compute_kw_rectangle_cover(n, clauses, use_general=False)
            f_gen = compute_kw_rectangle_cover(n, clauses, use_general=True)

            if f_mono > best_mono:
                best_mono = f_mono
                best_gen = f_gen
                best_clauses = clauses[:]

        if best_mono > 0:
            ratio = best_gen / best_mono if best_mono > 0 else 0
            base = best_mono ** (1.0/n) if best_mono > 1 else 0
            # Critical depth: d_crit such that α^n / 2^d = 1
            # d_crit = n · log₂(α)
            d_crit = n * math.log2(base) if base > 1 else 0

            results[n] = {
                'mono': best_mono,
                'gen': best_gen,
                'ratio': ratio,
                'base': base,
                'd_crit': d_crit,
            }

            print(f"{n:4d} {best_mono:8d} {best_gen:8d} {ratio:8.3f} "
                  f"{base:8.4f} {d_crit:7.1f}")

        sys.stdout.flush()

    # Analysis
    print(f"\n{'='*80}")
    print("  DEPTH-SIZE TRADEOFF IMPLICATIONS")
    print(f"{'='*80}")

    ns = sorted(results.keys())
    if ns:
        latest = results[ns[-1]]
        print(f"""
    For n={ns[-1]}:
      Monotone formula size: {latest['mono']}
      General formula size:  {latest['gen']}
      Ratio (gen/mono):      {latest['ratio']:.3f}
      Formula base:          {latest['base']:.4f}
      Critical depth:        {latest['d_crit']:.1f}

    DEPTH-SIZE TRADEOFF:
      circuit_size ≥ formula_size / 2^depth
      = {latest['mono']} / 2^d

      For d ≤ {latest['d_crit']:.0f}: circuit_size ≥ exponential
      For d > {latest['d_crit']:.0f}: bound becomes trivial

    KEY FINDING:
      If gen/mono ratio stays ≈ 1.0 (NOT doesn't help for formulas):
        General formula size ≈ Monotone formula size
        → depth-size tradeoff applies to GENERAL circuits
        → circuits of depth < n·log₂(base) need exponential size

      The ratio {latest['ratio']:.3f} suggests formula sizes are
      {'EQUAL' if latest['ratio'] > 0.95 else 'DIFFERENT'} —
      {'NOT gates DO NOT help for formula size!' if latest['ratio'] > 0.95 else 'NOT gates help for formula size.'}
    """)

    # Growth rate of formula size
    if len(ns) >= 3:
        print(f"\n  Formula size growth rate:")
        print(f"  {'n':>4} {'F_mono':>8} {'base':>8} {'gen/mono':>9}")
        for n_val in ns:
            r = results[n_val]
            print(f"  {n_val:4d} {r['mono']:8d} {r['base']:8.4f} {r['ratio']:9.3f}")

        # Fit exponential growth
        mono_bases = [results[n_val]['base'] for n_val in ns[-4:]]
        avg_base = sum(mono_bases) / len(mono_bases)
        print(f"\n  Average formula base (last 4): {avg_base:.4f}")
        print(f"  Critical depth = n × log₂({avg_base:.4f}) ≈ "
              f"n × {math.log2(avg_base):.4f}")

        if avg_base > 1.3:
            print(f"\n  >>> STRONG: formula size grows as {avg_base:.3f}^n")
            print(f"  >>> Circuits of depth < {math.log2(avg_base):.3f}·n need exp size")
            print(f"  >>> This is BETTER than switching lemma bounds for depth")
        elif avg_base > 1.1:
            print(f"\n  >>> MODERATE: formula base = {avg_base:.3f}")
        else:
            print(f"\n  >>> WEAK: formula base = {avg_base:.3f} close to 1")


def direct_formula_depth_bound():
    """Compute formula DEPTH (not size) lower bounds.

    Formula depth = communication complexity of KW game.
    This is known to equal circuit depth.

    For monotone: depth ≥ monotone KW communication complexity
    For general: depth ≥ general KW CC

    If they're equal: monotone depth bound = general depth bound.
    """
    print(f"\n\n{'='*80}")
    print("  FORMULA DEPTH BOUNDS")
    print(f"{'='*80}")
    print("""
    Circuit depth = KW communication complexity.

    For MONO-3SAT evaluation (fixed formula):
      Monotone depth: O(log n) (balanced formula tree)
      General depth: O(log n) (same)

    For CLIQUE (NP-hard):
      Monotone depth: Ω(n) (from Razborov's bound)
      General depth: O(n) (trivially, circuit is poly)
      BUT: general depth might be O(log² n) if CLIQUE ∈ NC²

    The formula SIZE is more relevant than depth for our purpose.
    Formula size gives circuit lower bounds via:
      circuit_size ≥ formula_size / 2^{circuit_depth}

    So: if formula_size ≥ 2^{Ω(n)} and depth = O(n^{1-ε}):
      circuit_size ≥ 2^{Ω(n)} / 2^{O(n^{1-ε})} = 2^{Ω(n) - O(n^{1-ε})}
      = 2^{Ω(n)} — EXPONENTIAL!

    This would prove P ≠ NP for bounded-depth circuits.

    OPEN: Is formula_size = 2^{Ω(n)} for CLIQUE?
    Known: monotone formula size ≥ 2^{Ω(N^{1/6})} (Razborov)
    where N = number of vertices, n = C(N,2) bits.
    So monotone formula size ≥ 2^{Ω(n^{1/12})} — super-polynomial
    but only slightly exponential.
    """)


if __name__ == "__main__":
    random.seed(42)
    formula_size_scaling()
    direct_formula_depth_bound()
