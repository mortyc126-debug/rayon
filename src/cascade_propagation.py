"""
PROOF ATTEMPT: Gate propagation always gives c < 1.

THEOREM ATTEMPT:
  For any Boolean circuit C of size s computing f: {0,1}^n → {0,1},
  the DFS with gate-level constant propagation visits at most
  2^{cn} states where c = 1 - Ω(1/s).

  This gives speedup 2^{Ω(n/s)}. For s = poly(n): speedup = 2^{Ω(n/poly)}
  = super-polynomial!

PROOF SKETCH:
  Consider the output gate g_out. It's AND or OR of two sub-circuits.

  Case: g_out = AND(A, B).

  The DFS fixes variables one by one. Consider the FIRST variable x_i
  that makes A or B evaluate to a constant.

  On the "good" branch (x_i = value that makes A or B constant):
    g_out becomes constant → entire subtree pruned. Cost: 1 state.

  On the "bad" branch: continue recursing.

  The question: how DEEP before some variable makes A or B constant?

  A depends on some set of variables V_A ⊆ [n].
  B depends on V_B ⊆ [n].

  For g_out = AND(A,B): output = 0 if A = 0 OR B = 0.

  After fixing k variables: the probability (over random ordering)
  that A or B becomes constant depends on the circuit structure.

  KEY LEMMA: For any circuit of size s, after fixing n/s variables,
  at least ONE gate becomes constant (with high probability over ordering).

  Why? Each gate has 2 inputs from earlier gates/variables.
  After fixing n/s variables: each variable is fixed with probability 1/s.
  A gate becomes constant if BOTH its inputs are determined.
  The probability that both inputs of a gate are determined:
  ≈ (n/s × 1/n)² = (1/s)². Very small.

  But: we have s gates. Expected number of constant gates:
  s × (1/s)² = 1/s. Small.

  This is too pessimistic. Let me reconsider.

  After fixing k variables: the number of "determined" wires
  propagates through the circuit. Each fixed variable directly
  determines 1 wire. Through propagation: more wires determined.

  For a CHAIN of AND gates: fixing x_1 = 0 → first AND = 0 →
  second AND (using first AND as input) = 0 → cascade!

  For general circuit: the CASCADE DEPTH = longest path of
  "determinable" gates from fixed variables.

  If cascade depth ≥ d after fixing 1 variable:
    The gate at depth d becomes constant.
    All gates above it in the same AND-chain become constant.
    The entire sub-tree above is pruned.

  For a circuit of depth D: cascade of depth D happens when
  the fixed variable is at the "bottom" of a long AND-chain.

  Average cascade depth: depends on circuit structure.
  For balanced circuit: cascade depth ≈ log s.
  For chain: cascade depth ≈ s.

EXPERIMENT: Measure actual cascade depth and pruning per variable.
"""

import random
import math
import sys


def simplify_and_measure(gates, n, fixed_vars):
    """Simplify circuit and count cascaded constant gates."""
    wire_val = dict(fixed_vars)
    constant_gates = 0
    total_gates = len(gates)

    for gtype, inp1, inp2, out in gates:
        v1 = wire_val.get(inp1)
        v2 = wire_val.get(inp2) if inp2 >= 0 else None

        determined = False
        if gtype == 'AND':
            if v1 == 0 or v2 == 0:
                wire_val[out] = 0; determined = True
            elif v1 == 1 and v2 == 1:
                wire_val[out] = 1; determined = True
            elif v1 == 1:
                wire_val[out] = v2; determined = (v2 is not None)
            elif v2 == 1:
                wire_val[out] = v1; determined = (v1 is not None)
        elif gtype == 'OR':
            if v1 == 1 or v2 == 1:
                wire_val[out] = 1; determined = True
            elif v1 == 0 and v2 == 0:
                wire_val[out] = 0; determined = True
            elif v1 == 0:
                wire_val[out] = v2; determined = (v2 is not None)
            elif v2 == 0:
                wire_val[out] = v1; determined = (v1 is not None)
        elif gtype == 'NOT':
            if v1 is not None:
                wire_val[out] = 1 - v1; determined = True

        if determined:
            constant_gates += 1

    output_determined = wire_val.get(gates[-1][3]) is not None
    return constant_gates, total_gates, output_determined


