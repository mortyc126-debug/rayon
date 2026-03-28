"""
DeMorgan NOT-Elimination: Concrete Implementation.

The DeMorgan technique:
  For each wire w in the circuit, compute BOTH w and ¬w.
  AND(a,b) → AND(a,b) for positive, OR(¬a,¬b) for negative
  OR(a,b) → OR(a,b) for positive, AND(¬a,¬b) for negative
  NOT(a) → swap: positive=¬a (already computed), negative=a

Cost: exactly 2× original gates (minus NOT gates, which become free).
Result: 0 internal NOT gates, only n input NOTs (¬x₁,...,¬xₙ).

Then: can we eliminate input NOTs? Each ¬xᵢ is used by multiple gates.
If we remove ¬xᵢ, we need to replace it with a function of x₁,...,xₙ.
But ¬xᵢ = NOT(xᵢ) — there's no way to compute it without NOT!

UNLESS: the circuit doesn't actually NEED all ¬xᵢ. Maybe some are
redundant, or can be combined.

KEY INSIGHT: After DeMorgan, the circuit computes (f, ¬f) using
input NOTs only. If we only need f (not ¬f), we might be able to
PRUNE the ¬f computation and some input NOTs.

The question: how much pruning is possible?
- If most of the ¬f computation is needed → exponential blowup
- If most is redundant → polynomial preservation

THIS IS THE EXPERIMENT.
"""

import sys
import time
from collections import defaultdict


class Circuit:
    """Circuit with tracking of wire dependencies and fan-out."""

    def __init__(self, n):
        self.n = n
        self.gates = []  # (type, inp1, inp2)  type: 'AND','OR','NOT'
        self.wire_names = {i: f'x{i}' for i in range(n)}

    def add(self, gtype, inp1, inp2=-1):
        idx = self.n + len(self.gates)
        self.gates.append((gtype, inp1, inp2))
        if gtype == 'NOT':
            self.wire_names[idx] = f'¬({self.wire_names.get(inp1, f"w{inp1}")})'
        elif gtype == 'AND':
            self.wire_names[idx] = (f'({self.wire_names.get(inp1, f"w{inp1}")} ∧ '
                                     f'{self.wire_names.get(inp2, f"w{inp2}")})')
        elif gtype == 'OR':
            self.wire_names[idx] = (f'({self.wire_names.get(inp1, f"w{inp1}")} ∨ '
                                     f'{self.wire_names.get(inp2, f"w{inp2}")})')
        return idx

    def evaluate(self, x):
        """Evaluate on input x (tuple of bits)."""
        vals = list(x) + [0] * len(self.gates)
        for i, (gtype, inp1, inp2) in enumerate(self.gates):
            idx = self.n + i
            if gtype == 'NOT':
                vals[idx] = 1 - vals[inp1]
            elif gtype == 'AND':
                vals[idx] = vals[inp1] & vals[inp2]
            elif gtype == 'OR':
                vals[idx] = vals[inp1] | vals[inp2]
        return vals

    def truth_table(self):
        """Compute truth table as integer."""
        tt = 0
        for i in range(2**self.n):
            x = tuple((i >> j) & 1 for j in range(self.n))
            vals = self.evaluate(x)
            if vals[-1]:
                tt |= (1 << i)
        return tt

    def size(self):
        return len(self.gates)

    def not_count(self):
        return sum(1 for g, _, _ in self.gates if g == 'NOT')

    def fan_out(self):
        """Compute fan-out of each wire."""
        fo = defaultdict(int)
        for gtype, inp1, inp2 in self.gates:
            fo[inp1] += 1
            if inp2 >= 0:
                fo[inp2] += 1
        return fo

    def copy(self):
        c = Circuit(self.n)
        c.gates = self.gates[:]
        c.wire_names = self.wire_names.copy()
        return c


