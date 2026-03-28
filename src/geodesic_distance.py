"""
GEODESIC DISTANCE IN FUNCTION SPACE: A non-counting measure.

The counting barrier: s gates → 2^s functions → s ≥ log(count).
This is because we count DISTINCT functions.

NEW APPROACH: Don't count functions. Measure DISTANCE.

Define: d(f, g) = Hamming distance of truth tables = |{x: f(x) ≠ g(x)}|.

A circuit builds f from inputs x₁,...,xₙ through gates.
Each gate transforms one function into another.
The TOTAL DISTANCE traversed = sum of per-gate distances.

Per-gate distance:
  d(g, AND(g,h)) = |{x: g(x)=1, AND(g,h)(x)=0}| = |{x: g(x)=1, h(x)=0}|
  This can be up to 2^{n-1} (if g and h are uncorrelated).
  But for "useful" gates: typically much less.

TOTAL DISTANCE from inputs to f:
  R(f) = min over all circuits computing f: Σ_gates d(gate_input, gate_output)

If R(f) = super-poly: circuit_size ≥ R(f) / max_per_gate_distance.

BUT: max_per_gate_distance = 2^{n-1}. So: size ≥ R(f) / 2^{n-1}.
For R(f) ≤ n × 2^{n-1}: size ≥ n. TRIVIAL.

THE FIX: Use NORMALIZED distance = d(f,g) / 2^n ∈ [0, 1/2].
And measure the PRODUCT of successive distances (not sum).

OR: Use a DIFFERENT metric where gate distance is bounded by poly(n).

THE KEY INSIGHT: For MONOTONE gates (AND/OR without NOT):
  The distance is constrained by MONOTONICITY.
  AND(g,h)(x) ≤ g(x) for all x. So d(g, AND(g,h)) = |{x: g=1, h=0}|.
  This is the "lost" 1s. Each AND can only REMOVE 1s.
  OR can only ADD 1s.

  In the monotone world: the path from inputs to f is DIRECTED
  (1s only increase through OR, decrease through AND).
  The "monotone distance" is constrained.

For GENERAL circuits with NOT: NOT can FLIP arbitrary sets of bits.
  d(g, NOT(g)) = |{x: g(x)=1}| (all 1s become 0s and vice versa).
  This is a HUGE distance.

BUT: NOT doesn't change the INFORMATION — just inverts it.
The "informational distance" of NOT is 0.

DEFINE: Informational distance ρ(g, h) = min(d(g,h), d(g, NOT(h)))
  This measures how "different" g and h are, up to negation.

For NOT gate: ρ(g, NOT(g)) = 0.
For AND gate: ρ(g, AND(g,h)) = |{x: g=1, h=0}| or |{x: g=0, h=1, ...}|.

With informational distance: NOT is free, AND/OR cost something.

THE GEODESIC ARGUMENT:
  Start: input variables x_i have truth table weight 2^{n-1}.
  End: CLIQUE has truth table weight |CLIQUE⁻¹(1)|.

  The geodesic distance from inputs to CLIQUE in informational metric:
  ρ(x_i, CLIQUE) = min(d(x_i, CLIQUE), d(x_i, NOT(CLIQUE)))

  Each gate traverses distance ≤ max_ρ per gate.
  Circuit size ≥ total_geodesic / max_ρ.

EXPERIMENT: Compute geodesic distances and per-gate distances.
"""

import itertools
from collections import defaultdict
import random
import math
import sys


def hamming_distance(tt1, tt2, n):
    """Hamming distance between two truth tables."""
    total = 2**n
    return sum(1 for b in range(total) if tt1[b] != tt2[b])


def informational_distance(tt1, tt2, n):
    """min(d(f,g), d(f, NOT(g)))"""
    total = 2**n
    d_same = sum(1 for b in range(total) if tt1[b] != tt2[b])
    d_neg = total - d_same  # d(f, NOT(g))
    return min(d_same, d_neg)


def compute_geodesic_from_inputs(n, tt_f):
    """Compute informational distance from each input to f."""
    total = 2**n
    distances = []
    for j in range(n):
        tt_xj = {b: (b >> j) & 1 for b in range(total)}
        d = informational_distance(tt_xj, tt_f, n)
        distances.append(d)
    return distances


def compute_gate_distances_in_circuit(n, clauses):
    """Build MSAT circuit and measure per-gate informational distance."""
    total = 2**n

    wire_tt = {}
    for j in range(n):
        wire_tt[j] = {b: (b >> j) & 1 for b in range(total)}

    gates = []
    next_id = n

    clause_outs = []
    for clause in clauses:
        v0, v1, v2 = clause
        or1 = next_id
        wire_tt[or1] = {b: wire_tt[v0][b] | wire_tt[v1][b] for b in range(total)}
        gates.append(('OR', v0, v1, or1))
        next_id += 1
        or2 = next_id
        wire_tt[or2] = {b: wire_tt[or1][b] | wire_tt[v2][b] for b in range(total)}
        gates.append(('OR', or1, v2, or2))
        next_id += 1
        clause_outs.append(or2)

    current = clause_outs[0]
    for i in range(1, len(clause_outs)):
        new_id = next_id
        wire_tt[new_id] = {b: wire_tt[current][b] & wire_tt[clause_outs[i]][b]
                           for b in range(total)}
        gates.append(('AND', current, clause_outs[i], new_id))
        current = new_id
        next_id += 1

    output = current
    tt_f = wire_tt[output]

    # Per-gate distances
    gate_dists = []
    for gtype, inp1, inp2, out in gates:
        d_from_inp1 = informational_distance(wire_tt[inp1], wire_tt[out], n)
        d_from_inp2 = informational_distance(wire_tt[inp2], wire_tt[out], n)
        gate_dists.append(min(d_from_inp1, d_from_inp2))

    return gate_dists, tt_f, len(gates)


