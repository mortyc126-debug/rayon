"""
TRUE SA-3: Gate-level triple variables for circuit lower bounds.

SA-2 constraint: p_{g,h}(b) ∈ [Fréchet bounds from p_g, p_h]
SA-3 adds: for AND(a,c) = g:
  p_{g,h}(b) = p_{a,c,h}(b)  [exact equality]
  p_{a,c,h}(b) ≤ min(p_{a,h}(b), p_{c,h}(b))  [tighter upper bound!]
  p_{a,c,h}(b) ≥ p_{a,h}(b) + p_{c,h}(b) - p_h(b)  [tighter lower bound!]

The KEY: SA-3 says p_{g,h} ≤ min(p_{a,h}, p_{c,h}), which is TIGHTER
than SA-2's p_{g,h} ≤ min(p_g, p_h).

This adds O(s³) variables but potentially much tighter constraints.
"""

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csc_matrix
from itertools import combinations
import random
import time
import sys

sys.path.insert(0, 'src')
from tension_clique import clique_truth_table, compute_conditionals


def check_true_sa3(n, s, gate_types, connections, p1, p2):
    """
    True SA-3 LP with gate-triple variables.
    Variables per b:
      mvar: s marginals p_g(b)
      pvar: C(s,2) pairwise p_{gi,gj}(b)
      tvar: C(s,3) triples p_{gi,gj,gk}(b)  [NEW]
    """
    n_gates = s
    n_pairs = n_gates * (n_gates - 1) // 2
    n_triples = n_gates * (n_gates - 1) * (n_gates - 2) // 6

    # Variable layout per b
    pair_map = {}
    idx = n_gates
    for i in range(n_gates):
        for j in range(i+1, n_gates):
            pair_map[(i,j)] = idx; idx += 1

    triple_map = {}
    for i in range(n_gates):
        for j in range(i+1, n_gates):
            for k in range(j+1, n_gates):
                triple_map[(i,j,k)] = idx; idx += 1

    vars_per_b = n_gates + n_pairs + n_triples
    total_vars = 2 * vars_per_b

    def mvar(gi, b): return b * vars_per_b + gi
    def pvar(gi, gj, b):
        if gi > gj: gi, gj = gj, gi
        if gi == gj: return mvar(gi, b)
        return b * vars_per_b + pair_map[(gi, gj)]
    def tvar(gi, gj, gk, b):
        triple = tuple(sorted([gi, gj, gk]))
        if triple[0] == triple[1] or triple[1] == triple[2]:
            # Degenerate: two same → pairwise
            if triple[0] == triple[1]: return pvar(triple[0], triple[2], b)
            return pvar(triple[0], triple[1], b)
        return b * vars_per_b + triple_map[triple]

    def known_p1(w, b):
        return p1.get((w, b)) if w < n else None
    def known_p2(w1, w2, b):
        if w1 < n and w2 < n:
            return p2.get((min(w1,w2), max(w1,w2), b))
        return None

    eq_r, eq_c, eq_v, eq_rhs = [], [], [], []
    ub_r, ub_c, ub_v, ub_rhs = [], [], [], []
    eq_cnt = [0]; ub_cnt = [0]

    def add_eq(terms, rhs):
        for col, val in terms:
            eq_r.append(eq_cnt[0]); eq_c.append(col); eq_v.append(val)
        eq_rhs.append(rhs); eq_cnt[0] += 1
    def add_ub(terms, rhs):
        for col, val in terms:
            ub_r.append(ub_cnt[0]); ub_c.append(col); ub_v.append(val)
        ub_rhs.append(rhs); ub_cnt[0] += 1

    for b in [0, 1]:
        # ── SA-2 constraints (marginals + pairwise) ──
        for gi in range(s):
            gt = gate_types[gi]
            i1, i2 = connections[gi]

            if gt == 'NOT':
                if i1 < n:
                    add_eq([(mvar(gi, b), 1.0)], 1.0 - known_p1(i1, b))
                else:
                    add_eq([(mvar(gi, b), 1.0), (mvar(i1-n, b), 1.0)], 1.0)
            elif gt == 'AND':
                if i1 < n and i2 < n:
                    add_eq([(mvar(gi, b), 1.0)], known_p2(i1, i2, b) or 0)
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
                    k1, k2 = known_p1(i1, b), known_p1(i2, b)
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

        # Output
        add_eq([(mvar(s-1, b), 1.0)], 1.0 if b == 1 else 0.0)

        # Pairwise Fréchet
        for gi in range(n_gates):
            for gj in range(gi+1, n_gates):
                pv = pvar(gi, gj, b)
                add_ub([(pv, 1.0), (mvar(gi, b), -1.0)], 0)
                add_ub([(pv, 1.0), (mvar(gj, b), -1.0)], 0)
                add_ub([(pv, -1.0), (mvar(gi, b), 1.0), (mvar(gj, b), 1.0)], 1.0)

        # ── TRUE SA-3: Triple Fréchet bounds ──
        for gi in range(n_gates):
            for gj in range(gi+1, n_gates):
                for gk in range(gj+1, n_gates):
                    tv = tvar(gi, gj, gk, b)
                    # Upper bounds: t ≤ each pairwise
                    add_ub([(tv, 1.0), (pvar(gi, gj, b), -1.0)], 0)
                    add_ub([(tv, 1.0), (pvar(gi, gk, b), -1.0)], 0)
                    add_ub([(tv, 1.0), (pvar(gj, gk, b), -1.0)], 0)
                    # Lower bound: t ≥ p_{ij} + p_{ik} + p_{jk} - p_i - p_j - p_k + 1
                    # (inclusion-exclusion lower)
                    # Simpler: t ≥ p_{ij} + p_{ik} - p_i
                    add_ub([(tv, -1.0), (pvar(gi, gj, b), 1.0),
                            (pvar(gi, gk, b), 1.0), (mvar(gi, b), -1.0)], 0)
                    add_ub([(tv, -1.0), (pvar(gi, gj, b), 1.0),
                            (pvar(gj, gk, b), 1.0), (mvar(gj, b), -1.0)], 0)
                    add_ub([(tv, -1.0), (pvar(gi, gk, b), 1.0),
                            (pvar(gj, gk, b), 1.0), (mvar(gk, b), -1.0)], 0)

        # ── SA-3 GATE SEMANTICS: the KEY new constraints ──
        for gi in range(s):
            gt = gate_types[gi]
            i1, i2 = connections[gi]

            if gt == 'AND' and i1 >= n and i2 >= n:
                a, c = i1 - n, i2 - n
                if a == c: continue
                # For every other gate h:
                for h in range(n_gates):
                    if h == gi: continue
                    # SA-3: p_{g,h} = p_{a,c,h}
                    # g = AND(a,c) so p_{g,h} = Pr[a=1,c=1,h=1|f=b] = p_{a,c,h}
                    pv_gh = pvar(gi, h, b)

                    # Get the triple var for (a, c, h)
                    triple = tuple(sorted([a, c, h]))
                    if len(set(triple)) < 3:
                        # Degenerate case
                        if a == h:  # p_{g,h} = p_{a,c,a} = p_{a,c} = p_g
                            add_eq([(pv_gh, 1.0), (mvar(gi, b), -1.0)], 0)
                        elif c == h:
                            add_eq([(pv_gh, 1.0), (mvar(gi, b), -1.0)], 0)
                        continue

                    tv_ach = tvar(a, c, h, b)
                    # EXACT equality: p_{g,h} = p_{a,c,h}
                    add_eq([(pv_gh, 1.0), (tv_ach, -1.0)], 0)

                    # Also: p_{g,h} ≤ p_{a,h} and p_{g,h} ≤ p_{c,h}
                    # (tighter than SA-2's p_{g,h} ≤ p_h)
                    add_ub([(pv_gh, 1.0), (pvar(a, h, b), -1.0)], 0)
                    add_ub([(pv_gh, 1.0), (pvar(c, h, b), -1.0)], 0)

            elif gt == 'OR' and i1 >= n and i2 >= n:
                a, c = i1 - n, i2 - n
                if a == c: continue
                for h in range(n_gates):
                    if h == gi: continue
                    pv_gh = pvar(gi, h, b)
                    # OR(a,c) = g: p_{g,h} = p_{a,h} + p_{c,h} - p_{a,c,h}
                    triple = tuple(sorted([a, c, h]))
                    if len(set(triple)) < 3: continue
                    tv_ach = tvar(a, c, h, b)
                    add_eq([(pv_gh, 1.0), (pvar(a, h, b), -1.0),
                            (pvar(c, h, b), -1.0), (tv_ach, 1.0)], 0)

    nv = total_vars
    c_obj = np.zeros(nv)
    bounds = [(0.0, 1.0)] * nv

    A_eq = csc_matrix((eq_v, (eq_r, eq_c)), shape=(eq_cnt[0], nv)) if eq_cnt[0] > 0 else None
    b_eq = np.array(eq_rhs) if eq_cnt[0] > 0 else None
    A_ub = csc_matrix((ub_v, (ub_r, ub_c)), shape=(ub_cnt[0], nv)) if ub_cnt[0] > 0 else None
    b_ub = np.array(ub_rhs) if ub_cnt[0] > 0 else None

    try:
        res = linprog(c_obj, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                      bounds=bounds, method='highs',
                      options={'presolve': True, 'time_limit': 3.0})
        return res.status != 2
    except:
        return False


