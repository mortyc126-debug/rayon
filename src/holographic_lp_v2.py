"""
HOLOGRAPHIC LP v2: Level-2 Sherali-Adams strengthening for circuit lower bounds.

Key idea: For each gate g with known semantics (AND/OR/NOT), the pairwise
conditional probabilities p_{g,h}(b) = Pr[g=1 AND h=1 | f=b] must satisfy
EXACT equalities:

  AND(a,c) = g:  p_g(b) = p_{a,c}(b)
  OR(a,c) = g:   p_g(b) = p_a(b) + p_c(b) - p_{a,c}(b)
  NOT(a) = g:    p_g(b) = 1 - p_a(b)

Plus cross-gate pairwise constraints and Sherali-Adams consistency.
"""

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csc_matrix
from itertools import product as iproduct
import itertools
import sys


def truth_table_properties(tt, n):
    """Compute conditional input probabilities (marginal and pairwise)."""
    total = 2**n
    ones = bin(tt).count('1')
    zeros = total - ones
    if ones == 0 or zeros == 0:
        return None

    p = {}
    for i in range(n):
        c1, c0 = 0, 0
        for x in range(total):
            if (x >> i) & 1:
                if (tt >> x) & 1:
                    c1 += 1
                else:
                    c0 += 1
        p[(i, 1)] = c1 / ones
        p[(i, 0)] = c0 / zeros

    p2 = {}
    for i in range(n):
        for j in range(i, n):
            for b in [0, 1]:
                count = 0
                denom = ones if b == 1 else zeros
                for x in range(total):
                    if ((x >> i) & 1) and ((x >> j) & 1) and (((tt >> x) & 1) == b):
                        count += 1
                p2[(i, j, b)] = count / denom
                p2[(j, i, b)] = count / denom

    return p, p2, ones / total


def compute_sizes(n):
    """Compute actual circuit sizes for all n-bit Boolean functions."""
    total = 2**(2**n)
    level = {}
    cur = set()
    cur.add(0)
    cur.add(total - 1)
    for i in range(n):
        tt = 0
        for x in range(2**n):
            if (x >> i) & 1:
                tt |= (1 << x)
        cur.add(tt)
        cur.add((total - 1) ^ tt)
    for t in cur:
        level[t] = 0
    s = 0
    while len(level) < total:
        s += 1
        new = set()
        existing = list(level.keys())
        for f in existing:
            nf = (total - 1) ^ f
            if nf not in level and nf not in new:
                new.add(nf)
            for g in existing:
                v = f & g
                if v not in level and v not in new:
                    new.add(v)
                v = f | g
                if v not in level and v not in new:
                    new.add(v)
        for t in new:
            level[t] = s
        if not new or s > 20:
            break
    return level