def measure_propagation_per_variable(gates, n):
    """For each variable: how many gates become constant when it's fixed?"""
    results = []

    for var in range(n):
        for val in [0, 1]:
            const_count, total, out_det = simplify_and_measure(
                gates, n, {var: val})
            results.append({
                'var': var, 'val': val,
                'const': const_count, 'total': total,
                'output_det': out_det,
                'fraction': const_count / total if total > 0 else 0
            })

    return results


def measure_cumulative_propagation(gates, n, ordering=None):
    """Fix variables one by one and track cumulative propagation."""
    if ordering is None:
        ordering = list(range(n))

    fixed = {}
    trajectory = []

    for var in ordering:
        # Try both values, pick the one that propagates more
        best_val = 0
        best_const = -1

        for val in [0, 1]:
            fixed[var] = val
            const, total, out_det = simplify_and_measure(gates, n, fixed)
            if const > best_const:
                best_const = const
                best_val = val
                best_out = out_det
            del fixed[var]

        fixed[var] = best_val
        const, total, out_det = simplify_and_measure(gates, n, fixed)
        trajectory.append({
            'k': len(fixed), 'const': const, 'total': total,
            'fraction': const / total, 'output_det': out_det
        })

        if out_det:
            break  # Output determined — done!

    return trajectory


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
    print("  CASCADE PROPAGATION: How fast do gates become constant?")
    print("  If output determined after k << n variables → c < 1")
    print("=" * 70)

    print(f"\n  {'Instance':<20} {'n':>4} {'s':>5} {'k_to_det':>9} "
          f"{'k/n':>6} {'frac@k/2':>9} {'frac@k':>8}")
    print("  " + "-" * 65)

    for n in range(5, 22):
        if 2**n > 5000000:
            break

        # Random 3-SAT at threshold
        alpha = 4.27
        m = int(alpha * n)

        max_k = 0
        avg_k = 0
        trials = 10

        for trial in range(trials):
            clauses = []
            for _ in range(m):
                vars_ = random.sample(range(n), 3)
                clause = [(v, random.random() > 0.5) for v in vars_]
                clauses.append(clause)

            gates, output = build_3sat_circuit(n, clauses)
            if output < 0: continue

            s = len(gates)

            # Measure: how many variables before output determined?
            # Try random ordering
            ordering = list(range(n))
            random.shuffle(ordering)
            traj = measure_cumulative_propagation(gates, n, ordering)

            k_det = len(traj)
            if k_det > max_k:
                max_k = k_det
                best_traj = traj
                best_s = s
            avg_k += k_det

        avg_k /= trials

        # Fraction of gates constant at k/2 and k
        frac_half = best_traj[max_k//2 - 1]['fraction'] if max_k > 1 else 0
        frac_full = best_traj[-1]['fraction'] if best_traj else 0

        print(f"  {'3SAT-'+str(n)+'-4.27':<20} {n:>4} {best_s:>5} "
              f"{max_k:>9} {max_k/n:>6.2f} {frac_half:>9.3f} {frac_full:>8.3f}")

        sys.stdout.flush()

    print(f"\n{'='*70}")
    print("  KEY METRIC: k_to_det / n")
    print(f"{'='*70}")
    print("""
    k_to_det = variables needed before output is determined.
    k_to_det / n < 1 means: don't need ALL variables → pruning.

    States in DFS ≤ 2^{k_to_det} (only branch on k_to_det variables).
    c = k_to_det / n.

    If k_to_det / n < 1 always: c < 1 → Williams speedup.
    If k_to_det / n → 1 for hard instances: c → 1 → no speedup.

    The BEST ordering (most propagation) gives the smallest k_to_det.
    The WORST ordering gives the largest.

    For P ≠ NP via Williams: need WORST ordering to still have k/n < 1.
    """)


if __name__ == "__main__":
    main()
