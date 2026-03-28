"""
Width-Depth-NOT Tradeoff: A Path to Super-Linear Circuit Lower Bounds.

MODEL: Layered circuit with cuts.

A "cut" at depth d partitions the circuit into:
  - Bottom (depth < d): reads inputs, produces w(d) wires
  - Top (depth ≥ d): reads w(d) wires, produces output

The w(d) wires carry at most 2^{w(d)} distinct states.

MONOTONE CONSTRAINT:
For a monotone function f, if the bottom is monotone (no NOT),
then the w(d) wires carry MONOTONE functions of the input.
The number of distinct monotone states is at most D(w) (Dedekind number),
which is MUCH less than 2^{2^w} for small w.

NOT-AUGMENTED CONSTRAINT:
If the bottom has k NOT gates, the wires carry functions that are
"k-close to monotone". The number of distinct states is at most
D(w) × 2^k (roughly: k NOT gates add k bits of non-monotone info).

BOUNDARY SEPARATION REQUIREMENT:
For f to be computed correctly, the cut must SEPARATE all boundary
pairs (x_b, x_b⁺). Two inputs in the same state get the same output,
so x_b and x_b⁺ must be in different states.

THEOREM ATTEMPT:
For a monotone f with anti-chain boundary of size A in the poset:
  Any circuit with width w at some cut and k NOT gates below the cut
  must satisfy: D(w) × 2^k ≥ A.

For A ≥ α^n (from our experiments, α ≈ 1.6 for anti-chain):
  D(w) × 2^k ≥ 1.6^n

Since D(w) ≈ 2^{C(w, w/2)} ≈ 2^{2^w / √w}:
  2^{C(w,w/2) + k} ≥ 1.6^n
  C(w, w/2) + k ≥ n log₂(1.6) ≈ 0.678n

This is a REAL tradeoff between width and NOT count!

For k = 0 (monotone): C(w, w/2) ≥ 0.678n → w ≥ Ω(log n)
  (since C(w,w/2) ≈ 2^w/√w, need 2^w/√w ≥ 0.678n → w ≥ log₂(n))
  This gives: width ≥ Ω(log n) at every cut. Trivial.

For w = O(1) (bounded width): k ≥ 0.678n
  This gives: Ω(n) NOT gates needed. Non-trivial if combined with size!

For w = √n: C(√n, √n/2) ≈ 2^√n / n^{1/4} >> n, so k can be 0.
  The constraint is satisfied. Not useful.

REFINED APPROACH: Use the EXACT structure of the boundary, not just size.

For MONOTONE cuts: the wires must separate the anti-chain in a
MONOTONE way. This means: if x ≤ y (component-wise), then the
state of x must be ≤ state of y (component-wise on the w wires).

The maximum anti-chain separable by w monotone wires is C(w, w/2)
(by the Dilworth/Sperner bound). If the function's anti-chain is
larger than C(w, w/2), the cut is too narrow.

For our functions: anti-chain ≈ 1.6^n.
C(w, w/2) ≥ 1.6^n → w ≥ Ω(n / log n) (by Stirling).

This gives WIDTH ≥ Ω(n / log n) for MONOTONE cuts!

For EVERY cut in a monotone circuit: width ≥ Ω(n / log n).
Size = Σ width(d) ≥ depth × Ω(n / log n).

If depth ≥ Ω(log n) (from standard depth lower bounds):
  Size ≥ Ω(n) — still trivial.

If depth ≥ Ω(n): Size ≥ Ω(n² / log n) — SUPER-LINEAR!

But depth can be O(log n) for P functions. So this doesn't help.

HOWEVER: if we can show that the depth must be large (for specific
functions), combined with the width bound, we get super-linear size.

THE NOT-GATE INTERACTION:
Each NOT gate at a cut adds 1 bit of non-monotone information.
With k NOT gates at the cut: the constraint becomes:
  C(w, w/2) × 2^k ≥ 1.6^n

For the MINIMUM cut (narrowest): if w_min is the narrowest width:
  C(w_min, w_min/2) × 2^{k_total} ≥ 1.6^n
  (k_total = all NOT gates in the circuit, since they all contribute
   at some cut)

This gives: C(w_min, w_min/2) ≥ 1.6^n / 2^{k_total}

For k_total ≤ circuit size s:
  C(w_min, w_min/2) ≥ 1.6^n / 2^s

If s = O(n^c): 1.6^n / 2^{n^c} = (1.6/2^{n^{c-1}})^n → 0 for c > 1.
If s = O(n): 1.6^n / 2^{cn} = (1.6/2^c)^n. For c ≥ log₂(1.6) ≈ 0.678:
  This → 0. So the constraint is satisfied for s ≥ 0.678n. TRIVIAL.

CONCLUSION: The basic width-NOT tradeoff gives only s ≥ 0.678n.

WE NEED A STRONGER ARGUMENT that exploits the CUT STRUCTURE.
"""

