"""
IDEA D: Computational Bell Inequality.

In physics: Bell inequality bounds correlations achievable by
local hidden variable models. Violation → nonlocality → quantum.

In computation: "local" = each gate sees 2 inputs from nearby wires.
"Nonlocal" = output depends on ALL n inputs simultaneously.

A circuit of size s: at depth d, a gate "knows" about ≤ 2^d inputs
(its backward light cone). For d < log n: gate knows < n inputs.
Gate is "local" — can't see all inputs.

For output at depth D: sees all n inputs (if D ≥ log n).

BELL INEQUALITY ANALOG:
  Partition inputs into k distant groups (|group| = n/k).
  "Local" computation: within each group, compute partial result.
  "Communication": between groups, exchange partial results.
  Total information exchanged = circuit's "communication budget."

  If function requires "nonlocal" correlations between groups:
  communication budget must be large.

  For k groups: budget = k × (wires between groups).
  Wires between = circuit's "cut width" at the partition.

  If cut width ≤ w for some partition: budget = k × w.
  Function's "nonlocality" = min budget needed.

THIS IS COMMUNICATION COMPLEXITY in disguise!
Multiple partitions simultaneously.

But: we've already explored CC and it gives only log bounds.

NEW ANGLE: Instead of ONE partition, use ALL partitions SIMULTANEOUSLY.
The function must satisfy Bell-like inequality for EVERY partition.

For a circuit of size s: for EACH partition: cut width ≤ s.
For k partitions simultaneously: total budget ≤ k × s.

If function requires total budget ≥ super-poly × k: s ≥ super-poly.

"Requires total budget": for EACH partition, the CC ≥ some amount.
SUM of CC over all partitions = ???

For n inputs, all balanced 2-partitions: C(n, n/2) partitions.
Each: CC ≥ 1 (trivially). Sum ≥ C(n, n/2) ≈ 2^n / √n. HUGE.

But: circuit has cut width ≤ s for EACH partition.
Sum ≤ C(n, n/2) × s. Need sum ≥ C(n, n/2) (trivially).
s ≥ 1. TRIVIAL.

The issue: different partitions share the same wires.
A wire in the circuit contributes to cut of MANY partitions.
One wire covers many partitions → sum is cheaply covered.

For a wire from gate at depth d: it crosses all partitions that
split its input cone differently. Number of such partitions: large.

So: total sum / s ≈ coverage_per_wire. If coverage = 2^n: s ≥ 1.

The multi-partition approach doesn't help because wires are "universal"
(one wire covers many partitions).

HOWEVER: what if we weight partitions by FUNCTION-SPECIFIC importance?

For CLIQUE: partition into vertex groups. A partition separating
vertices of a clique → requires communication about cross-edges.

There are C(N, k) potential cliques. Each clique: induces C(k,2) edges.
A partition splitting the clique: requires those edges to be communicated.

For each clique Q: weight w(Q, partition) = 1 if partition splits Q, 0 otherwise.

Total weighted CC ≥ Σ_Q Σ_P w(Q,P) × CC(partition P for clique Q).

Each clique Q: split by most partitions. CC for each ≥ 1 (need ≥1 cross-edge).

Total ≥ C(N,k) × C(N/2, k/2)² / C(N,k) ... complicated.

Let me just COMPUTE the multi-partition CC for small CLIQUE.

ACTUALLY: the most useful version is the INFORMATION COMPLEXITY.

IC(f) = minimum over all protocols: Σ_P I(transcript; X | partition P).

IC ≥ CC for each partition. And: IC sums over partitions meaningfully.

For circuits: IC ≤ s × log s (each gate contributes O(log s) bits).

If IC(CLIQUE) = super-poly × log s: s ≥ super-poly.

IC is a well-studied object. Known: IC(DISJ) = Ω(n) (disjointness).

Can we REDUCE DISJ to CLIQUE in the IC framework?

DISJ_n: Alice has set A ⊆ [n], Bob has set B ⊆ [n]. Disjoint?
CLIQUE: is there a k-clique?

Reduction: encode DISJ as CLIQUE sub-problem.
Alice's set A → edges of a graph. Bob's set B → edges.
A ∩ B ≠ ∅ iff shared edge → graph has ... edge. Not clique.

Standard DISJ-to-CLIQUE reduction: not direct. Need k-way disjointness
or other multi-party variant.

k-party DISJ: k parties, each has a set, test if common intersection empty.
k-party DISJ CC = Ω(n/k) (known).
Reduce to CLIQUE: each party = a vertex in clique.

Hmm, the reduction is non-trivial. But: if achievable:
IC(CLIQUE) ≥ IC(k-DISJ) = Ω(n/k). For k = N^{1/3}: IC ≥ Ω(N²/N^{1/3}) = Ω(N^{5/3}).

And: circuit IC ≤ s × O(log s). So: s ≥ Ω(N^{5/3} / log s).
For s = poly(N): Ω(N^{5/3} / poly log) = Ω(N^{5/3-ε}).
THIS IS SUPER-LINEAR FOR N (polynomial in N with exponent > 1)!

N^{5/3} in terms of n = N²/2: N = √(2n). N^{5/3} = (2n)^{5/6} = Ω(n^{5/6}).

s ≥ Ω(n^{5/6})!!! SUPER-LINEAR!!!

Wait — is IC ≤ s × log s correct for circuits? Information complexity
of a circuit: each gate reveals O(1) bits. Total: O(s) bits.

IC ≤ O(s). Then: s ≥ IC(CLIQUE). If IC(CLIQUE) = Ω(n^{5/6}): s ≥ n^{5/6}.

THIS WOULD BE A SUPER-LINEAR CIRCUIT LOWER BOUND!

Better than the current record of ~5n for n > 5^6 ≈ 15000.

But: the reduction from k-DISJ to CLIQUE in the IC framework
is THE key step. Is it valid?

NEED TO VERIFY: k-party information complexity of CLIQUE ≥ Ω(n/k).
"""

print("IDEA D: Computational Bell Inequality / Information Complexity")
print("=" * 60)
print()
print("IF k-party IC(CLIQUE) ≥ Ω(n/k):")
print("  For k = N^{1/3}: IC ≥ Ω(N^{5/3}) = Ω(n^{5/6})")
print("  Circuit IC ≤ O(s)")
print("  → s ≥ Ω(n^{5/6})")
print("  → SUPER-LINEAR circuit lower bound!")
print()

import math
for N in [10, 100, 1000, 10000]:
    n = N*(N-1)//2
    k = int(round(N**(1/3)))
    ic_bound = n / k  # IC ≥ Ω(n/k)
    n_bound = n**(5/6)  # in terms of n

    print(f"  N={N:>6}: n={n:>10}, k={k:>4}, IC≥{ic_bound:>10.0f}, "
          f"s≥n^(5/6)={n_bound:>10.0f}")

print()
print("CAVEAT: The reduction from k-DISJ to CLIQUE in IC framework")
print("is NOT established. This is the KEY step to verify.")
print("If reduction works: s ≥ n^{5/6} = SUPER-LINEAR.")
print("If doesn't: another dead end.")
print()
print("Known: k-party DISJ has IC = Ω(n/k²) (Braverman et al.)")
print("Reduction CLIQUE → DISJ: standard NP-completeness.")
print("Reduction DISJ → CLIQUE in IC: NON-STANDARD. Need to formalize.")
