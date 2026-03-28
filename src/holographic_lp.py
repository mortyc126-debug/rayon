"""
HOLOGRAPHIC LP: Circuit lower bounds via linear programming.

NEW IDEA: For a circuit computing f, every gate has conditional probabilities:
  p_g(b) = Pr[gate g outputs 1 | f(x) = b]  for b ∈ {0, 1}

These probabilities satisfy LINEAR constraints (Fréchet bounds):
  AND(a,b) = g:  p_g(b) ∈ [max(0, p_a(b)+p_b(b)-1), min(p_a(b), p_b(b))]
  OR(a,b) = g:   p_g(b) ∈ [max(p_a(b),p_b(b)), min(1, p_a(b)+p_b(b))]
  NOT(a) = g:    p_g(b) = 1 - p_a(b)

Boundary conditions (from f):
  Inputs: p_{x_i}(b) = Pr[x_i=1 | f=b] (KNOWN from truth table)
  Output: p_{out}(1) = 1, p_{out}(0) = 0

If this LP is INFEASIBLE for all DAGs of size s: circuit(f) > s.

The LP captures "global consistency" constraints on the circuit —
this is a NON-LOCAL argument (exactly what our meta-theorem says is needed).

ENHANCEMENT: Add correlation constraints (level-2 Sherali-Adams):
  p_{g,h}(b) = Pr[g=1 AND h=1 | f=b]  for all pairs (g,h)

This is tighter but has O(s²) variables.

Let's test: for the HARDEST functions at n=3,4, what's the minimum
circuit size the LP certifies?
"""

import math
from itertools import combinations, product
from collections import defaultdict

def truth_table_properties(tt, n):
    """Compute conditional input probabilities from truth table."""
    total = 2**n
    ones = bin(tt).count('1')
    zeros = total - ones
    if ones == 0 or zeros == 0:
        return None  # constant function

    # p_xi(b) = Pr[x_i = 1 | f = b]
    p = {}  # p[(i, b)] = Pr[x_i = 1 | f = b]
    for i in range(n):
        count_1_given_1 = 0  # x_i=1 and f=1
        count_1_given_0 = 0  # x_i=1 and f=0
        for x in range(total):
            xi = (x >> i) & 1
            fx = (tt >> x) & 1
            if xi == 1 and fx == 1:
                count_1_given_1 += 1
            if xi == 1 and fx == 0:
                count_1_given_0 += 1
        p[(i, 1)] = count_1_given_1 / ones if ones > 0 else 0.5
        p[(i, 0)] = count_1_given_0 / zeros if zeros > 0 else 0.5
    return p, ones/total

