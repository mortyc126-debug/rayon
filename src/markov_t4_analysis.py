"""
Markov's Theorem + T4: The Precise Structure of the P vs NP Barrier.

CRITICAL OBSERVATION:

Markov 1958: Any Boolean function on n variables can be computed by a
circuit using at most ⌈log₂(n+1)⌉ NOT gates.

T4 (from document): Any circuit with s < 0.844n NOT gates computing a
function with |∂f| ≥ 1.795^n has size ≥ exp(Ω(n)).

Since ⌈log₂(n+1)⌉ ≪ 0.844n for all n ≥ 2, T4 COVERS circuits with
the Markov-minimum number of NOT gates.

IMPLICATION:
  Let C be ANY circuit of size s computing f.
  By Markov: C can be converted to C' with ⌈log₂(n+1)⌉ NOT gates.
  By T4: size(C') ≥ exp(Ω(n)).
  So: size(C') ≥ exp(Ω(n)).

  If the Markov conversion increases size by factor R(s):
    size(C') ≤ s · R(s)
    So: s · R(s) ≥ exp(Ω(n))
    So: s ≥ exp(Ω(n)) / R(s)

  If R(s) is POLYNOMIAL: s ≥ exp(Ω(n)) / poly(n) → s ≥ exp(Ω(n))
  This proves f needs EXPONENTIAL circuits → P ≠ NP

  If R(s) is EXPONENTIAL: we get nothing useful.

THE KEY QUESTION: What is R(s) — the size blowup from Markov's
conversion from s NOT gates to O(log n) NOT gates?

This module:
1. Computes I(f, k) = min circuit size with exactly k NOT gates
2. Measures the actual R(s) for small instances
3. Identifies structural reasons for size increase
4. Tests whether R(s) is polynomial or exponential

THIS IS THE EXACT BOTTLENECK FOR P VS NP.
"""

import itertools
from collections import defaultdict
import random
import math
import sys
import time


def evaluate_function(truth_table, x_int):
    """Evaluate function from truth table at input x (as integer)."""
    return truth_table[x_int]


class SmallCircuit:
    """Optimized circuit representation for brute-force search."""

    def __init__(self, n):
        self.n = n
        self.gates = []  # (type_id, inp1, inp2)
        # type_id: 0=AND, 1=OR, 2=NOT

    def add(self, type_id, inp1, inp2=-1):
        idx = self.n + len(self.gates)
        self.gates.append((type_id, inp1, inp2))
        return idx

    def pop(self):
        self.gates.pop()

    def evaluate_tt(self):
        """Return truth table as list of 2^n values."""
        n = self.n
        num_inputs = 2**n
        total = self.n + len(self.gates)

        # Compute truth table for ALL inputs simultaneously
        # Use bitwise operations on integers
        # wire_tt[w] = integer where bit i = value of wire w on input i
        wire_tt = [0] * total

        # Input wires: bit i of wire j = bit j of input i
        for j in range(n):
            mask = 0
            for i in range(num_inputs):
                if (i >> j) & 1:
                    mask |= (1 << i)
            wire_tt[j] = mask

        all_ones = (1 << num_inputs) - 1

        for gi, (type_id, inp1, inp2) in enumerate(self.gates):
            idx = n + gi
            if type_id == 0:  # AND
                wire_tt[idx] = wire_tt[inp1] & wire_tt[inp2]
            elif type_id == 1:  # OR
                wire_tt[idx] = wire_tt[inp1] | wire_tt[inp2]
            elif type_id == 2:  # NOT
                wire_tt[idx] = all_ones ^ wire_tt[inp1]

        return wire_tt[-1] if self.gates else 0

    def not_count(self):
        return sum(1 for t, _, _ in self.gates if t == 2)

    def size(self):
        return len(self.gates)


def find_min_circuit_with_k_nots(n, target_tt, max_size, k_nots):
    """Find minimum-size circuit with exactly k_nots NOT gates.

    Uses iterative deepening DFS.
    target_tt: integer representing truth table.

    Returns circuit size or None if not found within max_size.
    """
    for size in range(1, max_size + 1):
        circuit = SmallCircuit(n)
        result = _search_k_nots(circuit, n, target_tt, size, k_nots, 0, 0)
        if result is not None:
            return result
    return None


