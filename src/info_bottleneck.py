"""
Information Bottleneck Analysis for Circuit Lower Bounds.

NEW APPROACH: Instead of counting boundary points or orbits,
measure the INFORMATION CONTENT that a circuit must carry.

For a circuit C computing f:
  - Each wire w carries a Boolean function g_w: {0,1}^n → {0,1}
  - The output wire computes f
  - Gate g(a,b) = AND/OR of wires a,b

KEY OBSERVATION: On the boundary ∂f, a single bit flip changes f.
This means the circuit's output is "maximally sensitive" to input
changes at boundary points.

Define the BOUNDARY MUTUAL INFORMATION:
  I_∂(g_w) = number of boundary transitions where g_w changes value

For the output wire: I_∂(output) = |∂f| (all transitions)
For each gate: I_∂(gate) measures how many boundary transitions
the gate "participates in"

THEOREM-LIKE CLAIM:
  For AND gate g = a ∧ b:
    I_∂(g) ≤ I_∂(a) + I_∂(b)   (sub-additive)
  For NOT gate g = ¬a:
    I_∂(g) = I_∂(a)             (invariant)

This means: total boundary information flows through AND/OR gates.
NOT gates don't create new boundary information.

LOWER BOUND:
  circuit_size ≥ I_∂(f) / max_per_gate_info

If max_per_gate_info is bounded (e.g., by n or poly(n)),
we get a non-trivial lower bound.

THIS MODULE: Compute I_∂ for actual circuits and verify the claims.
"""

import itertools
from collections import defaultdict
import random
import math
import sys


def evaluate_mono3sat(assignment, clauses):
    for clause in clauses:
        if not any(assignment[v] for v in clause):
            return False
    return True


class AnalyzableCircuit:
    """Circuit that tracks intermediate function values for analysis."""

    def __init__(self, n):
        self.n = n
        self.gates = []  # (type, inp1, inp2)

    def add_and(self, a, b):
        idx = self.n + len(self.gates)
        self.gates.append(('AND', a, b))
        return idx

    def add_or(self, a, b):
        idx = self.n + len(self.gates)
        self.gates.append(('OR', a, b))
        return idx

    def add_not(self, a):
        idx = self.n + len(self.gates)
        self.gates.append(('NOT', a, None))
        return idx

    def evaluate_all(self, x):
        """Return values of all wires (inputs + gates)."""
        values = list(x) + [0] * len(self.gates)
        for i, (gtype, a, b) in enumerate(self.gates):
            idx = self.n + i
            if gtype == 'AND':
                values[idx] = values[a] & values[b]
            elif gtype == 'OR':
                values[idx] = values[a] | values[b]
            elif gtype == 'NOT':
                values[idx] = 1 - values[a]
        return values

    def size(self):
        return len(self.gates)


def build_mono3sat_circuit(n, clauses, use_not=False):
    """Build a circuit computing MONO-3SAT.

    Without NOT: f = AND_j (OR_{i∈C_j} x_i)
    With NOT: can potentially use NOT to reduce size.
    """
    c = AnalyzableCircuit(n)

    if not clauses:
        return c

    # Build OR for each clause
    clause_outputs = []
    for clause in clauses:
        v0, v1, v2 = clause
        or1 = c.add_or(v0, v1)
        or2 = c.add_or(or1, v2)
        clause_outputs.append(or2)

    # Build AND of all clauses
    if len(clause_outputs) == 1:
        return c

    current = clause_outputs[0]
    for i in range(1, len(clause_outputs)):
        current = c.add_and(current, clause_outputs[i])

    return c


def compute_boundary_info(circuit, n, clauses):
    """Compute boundary information I_∂ for each wire in the circuit.

    I_∂(wire w) = number of boundary transitions where w changes value.
    """
    # Compute solutions
    solutions = set()
    for bits in range(2**n):
        x = tuple((bits >> i) & 1 for i in range(n))
        if evaluate_mono3sat(x, clauses):
            solutions.add(x)

    # Compute boundary transitions
    transitions = []
    for bits in range(2**n):
        x_b = tuple((bits >> i) & 1 for i in range(n))
        if x_b in solutions:
            continue
        for j in range(n):
            if x_b[j] == 0:
                flipped = list(x_b)
                flipped[j] = 1
                if tuple(flipped) in solutions:
                    transitions.append((x_b, j, tuple(flipped)))

    if not transitions:
        return None

    # For each wire, count boundary transitions where it changes
    total_wires = n + circuit.size()
    wire_info = [0] * total_wires

    for x_b, j, x_bp in transitions:
        vals_b = circuit.evaluate_all(x_b)
        vals_bp = circuit.evaluate_all(x_bp)

        for w in range(total_wires):
            if vals_b[w] != vals_bp[w]:
                wire_info[w] += 1

    return wire_info, transitions


