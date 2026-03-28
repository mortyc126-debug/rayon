"""
MIXED BOOTSTRAP PERCOLATION on circuit DAG.

Gate fires (becomes determined) if:
  - ≥ 1 input is determined AND has controlling value (0 for AND, 1 for OR)
  - OR both inputs are determined (any values)

This is a MIXED threshold: effectively threshold between 1 and 2.

Model: at each step, compute fraction of determined gates.
Iterate until convergence.

The fraction at convergence = Pr[output determined].

MEAN-FIELD APPROXIMATION:
  Let p = fraction of determined wires at current step.
  Each wire determined with prob p.

  Gate fires if:
    P1: ≥1 input controlling = 1 - (1 - p × 1/2)² = 1 - (1 - p/2)²
    P2: both inputs determined = p²

  P(fire) = P1 + (1-P1) × P2 (fire via controlling OR via both-det)
           = 1 - (1-p/2)² × (1 - p²) ... not quite right.

  More carefully:
    P(NOT fire) = P(no controlling) × P(not both determined)
    P(no controlling) = P(inp1 not controlling) × P(inp2 not controlling)
    P(inp not controlling) = P(inp not det) + P(inp det, not controlling)
                           = (1-p) + p × 1/2 = 1 - p/2

    P(not both det) = 1 - p² (at least one not determined)

    But: "not both det" AND "no controlling" overlap.
    P(NOT fire) = P(no inp provides controlling AND not both det)

    Event "no controlling AND not both det" =
      (inp1 not det OR (det, not controlling)) AND
      (inp2 not det OR (det, not controlling)) AND
      NOT (inp1 det AND inp2 det)

    = (inp1: not det or det-NC) AND (inp2: not det or det-NC) AND NOT(both det)

    Hmm, this is getting complex. Let me just enumerate.

    Each input has 3 states: not-det (prob 1-p), det-controlling (prob p/2),
    det-not-controlling (prob p/2).

    Gate NOT fired only if: no input is controlling AND not both det.
    = both inputs are (not-det or det-NC) AND at least one is not-det.

    P(inp = not-det or det-NC) = (1-p) + p/2 = 1 - p/2.
    P(both = not-det or det-NC) = (1-p/2)².
    P(both det) = p² (regardless of controlling).
    P(at least one not-det | both non-controlling) = 1 - (p/2)²/(1-p/2)² ... complex.

    SIMPLER: P(fire) = 1 - P(NOT fire).
    P(NOT fire) = P(no controlling input) × P(at most 1 det input)
    ... no, this double-counts.

    DIRECT: P(NOT fire) = P(neither controlling AND not both det)
    = P(inp1 not controlling) × P(inp2 not controlling) - P(both det-NC)
    Wait, I need to be more careful.

    P(NOT fire) = P(inp1 ∈ {ND, DNC}) × P(inp2 ∈ {ND, DNC}) - P(inp1=DNC, inp2=DNC)
    No — P(NOT fire) = P(inp1 ∈ {ND, DNC} AND inp2 ∈ {ND, DNC}) - P(inp1=DNC AND inp2=DNC)
    Because: if both DNC → both determined → gate fires.

    P(inp ∈ {ND, DNC}) = 1 - p/2.
    P(both ∈ {ND, DNC}) = (1 - p/2)².
    P(both = DNC) = (p/2)².

    P(NOT fire) = (1-p/2)² - (p/2)²
                = 1 - p + p²/4 - p²/4
                = 1 - p.

    WAIT: P(NOT fire) = 1 - p ???

    That means: P(fire) = p.

    The fraction of fired gates = p = fraction of determined inputs.
    This is a FIXED POINT: if inputs are p determined → gates are p determined.

    No cascade! p stays constant! THIS IS BAD.

Let me recheck...

    Three states per input: ND (prob 1-p), DC (prob p/2), DNC (prob p/2).

    Gate fires if: ≥1 DC input OR both inputs determined (DC or DNC).

    P(fire) = 1 - P(no DC AND not both determined)
    = 1 - P(no DC AND ≥1 ND)

    P(no DC) = P(inp1 ∈ {ND, DNC}) × P(inp2 ∈ {ND, DNC}) = (1-p/2)²
    P(≥1 ND | no DC) = 1 - P(both DNC | no DC) = 1 - (p/2)²/(1-p/2)²

    P(NOT fire) = P(no DC) - P(no DC AND both DNC)
    Wait: P(no DC AND both determined) = P(both DNC) = (p/2)².
    If both DNC: both determined → gate fires. So this SHOULD be subtracted.

    P(NOT fire) = P(no DC input AND NOT both determined)
    = P(no DC) - P(both DNC)
    = (1-p/2)² - (p/2)²
    = (1 - p/2 - p/2)(1 - p/2 + p/2)
    = (1 - p)(1)
    = 1 - p.

    So P(fire) = p. ✓

    This means: in mean-field, the gate determination probability equals
    the input determination probability. NO AMPLIFICATION.

    The fraction stays at p = n_fixed / (n + s).

    For n_fixed = n/2: p = (n/2) / (n + s) ≈ 1/(2 + 2s/n).
    For s = n: p ≈ 1/4.
    For s = n²: p ≈ 1/(2n).

    Output determined with prob ≈ p. CONSTANT for s = O(n). VANISHING for s >> n.

    THIS IS THE CORRECT MEAN-FIELD RESULT.
    No cascade amplification in mean-field!

    The experimental c < 1 must come from BEYOND mean-field effects:
    correlations, structure of the DAG, specific gate arrangements.

    MEAN-FIELD SAYS: No universal speedup. P(output det) = O(1/s).
    EXPERIMENTS SAY: P(output det) → 1.

    DISCREPANCY: mean-field is WRONG for structured DAGs.
    The circuit DAG has structure (topological ordering, fan-out patterns)
    that creates CORRELATIONS not captured by mean-field.

    Specifically: in a circuit, determined gates ABOVE feed into gates BELOW.
    The topological ordering creates a CASCADE that mean-field misses.

    Mean-field assumes: each gate's inputs are independently determined with prob p.
    Reality: if gate g is determined, ALL gates above g that use g are MORE LIKELY
    to be determined (because one of their inputs is known).

    This POSITIVE CORRELATION is what drives the cascade.
    Mean-field UNDERESTIMATES because it ignores this correlation.
"""

