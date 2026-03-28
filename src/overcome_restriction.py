"""
OVERCOMING THE RESTRICTION BARRIER FOR CLIQUE.

The restriction barrier: random half-restriction makes CLIQUE trivially 0 (large k)
or poly-DNF (constant k). Four approaches to overcome this.

APPROACH 1: PARTIAL RESTRICTION THRESHOLD
  Instead of fixing n/2, fix fewer. Find p* where CLIQUE transitions hard→easy.
  If cascade achieves less than p*: the residual formula argument might work.

APPROACH 2: ADVERSARIAL vs RANDOM RESTRICTION
  Cascade doesn't fix randomly — it fixes based on DFS path.
  Adversarial restriction might preserve hardness better.

APPROACH 3: DIFFERENT NP-HARD FUNCTIONS
  Maybe CLIQUE is uniquely brittle. Test other functions.

APPROACH 4: USE THE HOLOGRAPHIC LP INSTEAD
  Don't argue about the residual function's hardness.
  Instead use global LP consistency (which we proved tight for n=3).
"""

import random
import math
from itertools import combinations
from collections import defaultdict

# ================================================================
# CLIQUE truth table builder
# ================================================================
def clique_truth_table(N, k):
    """Build truth table for k-CLIQUE on N vertices."""
    n = N * (N - 1) // 2
    edge_idx = {}
    idx = 0
    for u in range(N):
        for v in range(u + 1, N):
            edge_idx[(u, v)] = idx
            idx += 1

    tt = 0
    for x in range(2**n):
        edges = set()
        for (u, v), i in edge_idx.items():
            if (x >> i) & 1:
                edges.add((u, v))
        has_clique = False
        for subset in combinations(range(N), k):
            if all((min(a, b), max(a, b)) in edges
                   for a in subset for b in subset if a != b):
                has_clique = True
                break
        if has_clique:
            tt |= (1 << x)
    return tt, n, edge_idx


def apply_restriction(tt, n, fixed_vars):
    """Apply restriction: fix some variables, return restricted truth table on free vars."""
    free = [i for i in range(n) if i not in fixed_vars]
    n_free = len(free)
    new_tt = 0
    for x_free in range(2**n_free):
        # Build full assignment
        x = 0
        for j, var in enumerate(free):
            if (x_free >> j) & 1:
                x |= (1 << var)
        for var, val in fixed_vars.items():
            if val:
                x |= (1 << var)
        if (tt >> x) & 1:
            new_tt |= (1 << x_free)
    return new_tt, n_free


def count_ones(tt, n):
    return bin(tt & ((1 << (2**n)) - 1)).count('1')


def sensitivity(tt, n):
    """Average sensitivity."""
    total = 2**n
    sens = 0
    for x in range(total):
        for i in range(n):
            if ((tt >> x) & 1) != ((tt >> (x ^ (1 << i))) & 1):
                sens += 1
    return sens / total


def top_fourier(tt, n):
    """Absolute value of top Fourier coefficient."""
    total = 2**n
    S_mask = (1 << n) - 1
    coeff = 0
    for x in range(total):
        fx = (tt >> x) & 1
        parity = bin(x & S_mask).count('1') % 2
        coeff += fx * ((-1) ** parity)
    return abs(coeff) / total


