#!/usr/bin/env python3
"""
RAYON ATTACK SUITE — Automated differential search + preimage attack.

ATTACK 1: Find optimal δ for collision (minimize branch points)
ATTACK 2: Preimage via backward propagation + Rayon Wave
Both scale from 1 round to 64.
"""

import sys, os, time, random
sys.path.insert(0, os.path.dirname(__file__))

from rayon_numbers import RayonInt
from arithmetic import Ch, Maj, Sigma0, Sigma1
from rayon_wave import GF2Expr, WaveCircuit
from advanced_wave import RayonEngine

M32 = 0xFFFFFFFF
K256 = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]
IV = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
      0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]


def sha256_compress(W_words, n_rounds=64):
    W = list(W_words[:16])
    while len(W) < 16: W.append(0)
    for i in range(16, max(n_rounds, 16)):
        s0 = (((W[i-15]>>7)|(W[i-15]<<25))&M32)^(((W[i-15]>>18)|(W[i-15]<<14))&M32)^(W[i-15]>>3)
        s1 = (((W[i-2]>>17)|(W[i-2]<<15))&M32)^(((W[i-2]>>19)|(W[i-2]<<13))&M32)^(W[i-2]>>10)
        W.append((W[i-16]+s0+W[i-7]+s1)&M32)
    a,b,c,d,e,f,g,h = IV
    for r in range(n_rounds):
        S1=(((e>>6)|(e<<26))&M32)^(((e>>11)|(e<<21))&M32)^(((e>>25)|(e<<7))&M32)
        ch=(e&f)^(~e&g)&M32
        t1=(h+S1+ch+K256[r]+W[r])&M32
        S0=(((a>>2)|(a<<30))&M32)^(((a>>13)|(a<<19))&M32)^(((a>>22)|(a<<10))&M32)
        maj=(a&b)^(a&c)^(b&c)
        t2=(S0+maj)&M32
        h,g,f,e,d,c,b,a = g,f,e,(d+t1)&M32,c,b,a,(t1+t2)&M32
    return tuple((IV[i]+x)&M32 for i,x in enumerate([a,b,c,d,e,f,g,h]))


# ══════════════════════════════════════════════════════════
# ATTACK 1: Automated differential δ search
# ══════════════════════════════════════════════════════════

def differential_branch_count(delta_W0, n_rounds):
    """
    Count effective branch points for differential δ in W[0].

    Method: compute H(W) and H(W⊕δ) for random W.
    Measure: how many output bits differ? (Hamming weight of ΔH)
    Lower HW = closer to collision = fewer effective branches.
    """
    n_samples = 200
    hw_sum = 0

    for _ in range(n_samples):
        W = [random.randint(0, M32) for _ in range(16)]
        W2 = list(W)
        W2[0] ^= delta_W0

        h1 = sha256_compress(W, n_rounds)
        h2 = sha256_compress(W2, n_rounds)

        # Hamming weight of output difference
        hw = sum(bin(h1[i] ^ h2[i]).count('1') for i in range(8))
        hw_sum += hw

    return hw_sum / n_samples


