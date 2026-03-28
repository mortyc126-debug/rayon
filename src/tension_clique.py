"""
TENSION FOR CLIQUE: Computing τ₂(CLIQUE, s) for small instances.

Does the Holographic LP detect that CLIQUE needs large circuits?

Test: k-CLIQUE on N vertices.
  n = C(N,2) edge variables.
  Build truth table, compute conditional probabilities,
  test LP feasibility for various circuit sizes s.

If LP says infeasible at size s: τ₂(CLIQUE, s) > 0 → circuit_size > s.
"""

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csc_matrix
from itertools import combinations
import random
import time
import math

def clique_truth_table(N, k):
    """Build truth table for k-CLIQUE on N vertices."""
    n = N * (N - 1) // 2
    edge_idx = {}
    idx = 0
    for u in range(N):
        for v in range(u + 1, N):
            edge_idx[(u, v)] = idx
            idx += 1

    tt = 0
    for x in range(2**n):
        edges = set()
        for (u, v), i in edge_idx.items():
            if (x >> i) & 1:
                edges.add((u, v))
        has_clique = False
        for subset in combinations(range(N), k):
            if all((min(a, b), max(a, b)) in edges
                   for a in subset for b in subset if a != b):
                has_clique = True
                break
        if has_clique:
            tt |= (1 << x)
    return tt, n


def compute_conditionals(tt, n):
    """Compute marginal and pairwise conditional probabilities."""
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
    return p1, p2, ones / total


def check_lp_feasibility(n, s, gate_types, connections, p1, p2):
    """Check if circuit structure is LP-feasible for function with given conditionals."""
    W = n + s
    output = n + s - 1
    n_gates = s
    n_pairs = n_gates * (n_gates - 1) // 2
    vars_per_b = n_gates + n_pairs
    total_vars = 2 * vars_per_b

    def mvar(gi, b):
        return b * vars_per_b + gi

    pair_map = {}
    idx = n_gates
    for i in range(n_gates):
        for j in range(i + 1, n_gates):
            pair_map[(i, j)] = idx
            idx += 1

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
                    kp = p2.get((min(i1,i2), max(i1,i2), b), 0)
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
                    kp = p2.get((min(i1,i2), max(i1,i2), b), 0)
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

        # Output
        add_eq([(mvar(s - 1, b), 1.0)], 1.0 if b == 1 else 0.0)

        # Pairwise Fréchet
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
                      options={'presolve': True, 'time_limit': 1.0})
        return res.status != 2  # not infeasible = feasible
    except:
        return False


def test_tension(n, s, p1, p2, n_trials=1000):
    """Test LP feasibility for many random circuit structures of size s."""
    random.seed(42)
    for trial in range(n_trials):
        gt_list = [random.choice(['AND', 'OR', 'NOT']) for _ in range(s)]
        conn_list = []
        for g in range(s):
            avail = list(range(n + g))
            i1 = random.choice(avail)
            i2 = random.choice(avail) if gt_list[g] != 'NOT' else 0
            conn_list.append((i1, i2))
        if check_lp_feasibility(n, s, gt_list, conn_list, p1, p2):
            return True, trial + 1  # feasible found
    return False, n_trials  # all infeasible


# ════════════════════════════════════════════════════════════════
print("TENSION FOR CLIQUE")
print("═" * 65)
print()

for N, k in [(4, 3), (5, 3)]:
    tt, n = clique_truth_table(N, k)
    ones = bin(tt).count('1')
    total = 2**n
    balance = ones / total

    print(f"{k}-CLIQUE on N={N}: n={n} variables, balance={balance:.4f}")
    print(f"  ({ones} true inputs out of {total})")

    result = compute_conditionals(tt, n)
    if result is None:
        print("  Constant function, skipping.")
        continue
    p1, p2, bal = result

    # Show conditional marginal structure
    print(f"  Conditional marginals Pr[x_i=1|f=b]:")
    vals_1 = [p1[(i, 1)] for i in range(n)]
    vals_0 = [p1[(i, 0)] for i in range(n)]
    print(f"    f=1: min={min(vals_1):.4f} max={max(vals_1):.4f} mean={sum(vals_1)/len(vals_1):.4f}")
    print(f"    f=0: min={min(vals_0):.4f} max={max(vals_0):.4f} mean={sum(vals_0)/len(vals_0):.4f}")

    # Test tension at various sizes
    print(f"\n  Testing τ₂(CLIQUE, s):")
    print(f"  {'s':>4} {'trials':>8} {'result':>12} {'time':>8}")
    print(f"  {'-'*35}")

    for s in range(1, min(n * 3, 20)):
        t0 = time.time()
        n_trials = min(500, 100 * s)
        feasible, tried = test_tension(n, s, p1, p2, n_trials=n_trials)
        dt = time.time() - t0

        if feasible:
            print(f"  {s:>4} {tried:>8} {'FEASIBLE':>12} {dt:>7.1f}s")
            print(f"  → τ₂(CLIQUE({N},{k}), {s}) = 0. Circuit size ≤ {s} possible.")
            break
        else:
            print(f"  {s:>4} {n_trials:>8} {'infeasible':>12} {dt:>7.1f}s")

        if dt > 30:
            print(f"  (timeout, stopping)")
            break

    print()

# Fourier analysis of CLIQUE
print("═" * 65)
print("FOURIER STRUCTURE OF CLIQUE")
print("-" * 65)
print()

for N, k in [(4, 3)]:
    tt, n = clique_truth_table(N, k)
    total = 2**n

    # Level-by-level Fourier energy
    print(f"{k}-CLIQUE on N={N} (n={n}):")
    for level in range(n + 1):
        energy = 0
        count = 0
        for S in combinations(range(n), level):
            S_mask = sum(1 << i for i in S)
            coeff = sum(((tt >> x) & 1) * ((-1) ** bin(x & S_mask).count('1'))
                       for x in range(total)) / total
            energy += abs(coeff)
            count += 1
        print(f"  Level {level:>2}: {count:>4} coeffs, L1 energy = {energy:.6f}")

print(f"""
═══════════════════════════════════════════════════════════════════
CLIQUE TENSION ANALYSIS:

The LP tests whether conditional probability consistency is
achievable for circuits of each size. The smallest feasible s
is the LP lower bound on circuit size.

For CLIQUE: the conditional probabilities encode:
  "Given that there IS a k-clique, what's the probability each edge is 1?"
  "Given that there is NO k-clique, what's the probability each edge is 1?"

These conditional distributions are HIGHLY STRUCTURED for CLIQUE:
  - Edges within potential cliques have correlated conditionals
  - Edges not in any clique are nearly independent

The LP detects: can a small circuit produce these specific correlations?
If the correlations require many sharing conflicts: large circuit needed.
═══════════════════════════════════════════════════════════════════
""")
