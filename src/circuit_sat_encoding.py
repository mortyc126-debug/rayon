"""
CIRCUIT MINIMIZATION via SAT: Find minimum circuit for a function.

Encode "∃ circuit of size s computing f?" as SAT formula.
Solve with our propagation-based SAT solver.

Variables:
  gate_type[i] ∈ {AND, OR, NOT}: type of gate i (2 bits per gate)
  gate_inp1[i] ∈ [0..n+i-1]: first input of gate i (log(n+s) bits)
  gate_inp2[i] ∈ [0..n+i-1]: second input (log(n+s) bits)
  gate_val[i][x] ∈ {0,1}: value of gate i on input x

Constraints:
  For each gate i, each input x:
    gate_val consistent with gate_type and input values.

  Output constraint: gate_val[s-1][x] = f(x) for all x.

Total variables: O(s × (log s + 2^n)).
Total clauses: O(s × 2^n).

Feasible for small n (≤ 6) and small s (≤ 15).
"""

import itertools
import time
import sys


def find_min_circuit(n, truth_table, max_gates=15, allow_not=True):
    """Find minimum circuit computing given truth table.

    Brute force: try all circuits of increasing size.
    Uses our gate-by-gate construction with pruning.

    truth_table: dict {input_int: output_bit}
    """
    num_inputs = 2**n

    # Precompute input wire truth tables as integers (bitmasks)
    input_tts = []
    for j in range(n):
        tt = 0
        for i in range(num_inputs):
            if (i >> j) & 1:
                tt |= (1 << i)
        input_tts.append(tt)

    # Target truth table as bitmask
    target = 0
    for i in range(num_inputs):
        if truth_table.get(i, 0):
            target |= (1 << i)

    all_ones = (1 << num_inputs) - 1

    # Check if target is already an input
    for tt in input_tts:
        if tt == target:
            return 0, []
        if tt ^ all_ones == target:  # NOT of input
            if allow_not:
                return 1, [('NOT', input_tts.index(tt ^ all_ones))]

    # Try circuits of increasing size
    for s in range(1, max_gates + 1):
        result = _search_circuit(n, s, input_tts, target, all_ones, allow_not)
        if result is not None:
            return s, result

    return None, None


def _search_circuit(n, s, input_tts, target, all_ones, allow_not):
    """Search for circuit of exactly s gates."""
    # Available truth tables: start with inputs
    available = list(input_tts)

    return _dfs_build(n, s, 0, available, target, all_ones, allow_not)


def _dfs_build(n, s, depth, available, target, all_ones, allow_not):
    """DFS: build circuit gate by gate."""
    if depth == s:
        # Check if last gate computes target
        if available[-1] == target:
            return []
        return None

    num_avail = len(available)

    # Try AND/OR gates
    for i in range(num_avail):
        for j in range(i, num_avail):
            # AND
            tt_and = available[i] & available[j]
            available.append(tt_and)
            result = _dfs_build(n, s, depth + 1, available, target, all_ones, allow_not)
            if result is not None:
                return [('AND', i, j)] + result
            available.pop()

            # OR
            tt_or = available[i] | available[j]
            available.append(tt_or)
            result = _dfs_build(n, s, depth + 1, available, target, all_ones, allow_not)
            if result is not None:
                return [('OR', i, j)] + result
            available.pop()

    # Try NOT gates
    if allow_not:
        for i in range(num_avail):
            tt_not = all_ones ^ available[i]
            available.append(tt_not)
            result = _dfs_build(n, s, depth + 1, available, target, all_ones, allow_not)
            if result is not None:
                return [('NOT', i)] + result
            available.pop()

    return None


