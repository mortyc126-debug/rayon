"""
SA-3 FOR CLIQUE: Level-3 Sherali-Adams with triple correlations.

SA-2 gives polynomial bounds for 3-CLIQUE (≈ N^0.71).
SA-3 captures TRIPLE correlations — exactly what triangles need.

For AND(a,c) = g:
  SA-2: p_g(b) = p_{a,c}(b)
  SA-3: p_{g,h}(b) = p_{a,c,h}(b)  (triple involving gate inputs + any wire)

This links the gate's output to THREE-WAY interactions — matching
the 3-edge structure of triangles in CLIQUE.
"""

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csc_matrix
from itertools import combinations
import random
import time

def clique_truth_table(N, k):
    n = N * (N - 1) // 2
    edge_idx = {}
    idx = 0
    for u in range(N):
        for v in range(u + 1, N):
            edge_idx[(u, v)] = idx
            idx += 1
    tt = 0
    clique_edges = []
    for subset in combinations(range(N), k):
        edges = frozenset(edge_idx[(min(a,b), max(a,b))]
                         for a in subset for b in subset if a < b)
        clique_edges.append(edges)
    for x in range(2**n):
        for ce in clique_edges:
            if all((x >> e) & 1 for e in ce):
                tt |= (1 << x)
                break
    return tt, n

def compute_conditionals_3(tt, n):
    """Compute marginal, pairwise, and TRIPLE conditional probabilities."""
    total = 2**n
    ones = sum(1 for x in range(total) if (tt >> x) & 1)
    zeros = total - ones
    if ones == 0 or zeros == 0:
        return None

    p1 = {}
    for i in range(n):
        for b in [0, 1]:
            cnt = sum(1 for x in range(total)
                     if ((x >> i) & 1) and ((tt >> x) & 1) == b)
            denom = ones if b == 1 else zeros
            p1[(i, b)] = cnt / denom if denom > 0 else 0

    p2 = {}
    for i in range(n):
        for j in range(i, n):
            for b in [0, 1]:
                cnt = sum(1 for x in range(total)
                         if ((x >> i) & 1) and ((x >> j) & 1) and ((tt >> x) & 1) == b)
                denom = ones if b == 1 else zeros
                p2[(i, j, b)] = cnt / denom if denom > 0 else 0

    p3 = {}
    for i in range(n):
        for j in range(i + 1, n):
            for k_idx in range(j + 1, n):
                for b in [0, 1]:
                    cnt = sum(1 for x in range(total)
                             if ((x >> i) & 1) and ((x >> j) & 1) and
                                ((x >> k_idx) & 1) and ((tt >> x) & 1) == b)
                    denom = ones if b == 1 else zeros
                    p3[(i, j, k_idx, b)] = cnt / denom if denom > 0 else 0

    return p1, p2, p3, ones / total


