"""
PROOF: After fixing n/2 random variables, circuit output is determined
with high probability. → SAT in 2^{n/2} × poly → Williams → NEXP ⊄ P/poly.

THEOREM ATTEMPT:
  For any Boolean circuit C of size s on n inputs, after fixing
  n/2 variables chosen uniformly at random to random values,
  the output gate is "determined" (constant) with probability
  ≥ 1 - 1/poly(n).

PROOF:
  After fixing k = n/2 variables: each variable is fixed with prob 1/2.

  A gate g = AND(a, b) becomes constant if:
    a = 0 (then g = 0) OR b = 0 (then g = 0) OR (a=1 AND b=1, then g=1).

  If a is a wire whose value is determined: g might be constant.
  If a is an unfixed variable: a = 0 with prob 1/2 (unfixed, random value on DFS).

  Wait — we're not assigning random VALUES to fixed variables.
  We're doing DFS: trying both values. The STRUCTURE of which
  gates become constant depends on the variable ORDER and VALUES.

  Let me reconsider. The claim is:
  For RANDOM restriction ρ (fix each variable independently with prob 1/2):
    Pr[output determined under ρ] ≥ ???

  A gate AND(a,b) is determined under ρ if:
    a is determined and = 0, OR
    b is determined and = 0, OR
    both a,b determined and a=1 and b=1.

  "Determined" propagates bottom-up: inputs are determined if fixed by ρ.
  Gates determined if their inputs allow propagation.

  This is EXACTLY the switching lemma setting!

  Håstad's Switching Lemma (1987): After random restriction with
  parameter p (each variable lives with prob p):
    Pr[f doesn't simplify to depth-d decision tree] ≤ (5ps)^d
  where s = bottom fan-in of the DNF/CNF.

  But this is for DNF/CNF, not arbitrary circuits.

  For CIRCUITS: the analogous result is less studied.

  Let me prove directly for our setting.

  MODEL: Circuit C, size s, depth D. Fix each variable independently
  with prob 1/2 to a random value.

  For a gate at depth d (from inputs):
    Its value is "determined" if constant propagation reaches it.

  Claim: gate at depth d is determined with prob ≥ 1 - (3/4)^{d}.

  Why? Each gate is AND or OR of two inputs.

  For AND(a,b):
    If a determined and = 0: AND = 0. Determined.
    If b determined and = 0: AND = 0. Determined.
    If both determined: AND determined.

  The gate is NOT determined only if:
    a is not determined, OR a determined but = 1,
    AND b is not determined OR b determined but = 1.

  Pr[AND not determined] ≤ Pr[a not helpful] × Pr[b not helpful]

  "a not helpful" = a not determined OR a = 1.

  If a is at depth d-1:
    Pr[a not determined] ≤ (3/4)^{d-1} (induction)
    Pr[a = 1 | determined] ≈ 1/2 (random restriction)

  Pr[a not helpful] = Pr[a not det] + Pr[a det and a=1]
                    ≤ (3/4)^{d-1} + 1/2 × (1 - (3/4)^{d-1})
                    = (3/4)^{d-1} + 1/2 - 1/2 × (3/4)^{d-1}
                    = 1/2 + 1/2 × (3/4)^{d-1}
                    ≤ 1/2 + 1/2 = 1    (trivially)

  Hmm, this doesn't give < 1. The issue: even determined gates
  might have value 1, which doesn't help AND propagate.

  Let me think differently. For AND:
    Pr[AND = 0] ≥ Pr[a = 0] + Pr[b = 0] - Pr[a=0 AND b=0]
    ≈ 1/2 + 1/2 - 1/4 = 3/4 (for independent inputs)

    So: Pr[AND not constant=0] ≤ 1/4 (if both inputs determined).

    But: Pr[inputs determined] depends on depth.

  Let's define: p_d = Pr[gate at depth d is UNDETERMINED after restriction].

  For input variables: p_0 = 1/2 (fixed with prob 1/2 → determined).

  For gate at depth d: AND(a, b) where a at depth ≤ d-1, b at depth ≤ d-1.
    Gate undetermined iff:
      NOT (a determined and a=0) — so a undetermined or a=1
      AND NOT (b determined and b=0) — same for b
      AND NOT (a determined and b determined) — if both det, gate det.

    Actually: gate determined iff a=0(det) OR b=0(det) OR (a det AND b det).

    Gate UNdetermined iff:
      a undetermined AND b undetermined
      OR a undetermined AND b determined AND b=1
      OR a determined AND a=1 AND b undetermined.

    = (a undet)(b undet) + (a undet)(b det, b=1) + (a det, a=1)(b undet)

    p_d ≤ p_{d-1}² + p_{d-1} × (1-p_{d-1}) × q + (1-p_{d-1}) × q × p_{d-1}

    where q = Pr[value = 1 | determined] ≈ ???

    For random restriction: determined values are roughly balanced (1/2 zeros, 1/2 ones).
    But for AND gates: Pr[AND = 1] = Pr[a=1]×Pr[b=1] ≈ 1/4. So AND biased toward 0.

    This makes q < 1/2 for AND gates → p_d DECREASES faster.

  SIMPLIFICATION: Assume q = 1/2 (determined values balanced).

    p_d ≤ p_{d-1}² + 2 × p_{d-1} × (1-p_{d-1}) × 1/2
        = p_{d-1}² + p_{d-1}(1-p_{d-1})
        = p_{d-1}² + p_{d-1} - p_{d-1}²
        = p_{d-1}.

    So p_d ≤ p_{d-1}. NOT decreasing (at best constant). USELESS.

  The issue: even with q = 1/2, the "a determined and = 1" case
  doesn't help (AND output still depends on b).

  For OR gates: OR = 1 if a=1 OR b=1. So a=1 determined DOES help.
    Pr[OR undetermined] ≤ Pr[a not 1-determined] × Pr[b not 1-determined]
    "not 1-determined" = undetermined OR determined=0.
    Pr = p_{d-1} + (1-p_{d-1}) × 1/2 = (1 + p_{d-1})/2.

    For OR: p_d ≤ ((1+p_{d-1})/2)² = (1+p_{d-1})²/4.

    For p_0 = 1/2: p_1 ≤ (1.5)²/4 = 2.25/4 = 0.5625. INCREASING!

  AND: p_d ≤ p_{d-1} (constant)
  OR: p_d ≤ (1+p_{d-1})²/4 (might increase!)

  Neither decreases. This means: random restriction alone
  doesn't guarantee propagation.

  THE PROBLEM: Fixing a variable to a RANDOM value doesn't help
  because the "wrong" value (1 for AND, 0 for OR) doesn't propagate.

  In DFS: we try BOTH values. The "right" value propagates.

  KEY INSIGHT: In DFS, for each variable we try BOTH values.
  On one branch: the value propagates (makes some gate constant).
  On the other: it doesn't.

  If we always pick the "propagating" value first:
    With probability ≥ some constant, the output is determined.
    Then: 1 state (pruned) on that branch.
    On the other branch: recurse.

  Total states: at most 2 × T(n-1) (one branch determined, one recurses).
  T(n) = 2 × T(n-1) → T(n) = 2^n. No improvement.

  BUT: on the "bad" branch (no propagation), the circuit has FEWER
  active gates (even if output not determined, SOME gates simplified).

  If each variable fixes eliminates 1/s fraction of active gates:
    After k variables: (1 - 1/s)^k × s gates active.
    For k = s: (1/e) × s gates. Still Θ(s).

  This doesn't converge fast enough.

ACTUAL MEASUREMENT: Let me just measure the EXACT probability
that output is determined after fixing k random variables.
"""

