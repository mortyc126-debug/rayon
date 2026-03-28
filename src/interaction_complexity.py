"""
INTERACTION COMPLEXITY: A new measure for circuit lower bounds.

Discovery from n=3: k-wise interaction PERFECTLY predicts circuit size.
  - I₃ = 0 for all size-0 and size-1 functions
  - I₃ = 1.0 for ALL hardest (size-4) functions
  - Monotone increase in between

This suggests: k-wise interaction is the CORE QUANTITY that determines
circuit complexity. Let's verify for n=4 and develop the theory.

DEFINITION: k-wise interaction of f at subset S ⊆ [n], |S| = k:
  I_S(f) = (1/2^n) Σ_x |Σ_{T⊆S} (-1)^{|T|} f(x ⊕ χ_T)|

  This is the average absolute Möbius function over inputs.
  I_S > 0 means: the variables in S interact in a way that
  CANNOT be decomposed into lower-order interactions.

  Total k-interaction: I_k(f) = Σ_{|S|=k} I_S(f)

FOURIER CONNECTION:
  I_S(f) is related to the Fourier coefficient f̂(S).
  Specifically: Σ_{T⊆S} (-1)^{|T|} f(x ⊕ χ_T) = 2^k × f̂(S) × (-1)^{x·S}
  (for the ±1 convention of f).

  So I_S = 2^k × |f̂(S)|. And I_k = 2^k × Σ_{|S|=k} |f̂(S)|.

  I_k is the L1 NORM of the level-k Fourier spectrum, scaled by 2^k.

WHY THIS MIGHT GIVE CIRCUIT LOWER BOUNDS:
  Each gate (AND/OR) can "process" at most one new pairwise interaction.
  To create all necessary interactions, the circuit must perform enough operations.

  If the total interaction I = Σ_k I_k is large, the circuit must be large.

  KNOWN: L1 Fourier norm (spectral norm) ≤ circuit_size^{O(1)} × 2^{depth}.
  This gives polynomial lower bounds for bounded depth.
  For unbounded depth: no lower bound from spectral norm alone.

  BUT: our I_k is WEIGHTED by 2^k. Higher-order interactions count more.
  Maybe the WEIGHTED sum gives stronger lower bounds?
"""

from collections import defaultdict
from itertools import combinations
import time

def compute_truth_table(f_func, n):
    """Compute truth table of function f_func on n variables."""
    tt = 0
    for x in range(2**n):
        if f_func(x, n):
            tt |= (1 << x)
    return tt

def compute_all_circuit_sizes(n, verbose=False):
    """Compute minimum circuit size for all functions on n variables using BFS closure."""
    total = 2**(2**n)

    # Level 0: projections and their negations, constants
    level = {}
    cur = set()

    # Constants
    cur.add(0)
    cur.add(total - 1)

    # Projections and negations
    for i in range(n):
        tt = 0
        for x in range(2**n):
            if (x >> i) & 1:
                tt |= (1 << x)
        cur.add(tt)
        cur.add((total - 1) ^ tt)

    for tt in cur:
        level[tt] = 0

    s = 0
    while len(level) < total:
        s += 1
        new = set()
        existing = list(level.keys())

        for f in existing:
            not_f = (total - 1) ^ f
            if not_f not in level:
                new.add(not_f)
            for g in existing:
                and_fg = f & g
                or_fg = f | g
                if and_fg not in level and and_fg not in new:
                    new.add(and_fg)
                if or_fg not in level and or_fg not in new:
                    new.add(or_fg)

        if not new:
            break

        for tt in new:
            level[tt] = s

        if verbose:
            print(f"  Size {s}: {len(new)} new, {len(level)} total ({len(level)/total:.1%})")

        if s > 20:
            break

    return level

def fourier_coefficient(tt, S, n):
    """Compute Fourier coefficient f̂(S) using ±1 convention.
    f̂(S) = (1/2^n) Σ_x f(x) × (-1)^{x·S}
    where f is in {-1, +1}: f(x) = 1 - 2×bit(x)
    """
    total = 2**n
    coeff = 0
    S_mask = 0
    for i in S:
        S_mask |= (1 << i)

    for x in range(total):
        fx = 1 - 2 * ((tt >> x) & 1)  # convert {0,1} to {+1,-1}
        parity = bin(x & S_mask).count('1') % 2
        chi = 1 - 2 * parity  # (-1)^{x·S}
        coeff += fx * chi

    return coeff / total

def fourier_spectrum(tt, n):
    """Compute full Fourier spectrum."""
    spectrum = {}
    for k in range(n+1):
        for S in combinations(range(n), k):
            S_frozen = frozenset(S)
            spectrum[S_frozen] = fourier_coefficient(tt, S, n)
    return spectrum

def level_k_L1(tt, n, k):
    """L1 norm of level-k Fourier coefficients."""
    total = 0
    for S in combinations(range(n), k):
        coeff = fourier_coefficient(tt, S, n)
        total += abs(coeff)
    return total

def spectral_norm(tt, n):
    """L1 Fourier norm = Σ_S |f̂(S)|."""
    total = 0
    for k in range(n+1):
        total += level_k_L1(tt, n, k)
    return total

def weighted_interaction(tt, n):
    """Our new measure: Σ_k 2^k × L1(level k) = Σ_S 2^{|S|} |f̂(S)|."""
    total = 0
    for k in range(n+1):
        total += (2**k) * level_k_L1(tt, n, k)
    return total


# MAIN COMPUTATION
print("INTERACTION COMPLEXITY: Scaling to n=4")
print("=" * 65)
print()

