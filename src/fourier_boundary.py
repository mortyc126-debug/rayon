"""
Fourier Analysis of the Boundary: A New Approach to Circuit Lower Bounds.

KEY IDEA:
For f: {0,1}^n → {0,1}, the Fourier expansion is:
  f(x) = Σ_S f̂(S) χ_S(x)  where χ_S(x) = (-1)^{Σ_{i∈S} x_i}

Each boundary transition (x_b, j, x_b⁺) with f(x_b)=0, f(x_b⁺)=1
creates the constraint:
  f(x_b⁺) - f(x_b) = 1
  ⟹ Σ_S f̂(S) [χ_S(x_b⁺) - χ_S(x_b)] = 1

Since x_b⁺ = x_b ⊕ e_j, and χ_S(x⊕e_j) = χ_S(x) · (-1)^{[j∈S]}:
  χ_S(x_b⁺) - χ_S(x_b) = χ_S(x_b) · [(-1)^{[j∈S]} - 1]
                          = { 0           if j ∉ S
                          = { -2·χ_S(x_b) if j ∈ S

So each boundary transition gives:
  -2 Σ_{S∋j} f̂(S) χ_S(x_b) = 1

This is a LINEAR CONSTRAINT on the Fourier coefficients f̂(S) for S ∋ j.

The RANK of the matrix of all such constraints is a lower bound on:
- The number of non-zero Fourier coefficients f̂(S) with j ∈ S
- Which relates to the CIRCUIT COMPLEXITY of f

HYPOTHESIS: The rank grows exponentially with n for NP-hard functions,
while it grows polynomially for P functions. If true, this gives a
new separation criterion.
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


def chi(S, x):
    """Fourier character χ_S(x) = (-1)^{Σ_{i∈S} x_i}"""
    parity = sum(x[i] for i in S) % 2
    return 1 - 2 * parity  # (-1)^parity


def compute_fourier_coefficients(n, f_values):
    """Compute all Fourier coefficients f̂(S) = (1/2^n) Σ_x f(x) χ_S(x)"""
    coeffs = {}
    for mask in range(2**n):
        S = frozenset(i for i in range(n) if (mask >> i) & 1)
        total = 0.0
        for bits in range(2**n):
            x = tuple((bits >> i) & 1 for i in range(n))
            fx = f_values[x]
            total += fx * chi(S, x)
        coeffs[S] = total / (2**n)
    return coeffs


def compute_boundary_constraint_matrix(n, clauses):
    """Compute the constraint matrix from boundary transitions.

    Each row = one boundary transition (x_b, j)
    Each column = one Fourier coefficient f̂(S) with j ∈ S
    Entry = -2 · χ_S(x_b)

    The rank of this matrix bounds the number of non-zero Fourier
    coefficients needed, which relates to circuit complexity.
    """
    # Compute solutions
    solutions = set()
    for bits in range(2**n):
        assignment = tuple((bits >> i) & 1 for i in range(n))
        if evaluate_mono3sat(assignment, clauses):
            solutions.add(assignment)

    # Compute boundary transitions
    transitions = []
    for bits in range(2**n):
        x_b = tuple((bits >> i) & 1 for i in range(n))
        if x_b in solutions:
            continue
        for j in range(n):
            if x_b[j] == 0:
                flipped = list(x_b)
                flipped[j] = 1
                if tuple(flipped) in solutions:
                    transitions.append((x_b, j))

    if not transitions:
        return None

    # Build constraint matrix
    # Columns: all subsets S that contain at least one transition variable j
    # For efficiency, only consider S with |S| ≤ some bound

    # All subsets containing j, for each j that appears in transitions
    active_js = set(j for _, j in transitions)

    # Enumerate relevant columns (subsets S)
    all_columns = []
    for mask in range(1, 2**n):  # skip empty set
        S = frozenset(i for i in range(n) if (mask >> i) & 1)
        # S must contain at least one active j
        if S & active_js:
            all_columns.append(S)

    # Build matrix: rows = transitions, columns = subsets S
    # Entry[t, S] = -2 · χ_S(x_b) if j ∈ S, else 0
    matrix = []
    for x_b, j in transitions:
        row = []
        for S in all_columns:
            if j in S:
                row.append(-2.0 * chi(S, x_b))
            else:
                row.append(0.0)
        matrix.append(row)

    return matrix, transitions, all_columns


def matrix_rank(matrix, tol=1e-10):
    """Compute rank of a matrix using Gaussian elimination."""
    if not matrix:
        return 0

    m = len(matrix)
    ncols = len(matrix[0])
    mat = [row[:] for row in matrix]  # copy

    rank = 0
    for col in range(ncols):
        # Find pivot
        pivot_row = None
        for row in range(rank, m):
            if abs(mat[row][col]) > tol:
                pivot_row = row
                break

        if pivot_row is None:
            continue

        # Swap with current rank row
        mat[rank], mat[pivot_row] = mat[pivot_row], mat[rank]

        # Eliminate
        pivot_val = mat[rank][col]
        for row in range(m):
            if row == rank:
                continue
            if abs(mat[row][col]) > tol:
                factor = mat[row][col] / pivot_val
                for c in range(ncols):
                    mat[row][c] -= factor * mat[rank][c]

        rank += 1

    return rank


def analyze_fourier_constraints(n, clauses):
    """Full Fourier constraint analysis."""
    result = compute_boundary_constraint_matrix(n, clauses)
    if result is None:
        return None

    matrix, transitions, columns = result

    print(f"\n  Fourier constraint matrix: {len(transitions)} rows × {len(columns)} cols")

    # Compute rank
    if len(transitions) <= 2000 and len(columns) <= 2000:
        rank = matrix_rank(matrix)
        print(f"  Matrix rank: {rank}")
        print(f"  Rank / n: {rank/n:.2f}")
        print(f"  Rank / |transitions|: {rank/len(transitions):.4f}")

        if rank > 0:
            rank_base = rank ** (1.0/n) if rank > 1 else 0
            print(f"  Rank base (rank^(1/n)): {rank_base:.4f}")
        return rank
    else:
        print(f"  Matrix too large for full rank computation")
        # Sample rows and compute rank of submatrix
        sample_size = min(500, len(transitions))
        indices = random.sample(range(len(transitions)), sample_size)
        sub_matrix = [matrix[i] for i in indices]
        rank = matrix_rank(sub_matrix)
        print(f"  Sampled rank ({sample_size} rows): {rank}")
        return rank


def analyze_per_variable_constraints(n, clauses):
    """Analyze constraints per variable j separately.

    For each j, the constraints from transitions using j form a
    subsystem. The rank of this subsystem measures how "complex"
    the boundary is in direction j.
    """
    solutions = set()
    for bits in range(2**n):
        assignment = tuple((bits >> i) & 1 for i in range(n))
        if evaluate_mono3sat(assignment, clauses):
            solutions.add(assignment)

    print(f"\n  Per-variable Fourier constraint ranks:")

    total_rank = 0

    for j in range(n):
        # Transitions using variable j
        trans_j = []
        for bits in range(2**n):
            x_b = tuple((bits >> i) & 1 for i in range(n))
            if x_b in solutions or x_b[j] == 1:
                continue
            flipped = list(x_b)
            flipped[j] = 1
            if tuple(flipped) in solutions:
                trans_j.append(x_b)

        if not trans_j:
            print(f"    x_{j}: 0 transitions")
            continue

        # Columns: subsets S containing j, |S| ≤ n
        columns_j = []
        for mask in range(1, 2**n):
            S = frozenset(i for i in range(n) if (mask >> i) & 1)
            if j in S:
                columns_j.append(S)

        # Build matrix
        mat = []
        for x_b in trans_j:
            row = [-2.0 * chi(S, x_b) for S in columns_j]
            mat.append(row)

        if len(mat) <= 1000 and len(columns_j) <= 1000:
            rank_j = matrix_rank(mat)
        else:
            # Sample
            sample = min(300, len(mat))
            indices = random.sample(range(len(mat)), sample)
            sub = [mat[i] for i in indices]
            rank_j = matrix_rank(sub)

        total_rank += rank_j
        print(f"    x_{j}: {len(trans_j)} transitions, rank={rank_j}, "
              f"rank/|trans|={rank_j/len(trans_j):.3f}")

    print(f"  Total rank (sum over j): {total_rank}")
    return total_rank


def fourier_scaling():
    """Scale Fourier rank analysis and look for growth patterns."""
    print("=" * 80)
    print("  FOURIER BOUNDARY RANK SCALING")
    print("  rank(constraint matrix) as function of n")
    print("=" * 80)

    from mono3sat import generate_all_mono3sat_clauses

    results = {}

    for n in range(4, 15):
        if 2**n > 50000:  # need 2^n columns
            break

        all_clauses = generate_all_mono3sat_clauses(n)
        trials = max(20, 200 // n)
        if n >= 10:
            trials = 10

        best_rank = 0
        best_clauses = None
        best_transitions = 0

        for _ in range(trials):
            k = random.randint(max(1, n//2), min(len(all_clauses), 4*n))
            clauses = random.sample(all_clauses, k)

            # Quick boundary size check
            solutions = set()
            for bits in range(2**n):
                assignment = tuple((bits >> i) & 1 for i in range(n))
                if evaluate_mono3sat(assignment, clauses):
                    solutions.add(assignment)

            if not solutions:
                continue

            trans_count = 0
            for bits in range(2**n):
                x_b = tuple((bits >> i) & 1 for i in range(n))
                if x_b in solutions:
                    continue
                for j in range(n):
                    if x_b[j] == 0:
                        flipped = list(x_b)
                        flipped[j] = 1
                        if tuple(flipped) in solutions:
                            trans_count += 1
                            break

            if trans_count > best_transitions:
                best_transitions = trans_count
                best_clauses = clauses[:]

        if best_clauses:
            print(f"\nn={n}:")
            rank = analyze_fourier_constraints(n, best_clauses)
            per_var_rank = analyze_per_variable_constraints(n, best_clauses)

            if rank is not None and rank > 0:
                results[n] = {
                    'rank': rank,
                    'per_var_rank': per_var_rank,
                    'transitions': best_transitions,
                }

        sys.stdout.flush()

    # Growth analysis
    print(f"\n\n{'='*80}")
    print("  FOURIER RANK GROWTH SUMMARY")
    print(f"{'='*80}")

    ns = sorted(results.keys())
    print(f"\n{'n':>4} {'rank':>8} {'base':>8} {'|trans|':>8} {'rank/n':>8} "
          f"{'per_var':>8}")

    for n_val in ns:
        r = results[n_val]
        rank = r['rank']
        base = rank ** (1.0/n_val) if rank > 1 else 0
        print(f"{n_val:4d} {rank:8d} {base:8.4f} {r['transitions']:8d} "
              f"{rank/n_val:8.2f} {r['per_var_rank']:8d}")

    # Fit: rank ~ α^n?
    if len(ns) >= 4:
        bases = [results[n_val]['rank'] ** (1.0/n_val)
                 for n_val in ns if results[n_val]['rank'] > 1]
        if bases:
            print(f"\n  Average rank base: {sum(bases)/len(bases):.4f}")
            print(f"  Last rank base: {bases[-1]:.4f}")

            if bases[-1] > 1.5:
                print("  >>> Fourier rank grows EXPONENTIALLY — promising!")
                print("  >>> Each independent constraint needs a distinct circuit gate")
            else:
                print("  >>> Fourier rank growth is moderate")


def fourier_vs_circuit_comparison(n, clauses):
    """Compare Fourier rank with known circuit complexity measures.

    Key connection: the number of non-zero Fourier coefficients
    is related to:
    - Decision tree complexity: #leaves ≥ #non-zero coefficients
    - Formula size: formula_size(f) ≥ sparsity(f) / 2
    - Circuit size: less direct, but Fourier sparsity bounds apply
    """
    # Compute all Fourier coefficients
    f_values = {}
    for bits in range(2**n):
        x = tuple((bits >> i) & 1 for i in range(n))
        f_values[x] = 1 if evaluate_mono3sat(x, clauses) else 0

    coeffs = compute_fourier_coefficients(n, f_values)

    # Fourier sparsity (number of non-zero coefficients)
    nonzero = sum(1 for v in coeffs.values() if abs(v) > 1e-10)
    l1_norm = sum(abs(v) for v in coeffs.values())
    l2_norm = sum(v**2 for v in coeffs.values()) ** 0.5

    # Spectral norm (max |f̂(S)|)
    spectral = max(abs(v) for v in coeffs.values())

    # Degree (max |S| with f̂(S) ≠ 0)
    degree = max(len(S) for S, v in coeffs.items() if abs(v) > 1e-10)

    print(f"\n  Fourier spectrum analysis (n={n}):")
    print(f"    Sparsity (non-zero coeffs): {nonzero} / {2**n}")
    print(f"    L1 norm: {l1_norm:.4f}")
    print(f"    L2 norm: {l2_norm:.4f}")
    print(f"    Spectral norm: {spectral:.4f}")
    print(f"    Degree: {degree}")

    # Degree distribution
    deg_dist = defaultdict(int)
    deg_l1 = defaultdict(float)
    for S, v in coeffs.items():
        if abs(v) > 1e-10:
            deg_dist[len(S)] += 1
            deg_l1[len(S)] += abs(v)

    print(f"\n    Degree distribution:")
    for d in sorted(deg_dist.keys()):
        print(f"      degree {d}: {deg_dist[d]} coeffs, "
              f"L1 contribution: {deg_l1[d]:.4f}")

    return {
        'sparsity': nonzero,
        'l1': l1_norm,
        'degree': degree,
        'spectral': spectral,
    }


if __name__ == "__main__":
    random.seed(42)

    # Phase 1: Scaling analysis
    fourier_scaling()

    # Phase 2: Detailed spectrum for small instances
    print(f"\n\n{'='*80}")
    print("  DETAILED FOURIER SPECTRUM ANALYSIS")
    print(f"{'='*80}")

    from mono3sat import generate_all_mono3sat_clauses

    for n in [6, 8, 10]:
        if 2**n > 50000:
            break

        all_clauses = generate_all_mono3sat_clauses(n)
        best_boundary = 0
        best_clauses = None

        for _ in range(100):
            k = random.randint(max(1, n//2), min(len(all_clauses), 4*n))
            clauses = random.sample(all_clauses, k)
            sols = set()
            for bits in range(2**n):
                x = tuple((bits >> i) & 1 for i in range(n))
                if evaluate_mono3sat(x, clauses):
                    sols.add(x)
            if 0 < len(sols) < 2**n:
                trans = 0
                for bits in range(2**n):
                    x = tuple((bits >> i) & 1 for i in range(n))
                    if x not in sols:
                        for j in range(n):
                            if x[j] == 0:
                                fl = list(x); fl[j] = 1
                                if tuple(fl) in sols:
                                    trans += 1
                                    break
                if trans > best_boundary:
                    best_boundary = trans
                    best_clauses = clauses[:]

        if best_clauses:
            fourier_vs_circuit_comparison(n, best_clauses)