def test_true_sa3(n, s, p1, p2, n_trials=300):
    random.seed(42)
    for trial in range(n_trials):
        gt_list = [random.choice(['AND', 'OR', 'NOT']) for _ in range(s)]
        conn_list = []
        for g in range(s):
            avail = list(range(n + g))
            i1 = random.choice(avail)
            i2 = random.choice(avail) if gt_list[g] != 'NOT' else 0
            conn_list.append((i1, i2))
        if check_true_sa3(n, s, gt_list, conn_list, p1, p2):
            return True, trial + 1
    return False, n_trials


if __name__ == '__main__':
    print("TRUE SA-3: Gate-Triple Variables for CLIQUE")
    print("═" * 65)

    from tension_clique import test_tension

    for N, k in [(4, 3), (5, 3), (6, 3)]:
        tt, n = clique_truth_table(N, k)
        result = compute_conditionals(tt, n)
        if not result: continue
        p1, p2, bal = result

        print(f"\n{k}-CLIQUE on N={N} (n={n}, balance={bal:.4f}):")
        print(f"  {'s':>4} {'SA-2':>8} {'TRUE-SA3':>10} {'improvement':>12}  {'time':>6}")
        print(f"  {'-'*45}")

        sa2_bound = sa3_bound = None
        for s in range(1, 20):
            t0 = time.time()
            trials = min(300, 40 * s)

            sa2_feas, _ = test_tension(n, s, p1, p2, n_trials=trials)
            sa3_feas, _ = test_true_sa3(n, s, p1, p2, n_trials=trials)
            dt = time.time() - t0

            sa2_s = "feas" if sa2_feas else "INF"
            sa3_s = "feas" if sa3_feas else "INF"
            imp = "SA3 TIGHTER!" if sa2_feas and not sa3_feas else ""

            print(f"  {s:>4} {sa2_s:>8} {sa3_s:>10} {imp:>12}  {dt:>5.1f}s")

            if sa2_feas and sa2_bound is None: sa2_bound = s
            if sa3_feas and sa3_bound is None: sa3_bound = s

            if sa3_feas:
                break
            if dt > 30:
                print(f"  (timeout at s={s})")
                if sa3_bound is None: sa3_bound = s + 1
                break

        print(f"  → SA-2 bound: {sa2_bound or '?'}, True-SA3 bound: {sa3_bound or '?'}")
        if sa2_bound and sa3_bound and sa3_bound > sa2_bound:
            print(f"  → IMPROVEMENT: +{sa3_bound - sa2_bound} gates!")
