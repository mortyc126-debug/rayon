"""
DISTINCT SUBTREE COUNT: The bridge between tree depth and circuit size.

A decision tree of depth n has up to 2^n leaves.
But many subtrees may be IDENTICAL → they can share one circuit gate.
The number of DISTINCT subtrees = effective circuit complexity.

For MAJ: symmetry (S_n) means subtrees depend only on
  (remaining_vars, ones_seen) → O(n²) distinct subtrees.

For CLIQUE: symmetry (S_N on vertices) means subtrees depend on
  isomorphism class of the revealed partial graph.
  Number of non-isomorphic partial graphs: SUPER-POLYNOMIAL.

MEASUREMENT: Build the full decision tree, hash each subtree's
truth table, count distinct hashes = distinct subtrees.

If distinct_subtrees = poly(n) → function has poly circuit → P
If distinct_subtrees = super-poly → function needs big circuit → NP-hard
"""

import itertools
from collections import defaultdict
import random
import math
import sys


def compute_phi_fast(n, tt, active, num_trials=60):
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


def build_tree_count_subtrees(n, tt, active, depth=0, max_depth=20, memo=None):
    """Build decision tree and count distinct subtrees via memoization.

    A subtree is identified by its truth table on the active inputs.
    Two subtrees are "same" if they compute the same function.

    Returns: (depth, leaves, distinct_subtrees, subtree_hash)
    """
    if memo is None:
        memo = {}

    # Hash the current sub-problem: the truth table restricted to active inputs
    key = tuple(sorted((b, tt[b]) for b in active))
    if key in memo:
        return memo[key]

    # Base cases
    if len(active) <= 1:
        result = (depth, 1, 1, key)
        memo[key] = result
        return result

    vals = set(tt[b] for b in active)
    if len(vals) == 1:
        result = (depth, 1, 1, key)
        memo[key] = result
        return result

    if depth >= max_depth:
        result = (depth, 1, 1, key)
        memo[key] = result
        return result

    # Find best variable to split on (greedy: minimize max child Φ)
    best_j = 0
    best_max_phi = float('inf')

    for j in range(n):
        left = [b for b in active if not (b >> j) & 1]
        right = [b for b in active if (b >> j) & 1]
        if not left or not right:
            continue
        # Quick check: is split useful?
        vals_l = set(tt[b] for b in left)
        vals_r = set(tt[b] for b in right)
        if len(vals_l) <= 1 and len(vals_r) <= 1:
            best_j = j
            best_max_phi = 0
            break
        # Use Φ to guide
        phi_l = compute_phi_fast(n, tt, left, 30)
        phi_r = compute_phi_fast(n, tt, right, 30)
        max_phi = max(phi_l, phi_r)
        if max_phi < best_max_phi:
            best_max_phi = max_phi
            best_j = j

    left = [b for b in active if not (b >> best_j) & 1]
    right = [b for b in active if (b >> best_j) & 1]

    _, leaves_l, dist_l, _ = build_tree_count_subtrees(n, tt, left, depth+1, max_depth, memo)
    _, leaves_r, dist_r, _ = build_tree_count_subtrees(n, tt, right, depth+1, max_depth, memo)

    total_leaves = leaves_l + leaves_r
    # Distinct subtrees: count unique keys in memo
    # (we'll count at the end)

    result = (max(depth, depth+1), total_leaves, len(memo), key)
    memo[key] = result
    return result


def analyze_distinct_subtrees(n, tt, name):
    """Full analysis: build tree, count distinct subtrees."""
    all_inputs = list(range(2**n))
    memo = {}
    depth, leaves, _, _ = build_tree_count_subtrees(n, tt, all_inputs, 0, n+2, memo)
    distinct = len(memo)

    log_n = math.log2(max(2, n))

    print(f"  {name:<18} {n:>4} {depth:>6} {leaves:>8} {distinct:>10} "
          f"{distinct/n:>10.1f} {distinct/n**2:>10.2f}")

    return distinct


