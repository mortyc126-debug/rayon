"""
STEP A: Gate Contribution to Computational Potential.

GOAL: Show that each AND/OR/NOT gate increases Φ by at most poly(n).

If true: circuit_size × poly(n) ≥ Φ(f) → size ≥ Φ(f)/poly(n).
For Φ(MSAT) ~ n^4 (from experiments): size ≥ n^3. SUPER-LINEAR!

METHOD: For a circuit computing f = g OP h (where OP = AND/OR):
  Φ(f) ≤ Φ(g) + Φ(h) + INTERACTION(g, h)

The INTERACTION term captures what the gate adds beyond its inputs.
If INTERACTION ≤ poly(n): we're done.

EXPERIMENT: Compute Φ(f), Φ(g), Φ(h), and INTERACTION for actual
circuits, where g and h are intermediate functions.

Also measure: how does Φ change as we BUILD the circuit gate by gate?
"""

import itertools
from collections import defaultdict
import random
import math
import sys


def compute_phi(n, truth_table_dict, num_trials=200):
    """Compute Φ(f) = max over partitions of cons × comp × depth.

    truth_table_dict: {int_input: 0 or 1}
    """
    total = 2**n

    # Precompute boundary
    boundary = []
    for bits in range(total):
        for j in range(n):
            nb = bits ^ (1 << j)
            if bits < nb and truth_table_dict[bits] != truth_table_dict[nb]:
                boundary.append((bits, nb))

    best_phi = 0

    for _ in range(num_trials):
        k = random.randint(1, min(n-1, 6))
        coords = random.sample(range(n), k)

        # Assign blocks
        block_of = {}
        blocks = defaultdict(set)
        for bits in range(total):
            bid = 0
            for ci, c in enumerate(coords):
                if (bits >> c) & 1:
                    bid |= (1 << ci)
            block_of[bits] = bid
            blocks[bid].add(bits)

        # Consistency: cross-boundary transitions
        cross = sum(1 for b1, b2 in boundary if block_of[b1] != block_of[b2])
        cons = max(1, cross)

        # Compression: distinct signatures
        sigs = set()
        for bid, members in blocks.items():
            sig = tuple(truth_table_dict[b] for b in sorted(members))
            sigs.add(sig)
        comp = max(1, len(sigs))

        # Composability: depth = log2(distinct sigs)
        depth = max(1, int(math.ceil(math.log2(max(2, len(sigs))))))

        phi = cons * comp * depth
        best_phi = max(best_phi, phi)

    return best_phi


def build_truth_table(n, func):
    """Build truth table dict from function."""
    tt = {}
    for bits in range(2**n):
        x = tuple((bits >> j) & 1 for j in range(n))
        tt[bits] = 1 if func(x) else 0
    return tt


def gate_and(tt_a, tt_b, n):
    """Compute truth table of AND(a, b)."""
    return {bits: tt_a[bits] & tt_b[bits] for bits in range(2**n)}


def gate_or(tt_a, tt_b, n):
    """Compute truth table of OR(a, b)."""
    return {bits: tt_a[bits] | tt_b[bits] for bits in range(2**n)}


def gate_not(tt_a, n):
    """Compute truth table of NOT(a)."""
    return {bits: 1 - tt_a[bits] for bits in range(2**n)}


def measure_gate_contribution(n, tt_a, tt_b, gate_type='AND'):
    """Measure how much a gate increases Φ.

    Computes Φ(a), Φ(b), Φ(a OP b), and the interaction.
    """
    phi_a = compute_phi(n, tt_a, 300)
    phi_b = compute_phi(n, tt_b, 300)

    if gate_type == 'AND':
        tt_out = gate_and(tt_a, tt_b, n)
    elif gate_type == 'OR':
        tt_out = gate_or(tt_a, tt_b, n)
    elif gate_type == 'NOT':
        tt_out = gate_not(tt_a, n)
        phi_b = 0

    phi_out = compute_phi(n, tt_out, 300)

    interaction = phi_out - phi_a - phi_b

    return phi_a, phi_b, phi_out, interaction