import itertools
from collections import defaultdict
import random
import math
import sys


def dedekind_approx(w):
    """Approximate Dedekind number D(w) = number of monotone Boolean
    functions on w variables = number of antichains of {0,1}^w."""
    if w <= 0:
        return 2
    # Known exact values
    exact = {0: 2, 1: 3, 2: 6, 3: 20, 4: 168, 5: 7581, 6: 7828354,
             7: 2414682040998, 8: 56130437228687557907788}
    if w in exact:
        return exact[w]
    # Approximation: D(w) ≈ 2^{C(w, w//2)}
    from math import comb
    return 2 ** comb(w, w // 2)


def sperner_bound(w):
    """Maximum antichain size in {0,1}^w = C(w, w//2)."""
    from math import comb
    return comb(w, w // 2)


def compute_monotone_boundary_antichain(n, clauses):
    """Compute the monotone anti-chain in the boundary.

    For a monotone function f, the boundary anti-chain consists of
    MAXIMAL non-solutions (elements of ∂f that are incomparable
    under the component-wise order).
    """
    solutions = set()
    for bits in range(2**n):
        x = tuple((bits >> j) & 1 for j in range(n))
        sat = True
        for clause in clauses:
            if not any(x[v] for v in clause):
                sat = False
                break
        if sat:
            solutions.add(bits)

    # Find boundary: non-solutions adjacent to a solution
    boundary = set()
    for bits in range(2**n):
        if bits in solutions:
            continue
        x = tuple((bits >> j) & 1 for j in range(n))
        for j in range(n):
            if not (bits & (1 << j)):
                flipped = bits | (1 << j)
                if flipped in solutions:
                    boundary.add(bits)
                    break

    # Extract maximal antichain from boundary
    # (greedy: sort by weight, add if incomparable with all current)
    boundary_list = sorted(boundary, key=lambda b: bin(b).count('1'))
    antichain = []

    for b in boundary_list:
        compatible = True
        for a in antichain:
            # Check comparability: a ≤ b iff (a & b) == a
            if (a & b) == a or (a & b) == b:
                compatible = False
                break
        if compatible:
            antichain.append(b)

    return len(boundary), len(antichain), len(solutions)


def width_not_tradeoff_analysis():
    """Compute the width-NOT tradeoff for specific functions."""
    print("=" * 80)
    print("  WIDTH-DEPTH-NOT TRADEOFF ANALYSIS")
    print("=" * 80)

    from mono3sat import generate_all_mono3sat_clauses

    print(f"\n{'n':>4} {'|∂f|':>8} {'antichain':>10} {'AC base':>8} "
          f"{'w_mono':>7} {'w_general':>9} {'Sperner':>8}")
    print("-" * 65)

    for n in range(4, 18):
        if 2**n > 500000:
            break

        all_clauses = generate_all_mono3sat_clauses(n)
        trials = max(20, 200 // n)
        if n >= 12:
            trials = 10

        best_ac = 0
        best_boundary = 0

        for _ in range(trials):
            k = random.randint(max(1, n//2), min(len(all_clauses), 4*n))
            clauses = random.sample(all_clauses, k)
            b_size, ac_size, sol_size = compute_monotone_boundary_antichain(n, clauses)
            if ac_size > best_ac:
                best_ac = ac_size
                best_boundary = b_size

        if best_ac <= 1:
            continue

        ac_base = best_ac ** (1.0/n)
        log_ac = math.log2(best_ac)

        # Minimum width for monotone cut: Sperner bound
        # Need C(w, w/2) ≥ antichain → find minimum w
        w_mono = 1
        while sperner_bound(w_mono) < best_ac:
            w_mono += 1

        # Minimum width for general cut (with unlimited NOT)
        # Need 2^w ≥ boundary → w = log₂(boundary)
        w_general = max(1, int(math.ceil(math.log2(best_boundary + 1))))

        sperner_w = sperner_bound(w_mono)

        print(f"{n:4d} {best_boundary:8d} {best_ac:10d} {ac_base:8.4f} "
              f"{w_mono:7d} {w_general:9d} {sperner_w:8d}")

        sys.stdout.flush()

    print(f"""
    INTERPRETATION:

    w_mono = minimum width for a MONOTONE cut to separate the anti-chain
    w_general = minimum width for a GENERAL cut (log₂ of boundary)

    The GAP between w_mono and w_general represents the "NOT benefit":
    NOT gates effectively reduce the required width.

    For SIZE lower bounds:
    - Monotone circuits: size ≥ w_mono × depth_lower_bound
    - General circuits: size ≥ w_general × depth_lower_bound

    If w_mono >> w_general: NOT gates provide large savings → hard to transfer
    If w_mono ≈ w_general: NOT gates don't help → monotone bounds transfer
    """)


def cut_separation_analysis(n, clauses):
    """For a specific function, analyze what each cut must separate.

    A "cut" at the boundary between layers must separate:
    1. All (x_b, x_b⁺) boundary pairs (different outputs)
    2. In a monotone way (for monotone cuts)

    The minimum CUT CAPACITY determines the minimum width.
    """
    solutions = set()
    for bits in range(2**n):
        x = tuple((bits >> j) & 1 for j in range(n))
        sat = all(any(x[v] for v in c) for c in clauses)
        if sat:
            solutions.add(bits)

    # Boundary pairs: (non-solution, solution) at Hamming distance 1
    boundary_pairs = []
    for bits in range(2**n):
        if bits in solutions:
            continue
        for j in range(n):
            if not (bits & (1 << j)):
                flipped = bits | (1 << j)
                if flipped in solutions:
                    boundary_pairs.append((bits, flipped, j))

    print(f"\n  Cut separation analysis (n={n}):")
    print(f"  Boundary pairs: {len(boundary_pairs)}")
    print(f"  |solutions| = {len(solutions)}, |non-sol| = {2**n - len(solutions)}")

    # For each possible "hash function" (single wire), count how many
    # boundary pairs it separates
    # A wire computing a Boolean function g separates (x_b, x_b⁺) iff
    # g(x_b) ≠ g(x_b⁺)

    # For a monotone wire: g is monotone, so g(x_b) ≤ g(x_b⁺)
    # (since x_b ≤ x_b⁺ component-wise, with x_b having one more 0)
    # So g separates iff g(x_b)=0 and g(x_b⁺)=1

    # The maximum number of pairs a single monotone wire separates
    # is the maximum number of boundary pairs where a monotone function
    # "crosses" (0 → 1)

    # For each variable xⱼ: it's monotone, separates pairs where j is flipped
    var_separations = [0] * n
    for x_b, x_bp, j in boundary_pairs:
        var_separations[j] += 1

    print(f"\n  Separation by input variables (monotone wires):")
    max_sep = 0
    for j in range(n):
        max_sep = max(max_sep, var_separations[j])
        print(f"    x_{j}: separates {var_separations[j]} pairs")

    print(f"  Max single-variable separation: {max_sep}")
    print(f"  Total pairs: {len(boundary_pairs)}")
    print(f"  Variables needed (greedy): ", end="")

    # Greedy cover: how many monotone wires to cover all pairs?
    uncovered = set(range(len(boundary_pairs)))
    cover = []
    pair_sets = {j: set(i for i, (xb, xbp, jj) in enumerate(boundary_pairs) if jj == j)
                 for j in range(n)}

    while uncovered:
        best_var = max(range(n), key=lambda j: len(pair_sets[j] & uncovered))
        covered = pair_sets[best_var] & uncovered
        if not covered:
            break
        uncovered -= covered
        cover.append((best_var, len(covered)))

    print(f"{len(cover)} variables")

    # Now: can non-monotone wires do better?
    # A non-monotone wire (using NOT) can separate pairs where
    # g(x_b) ≠ g(x_b⁺) in EITHER direction (0→1 or 1→0)

    # The key question: how much better is non-monotone separation?
    # For a NOT-wire ¬xⱼ: it separates the SAME pairs as xⱼ (just reversed)
    # For a complex non-monotone wire: might separate DIFFERENT pairs

    # Example: g = x₀ XOR x₁ is non-monotone.
    # It separates (x_b, x_b⁺) where flipping bit j changes the XOR.
    # This happens for ALL flips of x₀ or x₁, regardless of other bits.

    # So non-monotone wires can potentially separate MORE pairs
    # (by being sensitive to more variables)

    # The SENSITIVITY of a wire = number of variables it depends on
    # Higher sensitivity → more pairs separated → fewer wires needed

    # Maximum sensitivity: n (depends on all variables)
    # Such a wire separates ALL boundary pairs (if sensitive to the flipped bit)
    # But: a single wire with sensitivity n can separate at most
    # n × 2^{n-1} / ... hmm, this is the same as before.

    # Actually: a wire with sensitivity = n separates ALL pairs where
    # the flipped bit is one of its sensitive bits. If it's sensitive to
    # all bits: it separates ALL pairs. ONE wire suffices!

    # But: one wire produces 1 bit of output. The circuit needs to
    # determine not just WHETHER f changes, but WHICH direction.
    # So one wire is not enough.

    # The minimum number of wires needed:
    # Each wire gives 1 bit. Total: w bits = 2^w possible states.
    # Need 2^w ≥ |boundary pairs| that need different outcomes.
    # The pairs where f=0 vs f=1 must be in different states.

    # So: 2^w ≥ (max number of pairs that must be separated)
    # = max antichain of "separation requirements"

    return len(boundary_pairs), len(cover)


def compute_tradeoff_curve(n, clauses):
    """Compute the width-NOT tradeoff curve for a specific function.

    For each possible number of NOT gates k:
    What is the minimum cut width w such that the cut
    can separate all boundary pairs?

    Method: for k NOT gates, the cut has k "non-monotone" wires
    and (w-k) monotone wires. The total separation capacity is:
    C(w-k, (w-k)/2) × 2^k ≥ antichain_size
    """
    _, ac_size, _ = compute_monotone_boundary_antichain(n, clauses)

    print(f"\n  Width-NOT tradeoff curve (n={n}, antichain={ac_size}):")
    print(f"  {'k NOT':>7} {'w_min':>7} {'C(w-k)':>10} {'2^k':>8} {'product':>10}")
    print(f"  {'-'*50}")

    log_ac = math.log2(ac_size) if ac_size > 0 else 0

    for k in range(0, n + 1):
        # Find minimum w such that C(w-k, (w-k)//2) × 2^k ≥ ac_size
        target = ac_size / (2**k)
        if target <= 1:
            w_min = k
        else:
            w_mono = 1
            while sperner_bound(w_mono) < target:
                w_mono += 1
            w_min = w_mono + k

        sperner_val = sperner_bound(max(0, w_min - k))
        product = sperner_val * (2**k)

        print(f"  {k:7d} {w_min:7d} {sperner_val:10d} {2**k:8d} {product:10d}")

        if w_min <= k + 1:  # trivially small
            print(f"  ... (remaining k values give w_min ≤ k+1)")
            break


def main():
    random.seed(42)

    # Phase 1: Scaling analysis
    width_not_tradeoff_analysis()

    # Phase 2: Detailed cut analysis
    print(f"\n\n{'='*80}")
    print("  PHASE 2: CUT SEPARATION DETAILS")
    print(f"{'='*80}")

    from mono3sat import generate_all_mono3sat_clauses

    for n in [6, 8, 10]:
        if 2**n > 100000:
            break

        all_clauses = generate_all_mono3sat_clauses(n)
        best_ac = 0
        best_clauses = None

        for _ in range(100):
            k = random.randint(max(1, n//2), min(len(all_clauses), 4*n))
            clauses = random.sample(all_clauses, k)
            _, ac, _ = compute_monotone_boundary_antichain(n, clauses)
            if ac > best_ac:
                best_ac = ac
                best_clauses = clauses[:]

        if best_clauses:
            cut_separation_analysis(n, best_clauses)
            compute_tradeoff_curve(n, best_clauses)


if __name__ == "__main__":
    main()
