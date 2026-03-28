"""
Φ_eff: Effective Computational Potential (circuit-relevant).

Φ measures formula complexity. To get circuit complexity, subtract
the maximum fan-out recovery achievable by the function's structure.

Φ_eff(f) = Φ(f) - max_recovery(f)

max_recovery = maximum Φ recoverable by optimally placing fan-out
             = max over all possible intermediate functions g of:
               (optimal_fan_out(g) - 1) × Φ(g)

The key insight: fan-out recovery depends on how "reusable" intermediate
results are. A function g is reusable if it's useful for MANY different
parts of the computation.

MEASURE OF REUSABILITY: For intermediate function g, how much of Φ(f)
can be "explained" by knowing g?

Define: RELEVANCE(g, f) = Φ(f) - Φ(f | g)
where Φ(f | g) = Φ of f conditioned on knowing g's value.

If g is highly relevant: knowing g reduces Φ(f) a lot → g is reusable.
If g is irrelevant: knowing g doesn't help → g is not reusable.

For the best possible circuit:
  max_recovery = max over all sets S of intermediates with |S| = s:
    Σ_{g ∈ S} RELEVANCE(g, f)

If RELEVANCE is bounded for all g: max_recovery ≤ s × max_RELEVANCE.
If max_RELEVANCE is polynomial: Φ_eff = Φ(f) - s × poly.
For Φ(f) super-polynomial: Φ_eff is still super-polynomial!

EXPERIMENT: Compute RELEVANCE for natural intermediate functions
and compare between CLIQUE, MAJ, and MSAT.
"""

import itertools
from collections import defaultdict
import random
import math
import sys


def compute_phi(n, tt, num_trials=150):
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
    """Compute Φ(f | g) = Φ of f conditioned on knowing g's value.

    Split inputs into {g=0} and {g=1}. Compute Φ of f restricted to
    each, then combine: Φ(f|g) = max(Φ(f|g=0), Φ(f|g=1)).

    This measures: how much complexity remains AFTER knowing g.
    """
    total = 2**n

    # Split by g value
    inputs_0 = [b for b in range(total) if tt_g[b] == 0]
    inputs_1 = [b for b in range(total) if tt_g[b] == 1]

    # For each split: compute boundary within that subset
    phi_parts = []

    for subset in [inputs_0, inputs_1]:
        if len(subset) <= 1:
            phi_parts.append(0)
            continue

        subset_set = set(subset)
        boundary = []
        for bits in subset:
            for j in range(n):
                nb = bits ^ (1 << j)
                if nb in subset_set and bits < nb and tt_f[bits] != tt_f[nb]:
                    boundary.append((bits, nb))

        if not boundary:
            phi_parts.append(0)
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
            cons = max(1, cross)
            comp = max(1, len(sigs))
            depth = max(1, int(math.ceil(math.log2(max(2, comp)))))
            best = max(best, cons * comp * depth)
        phi_parts.append(best)

    return max(phi_parts)  # worst case over g=0 and g=1


def compute_relevance(n, tt_f, tt_g):
    """RELEVANCE(g, f) = Φ(f) - Φ(f|g).

    How much knowing g reduces the complexity of computing f.
    """
    phi_f = compute_phi(n, tt_f)
    phi_f_given_g = compute_conditional_phi(n, tt_f, tt_g)
    return phi_f - phi_f_given_g, phi_f, phi_f_given_g


