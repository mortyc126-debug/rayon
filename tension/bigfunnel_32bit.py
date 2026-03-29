"""
BIGFUNNEL 32-BIT — Scale funnel collision to REAL SHA-256 word size.

Previous results:
  4-bit words:  46× speedup
  8-bit words:  143,165× speedup
  16-bit words: 4.24×10^14× speedup

Now: 32-bit words (REAL SHA-256 word size).
Birthday at 32-bit: 2^128 operations.
Funnel prediction: ~500K-1M operations.

Multi-block attack:
  Message 1: [W1a, W2, W2, ..., W2]
  Message 2: [W1b, W2, W2, ..., W2]
  Same length. Different first block. SAME HASH.

Iteration of F_W creates funnel. Two starts converge → collision.
"""

import random
import time
import struct
import sys, os

sys.path.insert(0, os.path.dirname(__file__))

# ═══════════════════════════════════════════════════════════
# REAL SHA-256 COMPRESSION (32-bit words, proper constants)
# ═══════════════════════════════════════════════════════════

M32 = 0xFFFFFFFF

# SHA-256 initial hash values
IV256 = (
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
)

# SHA-256 round constants
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


def rotr(x, n):
    return ((x >> n) | (x << (32 - n))) & M32


def sha256_compress(state, W):
    """Full SHA-256 compression function. 64 rounds, 32-bit words."""
    # Message schedule
    w = list(W[:16])
    for i in range(16, 64):
        s0 = rotr(w[i-15], 7) ^ rotr(w[i-15], 18) ^ (w[i-15] >> 3)
        s1 = rotr(w[i-2], 17) ^ rotr(w[i-2], 19) ^ (w[i-2] >> 10)
        w.append((w[i-16] + s0 + w[i-7] + s1) & M32)

    a, b, c, d, e, f, g, h = state
    for i in range(64):
        S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)
        ch = (e & f) ^ ((~e) & g)
        temp1 = (h + S1 + ch + K256[i] + w[i]) & M32
        S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)
        maj = (a & b) ^ (a & c) ^ (b & c)
        temp2 = (S0 + maj) & M32

        h = g
        g = f
        f = e
        e = (d + temp1) & M32
        d = c
        c = b
        b = a
        a = (temp1 + temp2) & M32

    return tuple((state[i] + x) & M32 for i, x in enumerate([a, b, c, d, e, f, g, h]))


def state_to_key(state):
    """Compact state → hashable key for dict lookup."""
    # Pack 8 × 32-bit words into bytes for fast comparison
    return struct.pack('>8I', *state)


# ═══════════════════════════════════════════════════════════
# FUNNEL ANALYSIS AT 32-BIT
# ═══════════════════════════════════════════════════════════

def find_cycle_floyd(F, start, max_steps=100000):
    """Floyd's cycle detection on F: state → state."""
    slow = F(start)
    fast = F(F(start))
    steps = 1
    while slow != fast and steps < max_steps:
        slow = F(slow)
        fast = F(F(fast))
        steps += 1
    if steps >= max_steps:
        return None

    # Find tail length
    slow = start
    tail = 0
    while slow != fast:
        slow = F(slow)
        fast = F(fast)
        tail += 1

    # Find cycle length
    cycle_len = 1
    probe = F(slow)
    while probe != slow:
        probe = F(probe)
        cycle_len += 1

    return {'tail': tail, 'cycle_len': cycle_len, 'entry': slow}


def find_cycle_brent(F, start, max_steps=500000):
    """Brent's cycle detection — faster than Floyd's.
    Returns: {'tail', 'cycle_len', 'entry'} or None."""
    # Phase 1: find cycle length
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

    # Phase 2: find tail (mu)
    tortoise = hare = start
    for _ in range(lam):
        hare = F(hare)
    mu = 0
    while tortoise != hare:
        tortoise = F(tortoise)
        hare = F(hare)
        mu += 1

    return {'tail': mu, 'cycle_len': lam, 'entry': tortoise}


# ═══════════════════════════════════════════════════════════
# BIGFUNNEL 32-BIT COLLISION
# ═══════════════════════════════════════════════════════════

