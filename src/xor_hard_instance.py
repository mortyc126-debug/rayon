"""
XOR-BASED HARD INSTANCES: Designed to defeat constant propagation.

XOR(a,b) never becomes constant when fixing one input:
  a=0: XOR = b (still depends on b)
  a=1: XOR = ¬b (still depends on b)

So: a circuit made entirely of XOR gates has ZERO constant propagation.
Every variable is "relevant" → no pruning → states ≈ 2^n → c = 1.

If c = 1 for XOR circuits: Williams doesn't work.
But: is XOR-SAT actually hard? No — Gaussian elimination solves it in poly!

The REAL question: can we build a HARD (NP-complete) instance that
ALSO defeats constant propagation?

Strategy: mix XOR with AND/OR to get NP-completeness while
maintaining resistance to propagation.

RANDOM k-XOR-SAT: random XOR constraints. Solvable in poly (Gauss).
Mixed XOR+clause: XOR + standard 3-SAT clauses. NP-hard AND
potentially resistant to propagation.
"""

import itertools
from collections import defaultdict
import random
import math
import sys


def simplify_circuit(gates, n, fixed_vars):
    wire_val = dict(fixed_vars)
    sig = []
    for gtype, inp1, inp2, out in gates:
        v1 = wire_val.get(inp1)
        v2 = wire_val.get(inp2) if inp2 >= 0 else None
        if gtype == 'AND':
            if v1 == 0 or v2 == 0: wire_val[out] = 0; sig.append(0)
            elif v1 == 1 and v2 == 1: wire_val[out] = 1; sig.append(1)
            elif v1 == 1: wire_val[out] = v2; sig.append(2)
            elif v2 == 1: wire_val[out] = v1; sig.append(3)
            else: sig.append(4)
        elif gtype == 'OR':
            if v1 == 1 or v2 == 1: wire_val[out] = 1; sig.append(5)
            elif v1 == 0 and v2 == 0: wire_val[out] = 0; sig.append(6)
            elif v1 == 0: wire_val[out] = v2; sig.append(7)
            elif v2 == 0: wire_val[out] = v1; sig.append(8)
            else: sig.append(9)
        elif gtype == 'NOT':
            if v1 == 0: wire_val[out] = 1; sig.append(10)
            elif v1 == 1: wire_val[out] = 0; sig.append(11)
            else: sig.append(12)
    return tuple(sig), wire_val.get(gates[-1][3]) if gates else None


def memoized_sat(gates, n, fixed_vars=None, memo=None):
    if fixed_vars is None: fixed_vars = {}
    if memo is None: memo = {}
    sig, out = simplify_circuit(gates, n, fixed_vars)
    if sig in memo: return memo[sig], len(memo)
    if out == 1: memo[sig] = True; return True, len(memo)
    if out == 0: memo[sig] = False; return False, len(memo)
    unfixed = [i for i in range(n) if i not in fixed_vars]
    if not unfixed: memo[sig] = False; return False, len(memo)
    var = unfixed[0]
    fixed_vars[var] = 1
    r1, _ = memoized_sat(gates, n, fixed_vars, memo)
    if r1: del fixed_vars[var]; memo[sig] = True; return True, len(memo)
    fixed_vars[var] = 0
    r0, _ = memoized_sat(gates, n, fixed_vars, memo)
    del fixed_vars[var]; memo[sig] = r0; return r0, len(memo)


def build_xor_gate(nid, a, b):
    """Build XOR(a,b) using AND/OR/NOT. Returns (gates, output, new_nid)."""
    gates = []
    # XOR = (a OR b) AND NOT(a AND b)
    ab = nid; gates.append(('AND', a, b, ab)); nid += 1
    nab = nid; gates.append(('NOT', ab, -1, nab)); nid += 1
    aob = nid; gates.append(('OR', a, b, aob)); nid += 1
    xor_out = nid; gates.append(('AND', aob, nab, xor_out)); nid += 1
    return gates, xor_out, nid


def build_pure_xor_circuit(n, constraints):
    """Build circuit for XOR-SAT: system of XOR constraints.
    Each constraint: (vars, parity) = XOR of vars = parity.
    """
    all_gates = []
    nid = n
    c_outs = []

    for variables, parity in constraints:
        # XOR of all variables in the constraint
        if len(variables) == 0:
            continue
        cur = variables[0]
        for v in variables[1:]:
            new_gates, out, nid = build_xor_gate(nid, cur, v)
            all_gates.extend(new_gates)
            cur = out

        # Check parity
        if parity == 0:
            # Need XOR = 0, so NOT(cur) should be 1... actually need cur = 0
            # Encode: NOT(cur) as the "satisfied" signal
            not_cur = nid; all_gates.append(('NOT', cur, -1, not_cur)); nid += 1
            c_outs.append(not_cur)
        else:
            c_outs.append(cur)

    # AND all constraints
    if not c_outs:
        return all_gates, -1
    cur = c_outs[0]
    for ci in c_outs[1:]:
        g = nid; all_gates.append(('AND', cur, ci, g)); nid += 1; cur = g

    return all_gates, cur


