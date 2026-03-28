"""
RELEVANCE SCALING: How does max_relevance/Φ change with N for CLIQUE?

Critical test: if max_relevance/Φ → 0 as N grows → P ≠ NP
              if max_relevance/Φ → const → framework insufficient

We test Triangle (3-clique) on K4, K5, K6 and measure how the
best intermediate's relevance scales relative to Φ.

The BEST intermediate for triangle detection:
  - deg≥2(v): "vertex v has degree ≥ 2" (necessary for triangle through v)
  - edge_count≥3: "graph has ≥ 3 edges" (necessary for any triangle)
  - specific_triangle: "specific triple forms triangle"

For k-clique with growing k: the "deg≥k-1" intermediate should have
DECREASING relative relevance because most graphs near the threshold
already satisfy degree conditions.
"""

import itertools
from collections import defaultdict
import random
import math
import sys


def compute_phi(n, tt, num_trials=200):
    total = 2**n
    boundary = []
    for bits in range(total):
        for j in range(n):
            nb = bits ^ (1 << j)
            if bits < nb and tt[bits] != tt[nb]:
                boundary.append((bits, nb))
    if not boundary:
        return 0
    best = 0
    for _ in range(num_trials):
        k = random.randint(1, min(n-1, 7))
        coords = random.sample(range(n), k)
        block_of = {}
        sigs_dict = defaultdict(list)
        for bits in range(total):
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


def compute_conditional_phi(n, tt_f, tt_g, num_trials=150):
    total = 2**n
    parts = [
        [b for b in range(total) if tt_g[b] == 0],
        [b for b in range(total) if tt_g[b] == 1]
    ]
    max_phi = 0
    for subset in parts:
        if len(subset) <= 1:
            continue
        subset_set = set(subset)
        boundary = []
        for bits in subset:
            for j in range(n):
                nb = bits ^ (1 << j)
                if nb in subset_set and bits < nb and tt_f[bits] != tt_f[nb]:
                    boundary.append((bits, nb))
        if not boundary:
            continue
        best = 0
        for _ in range(num_trials):
            k = random.randint(1, min(n-1, 6))
            coords = random.sample(range(n), k)
            block_of = {}
            sigs_dict = defaultdict(list)
            for bits in subset:
                bid = sum((1 << ci) for ci, c in enumerate(coords) if (bits >> c) & 1)
                block_of[bits] = bid
                sigs_dict[bid].append(tt_f[bits])
            cross = sum(1 for b1, b2 in boundary if block_of[b1] != block_of[b2])
            sigs = set(tuple(v) for v in sigs_dict.values())
            best = max(best, max(1,cross) * max(1,len(sigs)) *
                       max(1, int(math.ceil(math.log2(max(2, len(sigs)))))))
        max_phi = max(max_phi, best)
    return max_phi


def make_triangle_tt(N):
    n = N*(N-1)//2
    edge_idx = {}
    idx = 0
    for i in range(N):
        for j in range(i+1, N):
            edge_idx[(i,j)] = idx
            edge_idx[(j,i)] = idx
            idx += 1

    tt = {}
    for bits in range(2**n):
        x = tuple((bits >> j) & 1 for j in range(n))
        has = False
        for i in range(N):
            for j in range(i+1, N):
                for k in range(j+1, N):
                    if x[edge_idx[(i,j)]] and x[edge_idx[(i,k)]] and x[edge_idx[(j,k)]]:
                        has = True
                        break
                if has: break
            if has: break
        tt[bits] = 1 if has else 0
    return tt, n, edge_idx


def make_4clique_tt(N):
    n = N*(N-1)//2
    edge_idx = {}
    idx = 0
    for i in range(N):
        for j in range(i+1, N):
            edge_idx[(i,j)] = idx
            edge_idx[(j,i)] = idx
            idx += 1

    tt = {}
    for bits in range(2**n):
        x = tuple((bits >> j) & 1 for j in range(n))
        has = False
        for combo in itertools.combinations(range(N), 4):
            clique = True
            for a in range(4):
                for b in range(a+1, 4):
                    if not x[edge_idx[(combo[a], combo[b])]]:
                        clique = False
                        break
                if not clique: break
            if clique:
                has = True
                break
        tt[bits] = 1 if has else 0
    return tt, n, edge_idx