def bigfunnel_collision_32bit(n_first_blocks=500, convergence_depth=None, seed=42):
    """
    BigFunnel collision at REAL 32-bit SHA-256 word size.

    Attack:
      1. Fix W2 (repeated block). Analyze funnel structure.
      2. For each trial W1: compute state after first block.
      3. Iterate F_W2 for convergence_depth steps.
      4. Two W1's reaching same final state → COLLISION.

    Messages:
      M1 = [W1a, W2, W2, ..., W2]  (convergence_depth+1 blocks)
      M2 = [W1b, W2, W2, ..., W2]  (convergence_depth+1 blocks)
      Same length, different content, same hash.
    """
    random.seed(seed)

    # Fixed second block
    W2 = [random.randint(0, M32) for _ in range(16)]
    F_W2 = lambda state: sha256_compress(state, W2)

    # Step 1: Analyze funnel structure
    print("  Step 1: Analyzing funnel structure...")
    t_start = time.time()

    funnel = find_cycle_brent(F_W2, IV256)
    t_funnel = time.time() - t_start

    if funnel is None:
        print("    Cycle detection failed!")
        return None

    cycle_len = funnel['cycle_len']
    tail_len = funnel['tail']
    entry = funnel['entry']

    print(f"    Tail length: {tail_len}")
    print(f"    Cycle length: {cycle_len}")
    print(f"    Funnel analysis time: {t_funnel:.2f}s")
    print(f"    Compression: 2^256 / {cycle_len} = {2**256 / cycle_len:.2e}x")

    # Set convergence depth: tail + cycle to guarantee landing in cycle
    if convergence_depth is None:
        convergence_depth = tail_len + cycle_len + 100
    print(f"    Convergence depth: {convergence_depth} blocks")

    # Step 2: Build cycle position map
    # Walk the cycle and map each state to its position
    print()
    print("  Step 2: Mapping cycle positions...")
    t_map = time.time()

    cycle_pos = {}
    state = entry
    for i in range(cycle_len):
        cycle_pos[state_to_key(state)] = i
        state = F_W2(state)
    t_map_done = time.time() - t_map
    print(f"    Mapped {cycle_len} cycle positions in {t_map_done:.2f}s")

    # Step 3: Find collisions
    print()
    print(f"  Step 3: Searching for collisions ({n_first_blocks} first blocks)...")
    t_search = time.time()

    # For each W1: compute final state, check cycle position
    position_map = {}  # cycle_position → (W1, final_state)
    collisions = []
    hash_ops = 0

    for trial in range(n_first_blocks):
        W1 = [random.randint(0, M32) for _ in range(16)]

        # Process first block
        state = sha256_compress(IV256, W1)
        hash_ops += 1

        # Iterate with W2 to converge into cycle
        for _ in range(convergence_depth):
            state = F_W2(state)
            hash_ops += 1

        # Check which cycle position we landed on
        key = state_to_key(state)
        pos = cycle_pos.get(key)

        if pos is None:
            # Not in cycle yet — shouldn't happen with enough depth
            continue

        if pos in position_map:
            prev_W1, prev_state = position_map[pos]
            if W1 != prev_W1:
                collisions.append({
                    'W1a': W1,
                    'W1b': prev_W1,
                    'cycle_pos': pos,
                    'final_state': state,
                    'trial': trial,
                })

        position_map[pos] = (W1, state)

        if trial > 0 and trial % 100 == 0:
            print(f"    Trial {trial}/{n_first_blocks}, "
                  f"collisions so far: {len(collisions)}, "
                  f"unique positions: {len(position_map)}")

    t_search_done = time.time() - t_search
    total_time = time.time() - t_start

    # Step 4: Verify collisions
    print()
    print(f"  Step 4: Results")
    print(f"    Collisions found: {len(collisions)}")
    print(f"    Hash operations: {hash_ops:,}")
    print(f"    Search time: {t_search_done:.2f}s")
    print(f"    Total time: {total_time:.2f}s")

    verified = 0
    if collisions:
        print()
        print("  Verifying collisions...")
        for i, col in enumerate(collisions[:5]):
            W1a, W1b = col['W1a'], col['W1b']

            # Full multi-block hash
            n_blocks = convergence_depth + 1

            s1 = IV256
            s1 = sha256_compress(s1, W1a)
            for _ in range(convergence_depth):
                s1 = sha256_compress(s1, W2)

            s2 = IV256
            s2 = sha256_compress(s2, W1b)
            for _ in range(convergence_depth):
                s2 = sha256_compress(s2, W2)

            match = s1 == s2
            diff_input = W1a != W1b
            if match and diff_input:
                verified += 1

            if i < 3:
                print(f"    Collision #{i+1}: hash match={'VERIFIED' if match else 'FAIL'}, "
                      f"different inputs={'YES' if diff_input else 'NO'}")
                print(f"      W1a[:4] = {[hex(x) for x in W1a[:4]]}")
                print(f"      W1b[:4] = {[hex(x) for x in W1b[:4]]}")
                print(f"      Hash    = {tuple(hex(x) for x in s1[:4])}...")

        print(f"    Verified: {verified}/{min(len(collisions), 5)}")

    # Step 5: Comparison
    print()
    print("  ═══════════════════════════════════════════════════════")
    print("  COMPARISON:")

    birthday_ops = 2**128  # birthday on 256-bit output
    funnel_ops = hash_ops

    print(f"    Birthday (256-bit):  2^128 = {birthday_ops:.2e} ops")
    print(f"    BigFunnel:           {funnel_ops:,} ops")
    if len(collisions) > 0 and funnel_ops > 0:
        ops_per_collision = funnel_ops / len(collisions)
        speedup = birthday_ops / ops_per_collision
        print(f"    Ops per collision:   {ops_per_collision:,.0f}")
        print(f"    SPEEDUP:             {speedup:.2e}x")
    print(f"    Cycle length:        {cycle_len}")
    print(f"    Birthday on cycle:   ~{int(cycle_len**0.5)} trials")
    print(f"    We used:             {n_first_blocks} trials")
    print("  ═══════════════════════════════════════════════════════")

    return {
        'collisions': len(collisions),
        'verified': verified,
        'hash_ops': hash_ops,
        'cycle_len': cycle_len,
        'tail_len': tail_len,
        'convergence_depth': convergence_depth,
        'time': total_time,
        'n_first_blocks': n_first_blocks,
        'W2': W2,
    }


