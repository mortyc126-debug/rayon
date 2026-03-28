"""
BAG COMPLEXITY: Local work per tree-decomposition bag.

In a tree decomposition of width T:
  - Each bag has ≤ T+1 circuit nodes (wires).
  - Adjacent bags share ≤ T nodes (the "interface").
  - Within each bag: some gates compute.

The LOCAL COMPLEXITY of a bag = number of gates in the bag.

Total gates = Σ_bags local_complexity(bag) = S.

But: what's the MINIMUM local complexity per bag?

If the bag's T+1 wires must "process" boundary transitions
that pass through the bag: each such transition requires
at least 1 gate in the bag to "handle" it.

The number of transitions through a bag: depends on the function
and the specific bag position.

THE KEY BOUND:
  For CLIQUE: at the "bottleneck" bag (widest part of tree decomp),
  the number of boundary transitions passing through = ???

  If each bag must handle ≥ Ω(T) transitions: #gates_per_bag ≥ Ω(T).
  Total: #bags × Ω(T) = (S/T) × Ω(T) = S. TAUTOLOGICAL.

  If each bag must handle ≥ Ω(T²) transitions: #gates_per_bag ≥ Ω(T²/T) = Ω(T).
  Same tautology.

DIFFERENT APPROACH: Bag COMMUNICATION complexity.

Each bag has an "interface" with neighboring bags: ≤ T shared nodes.
The bag must transform the T-bit input interface into T-bit output interface.
The transformation must be CONSISTENT with the circuit computation.

For each bag: the transformation is a function from T bits to T bits.
The circuit complexity of this function ≥ ???

If the transformation requires Ω(T²) gates (like matrix multiply):
  Total ≥ #bags × T² = (S/T) × T² = S × T.
  S × T ≤ actual gates. So: S ≥ S × T → T ≤ 1. CONTRADICTION for T > 1.

Wait, that's wrong. The total gates = S, not S × T. The bound says:
  S ≥ #bags × min_gates_per_bag.
  S ≥ (S/T) × min_gates_per_bag (approximately).
  T × S ≥ S × min_gates_per_bag.
  min_gates_per_bag ≤ T.

So: each bag has at most T gates. And we need at least ??? gates per bag.

For CLIQUE: the function within each bag depends on the bag's position.
At the "center" of the tree decomposition: the bag sees T wires that
carry information about BOTH halves of the circuit. The function
on these T wires must "merge" the two halves.

The merging function is essentially: does the left sub-problem AND
the right sub-problem together satisfy CLIQUE?

This is a version of SET DISJOINTNESS on T bits:
  Left sends T bits about its clique structure.
  Right sends T bits about its clique structure.
  They need to determine if a full k-clique spans both.

CC(DISJ on T bits) = Ω(T). So: the "merging" at the central bag
requires Ω(T) communication → Ω(T) gates in the bag.

And: #bags × T ≤ S (each bag has ≤ T gates).
With #bags ≥ S/T: (S/T) × T = S ≤ S. TAUTOLOGICAL again.

THE FUNDAMENTAL ISSUE: the tree decomposition has ≤ S bags, each
with ≤ T gates. Total = S. Every argument that bounds per-bag
complexity by T gives total = S. No improvement.

WE NEED: per-bag complexity > T. But: bag has T+1 nodes → at most
T gates (one per node minus inputs). Can't have > T gates per bag!

So: bag complexity ≤ T always. And total = bags × bag_complexity ≤ S.

COMPLETELY DIFFERENT IDEA: Don't use tree decomposition.
Use a DIFFERENT structural decomposition.

IDEA: FLOW DECOMPOSITION.

Instead of decomposing the DAG into bags, decompose the COMPUTATION
into FLOWS. Each flow = a path from some input to the output.

The number of distinct flows = formula size (each flow = a path
in the unfolded formula tree).

For a circuit with fan-out: one wire is in MULTIPLE flows.
Total wires × avg_flow_membership = formula_size.

If each wire is in at most F flows (fan-out bound):
  S × F ≥ formula_size.
  S ≥ formula_size / F.

For F = max fan-out ≤ S: S ≥ formula / S → S² ≥ formula.

For CLIQUE: formula ≥ 2^{Ω(N^{1/6})}.
  S² ≥ 2^{Ω(N^{1/6})}
  S ≥ 2^{Ω(N^{1/6}/2)} = 2^{Ω(N^{1/6})} = SUPER-POLY!!!

Wait — S ≥ formula / F where F ≤ S gives S² ≥ formula.
For formula = 2^{Ω(N^{1/6})}: S² ≥ 2^{Ω(N^{1/6})} → S ≥ 2^{Ω(N^{1/12})}.

SUPER-POLY? 2^{N^{1/12}} where N = √(2n): 2^{(2n)^{1/24}} = 2^{n^{1/24}}.

This grows FASTER than any polynomial! 2^{n^{1/24}} > n^c for any c.

IS THIS CORRECT?

Let me verify: formula(f) ≤ S × F where F = max fan-out.
This is because: each gate in the circuit, when unfolded, appears
F times (once per parent). Total formula leaves = Σ_gates F_g.

Σ_gates F_g = total fan-out = 2S (each gate has 2 inputs).

Wait: Σ F_g = 2S (total edges in DAG). This is the total fan-out
summed over all gates. The formula size = the number of paths
from output to inputs = Π fan-outs along paths ≤ F^depth.

The correct bound: formula ≤ S × F^d where F = max fan-out, d = depth.

For F ≤ S, d ≤ S: formula ≤ S × S^S = S^{S+1}. Enormous.

BUT: a tighter bound using AVERAGE fan-out:
  formula ≤ (avg_fan_out)^depth × S.
  avg_fan_out = 2S/(S+n) ≈ 2.
  formula ≤ 2^d × S. STANDARD.

So: S ≥ formula / 2^d. For d = S: S ≥ formula / 2^S. USELESS.

The S² ≥ formula bound comes from a DIFFERENT argument:

Each wire w has fan-out F_w. The formula contribution of w:
  the subtree below w is copied F_w times.
  Formula contribution of w = F_w × subtree_size(w).

Total formula = Σ_w F_w × subtree_size(w).

Now: Σ F_w ≤ 2S (total fan-out).
And: max subtree_size ≤ formula.

By Cauchy-Schwarz or AM-GM:
  formula = Σ F_w × subtree_size(w) ≤ (Σ F_w) × max(subtree) = 2S × formula.

This gives formula ≤ 2S × formula → 1 ≤ 2S → S ≥ 1/2. USELESS.

OK, Cauchy-Schwarz doesn't help directly.

ACTUALLY: The formula is NOT Σ F_w × subtree. It's more complex.
The formula = product of fan-outs along paths.

Let me try a specific argument:

CLAIM: For a circuit of size S, formula ≤ 2^S.

PROOF: Each gate has fan-out ≤ S. The formula is the unfolded tree.
At each gate, the formula branches into F_g copies.
Total branches: Π F_g. But we only follow paths from root.
Number of paths from root = formula = Π_{gates on path} F_g.

For ANY root-to-leaf path of length d:
  This path passes through d gates.
  The formula contribution = Π_{i=1}^d F_{g_i} where g_i are gates on path.

By AM-GM: Π F_{g_i} ≤ (Σ F_{g_i} / d)^d.

We know: Σ (over ALL gates) F_g = 2S. Along a path of length d:
  Σ_{on path} F_{g_i} ≤ 2S (all fan-outs of all gates).

So: Π F_{g_i} ≤ (2S/d)^d.

Formula = number of leaves = max over paths of Π F_{g_i}.

For d = S: formula ≤ (2)^S = 2^S.
For d = √S: formula ≤ (2√S)^{√S} = 2^{√S log(2√S)} ≈ 2^{√S log S}.

These are upper bounds. We need the LOWER bound on S.

formula ≤ (2S/d)^d for optimal d.

Minimizing RHS over d: d* = 2S/e → RHS = e^{2S/e} = e^{0.74S}. So formula ≤ e^{0.74S} → S ≥ 1.35 ln(formula).

For formula = 2^{Ω(N^{1/6})}: S ≥ Ω(N^{1/6}). SAME AS BEFORE.

Hmm. The AM-GM on path fan-outs gives formula ≤ 2^{O(S)}.
So S ≥ Ω(log formula) = Ω(N^{1/6}). Already known.

But: the AM-GM bound uses Σ_{path} F_g ≤ 2S. This is a LOOSE bound
because not all fan-out is on the critical path.

A TIGHTER bound: Σ_{path} F_g ≤ ??? depends on the specific path.

If the path has length d and passes through gates with fan-out
F₁,...,F_d: the path "uses" F₁ + ... + F_d of the total 2S fan-out.

The remaining gates have 2S - Σ F_i fan-out.

For the path to contribute maximally: each F_i = 2S/d (equal).
Π = (2S/d)^d. This is the AM-GM bound.

But: the TOTAL formula accounts for ALL paths, not just the max.
formula = Σ over ALL root-to-leaf paths of 1.

The number of paths = the number of leaves. Each leaf is an input.

Actually, I realize: formula size and the bounds on it from
circuit size are WELL-STUDIED. The best known is:
  formula ≤ 2^{O(S)} (trivial, from S^S upper bound on paths)

And: S ≥ Ω(log formula). This is tight (achieved by full binary tree).

I keep arriving at the same bound. Let me accept that log is the best
we can get from this type of argument and try something truly different.
"""


def main():
    print("Bag complexity analysis is theoretical.")
    print("Key finding: S² ≥ formula argument FAILS")
    print("(AM-GM gives formula ≤ 2^{O(S)}, so S ≥ log formula)")
    print()
    print("Every structural decomposition ultimately gives S ≥ log(something).")
    print("The logarithmic barrier appears ABSOLUTE for circuit lower bounds")
    print("via any combinatorial/algebraic argument.")


if __name__ == "__main__":
    main()
