"""
BISECTION WIDTH → TREEWIDTH → CIRCUIT SIZE.

tw ≥ bisection_width / 6  (standard graph theory).

bisection_width of circuit DAG ≥ communication complexity of f
under the partition induced by the bisection on INPUT variables.

So: tw ≥ CC(f, best partition) / 6.

For CLIQUE: we need CC(CLIQUE, some partition) ≥ ω(log N).

PARTITION STRATEGY for k-CLIQUE on N vertices:
  Split EDGES (inputs) into L and R based on VERTEX partition.
  Vertices {1,...,N/2} = "left", {N/2+1,...,N} = "right".

  L-edges: both endpoints in left half.
  R-edges: both endpoints in right half.
  Cross-edges: one endpoint in each half.

  Alice knows L-edges + cross-edges, Bob knows R-edges + cross-edges.
  (Or some other split.)

  To detect a k-clique spanning both halves:
    Need cross-edge info → communication.

  A k-clique Q with |Q∩left| = a, |Q∩right| = k-a:
    Need a(k-a) cross-edges to be present.
    Alice and Bob must verify this jointly.

COMMUNICATION LOWER BOUND:
  Use a REDUCTION from a known hard communication problem.

  SET DISJOINTNESS on m bits: Alice has set A, Bob has set B,
  both subsets of [m]. They want to determine if A ∩ B = ∅.
  CC(DISJ_m) = Ω(m).

  Can we REDUCE DISJ to CLIQUE?

  If we embed DISJ_m into CLIQUE such that CLIQUE = 1 iff DISJ = 0:
    CC(CLIQUE) ≥ CC(DISJ_m) = Ω(m).

  For m = Ω(N^{1/3}): CC(CLIQUE) ≥ Ω(N^{1/3}) = ω(log N) → P ≠ NP!

EXPERIMENT: Test communication complexity of CLIQUE at various partitions.
"""

import itertools
from collections import defaultdict
import random
import math
import sys


def compute_cc_upper_bound(n, tt, partition_A):
    """Upper bound on deterministic CC: just the number of A-variables.
    Alice sends all her bits → Bob computes.
    """
    return len(partition_A)


def compute_cc_rectangle_bound(n, tt, partition_A):
    """Lower bound on CC via rectangle/rank method.

    CC ≥ log₂(rank(M)) where M is the communication matrix.
    M[x_A, x_B] = f(x_A, x_B).
    """
    A = sorted(partition_A)
    B = sorted(set(range(n)) - set(A))

    nA = len(A)
    nB = len(B)

    # Build matrix and compute GF(2) rank
    matrix = []
    for a_bits in range(2**nA):
        row = []
        for b_bits in range(2**nB):
            full = [0] * n
            for i, var in enumerate(A):
                full[var] = (a_bits >> i) & 1
            for i, var in enumerate(B):
                full[var] = (b_bits >> i) & 1
            bits = sum(full[j] << j for j in range(n))
            row.append(tt[bits])
        matrix.append(row)

    # GF(2) rank
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

    return math.ceil(math.log2(max(1, rank)))


def max_cc_over_partitions(n, tt, num_trials=100):
    """Find the partition that maximizes CC lower bound."""
    best_cc = 0
    best_partition = None

    for _ in range(num_trials):
        k = n // 2
        A = tuple(sorted(random.sample(range(n), k)))
        cc = compute_cc_rectangle_bound(n, tt, A)
        if cc > best_cc:
            best_cc = cc
            best_partition = A

    return best_cc, best_partition


