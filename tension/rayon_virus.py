"""
rayon_virus.py -- Tagged Bit Tracing Through SHA-256 ("?-virus")

Each unknown bit gets a UNIQUE TAG identifying which original input bit
(word_idx, bit_idx) it came from. As bits propagate through SHA-256,
tags propagate with them via union. This lets us trace exactly which
input bits influence each output bit -- the "viral spread" of unknowns.

Core insight: if an output bit carries fewer than 512 tags after full
SHA-256, it depends on fewer inputs than expected. Those are weak points.
"""

from __future__ import annotations
import time
from collections import Counter

# ── SHA-256 constants ────────────────────────────────────────────────

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

IV = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
]

EMPTY = frozenset()


# ── TaggedBit ────────────────────────────────────────────────────────

class TaggedBit:
    """A bit that is 0, 1, or '?' with a frozenset of origin tags."""

    __slots__ = ('val', 'tags')

    def __init__(self, val, tags=EMPTY):
        self.val = val  # 0, 1, or '?'
        self.tags = tags

    def is_known(self):
        return self.val != '?'

    def __repr__(self):
        if self.val != '?':
            return f'{self.val}'
        return f'?[{len(self.tags)}]'


# Known constants -- reuse these to avoid allocations
ZERO = TaggedBit(0, EMPTY)
ONE  = TaggedBit(1, EMPTY)


def tb_not(a: TaggedBit) -> TaggedBit:
    if a.val == 0:
        return ONE
    if a.val == 1:
        return ZERO
    return TaggedBit('?', a.tags)


def tb_and(a: TaggedBit, b: TaggedBit) -> TaggedBit:
    # AND with known 0 kills everything
    if a.val == 0 or b.val == 0:
        return ZERO
    # AND(1, x) = x
    if a.val == 1:
        return b
    if b.val == 1:
        return a
    # Both are '?' -- tags merge
    return TaggedBit('?', a.tags | b.tags)


def tb_xor(a: TaggedBit, b: TaggedBit) -> TaggedBit:
    # XOR with known 0 = identity
    if a.val == 0:
        return b
    if b.val == 0:
        return a
    # XOR(1, x) = NOT(x)
    if a.val == 1:
        return tb_not(b)
    if b.val == 1:
        return tb_not(a)
    # Both '?'
    # If identical tag sets, XOR might cancel -- but we cannot know the
    # actual values, so result is still '?'. However, mark interference.
    merged = a.tags | b.tags
    return TaggedBit('?', merged)


def tb_or(a: TaggedBit, b: TaggedBit) -> TaggedBit:
    if a.val == 1 or b.val == 1:
        return ONE
    if a.val == 0:
        return b
    if b.val == 0:
        return a
    return TaggedBit('?', a.tags | b.tags)


def tb_maj(a: TaggedBit, b: TaggedBit, c: TaggedBit) -> TaggedBit:
    """Majority function: (a AND b) XOR (a AND c) XOR (b AND c)."""
    return tb_xor(tb_xor(tb_and(a, b), tb_and(a, c)), tb_and(b, c))


def tb_ch(e: TaggedBit, f: TaggedBit, g: TaggedBit) -> TaggedBit:
    """Choice function: (e AND f) XOR (NOT e AND g)."""
    return tb_xor(tb_and(e, f), tb_and(tb_not(e), g))


# ── 32-bit word operations using TaggedBit[32] ──────────────────────

def make_word_known(val: int) -> list:
    """Create a 32-bit word from a known integer. Bit 0 = MSB."""
    return [TaggedBit((val >> (31 - i)) & 1, EMPTY) for i in range(32)]


def make_word_tagged(word_idx: int) -> list:
    """Create a 32-bit word where every bit is '?' with unique tag."""
    return [TaggedBit('?', frozenset({(word_idx, i)})) for i in range(32)]


def word_rotr(w: list, n: int) -> list:
    """Right-rotate a 32-bit word by n positions."""
    return w[-n:] + w[:-n]


def word_shr(w: list, n: int) -> list:
    """Right-shift a 32-bit word by n positions (fill with 0)."""
    return [ZERO] * n + w[:32 - n]


def word_xor(a: list, b: list) -> list:
    return [tb_xor(a[i], b[i]) for i in range(32)]


def word_and(a: list, b: list) -> list:
    return [tb_and(a[i], b[i]) for i in range(32)]


def word_not(a: list) -> list:
    return [tb_not(a[i]) for i in range(32)]


