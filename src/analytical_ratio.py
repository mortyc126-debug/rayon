"""
ANALYTICAL GAP RATIO: Exact formula and verification.

DERIVED:
  gap_clique = 2^{-m} / p     where m = C(k,2), p = Pr[∃ k-clique]
  gap_random = 2^{-m} × ΔP(R) / (p(1-p))   where ΔP = Pr[clique|R] - p

  RATIO = (1-p) / ΔP(R)

  ΔP(R) = Pr[∃ k-clique | R ⊆ edges] - Pr[∃ k-clique]

For random R (m edges from n total):
  ΔP ≈ 2^{-m} × Σ_Q (2^{|E_Q ∩ R|} - 1)
     ≈ 2^{-m} × C(N,k) × (2^{E[overlap]} - 1)
  where E[overlap] = |E_Q| × |R| / n = m²/n

  For m²/n << 1: 2^{m²/n} - 1 ≈ ln(2) × m²/n

  ΔP ≈ C(N,k) × 2^{-m} × ln(2) × m² / n

  Using C(N,k) ≈ p × 2^m (from gap composition: total OR gap = 1):
  ΔP ≈ p × ln(2) × m² / n

  RATIO ≈ (1-p) × n / (p × ln(2) × m²)
        = (1-p) × C(N,2) / (p × ln(2) × C(k,2)²)

For balanced p ≈ 1/2:
  RATIO ≈ C(N,2) / (ln(2) × C(k,2)²)
        = N(N-1)/2 / (ln(2) × (k(k-1)/2)²)
        ≈ 2N² / (ln(2) × k⁴)

SCALING:
  k = N^{1/3}: ratio ≈ 2N² / (ln2 × N^{4/3}) = 2N^{2/3} / ln2 → ∞
  k = N^{1/2}: ratio ≈ 2N² / (ln2 × N²) = 2/ln2 ≈ const
  k fixed:     ratio ≈ 2N² / (ln2 × k⁴) → ∞

For k = O(N^{1/3}): ratio → ∞ means circuit MUST use clique-aligned gates.
This is the Razborov regime!
"""

import math
import random
from itertools import combinations
from collections import defaultdict
import time


def exact_gap_ratio(N, k, n_samples=10000):
    """Compute exact gap ratio by sampling."""
    n = N * (N - 1) // 2
    m = k * (k - 1) // 2

    edge_idx = {}; idx = 0
    for u in range(N):
        for v in range(u+1, N):
            edge_idx[(u,v)] = idx; idx += 1

    # All k-clique edge sets
    clique_sets = []
    for subset in combinations(range(N), k):
        es = frozenset(edge_idx[(min(a,b),max(a,b))]
                      for a in subset for b in subset if a < b)
        clique_sets.append(es)
    clique_frozen = set(clique_sets)

    # Sample non-clique sets
    non_clique_samples = []
    for _ in range(300):
        r = frozenset(random.sample(range(n), m))
        if r not in clique_frozen:
            non_clique_samples.append(r)
            if len(non_clique_samples) >= 50: break

    # Sample and compute
    n_yes = n_no = 0
    cliq_gap_num = [0] * min(30, len(clique_sets))
    nonc_gap_yes = defaultdict(int)
    nonc_gap_no = defaultdict(int)

    for _ in range(n_samples):
        present = frozenset(e for e in range(n) if random.random() < 0.5)
        has = any(cs <= present for cs in clique_sets)
        if has:
            n_yes += 1
            for i, cs in enumerate(clique_sets[:30]):
                if cs <= present: cliq_gap_num[i] += 1
            for i, ns in enumerate(non_clique_samples[:30]):
                if ns <= present: nonc_gap_yes[i] += 1
        else:
            n_no += 1
            for i, ns in enumerate(non_clique_samples[:30]):
                if ns <= present: nonc_gap_no[i] += 1

    if n_yes < 10 or n_no < 10:
        return None

    p = n_yes / n_samples
    # Clique gaps
    cliq_gaps = [cliq_gap_num[i]/n_yes for i in range(min(30, len(clique_sets)))]
    avg_cliq_gap = sum(cliq_gaps) / len(cliq_gaps)  # = 2^{-m}/p ≈

    # Non-clique gaps
    nc_gaps = []
    for i in range(min(30, len(non_clique_samples))):
        py = nonc_gap_yes.get(i, 0) / n_yes
        pn = nonc_gap_no.get(i, 0) / n_no
        nc_gaps.append(py - pn)
    avg_nc_gap = sum(abs(g) for g in nc_gaps) / len(nc_gaps) if nc_gaps else 1e-10

    # Measured ratio
    measured_ratio = avg_cliq_gap / avg_nc_gap if avg_nc_gap > 1e-10 else float('inf')

    # Theoretical prediction
    # ratio ≈ (1-p) × n / (p × ln2 × m²)
    if p > 0 and p < 1:
        predicted_ratio = (1 - p) * n / (p * math.log(2) * m * m)
    else:
        predicted_ratio = float('inf')

    # Also compute ΔP directly for verification
    # ΔP ≈ p × ln2 × m² / n
    predicted_delta_p = p * math.log(2) * m * m / n
    actual_delta_p = (1 - p) / measured_ratio if measured_ratio > 0 else 0

    return {
        'N': N, 'k': k, 'n': n, 'm': m, 'p': p,
        'measured_ratio': measured_ratio,
        'predicted_ratio': predicted_ratio,
        'pred_delta_p': predicted_delta_p,
        'actual_delta_p': actual_delta_p,
        'avg_cliq_gap': avg_cliq_gap,
        'avg_nc_gap': avg_nc_gap,
    }


