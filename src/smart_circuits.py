"""
SMART CIRCUIT SEARCH: Can clever topologies fool the LP?

We know:
  - Random topologies: LP feasible at s=6 for CLIQUE(4,3) (actual ≈ 11)
  - CLIQUE-specific: LP infeasible at s<11 (exact!)

Question: are there NON-RANDOM, NON-CLIQUE topologies that:
  1. Actually compute CLIQUE (correct on all inputs)
  2. Use fewer gates than the natural circuit
  3. LP says feasible?

If NO smart small circuit passes both (correct AND LP-feasible):
  The LP gap only exists for WRONG circuits (don't compute CLIQUE).
  For CORRECT circuits: LP is always tight. → lower bound proof path!

Strategy: systematically build small circuits and check:
  (a) Do they compute CLIQUE? (evaluate on all inputs)
  (b) Does LP say feasible? (check conditional probability consistency)
"""

import random
import time
from itertools import combinations

def clique_truth_table(N, k):
    n = N * (N - 1) // 2
    edge_idx = {}; idx = 0
    for u in range(N):
        for v in range(u+1, N):
            edge_idx[(u,v)] = idx; idx += 1
    tt = 0
    for x in range(2**n):
        for subset in combinations(range(N), k):
            if all((x >> edge_idx[(min(a,b),max(a,b))]) & 1
                   for a in subset for b in subset if a < b):
                tt |= (1 << x); break
    return tt, n, edge_idx

def eval_circuit(gates, n, x):
    """Evaluate circuit on input x."""
    wv = {}
    for i in range(n):
        wv[i] = (x >> i) & 1
    for gi, (gt, i1, i2) in enumerate(gates):
        v1 = wv[i1]
        v2 = wv.get(i2, 0) if i2 >= 0 else 0
        if gt == 'AND': wv[n+gi] = v1 & v2
        elif gt == 'OR': wv[n+gi] = v1 | v2
        elif gt == 'NOT': wv[n+gi] = 1 - v1
    return wv[n + len(gates) - 1]

def circuit_computes(gates, n, target_tt):
    """Check if circuit computes the target truth table."""
    for x in range(2**n):
        result = eval_circuit(gates, n, x)
        expected = (target_tt >> x) & 1
        if result != expected:
            return False
    return True