def _search_k_nots(circuit, n, target_tt, target_size, target_nots,
                    current_nots, depth):
    """DFS search for circuit of exact size and NOT count."""
    if depth == target_size:
        if current_nots != target_nots:
            return None
        tt = circuit.evaluate_tt()
        if tt == target_tt:
            return depth
        return None

    remaining = target_size - depth
    nots_needed = target_nots - current_nots

    # Pruning: can't use more NOTs than remaining gates
    if nots_needed > remaining or nots_needed < 0:
        return None

    total_wires = n + depth

    # Try AND gates
    if nots_needed < remaining:  # leave room for remaining NOTs
        for inp1 in range(total_wires):
            for inp2 in range(inp1, total_wires):
                circuit.add(0, inp1, inp2)
                result = _search_k_nots(circuit, n, target_tt, target_size,
                                         target_nots, current_nots, depth + 1)
                if result is not None:
                    return result
                circuit.pop()

    # Try OR gates
    if nots_needed < remaining:
        for inp1 in range(total_wires):
            for inp2 in range(inp1, total_wires):
                circuit.add(1, inp1, inp2)
                result = _search_k_nots(circuit, n, target_tt, target_size,
                                         target_nots, current_nots, depth + 1)
                if result is not None:
                    return result
                circuit.pop()

    # Try NOT gates
    if current_nots < target_nots:
        for inp1 in range(total_wires):
            circuit.add(2, inp1)
            result = _search_k_nots(circuit, n, target_tt, target_size,
                                     target_nots, current_nots + 1, depth + 1)
            if result is not None:
                return result
            circuit.pop()

    return None


def find_min_circuit_any_nots(n, target_tt, max_size, max_nots=None):
    """Find minimum-size circuit with at most max_nots NOT gates.

    More efficient: doesn't constrain exact NOT count.
    """
    for size in range(1, max_size + 1):
        circuit = SmallCircuit(n)
        mn = max_nots if max_nots is not None else size
        result = _search_any(circuit, n, target_tt, size, mn, 0, 0)
        if result is not None:
            return result
    return None


def _search_any(circuit, n, target_tt, target_size, max_nots,
                current_nots, depth):
    """DFS search with at most max_nots NOT gates."""
    if depth == target_size:
        tt = circuit.evaluate_tt()
        if tt == target_tt:
            return (depth, current_nots)
        return None

    total_wires = n + depth

    # Try AND and OR gates
    for gate_type in [0, 1]:  # AND, OR
        for inp1 in range(total_wires):
            for inp2 in range(inp1, total_wires):
                circuit.add(gate_type, inp1, inp2)
                result = _search_any(circuit, n, target_tt, target_size,
                                      max_nots, current_nots, depth + 1)
                if result is not None:
                    return result
                circuit.pop()

    # Try NOT gates
    if current_nots < max_nots:
        for inp1 in range(total_wires):
            circuit.add(2, inp1)
            result = _search_any(circuit, n, target_tt, target_size,
                                  max_nots, current_nots + 1, depth + 1)
            if result is not None:
                return result
            circuit.pop()

    return None


def compute_truth_table_int(n, func):
    """Compute truth table as integer."""
    tt = 0
    for i in range(2**n):
        x = tuple((i >> j) & 1 for j in range(n))
        if func(x):
            tt |= (1 << i)
    return tt


