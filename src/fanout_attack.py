"""
DIRECT ATTACK ON FAN-OUT: The Core of P vs NP.

THESIS: If we can show that no gate in a polynomial-size circuit
can be "relevant" to more than polynomially many cliques, then
P ≠ NP follows.

MODEL: Circuit C of size s computing k-CLIQUE on N vertices.
  - n = C(N,2) input bits (edges)
  - k = N^{1/3} (growing clique size)
  - Gate g at depth d depends on at most 2^d inputs

DEFINITION: Gate g is "relevant" to a potential k-clique Q if
  changing the edges within Q can change g's output.
  Formally: ∃ two inputs x, x' that differ only on edges within Q,
  such that g(x) ≠ g(x').

COUNTING ARGUMENT:
  Each potential k-clique Q has C(k,2) = Θ(N^{2/3}) edges.
  A gate g depends on ≤ 2^d input edges.
  g is relevant to clique Q only if g depends on ≥ 1 edge within Q.

  Number of cliques sharing an edge (i,j): C(N-2, k-2).
  So g is relevant to at most 2^d × C(N-2, k-2) cliques.

  For d = c·log N (polynomial depth): 2^d = N^c.
  C(N-2, k-2) ≈ C(N, k) × k²/N² ≈ C(N, k) × N^{-4/3}.

  So g is relevant to ≈ N^c × C(N,k) × N^{-4/3} = C(N,k) × N^{c-4/3} cliques.

  For c < 4/3: g is relevant to FEWER than C(N,k) cliques.
  For c ≥ 4/3: g can be relevant to all cliques.

  With 4/3 log N ≈ 1.33 log N depth, a single gate can "see" enough
  edges to be relevant to all cliques. So depth isn't the bottleneck.

BUT: being "relevant" ≠ being "useful." A gate computes 1 BIT.
  One bit partitions inputs into two groups. It can "half" the set
  of candidate cliques but can't identify which clique exists.

  To identify among C(N,k) cliques: need log₂ C(N,k) bits.
  C(N, N^{1/3}) ≈ (eN^{2/3})^{N^{1/3}} → log = Θ(N^{1/3} log N).

  So: Θ(N^{1/3} log N) "useful" gates needed.
  A poly(N) circuit has poly(N) >> N^{1/3} log N gates. SUFFICIENT.

CONCLUSION: Simple counting doesn't work. Each gate provides 1 bit,
  poly gates provide poly bits, and we need only N^{1/3} log N bits.

THE DEEPER QUESTION: Not "how many bits" but "how structured must
  the bits be?" The circuit must not just PARTITION cliques but
  CONSISTENTLY determine membership across ALL inputs.

THE NEW ANGLE: CONSISTENCY CONSTRAINT.

For a circuit to correctly compute CLIQUE on ALL 2^n inputs:
  For EVERY pair of inputs (x, y) where CLIQUE(x)=1, CLIQUE(y)=0:
    At least one gate g must have g(x) ≠ g(y).

This is the KW separation requirement. The question is:
  Can s = poly(N) gates separate ALL such pairs?

The number of such pairs: |CLIQUE⁻¹(1)| × |CLIQUE⁻¹(0)|.

For random graphs near threshold: |CLIQUE⁻¹(1)| ≈ 2^{n-1}.
So: ~2^{2n-2} pairs need separation.

Each gate separates at most 2^{n-1} pairs (it flips on half the inputs).

So: s ≥ 2^{2n-2} / 2^{n-1} = 2^{n-1}. Wait, this is exponential!

NO — the gate separates PAIRS, not inputs. A gate that changes on
2^{n-1} inputs separates at most 2^{n-1} × 2^{n-1} = 2^{2n-2} pairs
(all pairs where one element has g=0 and other has g=1).

So ONE gate can separate ALL pairs. Circuit size ≥ 1. Trivial.

THIS IS THE FUNDAMENTAL PROBLEM: one bit CAN separate all pairs.

But it can only separate them IF it exactly computes f.
The FIRST gate can't compute f (it's too simple).
Each gate builds toward f incrementally.

THE INCREMENTAL ARGUMENT: How much "progress" does each gate make?

Define PROGRESS(g) = |{(x,y) : f(x)≠f(y), g correctly separates}|
                   / |{(x,y) : f(x)≠f(y)}|

For the output gate: PROGRESS = 1.0 (100%).
For input xᵢ: PROGRESS = |{(x,y) : f(x)≠f(y), xᵢ(x)≠xᵢ(y)}|
            / |{(x,y) : f(x)≠f(y)}| ≈ 1/n.

Each gate combines two sub-results. If a combines two gates with
progress p₁ and p₂: the combined progress is at most p₁ + p₂ - p₁×p₂
(union bound) = 1 - (1-p₁)(1-p₂).

Starting from n inputs with progress ~1/n each:
  After 1 layer: progress ≈ 1 - (1 - 1/n)² ≈ 2/n.
  After k layers: progress ≈ 1 - (1 - 1/n)^{2^k}.
  To reach progress ≈ 1: need 2^k ≈ n, i.e., k ≈ log n.
  So: depth log n suffices! And size = n per layer × log n = n log n.

This gives size ≥ n log n??? Wait no, this is an UPPER bound on
how fast progress can grow, not a lower bound on circuit size.

The LOWER BOUND version: progress grows at most by factor 2 per layer.
Starting at progress 1/n: after d layers, progress ≤ 2^d / n.
For progress = 1: need d ≥ log n. Gives depth ≥ log n. Trivial.

WHAT WE NEED: a SLOWER growth rate for progress.

If progress grows by factor (1 + 1/poly) per gate:
  After s gates: progress ≤ (1 + 1/poly)^s ≈ e^{s/poly}.
  For progress = 1: s ≥ poly × ln(n). Still polynomial.

If progress grows by factor (1 + 1/exp) per gate:
  After s gates: progress ≤ (1 + 1/exp)^s. For progress 1: s ≥ exp.
  EXPONENTIAL! This would prove P ≠ NP!

THE KEY: What is the maximum progress increment per gate for CLIQUE?

For CLIQUE: each gate adds at most... this depends on the function.
For MONOTONE gates on MONOTONE functions: the progress increment
is bounded by the "influence" of the gate.

For GENERAL gates with NOT: the progress increment can be larger
(NOT allows "inversion" which can align progress directions).

If NOT increases progress increment by factor 2: we need 2× more
gates. Still polynomial.

If NOT increases progress by factor exp: unbounded saving. This is
what we observe (monotone exp, general possibly poly).

THE CRUX: Does NOT give constant factor or exponential improvement
in progress per gate?

EXPERIMENT: Compute progress profiles for actual circuits.
"""

