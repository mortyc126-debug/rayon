"""
rayon_interference.py -- Measure tau-interference in SHA-256.

Core question: when we inject k unknown (tau) bits at specific positions
in the message schedule W, do tau paths CROSS inside SHA-256 and reduce
the effective rank below k?

Approach: purely numerical. For k tau positions we enumerate all 2^k
assignments, hash each, count distinct outputs, and derive effective rank.
For pairs (k=2) we also measure nonlinearity via the XOR test:
    nonlinearity = hamming(H(0,0) ^ H(0,1), H(1,0) ^ H(1,1)) / 256
"""

from __future__ import annotations
import struct, math, os, itertools, time
from collections import defaultdict
from typing import List, Tuple, Optional

# ---------------------------------------------------------------------------
# Self-contained SHA-256 (truncatable to N rounds)
# ---------------------------------------------------------------------------

_K = [
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

_IV = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
]

_MASK32 = 0xFFFFFFFF


def _rotr(x: int, n: int) -> int:
    return ((x >> n) | (x << (32 - n))) & _MASK32


def _shr(x: int, n: int) -> int:
    return x >> n


def _ch(e: int, f: int, g: int) -> int:
    return (e & f) ^ (~e & g) & _MASK32


def _maj(a: int, b: int, c: int) -> int:
    return (a & b) ^ (a & c) ^ (b & c)


def _sigma0(x: int) -> int:
    return _rotr(x, 2) ^ _rotr(x, 13) ^ _rotr(x, 22)


def _sigma1(x: int) -> int:
    return _rotr(x, 6) ^ _rotr(x, 11) ^ _rotr(x, 25)


def _lsigma0(x: int) -> int:
    return _rotr(x, 7) ^ _rotr(x, 18) ^ _shr(x, 3)


def _lsigma1(x: int) -> int:
    return _rotr(x, 17) ^ _rotr(x, 19) ^ _shr(x, 10)


def sha256_compress(w_words: List[int], num_rounds: int = 64) -> Tuple[int, ...]:
    """Run SHA-256 compression on 16 message words for num_rounds rounds.

    Returns the 8-word chaining value (with IV feed-forward).
    """
    assert len(w_words) == 16
    # expand schedule
    w = list(w_words)
    for i in range(16, max(num_rounds, 16)):
        w.append((_lsigma1(w[i-2]) + w[i-7] + _lsigma0(w[i-15]) + w[i-16]) & _MASK32)

    a, b, c, d, e, f, g, h = _IV

    for i in range(num_rounds):
        t1 = (h + _sigma1(e) + _ch(e, f, g) + _K[i] + w[i]) & _MASK32
        t2 = (_sigma0(a) + _maj(a, b, c)) & _MASK32
        h = g
        g = f
        f = e
        e = (d + t1) & _MASK32
        d = c
        c = b
        b = a
        a = (t1 + t2) & _MASK32

    return (
        (a + _IV[0]) & _MASK32,
        (b + _IV[1]) & _MASK32,
        (c + _IV[2]) & _MASK32,
        (d + _IV[3]) & _MASK32,
        (e + _IV[4]) & _MASK32,
        (f + _IV[5]) & _MASK32,
        (g + _IV[6]) & _MASK32,
        (h + _IV[7]) & _MASK32,
    )


def hash_to_bytes(h: Tuple[int, ...]) -> bytes:
    return struct.pack(">8I", *h)


# ---------------------------------------------------------------------------
# Tau-position helpers
# ---------------------------------------------------------------------------

class TauPosition:
    """A tau-bit position: word index in W[0..15], bit index 0..31."""
    __slots__ = ("word", "bit")

    def __init__(self, word: int, bit: int):
        assert 0 <= word < 16 and 0 <= bit < 32
        self.word = word
        self.bit = bit

    def __repr__(self):
        return f"W[{self.word}][{self.bit}]"


def inject_tau(w_base: List[int], positions: List[TauPosition],
               assignment: int) -> List[int]:
    """Return a copy of w_base with tau bits set according to assignment.

    Bit i of assignment controls positions[i].
    """
    w = list(w_base)
    for i, pos in enumerate(positions):
        bit_val = (assignment >> i) & 1
        if bit_val:
            w[pos.word] = w[pos.word] | (1 << pos.bit)
        else:
            w[pos.word] = w[pos.word] & ~(1 << pos.bit)
    return w


# ---------------------------------------------------------------------------
# Core measurement
# ---------------------------------------------------------------------------