def word_add(a: list, b: list) -> list:
    """32-bit addition with carry propagation. Bit 31 = LSB."""
    result = [None] * 32
    carry = ZERO
    for i in range(31, -1, -1):  # LSB to MSB
        # sum = a[i] XOR b[i] XOR carry
        s1 = tb_xor(a[i], b[i])
        result[i] = tb_xor(s1, carry)
        # carry = (a[i] AND b[i]) OR (a[i] AND carry) OR (b[i] AND carry)
        c1 = tb_and(a[i], b[i])
        c2 = tb_and(a[i], carry)
        c3 = tb_and(b[i], carry)
        carry = tb_or(tb_or(c1, c2), c3)
    return result


def word_add_multi(*words) -> list:
    """Add multiple 32-bit words."""
    result = words[0]
    for w in words[1:]:
        result = word_add(result, w)
    return result


# ── SHA-256 functions ────────────────────────────────────────────────

def sigma0(w: list) -> list:
    """Lowercase sigma_0: ROTR(7) XOR ROTR(18) XOR SHR(3)."""
    return word_xor(word_xor(word_rotr(w, 7), word_rotr(w, 18)), word_shr(w, 3))


def sigma1(w: list) -> list:
    """Lowercase sigma_1: ROTR(17) XOR ROTR(19) XOR SHR(10)."""
    return word_xor(word_xor(word_rotr(w, 17), word_rotr(w, 19)), word_shr(w, 10))


def big_sigma0(w: list) -> list:
    """Uppercase Sigma_0: ROTR(2) XOR ROTR(13) XOR ROTR(22)."""
    return word_xor(word_xor(word_rotr(w, 2), word_rotr(w, 13)), word_rotr(w, 22))


def big_sigma1(w: list) -> list:
    """Uppercase Sigma_1: ROTR(6) XOR ROTR(11) XOR ROTR(25)."""
    return word_xor(word_xor(word_rotr(w, 6), word_rotr(w, 11)), word_rotr(w, 25))


def ch_word(e: list, f: list, g: list) -> list:
    return [tb_ch(e[i], f[i], g[i]) for i in range(32)]


def maj_word(a: list, b: list, c: list) -> list:
    return [tb_maj(a[i], b[i], c[i]) for i in range(32)]


# ── Message schedule ─────────────────────────────────────────────────

def message_schedule(W: list) -> list:
    """Expand 16 words to 64 words. W is list of 16 x 32-bit TaggedBit words."""
    assert len(W) == 16
    Ws = list(W)
    for i in range(16, 64):
        s0 = sigma0(Ws[i - 15])
        s1 = sigma1(Ws[i - 2])
        Ws.append(word_add_multi(Ws[i - 16], s0, Ws[i - 7], s1))
    return Ws


# ── SHA-256 compression ─────────────────────────────────────────────

def sha256_compress(W_expanded: list, num_rounds: int = 64) -> list:
    """
    Run SHA-256 compression for num_rounds rounds.
    W_expanded: list of 64 words (each 32 TaggedBits).
    Returns 8 words (256 bits) of output state.
    """
    # Initialize working variables from IV
    state = [make_word_known(iv) for iv in IV]
    a, b, c, d, e, f, g, h = state

    for r in range(min(num_rounds, 64)):
        k_word = make_word_known(K256[r])

        # T1 = h + Sigma1(e) + Ch(e,f,g) + K[r] + W[r]
        t1 = word_add_multi(h, big_sigma1(e), ch_word(e, f, g), k_word, W_expanded[r])

        # T2 = Sigma0(a) + Maj(a,b,c)
        t2 = word_add(big_sigma0(a), maj_word(a, b, c))

        # Update
        h = g
        g = f
        f = e
        e = word_add(d, t1)
        d = c
        c = b
        b = a
        a = word_add(t1, t2)

    # Add IV back
    iv_words = [make_word_known(iv) for iv in IV]
    output = [
        word_add(a, iv_words[0]),
        word_add(b, iv_words[1]),
        word_add(c, iv_words[2]),
        word_add(d, iv_words[3]),
        word_add(e, iv_words[4]),
        word_add(f, iv_words[5]),
        word_add(g, iv_words[6]),
        word_add(h, iv_words[7]),
    ]
    return output


# ── Analysis ─────────────────────────────────────────────────────────