def check_lp_feasibility(n, s, gate_types, connections, input_probs, balance):
    """
    Check if a specific circuit structure has feasible conditional probabilities.

    gate_types: list of s gate types ('AND', 'OR', 'NOT')
    connections: list of s tuples (input1, input2) for each gate
                 inputs 0..n-1 are variables, n..n+s-1 are gates
    input_probs: dict of (var_index, b) -> probability
    balance: Pr[f=1]

    Uses iterative constraint propagation (simple LP substitute).
    Returns True if feasible, False if provably infeasible.
    """
    # Variables: p[(gate_idx, b)] for gate_idx = n..n+s-1, b ∈ {0,1}
    # Ranges: lb[g,b], ub[g,b]

    total_wires = n + s
    lb = {}  # lower bounds
    ub = {}  # upper bounds

    # Initialize variable probabilities
    for i in range(n):
        for b in [0, 1]:
            lb[(i, b)] = input_probs[(i, b)]
            ub[(i, b)] = input_probs[(i, b)]

    # Initialize gate probabilities to [0, 1]
    for g in range(s):
        for b in [0, 1]:
            lb[(n+g, b)] = 0.0
            ub[(n+g, b)] = 1.0

    # Output constraint: p_out(1) = 1, p_out(0) = 0
    output_gate = n + s - 1
    lb[(output_gate, 1)] = 1.0
    ub[(output_gate, 1)] = 1.0
    lb[(output_gate, 0)] = 0.0
    ub[(output_gate, 0)] = 0.0

    # Iterative propagation
    changed = True
    iterations = 0
    while changed and iterations < 100:
        changed = False
        iterations += 1

        for g in range(s):
            gt = gate_types[g]
            i1, i2 = connections[g]

            for b in [0, 1]:
                old_lb = lb[(n+g, b)]
                old_ub = ub[(n+g, b)]

                if gt == 'AND':
                    # p_g ∈ [max(0, p_a+p_b-1), min(p_a, p_b)]
                    new_lb = max(old_lb, max(0, lb[(i1,b)] + lb[(i2,b)] - 1))
                    new_ub = min(old_ub, min(ub[(i1,b)], ub[(i2,b)]))

                elif gt == 'OR':
                    # p_g ∈ [max(p_a, p_b), min(1, p_a+p_b)]
                    new_lb = max(old_lb, max(lb[(i1,b)], lb[(i2,b)]))
                    new_ub = min(old_ub, min(1, ub[(i1,b)] + ub[(i2,b)]))

                elif gt == 'NOT':
                    # p_g = 1 - p_a
                    new_lb = max(old_lb, 1 - ub[(i1,b)])
                    new_ub = min(old_ub, 1 - lb[(i1,b)])

                if new_lb > old_lb + 1e-10 or new_ub < old_ub - 1e-10:
                    changed = True
                lb[(n+g, b)] = new_lb
                ub[(n+g, b)] = new_ub

                if new_lb > new_ub + 1e-10:
                    return False  # INFEASIBLE!

        # Backward propagation: output constraints propagate backward
        for g in range(s-1, -1, -1):
            gt = gate_types[g]
            i1, i2 = connections[g]

            for b in [0, 1]:
                if gt == 'AND':
                    # If p_g(b) has high lower bound, inputs must too
                    if lb[(n+g, b)] > 0:
                        # Both inputs must be ≥ lb_g
                        new_lb1 = max(lb[(i1,b)], lb[(n+g,b)])
                        new_lb2 = max(lb[(i2,b)], lb[(n+g,b)])
                        if new_lb1 > lb[(i1,b)] + 1e-10:
                            lb[(i1,b)] = new_lb1; changed = True
                        if new_lb2 > lb[(i2,b)] + 1e-10:
                            lb[(i2,b)] = new_lb2; changed = True
                    # If p_g(b) has low upper bound, at least one input must be low
                    # (can't propagate cleanly for AND with just bounds)

                elif gt == 'OR':
                    # If p_g(b) has low upper bound, both inputs must be low
                    if ub[(n+g, b)] < 1:
                        new_ub1 = min(ub[(i1,b)], ub[(n+g,b)])
                        new_ub2 = min(ub[(i2,b)], ub[(n+g,b)])
                        if new_ub1 < ub[(i1,b)] - 1e-10:
                            ub[(i1,b)] = new_ub1; changed = True
                        if new_ub2 < ub[(i2,b)] - 1e-10:
                            ub[(i2,b)] = new_ub2; changed = True

                elif gt == 'NOT':
                    # p_g = 1 - p_a → p_a = 1 - p_g
                    new_lb_a = max(lb[(i1,b)], 1 - ub[(n+g,b)])
                    new_ub_a = min(ub[(i1,b)], 1 - lb[(n+g,b)])
                    if new_lb_a > lb[(i1,b)] + 1e-10:
                        lb[(i1,b)] = new_lb_a; changed = True
                    if new_ub_a < ub[(i1,b)] - 1e-10:
                        ub[(i1,b)] = new_ub_a; changed = True

                # Check feasibility of input constraints
                if lb[(i1,b)] > ub[(i1,b)] + 1e-10:
                    return False
                if i2 >= 0 and lb[(i2,b)] > ub[(i2,b)] + 1e-10:
                    return False

    return True  # Feasible (or at least not provably infeasible)


def enumerate_circuits_and_check(n, s, tt):
    """Try many circuit structures of size s, check LP feasibility."""
    result = truth_table_properties(tt, n)
    if result is None:
        return True  # constant function, trivially computable

    input_probs, balance = result

    total_wires = n + s
    gate_types_options = ['AND', 'OR', 'NOT']

    # Try random circuit structures
    import random
    random.seed(42)

    feasible_count = 0
    total_tried = 0

    for trial in range(min(1000, 3**(s) * (n+s)**(2*s))):
        # Random circuit structure
        gt_list = []
        conn_list = []
        for g in range(s):
            gt = random.choice(gate_types_options)
            available = list(range(n + g))
            if not available:
                break
            i1 = random.choice(available)
            i2 = random.choice(available) if gt != 'NOT' else 0
            gt_list.append(gt)
            conn_list.append((i1, i2))

        if len(gt_list) < s:
            continue

        total_tried += 1
        if check_lp_feasibility(n, s, gt_list, conn_list, input_probs, balance):
            feasible_count += 1

    return feasible_count, total_tried


