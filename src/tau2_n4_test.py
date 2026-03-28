"""
tau2_n4_test.py: Test whether Sherali-Adams level-2 LP gives EXACT circuit
lower bounds for n=4.

For n=3, we proved SA-2 is exact: LP_min = actual circuit size for all 256 functions.
For n=4, there are 65536 functions, with 96 having maximum circuit size 5.

Test plan:
1. Compute actual circuit sizes for n=4 via closure-based BFS.
2. For a sample of the 96 hardest functions (size 5): test if LP is infeasible
   at size 4. If ALL sampled structures are infeasible => LP_min >= 5.
   If ANY is feasible => LP_min <= 4, meaning a gap exists.
3. Sanity check: test a few size-3 functions to verify LP says feasible at size 3.
"""

import sys
import time
import random

sys.path.insert(0, '/home/user/rayon/src')
from holographic_lp_v2 import (
    compute_sizes, truth_table_properties, build_and_check_lp
)


def sample_and_check(n, s, input_probs, input_probs2, max_tries=2000, seed=42):
    """
    Sample random circuit structures of size s for n inputs.
    Returns (any_feasible, num_tested).
    """
    rng = random.Random(seed)
    for trial in range(max_tries):
        gt_list = []
        conn_list = []
        neg_list = []
        for g in range(s):
            gt = rng.choice(['AND', 'OR'])
            avail = list(range(n + g))
            w1 = rng.choice(avail)
            w2 = rng.choice(avail)
            n1 = rng.choice([False, True])
            n2 = rng.choice([False, True])
            gt_list.append(gt)
            conn_list.append((w1, w2))
            neg_list.append((n1, n2))

        if build_and_check_lp(n, s, gt_list, conn_list, neg_list,
                              input_probs, input_probs2):
            return True, trial + 1

    return False, max_tries


def main():
    print("=" * 70)
    print("tau2 EXACTNESS TEST FOR n=4")
    print("Sherali-Adams level-2 LP circuit lower bounds")
    print("=" * 70)
    print()

    # ------------------------------------------------------------------
    # Step 1: Compute actual circuit sizes for n=4
    # ------------------------------------------------------------------
    print("Step 1: Computing actual circuit sizes for n=4 ...")
    t0 = time.time()
    sizes4 = compute_sizes(4)
    elapsed = time.time() - t0
    print(f"  Done in {elapsed:.1f}s. Total functions catalogued: {len(sizes4)}")

    from collections import Counter
    dist = Counter(sizes4.values())
    for s in sorted(dist):
        print(f"    size {s}: {dist[s]} functions")

    max_size = max(sizes4.values())
    hardest = sorted([tt for tt, sz in sizes4.items() if sz == max_size])
    print(f"\n  Hardest: {len(hardest)} functions with circuit size {max_size}")
    print()

    n = 4
    NUM_HARDEST_TO_TEST = 10
    MAX_SAMPLES = 2000

    # ------------------------------------------------------------------
    # Step 2: Sanity check -- size-3 functions should be LP-feasible at s=3
    # ------------------------------------------------------------------
    print("=" * 70)
    print("Step 2: SANITY CHECK -- size-3 functions feasible at s=3?")
    print("=" * 70)

    size3_fns = sorted([tt for tt, sz in sizes4.items() if sz == 3])
    print(f"  {len(size3_fns)} functions with actual size 3. Testing first 5.")
    print(f"  {'TT':>20}  {'s=2 feas?':>10}  {'s=3 feas?':>10}  {'time':>8}")
    print(f"  {'-'*55}")

    for tt in size3_fns[:5]:
        result = truth_table_properties(tt, n)
        if result is None:
            continue
        ip, ip2, bal = result
        tt_str = bin(tt)[2:].zfill(2**n)

        t0 = time.time()
        feas2, cnt2 = sample_and_check(n, 2, ip, ip2, max_tries=500)
        feas3, cnt3 = sample_and_check(n, 3, ip, ip2, max_tries=500)
        elapsed = time.time() - t0

        print(f"  {tt_str:>20}  {'YES' if feas2 else 'no':>10}  "
              f"{'YES' if feas3 else 'no':>10}  {elapsed:>7.1f}s")
        sys.stdout.flush()

    # ------------------------------------------------------------------
    # Step 3: MAIN TEST -- hardest functions (size 5), test LP at size 4
    # ------------------------------------------------------------------
    print()
    print("=" * 70)
    print(f"Step 3: MAIN TEST -- {NUM_HARDEST_TO_TEST} hardest functions (actual size {max_size})")
    print(f"  Testing LP feasibility at size {max_size - 1} with {MAX_SAMPLES} random structures")
    print("  If ANY structure is feasible => gap exists (LP_min <= {})".format(max_size - 1))
    print("  If ALL infeasible => LP_min >= {} (exact for this function)".format(max_size))
    print("=" * 70)
    print()
    print(f"  {'#':>3}  {'TT':>20}  {'s={} feas?'.format(max_size-1):>12}  "
          f"{'tried':>8}  {'LP_min':>8}  {'exact?':>8}  {'time':>8}")
    print(f"  {'-'*75}")

    gap_found = False
    exact_count = 0
    gap_count = 0

    for idx, tt in enumerate(hardest[:NUM_HARDEST_TO_TEST]):
        result = truth_table_properties(tt, n)
        if result is None:
            print(f"  {idx+1:>3}  (constant/degenerate, skipped)")
            continue
        ip, ip2, bal = result
        tt_str = bin(tt)[2:].zfill(2**n)

        t0 = time.time()
        feas, cnt = sample_and_check(n, max_size - 1, ip, ip2,
                                     max_tries=MAX_SAMPLES, seed=42 + idx)
        elapsed = time.time() - t0

        if feas:
            lp_min_str = f"<= {max_size - 1}"
            exact_str = "GAP"
            gap_found = True
            gap_count += 1
        else:
            lp_min_str = f">= {max_size}"
            exact_str = "exact"
            exact_count += 1

        print(f"  {idx+1:>3}  {tt_str:>20}  {'YES' if feas else 'no':>12}  "
              f"{cnt:>8}  {lp_min_str:>8}  {exact_str:>8}  {elapsed:>7.1f}s")
        sys.stdout.flush()

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Tested {exact_count + gap_count} of {len(hardest)} hardest n=4 functions (actual size {max_size})")
    print(f"  LP tested at size {max_size - 1} with {MAX_SAMPLES} random circuit structures each")
    print()
    if gap_found:
        print(f"  RESULT: GAP FOUND for {gap_count} functions!")
        print(f"  tau_2 is NOT exact for n=4.")
        print(f"  The SA-2 LP allows feasible solutions at size {max_size - 1}")
        print(f"  for functions that actually require size {max_size}.")
    else:
        print(f"  RESULT: All {exact_count} tested functions had LP infeasible at size {max_size - 1}.")
        print(f"  tau_2 appears exact for n=4 (at least for the tested functions).")
        print(f"  NOTE: This used random sampling ({MAX_SAMPLES} structures), not exhaustive enumeration.")
        print(f"  A feasible structure might exist that was not sampled.")
    print()


if __name__ == '__main__':
    main()