def generate_natural_intermediates_triangle(N):
    """Generate natural intermediate functions for triangle detection.

    Natural intermediates:
    - Single edges (trivial)
    - "Vertex has degree ≥ k" functions
    - "Edge (i,j) is in a triangle" functions
    - Sub-triangle indicators
    """
    n = N * (N-1) // 2
    edge_idx = {}
    idx = 0
    for i in range(N):
        for j in range(i+1, N):
            edge_idx[(i,j)] = idx
            edge_idx[(j,i)] = idx
            idx += 1

    intermediates = {}

    # Degree ≥ 2 for each vertex
    for v in range(N):
        def deg_func(bits, vv=v):
            x = tuple((bits >> j) & 1 for j in range(n))
            deg = sum(x[edge_idx[(vv, u)]] for u in range(N) if u != vv)
            return 1 if deg >= 2 else 0
        tt = {b: deg_func(b) for b in range(2**n)}
        intermediates[f'deg≥2(v{v})'] = tt

    # "Edge (i,j) is in a triangle"
    for i in range(min(N, 4)):
        for j in range(i+1, min(N, 5)):
            def edge_in_tri(bits, ii=i, jj=j):
                x = tuple((bits >> k) & 1 for k in range(n))
                if not x[edge_idx[(ii,jj)]]:
                    return 0
                for k in range(N):
                    if k != ii and k != jj:
                        if x[edge_idx[(ii,k)]] and x[edge_idx[(jj,k)]]:
                            return 1
                return 0
            tt = {b: edge_in_tri(b) for b in range(2**n)}
            intermediates[f'tri_edge({i},{j})'] = tt

    # "Vertices {i,j,k} form a triangle"
    for combo in itertools.combinations(range(min(N, 5)), 3):
        i, j, k = combo
        def specific_tri(bits, ii=i, jj=j, kk=k):
            x = tuple((bits >> m) & 1 for m in range(n))
            return 1 if (x[edge_idx[(ii,jj)]] and x[edge_idx[(ii,kk)]]
                        and x[edge_idx[(jj,kk)]]) else 0
        tt = {b: specific_tri(b) for b in range(2**n)}
        intermediates[f'tri({i},{j},{k})'] = tt

    return intermediates


def generate_natural_intermediates_maj(n_bits):
    """Natural intermediates for MAJ: partial sums, comparisons."""
    intermediates = {}

    # Partial sum ≥ k for first m variables
    for m in range(2, n_bits):
        for k in range(1, m):
            def partial_sum(bits, mm=m, kk=k):
                count = sum((bits >> j) & 1 for j in range(mm))
                return 1 if count >= kk else 0
            tt = {b: partial_sum(b) for b in range(2**n_bits)}
            intermediates[f'sum({m})≥{k}'] = tt

    # Pairwise AND/OR
    for i in range(min(n_bits, 4)):
        for j in range(i+1, min(n_bits, 5)):
            tt_and = {b: ((b>>i)&1) & ((b>>j)&1) for b in range(2**n_bits)}
            intermediates[f'x{i}∧x{j}'] = tt_and

    return intermediates


def analyze_relevance(func_name, n, tt_f, intermediates):
    """Compute relevance of each intermediate for function f."""
    phi_f = compute_phi(n, tt_f, 200)

    print(f"\n{'─'*60}")
    print(f"  {func_name} (n={n}, Φ={phi_f})")
    print(f"{'─'*60}")
    print(f"  {'Intermediate':<25} {'Φ(g)':>8} {'Φ(f|g)':>8} {'Relev':>8} "
          f"{'Rel%':>7}")
    print("  " + "-" * 58)

    relevances = []
    for name, tt_g in sorted(intermediates.items()):
        phi_g = compute_phi(n, tt_g, 100)
        phi_fg = compute_conditional_phi(n, tt_f, tt_g, 100)
        relev = phi_f - phi_fg
        rel_pct = relev / phi_f * 100 if phi_f > 0 else 0
        relevances.append((name, phi_g, phi_fg, relev, rel_pct))

    # Sort by relevance
    relevances.sort(key=lambda x: -x[3])

    for name, phi_g, phi_fg, relev, rel_pct in relevances[:15]:
        print(f"  {name:<25} {phi_g:>8} {phi_fg:>8} {relev:>+8} {rel_pct:>6.1f}%")

    # Key metrics
    max_relev = max(r[3] for r in relevances) if relevances else 0
    max_rel_pct = max(r[4] for r in relevances) if relevances else 0
    avg_relev = sum(r[3] for r in relevances) / len(relevances) if relevances else 0

    print(f"\n  Max relevance: {max_relev} ({max_rel_pct:.1f}% of Φ)")
    print(f"  Avg relevance: {avg_relev:.0f}")
    print(f"  Φ(f): {phi_f}")

    # EFFECTIVE POTENTIAL with optimal k intermediates
    sorted_revs = sorted([r[3] for r in relevances], reverse=True)
    for k in [1, 3, 5, 10]:
        if k > len(sorted_revs):
            break
        recovery = sum(sorted_revs[:k])
        phi_eff = phi_f - recovery
        print(f"  Φ_eff with {k} best intermediates: {phi_eff} "
              f"({phi_eff/phi_f*100:.1f}% remaining)")

    return phi_f, max_relev, relevances


