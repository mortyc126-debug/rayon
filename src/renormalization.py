"""
RENORMALIZATION GROUP ON CIRCUIT SPACE.

RG step: remove least-important gate from circuit.
Importance(g) = fraction of inputs where output changes when g removed.

Iterate: remove gates one by one, tracking error accumulation.

RG TRAJECTORY: (size, error) pairs as gates are removed.

P functions: many removable gates → fast flow → small minimum circuit.
NP-hard: few removable gates → slow flow → large minimum circuit.

THE RG FLOW RATE = new measure of circuit complexity.
"""

import random
import math
import time
import sys


def evaluate_circuit(gates, n, x):
    wire = [(x >> j) & 1 for j in range(n)]
    for gt, i1, i2 in gates:
        if gt == 0: wire.append(wire[i1] & wire[i2])
        elif gt == 1: wire.append(wire[i1] | wire[i2])
        elif gt == 2: wire.append(1 - wire[i1])
    return wire[-1] if gates else 0


def compute_truth_table(gates, n):
    return tuple(evaluate_circuit(gates, n, x) for x in range(2**n))


def gate_importance(gates, n, gate_idx, original_tt):
    """Fraction of inputs where removing gate changes output."""
    # Remove gate: replace its output with its first input (bypass)
    modified = list(gates)
    gt, i1, i2 = gates[gate_idx]

    # Replace gate output with input1 (simplest bypass)
    # All subsequent gates referencing this gate's output now get i1's value
    gate_output_wire = n + gate_idx

    new_gates = []
    for gi, (g, a, b) in enumerate(gates):
        if gi == gate_idx:
            continue  # skip removed gate
        # Remap references to removed gate
        na = i1 if a == gate_output_wire else a
        nb = i1 if b == gate_output_wire else b
        # Adjust wire indices for gates after removed one
        new_gates.append((g, na, nb))

    # This is a rough approximation - proper removal is complex
    # Just measure: how different is output if we replace gate with wire?
    changes = 0
    for x in range(2**n):
        wire = [(x >> j) & 1 for j in range(n)]
        for gi, (g, a, b) in enumerate(gates):
            if gi == gate_idx:
                wire.append(wire[i1])  # bypass: output = input1
            else:
                if g == 0: wire.append(wire[a] & wire[b])
                elif g == 1: wire.append(wire[a] | wire[b])
                elif g == 2: wire.append(1 - wire[a])

        if wire[-1] != original_tt[x]:
            changes += 1

    return changes / (2**n)


def rg_flow(gates, n, original_tt):
    """Perform RG flow: iteratively remove least important gate."""
    current_gates = list(gates)
    trajectory = []  # (size, total_error, min_importance)
    total_error = 0

    current_tt = compute_truth_table(current_gates, n)
    base_error = sum(1 for x in range(2**n) if current_tt[x] != original_tt[x]) / 2**n

    trajectory.append({
        'size': len(current_gates),
        'error': base_error,
        'min_importance': 0,
        'removed': None
    })

    while len(current_gates) > 1:
        # Find least important gate
        importances = []
        for gi in range(len(current_gates)):
            imp = gate_importance(current_gates, n, gi, original_tt)
            importances.append((imp, gi))

        importances.sort()
        min_imp, min_gi = importances[0]

        # Remove it (replace with bypass)
        gt, i1, i2 = current_gates[min_gi]
        gate_wire = n + min_gi
        new_gates = []
        for gi, (g, a, b) in enumerate(current_gates):
            if gi == min_gi:
                continue
            na = i1 if a == gate_wire else (a if a < gate_wire else a - 1)
            nb = i1 if b == gate_wire else (b if b < gate_wire else b - 1)
            na = min(na, n + len(new_gates))
            nb = min(nb, n + len(new_gates))
            new_gates.append((g, max(0,na), max(0,nb)))

        current_gates = new_gates

        # Measure error
        current_tt = compute_truth_table(current_gates, n)
        error = sum(1 for x in range(2**n) if current_tt[x] != original_tt[x]) / 2**n

        trajectory.append({
            'size': len(current_gates),
            'error': error,
            'min_importance': min_imp,
            'removed': min_gi
        })

        if error > 0.49:  # function essentially destroyed
            break

    return trajectory