def main():
    random.seed(42)
    print("=" * 70)
    print("  GEODESIC DISTANCE: Non-counting measure for circuit bounds")
    print("=" * 70)

    from mono3sat import generate_all_mono3sat_clauses

    print(f"\n{'Func':<15} {'n':>4} {'|f⁻¹(1)|':>10} {'min ρ(x,f)':>12} "
          f"{'avg ρ(x,f)':>12} {'max gate ρ':>12} {'size':>6} "
          f"{'Σ gate ρ':>10} {'bound':>8}")
    print("-" * 95)

    for n in range(5, 14):
        if 2**n > 200000:
            break

        all_cl = generate_all_mono3sat_clauses(n)
        clauses = random.sample(all_cl, min(len(all_cl), 3*n))

        gate_dists, tt_f, size = compute_gate_distances_in_circuit(n, clauses)
        input_dists = compute_geodesic_from_inputs(n, tt_f)

        f_weight = sum(tt_f[b] for b in range(2**n))
        min_input_d = min(input_dists)
        avg_input_d = sum(input_dists) / n
        max_gate_d = max(gate_dists) if gate_dists else 0
        sum_gate_d = sum(gate_dists)

        # Bound: size ≥ min_input_d / max_gate_d
        bound = min_input_d / max_gate_d if max_gate_d > 0 else 0

        print(f"{'MSAT-'+str(n):<15} {n:>4} {f_weight:>10} {min_input_d:>12} "
              f"{avg_input_d:>12.0f} {max_gate_d:>12} {size:>6} "
              f"{sum_gate_d:>10} {bound:>8.2f}")
        sys.stdout.flush()

    # Triangle
    for N in range(4, 7):
        n = N*(N-1)//2
        if 2**n > 200000:
            break

        edge_idx = {}; idx = 0
        for i in range(N):
            for j in range(i+1, N):
                edge_idx[(i,j)] = idx; edge_idx[(j,i)] = idx; idx += 1

        tt_f = {}
        for bits in range(2**n):
            x = tuple((bits >> j) & 1 for j in range(n))
            has = any(x[edge_idx[(i,j)]] and x[edge_idx[(i,k)]] and x[edge_idx[(j,k)]]
                      for i in range(N) for j in range(i+1,N) for k in range(j+1,N))
            tt_f[bits] = 1 if has else 0

        input_dists = compute_geodesic_from_inputs(n, tt_f)
        f_weight = sum(tt_f[b] for b in range(2**n))
        min_d = min(input_dists)
        avg_d = sum(input_dists) / n

        print(f"{'TRI-K'+str(N):<15} {n:>4} {f_weight:>10} {min_d:>12} "
              f"{avg_d:>12.0f} {'---':>12} {'---':>6} "
              f"{'---':>10} {'---':>8}")

    # Analyze scaling
    print(f"\n{'='*70}")
    print("  SCALING: How does geodesic distance grow?")
    print(f"{'='*70}")
    print("""
    min ρ(input, f) = minimum informational distance from any input to f.
    This is a LOWER BOUND on the total "work" the circuit must do.

    If min ρ grows as 2^{cn} for some c > 0:
      AND max gate ρ ≤ 2^{(c-ε)n}:
      size ≥ 2^{εn} → EXPONENTIAL!

    But: max gate ρ CAN be up to 2^{n-1} (half the truth table).
    So: size ≥ min_ρ / 2^{n-1}.

    For min_ρ ≈ α × 2^{n-1} (fraction α of truth table differs):
      size ≥ α. TRIVIAL (constant).

    THE ISSUE: gate distance CAN be huge (up to 2^{n-1}).

    RESOLUTION: For circuits of BOUNDED DEPTH d:
      Each gate at depth ≤ d changes a function that depends on ≤ 2^d inputs.
      The truth table change: at most 2^{n-d} positions flip.
      So: per-gate distance ≤ 2^{n-d}.

      With depth d and gate distance ≤ 2^{n-d}:
        Total traversable distance ≤ s × 2^{n-d}.
        Need ≥ min_ρ ≈ 2^{n-1}.
        s ≥ 2^{n-1} / 2^{n-d} = 2^{d-1}.

      For d = O(log n): s ≥ poly(n)/2. Weak.
      For d = O(1): s ≥ constant. Trivial.

    CONCLUSION: Geodesic distance gives non-trivial bounds ONLY
    when combined with depth restrictions. For unrestricted depth:
    a single gate CAN traverse huge distance.
    """)


if __name__ == "__main__":
    main()