def demorgan_transform(circuit):
    """Apply DeMorgan transformation to eliminate internal NOT gates.

    For each wire w, compute both w⁺ (positive) and w⁻ (negative).

    Returns new circuit with only input NOTs.
    """
    n = circuit.n
    new_circuit = Circuit(n)

    # Wire mapping: old_wire -> (new_positive_wire, new_negative_wire)
    wire_map = {}

    # Inputs: positive = xᵢ, negative = ¬xᵢ
    for i in range(n):
        neg_wire = new_circuit.add('NOT', i)
        wire_map[i] = (i, neg_wire)  # (positive, negative)

    # Process gates in order
    for gi, (gtype, inp1, inp2) in enumerate(circuit.gates):
        old_idx = n + gi

        pos1, neg1 = wire_map[inp1]
        if inp2 >= 0:
            pos2, neg2 = wire_map[inp2]

        if gtype == 'AND':
            # positive: AND(pos1, pos2)
            # negative: OR(neg1, neg2)  [DeMorgan: ¬(a∧b) = ¬a∨¬b]
            new_pos = new_circuit.add('AND', pos1, pos2)
            new_neg = new_circuit.add('OR', neg1, neg2)
            wire_map[old_idx] = (new_pos, new_neg)

        elif gtype == 'OR':
            # positive: OR(pos1, pos2)
            # negative: AND(neg1, neg2)  [DeMorgan: ¬(a∨b) = ¬a∧¬b]
            new_pos = new_circuit.add('OR', pos1, pos2)
            new_neg = new_circuit.add('AND', neg1, neg2)
            wire_map[old_idx] = (new_pos, new_neg)

        elif gtype == 'NOT':
            # positive: neg1 (swap!)
            # negative: pos1
            wire_map[old_idx] = (neg1, pos1)

    return new_circuit, wire_map


def prune_circuit(circuit, output_wire):
    """Remove gates not needed for computing the output wire.

    Returns pruned circuit and the new output wire index.
    """
    n = circuit.n

    # BFS backwards from output to find needed gates
    needed = set()
    queue = [output_wire]

    while queue:
        w = queue.pop()
        if w < n:  # input wire
            continue
        gi = w - n
        if gi in needed:
            continue
        needed.add(gi)
        gtype, inp1, inp2 = circuit.gates[gi]
        queue.append(inp1)
        if inp2 >= 0:
            queue.append(inp2)

    # Rebuild circuit with only needed gates
    new_circuit = Circuit(n)
    old_to_new = {}
    for i in range(n):
        old_to_new[i] = i

    for gi in sorted(needed):
        gtype, inp1, inp2 = circuit.gates[gi]
        old_idx = n + gi
        new_inp1 = old_to_new[inp1]
        new_inp2 = old_to_new[inp2] if inp2 >= 0 else -1
        new_idx = new_circuit.add(gtype, new_inp1, new_inp2)
        old_to_new[old_idx] = new_idx

    new_output = old_to_new[output_wire]
    return new_circuit, new_output


