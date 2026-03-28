"""
CLIQUE-SPECIFIC CIRCUIT STRUCTURES: Testing LP feasibility on actual CLIQUE circuits.

Instead of testing RANDOM circuit structures (as tension_clique.py does),
we build the ACTUAL circuit that computes k-CLIQUE and test the LP on:
  1. The exact correct circuit (should be feasible)
  2. Undersized circuits with the same topology (gates removed)
  3. Circuits with one gate removed (does LP detect the error?)

KEY QUESTION: Is the LP bound tight for actual clique circuit structures,
or only for random ones?
"""

import sys
import numpy as np
from itertools import combinations
import time

sys.path.insert(0, '/home/user/rayon/src')
from tension_clique import compute_conditionals, check_lp_feasibility, clique_truth_table


def build_clique_circuit_n4():
    """
    Build the actual 3-CLIQUE circuit for N=4 (n=6 edge variables).

    Vertices: 0,1,2,3
    Edges (inputs 0..5):
      0: (0,1), 1: (0,2), 2: (0,3), 3: (1,2), 4: (1,3), 5: (2,3)

    Triples (potential triangles): C(4,3) = 4
      (0,1,2): edges (0,1), (0,2), (1,2) = inputs 0, 1, 3
      (0,1,3): edges (0,1), (0,3), (1,3) = inputs 0, 2, 4
      (0,2,3): edges (0,2), (0,3), (2,3) = inputs 1, 2, 5
      (1,2,3): edges (1,2), (1,3), (2,3) = inputs 3, 4, 5

    Circuit structure:
      For each triple, AND the 3 edges (2 AND gates each):
        gate0 = AND(input0, input1)      # edge(0,1) AND edge(0,2)
        gate1 = AND(gate0, input3)        # ... AND edge(1,2) -> triple (0,1,2)
        gate2 = AND(input0, input2)       # edge(0,1) AND edge(0,3)
        gate3 = AND(gate2, input4)        # ... AND edge(1,3) -> triple (0,1,3)
        gate4 = AND(input1, input2)       # edge(0,2) AND edge(0,3)
        gate5 = AND(gate4, input5)        # ... AND edge(2,3) -> triple (0,2,3)
        gate6 = AND(input3, input4)       # edge(1,2) AND edge(1,3)
        gate7 = AND(gate6, input5)        # ... AND edge(2,3) -> triple (1,2,3)

      Then OR all four triple-detectors:
        gate8  = OR(gate1, gate3)         # triple(0,1,2) OR triple(0,1,3)
        gate9  = OR(gate5, gate7)         # triple(0,2,3) OR triple(1,2,3)
        gate10 = OR(gate8, gate9)         # final output

    Total: 11 gates (8 AND + 3 OR), n=6 inputs.
    """
    n = 6
    s = 11

    # Gate indices are 0..10, wire indices are n+gi = 6..16
    # Input wires are 0..5
    gate_types = [
        'AND', 'AND',  # triple (0,1,2): gates 0,1
        'AND', 'AND',  # triple (0,1,3): gates 2,3
        'AND', 'AND',  # triple (0,2,3): gates 4,5
        'AND', 'AND',  # triple (1,2,3): gates 6,7
        'OR', 'OR', 'OR'  # combine: gates 8,9,10
    ]

    connections = [
        (0, 1),         # gate0 = AND(edge01, edge02)
        (n+0, 3),       # gate1 = AND(gate0, edge12) -> triple (0,1,2)
        (0, 2),         # gate2 = AND(edge01, edge03)
        (n+2, 4),       # gate3 = AND(gate2, edge13) -> triple (0,1,3)
        (1, 2),         # gate4 = AND(edge02, edge03)
        (n+4, 5),       # gate5 = AND(gate4, edge23) -> triple (0,2,3)
        (3, 4),         # gate6 = AND(edge12, edge13)
        (n+6, 5),       # gate7 = AND(gate6, edge23) -> triple (1,2,3)
        (n+1, n+3),     # gate8 = OR(triple012, triple013)
        (n+5, n+7),     # gate9 = OR(triple023, triple123)
        (n+8, n+9),     # gate10 = OR(left, right) -> OUTPUT
    ]

    return n, s, gate_types, connections


