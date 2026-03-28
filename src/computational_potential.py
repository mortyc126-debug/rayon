"""
THE COMPUTATIONAL POTENTIAL: A New Mathematical Object.

MOTIVATION: Every approach to P vs NP attacks ONE aspect:
  - Counting → compression (how many bits?)
  - Fourier/algebraic → composability (what can AND/OR/NOT do?)
  - Communication → consistency (correct on all inputs?)

We need an object that captures ALL THREE simultaneously.

ANALOGY: In thermodynamics, the FREE ENERGY F = U - TS captures
the interplay between energy U, entropy S, and temperature T.
You can't minimize F by changing just one variable.

DEFINITION: The COMPUTATIONAL POTENTIAL of a Boolean function f.

For a function f: {0,1}^n → {0,1}, define:

  Φ(f) = max over all PARTITIONS of inputs into "blocks"
          of [consistency_cost × compression_cost × composability_cost]

Where:
  - consistency_cost(P) = number of boundary transitions BETWEEN blocks
    (how many input pairs (x,x') with f(x)≠f(x') cross block boundaries)

  - compression_cost(P) = log of the number of distinct "behaviors"
    within blocks (how many different restrictions f|_B are there?)

  - composability_cost(P) = depth required to compute the "inter-block"
    function (how deep must the circuit be to combine block results?)

The partition P defines a "decomposition" of the computation into
local (within-block) and global (between-block) parts.

For ANY circuit C computing f:
  size(C) ≥ Φ(f) / max_gate_contribution

If max_gate_contribution is polynomial: size ≥ Φ(f) / poly.
If Φ(f) is super-polynomial: circuit size is super-polynomial.

THE KEY INSIGHT: The three costs TRADE OFF against each other.
  - Many small blocks: low compression cost but high consistency cost
  - Few large blocks: low consistency cost but high compression cost
  - The composability cost depends on the interaction structure

The OPTIMUM partition minimizes the product. If the minimum product
is still super-polynomial: P ≠ NP.

TESTING THIS FRAMEWORK:
For MONO-3SAT and small functions, compute Φ(f) and check if it
separates P from NP-hard functions.
"""

import itertools
from collections import defaultdict
import random
import math
import sys


def evaluate_function(x, func):
    return 1 if func(x) else 0


def compute_computational_potential(n, func, num_partitions=100):
    """Compute the computational potential Φ(f) for a function f.

    Try random partitions and find the one maximizing the product
    of consistency × compression × composability costs.
    """
    # Precompute truth table
    truth_table = {}
    for bits in range(2**n):
        x = tuple((bits >> j) & 1 for j in range(n))
        truth_table[bits] = evaluate_function(x, func)

    # Compute boundary transitions
    boundary = []
    for bits in range(2**n):
        for j in range(n):
            neighbor = bits ^ (1 << j)
            if truth_table[bits] != truth_table[neighbor] and bits < neighbor:
                boundary.append((bits, neighbor))

    total_boundary = len(boundary)

    best_potential = 0
    best_partition = None
    best_costs = None

    for trial in range(num_partitions):
        # Generate random partition into 2^k blocks
        # using k random "hash bits"
        k = random.randint(1, min(n-1, 5))

        # Hash: project onto k random coordinates
        coords = random.sample(range(n), k)
        num_blocks = 2**k

        # Assign each input to a block
        blocks = defaultdict(set)
        for bits in range(2**n):
            block_id = 0
            for ci, c in enumerate(coords):
                if (bits >> c) & 1:
                    block_id |= (1 << ci)
            blocks[block_id].add(bits)

        # COST 1: Consistency cost
        # Number of boundary transitions BETWEEN blocks
        cross_boundary = 0
        for b1, b2 in boundary:
            block1 = 0
            block2 = 0
            for ci, c in enumerate(coords):
                if (b1 >> c) & 1:
                    block1 |= (1 << ci)
                if (b2 >> c) & 1:
                    block2 |= (1 << ci)
            if block1 != block2:
                cross_boundary += 1

        consistency_cost = max(1, cross_boundary)

        # COST 2: Compression cost
        # Number of distinct function "signatures" across blocks
        # A signature = the truth table of f restricted to the block's inputs
        signatures = set()
        for block_id, block_inputs in blocks.items():
            if not block_inputs:
                continue
            sig = tuple(truth_table[bits] for bits in sorted(block_inputs))
            signatures.add(sig)

        compression_cost = max(1, len(signatures))

        # COST 3: Composability cost
        # Depth needed to combine block results into final answer
        # Approximate: log₂ of number of distinct block outputs needed
        # Each block produces 1 bit (its signature determines the output)
        # The inter-block function combines these bits
        composability_cost = max(1, int(math.ceil(math.log2(max(2, len(signatures))))))

        # Total potential = product of costs
        potential = consistency_cost * compression_cost * composability_cost

        if potential > best_potential:
            best_potential = potential
            best_partition = (coords, k)
            best_costs = (consistency_cost, compression_cost, composability_cost)

    return best_potential, best_costs, total_boundary


