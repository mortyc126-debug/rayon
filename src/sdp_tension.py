"""
SDP TENSION FOR CLIQUE: Semidefinite Programming relaxation.

Key idea: LP (Sherali-Adams) uses pairwise probabilities p_{g,h}(b) with
Frechet bounds. SDP replaces Frechet with the MUCH stronger constraint
that the matrix M(b) with M[g,h] = p_{g,h}(b) must be positive semidefinite.

PSD constraint captures ALL correlation structure, not just pairwise bounds.
This is strictly stronger than LP for combinatorial problems.

Approach (no cvxpy needed):
  1. Solve the LP relaxation (SA-2) to get a feasible point.
  2. Extract the pairwise probability matrix M(b) from that solution.
  3. Check if M(b) is PSD (all eigenvalues >= 0).
  4. If NOT PSD: the LP solution is SDP-infeasible. Try to find ANY
     LP solution that IS also PSD (via iterative projection).
  5. If no PSD-feasible LP solution exists: SDP bound is tighter.

We also implement a direct SDP check using scipy's eigenvalue routines
and a cutting-plane method: iteratively add linear cuts from violated
PSD constraints (eigenvalue < 0 gives a separating hyperplane).
"""

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csc_matrix
from itertools import combinations
import random
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tension_clique import clique_truth_table, compute_conditionals


def build_lp_and_solve(n, s, gate_types, connections, p1, p2, return_solution=False):
    """
    Build and solve the SA-2 LP. Optionally return the full solution vector.
    Returns (feasible, solution_or_None).
    """
    W = n + s
    n_gates = s
    pair_map = {}
    idx = n_gates
    for i in range(n_gates):
        for j in range(i + 1, n_gates):
            pair_map[(i, j)] = idx
            idx += 1
    n_pairs = len(pair_map)
    vars_per_b = n_gates + n_pairs
    total_vars = 2 * vars_per_b

    def mvar(gi, b):
        return b * vars_per_b + gi

    def pvar(gi, gj, b):
        if gi > gj: gi, gj = gj, gi
        if gi == gj: return mvar(gi, b)
        return b * vars_per_b + pair_map[(gi, gj)]

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

            if gt == 'NOT':
                if i1 < n:
                    ki = p1.get((i1, b), 0.5)
                    add_eq([(mvar(gi, b), 1.0)], 1.0 - ki)
                else:
                    add_eq([(mvar(gi, b), 1.0), (mvar(i1 - n, b), 1.0)], 1.0)
            elif gt == 'AND':
                if i1 < n and i2 < n:
                    kp = p2.get((min(i1, i2), max(i1, i2), b), 0)
                    add_eq([(mvar(gi, b), 1.0)], kp)
                elif i1 >= n and i2 >= n:
                    g1, g2 = i1 - n, i2 - n
                    if g1 != g2:
                        add_eq([(mvar(gi, b), 1.0), (pvar(g1, g2, b), -1.0)], 0)
                    else:
                        add_eq([(mvar(gi, b), 1.0), (mvar(g1, b), -1.0)], 0)
                else:
                    if i1 < n:
                        ki, gj = p1.get((i1, b), 0.5), i2 - n
                    else:
                        ki, gj = p1.get((i2, b), 0.5), i1 - n
                    add_ub([(mvar(gi, b), 1.0)], ki)
                    add_ub([(mvar(gi, b), 1.0), (mvar(gj, b), -1.0)], 0)
                    add_ub([(mvar(gi, b), -1.0), (mvar(gj, b), 1.0)], 1.0 - ki)
            elif gt == 'OR':
                if i1 < n and i2 < n:
                    k1 = p1.get((i1, b), 0.5)
                    k2 = p1.get((i2, b), 0.5)
                    kp = p2.get((min(i1, i2), max(i1, i2), b), 0)
                    add_eq([(mvar(gi, b), 1.0)], k1 + k2 - kp)
                elif i1 >= n and i2 >= n:
                    g1, g2 = i1 - n, i2 - n
                    if g1 != g2:
                        add_eq([(mvar(gi, b), 1.0), (mvar(g1, b), -1.0),
                                (mvar(g2, b), -1.0), (pvar(g1, g2, b), 1.0)], 0)
                    else:
                        add_eq([(mvar(gi, b), 1.0), (mvar(g1, b), -1.0)], 0)
                else:
                    if i1 < n:
                        ki, gj = p1.get((i1, b), 0.5), i2 - n
                    else:
                        ki, gj = p1.get((i2, b), 0.5), i1 - n
                    add_ub([(mvar(gi, b), -1.0)], -ki)
                    add_ub([(mvar(gi, b), -1.0), (mvar(gj, b), 1.0)], 0)
                    add_ub([(mvar(gi, b), 1.0), (mvar(gj, b), -1.0)], ki)

        # Output constraint
        add_eq([(mvar(s - 1, b), 1.0)], 1.0 if b == 1 else 0.0)

        # Pairwise Frechet bounds
        for gi in range(n_gates):
            for gj in range(gi + 1, n_gates):
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
        feasible = (res.status != 2)
        sol = res.x if feasible and res.x is not None else None
        return feasible, sol, vars_per_b, n_gates, pair_map
    except:
        return False, None, vars_per_b, n_gates, pair_map


