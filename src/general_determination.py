"""
GENERAL THEOREM: Random restriction determines ANY circuit's output w.h.p.

THEOREM. For ANY Boolean circuit C of size s ≥ n on n inputs,
random restriction ρ (fix each variable with prob 1/2 to random value)
determines the output with probability:

  Pr[output determined] ≥ 1 - exp(-Ω(n/s))

For s = poly(n): Pr → 1 - exp(-Ω(n^{1-c})) → 1.

PROOF.

Step 1: Gate-level propagation.

Each gate g has two inputs. For AND gate: if any input is determined
and equals 0, the gate output = 0 (determined).

An input variable x_i: under ρ, Pr[x_i determined] = 1/2.
Pr[x_i determined AND x_i = 0] = 1/4.

Step 2: Direct input gates.

A "direct input gate" g = AND(x_i, x_j) where both inputs are variables.
Pr[g determined] ≥ Pr[x_i det-0 OR x_j det-0 OR both det]
                 = 1 - Pr[neither provides controlling value]
                 For AND: controlling = 0.
                 Pr[x_i not det-0] = 1 - 1/4 = 3/4.
                 Pr[g not det via controlling] = (3/4)² = 9/16.
                 But also: Pr[both det, both=1] = (1/4)² = 1/16.
                 Pr[g determined] ≥ 1 - 9/16 + 1/16 = 8/16 = 1/2.

So: direct input gates are determined with prob ≥ 1/2.

Step 3: Any gate connected to a variable.

A gate g where at least one input is a variable x_i:
  Pr[g determined via x_i] ≥ Pr[x_i provides controlling value] = 1/4.
  (1/4 for AND getting 0, 1/4 for OR getting 1.)

Step 4: Counting variable-connected gates.

In a circuit of size s on n inputs: total input edges = 2s.
Input variables provide n × (average fan-out) = 2s variable-edges.
Average fan-out per variable = 2s/n.

Gates with at least one variable input: at most s, at least n
(each variable feeds at least one gate, otherwise unused).

Actually: the number of gates with DIRECT variable input:
  Each variable has fan-out f_i. Σ f_i = (variable contribution to edges).
  In a circuit: some gate inputs come from variables, some from other gates.
  Total gate inputs = 2s. Variable inputs = Σ f_i. Gate inputs = 2s - Σf_i.

  Number of gates with ≥1 variable input: at most Σ f_i ≤ 2s.
  At least: each variable feeds ≥1 gate → at least n such gates.

Step 5: Independent set of variable-connected gates.

Consider gates that have ≥1 direct variable input. There are ≥ n such gates.
Among these: find an INDEPENDENT SET I (no two share a variable input).

Each variable feeds ≤ s gates. So: chromatic number ≤ s.
Independent set size ≥ |variable-connected gates| / s ≥ n/s.

For gates in I: their variable inputs are DISTINCT.
So: their determination events are INDEPENDENT (different variables fixed).

Each gate in I: Pr[determined] ≥ 1/4 (variable provides controlling value).

Pr[NO gate in I determined] = Π_{g∈I} Pr[g not det] ≤ (3/4)^{|I|} ≤ (3/4)^{n/s}.

Step 6: Propagation from determined gate to output.

If gate g is determined: its value propagates UPWARD through the circuit.
The output is determined if there's a PATH of determined gates from g to output.

Worst case: g is at depth 0 (input layer). Need D more gates determined
on the path to output. Each subsequent gate is determined if g's value
propagates (controlling value for AND/OR) OR the other input is determined.

For the OUTPUT to be determined: need at least ONE of its inputs
to be determined via propagation.

Step 7: The key bound.

Even without propagation beyond the first layer: if ANY gate in I
produces a determined controlling value that DIRECTLY affects the
output chain:

In a circuit of depth D: the output is AND/OR of D layers.
If each layer has an independent set of size ≥ n/(s×D):
  Pr[no determination at any layer] ≤ (3/4)^{n/(s×D) × D} = (3/4)^{n/s}.

  Wait — layers don't work that way. Let me reconsider.

CLEANER ARGUMENT:

The output gate g_out depends (transitively) on all n inputs.
Consider the LONGEST PATH from any input to g_out: length D ≤ s.

On this path: there are D gates, each depending on variables
through sub-circuits.

At EACH gate on the path: the gate has two inputs. At least one
input sub-tree contains some input variables.

For the gate at depth d on the critical path:
  Its "other" input (not on the critical path) is a sub-circuit
  reading some variables. If ANY of those variables provides a
  controlling value → gate determined → propagation continues.

The number of variables in the "other" sub-tree ≥ 1 (at minimum).
Pr[other sub-tree provides controlling value] ≥ 1/4 (at least one
variable, with prob 1/4 it provides controlling value).

For D gates on the critical path:
  Pr[NO gate determined via its other input] ≤ (3/4)^D ≤ (3/4)^{log s}
  = s^{log(3/4)} = s^{-0.415} = 1/s^{0.415}.

Wait, D can be as small as log s (for balanced circuits).
(3/4)^{log s} = 1/s^{0.415}. Not very small but → 0.

For D = s (chain circuit): (3/4)^s → 0 exponentially. Very good.
For D = log s: 1/s^{0.415}. Goes to 0 polynomially. Weaker.

REFINED: At each gate on the path: the "other" sub-tree contains
k_d variables. Pr[controlling value from other tree] ≥ 1-(3/4)^{k_d}.
For k_d ≥ 1: Pr ≥ 1/4.

Total variables on "other" sub-trees: Σ k_d.
Since all n variables appear somewhere: Σ k_d ≥ n - D (at least n - D
variables are NOT on the critical path itself → they're in other sub-trees).

If independent: Pr[no propagation at any gate on path]
  ≤ Π (1 - (1-(3/4)^{k_d}))
  = Π (3/4)^{k_d}
  = (3/4)^{Σ k_d}
  ≤ (3/4)^{n - D}
  ≤ (3/4)^{n - s}

For s < n: (3/4)^{n-s} → 0.
For s = n: (3/4)^0 = 1. Doesn't help!
For s = cn (c < 1): (3/4)^{(1-c)n} → 0.

BUT: s ≥ n always (need ≥ n gates to read n inputs... actually
you can read multiple inputs with fewer gates? No — each variable
must feed into the circuit, requiring at least one gate or being
used directly. The circuit has s gates + n input wires.)

THE ISSUE: s ≥ n trivially (need n input wires + gates to process).
And the "other sub-trees" might share variables with the path.

Let me redo this more carefully.

CAREFUL ARGUMENT:

Let P = (g₁, g₂, ..., g_D = g_out) be ANY path from an input gate to output.
Each gᵢ has two inputs: one from the path (gᵢ₋₁ or a variable), one "side" input sᵢ.

The side input sᵢ is a sub-circuit reading some variables.
Let V(sᵢ) = set of variables read by sᵢ.

Claim: Σ |V(sᵢ)| ≥ n - 1.
  (Every variable appears in some side input or on the path itself.
   The path uses at most D ≤ s wire connections, touching ≤ D variables directly.
   The remaining n - D variables must appear in side inputs.)
  Actually: the path itself may not read any variables directly
  (gates can feed from other gates). Let me just say:

All n variables feed into the circuit. The circuit computes f.
For the output to be correct on all 2^n inputs: every variable
must INFLUENCE the output (otherwise f doesn't depend on it,
but we assume f depends on all n variables).

Each variable's influence reaches the output through SOME path.
The paths form a DAG. On the critical path P: side inputs contain
sub-DAGs that read various variables.

I'll use a simpler approach:

SIMPLEST CORRECT ARGUMENT:

Fact: The circuit has s AND/OR gates. Each has fan-in 2.
Each gate, when one input receives controlling value (0 for AND, 1 for OR),
becomes determined.

Under random restriction (prob 1/2):
  Each input variable x_i: Pr[x_i provides controlling value to gate g]
  = Pr[x_i fixed to controlling value of g] = 1/4.
  (Fixed with prob 1/2, controlling value with prob 1/2.)

For gate g with BOTH inputs being variables:
  Pr[g determined via controlling] ≥ 1 - (3/4)² = 7/16.

For gate g with one variable input, one gate input:
  Pr[g determined via variable] ≥ 1/4.

Across ALL s gates:
  Expected number of "directly determined" gates (via variable input):
  E = Σ_g Pr[g determined via variable input]
  Each variable provides controlling value to some gates.
  Variable x_i provides controlling to gate g with prob 1/4 if x_i is input of g.
  E = Σ_g Σ_{x_i input of g} 1/4 = (1/4) × 2s = s/2.

  EXPECTED s/2 gates become determined after restriction.

Among these: the OUTPUT gate is determined with some probability.
  Pr[output gate directly determined] = prob that output's variable
  inputs (if any) provide controlling value. For deep circuits:
  output gate has NO variable input → not directly determined.

  BUT: if s/2 gates determined, and these include gates on the path
  to output → cascade.

For the cascade: if a determined gate's value propagates to the
output through a chain of AND/OR gates:
  Each intermediate gate becomes determined if the propagating value
  is controlling.
  AND propagating 0: always controlling → cascade continues.
  OR propagating 1: always controlling → cascade continues.
  AND propagating 1: NOT controlling → cascade stops.
  OR propagating 0: NOT controlling → cascade stops.

For an AND chain: a determined-0 value propagates all the way to output!
For mixed AND/OR: probability 1/2 at each gate that cascade continues.

For a path of length L: Pr[cascade reaches output] ≥ (1/2)^L.

With s/2 determined gates spread across the circuit:
  Some are close to the output (small L).
  The closest: L ≤ s / (s/2) = 2 (on average, every other gate determined).

  Pr[cascade from closest determined gate reaches output] ≥ (1/2)^2 = 1/4.

COMBINED:
  Pr[output determined] ≥ Pr[∃ determined gate near output] × Pr[cascade]
  ≥ (1 - exp(-s/2)) × 1/4 ≈ 1/4 for s ≥ n.

This gives Pr ≥ 1/4. Not → 1.

To get Pr → 1: need MULTIPLE independent attempts at cascade.
With ≥ cn determined gates (c > 0): many potential cascade sources.
The probability ALL fail to cascade: ≤ (3/4)^{cn} → 0.

THEOREM: Pr[output determined | n/2 restriction] ≥ 1 - (3/4)^{Ω(n/s)}.

For s = poly(n): Pr ≥ 1 - (3/4)^{Ω(n^{1-c})} → 1.

For s = O(n): Pr ≥ 1 - (3/4)^{Ω(1)} = constant. Not → 1.

For the WILLIAMS application: need Pr → 1 as n → ∞.
This requires s = o(n)... but s ≥ n always. CONTRADICTION.

Actually: s/n → ∞ for circuits of size s = n^c (c > 1).
Then: n/s = n^{1-c} → 0. So (3/4)^{n/s} → 1. Pr → 0. WRONG DIRECTION.

I have the bound backwards. Let me fix.

The n/s exponent comes from: independent set of variable-connected gates
= n/s. For s >> n: this is small → few independent gates → weak bound.

For s = O(n): independent set = Ω(1) → constant number → weak.
For s = n²: independent set = 1/n → less than 1 → useless.

THE PROBLEM: Larger circuits have FEWER variable-connected gates
per unit (more gates are gate-connected, not variable-connected).

For a circuit of size s: variable-connected gates ≤ 2n (each variable
feeds ≤ some gates). Independent set among them ≤ n (at most n variables).

So: independent set = min(n, n/max_fanout) = n/max_fanout.
For max_fanout = s: independent set = n/s.

Pr[no determination] ≤ (3/4)^{n/s}. For s = n^c: (3/4)^{n^{1-c}}.
For c < 1: → 0. GOOD (sub-linear circuits).
For c = 1: (3/4)^1 = 3/4. NOT → 0.
For c > 1: (3/4)^{n^{1-c}} → (3/4)^0 = 1. USELESS.

The theorem only works for SUB-LINEAR circuits. Not useful for Williams
(which needs super-linear circuits).

For 3-SAT circuits: s = O(n) (linear). The 3-SAT specific analysis
gave (63/64)^{4n} because each CLAUSE (not each gate) provides 1/64
probability. There are 4n clauses → exponent = 4n. Not n/s = O(1).

The difference: 3-SAT has MANY independent "opportunity points"
(clauses), each with constant probability. General circuits might not.

CONCLUSION: The general theorem gives Pr ≥ 1-(3/4)^{n/s}.
For s = O(n): Pr = constant (maybe 1/4). Not → 1.
For 3-SAT: the special structure gives exponentially better Pr.

THE GAP: General circuits don't have the "many independent clauses"
structure. The cascade propagation is WEAKER for general circuits.

THIS MAY BE THE FUNDAMENTAL DIFFERENCE BETWEEN P AND NP:
  P functions: circuits can be structured so that cascade propagation
  is EFFECTIVE (many independent propagation opportunities).
  NP-hard functions: no such structure → cascade propagation fails.

If we could PROVE that optimal CLIQUE circuits have weak propagation:
  → SAT for CLIQUE circuits is hard → P ≠ NP directly.

But: we already proved SAT for 3-SAT circuits is EASY (strong propagation).
The 3-SAT FORMULA circuit (AND of OR) has perfect structure for propagation.
General circuits may not.

The question reduces to: does the OPTIMAL circuit for an NP-hard function
have good or bad cascade propagation structure?

If good: SAT is fast → Williams → NEXP ⊄ P/poly.
If bad: SAT is slow → no conclusion.
"""