import itertools
from collections import defaultdict
import random
import math
import sys
import time


def compute_progress_profile(n, func, circuit_gates):
    """Compute the progress of each gate toward computing func.

    Progress(g) = fraction of (x,y) pairs with f(x)≠f(y) that g separates.
    Separation: g(x) ≠ g(y) AND g(x) agrees with f(x) direction.

    Actually, simpler: Progress(g) = correlation between g and f.
    = |{x : g(x) = f(x)}| / 2^n
    """
    # Compute f values
    f_vals = []
    for bits in range(2**n):
        x = tuple((bits >> j) & 1 for j in range(n))
        f_vals.append(1 if func(x) else 0)

    # Compute each gate's truth table
    wire_tts = []
    # Input wires
    for j in range(n):
        tt = [0] * (2**n)
        for bits in range(2**n):
            tt[bits] = (bits >> j) & 1
        wire_tts.append(tt)

    # Gate wires
    for gtype, inp1, inp2 in circuit_gates:
        tt = [0] * (2**n)
        for bits in range(2**n):
            if gtype == 'AND':
                tt[bits] = wire_tts[inp1][bits] & wire_tts[inp2][bits]
            elif gtype == 'OR':
                tt[bits] = wire_tts[inp1][bits] | wire_tts[inp2][bits]
            elif gtype == 'NOT':
                tt[bits] = 1 - wire_tts[inp1][bits]
        wire_tts.append(tt)

    # Compute progress: correlation with f
    # Agreement = |{x : g(x) = f(x)}| / 2^n
    # Progress = (agreement - 0.5) / 0.5 for balanced f
    #          = 2 × agreement - 1

    total = 2**n
    f_ones = sum(f_vals)
    f_zeros = total - f_ones

    progress = []

    # Input wires
    for j in range(n):
        agree = sum(1 for bits in range(total)
                   if wire_tts[j][bits] == f_vals[bits])
        progress.append(agree / total)

    # Gate wires
    for gi in range(len(circuit_gates)):
        idx = n + gi
        agree = sum(1 for bits in range(total)
                   if wire_tts[idx][bits] == f_vals[bits])
        progress.append(agree / total)

        # Also check complement
        agree_not = total - agree
        progress[-1] = max(agree, agree_not) / total

    return progress