def best_intermediate_relevance(N, tt_f, n, edge_idx, k_clique=3):
    """Find the most relevant intermediate for k-clique detection.

    Try: degree conditions, edge counts, specific sub-cliques.
    """
    phi_f = compute_phi(n, tt_f, 300)
    best_relev = 0
    best_name = ""
    best_pct = 0

    # 1. Degree ≥ k-1 for each vertex
    for v in range(N):
        tt_g = {}
        for bits in range(2**n):
            x = tuple((bits >> j) & 1 for j in range(n))
            deg = sum(x[edge_idx[(v, u)]] for u in range(N) if u != v)
            tt_g[bits] = 1 if deg >= k_clique - 1 else 0
        phi_cond = compute_conditional_phi(n, tt_f, tt_g, 150)
        relev = phi_f - phi_cond
        pct = relev / phi_f * 100 if phi_f > 0 else 0
        if relev > best_relev:
            best_relev = relev
            best_name = f"deg≥{k_clique-1}(v{v})"
            best_pct = pct

    # 2. Edge count ≥ threshold
    for thresh in [k_clique, k_clique + 1, n // 2]:
        tt_g = {}
        for bits in range(2**n):
            tt_g[bits] = 1 if bin(bits).count('1') >= thresh else 0
        phi_cond = compute_conditional_phi(n, tt_f, tt_g, 150)
        relev = phi_f - phi_cond
        pct = relev / phi_f * 100 if phi_f > 0 else 0
        if relev > best_relev:
            best_relev = relev
            best_name = f"edges≥{thresh}"
            best_pct = pct

    # 3. Specific sub-clique exists
    for size in range(2, k_clique):
        # Check if any sub-clique of this size exists
        # (For size=2: any edge exists)
        count = 0
        for combo in itertools.combinations(range(N), size):
            if count >= 5:  # limit
                break
            count += 1
            tt_g = {}
            for bits in range(2**n):
                x = tuple((bits >> j) & 1 for j in range(n))
                is_clique = True
                for a in range(size):
                    for b in range(a+1, size):
                        if not x[edge_idx[(combo[a], combo[b])]]:
                            is_clique = False
                            break
                    if not is_clique: break
                tt_g[bits] = 1 if is_clique else 0
            phi_cond = compute_conditional_phi(n, tt_f, tt_g, 100)
            relev = phi_f - phi_cond
            pct = relev / phi_f * 100 if phi_f > 0 else 0
            if relev > best_relev:
                best_relev = relev
                best_name = f"{size}-clique{combo}"
                best_pct = pct

    # 4. "Any vertex in a (k-1)-clique" (exists (k-1)-clique through v)
    for v in range(min(N, 3)):
        tt_g = {}
        for bits in range(2**n):
            x = tuple((bits >> j) & 1 for j in range(n))
            has = False
            for combo in itertools.combinations([u for u in range(N) if u != v], k_clique - 1):
                full = (v,) + combo
                clique = True
                for a in range(len(full)):
                    for b in range(a+1, len(full)):
                        if not x[edge_idx[(full[a], full[b])]]:
                            clique = False
                            break
                    if not clique: break
                if clique:
                    has = True
                    break
            tt_g[bits] = 1 if has else 0
        phi_cond = compute_conditional_phi(n, tt_f, tt_g, 100)
        relev = phi_f - phi_cond
        pct = relev / phi_f * 100 if phi_f > 0 else 0
        if relev > best_relev:
            best_relev = relev
            best_name = f"v{v}_in_{k_clique-1}clique"
            best_pct = pct

    return phi_f, best_relev, best_pct, best_name


def main():
    random.seed(42)
    print("=" * 70)
    print("  RELEVANCE SCALING WITH N")
    print("  Does max_relevance/Φ decrease for larger instances?")
    print("=" * 70)

    print(f"\n{'Problem':<20} {'N':>4} {'k':>3} {'n':>5} {'Φ':>10} "
          f"{'best_rel':>10} {'rel/Φ':>8} {'best_intermediate':<25}")
    print("-" * 90)

    # Triangle (k=3) on various N
    for N in range(4, 8):
        n = N*(N-1)//2
        if 2**n > 200000:
            break
        tt, n_bits, eidx = make_triangle_tt(N)
        phi, rel, pct, name = best_intermediate_relevance(N, tt, n_bits, eidx, 3)
        print(f"{'Triangle':<20} {N:>4} {3:>3} {n_bits:>5} {phi:>10} "
              f"{rel:>10} {pct:>7.1f}% {name:<25}")
        sys.stdout.flush()

    # 4-clique on various N
    for N in range(5, 8):
        n = N*(N-1)//2
        if 2**n > 200000:
            break
        tt, n_bits, eidx = make_4clique_tt(N)
        phi, rel, pct, name = best_intermediate_relevance(N, tt, n_bits, eidx, 4)
        print(f"{'4-Clique':<20} {N:>4} {4:>3} {n_bits:>5} {phi:>10} "
              f"{rel:>10} {pct:>7.1f}% {name:<25}")
        sys.stdout.flush()

    print(f"\n{'='*70}")
    print("  SCALING TREND")
    print(f"{'='*70}")
    print("""
    KEY QUESTION: Does rel/Φ decrease as N grows?

    For Triangle (k=3):
      If rel/Φ stays ~40-50%: intermediates remain powerful → easy
      If rel/Φ decreases: intermediates weaken → harder

    For 4-Clique (k=4):
      Compare with Triangle at same N: should be harder
      rel/Φ for 4-clique should be LOWER than for triangle

    THE PREDICTION for k = N^{1/3}:
      rel/Φ ≈ O(k/N) = O(N^{-2/3}) → 0 as N → ∞
      Because: best intermediates (degree conditions) are almost
      always satisfied near the clique threshold, providing no info.

    If confirmed: Φ_eff(CLIQUE) ≈ Φ(CLIQUE) for large N → P ≠ NP
    """)


if __name__ == "__main__":
    main()