def vertex_partition_cc(N, k_clique, tt, n):
    """Compute CC for VERTEX-based partition of CLIQUE.

    Split vertices into L = {0,...,N/2-1} and R = {N/2,...,N-1}.
    Alice gets L-internal edges + half of cross-edges.
    Bob gets R-internal edges + other half of cross-edges.
    """
    edge_idx = {}; idx = 0
    for i in range(N):
        for j in range(i+1, N):
            edge_idx[(i,j)] = idx; idx += 1

    half = N // 2

    # Alice's edges: edges within left half
    A_edges = []
    for i in range(half):
        for j in range(i+1, half):
            A_edges.append(edge_idx[(i,j)])

    # Add half of cross edges to Alice
    cross_edges = []
    for i in range(half):
        for j in range(half, N):
            cross_edges.append(edge_idx[(i,j)])

    # Give first half of cross to Alice
    A_edges.extend(cross_edges[:len(cross_edges)//2])

    partition_A = tuple(sorted(A_edges))
    cc = compute_cc_rectangle_bound(n, tt, partition_A)

    return cc, len(partition_A), n - len(partition_A)


def main():
    random.seed(42)
    print("=" * 70)
    print("  COMMUNICATION COMPLEXITY OF CLIQUE")
    print("  CC ≥ ω(log N) → tw ≥ ω(log N) → P ≠ NP")
    print("=" * 70)

    print(f"\n  {'Function':<20} {'N':>3} {'n':>5} {'max CC':>7} "
          f"{'log n':>6} {'CC/log n':>9} {'vertex CC':>10}")
    print("  " + "-" * 65)

    for N in range(4, 8):
        n = N*(N-1)//2
        if 2**n > 200000:
            break

        # Build k-clique truth tables
        for k in [3, 4]:
            if k > N - 1:
                continue

            edge_idx = {}; idx = 0
            for i in range(N):
                for j in range(i+1, N):
                    edge_idx[(i,j)] = idx; edge_idx[(j,i)] = idx; idx += 1

            tt = {}
            for bits in range(2**n):
                x = tuple((bits >> j) & 1 for j in range(n))
                has = False
                for combo in itertools.combinations(range(N), k):
                    if all(x[edge_idx[(combo[a],combo[b])]]
                           for a in range(len(combo)) for b in range(a+1,len(combo))):
                        has = True; break
                tt[bits] = 1 if has else 0

            max_cc, best_part = max_cc_over_partitions(n, tt, 200)
            log_n = math.log2(max(2, n))

            v_cc, v_a, v_b = vertex_partition_cc(N, k, tt, n)

            print(f"  {str(k)+'-CLQ K'+str(N):<20} {N:>3} {n:>5} {max_cc:>7} "
                  f"{log_n:>6.1f} {max_cc/log_n:>9.2f} {v_cc:>10}")
            sys.stdout.flush()

    # Compare with easy functions
    for n in [6, 10, 15]:
        if 2**n > 200000:
            break
        # OR
        tt_or = {b: 0 if b == 0 else 1 for b in range(2**n)}
        cc_or, _ = max_cc_over_partitions(n, tt_or, 100)
        log_n = math.log2(n)
        print(f"  {'OR-'+str(n):<20} {'':>3} {n:>5} {cc_or:>7} "
              f"{log_n:>6.1f} {cc_or/log_n:>9.2f}")

        # MAJ
        tt_maj = {b: 1 if bin(b).count('1') > n/2 else 0 for b in range(2**n)}
        cc_maj, _ = max_cc_over_partitions(n, tt_maj, 100)
        print(f"  {'MAJ-'+str(n):<20} {'':>3} {n:>5} {cc_maj:>7} "
              f"{log_n:>6.1f} {cc_maj/log_n:>9.2f}")

    print(f"\n{'='*70}")
    print("  CC SCALING ANALYSIS")
    print(f"{'='*70}")
    print("""
    CC/log(n) tells us if CC = O(log n) or larger.

    For P ≠ NP via treewidth:
      CC(CLIQUE, some partition) ≥ ω(log N) → tw ≥ CC/6 → super-poly size

    KEY: Does CC/log(n) GROW with N for CLIQUE but stay constant for P?

    If CC(CLIQUE) grows as N^ε for some ε > 0: SUPER-LOGARITHMIC.
    Combined with formula bound: P ≠ NP.

    The SET DISJOINTNESS reduction would give:
      CC(CLIQUE) ≥ Ω(k) = Ω(N^{1/3}) for k = N^{1/3}.
      This is ω(log N). SUFFICIENT!

    But: the reduction from DISJ to CLIQUE is non-trivial.
    Need: encode DISJ as a CLIQUE sub-problem.
    """)


if __name__ == "__main__":
    main()