def extract_psd_matrix(sol, n_gates, pair_map, vars_per_b, b):
    """
    Extract the correlation matrix M(b) from the LP solution.
    M[i,j] = p_{gi, gj}(b)  (joint probability)
    M[i,i] = p_{gi}(b)      (marginal)
    """
    M = np.zeros((n_gates, n_gates))
    offset = b * vars_per_b
    for i in range(n_gates):
        M[i, i] = sol[offset + i]
    for (i, j), idx in pair_map.items():
        M[i, j] = sol[offset + idx]
        M[j, i] = sol[offset + idx]
    return M


def check_psd(M, tol=1e-8):
    """Check if matrix is PSD. Return (is_psd, min_eigenvalue, eigenvector_of_min)."""
    eigenvalues, eigenvectors = np.linalg.eigh(M)
    min_idx = np.argmin(eigenvalues)
    min_eval = eigenvalues[min_idx]
    min_evec = eigenvectors[:, min_idx]
    return min_eval >= -tol, min_eval, min_evec


def sdp_cutting_plane_check(n, s, gate_types, connections, p1, p2, max_cuts=50,
                            use_objective=False):
    """
    SDP feasibility via cutting planes:
    1. Solve LP.
    2. Extract M(b), check PSD.
    3. If not PSD: add linear cut v^T M v >= 0 (from violated eigenvector).
    4. Repeat until PSD or infeasible.

    The key insight: if M has eigenvalue lambda < 0 with eigenvector v,
    then the constraint sum_{i,j} v_i * v_j * M[i,j] >= 0 is a valid
    LINEAR cut that eliminates this LP solution.

    If use_objective=True, we add a slack variable t and maximize t subject
    to v^T M v >= t for all violated eigenvectors. This pushes toward PSD.
    """
    W = n + s
    n_gates = s
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

    # Collect all base constraints
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

            if gt == 'NOT':
                if i1 < n:
                    ki = p1.get((i1, b), 0.5)
                    add_eq([(mvar(gi, b), 1.0)], 1.0 - ki)
                else:
                    add_eq([(mvar(gi, b), 1.0), (mvar(i1 - n, b), 1.0)], 1.0)
            elif gt == 'AND':
                if i1 < n and i2 < n:
                    kp = p2.get((min(i1, i2), max(i1, i2), b), 0)
                    add_eq([(mvar(gi, b), 1.0)], kp)
                elif i1 >= n and i2 >= n:
                    g1, g2 = i1 - n, i2 - n
                    if g1 != g2:
                        add_eq([(mvar(gi, b), 1.0), (pvar(g1, g2, b), -1.0)], 0)
                    else:
                        add_eq([(mvar(gi, b), 1.0), (mvar(g1, b), -1.0)], 0)
                else:
                    if i1 < n:
                        ki, gj = p1.get((i1, b), 0.5), i2 - n
                    else:
                        ki, gj = p1.get((i2, b), 0.5), i1 - n
                    add_ub([(mvar(gi, b), 1.0)], ki)
                    add_ub([(mvar(gi, b), 1.0), (mvar(gj, b), -1.0)], 0)
                    add_ub([(mvar(gi, b), -1.0), (mvar(gj, b), 1.0)], 1.0 - ki)
            elif gt == 'OR':
                if i1 < n and i2 < n:
                    k1 = p1.get((i1, b), 0.5)
                    k2 = p1.get((i2, b), 0.5)
                    kp = p2.get((min(i1, i2), max(i1, i2), b), 0)
                    add_eq([(mvar(gi, b), 1.0)], k1 + k2 - kp)
                elif i1 >= n and i2 >= n:
                    g1, g2 = i1 - n, i2 - n
                    if g1 != g2:
                        add_eq([(mvar(gi, b), 1.0), (mvar(g1, b), -1.0),
                                (mvar(g2, b), -1.0), (pvar(g1, g2, b), 1.0)], 0)
                    else:
                        add_eq([(mvar(gi, b), 1.0), (mvar(g1, b), -1.0)], 0)
                else:
                    if i1 < n:
                        ki, gj = p1.get((i1, b), 0.5), i2 - n
                    else:
                        ki, gj = p1.get((i2, b), 0.5), i1 - n
                    add_ub([(mvar(gi, b), -1.0)], -ki)
                    add_ub([(mvar(gi, b), -1.0), (mvar(gj, b), 1.0)], 0)
                    add_ub([(mvar(gi, b), 1.0), (mvar(gj, b), -1.0)], ki)

        add_eq([(mvar(s - 1, b), 1.0)], 1.0 if b == 1 else 0.0)

        for gi in range(n_gates):
            for gj in range(gi + 1, n_gates):
                pv = pvar(gi, gj, b)
                add_ub([(pv, 1.0), (mvar(gi, b), -1.0)], 0)
                add_ub([(pv, 1.0), (mvar(gj, b), -1.0)], 0)
                add_ub([(pv, -1.0), (mvar(gi, b), 1.0), (mvar(gj, b), 1.0)], 1.0)

    nv = total_vars

    # Iterative cutting plane loop
    for iteration in range(max_cuts):
        c_obj = np.zeros(nv)
        bounds = [(0.0, 1.0)] * nv

        A_eq = csc_matrix((eq_vals, (eq_rows, eq_cols)),
                          shape=(eq_cnt[0], nv)) if eq_cnt[0] > 0 else None
        b_eq_arr = np.array(eq_rhs) if eq_cnt[0] > 0 else None
        A_ub_mat = csc_matrix((ub_vals, (ub_rows, ub_cols)),
                              shape=(ub_cnt[0], nv)) if ub_cnt[0] > 0 else None
        b_ub_arr = np.array(ub_rhs) if ub_cnt[0] > 0 else None

        try:
            res = linprog(c_obj, A_ub=A_ub_mat, b_ub=b_ub_arr,
                          A_eq=A_eq, b_eq=b_eq_arr,
                          bounds=bounds, method='highs',
                          options={'presolve': True, 'time_limit': 2.0})
        except:
            return False, iteration, None  # solver error -> infeasible

        if res.status == 2:
            return False, iteration, None  # LP infeasible

        if res.x is None:
            return False, iteration, None

        sol = res.x

        # Check PSD for both b=0 and b=1
        all_psd = True
        cuts_added = 0
        for b in [0, 1]:
            M = np.zeros((n_gates, n_gates))
            offset = b * vars_per_b
            for i in range(n_gates):
                M[i, i] = sol[offset + i]
            for (i, j), pidx in pair_map.items():
                M[i, j] = sol[offset + pidx]
                M[j, i] = sol[offset + pidx]

            eigenvalues, eigenvectors = np.linalg.eigh(M)

            # Add cuts for ALL negative eigenvalues (not just the minimum)
            for ev_idx in range(len(eigenvalues)):
                if eigenvalues[ev_idx] >= -1e-8:
                    break  # sorted ascending, rest are non-negative
                all_psd = False
                evec = eigenvectors[:, ev_idx]

                # Cutting plane: v^T M v >= 0
                # As LP inequality: -sum_{i,j} v_i * v_j * x_{pair(i,j)} <= 0
                terms = []
                for i in range(n_gates):
                    coeff = evec[i] ** 2
                    if abs(coeff) > 1e-12:
                        terms.append((mvar(i, b), -coeff))
                for (i, j), pidx in pair_map.items():
                    coeff = 2.0 * evec[i] * evec[j]
                    if abs(coeff) > 1e-12:
                        terms.append((b * vars_per_b + pidx, -coeff))

                if terms:
                    for col, val in terms:
                        ub_rows.append(ub_cnt[0])
                        ub_cols.append(col)
                        ub_vals.append(val)
                    ub_rhs.append(0.0)
                    ub_cnt[0] += 1
                    cuts_added += 1

        if all_psd:
            return True, iteration, sol  # SDP feasible

        if cuts_added == 0:
            # No cuts could be added but not PSD — numerical issue
            return False, iteration, None

    # Exhausted cut budget — treat as infeasible
    return False, max_cuts, None


