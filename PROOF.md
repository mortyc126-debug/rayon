# Cascade Propagation Theorem

## Claim

**Theorem.** For every constant c > 1 and ε > 0, NEXP ⊄ SIZE(n^{c(1-ε)}).

In particular: there exists an explicit function in NEXP that requires circuits of size > n^{2-ε} for every ε > 0.

## Proof Structure

The proof has three parts:
1. An algorithm for Circuit-SAT running in time 2^{δn} for δ < 1
2. Correctness and runtime analysis
3. Application of Williams' theorem

---

## Part 1: The Algorithm

**Input:** Boolean circuit C with s gates and n input variables.

**Output:** Is there an assignment x ∈ {0,1}^n such that C(x) = 1?

**Algorithm CascadeSAT(C, n):**

```
function CascadeSAT(C, n, assigned = {}):
    // Constant propagation
    Simplify C using assigned values:
      For each gate g with known input:
        AND(a, b): if a=0 or b=0, set g=0; if a=1,b=1, set g=1
        OR(a, b):  if a=1 or b=1, set g=1; if a=0,b=0, set g=0
        NOT(a):    if a known, set g=1-a
      Repeat until no more propagation.

    If output of C is determined:
      return (output == 1)

    // Branch on next unassigned variable
    Pick any unassigned variable x_i
    if CascadeSAT(C, n, assigned ∪ {x_i = 1}):
      return true
    return CascadeSAT(C, n, assigned ∪ {x_i = 0})
```

This is standard DPLL with **gate-level** (not clause-level) unit propagation.

---

## Part 2: Runtime Analysis

**Theorem (Cascade Determination).** Let C be a Boolean circuit with s ≥ 2n gates on n inputs. Fix each of the n variables independently: with probability 1/2 fix to a uniformly random value, with probability 1/2 leave free. Then:

Pr[output of C is determined by constant propagation] ≥ 1 - (15/16)^{n/4}

**Proof.**

### Step 2.1: Seed Creation

A variable x_i is "fixed" with probability 1/2. Its value is 0 or 1 each with probability 1/2.

A gate g = AND(x_i, b) where x_i is a direct input: if x_i is fixed to 0, then g = 0 (determined). This happens with probability 1/4 (fixed × value 0).

Similarly for OR: if x_i fixed to 1, gate determined. Probability 1/4.

Define: a **seed** is a gate that becomes determined directly from a fixed variable providing a controlling value (0 for AND, 1 for OR).

For each variable x_i: x_i feeds into some gate g as direct input. Pr[x_i creates a seed at g] = 1/4.

With n variables: Expected[seeds] = n/4.

### Step 2.2: Seed Independence

**CRITICAL ISSUE.** Different variables create seeds at different gates. Two seeds are independent if they come from different variables (the fixing of different variables is independent).

However: the seeds' EFFECTS on the circuit are NOT independent — they propagate through the shared DAG structure.

For the purpose of determining the output, we need: at least ONE seed's cascade reaches the output.

**Claim.** The events "seed from x_i determines the output" are NOT independent, but they are POSITIVELY correlated (one cascade helping another by determining more gates).

Positive correlation means: Pr[any seed determines output] ≥ 1 - Π Pr[seed i fails to determine output].

**THIS IS WHERE THE ARGUMENT HAS A SUBTLE GAP.**

Positive correlation (FKG inequality) requires the events to be "increasing" in a lattice. For our setting:

- "x_i is fixed to controlling value" → seed i created. These are independent. ✓
- "seed i's cascade reaches output" → depends on OTHER seeds and OTHER fixed variables.

The cascade from seed i depends on gate values, which depend on OTHER variables' restrictions. If another variable x_j is also fixed: it might help seed i's cascade (by determining more gates on the path).

So: more fixed variables = more help for each cascade. The events "cascade i reaches output" are POSITIVELY correlated with "x_j is fixed." ✓

By FKG inequality (or Harris inequality) for increasing events on a product lattice:

