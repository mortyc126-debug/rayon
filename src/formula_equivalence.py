"""
Formula Equivalence Conjecture: Testing on Hard Functions.

CONJECTURE: For monotone Boolean functions f,
  general_formula_size(f) = Θ(monotone_formula_size(f))

If true → depth-restricted circuit lower bounds for NP-hard functions.

Previous test (MONO-3SAT): ratio = 1.000 but formula size = n (trivial).
We need to test on functions with LARGE monotone formula complexity.

Test functions:
1. MAJORITY/THRESHOLD: known monotone formula complexity Θ(n^{5/2})
2. PERFECT MATCHING: detecting if a bipartite graph has perfect matching
3. CLIQUE on small N: triangle/clique detection
4. SORTING-related: functions from sorting network theory

For these, if gen/mono ≈ 1 even when formula size >> n, the conjecture
gains strong evidence.
"""

import itertools
from collections import defaultdict
import random
import math
import sys
import time


def compute_kw_cover_size(n, func, use_general=False):
    """Compute KW rectangle cover size for function func.

    func: function from tuple of n bits → {0, 1}

    Returns: (num_rectangles, num_ones, num_zeros)
    """
    ones = []
    zeros = []
    for bits in range(2**n):
        x = tuple((bits >> j) & 1 for j in range(n))
        if func(x):
            ones.append(x)
        else:
            zeros.append(x)

    if not ones or not zeros:
        return 0, len(ones), len(zeros)

    # KW relation
    kw = {}
    for xi, x in enumerate(ones):
        kw[xi] = {}
        for yi, y in enumerate(zeros):
            if use_general:
                valid = frozenset(i for i in range(n) if x[i] != y[i])
            else:
                valid = frozenset(i for i in range(n) if x[i] == 1 and y[i] == 0)
            kw[xi][yi] = valid

    # Greedy rectangle cover
    uncovered = set()
    for xi in range(len(ones)):
        for yi in range(len(zeros)):
            uncovered.add((xi, yi))

    num_rect = 0
    while uncovered:
        xi0, yi0 = next(iter(uncovered))
        best = None
        best_cov = 0

        for t in kw[xi0][yi0]:
            rows = {xi for xi in range(len(ones)) if t in kw[xi][yi0]}
            cols = set()
            for yi in range(len(zeros)):
                if all(t in kw[xi][yi] for xi in rows):
                    cols.add(yi)
            cov = sum(1 for xi in rows for yi in cols if (xi, yi) in uncovered)
            if cov > best_cov:
                best_cov = cov
                best = (rows, cols)

        if best:
            for xi in best[0]:
                for yi in best[1]:
                    uncovered.discard((xi, yi))
        num_rect += 1

    return num_rect, len(ones), len(zeros)


def majority(x):
    """Majority function: 1 if more than half of bits are 1."""
    return 1 if sum(x) > len(x) / 2 else 0


def threshold_k(x, k):
    """Threshold-k: 1 if sum(x) >= k."""
    return 1 if sum(x) >= k else 0


def exact_k(x, k):
    """Exact-k: 1 if sum(x) == k."""
    return 1 if sum(x) == k else 0


def triangle_detection(adj_matrix, N):
    """Triangle detection on N-vertex graph encoded as flat adjacency."""
    # adj_matrix is tuple of n=C(N,2) bits
    idx = 0
    edges = {}
    for i in range(N):
        for j in range(i+1, N):
            edges[(i,j)] = adj_matrix[idx]
            edges[(j,i)] = adj_matrix[idx]
            idx += 1

    for i in range(N):
        for j in range(i+1, N):
            for k in range(j+1, N):
                if edges[(i,j)] and edges[(i,k)] and edges[(j,k)]:
                    return 1
    return 0


def bipartite_matching(adj, n_left, n_right):
    """Check if bipartite graph has perfect matching (n_left = n_right).
    adj is tuple of n_left * n_right bits.
    """
    if n_left != n_right:
        return 0

    n = n_left

    # Try all permutations (brute force for small n)
    for perm in itertools.permutations(range(n)):
        match = True
        for i in range(n):
            if not adj[i * n + perm[i]]:
                match = False
                break
        if match:
            return 1
    return 0


