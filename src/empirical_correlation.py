"""
EMPIRICAL CORRELATION MEASUREMENT.

For actual circuit gates: measure Cov(inp1_det, inp2_det) directly.
Compare with mean-field prediction (Cov = 0).

If measured Cov > 0: cascade mechanism confirmed.
If measured Cov ≈ 0: mean-field correct, cascade argument fails.
"""

import random
import math
import sys


def propagate(gates, n, fixed_vars):
    """Return dict of determined wire values."""
    wire_val = dict(fixed_vars)
    for gtype, inp1, inp2, out in gates:
        v1 = wire_val.get(inp1)
        v2 = wire_val.get(inp2) if inp2 >= 0 else None
        if gtype == 'AND':
            if v1 == 0 or v2 == 0: wire_val[out] = 0
            elif v1 is not None and v2 is not None: wire_val[out] = v1 & v2
        elif gtype == 'OR':
            if v1 == 1 or v2 == 1: wire_val[out] = 1
            elif v1 is not None and v2 is not None: wire_val[out] = v1 | v2
        elif gtype == 'NOT':
            if v1 is not None: wire_val[out] = 1 - v1
    return wire_val


def measure_gate_correlations(gates, n, num_trials=5000):
    """For each gate: measure Pr[inp1 det], Pr[inp2 det], Pr[both det].
    Compute Cov = Pr[both] - Pr[1] × Pr[2].
    """
    s = len(gates)
    gate_stats = []

    for gi, (gtype, inp1, inp2, out) in enumerate(gates):
        if inp2 < 0:  # NOT gate
            continue

        count_1det = 0
        count_2det = 0
        count_both = 0
        count_fire = 0

        for _ in range(num_trials):
            fixed = {}
            for i in range(n):
                if random.random() < 0.5:
                    fixed[i] = random.randint(0, 1)

            wv = propagate(gates, n, fixed)

            d1 = inp1 in wv
            d2 = inp2 in wv

            if d1: count_1det += 1
            if d2: count_2det += 1
            if d1 and d2: count_both += 1
            if out in wv: count_fire += 1

        p1 = count_1det / num_trials
        p2 = count_2det / num_trials
        p_both = count_both / num_trials
        p_fire = count_fire / num_trials
        cov = p_both - p1 * p2
        p_mean_field = (p1 + p2) / 2  # average input determination

        gate_stats.append({
            'gate': gi, 'type': gtype, 'inp1': inp1, 'inp2': inp2,
            'p1': p1, 'p2': p2, 'p_both': p_both, 'p_fire': p_fire,
            'cov': cov, 'p_mf': p_mean_field
        })

    return gate_stats


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
    print("  EMPIRICAL CORRELATION MEASUREMENT")
    print("  Cov = Pr[both det] - Pr[inp1 det] × Pr[inp2 det]")
    print("  Cov > 0 → cascade. Cov = 0 → no cascade.")
    print("=" * 70)

    for n in [10, 15, 20]:
        clauses = []
        for _ in range(int(4.27 * n)):
            vars_ = random.sample(range(n), min(3, n))
            clause = [(v, random.random() > 0.5) for v in vars_]
            clauses.append(clause)

        gates, output = build_3sat_circuit(n, clauses)
        if output < 0: continue

        stats = measure_gate_correlations(gates, n, 3000)

        # Separate by gate type
        and_gates = [s for s in stats if s['type'] == 'AND']
        or_gates = [s for s in stats if s['type'] == 'OR']

        print(f"\n  n={n}, s={len(gates)}")

        for label, subset in [('AND', and_gates), ('OR', or_gates)]:
            if not subset: continue
            covs = [s['cov'] for s in subset]
            p_fires = [s['p_fire'] for s in subset]
            p_mfs = [s['p_mf'] for s in subset]

            avg_cov = sum(covs) / len(covs)
            pos_cov = sum(1 for c in covs if c > 0.01)
            avg_fire = sum(p_fires) / len(p_fires)
            avg_mf = sum(p_mfs) / len(p_mfs)

            print(f"    {label} gates ({len(subset)}):")
            print(f"      Avg Cov: {avg_cov:+.4f}")
            print(f"      Gates with Cov > 0.01: {pos_cov}/{len(subset)} ({pos_cov/len(subset)*100:.0f}%)")
            print(f"      Avg P(fire): {avg_fire:.4f}")
            print(f"      Avg P(mean-field): {avg_mf:.4f}")
            print(f"      Fire - MF: {avg_fire - avg_mf:+.4f}")

            # Show top correlated gates
            top = sorted(subset, key=lambda s: -s['cov'])[:3]
            for s in top:
                print(f"        Gate {s['gate']}: Cov={s['cov']:+.4f}, P(fire)={s['p_fire']:.3f}, "
                      f"P1={s['p1']:.3f}, P2={s['p2']:.3f}, Pboth={s['p_both']:.3f}")

        sys.stdout.flush()

    print(f"\n{'='*70}")
    print("  VERDICT")
    print(f"{'='*70}")
    print("""
    If Avg Cov > 0 AND Fire > MF: CORRELATION DRIVES CASCADE. ✓
    If Avg Cov ≈ 0 AND Fire ≈ MF: NO CASCADE from correlation.

    The difference (Fire - MF) is the EXTRA determination from
    correlation beyond mean-field prediction.
    """)


if __name__ == "__main__":
    main()
