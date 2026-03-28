"""
ITERATIVE Φ-DECOMPOSITION: A potential polynomial algorithm.

IDEA: At each step, find the intermediate g that maximally reduces Φ.
Condition on g. Repeat. If Φ → 0 in O(log Φ) steps → polynomial!

From our data:
  - Best intermediate explains ~85% of Φ
  - If this holds at each step: Φ_k = (1-0.85)^k × Φ_0 = 0.15^k × Φ_0
  - For Φ_k < 1: k > log(Φ_0) / log(1/0.15) ≈ log(Φ_0) / 1.9
  - For Φ_0 ~ n^10: k ≈ 10 log(n) / 1.9 ≈ 5 log(n) steps
  - Each step: polynomial (find best g, condition)
  - TOTAL: O(log n) × poly(n) = POLYNOMIAL!

But: does the 85% reduction hold at EVERY step?
Or does it degrade after a few steps?

THIS IS THE CRITICAL TEST.

If reduction stays ≥ 50% → converges in O(log Φ) steps → P = NP direction
If reduction drops to 0% → gets stuck → P ≠ NP direction
"""

import itertools
from collections import defaultdict
import random
import math
import sys


def compute_phi(n, tt, active_inputs, num_trials=150):
    """Compute Φ restricted to active_inputs."""
    if len(active_inputs) <= 1:
        return 0

    active_set = set(active_inputs)
    boundary = []
    for bits in active_inputs:
        for j in range(n):
            nb = bits ^ (1 << j)
            if nb in active_set and bits < nb and tt[bits] != tt[nb]:
                boundary.append((bits, nb))

    if not boundary:
        return 0

    best = 0
    for _ in range(num_trials):
        k = random.randint(1, min(n-1, 6))
        coords = random.sample(range(n), k)
        block_of = {}
        sigs_dict = defaultdict(list)
        for bits in active_inputs:
            bid = sum((1 << ci) for ci, c in enumerate(coords) if (bits >> c) & 1)
            block_of[bits] = bid
            sigs_dict[bid].append(tt[bits])
        cross = sum(1 for b1, b2 in boundary if block_of[b1] != block_of[b2])
        sigs = set(tuple(v) for v in sigs_dict.values())
        cons = max(1, cross)
        comp = max(1, len(sigs))
        depth = max(1, int(math.ceil(math.log2(max(2, comp)))))
        best = max(best, cons * comp * depth)
    return best


def find_best_split(n, tt, active_inputs):
    """Find the Boolean function g that maximally reduces Φ when conditioned.

    Try splits: single variables, pairs, thresholds.
    Return the split and the resulting Φ reduction.
    """
    active_set = set(active_inputs)
    phi_total = compute_phi(n, tt, active_inputs)

    if phi_total == 0:
        return None, 0, phi_total

    best_reduction = 0
    best_split_name = ""
    best_parts = None

    # Try single variable splits
    for j in range(n):
        part0 = [b for b in active_inputs if not (b >> j) & 1]
        part1 = [b for b in active_inputs if (b >> j) & 1]

        if not part0 or not part1:
            continue

        phi0 = compute_phi(n, tt, part0, 80)
        phi1 = compute_phi(n, tt, part1, 80)
        phi_after = max(phi0, phi1)
        reduction = phi_total - phi_after

        if reduction > best_reduction:
            best_reduction = reduction
            best_split_name = f"x_{j}"
            best_parts = (part0, part1)

    # Try threshold on sum of variables
    for thresh in range(1, n):
        part0 = [b for b in active_inputs if bin(b).count('1') < thresh]
        part1 = [b for b in active_inputs if bin(b).count('1') >= thresh]

        if not part0 or not part1:
            continue

        phi0 = compute_phi(n, tt, part0, 80)
        phi1 = compute_phi(n, tt, part1, 80)
        phi_after = max(phi0, phi1)
        reduction = phi_total - phi_after

        if reduction > best_reduction:
            best_reduction = reduction
            best_split_name = f"weight≥{thresh}"
            best_parts = (part0, part1)

    # Try AND of two variables
    for i in range(min(n, 8)):
        for j in range(i+1, min(n, 8)):
            part0 = [b for b in active_inputs if not ((b >> i) & 1 and (b >> j) & 1)]
            part1 = [b for b in active_inputs if (b >> i) & 1 and (b >> j) & 1]

            if not part0 or not part1:
                continue

            phi0 = compute_phi(n, tt, part0, 60)
            phi1 = compute_phi(n, tt, part1, 60)
            phi_after = max(phi0, phi1)
            reduction = phi_total - phi_after

            if reduction > best_reduction:
                best_reduction = reduction
                best_split_name = f"x_{i}∧x_{j}"
                best_parts = (part0, part1)

    pct = best_reduction / phi_total * 100 if phi_total > 0 else 0
    return best_split_name, best_reduction, phi_total, best_parts, pct