import random
import math
import sys


def propagate(gates, n, fixed_vars):
    """Propagate constants through circuit. Return output value or None."""
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
    return wire_val.get(gates[-1][3])


def measure_determination_probability(gates, n, k, num_trials=1000):
    """Pr[output determined after fixing k random variables to random values]."""
    determined = 0
    for _ in range(num_trials):
        vars_to_fix = random.sample(range(n), k)
        fixed = {v: random.randint(0, 1) for v in vars_to_fix}
        out = propagate(gates, n, fixed)
        if out is not None:
            determined += 1
    return determined / num_trials


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
    print("  DETERMINATION PROBABILITY vs k/n")
    print("  Pr[output determined after fixing k random vars]")
    print("=" * 70)

    for n in [10, 15, 20, 30]:
        alpha = 4.27
        m = int(alpha * n)
        clauses = []
        for _ in range(m):
            vars_ = random.sample(range(n), min(3, n))
            clause = [(v, random.random() > 0.5) for v in vars_]
            clauses.append(clause)

        gates, output = build_3sat_circuit(n, clauses)
        if output < 0: continue

        print(f"\n  n={n}, s={len(gates)}, m={m}:")
        print(f"  {'k/n':>6} {'k':>4} {'Pr[det]':>10}")
        print(f"  {'-'*24}")

        for frac in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
            k = max(1, int(frac * n))
            if k > n: k = n
            pr = measure_determination_probability(gates, n, k, 2000)
            print(f"  {frac:>6.1f} {k:>4} {pr:>10.3f}")

        sys.stdout.flush()

    print(f"\n{'='*70}")
    print("  INTERPRETATION")
    print(f"{'='*70}")
    print("""
    If Pr[det] ≥ 1/2 at k/n = 0.5: then DFS with n/2 variables
    already determines output on half the branches.
    Effective states ≤ 2 × 2^{n/2} = 2^{n/2+1}. Speedup = 2^{n/2}.

    If Pr[det] ≥ 1-ε at k/n = c: then DFS needs only cn variables.
    States ≤ 2^{cn}. Speedup = 2^{(1-c)n}.

    For Williams: any c < 1 with Pr → 1 gives super-poly speedup.
    """)


if __name__ == "__main__":
    main()
