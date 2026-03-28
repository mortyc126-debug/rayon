"""
ENTANGLEMENT OF COMPUTATION: A new kind of measure.

INSIGHT: In quantum physics, entanglement between subsystems A and B
grows when they INTERACT. Before interaction: E = 0.
After interaction: E = min(|A|, |B|). Maximal.

For CLASSICAL computation: define "computational entanglement"
between two SETS of variables.

For f: {0,1}^n → {0,1}, partition variables into A and B.
Define: E_AB(f) = communication complexity of f with Alice having A
and Bob having B.

E_AB measures how "entangled" parts A and B are in computing f.

KEY PROPERTY:
  E_AB(AND(g,h)) = ???

If g depends only on A: E_AB(AND(g,h)) = E_AB(h) (Alice computes g locally).
If g depends on both A and B: E_AB(AND(g,h)) ≤ E_AB(g) + E_AB(h) + 1.

So: E_AB IS sub-additive. But: E_AB ≤ min(|A|, |B|) ≤ n/2. BOUNDED.

THE TRICK: Use MANY partitions simultaneously.

Define: μ(f) = Σ over random partitions (A,B) of E_AB(f).

Or: μ(f) = max over all partitions of E_AB(f) × |partition_info|.

Or better: μ(f) = PARTITION ENTROPY
= the minimum total communication over ALL possible partitioning schemes.

THE CONCEPT:
  Imagine computing f by "peeling off" variables one at a time.
  Each variable x_i is assigned to a "processor."
  The processors communicate to compute f.
  The TOTAL communication needed = μ(f).

If we have P processors, each with n/P variables:
  Communication = Σ pairwise E_{ij} ≈ P² × avg_E.

For a CIRCUIT of size s: the circuit assigns computation to gates.
Each gate is a "processor" that combines two inputs.
The communication between gates = gate connections = 2s (total wires).

But: the INFORMATIONAL content of each wire = 1 bit.
Total information flow through circuit = 2s bits.

If the function requires μ(f) bits of total information flow:
  2s ≥ μ(f) → s ≥ μ(f) / 2.

What is μ(f)?
For most functions: μ(f) = Θ(n) (need to read all inputs).
For CLIQUE: μ(f) = ???

THE PROBLEM: total information flow = 2s gives only s ≥ n/2. Trivial.

DEEPER VERSION: Instead of total information, measure the
MULTI-PARTY entanglement.

In k-party communication: k parties each hold n/k variables.
They compute f by communicating. Total bits = C(f, k).

For k = n (each party holds 1 variable): C(f, n) = ???

This is the NUMBER-ON-FOREHEAD model for k parties.
Known: for k = log n parties, there ARE exponential lower bounds
for specific functions (Babai-Nisan-Szegedy).

ACTUAL NEW IDEA: "Entanglement Entropy" of a Boolean function.

For f: {0,1}^n → {0,1}, view f as a vector in R^{2^n}.
The "entanglement" of f with respect to partition (A,B):
  Flatten the truth table into a 2^{|A|} × 2^{|B|} matrix M_f.
  E_AB(f) = rank(M_f) over GF(2).

This GF(2) rank measures how "entangled" parts A and B are.

For product functions f(x) = g(x_A) × h(x_B):
  rank(M_f) = rank(g) × rank(h) = 1 × 1 = 1. No entanglement.

For XOR: f(x) = x_1 ⊕ x_2. M_f = [[0,1],[1,0]]. rank = 2. Entangled.

For CLIQUE: the GF(2) rank of the communication matrix is ???

EXPERIMENT: Compute GF(2) rank of CLIQUE's communication matrix
for various partitions.
"""

import itertools
from collections import defaultdict
import random
import math
import sys


