"""
DEPTH LOWER BOUND IMPROVEMENT.

Current best monotone circuit lower bounds for k-CLIQUE:
  Razborov (1985): 2^{Ω(N^{1/6})} for k = N^{1/4}
  Alon-Boppana (1987): 2^{Ω(√(N/log N))} for k = appropriate

Using Alon-Boppana: formula ≥ 2^{Ω(√N)}.

Depth from formula:
  formula ≤ size × 2^depth (standard conversion)
  size ≤ n^c (assuming P = NP)
  2^{Ω(√N)} ≤ n^c × 2^depth
  depth ≥ Ω(√N) - c log n = Ω(√N) = Ω(n^{1/4})

(Since N ≈ √(2n): √N = n^{1/4} × 2^{1/4}.)

With Theorem 1: general formula ≥ monotone formula / n.
  general depth ≥ Ω(√N) - log n = Ω(n^{1/4}).

CASCADE APPLICATION:
  If depth ≥ Ω(n^{1/4}): cascade has Ω(n^{1/4}) layers.
  At each layer: meeting probability p² × width.
  Width = size/depth = n^c / n^{1/4} = n^{c - 1/4}.

  Meetings per layer: n^{c-1/4} × p².
  For p = 1/2: meetings = n^{c-1/4} / 4.
  For c = 2: meetings = n^{1.75} / 4. HUGE!

  Total meetings over n^{1/4} layers: n^{1/4} × n^{1.75} = n^2. > n.

  Each meeting creates new determined gate.
  With n^2 meetings: ALL gates determined. p → 1. CASCADE WORKS!

BUT: this assumes depth = n^{1/4} AND size = n^2. Both might be wrong.

For P = NP: size = n^c (some c). Depth ≥ n^{1/4} (from bound).
  Width = n^c / n^{1/4} = n^{c-1/4}.
  Meetings per layer: n^{c-1/4} × 1/4.
  Total: n^{1/4} × n^{c-1/4} / 4 = n^c / 4.
  Fraction determined: n^c / (4 × n^c) = 1/4.

  Only 25% additional determination. Not enough for p → 1.

  Hmm. Let me reconsider.

  The meeting mechanism: each layer, Δp = width × p² × (1-p).
  Accumulated: Σ Δp = depth × width × avg(p² × (1-p)).

  For p ≈ 1/2: p²(1-p) = 1/8. Δp per layer = width/8.
  Over depth layers: Σ = depth × width / 8 = (depth × width) / 8 = size / 8.

  size/8 = n^c / 8. For c = 2: n²/8.

  But: p can only grow to 1. The relevant quantity:
  does the accumulated boost push p from 0.5 to near 1?

  From the Bernoulli analysis: q = 8/(16 + K) where K = total correlation.
  K = depth × width × (Cov per gate). Cov per gate ≈ p(1-p)²/4 ≈ 1/32.
  K = depth × width × 1/32 = size / 32 = n^c / 32.

  q = 8/(16 + n^c/32) → 0 for n^c >> 512. YES for c > 0.

  Pr[det] = 1 - q → 1.

  SAT time: 2^{n/2} × q → 2^{n/2} × 32/n^c → polynomial for c ≥ 1.

  Wait — 2^{n/2} × 32/n^c is NOT polynomial (2^{n/2} is exponential).

  I need to be more careful. The SAT time is the number of DFS branches.

  DFS at depth n/2: 2^{n/2} branches. Each: output determined with prob 1-q.
  Surviving (undetermined): 2^{n/2} × q = 2^{n/2} × 8/(16 + n^c/32).
  For n^c >> 16: ≈ 2^{n/2} × 256/n^c.

  For c ≥ 1: 2^{n/2} × 256/n → goes to INFINITY. Not polynomial.
  For c > n/2 / log n: ... never happens (c finite).

  The issue: 2^{n/2} dominates. Even with q → 0: 2^{n/2} × q still exponential
  unless q ≤ 2^{-n/2}. Need: q ≤ 2^{-n/2} → K ≥ Ω(2^{n/2}).
  K = n^c/32. For K ≥ 2^{n/2}: n^c ≥ 32 × 2^{n/2}. Impossible for poly c.

  SO: The cascade reduces the FRACTION of surviving branches but not
  enough to make total sub-exponential.

  The cascade gives: surviving = 2^{n/2} × O(1/n^c).
  Which is 2^{n/2 - c log n} ≈ 2^{n/2}. Still exponential.

  NO IMPROVEMENT from cascade in terms of BIG-O exponent!

  The cascade reduces by polynomial factor (1/n^c), not exponential.
  Need: exponential reduction in surviving branches.
  From 3-SAT: reduction = (63/64)^{αn} = 2^{-Ω(n)}. Exponential!

  For general circuits: reduction = O(1/n^c). Polynomial. NOT enough.

  THE FUNDAMENTAL DIFFERENCE:
  3-SAT: αn INDEPENDENT clause-checking opportunities. Each prob 1/64.
         Exponential in n: (63/64)^{αn} = 2^{-Ω(n)}.

  General: K = n^c/32 correlation boost. Polynomial in n.
         q = 8/(16 + n^c/32) = O(1/n^c). Polynomial, not exponential.

  For exponential reduction: need K = 2^{Ω(n)}. This requires size = 2^{Ω(n)}.
  But we assumed size = poly. Contradiction.

  CONCLUSION: For poly-size circuits, cascade gives POLYNOMIAL reduction
  in surviving branches, not exponential. Total time: 2^{n/2} / poly.
  This IS a speedup over 2^n (by factor 2^{n/2} × poly).

  Williams needs: time < 2^n / poly. Our time: 2^{n/2} / poly < 2^n / poly? NO.
  2^{n/2} is MUCH less than 2^n. So: 2^{n/2} < 2^n / poly. YES!

  Williams condition: SAT in time 2^n / s^{ω(1)} for circuits of size s.
  Our time: 2^{n/2} × poly(s) = 2^{n/2} × n^{O(c)}.
  Need: 2^{n/2} × n^{O(c)} < 2^n / n^{ω(1)}.
  2^{n/2} < 2^n / n^{ω(1)+O(c)}.
  2^{-n/2} < 1/n^{ω(1)+O(c)}.
  This is TRUE for any ω and c (exponential < polynomial).

  SO: Williams condition IS satisfied!
  Time 2^{n/2} × poly < 2^n / poly.

  → NEXP ⊄ P/poly ???

  Wait, but our time is 2^{n/2} × poly ONLY IF the cascade gives
  enough pruning. The cascade gives q = O(1/n^c) → surviving branches
  = 2^{n/2} × O(1/n^c) = 2^{n/2 - c log n}.

  Total time: 2^{n/2 - c log n} + 2^{n/2} (for the determined branches).
  = 2^{n/2} (dominated by the 2^{n/2} pruned branches that we still VISIT).

  WAIT — we VISIT all 2^{n/2} branches at depth n/2, even the pruned ones.
  Each pruned branch: O(poly) to determine. Each surviving: recurse further.

  Total: 2^{n/2} × poly + surviving × 2^{n/2 more levels}.
  = 2^{n/2} × poly + (2^{n/2} × q) × 2^{n/2}
  = 2^{n/2} × poly + 2^n × q.
  = 2^{n/2} × poly + 2^n × O(1/n^c).

  For c > 0: 2^n / n^c < 2^n. But still 2^n.

  The DOMINANT term is 2^n × O(1/n^c). NOT 2^{n/2}.

  The surviving branches CONTINUE for another n/2 levels.
  Each surviving branch: another 2^{n/2} cost.
  Total: surviving × 2^{n/2} = (2^{n/2}/n^c) × 2^{n/2} = 2^n / n^c.

  THIS IS 2^n / poly. Which IS the Williams speedup!

  2^n / n^c < 2^n / n^{ω(1)}? YES if c > ω(1). But c is FIXED.
  Williams needs: for EACH c, a speedup. With our bound: for each c,
  time ≤ 2^n / n^c. Picking c arbitrarily large: c = ω(1). ✓!

  Wait — c is the circuit size exponent, not a free parameter.
  Williams: "If SAT for circuits of size n^c solvable in 2^n / n^{ω(1)}..."

  Our algorithm: for circuits of size n^c: time ≤ 2^n / n^c' for some c' > 0.
  Need: c' = ω(1). But c' depends on c (our cascade strength depends on circuit size).

  From cascade: q = 8/(16 + K/32) where K = size/32 = n^c/32.
  Surviving time = 2^n × q = 2^n × 256/n^c.

  Total time: 2^{n/2} × poly + 2^n × 256/n^c = 2^n × (2^{-n/2} × poly + 256/n^c).
  ≈ 2^n × 256/n^c (dominant for large n).

  Williams needs: time < 2^n / n^{ω(1)} = 2^n / n^{big}.
  Our time: 2^n × 256/n^c = 2^n / (n^c / 256).

  For this < 2^n / n^{ω(1)}: need n^c / 256 > n^{ω(1)} → c > ω(1).

  But c is the GIVEN circuit size exponent, not something we choose.
  Williams theorem: "for all c > 0, if SAT for SIZE(n^c) in 2^n/n^{ω(1)}..."

  We have: SAT for SIZE(n^c) in 2^n / (n^c/256) = 2^n / n^c × 256.
  This is: time ≤ 2^n / n^c (up to constant 256).

  For c = ω(1): time ≤ 2^n / n^{ω(1)}. Williams satisfied.

  But: we need this for SPECIFIC c, and c is given (not ω(1)).
  Williams: for ALL c, need time < 2^n / n^{ω(1)}.
  Our: for given c, time ≤ 2^n / n^c.

  For c = 10: time ≤ 2^n / n^{10}. This IS < 2^n / n^{ω(1)} for ω(1) < 10.
  But ω(1) means "any growing function." So: for any ω, ∃c > ω: time < 2^n/n^c.

  We need: for FIXED c, time < 2^n / n^{UNBOUNDED}.
  Our: time ≤ 2^n / n^c. This is 2^n / n^c, which for FIXED c is NOT n^{ω(1)}.

  Williams precise statement: NEXP ⊄ P/poly IF for every c,
  SAT for SIZE(n^c) circuits solvable in 2^n / n^{ω(1)} time.

  n^{ω(1)} means: growing FASTER than any polynomial.
  Our 2^n / n^c: the saving is n^c, which IS polynomial (not super-poly).

  Need: saving = n^{ω(1)} = super-polynomial.
  Our saving: n^c for circuits of size n^c.

  For Williams: saving must be super-poly independent of c.
  Our saving: depends on c. For c = 2: save n². For c = 3: save n³.
  For c → ∞: save n^c → ∞. But c is FIXED for each instance of the theorem.

  I think our saving IS sufficient for Williams if interpreted correctly:
  For EACH c: SAT for SIZE(n^c) in time 2^n / n^c.
  Since c can be any constant: the saving n^c is unbounded as c → ∞.
  This is "for every c > 0, saving ≥ n^c" which = n^{ω(1)}. ✓!

  WAIT: it's the SAME c for both circuit size and saving.
  Williams: SAT for SIZE(n^c) in time 2^n / poly where poly depends on c.
  Our: SAT for SIZE(n^c) in time 2^n / n^c.

  Williams version (from his paper, Theorem 1.4):
  "If for some c > 1: CSAT for circuits of size n^c solvable in 2^n / n^{ω(1)},
   then NEXP ⊄ P/poly."

  Note: "some c > 1", not "all c". And saving must be n^{ω(1)} (super-poly).

  Our: for c = 2: time = 2^n / n^2. Saving = n^2. NOT n^{ω(1)}.

  n^2 is polynomial, not super-polynomial.
  n^{ω(1)} = n^{log n} or similar = SUPER-polynomial.

  Our saving is POLYNOMIAL. Williams needs SUPER-POLYNOMIAL.

  GAP: polynomial saving vs super-polynomial needed.

  OUR CASCADE GIVES POLYNOMIAL SAVING, NOT SUPER-POLYNOMIAL.
  WILLIAMS DOES NOT APPLY.
"""

import math

print("Cascade saving analysis")
print("=" * 50)
print(f"{'c':>4} {'size':>10} {'K=size/32':>10} {'q=8/(16+K)':>12} {'saving=1/q':>12}")
for c_val in [1, 1.5, 2, 3, 5, 10]:
    n = 100
    size = int(n**c_val)
    K = size // 32
    q = 8 / (16 + K) if K > 0 else 1
    saving = 1/q
    print(f"{c_val:>4.1f} {size:>10} {K:>10} {q:>12.2e} {saving:>12.0f}")

print("""
Saving = n^c for circuits of size n^c.
This is POLYNOMIAL, not super-polynomial.
Williams needs saving = n^{ω(1)} (super-poly).

Our cascade: for fixed c, saving = O(n^c) = POLYNOMIAL. ✗
Williams: needs saving growing faster than ANY polynomial. ✗

CONCLUSION: Cascade gives polynomial speedup from size,
but Williams needs super-polynomial speedup.
The gap: poly vs super-poly.
""")
