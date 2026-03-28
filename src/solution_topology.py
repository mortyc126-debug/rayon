"""
TOPOLOGY OF SOLUTION SPACES: A genuinely new approach.

f⁻¹(1) ⊆ {0,1}^n = subset of the Boolean hypercube.

The SIMPLICIAL COMPLEX of f⁻¹(1): vertices = solutions,
edges = pairs at Hamming distance 1, triangles = triples at
pairwise distance 1, etc.

BETTI NUMBERS: β₀ = connected components, β₁ = 1-holes, etc.

TOTAL BETTI NUMBER: β(f) = Σ βₖ.

HYPOTHESIS: β(f) ≤ g(circuit_size(f)) for some function g.
If β(CLIQUE) = super-poly AND g = poly: circuit ≥ super-poly.

WHY THIS MIGHT WORK:
  1. Topology is NOT counting (Betti = structural, not cardinality)
  2. AND/OR gates change topology in BOUNDED ways:
     AND: intersects two sets → topology can increase or decrease
     OR: unions two sets → Mayer-Vietoris → bounded change
  3. Each gate changes β by at most ??? → s ≥ β(f) / max_change

KEY: How much can one AND/OR gate change β?

AND: f⁻¹(1) = g⁻¹(1) ∩ h⁻¹(1). By Mayer-Vietoris:
  β(g∩h) ≤ β(g) + β(h) + β(g∪h). ADDITIVE.

OR: f⁻¹(1) = g⁻¹(1) ∪ h⁻¹(1). By Mayer-Vietoris:
  β(g∪h) ≤ β(g) + β(h) + β(g∩h). ADDITIVE.

So: β is SUB-ADDITIVE under AND/OR? Let's check.

β(AND(g,h)) = β(g⁻¹(1) ∩ h⁻¹(1)) ≤ β(g) + β(h) + β(g∪h) ≤ 2β(g) + 2β(h).
Hmm, this doesn't bound nicely because β(g∪h) involves both.

ACTUALLY: Mayer-Vietoris exact sequence:
  ... → Hₖ(A∩B) → Hₖ(A) ⊕ Hₖ(B) → Hₖ(A∪B) → Hₖ₋₁(A∩B) → ...

This gives: β_k(A∪B) ≤ β_k(A) + β_k(B) + β_{k-1}(A∩B).
And: β_k(A∩B) ≤ β_k(A) + β_k(B) + β_{k+1}(A∪B).

Total: Σ β_k(A∪B) ≤ Σ β_k(A) + Σ β_k(B) + Σ β_k(A∩B).
And: Σ β_k(A∩B) ≤ Σ β_k(A) + Σ β_k(B) + Σ β_k(A∪B).

From first: β(OR) ≤ β(g) + β(h) + β(AND).
From second: β(AND) ≤ β(g) + β(h) + β(OR).

Adding: β(OR) + β(AND) ≤ 2β(g) + 2β(h) + β(AND) + β(OR).
This is 0 ≤ 2β(g) + 2β(h). Always true. VACUOUS.

The Mayer-Vietoris doesn't give useful one-directional bound.

DIFFERENT APPROACH: Morse theory on Boolean cube.

The circuit defines a "filtration" of the Boolean cube.
At each gate, the solution set changes (adds/removes points).
The PERSISTENT HOMOLOGY of this filtration = circuit complexity.

Persistent homology: tracks birth/death of topological features.
Number of persistence pairs = topological complexity of the filtration.

For a circuit of size s: the filtration has s+1 steps.
Persistence pairs ≤ s+1 (at most one per step).
Total β ≤ s+1 (at most s+1 features alive at any time).

So: β(f) ≤ s+1 → s ≥ β(f) - 1.

THIS IS A BOUND! s ≥ β(f) - 1.

If β(CLIQUE) = super-poly: s ≥ super-poly → P ≠ NP!

But: is β(f) ≤ s+1 correct? Let me verify.

Persistent homology: filtration ∅ = X₀ ⊂ X₁ ⊂ ... ⊂ Xₛ = f⁻¹(1).
At each step: add one "cell" (corresponding to one gate's contribution).
Each cell addition: creates at most 1 new homology class OR kills at most 1.
Total: at most s births + s deaths. Final β ≤ s.

Wait — the filtration for a circuit isn't a cell-by-cell addition.
Each gate CHANGES the solution set (AND restricts, OR expands).
The change at each step ≠ adding one cell.

For OR gate: f = g ∨ h. Solution set grows (adds h's solutions).
For AND gate: f = g ∧ h. Solution set shrinks (removes non-h solutions).

The topology can change DRASTICALLY at each step.
Adding h's solutions to g's: could create MANY new components or fill MANY holes.

So: β change per gate is NOT bounded by 1. It could be LARGE.

HOWEVER: the NUMBER of points added/removed per gate:
AND: removes |g⁻¹(1) \ h⁻¹(1)| points.
OR: adds |h⁻¹(1) \ g⁻¹(1)| points.

Each point addition/removal changes β by at most ±1 (one simplex at a time).
Number of point changes: up to 2^{n-1} per gate.

So: β change per gate ≤ 2^{n-1}. Over s gates: β(f) ≤ s × 2^{n-1}.
s ≥ β(f) / 2^{n-1}. For β = 2^n: s ≥ 2. TRIVIAL.

The 2^{n-1} factor kills any non-trivial bound.

Hmm. But: the point changes are NOT independent for the topology.
Adding 2^{n-1} points in a STRUCTURED way changes β by LESS than 2^{n-1}.

For AND: removing points from g⁻¹(1) that don't satisfy h. The removed set
is g⁻¹(1) ∩ h⁻¹(0). Its topology determines the β change.

β(g⁻¹(1)) - β(g⁻¹(1) ∩ h⁻¹(1)) ≤ β(g⁻¹(1) ∩ h⁻¹(0)) + 1 (by Mayer-Vietoris).

This is still potentially large.

EXPERIMENT: Compute Betti numbers for solution spaces of actual functions.
Compare with circuit size. Look for correlation.
"""

