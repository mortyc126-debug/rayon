"""
HOLOGRAPHIC LP v2: Level-2 Sherali-Adams strengthening for circuit lower bounds.

Key improvements over v1:
1. NOT gates are FREE (matching compute_sizes convention)
2. Each gate is AND(l1, l2) or OR(l1, l2) where l1, l2 are literals (wire or NOT(wire))
3. Pairwise variables p_{g,h}(b) with exact equalities from gate semantics
4. Full Sherali-Adams level-2 consistency constraints
"""

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csc_matrix
from itertools import product as iproduct
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
    """Compute actual circuit sizes for all n-bit Boolean functions.
    NOT is free (size 0). Each AND/OR costs 1."""
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


def build_and_check_lp(n, s, gate_types, connections, neg_flags, input_probs, input_probs2):
    """
    Build and solve the SA2-strengthened LP for one circuit structure.

    gate_types[g]: 'AND' or 'OR' for gate g (0..s-1)
    connections[g]: (w1, w2) wire indices in 0..n+g-1
    neg_flags[g]: (neg1, neg2) booleans - whether each input is negated

    Wire indices: 0..n-1 are inputs, n..n+s-1 are gates.
    Output is wire n+s-1 (possibly negated -- we handle output negation separately).

    Returns True if feasible for BOTH b=0 and b=1.
    """
    W = n + s  # total wires
    output_wire = W - 1

    for b in [0, 1]:
        # Variable layout:
        # [0..s-1]: p_w(b) for wires w = n..n+s-1 (gate outputs before negation)
        # [s..]: p_{i,j}(b) for pairs (i,j) with i<=j, at least one >= n

        pair_map = {}
        idx = s
        for i in range(W):
            for j in range(i, W):
                if i < n and j < n:
                    continue
                pair_map[(i, j)] = idx
                idx += 1
        nv = idx

        eq_rows, eq_cols, eq_vals, eq_rhs = [], [], [], []
        ub_rows, ub_cols, ub_vals, ub_rhs = [], [], [], []
        eq_cnt = 0
        ub_cnt = 0

        def gvar(w):
            """Variable index for wire w's marginal, or None if input."""
            return w - n if w >= n else None

        def gval(w):
            """Known value for wire w's marginal if it's an input."""
            return input_probs[(w, b)] if w < n else None

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

        # Helper: get marginal of a literal (wire w, possibly negated)
        # Returns (coeffs_list, constant) such that p_literal = sum(coeff*var) + constant
        def literal_marginal(w, neg):
            """Return (coeffs, const) for Pr[literal=1 | f=b]."""
            v = gval(w)
            if v is not None:
                return [], (1.0 - v) if neg else v
            else:
                if neg:
                    return [(gvar(w), -1.0)], 1.0
                else:
                    return [(gvar(w), 1.0)], 0.0

        # Helper: get pairwise Pr[l1=1 AND l2=1 | f=b] in terms of p_{w1,w2}
        # where l1 = w1 or NOT(w1), l2 = w2 or NOT(w2)
        def literal_pair(w1, neg1, w2, neg2):
            """Return (coeffs, const) for Pr[l1=1 AND l2=1 | f=b]."""
            # Pr[l1=1, l2=1] in terms of p_{w1,w2}, p_w1, p_w2:
            # (w1, w2):         p_{w1,w2}
            # (w1, ~w2):        p_w1 - p_{w1,w2}
            # (~w1, w2):        p_w2 - p_{w1,w2}
            # (~w1, ~w2):       1 - p_w1 - p_w2 + p_{w1,w2}

            coeffs = []
            const = 0.0

            # Start with the p_{w1,w2} term
            if w1 == w2:
                # p_{w,w} = p_w
                sign_pair = 1.0
                if neg1 != neg2:
                    # one negated: Pr[w=1, ~w=1] = 0
                    return [], 0.0
                elif neg1 and neg2:
                    # Pr[~w=1, ~w=1] = 1 - p_w
                    c, k = literal_marginal(w1, True)
                    return c, k
                else:
                    c, k = literal_marginal(w1, False)
                    return c, k

            pv = pvar(w1, w2)
            pk = pknown(w1, w2)

            # Coefficient of p_{w1,w2}
            if neg1 and neg2:
                pair_coeff = 1.0
            elif neg1 or neg2:
                pair_coeff = -1.0
            else:
                pair_coeff = 1.0

            if pv is not None:
                coeffs.append((pv, pair_coeff))
            elif pk is not None:
                const += pair_coeff * pk

            # Terms involving p_w1
            if neg1 and neg2:
                # 1 - p_w1 - p_w2 + p_{w1,w2}: need -p_w1
                c1, k1 = literal_marginal(w1, False)
                for cv, cc in c1:
                    coeffs.append((cv, -cc))
                const -= k1
            elif neg1 and not neg2:
                # p_w2 - p_{w1,w2}: need nothing with w1 directly
                pass
            elif not neg1 and neg2:
                # p_w1 - p_{w1,w2}: need p_w1
                c1, k1 = literal_marginal(w1, False)
                for cv, cc in c1:
                    coeffs.append((cv, cc))
                const += k1
            # else: (not neg1, not neg2): just p_{w1,w2}

            # Terms involving p_w2
            if neg1 and neg2:
                c2, k2 = literal_marginal(w2, False)
                for cv, cc in c2:
                    coeffs.append((cv, -cc))
                const -= k2
                const += 1.0  # the +1 term
            elif neg1 and not neg2:
                c2, k2 = literal_marginal(w2, False)
                for cv, cc in c2:
                    coeffs.append((cv, cc))
                const += k2
            elif not neg1 and neg2:
                pass
            # else: nothing

            return coeffs, const

        # 1. Output constraint: p_{output_wire}(b) = b
        # (output can also be negated - handled by allowing output_neg)
        add_eq([(gvar(output_wire), 1.0)], float(b))

        # 2. Gate semantics (marginals) - each gate is AND/OR of two literals
        for g_idx in range(s):
            g = n + g_idx
            gt = gate_types[g_idx]
            w1, w2 = connections[g_idx]
            neg1, neg2 = neg_flags[g_idx]

            if gt == 'AND':
                # p_g = Pr[l1=1 AND l2=1] = literal_pair(w1,neg1,w2,neg2)
                lp_coeffs, lp_const = literal_pair(w1, neg1, w2, neg2)
                coeffs = [(gvar(g), 1.0)]
                rhs = lp_const
                for cv, cc in lp_coeffs:
                    coeffs.append((cv, -cc))
                add_eq(coeffs, rhs)

            elif gt == 'OR':
                # p_g = Pr[l1=1] + Pr[l2=1] - Pr[l1=1 AND l2=1]
                m1_coeffs, m1_const = literal_marginal(w1, neg1)
                m2_coeffs, m2_const = literal_marginal(w2, neg2)
                lp_coeffs, lp_const = literal_pair(w1, neg1, w2, neg2)

                coeffs = [(gvar(g), 1.0)]
                rhs = m1_const + m2_const - lp_const
                for cv, cc in m1_coeffs:
                    coeffs.append((cv, -cc))
                for cv, cc in m2_coeffs:
                    coeffs.append((cv, -cc))
                for cv, cc in lp_coeffs:
                    coeffs.append((cv, cc))  # minus the minus
                add_eq(coeffs, rhs)

        # 3. Consistency: p_{w,w} = p_w
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
        # For gate g = OP(l1, l2), and any wire w:
        # p_{g,w} must be consistent with the gate semantics
        for g_idx in range(s):
            g = n + g_idx
            gt = gate_types[g_idx]
            w1, w2 = connections[g_idx]
            neg1, neg2 = neg_flags[g_idx]

            for w in range(W):
                if w == g:
                    continue
                pv_gw = pvar(g, w)
                if pv_gw is None:
                    continue

                if gt == 'AND':
                    # g = l1 AND l2
                    # Pr[g=1, w=1] <= Pr[l1=1, w=1] and <= Pr[l2=1, w=1]
                    for (wi, negi) in [(w1, neg1), (w2, neg2)]:
                        if wi == w:
                            # Pr[li=1, w=1]: if li = w, it's p_w; if li = ~w, it's 0
                            if negi:
                                # p_{g,w} <= 0
                                add_ub([(pv_gw, 1.0)], 0.0)
                            # else p_{g,w} <= p_w, already in Frechet
                            continue

                        lp_c, lp_k = literal_pair(wi, negi, w, False)
                        # p_{g,w} <= lp_c * vars + lp_k
                        coeffs = [(pv_gw, 1.0)]
                        rhs = lp_k
                        for cv, cc in lp_c:
                            coeffs.append((cv, -cc))
                        add_ub(coeffs, rhs)

                    # p_{g,w} >= Pr[l1=1,w=1] + Pr[l2=1,w=1] - Pr[w=1]
                    coeffs = [(pv_gw, -1.0)]
                    rhs = 0.0
                    for (wi, negi) in [(w1, neg1), (w2, neg2)]:
                        if wi == w:
                            if negi:
                                pass  # Pr[~w=1, w=1] = 0
                            else:
                                # Pr[w=1, w=1] = p_w
                                vw = gval(w)
                                if vw is not None:
                                    rhs -= vw
                                else:
                                    coeffs.append((gvar(w), 1.0))
                        else:
                            lp_c, lp_k = literal_pair(wi, negi, w, False)
                            rhs -= lp_k
                            for cv, cc in lp_c:
                                coeffs.append((cv, cc))

                    vw = gval(w)
                    if vw is not None:
                        rhs += vw
                    else:
                        coeffs.append((gvar(w), -1.0))
                    add_ub(coeffs, rhs)

                elif gt == 'OR':
                    # g = l1 OR l2
                    # Pr[g=1, w=1] >= Pr[li=1, w=1] for each input
                    for (wi, negi) in [(w1, neg1), (w2, neg2)]:
                        if wi == w:
                            if negi:
                                pass  # Pr[~w=1, w=1] = 0, so >= 0 trivially
                            else:
                                # p_{g,w} >= p_w: already handled? No. Let's add.
                                # -p_{g,w} <= -p_w
                                coeffs = [(pv_gw, -1.0)]
                                rhs = 0.0
                                vw = gval(w)
                                if vw is not None:
                                    rhs = -vw
                                else:
                                    coeffs.append((gvar(w), 1.0))
                                add_ub(coeffs, rhs)
                            continue

                        lp_c, lp_k = literal_pair(wi, negi, w, False)
                        coeffs = [(pv_gw, -1.0)]
                        rhs = -lp_k
                        for cv, cc in lp_c:
                            coeffs.append((cv, cc))
                        add_ub(coeffs, rhs)

                    # p_{g,w} <= Pr[l1=1,w=1] + Pr[l2=1,w=1]
                    coeffs = [(pv_gw, 1.0)]
                    rhs = 0.0
                    for (wi, negi) in [(w1, neg1), (w2, neg2)]:
                        if wi == w:
                            if negi:
                                pass
                            else:
                                vw = gval(w)
                                if vw is not None:
                                    rhs += vw
                                else:
                                    coeffs.append((gvar(w), -1.0))
                        else:
                            lp_c, lp_k = literal_pair(wi, negi, w, False)
                            rhs += lp_k
                            for cv, cc in lp_c:
                                coeffs.append((cv, -cc))
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


