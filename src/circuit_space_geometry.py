"""
FRESH START: Circuit Space Geometry.

New mathematics. Start from the simplest possible question:

  How does the SET of computable functions grow as circuit size increases?

  Φ: Circuit_{s,n} → Bool_n maps circuits to the functions they compute.
  SIZE(s) = Image(Φ) = functions computable by size s.

  |SIZE(0)| = 2n + 2 (just variables, their negations, and constants)
  |SIZE(s)| grows with s until it reaches |Bool_n| = 2^{2^n}.

  THE GROWTH CURVE of |SIZE(s)| vs s encodes ALL of circuit complexity.

  If |SIZE(s)| grows slowly: many hard functions.
  If |SIZE(s)| grows fast: few hard functions.

For small n: we can ENUMERATE and measure exactly.

NEW CONCEPT: "Circuit Frontier" = functions first achievable at size exactly s.
  Frontier(s) = SIZE(s) \ SIZE(s-1).

ANOTHER NEW CONCEPT: "Redundancy" = how many circuits compute the same function.
  R(f, s) = |{C ∈ Circuit_{s,n} : f_C = f}| / |Circuit_{s,n}|.

  Easy functions: high redundancy (many circuits compute them).
  Hard functions: low redundancy (few circuits, if any, compute them).

  If R(CLIQUE, s) = 0 for s = poly(n): CLIQUE ∉ SIZE(poly) → P ≠ NP.

Let's compute these for small n and look for patterns.
"""

import itertools
import random
from collections import defaultdict, Counter

def enumerate_functions(n):
    """All Boolean functions on n variables as truth tables."""
    return range(2**(2**n))

def eval_truth_table(n, gates):
    """Evaluate circuit on all inputs, return truth table as integer."""
    tt = 0
    for x in range(2**n):
        # Set input values
        wv = {}
        for i in range(n):
            wv[i] = (x >> i) & 1

        # Evaluate gates
        for gt, i1, i2, o in gates:
            v1 = wv.get(i1, 0)
            v2 = wv.get(i2, 0) if i2 >= 0 else 0
            if gt == 'AND':
                wv[o] = v1 & v2
            elif gt == 'OR':
                wv[o] = v1 | v2
            elif gt == 'NOT':
                wv[o] = 1 - v1

        # Output = last gate
        if gates:
            out = wv[gates[-1][3]]
        else:
            out = wv.get(0, 0)
        tt |= (out << x)
    return tt

def count_computable(n, max_s):
    """Count distinct functions computable by circuits of size 0..max_s."""
    total_funcs = 2**(2**n)

    # Size 0: just projections and constants
    size0 = set()
    # Constants
    size0.add(0)  # constant 0
    size0.add(total_funcs - 1)  # constant 1
    # Projections and their negations
    for i in range(n):
        tt = 0
        for x in range(2**n):
            if (x >> i) & 1:
                tt |= (1 << x)
        size0.add(tt)
        size0.add((total_funcs - 1) ^ tt)  # negation

    results = {0: len(size0)}
    computable = set(size0)

    # For each additional gate
    for s in range(1, max_s + 1):
        new_funcs = set()
        # Available wires: n inputs + (s-1) previous gate outputs
        # Add one gate with inputs from available wires

        # For gate s: inputs can be any of n + s - 1 wires
        # But we build incrementally: for each existing circuit of size s-1,
        # add one gate.

        # OPTIMIZATION: instead of full enumeration, use random sampling
        # + exact for small cases

        # For tiny n: exact enumeration is feasible
        if n <= 3 and s <= 4:
            # Enumerate all possible single-gate additions
            # Available inputs for new gate: 0..n-1 (vars) and n..n+s-2 (prev gates)
            n_wires = n + s - 1 if s > 1 else n
            gate_id = n + s - 1

            # We need to track ALL circuits of size s, not just add to previous
            # Let's do it differently: enumerate all circuits of size exactly s

    # Actually, let's enumerate differently.
    # For small n, enumerate ALL circuits up to size max_s and collect truth tables.

    if n <= 3:
        computable = set()
        # Constants and projections
        total_funcs = 2**(2**n)
        computable.add(0)
        computable.add(total_funcs - 1)
        for i in range(n):
            tt = 0
            for x in range(2**n):
                if (x >> i) & 1:
                    tt |= (1 << x)
            computable.add(tt)
            computable.add((total_funcs - 1) ^ tt)

        results = {0: len(computable)}

        # Enumerate circuits by size
        for s in range(1, max_s + 1):
            new_computable = set(computable)

            # For each existing truth table pair, try combining with a gate
            # This is equivalent to: f AND g, f OR g, NOT f for all known f, g
            existing_tts = list(computable)
            for f_tt in existing_tts:
                # NOT
                new_computable.add((total_funcs - 1) ^ f_tt)
                for g_tt in existing_tts:
                    # AND
                    new_computable.add(f_tt & g_tt)
                    # OR
                    new_computable.add(f_tt | g_tt)

            computable = new_computable
            results[s] = len(computable)

            if len(computable) == total_funcs:
                # All functions reached
                for s2 in range(s+1, max_s+1):
                    results[s2] = total_funcs
                break

        return results, total_funcs

    return results, total_funcs