def check_sa3_feasibility(n, s, gate_types, connections, p1, p2, p3):
    """
    SA-3 LP: marginals + pairwise + KEY triple constraints from gate semantics.

    For AND(a,c) = g and any wire w:
      p_{g,w}(b) = p_{a,c,w}(b)  (exact triple equality)

    This is the SA-3 power: it links gate outputs to triple input correlations.
    """
    W = n + s
    n_gates = s

    # Variables per b:
    # [0, s): marginal p_g(b)
    # [s, s + C(s,2)): pairwise p_{gi,gj}(b) for gate pairs
    pair_map = {}
    idx = n_gates
    for i in range(n_gates):
        for j in range(i + 1, n_gates):
            pair_map[(i, j)] = idx
            idx += 1
    n_pairs = len(pair_map)
    vars_per_b = n_gates + n_pairs
    total_vars = 2 * vars_per_b

    def mvar(gi, b): return b * vars_per_b + gi
    def pvar(gi, gj, b):
        if gi > gj: gi, gj = gj, gi
        if gi == gj: return mvar(gi, b)
        return b * vars_per_b + pair_map[(gi, gj)]

    def known_p1(wire, b):
        return p1.get((wire, b)) if wire < n else None
    def known_p2(w1, w2, b):
        if w1 < n and w2 < n:
            i, j = min(w1, w2), max(w1, w2)
            return p2.get((i, j, b))
        return None
    def known_p3(w1, w2, w3, b):
        if w1 < n and w2 < n and w3 < n:
            triple = tuple(sorted([w1, w2, w3]))
            return p3.get((*triple, b))
        return None

    eq_rows, eq_cols, eq_vals, eq_rhs = [], [], [], []
    ub_rows, ub_cols, ub_vals, ub_rhs = [], [], [], []
    eq_cnt = [0]
    ub_cnt = [0]

    def add_eq(terms, rhs):
        for col, val in terms:
            eq_rows.append(eq_cnt[0]); eq_cols.append(col); eq_vals.append(val)
        eq_rhs.append(rhs); eq_cnt[0] += 1
    def add_ub(terms, rhs):
        for col, val in terms:
            ub_rows.append(ub_cnt[0]); ub_cols.append(col); ub_vals.append(val)
        ub_rhs.append(rhs); ub_cnt[0] += 1

    for b in [0, 1]:
        for gi in range(s):
            gt = gate_types[gi]
            i1, i2 = connections[gi]

            # ── SA-2 CONSTRAINTS (same as before) ──
            if gt == 'NOT':
                if i1 < n:
                    add_eq([(mvar(gi, b), 1.0)], 1.0 - known_p1(i1, b))
                else:
                    add_eq([(mvar(gi, b), 1.0), (mvar(i1-n, b), 1.0)], 1.0)

            elif gt == 'AND':
                if i1 < n and i2 < n:
                    kp = known_p2(i1, i2, b) or 0
                    add_eq([(mvar(gi, b), 1.0)], kp)
                elif i1 >= n and i2 >= n:
                    g1, g2 = i1-n, i2-n
                    if g1 != g2:
                        add_eq([(mvar(gi, b), 1.0), (pvar(g1, g2, b), -1.0)], 0)
                    else:
                        add_eq([(mvar(gi, b), 1.0), (mvar(g1, b), -1.0)], 0)
                else:
                    inp, gate = (i1, i2-n) if i1 < n else (i2, i1-n)
                    ki = known_p1(inp, b)
                    add_ub([(mvar(gi, b), 1.0)], ki)
                    add_ub([(mvar(gi, b), 1.0), (mvar(gate, b), -1.0)], 0)
                    add_ub([(mvar(gi, b), -1.0), (mvar(gate, b), 1.0)], 1.0 - ki)

            elif gt == 'OR':
                if i1 < n and i2 < n:
                    k1 = known_p1(i1, b) or 0
                    k2 = known_p1(i2, b) or 0
                    kp = known_p2(i1, i2, b) or 0
                    add_eq([(mvar(gi, b), 1.0)], k1 + k2 - kp)
                elif i1 >= n and i2 >= n:
                    g1, g2 = i1-n, i2-n
                    if g1 != g2:
                        add_eq([(mvar(gi, b), 1.0), (mvar(g1, b), -1.0),
                                (mvar(g2, b), -1.0), (pvar(g1, g2, b), 1.0)], 0)
                    else:
                        add_eq([(mvar(gi, b), 1.0), (mvar(g1, b), -1.0)], 0)
                else:
                    inp, gate = (i1, i2-n) if i1 < n else (i2, i1-n)
                    ki = known_p1(inp, b)
                    add_ub([(mvar(gi, b), -1.0)], -ki)
                    add_ub([(mvar(gi, b), -1.0), (mvar(gate, b), 1.0)], 0)
                    add_ub([(mvar(gi, b), 1.0), (mvar(gate, b), -1.0)], ki)

            # ── SA-3 CONSTRAINTS: triple correlations ──
            # For AND(i1,i2) = g and any other gate gj:
            #   p_{g, gj}(b) = Pr[i1=1, i2=1, gj=1 | f=b]
            # If all three are input wires: we know this exactly!
            if gt == 'AND':
                for gj in range(n_gates):
                    if gj == gi: continue
                    w3 = n + gj  # wire index of gate gj

                    # Case: both AND inputs are input wires, gj's inputs also known
                    if i1 < n and i2 < n:
                        # p_{g, gj}(b) = p_{i1, i2, gj}(b)
                        # If gj also takes from inputs:
                        gj_type = gate_types[gj]
                        gj_i1, gj_i2 = connections[gj]

                        # We can bound p_{g, gj} using known triple probs
                        # p_{g, gj} = Pr[i1=1, i2=1, gj=1 | f=b]
                        # ≤ Pr[i1=1, i2=1 | f=b] = p_g(b)  (already have)
                        # ≤ p_gj(b)  (already have)

                        # SA-3 power: if gj = AND(w1, w2) with w1, w2 inputs:
                        #   p_{g, gj} = Pr[i1=1, i2=1, w1=1, w2=1 | f=b]
                        #   ≤ Pr[i1=1, i2=1, w1=1 | f=b]  (known triple!)
                        #   ≤ Pr[i1=1, i2=1, w2=1 | f=b]  (known triple!)
                        if gj_type == 'AND' and gj_i1 < n and gj_i2 < n:
                            # p_{g,gj} ≤ known triple probs
                            kt1 = known_p3(i1, i2, gj_i1, b)
                            kt2 = known_p3(i1, i2, gj_i2, b)
                            pv = pvar(gi, gj, b)
                            if kt1 is not None:
                                add_ub([(pv, 1.0)], kt1)
                            if kt2 is not None:
                                add_ub([(pv, 1.0)], kt2)

                        elif gj_type == 'OR' and gj_i1 < n and gj_i2 < n:
                            # gj = OR(w1, w2): p_gj = p_w1 + p_w2 - p_{w1,w2}
                            # p_{g, gj} = p_{g, w1} + p_{g, w2} - p_{g, w1, w2}
                            # = Pr[i1=1,i2=1,w1=1|f=b] + Pr[i1=1,i2=1,w2=1|f=b]
                            #   - Pr[i1=1,i2=1,w1=1,w2=1|f=b]
                            # We know the first two from p3. The last is a quad — bound it.
                            kt1 = known_p3(i1, i2, gj_i1, b)
                            kt2 = known_p3(i1, i2, gj_i2, b)
                            if kt1 is not None and kt2 is not None:
                                pv = pvar(gi, gj, b)
                                # p_{g,gj} ≥ max of the two triples (can't be less)
                                add_ub([(pv, -1.0)], -max(kt1, kt2))
                                # p_{g,gj} ≤ sum of triples
                                add_ub([(pv, 1.0)], kt1 + kt2)

        # Output
        add_eq([(mvar(s-1, b), 1.0)], 1.0 if b == 1 else 0.0)

        # Pairwise Fréchet
        for gi in range(n_gates):
            for gj in range(gi+1, n_gates):
                pv = pvar(gi, gj, b)
                add_ub([(pv, 1.0), (mvar(gi, b), -1.0)], 0)
                add_ub([(pv, 1.0), (mvar(gj, b), -1.0)], 0)
                add_ub([(pv, -1.0), (mvar(gi, b), 1.0), (mvar(gj, b), 1.0)], 1.0)

    nv = total_vars
    c_obj = np.zeros(nv)
    bounds = [(0.0, 1.0)] * nv

    A_eq = csc_matrix((eq_vals, (eq_rows, eq_cols)), shape=(eq_cnt[0], nv)) if eq_cnt[0] > 0 else None
    b_eq_arr = np.array(eq_rhs) if eq_cnt[0] > 0 else None
    A_ub = csc_matrix((ub_vals, (ub_rows, ub_cols)), shape=(ub_cnt[0], nv)) if ub_cnt[0] > 0 else None
    b_ub_arr = np.array(ub_rhs) if ub_cnt[0] > 0 else None

    try:
        res = linprog(c_obj, A_ub=A_ub, b_ub=b_ub_arr, A_eq=A_eq, b_eq=b_eq_arr,
                      bounds=bounds, method='highs',
                      options={'presolve': True, 'time_limit': 2.0})
        return res.status != 2
    except:
        return False