def analyze_info_flow(n, clauses):
    """Analyze information flow through a circuit computing MONO-3SAT."""

    circuit = build_mono3sat_circuit(n, clauses)
    result = compute_boundary_info(circuit, n, clauses)

    if result is None:
        return None

    wire_info, transitions = result
    total_transitions = len(transitions)

    print(f"\n{'='*70}")
    print(f"  INFORMATION BOTTLENECK ANALYSIS (n={n})")
    print(f"  |∂f| = {total_transitions} boundary transitions")
    print(f"  Circuit size = {circuit.size()} gates")
    print(f"{'='*70}")

    # Input wire information
    print(f"\n  Input wire boundary information:")
    for i in range(n):
        print(f"    x_{i}: I_∂ = {wire_info[i]} "
              f"({wire_info[i]/total_transitions*100:.1f}%)")

    # Gate information
    print(f"\n  Gate boundary information:")
    max_gate_info = 0
    for i, (gtype, a, b) in enumerate(circuit.gates):
        idx = n + i
        info = wire_info[idx]
        max_gate_info = max(max_gate_info, info)
        if b is not None:
            print(f"    Gate {i} ({gtype}, {a}, {b}): I_∂ = {info} "
                  f"({info/total_transitions*100:.1f}%)")
        else:
            print(f"    Gate {i} ({gtype}, {a}): I_∂ = {info} "
                  f"({info/total_transitions*100:.1f}%)")

    # Key metric: max per-gate information
    print(f"\n  Max per-gate I_∂: {max_gate_info}")
    print(f"  Output I_∂: {wire_info[-1]} (should = {total_transitions})")
    print(f"  Lower bound (|∂f| / max_gate): "
          f"{total_transitions / max_gate_info:.2f}")

    # Sub-additivity check
    print(f"\n  Sub-additivity check (AND/OR gates):")
    violations = 0
    for i, (gtype, a, b) in enumerate(circuit.gates):
        if gtype in ('AND', 'OR'):
            idx = n + i
            if wire_info[idx] > wire_info[a] + wire_info[b]:
                violations += 1
                print(f"    Gate {i}: {wire_info[idx]} > {wire_info[a]} + {wire_info[b]} VIOLATION!")
            # Check: does NOT change info?

    print(f"  Sub-additivity violations: {violations}")

    # Information profile: sorted gate info values
    gate_infos = sorted([wire_info[n + i] for i in range(circuit.size())], reverse=True)
    print(f"\n  Gate information profile (sorted):")
    for i, info in enumerate(gate_infos[:10]):
        print(f"    Gate rank {i}: I_∂ = {info}")

    return {
        'total_transitions': total_transitions,
        'max_gate_info': max_gate_info,
        'circuit_size': circuit.size(),
        'lower_bound': total_transitions / max_gate_info,
    }


def analyze_optimal_info_distribution(n, clauses):
    """What is the MINIMUM max-per-gate information achievable?

    If we could design a circuit that spreads boundary information
    evenly across gates, each gate would carry |∂f| / size information.

    BUT: can we actually achieve this? Or is there a fundamental
    lower bound on max-per-gate info?

    If max-per-gate ≤ poly(n) for ALL circuits, then:
      circuit_size ≥ |∂f| / poly(n) = exp(n) / poly(n)
    This would prove P ≠ NP!

    The question: can NOT gates help reduce max-per-gate info?
    """
    solutions = set()
    for bits in range(2**n):
        x = tuple((bits >> i) & 1 for i in range(n))
        if evaluate_mono3sat(x, clauses):
            solutions.add(x)

    transitions = []
    for bits in range(2**n):
        x_b = tuple((bits >> i) & 1 for i in range(n))
        if x_b in solutions:
            continue
        for j in range(n):
            if x_b[j] == 0:
                fl = list(x_b); fl[j] = 1
                if tuple(fl) in solutions:
                    transitions.append((x_b, j, tuple(fl)))

    total = len(transitions)

    print(f"\n  Optimal information distribution analysis:")
    print(f"  |∂f| = {total}")

    # For input variables: what is their boundary info?
    input_infos = [0] * n
    for x_b, j, x_bp in transitions:
        for i in range(n):
            if x_b[i] != x_bp[i]:
                input_infos[i] += 1

    max_input_info = max(input_infos)
    sum_input_info = sum(input_infos)

    print(f"  Max input wire info: {max_input_info}")
    print(f"  Sum input wire info: {sum_input_info}")
    print(f"  Average input wire info: {sum_input_info/n:.1f}")

    # KEY INSIGHT: For monotone functions, x_j changes on ALL transitions
    # where j is the flipped bit. But also on transitions where x_b[j]=0
    # and x_bp[j]=0 but some gate involving j changes.
    # For input variables in monotone functions:
    # x_j changes on transition (x_b, k) iff x_b[j]=0 and x_bp[j]=1 (j=k)
    # OR x_b[j]=1 and x_bp[j]=1 and j≠k — but this is NOT a change.
    # Wait: x_bp = x_b with bit k flipped. If j≠k, then x_bp[j] = x_b[j].
    # So x_j changes ONLY when j=k (the flipped bit).

    # This means: input wire info = number of transitions using that variable
    print(f"\n  Input variable = flipped bit transitions:")
    for i in range(n):
        count = sum(1 for _, j, _ in transitions if j == i)
        print(f"    x_{i}: {count} transitions (= I_∂(x_{i}))")

    # So max input info is bounded by max(count over j)
    # For balanced instances: max ~|∂f|/n
    # This is the bottleneck: each variable carries at most |∂f|/n info

    # For a circuit of size s:
    # Each gate combines two inputs → can carry info of both
    # After d levels of combination: info ≤ 2^d * max_input_info
    # To carry all |∂f|: 2^d * |∂f|/n ≥ |∂f| → d ≥ log₂(n)
    # This gives: depth ≥ log(n), not size ≥ exp(n)

    # The issue: gates COMBINE information, so the total info grows
    # exponentially with depth. A circuit of size poly(n) and depth O(log n)
    # can carry all |∂f| information.

    print(f"\n  CONCLUSION: Information bottleneck gives only depth ≥ log(n)")
    print(f"  NOT sufficient for super-polynomial size bounds")
    print(f"  Reason: gates combine info → exponential growth with depth")

    return max_input_info, sum_input_info


