"""
FATAL FLAW IN RESIDUAL FORMULA ARGUMENT: Restriction makes CLIQUE EASY.

Two regimes, both fatal:

REGIME 1 (k = Θ(√N) or larger):
  Alon-Boppana gives 2^{Ω(√N)} monotone formula lower bound.
  BUT: random half-restriction makes CLIQUE trivially 0 (no surviving cliques).
  Trivial function → complexity O(1). No lower bound.

REGIME 2 (k = O(1) constant):
  Random restriction preserves non-triviality (many k-cliques survive).
  Alon-Boppana FULL CLIQUE: 2^{Ω(√N)}.
  BUT: RESTRICTED CLIQUE = polynomial-size monotone DNF!

  PROOF for Regime 2:
    After restriction, each candidate k-clique S either:
    - Has some edge fixed to 0 → impossible (eliminated)
    - Has all edges either free or fixed to 1 → S survives

    f_restricted(x_free) = OR_{S surviving} AND_{(u,v)∈S, (u,v) free} x_{u,v}

    This is a MONOTONE DNF with:
    - Number of terms: C(N,k) × (3/4)^{C(k,2)} = Θ(N^k) (for constant k)
    - Width per term: ≤ C(k,2) = O(1) (for constant k)

    Monotone formula complexity ≤ O(N^k × k²) = poly(N).

  CONCLUSION: Restriction drops complexity from 2^{Ω(√N)} to poly(N).

BOTH REGIMES KILL THE ARGUMENT:
  - Large k: function trivially 0, complexity O(1)
  - Small k: function non-trivial but EASY (poly DNF), complexity poly(N)

  In both cases: s/9 ≥ poly(N) → s ≥ poly(N). No super-poly bound.

THIS IS NOT A TECHNICALITY — it's a deep structural reason why
"partially evaluate then argue hardness of residual" fails for CLIQUE.

CLIQUE is simultaneously:
  - HARD to compute from scratch (exponential monotone complexity)
  - EASY to compute after partial information (polynomial DNF after restriction)

This gap between full and restricted complexity is EXACTLY what the
residual formula approach cannot bridge.
"""

import math

print("RESTRICTION KILLS RESIDUAL FORMULA ARGUMENT")
print("=" * 60)
print()

# Regime 1: Large k — restriction makes function trivially 0
print("REGIME 1: k = √N — Restriction kills all cliques")
print("-" * 60)
print(f"{'N':>6} {'k':>4} {'C(k,2)':>7} {'E[survivors]':>14} {'status':>12}")
print("-" * 50)

for N in [20, 50, 100, 200, 500, 1000, 5000]:
    k = max(3, int(math.sqrt(N)))
    ck2 = k*(k-1)//2
    log_comb = sum(math.log(N-i) - math.log(i+1) for i in range(k))
    log_surv = ck2 * math.log(3/4)
    log_E = log_comb + log_surv
    E = math.exp(log_E) if log_E < 300 else float('inf')
    E_str = f"{E:.1e}" if E > 0.01 else f"exp({log_E:.0f})"
    status = "TRIVIAL" if log_E < 0 else "non-trivial"
    print(f"{N:>6} {k:>4} {ck2:>7} {E_str:>14} {status:>12}")

print()
print("  For large N with k=√N: E[survivors] → 0 → function is 0 identically")
print()

# Regime 2: Small constant k — function non-trivial but EASY
print("REGIME 2: k constant — Restricted CLIQUE = poly-size DNF")
print("-" * 60)

for k in [3, 5, 10]:
    print(f"\n  k = {k}: C(k,2) = {k*(k-1)//2} edges per clique")
    print(f"  {'N':>6} {'candidates':>12} {'surviving':>12} {'free edges/term':>16} {'DNF size':>12} {'Alon-Bop':>12}")
    print(f"  {'-'*70}")

    ck2 = k*(k-1)//2
    surv_prob = (3/4)**ck2  # prob no edge fixed to 0
    avg_free = ck2 * 0.5    # expected free edges per surviving clique

    for N in [20, 50, 100, 500, 1000]:
        if k > N: continue
        log_comb = sum(math.log(N-i) - math.log(i+1) for i in range(k))
        candidates = math.exp(log_comb)
        surviving = candidates * surv_prob
        dnf_size = surviving * avg_free  # terms × width
        alon_bop = 2**(0.1 * math.sqrt(N))  # 2^{Ω(√N)}

        print(f"  {N:>6} {candidates:>12.0f} {surviving:>12.0f} {avg_free:>16.1f} "
              f"{dnf_size:>12.0f} {alon_bop:>12.0f}")

print(f"""
KEY COMPARISON for k=10, N=1000:
  Full CLIQUE monotone formula:     2^{{Ω(√1000)}} ≈ 2^{{31}} ≈ 2×10⁹
  Restricted CLIQUE DNF complexity: O(N^10) = 10^{{30}}

  Wait — N^k can be huge too! Let me re-examine...
""")

# Actually N^k for k=10 is huge. The point is it's POLYNOMIAL in N.
# And the Alon-Boppana bound is EXPONENTIAL in √N ≈ N^{0.5}.
# For N^10 vs 2^{√N}: eventually 2^{√N} > N^10 (when √N > 10 log₂ N).

print("Restricted vs Full complexity:")
print(f"{'N':>6} {'N^k (k=10)':>15} {'2^(√N/10)':>15} {'restricted < full?':>20}")
print("-" * 60)
for N in [100, 1000, 10000, 100000]:
    nk = N**10
    alon = 2**(math.sqrt(N)/10)
    print(f"{N:>6} {nk:>15.2e} {alon:>15.2e} {'YES' if nk < alon else 'no':>20}")

print(f"""
For k = 10:
  - Restricted CLIQUE has DNF of size ≈ N^10 (polynomial in N)
  - Full CLIQUE has monotone formula ≥ 2^{{Ω(√N)}} (exponential in √N)
  - For N > 10^20: 2^{{√N}} >> N^10, so restriction EXPONENTIALLY simplifies

  The residual formula argument needs: restricted ≥ 2^{{Ω(√N)}}
  Reality: restricted ≤ O(N^10) << 2^{{Ω(√N)}}

  GAP: exponential! The restriction makes CLIQUE EXPONENTIALLY easier.

CONCLUSION:
  The residual formula argument FAILS because:
  1. After fixing half the edge variables, remaining CLIQUE is a
     polynomial-size monotone DNF (for constant k)
  2. Or trivially zero (for k ≈ √N)
  3. In neither case is the restricted function super-polynomially hard
  4. s/9 ≥ poly(N) gives only s ≥ poly(N), no super-poly lower bound

  DEEPER LESSON: CLIQUE's hardness is "brittle" — it depends on the
  GLOBAL structure of all edges, and partial information collapses
  the combinatorial explosion that makes it hard.

  This is related to why CLIQUE has small depth-3 circuits after
  random restrictions (Håstad's switching lemma). Random restrictions
  turn hard functions into easy ones — this is a FEATURE of NP-hard
  problems, not a bug.

STATUS OF ALL P ≠ NP APPROACHES:
  ✗ Cascade + residual: restriction makes CLIQUE easy
  ✗ Meta-theorem: no composition-based measure in the gap
  ✗ Damping barrier: information decays exponentially
  ✗ NEXP proof: cascade gives polynomial saving, not super-poly

  All four approaches hit fundamental barriers.
  The problem remains OPEN.
""")