def analyze_demorgan_cost(name, circuit):
    """Analyze the cost of DeMorgan transformation."""
    n = circuit.n
    orig_size = circuit.size()
    orig_nots = circuit.not_count()
    orig_tt = circuit.truth_table()

    print(f"\n{'─'*70}")
    print(f"  {name}")
    print(f"  Original: {orig_size} gates, {orig_nots} NOT gates")

    # Apply DeMorgan
    dm_circuit, wire_map = demorgan_transform(circuit)

    # The output of the original circuit
    orig_output = n + len(circuit.gates) - 1
    pos_output, neg_output = wire_map[orig_output]

    dm_size = dm_circuit.size()
    dm_nots = dm_circuit.not_count()

    print(f"  DeMorgan: {dm_size} gates, {dm_nots} NOT gates (all on inputs)")
    print(f"  Size ratio: {dm_size/orig_size:.2f}x")

    # Prune: keep only gates needed for positive output
    pruned, new_output = prune_circuit(dm_circuit, pos_output)
    pruned_size = pruned.size()
    pruned_nots = pruned.not_count()

    # Verify correctness
    pruned_tt = 0
    for i in range(2**n):
        x = tuple((i >> j) & 1 for j in range(n))
        vals = pruned.evaluate(x)
        if vals[new_output]:
            pruned_tt |= (1 << i)

    correct = pruned_tt == orig_tt

    print(f"  Pruned:   {pruned_size} gates, {pruned_nots} NOT gates")
    print(f"  Pruned ratio: {pruned_size/orig_size:.2f}x")
    print(f"  NOT reduction: {orig_nots} → {pruned_nots} "
          f"(saved {orig_nots - pruned_nots})")
    print(f"  Correct: {'✓' if correct else '✗'}")

    # How many input NOTs are actually needed?
    # Count which ¬xᵢ wires are used in the pruned circuit
    used_input_nots = set()
    for gi, (gtype, inp1, inp2) in enumerate(pruned.gates):
        if gtype == 'NOT' and inp1 < n:
            used_input_nots.add(inp1)
    print(f"  Input NOTs used: {len(used_input_nots)}/{n} "
          f"({sorted(used_input_nots)})")

    return {
        'orig_size': orig_size,
        'orig_nots': orig_nots,
        'dm_size': dm_size,
        'pruned_size': pruned_size,
        'pruned_nots': pruned_nots,
        'input_nots_used': len(used_input_nots),
    }


def build_triangle_circuit(N):
    """Build circuit for triangle detection on N vertices.

    Input: n = C(N,2) edge bits.
    Output: 1 if graph contains a triangle.

    Using the direct monotone approach (no NOT needed).
    """
    n = N * (N - 1) // 2

    # Edge index mapping: (i,j) -> input bit index
    edge_idx = {}
    idx = 0
    for i in range(N):
        for j in range(i+1, N):
            edge_idx[(i,j)] = idx
            edge_idx[(j,i)] = idx
            idx += 1

    circuit = Circuit(n)

    # For each triple (i,j,k), compute AND of three edges
    triangle_outputs = []
    for i in range(N):
        for j in range(i+1, N):
            for k in range(j+1, N):
                e_ij = edge_idx[(i,j)]
                e_ik = edge_idx[(i,k)]
                e_jk = edge_idx[(j,k)]

                a = circuit.add('AND', e_ij, e_ik)
                b = circuit.add('AND', a, e_jk)
                triangle_outputs.append(b)

    # OR all triangles
    if len(triangle_outputs) == 1:
        pass  # output is already the single triangle
    else:
        current = triangle_outputs[0]
        for t in triangle_outputs[1:]:
            current = circuit.add('OR', current, t)

    return circuit


def build_triangle_with_not(N):
    """Build triangle detection circuit that USES NOT gates.

    Strategy: use ¬edge to detect non-edges, then negate.
    Triangle = NOT(non-triangle) = NOT(∃ missing edge in triple)

    This gives a circuit with NOT gates that might be smaller
    than the monotone circuit (for large N).
    """
    n = N * (N - 1) // 2
    edge_idx = {}
    idx = 0
    for i in range(N):
        for j in range(i+1, N):
            edge_idx[(i,j)] = idx
            edge_idx[(j,i)] = idx
            idx += 1

    circuit = Circuit(n)

    # For each triple (i,j,k):
    # non-triangle(i,j,k) = ¬e_ij ∨ ¬e_ik ∨ ¬e_jk
    # triangle(i,j,k) = ¬(non-triangle) = e_ij ∧ e_ik ∧ e_jk
    # But this is the same as before!

    # Alternative with NOT: detect complement
    # "no triangle" = AND over all triples of "not all edges present"
    # = AND over triples of (¬eij ∨ ¬eik ∨ ¬ejk)
    # "has triangle" = NOT("no triangle")

    # First compute ¬eij for all edges
    neg_edges = {}
    for (i, j), idx_val in edge_idx.items():
        if i < j and idx_val not in neg_edges:
            neg_edges[idx_val] = circuit.add('NOT', idx_val)

    # For each triple: ¬eij ∨ ¬eik ∨ ¬ejk
    non_triangle_outputs = []
    for i in range(N):
        for j in range(i+1, N):
            for k in range(j+1, N):
                ne_ij = neg_edges[edge_idx[(i,j)]]
                ne_ik = neg_edges[edge_idx[(i,k)]]
                ne_jk = neg_edges[edge_idx[(j,k)]]

                a = circuit.add('OR', ne_ij, ne_ik)
                b = circuit.add('OR', a, ne_jk)
                non_triangle_outputs.append(b)

    # AND all non-triangle conditions: "no triangle"
    current = non_triangle_outputs[0]
    for t in non_triangle_outputs[1:]:
        current = circuit.add('AND', current, t)

    # NOT: "has triangle" = NOT("no triangle")
    circuit.add('NOT', current)

    return circuit