def main():
    random.seed(42)
    print("=" * 60)
    print("  EFFECTIVE POTENTIAL Φ_eff: CLIQUE vs MAJ")
    print("  Does fan-out recovery differ between them?")
    print("=" * 60)

    # Triangle K5 (n=10)
    N = 5
    n = N*(N-1)//2
    tri_tt = {}
    edge_idx = {}
    idx = 0
    for i in range(N):
        for j in range(i+1, N):
            edge_idx[(i,j)] = idx
            edge_idx[(j,i)] = idx
            idx += 1

    for bits in range(2**n):
        x = tuple((bits >> j) & 1 for j in range(n))
        has_tri = False
        for i in range(N):
            for j in range(i+1, N):
                for k in range(j+1, N):
                    if x[edge_idx[(i,j)]] and x[edge_idx[(i,k)]] and x[edge_idx[(j,k)]]:
                        has_tri = True
                        break
                if has_tri: break
            if has_tri: break
        tri_tt[bits] = 1 if has_tri else 0

    tri_intermediates = generate_natural_intermediates_triangle(N)
    phi_tri, max_rel_tri, _ = analyze_relevance("Triangle K5", n, tri_tt, tri_intermediates)

    # MAJ on 10 bits
    n_maj = 10
    maj_tt = {}
    for bits in range(2**n_maj):
        maj_tt[bits] = 1 if bin(bits).count('1') > n_maj/2 else 0

    maj_intermediates = generate_natural_intermediates_maj(n_maj)
    phi_maj, max_rel_maj, _ = analyze_relevance("MAJ-10", n_maj, maj_tt, maj_intermediates)

    # COMPARISON
    print(f"\n\n{'='*60}")
    print("  COMPARISON: CLIQUE vs MAJ")
    print(f"{'='*60}")
    print(f"  {'Metric':<30} {'Triangle':>12} {'MAJ':>12}")
    print("  " + "-" * 55)
    print(f"  {'n (input bits)':<30} {n:>12} {n_maj:>12}")
    print(f"  {'Φ(f)':<30} {phi_tri:>12} {phi_maj:>12}")
    print(f"  {'Max single relevance':<30} {max_rel_tri:>12} {max_rel_maj:>12}")
    print(f"  {'Max relevance / Φ':<30} "
          f"{max_rel_tri/phi_tri*100:>11.1f}% {max_rel_maj/phi_maj*100:>11.1f}%")

    if max_rel_tri/phi_tri < max_rel_maj/phi_maj:
        print(f"\n  >>> CLIQUE has LOWER relative relevance per intermediate!")
        print(f"  >>> Each fan-out saves LESS for CLIQUE than for MAJ")
        print(f"  >>> CLIQUE's potential is more 'rigid' — harder to recover")
        print(f"  >>> This supports: Φ_eff(CLIQUE) >> Φ_eff(MAJ)")
    else:
        print(f"\n  >>> CLIQUE has HIGHER relative relevance per intermediate")
        print(f"  >>> Fan-out is equally or more effective for CLIQUE")


if __name__ == "__main__":
    main()
