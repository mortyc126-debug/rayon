"""
PARTITION GEOMETRY — Mathematics that sees THROUGH SHA-256.

Not inside SHA-256 (rounds, carries, schedule).
OUTSIDE: the geometry of how SHA-256 partitions input space.

f: {0,1}^512 → {0,1}^256 creates partition Π = {f⁻¹(h) : h ∈ outputs}

Each fiber f⁻¹(h) is a subset of {0,1}^512 containing ≈ 2^256 elements.
Collision = two elements in same fiber.

NEW OBJECT: PARTITION TENSOR P(S)
  For set S ⊆ {input bits}:
  P(S) = Pr[H(W₁) = H(W₂) | W₁ and W₂ agree on bits in S, random elsewhere]

  Random oracle: P(S) = 2^{-m} for all S (no structure)
  SHA-256: P(S) ≠ 2^{-m} for some S → THOSE ARE THE WEAK DIRECTIONS

Method: use reduced SHA-256 (8-bit output) to make P(S) measurable.
Then check if structure scales to full SHA-256.
"""

import numpy as np
import time
from carry_algebra_foundation import sha256_with_carries, M32


def sha256_reduced(W_words, output_bits=8):
    """SHA-256 with truncated output (for partition geometry study)."""
    H, _, _ = sha256_with_carries(W_words)
    # Take lowest output_bits from H[7]
    return H[7] & ((1 << output_bits) - 1)


def partition_tensor_1d(bit_idx, n_samples=100000, output_bits=8):
    """
    Measure P({bit_idx}): collision probability when bit_idx is shared.

    Method: generate pairs (W₁, W₂) that agree on bit bit_idx,
    random elsewhere. Measure collision rate.

    Compare to baseline 2^{-output_bits}.
    """
    word, bit = bit_idx // 32, bit_idx % 32

    collisions = 0
    for _ in range(n_samples):
        # Random W₁
        W1 = [np.random.randint(0, 2**32) for _ in range(16)]
        # W₂ agrees on bit (word, bit), random elsewhere
        W2 = [np.random.randint(0, 2**32) for _ in range(16)]
        # Force agreement on the specified bit
        if (W1[word] >> bit) & 1:
            W2[word] |= (1 << bit)
        else:
            W2[word] &= ~(1 << bit)

        h1 = sha256_reduced(W1, output_bits)
        h2 = sha256_reduced(W2, output_bits)

        if h1 == h2:
            collisions += 1

    return collisions / n_samples


def partition_tensor_set(bit_set, n_samples=50000, output_bits=8):
    """
    P(S): collision prob when ALL bits in S are shared.
    """
    collisions = 0
    for _ in range(n_samples):
        W1 = [np.random.randint(0, 2**32) for _ in range(16)]
        W2 = [np.random.randint(0, 2**32) for _ in range(16)]

        # Force agreement on all bits in set
        for bit_idx in bit_set:
            word, bit = bit_idx // 32, bit_idx % 32
            if (W1[word] >> bit) & 1:
                W2[word] |= (1 << bit)
            else:
                W2[word] &= ~(1 << bit)

        h1 = sha256_reduced(W1, output_bits)
        h2 = sha256_reduced(W2, output_bits)
        if h1 == h2:
            collisions += 1

    return collisions / n_samples


def fiber_geometry(output_bits=8, n_samples=50000):
    """
    Study the SHAPE of fibers for reduced SHA-256.

    For each hash value h: collect inputs W with SHA(W) mod 2^bits = h.
    Measure: are inputs CLUSTERED or uniformly spread?
    """
    # Collect samples grouped by hash
    fibers = {}
    for _ in range(n_samples):
        W = [np.random.randint(0, 2**32) for _ in range(16)]
        h = sha256_reduced(W, output_bits)
        if h not in fibers:
            fibers[h] = []
        if len(fibers[h]) < 200:  # cap per fiber
            # Store only W[0] for simplicity (32 bits)
            fibers[h].append(W[0])

    # Measure intra-fiber distances
    distances = []
    for h, members in fibers.items():
        if len(members) < 10:
            continue
        for i in range(min(50, len(members))):
            for j in range(i+1, min(50, len(members))):
                d = bin(members[i] ^ members[j]).count('1')
                distances.append(d)

    return fibers, distances