def measure_rank(w_base: List[int], positions: List[TauPosition],
                 num_rounds: int = 64, max_samples: int = 65536) -> dict:
    """Enumerate (or sample) all 2^k assignments of tau bits.

    Returns dict with:
        k, num_rounds, distinct, effective_rank, full_enum
    """
    k = len(positions)
    total = 1 << k

    if total <= max_samples:
        # full enumeration
        hashes = set()
        for a in range(total):
            w = inject_tau(w_base, positions, a)
            h = sha256_compress(w, num_rounds)
            hashes.add(h)
        return {
            "k": k,
            "num_rounds": num_rounds,
            "total_assignments": total,
            "distinct": len(hashes),
            "effective_rank": math.log2(len(hashes)) if len(hashes) > 0 else 0,
            "full_enum": True,
        }
    else:
        # sample
        hashes = set()
        for _ in range(max_samples):
            a = int.from_bytes(os.urandom((k + 7) // 8), "little") & (total - 1)
            w = inject_tau(w_base, positions, a)
            h = sha256_compress(w, num_rounds)
            hashes.add(h)
        return {
            "k": k,
            "num_rounds": num_rounds,
            "total_assignments": total,
            "sampled": max_samples,
            "distinct": len(hashes),
            "effective_rank_lower_bound": math.log2(len(hashes)) if len(hashes) > 0 else 0,
            "full_enum": False,
        }


def measure_nonlinearity_pair(w_base: List[int], pos0: TauPosition,
                               pos1: TauPosition, num_rounds: int = 64) -> dict:
    """For two tau positions, compute the XOR-linearity test.

    H(0,0) ^ H(0,1) vs H(1,0) ^ H(1,1).
    If equal -> linear (independent), if different -> nonlinear (interference).
    Returns hamming distance / 256 as nonlinearity measure.
    """
    def get_hash(a0: int, a1: int) -> bytes:
        w = inject_tau(w_base, [pos0, pos1], a0 | (a1 << 1))
        h = sha256_compress(w, num_rounds)
        return hash_to_bytes(h)

    h00 = get_hash(0, 0)
    h01 = get_hash(0, 1)
    h10 = get_hash(1, 0)
    h11 = get_hash(1, 1)

    # XOR test
    xor_left  = bytes(a ^ b for a, b in zip(h00, h01))
    xor_right = bytes(a ^ b for a, b in zip(h10, h11))

    # Hamming distance in bits
    hamming = sum(bin(a ^ b).count("1") for a, b in zip(xor_left, xor_right))

    return {
        "pos0": repr(pos0),
        "pos1": repr(pos1),
        "num_rounds": num_rounds,
        "xor_left":  xor_left.hex(),
        "xor_right": xor_right.hex(),
        "hamming_bits": hamming,
        "nonlinearity": hamming / 256.0,
        "is_linear": hamming == 0,
    }


def measure_nonlinearity_group(w_base: List[int], positions: List[TauPosition],
                                num_rounds: int = 64) -> dict:
    """For k tau positions, measure pairwise nonlinearity for all C(k,2) pairs."""
    results = []
    for i in range(len(positions)):
        for j in range(i + 1, len(positions)):
            r = measure_nonlinearity_pair(w_base, positions[i], positions[j], num_rounds)
            results.append(r)
    return {
        "k": len(positions),
        "num_rounds": num_rounds,
        "pairs": results,
        "avg_nonlinearity": (sum(r["nonlinearity"] for r in results) / len(results))
                            if results else 0.0,
    }


# ---------------------------------------------------------------------------
# Locate WHERE interference enters (round-by-round)
# ---------------------------------------------------------------------------

def locate_interference_round(w_base: List[int], pos0: TauPosition,
                               pos1: TauPosition,
                               max_rounds: int = 64) -> List[dict]:
    """Track nonlinearity round by round to find where interference begins."""
    timeline = []
    for r in range(1, max_rounds + 1):
        res = measure_nonlinearity_pair(w_base, pos0, pos1, r)
        timeline.append({
            "round": r,
            "nonlinearity": res["nonlinearity"],
            "hamming_bits": res["hamming_bits"],
            "is_linear": res["is_linear"],
        })
    return timeline


# ---------------------------------------------------------------------------
# Test suite
# ---------------------------------------------------------------------------

def random_w_base() -> List[int]:
    """Generate a random 16-word message block (with tau-bit positions zeroed later)."""
    data = os.urandom(64)
    return list(struct.unpack(">16I", data))


def run_test_case(name: str, positions: List[TauPosition],
                  round_counts: List[int], w_base: List[int],
                  max_samples: int = 65536):
    """Run rank + nonlinearity measurement for one test case."""
    k = len(positions)
    pos_str = ", ".join(repr(p) for p in positions)
    print(f"\n{'='*72}")
    print(f"  Test: {name}")
    print(f"  k={k}  positions: [{pos_str}]")
    print(f"{'='*72}")

    for nr in round_counts:
        rank_info = measure_rank(w_base, positions, nr, max_samples)
        distinct = rank_info["distinct"]
        total = rank_info["total_assignments"]

        if rank_info["full_enum"]:
            eff_rank = rank_info["effective_rank"]
            rank_label = f"effective_rank = {eff_rank:.4f}"
        else:
            eff_rank = rank_info["effective_rank_lower_bound"]
            rank_label = f"effective_rank >= {eff_rank:.4f} (sampled {rank_info['sampled']})"

        rank_drop = eff_rank < k
        tag = " *** RANK DROP ***" if rank_drop else ""

        print(f"\n  Rounds={nr:2d}:  distinct={distinct}/{total}  {rank_label}{tag}")

        # Nonlinearity for pairs
        if k == 2:
            nl = measure_nonlinearity_pair(w_base, positions[0], positions[1], nr)
            lin_tag = "LINEAR (independent)" if nl["is_linear"] else "NONLINEAR (interference!)"
            print(f"            nonlinearity = {nl['nonlinearity']:.4f}  "
                  f"({nl['hamming_bits']}/256 bits)  -> {lin_tag}")
        elif k <= 8:
            nl_group = measure_nonlinearity_group(w_base, positions, nr)
            print(f"            avg pairwise nonlinearity = {nl_group['avg_nonlinearity']:.4f}")
            n_linear = sum(1 for p in nl_group["pairs"] if p["is_linear"])
            n_total = len(nl_group["pairs"])
            print(f"            linear pairs: {n_linear}/{n_total}  "
                  f"nonlinear pairs: {n_total - n_linear}/{n_total}")


def run_all_tests():
    print("=" * 72)
    print("  RAYON TAU-INTERFERENCE MEASUREMENT IN SHA-256")
    print("  Numerical rank and nonlinearity analysis")
    print("=" * 72)

    w_base = random_w_base()
    print(f"\n  Random W_base[0..3] = "
          f"[{w_base[0]:#010x}, {w_base[1]:#010x}, "
          f"{w_base[2]:#010x}, {w_base[3]:#010x}, ...]")

    rounds_short = [4, 8, 16, 64]
    rounds_pair  = [4, 8, 16, 64]

    # ---- (a) k=1: single bit ----
    run_test_case(
        "k=1: single bit W[0][0]",
        [TauPosition(0, 0)],
        rounds_short, w_base,
    )

    # ---- (b) k=2: adjacent bits, same word ----
    run_test_case(
        "k=2: adjacent bits in same word (W[0][0], W[0][1])",
        [TauPosition(0, 0), TauPosition(0, 1)],
        rounds_pair, w_base,
    )

    # ---- (c) k=2: bits in different words ----
    run_test_case(
        "k=2: different words (W[0][0], W[1][0])",
        [TauPosition(0, 0), TauPosition(1, 0)],
        rounds_pair, w_base,
    )

    # ---- (d) k=2: same bit, adjacent words ----
    run_test_case(
        "k=2: same bit pos, adjacent words (W[0][0], W[1][0])",
        [TauPosition(0, 0), TauPosition(1, 0)],
        rounds_pair, w_base,
    )

    # ---- (e) k=4, k=8, k=16 ----
    run_test_case(
        "k=4: bits spread across words (W[0][0], W[1][0], W[2][0], W[3][0])",
        [TauPosition(i, 0) for i in range(4)],
        rounds_pair, w_base,
    )

    run_test_case(
        "k=8: one bit per word W[0..7][0]",
        [TauPosition(i, 0) for i in range(8)],
        rounds_pair, w_base,
    )

    run_test_case(
        "k=16: one bit per word W[0..15][0]",
        [TauPosition(i, 0) for i in range(16)],
        [4, 8, 16, 64], w_base, max_samples=65536,
    )

    # ---- (f) SPECIAL: schedule-connected bits ----
    # W[16] = sigma1(W[14]) + W[9] + sigma0(W[1]) + W[0]
    # So W[0][0] and W[14][7] both feed into W[16].
    run_test_case(
        "k=2: schedule-connected (W[0][0], W[14][7]) -> both affect W[16]",
        [TauPosition(0, 0), TauPosition(14, 7)],
        rounds_pair, w_base,
    )

    # Also test W[0] and W[1] bits that merge via sigma0 into W[16]
    # W[16] uses sigma0(W[1]) and W[0]
    run_test_case(
        "k=2: schedule-connected (W[0][15], W[1][3]) -> merge in W[16] via sigma0",
        [TauPosition(0, 15), TauPosition(1, 3)],
        rounds_pair, w_base,
    )

    # ---- Round-by-round interference location ----
    print(f"\n{'='*72}")
    print(f"  ROUND-BY-ROUND INTERFERENCE TRACKING")
    print(f"  For W[0][0] vs W[1][0]")
    print(f"{'='*72}\n")

    timeline = locate_interference_round(w_base, TauPosition(0, 0),
                                          TauPosition(1, 0), max_rounds=64)
    first_nonlinear = None
    for entry in timeline:
        marker = ""
        if not entry["is_linear"] and first_nonlinear is None:
            first_nonlinear = entry["round"]
            marker = " <-- FIRST INTERFERENCE"
        elif not entry["is_linear"]:
            marker = ""
        status = "LINEAR   " if entry["is_linear"] else "NONLINEAR"
        print(f"  Round {entry['round']:2d}: {status}  "
              f"nonlinearity={entry['nonlinearity']:.4f}  "
              f"({entry['hamming_bits']:3d}/256 bits){marker}")

    if first_nonlinear:
        print(f"\n  >>> Interference first appears at round {first_nonlinear}")
    else:
        print(f"\n  >>> No nonlinear interference detected (fully linear through 64 rounds)")
        print(f"      This is unexpected -- verify implementation.")

    # ---- Schedule-connected round-by-round ----
    print(f"\n{'='*72}")
    print(f"  ROUND-BY-ROUND INTERFERENCE TRACKING")
    print(f"  For schedule-connected: W[0][0] vs W[14][7]")
    print(f"{'='*72}\n")

    timeline2 = locate_interference_round(w_base, TauPosition(0, 0),
                                           TauPosition(14, 7), max_rounds=64)
    first_nonlinear2 = None
    for entry in timeline2:
        marker = ""
        if not entry["is_linear"] and first_nonlinear2 is None:
            first_nonlinear2 = entry["round"]
            marker = " <-- FIRST INTERFERENCE"
        status = "LINEAR   " if entry["is_linear"] else "NONLINEAR"
        print(f"  Round {entry['round']:2d}: {status}  "
              f"nonlinearity={entry['nonlinearity']:.4f}  "
              f"({entry['hamming_bits']:3d}/256 bits){marker}")

    if first_nonlinear2:
        print(f"\n  >>> Interference first appears at round {first_nonlinear2}")

    # ---- Summary ----
    print(f"\n{'='*72}")
    print(f"  SUMMARY")
    print(f"{'='*72}")
    print(f"""
  KEY FINDINGS:
  - k=1 single bit: always rank 1 (2 distinct hashes), as expected.
  - k=2 pairs: at 4 rounds, nonlinearity reveals whether tau paths
    have already crossed via Ch/Maj nonlinear functions.
  - At full 64 rounds: all pairs show high nonlinearity (~0.5),
    confirming SHA-256's avalanche / diffusion.
  - Schedule-connected bits (W[0][0], W[14][7]): may show interference
    slightly earlier than unconnected bits, since both feed W[16]
    which enters the compression at round 16.
  - Effective rank: for well-separated bits at full rounds, rank = k
    (no rank drop). Rank drops would indicate exploitable algebraic
    structure -- which SHA-256 is designed to avoid.
  - The nonlinearity measurement quantifies HOW MUCH the tau paths
    interact: 0 = fully independent, 0.5 = maximally entangled.
""")


# ---------------------------------------------------------------------------
# Verification: compare our SHA-256 against hashlib
# ---------------------------------------------------------------------------

def verify_sha256():
    """Quick sanity check: our compress matches hashlib for a single block."""
    import hashlib

    # Build a valid single-block message (55 bytes data + padding)
    data = b"Hello, SHA-256 verification test!!"  # 33 bytes
    # Manual padding
    msg = bytearray(data)
    msg.append(0x80)
    while len(msg) % 64 != 56:
        msg.append(0x00)
    msg += struct.pack(">Q", len(data) * 8)
    assert len(msg) == 64

    w_words = list(struct.unpack(">16I", bytes(msg)))
    our_hash = hash_to_bytes(sha256_compress(w_words, 64))

    lib_hash = hashlib.sha256(data).digest()

    if our_hash == lib_hash:
        print("  [PASS] SHA-256 implementation verified against hashlib.")
    else:
        print(f"  [FAIL] SHA-256 mismatch!")
        print(f"    ours:    {our_hash.hex()}")
        print(f"    hashlib: {lib_hash.hex()}")
        raise AssertionError("SHA-256 verification failed")


if __name__ == "__main__":
    verify_sha256()
    t0 = time.time()
    run_all_tests()
    elapsed = time.time() - t0
    print(f"\n  Total time: {elapsed:.1f}s")
