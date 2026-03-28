"""
DISCRETE CURVATURE OF TRAJECTORY SURFACE.

T(C) is a "surface" in {0,1}^{n+s} — the graph of τ: {0,1}^n → {0,1}^s.

Two trajectory points are NEIGHBORS if they differ on exactly 1 INPUT bit.
(Flipping one gate bit without flipping the corresponding input is IMPOSSIBLE
due to consistency equations.)

So: T(C) inherits the GRAPH STRUCTURE from the input hypercube {0,1}^n.
Two trajectories τ(x) and τ(x⊕eⱼ) are adjacent. Their Hamming distance
in {0,1}^{n+s} = 1 (input) + (number of gates that change) = 1 + bdry_wdiff(x,j).

CURVATURE: For a surface in a metric space, curvature at point p measures
how the surface DEVIATES from flat.

For trajectory surface: "flat" = each input flip changes exactly 1 wire
(only the input bit). "Curved" = input flip changes MANY wires.

Define: CURVATURE(x, j) = number of gate wires that change when
flipping input j at point x. = bdry_wdiff(x, j) - 1.

Total curvature = Σ_{x,j} curvature(x, j).

For a circuit of size s:
  Each gate can change on at most 2^n inputs.
  Total changes across all gates and inputs ≤ s × 2^n.
  Total curvature ≤ s × 2^n.

For function f:
  Total curvature ≥ ??? (depends on f).

If total_curvature(f) = min over all circuits computing f of Σ curvature:
  total_curvature(f) ≤ s × 2^n for circuit of size s.
  s ≥ total_curvature(f) / 2^n.

What is total_curvature(f)?

For EACH boundary pair (x, x⊕eⱼ) with f(x) ≠ f(x⊕eⱼ):
  The output gate MUST change → curvature ≥ 1 at this point.

For non-boundary pairs: curvature CAN be 0 (no gate changes except input).
  But: intermediate gates might still change (not required, but possible).

So: total_curvature ≥ |boundary(f)| (at least 1 per boundary pair).
And: s ≥ |boundary| / 2^n ≈ |boundary| / 2^n.

For |boundary| ≈ 1.9^n × n: s ≥ n × (1.9/2)^n → 0. TRIVIAL (same as before).

BUT: what if we weight curvature differently?

WEIGHTED CURVATURE: weight each gate change by the gate's "depth"
or "fan-out" or some other measure.

Or: instead of counting gate changes, count UNIQUE PATTERNS of changes.

Each boundary point (x, j) produces a "change vector" v(x,j) ∈ {0,1}^s
where v_i = 1 if gate i changes.

The number of DISTINCT change vectors ≤ 2^s (any subset of s gates).
But: change vectors are CONNECTED (change propagates through DAG).
Number of connected subsets of DAG ≤ s × 2^{O(tw)}.

For distinct change vectors ≥ D: s × 2^{O(tw)} ≥ D.

From Independence Lemma: D ≥ C(N,k) for CLIQUE.
So: s × 2^{O(tw)} ≥ C(N,k). (Already derived.)

DIFFERENT APPROACH: Instead of counting distinct vectors,
measure their SPREAD in Hamming space.

If the change vectors are spread across {0,1}^s:
  they form a CODE with minimum distance d_min.
  A code with M codewords and min distance d in {0,1}^s:
    M ≤ 2^s / V(s, d_min) (Hamming bound)
  where V(s, d) = ball volume.

If we can show d_min ≥ s/3 (change vectors differ in ≥ s/3 positions):
  V(s, s/3) ≈ 2^{H(1/3) × s} ≈ 2^{0.92s}.
  C(N,k) ≤ 2^s / 2^{0.92s} = 2^{0.08s}.
  s ≥ log₂ C(N,k) / 0.08 ≈ 12.5 × log₂ C(N,k).

This is still O(log C(N,k)) = O(N^{1/3} log N). Logarithmic!
But: 12.5× better constant than naive counting!

For this to be super-poly: need d_min to be SUPER-CONSTANT fraction of s.
But d_min ≤ s always, so the Hamming bound can't give super-poly.

COMPLETELY DIFFERENT GEOMETRIC IDEA:

The trajectory surface T(C) is an n-dimensional submanifold of {0,1}^{n+s}.
It's determined by s "coordinate functions" g₁,...,gₛ.

For different circuits computing the same f: different surfaces,
but same projection to output.

THE MINIMUM SURFACE COMPLEXITY:
  Among all surfaces T ⊂ {0,1}^{n+s} with:
    1. T is an n-dimensional graph (each x maps to unique (g₁,...,gₛ))
    2. The last coordinate gₛ = f(x)
    3. Each gᵢ = AND/OR/NOT of two earlier gⱼ's
  What is the minimum s?

Constraint 3 is THE circuit constraint. Without it: s = 1 suffices
(just set gₛ = f directly). With it: s ≥ circuit_complexity(f).

Constraint 3 says: the surface must be "locally degree-2" —
each coordinate is a degree-2 polynomial of earlier coordinates.

THIS IS AN ALGEBRAIC CONSTRAINT ON THE SURFACE.

A surface where each new coordinate = degree-2 function of previous:
after s steps: the last coordinate can be degree ≤ 2^s.

For f of degree d: 2^s ≥ d → s ≥ log d. LOGARITHMIC again.

BUT: not just degree — the SPECIFIC polynomial structure matters.

For AND: gᵢ = gⱼ × gₖ (product — increases degree multiplicatively).
For OR: gᵢ = gⱼ + gₖ + gⱼgₖ (adds + multiplies).
For NOT: gᵢ = 1 + gⱼ (linear shift).

The mix of AND/OR/NOT determines which polynomials are reachable.
Not all degree-2^s polynomials are reachable — only those
constructible by ITERATING degree-2 operations.

QUESTION: What fraction of degree-d polynomials are reachable
by s steps of degree-2 composition?

If only a SMALL fraction: then if f requires a polynomial in the
"unreachable" part: s must be large.

This is related to the ALGEBRAIC CIRCUIT complexity of the
polynomial f over GF(2).

For the multilinear polynomial of f over GF(2):
  Algebraic circuit complexity = minimum s to compute f(x)
  using + and × over GF(2).

This is ≥ Boolean circuit complexity (each AND/OR is one algebraic op).
And: algebraic complexity over GF(2) is well-studied!

KEY: For the multilinear polynomial of CLIQUE over GF(2):
  CLIQUE(G) = Σ_{S∈C(V,k)} Π_{(i,j)∈S} x_{ij}   (sum of products)

The ALGEBRAIC complexity of this polynomial:
  It has C(N,k) monomials, each of degree C(k,2).
  The algebraic circuit complexity = ???

For a POLYNOMIAL with M monomials of degree d:
  algebraic circuit ≥ M^{1/d} - n  (roughly, from degree argument)

For CLIQUE: M = C(N,k), d = C(k,2) = k(k-1)/2.
  algebraic circuit ≥ C(N,k)^{2/(k(k-1))} - n
  = ((eN/k)^k)^{2/(k²)} - n
  ≈ (N/k)^{2/k} - n
  For k = N^{1/3}: (N^{2/3})^{2/N^{1/3}} - n
  = N^{4/(3N^{1/3})} - n → 1 - n. USELESS.

The degree argument fails because d = C(k,2) is LARGE.

ACTUAL QUESTION: What is the algebraic circuit complexity of
the CLIQUE polynomial Σ Π x_{ij} over GF(2)?

Over LARGE fields: this relates to VP vs VNP (Valiant).
Over GF(2): specific hardness results exist (less studied).

THIS IS THE EXACT INTERSECTION of our research with established
algebraic complexity theory. The next step is to connect our
trajectory variety framework with VP vs VNP techniques adapted
to GF(2).

EXPERIMENT: Compute the actual algebraic complexity of the CLIQUE
polynomial for small N, and compare with Boolean circuit complexity.
"""