# n=3 first (quick verification)
t0 = time.time()
print("n = 3: Computing circuit sizes...")
sizes3 = compute_all_circuit_sizes(3, verbose=True)
print(f"  Done in {time.time()-t0:.1f}s")
print()

# Analyze correlation between measures and circuit size
print("CORRELATION: Fourier measures vs circuit size (n=3)")
print(f"  {'size':>4} {'count':>6} {'L1 norm':>10} {'weighted I':>12} {'I_top':>10}")
print(f"  {'-'*48}")

by_size = defaultdict(list)
for tt, s in sizes3.items():
    by_size[s].append(tt)

for s in sorted(by_size.keys()):
    funcs = by_size[s]
    l1s = [spectral_norm(tt, 3) for tt in funcs]
    wis = [weighted_interaction(tt, 3) for tt in funcs]
    itops = [abs(fourier_coefficient(tt, (0,1,2), 3)) for tt in funcs]
    print(f"  {s:>4} {len(funcs):>6} {sum(l1s)/len(l1s):>10.3f} "
          f"{sum(wis)/len(wis):>12.3f} {sum(itops)/len(itops):>10.3f}")

# n=4
print()
t0 = time.time()
print("n = 4: Computing circuit sizes...")
sizes4 = compute_all_circuit_sizes(4, verbose=True)
print(f"  Done in {time.time()-t0:.1f}s")
print()

by_size4 = defaultdict(list)
for tt, s in sizes4.items():
    by_size4[s].append(tt)

print("CORRELATION: Fourier measures vs circuit size (n=4)")
print(f"  {'size':>4} {'count':>6} {'L1 norm':>10} {'weighted I':>12} {'I_top':>10}")
print(f"  {'-'*48}")

for s in sorted(by_size4.keys()):
    funcs = by_size4[s]
    # Sample if too many
    sample = funcs if len(funcs) <= 100 else [funcs[i] for i in range(0, len(funcs), len(funcs)//100)]

    l1s = [spectral_norm(tt, 4) for tt in sample]
    wis = [weighted_interaction(tt, 4) for tt in sample]
    itops = [abs(fourier_coefficient(tt, (0,1,2,3), 4)) for tt in sample]
    print(f"  {s:>4} {len(funcs):>6} {sum(l1s)/len(l1s):>10.3f} "
          f"{sum(wis)/len(wis):>12.3f} {sum(itops)/len(itops):>10.3f}")

print()

# KEY: Check if weighted interaction gives TIGHTER prediction than L1 norm
print("CRITICAL TEST: Does weighted interaction predict size BETTER than L1?")
print()

# Compute rank correlation
def rank_correlation(x_vals, y_vals):
    """Spearman rank correlation."""
    n = len(x_vals)
    ranked_x = sorted(range(n), key=lambda i: x_vals[i])
    ranked_y = sorted(range(n), key=lambda i: y_vals[i])
    rank_x = [0]*n
    rank_y = [0]*n
    for i, idx in enumerate(ranked_x): rank_x[idx] = i
    for i, idx in enumerate(ranked_y): rank_y[idx] = i
    d_sq = sum((rank_x[i] - rank_y[i])**2 for i in range(n))
    return 1 - 6*d_sq / (n * (n*n - 1))

# For n=3
all_tts_3 = list(sizes3.keys())
all_sizes_3 = [sizes3[tt] for tt in all_tts_3]
all_l1_3 = [spectral_norm(tt, 3) for tt in all_tts_3]
all_wi_3 = [weighted_interaction(tt, 3) for tt in all_tts_3]

rho_l1 = rank_correlation(all_l1_3, all_sizes_3)
rho_wi = rank_correlation(all_wi_3, all_sizes_3)
print(f"  n=3: Rank correlation with circuit size:")
print(f"    L1 norm (spectral):     ρ = {rho_l1:.4f}")
print(f"    Weighted interaction:   ρ = {rho_wi:.4f}")
print()

# For n=4 (sample)
sample4 = list(sizes4.keys())
if len(sample4) > 2000:
    import random
    random.seed(42)
    sample4 = random.sample(sample4, 2000)

all_sizes_4 = [sizes4[tt] for tt in sample4]
all_l1_4 = [spectral_norm(tt, 4) for tt in sample4]
all_wi_4 = [weighted_interaction(tt, 4) for tt in sample4]

rho_l1_4 = rank_correlation(all_l1_4, all_sizes_4)
rho_wi_4 = rank_correlation(all_wi_4, all_sizes_4)
print(f"  n=4: Rank correlation with circuit size (sample of {len(sample4)}):")
print(f"    L1 norm (spectral):     ρ = {rho_l1_4:.4f}")
print(f"    Weighted interaction:   ρ = {rho_wi_4:.4f}")

# Also check level-by-level
print()
print("  Level-by-level Fourier L1 correlation with size (n=4):")
for k in range(5):
    vals = [level_k_L1(tt, 4, k) for tt in sample4]
    rho = rank_correlation(vals, all_sizes_4)
    print(f"    Level {k}: ρ = {rho:.4f}")

print(f"""
THEORY BUILDING:
  If weighted interaction (WI) predicts circuit size better than L1:
  → Higher-order Fourier coefficients are MORE important for complexity
  → The 2^k weighting captures something fundamental

  NEXT: Can we prove WI(f) ≤ circuit_size(f)^c for some c?
  If so: WI lower bound → circuit size lower bound.

  For CLIQUE: WI should be exponentially large (all C(k,2) edges interact).
  If we can show WI(CLIQUE) ≥ 2^{{Ω(k)}} AND WI ≤ s^c:
  → s ≥ 2^{{Ω(k/c)}} → super-polynomial for k = ω(1).
""")
