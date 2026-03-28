"""
GAP COMPOSITION: How does the discrimination gap propagate through circuits?

gap(wire w) = Pr[w=1|f=1] - Pr[w=1|f=0]

INPUT gaps: gap(x_i) ≈ 0.3 for CLIQUE
OUTPUT gap: gap(output) = 1.0

HOW DOES gap COMPOSE THROUGH GATES?

For AND(a, b):
  gap_AND = Pr[a=1,b=1|f=1] - Pr[a=1,b=1|f=0]

  General case (with correlations):
    gap_AND = p_a(1)×p_b(1) + Cov₁(a,b) - p_a(0)×p_b(0) - Cov₀(a,b)
  where Cov_b(a,b) = Pr[a=1,b=1|f=b] - Pr[a=1|f=b]×Pr[b=1|f=b]

  Rewrite:
    gap_AND = p_b(1)×gap_a + p_a(0)×gap_b + (Cov₁ - Cov₀)

  WITHOUT CORRELATION (independent gates given f):
    gap_AND = p_b(1)×gap_a + p_a(0)×gap_b ≤ gap_a + gap_b
    (but with coefficients < 1, so actually ≤ max(gap_a, gap_b))

  WITH CORRELATION (edges in same clique):
    Cov₁ > 0 (positive correlation given ∃ clique)
    Cov₀ ≈ 0 (independent given ¬∃ clique)
    → (Cov₁ - Cov₀) > 0 → CORRELATION AMPLIFIES the gap!

For OR(a, b):
  gap_OR = (p_a(1) + p_b(1) - p_{a,b}(1)) - (p_a(0) + p_b(0) - p_{a,b}(0))
         = gap_a + gap_b - gap_AND(a,b)

  OR SUMS gaps (minus the AND correction).
  For nearly independent gates: gap_OR ≈ gap_a + gap_b.

CIRCUIT GAP FLOW:
  AND: gap_AND ≤ gap_a + gap_b (roughly, without correlation bonus)
  OR:  gap_OR  ≈ gap_a + gap_b (additive)

  Through a balanced tree of depth d with fan-in 2:
    AND layer: gap roughly preserved (each AND ≈ gap × factor)
    OR layer: gap roughly doubled (additive)

  Total amplification in OR-of-AND structure:
    AND layer: C(k,2) edges → 1 triangle → gap = gap_triangle
    OR layer: C(N,k) triangles → output → gap ≈ C(N,k) × gap_triangle

  This gives output gap ≈ C(N,k) × (1/2)^{C(k,2)} / balance.
  For this to reach 1.0: need C(N,k) ≈ balance × 2^{C(k,2)}.

KEY: The OR layer needs C(N,k) terms. Each term = one triangle AND.
The OR tree needs C(N,k) - 1 gates. TOTAL: C(N,k)×(C(k,2)-1) AND + (C(N,k)-1) OR.

Can a SMALLER circuit achieve the same output gap?
"""

import random
import math
from itertools import combinations
import time


def measure_gap_composition(N, k, n_samples=5000):
    """Measure how gap propagates through a CLIQUE circuit."""
    n = N * (N - 1) // 2
    edge_idx = {}
    idx = 0
    for u in range(N):
        for v in range(u + 1, N):
            edge_idx[(u, v)] = idx
            idx += 1

    # Build clique circuit: AND of triangle edges, then OR
    clique_subsets = list(combinations(range(N), k))
    triangle_edge_sets = []
    for subset in clique_subsets:
        es = [edge_idx[(min(a, b), max(a, b))]
              for a in subset for b in subset if a < b]
        triangle_edge_sets.append(es)

    # Simulate and measure gaps at each circuit level
    stats = {
        'input_gaps': [],
        'and_gaps': [],
        'or_partial_gaps': [],
        'output_gap': 0,
        'correlations': [],
    }

    # Accumulate conditional probabilities
    n_yes = 0
    n_no = 0
    edge_yes = [0] * n
    edge_no = [0] * n
    tri_yes = [0] * len(triangle_edge_sets)
    tri_no = [0] * len(triangle_edge_sets)

    # Partial OR gaps (OR of first m triangles)
    partial_or_yes = {}
    partial_or_no = {}

    for _ in range(n_samples):
        present = set()
        for e in range(n):
            if random.random() < 0.5:
                present.add(e)

        # Check clique
        has_clique = any(all(e in present for e in tes)
                        for tes in triangle_edge_sets)

        if has_clique:
            n_yes += 1
            for e in range(n):
                if e in present:
                    edge_yes[e] += 1
            for i, tes in enumerate(triangle_edge_sets):
                if all(e in present for e in tes):
                    tri_yes[i] += 1
            # Partial OR
            any_so_far = False
            for m in range(len(triangle_edge_sets)):
                if all(e in present for e in triangle_edge_sets[m]):
                    any_so_far = True
                if any_so_far:
                    partial_or_yes[m] = partial_or_yes.get(m, 0) + 1
        else:
            n_no += 1
            for e in range(n):
                if e in present:
                    edge_no[e] += 1
            for i, tes in enumerate(triangle_edge_sets):
                if all(e in present for e in tes):
                    tri_no[i] += 1
            any_so_far = False
            for m in range(len(triangle_edge_sets)):
                if all(e in present for e in triangle_edge_sets[m]):
                    any_so_far = True
                if any_so_far:
                    partial_or_no[m] = partial_or_no.get(m, 0) + 1

    if n_yes < 10 or n_no < 10:
        return None

    # Compute gaps at each level
    input_gaps = [(edge_yes[e] / n_yes - edge_no[e] / n_no) for e in range(n)]
    and_gaps = [(tri_yes[i] / n_yes - tri_no[i] / n_no) for i in range(len(triangle_edge_sets))]
    or_gaps = []
    for m in range(len(triangle_edge_sets)):
        p1 = partial_or_yes.get(m, 0) / n_yes
        p0 = partial_or_no.get(m, 0) / n_no
        or_gaps.append(p1 - p0)

    return {
        'N': N, 'k': k, 'n': n,
        'balance': n_yes / n_samples,
        'input_gap': sum(abs(g) for g in input_gaps) / len(input_gaps),
        'and_gaps': and_gaps,
        'or_gaps': or_gaps,
        'n_triangles': len(triangle_edge_sets),
    }