def clique_polynomial_terms(N, k):
    """Count monomials and max degree of CLIQUE polynomial over GF(2).

    CLIQUE = Σ_{S ∈ C(V,k)} Π_{(i,j)∈S} x_{ij}

    Over GF(2): same formula (sum = XOR).
    """
    import itertools

    n = N*(N-1)//2
    edge_idx = {}; idx = 0
    for i in range(N):
        for j in range(i+1, N):
            edge_idx[(i,j)] = idx; idx += 1

    # Collect monomials (as frozensets of variable indices)
    monomials = set()
    for S in itertools.combinations(range(N), k):
        mono = frozenset(edge_idx[(S[a], S[b])] for a in range(k) for b in range(a+1, k))
        if mono in monomials:
            monomials.remove(mono)  # GF(2): duplicate cancels
        else:
            monomials.add(mono)

    degrees = [len(m) for m in monomials]
    return len(monomials), max(degrees) if degrees else 0, min(degrees) if degrees else 0


def main():
    import math
    print("=" * 70)
    print("  CLIQUE POLYNOMIAL OVER GF(2)")
    print("  Algebraic complexity of the target function")
    print("=" * 70)

    print(f"\n  {'N':>3} {'k':>3} {'C(N,k)':>8} {'GF2 terms':>10} "
          f"{'degree':>7} {'cancelled':>10}")
    print("  " + "-" * 45)

    for N in range(4, 12):
        for k in [3, 4, max(2, int(N**0.33))]:
            if k >= N or k < 2:
                continue
            cnk = math.comb(N, k)
            terms, max_d, min_d = clique_polynomial_terms(N, k)
            cancelled = cnk - terms
            print(f"  {N:>3} {k:>3} {cnk:>8} {terms:>10} {max_d:>7} {cancelled:>10}")

    print(f"\n  'cancelled' = monomials that appear even number of times")
    print(f"  (cancel in GF(2)). If many cancel → polynomial simpler over GF(2).")
    print(f"  If few cancel → polynomial retains full complexity.")


if __name__ == "__main__":
    main()
