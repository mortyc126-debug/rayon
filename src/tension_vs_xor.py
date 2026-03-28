"""
TENSION vs XOR BARRIER: Can the LP handle what constant propagation can't?

Constant propagation fails on XOR: no controlling value.
  AND(a, 0) = 0 ✓ (controlling)
  OR(a, 1) = 1  ✓ (controlling)
  XOR(a, b) = ?  ✗ (need BOTH inputs)

But the LP uses CONDITIONAL PROBABILITIES, not controlling values:
  XOR(a, b) = c: p_c(b) = p_a(b) + p_b(b) - 2×p_{a,b}(b)

This is an EQUALITY constraint — even MORE rigid than AND/OR!

HYPOTHESIS: The LP can reason about XOR-heavy circuits
through pairwise probability constraints, where constant
propagation completely fails.

TEST: Build circuits with XOR gates, measure LP bounds.
Compare to AND/OR-only circuits of same function.
"""

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csc_matrix
import random
import time
from itertools import combinations


def build_truth_table(n, circuit):
    """Evaluate circuit on all inputs, return truth table."""
    tt = 0
    for x in range(2**n):
        wv = {}
        for i in range(n):
            wv[i] = (x >> i) & 1
        for gi, (gt, i1, i2) in enumerate(circuit):
            v1 = wv[i1]
            v2 = wv[i2]
            if gt == 'AND': wv[n+gi] = v1 & v2
            elif gt == 'OR': wv[n+gi] = v1 | v2
            elif gt == 'XOR': wv[n+gi] = v1 ^ v2
            elif gt == 'NOT': wv[n+gi] = 1 - v1
        if circuit:
            if wv[n + len(circuit) - 1]:
                tt |= (1 << x)
    return tt


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


