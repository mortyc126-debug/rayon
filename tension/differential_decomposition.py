"""
DIFFERENTIAL DECOMPOSITION — The new mathematics.

Standard view: ΔH = H(W) ⊕ H(W⊕δ). One number depending on W and δ.
Rayon view: ΔH = LINEAR(δ) ⊕ CARRY_NOISE(W)

WHY? Because in SHA-256 with fixed carries:
  - XOR operations: ΔH contribution depends ONLY on Δinput = δ (deterministic)
  - Carry-dependent: ΔH contribution depends on actual W (variable)

MEASUREMENT: for fixed δ, how much of ΔH is deterministic?
  If most bits are deterministic: collision is easier (fix δ to zero them).
  If most bits are noisy: collision is hard (random).
"""

import random
import time
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from carry_algebra_foundation import sha256_with_carries

M32 = 0xFFFFFFFF


def measure_decomposition(delta_W0, n_samples=5000):
    """
    For fixed δ in W[0], measure ΔH across many random W.

    If ΔH is the SAME for all W: that bit is deterministic (LINEAR).
    If ΔH varies across W: that bit is carry-dependent (NOISY).

    Returns: (n_deterministic_bits, n_noisy_bits, stability per bit)
    """
    # Collect ΔH for many random W
    dh_samples = []

    for _ in range(n_samples):
        W1 = [random.randint(0, M32) for _ in range(16)]
        W2 = list(W1)
        W2[0] ^= delta_W0

        H1, _, _ = sha256_with_carries(W1)
        H2, _, _ = sha256_with_carries(W2)

        # ΔH = H1 ⊕ H2 (per word)
        dH = tuple(H1[i] ^ H2[i] for i in range(8))
        dh_samples.append(dH)

    # Per bit: how stable is ΔH?
    # Stability = max(P(bit=0), P(bit=1)). 1.0 = deterministic. 0.5 = random.
    bit_stability = []
    for word in range(8):
        for bit in range(32):
            ones = sum(1 for dh in dh_samples if (dh[word] >> bit) & 1)
            p = ones / n_samples
            stab = max(p, 1 - p)
            bit_stability.append(stab)

    n_deterministic = sum(1 for s in bit_stability if s > 0.99)
    n_biased = sum(1 for s in bit_stability if 0.6 < s <= 0.99)
    n_noisy = sum(1 for s in bit_stability if s <= 0.6)

    avg_stability = sum(bit_stability) / len(bit_stability)

    return {
        'n_deterministic': n_deterministic,
        'n_biased': n_biased,
        'n_noisy': n_noisy,
        'avg_stability': avg_stability,
        'bit_stability': bit_stability,
        'n_samples': n_samples,
    }


if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  DIFFERENTIAL DECOMPOSITION — What Rayon math reveals    ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()
    print("  ΔH = LINEAR(δ) ⊕ CARRY_NOISE(W)")
    print("  Measuring: how many bits of ΔH are deterministic?")
    print()

    random.seed(42)

    # Test multiple δ values
    deltas = [
        (0x00000001, "LSB flip"),
        (0x80000000, "MSB flip"),
        (0x00000100, "byte boundary"),
        (0xFFFFFFFF, "all bits"),
        (0x55555555, "alternating"),
    ]

    print(f"  {'δ':>12} {'name':>15} {'determ':>7} {'biased':>7} {'noisy':>7} {'avg stab':>9}")
    print(f"  {'─'*62}")

    for delta, name in deltas:
        result = measure_decomposition(delta, n_samples=3000)
        print(f"  {delta:#010x} {name:>15} "
              f"{result['n_deterministic']:>7} {result['n_biased']:>7} "
              f"{result['n_noisy']:>7} {result['avg_stability']:>9.4f}")

    # Detailed analysis of best δ
    print()
    print("  DETAILED: δ = 0x80000000 (MSB flip)")
    print("  " + "─" * 50)

    result = measure_decomposition(0x80000000, n_samples=5000)

    print(f"    Deterministic bits (>99% stable): {result['n_deterministic']}/256")
    print(f"    Biased bits (60-99% stable):      {result['n_biased']}/256")
    print(f"    Noisy bits (≤60% stable):         {result['n_noisy']}/256")
    print()

    # Per-word stability
    print("    Per-word breakdown:")
    for word in range(8):
        word_bits = result['bit_stability'][word*32:(word+1)*32]
        det = sum(1 for s in word_bits if s > 0.99)
        avg = sum(word_bits) / 32
        print(f"      H[{word}]: {det:>2}/32 deterministic, avg stability {avg:.4f}")

    print(f"""
  ═══════════════════════════════════════════════════════
  DECOMPOSITION RESULTS:

    ΔH has TWO components:
      LINEAR(δ):      {result['n_deterministic']} bits (same for ALL W)
      CARRY_NOISE(W): {256 - result['n_deterministic']} bits (varies with W)

    For COLLISION (ΔH = 0):
      Step 1: Choose δ to zero the {result['n_deterministic']} deterministic bits
              → Linear system in δ, solvable by GF(2)
      Step 2: Find W where {256 - result['n_deterministic']} noisy bits = 0
              → Birthday on noisy space: 2^{(256 - result['n_deterministic'])//2}

    TOTAL COST: 2^{(256 - result['n_deterministic'])//2}
    vs Birthday: 2^128

    {'★ BETTER THAN BIRTHDAY!' if (256-result['n_deterministic'])//2 < 128 else 'Birthday still wins.'}
    {'  Saving: ' + str(128 - (256-result['n_deterministic'])//2) + ' bits' if (256-result['n_deterministic'])//2 < 128 else ''}
  ═══════════════════════════════════════════════════════
""")