def compute_separation_power(n, func):
    """For each variable, compute how many (1,0) pairs it separates.

    A pair (x,y) with f(x)=1, f(y)=0 is "separated" by variable j
    if x_j ≠ y_j.

    The TOTAL separation needed: all (1,0) pairs.
    """
    ones = []
    zeros = []
    for bits in range(2**n):
        x = tuple((bits >> j) & 1 for j in range(n))
        if func(x):
            ones.append(bits)
        else:
            zeros.append(bits)

    total_pairs = len(ones) * len(zeros)

    # For each variable: separation count
    var_sep = [0] * n
    for x in ones:
        for y in zeros:
            for j in range(n):
                if ((x >> j) & 1) != ((y >> j) & 1):
                    var_sep[j] += 1

    return var_sep, total_pairs


def triangle_function(N):
    """Create triangle detection function for N vertices."""
    n = N * (N-1) // 2
    edge_idx = {}
    idx = 0
    for i in range(N):
        for j in range(i+1, N):
            edge_idx[(i,j)] = idx
            edge_idx[(j,i)] = idx
            idx += 1

    def func(x):
        for i in range(N):
            for j in range(i+1, N):
                for k in range(j+1, N):
                    if x[edge_idx[(i,j)]] and x[edge_idx[(i,k)]] and x[edge_idx[(j,k)]]:
                        return True
        return False

    return func, n, edge_idx


def build_triangle_circuit(N):
    """Build monotone triangle detection circuit."""
    n = N * (N-1) // 2
    edge_idx = {}
    idx = 0
    for i in range(N):
        for j in range(i+1, N):
            edge_idx[(i,j)] = idx
            idx += 1

    gates = []
    triangle_outputs = []

    for i in range(N):
        for j in range(i+1, N):
            for k in range(j+1, N):
                e_ij = edge_idx[(i,j)]
                e_ik = edge_idx[(i,k)]
                e_jk = edge_idx[(j,k)]

                a = n + len(gates)
                gates.append(('AND', e_ij, e_ik))
                b = n + len(gates)
                gates.append(('AND', a, e_jk))
                triangle_outputs.append(b)

    if len(triangle_outputs) == 1:
        return gates

    current = triangle_outputs[0]
    for t in triangle_outputs[1:]:
        new = n + len(gates)
        gates.append(('OR', current, t))
        current = new

    return gates