def trace_circuit_phi(n, clauses):
    """Build a MONO-3SAT circuit gate by gate and track Φ at each step.

    This shows HOW Φ grows during circuit construction.
    """
    # Build circuit: AND of ORs
    # First: OR gates for each clause
    # Then: AND gates to combine

    # Input truth tables
    input_tts = {}
    for j in range(n):
        tt = {}
        for bits in range(2**n):
            tt[bits] = (bits >> j) & 1
        input_tts[j] = tt

    print(f"\n  Building MONO-3SAT circuit (n={n}, {len(clauses)} clauses)")
    print(f"  {'Step':<6} {'Gate':<20} {'Φ':>8} {'ΔΦ':>8} {'ΔΦ/Φ':>8}")
    print("  " + "-" * 55)

    wire_tts = dict(input_tts)  # wire_id -> truth table
    next_wire = n

    prev_phi = 0

    # OR gates for clauses
    clause_outputs = []
    for ci, clause in enumerate(clauses):
        v0, v1, v2 = clause
        # OR(v0, v1)
        or1_tt = gate_or(wire_tts[v0], wire_tts[v1], n)
        wire_tts[next_wire] = or1_tt
        or1_id = next_wire
        next_wire += 1

        # OR(or1, v2)
        or2_tt = gate_or(or1_tt, wire_tts[v2], n)
        wire_tts[next_wire] = or2_tt
        clause_outputs.append(next_wire)
        next_wire += 1

    # AND gates to combine clauses
    if clause_outputs:
        current = clause_outputs[0]
        step = 0

        # Measure initial Φ (first clause)
        phi = compute_phi(n, wire_tts[current], 200)
        print(f"  {step:<6} {'clause_0':<20} {phi:>8} {phi:>8} {'---':>8}")
        prev_phi = phi
        step += 1

        for i in range(1, len(clause_outputs)):
            and_tt = gate_and(wire_tts[current], wire_tts[clause_outputs[i]], n)
            wire_tts[next_wire] = and_tt
            current = next_wire
            next_wire += 1

            phi = compute_phi(n, and_tt, 200)
            delta = phi - prev_phi
            ratio = delta / prev_phi if prev_phi > 0 else 0

            print(f"  {step:<6} {'AND(acc, clause_'+str(i)+')':<20} "
                  f"{phi:>8} {delta:>+8} {ratio:>8.2f}")
            prev_phi = phi
            step += 1

    return prev_phi


def main():
    random.seed(42)

    print("=" * 70)
    print("  GATE CONTRIBUTION TO COMPUTATIONAL POTENTIAL")
    print("  How much does each gate increase Φ?")
    print("=" * 70)

    # Test 1: Individual gate contributions
    print(f"\n{'='*70}")
    print("  TEST 1: Individual gate contributions")
    print(f"{'='*70}")

    for n in [5, 6, 7, 8]:
        if 2**n > 50000:
            break

        print(f"\n  n = {n}:")
        print(f"  {'Gate':<20} {'Φ(a)':>8} {'Φ(b)':>8} {'Φ(out)':>8} "
              f"{'Inter':>8} {'Inter/n':>8}")
        print("  " + "-" * 60)

        # Random functions for inputs
        for trial in range(5):
            # Two random "intermediate" functions
            tt_a = {bits: random.randint(0, 1) for bits in range(2**n)}
            tt_b = {bits: random.randint(0, 1) for bits in range(2**n)}

            for gate_type in ['AND', 'OR']:
                pa, pb, po, inter = measure_gate_contribution(n, tt_a, tt_b, gate_type)
                print(f"  {gate_type+'(rand,rand)_'+str(trial):<20} "
                      f"{pa:>8} {pb:>8} {po:>8} {inter:>+8} {inter/n:>8.1f}")

            # NOT gate
            pa, _, po, inter = measure_gate_contribution(n, tt_a, tt_a, 'NOT')
            print(f"  {'NOT(rand)_'+str(trial):<20} "
                  f"{pa:>8} {'---':>8} {po:>8} {inter:>+8} {inter/n:>8.1f}")

        sys.stdout.flush()

    # Test 2: Circuit trace for MONO-3SAT
    print(f"\n\n{'='*70}")
    print("  TEST 2: Φ growth during MONO-3SAT circuit construction")
    print(f"{'='*70}")

    from mono3sat import generate_all_mono3sat_clauses

    for n in [6, 7, 8]:
        if 2**n > 50000:
            break
        all_clauses = generate_all_mono3sat_clauses(n)
        k = min(len(all_clauses), 3*n)
        clauses = random.sample(all_clauses, k)
        final_phi = trace_circuit_phi(n, clauses)
        print(f"\n  Final Φ = {final_phi}, Φ/n = {final_phi/n:.1f}")

    # Analysis
    print(f"\n\n{'='*70}")
    print("  ANALYSIS: IS INTERACTION BOUNDED BY poly(n)?")
    print(f"{'='*70}")
    print("""
    If max interaction per gate ≤ C × n^k for some constants C, k:
      → Each gate adds at most poly(n) to Φ
      → circuit_size ≥ Φ(f) / poly(n)
      → For Φ(MSAT) ~ n^4: size ≥ n^3 — SUPER-LINEAR!

    From the data: check if interaction values are bounded by poly(n).

    KEY OBSERVATION: The interaction can be NEGATIVE!
    This means AND/OR can REDUCE the potential.
    This happens when combining two functions simplifies the partition.

    For the circuit lower bound: we need Φ to be MONOTONICALLY
    increasing along the circuit computation. If it can decrease:
    the argument fails (gates can "undo" potential increases).

    RESOLUTION: Use a MODIFIED potential that is monotone:
      Φ'(f) = max over all sub-functions g of the circuit: Φ(g)

    Then: Φ'(f) ≤ max Φ over all circuit wires.
    And: circuit_size ≥ max_wire_Φ / max_gate_contribution.

    But this requires max Φ over wires to be large, which it is
    (the output wire has Φ = Φ(f)).
    """)


if __name__ == "__main__":
    main()
