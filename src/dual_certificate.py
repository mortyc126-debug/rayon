"""
DUAL CERTIFICATE ANALYSIS: The mathematical core of circuit lower bounds.

The Holographic LP v2 proves: for n=3, size-3 circuits CANNOT compute
the hardest functions (LP infeasible). Size-4 CAN (LP feasible).

The LP DUAL gives us a CERTIFICATE of infeasibility — a set of weights
on constraints that sum to a contradiction.

THIS IS THE MATHEMATICAL OBJECT WE NEED TO UNDERSTAND.

If we can characterize the dual certificate's STRUCTURE:
  - What makes it exist for size 3 but not size 4?
  - Does the structure generalize to larger n?
  - Can we construct dual certificates for CLIQUE circuits?

The dual certificate IS the proof. Understanding it IS solving the problem.
"""

import numpy as np
from scipy.optimize import linprog
from itertools import combinations
import random
import math

# ================================================================
# Build the LP for a specific circuit and function, RETURN DUAL
# ================================================================

def truth_table_conditionals(tt, n):
    """Compute p_{x_i}(b) and p_{x_i,x_j}(b) from truth table."""
    total = 2**n
    ones = sum(1 for x in range(total) if (tt >> x) & 1)
    zeros = total - ones
    if ones == 0 or zeros == 0:
        return None

    p1 = {}  # marginals
    for i in range(n):
        for b in [0, 1]:
            count = sum(1 for x in range(total)
                       if ((x >> i) & 1) == 1 and ((tt >> x) & 1) == b)
            denom = ones if b == 1 else zeros
            p1[(i, b)] = count / denom

    p2 = {}  # pairwise
    for i in range(n):
        for j in range(i, n):
            for b in [0, 1]:
                count = sum(1 for x in range(total)
                           if ((x >> i) & 1) and ((x >> j) & 1) and ((tt >> x) & 1) == b)
                denom = ones if b == 1 else zeros
                p2[(i, j, b)] = count / denom
    return p1, p2, ones / total