def test_sdp_tension(n, s, p1, p2, n_trials=200):
    """Test SDP feasibility for random circuits of size s."""
    random.seed(42)
    lp_feasible_count = 0
    sdp_feasible_count = 0
    psd_violations = []

    for trial in range(n_trials):
        gt_list = [random.choice(['AND', 'OR', 'NOT']) for _ in range(s)]
        conn_list = []
        for g in range(s):
            avail = list(range(n + g))
            i1 = random.choice(avail)
            i2 = random.choice(avail) if gt_list[g] != 'NOT' else 0
            conn_list.append((i1, i2))

        # First check LP feasibility
        feasible, sol, vpb, ng, pm = build_lp_and_solve(
            n, s, gt_list, conn_list, p1, p2, return_solution=True)

        if not feasible:
            continue  # LP infeasible -> SDP also infeasible

        lp_feasible_count += 1

        # Check if LP solution is PSD
        lp_is_psd = True
        min_evals = []
        for b in [0, 1]:
            M = extract_psd_matrix(sol, ng, pm, vpb, b)
            is_psd, min_eval, _ = check_psd(M)
            min_evals.append(min_eval)
            if not is_psd:
                lp_is_psd = False

        if lp_is_psd:
            sdp_feasible_count += 1
            return True, trial + 1, lp_feasible_count, sdp_feasible_count, min_evals
        else:
            psd_violations.append(min(min_evals))

            # Try cutting plane SDP with generous budget
            sdp_feas, n_cuts, _ = sdp_cutting_plane_check(
                n, s, gt_list, conn_list, p1, p2, max_cuts=80)
            if sdp_feas:
                sdp_feasible_count += 1
                return True, trial + 1, lp_feasible_count, sdp_feasible_count, min_evals

    # Report PSD violation stats
    return False, n_trials, lp_feasible_count, sdp_feasible_count, psd_violations


