"""
FRESH START: Building new mathematics from scratch.

Forget all prior approaches. Start from ONE observation and build outward.

THE OBSERVATION (empirically verified across 82 modules):
  When a circuit computes a "hard" function (like CLIQUE),
  fixing a variable determines ~2 gates (cascade).
  When computing an "easy" function, fixing a variable
  determines ~s/n gates (nearly everything).

  The RATIO r = (gates determined per variable) / (total gates / variables)
  measures "how much information one variable carries about the output."

  For easy functions: r ≈ 1 (each variable carries its share).
  For hard functions: r << 1 (each variable is "diluted").

THIS IS THE STARTING POINT. Not circuits, not formulas, not measures.
Just: how does local information (one variable) relate to global computation?

AXIOM 1 (Information Dilution):
  For a function f: {0,1}^n → {0,1} computed by circuit C of size s,
  define the dilution:
    δ(f, C) = (1/n) Σ_i (gates determined by fixing x_i) / s

  δ measures the average fraction of the circuit resolved per variable.
  δ ∈ [0, 1]. δ = 1 means each variable determines everything.

AXIOM 2 (Dilution-Size Tradeoff):
  IF δ(f, C) is small, THEN the circuit must "work harder" somewhere.
  Specifically: the TOTAL information flow through the circuit
  must compensate for the dilution.

  Intuition: if each variable only determines δ fraction of gates,
  then the circuit needs ≈ 1/δ "layers" of processing.
  Each layer can at most double the determined fraction.
  So: depth ≥ log(1/δ). And: s ≥ n × (1/δ).

  For hard functions with δ = O(1/s): s ≥ n × s → contradiction unless...

  Wait. Let me think about this more carefully.

WHAT DO WE ACTUALLY KNOW?
  From our experiments:
  - Fixing 1 variable in CLIQUE circuit: determines ~2 gates out of ~400
  - That's δ ≈ 2/400 = 0.005 per variable
  - n = 45 edges for 10-CLIQUE, s ≈ 400
  - δ × n = 0.005 × 45 = 0.225 (22.5% from all variables individually)
  - But CASCADE gets to 89%! Because gates determine OTHER gates.

  The GAP between 22.5% (sum of individual) and 89% (cascade) is
  the NON-LINEAR AMPLIFICATION from gate-to-gate propagation.

  For easy functions: individual already gets ~100%. No amplification needed.
  For hard functions: individual gets ~20%. Need 4× amplification from cascade.

THIS is the new starting point: the AMPLIFICATION RATIO.

  A(f,C) = cascade_fraction / sum_of_individual_fractions
         = (fraction determined by cascade) / (δ × n)

  For CLIQUE: A ≈ 0.89 / 0.225 ≈ 4.0
  For easy functions: A ≈ 1.0 (no amplification needed)

  A measures how much the circuit relies on INTERNAL AMPLIFICATION
  (gate-to-gate cascading) versus DIRECT INFORMATION from inputs.

HYPOTHESIS: A(f,C) × s relates to function complexity.
  High A → circuit relies on internal amplification → fragile
  Low A → circuit directly channels input information → robust

Let's measure this.
"""

import random
import math
import time

def make_random_circuit(n, s, seed=42):
    """Random circuit: s gates on n variables."""
    random.seed(seed)
    gates = []
    for i in range(s):
        gt = random.choice(['AND', 'OR', 'NOT'])
        available = list(range(n + i))
        i1 = random.choice(available)
        i2 = random.choice(available) if gt != 'NOT' else -1
        gates.append((gt, i1, i2, n + i))
    return gates

