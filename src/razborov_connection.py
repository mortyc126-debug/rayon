"""
CONNECTING Φ TO RAZBOROV'S APPROXIMATION METHOD.

Razborov's method for monotone circuit lower bounds:
  1. Define approximation A: functions → set families.
  2. A(AND) = A(g) ∩ A(h). A(OR) = A(g) ∪ A(h).
  3. Error per gate: |A(gate) Δ gate| ≤ δ.
  4. Total error ≤ s × δ.
  5. Need: total error ≥ |A(CLIQUE) Δ CLIQUE| = "distance."
  6. s ≥ distance / δ.

The distance = how far CLIQUE is from any "simple" set family.
The error δ = how much each gate perturbs the approximation.

OUR Φ: Φ(f) = consistency × compression × composability.
Each gate: Φ changes (conservation law).

CONNECTION HYPOTHESIS:
  Razborov's "distance" ∝ Φ(CLIQUE).
  Razborov's "error δ" ∝ 1/Φ-change-per-gate.

If Φ(CLIQUE) = 2^{Ω(N)}: distance = 2^{Ω(N)}.
With δ = O(1): s ≥ 2^{Ω(N)}. EXPONENTIAL in N!

Current Razborov/Alon-Boppana: distance = 2^{Ω(√N)}.
Our Φ(CLIQUE) for N=6 (Triangle): Φ ≈ 10^7 (from data).
Extrapolating: Φ ∝ n^{10.5} (from power-law fit).

For Φ = n^{10.5}: distance = n^{10.5}?
s ≥ n^{10.5} / δ. With δ = O(1): s ≥ n^{10.5}. SUPER-POLYNOMIAL!

BUT: Φ is NOT Razborov's "distance." The connection is hypothetical.

EXPERIMENT: Compute Razborov's actual distance for small CLIQUE
instances and compare with Φ.
"""

import math

print("HYPOTHESIS: Razborov distance ∝ Φ(CLIQUE)")
print("=" * 50)
print()
print("Our measurements:")
print(f"  Φ(Triangle K4, n=6):  ≈ 648")
print(f"  Φ(Triangle K5, n=10): ≈ 95,400")
print(f"  Φ(Triangle K6, n=15): ≈ 10,049,655")
print(f"  Φ growth: n^{10.5}")
print()
print("Razborov/Alon-Boppana distance:")
print(f"  2^{{Ω(√N)}} where N = number of vertices")
print(f"  For K6 (N=6): 2^{{√6}} ≈ 2^2.45 ≈ 5.5")
print(f"  For K10 (N=10): 2^{{√10}} ≈ 2^3.16 ≈ 9")
print()
print("Our Φ vs Razborov distance:")
print(f"  K4: Φ=648 vs Raz≈4.       Ratio: {648/4:.0f}")
print(f"  K5: Φ=95400 vs Raz≈5.5.   Ratio: {95400/5.5:.0f}")
print(f"  K6: Φ=10M vs Raz≈9.       Ratio: {10049655/9:.0f}")
print()
print("Φ grows MUCH faster than Razborov's bound!")
print("Φ ~ n^{10.5} while Razborov ~ 2^{n^{1/4}} ~ n^{O(1)}.")
print()
print("IF Φ could replace Razborov's distance:")
print(f"  s ≥ Φ / δ = n^{{10.5}} / O(1) = n^{{10.5}}")
print(f"  SUPER-POLYNOMIAL monotone lower bound!")
print(f"  depth ≥ log(n^{{10.5}}) = 10.5 log n. Only logarithmic :(")
print()
print("Even with Φ as distance: depth bound = O(log n). Not helpful.")
print("Because: Φ = n^{10.5} is POLYNOMIAL, not exponential.")
print("Need: Φ = 2^{Ω(n)} for exponential distance → linear depth.")
print()
print("Our Φ for large n: Φ ~ n^{α(k)} where α(k) ~ 1.74k.")
print(f"For k=N^{{1/3}}: α = 1.74N^{{1/3}}. Φ ~ n^{{1.74N^{{1/3}}}}.")
print(f"This is n^{{N^{{1/3}}}} = 2^{{N^{{1/3}} log n}} = 2^{{Ω(n^{{1/6}} log n)}}.")
print(f"Exponent: n^{{1/6}} × log n. Compare Alon-Boppana: n^{{1/4}}.")
print(f"Our Φ-based bound WEAKER than Alon-Boppana!")
print()
print("CONCLUSION: Φ doesn't improve on Razborov for monotone bounds.")
print("The power-law growth (polynomial, not exponential) is insufficient.")