import math

def mean_field_iteration(n, s, steps=100):
    """Mean-field approximation of cascade propagation."""
    # Initial: n/2 variables determined, rest unknown
    total_wires = n + s
    p = (n / 2) / total_wires  # initial fraction determined

    print(f"  n={n}, s={s}, initial p = {p:.4f}")
    print(f"  {'step':>4} {'p':>8} {'gates_det':>10}")
    print(f"  {0:>4} {p:>8.4f} {p*s:>10.1f}")

    for step in range(1, steps):
        # P(gate fires) = p (from our derivation)
        p_new = p  # FIXED POINT!
        if abs(p_new - p) < 1e-10:
            break
        p = p_new
        print(f"  {step:>4} {p:>8.4f} {p*s:>10.1f}")

    print(f"  FIXED POINT: p = {p:.4f} (no amplification)")
    return p


def layered_propagation(n, s, depth):
    """Layer-by-layer propagation (more accurate than mean-field)."""
    # Layer 0: input variables. n/2 determined.
    # Layer d: gates at depth d.

    p_det = [0.0] * (depth + 1)
    p_det[0] = 0.5  # 50% of input vars determined

    print(f"\n  Layered propagation (n={n}, s={s}, depth={depth}):")
    print(f"  {'layer':>5} {'p_det':>8} {'p_controlling':>14}")

    for d in range(1, depth + 1):
        p = p_det[d-1]
        # Gate at layer d: both inputs from layer d-1.
        # P(fire) = 1 - P(not fire)
        # P(not fire) = 1 - p (from mean-field derivation)

        # BUT: in layered model, inputs are from PREVIOUS layer,
        # not randomly drawn from pool.
        # P(inp det) = p_{d-1}.
        # P(inp controlling | det) = 1/2.

        p_fire = 1 - (1 - p)  # = p. Same as mean-field.

        # WAIT — I keep getting p_fire = p. Let me recheck with numbers.
        # P(inp1 = DC) = p/2. P(inp1 = DNC) = p/2. P(inp1 = ND) = 1-p.
        # Gate NOT fire = (inp1 ∈ {ND,DNC})(inp2 ∈ {ND,DNC}) - (inp1=DNC)(inp2=DNC)
        # = (1-p/2)² - (p/2)² = 1 - p. So p_fire = p. ALWAYS.

        p_det[d] = p_fire
        p_ctrl = p_fire / 2

        print(f"  {d:>5} {p_det[d]:>8.4f} {p_ctrl:>14.4f}")

    print(f"  Output (layer {depth}): p_det = {p_det[depth]:.4f}")
    return p_det[depth]