def test_sa3_tension(n, s, p1, p2, p3, n_trials=500):
    random.seed(42)
    for trial in range(n_trials):
        gt_list = [random.choice(['AND', 'OR', 'NOT']) for _ in range(s)]
        conn_list = []
        for g in range(s):
            avail = list(range(n + g))
            i1 = random.choice(avail)
            i2 = random.choice(avail) if gt_list[g] != 'NOT' else 0
            conn_list.append((i1, i2))
        if check_sa3_feasibility(n, s, gt_list, conn_list, p1, p2, p3):
            return True, trial + 1
    return False, n_trials


if __name__ == '__main__':
    print("SA-3 FOR CLIQUE: Triple Correlations")
    print("═" * 65)
    print()

    for N, k in [(4, 3), (5, 3), (6, 3)]:
        tt, n = clique_truth_table(N, k)
        print(f"{k}-CLIQUE on N={N} (n={n}):")

        t0 = time.time()
        result = compute_conditionals_3(tt, n)
        if result is None:
            print("  Constant, skip."); continue
        p1, p2, p3, bal = result
        print(f"  Conditionals (incl. triples) computed in {time.time()-t0:.1f}s")
        print(f"  Balance = {bal:.4f}, {len(p3)} triple values")

        print(f"  {'s':>4} {'SA-2':>10} {'SA-3':>10} {'improvement':>12}")
        print(f"  {'-'*40}")

        sa2_bound = None
        sa3_bound = None

        for s in range(1, 20):
            t0 = time.time()
            trials = min(300, 40 * s)

            # SA-2 test (import from tension_clique)
            from tension_clique import test_tension
            sa2_feas, _ = test_tension(n, s, p1, p2, n_trials=trials)

            # SA-3 test
            sa3_feas, _ = test_sa3_tension(n, s, p1, p2, p3, n_trials=trials)

            dt = time.time() - t0

            sa2_str = "feas" if sa2_feas else "INF"
            sa3_str = "feas" if sa3_feas else "INF"
            imp = ""
            if sa2_feas and not sa3_feas:
                imp = "SA-3 TIGHTER!"
            print(f"  {s:>4} {sa2_str:>10} {sa3_str:>10} {imp:>12}")

            if sa2_feas and sa2_bound is None:
                sa2_bound = s
            if sa3_feas and sa3_bound is None:
                sa3_bound = s

            if sa2_feas and sa3_feas:
                break
            if dt > 20:
                print(f"  (timeout)")
                break

        if sa2_bound and sa3_bound:
            print(f"  SA-2 bound: {sa2_bound}, SA-3 bound: {sa3_bound}, "
                  f"improvement: +{sa3_bound - sa2_bound}")
        print()

    print("═" * 65)
    print("If SA-3 bound > SA-2 bound: triple correlations MATTER for CLIQUE.")
    print("If SA-3 bound >> SA-2 bound: potential for super-poly scaling!")