def analyze_output(output_words: list, total_tagged: int, label: str = ""):
    """Analyze tag density and structure in output bits."""
    all_tags = []
    all_tag_sets = []
    for wi, word in enumerate(output_words):
        for bi, bit in enumerate(word):
            n = len(bit.tags)
            all_tags.append(n)
            all_tag_sets.append(bit.tags)

    total_bits = len(all_tags)
    avg_density = sum(all_tags) / total_bits if total_bits else 0
    min_tags = min(all_tags)
    max_tags = max(all_tags)
    known_count = sum(1 for t in all_tags if t == 0)
    unknown_count = total_bits - known_count

    # Tag overlap: count how many distinct tag sets exist
    unique_sets = len(set(id(s) for s in all_tag_sets))  # rough -- use actual set comparison below
    frozen_sets = [s for s in all_tag_sets if len(s) > 0]
    # For overlap, group identical tag sets
    set_to_count = Counter()
    for s in frozen_sets:
        set_to_count[s] += 1
    duplicated = sum(c for c in set_to_count.values() if c > 1)
    unique_nonempty = len(set_to_count)

    print(f"\n{'=' * 64}")
    if label:
        print(f"  {label}")
        print(f"{'=' * 64}")
    print(f"  Output bits:       {total_bits}")
    print(f"  Known (tags=0):    {known_count}")
    print(f"  Unknown (tags>0):  {unknown_count}")
    print(f"  Tag density (avg): {avg_density:.1f} / {total_tagged}")
    print(f"  Tag count (min):   {min_tags}")
    print(f"  Tag count (max):   {max_tags}")
    print(f"  Unique tag sets:   {unique_nonempty}")
    print(f"  Overlapping bits:  {duplicated} (share a tag set with another bit)")

    # Distribution histogram
    buckets = [0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]
    print(f"\n  Tag count distribution:")
    for i in range(len(buckets) - 1):
        lo, hi = buckets[i], buckets[i + 1]
        cnt = sum(1 for t in all_tags if lo <= t < hi)
        if cnt > 0:
            bar = '#' * min(cnt, 50)
            print(f"    [{lo:4d},{hi:4d})  {cnt:4d}  {bar}")
    cnt = sum(1 for t in all_tags if t >= buckets[-1])
    if cnt > 0:
        bar = '#' * min(cnt, 50)
        print(f"    [{buckets[-1]:4d},  +)  {cnt:4d}  {bar}")

    # Find weakest output bits (fewest tags, excluding known)
    weak = [(i, all_tags[i]) for i in range(total_bits) if all_tags[i] > 0]
    weak.sort(key=lambda x: x[1])
    if weak:
        print(f"\n  Weakest output bits (fewest tags, top 10):")
        for idx, ntags in weak[:10]:
            wi = idx // 32
            bi = idx % 32
            print(f"    output word {wi} bit {bi:2d}:  {ntags} tags")

    # Patient zero: which input tags appear in the MOST output bits?
    tag_reach = Counter()
    for s in all_tag_sets:
        for tag in s:
            tag_reach[tag] += 1
    if tag_reach:
        top = tag_reach.most_common(10)
        print(f"\n  Most viral input bits (appear in most output bits):")
        for (w, b), cnt in top:
            print(f"    W[{w:2d}] bit {b:2d}:  reaches {cnt}/{total_bits} output bits")

    return {
        'avg_density': avg_density,
        'min_tags': min_tags,
        'max_tags': max_tags,
        'known': known_count,
        'unknown': unknown_count,
    }


# ── Main experiments ─────────────────────────────────────────────────

def run_single_word_experiment():
    """
    Tag only W[0] (32 tagged bits), rest of W known as zero.
    This is tractable even at 64 rounds.
    """
    print("\n" + "+" * 64)
    print("+  EXPERIMENT 1: Single Word Virus (W[0] = 32 tagged ?)")
    print("+" * 64)

    # Build message: W[0] = tagged, W[1..15] = 0
    W = [make_word_tagged(0)]
    for i in range(1, 16):
        W.append(make_word_known(0))

    total_tagged = 32

    # Expand schedule once
    t0 = time.time()
    W_expanded = message_schedule(W)
    t_sched = time.time() - t0
    print(f"\n  Message schedule expanded in {t_sched:.2f}s")

    # Show tag density in schedule words
    print(f"\n  Schedule word tag density (avg tags per bit):")
    for i in range(0, 64, 4):
        densities = []
        for j in range(i, min(i + 4, 64)):
            avg = sum(len(b.tags) for b in W_expanded[j]) / 32
            densities.append(f"W[{j:2d}]={avg:5.1f}")
        print(f"    {'  '.join(densities)}")

    # Run for different round counts
    round_counts = [1, 2, 4, 8, 16, 32, 64]
    results = {}

    for nr in round_counts:
        t0 = time.time()
        output = sha256_compress(W_expanded, num_rounds=nr)
        elapsed = time.time() - t0
        label = f"{nr} rounds  (computed in {elapsed:.2f}s)"
        stats = analyze_output(output, total_tagged, label=label)
        results[nr] = stats

    # Summary table
    print(f"\n{'=' * 64}")
    print(f"  SUMMARY: Tag Density Growth (single word, 32 input tags)")
    print(f"{'=' * 64}")
    print(f"  {'Rounds':>8s}  {'Avg Density':>12s}  {'Min':>6s}  {'Max':>6s}  {'Known':>6s}")
    print(f"  {'-' * 48}")
    for nr in round_counts:
        s = results[nr]
        print(f"  {nr:>8d}  {s['avg_density']:>12.1f}  {s['min_tags']:>6d}  {s['max_tags']:>6d}  {s['known']:>6d}")


