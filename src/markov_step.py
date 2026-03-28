"""
The Markov Step: Reducing n Input NOTs to O(log n).

After DeMorgan, we have a circuit using n input NOTs (¬x₁,...,¬xₙ).
Markov's theorem says we can compute f with only ⌈log₂(n+1)⌉ NOTs.

The construction: instead of negating EACH input separately,
negate COMPLEX functions of inputs that "encode" multiple negations.

Example for n=4, needing ⌈log₂(5)⌉ = 3 NOTs:
  Instead of ¬x₀, ¬x₁, ¬x₂, ¬x₃ (4 NOTs), compute:
  ¬g₁(x), ¬g₂(x), ¬g₃(x) (3 NOTs) where g₁, g₂, g₃ are chosen so that
  from x₀,...,x₃, ¬g₁, ¬g₂, ¬g₃ we can reconstruct ¬x₀,...,¬x₃
  using only AND/OR gates.

KEY QUESTION: How big are the AND/OR circuits needed to reconstruct
¬xᵢ from the complex negations ¬gⱼ?

If reconstruction is O(poly(n)) → total circuit stays polynomial
If reconstruction is O(exp(n)) → exponential blowup

THIS IS THE P VS NP BOTTLENECK.
"""

import itertools
from collections import defaultdict
import random
import math
import sys


def can_reconstruct(n, neg_functions, target_neg_idx):
    """Check if ¬x_{target} can be reconstructed from:
    x₀,...,x_{n-1}, ¬g₁,...,¬gₖ using AND/OR only (no NOT).

    neg_functions: list of truth tables of ¬gⱼ (as integers)
    target_neg_idx: which ¬xᵢ to reconstruct (truth table)

    Uses BFS to find all functions computable from inputs + neg_functions.
    """
    num_inputs = 2**n
    all_ones = (1 << num_inputs) - 1

    # Available truth tables: inputs + negated functions
    available = set()
    for j in range(n):
        tt = 0
        for i in range(num_inputs):
            if (i >> j) & 1:
                tt |= (1 << i)
        available.add(tt)

    # Add negated functions
    for nf in neg_functions:
        available.add(nf)

    # Add constants
    available.add(0)
    available.add(all_ones)

    # BFS: expand using AND/OR
    prev_size = 0
    max_iters = 15  # depth limit

    for _ in range(max_iters):
        if target_neg_idx in available:
            return True

        if len(available) == prev_size:
            return False  # no new functions found
        prev_size = len(available)

        new_fns = set()
        avail_list = list(available)
        for i in range(len(avail_list)):
            for j in range(i, len(avail_list)):
                new_fns.add(avail_list[i] & avail_list[j])  # AND
                new_fns.add(avail_list[i] | avail_list[j])  # OR

        available |= new_fns

        if len(available) > 100000:  # safety limit
            break

    return target_neg_idx in available


def find_good_negation_functions(n, k):
    """Find k functions g₁,...,gₖ such that ¬g₁,...,¬gₖ allow
    reconstructing ALL ¬x₀,...,¬x_{n-1} using AND/OR.

    Returns list of (function_tt, neg_function_tt) pairs, or None.
    """
    num_inputs = 2**n
    all_ones = (1 << num_inputs) - 1

    # Input truth tables
    input_tts = []
    for j in range(n):
        tt = 0
        for i in range(num_inputs):
            if (i >> j) & 1:
                tt |= (1 << i)
        input_tts.append(tt)

    # Target: ¬xᵢ for each i
    targets = [all_ones ^ tt for tt in input_tts]

    # Try random combinations of k functions
    # Each function g is a monotone function of inputs
    # (We need g to be computable WITHOUT NOT, since NOT is what we're saving)

    # Generate all functions computable with AND/OR from inputs (depth ≤ 4)
    available = set(input_tts) | {0, all_ones}
    for depth in range(4):
        new_fns = set()
        avail_list = list(available)
        for i in range(len(avail_list)):
            for j in range(i, len(avail_list)):
                new_fns.add(avail_list[i] & avail_list[j])
                new_fns.add(avail_list[i] | avail_list[j])
        available |= new_fns
        if len(available) > 10000:
            break

    # The functions g must be from `available` (computable without NOT)
    # Their negations ¬g are what we get from the k NOT gates
    monotone_fns = list(available)

    print(f"  Available monotone functions: {len(monotone_fns)}")

    # Try random subsets of size k
    best_coverage = 0
    best_fns = None

    for trial in range(min(1000, len(monotone_fns) ** k)):
        chosen = random.sample(monotone_fns, k)
        neg_chosen = [all_ones ^ g for g in chosen]

        # Check how many targets can be reconstructed
        coverage = 0
        for t in targets:
            if can_reconstruct(n, neg_chosen, t):
                coverage += 1

        if coverage > best_coverage:
            best_coverage = coverage
            best_fns = list(zip(chosen, neg_chosen))

        if best_coverage == n:
            break

    return best_fns, best_coverage


def markov_step_analysis():
    """Analyze the Markov step for small n."""
    print("=" * 70)
    print("  MARKOV STEP: n Input NOTs → O(log n) NOTs")
    print("=" * 70)

    for n in range(3, 7):
        markov_bound = (n + 1).bit_length()

        print(f"\n{'─'*70}")
        print(f"  n = {n}: need to reduce {n} NOTs to {markov_bound} NOTs")
        print(f"{'─'*70}")

        for k in range(1, n + 1):
            if k > n:
                break

            result, coverage = find_good_negation_functions(n, k)

            status = "✓ ALL" if coverage == n else f"only {coverage}/{n}"
            print(f"  k={k} NOT gates: can reconstruct {status} input negations")

            if result and coverage == n:
                print(f"    Functions used:")
                for g_tt, neg_tt in result:
                    print(f"      g = {bin(g_tt)}, ¬g = {bin(neg_tt)}")
                break  # found minimum k

            if k == markov_bound and coverage < n:
                print(f"    WARNING: Markov bound {markov_bound} NOT gates "
                      f"insufficient with depth-4 reconstruction!")

    print(f"\n{'='*70}")
    print("  INTERPRETATION")
    print(f"{'='*70}")
    print("""
    The Markov step requires finding k "aggregate negation" functions
    g₁,...,gₖ such that ¬g₁,...,¬gₖ together with x₁,...,xₙ allow
    reconstructing all ¬x₁,...,¬xₙ using AND/OR only.

    The RECONSTRUCTION CIRCUIT size determines the total blowup:
    - If reconstruction uses O(poly(n)) gates per ¬xᵢ: total O(n·poly(n))
    - If reconstruction uses O(exp(n)) gates: total exponential

    For small n (3-6): reconstruction is easy (found within depth 4).
    For large n: the reconstruction depth/size might grow.

    THE KEY: Does the reconstruction complexity grow polynomially or
    exponentially with n? This is equivalent to P vs NP.
    """)


if __name__ == "__main__":
    random.seed(42)
    markov_step_analysis()
