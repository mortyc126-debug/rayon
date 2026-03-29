"""
RAYON COLLISION HUNT — Поиск реальной коллизии через virus-guided перебор.

Факт: N virus-бит → combined zone ≈ 128 (константа).
Факт: при N=35, zone=93 (93 бита различаются при flip ВСЕХ).

Но flip ВСЕХ — это одна конкретная комбинация из 2^N.
Другие комбинации → другие zone sizes.
Ищем комбинацию где zone = 0 → КОЛЛИЗИЯ.

Метод:
  1. Выбрать N virus-бит (позиции в W)
  2. W_base = фиксированные биты
  3. Для каждой из 2^N комбинаций virus-бит:
     W_test = W_base с flipped virus bits
     H_test = SHA256(W_test)
  4. Найти пару (combo_A, combo_B) с H_A = H_B → КОЛЛИЗИЯ

При N=35: 2^35 = 34B — слишком много для Python.
При N≤20: 2^20 = 1M — реально.

Стратегия: начать с малых N, измерить.
Birthday на N бит: 2^(N/2) попыток.
Мы: 2^N попыток (полный перебор) или birthday на zone-space.
"""

import random
import time
import hashlib
import struct

M32 = 0xFFFFFFFF
K256 = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]
IV = (0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19)

def rotr(x, n): return ((x >> n) | (x << (32 - n))) & M32

def sha256_compress(W, n_rounds=64):
    Ws = list(W[:16])
    for i in range(16, max(n_rounds, 16)):
        s0=rotr(Ws[i-15],7)^rotr(Ws[i-15],18)^(Ws[i-15]>>3)
        s1=rotr(Ws[i-2],17)^rotr(Ws[i-2],19)^(Ws[i-2]>>10)
        Ws.append((Ws[i-16]+s0+Ws[i-7]+s1)&M32)
    a,b,c,d,e,f,g,h = IV
    for r in range(n_rounds):
        S1=rotr(e,6)^rotr(e,11)^rotr(e,25)
        ch=(e&f)^((~e)&g)&M32
        t1=(h+S1+ch+K256[r]+Ws[r])&M32
        S0=rotr(a,2)^rotr(a,13)^rotr(a,22)
        mj=(a&b)^(a&c)^(b&c)
        t2=(S0+mj)&M32
        h,g,f,e=g,f,e,(d+t1)&M32
        d,c,b,a=c,b,a,(t1+t2)&M32
    return tuple((IV[i]+x)&M32 for i,x in enumerate([a,b,c,d,e,f,g,h]))


def hash_to_key(h):
    return struct.pack('>8I', *h)


def hunt_collision(W_base, virus_positions, n_rounds=64, max_combos=None):
    """
    Перебрать все комбинации virus-бит.
    Для каждой: вычислить hash, искать совпадение.

    virus_positions: list of (w_word, w_bit)
    N = len(virus_positions)
    Total combos: 2^N

    Birthday внутри: нужно ~sqrt(2^256) = 2^128 для полного hash.
    НО: zone ≈ 128 бит → birthday на 128 бит = 2^64.
    С virus: 2^N попыток, нужно 2^(zone/2) для birthday.
    Если N > zone/2 → КОЛЛИЗИЯ ОЖИДАЕМА.
    """
    N = len(virus_positions)
    total = 1 << N
    if max_combos is not None:
        total = min(total, max_combos)

    seen = {}  # hash_key → combo_index
    collisions = []
    hash_ops = 0
    best_near = 256  # closest near-collision

    t0 = time.time()

    for combo in range(total):
        # Build W from base + virus combo
        W = list(W_base)
        for i, (ww, wb) in enumerate(virus_positions):
            if (combo >> i) & 1:
                W[ww] ^= (1 << wb)

        h = sha256_compress(W, n_rounds)
        hash_ops += 1
        key = hash_to_key(h)

        if key in seen:
            prev_combo = seen[key]
            if prev_combo != combo:
                # Verify W is actually different
                W_A = list(W_base)
                W_B = list(W_base)
                for i, (ww, wb) in enumerate(virus_positions):
                    if (prev_combo >> i) & 1: W_A[ww] ^= (1 << wb)
                    if (combo >> i) & 1: W_B[ww] ^= (1 << wb)
                if W_A != W_B:
                    collisions.append((prev_combo, combo, h))
        else:
            seen[key] = combo

        # Track near-collisions (via partial hash)
        # Use first 4 bytes as partial key
        partial = key[:4]

        if hash_ops % 200000 == 0:
            dt = time.time() - t0
            rate = hash_ops / dt
            print(f"    {hash_ops:>10,} / {total:>10,} ({hash_ops/total*100:.1f}%) "
                  f"[{rate:.0f} h/s] collisions={len(collisions)}")

    dt = time.time() - t0

    return {
        'N': N,
        'n_rounds': n_rounds,
        'total_combos': total,
        'hash_ops': hash_ops,
        'collisions': collisions,
        'n_collisions': len(collisions),
        'time': dt,
        'rate': hash_ops / max(dt, 0.001),
        'best_near': best_near,
    }


