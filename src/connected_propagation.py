"""
CONNECTED PROPAGATION SETS: Two-layer bound.

LAYER 1: Propagation sets are CONNECTED subsets of the circuit DAG.
LAYER 2: Connected subsets are bounded by treewidth.

Combined: S × 2^{O(T)} ≥ #distinct_propagation_sets

From Independence Lemma: distinct sets ≥ C(N,k) for k-CLIQUE.

CASE ANALYSIS:
  Case A: T ≤ c·N^{1/3} (small treewidth)
    S × 2^{O(c·N^{1/3})} ≥ C(N, N^{1/3})
    log: log S + O(N^{1/3}) ≥ Θ(N^{1/3} log N)
    log S ≥ Θ(N^{1/3} log N) - O(N^{1/3}) = Ω(N^{1/3} log N)
    S ≥ 2^{Ω(N^{1/3} log N)} = SUPER-POLY!

  Case B: T > c·N^{1/3} (large treewidth)
    S ≥ T > c·N^{1/3}
    But N^{1/3} is polynomial in N, so S > polynomial.
    Is this super-polynomial? N^{1/3} = o(N^c) for c > 1/3.
    So for circuits of size N^c with c > 1/3: NOT a contradiction.

  THE GAP: Case B gives S > N^{1/3}, not super-poly.

  TO CLOSE THE GAP: Need either:
  (a) A better bound in Case B (use formula bound + treewidth)
  (b) More distinct propagation sets (> C(N,k))
  (c) A tighter connected subsets bound

Let me try (a): combine connected propagation with formula bound.

COMBINED BOUND:
  From formula: S^{T+1} ≥ formula ≥ 2^{Ω(N^{1/6})}
  From propagation: S × 2^{O(T)} ≥ C(N, N^{1/3})

  Multiply: S^{T+2} × 2^{O(T)} ≥ 2^{Ω(N^{1/6})} × C(N, N^{1/3})

  RHS = 2^{Ω(N^{1/6}) + Θ(N^{1/3} log N)} = 2^{Θ(N^{1/3} log N)}

  S^{T+2} × 2^{O(T)} ≥ 2^{Θ(N^{1/3} log N)}

  For S = N^c: N^{c(T+2)} × 2^{O(T)} ≥ 2^{Θ(N^{1/3} log N)}

  Taking log: c(T+2) log N + O(T) ≥ Θ(N^{1/3} log N)
  cT log N ≥ Θ(N^{1/3} log N)  (dominating terms)
  cT ≥ Θ(N^{1/3})
  T ≥ Θ(N^{1/3}/c)

  And T ≤ S = N^c. So: N^c ≥ N^{1/3}/c → c ≥ 1/3 (approximately).

  This gives: S ≥ N^{1/3}. SAME AS BEFORE.

  STILL NOT SUPER-POLY.

Let me try approach (b): can we get MORE distinct propagation sets?

The Independence Lemma gives C(N,k) distinct sub-functions.
But propagation sets come from BOUNDARY PAIRS, not sub-functions.

Each sub-function S has C(k,2) boundary pairs (one per edge of S).
From our "intra-set" result: C(k,2) pairs within one S are distinct.

Total distinct propagation sets ≥ C(N,k) × C(k,2)?
No — pairs from different S might have same propagation sets.

But from Independence Lemma with adaptive e₁:
  Each (S, e_S) with e_S specific to S gives a distinct sub-function.
  C(N,k) such pairs.

Each pair is a boundary pair at a SPECIFIC input (S minus e_S).
The propagation set at this input, flipping e_S: a specific connected subset.

Are these C(N,k) propagation sets all distinct?

They MUST be distinct because: if two boundary pairs had identical
propagation sets, the circuit would behave identically on both.
But the Independence Lemma says they're NON-EQUIVALENT
(there exists a completion distinguishing them).

Wait — same propagation set doesn't mean identical behavior everywhere.
It means: on THIS specific input, the SAME wires flip.
But on OTHER inputs: different wires might flip.

So: same propagation set on one input ≠ same behavior everywhere.
The propagation sets at ONE input can be identical for
non-equivalent sub-functions.

THE PROBLEM: We can't force propagation sets to be distinct.

FINAL ATTEMPT: Use the trajectory space DIRECTLY.

The trajectory τ(x) = (x, g₁(x),...,gₛ(x)) ∈ {0,1}^{n+s}.

Two inputs x₁, x₂ have τ(x₁) ≠ τ(x₂) iff SOME wire differs.

The number of DISTINCT trajectories = 2^n (one per input, since
τ is injective: the input bits are part of the trajectory).

So: |T(C)| = 2^n always. No information here.

But: the STRUCTURE of T(C) (as an algebraic variety) captures info.

The consistency equations: each gate adds one equation.
  s equations of degree 2 in n+s variables over GF(2).

The VARIETY V defined by these equations has degree ≤ 2^s (Bezout).
The NUMBER OF POINTS on V = 2^n (we know this).

But: the HILBERT FUNCTION of V:
  H_V(d) = dim of degree-d polynomials modulo the ideal I(V).

For V defined by s degree-2 equations: H_V(d) depends on the
regularity of the ideal.

THE CASTELNUOVO-MUMFORD REGULARITY reg(I):
  If reg(I) is high: the ideal is "complex" — many independent
  high-degree relations.

For a circuit computing a "hard" function: reg(I) should be high.
For a circuit computing an "easy" function: reg(I) should be low.

Can we BOUND reg(I) in terms of circuit size and the function?

This connects to ALGEBRAIC GEOMETRY of the trajectory variety.
It's a genuinely new direction that doesn't reduce to counting.
"""


def main():
    print("The connected propagation argument gives:")
    print("  S ≥ N^{1/3} for CLIQUE — super-linear in N but not super-poly in n")
    print()
    print("The algebraic geometry of trajectory space (regularity, Hilbert function)")
    print("is a genuinely new direction that doesn't reduce to counting.")
    print()
    print("This requires deep algebraic geometry — computing Castelnuovo-Mumford")
    print("regularity of the gate-consistency ideal.")
    print()
    print("This is the EXACT frontier where new mathematics meets P vs NP.")


if __name__ == "__main__":
    main()