def mutual_info_boundary_vs_correction(n, clauses):
    """Compute mutual information between wire values and the
    "correction identity" (which variable j corrects x_b).

    The correction function g(x_b) = j has log₂(n) bits of entropy.
    How much does each wire reveal about g?

    This is different from I_∂: it measures WHICH transition happens,
    not WHETHER a transition happens.
    """
    solutions = set()
    for bits in range(2**n):
        x = tuple((bits >> i) & 1 for i in range(n))
        if evaluate_mono3sat(x, clauses):
            solutions.add(x)

    # Boundary points with their correction variables
    boundary = []
    for bits in range(2**n):
        x_b = tuple((bits >> i) & 1 for i in range(n))
        if x_b in solutions:
            continue
        corrections = []
        for j in range(n):
            if x_b[j] == 0:
                fl = list(x_b); fl[j] = 1
                if tuple(fl) in solutions:
                    corrections.append(j)
        if corrections:
            boundary.append((x_b, corrections))

    if not boundary:
        return

    print(f"\n{'='*70}")
    print(f"  MUTUAL INFORMATION: Wire Values vs Correction Identity (n={n})")
    print(f"  |∂f| = {len(boundary)} boundary points")
    print(f"{'='*70}")

    # For each input variable x_i:
    # Compute MI between x_i and the correction variable j
    # P(x_i=0|j=k) vs P(x_i=0|j=l) — if different, x_i reveals info about j

    print(f"\n  Per-input MI with correction variable:")

    for i in range(n):
        # Split boundary by x_i value
        counts = defaultdict(lambda: defaultdict(int))
        for x_b, corrections in boundary:
            val = x_b[i]
            for j in corrections:
                counts[val][j] += 1

        # Compute mutual information
        total = sum(len(corrs) for _, corrs in boundary)
        mi = 0.0

        for val in [0, 1]:
            val_total = sum(counts[val].values())
            if val_total == 0:
                continue
            p_val = val_total / total
            for j in range(n):
                p_j_given_val = counts[val][j] / val_total if val_total > 0 else 0
                p_j = sum(counts[v][j] for v in [0,1]) / total

                if p_j_given_val > 0 and p_j > 0:
                    mi += p_val * p_j_given_val * math.log2(p_j_given_val / p_j)

        print(f"    x_{i}: MI = {mi:.4f} bits")

    # Total MI from all inputs
    # H(correction) = log₂(n) ≈ {math.log2(n)} bits
    print(f"\n  H(correction) ≈ {math.log2(n):.2f} bits (uniform)")
    print(f"  To identify correction, circuit needs ≥ {math.log2(n):.2f} bits total")
    print(f"  But circuit has {n} input bits = {n} bits available")
    print(f"  Ratio: {n / math.log2(n):.1f}x redundancy")


if __name__ == "__main__":
    random.seed(42)

    from mono3sat import generate_all_mono3sat_clauses

    for n in [6, 8, 10, 12]:
        if 2**n > 100000:
            break

        all_clauses = generate_all_mono3sat_clauses(n)

        # Find good instance
        best_boundary = 0
        best_clauses = None

        for _ in range(100):
            k = random.randint(max(1, n//2), min(len(all_clauses), 4*n))
            clauses = random.sample(all_clauses, k)
            sols = sum(1 for bits in range(2**n)
                      if evaluate_mono3sat(tuple((bits>>i)&1 for i in range(n)), clauses))
            if 0 < sols < 2**n:
                trans = 0
                for bits in range(2**n):
                    x = tuple((bits>>i)&1 for i in range(n))
                    if evaluate_mono3sat(x, clauses):
                        continue
                    for j in range(n):
                        if x[j] == 0:
                            fl = list(x); fl[j] = 1
                            if evaluate_mono3sat(tuple(fl), clauses):
                                trans += 1
                                break
                if trans > best_boundary:
                    best_boundary = trans
                    best_clauses = clauses[:]

        if best_clauses:
            analyze_info_flow(n, best_clauses)
            analyze_optimal_info_distribution(n, best_clauses)
            mutual_info_boundary_vs_correction(n, best_clauses)