def check_lp_with_xor(n, s, gate_types, connections, p1, p2):
    """
    LP feasibility check supporting AND/OR/XOR/NOT gates.

    XOR(a,b) = c: p_c(b) = p_a(b) + p_b(b) - 2×p_{a,b}(b)
    This is an EQUALITY constraint (very rigid!).
    """
    n_gates = s
    n_pairs = n_gates * (n_gates - 1) // 2
    vars_per_b = n_gates + n_pairs
    total_vars = 2 * vars_per_b

    def mvar(gi, b): return b * vars_per_b + gi
    pair_map = {}
    idx = n_gates
    for i in range(n_gates):
        for j in range(i+1, n_gates):
            pair_map[(i,j)] = idx; idx += 1

    def pvar(gi, gj, b):
        if gi > gj: gi, gj = gj, gi
        if gi == gj: return mvar(gi, b)
        return b * vars_per_b + pair_map[(gi, gj)]

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
        for gi in range(s):
            gt = gate_types[gi]
            i1, i2 = connections[gi]

            if gt == 'NOT':
                if i1 < n:
                    add_eq([(mvar(gi, b), 1.0)], 1.0 - p1.get((i1, b), 0.5))
                else:
                    add_eq([(mvar(gi, b), 1.0), (mvar(i1-n, b), 1.0)], 1.0)

            elif gt == 'AND':
                if i1 < n and i2 < n:
                    add_eq([(mvar(gi, b), 1.0)], p2.get((min(i1,i2), max(i1,i2), b), 0))
                elif i1 >= n and i2 >= n:
                    g1, g2 = i1-n, i2-n
                    if g1 != g2:
                        add_eq([(mvar(gi, b), 1.0), (pvar(g1, g2, b), -1.0)], 0)
                    else:
                        add_eq([(mvar(gi, b), 1.0), (mvar(g1, b), -1.0)], 0)
                else:
                    inp, gate = (i1, i2-n) if i1 < n else (i2, i1-n)
                    ki = p1.get((inp, b), 0.5)
                    add_ub([(mvar(gi, b), 1.0)], ki)
                    add_ub([(mvar(gi, b), 1.0), (mvar(gate, b), -1.0)], 0)
                    add_ub([(mvar(gi, b), -1.0), (mvar(gate, b), 1.0)], 1.0 - ki)

            elif gt == 'OR':
                if i1 < n and i2 < n:
                    k1, k2 = p1.get((i1, b), 0.5), p1.get((i2, b), 0.5)
                    kp = p2.get((min(i1,i2), max(i1,i2), b), 0)
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
                    ki = p1.get((inp, b), 0.5)
                    add_ub([(mvar(gi, b), -1.0)], -ki)
                    add_ub([(mvar(gi, b), -1.0), (mvar(gate, b), 1.0)], 0)
                    add_ub([(mvar(gi, b), 1.0), (mvar(gate, b), -1.0)], ki)

            elif gt == 'XOR':
                # XOR(a,b) = c: p_c = p_a + p_b - 2*p_{a,b}
                # This is an EQUALITY — very rigid!
                if i1 < n and i2 < n:
                    k1 = p1.get((i1, b), 0.5)
                    k2 = p1.get((i2, b), 0.5)
                    kp = p2.get((min(i1,i2), max(i1,i2), b), 0)
                    add_eq([(mvar(gi, b), 1.0)], k1 + k2 - 2*kp)
                elif i1 >= n and i2 >= n:
                    g1, g2 = i1-n, i2-n
                    if g1 != g2:
                        # p_g = p_{g1} + p_{g2} - 2*p_{g1,g2}
                        add_eq([(mvar(gi, b), 1.0), (mvar(g1, b), -1.0),
                                (mvar(g2, b), -1.0), (pvar(g1, g2, b), 2.0)], 0)
                    else:
                        # XOR(g,g) = 0
                        add_eq([(mvar(gi, b), 1.0)], 0)
                else:
                    inp, gate = (i1, i2-n) if i1 < n else (i2, i1-n)
                    ki = p1.get((inp, b), 0.5)
                    # p_g = ki + p_gate - 2*p_{inp,gate}
                    # p_{inp,gate} is unknown but bounded
                    # Fréchet: p_{inp,gate} ∈ [max(0, ki+p_gate-1), min(ki, p_gate)]
                    # So p_g ∈ [ki + p_gate - 2*min(ki,p_gate), ki + p_gate - 2*max(0,ki+p_gate-1)]
                    # = [|ki - p_gate|, min(ki+p_gate, 2-ki-p_gate)]
                    add_ub([(mvar(gi, b), 1.0), (mvar(gate, b), -1.0)], ki)
                    add_ub([(mvar(gi, b), -1.0), (mvar(gate, b), 1.0)], ki)
                    add_ub([(mvar(gi, b), 1.0), (mvar(gate, b), 1.0)], 2.0 - ki)
                    add_ub([(mvar(gi, b), -1.0), (mvar(gate, b), -1.0)], -ki)

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
    A_eq = csc_matrix((eq_v, (eq_r, eq_c)), shape=(eq_cnt[0], nv)) if eq_cnt[0] > 0 else None
    b_eq = np.array(eq_rhs) if eq_cnt[0] > 0 else None
    A_ub = csc_matrix((ub_v, (ub_r, ub_c)), shape=(ub_cnt[0], nv)) if ub_cnt[0] > 0 else None
    b_ub = np.array(ub_rhs) if ub_cnt[0] > 0 else None

    try:
        res = linprog(c_obj, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                      bounds=bounds, method='highs',
                      options={'presolve': True, 'time_limit': 2.0})
        return res.status != 2
    except:
        return False


def test_xor_tension(n, s, p1, p2, n_trials=300, allow_xor=True):
    """Test LP with XOR gates."""
    random.seed(42 + s)
    gate_options = ['AND', 'OR', 'XOR', 'NOT'] if allow_xor else ['AND', 'OR', 'NOT']
    for trial in range(n_trials):
        gt = [random.choice(gate_options) for _ in range(s)]
        cn = []
        for g in range(s):
            avail = list(range(n + g))
            i1 = random.choice(avail)
            i2 = random.choice(avail) if gt[g] != 'NOT' else 0
            cn.append((i1, i2))
        if check_lp_with_xor(n, s, gt, cn, p1, p2):
            return True, trial + 1
    return False, n_trials


# ════════════════════════════════════════════════════════════
print("TENSION vs XOR BARRIER")
print("═" * 65)
print()

