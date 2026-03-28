"""
THE CRITICAL TEST: Does α(k) grow with clique size k?

α = exponent in distinct_subtrees ~ n^α

If α(k) → ∞: P ≠ NP (super-poly distinct subtrees for growing k)
If α(k) = O(1): P = NP possible

Test: k-CLIQUE on N vertices for k = 2, 3, 4 at same N.
"""

import itertools
from collections import defaultdict
import random
import math
import sys


def compute_phi_fast(n, tt, active, num_trials=40):
    if len(active) <= 1:
        return 0
    active_set = set(active)
    boundary = []
    for bits in active:
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
        for bits in active:
            bid = sum((1 << ci) for ci, c in enumerate(coords) if (bits >> c) & 1)
            block_of[bits] = bid
            sigs_dict[bid].append(tt[bits])
        cross = sum(1 for b1, b2 in boundary if block_of[b1] != block_of[b2])
        sigs = set(tuple(v) for v in sigs_dict.values())
        best = max(best, max(1,cross) * max(1,len(sigs)) *
                   max(1, int(math.ceil(math.log2(max(2, len(sigs)))))))
    return best


def build_tree_count(n, tt, active, depth=0, max_depth=20, memo=None):
    if memo is None:
        memo = {}
    key = tuple(sorted((b, tt[b]) for b in active))
    if key in memo:
        return memo[key]

    if len(active) <= 1 or len(set(tt[b] for b in active)) <= 1 or depth >= max_depth:
        memo[key] = (depth, 1)
        return (depth, 1)

    # Best variable split
    best_j = 0
    best_score = float('inf')
    for j in range(n):
        left = [b for b in active if not (b >> j) & 1]
        right = [b for b in active if (b >> j) & 1]
        if not left or not right:
            continue
        vl = len(set(tt[b] for b in left))
        vr = len(set(tt[b] for b in right))
        score = vl + vr  # prefer splits that make sides constant
        if score < best_score:
            best_score = score
            best_j = j

    left = [b for b in active if not (b >> best_j) & 1]
    right = [b for b in active if (b >> best_j) & 1]

    dl, ll = build_tree_count(n, tt, left, depth+1, max_depth, memo)
    dr, lr = build_tree_count(n, tt, right, depth+1, max_depth, memo)

    result = (max(dl, dr), ll + lr)
    memo[key] = result
    return result


def make_k_clique_tt(N, k):
    n = N*(N-1)//2
    edge_idx = {}; idx = 0
    for i in range(N):
        for j in range(i+1, N):
            edge_idx[(i,j)] = idx; edge_idx[(j,i)] = idx; idx += 1

    tt = {}
    for bits in range(2**n):
        x = tuple((bits >> j) & 1 for j in range(n))
        has = False
        for combo in itertools.combinations(range(N), k):
            clique = all(x[edge_idx[(combo[a], combo[b])]]
                        for a in range(len(combo)) for b in range(a+1, len(combo)))
            if clique:
                has = True
                break
        tt[bits] = 1 if has else 0
    return tt, n


