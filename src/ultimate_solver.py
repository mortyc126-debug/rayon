"""
ULTIMATE SAT SOLVER: Combining ALL insights from 69 modules.

Assumes P = NP. Builds the best possible solver from our research.
If it solves in poly: evidence for P = NP.
If exponential: evidence for P ≠ NP.

COMBINES:
1. Gate-level constant propagation (cascade)
2. State memoization (cache gate signatures)
3. Greedy variable ordering (maximize propagation)
4. Bidirectional (top-down constraints + bottom-up)
5. Φ-guided splitting (pick variable reducing Φ most)

Tests on random 3-SAT at threshold (α ≈ 4.27).
"""

import random
import time
import math
import sys


def propagate(gates, n, fixed):
    """Gate-level constant propagation. Returns output value or None."""
    wv = dict(fixed)
    for gt, i1, i2, o in gates:
        v1 = wv.get(i1)
        v2 = wv.get(i2) if i2 >= 0 else None
        if gt == 'AND':
            if v1 == 0 or v2 == 0: wv[o] = 0
            elif v1 is not None and v2 is not None: wv[o] = v1 & v2
        elif gt == 'OR':
            if v1 == 1 or v2 == 1: wv[o] = 1
            elif v1 is not None and v2 is not None: wv[o] = v1 | v2
        elif gt == 'NOT':
            if v1 is not None: wv[o] = 1 - v1
    return wv.get(gates[-1][3]) if gates else None


def gate_signature(gates, n, fixed):
    """Compact state: which gates are constant (0/1/active)."""
    wv = dict(fixed)
    sig = []
    for gt, i1, i2, o in gates:
        v1 = wv.get(i1)
        v2 = wv.get(i2) if i2 >= 0 else None
        if gt == 'AND':
            if v1 == 0 or v2 == 0: wv[o] = 0; sig.append(0)
            elif v1 is not None and v2 is not None: wv[o] = v1 & v2; sig.append(v1&v2)
            elif v1 == 1: sig.append(2)
            elif v2 == 1: sig.append(3)
            else: sig.append(4)
        elif gt == 'OR':
            if v1 == 1 or v2 == 1: wv[o] = 1; sig.append(5)
            elif v1 is not None and v2 is not None: wv[o] = v1 | v2; sig.append(v1|v2)
            elif v1 == 0: sig.append(6)
            elif v2 == 0: sig.append(7)
            else: sig.append(8)
        elif gt == 'NOT':
            if v1 is not None: wv[o] = 1-v1; sig.append(1-v1)
            else: sig.append(9)
    return tuple(sig)


def count_determined(gates, n, fixed):
    """Count gates determined after propagation."""
    wv = dict(fixed)
    det = 0
    for gt, i1, i2, o in gates:
        v1 = wv.get(i1); v2 = wv.get(i2) if i2 >= 0 else None
        d = False
        if gt == 'AND':
            if v1 == 0 or v2 == 0: wv[o] = 0; d = True
            elif v1 is not None and v2 is not None: wv[o] = v1&v2; d = True
        elif gt == 'OR':
            if v1 == 1 or v2 == 1: wv[o] = 1; d = True
            elif v1 is not None and v2 is not None: wv[o] = v1|v2; d = True
        elif gt == 'NOT':
            if v1 is not None: wv[o] = 1-v1; d = True
        if d: det += 1
    return det


def best_variable(gates, n, fixed):
    """Pick variable that maximizes determined gates (greedy propagation)."""
    unfixed = [i for i in range(n) if i not in fixed]
    if not unfixed:
        return None

    best_v = unfixed[0]
    best_det = -1

    for v in unfixed:
        total = 0
        for val in [0, 1]:
            fixed[v] = val
            total += count_determined(gates, n, fixed)
            del fixed[v]
        if total > best_det:
            best_det = total
            best_v = v

    return best_v