def analyze_fanout_for_clique():
    """Analyze fan-out structure for triangle/clique detection."""
    print("=" * 80)
    print("  FAN-OUT ANALYSIS FOR CLIQUE")
    print("=" * 80)

    for N in [4, 5, 6]:
        func, n, edge_idx = triangle_function(N)

        if 2**n > 200000:
            print(f"\n  N={N}: too large (n={n})")
            continue

        print(f"\n{'─'*70}")
        print(f"  TRIANGLE on K_{N} (n={n} edges, C({N},3)={N*(N-1)*(N-2)//6} triangles)")
        print(f"{'─'*70}")

        # Build circuit
        gates = build_triangle_circuit(N)

        # Compute progress profile
        progress = compute_progress_profile(n, func, gates)

        # Input progress
        input_progress = progress[:n]
        avg_input = sum(input_progress) / n
        print(f"\n  Input variable progress:")
        print(f"    Average: {avg_input:.4f}")
        print(f"    Range: [{min(input_progress):.4f}, {max(input_progress):.4f}]")

        # Gate progress (sorted)
        gate_progress = progress[n:]
        gate_sorted = sorted(gate_progress)

        print(f"\n  Gate progress (circuit size = {len(gates)}):")
        print(f"    Final (output): {gate_progress[-1]:.4f}")

        # Progress increment per gate
        increments = []
        for gi, (gtype, inp1, inp2) in enumerate(gates):
            p_out = progress[n + gi]
            p_in1 = progress[inp1]
            p_in2 = progress[inp2] if inp2 >= 0 else 0.5
            increment = p_out - max(p_in1, p_in2)
            increments.append(increment)

        avg_inc = sum(increments) / len(increments)
        max_inc = max(increments)
        pos_inc = sum(1 for x in increments if x > 0.001)

        print(f"\n  Progress increments:")
        print(f"    Average: {avg_inc:.6f}")
        print(f"    Maximum: {max_inc:.6f}")
        print(f"    Positive: {pos_inc}/{len(increments)} gates")
        print(f"    Gates needed (1.0 / avg_inc): {1.0/avg_inc:.0f}" if avg_inc > 0 else "")

        # Fan-out analysis
        fan_out = defaultdict(int)
        for gtype, inp1, inp2 in gates:
            fan_out[inp1] += 1
            if inp2 >= 0:
                fan_out[inp2] += 1

        input_fanout = [fan_out.get(i, 0) for i in range(n)]
        gate_fanout = [fan_out.get(n+i, 0) for i in range(len(gates))]

        print(f"\n  Fan-out structure:")
        print(f"    Input fan-out: avg={sum(input_fanout)/n:.1f}, "
              f"max={max(input_fanout)}")
        if gate_fanout:
            print(f"    Gate fan-out:  avg={sum(gate_fanout)/len(gate_fanout):.1f}, "
                  f"max={max(gate_fanout) if gate_fanout else 0}")

        # Separation power
        var_sep, total_pairs = compute_separation_power(n, func)
        max_sep = max(var_sep)
        sum_sep = sum(var_sep)

        print(f"\n  Separation power:")
        print(f"    Total pairs: {total_pairs}")
        print(f"    Max variable separation: {max_sep} ({max_sep/total_pairs*100:.1f}%)")
        print(f"    Sum all variables: {sum_sep} ({sum_sep/total_pairs*100:.1f}%)")
        print(f"    Average coverage per var: {sum_sep/total_pairs/n*100:.1f}%")

        # KEY METRIC: How much does fan-out help?
        # Without fan-out (formula): each gate used once
        # With fan-out: gates reused
        # Formula size = circuit size × average fan-out along paths

        total_fanout = sum(fan_out.values())
        avg_fanout = total_fanout / (len(gates) + n) if len(gates) + n > 0 else 0

        print(f"\n  Fan-out benefit:")
        print(f"    Total fan-out: {total_fanout}")
        print(f"    Average: {avg_fanout:.2f}")
        print(f"    Estimated formula size: {len(gates) * avg_fanout:.0f}")
        print(f"    Circuit size: {len(gates)}")
        print(f"    Fan-out savings: {avg_fanout:.2f}×")


def main():
    random.seed(42)
    analyze_fanout_for_clique()

    print(f"\n\n{'='*80}")
    print("  THEORETICAL ANALYSIS: FAN-OUT LIMITATION")
    print(f"{'='*80}")
    print("""
    For CLIQUE(N, k) with k = N^{1/3}:

    Number of potential k-cliques: C(N, k) ≈ (eN/k)^k = (eN^{2/3})^{N^{1/3}}
      = exp(N^{1/3} × (2/3) ln N) — super-polynomial

    Each gate computes 1 bit → can "halve" the candidate set.
    Gates needed to identify one clique: log₂ C(N,k) = Θ(N^{1/3} log N)

    A polynomial circuit with s = N^c gates provides s bits.
    For c ≥ 1: s = N^c >> N^{1/3} log N. PLENTY of bits.

    So the counting argument FAILS: polynomial circuits have enough
    information capacity.

    THE MISSING PIECE: not information capacity, but COMPUTATIONAL
    structure. The bits must be COMPUTED, not just stored.

    Each bit requires a CONSISTENT function of ALL inputs.
    The consistency requirement is what makes circuits hard:
      - Gate g must give correct information for ALL 2^n inputs
      - Not just for one specific input

    This "universality" constraint is what separates circuits from
    lookup tables. A lookup table of size 2^n trivially computes f.
    A circuit of size poly(n) must COMPRESS this.

    THE COMPRESSION QUESTION:
    Can CLIQUE be compressed from 2^n bits to poly(n) gates?

    This is EXACTLY P vs NP. And we've come full circle.

    INSIGHT: The problem is not about fan-out, bits, curvature,
    or any single measure. It's about the INTERPLAY between:
      1. Consistency (correct on all inputs)
      2. Compression (polynomial size)
      3. Composability (building from AND/OR/NOT)

    These three constraints together are what make P vs NP hard.
    """)


if __name__ == "__main__":
    main()