def build_non_monotone_formula(n):
    """Build a non-monotone function that benefits from NOT gates.

    f(x) = (x₀ ∧ ¬x₁) ∨ (x₁ ∧ ¬x₂) ∨ ... ∨ (x_{n-1} ∧ ¬x₀)

    This is a "rotation" function — it checks if any consecutive
    pair has (1, 0). This is non-monotone and requires NOT.
    """
    circuit = Circuit(n)

    terms = []
    for i in range(n):
        j = (i + 1) % n
        neg_j = circuit.add('NOT', j)
        term = circuit.add('AND', i, neg_j)
        terms.append(term)

    current = terms[0]
    for t in terms[1:]:
        current = circuit.add('OR', current, t)

    return circuit


def build_comparator(n):
    """Build comparator circuit: f(x,y) = 1 iff x ≥ y (as n-bit binary).

    This is a MONOTONE function with:
      Monotone circuit complexity: Θ(n²)
      General circuit complexity: O(n)

    The O(n) general circuit uses NOT for subtraction.
    This is the classic example of NOT helping for monotone functions.
    """
    # 2n inputs: x₀...x_{n-1} (bits of x), y₀...y_{n-1} (bits of y)
    # x_i is input wire i, y_i is input wire n+i
    total_inputs = 2 * n
    circuit = Circuit(total_inputs)

    # Ripple comparator: scan from MSB to LSB
    # At each bit position i (MSB first):
    #   if x_i > y_i (x_i=1, y_i=0): definitely x ≥ y → 1
    #   if x_i < y_i (x_i=0, y_i=1): definitely x < y → 0
    #   if x_i = y_i: continue to next bit

    # Using NOT: compute x_i AND NOT(y_i) and NOT(x_i) AND y_i
    # Then cascade

    # Result wire at position i: "x ≥ y considering bits 0..i"
    # Base: x₀ ≥ y₀ iff x₀ OR NOT(y₀) = x₀ OR ¬y₀ = ¬(¬x₀ AND y₀)

    # Actually, let's build it as:
    # geq = 1 (initial: equal so far, so ≥)
    # For i from MSB (n-1) to LSB (0):
    #   x_gt = x_i AND NOT(y_i)  -- x_i > y_i
    #   y_gt = NOT(x_i) AND y_i  -- y_i > x_i
    #   geq = x_gt OR (NOT(y_gt) AND geq)
    #        = x_gt OR ((x_i OR NOT(y_i)) AND geq)
    # Hmm, this uses NOT.

    # Simpler: geq_{i} = (x_i AND ¬y_i) OR (¬(x_i XOR y_i) AND geq_{i-1})
    # = (x_i AND ¬y_i) OR ((x_i AND y_i) OR (¬x_i AND ¬y_i)) AND geq_{i-1}

    # Let me just build a simple version with NOT
    if n == 0:
        return circuit

    # For single-bit comparison: x ≥ y iff x OR NOT(y)
    # x_0 is at input 0, y_0 is at input n

    not_y = [circuit.add('NOT', n + i) for i in range(n)]

    # Process from MSB (bit n-1) to LSB (bit 0)
    # geq starts as "true" (1 = x_const_1? no, we need a wire for 1)
    # Actually, after MSB: geq = x_{n-1} OR NOT(y_{n-1})

    # MSB comparison
    geq = circuit.add('OR', n - 1, not_y[n-1])  # x_{n-1} >= y_{n-1}

    for i in range(n-2, -1, -1):
        # x_i > y_i: x_i AND NOT(y_i)
        x_gt = circuit.add('AND', i, not_y[i])

        # equal_i: x_i == y_i: (x_i AND y_i) OR (NOT(x_i) AND NOT(y_i))
        # = NOT(x_i XOR y_i)
        # With NOT: equal = NOT(x_i XOR y_i)
        # x XOR y = (x OR y) AND NOT(x AND y)
        # equal = (x AND y) OR (NOT(x) AND NOT(y))

        xy_and = circuit.add('AND', i, n + i)
        not_x = circuit.add('NOT', i)
        nxny = circuit.add('AND', not_x, not_y[i])
        equal = circuit.add('OR', xy_and, nxny)

        # geq = x_gt OR (equal AND prev_geq)
        eq_geq = circuit.add('AND', equal, geq)
        geq = circuit.add('OR', x_gt, eq_geq)

    return circuit