def corrected_propagation(n, s, depth):
    """Propagation WITH positive correlation from DAG structure.

    Key correction: when gate g fires, its parent h gets ONE
    determined input. If h's OTHER input was ALREADY determined
    (from a different source), h fires immediately.

    The probability that h's other input is "already determined"
    is HIGHER than the mean-field p because of the DAG structure.
    """
    p = [0.5]  # layer 0: 50% determined

    print(f"\n  Corrected propagation (with DAG correlation):")
    print(f"  {'layer':>5} {'p_indep':>10} {'p_correlated':>14} {'boost':>8}")

    for d in range(1, depth + 1):
        p_prev = p[-1]

        # Independent model: p_fire = p_prev (as derived)
        p_indep = p_prev

        # Correlated model: gates at layer d share inputs from layer d-1.
        # If gate g1 and g2 at layer d share input from gate h at d-1:
        #   If h fires → BOTH g1 and g2 get a determined input.
        #   Correlation: Pr[g1 fires AND g2 fires] > Pr[g1] × Pr[g2].
        #
        # For fan-out f at layer d-1: each gate feeds f gates at layer d.
        # When it fires: f gates simultaneously get determined input.
        # Each of those f gates: Pr[OTHER input also det] = p_prev.
        # Pr[gate fires from both det] = p_prev.
        # Additional firings from fan-out: f × p_prev per fired gate.
        #
        # This is the cascade BOOST:
        # Effective p_fire = p_prev + p_prev × p_prev × (f-1)
        #                  = p_prev × (1 + p_prev × (f-1))

        avg_fanout = 2 * s / (s + n)
        f = avg_fanout

        # Boost: when a gate fires via controlling, its fan-out siblings
        # also get determined input. Fraction that then fire (other input already det):
        boost = p_prev * (f - 1) * p_prev  # fan-out siblings × prob other det

        p_corr = min(1.0, p_prev + boost)

        p.append(p_corr)
        print(f"  {d:>5} {p_indep:>10.4f} {p_corr:>14.4f} {boost:>8.4f}")

    print(f"  Output: p_corr = {p[-1]:.4f}")
    return p[-1]


def main():
    print("=" * 70)
    print("  MEAN-FIELD vs REALITY: Why mean-field fails")
    print("=" * 70)

    # Mean-field
    for n, s in [(10, 30), (20, 60), (30, 90)]:
        mean_field_iteration(n, s)

    # Layered (also gives p = constant)
    layered_propagation(20, 60, 10)

    # Corrected with DAG correlation
    for n, s in [(10, 30), (20, 80), (30, 150)]:
        corrected_propagation(n, s, 15)

    print(f"\n{'='*70}")
    print("  THE REAL MECHANISM")
    print(f"{'='*70}")
    print("""
    Mean-field gives p_fire = p_input = CONSTANT. No amplification.
    This is WRONG — experiments show clear cascade.

    The mean-field MISSES the DAG structure:
    1. Gates are ORDERED (topological). Layer d uses layer d-1 outputs.
    2. Fan-out creates CORRELATED infections at layer d+1.
    3. The correlation is POSITIVE (one infection helps others).

    The BOOST from correlation:
      p_{d+1} = p_d + p_d² × (fan_out - 1)
      = p_d × (1 + p_d × (f-1))

    For f = 2: p_{d+1} = p_d × (1 + p_d).
    Starting from p_0 = 0.5: p_1 = 0.5 × 1.5 = 0.75.
    p_2 = 0.75 × 1.75 = 1.3 → capped at 1.0.

    CASCADE TO 1 IN 2 STEPS for fan-out 2!

    But: this is an OVERESTIMATE (assumes all correlations positive).
    Reality is between mean-field (no cascade) and corrected (instant cascade).

    THE TRUTH lies in careful analysis of the SPECIFIC DAG topology.
    """)


if __name__ == "__main__":
    main()
