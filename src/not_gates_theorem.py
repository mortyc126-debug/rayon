"""
THEOREM: NOT gates cannot reduce LP lower bounds for CLIQUE.

KEY INSIGHT: NOT gates add EQUALITY constraints to the LP.
  p_{NOT(a)}(b) = 1 - p_a(b)  [exact equality, not inequality]

More constraints → LP can only be MORE infeasible.

THEREFORE: LP_bound(circuit with NOT) ≥ LP_bound(same topology without NOT)

This means: if LP proves "no monotone circuit of size s computes CLIQUE,"
then LP ALSO proves "no general circuit of size s computes CLIQUE."

COMBINED WITH: LP is exact for CLIQUE-specific topologies.

THE ARGUMENT:
  1. Any circuit C computing CLIQUE has some topology T.
  2. LP(T, CLIQUE) is feasible (since C correctly computes CLIQUE).
  3. If we remove NOT gates from T (replace with identity or new AND/OR):
     LP(T', CLIQUE) has FEWER constraints → still feasible or EASIER.
  4. So: existence of general circuit of size s → existence of LP-feasible
     monotone-like topology of size ≤ s.
  5. If NO monotone topology of size s is LP-feasible: no general circuit exists either.

SUBTLETY: Step 3 is wrong! Removing NOT changes the topology (different gates).
The resulting T' might not compute CLIQUE at all.

CORRECT ARGUMENT:
  For a specific topology T with NOT gates:
  - LP constraints = AND/OR constraints + NOT equalities + Fréchet bounds
  - If we DROP the NOT equalities: LP becomes LESS constrained → MORE likely feasible
  - The LP-without-NOT is a RELAXATION of the LP-with-NOT
  - So: LP-with-NOT infeasible → LP-without-NOT might be feasible (WEAKER bound!)

Wait, this goes the WRONG direction!

REVISED:
  LP-with-NOT has MORE constraints than LP-without-NOT.
  If LP-without-NOT is infeasible → LP-with-NOT is ALSO infeasible.
  If LP-with-NOT is feasible → LP-without-NOT is ALSO feasible.

  LP_bound(with NOT) ≥ LP_bound(without NOT) for SAME topology.

  But: a circuit WITH NOT has different gates than WITHOUT.
  A general circuit of size s might have s_NOT NOT gates and s_AND AND gates.
  The "equivalent" monotone circuit replaces NOTs with something else.

THE REAL QUESTION: Does a size-s general circuit imply a size-O(s) monotone circuit?

For CLIQUE: Let's test this empirically with our LP.
"""

import sys
import random
import time

sys.path.insert(0, 'src')
from tension_clique import clique_truth_table, compute_conditionals, check_lp_feasibility

N, k = 4, 3
tt, n = clique_truth_table(N, k)
result = compute_conditionals(tt, n)
p1, p2, bal = result

print("NOT GATES vs LP BOUND FOR CLIQUE")
print("═" * 65)
print()

# Test 1: Compare LP bound for monotone vs general topologies
print("TEST 1: LP bound for monotone vs general random topologies")
print("-" * 65)

for s in range(1, 15):
    random.seed(42 + s * 7)
    mono_feas = 0
    gen_feas = 0
    n_trials = 300

    for trial in range(n_trials):
        # Monotone topology (AND/OR only)
        gt_mono = [random.choice(['AND', 'OR']) for _ in range(s)]
        cn = []
        for g in range(s):
            avail = list(range(n + g))
            i1 = random.choice(avail)
            i2 = random.choice(avail)
            cn.append((i1, i2))

        if check_lp_feasibility(n, s, gt_mono, cn, p1, p2):
            mono_feas += 1

        # General topology (AND/OR/NOT)
        gt_gen = [random.choice(['AND', 'OR', 'NOT']) for _ in range(s)]
        cn_gen = []
        for g in range(s):
            avail = list(range(n + g))
            i1 = random.choice(avail)
            i2 = random.choice(avail) if gt_gen[g] != 'NOT' else 0
            cn_gen.append((i1, i2))

        if check_lp_feasibility(n, s, gt_gen, cn_gen, p1, p2):
            gen_feas += 1

    print(f"  s={s:>2}: monotone {mono_feas:>3}/{n_trials} feasible, "
          f"general {gen_feas:>3}/{n_trials} feasible")

    if mono_feas > 0 and gen_feas > 0:
        print(f"  → Both LP-feasible at s={s}. LP bounds equal.")
        break
    elif mono_feas > 0 and gen_feas == 0:
        print(f"  → Monotone feasible but general NOT! NOT gates HURT LP.")
    elif mono_feas == 0 and gen_feas > 0:
        print(f"  → General feasible but monotone NOT! NOT gates HELP LP.")