Pr[NO cascade reaches output] ≤ Π_i Pr[cascade i doesn't reach output]

This is the WRONG direction for us. We want:
Pr[SOME cascade reaches output] ≥ 1 - Π_i Pr[cascade i doesn't reach output]

And: Π_i Pr[cascade i fails] ≤ Pr[all cascades fail].

With FKG for DECREASING events: "cascade i fails" might be a decreasing event (more restrictions → less likely to fail). Then:

Pr[all fail] ≤ Π Pr[each fails].

IS "cascade i fails" a DECREASING event? Decreasing means: adding more restrictions can only DECREASE the probability.

Adding restrictions (fixing more variables) creates more seeds → more cascades → LESS likely that cascade i fails.

Wait — cascade i is a SPECIFIC cascade from seed i. If we add more restrictions, we might determine more gates, which HELPS cascade i reach the output. So: Pr[cascade i fails] DECREASES with more restrictions.

"Cascade i fails" IS a decreasing event. By FKG:

Pr[all fail] ≤ Π_i Pr[cascade i fails].

But we can only bound Pr[cascade i fails] individually.

### Step 2.3: Individual Cascade Failure Probability

For a single seed at gate g₀ (determined by variable x_i):

The cascade propagates from g₀ upward through the DAG.
At each gate g above g₀: g becomes determined if g₀'s determined value is the controlling value for g's parent gate.

The cascade continues if at each step, the determined value is controlling:
- AND parent receiving 0: controlling. ✓ Always propagates.
- AND parent receiving 1: NOT controlling. Stops unless other input determined.
- OR parent receiving 1: controlling. ✓ Always propagates.
- OR parent receiving 0: NOT controlling. Stops.

For AND gates: seed typically produces 0 (AND biased toward 0).
  If seed value = 0: propagates through AND parent. ✓
  If seed value = 1: stops at AND parent (unless other input also determined).

Pr[seed value = 0 for AND gate] = Pr[controlling input = 0 for AND] = 3/4.

Wait — the seed is DEFINED as having a controlling value. So seed value IS controlling.

Seed at AND gate: gate = 0 (controlling). This propagates to any AND parent as 0 (controlling). Cascade continues.

It propagates to OR parent as 0 (NOT controlling). Cascade stops at OR parent.

So: cascade continues through AND-chains but stops at OR gates.

For circuits that alternate AND and OR layers:
  Cascade from an AND-seed (value 0): propagates through AND chain.
  Hits OR gate: stops (0 is not controlling for OR).

For the cascade to CROSS an OR gate: need the OTHER input of OR to be 0 (then OR output = 0, determined).

Pr[other input = 0 and determined] = prob that the OTHER sub-circuit also cascades to 0.

This is the BRANCHING: the cascade needs HELP from another cascade at each OR gate.

### Step 2.4: The Real Model

The cascade propagation is NOT a simple branching process. It's a PERCOLATION PROCESS on the circuit DAG with specific rules:

- 0 propagates through AND (controlling)
- 1 propagates through OR (controlling)
- 0 does NOT propagate through OR (needs help)
- 1 does NOT propagate through AND (needs help)

For a circuit with mixed AND/OR gates: the cascade value alternates.

**KEY OBSERVATION:** In a circuit computing a non-trivial function:
AND and OR gates ALTERNATE (otherwise the circuit computes a trivial monotone function).

At each AND gate: 0 propagates. At next OR gate: needs 1 to propagate.
These are OPPOSITE requirements. A single cascade CANNOT pass through both.

**THIS BREAKS THE ARGUMENT.**

A cascade starting with value 0 (from AND seed):
- Passes AND gates: ✓ (0 is controlling)
- Hits OR gate: STOPS (0 is NOT controlling for OR)

A cascade starting with value 1 (from OR seed):
- Passes OR gates: ✓ (1 is controlling)
- Hits AND gate: STOPS (1 is NOT controlling for AND)

**No single cascade can traverse a mixed AND/OR circuit!**

The cascade dies at the first gate of the "wrong" type.

### Step 2.5: What Actually Happens

The REAL propagation is more nuanced:

1. Seed at AND gate: output = 0. Propagates to parent.
2. If parent is AND: 0 is controlling → parent = 0. Continue.
3. If parent is OR: 0 is NOT controlling. BUT: parent might still be determined if the OTHER input is also determined.

So: the cascade doesn't die at OR — it WAITS for help from the other input.

If the other input is independently determined (from another seed):
  parent OR is determined (both inputs known → output known).

This is the "help" mechanism: two cascades MERGE at OR gates.

For the output to be determined: need TWO cooperating cascades — one providing 0 for AND gates, one providing 1 for OR gates.

Expected seeds of type 0 (AND controlling): n/8 (n/4 seeds × 1/2 are AND).
Expected seeds of type 1 (OR controlling): n/8.

For a circuit with D alternating layers:
  Need: at least one 0-cascade and one 1-cascade to meet at each OR/AND boundary.

At each boundary: Pr[both available] ≈ (1 - (7/8)^{n/8})² → 1.

But: they need to meet at the SAME gate, not just exist somewhere.

### Step 2.6: Conclusion

**THE ORIGINAL ARGUMENT HAS A FLAW.**

The cascade does NOT simply propagate from input to output with probability 3/4 per gate. It ALTERNATES between needing 0-cascades and 1-cascades at AND vs OR gates.

The actual propagation probability depends on the circuit's AND/OR structure, and for mixed circuits, a single cascade CANNOT traverse the entire circuit.

The speedup is REAL (confirmed experimentally) but the formal proof via branching process is INCORRECT in its current form.

The correct analysis requires:
1. Modeling the TWO-TYPE cascade (0-cascades and 1-cascades)
2. Analyzing their MEETING probability at each alternating layer
3. This is a TWO-TYPE percolation problem, significantly harder

**STATUS: The formal proof has a gap. The experimental evidence supports the speedup, but the theoretical analysis needs a more sophisticated percolation model.**
