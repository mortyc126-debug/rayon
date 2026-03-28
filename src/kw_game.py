"""
Karchmer-Wigderson Game Analysis for Circuit Lower Bounds.

The KW game for f: {0,1}^n → {0,1}:
  - Alice gets x ∈ f⁻¹(1) (a solution)
  - Bob gets y ∈ f⁻¹(0) (a non-solution)
  - Goal: find index i where x_i ≠ y_i
  - D(KW_f) = circuit depth(f)
  - Protocol partition into rectangles ↔ circuit structure

For SIZE (not depth), we need the number of LEAVES in the KW protocol tree.
This equals the circuit size for FORMULAS (fan-out 1 circuits).

KEY INSIGHT: For monotone f, Alice always outputs i with x_i=1, y_i=0.
Adding NOT gates = allowing Alice/Bob to swap "perspective".
Each NOT corresponds to a role swap in the communication game.

Our approach:
1. Compute the KW matrix M[x,y] = {i : x_i ≠ y_i} for MONO-3SAT
2. Find minimum rectangle partition (= formula size)
3. Analyze how NOT gates reduce the partition size
4. Look for structural constraints that limit NOT gate benefit

This is NOT blocked by natural proofs because:
- KW analysis depends on the SPECIFIC function structure
- It's not a "largeness" condition on functions
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


def compute_kw_matrix(n, clauses):
    """Compute the KW relation matrix.

    Returns:
      ones: list of solutions (f(x)=1)
      zeros: list of non-solutions (f(x)=0)
      kw[x_idx][y_idx]: set of indices i where x_i ≠ y_i
    """
    ones = []
    zeros = []

    for bits in range(2**n):
        assignment = tuple((bits >> i) & 1 for i in range(n))
        if evaluate_mono3sat(assignment, clauses):
            ones.append(assignment)
        else:
            zeros.append(assignment)

    # KW matrix: for each (x, y), the valid outputs
    # For monotone, valid = {i : x_i=1, y_i=0}
    # For general, valid = {i : x_i ≠ y_i}

    kw_mono = {}  # Monotone KW
    kw_gen = {}   # General KW

    for xi, x in enumerate(ones):
        kw_mono[xi] = {}
        kw_gen[xi] = {}
        for yi, y in enumerate(zeros):
            mono_diff = frozenset(i for i in range(n) if x[i] == 1 and y[i] == 0)
            gen_diff = frozenset(i for i in range(n) if x[i] != y[i])
            kw_mono[xi][yi] = mono_diff
            kw_gen[xi][yi] = gen_diff

    return ones, zeros, kw_mono, kw_gen


def is_monochromatic_rectangle(rows, cols, kw, target_i):
    """Check if a rectangle can be labeled with index target_i.
    A rectangle R×C is valid for label i if:
      for all x in R, y in C: i ∈ kw[x][y]
    """
    for xi in rows:
        for yi in cols:
            if target_i not in kw[xi][yi]:
                return False
    return True


def greedy_rectangle_cover(ones, zeros, kw, n):
    """Find a rectangle cover of the KW matrix.

    Each rectangle (R, C, i) means: when Alice has x ∈ R and Bob has y ∈ C,
    output index i. We need to cover all (x, y) pairs.

    Returns the number of rectangles (= formula size lower bound).
    """
    num_ones = len(ones)
    num_zeros = len(zeros)

    uncovered = set()
    for xi in range(num_ones):
        for yi in range(num_zeros):
            uncovered.add((xi, yi))

    rectangles = []

    while uncovered:
        best_rect = None
        best_size = 0

        # Pick an uncovered pair
        xi0, yi0 = next(iter(uncovered))

        # Try each valid index for this pair
        for target_i in kw[xi0][yi0]:
            # Grow rectangle greedily
            rows = {xi0}
            cols = {yi0}

            # Add all valid rows
            for xi in range(num_ones):
                if xi in rows:
                    continue
                # Check if xi is compatible with all current cols
                valid = True
                for yi in cols:
                    if target_i not in kw[xi][yi]:
                        valid = False
                        break
                if valid:
                    rows.add(xi)

            # Add all valid cols
            for yi in range(num_zeros):
                if yi in cols:
                    continue
                valid = True
                for xi in rows:
                    if target_i not in kw[xi][yi]:
                        valid = False
                        break
                if valid:
                    cols.add(yi)

            coverage = sum(1 for xi in rows for yi in cols if (xi, yi) in uncovered)
            if coverage > best_size:
                best_size = coverage
                best_rect = (frozenset(rows), frozenset(cols), target_i)

        if best_rect:
            rows, cols, idx = best_rect
            for xi in rows:
                for yi in cols:
                    uncovered.discard((xi, yi))
            rectangles.append(best_rect)

    return len(rectangles), rectangles


def analyze_kw_structure(n, clauses):
    """Analyze KW matrix structure for a MONO-3SAT instance."""
    ones, zeros, kw_mono, kw_gen = compute_kw_matrix(n, clauses)

    print(f"\nKW Analysis (n={n}, |1|={len(ones)}, |0|={len(zeros)})")
    print(f"  Matrix size: {len(ones)} × {len(zeros)} = {len(ones)*len(zeros)} entries")

    if len(ones) * len(zeros) > 100000:
        print("  Too large for rectangle cover analysis")
        return

    # 1. Distribution of valid output sets
    set_sizes_mono = []
    set_sizes_gen = []

    for xi in kw_mono:
        for yi in kw_mono[xi]:
            set_sizes_mono.append(len(kw_mono[xi][yi]))
            set_sizes_gen.append(len(kw_gen[xi][yi]))

    avg_mono = sum(set_sizes_mono) / len(set_sizes_mono) if set_sizes_mono else 0
    avg_gen = sum(set_sizes_gen) / len(set_sizes_gen) if set_sizes_gen else 0
    min_mono = min(set_sizes_mono) if set_sizes_mono else 0

    print(f"\n  Valid output set sizes:")
    print(f"    Monotone: avg={avg_mono:.2f}, min={min_mono}")
    print(f"    General:  avg={avg_gen:.2f}, min={min(set_sizes_gen) if set_sizes_gen else 0}")
    print(f"    Ratio gen/mono: {avg_gen/avg_mono:.2f}" if avg_mono > 0 else "")

    # 2. Rectangle cover (formula size)
    num_rect_mono, rects_mono = greedy_rectangle_cover(ones, zeros, kw_mono, n)
    num_rect_gen, rects_gen = greedy_rectangle_cover(ones, zeros, kw_gen, n)

    print(f"\n  Rectangle cover (formula size lower bound):")
    print(f"    Monotone: {num_rect_mono} rectangles")
    print(f"    General:  {num_rect_gen} rectangles")
    print(f"    NOT benefit: {num_rect_mono - num_rect_gen} "
          f"({(num_rect_mono-num_rect_gen)/num_rect_mono*100:.1f}%)")

    # 3. Per-index analysis: for each output index i,
    #    what is the maximum rectangle using i?
    print(f"\n  Per-index max rectangle (monotone):")
    for i in range(n):
        # Count how many entries can use index i
        count = sum(1 for xi in kw_mono for yi in kw_mono[xi] if i in kw_mono[xi][yi])
        total = len(ones) * len(zeros)
        print(f"    Index {i}: {count}/{total} entries ({count/total*100:.1f}%)")

    # 4. Analyze rectangle sizes
    mono_sizes = [len(r) * len(c) for r, c, _ in rects_mono]
    gen_sizes = [len(r) * len(c) for r, c, _ in rects_gen]

    print(f"\n  Rectangle size distribution:")
    print(f"    Monotone: max={max(mono_sizes)}, avg={sum(mono_sizes)/len(mono_sizes):.1f}")
    print(f"    General:  max={max(gen_sizes)}, avg={sum(gen_sizes)/len(gen_sizes):.1f}")

    return {
        'mono_rects': num_rect_mono,
        'gen_rects': num_rect_gen,
        'not_benefit': num_rect_mono - num_rect_gen,
        'avg_mono_set': avg_mono,
        'avg_gen_set': avg_gen,
    }


def kw_scaling_analysis():
    """Analyze how KW rectangle cover scales with n."""
    print("=" * 80)
    print("  KARCHMER-WIGDERSON SCALING ANALYSIS")
    print("  Formula size = min rectangle cover of KW matrix")
    print("=" * 80)

    from mono3sat import generate_all_mono3sat_clauses

    results = {}

    for n in range(3, 13):
        all_clauses = generate_all_mono3sat_clauses(n)

        best_result = None
        best_benefit = 0

        trials = max(20, 100 // n)
        if n >= 9:
            trials = 10
        if n >= 11:
            trials = 5

        for _ in range(trials):
            k = random.randint(max(1, n//2), min(len(all_clauses), 4*n))
            clauses = random.sample(all_clauses, k)

            # Quick check for non-trivial instance
            ones_count = 0
            zeros_count = 0
            for bits in range(2**n):
                assignment = tuple((bits >> i) & 1 for i in range(n))
                if evaluate_mono3sat(assignment, clauses):
                    ones_count += 1
                else:
                    zeros_count += 1

            if ones_count == 0 or zeros_count == 0:
                continue
            if ones_count * zeros_count > 50000:
                continue

            result = analyze_kw_structure(n, clauses)
            if result and result['not_benefit'] > best_benefit:
                best_benefit = result['not_benefit']
                best_result = result

        if best_result:
            results[n] = best_result

    # Summary
    print(f"\n{'='*80}")
    print("  SCALING SUMMARY")
    print(f"{'='*80}")
    print(f"{'n':>4} {'Mono rects':>12} {'Gen rects':>12} {'NOT benefit':>12} {'Benefit %':>10}")
    for n in sorted(results.keys()):
        r = results[n]
        pct = r['not_benefit'] / r['mono_rects'] * 100 if r['mono_rects'] > 0 else 0
        print(f"{n:4d} {r['mono_rects']:12d} {r['gen_rects']:12d} "
              f"{r['not_benefit']:12d} {pct:10.1f}%")

    return results


def analyze_critical_pairs(n, clauses):
    """Find critical pairs in the KW game that are hardest to cover.

    A pair (x, y) is "critical" if the valid output set kw[x][y] is small.
    These pairs FORCE specific rectangles and constrain the cover.

    If these critical pairs have specific SAT-structure, we can exploit it
    to prove lower bounds that are NOT natural proofs.
    """
    ones, zeros, kw_mono, kw_gen = compute_kw_matrix(n, clauses)

    print(f"\nCritical pair analysis (n={n}):")

    # Find pairs with minimal valid output set
    critical = []
    for xi in kw_mono:
        for yi in kw_mono[xi]:
            size = len(kw_mono[xi][yi])
            if size <= 2:  # very constrained
                critical.append((xi, yi, kw_mono[xi][yi], ones[xi], zeros[yi]))

    print(f"  Critical pairs (|valid output| ≤ 2): {len(critical)}")
    print(f"  Total pairs: {len(ones)*len(zeros)}")

    if critical:
        # Analyze structure of critical pairs
        print(f"\n  Sample critical pairs:")
        for xi, yi, valid, x, y in critical[:10]:
            hamming = sum(a != b for a, b in zip(x, y))
            mono_diff = sum(1 for a, b in zip(x, y) if a == 1 and b == 0)
            print(f"    x={x}, y={y}, valid={valid}, "
                  f"hamming={hamming}, mono_diff={mono_diff}")

        # Key question: are critical pairs "local" (small Hamming distance)?
        distances = [sum(a != b for a, b in zip(c[3], c[4])) for c in critical]
        avg_dist = sum(distances) / len(distances)
        print(f"\n  Avg Hamming distance of critical pairs: {avg_dist:.2f}")
        print(f"  Expected for random: {n/2:.2f}")

        if avg_dist < n / 3:
            print("  >>> Critical pairs are LOCAL — SAT structure creates clusters")
            print("  >>> This locality could be exploited for non-natural lower bounds")
        else:
            print("  >>> Critical pairs are spread out — generic structure")

    # Analyze the "hardness" distribution
    hardness = defaultdict(int)
    for xi in kw_mono:
        for yi in kw_mono[xi]:
            hardness[len(kw_mono[xi][yi])] += 1

    print(f"\n  KW hardness distribution (size of valid output set):")
    for k in sorted(hardness.keys()):
        print(f"    |valid| = {k}: {hardness[k]} pairs")


def analyze_clause_constraint_propagation(n, clauses):
    """Analyze how SAT clause structure constrains the KW game.

    For MONO-3SAT with clause (i,j,k):
    If y[i]=y[j]=y[k]=0 (clause unsatisfied in y),
    then x must have at least one of x[i],x[j],x[k]=1.
    This means at least one of i,j,k is a valid KW output.

    This creates a HYPERGRAPH structure on the valid outputs:
    each unsatisfied clause in y forces a "choice" from 3 indices.

    The key insight: the number of distinct "choice patterns"
    over all unsatisfied clauses determines the rectangle complexity.
    """
    ones, zeros, kw_mono, _ = compute_kw_matrix(n, clauses)

    print(f"\nClause-constraint analysis (n={n}, {len(clauses)} clauses):")

    # For each zero assignment y, find which clauses are unsatisfied
    for yi, y in enumerate(zeros[:5]):  # sample
        unsat_clauses = []
        for clause in clauses:
            if not any(y[v] for v in clause):
                unsat_clauses.append(clause)

        print(f"\n  y={y}: {len(unsat_clauses)} unsatisfied clauses")

        # The forced choices: for each unsat clause, x must have ≥1 variable set
        # This creates an "OR constraint" on valid KW outputs
        for clause in unsat_clauses[:3]:
            # Which of the clause variables are actually set in solutions?
            choosers = defaultdict(int)
            for xi, x in enumerate(ones):
                for v in clause:
                    if x[v] == 1 and y[v] == 0:
                        choosers[v] += 1

            choices_str = ", ".join(f"x_{v}({choosers[v]})" for v in clause)
            print(f"    Clause {clause}: choices = {choices_str}")


if __name__ == "__main__":
    random.seed(42)

    # Phase 1: Scaling analysis
    results = kw_scaling_analysis()

    # Phase 2: Critical pair and clause analysis for interesting instances
    print(f"\n\n{'='*80}")
    print("  CRITICAL PAIR AND CLAUSE STRUCTURE ANALYSIS")
    print(f"{'='*80}")

    from mono3sat import generate_all_mono3sat_clauses

    for n in [5, 6, 7]:
        all_clauses = generate_all_mono3sat_clauses(n)
        for _ in range(20):
            k = random.randint(n, min(len(all_clauses), 3*n))
            clauses = random.sample(all_clauses, k)

            ones_count = sum(1 for bits in range(2**n)
                           if evaluate_mono3sat(tuple((bits>>i)&1 for i in range(n)), clauses))
            zeros_count = 2**n - ones_count

            if 0 < ones_count < 2**n and ones_count * zeros_count < 10000:
                analyze_critical_pairs(n, clauses)
                analyze_clause_constraint_propagation(n, clauses)
                break