# ════════════════════════════════════════════════════════════
if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  PARTITION GEOMETRY — Seeing through SHA-256             ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    output_bits = 8
    baseline = 1.0 / (1 << output_bits)  # 1/256 for 8-bit
    print(f"Reduced SHA-256: {output_bits}-bit output")
    print(f"Baseline collision prob: {baseline:.6f} = 2^{{-{output_bits}}}")
    print()

    # ─── PARTITION TENSOR: 1D ───
    print("PARTITION TENSOR P({{bit}}): single-bit collision bias")
    print("─" * 60)
    print(f"{'bit':>6} {'word':>6} {'P(bit)':>10} {'ratio':>8} {'bias':>10}")
    print("─" * 45)

    biases = []
    # Sample bits from each word
    test_bits = []
    for word in range(16):
        for bit in [0, 15, 31]:  # low, mid, high bit of each word
            test_bits.append(word * 32 + bit)

    for bit_idx in test_bits:
        word, bit = bit_idx // 32, bit_idx % 32
        t0 = time.time()
        p = partition_tensor_1d(bit_idx, n_samples=30000, output_bits=output_bits)
        ratio = p / baseline
        bias = p - baseline
        biases.append((bit_idx, word, bit, p, ratio, bias))

        if ratio > 1.05 or ratio < 0.95 or bit == 0:
            marker = " ★" if abs(ratio - 1) > 0.05 else ""
            print(f"  {bit_idx:>4}  W[{word:>2}][{bit:>2}] {p:>10.6f} {ratio:>8.4f} {bias:>+10.6f}{marker}")

    # Top biases
    biases.sort(key=lambda x: -abs(x[5]))
    print(f"\n  TOP BIASES (most non-random):")
    for idx, word, bit, p, ratio, bias in biases[:5]:
        print(f"    W[{word}][{bit}]: ratio = {ratio:.4f} (bias = {bias:+.6f})")

    # ─── PARTITION TENSOR: multi-bit ───
    print(f"\nPARTITION TENSOR P(S): multi-bit sets")
    print("─" * 60)

    # Test: sharing entire words vs random bits
    tests = [
        ("W[0] (32 bits)", list(range(0, 32))),
        ("W[0][0:8] (8 bits)", list(range(0, 8))),
        ("W[0]+W[1] (64 bits)", list(range(0, 64))),
        ("W[0..3] (128 bits)", list(range(0, 128))),
        ("W[0..7] (256 bits)", list(range(0, 256))),
        ("random 32 bits", list(np.random.choice(512, 32, replace=False))),
        ("random 64 bits", list(np.random.choice(512, 64, replace=False))),
        ("random 128 bits", list(np.random.choice(512, 128, replace=False))),
    ]

    print(f"  {'Set':>25} {'|S|':>5} {'P(S)':>10} {'ratio':>8} {'2^x':>8}")
    print("  " + "─" * 58)
    for name, bit_set in tests:
        p = partition_tensor_set(bit_set, n_samples=20000, output_bits=output_bits)
        ratio = p / baseline
        log_ratio = np.log2(ratio) if ratio > 0 else -999
        print(f"  {name:>25} {len(bit_set):>5} {p:>10.6f} {ratio:>8.4f} {log_ratio:>+7.2f}")

    # ─── FIBER GEOMETRY ───
    print(f"\nFIBER GEOMETRY (shape of hash classes)")
    print("─" * 60)
    fibers, distances = fiber_geometry(output_bits=output_bits, n_samples=50000)

    filled = sum(1 for h, m in fibers.items() if len(m) >= 10)
    print(f"  Fibers with ≥10 samples: {filled}/{1 << output_bits}")

    if distances:
        print(f"  Intra-fiber Hamming distances (W[0] only, 32 bits):")
        print(f"    Mean: {np.mean(distances):.2f}")
        print(f"    Expected (random): 16.00")
        print(f"    Std:  {np.std(distances):.2f}")
        print(f"    Min:  {min(distances)}")
        print(f"    Bias: {np.mean(distances) - 16:.4f}")

        bias_val = np.mean(distances) - 16
        if abs(bias_val) > 0.1:
            print(f"    ★ FIBER GEOMETRY IS NON-RANDOM! Bias = {bias_val:.4f}")
        else:
            print(f"    Fiber geometry consistent with random")

    print(f"""
═══════════════════════════════════════════════════════════════
PARTITION GEOMETRY SUMMARY:

  PARTITION TENSOR P(S):
    Measures collision probability when inputs share bits S.
    Random oracle: P(S) = 2^{{-m}} for all S.
    SHA-256: P(S) ≈ 2^{{-m}} × ratio(S).

  If ratio(S) >> 1 for some S: S defines a COLLISION-PRONE direction.
  Fixing bits in S and randomizing the rest produces MORE collisions
  than expected. This means fibers are ALIGNED with S.

  FIBER GEOMETRY:
    Intra-fiber distance measures whether fiber elements are
    clustered or random. Mean distance ≠ 16 → non-random structure.

  THIS IS EXTERNAL MATHEMATICS:
    No reference to rounds, carries, schedule, or SHA internals.
    Pure input-output geometry of the partition function.
    If structure exists: it reveals WHERE collisions hide,
    regardless of how SHA-256 computes them internally.
═══════════════════════════════════════════════════════════════
""")
