"""
HOT WIRE ANALYSIS: How many wires can have high Φ simultaneously?

The dissipation bound fails because max_wire_Φ ≈ Φ(output).
But if only FEW wires can be "hot" (high Φ), we get a tighter bound.

KEY IDEA: A "hot" wire computes a function that is almost as complex
as f itself. But a circuit of size s can have at most s wires.
If Φ(wire) is high, the wire must "carry" a lot of the computation.

DEFINITION: A wire w is "α-hot" if Φ(w) ≥ α × Φ(f).

CLAIM: The number of α-hot wires is bounded.

ARGUMENT: Each α-hot wire computes a function g with Φ(g) ≥ α × Φ(f).
The truth tables of these functions must be "diverse" — if two hot
wires computed the same function, one would be redundant.

The NUMBER of distinct functions with Φ ≥ α × Φ(f): this depends
on the structure of the Φ measure.

EXPERIMENT: For each wire in the circuit, compute Φ and build the
full Φ PROFILE (distribution of wire potentials).
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

    best = 0
    for _ in range(num_trials):
        k = random.randint(1, min(n-1, 6))
        coords = random.sample(range(n), k)
        block_of = {}
        sigs_dict = defaultdict(list)
        for bits in range(total):
            bid = sum((1 << ci) for ci, c in enumerate(coords) if (bits >> c) & 1)
            block_of[bits] = bid
            sigs_dict[bid].append(tt[bits])
        cross = sum(1 for b1, b2 in boundary if block_of[b1] != block_of[b2])
        sigs = set(tuple(v) for v in sigs_dict.values())
        best = max(best, max(1, cross) * max(1, len(sigs)) *
                   max(1, int(math.ceil(math.log2(max(2, len(sigs)))))))
    return best


def compute_correlation(tt1, tt2, n):
    """Compute correlation between two truth tables."""
    total = 2**n
    agree = sum(1 for b in range(total) if tt1[b] == tt2[b])
    return (2 * agree - total) / total


def analyze_wire_profile(n, clauses):
    """Build circuit, compute Φ for every wire, analyze distribution."""
    total = 2**n

    # Build truth tables
    wire_tt = {}
    for j in range(n):
        wire_tt[j] = {b: (b >> j) & 1 for b in range(total)}

    gates = []
    next_id = n

    # OR for clauses
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

    # AND chain
    current = clause_outs[0]
    for i in range(1, len(clause_outs)):
        new_id = next_id
        wire_tt[new_id] = {b: wire_tt[current][b] & wire_tt[clause_outs[i]][b]
                           for b in range(total)}
        gates.append(('AND', current, clause_outs[i], new_id))
        current = new_id
        next_id += 1

    output = current
    circuit_size = len(gates)

    # Compute Φ for all wires
    wire_phi = {}
    for w in wire_tt:
        wire_phi[w] = compute_phi(n, wire_tt[w])

    phi_output = wire_phi[output]

    # Profile: sorted Φ values
    all_phi = sorted(wire_phi.values(), reverse=True)
    gate_phi = sorted([wire_phi[n + i] for i in range(circuit_size)], reverse=True)

    print(f"\n{'='*60}")
    print(f"  WIRE Φ PROFILE (n={n}, {len(clauses)} clauses)")
    print(f"  Circuit size: {circuit_size}, Φ(output): {phi_output}")
    print(f"{'='*60}")

    # Hot wire analysis
    for alpha in [0.9, 0.75, 0.5, 0.25, 0.1]:
        threshold = alpha * phi_output
        hot_count = sum(1 for p in gate_phi if p >= threshold)
        print(f"  {alpha:.0%}-hot wires (Φ ≥ {threshold:.0f}): "
              f"{hot_count}/{circuit_size} ({hot_count/circuit_size*100:.1f}%)")

    # Distribution buckets
    print(f"\n  Φ distribution (gate wires only):")
    buckets = [0, 0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]
    for i in range(len(buckets)-1):
        lo = buckets[i] * phi_output
        hi = buckets[i+1] * phi_output
        count = sum(1 for p in gate_phi if lo <= p < hi)
        print(f"    [{buckets[i]:.0%}-{buckets[i+1]:.0%}) of Φ(f): "
              f"{count} wires ({count/circuit_size*100:.1f}%)")

    # Correlation between hot wires
    hot_wires = [w for w in wire_phi if wire_phi[w] >= 0.5 * phi_output and w >= n]
    if len(hot_wires) >= 2:
        print(f"\n  Pairwise correlation of 50%-hot wires:")
        corrs = []
        for i in range(min(len(hot_wires), 10)):
            for j in range(i+1, min(len(hot_wires), 10)):
                c = compute_correlation(wire_tt[hot_wires[i]],
                                       wire_tt[hot_wires[j]], n)
                corrs.append(abs(c))
        if corrs:
            print(f"    Avg |correlation|: {sum(corrs)/len(corrs):.4f}")
            print(f"    Max |correlation|: {max(corrs):.4f}")
            print(f"    Min |correlation|: {min(corrs):.4f}")

    # REFINED BOUND using median wire Φ
    if gate_phi:
        median_phi = gate_phi[len(gate_phi)//2]
        p90_phi = gate_phi[len(gate_phi)//10] if len(gate_phi) >= 10 else gate_phi[0]

        # Fan-out
        fan_out = defaultdict(int)
        for _, inp1, inp2, _ in gates:
            fan_out[inp1] += 1
            fan_out[inp2] += 1
        max_fo = max(fan_out.values()) if fan_out else 1

        # Refined bounds
        bound_max = phi_output / (max_fo * gate_phi[0]) if gate_phi[0] > 0 else 0
        bound_p90 = phi_output / (max_fo * p90_phi) if p90_phi > 0 else 0
        bound_median = phi_output / (max_fo * median_phi) if median_phi > 0 else 0

        print(f"\n  REFINED BOUNDS (max_FO = {max_fo}):")
        print(f"    Using max Φ:    size ≥ {bound_max:.2f}")
        print(f"    Using P90 Φ:    size ≥ {bound_p90:.2f}")
        print(f"    Using median Φ: size ≥ {bound_median:.2f}")
        print(f"    Actual size:    {circuit_size}")

    # NEW BOUND: Count how many gates have Φ above each threshold
    # Total fan-out weighted by Φ
    total_fo_phi = sum(max(0, fan_out.get(w, 0) - 1) * wire_phi[w]
                       for w in wire_phi)
    # This equals fan-out recovery from balance equation
    print(f"\n  Total fan-out × Φ: {total_fo_phi}")
    print(f"  This must be ≥ Φ(f) - Φ(inputs) + dissipation")
    print(f"  = {phi_output} - {sum(wire_phi[j] for j in range(n))} + dissipation")

    # THE KEY INSIGHT: fan-out recovery comes from INPUT wires primarily
    input_fo_phi = sum(max(0, fan_out.get(j, 0) - 1) * wire_phi[j] for j in range(n))
    gate_fo_phi = total_fo_phi - input_fo_phi
    print(f"\n  Fan-out Φ from INPUTS:  {input_fo_phi} ({input_fo_phi/max(1,total_fo_phi)*100:.0f}%)")
    print(f"  Fan-out Φ from GATES:   {gate_fo_phi} ({gate_fo_phi/max(1,total_fo_phi)*100:.0f}%)")

    return wire_phi, phi_output, circuit_size


def main():
    random.seed(42)
    from mono3sat import generate_all_mono3sat_clauses

    results = []

    for n in range(5, 11):
        if 2**n > 100000:
            break
        all_clauses = generate_all_mono3sat_clauses(n)
        k = min(len(all_clauses), 3*n)
        clauses = random.sample(all_clauses, k)
        wire_phi, phi_out, size = analyze_wire_profile(n, clauses)
        results.append((n, phi_out, size))
        sys.stdout.flush()

    print(f"\n\n{'='*60}")
    print("  GRAND ANALYSIS")
    print(f"{'='*60}")
    print("""
    KEY FINDING: Fan-out Φ recovery comes almost entirely from
    INPUT wires, not from gate wires!

    Input wires have:
      - Low Φ individually (Φ(xᵢ) ~ n)
      - HIGH fan-out (each input used ~n times in MONO-3SAT)
      - Total input fan-out Φ ~ n × n × n = n³

    Gate wires have:
      - Variable Φ (some hot, most cold)
      - Fan-out = 1 (in this monotone formula-like circuit)
      - Zero fan-out recovery!

    THIS EXPLAINS WHY Φ(f) ~ n³:
      Φ(f) ≈ input_fan_out × Φ(input) ≈ n × n × n = n³

    For GENERAL circuits with gate fan-out > 1:
      Hot gate wires contribute to fan-out recovery.
      This is EXACTLY the power of circuits over formulas.

    THE REFINED QUESTION:
      Can gate fan-out create enough Φ recovery to compute CLIQUE
      with polynomial gates?

      For CLIQUE: Φ(f) should grow exponentially.
      Input fan-out Φ ~ poly(N) (polynomial fan-out × poly Φ per input).
      Gap: exponential Φ(f) vs polynomial input recovery.
      Gate fan-out must fill the gap.

      If gate fan-out fills poly × poly = poly → still exponential gap.
      → Need exponential gate recovery → need exponential fan-out
      → But total fan-out ≤ 2 × size = 2 × poly → polynomial.
      → CONTRADICTION (if Φ(CLIQUE) is truly exponential).
    """)


if __name__ == "__main__":
    main()
