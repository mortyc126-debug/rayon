"""
ADAPTIVE MEMOIZED SAT: Choose variable ordering to MAXIMIZE cache hits.

Previous: fixed ordering → 0 hits. But maybe SMART ordering creates hits.

Two states are "same" if the gate signatures match.
Gate signature depends on WHICH variables are fixed and to WHAT values.

For two different restriction paths to reach the same state:
  Different subsets of variables fixed, but same gate effects.

This happens when: variable x_i is "irrelevant" in context ρ
  (fixing x_i doesn't change any gate's status).

If x_i is irrelevant in BOTH branches: the two branches have
the same state → cache hit!

STRATEGY: Fix IRRELEVANT variables first (they don't change state).
Then: the remaining "relevant" variables create the actual branching.
Number of relevant variables = effective dimension of the problem.

If effective dimension = O(log n): total states = 2^{O(log n)} = poly(n).
If effective dimension = O(n): total states = 2^n. No help.

EXPERIMENT: Measure effective dimension for various functions.
"""

import itertools
from collections import defaultdict
import random
import math
import sys


def simplify_circuit(gates, n, fixed_vars):
    """Return gate signature (canonical state) after fixing variables."""
    wire_val = dict(fixed_vars)
    sig = []

    for gtype, inp1, inp2, out in gates:
        v1 = wire_val.get(inp1)
        v2 = wire_val.get(inp2) if inp2 >= 0 else None

        if gtype == 'AND':
            if v1 == 0 or v2 == 0:
                wire_val[out] = 0; sig.append(0)
            elif v1 == 1 and v2 == 1:
                wire_val[out] = 1; sig.append(1)
            elif v1 == 1:
                wire_val[out] = v2; sig.append(2)  # pass-through
            elif v2 == 1:
                wire_val[out] = v1; sig.append(3)
            else:
                sig.append(4)  # active
        elif gtype == 'OR':
            if v1 == 1 or v2 == 1:
                wire_val[out] = 1; sig.append(5)
            elif v1 == 0 and v2 == 0:
                wire_val[out] = 0; sig.append(6)
            elif v1 == 0:
                wire_val[out] = v2; sig.append(7)
            elif v2 == 0:
                wire_val[out] = v1; sig.append(8)
            else:
                sig.append(9)  # active
        elif gtype == 'NOT':
            if v1 == 0:
                wire_val[out] = 1; sig.append(10)
            elif v1 == 1:
                wire_val[out] = 0; sig.append(11)
            else:
                sig.append(12)

    return tuple(sig), wire_val.get(gates[-1][3]) if gates else None


def count_relevant_variables(gates, n, fixed_vars):
    """Count how many unfixed variables actually affect the gate signature."""
    base_sig, _ = simplify_circuit(gates, n, fixed_vars)
    unfixed = [i for i in range(n) if i not in fixed_vars]

    relevant = 0
    irrelevant_vars = []

    for var in unfixed:
        # Fix var = 0
        fixed_vars[var] = 0
        sig0, _ = simplify_circuit(gates, n, fixed_vars)
        del fixed_vars[var]

        # Fix var = 1
        fixed_vars[var] = 1
        sig1, _ = simplify_circuit(gates, n, fixed_vars)
        del fixed_vars[var]

        if sig0 == sig1:
            irrelevant_vars.append(var)  # Variable doesn't change state!
        else:
            relevant += 1

    return relevant, irrelevant_vars