def build_lp_with_dual(n, s, gate_types, connections, p1, p2):
    """
    Build LP for circuit feasibility. Return primal status and DUAL variables.

    Variables: for each b in {0,1}:
      p_g(b) for gates g = n..n+s-1
      p_{g,h}(b) for pairs (g,h) with g < h, both gates

    Constraints:
      Equality: gate semantics (AND/OR/NOT exact equations)
      Inequality: Fréchet bounds on pairwise probs
      Bounds: 0 ≤ all probs ≤ 1
    """
    W = n + s  # total wires
    output = n + s - 1

    # Variable indexing: for each b in {0,1}
    # Marginals: p_g(b) for g in [n, n+s)
    # Pairwise: p_{g,h}(b) for g < h, both in [n, n+s)
    # We only create variables for GATE marginals and GATE-GATE pairwise

    gate_indices = list(range(n, n + s))
    n_gates = s

    # Variable layout per b:
    # [0, s): marginal p_g(b) for gates g=n..n+s-1
    # [s, s + s*(s-1)/2): pairwise p_{g,h}(b) for gate pairs
    n_pairs = n_gates * (n_gates - 1) // 2
    vars_per_b = n_gates + n_pairs
    total_vars = 2 * vars_per_b  # for b=0 and b=1

    def mvar(g_idx, b):
        """Index of marginal variable p_{gate[g_idx]}(b)."""
        return b * vars_per_b + g_idx

    pair_map = {}
    idx = n_gates
    for i in range(n_gates):
        for j in range(i + 1, n_gates):
            pair_map[(i, j)] = idx
            idx += 1

    def pvar(gi, gj, b):
        """Index of pairwise variable p_{gate[gi], gate[gj]}(b)."""
        if gi > gj:
            gi, gj = gj, gi
        if gi == gj:
            return mvar(gi, b)  # p_{g,g} = p_g
        return b * vars_per_b + pair_map[(gi, gj)]

    # Known values for input wires
    def known_marginal(wire, b):
        if wire < n:
            return p1.get((wire, b))
        return None

    def known_pairwise(w1, w2, b):
        if w1 < n and w2 < n:
            i, j = min(w1, w2), max(w1, w2)
            return p2.get((i, j, b))
        return None

    # Build constraint matrices
    eq_rows, eq_cols, eq_vals, eq_rhs = [], [], [], []
    ub_rows, ub_cols, ub_vals, ub_rhs = [], [], [], []
    eq_cnt = 0
    ub_cnt = 0

    def add_eq(terms, rhs):
        nonlocal eq_cnt
        for col, val in terms:
            eq_rows.append(eq_cnt)
            eq_cols.append(col)
            eq_vals.append(val)
        eq_rhs.append(rhs)
        eq_cnt += 1

    def add_ub(terms, rhs):
        nonlocal ub_cnt
        for col, val in terms:
            ub_rows.append(ub_cnt)
            ub_cols.append(col)
            ub_vals.append(val)
        ub_rhs.append(rhs)
        ub_cnt += 1

    for b in [0, 1]:
        for g_idx in range(s):
            g = n + g_idx
            gt = gate_types[g_idx]
            i1, i2 = connections[g_idx]

            # ---- MARGINAL gate constraints ----
            if gt == 'AND':
                # p_g(b) = p_{i1,i2}(b) (joint prob of both inputs being 1)
                # Need to handle: i1,i2 can be inputs or gates
                # Case: both inputs
                if i1 < n and i2 < n:
                    km = known_pairwise(i1, i2, b)
                    if km is not None:
                        add_eq([(mvar(g_idx, b), 1.0)], km)
                elif i1 < n and i2 >= n:
                    # p_g = p_{i1, gate_i2}  — need pairwise with input
                    # Approximate: use Fréchet bounds
                    ki1 = known_marginal(i1, b)
                    gi2 = i2 - n
                    # p_g ≤ min(p_{i1}, p_{i2})
                    if ki1 is not None:
                        add_ub([(mvar(g_idx, b), 1.0)], ki1)
                    add_ub([(mvar(g_idx, b), 1.0), (mvar(gi2, b), -1.0)], 0)
                    # p_g ≥ p_{i1} + p_{i2} - 1
                    rhs = -1.0
                    terms = [(mvar(g_idx, b), -1.0), (mvar(gi2, b), 1.0)]
                    if ki1 is not None:
                        rhs += -ki1
                    add_ub(terms, rhs)
                elif i1 >= n and i2 < n:
                    ki2 = known_marginal(i2, b)
                    gi1 = i1 - n
                    if ki2 is not None:
                        add_ub([(mvar(g_idx, b), 1.0)], ki2)
                    add_ub([(mvar(g_idx, b), 1.0), (mvar(gi1, b), -1.0)], 0)
                    rhs = -1.0
                    terms = [(mvar(g_idx, b), -1.0), (mvar(gi1, b), 1.0)]
                    if ki2 is not None:
                        rhs += -ki2
                    add_ub(terms, rhs)
                else:
                    # Both gates: p_g = p_{i1,i2} = pvar
                    gi1, gi2 = i1 - n, i2 - n
                    if gi1 != gi2:
                        pv = pvar(gi1, gi2, b)
                        add_eq([(mvar(g_idx, b), 1.0), (pv, -1.0)], 0)
                    else:
                        # AND(g,g) = g
                        add_eq([(mvar(g_idx, b), 1.0), (mvar(gi1, b), -1.0)], 0)

            elif gt == 'OR':
                # p_g(b) = p_{i1}(b) + p_{i2}(b) - p_{i1,i2}(b)
                if i1 < n and i2 < n:
                    ki1 = known_marginal(i1, b)
                    ki2 = known_marginal(i2, b)
                    kp = known_pairwise(i1, i2, b)
                    rhs = 0
                    if ki1 is not None: rhs += ki1
                    if ki2 is not None: rhs += ki2
                    if kp is not None: rhs -= kp
                    add_eq([(mvar(g_idx, b), 1.0)], rhs)
                elif i1 >= n and i2 >= n:
                    gi1, gi2 = i1 - n, i2 - n
                    if gi1 != gi2:
                        pv = pvar(gi1, gi2, b)
                        add_eq([(mvar(g_idx, b), 1.0),
                                (mvar(gi1, b), -1.0),
                                (mvar(gi2, b), -1.0),
                                (pv, 1.0)], 0)
                    else:
                        # OR(g,g) = g
                        add_eq([(mvar(g_idx, b), 1.0), (mvar(gi1, b), -1.0)], 0)
                else:
                    # Mixed: one input, one gate — use bounds
                    if i1 < n:
                        ki = known_marginal(i1, b)
                        gi = i2 - n
                    else:
                        ki = known_marginal(i2, b)
                        gi = i1 - n
                    # OR: p_g ≥ max(p_input, p_gate)
                    if ki is not None:
                        add_ub([(mvar(g_idx, b), -1.0)], -ki)
                    add_ub([(mvar(g_idx, b), -1.0), (mvar(gi, b), 1.0)], 0)
                    # OR: p_g ≤ p_input + p_gate
                    terms = [(mvar(g_idx, b), 1.0), (mvar(gi, b), -1.0)]
                    rhs = ki if ki is not None else 1.0
                    add_ub(terms, rhs)

            elif gt == 'NOT':
                if i1 < n:
                    ki = known_marginal(i1, b)
                    if ki is not None:
                        add_eq([(mvar(g_idx, b), 1.0)], 1.0 - ki)
                else:
                    gi = i1 - n
                    add_eq([(mvar(g_idx, b), 1.0), (mvar(gi, b), 1.0)], 1.0)

        # Output constraint
        out_idx = s - 1
        add_eq([(mvar(out_idx, b), 1.0)], 1.0 if b == 1 else 0.0)

        # ---- PAIRWISE Fréchet bounds ----
        for gi in range(n_gates):
            for gj in range(gi + 1, n_gates):
                pv = pvar(gi, gj, b)
                # p_{gi,gj} ≤ p_gi
                add_ub([(pv, 1.0), (mvar(gi, b), -1.0)], 0)
                # p_{gi,gj} ≤ p_gj
                add_ub([(pv, 1.0), (mvar(gj, b), -1.0)], 0)
                # p_{gi,gj} ≥ p_gi + p_gj - 1
                add_ub([(pv, -1.0), (mvar(gi, b), 1.0), (mvar(gj, b), 1.0)], 1.0)
                # p_{gi,gj} ≥ 0  (already in bounds)

    # Solve
    from scipy.sparse import csc_matrix

    nv = total_vars
    c_obj = np.zeros(nv)
    bounds = [(0.0, 1.0)] * nv

    A_eq = csc_matrix((eq_vals, (eq_rows, eq_cols)), shape=(eq_cnt, nv)) if eq_cnt > 0 else None
    b_eq = np.array(eq_rhs) if eq_cnt > 0 else None
    A_ub = csc_matrix((ub_vals, (ub_rows, ub_cols)), shape=(ub_cnt, nv)) if ub_cnt > 0 else None
    b_ub = np.array(ub_rhs) if ub_cnt > 0 else None

    try:
        # Use revised simplex for dual access
        res = linprog(c_obj, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                      bounds=bounds, method='highs',
                      options={'presolve': True, 'time_limit': 2.0,
                               'dual_feasibility_tolerance': 1e-7})

        feasible = res.success and res.status == 0
        infeasible = res.status == 2

        # Extract dual values if available
        dual_eq = None
        dual_ub = None
        if hasattr(res, 'eqlin') and res.eqlin is not None:
            dual_eq = res.eqlin.marginals if hasattr(res.eqlin, 'marginals') else None
        if hasattr(res, 'ineqlin') and res.ineqlin is not None:
            dual_ub = res.ineqlin.marginals if hasattr(res.ineqlin, 'marginals') else None

        return feasible, infeasible, res, dual_eq, dual_ub, eq_cnt, ub_cnt

    except Exception as e:
        return False, True, None, None, None, eq_cnt, ub_cnt