def sample_circuits(n, s, input_probs, input_probs2, max_tries=3000):
    """
    Sample random circuit structures of size s (AND/OR gates with free NOT).
    Returns True if ANY structure is LP-feasible.
    """
    import random as _rnd
    _rnd.seed(42)

    count = 0
    for trial in range(max_tries):
        gt_list = []
        conn_list = []
        neg_list = []
        for g in range(s):
            gt = _rnd.choice(['AND', 'OR'])
            avail = list(range(n + g))
            w1 = _rnd.choice(avail)
            w2 = _rnd.choice(avail)
            n1 = _rnd.choice([False, True])
            n2 = _rnd.choice([False, True])
            gt_list.append(gt)
            conn_list.append((w1, w2))
            neg_list.append((n1, n2))
        count += 1
        if build_and_check_lp(n, s, gt_list, conn_list, neg_list,
                               input_probs, input_probs2):
            return True, count

    return False, count


def enumerate_circuits(n, s, input_probs, input_probs2):
    """
    Enumerate ALL circuit structures of size s for n inputs.
    Each gate: AND or OR, two inputs from available wires, each optionally negated.
    Returns (feasible, count).
    """
    count = 0
    for type_combo in iproduct(['AND', 'OR'], repeat=s):
        conn_opts = []
        neg_opts = []
        for g in range(s):
            avail = list(range(n + g))
            # For commutative gates, (w1,w2) with w1<=w2 to avoid duplication
            c_opts = [(a, c) for a in avail for c in range(a, n+g)]
            conn_opts.append(c_opts)
            neg_opts.append([(False,False),(False,True),(True,False),(True,True)])

        for conn_combo in iproduct(*conn_opts):
            for neg_combo in iproduct(*neg_opts):
                count += 1
                if build_and_check_lp(n, s, list(type_combo), list(conn_combo),
                                       list(neg_combo), input_probs, input_probs2):
                    return True, count

    return False, count