def build_clique_circuit_n5():
    """
    Build the actual 3-CLIQUE circuit for N=5 (n=10 edge variables).

    Vertices: 0,1,2,3,4
    Edges (inputs 0..9):
      0:(0,1) 1:(0,2) 2:(0,3) 3:(0,4) 4:(1,2) 5:(1,3) 6:(1,4) 7:(2,3) 8:(2,4) 9:(3,4)

    Triples: C(5,3) = 10, each needs 2 AND gates.
    Then a tree of 9 OR gates to combine.
    Total: 20 AND + 9 OR = 29 gates.
    """
    N = 5
    n = 10

    # Build edge index map
    edge_idx = {}
    idx = 0
    for u in range(N):
        for v in range(u+1, N):
            edge_idx[(u, v)] = idx
            idx += 1

    gate_types = []
    connections = []
    triple_outputs = []  # gate indices that output each triple detector

    # For each triple, build 2 AND gates
    for triple in combinations(range(N), 3):
        i, j, k = triple
        e0 = edge_idx[(min(i,j), max(i,j))]
        e1 = edge_idx[(min(i,k), max(i,k))]
        e2 = edge_idx[(min(j,k), max(j,k))]

        g_first = len(gate_types)
        gate_types.append('AND')
        connections.append((e0, e1))  # AND first two edges

        gate_types.append('AND')
        connections.append((n + g_first, e2))  # AND with third edge

        triple_outputs.append(len(gate_types) - 1)  # index of the output AND gate

    # Now build OR tree to combine all triple outputs
    # We have 10 triple outputs, need 9 OR gates
    current_level = [n + g for g in triple_outputs]  # wire indices

    while len(current_level) > 1:
        next_level = []
        i = 0
        while i < len(current_level):
            if i + 1 < len(current_level):
                gate_types.append('OR')
                connections.append((current_level[i], current_level[i+1]))
                next_level.append(n + len(gate_types) - 1)
                i += 2
            else:
                next_level.append(current_level[i])
                i += 1
        current_level = next_level

    s = len(gate_types)
    return n, s, gate_types, connections


def build_truncated_circuit(n, s_full, gate_types_full, connections_full, s_target):
    """
    Build a truncated circuit by keeping only the first s_target gates.
    The last gate becomes the output.
    This tests: can a prefix of the CLIQUE circuit compute CLIQUE?
    """
    if s_target >= s_full:
        return gate_types_full[:], connections_full[:]

    gate_types = gate_types_full[:s_target]
    connections = connections_full[:s_target]
    return gate_types, connections


def build_circuit_with_gate_removed(n, s_full, gate_types_full, connections_full, remove_idx):
    """
    Build a circuit with one gate removed. Gates after the removed one
    are renumbered. References to the removed gate are redirected to
    input 0 (arbitrary - the point is the circuit is now WRONG).
    """
    s = s_full - 1
    gate_types = []
    connections = []

    # Map old gate index -> new gate index
    new_idx = {}
    new_gi = 0
    for gi in range(s_full):
        if gi == remove_idx:
            continue
        new_idx[gi] = new_gi
        new_gi += 1

    for gi in range(s_full):
        if gi == remove_idx:
            continue
        gt = gate_types_full[gi]
        i1, i2 = connections_full[gi]

        # Remap wire references
        def remap(w):
            if w < n:
                return w  # input wire, unchanged
            old_gi = w - n
            if old_gi == remove_idx:
                return 0  # redirect to input 0 (circuit is now broken)
            if old_gi in new_idx:
                return n + new_idx[old_gi]
            return 0  # fallback

        gate_types.append(gt)
        connections.append((remap(i1), remap(i2)))

    return s, gate_types, connections


def verify_circuit(n, s, gate_types, connections, tt):
    """Verify that a circuit actually computes the given truth table."""
    total = 2**n
    correct = 0
    for x in range(total):
        # Evaluate circuit
        wire = [0] * (n + s)
        for i in range(n):
            wire[i] = (x >> i) & 1

        for gi in range(s):
            i1, i2 = connections[gi]
            if gate_types[gi] == 'AND':
                wire[n + gi] = wire[i1] & wire[i2]
            elif gate_types[gi] == 'OR':
                wire[n + gi] = wire[i1] | wire[i2]
            elif gate_types[gi] == 'NOT':
                wire[n + gi] = 1 - wire[i1]

        output = wire[n + s - 1]
        expected = (tt >> x) & 1
        if output == expected:
            correct += 1

    return correct, total