def analyze_not_size_tradeoff():
    """Main experiment: compute I(f, k) for various functions and k values.

    I(f, k) = minimum circuit size for f using at most k NOT gates.

    The P vs NP question reduces to:
    Is I(f, O(log n)) / I(f, ∞) polynomial or exponential?
    """
    print("=" * 80)
    print("  NOT-GATE vs CIRCUIT SIZE TRADEOFF")
    print("  I(f, k) = min circuit size with ≤ k NOT gates")
    print("  P ≠ NP ⟺ I(f, O(log n)) / I(f, ∞) is polynomial")
    print("=" * 80)

    # Test functions on n=3 variables (8 truth table values)
    n = 3

    # Generate interesting functions:
    # 1. MONO-3SAT instances (monotone)
    # 2. Non-monotone functions with varying complexity
    # 3. Functions requiring different numbers of NOT gates

    test_functions = {}

    # All monotone 3-SAT clauses on 3 variables: only (0,1,2)
    clause = (0, 1, 2)
    test_functions['OR(x0,x1,x2)'] = lambda x: 1 if any(x[i] for i in [0,1,2]) else 0
    test_functions['AND(x0,x1,x2)'] = lambda x: x[0] & x[1] & x[2]
    test_functions['MAJ(x0,x1,x2)'] = lambda x: 1 if sum(x) >= 2 else 0
    test_functions['XOR(x0,x1,x2)'] = lambda x: x[0] ^ x[1] ^ x[2]
    test_functions['NAND(x0,x1,x2)'] = lambda x: 1 - (x[0] & x[1] & x[2])
    test_functions['x0 AND NOT x1'] = lambda x: x[0] & (1 - x[1])
    test_functions['(x0∧x1)∨(¬x0∧x2)'] = lambda x: (x[0] & x[1]) | ((1-x[0]) & x[2])
    test_functions['MUX(x0,x1,x2)'] = lambda x: x[1] if x[0] else x[2]

    # Also test on n=4
    test_functions_4 = {}
    test_functions_4['MAJ4'] = lambda x: 1 if sum(x) >= 2 else 0
    test_functions_4['XOR4'] = lambda x: x[0]^x[1]^x[2]^x[3]
    test_functions_4['(x0∧x1)∨(x2∧x3)'] = lambda x: (x[0]&x[1]) | (x[2]&x[3])
    test_functions_4['(x0⊕x1)∧(x2⊕x3)'] = lambda x: (x[0]^x[1]) & (x[2]^x[3])
    test_functions_4['MONO-3SAT-4'] = lambda x: (x[0]|x[1]|x[2]) & (x[1]|x[2]|x[3]) & (x[0]|x[2]|x[3])

    # n=3 analysis
    print(f"\n{'─'*80}")
    print(f"  n = 3 (8 inputs)")
    print(f"  Markov bound: ⌈log₂(4)⌉ = 2 NOT gates suffice")
    print(f"{'─'*80}")

    max_search_size = 7  # feasible for brute force

    print(f"\n  {'Function':<25} ", end="")
    for k in range(max_search_size + 1):
        print(f"{'I(f,'+str(k)+')':>7}", end="")
    print(f" {'Ratio':>8}")

    for name, func in sorted(test_functions.items()):
        tt = compute_truth_table_int(3, func)

        # Check if monotone
        is_monotone = True
        for i in range(8):
            if (tt >> i) & 1:
                for j in range(3):
                    if (i >> j) & 1:
                        smaller = i & ~(1 << j)
                        if not ((tt >> smaller) & 1):
                            is_monotone = False

        results = {}
        print(f"  {name:<25} ", end="")
        sys.stdout.flush()

        for k in range(max_search_size + 1):
            r = find_min_circuit_any_nots(3, tt, max_search_size, max_nots=k)
            if r is not None:
                results[k] = r[0]
                print(f"{r[0]:>7}", end="")
            else:
                results[k] = None
                print(f"  >>{max_search_size}  ", end="")
            sys.stdout.flush()

        # Compute ratio I(f, 0) / I(f, ∞)
        if results.get(0) and results.get(max_search_size):
            ratio = results[0] / results[max_search_size]
            print(f" {ratio:>8.2f}", end="")
        print()

    # n=4 analysis
    print(f"\n{'─'*80}")
    print(f"  n = 4 (16 inputs)")
    print(f"  Markov bound: ⌈log₂(5)⌉ = 3 NOT gates suffice")
    print(f"{'─'*80}")

    max_search_size_4 = 6

    print(f"\n  {'Function':<25} ", end="")
    for k in range(max_search_size_4 + 1):
        print(f"{'I(f,'+str(k)+')':>7}", end="")
    print(f" {'Ratio':>8}")

    for name, func in sorted(test_functions_4.items()):
        tt = compute_truth_table_int(4, func)

        results = {}
        print(f"  {name:<25} ", end="")
        sys.stdout.flush()

        for k in range(max_search_size_4 + 1):
            t0 = time.time()
            r = find_min_circuit_any_nots(4, tt, max_search_size_4, max_nots=k)
            dt = time.time() - t0

            if r is not None:
                results[k] = r[0]
                print(f"{r[0]:>7}", end="")
            else:
                results[k] = None
                print(f"    >>{max_search_size_4}", end="")

            sys.stdout.flush()

            if dt > 30:  # timeout for remaining k values
                for k2 in range(k+1, max_search_size_4 + 1):
                    print(f"   skip", end="")
                break

        if results.get(0) and results.get(max_search_size_4):
            ratio = results[0] / results[max_search_size_4]
            print(f" {ratio:>8.2f}", end="")
        print()

    print(f"\n{'='*80}")
    print("  INTERPRETATION")
    print(f"{'='*80}")
    print("""
    I(f, k) = minimum circuit size with at most k NOT gates.

    For P ≠ NP, we need: I(f, O(log n)) / I(f, poly(n)) is POLYNOMIAL
    for some specific NP-hard function f.

    This means: reducing NOT gates from poly(n) to O(log n) should NOT
    cause more than polynomial size increase.

    If the ratio I(f, 0) / I(f, ∞) is SMALL (constant or polynomial in n):
      → NOT gates don't help much → monotone lower bounds transfer
      → P ≠ NP (for this class of functions)

    If the ratio is LARGE (exponential):
      → NOT gates provide exponential savings
      → Monotone lower bounds don't transfer
      → This function might be in P even though its monotone complexity is high

    KEY: For NP-hard functions, which regime applies?
    """)


if __name__ == "__main__":
    random.seed(42)
    analyze_not_size_tradeoff()