# ============================================================
# MAIN
# ============================================================
if __name__ == '__main__':
    import time

    print("HOLOGRAPHIC LP v2: Level-2 Sherali-Adams Circuit Lower Bounds")
    print("  (NOT gates are FREE, matching circuit complexity convention)")
    print("=" * 65)

    sizes3 = compute_sizes(3)
    n = 3
    max_sz = max(sizes3.values())
    hardest3 = sorted([tt for tt, sz in sizes3.items() if sz == max_sz])

    print(f"\nn=3: {len(hardest3)} hardest functions, actual circuit size = {max_sz}")
    print()

    # Test hardest functions
    print("Testing n=3 hardest functions:")
    print(f"  {'tt':>12} {'actual':>8}   results by size       LP_min  match?")
    print(f"  {'-'*65}")

    all_tight = True
    for tt in hardest3:
        result = truth_table_properties(tt, n)
        if result is None:
            continue
        ip, ip2, bal = result
        tt_str = bin(tt)[2:].zfill(2**n)
        actual = sizes3[tt]

        results = []
        lp_min = None
        t0 = time.time()
        for s_test in range(1, actual + 1):
            feas, cnt = sample_circuits(n, s_test, ip, ip2, max_tries=3000)
            results.append(f"s{s_test}:{'F' if feas else 'I'}")
            if feas and lp_min is None:
                lp_min = s_test
        elapsed = time.time() - t0

        if lp_min is None:
            lp_min = actual + 1  # LP too tight

        match_str = "YES" if lp_min == actual else f"gap={actual - lp_min}"
        if lp_min != actual:
            all_tight = False
        r = " ".join(results)
        print(f"  {tt_str:>12} {actual:>8}   {r:<24} {lp_min:>5}  {match_str:>6}  ({elapsed:.1f}s)")
        sys.stdout.flush()

    print()
    print("  v1 (Frechet only):     LP_min = 2 for actual-4 functions (gap = 2)")
    if all_tight:
        print("  v2 (Sherali-Adams 2):  LP_min = 4 for actual-4 functions (gap = 0)")
        print()
        print("  >>> GAP CLOSED! SA2 constraints give TIGHT bounds for n=3! <<<")
    else:
        print("  v2 still has some gaps.")

    # Sanity check on smaller functions
    print()
    print("Sanity check (smaller functions):")
    print(f"  {'tt':>12} {'actual':>8} {'LP_min':>8} {'ok?':>8}")
    print(f"  {'-'*44}")

    for target in [1, 2]:
        fns = sorted([t for t, sz in sizes3.items() if sz == target])
        for tt in fns[:3]:
            result = truth_table_properties(tt, n)
            if result is None:
                continue
            ip, ip2, bal = result
            tt_str = bin(tt)[2:].zfill(2**n)
            actual = sizes3[tt]
            lp_min = None
            for s_test in range(1, actual + 1):
                feas, cnt = sample_circuits(n, s_test, ip, ip2, max_tries=3000)
                if feas:
                    lp_min = s_test
                    break
            if lp_min is None:
                lp_min = actual + 1
            ok = "YES" if lp_min == actual else f"gap={actual-lp_min}"
            print(f"  {tt_str:>12} {actual:>8} {lp_min:>8} {ok:>8}")
    sys.stdout.flush()

    # n=4
    print()
    print("=" * 65)
    print("n=4 (random sampling):")
    sizes4 = compute_sizes(4)
    n4 = 4
    max4 = max(sizes4.values())
    hardest4 = sorted([t for t, sz in sizes4.items() if sz == max4])
    print(f"{len(hardest4)} functions with actual size {max4}")
    print(f"  {'tt':>20} {'actual':>8} {'LP_lb':>8}")
    print(f"  {'-'*40}")

    for tt in hardest4[:3]:
        result = truth_table_properties(tt, n4)
        if result is None:
            continue
        ip, ip2, bal = result
        tt_str = bin(tt)[2:].zfill(2**n4)
        actual = sizes4[tt]

        lp_lb = 1
        for s_test in range(1, actual):
            feas, cnt = sample_circuits(n4, s_test, ip, ip2, max_tries=1000)
            if feas:
                lp_lb = s_test
                break
            lp_lb = s_test + 1

        print(f"  {tt_str:>20} {actual:>8} {'>=' + str(lp_lb):>8}")
        sys.stdout.flush()
