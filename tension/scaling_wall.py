"""
SCALING WALL — Where does funnel compression die?

The honest measurement: funnel cycle length vs bit width.
At what point does SHA's mixing kill the short-cycle structure?

This is RAYON SCIENCE: we measure, we don't assume.

RESULTS:
  4-bit:  cycle ~90, compression 47M×     ← weak mixing
  8-bit:  cycle ~???, measure it
  16-bit: cycle ~???, measure it
  32-bit: cycle > 10M, no compression     ← strong mixing

The WALL exists. Finding it tells us where Rayon's funnel math
applies and where it doesn't. That's real knowledge.
"""

import random
import time
import sys, os

sys.path.insert(0, os.path.dirname(__file__))

M = {4: 0xF, 8: 0xFF, 12: 0xFFF, 16: 0xFFFF, 20: 0xFFFFF}

IV_BASE = (0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
           0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19)

K_BASE = [
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,
    0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,
    0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,
    0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,
    0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,
    0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,
    0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,
    0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,
    0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2,
]


def make_sha_variant(bits):
    """Create SHA variant for given bit width."""
    mask = (1 << bits) - 1
    iv = tuple(v & mask for v in IV_BASE)
    k = [v & mask for v in K_BASE]

    # Rotation amounts scaled to bit width
    # SHA-256 uses: (2,13,22), (6,11,25), (7,18,3>>), (17,19,10>>)
    # Scale proportionally
    def rot(x, n):
        n = n % bits if bits > 0 else 0
        return ((x >> n) | (x << (bits - n))) & mask

    def compress(state, W):
        w = list(W[:16])
        while len(w) < 16:
            w.append(0)
        for i in range(16, 64):
            s0 = rot(w[i-15], max(1, 7*bits//32)) ^ rot(w[i-15], max(1, 18*bits//32)) ^ (w[i-15] >> max(1, 3*bits//32))
            s1 = rot(w[i-2], max(1, 17*bits//32)) ^ rot(w[i-2], max(1, 19*bits//32)) ^ (w[i-2] >> max(1, 10*bits//32))
            w.append((w[i-16] + s0 + w[i-7] + s1) & mask)

        a, b, c, d, e, f, g, h = state
        for r in range(64):
            S1 = rot(e, max(1, 6*bits//32)) ^ rot(e, max(1, 11*bits//32)) ^ rot(e, max(1, 25*bits//32))
            ch = (e & f) ^ ((~e) & g) & mask
            t1 = (h + S1 + ch + k[r % 64] + w[r % len(w)]) & mask
            S0 = rot(a, max(1, 2*bits//32)) ^ rot(a, max(1, 13*bits//32)) ^ rot(a, max(1, 22*bits//32))
            maj = (a & b) ^ (a & c) ^ (b & c)
            t2 = (S0 + maj) & mask
            h, g, f, e = g, f, e, (d + t1) & mask
            d, c, b, a = c, b, a, (t1 + t2) & mask

        return tuple((state[i] + x) & mask for i, x in enumerate([a, b, c, d, e, f, g, h]))

    return compress, iv


def brent_cycle(F, start, max_steps):
    """Brent's cycle detection. Returns (cycle_len, tail_len) or None."""
    power = lam = 1
    tortoise = start
    hare = F(start)
    steps = 0
    while tortoise != hare:
        if power == lam:
            tortoise = hare
            power *= 2
            lam = 0
        hare = F(hare)
        lam += 1
        steps += 1
        if steps > max_steps:
            return None

    # Find tail
    tortoise = hare = start
    for _ in range(lam):
        hare = F(hare)
    mu = 0
    while tortoise != hare:
        tortoise = F(tortoise)
        hare = F(hare)
        mu += 1

    return (lam, mu)


def measure_scaling_wall():
    """Find where funnel compression dies."""
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  SCALING WALL — Where does funnel compression die?       ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    random.seed(42)

    results = []

    for bits in [4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 16]:
        mask = (1 << bits) - 1
        state_space = 2 ** (bits * 8)  # 8 words × bits per word
        birthday = int(state_space ** 0.5)

        compress, iv = make_sha_variant(bits)
        W2 = [random.randint(0, mask) for _ in range(16)]
        F = lambda s, c=compress, w=W2: c(s, w)

        # Limit: at most 10M steps, or 10 seconds
        max_steps = min(10_000_000, birthday * 100)
        t0 = time.time()
        result = brent_cycle(F, iv, max_steps)
        dt = time.time() - t0

        if result:
            cycle_len, tail_len = result
            compression = state_space / cycle_len if cycle_len > 0 else 0
            ratio = birthday / cycle_len if cycle_len > 0 else 0

            results.append((bits, cycle_len, tail_len, compression, ratio, dt))

            marker = ""
            if ratio > 100:
                marker = " ★★★ MASSIVE"
            elif ratio > 10:
                marker = " ★★ LARGE"
            elif ratio > 2:
                marker = " ★ SOME"
            elif ratio > 1:
                marker = " marginal"
            else:
                marker = " ✗ NO advantage"

            print(f"  {bits:>3}-bit: cycle={cycle_len:>10,}  tail={tail_len:>10,}  "
                  f"compression={compression:>12.0f}×  "
                  f"birthday/cycle={ratio:>8.1f}  [{dt:.1f}s]{marker}")
        else:
            results.append((bits, None, None, None, None, dt))
            print(f"  {bits:>3}-bit: NO CYCLE in {max_steps:,} steps  "
                  f"(state space = 2^{bits*8})  [{dt:.1f}s]  ✗ WALL")

    # Analysis
    print()
    print("  ═══════════════════════════════════════════════════════")
    print("  ANALYSIS: The Scaling Wall")
    print()

    wall_bits = None
    for bits, cycle, tail, comp, ratio, dt in results:
        if cycle is None:
            wall_bits = bits
            break

    if wall_bits:
        print(f"  The WALL is at {wall_bits}-bit words.")
        print(f"    Below {wall_bits}: funnel compression exists → collision advantage")
        print(f"    At {wall_bits}+: SHA mixing is strong enough → no short cycles")
        print()
        print(f"  WHY the wall exists:")
        print(f"    SHA-256's mixing quality depends on word size:")
        print(f"    - Rotations: at {wall_bits} bits, rotations span enough bits to mix well")
        print(f"    - Carries: at {wall_bits} bits, carry chains propagate information")
        print(f"    - Schedule: XOR-based schedule needs enough bits for entropy")
        print()
        print(f"  This is NOT failure. This is MEASUREMENT.")
        print(f"  Rayon's math reveals WHERE structure exists and WHERE it doesn't.")
    else:
        last_good = results[-1]
        print(f"  Funnel compression exists up to at least {last_good[0]}-bit!")
        print(f"  Largest tested: cycle={last_good[1]:,}, ratio={last_good[4]:.1f}×")

    # Birthday-equivalent comparison
    print()
    print("  FUNNEL vs BIRTHDAY at each scale:")
    print(f"  {'bits':>5}  {'state space':>14}  {'birthday':>14}  {'cycle':>14}  {'advantage':>12}")
    print(f"  {'─'*65}")
    for bits, cycle, tail, comp, ratio, dt in results:
        ss = f"2^{bits*8}"
        bd = f"2^{bits*4}"
        if cycle is not None:
            print(f"  {bits:>5}  {ss:>14}  {bd:>14}  {cycle:>14,}  {ratio:>12.1f}×")
        else:
            print(f"  {bits:>5}  {ss:>14}  {bd:>14}  {'> max':>14}  {'WALL':>12}")

    print(f"""
  ═══════════════════════════════════════════════════════
  THE SCALING WALL:

    Rayon funnel compression works where SHA mixing is weak.
    SHA mixing quality grows with word size.
    At some bit width, mixing becomes strong enough
    that cycles reach near-birthday length.

    This is the WALL. Beyond it, funnel ≈ birthday.
    Below it, funnel gives genuine advantage.

    The wall tells us: to break SHA-256 at 32-bit,
    we need something BEYOND funnel compression.
    We need to attack the MIXING itself.

    Rayon has tools for that:
      - ? propagation (three-state logic)
      - Kill-link analysis (which ops destroy info)
      - Carry algebra (where uncertainty concentrates)
      - Rasloyenie (stratification by dependency)

    The funnel was chapter 1. The wall is chapter 2.
    Chapter 3: attack the mixing directly.
  ═══════════════════════════════════════════════════════
""")

    return results


if __name__ == '__main__':
    measure_scaling_wall()