def build_3sat_circuit(n, clauses):
    gates = []
    nid = n
    neg = {}
    for i in range(n):
        neg[i] = nid; gates.append((2, i, 0)); nid += 1  # NOT
    c_outs = []
    for clause in clauses:
        lits = [v if p else neg[v] for v, p in clause]
        cur = lits[0]
        for l in lits[1:]:
            gates.append((1, cur, l)); cur = nid; nid += 1  # OR
        c_outs.append(cur)
    if not c_outs: return gates
    cur = c_outs[0]
    for ci in c_outs[1:]:
        gates.append((0, cur, ci)); cur = nid; nid += 1  # AND
    return gates


def main():
    random.seed(42)
    print("=" * 60)
    print("  RENORMALIZATION GROUP FLOW ON CIRCUIT SPACE")
    print("  Remove gates → track error → measure flow rate")
    print("=" * 60)

    # OR chain (easy function)
    n = 6
    or_gates = []
    nid = n; cur = 0
    for i in range(1, n):
        or_gates.append((1, cur, i)); cur = nid; nid += 1
    or_tt = compute_truth_table(or_gates, n)

    print(f"\n  OR-{n} (s={len(or_gates)}):")
    traj = rg_flow(or_gates, n, or_tt)
    print(f"  {'size':>5} {'error':>8} {'min_imp':>10}")
    for t in traj[:10]:
        print(f"  {t['size']:>5} {t['error']:>8.4f} {t['min_importance']:>10.4f}")

    # 3-SAT circuit
    n = 6
    clauses = []
    for _ in range(12):
        vars_ = random.sample(range(n), 3)
        clause = [(v, random.random() > 0.5) for v in vars_]
        clauses.append(clause)
    sat_gates = build_3sat_circuit(n, clauses)
    sat_tt = compute_truth_table(sat_gates, n)

    print(f"\n  3SAT-{n} (s={len(sat_gates)}):")
    traj = rg_flow(sat_gates, n, sat_tt)
    print(f"  {'size':>5} {'error':>8} {'min_imp':>10}")
    for t in traj[:15]:
        print(f"  {t['size']:>5} {t['error']:>8.4f} {t['min_importance']:>10.4f}")

    # Compare flow rates
    print(f"\n  RG FLOW COMPARISON:")
    print(f"  OR:   starts s={len(or_gates)}, reaches error=0.5 at s=???")
    print(f"  3SAT: starts s={len(sat_gates)}, reaches error=0.5 at s=???")

    # Find size where error exceeds 10%
    for label, gates, tt in [("OR", or_gates, or_tt), ("3SAT", sat_gates, sat_tt)]:
        traj = rg_flow(gates, n, tt)
        critical_size = len(gates)
        for t in traj:
            if t['error'] > 0.1:
                critical_size = t['size'] + 1
                break
        removable = len(gates) - critical_size
        print(f"  {label}: {removable} removable gates ({removable/len(gates)*100:.0f}% redundancy)")

    print(f"""
  INTERPRETATION:
  HIGH redundancy = many gates removable = EASY function = fast RG flow.
  LOW redundancy = few removable gates = HARD function = slow RG flow.

  If NP-hard functions have LOW redundancy at ANY poly circuit size:
  → minimum circuit ≈ actual circuit ≈ poly
  → BUT: minimum for NP-hard = super-poly (if P ≠ NP)
  → contradiction: no poly circuit exists.

  RG flow rate = proxy for distance between actual and minimum circuit.
  For P: flow leads to small fixed point. For NP-hard: no small fixed point.
  """)


if __name__ == "__main__":
    main()
