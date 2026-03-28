"""
OPTIMAL TRADEOFF: For EACH treewidth T, take the BEST bound.

Bound 1 (propagation): S ≥ C(N,k) / 2^{c₁·T}
  Strong for small T, weak for large T.

Bound 2 (formula):     S ≥ 2^{c₂·N^{1/6} / (T+1)}
  Strong for small T, weak for large T.

The ADVERSARY chooses T to MINIMIZE max(Bound1, Bound2).
If the minimum is still super-poly → P ≠ NP.

Minimum of max: at the crossing point where Bound1 = Bound2.
  C(N,k) / 2^{c₁T} = 2^{c₂N^{1/6}/(T+1)}
  log₂ C(N,k) - c₁T = c₂N^{1/6}/(T+1)

Let A = log₂ C(N, N^{1/3}) ≈ N^{1/3} log₂ N
Let B = c₂ · N^{1/6}

Equation: A - c₁T = B/(T+1)
  (A - c₁T)(T+1) = B
  AT + A - c₁T² - c₁T = B
  -c₁T² + (A - c₁)T + (A - B) = 0
  c₁T² - (A-c₁)T - (A-B) = 0

Discriminant: (A-c₁)² + 4c₁(A-B)
For large N: A >> B >> c₁.
T ≈ A/(2c₁) ≈ N^{1/3} log N / (2c₁)

At this T: Bound = C(N,k) / 2^{c₁ · A/(2c₁)} = C(N,k) / 2^{A/2}
  = 2^A / 2^{A/2} = 2^{A/2} = 2^{Ω(N^{1/3} log N / 2)}
  = 2^{Ω(N^{1/3} log N)}
  = SUPER-POLYNOMIAL!!!

Wait... this says: at the OPTIMAL T for the adversary,
the bound is STILL super-polynomial?!

Let me verify this carefully.
"""

import math
import sys