# Test 1: XOR-heavy function (parity)
print("TEST 1: PARITY function (pure XOR)")
n = 6
parity_tt = 0
for x in range(2**n):
    if bin(x).count('1') % 2 == 1:
        parity_tt |= (1 << x)

result = compute_conditionals(parity_tt, n)
p1, p2, bal = result
print(f"  Parity({n}): balance={bal:.3f}")
print(f"  {'s':>4} {'no XOR':>10} {'with XOR':>10} {'XOR helps?':>12}")
print(f"  {'-'*38}")

for s in range(1, 12):
    feas_no, _ = test_xor_tension(n, s, p1, p2, n_trials=200, allow_xor=False)
    feas_yes, _ = test_xor_tension(n, s, p1, p2, n_trials=200, allow_xor=True)
    no_s = "feas" if feas_no else "INF"
    yes_s = "feas" if feas_yes else "INF"
    helps = ""
    if not feas_no and feas_yes: helps = "XOR HELPS!"
    if feas_no and not feas_yes: helps = "XOR hurts"
    print(f"  {s:>4} {no_s:>10} {yes_s:>10} {helps:>12}")
    if feas_no and feas_yes:
        break

# Test 2: SHA-256-like function (mixed AND/OR/XOR)
print()
print("TEST 2: SHA-256-like round function")
# Build a simplified SHA-256 round: Ch(e,f,g) + Maj(a,b,c) + XOR mixing
n = 8
# Ch(e,f,g) = (e AND f) XOR (NOT(e) AND g) = e?f:g
# Simplified: AND(e, f) XOR AND(NOT(e), g)
sha_circuit = [
    ('AND', 0, 1),     # g0 = e AND f
    ('NOT', 0, 0),     # g1 = NOT(e)
    ('AND', 9, 2),      # g2 = NOT(e) AND g
    ('XOR', 8, 10),     # g3 = Ch(e,f,g) = g0 XOR g2
    ('AND', 3, 4),      # g4 = a AND b (part of Maj)
    ('AND', 3, 5),      # g5 = a AND c
    ('AND', 4, 5),      # g6 = b AND c
    ('XOR', 12, 13),    # g7 = partial Maj
    ('XOR', 15, 14),    # g8 = Maj(a,b,c)
    ('XOR', 11, 16),    # g9 = Ch XOR Maj
    ('XOR', 17, 6),     # g10 = + W[0] (simplified as XOR)
    ('XOR', 18, 7),     # g11 = + K (simplified as XOR)
]
sha_tt = build_truth_table(n, sha_circuit)
ones = bin(sha_tt).count('1')
print(f"  SHA-round-like({n}): {ones}/{2**n} ones, balance={ones/2**n:.3f}")

result = compute_conditionals(sha_tt, n)
if result:
    p1, p2, bal = result
    print(f"  {'s':>4} {'no XOR':>10} {'with XOR':>10} {'eq constraints':>15}")
    print(f"  {'-'*42}")
    for s in range(1, 15):
        feas_no, _ = test_xor_tension(n, s, p1, p2, n_trials=200, allow_xor=False)
        feas_yes, _ = test_xor_tension(n, s, p1, p2, n_trials=200, allow_xor=True)
        no_s = "feas" if feas_no else "INF"
        yes_s = "feas" if feas_yes else "INF"
        marker = ""
        if not feas_no and feas_yes: marker = "XOR BREAKS BARRIER!"
        if feas_no and not feas_yes: marker = "XOR tighter"
        print(f"  {s:>4} {no_s:>10} {yes_s:>10} {marker:>15}")
        if feas_no and feas_yes:
            break

print(f"""
═══════════════════════════════════════════════════════════════
RESULTS:

If XOR-LP gives TIGHTER bounds than AND/OR-LP:
  → XOR equality constraints ADD information to the LP
  → The LP can reason about XOR where const-prop fails
  → Tension can analyze SHA-256 circuits!

If XOR-LP gives SAME bounds:
  → XOR constraints are redundant with Fréchet bounds
  → No advantage over const-prop for XOR circuits

If XOR-LP gives LOOSER bounds:
  → XOR circuits are inherently harder to analyze
  → Need different approach for SHA-256
═══════════════════════════════════════════════════════════════
""")