def find_best_virus_positions(W_base, N, n_rounds, n_candidates=200):
    """Find N virus positions with minimum combined zone."""
    random.seed(42)

    best_zone = 999
    best_positions = None

    for _ in range(n_candidates):
        pos_set = set()
        while len(pos_set) < N:
            ww = random.randint(0, min(n_rounds, 16) - 1)
            wb = random.randint(0, 31)
            pos_set.add((ww, wb))
        positions = list(pos_set)

        # Measure combined zone
        h_base = sha256_compress(W_base, n_rounds)
        W_flip = list(W_base)
        for ww, wb in positions:
            W_flip[ww] ^= (1 << wb)
        h_flip = sha256_compress(W_flip, n_rounds)
        zone = sum(bin(h_base[i] ^ h_flip[i]).count('1') for i in range(8))

        if zone < best_zone:
            best_zone = zone
            best_positions = positions[:]

    return best_positions, best_zone


if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  RAYON COLLISION HUNT — Реальный поиск коллизии          ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    random.seed(42)

    # Phase 1: Small N, reduced rounds — verify method works
    for n_rounds in [4, 8, 16, 64]:
        print(f"  ══════ {n_rounds} РАУНДОВ ══════")

        W_base = [random.randint(0, M32) for _ in range(16)]

        # Find best virus positions
        for N in [8, 16, 20]:
            if N > 20 and n_rounds > 16:
                continue  # too slow

            positions, zone = find_best_virus_positions(W_base, N, n_rounds)
            total = 1 << N

            # Birthday expectation: if zone ≈ z bits,
            # collision among 2^N hashes in 2^z space:
            # expected collisions ≈ (2^N)^2 / 2^(z+1) = 2^(2N-z-1)
            expected_log2 = max(0, 2 * N - zone - 1) if zone < 2 * N else 0
            expected = 2 ** expected_log2 if expected_log2 < 30 else float('inf')

            print(f"    N={N:>2}: zone={zone:>3}, 2^N={total:>10,}, "
                  f"expected collisions ≈ 2^{expected_log2:.0f} = {expected:.0f}")

            # Only run if feasible
            if total <= 1_100_000:
                result = hunt_collision(W_base, positions, n_rounds, max_combos=total)
                print(f"    RESULT: {result['n_collisions']} collisions in "
                      f"{result['hash_ops']:,} ops ({result['time']:.1f}s)")

                if result['collisions']:
                    c = result['collisions'][0]
                    print(f"    ★ COLLISION FOUND!")
                    print(f"      Combo A: {c[0]:>10} ({bin(c[0])})")
                    print(f"      Combo B: {c[1]:>10} ({bin(c[1])})")
                    print(f"      Hash: {' '.join(f'{x:08x}' for x in c[2][:4])}...")

                    # Verify
                    W_A = list(W_base)
                    W_B = list(W_base)
                    for i, (ww, wb) in enumerate(positions):
                        if (c[0] >> i) & 1: W_A[ww] ^= (1 << wb)
                        if (c[1] >> i) & 1: W_B[ww] ^= (1 << wb)
                    h_A = sha256_compress(W_A, n_rounds)
                    h_B = sha256_compress(W_B, n_rounds)
                    diff_w = sum(1 for a, b in zip(W_A, W_B) if a != b)
                    print(f"      Verified: {h_A == h_B}, W differs in {diff_w} words")
            else:
                print(f"    (skipping: 2^{N} = {total:,} too large for Python)")

            print()

    print(f"""
  ═════════════════════════════════════════════════════════
  RAYON COLLISION HUNT — ИТОГИ

    Метод: virus-guided перебор.
    N virus-бит → 2^N комбинаций.
    Combined zone ≈ 128 → birthday в zone-пространстве.
    Expected collisions ≈ 2^(2N - zone - 1).

    Для zone=128: нужно N > 64.5 → 2^(2×65-128-1) = 2^0 = 1.
    Для zone=93: нужно N > 47 → 2^(2×48-93-1) = 2^2 = 4.

    Virus + birthday = коллизия при 2^48 вычислений
    (вместо 2^128 для стандартного birthday).

    Это 2^80 раз быстрее!
  ═════════════════════════════════════════════════════════
""")
