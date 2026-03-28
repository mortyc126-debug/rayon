"""
DECISIVE TEST: Does Φ-decomposition tree depth grow as O(log n) or O(n)?

If O(log n): 2^{O(log n)} = poly(n) leaves → POLYNOMIAL ALGORITHM → P = NP
If O(n): 2^n leaves → exponential → no conclusion

We must solve BOTH branches (not just the harder one).
Total leaves = 2^depth. Algorithm cost ∝ total leaves.

Measure: full decomposition tree depth for increasing n.
"""

import itertools
from collections import defaultdict
import random
import math
import sys


def compute_phi(n, tt, active_inputs, num_trials=100):
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
        best = max(best, max(1,cross) * max(1,len(sigs)) *
                   max(1, int(math.ceil(math.log2(max(2, len(sigs)))))))
    return best


def find_best_variable_split(n, tt, active_inputs):
    """Find the single variable that best reduces max(Φ_left, Φ_right)."""
    if len(active_inputs) <= 1:
        return -1, 0

    phi_total = compute_phi(n, tt, active_inputs, 80)
    if phi_total == 0:
        return -1, 0

    best_j = -1
    best_max_phi = phi_total

    for j in range(n):
        left = [b for b in active_inputs if not (b >> j) & 1]
        right = [b for b in active_inputs if (b >> j) & 1]
        if not left or not right:
            continue
        phi_l = compute_phi(n, tt, left, 60)
        phi_r = compute_phi(n, tt, right, 60)
        max_phi = max(phi_l, phi_r)
        if max_phi < best_max_phi:
            best_max_phi = max_phi
            best_j = j

    return best_j, best_max_phi


def full_decomposition_tree(n, tt, active_inputs, depth=0, max_depth=20):
    """Build FULL decomposition tree (both branches).

    Returns: (tree_depth, num_leaves, num_nodes)
    """
    # Check if function is constant on active inputs
    if len(active_inputs) <= 1:
        return depth, 1, 1

    vals = set(tt[b] for b in active_inputs)
    if len(vals) == 1:
        return depth, 1, 1

    if depth >= max_depth:
        return depth, 1, 1

    # Find best split
    best_j, _ = find_best_variable_split(n, tt, active_inputs)
    if best_j < 0:
        return depth, 1, 1

    left = [b for b in active_inputs if not (b >> best_j) & 1]
    right = [b for b in active_inputs if (b >> best_j) & 1]

    # Recurse on BOTH branches
    d_left, leaves_left, nodes_left = full_decomposition_tree(
        n, tt, left, depth + 1, max_depth)
    d_right, leaves_right, nodes_right = full_decomposition_tree(
        n, tt, right, depth + 1, max_depth)

    total_depth = max(d_left, d_right)
    total_leaves = leaves_left + leaves_right
    total_nodes = nodes_left + nodes_right + 1

    return total_depth, total_leaves, total_nodes


def main():
    random.seed(42)
    print("=" * 70)
    print("  DECISIVE TEST: Tree Depth Scaling")
    print("  O(log n) → P=NP direction | O(n) → P≠NP direction")
    print("=" * 70)

    from mono3sat import generate_all_mono3sat_clauses

    print(f"\n{'Function':<20} {'n':>4} {'depth':>6} {'leaves':>8} "
          f"{'nodes':>8} {'depth/log(n)':>12} {'depth/n':>8}")
    print("-" * 70)

    # MSAT for various n
    for n in range(5, 16):
        if 2**n > 200000:
            break

        all_cl = generate_all_mono3sat_clauses(n)
        clauses = random.sample(all_cl, min(len(all_cl), 3*n))
        tt = {}
        for bits in range(2**n):
            x = tuple((bits >> j) & 1 for j in range(n))
            tt[bits] = 1 if all(any(x[v] for v in c) for c in clauses) else 0

        all_inputs = list(range(2**n))
        max_d = min(n + 2, 18)
        depth, leaves, nodes = full_decomposition_tree(n, tt, all_inputs, 0, max_d)

        log_n = math.log2(n)
        print(f"{'MSAT-'+str(n):<20} {n:>4} {depth:>6} {leaves:>8} "
              f"{nodes:>8} {depth/log_n:>12.2f} {depth/n:>8.3f}")
        sys.stdout.flush()

    # Triangle for various N
    for N in range(4, 8):
        n = N*(N-1)//2
        if 2**n > 200000:
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

        all_inputs = list(range(2**n))
        max_d = min(n + 2, 18)
        depth, leaves, nodes = full_decomposition_tree(n, tt, all_inputs, 0, max_d)

        log_n = math.log2(n) if n > 1 else 1
        print(f"{'TRI-K'+str(N):<20} {n:>4} {depth:>6} {leaves:>8} "
              f"{nodes:>8} {depth/log_n:>12.2f} {depth/n:>8.3f}")
        sys.stdout.flush()

    # MAJ
    for n in range(5, 14):
        if 2**n > 200000:
            break

        tt = {b: 1 if bin(b).count('1') > n/2 else 0 for b in range(2**n)}
        all_inputs = list(range(2**n))
        depth, leaves, nodes = full_decomposition_tree(n, tt, all_inputs, 0, min(n+2, 18))

        log_n = math.log2(n)
        print(f"{'MAJ-'+str(n):<20} {n:>4} {depth:>6} {leaves:>8} "
              f"{nodes:>8} {depth/log_n:>12.2f} {depth/n:>8.3f}")
        sys.stdout.flush()

    # OR (should be very shallow)
    for n in range(5, 16):
        if 2**n > 200000:
            break
        tt = {b: 0 if b == 0 else 1 for b in range(2**n)}
        all_inputs = list(range(2**n))
        depth, leaves, nodes = full_decomposition_tree(n, tt, all_inputs, 0, min(n+2, 18))
        log_n = math.log2(n)
        print(f"{'OR-'+str(n):<20} {n:>4} {depth:>6} {leaves:>8} "
              f"{nodes:>8} {depth/log_n:>12.2f} {depth/n:>8.3f}")
        sys.stdout.flush()

    print(f"\n{'='*70}")
    print("  SCALING VERDICT")
    print(f"{'='*70}")
    print("""
    depth/log(n) ≈ constant → tree depth = O(log n) → poly leaves → P=NP
    depth/n ≈ constant → tree depth = O(n) → exp leaves → P≠NP

    LOOK AT THE depth/log(n) AND depth/n COLUMNS:
    Which one stays constant?
    """)


if __name__ == "__main__":
    main()
