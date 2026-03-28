"""
WORST CASE SAT: Test memoized SAT on DESIGNED hard instances.

Random 3-SAT: states ≈ 2^{0.65n}. But worst case might be 2^n.

Hard instances to test:
1. PIGEONHOLE PRINCIPLE (PHP): n+1 pigeons, n holes. Always UNSAT.
   Known to be hard for resolution. Exponential for DPLL.

2. TSEITIN FORMULAS: Parity constraints on a graph.
   Hard for resolution and bounded-depth Frege.

3. RANDOM XORSAT: Random XOR constraints. Hard for DPLL.

4. CRAFTED INSTANCES: Designed to defeat specific heuristics.
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


def memoized_sat_count(gates, n, fixed_vars=None, memo=None):
    if fixed_vars is None: fixed_vars = {}
    if memo is None: memo = {}

    sig, out = simplify_circuit(gates, n, fixed_vars)
    if sig in memo: return memo[sig], len(memo), True
    if out == 1: memo[sig] = True; return True, len(memo), False
    if out == 0: memo[sig] = False; return False, len(memo), False

    unfixed = [i for i in range(n) if i not in fixed_vars]
    if not unfixed:
        memo[sig] = (out == 1) if out is not None else False
        return memo[sig], len(memo), False

    var = unfixed[0]
    fixed_vars[var] = 1
    r1, _, _ = memoized_sat_count(gates, n, fixed_vars, memo)
    if r1:
        del fixed_vars[var]; memo[sig] = True; return True, len(memo), False

    fixed_vars[var] = 0
    r0, _, _ = memoized_sat_count(gates, n, fixed_vars, memo)
    del fixed_vars[var]
    memo[sig] = r0
    return r0, len(memo), False


def build_circuit_from_clauses(n, clauses):
    """Build circuit for CNF. Clause = list of (var, positive?)."""
    gates = []; nid = n
    neg = {}
    for i in range(n):
        neg[i] = nid; gates.append(('NOT', i, -1, nid)); nid += 1

    c_outs = []
    for clause in clauses:
        lits = [v if p else neg[v] for v, p in clause]
        cur = lits[0]
        for l in lits[1:]:
            out = nid; gates.append(('OR', cur, l, out)); nid += 1; cur = out
        c_outs.append(cur)

    if not c_outs:
        return gates, -1
    cur = c_outs[0]
    for ci in c_outs[1:]:
        g = nid; gates.append(('AND', cur, ci, g)); nid += 1; cur = g
    return gates, cur


def pigeonhole_clauses(pigeons, holes):
    """PHP_{pigeons}^{holes}: UNSAT when pigeons > holes.
    Variables: x_{i,j} = pigeon i in hole j. n = pigeons × holes.

    Clauses:
    1. Each pigeon in at least one hole: OR_j x_{i,j} for each i.
    2. No two pigeons in same hole: NOT(x_{i,j} AND x_{k,j}) for i≠k.
       = (¬x_{i,j} ∨ ¬x_{k,j}).
    """
    n = pigeons * holes
    clauses = []

    def var(i, j):
        return i * holes + j

    # Pigeon axioms: each pigeon somewhere
    for i in range(pigeons):
        clause = [(var(i, j), True) for j in range(holes)]
        clauses.append(clause)

    # Hole axioms: no two pigeons per hole
    for j in range(holes):
        for i1 in range(pigeons):
            for i2 in range(i1 + 1, pigeons):
                clauses.append([(var(i1, j), False), (var(i2, j), False)])

    return n, clauses


def tseitin_clauses(n_vertices):
    """Tseitin formula on a path graph with random parity.
    Variables: one per edge. Constraint: XOR of edges at each
    internal vertex = random bit.

    For ODD total parity: UNSAT.
    """
    # Path graph: vertices 0,...,n_vertices-1, edges (i,i+1)
    n_edges = n_vertices - 1
    n = n_edges  # variables = edges

    clauses = []

    # For each internal vertex v (1,...,n_vertices-2):
    # x_{v-1,v} XOR x_{v,v+1} = b_v (random bit)
    # XOR(a,b) = c encoded as:
    #   (a ∨ b ∨ ¬c), (a ∨ ¬b ∨ c), (¬a ∨ b ∨ c), (¬a ∨ ¬b ∨ ¬c)
    # For c = 1 (odd): (a ∨ b ∨ 0)...

    # Simpler: parity constraint at each vertex
    # For path graph: make total parity odd → UNSAT

    parities = [random.randint(0, 1) for _ in range(n_vertices)]
    # Force total parity to be odd (UNSAT)
    if sum(parities) % 2 == 0:
        parities[0] ^= 1

    for v in range(n_vertices):
        # Edges incident to v
        edges = []
        if v > 0:
            edges.append(v - 1)  # edge (v-1, v)
        if v < n_vertices - 1:
            edges.append(v)  # edge (v, v+1)

        if len(edges) == 1:
            e = edges[0]
            if parities[v] == 1:
                clauses.append([(e, True)])  # x_e = 1
            else:
                clauses.append([(e, False)])  # x_e = 0
        elif len(edges) == 2:
            e1, e2 = edges
            b = parities[v]
            if b == 0:
                # x1 XOR x2 = 0: x1 = x2
                clauses.append([(e1, True), (e2, True)])    # ¬x1 → x2
                clauses.append([(e1, False), (e2, False)])  # x1 → ¬x2... wait
                # XOR=0: (x1∨¬x2) ∧ (¬x1∨x2)
                clauses.append([(e1, True), (e2, False)])
                clauses.append([(e1, False), (e2, True)])
            else:
                # XOR=1: (x1∨x2) ∧ (¬x1∨¬x2)
                clauses.append([(e1, True), (e2, True)])
                clauses.append([(e1, False), (e2, False)])

    return n, clauses


def main():
    random.seed(42)
    print("=" * 70)
    print("  WORST CASE SAT: Designed hard instances")
    print("  PHP, Tseitin, Random XOR")
    print("=" * 70)

    print(f"\n  {'Instance':<25} {'n':>4} {'m':>5} {'s':>5} "
          f"{'states':>8} {'2^n':>8} {'c=log/n':>8} {'sat':>4}")
    print("  " + "-" * 70)

    # PIGEONHOLE PRINCIPLE
    for p in range(3, 10):
        h = p - 1  # p pigeons, p-1 holes → UNSAT
        n, clauses = pigeonhole_clauses(p, h)

        if n > 18:
            break

        gates, output = build_circuit_from_clauses(n, clauses)
        if output < 0:
            continue

        s = len(gates)
        memo = {}
        result, num_states, _ = memoized_sat_count(gates, n, {}, memo)
        distinct = len(memo)

        c = math.log2(max(1, distinct)) / max(1, n)
        status = 'SAT' if result else 'UNS'
        print(f"  {'PHP-'+str(p)+'-'+str(h):<25} {n:>4} {len(clauses):>5} "
              f"{s:>5} {distinct:>8} {2**n:>8} {c:>8.3f} {status:>4}")
        sys.stdout.flush()

    # TSEITIN FORMULAS
    for nv in range(4, 20):
        n, clauses = tseitin_clauses(nv)

        if n > 18:
            break

        gates, output = build_circuit_from_clauses(n, clauses)
        if output < 0:
            continue

        s = len(gates)
        memo = {}
        result, num_states, _ = memoized_sat_count(gates, n, {}, memo)
        distinct = len(memo)

        c = math.log2(max(1, distinct)) / max(1, n)
        status = 'SAT' if result else 'UNS'
        print(f"  {'Tseitin-'+str(nv):<25} {n:>4} {len(clauses):>5} "
              f"{s:>5} {distinct:>8} {2**n:>8} {c:>8.3f} {status:>4}")
        sys.stdout.flush()

    # RANDOM 3-SAT at phase transition (α ≈ 4.27)
    for n in range(4, 19):
        if 2**n > 500000:
            break
        alpha = 4.27
        m = int(alpha * n)
        max_states = 0

        for trial in range(10):
            clauses = []
            for _ in range(m):
                vars_ = random.sample(range(n), 3)
                clause = [(v, random.random() > 0.5) for v in vars_]
                clauses.append(clause)

            gates, output = build_circuit_from_clauses(n, clauses)
            if output < 0: continue

            memo = {}
            result, _, _ = memoized_sat_count(gates, n, {}, memo)
            max_states = max(max_states, len(memo))

        c = math.log2(max(1, max_states)) / max(1, n)
        print(f"  {'3SAT-'+str(n)+'-4.27':<25} {n:>4} {m:>5} "
              f"{'~':>5} {max_states:>8} {2**n:>8} {c:>8.3f} {'???':>4}")
        sys.stdout.flush()

    print(f"\n{'='*70}")
    print("  COMPARISON")
    print(f"{'='*70}")
    print("""
    c = log₂(states)/n measures the "hardness exponent."

    c → 0: sub-exponential states → Williams applies → NEXP ⊄ P/poly
    c → 1: exponential states → no speedup → no conclusion
    c > 1: worse than brute force (shouldn't happen)

    KEY: Do WORST-CASE instances (PHP, Tseitin) have c → 1?
    Or do they also show c < 1?

    If c < 1 even for worst case → universal speedup → Williams!
    """)


if __name__ == "__main__":
    main()