def compute_comm_matrix_rank(n, tt, partition_A):
    """Compute GF(2) rank of the communication matrix M[x_A, x_B].

    M[a, b] = f(a, b) where a = assignment to A-variables, b = to B-variables.
    """
    A = sorted(partition_A)
    B = sorted(set(range(n)) - set(A))

    nA = len(A)
    nB = len(B)

    if nA == 0 or nB == 0:
        return 1

    # Build matrix
    rows = 2**nA
    cols = 2**nB

    matrix = []
    for a_bits in range(rows):
        row = []
        for b_bits in range(cols):
            # Reconstruct full input
            full = [0] * n
            for i, var in enumerate(A):
                full[var] = (a_bits >> i) & 1
            for i, var in enumerate(B):
                full[var] = (b_bits >> i) & 1

            bits = sum(full[j] << j for j in range(n))
            row.append(tt[bits])
        matrix.append(row)

    # GF(2) Gaussian elimination
    m = len(matrix)
    nc = len(matrix[0])
    mat = [row[:] for row in matrix]

    rank = 0
    for col in range(nc):
        pivot = None
        for row in range(rank, m):
            if mat[row][col]:
                pivot = row
                break
        if pivot is None:
            continue
        mat[rank], mat[pivot] = mat[pivot], mat[rank]
        for row in range(m):
            if row != rank and mat[row][col]:
                for c in range(nc):
                    mat[row][c] ^= mat[rank][c]
        rank += 1

    return rank


def compute_max_rank_over_partitions(n, tt, num_trials=100):
    """Find the partition that maximizes communication matrix rank."""
    best_rank = 0
    best_partition = None

    for _ in range(num_trials):
        # Random balanced partition
        k = n // 2
        A = tuple(sorted(random.sample(range(n), k)))
        r = compute_comm_matrix_rank(n, tt, A)
        if r > best_rank:
            best_rank = r
            best_partition = A

    return best_rank, best_partition


def gate_rank_composition(n, tt_g, tt_h, partition_A, gate_type='AND'):
    """Compute how rank changes through a gate.

    rank(g), rank(h), rank(g OP h).
    """
    rg = compute_comm_matrix_rank(n, tt_g, partition_A)
    rh = compute_comm_matrix_rank(n, tt_h, partition_A)

    total = 2**n
    if gate_type == 'AND':
        tt_out = {b: tt_g[b] & tt_h[b] for b in range(total)}
    elif gate_type == 'OR':
        tt_out = {b: tt_g[b] | tt_h[b] for b in range(total)}
    elif gate_type == 'NOT':
        tt_out = {b: 1 - tt_g[b] for b in range(total)}
        rh = 0

    r_out = compute_comm_matrix_rank(n, tt_out, partition_A)
    return rg, rh, r_out