def analyze_function_properties(n):
    """For each function on n variables, compute properties."""
    total = 2**(2**n)
    properties = {}

    for tt in range(total):
        # Sensitivity
        sens = 0
        for x in range(2**n):
            fx = (tt >> x) & 1
            for i in range(n):
                y = x ^ (1 << i)
                fy = (tt >> y) & 1
                if fx != fy:
                    sens += 1
        avg_sens = sens / (2**n)

        # Balance
        ones = bin(tt).count('1')
        balance = ones / (2**n)

        properties[tt] = {
            'sensitivity': avg_sens,
            'balance': balance,
            'ones': ones,
        }

    return properties


print("CIRCUIT SPACE GEOMETRY")
print("=" * 65)
print()

for n in [2, 3, 4]:
    total = 2**(2**n)
    print(f"n = {n}: {total} total Boolean functions")

    if n <= 3:
        max_s = 8 if n <= 3 else 5
        results, total_funcs = count_computable(n, max_s)

        print(f"  {'size s':>8} {'|SIZE(s)|':>12} {'fraction':>10} {'frontier':>10}")
        print(f"  {'-'*45}")
        prev = 0
        for s in sorted(results.keys()):
            frac = results[s] / total_funcs
            frontier = results[s] - prev
            print(f"  {s:>8} {results[s]:>12} {frac:>10.4f} {frontier:>10}")
            prev = results[s]
    print()

# Deeper analysis for n=3
print("DETAILED ANALYSIS for n=3 (256 functions)")
print("=" * 65)
print()

n = 3
total = 256
props = analyze_function_properties(n)
results, _ = count_computable(n, 8)

# Which functions appear at each level?
# We can determine this by tracking which truth tables first appear
computable_at = {}
seen = set()

# Size 0
cur = set()
cur.add(0); cur.add(255)
for i in range(n):
    tt = 0
    for x in range(2**n):
        if (x >> i) & 1: tt |= (1 << x)
    cur.add(tt); cur.add(255 ^ tt)

for tt in cur:
    computable_at[tt] = 0
seen = set(cur)

for s in range(1, 8):
    new = set(seen)
    existing = list(seen)
    for f in existing:
        new.add(255 ^ f)
        for g in existing:
            new.add(f & g)
            new.add(f | g)
    frontier = new - seen
    for tt in frontier:
        computable_at[tt] = s
    seen = new
    if len(seen) == 256:
        break

# Analyze frontier functions
print("Functions by first-achievable circuit size:")
by_size = defaultdict(list)
for tt, s in computable_at.items():
    by_size[s].append(tt)

for s in sorted(by_size.keys()):
    funcs = by_size[s]
    sensitivities = [props[tt]['sensitivity'] for tt in funcs]
    balances = [props[tt]['balance'] for tt in funcs]
    avg_s = sum(sensitivities) / len(sensitivities)
    avg_b = sum(balances) / len(balances)
    print(f"  Size {s}: {len(funcs):>4} functions, "
          f"avg sensitivity={avg_s:.2f}, avg balance={avg_b:.3f}")

# Check remaining (not computed in 7 gates)
remaining = [tt for tt in range(256) if tt not in computable_at]
if remaining:
    sensitivities = [props[tt]['sensitivity'] for tt in remaining]
    balances = [props[tt]['balance'] for tt in remaining]
    avg_s = sum(sensitivities) / len(sensitivities)
    avg_b = sum(balances) / len(balances)
    print(f"  Size >7: {len(remaining):>4} functions, "
          f"avg sensitivity={avg_s:.2f}, avg balance={avg_b:.3f}")

print()

# Key question: do "harder" functions (higher circuit size) have specific properties?
print("PROPERTY DISTRIBUTION BY CIRCUIT SIZE:")
print(f"  {'size':>4} {'count':>6} {'avg sens':>10} {'avg balance':>12} {'sens range':>14}")
print(f"  {'-'*50}")
for s in sorted(by_size.keys()):
    funcs = by_size[s]
    sensitivities = [props[tt]['sensitivity'] for tt in funcs]
    balances = [props[tt]['balance'] for tt in funcs]
    if sensitivities:
        print(f"  {s:>4} {len(funcs):>6} {sum(sensitivities)/len(sensitivities):>10.3f} "
              f"{sum(balances)/len(balances):>12.3f} "
              f"[{min(sensitivities):.1f}-{max(sensitivities):.1f}]")

