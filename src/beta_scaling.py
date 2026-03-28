"""
β SCALING WITH n: Does the critical exponent depend on n?

If β(n) → const for P: universal class stable.
If β(n) → ∞ for NP-hard: transition disappears → different class.

Test: compute β for n=3 and n=4 functions.
For n=4: circuit enumeration expensive (s=3 has 12600 circuits for n=3,
but ~500K for n=4). Limit to s ≤ 3.
"""

import math
import time
import random


def count_valid(n, s, target_tt):
    """Count circuits of size s computing target. Returns (valid, total)."""
    count = [0]
    total = [0]

    def evaluate(specs, x):
        wire = [(x >> j) & 1 for j in range(n)]
        for gt, i1, i2 in specs:
            if gt == 0: wire.append(wire[i1] & wire[i2])
            elif gt == 1: wire.append(wire[i1] | wire[i2])
            elif gt == 2: wire.append(1 - wire[i1])
        return wire[-1] if specs else 0

    def search(depth, specs):
        if depth == s:
            total[0] += 1
            for x in range(2**n):
                if evaluate(specs, x) != target_tt[x]:
                    return
            count[0] += 1
            return
        nw = n + depth
        for gt in range(3):
            if gt == 2:
                for i1 in range(nw):
                    search(depth+1, specs + [(gt, i1, 0)])
            else:
                for i1 in range(nw):
                    for i2 in range(i1, nw):
                        search(depth+1, specs + [(gt, i1, i2)])

    search(0, [])
    return count[0], total[0]


def main():
    random.seed(42)
    print("=" * 60)
    print("  β SCALING: Critical exponent vs n")
    print("=" * 60)

    # n=3 functions (recompute for comparison)
    fns_3 = {
        'AND3': (3, {b: 1 if b == 7 else 0 for b in range(8)}),
        'OR3': (3, {b: 0 if b == 0 else 1 for b in range(8)}),
        'MAJ3': (3, {b: 1 if bin(b).count('1') >= 2 else 0 for b in range(8)}),
    }

    # n=4 functions
    fns_4 = {
        'AND4': (4, {b: 1 if b == 15 else 0 for b in range(16)}),
        'OR4': (4, {b: 0 if b == 0 else 1 for b in range(16)}),
        'MAJ4': (4, {b: 1 if bin(b).count('1') >= 2 else 0 for b in range(16)}),
        'TH3_4': (4, {b: 1 if bin(b).count('1') >= 3 else 0 for b in range(16)}),
    }

    all_fns = list(fns_3.items()) + list(fns_4.items())

    print(f"\n  {'Function':<10} {'n':>3} {'s':>3} {'valid':>8} {'total':>10} "
          f"{'density':>12} {'log D':>8}")
    print("  " + "-" * 58)

    results = {}

    for name, (n, tt) in all_fns:
        densities = []
        max_s = 4 if n == 3 else 3
        for s in range(1, max_s + 1):
            t0 = time.time()
            v, t = count_valid(n, s, tt)
            dt = time.time() - t0
            d = v / t if t > 0 else 0
            log_d = math.log10(d) if d > 0 else -99
            print(f"  {name:<10} {n:>3} {s:>3} {v:>8} {t:>10} "
                  f"{d:>12.8f} {log_d:>8.2f} [{dt:.1f}s]")
            densities.append((s, d))
            if dt > 60:
                break

        # Find s* and compute β
        s_star = None
        for s, d in densities:
            if d > 0:
                s_star = s
                break

        if s_star is not None:
            points = [(s, d) for s, d in densities if d > 0 and s > s_star]
            if points:
                xs = [math.log(s - s_star + 1) for s, d in points]
                ys = [math.log(d) for s, d in points]
                m = len(xs)
                if m >= 2:
                    sx=sum(xs); sy=sum(ys); sxy=sum(x*y for x,y in zip(xs,ys))
                    sxx=sum(x*x for x in xs); den=m*sxx-sx*sx
                    if den != 0:
                        beta = (m*sxy - sx*sy) / den
                        results[name] = {'n': n, 's_star': s_star, 'beta': beta}
                        print(f"  → s*={s_star}, β≈{beta:.2f}")

        print()
        import sys; sys.stdout.flush()

    print(f"\n{'='*60}")
    print("  COMPARISON: β across functions and n")
    print(f"{'='*60}")
    print(f"\n  {'Function':<10} {'n':>3} {'s*':>4} {'β':>8}")
    print("  " + "-" * 28)
    for name in sorted(results.keys()):
        r = results[name]
        print(f"  {name:<10} {r['n']:>3} {r['s_star']:>4} {r['beta']:>8.2f}")

    print(f"""
  KEY QUESTIONS:
  1. Is β(AND3) ≈ β(AND4)? (Same universality class across n?)
  2. Is β(AND) ≠ β(MAJ)? (Different classes for different complexity?)
  3. Does β increase with function complexity?

  If β universal for P-functions: UNIVERSALITY confirmed.
  If β different for NP-hard: SEPARATION via universality class.
  """)


if __name__ == "__main__":
    main()