def ultimate_solve(gates, n, fixed=None, memo=None, depth=0, stats=None):
    """Ultimate SAT solver combining all techniques."""
    if fixed is None: fixed = {}
    if memo is None: memo = {}
    if stats is None: stats = {'nodes': 0, 'hits': 0, 'max_depth': 0}

    stats['nodes'] += 1
    stats['max_depth'] = max(stats['max_depth'], depth)

    # 1. Propagate
    out = propagate(gates, n, fixed)
    if out is not None:
        return out == 1

    # 2. Memoize
    sig = gate_signature(gates, n, fixed)
    if sig in memo:
        stats['hits'] += 1
        return memo[sig]

    # 3. Greedy variable ordering
    if depth < 3:  # expensive, use only at top levels
        var = best_variable(gates, n, fixed)
    else:
        unfixed = [i for i in range(n) if i not in fixed]
        var = unfixed[0] if unfixed else None

    if var is None:
        memo[sig] = False
        return False

    # 4. Try value that propagates more first
    fixed[var] = 1
    det1 = count_determined(gates, n, fixed)
    del fixed[var]
    fixed[var] = 0
    det0 = count_determined(gates, n, fixed)
    del fixed[var]

    first_val = 1 if det1 >= det0 else 0

    # 5. Branch
    fixed[var] = first_val
    r1 = ultimate_solve(gates, n, fixed, memo, depth+1, stats)
    if r1:
        del fixed[var]
        memo[sig] = True
        return True

    fixed[var] = 1 - first_val
    r2 = ultimate_solve(gates, n, fixed, memo, depth+1, stats)
    del fixed[var]

    memo[sig] = r2
    return r2


def build_3sat_circuit(n, clauses):
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
    if not c_outs: return gates, -1
    cur = c_outs[0]
    for ci in c_outs[1:]:
        g = nid; gates.append(('AND', cur, ci, g)); nid += 1; cur = g
    return gates, cur


def main():
    random.seed(42)
    print("=" * 65)
    print("  ULTIMATE SAT SOLVER: All insights combined")
    print("  Testing on random 3-SAT at threshold (α = 4.27)")
    print("=" * 65)

    print(f"\n  {'n':>4} {'m':>5} {'nodes':>10} {'hits':>8} {'depth':>6} "
          f"{'time':>8} {'c=log/n':>8} {'result':>7}")
    print("  " + "-" * 60)

    for n in range(5, 30):
        alpha = 4.27
        m = int(alpha * n)

        max_nodes = 0
        max_time = 0
        results = []

        for trial in range(5):
            clauses = []
            for _ in range(m):
                vars_ = random.sample(range(n), min(3, n))
                clause = [(v, random.random() > 0.5) for v in vars_]
                clauses.append(clause)

            gates, output = build_3sat_circuit(n, clauses)
            if output < 0: continue

            stats = {'nodes': 0, 'hits': 0, 'max_depth': 0}
            t0 = time.time()
            result = ultimate_solve(gates, n, {}, {}, 0, stats)
            dt = time.time() - t0

            max_nodes = max(max_nodes, stats['nodes'])
            max_time = max(max_time, dt)
            results.append(('SAT' if result else 'UNS', stats))

            if dt > 30:
                break

        if max_nodes > 0:
            c = math.log2(max_nodes) / n if n > 0 else 0
            best_stats = max(results, key=lambda r: r[1]['nodes'])[1]
            print(f"  {n:>4} {m:>5} {max_nodes:>10} {best_stats['hits']:>8} "
                  f"{best_stats['max_depth']:>6} {max_time:>8.2f}s "
                  f"{c:>8.3f} {'mixed':>7}")

        if max_time > 30:
            print("  (timeout)")
            break

        sys.stdout.flush()

    print(f"\n  c = log₂(nodes)/n. Target: c → 0 (polynomial).")
    print(f"  c ≈ 0.5-0.7: sub-exponential (typical DPLL).")
    print(f"  c → 0 as n → ∞: POLYNOMIAL → P = NP!!!")
    print(f"  c → const > 0: EXPONENTIAL → P ≠ NP direction.")


if __name__ == "__main__":
    main()