def rayon_differential_analysis(delta_W0, n_rounds):
    """
    Rayon Wave analysis of differential circuit.

    Build: ΔH = H(W) ⊕ H(W⊕δ)
    Count: branch points in the differential propagation.
    """
    eng = RayonEngine()

    # Differential at round 0:
    # ΔW[0] = delta_W0. State difference = 0 (same IV).
    # After round 0: Δstate depends on ΔW[0] through Ch, Maj, additions.

    # Simplified 1-bit analysis: track which state bits become ?
    state_diff = [0] * 8  # 0 = no difference, 1 = difference exists

    # Round 0: ΔW[0] enters through T1
    # ΔT1 = ΔCh + ΔW[0] + carry_diffs
    # With same state (ΔIV=0): ΔCh = 0 (Ch inputs same)
    # So ΔT1 = ΔW[0] (the difference enters directly)

    branches = 0
    diff_bits = bin(delta_W0).count('1')  # initial difference bits

    for r in range(n_rounds):
        if r == 0:
            # Difference enters through W[0]
            active_diff = diff_bits
        elif r < 16:
            # W[r] has no difference (only W[0] differs)
            # But state carries difference from previous rounds
            # Each round: Ch and Maj on differing state = branch points
            active_diff = min(active_diff * 2, 256)  # rough: diff spreads
            branches += min(active_diff // 8, 32)  # AND gates on diffs
        else:
            # Schedule: ΔW[r] depends on ΔW[0] through XOR (linear, free)
            # But also through additions (nonlinear, branches)
            active_diff = min(active_diff + diff_bits, 256)
            branches += min(active_diff // 4, 64)

    return branches, active_diff


def attack_differential():
    print("━" * 60)
    print("  ATTACK 1: Automated Differential δ Search")
    print("━" * 60)
    print()

    for n_rounds in [1, 2, 4, 8, 16, 32, 64]:
        print(f"  {n_rounds}-round SHA-256:")

        best_delta = None
        best_hw = 256
        best_branches = 9999

        # Search over single-bit deltas in W[0]
        candidates = [1 << b for b in range(32)]
        # Add some multi-bit deltas
        candidates += [0x80000000, 0x00000001, 0xFF, 0xFF00,
                       0xFFFF0000, 0x0000FFFF, 0x55555555, 0xAAAAAAAA]
        candidates += [random.randint(1, M32) for _ in range(20)]

        t0 = time.time()
        for delta in candidates:
            hw = differential_branch_count(delta, n_rounds)
            branches, _ = rayon_differential_analysis(delta, n_rounds)

            if hw < best_hw:
                best_hw = hw
                best_delta = delta
                best_branches = branches

        dt = time.time() - t0

        # Try to find actual collision with best delta
        collision_found = False
        collision_tries = 0
        if best_hw < 200:  # only try if there's hope
            seen = {}
            for trial in range(min(50000, 2**17)):
                W = [random.randint(0, M32) for _ in range(16)]
                W2 = list(W)
                W2[0] ^= best_delta
                h1 = sha256_compress(W, n_rounds)
                h2 = sha256_compress(W2, n_rounds)
                collision_tries = trial + 1
                if h1 == h2:
                    collision_found = True
                    break

        status = "✓ COLLISION!" if collision_found else f"✗ (best HW={best_hw:.1f})"
        print(f"    Best δ: 0x{best_delta:08X}")
        print(f"    Avg ΔH HW: {best_hw:.1f}/256 (128=random, 0=collision)")
        print(f"    Rayon branches: {best_branches}")
        print(f"    Collision: {status} ({collision_tries} tries, {dt:.2f}s)")
        print()


# ══════════════════════════════════════════════════════════
# ATTACK 2: Preimage via backward propagation
# ══════════════════════════════════════════════════════════

def attack_preimage_backward(n_rounds, target_hash):
    """
    Preimage attack: given hash, find message.

    Method:
    1. Backward from output: recover final state
    2. Backward through rounds: recover W[r] values
    3. Backward through schedule: recover W[0..15]
    """
    # Step 1: Final state from hash
    final_state = tuple((target_hash[i] - IV[i]) & M32 for i in range(8))
    a63, b63, c63, d63, e63, f63, g63, h63 = final_state

    # Step 2: Backward round 63 → 62 → ...
    # Register shift backward: b[r] = a[r-1], c[r] = a[r-2], etc.
    # So: a[62] = b[63], a[61] = c[63], a[60] = d[63]
    #     e[62] = f[63], e[61] = g[63], e[60] = h[63]

    known_a = {n_rounds-1: a63}
    known_e = {n_rounds-1: e63}

    # From register shifts
    if n_rounds >= 2: known_a[n_rounds-2] = b63; known_e[n_rounds-2] = f63
    if n_rounds >= 3: known_a[n_rounds-3] = c63; known_e[n_rounds-3] = g63
    if n_rounds >= 4: known_a[n_rounds-4] = d63; known_e[n_rounds-4] = h63

    W_recovered = {}
    rounds_solved = 0

    for r in range(n_rounds - 1, -1, -1):
        # Need: a[r], a[r-1], a[r-2], a[r-3] for Maj
        #        e[r], e[r-1], e[r-2], e[r-3] for Ch
        a_r = known_a.get(r)
        a_r1 = known_a.get(r-1) if r >= 1 else IV[0]
        a_r2 = known_a.get(r-2) if r >= 2 else IV[1]
        a_r3 = known_a.get(r-3) if r >= 3 else IV[2]

        e_r = known_e.get(r)
        e_r1 = known_e.get(r-1) if r >= 1 else IV[4]
        e_r2 = known_e.get(r-2) if r >= 2 else IV[5]
        e_r3 = known_e.get(r-3) if r >= 3 else IV[6]
        h_prev = known_e.get(r-4) if r >= 4 else IV[7]  # h[r-1] = e[r-4]

        if all(x is not None for x in [a_r, a_r1, a_r2, a_r3, e_r, e_r1, e_r2, e_r3]):
            # T2 = Σ0(a[r-1]) + Maj(a[r-1], a[r-2], a[r-3])
            S0 = (((a_r1>>2)|(a_r1<<30))&M32)^(((a_r1>>13)|(a_r1<<19))&M32)^(((a_r1>>22)|(a_r1<<10))&M32)
            maj = (a_r1 & a_r2) ^ (a_r1 & a_r3) ^ (a_r2 & a_r3)
            T2 = (S0 + maj) & M32
            T1 = (a_r - T2) & M32

            # d[r-1] = a[r-4]
            d_prev = known_a.get(r-4)
            if r >= 4 and d_prev is None:
                # e[r] = d[r-1] + T1 → d[r-1] = e[r] - T1
                d_prev = (e_r - T1) & M32
                known_a[r-4] = d_prev

            if h_prev is not None:
                # T1 = h[r-1] + Σ1(e[r-1]) + Ch(e[r-1],e[r-2],e[r-3]) + K[r] + W[r]
                S1 = (((e_r1>>6)|(e_r1<<26))&M32)^(((e_r1>>11)|(e_r1<<21))&M32)^(((e_r1>>25)|(e_r1<<7))&M32)
                ch = (e_r1 & e_r2) ^ (~e_r1 & e_r3) & M32
                W_r = (T1 - h_prev - S1 - ch - K256[r]) & M32
                W_recovered[r] = W_r
                rounds_solved += 1

                # Also recover e[r-4] from: e[r] = d[r-1] + T1
                if r >= 4 and known_e.get(r-4) is None:
                    known_e[r-4] = (e_r - T1) & M32
            else:
                break  # h_prev unknown, chain broken
        else:
            break  # insufficient state knowledge

    return W_recovered, rounds_solved


def attack_preimage():
    print("━" * 60)
    print("  ATTACK 2: Preimage via Backward Propagation")
    print("━" * 60)
    print()

    for n_rounds in [1, 2, 4, 8, 16, 32, 64]:
        # Generate a random target
        random.seed(42)
        W_original = [random.randint(0, M32) for _ in range(16)]
        target = sha256_compress(W_original, n_rounds)

        t0 = time.time()
        W_recovered, rounds_solved = attack_preimage_backward(n_rounds, target)
        dt = time.time() - t0

        # Verify recovered W values
        correct = 0
        for r, w in W_recovered.items():
            if r < 16 and w == W_original[r]:
                correct += 1

        # Try to reconstruct full message and verify hash
        verified = False
        if rounds_solved >= n_rounds - 1:
            W_test = [W_recovered.get(r, 0) for r in range(16)]
            h_test = sha256_compress(W_test, n_rounds)
            verified = (h_test == target)

        print(f"  {n_rounds}-round SHA-256:")
        print(f"    Rounds solved backward: {rounds_solved}/{n_rounds}")
        print(f"    W values recovered: {len(W_recovered)}")
        print(f"    W[0..15] correct: {correct}/16")
        print(f"    Hash verified: {'✓ PREIMAGE FOUND!' if verified else '✗'}")
        print(f"    Time: {dt:.6f}s")
        print()


# ══════════════════════════════════════════════════════════
if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  RAYON ATTACK SUITE — Differential + Preimage            ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    random.seed(42)
    attack_preimage()
    attack_differential()

    print("━" * 60)
    print("  ATTACK SUITE COMPLETE")
    print("━" * 60)