# ================================================================
# APPROACH 1: Partial Restriction Threshold
# ================================================================
def partial_restriction_threshold():
    print("APPROACH 1: Partial Restriction Threshold")
    print("=" * 60)
    print()
    print("Fix fraction p of variables. Find p* where CLIQUE becomes easy.")
    print()

    for N, k in [(5, 3), (6, 3)]:
        tt, n, _ = clique_truth_table(N, k)
        if n > 20:
            continue

        print(f"  {k}-CLIQUE on N={N} ({n} variables):")
        print(f"  {'p':>6} {'avg_sens':>10} {'avg_|f̂_top|':>14} {'avg_ones%':>12} {'trivial%':>10}")
        print(f"  {'-'*55}")

        for p_frac in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
            n_fix = max(0, int(p_frac * n))
            trials = 50
            sens_sum = 0
            fourier_sum = 0
            ones_sum = 0
            trivial_count = 0

            for trial in range(trials):
                random.seed(trial * 137 + N * 31)
                vars_to_fix = random.sample(range(n), n_fix)
                fixed = {v: random.randint(0, 1) for v in vars_to_fix}
                rtt, rn = apply_restriction(tt, n, fixed)

                if rn == 0:
                    trivial_count += 1
                    continue

                ones = count_ones(rtt, rn)
                total = 2**rn
                if ones == 0 or ones == total:
                    trivial_count += 1
                    continue

                sens_sum += sensitivity(rtt, rn)
                fourier_sum += top_fourier(rtt, rn)
                ones_sum += ones / total

            non_triv = trials - trivial_count
            if non_triv > 0:
                avg_s = sens_sum / non_triv
                avg_f = fourier_sum / non_triv
                avg_o = ones_sum / non_triv
            else:
                avg_s = avg_f = avg_o = 0

            print(f"  {p_frac:>6.1f} {avg_s:>10.3f} {avg_f:>14.4f} "
                  f"{avg_o*100:>11.1f}% {trivial_count/trials*100:>9.0f}%")

        print()


# ================================================================
# APPROACH 2: Adversarial vs Random Restriction
# ================================================================
def adversarial_vs_random():
    print("APPROACH 2: Adversarial vs Random Restriction")
    print("=" * 60)
    print()

    for N, k in [(5, 3)]:
        tt, n, _ = clique_truth_table(N, k)
        n_fix = n // 2

        print(f"  {k}-CLIQUE on N={N}, fixing {n_fix}/{n} variables:")

        # Random restriction (average over trials)
        random_sens = []
        for trial in range(30):
            random.seed(trial * 97)
            vars_to_fix = random.sample(range(n), n_fix)
            fixed = {v: random.randint(0, 1) for v in vars_to_fix}
            rtt, rn = apply_restriction(tt, n, fixed)
            if rn > 0 and count_ones(rtt, rn) not in [0, 2**rn]:
                random_sens.append(sensitivity(rtt, rn))

        # Adversarial restriction: try many, keep the HARDEST
        best_adv_sens = 0
        best_adv_fourier = 0
        for trial in range(100):
            random.seed(trial * 53 + 7)
            vars_to_fix = random.sample(range(n), n_fix)
            for val_bits in range(min(2**n_fix, 32)):
                fixed = {}
                for j, v in enumerate(vars_to_fix):
                    fixed[v] = (val_bits >> j) & 1
                rtt, rn = apply_restriction(tt, n, fixed)
                if rn > 0 and count_ones(rtt, rn) not in [0, 2**rn]:
                    s = sensitivity(rtt, rn)
                    f = top_fourier(rtt, rn)
                    if s > best_adv_sens:
                        best_adv_sens = s
                    if f > best_adv_fourier:
                        best_adv_fourier = f

        avg_rand = sum(random_sens) / len(random_sens) if random_sens else 0
        print(f"    Random avg sensitivity:       {avg_rand:.3f}")
        print(f"    Adversarial max sensitivity:  {best_adv_sens:.3f}")
        print(f"    Ratio adv/rand:               {best_adv_sens/avg_rand:.2f}x" if avg_rand > 0 else "")
        print()