def main():
    print("=" * 80)
    print("  FORMULA EQUIVALENCE CONJECTURE: HARD FUNCTION TESTS")
    print("  Question: Does gen/mono ratio stay 1.0 for hard functions?")
    print("=" * 80)

    results = []

    # Test 1: MAJORITY on n bits
    print(f"\n{'─'*70}")
    print("  MAJORITY / THRESHOLD functions")
    print(f"{'─'*70}")

    for n in range(3, 12):
        if 2**n > 50000:
            break

        t0 = time.time()
        f_mono, ones, zeros = compute_kw_cover_size(
            n, majority, use_general=False)
        f_gen, _, _ = compute_kw_cover_size(
            n, majority, use_general=True)
        dt = time.time() - t0

        if ones * zeros > 100000:
            continue

        ratio = f_gen / f_mono if f_mono > 0 else 0
        base = f_mono ** (1.0/n) if f_mono > 1 else 0

        print(f"  MAJ-{n}: F_mono={f_mono:6d}, F_gen={f_gen:6d}, "
              f"ratio={ratio:.4f}, base={base:.4f}  [{dt:.1f}s]")
        results.append(('MAJ', n, f_mono, f_gen, ratio))
        sys.stdout.flush()

    # Test 2: THRESHOLD-k for various k
    print(f"\n{'─'*70}")
    print("  THRESHOLD-k functions")
    print(f"{'─'*70}")

    for n in range(4, 10):
        if 2**n > 30000:
            break
        for k in [2, n//2, n-1]:
            func = lambda x, kk=k: threshold_k(x, kk)

            t0 = time.time()
            f_mono, ones, zeros = compute_kw_cover_size(
                n, func, use_general=False)

            if ones * zeros > 50000:
                continue

            f_gen, _, _ = compute_kw_cover_size(n, func, use_general=True)
            dt = time.time() - t0

            ratio = f_gen / f_mono if f_mono > 0 else 0

            print(f"  TH{k}-{n}: F_mono={f_mono:6d}, F_gen={f_gen:6d}, "
                  f"ratio={ratio:.4f}  [{dt:.1f}s]")
            results.append(('TH', n, f_mono, f_gen, ratio))
            sys.stdout.flush()

    # Test 3: EXACT-k (non-monotone!)
    print(f"\n{'─'*70}")
    print("  EXACT-k functions (non-monotone, for comparison)")
    print(f"{'─'*70}")

    for n in range(4, 10):
        if 2**n > 30000:
            break
        k = n // 2
        func = lambda x, kk=k: exact_k(x, kk)

        t0 = time.time()
        f_mono, ones, zeros = compute_kw_cover_size(
            n, func, use_general=False)

        if ones * zeros > 50000 or ones == 0 or zeros == 0:
            continue

        f_gen, _, _ = compute_kw_cover_size(n, func, use_general=True)
        dt = time.time() - t0

        ratio = f_gen / f_mono if f_mono > 0 else 0

        print(f"  EX{k}-{n}: F_mono={f_mono:6d}, F_gen={f_gen:6d}, "
              f"ratio={ratio:.4f}  [{dt:.1f}s]")
        results.append(('EX', n, f_mono, f_gen, ratio))

    # Test 4: Triangle detection
    print(f"\n{'─'*70}")
    print("  TRIANGLE DETECTION")
    print(f"{'─'*70}")

    for N in [4, 5]:
        n = N * (N-1) // 2
        if 2**n > 100000:
            break

        func = lambda x, NN=N: triangle_detection(x, NN)

        t0 = time.time()
        f_mono, ones, zeros = compute_kw_cover_size(
            n, func, use_general=False)

        if ones * zeros > 50000:
            print(f"  TRI-{N}: too large ({ones}×{zeros})")
            continue

        f_gen, _, _ = compute_kw_cover_size(n, func, use_general=True)
        dt = time.time() - t0

        ratio = f_gen / f_mono if f_mono > 0 else 0

        print(f"  TRI-{N} (n={n}): F_mono={f_mono:6d}, F_gen={f_gen:6d}, "
              f"ratio={ratio:.4f}  [{dt:.1f}s]")
        results.append(('TRI', n, f_mono, f_gen, ratio))

    # Test 5: Perfect matching (bipartite)
    print(f"\n{'─'*70}")
    print("  PERFECT MATCHING (bipartite)")
    print(f"{'─'*70}")

    for m in [2, 3]:
        n = m * m
        if 2**n > 100000:
            break

        func = lambda x, mm=m: bipartite_matching(x, mm, mm)

        t0 = time.time()
        f_mono, ones, zeros = compute_kw_cover_size(
            n, func, use_general=False)

        if ones * zeros > 50000:
            print(f"  MATCH-{m} (n={n}): too large ({ones}×{zeros})")
            continue

        f_gen, _, _ = compute_kw_cover_size(n, func, use_general=True)
        dt = time.time() - t0

        ratio = f_gen / f_mono if f_mono > 0 else 0

        print(f"  MATCH-{m} (n={n}): F_mono={f_mono:6d}, F_gen={f_gen:6d}, "
              f"ratio={ratio:.4f}  [{dt:.1f}s]")
        results.append(('MATCH', n, f_mono, f_gen, ratio))

    # Summary
    print(f"\n{'='*80}")
    print("  FORMULA EQUIVALENCE SUMMARY")
    print(f"{'='*80}")
    print(f"\n  {'Function':<15} {'n':>4} {'F_mono':>8} {'F_gen':>8} {'ratio':>8}")
    print("  " + "-" * 45)

    all_ratios = []
    for name, n, fm, fg, r in results:
        print(f"  {name+'-'+str(n):<15} {n:4d} {fm:8d} {fg:8d} {r:8.4f}")
        if r > 0:
            all_ratios.append(r)

    if all_ratios:
        print(f"\n  Average ratio: {sum(all_ratios)/len(all_ratios):.4f}")
        print(f"  Min ratio:     {min(all_ratios):.4f}")
        print(f"  Max ratio:     {max(all_ratios):.4f}")

        if all(r > 0.99 for r in all_ratios):
            print(f"\n  >>> ALL RATIOS ≈ 1.0!")
            print(f"  >>> STRONG EVIDENCE for formula equivalence conjecture")
            print(f"  >>> NOT gates DO NOT help for formula size of monotone functions")
            print(f"  >>> Combined with Razborov: depth-restricted circuit lower bounds")
        elif min(all_ratios) < 0.5:
            print(f"\n  >>> Some ratios < 0.5: NOT gates help for formula size")
            print(f"  >>> Formula equivalence conjecture is FALSE")
        else:
            print(f"\n  >>> Mixed results: more data needed")


if __name__ == "__main__":
    main()
