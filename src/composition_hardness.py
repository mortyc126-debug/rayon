"""
Composition-Based Hardness Amplification.

IDEA: Take MONO-3SAT function f and compose with inner function g.
F(y) = f(g(y_1),...,g(y_n)) where each y_i is a block of m bits.

If g is chosen to "use up" NOT gates (e.g., g = MAJ or PARITY),
then the composition F requires:
  - NOT gates for computing each g
  - Additional circuit structure for f

The NOT gates used for g CAN'T also help with f,
potentially creating a stronger lower bound.

This is inspired by the composition theorem in communication
complexity (Raz-McKenzie) and the KRW conjecture.

KEY QUESTION: Does the boundary |∂F| grow as |∂f| · |∂g|^n?
If yes, the Z₂ threshold improves because the inner function
"consumes" NOT gates.

Also exploring: "Random restriction + boundary preservation".
Apply random restrictions that preserve boundary structure
while simplifying the circuit.
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


def majority(bits):
    """Majority function on bits."""
    return 1 if sum(bits) > len(bits) / 2 else 0


def parity(bits):
    """Parity (XOR) of bits."""
    return sum(bits) % 2


def threshold_k(bits, k):
    """Threshold function: 1 if sum(bits) >= k."""
    return 1 if sum(bits) >= k else 0


def compose_function(n, clauses, inner_func, m):
    """Compute the composed function F(y) = f(g(y_1),...,g(y_n)).

    y has n*m bits, divided into n blocks of m bits each.
    g is applied to each block to produce one bit.
    f is applied to the n resulting bits.
    """
    total_bits = n * m

    def F(y):
        # Apply inner function to each block
        x = []
        for i in range(n):
            block = y[i*m:(i+1)*m]
            x.append(inner_func(block))
        # Apply outer function
        return evaluate_mono3sat(tuple(x), clauses)

    return F, total_bits


def compute_composed_boundary(n, clauses, inner_func, m):
    """Compute boundary of composed function F = f ∘ g."""
    F, total_bits = compose_function(n, clauses, inner_func, m)

    if total_bits > 20:  # too large for exhaustive
        return None

    solutions = set()
    for bits in range(2**total_bits):
        y = tuple((bits >> i) & 1 for i in range(total_bits))
        if F(y):
            solutions.add(y)

    # Compute boundary (now for general function, both 0→1 and 1→0 flips matter)
    boundary_01 = []  # 0→1 transitions
    boundary_10 = []  # 1→0 transitions

    for bits in range(2**total_bits):
        y = tuple((bits >> i) & 1 for i in range(total_bits))
        is_sol = y in solutions

        for j in range(total_bits):
            flipped = list(y)
            flipped[j] = 1 - flipped[j]
            flipped_t = tuple(flipped)
            flipped_is_sol = flipped_t in solutions

            if not is_sol and flipped_is_sol:
                boundary_01.append((y, j, flipped_t))
            elif is_sol and not flipped_is_sol:
                boundary_10.append((y, j, flipped_t))

    return {
        'solutions': len(solutions),
        'total': 2**total_bits,
        'boundary_01': len(boundary_01),
        'boundary_10': len(boundary_10),
        'total_boundary': len(boundary_01) + len(boundary_10),
        'total_bits': total_bits,
    }


def analyze_composition():
    """Compare boundary growth for different inner functions."""
    print("=" * 80)
    print("  COMPOSITION HARDNESS AMPLIFICATION")
    print("  F(y) = f(g(y_1),...,g(y_n))  where g varies")
    print("=" * 80)

    from mono3sat import generate_all_mono3sat_clauses

    # Test with small n and m
    for n in [3, 4, 5]:
        all_clauses = generate_all_mono3sat_clauses(n)

        # Find a good MONO-3SAT instance
        best_clauses = None
        best_boundary = 0

        for _ in range(50):
            k = random.randint(1, min(len(all_clauses), 3*n))
            clauses = random.sample(all_clauses, k)
            sols = sum(1 for bits in range(2**n)
                      if evaluate_mono3sat(tuple((bits>>i)&1 for i in range(n)), clauses))
            if 0 < sols < 2**n:
                trans = 0
                for bits in range(2**n):
                    x = tuple((bits>>i)&1 for i in range(n))
                    if not evaluate_mono3sat(x, clauses):
                        for j in range(n):
                            if x[j] == 0:
                                fl = list(x); fl[j] = 1
                                if evaluate_mono3sat(tuple(fl), clauses):
                                    trans += 1
                                    break
                if trans > best_boundary:
                    best_boundary = trans
                    best_clauses = clauses[:]

        if not best_clauses:
            continue

        print(f"\nOuter function: MONO-3SAT on n={n}, |∂f|={best_boundary}")

        # Base case: identity (m=1)
        print(f"\n  {'Inner g':<15} {'m':>3} {'N=nm':>5} {'|sol|':>8} "
              f"{'|∂₀₁|':>8} {'|∂₁₀|':>8} {'|∂|':>8} {'base':>8}")
        print("  " + "-" * 70)

        inner_funcs = {
            'identity': (lambda bits: bits[0], 1),
            'AND_2': (lambda bits: bits[0] & bits[1], 2),
            'OR_2': (lambda bits: bits[0] | bits[1], 2),
            'MAJ_3': (lambda bits: majority(bits), 3),
            'XOR_2': (lambda bits: parity(bits), 2),
        }

        if n <= 4:
            inner_funcs['MAJ_5'] = (lambda bits: majority(bits), 5)
            inner_funcs['XOR_3'] = (lambda bits: parity(bits), 3)
            inner_funcs['TH2_3'] = (lambda bits: threshold_k(bits, 2), 3)

        for name, (gfunc, m) in sorted(inner_funcs.items()):
            total = n * m
            if total > 20:
                continue

            result = compute_composed_boundary(n, best_clauses, gfunc, m)
            if result is None:
                continue

            total_b = result['total_boundary']
            base = total_b ** (1.0 / result['total_bits']) if total_b > 1 else 0

            print(f"  {name:<15} {m:3d} {result['total_bits']:5d} "
                  f"{result['solutions']:8d} {result['boundary_01']:8d} "
                  f"{result['boundary_10']:8d} {total_b:8d} {base:8.4f}")

    # KEY ANALYSIS: Does composition with non-monotone g create
    # boundary transitions in BOTH directions (0→1 and 1→0)?
    # If yes, the function is no longer monotone, and monotone
    # lower bounds don't apply. But the NOT gates needed for g
    # are "consumed", leaving fewer for f.

    print(f"\n{'='*80}")
    print("  ANALYSIS: NOT Gate Budget")
    print(f"{'='*80}")

    print("""
    For F = f ∘ g with g = XOR (needs NOT gates):
    - Computing g on each block needs at least 1 NOT gate per block
    - Total NOT gates for g: at least n (one per block)
    - NOT gates available for f: s_total - n

    If circuit has s gates total with s_not NOT gates:
    - s_not ≥ n (for XOR inner function)
    - Remaining NOT for f: s_not - n

    From T4: if remaining NOT < 0.844n, then circuit size ≥ exp(Ω(n))
    So: if s_not < 0.844n + n = 1.844n, circuit size ≥ exp(Ω(n))

    BUT: this gives a lower bound on circuits with < 1.844n NOT gates,
    not on ALL circuits. A poly-size circuit can have poly NOT gates
    which is >> 1.844n for large n.

    CONCLUSION: Composition shifts the NOT budget by +n,
    but doesn't qualitatively change the barrier.
    The barrier is NOT the count of NOT gates, but the ability
    of NOT gates to create bidirectional information flow.
    """)


def random_restriction_analysis(n, clauses, p=0.5):
    """Apply random restrictions and analyze boundary preservation.

    A restriction ρ fixes some variables to 0 or 1, leaving others free.
    The restricted function f|_ρ has fewer variables.

    If the boundary is "robust" — preserved under restrictions —
    then we can iterate and compound lower bounds.

    For MONO-3SAT: fixing x_i=1 can only help (satisfies clauses).
    Fixing x_i=0 can only hurt (breaks clauses).

    Strategy: fix each variable to 1 with probability p, leave free with 1-p.
    This PRESERVES the monotone structure while reducing n.
    """
    solutions = set()
    for bits in range(2**n):
        x = tuple((bits >> i) & 1 for i in range(n))
        if evaluate_mono3sat(x, clauses):
            solutions.add(x)

    # Original boundary
    orig_boundary = 0
    for bits in range(2**n):
        x = tuple((bits >> i) & 1 for i in range(n))
        if x not in solutions:
            for j in range(n):
                if x[j] == 0:
                    fl = list(x); fl[j] = 1
                    if tuple(fl) in solutions:
                        orig_boundary += 1
                        break

    print(f"\n{'='*70}")
    print(f"  RANDOM RESTRICTION ANALYSIS (n={n}, p={p})")
    print(f"  Original |∂f| = {orig_boundary}")
    print(f"{'='*70}")

    # Apply many random restrictions and measure boundary
    results = []
    num_trials = 200

    for _ in range(num_trials):
        # Choose which variables to fix
        fixed = {}
        free_vars = []
        for i in range(n):
            if random.random() < p:
                fixed[i] = 1  # fix to 1 (helps monotone)
            else:
                free_vars.append(i)

        k = len(free_vars)
        if k == 0:
            continue

        # Compute restricted function
        restricted_clauses = []
        for clause in clauses:
            # Check if clause is already satisfied by fixed vars
            satisfied = False
            remaining_vars = []
            for v in clause:
                if v in fixed:
                    if fixed[v] == 1:
                        satisfied = True
                        break
                else:
                    remaining_vars.append(free_vars.index(v))

            if not satisfied and remaining_vars:
                restricted_clauses.append(tuple(remaining_vars))

        if not restricted_clauses:
            continue

        # Compute boundary of restricted function
        restricted_boundary = 0
        restricted_solutions = 0
        for bits in range(2**k):
            x = tuple((bits >> i) & 1 for i in range(k))
            if evaluate_mono3sat(x, restricted_clauses):
                restricted_solutions += 1
            else:
                for j in range(k):
                    if x[j] == 0:
                        fl = list(x); fl[j] = 1
                        if evaluate_mono3sat(tuple(fl), restricted_clauses):
                            restricted_boundary += 1
                            break

        if restricted_boundary > 0:
            results.append({
                'k': k,
                'boundary': restricted_boundary,
                'solutions': restricted_solutions,
                'clauses': len(restricted_clauses),
            })

    if not results:
        return

    # Analyze boundary preservation
    print(f"\n  Restriction results ({len(results)} valid trials):")

    by_k = defaultdict(list)
    for r in results:
        by_k[r['k']].append(r['boundary'])

    print(f"\n  {'k (free vars)':>15} {'avg |∂f_ρ|':>12} {'max |∂f_ρ|':>12} "
          f"{'base':>8} {'preservation':>14}")

    for k in sorted(by_k.keys()):
        boundaries = by_k[k]
        avg = sum(boundaries) / len(boundaries)
        mx = max(boundaries)
        base = mx ** (1.0/k) if mx > 1 and k > 0 else 0
        preservation = mx / orig_boundary if orig_boundary > 0 else 0

        print(f"  {k:15d} {avg:12.1f} {mx:12d} {base:8.4f} {preservation:14.4f}")

    # Key question: does the boundary base stay above threshold?
    # If base stays > 1.795 even after restriction, we can iterate
    print(f"\n  If boundary base stays > 1.795 after restriction,")
    print(f"  we can iterate and compound lower bounds.")


if __name__ == "__main__":
    random.seed(42)

    # Phase 1: Composition analysis
    analyze_composition()

    # Phase 2: Random restrictions
    print(f"\n\n{'='*80}")
    print("  PHASE 2: RANDOM RESTRICTIONS")
    print(f"{'='*80}")

    from mono3sat import generate_all_mono3sat_clauses

    for n in [8, 10, 12]:
        if 2**n > 100000:
            break

        all_clauses = generate_all_mono3sat_clauses(n)
        best_clauses = None
        best_boundary = 0

        for _ in range(100):
            k = random.randint(max(1, n//2), min(len(all_clauses), 4*n))
            clauses = random.sample(all_clauses, k)
            sols = sum(1 for bits in range(2**n)
                      if evaluate_mono3sat(tuple((bits>>i)&1 for i in range(n)), clauses))
            if 0 < sols < 2**n:
                trans = 0
                for bits in range(2**n):
                    x = tuple((bits>>i)&1 for i in range(n))
                    if not evaluate_mono3sat(x, clauses):
                        for j in range(n):
                            if x[j] == 0:
                                fl = list(x); fl[j] = 1
                                if evaluate_mono3sat(tuple(fl), clauses):
                                    trans += 1
                                    break
                if trans > best_boundary:
                    best_boundary = trans
                    best_clauses = clauses[:]

        if best_clauses:
            for p in [0.3, 0.5]:
                random_restriction_analysis(n, best_clauses, p)
