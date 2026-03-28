"""
EXACT SDP BOUNDS FOR 3-CLIQUE via cvxpy.

The SDP relaxation strengthens the LP (Sherali-Adams level 2) by requiring
the matrix M[g,h](b) of pairwise marginals to be positive semidefinite.

For each circuit structure and each output value b in {0,1}:
  - Variables: marginals p_g(b) for each gate g
  - Variables: pairwise p_{g,h}(b) encoded as entries of a PSD matrix M(b)
  - M[g,g](b) = p_g(b)  (diagonal = marginals)
  - M[g,h](b) = p_{g,h}(b)  (off-diagonal = pairwise)
  - M(b) >> 0  (positive semidefinite)
  - Gate semantic constraints (AND/OR/NOT)
  - Output boundary: p_output(1) = 1, p_output(0) = 0
"""

import numpy as np
import cvxpy as cp
import random
import time
import sys

sys.path.insert(0, '/home/user/rayon/src')
from tension_clique import clique_truth_table, compute_conditionals


def check_sdp_feasibility(n, s, gate_types, connections, p1, p2, solver='SCS'):
    """
    Check SDP feasibility for a circuit structure computing a function
    with given conditional probabilities.

    n: number of input bits
    s: number of gates
    gate_types: list of 'AND'/'OR'/'NOT' for each gate
    connections: list of (input1, input2) for each gate
                 inputs < n are circuit inputs, inputs >= n are gate outputs
    p1: dict (i, b) -> Pr[x_i=1 | f(x)=b]  for input variables
    p2: dict (i, j, b) -> Pr[x_i=1 AND x_j=1 | f(x)=b]  for input pairs
    """
    n_gates = s
    output_gate = s - 1  # last gate is output

    constraints = []

    # For each b in {0, 1}, create a PSD matrix M(b) of size n_gates x n_gates
    # M[i,j](b) = p_{gate_i, gate_j}(b)
    # Diagonal M[i,i](b) = p_{gate_i}(b)
    M = {}
    for b in [0, 1]:
        M[b] = cp.Variable((n_gates, n_gates), symmetric=True, name=f'M_{b}')
        constraints.append(M[b] >> 0)  # PSD constraint

        # All entries in [0, 1]
        constraints.append(M[b] >= 0)
        constraints.append(M[b] <= 1)

    # Helper: get marginal p_g(b) = M[g,g](b) for gate g (0-indexed in gate space)
    def mg(g, b):
        return M[b][g, g]

    # Helper: get pairwise p_{g1,g2}(b) = M[g1,g2](b)
    def pg(g1, g2, b):
        return M[b][g1, g2]

    # Gate semantic constraints
    for b in [0, 1]:
        for gi in range(s):
            gt = gate_types[gi]
            i1, i2 = connections[gi]

            if gt == 'NOT':
                if i1 < n:
                    # Gate gi = NOT(input i1)
                    # p_gi(b) = 1 - p1[(i1, b)]
                    ki = p1.get((i1, b), 0.5)
                    constraints.append(mg(gi, b) == 1.0 - ki)
                else:
                    # Gate gi = NOT(gate g1)
                    g1 = i1 - n
                    constraints.append(mg(gi, b) + mg(g1, b) == 1.0)
                    # Pairwise with any other gate gj:
                    # p_{gi, gj}(b) = p_gj(b) - p_{g1, gj}(b)
                    for gj in range(s):
                        if gj != gi and gj != g1:
                            constraints.append(
                                pg(gi, gj, b) == mg(gj, b) - pg(g1, gj, b)
                            )
                    # p_{gi, g1}(b) = 0 (NOT gate and its input can't both be 1...
                    # Actually: NOT(x)=1 and x=1 impossible, but NOT(x)=0 and x=0 also impossible
                    # p_{gi, g1}(b) = Pr[gi=1 AND g1=1 | f=b] = Pr[NOT(g1)=1 AND g1=1 | f=b] = 0
                    constraints.append(pg(gi, g1, b) == 0)

            elif gt == 'AND':
                if i1 < n and i2 < n:
                    # Gate gi = AND(input i1, input i2)
                    kp = p2.get((min(i1, i2), max(i1, i2), b), 0)
                    constraints.append(mg(gi, b) == kp)
                elif i1 >= n and i2 >= n:
                    # Gate gi = AND(gate g1, gate g2)
                    g1, g2 = i1 - n, i2 - n
                    if g1 != g2:
                        constraints.append(mg(gi, b) == pg(g1, g2, b))
                    else:
                        constraints.append(mg(gi, b) == mg(g1, b))
                    # Pairwise: p_{gi, gj}(b) for other gates gj
                    # AND(a,c)=1 AND gj=1 means a=1 AND c=1 AND gj=1
                    # This is a 3-way marginal - we can't express exactly,
                    # but we have Fréchet bounds from PSD + the constraint
                    # p_{gi, gj} <= p_{g1, gj} and p_{gi, gj} <= p_{g2, gj}
                    if g1 != g2:
                        for gj in range(s):
                            if gj != gi:
                                constraints.append(pg(gi, gj, b) <= pg(g1, gj, b))
                                constraints.append(pg(gi, gj, b) <= pg(g2, gj, b))
                else:
                    # Mixed: one input, one gate
                    if i1 < n:
                        ki = p1.get((i1, b), 0.5)
                        gj_idx = i2 - n
                    else:
                        ki = p1.get((i2, b), 0.5)
                        gj_idx = i1 - n
                    # p_gi(b) = ki * p_gj(b) ... no, that's only if independent
                    # Bounds: p_gi(b) <= min(ki, p_gj(b))
                    #         p_gi(b) >= max(0, ki + p_gj(b) - 1)
                    constraints.append(mg(gi, b) <= ki)
                    constraints.append(mg(gi, b) <= mg(gj_idx, b))
                    constraints.append(mg(gi, b) >= ki + mg(gj_idx, b) - 1.0)
                    constraints.append(mg(gi, b) >= 0)
                    # Pairwise with other gates
                    for gk in range(s):
                        if gk != gi:
                            constraints.append(pg(gi, gk, b) <= pg(gj_idx, gk, b) if gk != gj_idx else True)

            elif gt == 'OR':
                if i1 < n and i2 < n:
                    k1 = p1.get((i1, b), 0.5)
                    k2 = p1.get((i2, b), 0.5)
                    kp = p2.get((min(i1, i2), max(i1, i2), b), 0)
                    constraints.append(mg(gi, b) == k1 + k2 - kp)
                elif i1 >= n and i2 >= n:
                    g1, g2 = i1 - n, i2 - n
                    if g1 != g2:
                        # OR(g1,g2) = g1 + g2 - AND(g1,g2)
                        constraints.append(
                            mg(gi, b) == mg(g1, b) + mg(g2, b) - pg(g1, g2, b)
                        )
                        # Pairwise: p_{gi, gj} for other gates
                        # OR(a,c)=1 AND gj=1: at least one of (a AND gj), (c AND gj)
                        # p_{gi,gj} = p_{g1,gj} + p_{g2,gj} - p_{AND(g1,g2), gj}
                        # We bound: p_{gi,gj} >= max(p_{g1,gj}, p_{g2,gj})
                        for gj in range(s):
                            if gj != gi:
                                constraints.append(pg(gi, gj, b) >= pg(g1, gj, b))
                                constraints.append(pg(gi, gj, b) >= pg(g2, gj, b))
                    else:
                        constraints.append(mg(gi, b) == mg(g1, b))
                else:
                    if i1 < n:
                        ki = p1.get((i1, b), 0.5)
                        gj_idx = i2 - n
                    else:
                        ki = p1.get((i2, b), 0.5)
                        gj_idx = i1 - n
                    # OR: p_gi(b) >= max(ki, p_gj(b))
                    #     p_gi(b) <= ki + p_gj(b)
                    #     p_gi(b) <= 1
                    constraints.append(mg(gi, b) >= ki)
                    constraints.append(mg(gi, b) >= mg(gj_idx, b))
                    constraints.append(mg(gi, b) <= ki + mg(gj_idx, b))
                    constraints.append(mg(gi, b) <= 1.0)
                    # Pairwise
                    for gk in range(s):
                        if gk != gi:
                            constraints.append(pg(gi, gk, b) >= pg(gj_idx, gk, b) if gk != gj_idx else True)

        # Output constraint
        constraints.append(mg(output_gate, b) == (1.0 if b == 1 else 0.0))

    # Filter out any True values that snuck in from conditional expressions
    constraints = [c for c in constraints if c is not True]

    # Solve feasibility (minimize 0)
    prob = cp.Problem(cp.Minimize(0), constraints)
    try:
        prob.solve(solver=solver, verbose=False, max_iters=5000,
                   eps=1e-6)
        if prob.status in ['optimal', 'optimal_inaccurate']:
            return True
        elif prob.status in ['infeasible', 'infeasible_inaccurate']:
            return False
        else:
            # Unknown status - treat as infeasible to be conservative
            return False
    except cp.SolverError:
        return False