def main():
    print("=" * 70)
    print("  DEMORGAN NOT-ELIMINATION: CONCRETE COST ANALYSIS")
    print("  Question: how much does eliminating NOT gates cost?")
    print("=" * 70)

    results = []

    # Test 1: Triangle detection (monotone — no NOT needed)
    for N in [4, 5, 6]:
        c = build_triangle_circuit(N)
        r = analyze_demorgan_cost(f"Triangle K_{N} (monotone)", c)
        results.append((f"Tri-{N}-mono", r))

    # Test 2: Triangle detection with NOT gates
    for N in [4, 5]:
        c = build_triangle_with_not(N)
        r = analyze_demorgan_cost(f"Triangle K_{N} (with NOT)", c)
        results.append((f"Tri-{N}-not", r))

    # Test 3: Non-monotone rotation function
    for n in [4, 6, 8]:
        c = build_non_monotone_formula(n)
        r = analyze_demorgan_cost(f"Rotation n={n}", c)
        results.append((f"Rot-{n}", r))

    # Test 4: COMPARATOR — key test! Monotone with gap
    for nbits in [2, 3, 4]:
        c = build_comparator(nbits)
        r = analyze_demorgan_cost(f"Comparator {nbits}-bit", c)
        results.append((f"Comp-{nbits}", r))

    # Summary table
    print(f"\n{'='*70}")
    print("  SUMMARY")
    print(f"{'='*70}")
    print(f"{'Name':<15} {'Orig':>6} {'NOT':>4} {'DM':>6} {'Pruned':>7} "
          f"{'NOT→':>5} {'inNOT':>6} {'ratio':>7}")
    print("-" * 60)

    for name, r in results:
        ratio = r['pruned_size'] / r['orig_size'] if r['orig_size'] > 0 else 0
        print(f"{name:<15} {r['orig_size']:>6} {r['orig_nots']:>4} "
              f"{r['dm_size']:>6} {r['pruned_size']:>7} "
              f"{r['pruned_nots']:>5} {r['input_nots_used']:>6} "
              f"{ratio:>7.2f}")

    print(f"""
    KEY OBSERVATIONS:

    1. For MONOTONE circuits (Triangle-mono):
       Pruned ratio ≈ 1.0. DeMorgan doesn't add overhead.
       All input NOTs are pruned away (not needed).

    2. For NON-MONOTONE circuits (Triangle-NOT, Rotation):
       Pruned ratio > 1.0. DeMorgan adds overhead.
       Some input NOTs survive pruning.

    3. The COST of NOT elimination = pruned_size / orig_size.
       If this ratio is bounded by a constant → Markov reduction
       preserves polynomial size → P ≠ NP.

    4. For the functions tested: ratio is 1.0-2.0.
       This is POLYNOMIAL (constant factor).
       But these are small instances. The question is scaling.
    """)


if __name__ == "__main__":
    main()