def build_mixed_xor_clause(n, xor_constraints, sat_clauses):
    """Mixed instance: XOR constraints AND standard clauses."""
    all_gates = []
    nid = n
    neg = {}
    for i in range(n):
        neg[i] = nid; all_gates.append(('NOT', i, -1, nid)); nid += 1

    parts = []

    # XOR part
    for variables, parity in xor_constraints:
        if not variables: continue
        cur = variables[0]
        for v in variables[1:]:
            new_gates, out, nid = build_xor_gate(nid, cur, v)
            all_gates.extend(new_gates)
            cur = out
        if parity == 0:
            nc = nid; all_gates.append(('NOT', cur, -1, nc)); nid += 1
            parts.append(nc)
        else:
            parts.append(cur)

    # Clause part
    for clause in sat_clauses:
        lits = [v if p else neg[v] for v, p in clause]
        cur = lits[0]
        for l in lits[1:]:
            out = nid; all_gates.append(('OR', cur, l, out)); nid += 1; cur = out
        parts.append(cur)

    if not parts:
        return all_gates, -1
    cur = parts[0]
    for p in parts[1:]:
        g = nid; all_gates.append(('AND', cur, p, g)); nid += 1; cur = g

    return all_gates, cur


def main():
    random.seed(42)
    print("=" * 70)
    print("  XOR-BASED HARD INSTANCES: Defeating constant propagation")
    print("=" * 70)

    print(f"\n  {'Instance':<25} {'n':>4} {'s':>5} {'states':>8} "
          f"{'2^n':>8} {'c':>8} {'sat':>4}")
    print("  " + "-" * 60)

    # 1. Pure XOR-SAT (easy — poly time by Gauss, but hard for propagation?)
    for n in range(4, 16):
        if 2**n > 300000: break
        m = n  # n constraints on n variables
        constraints = []
        for _ in range(m):
            k = random.randint(2, min(3, n))
            variables = random.sample(range(n), k)
            parity = random.randint(0, 1)
            constraints.append((variables, parity))

        gates, output = build_pure_xor_circuit(n, constraints)
        if output < 0: continue
        s = len(gates)

        memo = {}
        result, _ = memoized_sat(gates, n, {}, memo)
        distinct = len(memo)
        c = math.log2(max(1, distinct)) / max(1, n)
        status = 'SAT' if result else 'UNS'
        print(f"  {'XOR-'+str(n):<25} {n:>4} {s:>5} {distinct:>8} "
              f"{2**n:>8} {c:>8.3f} {status:>4}")
        sys.stdout.flush()

    # 2. Mixed XOR + 3-SAT (NP-hard AND propagation-resistant?)
    print()
    for n in range(4, 16):
        if 2**n > 300000: break
        # XOR constraints
        xor_m = n // 2
        xor_constraints = []
        for _ in range(xor_m):
            k = random.randint(2, 3)
            variables = random.sample(range(n), k)
            parity = random.randint(0, 1)
            xor_constraints.append((variables, parity))

        # Standard 3-SAT clauses
        sat_m = 2 * n
        sat_clauses = []
        for _ in range(sat_m):
            vars_ = random.sample(range(n), 3)
            clause = [(v, random.random() > 0.5) for v in vars_]
            sat_clauses.append(clause)

        gates, output = build_mixed_xor_clause(n, xor_constraints, sat_clauses)
        if output < 0: continue
        s = len(gates)

        memo = {}
        result, _ = memoized_sat(gates, n, {}, memo)
        distinct = len(memo)
        c = math.log2(max(1, distinct)) / max(1, n)
        status = 'SAT' if result else 'UNS'
        print(f"  {'MIXED-'+str(n):<25} {n:>4} {s:>5} {distinct:>8} "
              f"{2**n:>8} {c:>8.3f} {status:>4}")
        sys.stdout.flush()

    # 3. ALL-XOR UNSAT (guaranteed unsatisfiable by parity)
    print()
    for n in range(4, 16):
        if 2**n > 300000: break
        # Create inconsistent XOR system
        constraints = []
        # x₁ ⊕ x₂ = 0, x₂ ⊕ x₃ = 0, ..., x_{n-1} ⊕ x_n = 0, x₁ ⊕ x_n = 1
        for i in range(n-1):
            constraints.append(([i, i+1], 0))
        constraints.append(([0, n-1], 1))  # inconsistent!

        gates, output = build_pure_xor_circuit(n, constraints)
        if output < 0: continue
        s = len(gates)

        memo = {}
        result, _ = memoized_sat(gates, n, {}, memo)
        distinct = len(memo)
        c = math.log2(max(1, distinct)) / max(1, n)
        status = 'SAT' if result else 'UNS'
        print(f"  {'XOR-UNSAT-'+str(n):<25} {n:>4} {s:>5} {distinct:>8} "
              f"{2**n:>8} {c:>8.3f} {status:>4}")
        sys.stdout.flush()

    print(f"\n{'='*70}")
    print("  VERDICT")
    print(f"{'='*70}")
    print("""
    If XOR instances show c ≈ 1: constant propagation FAILS for XOR.
    This means c < 1 is NOT universal → Williams doesn't apply.

    If XOR instances show c < 1: even XOR can be pruned somehow.
    Surprising but would strengthen the Williams argument.
    """)


if __name__ == "__main__":
    main()