import itertools
from collections import defaultdict
import random
import math
import sys


def compute_connected_components(n, solutions_set):
    """β₀ = number of connected components in the solution subgraph.
    Two solutions connected if Hamming distance 1."""
    if not solutions_set:
        return 0

    visited = set()
    components = 0

    for start in solutions_set:
        if start in visited:
            continue
        components += 1
        queue = [start]
        visited.add(start)
        while queue:
            current = queue.pop()
            for j in range(n):
                neighbor = current ^ (1 << j)
                if neighbor in solutions_set and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

    return components


def compute_euler_characteristic(n, solutions_set):
    """Euler characteristic χ = Σ (-1)^k × (number of k-simplices).
    For solution subgraph of Boolean cube:
    0-simplices = vertices = |solutions|
    1-simplices = edges (Hamming distance 1 pairs within solutions)
    2-simplices = triangles (triples at pairwise distance 1)
    etc.

    χ = V - E + F - ... = Σ (-1)^k β_k (alternating sum of Betti numbers).
    """
    sols = list(solutions_set)
    sol_set = solutions_set

    V = len(sols)

    # Edges: pairs at Hamming distance 1
    E = 0
    for s in sols:
        for j in range(n):
            nb = s ^ (1 << j)
            if nb in sol_set and s < nb:
                E += 1

    # Triangles: triples at pairwise distance 1
    # Three vertices a,b,c at pairwise dist 1: they form a 3-dim subcube face.
    # a⊕b, a⊕c, b⊕c must each have exactly 1 bit set.
    # And: a⊕b ≠ a⊕c ≠ b⊕c.
    T = 0
    if V <= 500:  # feasible only for small solutions
        for i in range(len(sols)):
            for j_idx in range(n):
                nb1 = sols[i] ^ (1 << j_idx)
                if nb1 not in sol_set or nb1 <= sols[i]:
                    continue
                for k_idx in range(j_idx + 1, n):
                    nb2 = sols[i] ^ (1 << k_idx)
                    if nb2 not in sol_set:
                        continue
                    # Check: nb1 and nb2 at distance 1?
                    # nb1 ⊕ nb2 = (sols[i] ^ (1<<j_idx)) ^ (sols[i] ^ (1<<k_idx))
                    # = (1<<j_idx) ^ (1<<k_idx). Two bits set. Distance 2. NOT adjacent.
                    # So: no triangles in Hamming graph! (distance-1 graph has no triangles.)

    # Actually: Hamming distance-1 graph on {0,1}^n is the hypercube graph.
    # Hypercube is BIPARTITE (even weight vs odd weight vertices).
    # Bipartite graphs have NO odd cycles → no triangles!
    # So: T = 0 always. And all higher simplices = 0.

    # Euler characteristic = V - E (since no higher simplices).
    chi = V - E
    # And: χ = β₀ - β₁ (since β_k = 0 for k ≥ 2 in a graph).
    # So: β₁ = β₀ - χ = β₀ - V + E.

    return V, E, chi