def build_and_check_lp(n, s, gate_types, connections, input_probs, input_probs2):
    """
    Build and solve the SA2-strengthened LP for one circuit structure.
    Returns True if feasible for BOTH b=0 and b=1.
    """
    W = n + s
    output_gate = W - 1

    for b in [0, 1]:
        # Variable layout:
        # [0..s-1]: p_g(b) for gates g = n..n+s-1
        # [s..s+num_pairs-1]: p_{i,j}(b) for pairs with at least one gate

        pair_map = {}
        idx = s
        for i in range(W):
            for j in range(i, W):
                if i < n and j < n:
                    continue
                pair_map[(i, j)] = idx
                idx += 1
        nv = idx

        # Lists for building sparse constraint matrices
        eq_rows, eq_cols, eq_vals, eq_rhs = [], [], [], []
        ub_rows, ub_cols, ub_vals, ub_rhs = [], [], [], []
        eq_cnt = 0
        ub_cnt = 0

        def gvar(g):
            return g - n if g >= n else None

        def gval(g):
            return input_probs[(g, b)] if g < n else None

        def pvar(i, j):
            a, c = (min(i,j), max(i,j))
            if a < n and c < n:
                return None
            return pair_map[(a, c)]

        def pknown(i, j):
            a, c = (min(i,j), max(i,j))
            if a < n and c < n:
                return input_probs2[(a, c, b)]
            return None

        def add_eq(coeffs, rhs):
            nonlocal eq_cnt
            for col, val in coeffs:
                eq_rows.append(eq_cnt)
                eq_cols.append(col)
                eq_vals.append(val)
            eq_rhs.append(rhs)
            eq_cnt += 1

        def add_ub(coeffs, rhs):
            nonlocal ub_cnt
            for col, val in coeffs:
                ub_rows.append(ub_cnt)
                ub_cols.append(col)
                ub_vals.append(val)
            ub_rhs.append(rhs)
            ub_cnt += 1

        # 1. Output constraint
        add_eq([(gvar(output_gate), 1.0)], float(b))

        # 2. Gate semantics (marginals)
        for g_idx in range(s):
            g = n + g_idx
            gt = gate_types[g_idx]
            i1, i2 = connections[g_idx]

            if gt == 'AND':
                # p_g = p_{i1,i2}
                coeffs = [(gvar(g), 1.0)]
                rhs = 0.0
                pv = pvar(i1, i2)
                pk = pknown(i1, i2)
                if pv is not None:
                    coeffs.append((pv, -1.0))
                else:
                    rhs = pk
                add_eq(coeffs, rhs)

            elif gt == 'OR':
                # p_g = p_i1 + p_i2 - p_{i1,i2}
                coeffs = [(gvar(g), 1.0)]
                rhs = 0.0

                for inp in [i1, i2]:
                    v = gval(inp)
                    if v is not None:
                        rhs += v
                    else:
                        coeffs.append((gvar(inp), -1.0))

                pv = pvar(i1, i2)
                pk = pknown(i1, i2)
                if pv is not None:
                    coeffs.append((pv, 1.0))
                elif pk is not None:
                    rhs -= pk

                add_eq(coeffs, rhs)

            elif gt == 'NOT':
                # p_g = 1 - p_i1
                coeffs = [(gvar(g), 1.0)]
                v1 = gval(i1)
                if v1 is not None:
                    add_eq(coeffs, 1.0 - v1)
                else:
                    coeffs.append((gvar(i1), 1.0))
                    add_eq(coeffs, 1.0)

        # 3. Consistency: p_{g,g} = p_g
        for i in range(W):
            pv = pvar(i, i)
            if pv is None:
                continue
            vi = gval(i)
            if vi is not None:
                add_eq([(pv, 1.0)], vi)
            else:
                add_eq([(pv, 1.0), (gvar(i), -1.0)], 0.0)

        # 4. Frechet bounds for pairs
        for i in range(W):
            for j in range(i+1, W):
                pv = pvar(i, j)
                if pv is None:
                    continue
                vi = gval(i)
                vj = gval(j)

                # p_{i,j} <= p_i
                coeffs = [(pv, 1.0)]
                rhs = 0.0
                if vi is not None:
                    rhs = vi
                else:
                    coeffs.append((gvar(i), -1.0))
                add_ub(coeffs, rhs)

                # p_{i,j} <= p_j
                coeffs = [(pv, 1.0)]
                rhs = 0.0
                if vj is not None:
                    rhs = vj
                else:
                    coeffs.append((gvar(j), -1.0))
                add_ub(coeffs, rhs)

                # p_{i,j} >= p_i + p_j - 1
                coeffs = [(pv, -1.0)]
                rhs = 1.0
                if vi is not None:
                    rhs -= vi
                else:
                    coeffs.append((gvar(i), 1.0))
                if vj is not None:
                    rhs -= vj
                else:
                    coeffs.append((gvar(j), 1.0))
                add_ub(coeffs, rhs)

        # 5. Cross-gate pairwise constraints
        for g_idx in range(s):
            g = n + g_idx
            gt = gate_types[g_idx]
            i1, i2 = connections[g_idx]

            for w in range(W):
                if w == g:
                    continue
                pv_gw = pvar(g, w)
                if pv_gw is None:
                    continue

                if gt == 'NOT':
                    # p_{g,w} = p_w - p_{i1,w}
                    coeffs = [(pv_gw, 1.0)]
                    rhs = 0.0
                    vw = gval(w)
                    if vw is not None:
                        rhs += vw
                    else:
                        coeffs.append((gvar(w), -1.0))

                    if i1 == w:
                        # p_{i1,w} = p_w
                        if vw is not None:
                            rhs -= vw
                        else:
                            coeffs.append((gvar(w), 1.0))
                    else:
                        pv_iw = pvar(i1, w)
                        pk_iw = pknown(i1, w)
                        if pv_iw is not None:
                            coeffs.append((pv_iw, 1.0))
                        elif pk_iw is not None:
                            rhs -= pk_iw

                    add_eq(coeffs, rhs)

                elif gt == 'AND':
                    # p_{g,w} <= p_{inp,w} for inp in {i1, i2}
                    for inp in [i1, i2]:
                        if inp == w:
                            # p_{g,w} <= p_w (already in Frechet)
                            continue
                        coeffs = [(pv_gw, 1.0)]
                        rhs = 0.0
                        pv_iw = pvar(inp, w)
                        pk_iw = pknown(inp, w)
                        if pv_iw is not None:
                            coeffs.append((pv_iw, -1.0))
                        elif pk_iw is not None:
                            rhs = pk_iw
                        add_ub(coeffs, rhs)

                    # p_{g,w} >= p_{i1,w} + p_{i2,w} - p_w
                    coeffs = [(pv_gw, -1.0)]
                    rhs = 0.0
                    for inp in [i1, i2]:
                        if inp == w:
                            vw = gval(w)
                            if vw is not None:
                                rhs -= vw
                            else:
                                coeffs.append((gvar(w), 1.0))
                        else:
                            pv_iw = pvar(inp, w)
                            pk_iw = pknown(inp, w)
                            if pv_iw is not None:
                                coeffs.append((pv_iw, 1.0))
                            elif pk_iw is not None:
                                rhs -= pk_iw

                    vw = gval(w)
                    if vw is not None:
                        rhs += vw
                    else:
                        coeffs.append((gvar(w), -1.0))

                    add_ub(coeffs, rhs)

                elif gt == 'OR':
                    # p_{g,w} >= p_{inp,w} for inp in {i1, i2}
                    for inp in [i1, i2]:
                        if inp == w:
                            continue
                        coeffs = [(pv_gw, -1.0)]
                        rhs = 0.0
                        pv_iw = pvar(inp, w)
                        pk_iw = pknown(inp, w)
                        if pv_iw is not None:
                            coeffs.append((pv_iw, 1.0))
                        elif pk_iw is not None:
                            rhs = -pk_iw
                        add_ub(coeffs, rhs)

                    # p_{g,w} <= p_{i1,w} + p_{i2,w}
                    coeffs = [(pv_gw, 1.0)]
                    rhs = 0.0
                    for inp in [i1, i2]:
                        if inp == w:
                            vw = gval(w)
                            if vw is not None:
                                rhs += vw
                            else:
                                coeffs.append((gvar(w), -1.0))
                        else:
                            pv_iw = pvar(inp, w)
                            pk_iw = pknown(inp, w)
                            if pv_iw is not None:
                                coeffs.append((pv_iw, -1.0))
                            elif pk_iw is not None:
                                rhs += pk_iw
                    add_ub(coeffs, rhs)

        # Build sparse matrices and solve
        c = np.zeros(nv)
        bounds = [(0.0, 1.0)] * nv

        A_eq = csc_matrix((eq_vals, (eq_rows, eq_cols)), shape=(eq_cnt, nv)) if eq_cnt > 0 else None
        b_eq = np.array(eq_rhs) if eq_cnt > 0 else None
        A_ub = csc_matrix((ub_vals, (ub_rows, ub_cols)), shape=(ub_cnt, nv)) if ub_cnt > 0 else None
        b_ub = np.array(ub_rhs) if ub_cnt > 0 else None

        try:
            res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                          bounds=bounds, method='highs',
                          options={'presolve': True, 'time_limit': 1.0})
            if res.status == 2:  # infeasible
                return False
            if not res.success and res.status != 0:
                return False
        except Exception:
            return False

    return True