print("ANALYTICAL GAP RATIO: Formula vs Data")
print("═" * 75)
print()
print("Formula: ratio ≈ (1-p) × C(N,2) / (p × ln2 × C(k,2)²)")
print()
print(f"{'N':>4} {'k':>3} {'m':>4} {'p':>6} {'measured':>10} {'predicted':>10} "
      f"{'pred/meas':>10} {'ΔP_meas':>10} {'ΔP_pred':>10}")
print("-" * 75)

configs = [(5,3), (6,3), (7,3), (7,4), (8,4), (9,4), (10,4), (10,5), (12,5), (15,6)]

for N, k in configs:
    r = exact_gap_ratio(N, k, n_samples=8000)
    if r is None:
        print(f"{N:>4} {k:>3} (skewed, skip)")
        continue

    accuracy = r['predicted_ratio'] / r['measured_ratio'] if r['measured_ratio'] > 0 else 0
    print(f"{r['N']:>4} {r['k']:>3} {r['m']:>4} {r['p']:>6.3f} "
          f"{r['measured_ratio']:>10.3f} {r['predicted_ratio']:>10.3f} "
          f"{accuracy:>10.3f} {r['actual_delta_p']:>10.6f} {r['pred_delta_p']:>10.6f}")

print(f"""
═══════════════════════════════════════════════════════════════════
SCALING PREDICTIONS:

  ratio ≈ (1-p) × N² / (2p × ln2 × C(k,2)²)

  k fixed (k=3):  ratio ∝ N²    → grows quadratically
  k = N^{{1/3}}:    ratio ∝ N^{{2/3}} → grows sub-linearly
  k = N^{{1/2}}:    ratio ∝ const   → stays bounded
  k = N^{{2/3}}:    ratio ∝ N^{{-2/3}} → shrinks

  CRITICAL REGIME: k = O(N^{{1/2}}).
  For k < √N: ratio grows → clique gates NEEDED → lower bound works
  For k > √N: ratio shrinks → non-clique gates might suffice

  FOR P ≠ NP: Need ratio → ∞ with super-poly C(N,k).
  k = N^{{1/3}}: ratio ∝ N^{{2/3}}, C(N,k) ≈ N^k/k! → super-poly. ✓
  k = N^{{1/4}}: ratio ∝ N^{{3/2}}, C(N,k) → super-poly. ✓

  LOWER BOUND (informal):
  circuit_size ≥ C(N,k) / (ratio × sharing_factor)
  For k = N^{{1/3}}: ≥ N^{{N^{{1/3}}}} / (N^{{2/3}} × poly(N)) = SUPER-POLYNOMIAL

  This relies on sharing_factor = poly(N), which is the Razborov
  monotone argument. For GENERAL circuits: sharing_factor might be
  exponential (via NOT gates). THIS is the remaining gap.
""")