def adaptive_sat(gates, n, fixed_vars=None, memo=None, depth=0):
    """SAT with adaptive variable ordering: fix irrelevant vars first."""
    if fixed_vars is None:
        fixed_vars = {}
    if memo is None:
        memo = {}

    sig, output_val = simplify_circuit(gates, n, fixed_vars)

    if sig in memo:
        return memo[sig], len(memo), 1

    if output_val == 1:
        memo[sig] = True
        return True, len(memo), 0
    elif output_val == 0:
        memo[sig] = False
        return False, len(memo), 0

    unfixed = [i for i in range(n) if i not in fixed_vars]
    if not unfixed:
        memo[sig] = (output_val == 1) if output_val is not None else False
        return memo[sig], len(memo), 0

    # Find irrelevant variables (fix them for free)
    _, irrelevant = count_relevant_variables(gates, n, fixed_vars)

    # Fix irrelevant variables to 0 (arbitrary — doesn't matter)
    for var in irrelevant:
        fixed_vars[var] = 0

    # Recheck after fixing irrelevant
    sig2, output_val2 = simplify_circuit(gates, n, fixed_vars)
    if sig2 in memo:
        for var in irrelevant:
            del fixed_vars[var]
        return memo[sig2], len(memo), 1

    if output_val2 is not None:
        memo[sig2] = (output_val2 == 1)
        for var in irrelevant:
            del fixed_vars[var]
        return memo[sig2], len(memo), 0

    # Branch on first RELEVANT variable
    remaining = [i for i in range(n) if i not in fixed_vars]
    if not remaining:
        memo[sig2] = False
        for var in irrelevant:
            del fixed_vars[var]
        return False, len(memo), 0

    var = remaining[0]

    total_hits = 0

    fixed_vars[var] = 1
    r1, _, h1 = adaptive_sat(gates, n, fixed_vars, memo, depth + 1)
    total_hits += h1

    if r1:
        del fixed_vars[var]
        for v in irrelevant:
            if v in fixed_vars:
                del fixed_vars[v]
        memo[sig] = True
        return True, len(memo), total_hits

    fixed_vars[var] = 0
    r0, _, h0 = adaptive_sat(gates, n, fixed_vars, memo, depth + 1)
    total_hits += h0

    del fixed_vars[var]
    for v in irrelevant:
        if v in fixed_vars:
            del fixed_vars[v]

    memo[sig] = r0
    return r0, len(memo), total_hits


def build_3sat_circuit(n, clauses):
    """Build circuit for general 3-SAT."""
    gates = []; nid = n
    neg = {}
    for i in range(n):
        neg[i] = nid; gates.append(('NOT', i, -1, nid)); nid += 1

    c_outs = []
    for clause in clauses:
        lits = []
        for var, pos in clause:
            lits.append(var if pos else neg[var])
        a = nid; gates.append(('OR', lits[0], lits[1], a)); nid += 1
        b = nid; gates.append(('OR', a, lits[2], b)); nid += 1
        c_outs.append(b)

    if not c_outs:
        return gates, -1
    cur = c_outs[0]
    for ci in c_outs[1:]:
        g = nid; gates.append(('AND', cur, ci, g)); nid += 1; cur = g
    return gates, cur


def main():
    random.seed(42)
    print("=" * 70)
    print("  ADAPTIVE MEMOIZED SAT")
    print("  Fix irrelevant variables first, then branch on relevant")
    print("=" * 70)

    print(f"\n  {'Instance':<18} {'n':>4} {'m':>4} {'s':>5} {'states':>8} "
          f"{'hits':>6} {'relevant':>9} {'rel/n':>6} {'sat':>4}")
    print("  " + "-" * 70)

    for n in range(4, 14):
        if 2**n > 500000:
            break

        for alpha in [3.0, 4.5, 6.0]:
            m = int(alpha * n)
            clauses = []
            for _ in range(m):
                vars_ = random.sample(range(n), 3)
                clause = [(v, random.random() > 0.5) for v in vars_]
                clauses.append(clause)

            gates, output = build_3sat_circuit(n, clauses)
            if output < 0:
                continue

            s = len(gates)

            # Measure relevant variables at root
            relevant, irrel = count_relevant_variables(gates, n, {})

            memo = {}
            result, num_states, hits = adaptive_sat(gates, n, {}, memo, 0)

            status = 'SAT' if result else 'UNS'
            print(f"  {'3SAT-'+str(n)+'-a'+str(alpha):<18} {n:>4} {m:>4} {s:>5} "
                  f"{num_states:>8} {hits:>6} {relevant:>9} "
                  f"{relevant/n:>6.2f} {status:>4}")

        sys.stdout.flush()

    print(f"\n{'='*70}")
    print("  ANALYSIS")
    print(f"{'='*70}")
    print("""
    relevant/n = fraction of variables that actually affect gate signatures.

    If relevant/n → 0 as n → ∞: effective dimension shrinks → poly states.
    If relevant/n → const: effective dimension = Θ(n) → exp states.

    For P = NP: need relevant = O(log n) → poly(n) total states.
    For P ≠ NP: relevant = Θ(n) → 2^n states → exponential.
    """)


if __name__ == "__main__":
    main()