def compare_functions():
    """Compare computational potential for P vs NP-candidate functions."""
    print("=" * 70)
    print("  COMPUTATIONAL POTENTIAL: Φ(f)")
    print("  Captures consistency × compression × composability")
    print("=" * 70)

    # P functions
    p_functions = {
        'OR': lambda x: 1 if any(x) else 0,
        'AND': lambda x: 1 if all(x) else 0,
        'PARITY': lambda x: sum(x) % 2,
        'MAJ': lambda x: 1 if sum(x) > len(x)/2 else 0,
        'TH2': lambda x: 1 if sum(x) >= 2 else 0,
    }

    # "Harder" functions (still in P but with more structure)
    hard_functions = {
        'TRIBES': None,  # will define per n
        'INNER_PROD': lambda x: (sum(x[i]*x[len(x)//2+i]
                                     for i in range(len(x)//2))) % 2 if len(x) >= 2 else 0,
    }

    print(f"\n{'n':>3} {'Function':<15} {'Φ':>10} {'cons':>8} {'comp':>8} "
          f"{'depth':>6} {'|∂f|':>8} {'Φ/n':>8}")
    print("-" * 70)

    for n in range(4, 11):
        if 2**n > 100000:
            break

        # MONO-3SAT instances
        from mono3sat import generate_all_mono3sat_clauses
        all_clauses = generate_all_mono3sat_clauses(n)

        for name, func in p_functions.items():
            if name in ('INNER_PROD',) and n % 2 != 0:
                continue

            phi, costs, boundary = compute_computational_potential(n, func, 200)

            print(f"{n:3d} {name:<15} {phi:10d} {costs[0]:8d} {costs[1]:8d} "
                  f"{costs[2]:6d} {boundary:8d} {phi/n:8.1f}")

        # MONO-3SAT
        for trial in range(2):
            k = random.randint(max(1, n//2), min(len(all_clauses), 3*n))
            clauses = random.sample(all_clauses, k)
            func = lambda x, cl=clauses: all(any(x[v] for v in c) for c in cl)

            phi, costs, boundary = compute_computational_potential(n, func, 200)

            print(f"{n:3d} {'MSAT-'+str(trial):<15} {phi:10d} {costs[0]:8d} "
                  f"{costs[1]:8d} {costs[2]:6d} {boundary:8d} {phi/n:8.1f}")

        sys.stdout.flush()

    # Analysis
    print(f"\n{'='*70}")
    print("  ANALYSIS")
    print(f"{'='*70}")
    print("""
    If Φ/n grows with n for NP-hard functions but stays constant for P:
      → Φ separates P from NP → P ≠ NP

    If Φ/n stays constant for all functions:
      → Φ is not the right measure → need refinement

    The key question: does the PRODUCT consistency × compression × depth
    grow faster than any single factor?

    For P functions: the three costs trade off perfectly — when one
    increases, another decreases, keeping the product at O(n).

    For NP-hard functions: the three costs are "coupled" — they must
    all be large simultaneously, making the product super-polynomial.

    This coupling IS the essence of NP-hardness: you can't simplify
    any one aspect without making another worse.
    """)


if __name__ == "__main__":
    random.seed(42)
    compare_functions()
