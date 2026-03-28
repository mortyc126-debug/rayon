"""
POTENTIAL DISSIPATION MODEL.

From experiments:
  - AND/OR gates DECREASE Φ (negative interaction)
  - NOT gates PRESERVE Φ (zero interaction)
  - Fan-out DUPLICATES Φ (wire split → potential on both branches)

This creates a "conservation law" for computational potential:

  Φ_out = Φ_in - dissipation + fan_out_recovery

For a circuit of size s:
  Total Φ at inputs: Σᵢ Φ(xᵢ) = n × Φ(single_var)
  Total Φ at output: Φ(f)
  Total dissipation: Σ_gates dissipation(g)
  Total fan-out recovery: Σ_wires (fan_out(w) - 1) × Φ(w)

Balance equation:
  Φ(f) = Σ Φ(xᵢ) - Σ dissipation(g) + Σ (fan_out(w)-1) × Φ(w)

Rearranging:
  Σ dissipation(g) = Σ Φ(xᵢ) - Φ(f) + Σ (fan_out(w)-1) × Φ(w)

Since dissipation ≥ 0 per gate:
  Σ (fan_out(w)-1) × Φ(w) ≥ Φ(f) - Σ Φ(xᵢ)

The fan-out recovery must compensate for the deficit.

For a circuit with max fan-out F:
  Σ (fan_out(w)-1) × Φ(w) ≤ F × Σ Φ(w) ≤ F × s × max_wire_Φ

This gives: F × s × max_wire_Φ ≥ Φ(f) - n × Φ(var)

KEY: If Φ(f) >> n × Φ(var) (function is "harder" than its inputs):
  F × s × max_wire_Φ ≥ Φ(f)
  s ≥ Φ(f) / (F × max_wire_Φ)

For F = poly(n) and max_wire_Φ = poly(n):
  s ≥ Φ(f) / poly(n)

If Φ(f) = super-poly: s = super-poly → P ≠ NP!

EXPERIMENT: Verify the balance equation numerically and measure
all terms for real circuits.
"""

import itertools
from collections import defaultdict
import random
import math
import sys


def compute_phi_fast(n, tt, num_trials=150):
    """Fast Φ computation."""
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
        cons = max(1, cross)
        comp = max(1, len(sigs))
        depth = max(1, int(math.ceil(math.log2(max(2, comp)))))
        best = max(best, cons * comp * depth)

    return best


def verify_balance_equation(n, clauses):
    """Build circuit, compute Φ for every wire, verify balance."""
    from mono3sat import generate_all_mono3sat_clauses

    total = 2**n

    # Build truth tables for inputs
    wire_tt = {}
    for j in range(n):
        wire_tt[j] = {bits: (bits >> j) & 1 for bits in range(total)}

    # Build circuit: OR for clauses, then AND
    gates = []  # (type, inp1, inp2)
    next_id = n

    clause_outs = []
    for clause in clauses:
        v0, v1, v2 = clause
        # OR(v0, v1)
        or1 = next_id
        wire_tt[or1] = {b: wire_tt[v0][b] | wire_tt[v1][b] for b in range(total)}
        gates.append(('OR', v0, v1, or1))
        next_id += 1
        # OR(or1, v2)
        or2 = next_id
        wire_tt[or2] = {b: wire_tt[or1][b] | wire_tt[v2][b] for b in range(total)}
        gates.append(('OR', or1, v2, or2))
        next_id += 1
        clause_outs.append(or2)

    # AND chain
    if clause_outs:
        current = clause_outs[0]
        for i in range(1, len(clause_outs)):
            new_id = next_id
            wire_tt[new_id] = {b: wire_tt[current][b] & wire_tt[clause_outs[i]][b]
                               for b in range(total)}
            gates.append(('AND', current, clause_outs[i], new_id))
            current = new_id
            next_id += 1

    output_wire = current
    circuit_size = len(gates)

    # Compute Φ for every wire
    wire_phi = {}
    for w_id in wire_tt:
        wire_phi[w_id] = compute_phi_fast(n, wire_tt[w_id])

    # Compute fan-out
    fan_out = defaultdict(int)
    for gtype, inp1, inp2, out in gates:
        fan_out[inp1] += 1
        fan_out[inp2] += 1

    # Compute dissipation per gate
    gate_dissipation = []
    for gtype, inp1, inp2, out in gates:
        d = wire_phi[inp1] + wire_phi[inp2] - wire_phi[out]
        gate_dissipation.append(d)

    # Balance equation terms
    input_phi_total = sum(wire_phi[j] for j in range(n))
    output_phi = wire_phi[output_wire]
    total_dissipation = sum(gate_dissipation)
    fanout_recovery = sum((fan_out[w] - 1) * wire_phi[w]
                          for w in fan_out if fan_out[w] > 1)

    # Max wire Φ
    max_wire_phi = max(wire_phi.values())

    print(f"\n{'='*60}")
    print(f"  BALANCE EQUATION (n={n}, {len(clauses)} clauses)")
    print(f"{'='*60}")
    print(f"  Circuit size: {circuit_size}")
    print(f"  Φ(inputs) total: {input_phi_total}")
    print(f"  Φ(output):       {output_phi}")
    print(f"  Max wire Φ:      {max_wire_phi}")
    print(f"  Total dissipation: {total_dissipation}")
    print(f"  Fan-out recovery:  {fanout_recovery}")
    print(f"  Balance: {input_phi_total} - {total_dissipation} + {fanout_recovery} = "
          f"{input_phi_total - total_dissipation + fanout_recovery}")
    print(f"  Expected (Φ output): {output_phi}")
    print(f"  Balance error: {abs(input_phi_total - total_dissipation + fanout_recovery - output_phi)}")

    # Per-gate statistics
    pos_dissipation = [d for d in gate_dissipation if d > 0]
    neg_dissipation = [d for d in gate_dissipation if d < 0]

    print(f"\n  Gate dissipation stats:")
    print(f"    Positive (Φ decreased): {len(pos_dissipation)} gates, "
          f"avg={sum(pos_dissipation)/len(pos_dissipation):.0f}" if pos_dissipation else "    None positive")
    print(f"    Negative (Φ increased): {len(neg_dissipation)} gates, "
          f"avg={sum(neg_dissipation)/len(neg_dissipation):.0f}" if neg_dissipation else "    None negative")
    print(f"    Zero: {sum(1 for d in gate_dissipation if d == 0)} gates")

    # Fan-out analysis
    print(f"\n  Fan-out structure:")
    fo_vals = [fan_out[w] for w in fan_out if w >= n]  # gate fan-outs
    input_fo = [fan_out.get(j, 0) for j in range(n)]
    print(f"    Input fan-out: avg={sum(input_fo)/n:.1f}, max={max(input_fo)}")
    if fo_vals:
        print(f"    Gate fan-out:  avg={sum(fo_vals)/len(fo_vals):.1f}, max={max(fo_vals)}")

    # THE KEY BOUND
    print(f"\n  KEY BOUND:")
    print(f"    Φ(f) = {output_phi}")
    print(f"    max_fan_out = {max(fan_out.values()) if fan_out else 1}")
    print(f"    max_wire_Φ = {max_wire_phi}")
    max_fo = max(fan_out.values()) if fan_out else 1
    lower_bound = output_phi / (max_fo * max_wire_phi) if max_fo * max_wire_phi > 0 else 0
    print(f"    size ≥ Φ(f) / (max_fo × max_wire_Φ) = {lower_bound:.2f}")
    print(f"    Actual size: {circuit_size}")
    print(f"    Tightness: {circuit_size / lower_bound:.2f}×" if lower_bound > 0 else "")

    return {
        'n': n,
        'size': circuit_size,
        'phi_output': output_phi,
        'phi_input_total': input_phi_total,
        'max_wire_phi': max_wire_phi,
        'total_dissipation': total_dissipation,
        'max_fanout': max_fo,
        'lower_bound': lower_bound,
    }