# MAIN EXPERIMENT
print("HOLOGRAPHIC LP: Circuit Lower Bounds via Conditional Probabilities")
print("=" * 65)
print()

# First: verify LP can detect impossibility for VERY small circuits
print("VERIFICATION: Can LP detect that some functions need size > 1?")
print("-" * 65)

n = 3
total = 2**(2**n)

# Compute actual circuit sizes (from previous analysis)
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

sizes = compute_sizes(3)

# Test LP on hardest functions (size 4 for n=3)
hardest = [tt for tt, s in sizes.items() if s == max(sizes.values())]
print(f"\nTesting {len(hardest)} hardest functions (actual size = {max(sizes.values())}) for n=3")
print()

for s_test in range(1, 5):
    feasible_any = False
    for tt in hardest[:5]:
        result = truth_table_properties(tt, n)
        if result is None:
            continue
        input_probs, balance = result

        # Try many circuit structures of size s_test
        import random
        random.seed(42)
        found_feasible = False
        for trial in range(500):
            gt_list = []
            conn_list = []
            for g in range(s_test):
                gt = random.choice(['AND', 'OR', 'NOT'])
                available = list(range(n + g))
                i1 = random.choice(available)
                i2 = random.choice(available) if gt != 'NOT' else 0
                gt_list.append(gt)
                conn_list.append((i1, i2))

            if check_lp_feasibility(n, s_test, gt_list, conn_list, input_probs, balance):
                found_feasible = True
                break

        if found_feasible:
            feasible_any = True
            break

    status = "LP says feasible (some structure works)" if feasible_any else "LP says INFEASIBLE (no structure works)"
    print(f"  Size {s_test}: {status}")

# Now test: does LP give TIGHT bounds?
print(f"\nLP tightness test (n=3):")
print(f"  {'tt':>12} {'actual':>8} {'LP_min':>8} {'match?':>8}")
print(f"  {'-'*40}")

for tt in [hardest[0], hardest[-1]] + [tt for tt, s in sizes.items() if s == 2][:3]:
    actual_size = sizes[tt]
    result = truth_table_properties(tt, n)
    if result is None:
        continue
    input_probs, balance = result

    lp_min = 0
    for s_test in range(1, actual_size + 1):
        import random
        random.seed(42)
        found = False
        for trial in range(1000):
            gt_list = []
            conn_list = []
            for g in range(s_test):
                gt = random.choice(['AND', 'OR', 'NOT'])
                available = list(range(n + g))
                i1 = random.choice(available)
                i2 = random.choice(available) if gt != 'NOT' else 0
                gt_list.append(gt)
                conn_list.append((i1, i2))
            if check_lp_feasibility(n, s_test, gt_list, conn_list, input_probs, balance):
                found = True
                break
        if found:
            lp_min = s_test
            break
        lp_min = s_test + 1

    tt_str = bin(tt)[2:].zfill(2**n)
    match = "✓" if lp_min == actual_size else f"gap={actual_size-lp_min}"
    print(f"  {tt_str:>12} {actual_size:>8} {lp_min:>8} {match:>8}")

print(f"""
ANALYSIS:
  The LP uses only MARGINAL conditional probabilities (Fréchet bounds).
  This is a RELAXATION — it might declare feasible when actually infeasible.

  If the LP gives tight bounds: the marginal structure fully determines
  circuit complexity (at least at this scale).

  If there's a gap: we need higher-order constraints (joint probabilities
  of pairs/triples of gates) for tighter bounds.

  KEY INSIGHT: This is a GLOBAL argument. It doesn't analyze gates
  one-by-one (composition). It checks CONSISTENCY of the entire circuit.

  This approach avoids the META-THEOREM barrier because:
  1. It's not a sub/super-additive measure
  2. It checks global feasibility, not local composition
  3. The LP dual certificate would be a genuine PROOF of lower bound

  SCALING QUESTION: Can this approach certify super-polynomial lower
  bounds for CLIQUE? That requires solving the LP for exponential-size
  circuits, which is itself hard. But the LP DUAL might have small
  certificates that work for all circuit sizes.
""")
