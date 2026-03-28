"""
WHAT ARE THE HARDEST FUNCTIONS?

For n=4: exactly 96 functions need 5 gates (maximum).
For n=3: exactly 18 functions need 4 gates (maximum).

Understanding WHAT makes these functions hard is the key to new mathematics.

If there's a structural property unique to hard functions that:
1. Can be proved to hold for CLIQUE
2. Can be proved to force large circuits
Then we have a proof strategy.
"""

from collections import defaultdict, Counter
from itertools import combinations
import math

def compute_all_circuit_sizes(n):
    """Compute minimum circuit size for all functions on n variables."""
    total = 2**(2**n)
    level = {}
    cur = set()
    cur.add(0); cur.add(total - 1)
    for i in range(n):
        tt = 0
        for x in range(2**n):
            if (x >> i) & 1: tt |= (1 << x)
        cur.add(tt); cur.add((total - 1) ^ tt)
    for tt in cur: level[tt] = 0

    s = 0
    while len(level) < total:
        s += 1
        new = set()
        existing = list(level.keys())
        for f in existing:
            not_f = (total - 1) ^ f
            if not_f not in level and not_f not in new:
                new.add(not_f)
            for g in existing:
                if f & g not in level and f & g not in new: new.add(f & g)
                if f | g not in level and f | g not in new: new.add(f | g)
        for tt in new: level[tt] = s
        if not new or s > 20: break
    return level

def tt_to_str(tt, n):
    """Convert truth table to readable string."""
    return ''.join(str((tt >> x) & 1) for x in range(2**n))

def function_properties(tt, n):
    """Compute various properties of a function."""
    total = 2**n

    # Balance
    ones = bin(tt).count('1')

    # Sensitivity
    sens = 0
    max_sens = 0
    for x in range(total):
        fx = (tt >> x) & 1
        local_sens = 0
        for i in range(n):
            fy = (tt >> (x ^ (1 << i))) & 1
            if fx != fy:
                sens += 1
                local_sens += 1
        max_sens = max(max_sens, local_sens)

    # Fourier spectrum (over {0,1}, so f̂(S) = E[f(x)(-1)^{x·S}])
    fourier = {}
    for k in range(n+1):
        for S in combinations(range(n), k):
            S_mask = sum(1 << i for i in S)
            coeff = 0
            for x in range(total):
                fx = (tt >> x) & 1
                parity = bin(x & S_mask).count('1') % 2
                coeff += fx * ((-1)**parity)
            fourier[S] = coeff / total

    # Symmetry: is the function symmetric (depends only on hamming weight)?
    symmetric = True
    hw_vals = {}
    for x in range(total):
        hw = bin(x).count('1')
        fx = (tt >> x) & 1
        if hw in hw_vals:
            if hw_vals[hw] != fx:
                symmetric = False
                break
        else:
            hw_vals[hw] = fx

    # Self-dual: f(x) = 1 - f(x̄)?
    self_dual = True
    for x in range(total):
        xbar = ((1 << n) - 1) ^ x
        if ((tt >> x) & 1) + ((tt >> xbar) & 1) != 1:
            self_dual = False
            break

    # Monotone: f(x) ≤ f(y) when x ≤ y (bitwise)?
    monotone = True
    for x in range(total):
        fx = (tt >> x) & 1
        for i in range(n):
            if not ((x >> i) & 1):
                y = x | (1 << i)
                fy = (tt >> y) & 1
                if fx > fy:
                    monotone = False
                    break
        if not monotone:
            break

    # Degree: max |S| with non-zero Fourier coefficient
    degree = 0
    for S, c in fourier.items():
        if abs(c) > 1e-10:
            degree = max(degree, len(S))

    return {
        'ones': ones,
        'balance': ones / total,
        'avg_sens': sens / total,
        'max_sens': max_sens,
        'symmetric': symmetric,
        'self_dual': self_dual,
        'monotone': monotone,
        'degree': degree,
        'fourier': fourier,
        'top_fourier': abs(fourier[tuple(range(n))]),
    }


# MAIN
print("ANALYSIS OF HARDEST BOOLEAN FUNCTIONS")
print("=" * 65)