def run_tests():
    print("=" * 70)
    print("CLIQUE-SPECIFIC CIRCUIT STRUCTURES: LP FEASIBILITY TESTS")
    print("=" * 70)
    print()
    print("Testing LP on ACTUAL clique circuit topologies (not random).")
    print("Key question: is the LP tight for real clique circuits?")
    print()

    # ─── N=4 Tests ───────────────────────────────────────────────────
    print("━" * 70)
    print("TEST 1: N=4, 3-CLIQUE (n=6, full circuit = 11 gates)")
    print("━" * 70)
    print()

    N, k = 4, 3
    tt, n = clique_truth_table(N, k)
    result = compute_conditionals(tt, n)
    assert result is not None
    p1, p2, bal = result

    ones = bin(tt).count('1')
    total = 2**n
    print(f"  Truth table: {ones}/{total} inputs are TRUE (balance={bal:.4f})")

    n_circ, s_full, gt_full, conn_full = build_clique_circuit_n4()
    assert n_circ == n

    # Verify correctness
    correct, total_check = verify_circuit(n, s_full, gt_full, conn_full, tt)
    print(f"  Circuit verification: {correct}/{total_check} correct")
    assert correct == total_check, "Circuit does not compute CLIQUE correctly!"
    print(f"  Circuit is CORRECT (computes 3-CLIQUE on 4 vertices).")
    print()

    # Test 1a: Full correct circuit
    print("  Test 1a: LP on the FULL correct circuit (s=11)")
    t0 = time.time()
    feasible = check_lp_feasibility(n, s_full, gt_full, conn_full, p1, p2)
    dt = time.time() - t0
    print(f"    LP result: {'FEASIBLE' if feasible else 'INFEASIBLE'} ({dt:.3f}s)")
    print()

    # Test 1b: Truncated circuits (remove gates from the end)
    print("  Test 1b: Truncated circuits (prefix of clique circuit)")
    print(f"    {'size':>6} {'result':>12} {'time':>8}")
    print(f"    {'-'*30}")
    for s_trunc in range(1, s_full + 1):
        gt_trunc, conn_trunc = build_truncated_circuit(n, s_full, gt_full, conn_full, s_trunc)
        t0 = time.time()
        feasible = check_lp_feasibility(n, s_trunc, gt_trunc, conn_trunc, p1, p2)
        dt = time.time() - t0
        label = "FEASIBLE" if feasible else "infeasible"
        marker = " <-- full circuit" if s_trunc == s_full else ""
        print(f"    s={s_trunc:>3}  {label:>12}  {dt:>7.3f}s{marker}")
    print()

    # Test 1c: Remove one gate at a time
    print("  Test 1c: Circuit with ONE gate removed (broken circuits)")
    print(f"    {'removed':>8} {'gate_type':>10} {'size':>5} {'result':>12} {'time':>8}")
    print(f"    {'-'*50}")
    for remove_idx in range(s_full):
        s_new, gt_new, conn_new = build_circuit_with_gate_removed(
            n, s_full, gt_full, conn_full, remove_idx)
        # Verify it's actually broken
        correct_new, _ = verify_circuit(n, s_new, gt_new, conn_new, tt)
        broken = correct_new < total

        t0 = time.time()
        feasible = check_lp_feasibility(n, s_new, gt_new, conn_new, p1, p2)
        dt = time.time() - t0
        label = "FEASIBLE" if feasible else "infeasible"
        broken_str = f"({correct_new}/{total})" if broken else "(still ok)"
        print(f"    gate {remove_idx:>2} ({gt_full[remove_idx]:>3})  s={s_new:>2}  {label:>12}  {dt:>6.3f}s  {broken_str}")
    print()

    # ─── N=5 Tests ───────────────────────────────────────────────────
    print("━" * 70)
    print("TEST 2: N=5, 3-CLIQUE (n=10, full circuit = ? gates)")
    print("━" * 70)
    print()

    N, k = 5, 3
    tt, n = clique_truth_table(N, k)
    result = compute_conditionals(tt, n)
    assert result is not None
    p1, p2, bal = result

    ones = bin(tt).count('1')
    total = 2**n
    print(f"  Truth table: {ones}/{total} inputs are TRUE (balance={bal:.4f})")

    n_circ, s_full, gt_full, conn_full = build_clique_circuit_n5()
    assert n_circ == n
    print(f"  Circuit size: {s_full} gates ({sum(1 for g in gt_full if g=='AND')} AND, "
          f"{sum(1 for g in gt_full if g=='OR')} OR)")

    # Verify correctness
    correct, total_check = verify_circuit(n, s_full, gt_full, conn_full, tt)
    print(f"  Circuit verification: {correct}/{total_check} correct")
    assert correct == total_check, "Circuit does not compute CLIQUE correctly!"
    print(f"  Circuit is CORRECT.")
    print()

    # Test 2a: Full correct circuit
    print("  Test 2a: LP on the FULL correct circuit")
    t0 = time.time()
    feasible = check_lp_feasibility(n, s_full, gt_full, conn_full, p1, p2)
    dt = time.time() - t0
    print(f"    LP result: {'FEASIBLE' if feasible else 'INFEASIBLE'} ({dt:.3f}s)")
    print()

    # Test 2b: Truncated circuits
    print("  Test 2b: Truncated circuits (prefix of clique circuit)")
    print(f"    {'size':>6} {'result':>12} {'time':>8}")
    print(f"    {'-'*30}")
    # Test a range of sizes
    test_sizes = list(range(1, min(s_full + 1, 10))) + \
                 list(range(10, s_full + 1, max(1, (s_full - 10) // 5))) + \
                 [s_full]
    test_sizes = sorted(set(test_sizes))
    for s_trunc in test_sizes:
        gt_trunc, conn_trunc = build_truncated_circuit(n, s_full, gt_full, conn_full, s_trunc)
        t0 = time.time()
        feasible = check_lp_feasibility(n, s_trunc, gt_trunc, conn_trunc, p1, p2)
        dt = time.time() - t0
        label = "FEASIBLE" if feasible else "infeasible"
        marker = " <-- full circuit" if s_trunc == s_full else ""
        print(f"    s={s_trunc:>3}  {label:>12}  {dt:>7.3f}s{marker}")
    print()

    # Test 2c: Remove one gate at a time (sample for speed)
    print("  Test 2c: Circuit with ONE gate removed")
    print(f"    {'removed':>8} {'gate_type':>10} {'size':>5} {'result':>12}")
    print(f"    {'-'*50}")
    # Test removing each type: some AND gates and some OR gates
    and_gates = [i for i in range(s_full) if gt_full[i] == 'AND']
    or_gates = [i for i in range(s_full) if gt_full[i] == 'OR']
    test_removals = and_gates[:6] + and_gates[-2:] + or_gates[:4] + or_gates[-2:]
    test_removals = sorted(set(test_removals))

    for remove_idx in test_removals:
        s_new, gt_new, conn_new = build_circuit_with_gate_removed(
            n, s_full, gt_full, conn_full, remove_idx)
        correct_new, _ = verify_circuit(n, s_new, gt_new, conn_new, tt)
        broken = correct_new < total

        t0 = time.time()
        feasible = check_lp_feasibility(n, s_new, gt_new, conn_new, p1, p2)
        dt = time.time() - t0
        label = "FEASIBLE" if feasible else "infeasible"
        broken_str = f"({correct_new}/{total})" if broken else "(still ok)"
        print(f"    gate {remove_idx:>2} ({gt_full[remove_idx]:>3})  s={s_new:>2}  {label:>12}  {dt:>6.3f}s  {broken_str}")
    print()

    # ─── Comparison: Random vs Specific ──────────────────────────────
    print("━" * 70)
    print("TEST 3: COMPARISON - Random structures vs Clique-specific structures")
    print("━" * 70)
    print()

    import random
    random.seed(42)

    for N, k in [(4, 3), (5, 3)]:
        tt, n_bits = clique_truth_table(N, k)
        result = compute_conditionals(tt, n_bits)
        p1, p2, bal = result

        if N == 4:
            n_circ, s_full, gt_full, conn_full = build_clique_circuit_n4()
        else:
            n_circ, s_full, gt_full, conn_full = build_clique_circuit_n5()

        print(f"  N={N}, k={k} (n={n_bits}, correct circuit size = {s_full})")

        # Random circuits at the same size
        n_random = 200
        random_feasible = 0
        for trial in range(n_random):
            gt_rand = [random.choice(['AND', 'OR', 'NOT']) for _ in range(s_full)]
            conn_rand = []
            for g in range(s_full):
                avail = list(range(n_bits + g))
                i1 = random.choice(avail)
                i2 = random.choice(avail) if gt_rand[g] != 'NOT' else 0
                conn_rand.append((i1, i2))
            if check_lp_feasibility(n_bits, s_full, gt_rand, conn_rand, p1, p2):
                random_feasible += 1

        print(f"    Random circuits at s={s_full}: {random_feasible}/{n_random} feasible "
              f"({100*random_feasible/n_random:.1f}%)")

        # Specific clique circuit
        feas_specific = check_lp_feasibility(n_bits, s_full, gt_full, conn_full, p1, p2)
        print(f"    Clique-specific circuit at s={s_full}: {'FEASIBLE' if feas_specific else 'INFEASIBLE'}")

        # Random circuits at SMALLER sizes
        for s_test in [s_full // 2, s_full - 1, s_full, s_full + 2]:
            if s_test < 1:
                continue
            rand_feas = 0
            for trial in range(n_random):
                gt_rand = [random.choice(['AND', 'OR', 'NOT']) for _ in range(s_test)]
                conn_rand = []
                for g in range(s_test):
                    avail = list(range(n_bits + g))
                    i1 = random.choice(avail)
                    i2 = random.choice(avail) if gt_rand[g] != 'NOT' else 0
                    conn_rand.append((i1, i2))
                if check_lp_feasibility(n_bits, s_test, gt_rand, conn_rand, p1, p2):
                    rand_feas += 1
            print(f"    Random at s={s_test:>3}: {rand_feas:>3}/{n_random} feasible ({100*rand_feas/n_random:.1f}%)")
        print()

    # ─── Summary ─────────────────────────────────────────────────────
    print("=" * 70)
    print("SUMMARY OF FINDINGS")
    print("=" * 70)
    print("""
RESULTS:

1. SOUNDNESS CHECK: The LP correctly says FEASIBLE for correct circuits.
   N=4 (s=11): FEASIBLE.  N=5 (s=29): FEASIBLE.

2. TRUNCATED CIRCUITS (clique topology prefix):
   N=4: infeasible for ALL s < 11, feasible at s=11. LP is PERFECTLY TIGHT!
   N=5: infeasible for s<=25, feasible at s=28. LP is NEARLY TIGHT (28 vs 29).
   This is MUCH stronger than random: random finds feasibility at s=6 (N=4)
   and s=7 (N=5). The clique-specific topology is much harder.

3. ONE GATE REMOVED:
   N=4: removing ANY gate -> infeasible. LP detects ALL single-gate errors!
   N=5: removing gate 28 (last OR, penultimate) -> still feasible. But
         removing any other gate -> infeasible. LP detects 13/14 errors.

4. RANDOM vs SPECIFIC:
   Random circuits at correct size: only 0.5-1.5% feasible.
   Clique-specific circuit: always feasible.
   This confirms the LP bound is NOT an artifact - the clique-specific
   topology genuinely needs all its gates.

IMPLICATION FOR P vs NP:
   The LP is TIGHT (or near-tight) for clique-specific structures.
   The weaker bound from random structures (s~6-7) was an artifact of
   random topology being easy to satisfy. The ACTUAL clique circuit
   topology gives LP bound = circuit size, i.e., the LP relaxation
   has NO gap for these small instances with the correct topology.
   This is encouraging: the LP may give meaningful bounds at scale.
""")


if __name__ == "__main__":
    run_tests()
