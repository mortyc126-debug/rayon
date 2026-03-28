"""
STRUCTURAL METRIC: Distance = complexity of the DIFFERENCE.

Standard Hamming: d(f,g) = |{x: f(x) ≠ g(x)}|. Can be 2^{n-1}.
One AND gate can cause distance 2^{n-1}. Too powerful.

NEW METRIC: d_C(f,g) = circuit_complexity(f ⊕ g)
where f ⊕ g is the XOR (symmetric difference) of truth tables.

This measures: how COMPLEX is the set where f and g differ?
If the difference is "structured" (simple function): small distance.
If the difference is "unstructured" (complex function): large distance.

KEY PROPERTY:
  d_C(g, AND(g,h)) = complexity(g ⊕ (g∧h)) = complexity(g ∧ ¬h)
  = complexity(g) + complexity(h) + O(1)  (just AND + NOT)

Wait, that's not right. complexity(g ∧ ¬h) ≤ complexity(g) + complexity(h) + 2.
So: d_C(g, AND(g,h)) ≤ complexity(g) + complexity(h) + 2.

For a circuit of size s where g and h are computed:
  complexity(g) ≤ s, complexity(h) ≤ s.
  So: d_C ≤ 2s + 2 per gate.

Total distance through s gates: ≤ s × (2s + 2) = O(s²).

NEED: d_C(input, CLIQUE) ≥ ???

d_C(x_i, CLIQUE) = complexity(x_i ⊕ CLIQUE) = complexity of the function
that's 1 iff exactly one of x_i and CLIQUE is true.
= complexity(CLIQUE) + O(1) (just XOR with x_i).

So: d_C(input, CLIQUE) = complexity(CLIQUE) + O(1) ≈ complexity(CLIQUE).

And: total distance through s gates ≤ O(s²).
Therefore: s² ≥ complexity(CLIQUE) → s ≥ √(complexity(CLIQUE)).

IF complexity(CLIQUE) = super-poly: s ≥ super-poly^{1/2} = super-poly!

But: complexity(CLIQUE) = circuit_complexity(CLIQUE) = s itself.
So: s² ≥ s → s ≥ 1. CIRCULAR!

THE FIX: Use a DIFFERENT complexity measure for the metric.
Not circuit complexity, but something we can bound independently.

OPTION 1: d_F(f,g) = formula_complexity(f ⊕ g).
Per gate: d_F(g, AND(g,h)) ≤ formula(g ∧ ¬h) ≤ formula(g) × formula(h).
This is MULTIPLICATIVE — bad (total distance can be huge).

OPTION 2: d_R(f,g) = rank of the "difference matrix" f ⊕ g.
Where rank = GF(2) rank of the truth table viewed as matrix.
For n even: view {0,1}^n as {0,1}^{n/2} × {0,1}^{n/2}.
d_R(f,g) = rank of M where M[x₁,x₂] = f(x₁,x₂) ⊕ g(x₁,x₂).

Per gate: d_R(g, AND(g,h)) = rank(g ⊕ g∧h) = rank(g ∧ ¬h).
rank(a ∧ b) ≤ rank(a) × rank(b) (tensor product bound).
rank(¬h) = rank of complement... hmm, this gets complicated.

OPTION 3: d_S(f,g) = sensitivity of f ⊕ g.
sensitivity(f⊕g) = max_x |{i : (f⊕g)(x) ≠ (f⊕g)(x⊕eᵢ)}|.

Per gate: sensitivity(g ⊕ g∧h) = sensitivity(g∧¬h).
sensitivity(a∧b) ≤ sensitivity(a) + sensitivity(b) (sub-additive).
So: d_S(g, AND(g,h)) ≤ sensitivity(g) + sensitivity(¬h) + O(1)
                      ≤ sensitivity(g) + sensitivity(h) + O(1).

For input: sensitivity(x_i) = 1.
After s gates: max sensitivity ≤ s + n.
d_S(input, f) ≤ sensitivity(f) + n.

Need: sensitivity(CLIQUE) = ???
sensitivity(k-CLIQUE) = C(k,2) = k(k-1)/2.
For k = N^{1/3}: sensitivity = O(N^{2/3}).

d_S ≤ s + n per gate. Total: s × (s + n).
s × (s+n) ≥ sensitivity(CLIQUE) = O(N^{2/3}).
s ≥ √(N^{2/3}) = N^{1/3}. SUPER-LINEAR but weak.

OPTION 4: Use BLOCK sensitivity or certificate complexity.
bs(k-CLIQUE) = C(k,2) = O(k²) for positive certificate.
Negative certificate: up to C(N-1, k-1) (many edges needed).

Actually, let me think about this completely differently.

THE REAL QUESTION: What property of a function CANNOT be achieved
by polynomial circuits, that grows super-polynomially, and is
SUB-ADDITIVE (not sub-multiplicative) under AND/OR?

Sub-additive: μ(AND(g,h)) ≤ μ(g) + μ(h) + c.
Then: μ(f) ≤ s × max_μ_per_gate ≤ s × (2 × max_intermediate_μ + c).
If max_intermediate ≤ μ(f): μ(f) ≤ s × (2μ(f) + c) → 1 ≤ 2s → s ≥ 1/2.

The problem: if μ is sub-additive and intermediate μ can be up to μ(f),
we get only s ≥ O(1).

NEED: μ where intermediate values are BOUNDED (not up to μ(f)).

μ(AND(g,h)) ≤ μ(g) + μ(h) + c.
If μ(x_i) = 1 and μ grows through composition:
After s AND/OR: μ ≤ 2^s (exponential growth via binary tree).
But with fan-out: μ of shared gate counted ONCE.

In a circuit: the output μ(f) is computed from inputs through s gates.
μ(f) ≤ Σ_{path from input to output} (contribution per gate along path).
Max path length = depth d.
Per-gate contribution: O(1) if sub-additive.
μ(f) ≤ d × O(1) per path, but multiple paths combine multiplicatively...

Actually for sub-additive μ: μ(AND(g,h)) ≤ μ(g) + μ(h) + c.
Starting from μ(x_i) = 1:
After d compositions: μ ≤ d + c×d (linear in depth).
For depth d = s: μ ≤ O(s).

So: μ(f) ≤ O(s) for sub-additive μ.
If μ(CLIQUE) = super-poly: s ≥ super-poly! P ≠ NP!

Wait — is this right? Let me check.

μ(gate1(x₁,x₂)) ≤ μ(x₁) + μ(x₂) + c = 1 + 1 + c = 2 + c.
μ(gate2(gate1, x₃)) ≤ μ(gate1) + μ(x₃) + c = (2+c) + 1 + c = 3 + 2c.
μ(gate_k(...)) ≤ k + (k-1)c after k gates in a CHAIN.

For a circuit of size s: the OUTPUT is computed after at most s gates.
In a chain (depth = s): μ ≤ s + (s-1)c = O(s).
In a tree (depth = log s): μ ≤ log(s) + (log s - 1)c = O(log s). EVEN BETTER!
With fan-out: a gate's μ is computed ONCE but used multiple times.
The OUTPUT μ depends on the LONGEST PATH, not the total size.

μ(output) ≤ depth × (1 + c) + n. (n inputs at the start.)

For depth d = O(s): μ ≤ O(s). So s ≥ μ(f) / O(1). If μ(f) = super-poly: DONE!
For depth d = O(log n): μ ≤ O(log n). So if μ(f) ≥ ω(log n): d > log n.

This is a DEPTH lower bound, not a size lower bound.

For SIZE: even with depth = s, μ ≤ O(s). So s ≥ μ(f).
IF μ(f) = super-poly AND μ is truly sub-additive: s ≥ super-poly!!!

THE KEY: Does a sub-additive μ exist with μ(CLIQUE) = super-poly?

All known sub-additive measures (sensitivity, degree, certificate):
μ(k-CLIQUE) = O(k²) = O(N^{2/3}) = POLYNOMIAL.

NONE are super-polynomial.

IS THERE AN UNKNOWN sub-additive measure with super-poly value?

By Huang's theorem (2019): sensitivity ≥ √degree.
All polynomial measures are polynomially related (sensitivity, degree,
certificate, block sensitivity, decision tree complexity — all poly of each other).

So: if ANY of these is polynomial, ALL are polynomial.

For CLIQUE: all are polynomial (degree = C(k,2), sensitivity = C(k,2), etc.)

IS THERE A sub-additive measure OUTSIDE this equivalence class?

Maybe. But it would need to be fundamentally different from all
known complexity measures. This is exactly what's needed for P ≠ NP.
"""


def main():
    print("The structural metric analysis is theoretical.")
    print("Key finding: a sub-additive measure with super-poly value")
    print("would prove P ≠ NP via: s ≥ μ(f) / O(1).")
    print()
    print("But all known sub-additive measures (sensitivity, degree,")
    print("certificate, block sensitivity) are POLYNOMIAL for CLIQUE.")
    print()
    print("Need: a NEW sub-additive measure outside the known equivalence class.")
    print("This is equivalent to inventing a new complexity measure —")
    print("the exact frontier of P vs NP research.")


if __name__ == "__main__":
    main()
