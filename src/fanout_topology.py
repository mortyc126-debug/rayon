"""
Fan-Out Topology Analysis: Why Circuit Size ≠ Formula Size.

The gap between formula size and circuit size is EXACTLY the fan-out.
Fan-out allows gates to be REUSED, exponentially reducing size.

For monotone functions with formula size F(f):
  Circuit size S(f) ≥ F(f) / max_fanout_savings

  max_fanout_savings = max over all circuits computing f of
    (formula_size_of_unfolded_circuit / circuit_size)

The P vs NP question for circuits reduces to:
  Can fan-out provide EXPONENTIAL savings for NP-hard functions?

This module analyzes the TOPOLOGY of fan-out in circuits:
1. Which gates have high fan-out?
2. What functions do high-fan-out gates compute?
3. Is there a structural constraint that limits fan-out savings?

KEY INSIGHT: A gate with fan-out k computes a function g that is
used by k other gates. For the reuse to "help", g must be USEFUL
in k different contexts. The ENTROPY of g's usage pattern determines
the actual savings.

If g is used in "similar" ways: less savings (could be replaced by
specialized gates with similar total cost).
If g is used in "diverse" ways: more savings (genuine reuse).

For NP-hard functions: are intermediate functions reusable?
"""

import itertools
from collections import defaultdict
import random
import math
import sys


def evaluate_mono3sat(assignment, clauses):
    for clause in clauses:
        if not any(assignment[v] for v in clause):
            return False
    return True


def compute_all_boolean_functions(n):
    """Enumerate all 2^{2^n} Boolean functions on n variables.
    Only feasible for n ≤ 3.
    """
    num_fns = 2**(2**n)
    functions = []
    for tt in range(num_fns):
        functions.append(tt)
    return functions


def function_properties(n, tt_int):
    """Compute properties of a Boolean function given by truth table integer."""
    num_inputs = 2**n

    # Monotonicity check
    is_monotone = True
    for i in range(num_inputs):
        if (tt_int >> i) & 1:
            # All "smaller" inputs should also be 1
            for j in range(n):
                if (i >> j) & 1:
                    smaller = i & ~(1 << j)
                    if not ((tt_int >> smaller) & 1):
                        is_monotone = False
                        break
            if not is_monotone:
                break

    # Number of 1s
    ones = bin(tt_int).count('1')

    # Sensitivity
    max_sens = 0
    for i in range(num_inputs):
        sens = 0
        for j in range(n):
            neighbor = i ^ (1 << j)
            if ((tt_int >> i) & 1) != ((tt_int >> neighbor) & 1):
                sens += 1
        max_sens = max(max_sens, sens)

    return {
        'monotone': is_monotone,
        'ones': ones,
        'sensitivity': max_sens,
    }


def analyze_intermediate_functions(n, clauses):
    """For a specific MONO-3SAT instance, analyze ALL Boolean functions
    that could serve as intermediate computations.

    Key question: which intermediate functions would benefit from fan-out?
    A function g benefits from fan-out if:
    1. g is "useful" (appears in a good circuit for f)
    2. g is reusable (used by multiple other gates)

    We enumerate all functions computable with few gates and check which
    ones are "useful" as intermediates for computing f.
    """
    # Compute target truth table
    f_tt = 0
    for i in range(2**n):
        x = tuple((i >> j) & 1 for j in range(n))
        if evaluate_mono3sat(x, clauses):
            f_tt |= (1 << i)

    print(f"\nIntermediate function analysis (n={n}):")
    print(f"  Target function: {bin(f_tt)}")

    # Generate all functions computable by 1 gate from inputs
    one_gate_fns = set()
    for i in range(n):
        for j in range(i, n):
            # Input truth tables
            tti = sum((1 << k) for k in range(2**n) if (k >> i) & 1)
            ttj = sum((1 << k) for k in range(2**n) if (k >> j) & 1)

            one_gate_fns.add(('AND', i, j, tti & ttj))
            one_gate_fns.add(('OR', i, j, tti | ttj))

        # NOT of input
        tti = sum((1 << k) for k in range(2**n) if (k >> i) & 1)
        all_ones = (1 << (2**n)) - 1
        one_gate_fns.add(('NOT', i, -1, all_ones ^ tti))

    print(f"  Functions computable with 1 gate: {len(one_gate_fns)}")

    # Check which of these are "useful" for computing f
    # A function g is useful if f can be computed from g and inputs
    # with fewer gates than without g
    useful_fns = []
    for name, i, j, g_tt in one_gate_fns:
        props = function_properties(n, g_tt)
        useful_fns.append({
            'name': f'{name}({i},{j})' if j >= 0 else f'{name}({i})',
            'tt': g_tt,
            'monotone': props['monotone'],
            'ones': props['ones'],
        })

    # Sort by usefulness (number of ones, sensitivity)
    print(f"\n  One-gate intermediate functions:")
    for fn in sorted(useful_fns, key=lambda x: x['ones']):
        mono_str = "M" if fn['monotone'] else "N"
        print(f"    {fn['name']:<15} tt={bin(fn['tt']):>12} "
              f"ones={fn['ones']:>3} [{mono_str}]")

    # KEY ANALYSIS: Fan-out savings potential
    # For each intermediate function g, how many DIFFERENT ways
    # can it be combined with other functions to help compute f?
    print(f"\n  Fan-out potential analysis:")
    print(f"  A function g has high fan-out potential if it can be")
    print(f"  combined with MANY different functions to produce")
    print(f"  sub-results useful for computing f.")

    # For each g: count how many other functions h such that
    # f can be expressed using g, h, and a few more gates
    # This is expensive, so we just check simple compositions

    all_ones = (1 << (2**n)) - 1

    for fn in useful_fns[:5]:
        g_tt = fn['tt']

        # What can we get by ANDing/ORing g with each input?
        compositions = set()
        for k in range(n):
            xk_tt = sum((1 << m) for m in range(2**n) if (m >> k) & 1)
            compositions.add(g_tt & xk_tt)
            compositions.add(g_tt | xk_tt)
            compositions.add((all_ones ^ g_tt) & xk_tt)
            compositions.add((all_ones ^ g_tt) | xk_tt)

        # How many DISTINCT functions?
        print(f"    {fn['name']}: {len(compositions)} distinct compositions with inputs")


