"""
DERIVATION OF EQUATION OF STATE c = T/(1+T).

Starting from logistic cascade model:

1. CASCADE EQUATION (from our experiments):
   p_{d+1} = p_d + δ × p_d × (1 - p_d)

   where p_d = fraction of determined gates at depth d.
   δ = cascade rate = f(curvature, fan-out).

   Solution: p(d) = 1 / (1 + ((1-p₀)/p₀) × e^{-δd})

   For p₀ = 1/2 (half variables fixed):
   p(d) = 1 / (1 + e^{-δd})  =  σ(δd)

2. CASCADE RATE δ:
   From Covariance Lemma: Cov ≥ p(1-p)²|κ|/4.
   Per-layer boost: δ ≈ width × |κ| / 4 × p(1-p).
   At p = 1/2: δ ≈ width × |κ| / 16.

   Width = s/D (circuit size / depth).
   So: δ ≈ s|κ| / (16D).

3. DFS NODES:
   DFS at depth k explores 2^k branches.
   At each: output determined with prob p(D-k) (cascade from bottom).

   For cascade from bottom reaching depth D:
   p(D) = σ(δD) = σ(s|κ|/16).

   Fraction surviving (not determined) at DFS depth n/2:
   q = 1 - p(D) = 1 - σ(s|κ|/16) = σ(-s|κ|/16) = 1/(1 + e^{s|κ|/16}).

   Total DFS nodes ≈ 2^{n/2} × q = 2^{n/2} / (1 + e^{s|κ|/16}).

   c = log₂(nodes)/n ≈ 1/2 + log₂(q)/n = 1/2 - s|κ|/(16n × ln2).

4. CONNECTING TO α:
   Φ ∝ n^α. For the circuit: Φ grows with circuit structure.
   From conservation law: Φ ≈ n × fan_out × Φ_per_input ≈ s × something.
   Φ ∝ s (roughly). So: α ≈ log(s/n)/log(n) for s = n^α.

   But: our equation uses α × |κ|. Let's see what this predicts.

   s = n^α (if circuit size scales as n^α for the function).
   Then: s|κ|/(16n) = n^α × |κ| / (16n) = n^{α-1} × |κ| / 16.

   c ≈ 1/2 - n^{α-1} × |κ| / (16 ln 2).

   For α > 1 (super-linear circuit): second term → ∞. c → -∞.
   But c ≥ 0. So: c ≈ 0 when cascade reduces all branches.

   Wait — this predicts c → 0 for large circuits. OPPOSITE of what we want.

   THE ISSUE: larger circuit → MORE cascade → MORE pruning → LOWER c.
   But: we observed c ≈ 0.6-0.7 for SAT (NOT c → 0).

   RESOLUTION: our formula circuits are SIZE ≈ O(n) (formula-like).
   s/n ≈ constant (not n^α).

   The α in our equation is NOT circuit size exponent.
   α = Φ GROWTH exponent. Φ ∝ n^α.

   Φ and s are DIFFERENT: Φ = potential (property of function),
   s = circuit size (property of circuit).

   For the OPTIMAL circuit: s = circuit_complexity(f).
   Φ ≥ some function of s (from conservation law).

   From conservation: Φ ≈ s × |κ| × something (curvature × size).

   THEN: α ≈ log(Φ)/log(n) ≈ log(s × |κ|)/log(n).

   T = α × |κ| ≈ |κ| × log(s × |κ|) / log(n).

   For s = n^c_circuit (polynomial circuit):
   T ≈ |κ| × (c_circuit × log n + log|κ|) / log n ≈ c_circuit × |κ|.

   c_cascade = T/(1+T) = c_circuit × |κ| / (1 + c_circuit × |κ|).

   THIS RELATES cascade exponent TO circuit size!

   For c_circuit = 1 (linear size), |κ| = 0.5: T = 0.5. c = 0.33.
   For c_circuit = 2 (quadratic), |κ| = 0.5: T = 1. c = 0.5.
   For c_circuit = ∞ (exponential), |κ| = 0.5: T → ∞. c → 1.

   THIS MAKES SENSE:
   - Small circuits → low T → low c → fast SAT (easy)
   - Large circuits → high T → high c → slow SAT (hard)
   - Minimum circuit = NP-hard → c close to 1

5. THE EQUATION OF STATE DERIVED:

   c_cascade = c_circuit × |κ| / (1 + c_circuit × |κ|)

   where c_circuit = log(circuit_size) / log(n).

   Rearranging: c_circuit = c_cascade / (|κ| × (1 - c_cascade)).

   For c_cascade = 0.6, |κ| = 0.5:
   c_circuit = 0.6 / (0.5 × 0.4) = 0.6 / 0.2 = 3.0.

   PREDICTION: optimal MSAT circuit has size ≈ n^3.

   For c_cascade = 0.7, |κ| = 0.5:
   c_circuit = 0.7 / (0.5 × 0.3) = 0.7 / 0.15 = 4.67.

   PREDICTION: optimal CLIQUE circuit has size ≈ n^{4.67}.

   For c_cascade → 1 (exponential):
   c_circuit → ∞. Size = super-poly. P ≠ NP!

   But: c_cascade < 1 always (from our data, c ≈ 0.6-0.7).
   So: c_circuit = finite. Size = polynomial. P = NP???

   WAIT: c measured on SPECIFIC circuits (formula-like, non-optimal).
   The c for OPTIMAL circuit might be DIFFERENT.

   For optimal circuit: minimum size → minimum cascade.
   Optimal circuit has LEAST redundancy → cascade works WORST.
   c_optimal = HIGHEST c among all circuits computing f.

   If c_optimal → 1 for CLIQUE as n → ∞: P ≠ NP.
   If c_optimal < 1: P = NP possible.

   We measured c on NON-OPTIMAL circuits. c_optimal ≥ c_measured.
   c_measured ≈ 0.6-0.7. c_optimal could be higher.

   THE KEY: c_optimal for CLIQUE as n → ∞.
   Equation: c_optimal = c_circuit* × |κ*| / (1 + c_circuit* × |κ*|)
   where c_circuit* = log(circuit_complexity)/log(n), κ* = curvature of optimal circuit.

   IF circuit_complexity = super-poly: c_circuit* → ∞. c_optimal → 1.
   IF circuit_complexity = poly: c_circuit* = O(1). c_optimal < 1.

   CIRCULAR AGAIN (c depends on circuit complexity which is unknown).

   BUT: the equation RELATES measurable quantities (c, κ) to
   the UNKNOWN (circuit complexity). If we measure c and κ on
   optimal circuits: we can COMPUTE circuit complexity!

   circuit_complexity = n^{c/(|κ|(1-c))}

   For c = 0.6, |κ| = 0.5: complexity = n^{0.6/0.2} = n^3.
   For c = 0.7, |κ| = 0.5: complexity = n^{0.7/0.15} = n^{4.67}.

   These are PREDICTIONS of circuit complexity from measurable data!
"""