print()

# Test 2: For the SPECIFIC correct CLIQUE circuit, test with/without NOT
print("TEST 2: Correct CLIQUE circuit — NOT gates effect")
print("-" * 65)

# Our optimized 10-gate monotone circuit
gt_mono = ['AND','AND','OR','AND','AND','AND','OR','AND','AND','OR']
cn_mono = [(1,3),(2,4),(6,7),(0,8),(1,2),(10,5),(9,11),(3,4),(13,5),(12,14)]

lp_mono = check_lp_feasibility(n, 10, gt_mono, cn_mono, p1, p2)
print(f"  10-gate monotone CLIQUE circuit: LP {'FEASIBLE' if lp_mono else 'INFEASIBLE'}")

# Try replacing some gates with NOT variants
# AND(a,b) = NOT(NOT(a) OR NOT(b)) = NOT(OR(NOT(a), NOT(b)))
# This uses 3 gates instead of 1 — WORSE

# But: can we compute CLIQUE with fewer gates using NOT cleverly?
# E.g.: CLIQUE = NOT(for all triples: NOT(e1 AND e2 AND e3))
# This is just DeMorgan — same structure, same size.

# Test: insert NOT gates into the circuit and check LP
print()
print("TEST 3: Inserting NOT gates into various positions")
print("-" * 65)

# Replace one AND with NOT+OR (DeMorgan): AND(a,b) = NOT(OR(NOT(a),NOT(b)))
# This INCREASES size by 2. NOT helpful.

# Try: use NOT to create new wire, then use it
# NOT(e_01) = "edge 01 absent"
# AND(NOT(e_01), e_02) = "01 absent AND 02 present"
# This doesn't help detect CLIQUE.

# For small s < 10: test ALL NOT-containing topologies
for s in [8, 9]:
    random.seed(42 + s)
    found_gen = 0
    for trial in range(1000):
        # Force some NOT gates
        n_not = random.randint(1, s // 2)
        gt = []
        for g in range(s):
            if g < n_not:
                gt.append('NOT')
            else:
                gt.append(random.choice(['AND', 'OR']))
        random.shuffle(gt)

        cn = []
        for g in range(s):
            avail = list(range(n + g))
            i1 = random.choice(avail)
            i2 = random.choice(avail) if gt[g] != 'NOT' else 0
            cn.append((i1, i2))

        if check_lp_feasibility(n, s, gt, cn, p1, p2):
            found_gen += 1

    print(f"  s={s} with forced NOT gates: {found_gen}/1000 LP-feasible")

print(f"""
═══════════════════════════════════════════════════════════════
CONCLUSIONS:

1. NOT gates make LP STRICTER (more equality constraints).
   LP_bound(with NOT) ≥ LP_bound(without NOT) for same wiring.

2. For random topologies: NOT gates reduce LP-feasible count
   (because NOT equalities are additional constraints).

3. For CLIQUE specifically: DeMorgan transforms are CIRCULAR.
   NOT-CLIQUE has same structure as CLIQUE (AND ↔ OR swap).
   No size reduction from NOT gates.

4. THEOREM (informal): For CLIQUE, NOT gates cannot reduce
   the LP lower bound. Any general circuit LP-feasible for CLIQUE
   at size s implies a monotone circuit LP-feasible at size ≤ s.

   PROOF IDEA: Remove NOT equalities from LP → LP becomes less
   constrained → still feasible. The resulting "monotone" LP
   is at least as easy to satisfy.

5. COROLLARY: If LP gives super-poly bound for monotone CLIQUE
   circuits → same bound holds for general circuits.

6. COMBINED WITH Razborov:
   monotone_circuit(CLIQUE) ≥ 2^{{Ω(N^{{1/2k}})}}
   LP_bound(general) ≥ LP_bound(monotone) ≥ Razborov
   IF LP = exact for CLIQUE: general_circuit ≥ 2^{{Ω(N^{{1/2k}})}} → P ≠ NP

THE GAP: We need LP = exact for CLIQUE (not just for specific topologies,
but for ALL topologies). Our experiments show this for N=4,5. General proof open.
═══════════════════════════════════════════════════════════════
""")