def make_clique_circuit(N, k):
    """Circuit for k-CLIQUE on N vertices."""
    n_edges = N * (N-1) // 2
    edge_var = {}
    idx = 0
    for u in range(N):
        for v in range(u+1, N):
            edge_var[(u,v)] = idx
            idx += 1

    gates = []
    nid = n_edges

    # For each k-subset, AND all edges
    from itertools import combinations

    clique_outputs = []
    for subset in combinations(range(N), k):
        edges = []
        for i in range(len(subset)):
            for j in range(i+1, len(subset)):
                u, v = subset[i], subset[j]
                edges.append(edge_var[(u,v)])

        # AND all edges in this clique
        if not edges:
            continue
        cur = edges[0]
        for e in edges[1:]:
            out = nid
            gates.append(('AND', cur, e, out))
            nid += 1
            cur = out
        clique_outputs.append(cur)

    # OR all clique candidates
    if not clique_outputs:
        return gates, n_edges, -1
    cur = clique_outputs[0]
    for c in clique_outputs[1:]:
        out = nid
        gates.append(('OR', cur, c, out))
        nid += 1
        cur = out

    return gates, n_edges, cur

def propagate_count(gates, n, fixed):
    """Count how many gates are determined."""
    wv = dict(fixed)
    det = 0
    for gt, i1, i2, o in gates:
        v1 = wv.get(i1)
        v2 = wv.get(i2) if i2 >= 0 else None
        d = False
        if gt == 'AND':
            if v1 == 0 or v2 == 0: wv[o] = 0; d = True
            elif v1 is not None and v2 is not None: wv[o] = v1 & v2; d = True
        elif gt == 'OR':
            if v1 == 1 or v2 == 1: wv[o] = 1; d = True
            elif v1 is not None and v2 is not None: wv[o] = v1 | v2; d = True
        elif gt == 'NOT':
            if v1 is not None: wv[o] = 1 - v1; d = True
        if d: det += 1
    return det

def measure_dilution_and_amplification(gates, n, trials=20):
    """Measure δ (dilution) and A (amplification ratio)."""
    s = len(gates)
    if s == 0:
        return 0, 0, 0

    total_individual = 0
    total_cascade = 0

    for trial in range(trials):
        random.seed(trial * 137)

        # Random base assignment for non-fixed variables
        base = {i: random.randint(0, 1) for i in range(n)}

        # Measure individual determination per variable
        individual_sum = 0
        for var in range(n):
            # Fix just this one variable
            fixed = {var: base[var]}
            det = propagate_count(gates, n, fixed)
            individual_sum += det

        # Measure cascade: fix n/2 variables
        perm = list(range(n))
        random.shuffle(perm)
        half = n // 2
        fixed_half = {perm[i]: base[perm[i]] for i in range(half)}
        cascade_det = propagate_count(gates, n, fixed_half)

        total_individual += individual_sum / (n * s)  # δ = avg fraction per var
        total_cascade += cascade_det / s               # fraction from cascade

    delta = total_individual / trials
    cascade_frac = total_cascade / trials

    # Amplification ratio
    delta_n = delta * n  # expected from sum of individuals
    A = cascade_frac / delta_n if delta_n > 0.001 else float('inf')

    return delta, cascade_frac, A

print("FRESH START: Information Dilution & Amplification")
print("=" * 65)
print()
print("δ = avg gates determined per variable / total gates")
print("cascade = fraction determined by fixing n/2 variables")
print("A = cascade / (δ × n) = amplification ratio")
print()

# Test on different function types
print(f"{'Function':<25} {'n':>4} {'s':>6} {'δ':>8} {'casc':>8} {'δ×n':>8} {'A':>8}")
print("-" * 70)

# 1. Random circuits
for n in [10, 20, 30]:
    s = 3 * n
    gates = make_random_circuit(n, s)
    d, c, A = measure_dilution_and_amplification(gates, n, trials=10)
    print(f"{'Random(3n)':<25} {n:>4} {s:>6} {d:>8.4f} {c:>8.3f} {d*n:>8.3f} {A:>8.2f}")

