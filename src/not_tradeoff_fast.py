"""
Fast NOT-gate vs Circuit Size Tradeoff using bottom-up enumeration.

Instead of DFS over circuit structures, enumerate all functions
reachable with s gates (bottom-up). Much faster for finding
minimum circuit sizes.
"""

import sys
import time
import math


def min_circuit_size(n, target_tt, max_size, max_nots):
    """Find minimum circuit size using bottom-up function enumeration.

    reachable[s] = set of (truth_table, not_count) reachable with s gates.

    This is exponential in the number of reachable functions, but for
    small n (3-4), the total number of functions is 2^{2^n} = 256 or 65536.
    """
    num_inputs = 2**n
    all_ones = (1 << num_inputs) - 1

    # Input truth tables
    inputs = []
    for j in range(n):
        tt = 0
        for i in range(num_inputs):
            if (i >> j) & 1:
                tt |= (1 << i)
        inputs.append(tt)

    # Constants
    const0 = 0
    const1 = all_ones

    # reachable: tt -> min (size, nots) to compute it
    # Store as dict: tt -> list of (size, nots)
    # We want Pareto-optimal (size, nots) pairs
    best = {}  # tt -> {nots: min_size}

    def update_best(tt, size, nots):
        if tt not in best:
            best[tt] = {}
        if nots not in best[tt] or best[tt][nots] > size:
            best[tt][nots] = size
            return True
        return False

    # Initialize with inputs (size 0, 0 NOTs)
    for tt in inputs:
        update_best(tt, 0, 0)
    update_best(const0, 0, 0)
    update_best(const1, 0, 0)

    # Check if target is already an input
    for nots in range(max_nots + 1):
        if target_tt in best and nots in best[target_tt]:
            return best[target_tt][nots]

    # Iteratively add gates
    for size in range(1, max_size + 1):
        # Collect all (tt, nots) reachable with < size gates
        current_fns = []
        for tt, nots_dict in best.items():
            for nots, s in nots_dict.items():
                if s < size:
                    current_fns.append((tt, nots, s))

        new_found = False

        # Try all pairs for AND/OR
        for i in range(len(current_fns)):
            tt1, n1, s1 = current_fns[i]
            for j in range(i, len(current_fns)):
                tt2, n2, s2 = current_fns[j]

                # The new gate uses both tt1 and tt2
                # Total size = max(s1, s2) + 1? No, that's wrong.
                # We need both sub-circuits plus the new gate.
                # In a circuit with fan-out, gates can be shared.
                # Minimum size = s1 + s2 + 1 is an UPPER BOUND
                # (no sharing). Could be less with sharing.

                # Actually, for minimum circuit size finding,
                # we use the bottom-up approach differently:
                # At step s, we have all functions computable with ≤ s-1 gates.
                # A new gate at step s combines two previously computed functions.
                # The total NOT count = sum of NOTs in both sub-circuits + gate NOT.

                # But this is tricky because sub-circuits can share gates.
                # For EXACT minimum circuit size, this approach gives UPPER BOUNDS.

                # For a correct approach, we need to track which gates are shared.
                # This is only feasible for very small circuits.

                # SIMPLIFICATION: We compute FORMULA complexity (no sharing).
                # This gives an UPPER BOUND on minimum circuit size.
                # But it's still useful for comparing with/without NOT gates.

                combined_size = s1 + s2 + 1
                combined_nots = n1 + n2

                if combined_size > max_size:
                    continue
                if combined_nots > max_nots:
                    continue

                # AND
                tt_and = tt1 & tt2
                update_best(tt_and, combined_size, combined_nots)

                # OR
                tt_or = tt1 | tt2
                update_best(tt_or, combined_size, combined_nots)

        # Try NOT gates
        for tt1, n1, s1 in current_fns:
            combined_size = s1 + 1
            combined_nots = n1 + 1

            if combined_size > max_size or combined_nots > max_nots:
                continue

            tt_not = all_ones ^ tt1
            update_best(tt_not, combined_size, combined_nots)

        # Check if target reached
        if target_tt in best:
            for nots in range(max_nots + 1):
                if nots in best[target_tt] and best[target_tt][nots] <= size:
                    # Found! But this is formula complexity (upper bound)
                    pass

    if target_tt in best:
        result = {}
        for nots, s in best[target_tt].items():
            result[nots] = s
        return result

    return None


