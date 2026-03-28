"""
Circuit complexity analysis for the P vs NP barrier.

Key insight from the research document:
- The Z₂-orbit argument works for s < 0.844n NOT gates
- Threshold 0.844 = log₂(1.795) comes from |∂f| ≈ 1.795^n
- If we find a DIFFERENT counting argument that doesn't lose 2^s factor,
  we might close the gap

This module explores:
1. Minimum circuit size for small MONO-3SAT instances
2. How NOT gates actually help circuits
3. The "switching" structure that NOT enables
"""

import itertools
from collections import defaultdict
import random
import math


class BooleanCircuit:
    """A Boolean circuit with AND, OR, NOT gates."""

    def __init__(self, n_inputs):
        self.n_inputs = n_inputs
        self.gates = []  # list of (type, input1, input2_or_None)
        # type: 'AND', 'OR', 'NOT'
        # inputs are indices: 0..n-1 for inputs, n.. for gate outputs

    def add_gate(self, gate_type, inp1, inp2=None):
        idx = self.n_inputs + len(self.gates)
        self.gates.append((gate_type, inp1, inp2))
        return idx

    def evaluate(self, assignment):
        """Evaluate circuit on an assignment."""
        values = list(assignment) + [None] * len(self.gates)
        for i, (gtype, inp1, inp2) in enumerate(self.gates):
            idx = self.n_inputs + i
            if gtype == 'NOT':
                values[idx] = 1 - values[inp1]
            elif gtype == 'AND':
                values[idx] = values[inp1] & values[inp2]
            elif gtype == 'OR':
                values[idx] = values[inp1] | values[inp2]
        return values[-1] if self.gates else 0

    def size(self):
        return len(self.gates)

    def not_count(self):
        return sum(1 for g in self.gates if g[0] == 'NOT')


def truth_table(n, func):
    """Compute truth table of a function on n variables."""
    table = {}
    for bits in range(2**n):
        assignment = tuple((bits >> i) & 1 for i in range(n))
        table[assignment] = func(assignment)
    return table


def minimum_circuit_size_bruteforce(n, target_func, max_gates=10, allow_not=True):
    """Find minimum circuit computing target_func.

    Brute force: try all circuits of increasing size.
    Only feasible for very small n (3-5).

    Returns (size, not_count, circuit) or None.
    """
    target = truth_table(n, target_func)

    for num_gates in range(1, max_gates + 1):
        result = _search_circuit(n, target, num_gates, allow_not)
        if result is not None:
            return result

    return None


def _search_circuit(n, target, num_gates, allow_not, depth=0, circuit=None):
    """DFS search for a circuit of exactly num_gates gates that computes target."""
    if circuit is None:
        circuit = BooleanCircuit(n)

    if depth == num_gates:
        # Check if circuit computes target
        for assignment, expected in target.items():
            if circuit.evaluate(assignment) != expected:
                return None
        return (circuit.size(), circuit.not_count(), circuit)

    total_wires = n + depth  # available signals

    gate_types = ['AND', 'OR']
    if allow_not:
        gate_types.append('NOT')

    for gtype in gate_types:
        if gtype == 'NOT':
            for inp1 in range(total_wires):
                idx = circuit.add_gate('NOT', inp1)
                result = _search_circuit(n, target, num_gates, allow_not, depth + 1, circuit)
                if result is not None:
                    return result
                circuit.gates.pop()
        else:
            for inp1 in range(total_wires):
                for inp2 in range(inp1, total_wires):
                    idx = circuit.add_gate(gtype, inp1, inp2)
                    result = _search_circuit(n, target, num_gates, allow_not, depth + 1, circuit)
                    if result is not None:
                        return result
                    circuit.gates.pop()

    return None


def mono3sat_function(n, clauses):
    """Return the function computed by a MONO-3SAT instance."""
    def f(assignment):
        for clause in clauses:
            if not any(assignment[v] for v in clause):
                return 0
        return 1
    return f