# ================================================================
# APPROACH 3: Different NP Functions — Brittleness Comparison
# ================================================================
def different_functions():
    print("APPROACH 3: Brittleness Comparison Across NP Functions")
    print("=" * 60)
    print()

    n = 8

    # CLIQUE (N=5, k=3, 10 vars) — already tested above, use n=8 subset
    # PARITY
    parity_tt = 0
    for x in range(2**n):
        if bin(x).count('1') % 2 == 1:
            parity_tt |= (1 << x)

    # MAJORITY
    maj_tt = 0
    for x in range(2**n):
        if bin(x).count('1') > n // 2:
            maj_tt |= (1 << x)

    # TRIBES (AND of ORs): divide n vars into groups of 2-3, OR within, AND across
    group_size = 2
    n_groups = n // group_size
    tribes_tt = 0
    for x in range(2**n):
        all_groups = True
        for g in range(n_groups):
            any_in_group = False
            for j in range(group_size):
                idx = g * group_size + j
                if idx < n and (x >> idx) & 1:
                    any_in_group = True
            if not any_in_group:
                all_groups = False
                break
        if all_groups:
            tribes_tt |= (1 << x)

    # Random 3-SAT like function
    random.seed(42)
    sat_tt = (1 << (2**n)) - 1  # start with all 1s
    for _ in range(int(4.27 * n)):
        vars_ = random.sample(range(n), 3)
        signs = [random.choice([True, False]) for _ in range(3)]
        for x in range(2**n):
            satisfied = False
            for v, s in zip(vars_, signs):
                if s == bool((x >> v) & 1):
                    satisfied = True
                    break
            if not satisfied:
                sat_tt &= ~(1 << x)

    functions = {
        'PARITY': parity_tt,
        'MAJORITY': maj_tt,
        'TRIBES': tribes_tt,
        '3-SAT': sat_tt,
    }

    print(f"  Fixing 50% of {n} variables. Measuring sensitivity preservation.")
    print()
    print(f"  {'function':<12} {'orig_sens':>10} {'restr_sens':>12} {'ratio':>8} {'trivial%':>10}")
    print(f"  {'-'*55}")

    for name, tt in functions.items():
        orig_s = sensitivity(tt, n)
        n_fix = n // 2
        restr_sens = []
        trivial = 0
        for trial in range(50):
            random.seed(trial * 71)
            vars_to_fix = random.sample(range(n), n_fix)
            fixed = {v: random.randint(0, 1) for v in vars_to_fix}
            rtt, rn = apply_restriction(tt, n, fixed)
            ones = count_ones(rtt, rn)
            if ones == 0 or ones == 2**rn:
                trivial += 1
                continue
            restr_sens.append(sensitivity(rtt, rn))

        avg_rs = sum(restr_sens) / len(restr_sens) if restr_sens else 0
        ratio = avg_rs / orig_s if orig_s > 0 else 0
        print(f"  {name:<12} {orig_s:>10.3f} {avg_rs:>12.3f} {ratio:>8.3f} {trivial/50*100:>9.0f}%")

    print(f"""
  INTERPRETATION:
    ratio close to 1.0 → function RESISTS restriction (robust)
    ratio close to 0.0 → function COLLAPSES under restriction (brittle)
    high trivial% → function often becomes constant (very brittle)
""")


# ================================================================
# APPROACH 4: Holographic LP as Alternative
# ================================================================
def holographic_alternative():
    print("APPROACH 4: Holographic LP — Bypassing Restriction Entirely")
    print("=" * 60)
    print("""
  The restriction barrier affects the RESIDUAL FORMULA argument.
  But the HOLOGRAPHIC LP takes a completely different approach:

  Instead of:
    1. Fix some variables
    2. Argue residual is hard
    3. Conclude circuit is large

  The Holographic LP does:
    1. For ANY circuit of size s computing f
    2. Check if conditional probabilities p_g(b) are globally consistent
    3. If inconsistent: circuit can't exist → lower bound

  This NEVER restricts the function. It argues about the WHOLE circuit.

  KEY RESULT: For n=3, Sherali-Adams level-2 gives EXACT lower bounds.
  All 18 hardest functions: LP_min = actual circuit size = 4.

  SCALING QUESTION: Can this work for n >> 3?
    - For n=4: 96 hardest functions with size 5 (needs testing)
    - For CLIQUE: n = C(N,2), exponentially large truth table
    - Direct LP is infeasible for large n

  BUT: if we can find a DUAL CERTIFICATE that works for all circuit
  structures simultaneously, we might prove lower bounds without
  solving the LP explicitly.

  The dual certificate would be a set of WEIGHTS on the LP constraints
  that sum to a contradiction. These weights might have STRUCTURE
  related to the function's combinatorial properties.

  THIS IS THE MOST PROMISING PATH FORWARD.
""")


# ================================================================
# MAIN
# ================================================================
if __name__ == '__main__':
    print("OVERCOMING THE RESTRICTION BARRIER")
    print("=" * 60)
    print()

    partial_restriction_threshold()
    print()
    adversarial_vs_random()
    print()
    different_functions()
    print()
    holographic_alternative()