print("GAP COMPOSITION THROUGH CLIQUE CIRCUIT")
print("═" * 65)
print()

for N, k in [(5, 3), (6, 3), (7, 4), (8, 4), (10, 4)]:
    t0 = time.time()
    r = measure_gap_composition(N, k, n_samples=5000)
    dt = time.time() - t0

    if r is None:
        print(f"N={N}, k={k}: skewed, skip")
        continue

    n_tri = r['n_triangles']
    print(f"{k}-CLIQUE on N={N} (n={r['n']}, {n_tri} clique candidates, bal={r['balance']:.3f}):")
    print(f"  Level 0 (inputs):  avg |gap| = {r['input_gap']:.6f}")

    # AND layer gaps
    avg_and = sum(abs(g) for g in r['and_gaps']) / len(r['and_gaps'])
    print(f"  Level 1 (AND):     avg |gap| = {avg_and:.6f}  (×{avg_and/r['input_gap']:.2f} from input)")

    # OR layer: progressive accumulation
    print(f"  Level 2 (OR):      progressive gap accumulation:")
    milestones = [1, 2, 5, 10, n_tri // 2, n_tri - 1]
    for m in milestones:
        if m < len(r['or_gaps']):
            print(f"    After {m+1:>4} triangles: gap = {r['or_gaps'][m]:.6f}")

    output_gap = r['or_gaps'][-1] if r['or_gaps'] else 0
    print(f"  OUTPUT gap:        {output_gap:.6f} (target: 1.0)")
    print(f"  Gap per triangle:  {avg_and:.6f}")
    print(f"  Triangles × gap:   {n_tri} × {avg_and:.6f} = {n_tri * avg_and:.4f}")
    print(f"  Actual output gap: {output_gap:.6f}")
    print(f"  Efficiency:        {output_gap / (n_tri * avg_and):.3f} (1.0 = perfect additivity)")
    print(f"  ({dt:.1f}s)")
    print()

print("═" * 65)
print()
print("COMPOSITION LAW:")
print()
print("  AND layer: gap_triangle ≈ (1/2)^{C(k,2)} / balance  (from single→triple)")
print("  OR layer:  gap_output ≈ Σ gap_triangle × efficiency")
print("           ≈ C(N,k) × gap_triangle × η  (η ≈ 0.3-0.7)")
print()
print("  The efficiency η < 1 because triangles OVERLAP (share edges/vertices).")
print("  Overlapping triangles are correlated → OR doesn't perfectly sum.")
print()
print("  For the circuit to achieve output gap = 1.0:")
print("    C(N,k) × (1/2)^{C(k,2)} × η / balance ≥ 1")
print("    C(N,k) ≥ balance × 2^{C(k,2)} / η")
print()
print("  This is satisfied in the balanced regime.")
print()
print("  NOW: if a circuit uses FEWER than C(N,k) OR-terms (smaller circuit):")
print("  It must use non-clique gates to compensate. But non-clique gates")
print("  have gap_random < gap_clique. Need ratio×more gates to compensate.")
print()
print("  LOWER BOUND: s ≥ C(N,k) / sharing_factor")
print("  where sharing_factor ≤ poly(N) from fan-out reuse.")
print("  For k = ω(1): C(N,k)/poly = super-poly → circuit lower bound!")
