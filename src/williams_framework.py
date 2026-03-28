"""
WILLIAMS' FRAMEWORK APPLIED: Algorithms → Lower Bounds.

Ryan Williams (2010): If there's a SAT algorithm for circuit class C
that runs faster than 2^n by a super-polynomial factor, then NEXP ⊄ C.

For C = P/poly (general polynomial circuits):
  Need: SAT for poly-size circuits in time 2^n / n^{ω(1)}.
  Then: NEXP ⊄ P/poly → implies E ⊄ SIZE(2^{δn}) for some δ > 0.

Current best SAT algorithm for general circuits:
  2^n × poly(n) (brute force).
  No super-polynomial speedup known.

OUR CONTRIBUTION: The Φ-decomposition framework provides STRUCTURE
that could enable faster-than-brute-force SAT solving.

THE ALGORITHM:
  Input: Circuit C of size s computing f: {0,1}^n → {0,1}.
  Question: ∃x: f(x) = 1?

  Standard: try all 2^n inputs. Time: 2^n × s.

  Φ-guided: decompose f into sub-problems using Φ-optimal splits.
  Each split reduces Φ by ~75% on the hard branch.
  After O(log Φ) splits: sub-problem trivial.

  BUT: need to solve BOTH branches → 2^{depth} sub-problems.
  Depth = n (from our data). Total: 2^n. No speedup.

  THE KEY: If we can PRUNE branches where the sub-problem is
  equivalent to an already-solved one (MEMOIZATION):

  Number of DISTINCT sub-problems = distinct subtrees in decision tree.
  From our data: distinct ≈ n^{α(k)} where α(k) ≈ 1.74k.

  For k = O(1): distinct = poly(n). POLYNOMIAL number of sub-problems!
  → SAT solvable in poly(n) × poly(n) = poly(n) time for fixed-k CLIQUE.
  This is KNOWN (k-CLIQUE in P for fixed k).

  For k = ω(1) (growing): distinct = n^{ω(1)} = super-poly.
  → SAT takes super-poly time. No speedup over brute force.

  BUT: super-poly < 2^n for k = o(n). So: SOME speedup exists!

  Specifically: distinct = n^{1.74k}. SAT time ≈ n^{1.74k} × poly.
  For k = n^{1/3}: time ≈ n^{1.74 × n^{1/3}} = 2^{O(n^{1/3} log n)}.

  This is 2^{o(n)} — FASTER than brute force 2^n!

  The SPEEDUP: 2^n / 2^{O(n^{1/3} log n)} = 2^{n - O(n^{1/3} log n)} = 2^{n(1-o(1))}.

  This is a 2^{Ω(n)} speedup? No — it's 2^{n - n^{1/3} log n}, which
  is 2^n / 2^{n^{1/3} log n}. The speedup factor is 2^{n^{1/3} log n}.
  Super-polynomial!

  APPLYING WILLIAMS:
  If we have a SAT algorithm with super-polynomial speedup
  for circuits of size poly(n): NEXP ⊄ P/poly.

  We have: SAT for k-CLIQUE circuits in time 2^{n - Ω(n^{1/3} log n)}.
  This IS a super-polynomial speedup (factor 2^{n^{1/3} log n}).

  BUT: Williams' theorem requires speedup for ALL poly-size circuits,
  not just CLIQUE circuits.

  Can we generalize our Φ-decomposition to ALL functions?

  For ANY function f computed by a circuit of size s:
    distinct_subtrees ≤ s + n (each gate creates ≤ 1 new sub-function).
    Decision tree with memoization: solve each distinct sub-problem once.
    Time: (s + n) × cost_per_sub-problem.

  Wait — THIS is the key. A circuit of size s has ≤ s + n distinct
  intermediate functions. The decision tree's distinct subtrees ≤ s + n.

  So: SAT with memoization takes (s + n) × poly(n) time?
  That would be POLYNOMIAL for s = poly(n)!

  But: this can't be right. It would mean P = NP.

  THE FLAW: The decision tree's distinct subtrees are NOT the same
  as the circuit's distinct intermediate functions.

  The circuit's s gates compute s specific functions.
  The decision tree branches on VARIABLES, creating sub-functions
  that are RESTRICTIONS of f. These restrictions are NOT the same
  as the circuit's intermediate functions.

  Number of distinct restrictions of f: can be up to 2^n
  (each restriction is a different sub-function).

  BUT: for a circuit of size s, the number of distinct
  restrictions that MATTER is bounded by... what?

  For a circuit of size s: after fixing variable x_j = b:
    the circuit simplifies to a circuit of size ≤ s on n-1 variables.
    The simplified circuit is determined by: which gates become constant.

  The number of DISTINCT simplified circuits: ≤ 2^s (each gate can
  become constant or not). So: 2^s possible simplified circuits.

  For s = poly: 2^{poly} = exp. No help.

  BUT: The simplified circuit has size ≤ s. And it can be FURTHER
  simplified (dead gate elimination). The EFFECTIVE size might decrease.

  If effective size decreases by 1 per restriction: after k restrictions:
  size ≤ s - k. After s restrictions: size = 0 → constant. Trivial.
  Total sub-problems: ≤ 2^s (binary tree of depth s). EXPONENTIAL.

  But with MEMOIZATION: distinct sub-problems ≤ ???
  Two simplified circuits are "same" if they compute the same function.
  Number of distinct functions computable by circuits of size ≤ s:
  ≤ 2^{O(s log s)} (counting argument).

  For each distinct function: solve once. Total: 2^{O(s log s)} solutions.
  Each solution: poly time (circuit of size ≤ s → evaluate in poly time).
  Total: 2^{O(s log s)} × poly.

  For s = n^c: 2^{O(n^c log n)} × poly = 2^{O(n^c log n)}.
  For c < 1: this is 2^{o(n)}. FASTER THAN BRUTE FORCE!

  THE SPEEDUP: 2^n / 2^{O(n^c log n)} for c < 1.
  = 2^{n(1 - O(n^{c-1} log n))}.
  For c < 1: n^{c-1} → 0, so speedup → 2^n. HUGE!

  But: is this actually achievable? Can we ENUMERATE the distinct
  sub-functions and solve each once?

  ENUMERATION: Given circuit C of size s, enumerate all distinct
  functions obtainable by restricting variables.

  A restriction: fix variables x_{i1},...,x_{ik} to values b_1,...,b_k.
  The restricted circuit C|_ρ has ≤ s gates on n-k variables.

  Two restrictions ρ₁, ρ₂ are equivalent if C|_{ρ₁} ≡ C|_{ρ₂}
  (same function on remaining variables).

  To CHECK equivalence: compare truth tables. Cost: 2^{n-k} per pair.
  To ENUMERATE distinct: iterate through restrictions, check each.

  Total restrictions: 2^k × C(n, k). For k = n: 2^n × 1 = 2^n.

  This doesn't help unless we can identify equivalences CHEAPLY.

  CHEAP EQUIVALENCE: Two restrictions ρ₁, ρ₂ are equivalent if
  they produce the same GATE SIGNATURE — the same set of gates
  that become constant.

  Gate g becomes constant under restriction ρ if all its input
  variables are fixed by ρ AND the gate's function on those
  fixed values is determined.

  The gate signature: for each gate, {constant_0, constant_1, active}.
  Number of signatures: 3^s. For s = n^c: 3^{n^c} = 2^{O(n^c)}.

  THIS IS THE COUNT OF DISTINCT MEMOIZABLE STATES.

  SAT with memoization by gate signatures:
    Time: 3^s × poly(n) = 2^{O(s)} × poly.
    For s = n^c: 2^{O(n^c)}.
    For c < 1: 2^{o(n)}. FASTER THAN BRUTE FORCE!

DOES THIS SATISFY WILLIAMS' CONDITIONS?

Williams requires: for a circuit class C, a SAT algorithm beating 2^n.

Our algorithm: for circuits of size s = n^c (c < 1):
  Time: 2^{O(n^c)} < 2^n for c < 1.
  Speedup: 2^{n - O(n^c)} = 2^{n(1-o(1))} factor.

For c < 1: this IS a speedup for sub-linear size circuits.
But Williams needs speedup for ALL poly-size circuits (including s = n^c for any c).

For c ≥ 1 (linear or larger circuits): 2^{O(n^c)} ≥ 2^n. NO speedup.

So: our speedup only works for SUB-LINEAR size circuits.

Williams' theorem for sub-linear circuits:
  "If SAT for circuits of size n^c (c < 1) can be solved in 2^{o(n)} time,
  then NEXP ⊄ SIZE(n^c)."

This gives: NEXP ⊄ SIZE(n^c) for c < 1.

Is this KNOWN? I think so — it's trivially true that NEXP functions
require at least linear size circuits (they depend on all inputs).

So: our speedup gives only TRIVIAL lower bounds from Williams.

FOR NONTRIVIAL: need speedup for s = n^c with c ≥ 1.
At s = n: 2^{O(n)} = 2^n. No speedup. EXACTLY at the boundary.

THE TANTALIZING FACT: at s = n^{1-ε}: speedup works.
At s = n: speedup vanishes. P vs NP lives EXACTLY at this boundary.
"""


