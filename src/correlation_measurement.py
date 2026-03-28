"""
MEASURING actual correlation vs mean-field prediction.

Mean-field: P(gate fires) = p = fraction of determined inputs.
Predicts: NO cascade. p stays constant across layers.

Experiment: ACTUALLY measure p per layer in real circuits.
If p_d INCREASES with d: cascade EXISTS (correlation-driven).
If p_d CONSTANT: mean-field correct, no cascade.

THE DEFINITIVE TEST.
"""

import random
import math
import sys


def propagate_and_measure(gates, n, fixed_vars):
    """Propagate constants and measure determination per layer."""
    wire_val = dict(fixed_vars)
    gate_determined = [False] * len(gates)

    # Assign layers (depth from inputs)
    wire_depth = {i: 0 for i in range(n)}
    for gi, (gtype, inp1, inp2, out) in enumerate(gates):
        d1 = wire_depth.get(inp1, 0)
        d2 = wire_depth.get(inp2, 0) if inp2 >= 0 else 0
        wire_depth[out] = max(d1, d2) + 1

    max_depth = max(wire_depth.get(gates[gi][3], 0) for gi in range(len(gates))) if gates else 0

    # Propagate
    for gi, (gtype, inp1, inp2, out) in enumerate(gates):
        v1 = wire_val.get(inp1)
        v2 = wire_val.get(inp2) if inp2 >= 0 else None

        determined = False
        if gtype == 'AND':
            if v1 == 0 or v2 == 0:
                wire_val[out] = 0; determined = True
            elif v1 is not None and v2 is not None:
                wire_val[out] = v1 & v2; determined = True
        elif gtype == 'OR':
            if v1 == 1 or v2 == 1:
                wire_val[out] = 1; determined = True
            elif v1 is not None and v2 is not None:
                wire_val[out] = v1 | v2; determined = True
        elif gtype == 'NOT':
            if v1 is not None:
                wire_val[out] = 1 - v1; determined = True

        gate_determined[gi] = determined

    # Count determined per layer
    layer_total = {}
    layer_det = {}
    for gi in range(len(gates)):
        d = wire_depth.get(gates[gi][3], 0)
        layer_total[d] = layer_total.get(d, 0) + 1
        if gate_determined[gi]:
            layer_det[d] = layer_det.get(d, 0) + 1

    return layer_total, layer_det, max_depth, wire_val.get(gates[-1][3]) if gates else None


def build_3sat_circuit(n, clauses):
    gates = []; nid = n
    neg = {}
    for i in range(n):
        neg[i] = nid; gates.append(('NOT', i, -1, nid)); nid += 1
    c_outs = []
    for clause in clauses:
        lits = [v if p else neg[v] for v, p in clause]
        cur = lits[0]
        for l in lits[1:]:
            out = nid; gates.append(('OR', cur, l, out)); nid += 1; cur = out
        c_outs.append(cur)
    if not c_outs: return gates, -1
    cur = c_outs[0]
    for ci in c_outs[1:]:
        g = nid; gates.append(('AND', cur, ci, g)); nid += 1; cur = g
    return gates, cur


def main():
    random.seed(42)
    print("=" * 70)
    print("  LAYER-BY-LAYER DETERMINATION: Mean-field vs Reality")
    print("  Mean-field predicts p_d = constant. Does p_d INCREASE?")
    print("=" * 70)

    for n in [15, 20, 30, 50]:
        alpha = 4.27
        m = int(alpha * n)
        clauses = []
        for _ in range(m):
            vars_ = random.sample(range(n), min(3, n))
            clause = [(v, random.random() > 0.5) for v in vars_]
            clauses.append(clause)

        gates, output = build_3sat_circuit(n, clauses)
        if output < 0:
            continue

        s = len(gates)

        # Average over many random restrictions
        num_trials = 500
        layer_det_sum = {}
        layer_total_sum = {}
        output_det_count = 0

        for _ in range(num_trials):
            # Random restriction: fix each variable with prob 1/2
            fixed = {}
            for i in range(n):
                if random.random() < 0.5:
                    fixed[i] = random.randint(0, 1)

            lt, ld, max_d, out_val = propagate_and_measure(gates, n, fixed)

            for d in lt:
                layer_total_sum[d] = layer_total_sum.get(d, 0) + lt[d]
                layer_det_sum[d] = layer_det_sum.get(d, 0) + ld.get(d, 0)

            if out_val is not None:
                output_det_count += 1

        # Print layer-by-layer p
        print(f"\n  n={n}, s={s}, m={m}, Pr[output det] = {output_det_count/num_trials:.3f}")
        print(f"  {'layer':>5} {'p_d (actual)':>14} {'p_0 (mean-field)':>18} {'ratio':>8}")
        print(f"  {'-'*48}")

        p0 = None
        for d in sorted(layer_total_sum.keys()):
            if layer_total_sum[d] > 0:
                p = layer_det_sum[d] / layer_total_sum[d]
                if p0 is None:
                    p0 = p
                ratio = p / p0 if p0 > 0 else 0
                print(f"  {d:>5} {p:>14.4f} {p0:>18.4f} {ratio:>8.3f}")

        sys.stdout.flush()

    print(f"\n{'='*70}")
    print("  VERDICT")
    print(f"{'='*70}")
    print("""
    If ratio (p_d / p_0) INCREASES with d: CASCADE EXISTS.
      The circuit structure creates positive correlation → amplification.
      This confirms: SAT speedup from cascade → Williams applicable.

    If ratio ≈ 1.0 for all d: NO CASCADE. Mean-field correct.
      The experimental speedup comes from other mechanisms (unit prop,
      not cascade). The formal proof via cascade is INCORRECT.
    """)


if __name__ == "__main__":
    main()