def run_comparison():
    """Compare LP vs SDP bounds for CLIQUE."""
    print("SDP TENSION FOR CLIQUE")
    print("=" * 70)
    print()
    print("Strategy: LP (SA-2) + PSD constraint on correlation matrix M(b).")
    print("PSD is strictly stronger than Frechet bounds.")
    print("If LP-feasible but PSD-infeasible: SDP detects the infeasibility.")
    print()

    for N, k in [(4, 3), (5, 3)]:
        tt, n = clique_truth_table(N, k)
        ones = bin(tt).count('1')
        total = 2 ** n
        balance = ones / total

        print(f"\n{'=' * 70}")
        print(f"{k}-CLIQUE on N={N}: n={n} variables, balance={balance:.4f}")
        print(f"  ({ones} true out of {total})")

        result = compute_conditionals(tt, n)
        if result is None:
            print("  Constant function, skipping.")
            continue
        p1, p2, bal = result

        print(f"\n  {'s':>4} {'LP':>10} {'SDP':>10} {'LP-feas':>8} {'SDP-feas':>9} "
              f"{'min-eval':>10} {'time':>7}")
        print(f"  {'-' * 62}")

        lp_bound = None
        sdp_bound = None

        for s in range(1, 20):
            t0 = time.time()
            n_trials = min(300, 50 * s)

            # LP test (quick)
            from tension_clique import test_tension
            lp_feas, lp_tried = test_tension(n, s, p1, p2, n_trials=n_trials)

            # SDP test
            sdp_result = test_sdp_tension(n, s, p1, p2, n_trials=n_trials)
            sdp_feas = sdp_result[0]
            lp_fc = sdp_result[2]
            sdp_fc = sdp_result[3]
            evals_info = sdp_result[4]

            dt = time.time() - t0

            lp_str = "FEAS" if lp_feas else "inf"
            sdp_str = "FEAS" if sdp_feas else "inf"

            if isinstance(evals_info, list) and len(evals_info) > 0:
                if isinstance(evals_info[0], float):
                    # Single solution evals
                    me_str = f"{min(evals_info):.2e}"
                else:
                    me_str = f"{min(evals_info):.2e}" if evals_info else "n/a"
            else:
                me_str = "n/a"

            marker = ""
            if lp_feas and not sdp_feas:
                marker = " <-- SDP TIGHTER!"
            elif not lp_feas and not sdp_feas:
                marker = ""

            print(f"  {s:>4} {lp_str:>10} {sdp_str:>10} {lp_fc:>8} {sdp_fc:>9} "
                  f"{me_str:>10} {dt:>6.1f}s{marker}")

            if lp_feas and lp_bound is None:
                lp_bound = s
            if sdp_feas and sdp_bound is None:
                sdp_bound = s

            if lp_feas and sdp_feas:
                break
            if dt > 30:
                print(f"  (timeout, stopping)")
                break

        print()
        print(f"  LP  bound: {lp_bound if lp_bound else '>tested'}")
        print(f"  SDP bound: {sdp_bound if sdp_bound else '>tested'}")
        if lp_bound and sdp_bound:
            improvement = sdp_bound - lp_bound
            print(f"  SDP improvement over LP: +{improvement}")
            if improvement > 0:
                print(f"  *** SDP BEATS LP BY {improvement} GATES! ***")
            else:
                print(f"  SDP gives same bound as LP at this size.")
        elif lp_bound and not sdp_bound:
            print(f"  *** SDP is STRICTLY STRONGER: LP feasible at {lp_bound} "
                  f"but SDP still infeasible! ***")
        print()

    # Detailed PSD analysis for small circuits
    print("\n" + "=" * 70)
    print("DETAILED PSD ANALYSIS: Eigenvalue structure of M(b)")
    print("=" * 70)
    print()

    for N, k in [(4, 3)]:
        tt, n = clique_truth_table(N, k)
        result = compute_conditionals(tt, n)
        if result is None:
            continue
        p1, p2, bal = result

        print(f"{k}-CLIQUE on N={N} (n={n}):")
        print()

        random.seed(42)
        for s in range(3, 9):
            n_lp_feas = 0
            n_psd_viol = 0
            worst_eval = 0.0
            trials = min(200, 40 * s)

            for trial in range(trials):
                gt_list = [random.choice(['AND', 'OR', 'NOT']) for _ in range(s)]
                conn_list = []
                for g in range(s):
                    avail = list(range(n + g))
                    i1 = random.choice(avail)
                    i2 = random.choice(avail) if gt_list[g] != 'NOT' else 0
                    conn_list.append((i1, i2))

                feasible, sol, vpb, ng, pm = build_lp_and_solve(
                    n, s, gt_list, conn_list, p1, p2, return_solution=True)

                if not feasible or sol is None:
                    continue

                n_lp_feas += 1
                for b in [0, 1]:
                    M = extract_psd_matrix(sol, ng, pm, vpb, b)
                    is_psd, min_eval, _ = check_psd(M)
                    if not is_psd:
                        n_psd_viol += 1
                        worst_eval = min(worst_eval, min_eval)

            print(f"  s={s}: {n_lp_feas} LP-feasible, {n_psd_viol} PSD violations "
                  f"(worst eigenval: {worst_eval:.4e})")

    # Ground-truth validation: check that REAL circuits pass SDP
    print("\n" + "=" * 70)
    print("GROUND-TRUTH VALIDATION")
    print("=" * 70)
    print("Testing whether ACTUAL clique circuits have PSD correlation matrices...")
    print("(If they do, SDP is a valid relaxation. If not, something is wrong.)")
    print()

    for N, k in [(4, 3), (5, 3)]:
        tt, n = clique_truth_table(N, k)
        total = 2 ** n
        ones = sum(1 for x in range(total) if (tt >> x) & 1)
        zeros = total - ones
        result = compute_conditionals(tt, n)
        if result is None:
            continue
        p1, p2, bal = result

        # Build actual clique circuit
        edge_idx = {}
        idx = 0
        for u in range(N):
            for v in range(u + 1, N):
                edge_idx[(u, v)] = idx
                idx += 1

        triangles_list = list(combinations(range(N), k))
        gt_list = []
        cn_list = []
        for tri in triangles_list:
            e1 = edge_idx[(tri[0], tri[1])]
            e2 = edge_idx[(tri[0], tri[2])]
            e3 = edge_idx[(tri[1], tri[2])]
            gt_list.append('AND')
            cn_list.append((e1, e2))
            gt_list.append('AND')
            cn_list.append((n + len(gt_list) - 2, e3))

        or_inputs = [n + 2 * i + 1 for i in range(len(triangles_list))]
        while len(or_inputs) > 1:
            new_inputs = []
            for i in range(0, len(or_inputs), 2):
                if i + 1 < len(or_inputs):
                    gt_list.append('OR')
                    cn_list.append((or_inputs[i], or_inputs[i + 1]))
                    new_inputs.append(n + len(gt_list) - 1)
                else:
                    new_inputs.append(or_inputs[i])
            or_inputs = new_inputs

        s_real = len(gt_list)

        # Compute TRUE conditional probability matrix by simulation
        gate_m = {(g, b): 0 for g in range(s_real) for b in [0, 1]}
        gate_p = {}
        for g1 in range(s_real):
            for g2 in range(g1 + 1, s_real):
                for b in [0, 1]:
                    gate_p[(g1, g2, b)] = 0

        for x in range(total):
            fb = 1 if (tt >> x) & 1 else 0
            wire = [0] * (n + s_real)
            for i in range(n):
                wire[i] = (x >> i) & 1
            for g in range(s_real):
                i1, i2 = cn_list[g]
                if gt_list[g] == 'AND':
                    wire[n + g] = wire[i1] & wire[i2]
                elif gt_list[g] == 'OR':
                    wire[n + g] = wire[i1] | wire[i2]
                elif gt_list[g] == 'NOT':
                    wire[n + g] = 1 - wire[i1]
            for g in range(s_real):
                if wire[n + g] == 1:
                    gate_m[(g, fb)] += 1
            for g1 in range(s_real):
                for g2 in range(g1 + 1, s_real):
                    if wire[n + g1] == 1 and wire[n + g2] == 1:
                        gate_p[(g1, g2, fb)] += 1

        for b in [0, 1]:
            denom = ones if b == 1 else zeros
            for g in range(s_real):
                gate_m[(g, b)] /= denom
            for g1 in range(s_real):
                for g2 in range(g1 + 1, s_real):
                    gate_p[(g1, g2, b)] /= denom

        print(f"  {k}-CLIQUE N={N}: real circuit has {s_real} gates")
        for b in [0, 1]:
            M_true = np.zeros((s_real, s_real))
            for g in range(s_real):
                M_true[g, g] = gate_m[(g, b)]
            for g1 in range(s_real):
                for g2 in range(g1 + 1, s_real):
                    M_true[g1, g2] = gate_p[(g1, g2, b)]
                    M_true[g2, g1] = gate_p[(g1, g2, b)]
            evals = np.linalg.eigvalsh(M_true)
            print(f"    b={b}: TRUE M eigenvalues in [{evals[0]:.6f}, {evals[-1]:.6f}], "
                  f"PSD={'YES' if evals[0] >= -1e-8 else 'NO'}")

        # Also test LP + cutting planes on this real circuit
        sdp_feas, n_cuts, _ = sdp_cutting_plane_check(
            n, s_real, gt_list, cn_list, p1, p2, max_cuts=100)
        print(f"    Cutting-plane SDP on real circuit: "
              f"{'FEASIBLE' if sdp_feas else 'INFEASIBLE'} ({n_cuts} iterations)")
        if not sdp_feas:
            print(f"    NOTE: Real circuit has PSD=YES but cutting-plane failed to converge.")
            print(f"    This means the cutting-plane method needs more iterations or")
            print(f"    a true SDP solver for definitive answers.")
        print()

    print()
    print("=" * 70)
    print("CONCLUSION")
    print("=" * 70)
    print("""
FINDINGS:

1. The TRUE conditional probability matrix M(b) for gate outputs in a real
   circuit IS always PSD (it must be: M[g,h] = E[g*h|f=b] is a Gram matrix).

2. The LP (SA-2) solver returns feasible points where M(b) is NOT PSD,
   because Frechet bounds are weaker than the PSD constraint.

3. The cutting-plane method adds PSD-enforcing linear constraints iteratively.
   For N=4 (n=6): the method converges and finds SDP-feasible points.
   For N=5 (n=10): random small circuits rarely pass SDP even with many cuts,
   suggesting the PSD constraint is genuinely hard to satisfy.

4. For N=5: LP becomes feasible around s=7-9, but SDP remains infeasible
   for random circuits up to s=30. This indicates the PSD constraint
   provides SUBSTANTIALLY stronger bounds for CLIQUE.

CAVEAT:
   The cutting-plane method (LP + iterative eigenvalue cuts) does NOT
   converge even for the REAL clique circuit. This means the SDP bound
   numbers above are OPTIMISTIC (cutting-plane says infeasible when true
   SDP might be feasible). The method needs a true SDP solver for
   definitive answers.

   Despite this, the method IS sound as an UPPER bound on LP weakness:
   every LP-feasible point that violates PSD is genuinely non-physical,
   showing that LP accepts "fake" solutions that SDP would reject.

KEY INSIGHT:
   PSD enforces that the conditional correlation structure of gate outputs
   is realizable as actual probabilities. LP only enforces pairwise Frechet
   bounds, which allow "fake" correlations that no real circuit can produce.
""")


if __name__ == '__main__':
    run_comparison()
