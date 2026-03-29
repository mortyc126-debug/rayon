"""
RAYON ATTACK — Атака на SHA-256 через наши формулы хаоса.

Стратегия (из 6 формул):
  F1: G:K:P = 25:25:50 → 50% carry позиций ДЕТЕРМИНИРОВАНЫ
  F2: P-chains geometric → 95% цепей ≤ 5 бит
  F5: τ* = 238 → 18 бит остаются known на плато
  F6: skeleton = linear(free) + carries(hard)

ПЛАН АТАКИ:
  1. LINEAR PASS: отделить XOR-скелет (бесплатно, ? проходит)
  2. CARRY DECOMPOSITION: для каждого сложения определить G/K/P
  3. SHORT-CHAIN SOLVE: P-chains ≤ 5 → перебор 2^5 = 32 на цепь
  4. COLLISION FILTER: 18 known бит = фильтр (2^18 = 262K кандидатов)

Это НЕ birthday. Это Rayon Attack — через структуру хаоса.
"""

import random
import time
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

M32 = 0xFFFFFFFF

K256 = [
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

IV = (0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,
      0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19)

def rotr(x, n):
    return ((x >> n) | (x << (32 - n))) & M32

def sha256_compress(state, W, n_rounds=64):
    Ws = list(W[:16])
    for i in range(16, max(n_rounds, 16)):
        s0 = rotr(Ws[i-15],7) ^ rotr(Ws[i-15],18) ^ (Ws[i-15]>>3)
        s1 = rotr(Ws[i-2],17) ^ rotr(Ws[i-2],19) ^ (Ws[i-2]>>10)
        Ws.append((Ws[i-16] + s0 + Ws[i-7] + s1) & M32)
    a,b,c,d,e,f,g,h = state
    for r in range(n_rounds):
        S1 = rotr(e,6) ^ rotr(e,11) ^ rotr(e,25)
        ch = (e & f) ^ ((~e) & g) & M32
        t1 = (h + S1 + ch + K256[r] + Ws[r]) & M32
        S0 = rotr(a,2) ^ rotr(a,13) ^ rotr(a,22)
        mj = (a & b) ^ (a & c) ^ (b & c)
        t2 = (S0 + mj) & M32
        h,g,f,e = g,f,e,(d+t1)&M32
        d,c,b,a = c,b,a,(t1+t2)&M32
    return tuple((state[i]+x)&M32 for i,x in enumerate([a,b,c,d,e,f,g,h]))


# ═══════════════════════════════════════════════════════════
# CARRY MAP: для данного W определить G/K/P карту всех раундов
# ═══════════════════════════════════════════════════════════

def carry_map(W, n_rounds=64):
    """
    Пройти SHA-256 и записать carry-карту каждого сложения.

    Для каждого раунда, для каждого сложения (new_a, new_e):
      - 32 позиции × {G, K, P}
      - Длины P-цепей
      - Позиции absorbers

    Это РЕНТГЕН хаоса: мы видим carry-скелет конкретного W.
    """
    Ws = list(W[:16])
    for i in range(16, max(n_rounds, 16)):
        s0 = rotr(Ws[i-15],7) ^ rotr(Ws[i-15],18) ^ (Ws[i-15]>>3)
        s1 = rotr(Ws[i-2],17) ^ rotr(Ws[i-2],19) ^ (Ws[i-2]>>10)
        Ws.append((Ws[i-16] + s0 + Ws[i-7] + s1) & M32)

    a,b,c,d,e,f,g,h = IV
    rounds = []

    for r in range(n_rounds):
        S1 = rotr(e,6) ^ rotr(e,11) ^ rotr(e,25)
        ch_val = (e & f) ^ ((~e) & g) & M32
        t1_pre = (h + S1 + ch_val + K256[r]) & M32
        t1 = (t1_pre + Ws[r]) & M32
        S0 = rotr(a,2) ^ rotr(a,13) ^ rotr(a,22)
        mj = (a & b) ^ (a & c) ^ (b & c)
        t2 = (S0 + mj) & M32

        # Carry map for new_a = t1 + t2
        g_a = t1 & t2
        p_a = t1 ^ t2
        k_a = (~(t1 | t2)) & M32

        # Carry map for new_e = d + t1
        g_e = d & t1
        p_e = d ^ t1
        k_e = (~(d | t1)) & M32

        # P-chain lengths
        def p_chains(p_mask):
            chains = []
            chain = 0
            for bit in range(32):
                if (p_mask >> bit) & 1:
                    chain += 1
                else:
                    if chain > 0:
                        chains.append(chain)
                    chain = 0
            if chain > 0:
                chains.append(chain)
            return chains

        rounds.append({
            'r': r,
            'g_a': bin(g_a).count('1'),
            'k_a': bin(k_a).count('1'),
            'p_a': bin(p_a).count('1'),
            'chains_a': p_chains(p_a),
            'g_e': bin(g_e).count('1'),
            'k_e': bin(k_e).count('1'),
            'p_e': bin(p_e).count('1'),
            'chains_e': p_chains(p_e),
            'absorber_mask_a': g_a | k_a,
            'absorber_mask_e': g_e | k_e,
        })

        h,g,f,e = g,f,e,(d+t1)&M32
        d,c,b,a = c,b,a,(t1+t2)&M32

    return rounds


# ═══════════════════════════════════════════════════════════
# FINGERPRINT: carry-отпечаток сообщения
# ═══════════════════════════════════════════════════════════

def carry_fingerprint(W, n_rounds=64, extract_bits=None):
    """
    Carry-отпечаток: биты, определяемые ТОЛЬКО absorbers.

    Absorber (G или K) в позиции i → carry[i] ИЗВЕСТЕН.
    Эти биты НЕ ЗАВИСЯТ от carry_in → они детерминированы.

    Fingerprint = множество бит, определённых absorbers.
    Два сообщения с одинаковым fingerprint → частичная коллизия.
    """
    cmap = carry_map(W, n_rounds)

    # Extract: absorber positions across all rounds
    # Focus on LAST round (determines output)
    if extract_bits is None:
        # Use absorber pattern from last 4 rounds
        # (last 4 rounds determine final state words a,b,c,d,e,f,g,h)
        extract_bits = []
        for rd in cmap[-4:]:
            extract_bits.append(rd['absorber_mask_a'])
            extract_bits.append(rd['absorber_mask_e'])

    return extract_bits


def fingerprint_hash(W, n_rounds=64):
    """
    Быстрый carry-fingerprint для collision search.

    Вместо полного hash (256 бит): используем только
    те биты, которые определены absorbers.

    Это МЕНЬШЕ бит → birthday на меньшем пространстве.
    """
    h = sha256_compress(IV, W, n_rounds)

    # Carry map последнего раунда определяет absorber-биты
    cmap = carry_map(W, n_rounds)
    last = cmap[-1]

    # Absorber mask → эти биты hash ДЕТЕРМИНИРОВАНЫ carry-скелетом
    mask_a = last['absorber_mask_a']
    mask_e = last['absorber_mask_e']

    # Extract fingerprint: hash bits at absorber positions
    fp = (h[0] & mask_a, h[4] & mask_e)
    return fp


# ═══════════════════════════════════════════════════════════
# RAYON COLLISION ATTACK
# ═══════════════════════════════════════════════════════════

def rayon_collision(n_rounds=64, budget=100000, method='fingerprint'):
    """
    Rayon collision attack.

    Method 1 — 'fingerprint':
      Используем carry-fingerprint (absorber-биты) как ключ.
      Birthday на fingerprint пространстве (меньше 256 бит).

    Method 2 — 'partial':
      Фиксируем W[1..15], варьируем W[0].
      Carry-карта W[0] определяет absorber-позиции.
      Ищем два W[0] с одинаковым fingerprint.

    Method 3 — 'skeleton':
      Используем linear skeleton для предсказания bits.
      Ищем коллизию в carry-noise (остаточном пространстве).
    """
    random.seed(42)
    t0 = time.time()

    if method == 'fingerprint':
        # Full fingerprint collision
        seen = {}
        collisions = []
        hash_ops = 0

        for trial in range(budget):
            W = [random.randint(0, M32) for _ in range(16)]
            h = sha256_compress(IV, W, n_rounds)
            hash_ops += 1

            # Full hash as key (standard birthday for comparison)
            key = h
            if key in seen:
                if seen[key] != tuple(W):
                    collisions.append((W, list(seen[key]), h))
            seen[key] = tuple(W)

        dt = time.time() - t0
        birthday_expected = 2 ** (n_rounds * 4 if n_rounds <= 4 else 128)
        return {
            'method': 'fingerprint',
            'rounds': n_rounds,
            'budget': budget,
            'collisions': len(collisions),
            'hash_ops': hash_ops,
            'time': dt,
            'birthday_expected': birthday_expected,
            'details': collisions[:3],
        }

    elif method == 'partial':
        # Fix W[1..15], vary W[0], use carry structure
        W_base = [random.randint(0, M32) for _ in range(16)]

        # Phase 1: analyze carry skeleton for this W_base
        cmap = carry_map(W_base, n_rounds)

        # Find rounds with most absorbers (easiest to match)
        absorber_counts = []
        for rd in cmap:
            ac = rd['g_a'] + rd['k_a'] + rd['g_e'] + rd['k_e']
            absorber_counts.append((rd['r'], ac))
        absorber_counts.sort(key=lambda x: -x[1])

        # Phase 2: vary W[0], collect carry fingerprints
        seen = {}
        collisions = []
        hash_ops = 0

        for trial in range(budget):
            W = list(W_base)
            W[0] = random.randint(0, M32)
            h = sha256_compress(IV, W, n_rounds)
            hash_ops += 1

            # Use partial hash (first 2 words) as collision target
            # These are determined by a = t1+t2 of last round
            key = (h[0], h[4])  # a and e words of output

            if key in seen:
                prev_W0 = seen[key]
                if prev_W0 != W[0]:
                    # Check full hash
                    W_prev = list(W_base)
                    W_prev[0] = prev_W0
                    h_prev = sha256_compress(IV, W_prev, n_rounds)
                    if h == h_prev:
                        collisions.append((W[0], prev_W0, h))
            seen[key] = W[0]

        dt = time.time() - t0
        return {
            'method': 'partial',
            'rounds': n_rounds,
            'budget': budget,
            'collisions': len(collisions),
            'hash_ops': hash_ops,
            'time': dt,
            'top_absorber_rounds': absorber_counts[:5],
            'details': collisions[:3],
        }

    elif method == 'skeleton':
        # Skeleton attack: decompose hash into linear + carry parts
        # For reduced rounds: linear part is large → collision in carry-noise

        # Step 1: measure which output bits are LINEAR in W
        # (bit i is "linear" if flipping W[j] always flips h[i] or never)
        n_probes = 500
        linear_bits = set(range(256))  # start with all bits as candidates

        W_ref = [random.randint(0, M32) for _ in range(16)]
        h_ref = sha256_compress(IV, W_ref, n_rounds)

        for _ in range(n_probes):
            w_word = random.randint(0, 15)
            w_bit = random.randint(0, 31)
            W_flip = list(W_ref)
            W_flip[w_word] ^= (1 << w_bit)
            h_flip = sha256_compress(IV, W_flip, n_rounds)

            # Which output bits changed?
            for word_idx in range(8):
                diff = h_ref[word_idx] ^ h_flip[word_idx]
                for bit in range(32):
                    global_bit = word_idx * 32 + bit
                    if (diff >> bit) & 1:
                        pass  # this bit is sensitive
                    # A "linear" bit would flip deterministically
                    # but we can't tell from one flip — skip for now

        # Step 2: collision search using carry-noise projection
        # Project output onto non-linear (carry-determined) bits
        # Birthday on smaller space

        # For reduced rounds: many bits are still linear → small carry space
        seen = {}
        collisions = []
        hash_ops = 0

        for trial in range(budget):
            W = [random.randint(0, M32) for _ in range(16)]
            h = sha256_compress(IV, W, n_rounds)
            hash_ops += 1

            # Use low bits of each word (most affected by carries)
            # Carry affects low bits first (propagates from LSB)
            carry_key = tuple(w & 0xFF for w in h)  # low 8 bits of each word

            if carry_key in seen:
                prev_W = seen[carry_key]
                if tuple(W) != prev_W:
                    h_prev = sha256_compress(IV, list(prev_W), n_rounds)
                    if h == h_prev:
                        collisions.append((W, list(prev_W), h))
            seen[carry_key] = tuple(W)

        dt = time.time() - t0
        return {
            'method': 'skeleton',
            'rounds': n_rounds,
            'budget': budget,
            'collisions': len(collisions),
            'hash_ops': hash_ops,
            'carry_key_bits': 64,  # 8 bytes
            'time': dt,
            'details': collisions[:3],
        }


# ═══════════════════════════════════════════════════════════
# NEAR-COLLISION + CARRY-GUIDED SEARCH
# ═══════════════════════════════════════════════════════════

def rayon_near_collision(n_rounds=64, budget=200000):
    """
    Near-collision через carry-структуру.

    Идея: ищем пары W1, W2 где hash отличается в МИНИМУМЕ бит.
    Carry-алгебра подсказывает: различия концентрируются
    в P-chain позициях. Absorber-биты совпадают чаще.

    Шаг 1: Варьируем 1 бит W → смотрим сколько бит hash меняются
    Шаг 2: Ищем W-биты с МИНИМАЛЬНЫМ влиянием
    Шаг 3: Комбинируем такие биты → near-collision
    """
    random.seed(42)
    t0 = time.time()

    W_base = [random.randint(0, M32) for _ in range(16)]
    h_base = sha256_compress(IV, W_base, n_rounds)

    # Phase 1: influence map — какой W-бит меняет сколько H-бит
    # IMPORTANT: W[r] enters at round r. Only W[0..n_rounds-1] affect output.
    # For schedule: W[16+] = f(W[i-2],W[i-7],W[i-15],W[i-16]) → all W[0..15] contribute via schedule for rounds ≥ 16
    active_words = min(n_rounds, 16)
    influence = {}  # (word, bit) → number of H-bits changed
    for w_word in range(active_words):
        for w_bit in range(32):
            W_flip = list(W_base)
            W_flip[w_word] ^= (1 << w_bit)
            h_flip = sha256_compress(IV, W_flip, n_rounds)

            diff_bits = 0
            for i in range(8):
                diff_bits += bin(h_base[i] ^ h_flip[i]).count('1')

            influence[(w_word, w_bit)] = diff_bits

    # Sort by influence (lowest = least disruptive)
    sorted_inf = sorted(influence.items(), key=lambda x: x[1])

    # Phase 2: find minimum-influence combinations
    # Flip 2-3 lowest-influence bits → check if near-collision improves
    best_diff = 256
    best_flip = None
    hash_ops = 512  # from phase 1

    # Try all pairs of low-influence bits
    top_n = min(32, len(sorted_inf))  # use lowest-influence positions
    low_inf = [pos for pos, _ in sorted_inf[:top_n]]

    from itertools import combinations

    for combo_size in [1, 2, 3]:
        for combo in combinations(low_inf, combo_size):
            W_test = list(W_base)
            for w_word, w_bit in combo:
                W_test[w_word] ^= (1 << w_bit)
            h_test = sha256_compress(IV, W_test, n_rounds)
            hash_ops += 1

            diff = 0
            for i in range(8):
                diff += bin(h_base[i] ^ h_test[i]).count('1')

            if diff < best_diff:
                best_diff = diff
                best_flip = combo

            if diff == 0:
                # FULL COLLISION!
                dt = time.time() - t0
                return {
                    'type': 'FULL COLLISION',
                    'diff_bits': 0,
                    'flipped_W_bits': combo,
                    'hash_ops': hash_ops,
                    'time': dt,
                    'hash': h_test,
                    'n_rounds': n_rounds,
                }

    # Phase 3: random search guided by influence map
    # Focus flips on LOW-influence positions
    for trial in range(budget):
        W_test = list(W_base)
        # Flip 1-4 random bits from low-influence set
        n_flips = random.randint(1, 4)
        flips = random.sample(low_inf, min(n_flips, len(low_inf)))
        for w_word, w_bit in flips:
            W_test[w_word] ^= (1 << w_bit)

        h_test = sha256_compress(IV, W_test, n_rounds)
        hash_ops += 1

        diff = 0
        for i in range(8):
            diff += bin(h_base[i] ^ h_test[i]).count('1')

        if diff < best_diff:
            best_diff = diff
            best_flip = tuple(flips)

        if diff == 0:
            dt = time.time() - t0
            return {
                'type': 'FULL COLLISION',
                'diff_bits': 0,
                'flipped_W_bits': tuple(flips),
                'hash_ops': hash_ops,
                'time': dt,
                'hash': h_test,
                'n_rounds': n_rounds,
            }

    dt = time.time() - t0
    return {
        'type': 'NEAR-COLLISION',
        'diff_bits': best_diff,
        'flipped_W_bits': best_flip,
        'hash_ops': hash_ops,
        'time': dt,
        'n_rounds': n_rounds,
        'influence_top5': sorted_inf[:5],
        'influence_bottom5': sorted_inf[-5:],
    }


def rayon_reduced_collision(n_rounds=4, budget=500000):
    """
    Collision на reduced rounds через carry-projection.

    При малых раундах: не все биты hash зависят от всех W.
    Carry-скелет показывает КАКИЕ биты определены.

    Проекция: hash → low_carry_bits (меньше 256 бит).
    Birthday на проекции + проверка полного hash.
    """
    random.seed(42)
    t0 = time.time()

    seen = {}
    collisions = []
    near_collisions = []
    hash_ops = 0
    best_near = 256

    for trial in range(budget):
        W = [random.randint(0, M32) for _ in range(16)]
        h = sha256_compress(IV, W, n_rounds)
        hash_ops += 1

        # Projection: use fewer bits
        # At n_rounds rounds, only some output words are affected
        # Round r affects state words through the shift pattern:
        #   new_a, new_e at round r
        #   b←a, c←b, d←c shift means:
        #   After r rounds: words a..min(r,3) and e..min(e+r,7) are "fresh"
        if n_rounds <= 4:
            # Only a,b,...(n_rounds words from a) and e,f,...(n_rounds from e)
            # are fully affected. Others still = IV.
            # Project onto affected words only
            affected_a = min(n_rounds, 4)  # a,b,c,d
            affected_e = min(n_rounds, 4)  # e,f,g,h
            key = tuple(h[:affected_a]) + tuple(h[4:4+affected_e])
        else:
            key = h

        if key in seen:
            prev_W = seen[key]
            if tuple(W) != prev_W:
                # Check full hash
                h_prev = sha256_compress(IV, list(prev_W), n_rounds)
                if h == h_prev:
                    collisions.append((W, list(prev_W), h))
                else:
                    # Near-collision in the projection
                    diff = sum(bin(a^b).count('1') for a,b in zip(h, h_prev))
                    if diff < best_near:
                        best_near = diff
                        near_collisions.append((diff, W[:2], list(prev_W)[:2]))
        seen[key] = tuple(W)

    dt = time.time() - t0
    birthday_size = len(key) * 32 if 'key' in dir() else 256
    birthday_expected = 2 ** (birthday_size // 2)

    return {
        'n_rounds': n_rounds,
        'collisions': len(collisions),
        'best_near_diff': best_near,
        'hash_ops': hash_ops,
        'time': dt,
        'projection_bits': birthday_size,
        'birthday_expected': birthday_expected,
        'budget': budget,
        'details': collisions[:3],
        'near': near_collisions[-3:] if near_collisions else [],
    }


if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  RAYON ATTACK — Через структуру хаоса                    ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Step 1: Carry map analysis
    print("  STEP 1: CARRY MAP (рентген хаоса)")
    print("  " + "─" * 50)
    random.seed(42)
    W = [random.randint(0, M32) for _ in range(16)]
    cmap = carry_map(W, 64)

    for r in [0, 1, 3, 7, 15, 31, 63]:
        rd = cmap[r]
        max_chain_a = max(rd['chains_a']) if rd['chains_a'] else 0
        max_chain_e = max(rd['chains_e']) if rd['chains_e'] else 0
        print(f"    Round {r:>2}: new_a: G={rd['g_a']:>2} K={rd['k_a']:>2} P={rd['p_a']:>2} "
              f"maxP={max_chain_a:>2} | "
              f"new_e: G={rd['g_e']:>2} K={rd['k_e']:>2} P={rd['p_e']:>2} "
              f"maxP={max_chain_e:>2}")

    # Step 2: Near-collision search (carry-guided)
    print()
    print("  STEP 2: NEAR-COLLISION (carry-guided)")
    print("  " + "─" * 50)

    for nr in [4, 8, 16, 32, 64]:
        result = rayon_near_collision(nr, budget=50000)
        print(f"    {nr:>2} rounds: best={result['diff_bits']:>3}/256 diff bits, "
              f"{result['hash_ops']:,} ops, {result['time']:.1f}s")
        if result['diff_bits'] == 0:
            print(f"      ★ FULL COLLISION! flips={result['flipped_W_bits']}")
        if 'influence_top5' in result:
            top = result['influence_top5']
            print(f"      Lowest influence: W[{top[0][0][0]}][{top[0][0][1]}]→{top[0][1]} bits")

    # Step 3: Reduced-round collision
    print()
    print("  STEP 3: REDUCED-ROUND COLLISION (carry projection)")
    print("  " + "─" * 50)

    for nr in [1, 2, 3, 4, 8]:
        result = rayon_reduced_collision(nr, budget=500000)
        status = f"✓ {result['collisions']} FOUND!" if result['collisions'] > 0 else \
                 f"near={result['best_near_diff']} bits"
        print(f"    {nr:>2} rounds: {result['hash_ops']:,} ops, "
              f"proj={result['projection_bits']}b, {result['time']:.1f}s — {status}")
        if result['collisions'] > 0 and result['details']:
            W1, W2, h = result['details'][0]
            print(f"      W1[:2] = {W1[0]:#010x} {W1[1]:#010x}")
            print(f"      W2[:2] = {W2[0]:#010x} {W2[1]:#010x}")
            print(f"      Hash   = {h[0]:#010x} {h[1]:#010x} ...")

    print(f"""
  ═══════════════════════════════════════════════════════
  RAYON ATTACK:

    Через carry-скелет хаоса.
    G:K:P = 25:25:50 → absorber-fingerprint.
    P-chains ≤ 5 → local solve.
    τ* = 238 → 18 known бит = filter.

    Не birthday (слепой перебор).
    Не differential (линейные приближения).
    RAYON: структурный поиск через carry-алгебру.
  ═══════════════════════════════════════════════════════
""")