def compute_bounds(N, k, c1, c2):
    """For each T, compute both bounds and the max."""
    n = N * (N-1) // 2
    log_cnk = k * math.log2(N) - sum(math.log2(i+1) for i in range(k))  # approx

    # More precise: log₂ C(N,k)
    log_cnk = sum(math.log2(N - i) - math.log2(i + 1) for i in range(k))

    # Razborov bound: formula ≥ 2^{c₂ · N^{1/6}}
    razborov_exp = c2 * N**(1/6)

    print(f"\n  N={N}, k={k}, n={n}")
    print(f"  log₂ C(N,k) = {log_cnk:.1f}")
    print(f"  Razborov exponent = {razborov_exp:.1f}")
    print(f"  (c₁={c1}, c₂={c2})")

    print(f"\n  {'T':>6} {'Bound1 (log)':>14} {'Bound2 (log)':>14} "
          f"{'max (log)':>12} {'super-poly?':>12}")
    print("  " + "-" * 60)

    best_min_max = float('inf')
    best_T = 0

    for T in range(1, n + 1):
        # Bound 1: log₂(S) ≥ log₂ C(N,k) - c₁·T
        b1 = log_cnk - c1 * T

        # Bound 2: log₂(S) ≥ c₂·N^{1/6} / (T+1)
        b2 = razborov_exp / (T + 1)

        max_b = max(b1, b2)

        if max_b < best_min_max:
            best_min_max = max_b
            best_T = T

        if T <= 5 or T % max(1, n // 20) == 0 or T == n:
            sp = "YES!" if max_b > 10 * math.log2(N) else "no"
            print(f"  {T:>6} {b1:>14.1f} {b2:>14.1f} "
                  f"{max_b:>12.1f} {sp:>12}")

    print(f"\n  Optimal T (adversary): T* = {best_T}")
    print(f"  Min-max bound: log₂(S) ≥ {best_min_max:.1f}")
    print(f"  S ≥ 2^{best_min_max:.1f}")

    threshold = 2 * math.log2(N)  # super-poly if > this
    if best_min_max > threshold:
        print(f"  >>> SUPER-POLYNOMIAL! (> 2·log N = {threshold:.1f})")
        print(f"  >>> This means: P ≠ NP (if propagation sets are distinct)")
    else:
        print(f"  Not super-polynomial (≤ {threshold:.1f})")

    return best_min_max, best_T


def main():
    print("=" * 70)
    print("  OPTIMAL TRADEOFF: Can the adversary escape BOTH bounds?")
    print("  If min over T of max(Bound1, Bound2) = super-poly → P ≠ NP")
    print("=" * 70)

    # Test for various N with k = N^{1/3}
    # Use conservative constants
    c1 = 3  # connected subsets constant
    c2 = 0.1  # Razborov constant (conservative)

    results = []

    for N in [8, 27, 64, 125, 216, 512, 1000, 10000]:
        k = max(2, int(round(N**(1/3))))
        if k >= N:
            continue

        best_bound, best_T = compute_bounds(N, k, c1, c2)
        results.append((N, k, best_bound, best_T))
        sys.stdout.flush()

    # Summary
    print(f"\n\n{'='*70}")
    print("  SCALING SUMMARY")
    print(f"{'='*70}")
    print(f"\n  {'N':>7} {'k':>5} {'T*':>5} {'log S*':>8} {'S* growth':>15}")
    print("  " + "-" * 45)

    for N, k, bound, T in results:
        if bound > 0:
            print(f"  {N:>7} {k:>5} {T:>5} {bound:>8.1f} 2^{bound:.0f}")
        else:
            print(f"  {N:>7} {k:>5} {T:>5} {bound:>8.1f} {'< 1':>15}")

    # Fit growth
    valid = [(N, b) for N, _, b, _ in results if b > 1]
    if len(valid) >= 3:
        log_Ns = [math.log(N) for N, _ in valid]
        bounds = [b for _, b in valid]

        # Fit: bound ≈ a × N^b
        m = len(log_Ns)
        sx = sum(log_Ns); sy = sum(bounds)
        sxy = sum(x*y for x,y in zip(log_Ns, bounds))
        sxx = sum(x*x for x in log_Ns)
        denom = m * sxx - sx**2
        if denom != 0:
            slope = (m * sxy - sx * sy) / denom
            intercept = (sy - slope * sx) / m

            print(f"\n  Growth fit: log₂(S*) ≈ {intercept:.1f} + {slope:.2f} × ln(N)")
            print(f"  S* ≈ 2^{{{slope:.2f} ln N}} = N^{{{slope/math.log(2):.2f}}}")

            if slope > 1:
                print(f"\n  >>> min-max bound grows SUPER-LOGARITHMICALLY!")
                print(f"  >>> S* grows as N^{slope/math.log(2):.2f} = POLYNOMIAL in N")
                print(f"  >>> For this to prove P ≠ NP: need S* super-poly in N")
                print(f"  >>> Currently: S* = polynomial → NOT sufficient alone")
                print(f"  >>> BUT: for large k (k growing with N): might become super-poly")

    print(f"\n{'='*70}")
    print("  THEORETICAL ANALYSIS")
    print(f"{'='*70}")
    print("""
    At the crossing point T* ≈ log₂C(N,k) / (2c₁):

    Bound at T* ≈ log₂C(N,k) / 2 ≈ (N^{1/3} log N) / 2

    This is Ω(N^{1/3} log N) — SUPER-LOGARITHMIC in N!

    But: "super-poly in N" requires S ≥ N^{ω(1)}, i.e., S growing
    faster than ANY fixed polynomial.

    Our bound: S ≥ 2^{Ω(N^{1/3} log N)}. IS this super-poly?

    2^{N^{1/3} log N} = N^{N^{1/3}} — YES, SUPER-POLYNOMIAL!

    Wait — let me recheck. At T* = Θ(N^{1/3} log N):
    Bound1 = log C(N,k) - c₁T* = A - c₁A/(2c₁) = A - A/2 = A/2.
    A = N^{1/3} log N.
    Bound1 at T* = N^{1/3} log N / 2.

    S ≥ 2^{N^{1/3} log N / 2} = N^{N^{1/3}/2} = SUPER-POLY!!!

    THE KEY QUESTION: Is the propagation bound valid?
    i.e., are there really C(N,k) DISTINCT connected propagation sets?

    If YES → P ≠ NP.
    If NO → bound doesn't hold.
    """)


if __name__ == "__main__":
    main()