# 2. CLIQUE circuits
for N in [6, 7, 8, 9]:
    k = 3
    gates, n, out = make_clique_circuit(N, k)
    if out >= 0 and len(gates) > 0:
        d, c, A = measure_dilution_and_amplification(gates, n, trials=10)
        print(f"{'CLIQUE('+str(N)+','+str(k)+')':<25} {n:>4} {len(gates):>6} {d:>8.4f} {c:>8.3f} {d*n:>8.3f} {A:>8.2f}")

for N in [6, 7, 8]:
    k = 4
    gates, n, out = make_clique_circuit(N, k)
    if out >= 0 and len(gates) > 0 and len(gates) < 5000:
        d, c, A = measure_dilution_and_amplification(gates, n, trials=10)
        print(f"{'CLIQUE('+str(N)+','+str(k)+')':<25} {n:>4} {len(gates):>6} {d:>8.4f} {c:>8.3f} {d*n:>8.3f} {A:>8.2f}")

# 3. Parity (chain of XORs, simulated with AND/OR/NOT)
def make_parity_circuit(n):
    """XOR chain: x1 ⊕ x2 ⊕ ... ⊕ xn using AND/OR/NOT."""
    gates = []
    nid = n
    # XOR(a,b) = OR(AND(a, NOT(b)), AND(NOT(a), b))
    def xor_gate(a, b):
        nonlocal nid
        nb = nid; gates.append(('NOT', b, -1, nb)); nid += 1
        na = nid; gates.append(('NOT', a, -1, na)); nid += 1
        ab = nid; gates.append(('AND', a, nb, ab)); nid += 1
        ba = nid; gates.append(('AND', na, b, ba)); nid += 1
        out = nid; gates.append(('OR', ab, ba, out)); nid += 1
        return out

    cur = 0
    for i in range(1, n):
        cur = xor_gate(cur, i)
    return gates

for n in [10, 20, 30]:
    gates = make_parity_circuit(n)
    d, c, A = measure_dilution_and_amplification(gates, n, trials=10)
    print(f"{'PARITY':<25} {n:>4} {len(gates):>6} {d:>8.4f} {c:>8.3f} {d*n:>8.3f} {A:>8.2f}")

# 4. OR tree (easy function)
def make_or_tree(n):
    gates = []
    nid = n
    layer = list(range(n))
    while len(layer) > 1:
        new_layer = []
        for i in range(0, len(layer)-1, 2):
            out = nid
            gates.append(('OR', layer[i], layer[i+1], out))
            nid += 1
            new_layer.append(out)
        if len(layer) % 2:
            new_layer.append(layer[-1])
        layer = new_layer
    return gates

for n in [10, 20, 30]:
    gates = make_or_tree(n)
    d, c, A = measure_dilution_and_amplification(gates, n, trials=10)
    print(f"{'OR-tree':<25} {n:>4} {len(gates):>6} {d:>8.4f} {c:>8.3f} {d*n:>8.3f} {A:>8.2f}")

# 5. AND tree (easy function)
def make_and_tree(n):
    gates = []
    nid = n
    layer = list(range(n))
    while len(layer) > 1:
        new_layer = []
        for i in range(0, len(layer)-1, 2):
            out = nid
            gates.append(('AND', layer[i], layer[i+1], out))
            nid += 1
            new_layer.append(out)
        if len(layer) % 2:
            new_layer.append(layer[-1])
        layer = new_layer
    return gates

for n in [10, 20, 30]:
    gates = make_and_tree(n)
    d, c, A = measure_dilution_and_amplification(gates, n, trials=10)
    print(f"{'AND-tree':<25} {n:>4} {len(gates):>6} {d:>8.4f} {c:>8.3f} {d*n:>8.3f} {A:>8.2f}")

print()
print("=" * 65)
print()
print("OBSERVATIONS:")
print("  If A >> 1: circuit amplifies internally → fragile to restrictions")
print("  If A ≈ 1: circuit channels inputs directly → robust")
print()
print("NEW DIRECTION: Can we prove A(f,C) ≥ some_bound(f)?")
print("  If hardness forces high A, and high A forces large s...")
print("  Then: hard function → large circuit.")