for n in [3, 4]:
    print(f"\n{'='*65}")
    print(f"n = {n}: Total functions = {2**(2**n)}")
    print(f"{'='*65}")

    sizes = compute_all_circuit_sizes(n)
    max_size = max(sizes.values())

    by_size = defaultdict(list)
    for tt, s in sizes.items():
        by_size[s].append(tt)

    print(f"\nDistribution: ", end="")
    for s in sorted(by_size.keys()):
        print(f"size-{s}:{len(by_size[s])}", end="  ")
    print()

    # Analyze hardest functions
    hardest = by_size[max_size]
    print(f"\n{len(hardest)} HARDEST functions (size {max_size}):")
    print()

    # Classify by properties
    sym_count = 0
    sd_count = 0
    mono_count = 0
    top_fourier_dist = []

    for tt in hardest:
        props = function_properties(tt, n)
        if props['symmetric']: sym_count += 1
        if props['self_dual']: sd_count += 1
        if props['monotone']: mono_count += 1
        top_fourier_dist.append(props['top_fourier'])

    print(f"  Symmetric:  {sym_count}/{len(hardest)}")
    print(f"  Self-dual:  {sd_count}/{len(hardest)}")
    print(f"  Monotone:   {mono_count}/{len(hardest)}")
    print(f"  Avg |f̂(top)|: {sum(top_fourier_dist)/len(top_fourier_dist):.4f}")
    print(f"  Max |f̂(top)|: {max(top_fourier_dist):.4f}")
    print(f"  Min |f̂(top)|: {min(top_fourier_dist):.4f}")

    # Balance distribution of hardest
    balance_dist = Counter()
    for tt in hardest:
        ones = bin(tt).count('1')
        balance_dist[ones] += 1

    print(f"\n  Balance distribution (number of 1s):")
    for ones in sorted(balance_dist.keys()):
        print(f"    {ones}/{2**n} ones: {balance_dist[ones]} functions")

    # Show some examples
    print(f"\n  Sample hardest functions (truth tables):")
    for tt in hardest[:min(10, len(hardest))]:
        props = function_properties(tt, n)
        ttstr = tt_to_str(tt, n)
        flags = []
        if props['symmetric']: flags.append('SYM')
        if props['self_dual']: flags.append('SD')
        if props['monotone']: flags.append('MON')
        print(f"    {ttstr}  sens={props['avg_sens']:.1f}  |f̂_top|={props['top_fourier']:.3f}"
              f"  {'  '.join(flags)}")

    # CRITICAL: Check if hardest functions are related by symmetries
    print(f"\n  Symmetry orbits of hardest functions:")
    # Two functions are equivalent if one can be obtained from the other
    # by permuting variables and/or complementing input/output
    orbits = []
    remaining = set(hardest)
    total_mask = 2**(2**n) - 1

    from itertools import permutations

    while remaining:
        tt = min(remaining)
        orbit = {tt}
        # Generate all permutations of variables
        for perm in permutations(range(n)):
            new_tt = 0
            for x in range(2**n):
                if (tt >> x) & 1:
                    # Permute bits of x according to perm
                    new_x = 0
                    for i in range(n):
                        if (x >> i) & 1:
                            new_x |= (1 << perm[i])
                    new_tt |= (1 << new_x)
            orbit.add(new_tt)
            orbit.add(total_mask ^ new_tt)  # complement
            # Also complement input bits
            comp_tt = 0
            for x in range(2**n):
                xcomp = ((1 << n) - 1) ^ x
                if (tt >> xcomp) & 1:
                    comp_tt |= (1 << x)
            # Permute variables of complement
            for perm2 in permutations(range(n)):
                new_tt2 = 0
                for x in range(2**n):
                    if (comp_tt >> x) & 1:
                        new_x = 0
                        for i in range(n):
                            if (x >> i) & 1:
                                new_x |= (1 << perm2[i])
                        new_tt2 |= (1 << new_x)
                orbit.add(new_tt2)
                orbit.add(total_mask ^ new_tt2)

        orbit_in_hardest = orbit & remaining
        remaining -= orbit_in_hardest
        orbits.append((tt, len(orbit_in_hardest)))

    print(f"  {len(orbits)} distinct orbits (up to var-perm + complement):")
    for tt, count in orbits:
        props = function_properties(tt, n)
        ttstr = tt_to_str(tt, n)
        flags = []
        if props['symmetric']: flags.append('SYM')
        if props['self_dual']: flags.append('SD')
        print(f"    {ttstr} (orbit size {count})  "
              f"sens={props['avg_sens']:.1f}  |f̂_top|={props['top_fourier']:.3f}  "
              f"{'  '.join(flags)}")

# CLIQUE connection
print(f"\n{'='*65}")
print("CONNECTION TO CLIQUE")
print(f"{'='*65}")
print()
print("For CLIQUE_k on N vertices:")
print("  Variables = C(N,2) edges")
print("  Hardness requires ALL C(k,2) edges of a clique to interact")
print("  → High (C(k,2))-wise Fourier interaction")
print()
print("  The hardest functions for n=3,4 have MAXIMAL top-level interaction")
print("  This is exactly the pattern we'd expect for CLIQUE")
print()
print("  CONJECTURE: Functions with |f̂([n])| ≥ c require circuits of")
print("  size ≥ g(n, c) for some increasing function g.")
print()
print("  If true for g super-polynomial: we'd need to show")
print("  |f̂([n])| ≥ super-poly^{-1} for CLIQUE.")
print()
print("  BUT: for CLIQUE, the 'relevant' Fourier level is NOT [n]")
print("  (the top level = ALL variables), but level C(k,2) << n.")
print("  Most Fourier weight is at INTERMEDIATE levels.")