def compute_formula_complexity(n, target_tt, max_depth=12):
    """Compute formula complexity (no fan-out) with different NOT limits.

    Uses dynamic programming on depth.

    dp[d] = set of (tt, nots) achievable with depth ≤ d formulas.
    """
    num_inputs = 2**n
    all_ones = (1 << num_inputs) - 1

    # Input truth tables
    inputs = set()
    for j in range(n):
        tt = 0
        for i in range(num_inputs):
            if (i >> j) & 1:
                tt |= (1 << i)
        inputs.add(tt)
    inputs.add(0)
    inputs.add(all_ones)

    # dp[tt] = {nots: min_depth}
    best = {}

    def update(tt, depth, nots):
        if tt not in best:
            best[tt] = {}
        if nots not in best[tt] or best[tt][nots] > depth:
            best[tt][nots] = depth
            return True
        return False

    # Base: inputs at depth 0
    for tt in inputs:
        update(tt, 0, 0)

    for depth in range(1, max_depth + 1):
        # All functions at depth < current_depth
        prev_fns = [(tt, nots, d) for tt in best for nots, d in best[tt].items()
                     if d < depth]

        changed = False

        # Combine pairs
        for i, (tt1, n1, d1) in enumerate(prev_fns):
            for j, (tt2, n2, d2) in enumerate(prev_fns):
                new_depth = max(d1, d2) + 1
                if new_depth > depth:
                    continue
                new_nots = n1 + n2

                # AND
                if update(tt1 & tt2, new_depth, new_nots):
                    changed = True
                # OR
                if update(tt1 | tt2, new_depth, new_nots):
                    changed = True

            # NOT
            new_depth_not = d1 + 1
            if new_depth_not <= depth:
                if update(all_ones ^ tt1, new_depth_not, n1 + 1):
                    changed = True

        # Check target
        if target_tt in best:
            min_depth_any = min(best[target_tt].values())
            if min_depth_any <= depth:
                pass  # found at this depth

        if not changed:
            break

    if target_tt in best:
        return best[target_tt]
    return None