print(f"""
OBSERVATIONS:
  - Functions achievable at size 0: projections, constants (low sensitivity)
  - Functions at size 1: simple gates (AND, OR of pairs)
  - Higher sizes: more complex functions

KEY QUESTION: What property of "hard" functions (high circuit size)
  distinguishes them from "easy" functions?

  Is it sensitivity? Balance? Or something else entirely?
""")

# NEW MEASURE: "Interaction complexity"
# How much do pairs of variables interact in determining f?
print("NEW MEASURE: Pairwise Interaction Complexity")
print("=" * 65)
print()

def interaction_matrix(tt, n):
    """Measure pairwise interaction between variables."""
    total = 2**n
    matrix = [[0.0]*n for _ in range(n)]
    for i in range(n):
        for j in range(i+1, n):
            # Count inputs where flipping both i,j changes f differently
            # than flipping i and j independently
            interact = 0
            for x in range(total):
                fx = (tt >> x) & 1
                fi = (tt >> (x ^ (1 << i))) & 1
                fj = (tt >> (x ^ (1 << j))) & 1
                fij = (tt >> (x ^ (1 << i) ^ (1 << j))) & 1
                # XOR interaction: does flipping both differ from sum of individual flips?
                if (fx ^ fij) != ((fx ^ fi) ^ (fx ^ fj)):
                    interact += 1
            matrix[i][j] = interact / total
            matrix[j][i] = matrix[i][j]
    return matrix

def total_interaction(tt, n):
    """Sum of all pairwise interactions."""
    mat = interaction_matrix(tt, n)
    return sum(mat[i][j] for i in range(n) for j in range(i+1, n))

print(f"For n=3: measuring total pairwise interaction I₂(f)")
print(f"  {'size':>4} {'count':>6} {'avg I₂':>10} {'I₂ range':>16}")
print(f"  {'-'*40}")

for s in sorted(by_size.keys()):
    funcs = by_size[s]
    interactions = [total_interaction(tt, n) for tt in funcs]
    if interactions:
        avg_i = sum(interactions) / len(interactions)
        print(f"  {s:>4} {len(funcs):>6} {avg_i:>10.3f} "
              f"[{min(interactions):.2f}-{max(interactions):.2f}]")

# Compute for remaining
if remaining:
    interactions = [total_interaction(tt, n) for tt in remaining]
    avg_i = sum(interactions) / len(interactions)
    print(f"  >7   {len(remaining):>6} {avg_i:>10.3f} "
          f"[{min(interactions):.2f}-{max(interactions):.2f}]")

print()

# Higher order interaction
def total_k_interaction(tt, n, k=3):
    """k-wise interaction: how much do k variables interact jointly?"""
    total = 2**n
    result = 0
    from itertools import combinations
    for subset in combinations(range(n), k):
        interact = 0
        for x in range(total):
            # Compute f on all 2^k flips of the subset
            values = []
            for mask in range(2**k):
                y = x
                for idx, var in enumerate(subset):
                    if (mask >> idx) & 1:
                        y ^= (1 << var)
                values.append((tt >> y) & 1)
            # k-wise interaction: parity of Möbius function
            # f has k-wise interaction at x if the alternating sum is nonzero
            mobius = 0
            for mask in range(2**k):
                sign = (-1) ** bin(mask).count('1')
                mobius += sign * values[mask]
            if mobius != 0:
                interact += 1
        result += interact / total
    return result

if n == 3:
    print(f"3-wise interaction (I₃) for n=3:")
    print(f"  {'size':>4} {'count':>6} {'avg I₃':>10}")
    print(f"  {'-'*25}")
    for s in sorted(by_size.keys()):
        funcs = by_size[s]
        i3s = [total_k_interaction(tt, n, 3) for tt in funcs]
        if i3s:
            print(f"  {s:>4} {len(funcs):>6} {sum(i3s)/len(i3s):>10.3f}")
    if remaining:
        i3s = [total_k_interaction(tt, n, 3) for tt in remaining]
        print(f"  >7   {len(remaining):>6} {sum(i3s)/len(i3s):>10.3f}")

print(f"""
NEW INSIGHT: k-wise interaction measures HOW ENTANGLED variables are.

  Functions with HIGH k-wise interaction require circuits that can
  simultaneously process k variables together — they can't be decomposed
  into simpler sub-computations.

  CONJECTURE: circuit_size(f) ≥ Σ_k I_k(f) / (some normalization)?

  If true: functions with high total interaction → large circuits.
  CLIQUE: all edges in a clique interact simultaneously → high interaction.
""")