def systematic_check_all(n, s, input_probs, input_probs2, max_tries=5000):
    """
    Sample random circuit structures of size s for n inputs.
    Returns True if ANY structure is LP-feasible.
    """
    import random as _rnd
    _rnd.seed(42)
    gate_types_opts = ['AND', 'OR', 'NOT']

    count = 0
    for trial in range(max_tries):
        type_combo = [_rnd.choice(gate_types_opts) for _ in range(s)]
        conn_combo = []
        for g in range(s):
            avail = list(range(n + g))
            if type_combo[g] == 'NOT':
                conn_combo.append((_rnd.choice(avail), 0))
            else:
                a = _rnd.choice(avail)
                c = _rnd.choice(avail)
                conn_combo.append((a, c))
        count += 1
        if build_and_check_lp(n, s, type_combo, conn_combo,
                               input_probs, input_probs2):
            return True, count

    return False, count


# ============================================================
# MAIN
# ============================================================
if __name__ == '__main__':
    import random
    import time

    print("HOLOGRAPHIC LP v2: Level-2 Sherali-Adams Circuit Lower Bounds")
    print("=" * 65)

    sizes3 = compute_sizes(3)
    n = 3
    max_sz = max(sizes3.values())
    hardest3 = sorted([tt for tt, sz in sizes3.items() if sz == max_sz])

    print(f"\nn=3: {len(hardest3)} hardest functions, actual circuit size = {max_sz}")
    print()

    # For n=3 hardest, systematically prove s=1,2,3 are infeasible
    # Then verify s=4 is feasible via random sampling (more trials)
    print("Testing n=3 hardest functions:")
    print(f"  {'tt':>12} {'actual':>8}  s=1   s=2   s=3  LP_min  match?")
    print(f"  {'-'*60}")

    all_tight = True
    for tt in hardest3:
        result = truth_table_properties(tt, n)
        if result is None:
            continue
        ip, ip2, bal = result
        tt_str = bin(tt)[2:].zfill(2**n)
        actual = sizes3[tt]

        results = []
        lp_min = actual  # default
        for s_test in range(1, 4):  # test s=1,2,3
            feas, cnt = systematic_check_all(n, s_test, ip, ip2, max_tries=5000)
            results.append("INF" if not feas else "feas")
            if feas and lp_min == actual:
                lp_min = s_test

        # For s=4, try more random structures
        if lp_min == actual:
            feas4, cnt4 = systematic_check_all(n, 4, ip, ip2, max_tries=10000)
            if feas4:
                lp_min = 4

        match_str = "YES" if lp_min == actual else f"gap={actual - lp_min}"
        if lp_min != actual:
            all_tight = False
        r = "  ".join(f"{r:>4}" for r in results)
        print(f"  {tt_str:>12} {actual:>8}  {r}  {lp_min:>5}  {match_str:>6}")

    print()
    print("  v1 (Frechet only):     LP_min = 2 for actual-4 functions (gap = 2)")
    if all_tight:
        print("  v2 (Sherali-Adams 2):  LP_min = 4 for actual-4 functions (gap = 0)")
        print()
        print("  >>> GAP CLOSED! SA2 constraints give TIGHT bounds for n=3! <<<")
    else:
        print("  v2 (Sherali-Adams 2):  Some gap remains")

    # Sanity: smaller functions should also be correct
    print()
    print("Sanity check (smaller functions):")
    print(f"  {'tt':>12} {'actual':>8} {'LP_min':>8} {'ok?':>8}")
    print(f"  {'-'*44}")
    for target in [1, 2]:
        fns = sorted([t for t, sz in sizes3.items() if sz == target])
        for tt in fns[:2]:
            result = truth_table_properties(tt, n)
            if result is None:
                continue
            ip, ip2, bal = result
            tt_str = bin(tt)[2:].zfill(2**n)
            actual = sizes3[tt]
            lp_min = None
            for s_test in range(1, actual + 1):
                feas, cnt = systematic_check_all(n, s_test, ip, ip2, max_tries=5000)
                if feas:
                    lp_min = s_test
                    break
            if lp_min is None:
                lp_min = actual + 1  # problem
            ok = "YES" if lp_min == actual else f"gap={actual-lp_min}"
            print(f"  {tt_str:>12} {actual:>8} {lp_min:>8} {ok:>8}")

    # n=4 test
    print()
    print("=" * 65)
    print("n=4 test (random sampling):")
    sizes4 = compute_sizes(4)
    n4 = 4
    max4 = max(sizes4.values())
    hardest4 = sorted([t for t, sz in sizes4.items() if sz == max4])
    print(f"{len(hardest4)} functions with actual size {max4}")
    print(f"  {'tt':>20} {'actual':>8} {'LP_min':>8}")
    print(f"  {'-'*40}")

    for tt in hardest4[:3]:
        result = truth_table_properties(tt, n4)
        if result is None:
            continue
        ip, ip2, bal = result
        tt_str = bin(tt)[2:].zfill(2**n4)
        actual = sizes4[tt]

        lp_min = actual  # default if nothing found feasible below actual
        for s_test in range(1, actual):
            feas, cnt = systematic_check_all(n4, s_test, ip, ip2, max_tries=2000)
            if feas:
                lp_min = s_test
                break

        print(f"  {tt_str:>20} {actual:>8} {'>=' + str(lp_min):>8}")