def fanout_savings_theoretical():
    """Theoretical analysis of fan-out savings.

    For a circuit of size s and formula size F:
      F ≤ s · 2^depth   (each gate is unfolded at most 2^depth times)

    For a circuit of depth d:
      F ≤ s · 2^d
      s ≥ F / 2^d

    For f with formula size F(f) ≥ 1.96^n (from Fourier analysis):
      s ≥ 1.96^n / 2^d

    For polynomial-size circuit: s = poly(n), so:
      poly(n) ≥ 1.96^n / 2^d
      2^d ≥ 1.96^n / poly(n)
      d ≥ n · log₂(1.96) - O(log n)
      d ≥ 0.97n

    So: polynomial-size circuits for f need depth ≥ 0.97n.
    This is ALMOST full depth (max depth = s ≈ poly(n)).

    But poly(n) gates can have depth poly(n) >> 0.97n.
    So this doesn't give a contradiction.

    HOWEVER: if most gates have depth ≈ n, then the circuit
    is essentially a formula (little reuse). The fan-out savings
    come from gates at INTERMEDIATE depth (depth << n).

    KEY QUESTION: Can intermediate-depth gates provide enough
    fan-out to reduce formula size from exp to poly?
    """
    print(f"\n{'='*80}")
    print("  THEORETICAL FAN-OUT SAVINGS ANALYSIS")
    print(f"{'='*80}")

    print("""
    Formula size vs Circuit size:

    For f with formula size F and circuit size S:
      S ≤ F ≤ S · 2^depth

    From our Fourier analysis: formula size ≥ 1.96^n
    From circuit depth lower bound: depth ≥ log₂(n) (trivial)

    The fan-out savings ratio R = F/S can be at most 2^depth.

    For R to be exponential: depth must be Ω(n).
    For R to be polynomial: depth can be O(log n).

    For MONO-3SAT evaluation (fixed formula):
      S = O(n), depth = O(log n), F = O(n)
      R = O(1) — constant! No fan-out savings needed.

    For NP-HARD monotone functions (CLIQUE):
      Monotone S ≥ 2^{Ω(N^{1/6})} (Razborov)
      General S ≤ N^k (polynomial, if P = NP)
      F_mono ≥ ? (unknown, but at least S_mono)
      R_needed = F_mono / S_general ≥ 2^{Ω(N^{1/6})} / N^k

    So: if CLIQUE is in P, fan-out provides EXPONENTIAL savings.
    This means high-fan-out intermediate functions exist that
    are reusable across exponentially many contexts.

    THE TOPOLOGICAL CONSTRAINT:
    A gate with fan-out k is used by k parent gates.
    Each parent gate connects to 2 children.
    Total edges in DAG = 2S (each gate has 2 inputs except NOT).

    Sum of fan-outs = total edges = 2S ≈ 2·poly(n).
    If one gate has fan-out k: k ≤ 2S ≈ poly(n).
    So individual fan-out is bounded by poly(n).

    But the FORMULA size contribution of one gate with fan-out k
    is k (it appears k times in the unfolded formula).

    Total formula size = Σ (fan-out of gate g) · (subtree size of g)

    For exponential savings: some gate g must have
    fan-out · subtree_size ≈ exponential.

    fan-out ≤ poly(n), so subtree_size ≥ exp/poly = exponential.
    This means the subtree below g is itself exponential.

    But the subtree below g is computed by gates below g.
    If those gates also have fan-out, the formula exponentially
    compounds.

    THIS IS EXACTLY HOW CIRCUITS WORK:
    Each level of fan-out multiplies the formula size by the fan-out.
    With O(log n) levels of fan-out 2: total formula = 2^{O(log n)} = poly(n).

    But for our function: formula ≥ 1.96^n.
    So: we need 2^{Σ log₂(fan_out_i)} ≥ 1.96^n
    where the sum is over the "fan-out path" (path from output to input).

    Σ log₂(fan_out_i) ≥ n · log₂(1.96) ≈ 0.97n

    This means: the TOTAL FAN-OUT along any root-to-leaf path
    must multiply to at least 1.96^n.

    With polynomial fan-out at each gate: need 0.97n levels.
    This requires depth ≥ 0.97n and circuit size ≥ 0.97n.

    BUT: these are just TRIVIAL lower bounds (size ≥ n).
    The fan-out argument doesn't give super-linear bounds because
    polynomial fan-out at polynomial many levels gives exponential
    formula size.
    """)

    # Numerical illustration
    print(f"  Numerical illustration:")
    for n in [10, 20, 50, 100]:
        F = 1.96**n  # formula size
        for d in [int(math.log2(n)), n//2, n]:
            max_R = 2**d
            min_S = F / max_R
            print(f"    n={n:3d}: F≥{F:.0e}, depth={d:3d}, "
                  f"max_R=2^{d}={max_R:.0e}, min_S≥{min_S:.0e}")
        print()


def analyze_depth_width_tradeoff(n, clauses):
    """Analyze the depth-width tradeoff for specific functions.

    Width = max number of "active" wires at any level.
    If width is bounded: the circuit must be "narrow",
    limiting information flow.

    Branching program lower bounds (Barrington, etc.) use
    width constraints to prove exponential lower bounds.

    Can we combine width + NOT-gate constraints?
    """
    print(f"\n{'='*80}")
    print(f"  DEPTH-WIDTH-NOT TRADEOFF ANALYSIS (n={n})")
    print(f"{'='*80}")

    # For a circuit of size s, depth d, width w:
    # - At most w wires are "live" at any level
    # - Each wire carries 1 bit of information
    # - Total information at any level: w bits
    # - To distinguish 2^n inputs: need w ≥ n (at some level)

    # With k NOT gates:
    # - Each NOT gate can be placed at any level
    # - NOT doesn't change width
    # - But NOT changes the "type" of information flowing

    # For monotone circuits: information is "monotone" — it can only
    # increase (in the poset sense) as we go up
    # NOT gates allow decreases, which enables "compression"

    print("""
    Branching Program connection:

    A circuit of width w can be simulated by a branching program
    of width 2^w. (Barrington 1989 for width 5 = NC¹)

    For our function with formula size ≥ 1.96^n:
    - Width-5 branching programs can compute any function in NC¹
    - But MONO-3SAT evaluation IS in NC¹ (log depth)
    - So width-5 suffices for evaluation

    The NP-HARD version requires:
    - Either large width, or
    - Large depth, or
    - Many NOT gates

    The width-depth-NOT tradeoff might give the answer.

    CONJECTURE: For NP-hard monotone functions,
    width · NOT_count ≥ Ω(n) at every level.

    If width is bounded (O(1)): need Ω(n) NOT gates per level
    → total NOT = Ω(n · depth) ≥ Ω(n²) for linear depth
    → size ≥ Ω(n²) (super-linear!)

    If NOT count is bounded (O(log n)): need Ω(n/log n) width
    → size ≥ depth · Ω(n/log n) ≥ Ω(n²/log n)

    These are WEAK bounds but they're for GENERAL circuits!
    Getting even Ω(n²) for circuits would be progress.

    CURRENT BEST: size ≥ 3n - o(n) (for general circuits)
    Even size ≥ 4n would be a breakthrough.
    """)


if __name__ == "__main__":
    random.seed(42)

    # Phase 1: Intermediate function analysis
    from mono3sat import generate_all_mono3sat_clauses

    for n_val in [3, 4]:
        all_clauses = generate_all_mono3sat_clauses(n_val)
        if all_clauses:
            clauses = all_clauses[:3]  # simple instance
            analyze_intermediate_functions(n_val, clauses)

    # Phase 2: Theoretical analysis
    fanout_savings_theoretical()

    # Phase 3: Depth-width-NOT tradeoff
    analyze_depth_width_tradeoff(5, [(0,1,2), (0,1,3), (2,3,4)])
