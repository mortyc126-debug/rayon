"""
PHASE TRANSITION IN CIRCUIT SPACE.

C(f, s) = {circuits of size ≤ s computing f}.
|C(f, s)| = 0 for s < complexity(f), > 0 for s ≥ complexity(f).

DENSITY D(f, s) = |C(f, s)| / |all circuits of size s|.

Near the critical point s* = complexity(f):
  D(s) ∝ (s - s*)^β  for s > s*.

β = CRITICAL EXPONENT. Universal property.

If β(P-functions) ≠ β(NP-hard functions): SEPARATION!

EXPERIMENT: Measure D(s) for various functions near their s*.
Fit β from the scaling D ∝ (s-s*)^β.
"""

import math
import time
import random
import itertools


def count_circuits(n, s, target_tt):
    """Count circuits of EXACTLY size s computing target."""
    num_inputs = 2**n
    count = 0
    total = 0

    def evaluate(specs, x):
        wire = [(x >> j) & 1 for j in range(n)]
        for gt, i1, i2 in specs:
            if gt == 0: wire.append(wire[i1] & wire[i2])
            elif gt == 1: wire.append(wire[i1] | wire[i2])
            elif gt == 2: wire.append(1 - wire[i1])
        return wire[-1] if specs else 0

    def search(depth, specs):
        nonlocal count, total
        if depth == s:
            total += 1
            ok = True
            for x in range(num_inputs):
                if evaluate(specs, x) != target_tt[x]:
                    ok = False
                    break
            if ok:
                count += 1
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
    return count, total


def main():
    random.seed(42)
    print("=" * 60)
    print("  PHASE TRANSITION: MCSP density D(s) near critical s*")
    print("  Scaling D ∝ (s - s*)^β → critical exponent β")
    print("=" * 60)

    functions = {
        'AND3': (3, {b: 1 if b == 7 else 0 for b in range(8)}),
        'OR3': (3, {b: 0 if b == 0 else 1 for b in range(8)}),
        'MAJ3': (3, {b: 1 if bin(b).count('1') >= 2 else 0 for b in range(8)}),
        'XOR3': (3, {b: bin(b).count('1') % 2 for b in range(8)}),
        'NAND3': (3, {b: 0 if b == 7 else 1 for b in range(8)}),
    }

    for name, (n, tt) in functions.items():
        print(f"\n  {name} (n={n}):")
        print(f"  {'s':>4} {'valid':>8} {'total':>10} {'density':>12} {'log D':>8}")
        print(f"  {'-'*45}")

        densities = []
        for s in range(1, 6):
            t0 = time.time()
            v, t = count_circuits(n, s, tt)
            dt = time.time() - t0
            d = v / t if t > 0 else 0
            log_d = math.log10(d) if d > 0 else -99
            print(f"  {s:>4} {v:>8} {t:>10} {d:>12.8f} {log_d:>8.2f}")
            densities.append((s, d))
            if dt > 15:
                break

        # Find critical s* (first s where density > 0)
        s_star = None
        for s, d in densities:
            if d > 0:
                s_star = s
                break

        if s_star is not None and len(densities) > s_star:
            print(f"  s* = {s_star} (first non-zero density)")

            # Fit β: log D = β × log(s - s* + 1) + const
            points = [(s, d) for s, d in densities if d > 0 and s > s_star]
            if len(points) >= 2:
                xs = [math.log(s - s_star + 1) for s, d in points]
                ys = [math.log(d) for s, d in points]
                # Linear fit
                m = len(xs)
                sx = sum(xs); sy = sum(ys)
                sxy = sum(x*y for x,y in zip(xs,ys)); sxx = sum(x*x for x in xs)
                den = m*sxx - sx*sx
                if den != 0:
                    beta = (m*sxy - sx*sy) / den
                    print(f"  β ≈ {beta:.2f} (critical exponent)")

    print(f"\n{'='*60}")
    print("  IF β differs between P and NP-hard functions:")
    print("  → different universality classes → SEPARATION")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
