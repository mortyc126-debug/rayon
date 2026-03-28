"""
CRITICAL FLAW FOUND: Covariance dampens exponentially with distance.

The Cov ≥ p(1-p)²/4 bound requires shared ancestor at distance 1.
For shared ancestor at distance k: Cov ≈ p × ((1-p)/2)^{2k}.
For k = Ω(s): Cov = exp(-Ω(s)) → 0. No cascade.

ADVERSARY COUNTEREXAMPLE:
  Build circuit: bottom = fan-out region (variables shared by many gates).
  Top = formula (each gate output used once, fan-out = 1).
  Fan-out gates at distance D from output.
  Cov at output level: exp(-D) → 0.
  No cascade reaches output. Mean-field correct at top.

CONSEQUENCE: The cascade argument works ONLY when fan-out gates
are NEAR the output (within O(1) distance).

For 3-SAT circuits: fan-out is at INPUT level (distance 2 from AND chain).
  AND chain is the OUTPUT side. Distance = O(1). CASCADE WORKS. ✓

For general circuits: adversary can push fan-out to bottom.
  Top formula region: no cascade. ✗

THIS KILLS THE NEXP ⊄ P/poly ARGUMENT.

The argument is valid for specific circuit structures (3-SAT, circuits
with fan-out near output) but NOT for ALL circuits.

Williams requires speedup for ALL poly-size circuits.
Our speedup only applies to circuits with fan-out near output.

STATUS: NEXP ⊄ P/poly NOT proved. Proof has a gap.
"""

print("CRITICAL FLAW: Covariance dampens with distance from fan-out to output.")
print()
print("For fan-out at distance k from output: Cov ≈ exp(-Ck).")
print("Adversary places fan-out at bottom → distance = circuit depth → Cov → 0.")
print()
print("The cascade argument works for 3-SAT (fan-out near output).")
print("DOES NOT work for general circuits (fan-out can be far from output).")
print()
print("NEXP ⊄ P/poly: NOT PROVED. Gap = damping over formula layers.")