def build_smart_circuits(n, s, edge_idx_inv, N, k):
    """Generate 'smart' circuit structures — not random, designed for CLIQUE-like computation."""
    circuits = []

    # Strategy 1: Partial triangle detection
    # AND some edges that form partial cliques, then combine
    edges = list(range(n))

    # Strategy 2: Use NOT gates to detect absence of edges
    # CLIQUE = NOT(for all triples, at least one edge missing)
    # = NOT(AND over triples of (NOT e1 OR NOT e2 OR NOT e3))
    # This uses DeMorgan: NOT e1 OR NOT e2 = NOT(e1 AND e2)

    # Strategy 3: Layered circuits
    # Layer 1: AND pairs of edges
    # Layer 2: combine with more edges
    # Layer 3: OR results

    # Generate many structured candidates
    random.seed(42)

    for trial in range(2000):
        gates = []
        # First layer: AND/OR of input pairs
        n_first = min(s // 2, n)
        for g in range(min(s, n_first)):
            gt = random.choice(['AND', 'OR', 'NOT'])
            avail = list(range(n + g))
            i1 = random.choice(avail)
            i2 = random.choice(avail) if gt != 'NOT' else -1
            gates.append((gt, i1, i2))

        # Remaining: combine previous results
        for g in range(len(gates), s):
            gt = random.choice(['AND', 'OR', 'NOT'])
            # Prefer connecting to recent gates (more structured)
            avail = list(range(n + g))
            # Bias toward gate outputs rather than inputs
            if g > 0 and random.random() < 0.7:
                i1 = n + random.randint(max(0, g-4), g-1)
            else:
                i1 = random.choice(avail)
            if gt != 'NOT':
                if random.random() < 0.5:
                    i2 = random.choice(range(n))  # input
                else:
                    i2 = random.choice(avail)
            else:
                i2 = -1
            gates.append((gt, i1, i2))

        circuits.append(gates)

    # Strategy 4: Specifically designed small circuits
    # For CLIQUE(4,3): try to build compact triangle detectors
    # using shared intermediate computations

    # Shared ANDs: AND of each edge pair sharing a vertex
    # There are 3 edge pairs per vertex × 4 vertices = 12, but many shared
    if s >= 8 and n == 6:
        # 6 edges: e01(0), e02(1), e03(2), e12(3), e13(4), e23(5)
        # Triangles: {0,1,2}: e01∧e02∧e12 = 0∧1∧3
        #            {0,1,3}: e01∧e03∧e13 = 0∧2∧4
        #            {0,2,3}: e02∧e03∧e23 = 1∧2∧5
        #            {1,2,3}: e12∧e13∧e23 = 3∧4∧5

        # Shared: AND(e01,e02)=a, AND(e03,e12)=b, AND(e13,e23)=c
        # t012 = AND(a, e12=3), t013 = AND(e01, AND(e03,e13))...
        # Hard to share much between triangles.

        # Try: compute vertex-star ANDs
        # For vertex 0: e01∧e02, e01∧e03, e02∧e03
        # Some of these are parts of triangles

        for perm in range(100):
            random.seed(perm + 1000)
            gates = []
            # Random permutation of a structured approach
            edge_order = list(range(6))
            random.shuffle(edge_order)

            # Layer 1: AND pairs
            for i in range(min(s//3, 3)):
                e1, e2 = edge_order[2*i], edge_order[2*i+1]
                gates.append(('AND', e1, e2))

            # Layer 2: AND with third edge
            for g in range(len(gates), min(s*2//3, len(gates)+3)):
                avail_gates = list(range(n, n+len(gates)))
                avail_inputs = list(range(n))
                i1 = random.choice(avail_gates) if avail_gates else random.choice(avail_inputs)
                i2 = random.choice(avail_inputs)
                gates.append(('AND', i1, i2))

            # Layer 3: OR everything
            while len(gates) < s - 1:
                avail = list(range(n, n+len(gates)))
                if len(avail) >= 2:
                    i1 = avail[-1]
                    i2 = avail[-2] if len(avail) >= 2 else avail[-1]
                    gates.append(('OR', i1, i2))
                else:
                    gates.append(('OR', random.choice(range(n+len(gates))),
                                 random.choice(range(n+len(gates)))))

            # Ensure correct size
            while len(gates) < s:
                gates.append(('OR', n+len(gates)-1, n+len(gates)-2))
            gates = gates[:s]

            circuits.append(gates)

    return circuits


# ════════════════════════════════════════════════════════════════
print("SMART CIRCUIT SEARCH FOR CLIQUE")
print("═" * 65)
print()

N, k = 4, 3
tt, n, edge_idx = clique_truth_table(N, k)
edge_idx_inv = {v: k_e for k_e, v in edge_idx.items()}

print(f"{k}-CLIQUE on N={N}: n={n}, truth table has {bin(tt).count('1')}/64 ones")
print()

# For each size: generate smart circuits, check correctness
print(f"{'s':>4} {'circuits':>10} {'correct':>8} {'LP_feas':>8} {'both':>8}")
print("-" * 42)

for s in range(6, 14):
    circuits = build_smart_circuits(n, s, edge_idx_inv, N, k)

    n_correct = 0
    n_lp_feas = 0
    n_both = 0

    for gates in circuits:
        if len(gates) != s:
            continue

        is_correct = circuit_computes(gates, n, tt)
        if is_correct:
            n_correct += 1

    print(f"{s:>4} {len(circuits):>10} {n_correct:>8} {'–':>8} {'–':>8}")

print(f"""
INTERPRETATION:
  'correct' = circuit produces exact CLIQUE truth table
  If correct circuits exist at size < 11: the natural circuit is not optimal
  If NO correct circuits at size < 11: 11 is likely optimal

  KEY QUESTION: For correct circuits, does LP always say feasible?
  If yes: LP is sound (never rejects correct circuits)
  If no: LP is too strict (might reject valid circuits)
""")

# For any correct circuits found, verify LP feasibility
print("VERIFYING LP FOR CORRECT CIRCUITS:")
print("-" * 65)

import sys
sys.path.insert(0, 'src')
from tension_clique import compute_conditionals, check_lp_feasibility

result = compute_conditionals(tt, n)
p1, p2, bal = result

for s in range(6, 14):
    circuits = build_smart_circuits(n, s, edge_idx_inv, N, k)
    correct_circuits = []
    for gates in circuits:
        if len(gates) != s: continue
        if circuit_computes(gates, n, tt):
            correct_circuits.append(gates)

    if not correct_circuits:
        print(f"  s={s}: no correct circuits found")
        continue

    # Test LP for correct circuits
    n_lp_ok = 0
    n_lp_fail = 0
    for gates in correct_circuits[:20]:  # test first 20
        gt_list = [g[0] for g in gates]
        conn_list = [(g[1], g[2] if g[2] >= 0 else 0) for g in gates]
        lp_feas = check_lp_feasibility(n, s, gt_list, conn_list, p1, p2)
        if lp_feas:
            n_lp_ok += 1
        else:
            n_lp_fail += 1

    print(f"  s={s}: {len(correct_circuits)} correct circuits, "
          f"LP says {n_lp_ok} feasible / {n_lp_fail} infeasible")
    if n_lp_fail > 0:
        print(f"    WARNING: LP rejects {n_lp_fail} CORRECT circuits! LP is too strict!")