def main():
    random.seed(42)
    print("=" * 60)
    print("  SOLUTION SPACE TOPOLOGY: Betti numbers")
    print("  β₀ = components, β₁ = holes")
    print("  The hypercube graph is bipartite → no triangles → β_k=0 for k≥2")
    print("=" * 60)

    from mono3sat import generate_all_mono3sat_clauses

    print(f"\n  {'Function':<18} {'n':>4} {'|sol|':>7} {'β₀':>5} {'E':>7} "
          f"{'β₁':>6} {'β₁/n':>7}")
    print("  " + "-" * 55)

    for n in range(4, 14):
        if 2**n > 200000:
            break

        # MONO-3SAT
        all_cl = generate_all_mono3sat_clauses(n)
        clauses = random.sample(all_cl, min(len(all_cl), 3*n))
        sols = set()
        for b in range(2**n):
            x = tuple((b>>j)&1 for j in range(n))
            if all(any(x[v] for v in c) for c in clauses):
                sols.add(b)

        beta0 = compute_connected_components(n, sols)
        V, E, chi = compute_euler_characteristic(n, sols)
        beta1 = beta0 - chi  # β₁ = β₀ - χ

        print(f"  {'MSAT-'+str(n):<18} {n:>4} {V:>7} {beta0:>5} {E:>7} "
              f"{beta1:>6} {beta1/n:>7.1f}")

        # OR
        sols_or = set(range(1, 2**n))
        b0_or = compute_connected_components(n, sols_or)
        V_or, E_or, chi_or = compute_euler_characteristic(n, sols_or)
        b1_or = b0_or - chi_or

        print(f"  {'OR-'+str(n):<18} {n:>4} {V_or:>7} {b0_or:>5} {E_or:>7} "
              f"{b1_or:>6} {b1_or/n:>7.1f}")

        sys.stdout.flush()

    # Triangle
    for N in range(4, 7):
        nn = N*(N-1)//2
        if 2**nn > 200000:
            break
        edge_idx = {}; idx = 0
        for i in range(N):
            for j in range(i+1, N):
                edge_idx[(i,j)] = idx; edge_idx[(j,i)] = idx; idx += 1
        sols = set()
        for b in range(2**nn):
            x = tuple((b>>j)&1 for j in range(nn))
            if any(x[edge_idx[(i,j)]] and x[edge_idx[(i,k)]] and x[edge_idx[(j,k)]]
                   for i in range(N) for j in range(i+1,N) for k in range(j+1,N)):
                sols.add(b)
        beta0 = compute_connected_components(nn, sols)
        V, E, chi = compute_euler_characteristic(nn, sols)
        beta1 = beta0 - chi
        print(f"  {'TRI-K'+str(N):<18} {nn:>4} {V:>7} {beta0:>5} {E:>7} "
              f"{beta1:>6} {beta1/nn:>7.1f}")

    print(f"\n{'='*60}")
    print("  IF β₁ grows super-polynomially for CLIQUE:")
    print("  AND β₁ ≤ f(circuit_size):")
    print("  THEN circuit_size ≥ super-poly → P ≠ NP")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