def main():
    random.seed(42)
    print("=" * 70)
    print("  α(k) vs k: Does tree complexity grow with clique size?")
    print("  α(k) → ∞ ⟹ P ≠ NP")
    print("=" * 70)

    # For each N: test k = 2, 3, 4, ... (as far as feasible)
    print(f"\n  {'N':>3} {'k':>3} {'n bits':>7} {'depth':>6} {'leaves':>8} "
          f"{'distinct':>10} {'α est':>8}")
    print("  " + "-" * 55)

    # Collect data for α fitting
    data_by_k = defaultdict(list)  # k -> [(n, distinct)]

    for N in range(4, 8):
        n_bits = N*(N-1)//2
        if 2**n_bits > 200000:
            break

        for k in range(2, N+1):
            if k > N:
                break

            # Check feasibility
            num_k_cliques = math.comb(N, k)
            if num_k_cliques == 0:
                continue

            tt, n = make_k_clique_tt(N, k)

            # Check non-trivial
            ones = sum(tt[b] for b in range(2**n))
            if ones == 0 or ones == 2**n:
                print(f"  {N:3d} {k:3d} {n:>7} {'trivial':>6}")
                continue

            all_inputs = list(range(2**n))
            memo = {}
            depth, leaves = build_tree_count(n, tt, all_inputs, 0, n+2, memo)
            distinct = len(memo)

            data_by_k[k].append((n, distinct))

            # Estimate α from single point: distinct ≈ n^α → α ≈ log(distinct)/log(n)
            alpha_est = math.log(max(1, distinct)) / math.log(max(2, n))

            print(f"  {N:3d} {k:3d} {n:>7} {depth:>6} {leaves:>8} "
                  f"{distinct:>10} {alpha_est:>8.2f}")
            sys.stdout.flush()

    # Fit α for each k
    print(f"\n\n{'='*70}")
    print("  α(k) SCALING: Power law fit per k")
    print(f"{'='*70}")

    alpha_values = {}

    for k in sorted(data_by_k.keys()):
        data = data_by_k[k]
        if len(data) < 2:
            continue

        ns = [d[0] for d in data]
        ds = [d[1] for d in data]
        log_ns = [math.log(n) for n in ns]
        log_ds = [math.log(max(1, d)) for d in ds]

        m = len(log_ns)
        sx = sum(log_ns); sy = sum(log_ds)
        sxy = sum(x*y for x,y in zip(log_ns, log_ds))
        sxx = sum(x*x for x in log_ns)
        denom = m*sxx - sx*sx

        if denom != 0:
            alpha = (m*sxy - sx*sy) / denom
            alpha_values[k] = alpha
            print(f"  k={k}: α = {alpha:.2f} (from {len(data)} data points)")
        else:
            print(f"  k={k}: insufficient data")

    # THE KEY PLOT: α vs k
    print(f"\n{'='*70}")
    print("  α(k) TREND")
    print(f"{'='*70}")

    if len(alpha_values) >= 2:
        ks = sorted(alpha_values.keys())
        print(f"\n  {'k':>4} {'α(k)':>8} {'Δα':>8}")
        print("  " + "-" * 22)
        prev_alpha = None
        for k_val in ks:
            a = alpha_values[k_val]
            delta = a - prev_alpha if prev_alpha is not None else 0
            print(f"  {k_val:4d} {a:8.2f} {delta:>+8.2f}")
            prev_alpha = a

        # Fit α(k) = a + b*k
        k_list = list(ks)
        a_list = [alpha_values[k_val] for k_val in k_list]
        m = len(k_list)
        sk = sum(k_list); sa = sum(a_list)
        ska = sum(k_val*a for k_val, a in zip(k_list, a_list))
        skk = sum(k_val**2 for k_val in k_list)
        denom = m*skk - sk*sk
        if denom != 0:
            slope = (m*ska - sk*sa) / denom
            intercept = (sa - slope*sk) / m
            print(f"\n  Linear fit: α(k) ≈ {intercept:.2f} + {slope:.2f} × k")

            if slope > 0.5:
                print(f"\n  >>> α GROWS with k! Slope = {slope:.2f}")
                print(f"  >>> For k = N^{{1/3}}: α ≈ {slope:.2f} × N^{{1/3}}")
                print(f"  >>> distinct_subtrees ≈ n^{{α}} = n^{{{slope:.2f}×N^{{1/3}}}}")
                print(f"  >>> = (N²)^{{{slope:.2f}×N^{{1/3}}}} = N^{{{2*slope:.2f}×N^{{1/3}}}}")
                print(f"  >>> This is SUPER-POLYNOMIAL for any fixed polynomial!")
                print(f"  >>> ⟹ P ≠ NP (if the trend holds)")
            elif slope > 0:
                print(f"\n  >>> α grows slowly with k (slope = {slope:.2f})")
                print(f"  >>> Need more data to confirm super-polynomial growth")
            else:
                print(f"\n  >>> α does NOT grow with k (slope = {slope:.2f})")
                print(f"  >>> No evidence for P ≠ NP from this measure")


if __name__ == "__main__":
    main()