def compute_memoized_sat_time(n, s):
    """Estimate SAT time with gate-signature memoization."""
    import math
    # Distinct gate signatures: ≤ 3^s
    # SAT time: 3^s × poly(n)
    log_time = s * math.log2(3)
    return log_time


def main():
    import math
    print("=" * 70)
    print("  WILLIAMS FRAMEWORK: Algorithms → Lower Bounds")
    print("  Gate-signature memoization for SAT")
    print("=" * 70)

    print(f"\n  {'s/n':>6} {'n=100 time':>12} {'brute 2^n':>12} {'speedup':>10} {'useful?':>8}")
    print("  " + "-" * 50)

    n = 100
    brute = n  # log₂(2^n) = n

    for ratio in [0.3, 0.5, 0.7, 0.9, 1.0, 1.5, 2.0]:
        s = int(ratio * n)
        log_time = compute_memoized_sat_time(n, s)
        speedup = brute - log_time

        useful = "YES" if log_time < brute else "no"
        print(f"  {ratio:>6.1f} {log_time:>12.0f} {brute:>12} "
              f"{speedup:>+10.0f} {useful:>8}")

    print(f"""
    For s < n (sub-linear circuits): 2^{{O(s)}} < 2^n → SPEEDUP!
    For s = n (linear circuits): 2^{{O(n)}} = 2^n → NO speedup.
    For s > n (super-linear): 2^{{O(s)}} > 2^n → SLOWER than brute force.

    Williams' theorem with our speedup:
      NEXP ⊄ SIZE(n^c) for c < 1. (Trivially known.)

    To get NEXP ⊄ P/poly: need speedup at s = n^c for ALL c.
    This requires: memoized SAT in 2^n / n^{{ω(1)}} for circuits of size n^c.

    Our memoization gives: 3^s = 2^{{s log 3}} ≈ 2^{{1.58s}}.
    For s = n: 2^{{1.58n}} > 2^n. WORSE than brute force!

    THE GAP: We need 3^s < 2^n for useful speedup.
    3^s < 2^n → s < n/log₂3 ≈ 0.63n.

    For circuits of size ≤ 0.63n: our algorithm beats brute force.
    For circuits of size > 0.63n: no improvement.

    P vs NP requires beating brute force for s = n^c (c > 1).
    Our gap: works for s < 0.63n, fails for s ≥ 0.63n.
    """)


if __name__ == "__main__":
    main()
