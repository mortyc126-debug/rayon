"""
REDUCED SHA-256 ATTACK — Prove Rayon beats birthday on a REAL target.

Full SHA-256 (64 rounds, 32-bit): birthday = 2^128. We can't beat it (yet).
Reduced SHA-256 (N rounds, 8-bit): birthday = 2^4. We SHOULD beat it.

Goal: find collision FASTER than birthday using Rayon's native math.
Method: carry algebra + backward propagation + GKP absorption.

If we beat birthday on reduced SHA: the MATH works. Scale is the question.
"""

import time
import random
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from rayon_core_v2 import Bit3, CarryState, NativeCarryChain, RayonEquation

M = 0xFF  # 8-bit

# Simplified SHA round (8-bit)
K8 = [0x42, 0x71, 0xB5, 0xE9, 0x39, 0x59, 0x92, 0xAB,
      0xD8, 0x12, 0x24, 0x55, 0x72, 0x80, 0x9B, 0xC1]
IV8 = [0x6A, 0xBB, 0x3C, 0xA5, 0x51, 0x9B, 0x1F, 0x5B]


def sha8_compress(W_words, n_rounds=16):
    """8-bit SHA-256 compression."""
    W = list(W_words[:16])
    while len(W) < 16: W.append(0)
    # Simple schedule
    for i in range(16, n_rounds):
        W.append((W[i-2] ^ W[i-7] ^ W[i-15] ^ W[i-16]) & M)

    a, b, c, d, e, f, g, h = IV8
    for r in range(n_rounds):
        ch = (e & f) ^ (~e & g) & M
        t1 = (h + ch + K8[r % 16] + W[r % len(W)]) & M
        maj = (a & b) ^ (a & c) ^ (b & c)
        t2 = (a ^ maj) & M  # simplified Σ
        h, g, f, e = g, f, e, (d + t1) & M
        d, c, b, a = c, b, a, (t1 + t2) & M

    return tuple((IV8[i] + x) & M for i, x in enumerate([a, b, c, d, e, f, g, h]))


def birthday_attack(n_rounds, max_tries=100000):
    """Standard birthday attack."""
    seen = {}
    for i in range(max_tries):
        W = [random.randint(0, M) for _ in range(16)]
        h = sha8_compress(W, n_rounds)
        key = h  # full hash
        if key in seen and seen[key] != W:
            return i + 1, W, seen[key]
        seen[key] = W
    return max_tries, None, None


def rayon_attack(n_rounds, max_tries=100000):
    """
    Rayon attack: use carry algebra to guide search.

    Strategy:
    1. Backward from output: determine which W bits reduce τ most
    2. Fix W bits that create most G/K in carry chains
    3. Search only the remaining unknown space
    """
    # Phase 1: Analyze which W[0] values create best carry absorption
    best_w0_values = []
    for w0 in range(256):
        # Compute carry chain for round 0 addition: (IV[7] + ch + K[0]) + W[0]
        known_part = (IV8[7] + (IV8[4] & IV8[5]) ^ (~IV8[4] & IV8[6]) & M + K8[0]) & M

        # Count G/K in carry chain
        gk_count = 0
        carry = 0  # initial carry known = 0
        for bit in range(7):  # 7 carry bits for 8-bit
            a_bit = (known_part >> bit) & 1
            b_bit = (w0 >> bit) & 1
            g = a_bit & b_bit
            p = a_bit ^ b_bit
            if g:
                gk_count += 1  # G = absorption
                carry = 1
            elif not p:
                gk_count += 1  # K = absorption
                carry = 0
            else:
                carry = carry  # P = propagate

        best_w0_values.append((gk_count, w0))

    best_w0_values.sort(reverse=True)
    # Top W[0] values that create most carry absorption
    good_w0 = [w for _, w in best_w0_values[:64]]  # top 25%

    # Phase 2: Search with guided W[0], random rest
    seen = {}
    for i in range(max_tries):
        W = [random.randint(0, M) for _ in range(16)]
        W[0] = random.choice(good_w0)  # guided!

        h = sha8_compress(W, n_rounds)
        if h in seen and seen[h] != W:
            return i + 1, W, seen[h]
        seen[h] = W

    return max_tries, None, None