def main():
    print("=" * 80)
    print("  FORMULA COMPLEXITY vs NOT-GATE COUNT")
    print("  (Formula = circuit with fan-out 1, i.e., tree circuit)")
    print("=" * 80)

    # n=3: 8 inputs, 256 possible functions
    n = 3
    num_inputs = 2**n
    all_ones = (1 << num_inputs) - 1

    # Define test functions
    test_fns = {}

    # MONO-3SAT: OR(x0,x1,x2)
    tt = 0
    for i in range(8):
        x = ((i>>0)&1, (i>>1)&1, (i>>2)&1)
        if x[0] or x[1] or x[2]:
            tt |= (1 << i)
    test_fns['OR3'] = tt

    # AND
    tt = 0
    for i in range(8):
        x = ((i>>0)&1, (i>>1)&1, (i>>2)&1)
        if x[0] and x[1] and x[2]:
            tt |= (1 << i)
    test_fns['AND3'] = tt

    # MAJ
    tt = 0
    for i in range(8):
        x = ((i>>0)&1, (i>>1)&1, (i>>2)&1)
        if sum(x) >= 2:
            tt |= (1 << i)
    test_fns['MAJ3'] = tt

    # XOR
    tt = 0
    for i in range(8):
        x = ((i>>0)&1, (i>>1)&1, (i>>2)&1)
        if x[0] ^ x[1] ^ x[2]:
            tt |= (1 << i)
    test_fns['XOR3'] = tt

    # MUX: x0 ? x1 : x2
    tt = 0
    for i in range(8):
        x = ((i>>0)&1, (i>>1)&1, (i>>2)&1)
        if (x[0] and x[1]) or (not x[0] and x[2]):
            tt |= (1 << i)
    test_fns['MUX'] = tt

    # NAND
    test_fns['NAND3'] = all_ones ^ test_fns['AND3']

    # (x0 AND NOT x1) OR x2
    tt = 0
    for i in range(8):
        x = ((i>>0)&1, (i>>1)&1, (i>>2)&1)
        if (x[0] and not x[1]) or x[2]:
            tt |= (1 << i)
    test_fns['x0∧¬x1∨x2'] = tt

    # MONO-3SAT with 2 clauses
    tt = 0
    for i in range(8):
        x = ((i>>0)&1, (i>>1)&1, (i>>2)&1)
        if (x[0] or x[1] or x[2]) and (x[0] or x[1]):
            tt |= (1 << i)
    test_fns['2-clause'] = tt

    print(f"\nn={n}: Formula depth with ≤ k NOT gates")
    print(f"{'Function':<15}", end="")
    for k in range(6):
        print(f" k={k:>2}", end="")
    print(f" {'mono?':>6} {'ratio':>7}")
    print("-" * 65)

    for name, target_tt in sorted(test_fns.items()):
        result = compute_formula_complexity(n, target_tt, max_depth=15)

        # Check monotonicity
        is_mono = True
        for i in range(num_inputs):
            if (target_tt >> i) & 1:
                for j in range(n):
                    if (i >> j) & 1:
                        smaller = i & ~(1 << j)
                        if not ((target_tt >> smaller) & 1):
                            is_mono = False

        print(f"{name:<15}", end="")

        depths = {}
        if result:
            for k in range(6):
                # Find min depth with ≤ k NOTs
                min_d = float('inf')
                for nots, d in result.items():
                    if nots <= k:
                        min_d = min(min_d, d)
                if min_d < float('inf'):
                    depths[k] = min_d
                    print(f" {min_d:>4}", end="")
                else:
                    print(f"   >15", end="")
        else:
            for k in range(6):
                print(f"    ?", end="")

        mono_str = "Y" if is_mono else "N"
        print(f" {mono_str:>6}", end="")

        if depths.get(0) and depths.get(5):
            ratio = depths[0] / depths[5]
            print(f" {ratio:>7.2f}", end="")
        print()

    # n=4 analysis
    n = 4
    num_inputs = 2**n
    all_ones = (1 << num_inputs) - 1

    test_fns_4 = {}

    # MAJ4
    tt = 0
    for i in range(16):
        x = tuple((i>>j)&1 for j in range(4))
        if sum(x) >= 2:
            tt |= (1 << i)
    test_fns_4['MAJ4'] = tt

    # XOR4
    tt = 0
    for i in range(16):
        x = tuple((i>>j)&1 for j in range(4))
        if x[0]^x[1]^x[2]^x[3]:
            tt |= (1 << i)
    test_fns_4['XOR4'] = tt

    # MONO-3SAT on 4 vars with 3 clauses
    tt = 0
    clauses = [(0,1,2), (1,2,3), (0,2,3)]
    for i in range(16):
        x = tuple((i>>j)&1 for j in range(4))
        ok = True
        for c in clauses:
            if not any(x[v] for v in c):
                ok = False
                break
        if ok:
            tt |= (1 << i)
    test_fns_4['MONO3SAT-4'] = tt

    # (x0∧x1) ∨ (x2∧x3) — AND-OR
    tt = 0
    for i in range(16):
        x = tuple((i>>j)&1 for j in range(4))
        if (x[0]&x[1]) | (x[2]&x[3]):
            tt |= (1 << i)
    test_fns_4['AND-OR-4'] = tt

    # MUX4: (x0∧x2) ∨ (¬x0∧x3) — uses NOT
    tt = 0
    for i in range(16):
        x = tuple((i>>j)&1 for j in range(4))
        if (x[0] and x[2]) or (not x[0] and x[3]):
            tt |= (1 << i)
    test_fns_4['MUX4'] = tt

    # Sort function: output 1 if x has ≥ 3 ones
    tt = 0
    for i in range(16):
        x = tuple((i>>j)&1 for j in range(4))
        if sum(x) >= 3:
            tt |= (1 << i)
    test_fns_4['TH3-4'] = tt

    print(f"\n{'='*80}")
    print(f"n={n}: Formula depth with ≤ k NOT gates")
    print(f"{'Function':<15}", end="")
    for k in range(6):
        print(f" k={k:>2}", end="")
    print(f" {'mono?':>6} {'ratio':>7}")
    print("-" * 65)

    for name, target_tt in sorted(test_fns_4.items()):
        t0 = time.time()
        result = compute_formula_complexity(n, target_tt, max_depth=12)
        dt = time.time() - t0

        is_mono = True
        for i in range(num_inputs):
            if (target_tt >> i) & 1:
                for j in range(n):
                    if (i >> j) & 1:
                        smaller = i & ~(1 << j)
                        if not ((target_tt >> smaller) & 1):
                            is_mono = False

        print(f"{name:<15}", end="")

        depths = {}
        if result:
            for k in range(6):
                min_d = float('inf')
                for nots, d in result.items():
                    if nots <= k:
                        min_d = min(min_d, d)
                if min_d < float('inf'):
                    depths[k] = min_d
                    print(f" {min_d:>4}", end="")
                else:
                    print(f"  >12", end="")
        else:
            for k in range(6):
                print(f"    ?", end="")

        mono_str = "Y" if is_mono else "N"
        print(f" {mono_str:>6}", end="")

        if depths.get(0) and depths.get(5):
            ratio = depths[0] / depths[5]
            print(f" {ratio:>7.2f}", end="")
        print(f"  [{dt:.1f}s]")

    print(f"\n{'='*80}")
    print("  KEY OBSERVATION")
    print(f"{'='*80}")
    print("""
    For MONOTONE functions (MAJ, AND-OR, MONO-3SAT, TH):
      I(f, 0) = I(f, k) for all k. NOT gates DON'T HELP.
      Ratio = 1.00. This is expected.

    For NON-MONOTONE functions (XOR, MUX, NAND):
      I(f, 0) > I(f, k) for k ≥ 1. NOT gates HELP.
      The ratio I(f,0)/I(f,∞) measures the "NOT benefit".

    For P vs NP:
      We need an NP-HARD function where NOT gates DON'T help much.
      But NP-hard monotone functions (CLIQUE) have:
        Monotone complexity: exp (Razborov)
        General complexity: unknown (poly if P=NP)
      So the question IS whether NOT gates help for CLIQUE.

    The Markov+T4 reduction says:
      If f has large |∂f| AND can be computed with O(log n) NOT gates
      AND small size → contradiction with T4.

      The key: does reducing to O(log n) NOT gates preserve small size?
    """)


if __name__ == "__main__":
    main()