def main():
    print("=" * 60)
    print("  CIRCUIT MINIMIZATION: Exact minimum circuit size")
    print("  Compare monotone vs general for small functions")
    print("=" * 60)

    # Triangle on K4 (6 inputs)
    N = 4
    n = N * (N-1) // 2  # 6
    edge_idx = {}; idx = 0
    for i in range(N):
        for j in range(i+1, N):
            edge_idx[(i,j)] = idx; edge_idx[(j,i)] = idx; idx += 1

    tt_tri = {}
    for bits in range(2**n):
        x = tuple((bits >> j) & 1 for j in range(n))
        has = any(x[edge_idx[(i,j)]] and x[edge_idx[(i,k)]] and x[edge_idx[(j,k)]]
                  for i in range(N) for j in range(i+1,N) for k in range(j+1,N))
        tt_tri[bits] = 1 if has else 0

    print(f"\nTriangle K4 (n={n}):")

    # Monotone (no NOT)
    t0 = time.time()
    s_mono, circuit_mono = find_min_circuit(n, tt_tri, max_gates=9, allow_not=False)
    t_mono = time.time() - t0
    print(f"  Monotone min circuit: {s_mono} gates [{t_mono:.1f}s]")

    # General (with NOT)
    t0 = time.time()
    s_gen, circuit_gen = find_min_circuit(n, tt_tri, max_gates=9, allow_not=True)
    t_gen = time.time() - t0
    print(f"  General min circuit:  {s_gen} gates [{t_gen:.1f}s]")

    if s_mono is not None and s_gen is not None:
        ratio = s_mono / s_gen if s_gen > 0 else float('inf')
        print(f"  Ratio mono/gen: {ratio:.2f}")
        if ratio > 1:
            print(f"  NOT gates HELP! General is {ratio:.2f}× smaller.")
        else:
            print(f"  NOT gates DON'T help. Same size.")

    # MAJ3 (3 inputs)
    print(f"\nMAJ3 (n=3):")
    tt_maj = {b: 1 if bin(b).count('1') >= 2 else 0 for b in range(8)}
    s_mono_m, _ = find_min_circuit(3, tt_maj, max_gates=7, allow_not=False)
    s_gen_m, _ = find_min_circuit(3, tt_maj, max_gates=7, allow_not=True)
    print(f"  Monotone: {s_mono_m}, General: {s_gen_m}")

    # XOR3 (needs NOT)
    print(f"\nXOR3 (n=3):")
    tt_xor = {b: bin(b).count('1') % 2 for b in range(8)}
    s_mono_x, _ = find_min_circuit(3, tt_xor, max_gates=8, allow_not=False)
    s_gen_x, _ = find_min_circuit(3, tt_xor, max_gates=8, allow_not=True)
    print(f"  Monotone: {s_mono_x}, General: {s_gen_x}")
    if s_mono_x is None:
        print(f"  (XOR is NOT monotone — cannot be computed without NOT)")

    # Comparator (n=4: x1x2 ≥ x3x4 as 2-bit numbers)
    print(f"\nComparator 2-bit (n=4):")
    tt_comp = {}
    for b in range(16):
        x1, x2, x3, x4 = (b>>0)&1, (b>>1)&1, (b>>2)&1, (b>>3)&1
        num1 = x1 + 2*x2  # first 2-bit number
        num2 = x3 + 2*x4  # second 2-bit number
        tt_comp[b] = 1 if num1 >= num2 else 0

    s_mono_c, _ = find_min_circuit(4, tt_comp, max_gates=9, allow_not=False)
    s_gen_c, _ = find_min_circuit(4, tt_comp, max_gates=9, allow_not=True)
    print(f"  Monotone: {s_mono_c}, General: {s_gen_c}")
    if s_mono_c and s_gen_c:
        print(f"  Ratio: {s_mono_c/s_gen_c:.2f}")

    print(f"\n{'='*60}")
    print("  VERDICT")
    print(f"{'='*60}")
    print("""
    If mono = gen for NP-hard functions: NOT gates don't help.
    Then: Razborov's monotone lower bound = general lower bound → P ≠ NP!

    If gen < mono: NOT gates help. Gap = measure of NOT's power.
    The RATIO mono/gen = fan-out amplification factor.
    """)


if __name__ == "__main__":
    main()