import math

print("DERIVED EQUATION OF STATE")
print("=" * 55)
print()
print("c_cascade = c_circuit × |κ| / (1 + c_circuit × |κ|)")
print()
print("Rearranged: c_circuit = c_cascade / (|κ| × (1 - c_cascade))")
print()
print("PREDICTIONS of circuit complexity from measured c and κ:")
print(f"{'c':>6} {'|κ|':>6} {'c_circuit':>10} {'size':>15}")
print("-" * 40)

for c_val in [0.1, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99]:
    kappa = 0.5
    if c_val >= 1:
        c_circ = float('inf')
        size_str = "super-poly"
    else:
        c_circ = c_val / (kappa * (1 - c_val))
        size_str = f"n^{{{c_circ:.1f}}}"

    print(f"{c_val:>6.2f} {kappa:>6.2f} {c_circ:>10.2f} {size_str:>15}")

print(f"""
FROM OUR DATA:
  MSAT (c≈0.7, κ≈0.5): circuit ≈ n^{0.7/(0.5*0.3):.1f} = n^{4.7}
  TRIANGLE (c≈0.7, κ≈0.5): circuit ≈ n^{4.7}
  OR (c≈0.0, κ≈0.3): circuit ≈ n^{0.0} = O(1). ✓ (OR = trivial)

For P ≠ NP: need c → 1 on OPTIMAL circuits for CLIQUE.
  c → 1: c_circuit → ∞ → size = super-polynomial.

For P = NP: c stays < 1 on optimal CLIQUE circuits.
  c < 1: c_circuit < ∞ → size = polynomial.

THE EQUATION CONVERTS BETWEEN:
  Observable (c, κ) → Non-observable (circuit complexity).

This is like E = mc²: converts between mass (hard to see)
and energy (easy to measure).
""")
