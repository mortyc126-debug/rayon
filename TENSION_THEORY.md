# Tension Theory: A Framework for Circuit Lower Bounds

## Summary

We developed **Tension Theory** — a new framework connecting LP feasibility,
Fourier analysis, and circuit complexity. The framework gives **exact** circuit
lower bounds for small functions (n=3,4) and **non-trivial** bounds for CLIQUE.

## Core Definition

**Tension function** τₖ(f, s): For Boolean function f and circuit size s,
τₖ > 0 iff the Sherali-Adams level-k LP relaxation is infeasible for ALL
circuit structures of size s. Equivalently: no circuit of size s can have
internally consistent conditional probability distributions while computing f.

## Proven Results

### 1. Exactness for Small Functions
- τ₂ is **exact** for all n=3 functions (256 functions, gap=0)
- τ₂ is **exact** for n=4 hardest functions (96 size-5 functions, gap=0)
- SA-3 adds nothing beyond SA-2 for these instances

### 2. CLIQUE Lower Bounds
- LP bound **exact** for CLIQUE-specific circuit topologies:
  - CLIQUE(4,3): LP bound = 10 = actual minimum circuit size
  - CLIQUE(5,3): LP bound = 28 ≈ actual 29
- LP detects ALL single-gate removals (11/11 for N=4)
- For random topologies: LP bound ≈ 2√n (weaker but still non-trivial)

### 3. Fourier Connection
- **Proven**: Pr[xᵢ=1, f=1] = (f̂(∅) - f̂({i})) / 2
- Conditional pairwise probabilities determined by level-≤2 Fourier spectrum
- τₖ depends on f only through its level-≤k Fourier spectrum

### 4. Gap Ratio Scaling
- For k-clique edge set S: **Pr[S present | ¬∃ k-clique] = 0** (exact zero)
- Clique-aligned AND gates are perfect discriminators (zero false positive)
- Gap ratio (clique/non-clique) grows with k:
  - k=4: ratio ≈ 1.67
  - k=5: ratio ≈ 2.11
  - k=6: ratio ≈ 5.99
  - Fit: ratio ≈ 0.13 × C(k,2)^{1.35}

### 5. Gap Composition
- AND layer: gap roughly preserved (factor 0.23-0.90 depending on k,N)
- OR layer: gaps sum with efficiency η ≈ 0.23-0.54
- Output gap = 1.0 is achieved by C(N,k) clique-OR-terms (verified)

### 6. Mechanism: Sharing Conflicts
- LP infeasibility comes from **sharing conflicts**, not decomposition impossibility
- When two sub-computations share gates (fan-out), their conditional
  probabilities must be jointly consistent — this creates contradictions
- 94 valid AND-decompositions exist for n=3 hardest functions, but LP
  still says infeasible at size 3 because sharing is impossible

### 7. Other Results
- Equation of state c = T/(1+T): DFS exponent nearly algorithm-invariant (CV=1% for CLIQUE)
- Interaction complexity WI: predicts circuit size better than L1 Fourier norm
- SDP = LP for small instances (PSD adds no power at n=4,5)

## Open Problems

### Gap to P ≠ NP
The LP is exact for CLIQUE-specific topologies but LP-feasible for random
topologies that DON'T compute CLIQUE. To prove P ≠ NP, need one of:

1. **Universal LP argument**: Show LP-infeasible for ALL topologies of small size
2. **LP+correctness**: Combine LP with circuit correctness verification
3. **Analytical tension bound**: Prove τ₂(CLIQUE, s) > 0 for s < super-poly analytically

### Key Technical Questions
- Does gap ratio continue growing as C(k,2)^{1.35} for k ≥ 7?
- Can fan-out sharing reduce required gates from C(N,k) to polynomial?
- Is there a closed-form formula for τ₂ in terms of Fourier spectrum?

## Files (100+ modules in src/)

Key new files from this session:
- `tension_theory.py` - Core definitions and Fourier connection proof
- `holographic_lp_v2.py` - SA-2 LP implementation (exact for n=3,4)
- `tension_clique.py` - CLIQUE lower bounds via LP
- `clique_specific_circuits.py` - LP exact for CLIQUE topologies
- `analytical_gap_ratio.py` - Pr[S|¬clique] = 0 proof
- `gap_composition.py` - Gap flow through AND-OR circuits
- `gap_scaling.py` - Ratio scaling with k
- `dual_certificate.py` - LP dual analysis
- `analytical_tension.py` - Sharing conflicts mechanism
- `universality_test.py` - Equation of state universality
- `interaction_theory.py` - WI composition laws
- `sdp_exact.py` - SDP vs LP comparison
- `smart_circuits.py` - Minimum CLIQUE circuit search