def scaling_analysis():
    """Run balance equation for increasing n."""
    print("=" * 60)
    print("  DISSIPATION MODEL: SCALING ANALYSIS")
    print("=" * 60)

    from mono3sat import generate_all_mono3sat_clauses

    results = []

    for n in range(5, 11):
        if 2**n > 100000:
            break

        all_clauses = generate_all_mono3sat_clauses(n)
        k = min(len(all_clauses), 3 * n)
        clauses = random.sample(all_clauses, k)

        r = verify_balance_equation(n, clauses)
        results.append(r)
        sys.stdout.flush()

    # Summary
    print(f"\n\n{'='*60}")
    print("  SCALING SUMMARY")
    print(f"{'='*60}")
    print(f"  {'n':>3} {'size':>6} {'Φ(f)':>8} {'maxΦ':>8} {'maxFO':>6} "
          f"{'bound':>8} {'tight':>7}")
    print("  " + "-" * 50)

    for r in results:
        tight = r['size'] / r['lower_bound'] if r['lower_bound'] > 0 else 0
        print(f"  {r['n']:3d} {r['size']:6d} {r['phi_output']:8d} "
              f"{r['max_wire_phi']:8d} {r['max_fanout']:6d} "
              f"{r['lower_bound']:8.1f} {tight:7.1f}×")

    # Growth rate of bound
    if len(results) >= 3:
        bounds = [r['lower_bound'] for r in results]
        ns = [r['n'] for r in results]
        print(f"\n  Lower bound growth:")
        for i in range(len(results)):
            if bounds[i] > 0:
                print(f"    n={ns[i]}: bound = {bounds[i]:.1f}")

    print(f"""
    INTERPRETATION:

    The balance equation: Φ(f) = Σ Φ(inputs) - dissipation + fan-out recovery

    Lower bound: size ≥ Φ(f) / (max_FO × max_wire_Φ)

    For this to give super-polynomial bounds:
      Φ(f) must grow super-polynomially
      AND max_FO × max_wire_Φ must be polynomially bounded

    From our data: Φ(f) grows fast (Φ/n ~ n³ for MSAT)
    But max_wire_Φ ALSO grows (intermediate wires can have high Φ)

    The bound is useful when Φ(output) >> max_FO × max_wire_Φ.
    Whether this holds for NP-hard functions is the key question.
    """)


if __name__ == "__main__":
    random.seed(42)
    scaling_analysis()