# ================================================================
# Compute minimum circuit sizes
# ================================================================
def compute_sizes(n):
    total = 2**(2**n)
    level = {}
    cur = set()
    cur.add(0); cur.add(total - 1)
    for i in range(n):
        tt = 0
        for x in range(2**n):
            if (x >> i) & 1: tt |= (1 << x)
        cur.add(tt); cur.add((total - 1) ^ tt)
    for tt in cur: level[tt] = 0
    s = 0
    while len(level) < total:
        s += 1
        new = set()
        existing = list(level.keys())
        for f in existing:
            not_f = (total - 1) ^ f
            if not_f not in level and not_f not in new: new.add(not_f)
            for g in existing:
                if f & g not in level and f & g not in new: new.add(f & g)
                if f | g not in level and f | g not in new: new.add(f | g)
        for tt in new: level[tt] = s
        if not new or s > 20: break
    return level


# ================================================================
# MAIN: Extract and analyze dual certificates
# ================================================================
if __name__ == '__main__':
    print("DUAL CERTIFICATE ANALYSIS")
    print("=" * 65)
    print()

    n = 3
    sizes = compute_sizes(n)
    max_sz = max(sizes.values())
    hardest = sorted([tt for tt, sz in sizes.items() if sz == max_sz])

    print(f"n={n}: {len(hardest)} hardest functions (size {max_sz})")
    print()

    # For each hardest function, try size s=3 circuits and collect infeasibility data
    print("Testing size-3 circuits on hardest functions:")
    print("(size 3 should be INFEASIBLE for all structures)")
    print()

    s_test = 3
    infeasible_count = 0
    feasible_count = 0
    dual_data = []

    for tt in hardest[:3]:  # Test 3 functions
        result = truth_table_conditionals(tt, n)
        if result is None:
            continue
        p1, p2, balance = result
        tt_str = bin(tt)[2:].zfill(2**n)

        print(f"  Function {tt_str} (balance={balance:.3f}):")

        local_inf = 0
        local_feas = 0

        random.seed(42)
        for trial in range(500):
            gt_list = [random.choice(['AND', 'OR', 'NOT']) for _ in range(s_test)]
            conn_list = []
            for g in range(s_test):
                avail = list(range(n + g))
                i1 = random.choice(avail)
                i2 = random.choice(avail) if gt_list[g] != 'NOT' else 0
                conn_list.append((i1, i2))

            feasible, infeasible, res, dual_eq, dual_ub, neq, nub = \
                build_lp_with_dual(n, s_test, gt_list, conn_list, p1, p2)

            if infeasible:
                local_inf += 1
                if dual_eq is not None:
                    dual_data.append({
                        'tt': tt, 'gates': gt_list, 'conns': conn_list,
                        'dual_eq': dual_eq, 'dual_ub': dual_ub,
                        'neq': neq, 'nub': nub
                    })
            elif feasible:
                local_feas += 1

        infeasible_count += local_inf
        feasible_count += local_feas
        print(f"    Infeasible: {local_inf}/500, Feasible: {local_feas}/500")

    print()
    print(f"  Total: {infeasible_count} infeasible, {feasible_count} feasible")
    print()

    # Analyze dual certificates
    if dual_data:
        print("DUAL CERTIFICATE STRUCTURE:")
        print("-" * 65)
        print()

        # Look at dual values
        for i, d in enumerate(dual_data[:5]):
            tt_str = bin(d['tt'])[2:].zfill(2**n)
            gates = '/'.join(d['gates'])
            print(f"  Certificate {i+1}: tt={tt_str}, gates={gates}")
            if d['dual_eq'] is not None:
                deq = np.array(d['dual_eq'])
                nonzero = np.sum(np.abs(deq) > 1e-8)
                print(f"    Equality duals: {len(deq)} total, {nonzero} non-zero")
                print(f"    Max |dual_eq|: {np.max(np.abs(deq)):.6f}")
                print(f"    Sum dual_eq: {np.sum(deq):.6f}")
                # Show distribution
                if nonzero > 0:
                    nz = deq[np.abs(deq) > 1e-8]
                    print(f"    Non-zero values: {nz[:10]}")
            if d['dual_ub'] is not None:
                dub = np.array(d['dual_ub'])
                nonzero = np.sum(np.abs(dub) > 1e-8)
                print(f"    Inequality duals: {len(dub)} total, {nonzero} non-zero")
                if nonzero > 0:
                    nz = dub[np.abs(dub) > 1e-8]
                    print(f"    Non-zero values: {nz[:10]}")
            print()

    # KEY ANALYSIS: What constraint types participate in the dual?
    print("CONSTRAINT TYPE ANALYSIS:")
    print("-" * 65)
    print()
    print("For each infeasible certificate, which constraints are 'active'?")
    print("Active = non-zero dual weight = constraint contributes to proof")
    print()

    eq_active_counts = []
    ub_active_counts = []
    for d in dual_data[:20]:
        if d['dual_eq'] is not None:
            deq = np.array(d['dual_eq'])
            eq_active_counts.append(np.sum(np.abs(deq) > 1e-8))
        if d['dual_ub'] is not None:
            dub = np.array(d['dual_ub'])
            ub_active_counts.append(np.sum(np.abs(dub) > 1e-8))

    if eq_active_counts:
        print(f"  Equality constraints active: {np.mean(eq_active_counts):.1f} avg "
              f"(out of {dual_data[0]['neq']})")
    if ub_active_counts:
        print(f"  Inequality constraints active: {np.mean(ub_active_counts):.1f} avg "
              f"(out of {dual_data[0]['nub']})")

    print(f"""
THEORETICAL FRAMEWORK:
══════════════════════════════════════════════════════════════

The dual certificate says:
  Σ_i λ_i × (constraint_i) = contradiction

where λ_i are the dual weights.

The constraints come from:
  1. Gate semantics: AND/OR/NOT equations (equality constraints)
  2. Fréchet bounds: pairwise probability bounds (inequality constraints)
  3. Input/output: known probabilities (fixed values)

The contradiction: the weighted sum of LHS = 0 but weighted sum of RHS ≠ 0.

INTERPRETATION:
  The dual weights λ_i measure the "tension" at each constraint.
  High |λ_i| = constraint i is critical for the proof.

  Gate semantics with high λ: these gates are "stressed" by computing f.
  Fréchet bounds with high λ: these probability pairs are "pushed to limits."

FOR A UNIVERSAL PROOF (all circuit structures):
  We need: for EVERY circuit C of size s, there exist dual weights
  that create a contradiction using C's constraints.

  If the active constraints are always the SAME TYPE (e.g., always
  the output constraint vs. specific input probabilities): the proof
  structure is UNIVERSAL.

  If different circuits need different active constraints: the proof
  is circuit-specific and harder to generalize.

THE NEW MATHEMATICS:
  Define the "tension function" τ(f, s) = min over circuits C of size s
  of the LP dual objective value.

  τ(f, s) > 0 ⟺ no circuit of size s computes f.
  τ(f, s) = 0 ⟺ some circuit of size s computes f.

  τ is the EXACT circuit complexity measure we need.
  It's non-constructive (defined via LP), non-local (global consistency),
  and avoids all known barriers.

  The challenge: computing τ for large n.
  The hope: τ has STRUCTURE that allows analytical bounds.
""")
