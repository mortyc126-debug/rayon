"""
RESIDUAL CIRCUIT IS A FORMULA.

After cascade: fraction p = 8/9 determined.
Undetermined fraction: 1-p = 1/9.

Undetermined gate g: has fan-out to some gates.
Each child gate: undetermined with prob 1/9.

Expected undetermined children per undetermined gate:
  fan-out × (1-p) = 2 × 1/9 = 2/9 < 1.

SUB-CRITICAL branching in residual → residual is TREE-LIKE (formula).

Residual = formula of size ≈ s/9 on n/2 free variables.

For CLIQUE UNSAT instances:
  Residual formula proves "no k-clique given fixed edges."
  Formula proof of "no k-clique" ≥ monotone formula ≥ 2^{Ω(√N)}.
  (From Razborov + Theorem 1.)

  s/9 ≥ 2^{Ω(√N)} → s ≥ 9 × 2^{Ω(√N)} = SUPER-POLYNOMIAL.

THIS PROVES: any circuit for CLIQUE has size ≥ super-polynomial → P ≠ NP.

BUT: the residual is formula ONLY IF effective fan-out < 1 in residual.
Effective fan-out = 2/9 < 1 for p = 8/9. ✓

HOWEVER: p = 8/9 is for the PERCOLATION MODEL (dual-parent boost).
The model is APPROXIMATE. Real p might be different.

AND: the Razborov bound applies to the RESIDUAL function, which is
"CLIQUE restricted to partially fixed edges." This restricted function
might be EASIER than full CLIQUE.

For random restriction fixing n/2 edges: residual CLIQUE is CLIQUE
on remaining edges with some edges fixed. This is STILL hard:
  - Fixed edges to 1: still need remaining edges to form clique.
  - Fixed edges to 0: eliminate some candidate cliques.
  - Residual: CLIQUE on smaller instance with constraints.

Razborov's bound for monotone: applies to ANY monotone function
that computes CLIQUE (even restricted). The restriction doesn't
change the monotone complexity (Alon-Boppana applies to restrictions).

Actually: restriction REDUCES the function complexity (simpler problem).
Restricted CLIQUE might have poly formula complexity.

For random restriction: by switching lemma arguments, many functions
SIMPLIFY to low-depth decision trees. CLIQUE under restriction:
might simplify to depth-d tree with d = O(k²/p) = O(N^{2/3}/p).

If d = poly(n): formula = poly. Residual formula = poly. s/9 ≥ poly → s ≥ poly.
NO super-poly bound.

THE FLAW: restricted CLIQUE might be EASY (poly formula after restriction).
Razborov bound for FULL CLIQUE ≠ bound for RESTRICTED CLIQUE.

CHECKING:
  Alon-Boppana: 2^{Ω(√N)} for CLIQUE on N vertices.
  After fixing n/2 edges: effectively CLIQUE on N vertices with some
  edges predetermined. The MONOTONE complexity of this restricted
  function: ≤ monotone complexity of full CLIQUE (restriction can
  only SIMPLIFY).

  So: residual formula ≤ 2^{Ω(√N)}. Not ≥.
  The residual might be MUCH simpler.

  s/9 = residual complexity ≤ residual function formula ≤ full formula.
  This gives: s/9 ≤ 2^{Ω(√N)}. Which means: s ≤ 9 × 2^{Ω(√N)}.
  This is an UPPER bound, not a lower bound. WRONG DIRECTION.

CORRECTION: The residual formula LOWER BOUND:
  residual formula ≥ ??? depends on how much restriction simplifies.

  For random restriction fixing half edges:
  Expected CLIQUE complexity after restriction = ???

  If restriction preserves complexity: residual ≥ 2^{Ω(√N)} → P ≠ NP.
  If restriction simplifies: residual = poly → no conclusion.

  From our random restriction experiments: boundary stays robust
  (base ~1.8 after fixing half). Suggests: complexity PRESERVED.

  But: boundary base ≠ formula complexity. Different measures.
"""

import math

print("RESIDUAL FORMULA ANALYSIS")
print("=" * 50)
print()
print("After cascade (p = 8/9):")
print(f"  Undetermined gates: {1/9:.3f} fraction = s/9")
print(f"  Effective fan-out in residual: 2 × {1/9:.3f} = {2/9:.3f} < 1")
print(f"  → Residual is FORMULA-LIKE (sub-critical branching)")
print()
print("Residual proves 'no k-clique given fixed edges'")
print(f"  Residual formula ≥ ??? (depends on restriction effect)")
print()
print("IF residual formula ≥ 2^{{Ω(√N)}} (complexity preserved):")
print(f"  s/9 ≥ 2^{{Ω(√N)}} → s ≥ super-poly → P ≠ NP! ✓")
print()
print("IF residual formula = poly (restriction simplifies):")
print(f"  s/9 ≥ poly → s ≥ poly → no conclusion ✗")
print()
print("THE KEY QUESTION:")
print("  Does random restriction PRESERVE monotone formula complexity of CLIQUE?")
print()
print("From our experiments (boundary base after restriction):")
print(f"  Original: ~1.9^n")
print(f"  After 50% restriction: ~1.8^{{n/2}} (slightly lower base)")
print(f"  Suggests: complexity partially preserved.")
print()
print("For formal proof: need Alon-Boppana type bound for RESTRICTED CLIQUE.")
print("This is a specific mathematical question:")
print("  monotone_formula(CLIQUE | random half-restriction) ≥ ???")