def run_full_message_experiment():
    """
    Tag ALL 512 input bits. This will be slow at high rounds.
    We only run a few rounds to see the scaling.
    """
    print("\n\n" + "+" * 64)
    print("+  EXPERIMENT 2: Full Message Virus (all 512 bits tagged)")
    print("+" * 64)

    W = [make_word_tagged(i) for i in range(16)]
    total_tagged = 512

    t0 = time.time()
    W_expanded = message_schedule(W)
    t_sched = time.time() - t0
    print(f"\n  Message schedule expanded in {t_sched:.2f}s")

    # Show schedule density for first few and last few
    print(f"\n  Schedule word tag density (avg tags per bit):")
    show_idxs = list(range(0, 20)) + list(range(60, 64))
    for i in show_idxs:
        avg = sum(len(b.tags) for b in W_expanded[i]) / 32
        print(f"    W[{i:2d}]: avg {avg:6.1f} tags/bit")

    # Run only modest round counts to keep runtime reasonable
    round_counts = [1, 2, 4, 8]
    results = {}

    for nr in round_counts:
        t0 = time.time()
        output = sha256_compress(W_expanded, num_rounds=nr)
        elapsed = time.time() - t0

        if elapsed > 120:
            print(f"\n  Stopping at {nr} rounds -- took {elapsed:.1f}s")
            break

        label = f"{nr} rounds, 512 tagged  (computed in {elapsed:.2f}s)"
        stats = analyze_output(output, total_tagged, label=label)
        results[nr] = stats

    # Try more rounds only if fast enough
    if results and list(results.values())[-1] is not None:
        for nr in [16, 32, 64]:
            t0 = time.time()
            output = sha256_compress(W_expanded, num_rounds=nr)
            elapsed = time.time() - t0

            if elapsed > 300:
                print(f"\n  Stopping at {nr} rounds -- took {elapsed:.1f}s, too slow")
                break

            label = f"{nr} rounds, 512 tagged  (computed in {elapsed:.2f}s)"
            stats = analyze_output(output, total_tagged, label=label)
            results[nr] = stats

    if results:
        print(f"\n{'=' * 64}")
        print(f"  SUMMARY: Full 512-bit Tag Density Growth")
        print(f"{'=' * 64}")
        print(f"  {'Rounds':>8s}  {'Avg Density':>12s}  {'Min':>6s}  {'Max':>6s}  {'Known':>6s}")
        print(f"  {'-' * 48}")
        for nr in sorted(results.keys()):
            s = results[nr]
            print(f"  {nr:>8d}  {s['avg_density']:>12.1f}  {s['min_tags']:>6d}  {s['max_tags']:>6d}  {s['known']:>6d}")


def run_interference_experiment():
    """
    Look for tag-set interference: output bits where tag sets are
    identical, suggesting structural regularity in the mixing.
    """
    print("\n\n" + "+" * 64)
    print("+  EXPERIMENT 3: Tag Interference Detection")
    print("+" * 64)

    W = [make_word_tagged(0)]
    for i in range(1, 16):
        W.append(make_word_known(0))

    W_expanded = message_schedule(W)

    for nr in [4, 16, 64]:
        output = sha256_compress(W_expanded, num_rounds=nr)

        # Collect all tag sets
        tag_sets = []
        for wi, word in enumerate(output):
            for bi, bit in enumerate(word):
                if bit.tags:
                    tag_sets.append(((wi, bi), bit.tags))

        # Find pairs with identical tag sets
        by_set = {}
        for (pos, ts) in tag_sets:
            key = ts
            by_set.setdefault(key, []).append(pos)

        groups = {k: v for k, v in by_set.items() if len(v) > 1}
        print(f"\n  {nr} rounds: {len(groups)} groups of bits share identical tag sets")
        if groups:
            sizes = sorted([len(v) for v in groups.values()], reverse=True)
            print(f"    Group sizes: {sizes[:20]}")
            # Show one example
            example_set = next(iter(groups))
            positions = groups[example_set]
            print(f"    Example: {len(example_set)} tags, shared by {len(positions)} bits:")
            for (wi, bi) in positions[:8]:
                print(f"      word {wi} bit {bi}")


# ── Entry point ──────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 64)
    print("  RAYON VIRUS: Tagged Bit Tracing Through SHA-256")
    print("  Each ? carries a frozenset of (word, bit) origin tags")
    print("  Tags propagate via union through XOR/AND/ADD/etc.")
    print("=" * 64)

    run_single_word_experiment()
    run_full_message_experiment()
    run_interference_experiment()

    print("\n" + "=" * 64)
    print("  DONE")
    print("=" * 64)