def analyze_not_gate_necessity(n, clauses):
    """Compare circuit size with and without NOT gates.

    If NOT gates don't help much, the monotone lower bound transfers.
    If NOT gates help a lot, we need to understand HOW they help.
    """
    f = mono3sat_function(n, clauses)
    target = truth_table(n, f)

    # Check if function is interesting (not trivial)
    ones = sum(target.values())
    if ones == 0 or ones == 2**n:
        return None

    print(f"\nCircuit analysis for MONO-3SAT (n={n}, {len(clauses)} clauses)")
    print(f"  |solutions| = {ones}, |non-solutions| = {2**n - ones}")

    # Find minimum circuit WITH NOT
    max_g = min(8, 2*n)
    result_with = minimum_circuit_size_bruteforce(n, f, max_gates=max_g, allow_not=True)

    # Find minimum circuit WITHOUT NOT (monotone)
    result_without = minimum_circuit_size_bruteforce(n, f, max_gates=max_g, allow_not=False)

    if result_with:
        print(f"  Min circuit (with NOT): {result_with[0]} gates, {result_with[1]} NOT gates")
    else:
        print(f"  Min circuit (with NOT): > {max_g} gates")

    if result_without:
        print(f"  Min circuit (no NOT):   {result_without[0]} gates")
    else:
        print(f"  Min circuit (no NOT):   > {max_g} gates")

    if result_with and result_without:
        savings = result_without[0] - result_with[0]
        print(f"  NOT gate savings: {savings} gates")
        print(f"  NOT gates used: {result_with[1]}")
        if result_with[1] > 0:
            print(f"  Savings per NOT: {savings/result_with[1]:.2f}")

    return result_with, result_without


def analyze_switching_with_not(n, clauses):
    """Analyze the switching behavior that NOT gates enable.

    Document key insight: NOT changes direction of switching.
    One gate x_{i*} switches 0→1 for x_b AND 1→0 for x_b' through different path.

    We analyze: for a given boundary pair (x_b, x_b⁺),
    which signals in the circuit actually switch?
    """
    from mono3sat import compute_boundary

    boundary, solutions = compute_boundary(n, clauses)

    print(f"\nSwitching analysis (n={n}, |∂f|={len(boundary)})")

    # For each pair of inputs that differ in one bit,
    # count how many boundary transitions it "explains"
    for i in range(n):
        # How many boundary transitions use bit i?
        count = sum(1 for _, j, _ in boundary if j == i)

        # How many non-boundary transitions use bit i?
        # (flip bit i in a non-solution, still non-solution → no boundary crossing)
        non_boundary_flips = 0
        for bits in range(2**n):
            assignment = tuple((bits >> k) & 1 for k in range(n))
            if assignment in solutions:
                continue
            if assignment[i] == 0:
                flipped = list(assignment)
                flipped[i] = 1
                if tuple(flipped) not in solutions:
                    non_boundary_flips += 1

        print(f"  Bit {i}: {count} boundary crossings, {non_boundary_flips} non-crossings")


def compute_sensitivity(n, f_func):
    """Compute sensitivity and block sensitivity of function f."""
    target = truth_table(n, f_func)

    max_sens = 0
    total_sens = 0

    for assignment, val in target.items():
        sens = 0
        for i in range(n):
            flipped = list(assignment)
            flipped[i] = 1 - flipped[i]
            if target[tuple(flipped)] != val:
                sens += 1
        max_sens = max(max_sens, sens)
        total_sens += sens

    avg_sens = total_sens / (2**n)
    return max_sens, avg_sens


def main():
    random.seed(42)
    print("=" * 70)
    print("  Circuit Complexity Analysis")
    print("  Comparing monotone vs general circuit size")
    print("=" * 70)

    # Small instances where brute force is feasible
    for n in [3, 4, 5]:
        print(f"\n--- n = {n} ---")

        # Generate several MONO-3SAT instances
        from mono3sat import generate_all_mono3sat_clauses, compute_solution_set

        all_clauses = generate_all_mono3sat_clauses(n)

        best_gap = 0
        best_clauses = None

        # Try random subsets
        for trial in range(min(200, 2**len(all_clauses))):
            if trial < 2**len(all_clauses):
                # Try subset indexed by trial
                if len(all_clauses) <= 15:
                    selected = [all_clauses[i] for i in range(len(all_clauses))
                               if (trial >> i) & 1]
                else:
                    k = random.randint(1, min(len(all_clauses), 3*n))
                    selected = random.sample(all_clauses, k)
            else:
                k = random.randint(1, min(len(all_clauses), 3*n))
                selected = random.sample(all_clauses, k)

            if not selected:
                continue

            sols = compute_solution_set(n, selected)
            if 1 < len(sols) < 2**n - 1:  # non-trivial
                result = analyze_not_gate_necessity(n, selected)
                if result and result[0] and result[1]:
                    gap = result[1][0] - result[0][0]
                    if gap > best_gap:
                        best_gap = gap
                        best_clauses = selected

        if best_clauses:
            print(f"\n  >>> Best gap (NOT savings): {best_gap} gates <<<")

        # Sensitivity analysis
        if best_clauses:
            f = mono3sat_function(n, best_clauses)
            max_s, avg_s = compute_sensitivity(n, f)
            print(f"  Sensitivity: max={max_s}, avg={avg_s:.2f}")


if __name__ == "__main__":
    main()