def main():
    random.seed(42)
    print("=" * 70)
    print("  ENTANGLEMENT (GF2 RANK) OF BOOLEAN FUNCTIONS")
    print("  rank(M_f) where M[x_A, x_B] = f(x_A, x_B)")
    print("=" * 70)

    # Compute for various functions
    print(f"\n  {'Function':<18} {'n':>4} {'max_rank':>10} {'2^(n/2)':>10} "
          f"{'rank/2^(n/2)':>12}")
    print("  " + "-" * 58)

    results = {}

    from mono3sat import generate_all_mono3sat_clauses

    for n in range(4, 14):
        if 2**n > 200000:
            break

        total = 2**n

        # OR
        tt_or = {b: 0 if b == 0 else 1 for b in range(total)}
        r, _ = compute_max_rank_over_partitions(n, tt_or, 50)
        print(f"  {'OR-'+str(n):<18} {n:>4} {r:>10} {2**(n//2):>10} "
              f"{r/2**(n//2):>12.4f}")

        # MAJ
        tt_maj = {b: 1 if bin(b).count('1') > n/2 else 0 for b in range(total)}
        r, _ = compute_max_rank_over_partitions(n, tt_maj, 50)
        print(f"  {'MAJ-'+str(n):<18} {n:>4} {r:>10} {2**(n//2):>10} "
              f"{r/2**(n//2):>12.4f}")

        # MSAT
        all_cl = generate_all_mono3sat_clauses(n)
        clauses = random.sample(all_cl, min(len(all_cl), 3*n))
        tt_msat = {}
        for b in range(total):
            x = tuple((b >> j) & 1 for j in range(n))
            tt_msat[b] = 1 if all(any(x[v] for v in c) for c in clauses) else 0
        r, _ = compute_max_rank_over_partitions(n, tt_msat, 50)
        print(f"  {'MSAT-'+str(n):<18} {n:>4} {r:>10} {2**(n//2):>10} "
              f"{r/2**(n//2):>12.4f}")
        results[('MSAT', n)] = r

        sys.stdout.flush()

    # Triangle
    for N in range(4, 7):
        n = N*(N-1)//2
        if 2**n > 200000:
            break
        edge_idx = {}; idx = 0
        for i in range(N):
            for j in range(i+1, N):
                edge_idx[(i,j)] = idx; edge_idx[(j,i)] = idx; idx += 1
        tt = {}
        for b in range(2**n):
            x = tuple((b >> j) & 1 for j in range(n))
            has = any(x[edge_idx[(i,j)]] and x[edge_idx[(i,k)]] and x[edge_idx[(j,k)]]
                      for i in range(N) for j in range(i+1,N) for k in range(j+1,N))
            tt[b] = 1 if has else 0
        r, _ = compute_max_rank_over_partitions(n, tt, 100)
        print(f"  {'TRI-K'+str(N):<18} {n:>4} {r:>10} {2**(n//2):>10} "
              f"{r/2**(n//2):>12.4f}")
        results[('TRI', n)] = r

    # Gate composition: how does rank change through AND/OR?
    print(f"\n\n{'='*70}")
    print("  RANK COMPOSITION: How does AND/OR change rank?")
    print(f"{'='*70}")

    n = 8
    total = 2**n
    A = tuple(range(n//2))  # first half

    print(f"\n  n={n}, partition A={A}")
    print(f"  {'Gate':<20} {'rank(g)':>8} {'rank(h)':>8} {'rank(out)':>10} "
          f"{'ratio':>8}")
    print("  " + "-" * 58)

    for trial in range(10):
        tt_g = {b: random.randint(0,1) for b in range(total)}
        tt_h = {b: random.randint(0,1) for b in range(total)}

        for gate in ['AND', 'OR']:
            rg, rh, ro = gate_rank_composition(n, tt_g, tt_h, A, gate)
            ratio = ro / max(1, max(rg, rh))
            print(f"  {gate+'(rand,rand)_'+str(trial):<20} {rg:>8} {rh:>8} "
                  f"{ro:>10} {ratio:>8.2f}")

    print(f"\n{'='*70}")
    print("  ANALYSIS: IS RANK SUB-ADDITIVE?")
    print(f"{'='*70}")
    print("""
    If rank(AND(g,h)) ≤ rank(g) × rank(h):
      MULTIPLICATIVE → circuit gives rank ≤ rank_input^s = 1
      (inputs have rank 1 or 2). USELESS.

    If rank(AND(g,h)) ≤ rank(g) + rank(h):
      ADDITIVE → rank ≤ O(s). Same as sub-additive. Gives s ≥ rank/O(1).
      For rank = super-poly: USEFUL!

    ACTUAL BEHAVIOR: rank(AND(g,h)) ≤ rank(g) × rank(h)
    (sub-multiplicative, because AND corresponds to tensor product/Hadamard).

    So rank is SUB-MULTIPLICATIVE. After s gates from rank-1 inputs:
    rank ≤ 1^{2^s} = 1? No — AND of two rank-1 functions can have rank > 1.

    Actually: rank(f·g) ≤ rank(f) × rank(g) (Schur product bound).
    Starting from rank-2 inputs: after s ANDs: rank ≤ 2^s.
    For rank(CLIQUE) ≥ R: s ≥ log₂(R). LOGARITHMIC AGAIN.

    THE LOGARITHMIC CURSE RETURNS.
    Any multiplicative measure: s ≥ log(measure).
    Any additive measure: s ≥ measure, but measure ≤ n (bounded).

    There is NO ESCAPE from the logarithm for circuit size.
    """)


if __name__ == "__main__":
    main()