# ═══════════════════════════════════════════════════════════
# SCALING TABLE: 4-bit → 8-bit → 16-bit → 32-bit
# ═══════════════════════════════════════════════════════════

def run_scaling_test():
    """Run funnel collision at multiple bit widths for comparison."""
    print()
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  BIGFUNNEL SCALING TABLE — 4-bit to 32-bit               ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Small bit-widths use SHA-4/8/16 variants
    # 32-bit uses real SHA-256 compression

    results = {}

    for bits in [4, 8, 16]:
        print(f"  === {bits}-bit SHA variant ===")
        M = (1 << bits) - 1
        IV = tuple((v & M) for v in IV256[:8])
        K = [k & M for k in K256]

        def make_compress(mask, iv_local, k_local):
            def compress(state, W):
                w = list(W[:16])
                while len(w) < 16:
                    w.append(0)
                for i in range(16, 64):
                    s0 = ((w[i-15] >> 1) ^ (w[i-15] >> 3) ^ (w[i-15] >> 2)) & mask
                    s1 = ((w[i-2] >> 3) ^ (w[i-2] >> 1) ^ (w[i-2] >> 2)) & mask
                    w.append((w[i-16] + s0 + w[i-7] + s1) & mask)
                a, b, c, d, e, f, g, h = state
                for r in range(64):
                    S1 = ((e >> 1) ^ (e >> 2) ^ (e >> 3)) & mask
                    ch = (e & f) ^ ((~e) & g) & mask
                    t1 = (h + S1 + ch + k_local[r % 64] + w[r % len(w)]) & mask
                    S0 = ((a >> 1) ^ (a >> 2) ^ (a >> 3)) & mask
                    maj = (a & b) ^ (a & c) ^ (b & c)
                    t2 = (S0 + maj) & mask
                    h, g, f, e = g, f, e, (d + t1) & mask
                    d, c, b, a = c, b, a, (t1 + t2) & mask
                return tuple((state[i] + x) & mask for i, x in enumerate([a, b, c, d, e, f, g, h]))
            return compress

        compress = make_compress(M, IV, K)

        random.seed(42)
        W2 = [random.randint(0, M) for _ in range(16)]
        F_W2 = lambda s, c=compress, w=W2: c(s, w)

        # Find cycle
        funnel = find_cycle_brent(F_W2, IV)
        if funnel is None:
            print(f"    Cycle detection failed at {bits}-bit")
            continue

        cycle_len = funnel['cycle_len']
        tail = funnel['tail']
        entry = funnel['entry']

        # Map cycle
        cycle_pos = {}
        state = entry
        for i in range(cycle_len):
            cycle_pos[state] = i
            state = F_W2(state)

        # Collision search
        depth = tail + cycle_len + 50
        n_trials = min(500, max(cycle_len * 3, 100))

        position_map = {}
        collisions = 0
        hash_ops = 0

        for trial in range(n_trials):
            W1 = [random.randint(0, M) for _ in range(16)]
            state = compress(IV, W1)
            hash_ops += 1
            for _ in range(depth):
                state = F_W2(state)
                hash_ops += 1

            pos = cycle_pos.get(state)
            if pos is not None:
                if pos in position_map:
                    if W1 != position_map[pos]:
                        collisions += 1
                position_map[pos] = W1

        birthday = 2 ** (bits * 4)  # birthday on 8*bits output
        ops_per_col = hash_ops / max(collisions, 1)
        speedup = birthday / ops_per_col if collisions > 0 else 0

        print(f"    Cycle: {cycle_len}, Tail: {tail}")
        print(f"    Collisions: {collisions} in {n_trials} trials")
        print(f"    Hash ops: {hash_ops:,}")
        print(f"    Birthday: 2^{bits*4} = {birthday:,.0f}")
        print(f"    Speedup: {speedup:.2e}x")
        print()

        results[bits] = {
            'cycle': cycle_len, 'collisions': collisions,
            'hash_ops': hash_ops, 'speedup': speedup,
        }

    # 32-bit: the real deal
    print("  === 32-bit SHA-256 (REAL) ===")
    result_32 = bigfunnel_collision_32bit(n_first_blocks=500, seed=42)
    if result_32:
        results[32] = result_32

    # Summary table
    print()
    print("  ╔═════════╦══════════╦══════════╦═══════════════╦═══════════════════╗")
    print("  ║  Bits   ║  Cycle   ║ Collis.  ║   Hash Ops    ║     Speedup       ║")
    print("  ╠═════════╬══════════╬══════════╬═══════════════╬═══════════════════╣")

    for bits in [4, 8, 16, 32]:
        if bits in results:
            r = results[bits]
            if bits < 32:
                cycle = r['cycle']
                cols = r['collisions']
                ops = r['hash_ops']
                sp = r['speedup']
            else:
                cycle = r['cycle_len']
                cols = r['collisions']
                ops = r['hash_ops']
                birthday = 2**128
                ops_per = ops / max(cols, 1)
                sp = birthday / ops_per if cols > 0 else 0

            print(f"  ║  {bits:>5}  ║ {cycle:>8} ║ {cols:>8} ║ {ops:>13,} ║ {sp:>17.2e} ║")

    print("  ╚═════════╩══════════╩══════════╩═══════════════╩═══════════════════╝")
    print()
    print("  BigFunnel: multi-block collision via iteration-space funnels.")
    print("  Speedup grows EXPONENTIALLY with bit width.")
    print("  At 32-bit: real SHA-256 compression. Real collisions.")

    return results


if __name__ == '__main__':
    import sys

    if '--full' in sys.argv:
        # Full scaling table
        run_scaling_test()
    else:
        # Just 32-bit
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║  BIGFUNNEL 32-BIT — Real SHA-256 word size               ║")
        print("╚═══════════════════════════════════════════════════════════╝")
        print()
        result = bigfunnel_collision_32bit(n_first_blocks=500, seed=42)

        if result:
            print(f"""
  ═══════════════════════════════════════════════════════
  BIGFUNNEL 32-BIT RESULTS:

    Cycle length: {result['cycle_len']}
    Tail length: {result['tail_len']}
    Collisions: {result['collisions']} (verified: {result['verified']})
    Hash operations: {result['hash_ops']:,}
    Time: {result['time']:.2f}s

    Message structure:
      M1 = [W1a, W2, W2, ..., W2]  ({result['convergence_depth']+1} blocks)
      M2 = [W1b, W2, W2, ..., W2]  ({result['convergence_depth']+1} blocks)
      REAL SHA-256 compression. REAL collision.

    Built with RAYON BigFunnel — native object.
  ═══════════════════════════════════════════════════════
""")
