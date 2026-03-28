"""
CURVATURE-SIZE THEOREM: Combining curvature bound with Main Theorem.

For circuit C computing CLIQUE:
  Case 1 (formula, f̄ = 1): size = formula ≥ 2^{Ω(√N)} (Alon-Boppana + Thm 1)
  Case 2 (circuit, f̄ > 1): κ ≈ -(f̄-1)/(2+f̄). Volume growth → size ≥ (1+h)^D.

Case 1: size ≥ 2^{c√N} for AB constant c.
Case 2: size ≥ (1+h)^D where D ≥ depth ≥ √N - O(log N) from Main Thm.
  h depends on f̄. For f̄ = 2: h ≈ 1/5. size ≥ 1.2^{√N}.

COMBINED: size ≥ max(2^{c√N}, (1+h(f̄))^{√N}).

For f̄ = 1 (formula): 2^{c√N}. For f̄ = 2: 1.2^{√N} = 2^{0.26√N}.

For c > 0.26: formula bound dominates. size ≥ 2^{c√N} always.
For c < 0.26: at f̄ = 2: curvature gives 2^{0.26√N} > 2^{c√N}. Better!

The adversary minimizes max over both bounds. Optimal f̄ = ???

OPTIMIZATION:
  Formula bound: 2^{c√N} / f̄^D (fan-out reduces formula → size = formula/fan-out^D... no).
  Actually: size × 2^D ≥ formula. size ≥ formula / 2^D.
  For D = sqrt(N): size ≥ 2^{c√N} / 2^{√N} = 2^{(c-1)√N}.
  For c > 1: SUPER-POLY regardless of f̄!

THE KEY: Is the Alon-Boppana constant c > 1 (in units where D = √N)?

More precisely: formula(CLIQUE) ≥ 2^{c√N}. Depth = D ≤ s.
size ≥ formula / 2^D ≥ 2^{c√N} / 2^s.

If s < c√N: 2^{c√N - s} > 1. size > 1. Not useful directly.
If s < (c-ε)√N: size > 2^{ε√N}. Super-poly!

So: need s ≥ (c-ε)√N for any ε. I.e., size ≥ c√N.
But: c√N = polynomial (√N = n^{1/4}). NOT super-poly.

WAIT: formula ≥ 2^{c√N}. And: formula ≤ size × 2^{size} (depth ≤ size).
So: size × 2^{size} ≥ 2^{c√N}.
2^{size} ≥ 2^{c√N} / size.
size ≥ c√N - log(size).
For size = poly: c√N - log(poly) ≈ c√N.
size ≥ c√N = c × n^{1/4}. POLYNOMIAL. Not super-poly.

For super-poly: need formula ≥ 2^{cn} (exponential in n).
Current: formula ≥ 2^{c√N} = 2^{cn^{1/4}}. Sub-exponential.

GAP: 2^{n^{1/4}} vs 2^n. Factor n^{3/4} in the exponent.
"""

import math

print("CURVATURE-SIZE ANALYSIS")
print("=" * 55)
print()
print("Formula(CLIQUE) ≥ 2^{c × N^{1/2}} (Alon-Boppana)")
print("Depth ≤ size. Formula ≤ size × 2^{depth} ≤ size × 2^{size}.")
print("→ size ≥ c × N^{1/2} - log(size) ≈ c × n^{1/4}")
print()
print("This is POLYNOMIAL in n (n^{1/4}), NOT super-polynomial.")
print()
print("For super-poly circuit bound: need formula ≥ 2^{cn}")
print("(exponential in input length, not sub-exponential).")
print()
print("Current best: 2^{c × n^{1/4}}. Gap: n^{1/4} vs n.")
print()
print("To close gap: improve Alon-Boppana from 2^{√N} to 2^{N²}.")
print("This = 37+ year open problem in monotone circuit complexity.")
print()

for c_exp in [0.25, 0.5, 0.75, 1.0]:
    print(f"  If formula ≥ 2^{{n^{{{c_exp}}}}}: circuit ≥ n^{{{c_exp}}} = ", end="")
    if c_exp < 1:
        print(f"SUB-LINEAR (n^{{{c_exp}}} < n). Not useful.")
    else:
        print(f"LINEAR. Still not super-poly.")

print()
print("For SUPER-POLY: need exponent > 1 in 2^{n^{exp}}.")
print("I.e., formula ≥ 2^{n^{1+ε}} for some ε > 0.")
print("This exceeds 2^n (truth table size!) → IMPOSSIBLE.")
print("Formula ≤ 2^n always (at most 2^n leaves).")
print()
print("SO: formula ≤ 2^n AND circuit ≥ formula / 2^{circuit}")
print("→ circuit ≥ n (at best). NEVER super-polynomial from this chain.")
print()
print("THE FUNDAMENTAL LIMIT:")
print("  formula ≤ 2^n (trivial upper bound)")
print("  formula / 2^{circuit} ≤ size (formula-circuit conversion)")
print("  → size ≥ formula / 2^{size}")
print("  → size × 2^{size} ≥ formula")
print("  → 2^{size} ≥ formula / size")
print("  → size ≥ log(formula) - log(size)")
print("  → size ≥ log(formula) (roughly)")
print()
print("log(2^n) = n. So: size ≥ n. THE LOG BARRIER. INESCAPABLE.")
print()
print("EVERY PATH through formula → circuit conversion")
print("hits the log barrier: size ≥ log(formula) = O(n).")
print()
print("To break through: MUST NOT go through formula-circuit conversion.")
print("Need DIRECT circuit lower bound without formulas.")