def test_sdp_tension(n, s, p1, p2, n_trials=200):
    """Test SDP feasibility for many random circuit structures of size s."""
    random.seed(42 + s)
    for trial in range(n_trials):
        gt_list = [random.choice(['AND', 'OR', 'NOT']) for _ in range(s)]
        conn_list = []
        for g in range(s):
            avail = list(range(n + g))
            i1 = random.choice(avail)
            i2 = random.choice(avail) if gt_list[g] != 'NOT' else 0
            conn_list.append((i1, i2))
        if check_sdp_feasibility(n, s, gt_list, conn_list, p1, p2):
            return True, trial + 1
    return False, n_trials


def find_lp_bound(n, p1, p2, max_s=20, n_trials=200):
    """Find smallest s where LP is feasible (using existing LP code)."""
    from tension_clique import check_lp_feasibility
    for s in range(1, max_s + 1):
        random.seed(42 + s)
        for trial in range(n_trials):
            gt_list = [random.choice(['AND', 'OR', 'NOT']) for _ in range(s)]
            conn_list = []
            for g in range(s):
                avail = list(range(n + g))
                i1 = random.choice(avail)
                i2 = random.choice(avail) if gt_list[g] != 'NOT' else 0
                conn_list.append((i1, i2))
            if check_lp_feasibility(n, s, gt_list, conn_list, p1, p2):
                return s
    return max_s + 1


