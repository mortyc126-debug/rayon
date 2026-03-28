"""
BATCH 2 IDEAS: Quick checks.

IDEA 13: Tensor rank.
IDEA 14: Derivative complexity.
IDEA 15: Noise sensitivity.
"""

import random
import math
import itertools


def compute_noise_sensitivity(n, tt, epsilon, num_trials=5000):
    """NS_ε(f) = Pr[f(x) ≠ f(x⊕noise)] where noise flips each bit with prob ε."""
    disagree = 0
    for _ in range(num_trials):
        x = random.randint(0, 2**n - 1)
        # Add noise
        noise = 0
        for j in range(n):
            if random.random() < epsilon:
                noise |= (1 << j)
        y = x ^ noise
        if tt[x] != tt[y]:
            disagree += 1
    return disagree / num_trials


def compute_total_influence(n, tt):
    """I(f) = Σ_j Pr[f(x) ≠ f(x⊕eⱼ)] = sum of influences."""
    total = 0
    for j in range(n):
        inf_j = 0
        for x in range(2**n):
            y = x ^ (1 << j)
            if tt[x] != tt[y]:
                inf_j += 1
        total += inf_j / (2**n)
    return total


def compute_derivative_complexities(n, tt):
    """For each j: compute truth table of D_j f = f(x) ⊕ f(x⊕eⱼ).
    Count the weight (number of 1s) of each derivative."""
    derivatives = []
    for j in range(n):
        weight = 0
        for x in range(2**n):
            y = x ^ (1 << j)
            if tt[x] != tt[y]:
                weight += 1
        derivatives.append(weight)
    return derivatives


def main():
    random.seed(42)
    print("=" * 60)
    print("  IDEAS 13-15: Tensor rank, Derivatives, Noise Sensitivity")
    print("=" * 60)

    # Build truth tables for various functions
    functions = {}

    for n in [6, 8, 10, 12]:
        if 2**n > 100000:
            break

        # OR
        functions[f'OR-{n}'] = (n, {b: 0 if b == 0 else 1 for b in range(2**n)})

        # MAJ
        functions[f'MAJ-{n}'] = (n, {b: 1 if bin(b).count('1') > n/2 else 0
                                      for b in range(2**n)})

        # Triangle (for n=6,10)
        if n == 6:
            N = 4
        elif n == 10:
            N = 5
        else:
            continue

        nn = N*(N-1)//2
        if nn != n:
            continue

        eidx = {}; idx = 0
        for i in range(N):
            for j in range(i+1, N):
                eidx[(i,j)] = idx; eidx[(j,i)] = idx; idx += 1

        tt_tri = {}
        for b in range(2**nn):
            x = tuple((b>>j)&1 for j in range(nn))
            has = any(x[eidx[(i,j)]] and x[eidx[(i,k)]] and x[eidx[(j,k)]]
                      for i in range(N) for j in range(i+1,N) for k in range(j+1,N))
            tt_tri[b] = 1 if has else 0
        functions[f'TRI-K{N}'] = (nn, tt_tri)

    print(f"\n  NOISE SENSITIVITY (ε = 0.1):")
    print(f"  {'Function':<15} {'n':>4} {'NS':>8} {'I(f)':>8} {'I/n':>8}")
    print("  " + "-" * 45)

    for name in sorted(functions.keys()):
        n, tt = functions[name]
        ns = compute_noise_sensitivity(n, tt, 0.1, 3000)
        inf = compute_total_influence(n, tt)
        print(f"  {name:<15} {n:>4} {ns:>8.4f} {inf:>8.2f} {inf/n:>8.3f}")

    print(f"\n  DERIVATIVE WEIGHTS:")
    print(f"  {'Function':<15} {'n':>4} {'max D_j':>8} {'avg D_j':>8} {'Σ D_j':>8}")
    print("  " + "-" * 45)

    for name in sorted(functions.keys()):
        n, tt = functions[name]
        derivs = compute_derivative_complexities(n, tt)
        max_d = max(derivs)
        avg_d = sum(derivs) / len(derivs)
        sum_d = sum(derivs)
        print(f"  {name:<15} {n:>4} {max_d:>8} {avg_d:>8.1f} {sum_d:>8}")

    print(f"\n  ANALYSIS:")
    print(f"  Noise sensitivity NS ∝ I(f) × ε (for small ε).")
    print(f"  I(f) = total influence. For CLIQUE: I ∝ n (linear).")
    print(f"  Circuit bound from NS: circuit ≥ NS/max_NS_per_gate.")
    print(f"  max_NS_per_gate = O(ε) → circuit ≥ I(f)/O(1) = O(n). Trivial.")
    print()
    print(f"  Derivative D_j f: has weight |D_j|. Sum = 2×total_influence×2^n.")
    print(f"  circuit(D_j f) ≤ 2×circuit(f). Known. Not new.")
    print()
    print(f"  TENSOR RANK: f as tensor in (C²)^⊗n.")
    print(f"  rank = minimum decomposition as sum of product states.")
    print(f"  For AND: rank = 1. For OR: rank = 2^n - 1.")
    print(f"  For CLIQUE: rank = ??? (likely 2^Ω(n) but hard to compute).")
    print(f"  circuit ≥ log(rank). Same logarithmic barrier.")


if __name__ == "__main__":
    main()
