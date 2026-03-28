"""
MEMOIZED SAT: Can we solve SAT in poly time via memoization?

Given circuit C of size s: find x with C(x) = 1.

ALGORITHM:
  1. Build decision tree by branching on variables.
  2. At each node: identify the "state" (simplified circuit).
  3. If state seen before: reuse cached result.
  4. Otherwise: recurse on both branches.

Total time: (number of distinct states) × poly(s).

THE CRITICAL QUESTION:
  For a circuit of size s, how many distinct states arise
  during variable-by-variable restriction?

STATE = the "canonical form" of the restricted circuit.
Two restrictions give same state if the remaining function is identical.

UPPER BOUND: 3^s (each gate: constant_0, constant_1, or active).
ACTUAL: much less (many combinations are impossible due to circuit structure).

EXPERIMENT: For actual circuits, count DISTINCT states during
exhaustive restriction (memoized DFS).
"""

import itertools
from collections import defaultdict
import random
import math
import sys


def circuit_evaluate(gates, inputs, n):
    """Evaluate circuit on given input."""
    wire = list(inputs) + [0] * len(gates)
    for gi, (gtype, inp1, inp2, out) in enumerate(gates):
        if gtype == 'AND':
            wire[out] = wire[inp1] & wire[inp2]
        elif gtype == 'OR':
            wire[out] = wire[inp1] | wire[inp2]
        elif gtype == 'NOT':
            wire[out] = 1 - wire[inp1]
    return wire


def simplify_circuit(gates, n, fixed_vars):
    """Simplify circuit given fixed variable assignments.

    Returns: canonical state (tuple of gate statuses).
    Gate status: 'a' (active), '0' (constant 0), '1' (constant 1).
    """
    wire_val = {}
    for var, val in fixed_vars.items():
        wire_val[var] = val

    gate_status = []
    for gi, (gtype, inp1, inp2, out) in enumerate(gates):
        v1 = wire_val.get(inp1)
        if inp2 >= 0:
            v2 = wire_val.get(inp2)
        else:
            v2 = None

        if gtype == 'AND':
            if v1 == 0 or v2 == 0:
                wire_val[out] = 0
                gate_status.append('0')
            elif v1 == 1 and v2 == 1:
                wire_val[out] = 1
                gate_status.append('1')
            elif v1 == 1:
                # out = inp2 (pass-through)
                if v2 is not None:
                    wire_val[out] = v2
                    gate_status.append(str(v2))
                else:
                    gate_status.append('p2')  # pass-through inp2
            elif v2 == 1:
                if v1 is not None:
                    wire_val[out] = v1
                    gate_status.append(str(v1))
                else:
                    gate_status.append('p1')
            else:
                gate_status.append('a')  # active

        elif gtype == 'OR':
            if v1 == 1 or v2 == 1:
                wire_val[out] = 1
                gate_status.append('1')
            elif v1 == 0 and v2 == 0:
                wire_val[out] = 0
                gate_status.append('0')
            elif v1 == 0:
                if v2 is not None:
                    wire_val[out] = v2
                    gate_status.append(str(v2))
                else:
                    gate_status.append('p2')
            elif v2 == 0:
                if v1 is not None:
                    wire_val[out] = v1
                    gate_status.append(str(v1))
                else:
                    gate_status.append('p1')
            else:
                gate_status.append('a')

        elif gtype == 'NOT':
            if v1 == 0:
                wire_val[out] = 1
                gate_status.append('1')
            elif v1 == 1:
                wire_val[out] = 0
                gate_status.append('0')
            else:
                gate_status.append('a')

    return tuple(gate_status)


def memoized_sat(gates, n, fixed_vars=None, memo=None, depth=0):
    """Solve SAT using memoized DFS on variable restrictions.

    Returns: (satisfiable, num_states_visited, memo_hits)
    """
    if fixed_vars is None:
        fixed_vars = {}
    if memo is None:
        memo = {}

    # Get canonical state
    state = simplify_circuit(gates, n, fixed_vars)

    if state in memo:
        return memo[state], 0, 1  # cached result, 0 new states, 1 hit

    # Check if output is determined
    output_status = state[-1]
    if output_status == '1':
        memo[state] = True
        return True, 1, 0
    elif output_status == '0':
        memo[state] = False
        return False, 1, 0

    # Find an unfixed variable
    unfixed = [i for i in range(n) if i not in fixed_vars]
    if not unfixed:
        # All variables fixed, evaluate
        inputs = tuple(fixed_vars.get(i, 0) for i in range(n))
        vals = circuit_evaluate(gates, inputs, n)
        result = vals[gates[-1][3]] == 1
        memo[state] = result
        return result, 1, 0

    # Branch on first unfixed variable
    var = unfixed[0]

    total_new = 1
    total_hits = 0

    # Try var = 1 first (often satisfies more clauses)
    fixed_vars[var] = 1
    r1, new1, hits1 = memoized_sat(gates, n, fixed_vars, memo, depth + 1)
    total_new += new1
    total_hits += hits1

    if r1:
        del fixed_vars[var]
        memo[state] = True
        return True, total_new, total_hits

    # Try var = 0
    fixed_vars[var] = 0
    r0, new0, hits0 = memoized_sat(gates, n, fixed_vars, memo, depth + 1)
    total_new += new0
    total_hits += hits0

    del fixed_vars[var]
    result = r0
    memo[state] = result
    return result, total_new, total_hits


def test_memoized_sat():
    """Test memoized SAT on various circuits and count distinct states."""
    print("=" * 70)
    print("  MEMOIZED SAT: Distinct states during search")
    print("  If states = poly(n) → P = NP")
    print("=" * 70)

    from mono3sat import generate_all_mono3sat_clauses

    print(f"\n  {'Function':<18} {'n':>4} {'s':>5} {'3^s':>12} "
          f"{'distinct':>10} {'hits':>8} {'ratio':>8} {'sat?':>5}")
    print("  " + "-" * 75)

    for n in range(4, 13):
        if 2**n > 100000:
            break

        # MSAT (satisfiable)
        all_cl = generate_all_mono3sat_clauses(n)
        for trial in range(2):
            num_cl = min(len(all_cl), 2*n + trial*n)
            clauses = random.sample(all_cl, num_cl)

            gates = []; nid = n; c_outs = []
            for cl in clauses:
                v0,v1,v2 = cl
                a=nid; gates.append(('OR',v0,v1,a)); nid+=1
                b=nid; gates.append(('OR',a,v2,b)); nid+=1
                c_outs.append(b)
            if not c_outs:
                continue
            cur = c_outs[0]
            for ci in c_outs[1:]:
                g=nid; gates.append(('AND',cur,ci,g)); nid+=1; cur=g

            s = len(gates)
            memo = {}
            result, new_states, hits = memoized_sat(gates, n, {}, memo, 0)
            distinct = len(memo)

            three_s = 3**min(s, 20)  # cap to avoid overflow
            ratio = distinct / (s + n)

            print(f"  {'MSAT-'+str(n)+'-t'+str(trial):<18} {n:>4} {s:>5} "
                  f"{'3^'+str(s) if s <= 20 else '>10^9':>12} "
                  f"{distinct:>10} {hits:>8} {ratio:>8.1f} "
                  f"{'Y' if result else 'N':>5}")

        sys.stdout.flush()

    # Summary
    print(f"\n{'='*70}")
    print("  SCALING ANALYSIS")
    print(f"{'='*70}")


if __name__ == "__main__":
    random.seed(42)
    test_memoized_sat()