def verify_general_bound():
    """Verify the general bound (3/4)^{n/s} numerically."""
    import math
    print("=" * 60)
    print("  General bound: Pr[NOT det] ≤ (3/4)^{n/s}")
    print("=" * 60)
    print(f"\n  {'s/n':>6} {'n':>5} {'s':>6} {'(3/4)^(n/s)':>12} {'Pr[det]':>10}")
    print("  " + "-" * 40)
    for ratio in [0.5, 1.0, 2.0, 5.0, 10.0]:
        n = 100
        s = int(ratio * n)
        bound = (3/4) ** (n/s)
        pr = 1 - bound
        print(f"  {ratio:>6.1f} {n:>5} {s:>6} {bound:>12.6f} {pr:>10.4f}")

    print("""
    For s/n = 1 (linear): Pr ≈ 0.25. Constant. Not useful.
    For s/n < 1: Pr → 1. But s < n impossible (need n input wires).
    For s/n > 1: Pr → 0. WORSE for larger circuits!

    The bound degrades for larger circuits because the independent
    set shrinks (more gates, fewer variable-connected per unit).

    3-SAT avoids this because its AND-of-OR structure provides
    O(n) INDEPENDENT propagation points (one per clause).
    General circuits may not have this structure.
    """)


if __name__ == "__main__":
    verify_general_bound()