def main():
    random.seed(42)
    print("=" * 80)
    print("  DISTINCT SUBTREE COUNT: Tree Complexity → Circuit Complexity")
    print("  distinct/n² ≈ const → poly circuit → P")
    print("  distinct/n² → ∞    → super-poly circuit → NP-hard")
    print("=" * 80)

    print(f"\n  {'Function':<18} {'n':>4} {'depth':>6} {'leaves':>8} "
          f"{'distinct':>10} {'dist/n':>10} {'dist/n²':>10}")
    print("  " + "-" * 72)

    results = defaultdict(list)

    # MAJ
    for n in range(4, 15):
        if 2**n > 100000:
            break
        tt = {b: 1 if bin(b).count('1') > n/2 else 0 for b in range(2**n)}
        d = analyze_distinct_subtrees(n, tt, f"MAJ-{n}")
        results['MAJ'].append((n, d))
        sys.stdout.flush()

    # MSAT
    from mono3sat import generate_all_mono3sat_clauses
    for n in range(4, 15):
        if 2**n > 100000:
            break
        all_cl = generate_all_mono3sat_clauses(n)
        clauses = random.sample(all_cl, min(len(all_cl), 3*n))
        tt = {}
        for bits in range(2**n):
            x = tuple((bits >> j) & 1 for j in range(n))
            tt[bits] = 1 if all(any(x[v] for v in c) for c in clauses) else 0
        d = analyze_distinct_subtrees(n, tt, f"MSAT-{n}")
        results['MSAT'].append((n, d))
        sys.stdout.flush()

    # Triangle
    for N in range(4, 7):
        n = N*(N-1)//2
        if 2**n > 100000:
            break
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
        d = analyze_distinct_subtrees(n, tt, f"TRI-K{N}")
        results['TRI'].append((n, d))
        sys.stdout.flush()

    # OR
    for n in range(4, 16):
        if 2**n > 100000:
            break
        tt = {b: 0 if b == 0 else 1 for b in range(2**n)}
        d = analyze_distinct_subtrees(n, tt, f"OR-{n}")
        results['OR'].append((n, d))
        sys.stdout.flush()

    # Growth rate analysis
    print(f"\n\n{'='*80}")
    print("  GROWTH RATE: distinct subtrees vs n")
    print(f"{'='*80}")

    for family in ['OR', 'MAJ', 'MSAT', 'TRI']:
        data = results[family]
        if len(data) < 3:
            continue
        print(f"\n  {family}:")
        ns = [d[0] for d in data]
        ds = [d[1] for d in data]

        # Fit power law: distinct ≈ C × n^α
        log_ns = [math.log(n) for n in ns if n > 1]
        log_ds = [math.log(max(1, d)) for d in ds]
        if len(log_ns) >= 3:
            m = len(log_ns)
            sx = sum(log_ns); sy = sum(log_ds)
            sxy = sum(x*y for x,y in zip(log_ns, log_ds))
            sxx = sum(x*x for x in log_ns)
            denom = m*sxx - sx*sx
            if denom != 0:
                alpha = (m*sxy - sx*sy) / denom
                logC = (sy - alpha*sx) / m
                print(f"    Power law: distinct ≈ {math.exp(logC):.2f} × n^{alpha:.2f}")

                if alpha > 3:
                    print(f"    >>> SUPER-CUBIC growth → hard function")
                elif alpha > 2:
                    print(f"    >>> QUADRATIC-CUBIC → moderate")
                elif alpha > 1:
                    print(f"    >>> LINEAR-QUADRATIC → easy")
                else:
                    print(f"    >>> SUB-LINEAR → very easy")

    print(f"\n{'='*80}")
    print("  VERDICT")
    print(f"{'='*80}")
    print("""
    The number of DISTINCT subtrees = effective circuit complexity.

    If distinct_subtrees(CLIQUE) grows FASTER than polynomial:
      → CLIQUE needs super-polynomial circuits → P ≠ NP

    The growth rate exponent α tells us:
      α < 2: probably in P (polynomial distinct subtrees)
      α > 2: possibly hard (super-quadratic distinct subtrees)
      α exponential in n: definitely hard (super-polynomial)

    Compare: MAJ (in P) vs CLIQUE/MSAT
    If CLIQUE has higher α than MAJ: evidence for P ≠ NP
    """)


if __name__ == "__main__":
    main()