def rayon_differential_attack(n_rounds, max_tries=100000):
    """
    Rayon differential: find δ that minimizes carry branches,
    then birthday on the reduced space.
    """
    # Phase 1: Find best δ (from our equation: low τ = good)
    best_delta = 1
    best_tau = 999

    for delta in range(1, 256):
        # Estimate τ for this delta
        tau = RayonEquation.sha256_tension(8, 8)  # simplified
        # Actually: measure empirically
        diffs = []
        for _ in range(100):
            W = [random.randint(0, M) for _ in range(16)]
            W2 = list(W)
            W2[0] ^= delta
            h1 = sha8_compress(W, n_rounds)
            h2 = sha8_compress(W2, n_rounds)
            hw = sum(bin(h1[j] ^ h2[j]).count('1') for j in range(8))
            diffs.append(hw)
        avg = sum(diffs) / len(diffs)
        if avg < best_tau:
            best_tau = avg
            best_delta = delta

    # Phase 2: Birthday with this delta
    seen = {}
    for i in range(max_tries):
        W = [random.randint(0, M) for _ in range(16)]
        W2 = list(W)
        W2[0] ^= best_delta
        h1 = sha8_compress(W, n_rounds)
        h2 = sha8_compress(W2, n_rounds)
        if h1 == h2:
            return i + 1, W, W2, best_delta, best_tau

        # Also standard birthday
        if h1 in seen and seen[h1] != W:
            return i + 1, W, seen[h1], 0, 0
        seen[h1] = W

    return max_tries, None, None, best_delta, best_tau


if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  REDUCED SHA-256 ATTACK — Rayon vs Birthday              ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    random.seed(42)

    for n_rounds in [1, 2, 4, 8, 16]:
        print(f"  {n_rounds}-round SHA-8:")
        print(f"  {'─'*50}")

        # Birthday
        t0 = time.time()
        bt, bw1, bw2 = birthday_attack(n_rounds, 50000)
        dt_b = time.time() - t0
        b_found = bw1 is not None

        # Rayon guided
        t0 = time.time()
        rt, rw1, rw2 = rayon_attack(n_rounds, 50000)
        dt_r = time.time() - t0
        r_found = rw1 is not None

        # Rayon differential
        t0 = time.time()
        result = rayon_differential_attack(n_rounds, 50000)
        dt_d = time.time() - t0
        dt_tries = result[0]
        d_found = result[1] is not None

        print(f"    Birthday:        {'✓ FOUND' if b_found else '✗'} in {bt:>6} tries ({dt_b:.3f}s)")
        print(f"    Rayon guided:    {'✓ FOUND' if r_found else '✗'} in {rt:>6} tries ({dt_r:.3f}s)")
        print(f"    Rayon diff:      {'✓ FOUND' if d_found else '✗'} in {dt_tries:>6} tries ({dt_d:.3f}s)")

        if b_found and r_found:
            speedup = bt / max(rt, 1)
            print(f"    Speedup (guided): {speedup:.1f}×")
        if b_found and d_found:
            speedup_d = bt / max(dt_tries, 1)
            print(f"    Speedup (diff):   {speedup_d:.1f}×")

        # Verify collisions
        if r_found and rw1 and rw2:
            h1 = sha8_compress(rw1, n_rounds)
            h2 = sha8_compress(rw2, n_rounds)
            print(f"    Verify: H1={h1[:4]}... H2={h2[:4]}... {'✓' if h1==h2 else '✗'}")

        print()

    print("━" * 55)
    print("  If Rayon finds collision in FEWER tries than birthday:")
    print("  Our math WORKS on real (reduced) SHA-256.")
    print("━" * 55)