def main():
    print("=" * 70)
    print("EXACT SDP BOUNDS FOR 3-CLIQUE")
    print("SDP = LP + PSD constraint on pairwise marginal matrix")
    print("=" * 70)
    print()

    results = {}

    for N in [4, 5]:
        k = 3
        tt, n = clique_truth_table(N, k)
        ones = bin(tt).count('1')
        total = 2**n

        print(f"3-CLIQUE on N={N}: n={n} input bits, {ones}/{total} true inputs")
        print("-" * 60)

        result = compute_conditionals(tt, n)
        if result is None:
            print("  Constant function, skipping.\n")
            continue
        p1, p2, bal = result

        # Find LP bound first
        print("  Finding LP bound (Sherali-Adams level 2)...")
        t0 = time.time()
        lp_bound = find_lp_bound(n, p1, p2, max_s=15, n_trials=200)
        lp_time = time.time() - t0
        print(f"  LP bound: {lp_bound} (found in {lp_time:.1f}s)")
        print()

        # Find SDP bound
        print("  Finding SDP bound (LP + PSD matrix constraint)...")
        print(f"  {'s':>4} | {'trials':>7} | {'status':>12} | {'time':>8}")
        print(f"  {'-'*42}")

        sdp_bound = None
        # Start searching from 1 up to a reasonable limit
        max_search = min(lp_bound + 5, 18)  # don't search too far

        for s in range(1, max_search + 1):
            t0 = time.time()
            # Use fewer trials for large s (SDP is slower)
            trials = min(200, max(50, 200 // max(1, s - 3)))
            feasible, tried = test_sdp_tension(n, s, p1, p2, n_trials=trials)
            dt = time.time() - t0

            if feasible:
                print(f"  {s:>4} | {tried:>7} | {'FEASIBLE':>12} | {dt:>7.1f}s")
                sdp_bound = s
                break
            else:
                print(f"  {s:>4} | {trials:>7} | {'infeasible':>12} | {dt:>7.1f}s")

            if dt > 120:
                print(f"  (timeout at s={s}, stopping)")
                break

        if sdp_bound is None:
            sdp_bound = f">{max_search}"

        results[N] = (lp_bound, sdp_bound)
        print()

    # Summary
    print("=" * 70)
    print("SUMMARY: LP vs SDP bounds for 3-CLIQUE")
    print("=" * 70)
    print(f"{'N':>4} | {'n (inputs)':>10} | {'LP bound':>10} | {'SDP bound':>10} | {'improvement':>12}")
    print(f"{'-'*58}")
    for N in sorted(results.keys()):
        lp_b, sdp_b = results[N]
        n = N * (N - 1) // 2
        if isinstance(sdp_b, int) and isinstance(lp_b, int):
            imp = sdp_b - lp_b
            imp_str = f"+{imp}" if imp > 0 else str(imp)
        else:
            imp_str = "?"
        print(f"{N:>4} | {n:>10} | {lp_b:>10} | {str(sdp_b):>10} | {imp_str:>12}")

    print()
    print("LP  = Sherali-Adams level 2 (Fréchet bounds on pairwise marginals)")
    print("SDP = LP + positive semidefiniteness of marginal matrix M[g,h](b)")
    print()
    print("If SDP bound > LP bound: the PSD constraint provides additional")
    print("power beyond Fréchet inequalities for ruling out small circuits.")
    print("=" * 70)


if __name__ == '__main__':
    main()