def iterative_decomposition(n, tt, name, max_steps=20):
    """Iteratively decompose f by conditioning on best intermediates."""
    print(f"\n{'='*60}")
    print(f"  ITERATIVE Φ-DECOMPOSITION: {name}")
    print(f"{'='*60}")

    all_inputs = list(range(2**n))
    phi_initial = compute_phi(n, tt, all_inputs, 200)

    print(f"  n = {n}, initial Φ = {phi_initial}")
    print(f"\n  {'Step':>4} {'Split':<15} {'Φ_before':>10} {'Φ_after':>10} "
          f"{'Reduction':>10} {'Red%':>7} {'Cumul%':>8}")
    print("  " + "-" * 65)

    # Track the HARDEST remaining sub-problem
    current_inputs = all_inputs
    current_phi = phi_initial
    cumulative_reduction = 0

    reductions = []

    for step in range(max_steps):
        if current_phi <= 0 or len(current_inputs) <= 1:
            print(f"  CONVERGED at step {step}! Φ = {current_phi}")
            break

        result = find_best_split(n, tt, current_inputs)
        if result[0] is None:
            print(f"  NO SPLIT FOUND at step {step}")
            break

        split_name, reduction, phi_before, parts, pct = result

        # Take the HARDER partition (higher Φ)
        phi0 = compute_phi(n, tt, parts[0], 80)
        phi1 = compute_phi(n, tt, parts[1], 80)

        if phi0 >= phi1:
            current_inputs = parts[0]
            current_phi = phi0
        else:
            current_inputs = parts[1]
            current_phi = phi1

        cumulative_reduction = (1 - current_phi / phi_initial) * 100

        reductions.append(pct)

        print(f"  {step:4d} {split_name:<15} {phi_before:>10} {current_phi:>10} "
              f"{reduction:>+10} {pct:>6.1f}% {cumulative_reduction:>7.1f}%")

        if current_phi <= phi_initial * 0.01:
            print(f"  99% REDUCTION ACHIEVED at step {step + 1}!")
            break

    print(f"\n  Final: Φ = {current_phi} ({current_phi/phi_initial*100:.2f}% remaining)")
    print(f"  Steps taken: {len(reductions)}")
    if reductions:
        print(f"  Avg reduction per step: {sum(reductions)/len(reductions):.1f}%")
        print(f"  Min reduction: {min(reductions):.1f}%")

    return reductions, phi_initial, current_phi


def main():
    random.seed(42)
    print("=" * 60)
    print("  P = NP ATTEMPT: Iterative Φ-Decomposition Algorithm")
    print("  If Φ → 0 in O(log n) steps → POLYNOMIAL ALGORITHM")
    print("=" * 60)

    # Test 1: Triangle K5
    N = 5
    n = N*(N-1)//2
    edge_idx = {}; idx = 0
    for i in range(N):
        for j in range(i+1, N):
            edge_idx[(i,j)] = idx; edge_idx[(j,i)] = idx; idx += 1
    tt = {}
    for bits in range(2**n):
        x = tuple((bits >> j) & 1 for j in range(n))
        has = any(x[edge_idx[(i,j)]] and x[edge_idx[(i,k)]] and x[edge_idx[(j,k)]]
                  for i in range(N) for j in range(i+1,N) for k in range(j+1,N))
        tt[bits] = 1 if has else 0
    r1, _, _ = iterative_decomposition(n, tt, "Triangle K5")

    # Test 2: MONO-3SAT
    from mono3sat import generate_all_mono3sat_clauses
    for n_val in [7, 8, 9]:
        if 2**n_val > 100000:
            break
        all_cl = generate_all_mono3sat_clauses(n_val)
        clauses = random.sample(all_cl, min(len(all_cl), 3*n_val))
        tt_msat = {}
        for bits in range(2**n_val):
            x = tuple((bits >> j) & 1 for j in range(n_val))
            tt_msat[bits] = 1 if all(any(x[v] for v in c) for c in clauses) else 0
        iterative_decomposition(n_val, tt_msat, f"MSAT n={n_val}")
        sys.stdout.flush()

    # Test 3: MAJ
    for n_val in [8, 10]:
        if 2**n_val > 100000:
            break
        tt_maj = {b: 1 if bin(b).count('1') > n_val/2 else 0 for b in range(2**n_val)}
        iterative_decomposition(n_val, tt_maj, f"MAJ n={n_val}")
        sys.stdout.flush()

    # Analysis
    print(f"\n\n{'='*60}")
    print("  VERDICT")
    print(f"{'='*60}")
    print("""
    If reduction per step stays ≥ 50% for ALL functions:
      → Φ halves each step
      → Converges in O(log Φ) = O(n log n) steps
      → Each step: polynomial (try all variable splits)
      → TOTAL: polynomial → direction toward P = NP

    If reduction drops below 50% and stalls:
      → Algorithm gets stuck
      → Exponentially many steps needed
      → Direction toward P ≠ NP

    The CRITICAL OBSERVATION: does the reduction rate SUSTAIN
    across steps, or does it degrade?
    """)


if __name__ == "__main__":
    main()
