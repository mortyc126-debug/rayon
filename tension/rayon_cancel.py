"""
RAYON CANCEL — Компенсация оставшихся бит до полной коллизии.

Имеем: near-collision с 2 бит разницы (carry-guided flip).
Цель: найти ВТОРОЙ flip, который убивает именно эти 2 бита.

Метод:
  1. Найти near-collision: flip A → 2 бита разницы (позиции p1, p2)
  2. Построить INFLUENCE MAP: для каждого W-бита → какие H-биты он меняет
  3. Найти flip B, который меняет РОВНО p1, p2 (и ничего больше)
  4. Применить A ⊕ B → 0 бит разницы = КОЛЛИЗИЯ

Если точного B нет — ищем B который меняет p1, p2 + минимум других.
Потом C который компенсирует остаток. И так далее.

Это RAYON CANCEL: не перебор, а структурная компенсация.
"""

import random
import time

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

def sha256_nr(W, n_rounds):
    Ws = list(W[:16])
    for i in range(16, max(n_rounds, 16)):
        s0 = rotr(Ws[i-15],7)^rotr(Ws[i-15],18)^(Ws[i-15]>>3)
        s1 = rotr(Ws[i-2],17)^rotr(Ws[i-2],19)^(Ws[i-2]>>10)
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


def hash_diff(h1, h2):
    """Вернуть множество позиций различающихся бит."""
    diff_positions = set()
    for word in range(8):
        d = h1[word] ^ h2[word]
        for bit in range(32):
            if (d >> bit) & 1:
                diff_positions.add(word * 32 + bit)
    return diff_positions


def diff_count(h1, h2):
    return sum(bin(a ^ b).count('1') for a, b in zip(h1, h2))


def build_influence_map(W_base, n_rounds):
    """
    Для каждого W-бита: какие H-биты он переключает?
    Возвращает: {(w_word, w_bit): set of h_bit_positions}
    """
    h_base = sha256_nr(W_base, n_rounds)
    influence = {}
    active_words = min(n_rounds, 16)

    for w_word in range(active_words):
        for w_bit in range(32):
            W_flip = list(W_base)
            W_flip[w_word] ^= (1 << w_bit)
            h_flip = sha256_nr(W_flip, n_rounds)
            diff = hash_diff(h_base, h_flip)
            influence[(w_word, w_bit)] = diff

    return influence, h_base


def cancel_search(n_rounds, n_attempts=20, budget_per_attempt=50000):
    """
    RAYON CANCEL: найти коллизию через компенсацию.

    Для нескольких random W_base:
      1. Построить influence map
      2. Найти flip A с минимальным влиянием
      3. Найти flip B, компенсирующий A
      4. Если A⊕B не даёт 0 → итеративно добавлять flips
    """
    random.seed(42)
    t0 = time.time()
    total_ops = 0
    best_global_diff = 256
    best_collision = None

    for attempt in range(n_attempts):
        W_base = [random.randint(0, M32) for _ in range(16)]
        influence, h_base = build_influence_map(W_base, n_rounds)
        total_ops += min(n_rounds, 16) * 32

        # Sort by influence size
        sorted_flips = sorted(influence.items(), key=lambda x: len(x[1]))

        # Phase 1: найти лучший одиночный flip
        best_single = sorted_flips[0]
        flip_a = best_single[0]
        diff_a = best_single[1]

        if len(diff_a) == 0:
            # Тривиальная коллизия (не должно быть если W[r] active)
            continue

        # Phase 2: найти flip B, компенсирующий diff_a
        # Идеальный B: influence(B) == diff_a (XOR отменит)
        # Реальный B: influence(B) ∩ diff_a максимально, остаток минимален
        best_pair_diff = len(diff_a)
        best_pair = None

        for (wb, bb), diff_b in sorted_flips:
            if (wb, bb) == flip_a:
                continue

            # Комбинированный diff: (diff_a ⊕ diff_b)
            # Биты, которые flip A и flip B оба меняют → отменяются
            # Биты, которые только один меняет → остаются
            combined = diff_a.symmetric_difference(diff_b)

            if len(combined) < best_pair_diff:
                best_pair_diff = len(combined)
                best_pair = ((flip_a, diff_a), ((wb, bb), diff_b))

                if len(combined) == 0:
                    break  # Идеальная компенсация!

        # Phase 3: проверить пару на реальном hash
        if best_pair and best_pair_diff < len(diff_a):
            (fa, _), (fb, _) = best_pair
            W_test = list(W_base)
            W_test[fa[0]] ^= (1 << fa[1])
            W_test[fb[0]] ^= (1 << fb[1])
            h_test = sha256_nr(W_test, n_rounds)
            total_ops += 1
            real_diff = diff_count(h_base, h_test)

            if real_diff < best_global_diff:
                best_global_diff = real_diff
                best_collision = {
                    'W_base': W_base[:4],
                    'flips': [fa, fb],
                    'predicted_diff': best_pair_diff,
                    'real_diff': real_diff,
                }

            if real_diff == 0:
                # КОЛЛИЗИЯ!
                dt = time.time() - t0
                return {
                    'found': True,
                    'type': 'PAIR CANCEL',
                    'n_rounds': n_rounds,
                    'W_base': W_base,
                    'flips': [fa, fb],
                    'hash': h_test,
                    'ops': total_ops,
                    'time': dt,
                    'attempt': attempt,
                }

        # Phase 4: тройки (если пары не хватило)
        if best_pair and best_pair_diff > 0 and best_pair_diff <= 8:
            (fa, da), (fb, db) = best_pair
            residual = da.symmetric_difference(db)

            for (wc, bc), diff_c in sorted_flips:
                if (wc, bc) in (fa, fb):
                    continue

                triple_diff = residual.symmetric_difference(diff_c)
                if len(triple_diff) < best_pair_diff:
                    # Проверяем тройку
                    W_test = list(W_base)
                    W_test[fa[0]] ^= (1 << fa[1])
                    W_test[fb[0]] ^= (1 << fb[1])
                    W_test[wc] ^= (1 << bc)
                    h_test = sha256_nr(W_test, n_rounds)
                    total_ops += 1
                    real_diff = diff_count(h_base, h_test)

                    if real_diff < best_global_diff:
                        best_global_diff = real_diff
                        best_collision = {
                            'W_base': W_base[:4],
                            'flips': [fa, fb, (wc, bc)],
                            'predicted_diff': len(triple_diff),
                            'real_diff': real_diff,
                        }

                    if real_diff == 0:
                        dt = time.time() - t0
                        return {
                            'found': True,
                            'type': 'TRIPLE CANCEL',
                            'n_rounds': n_rounds,
                            'W_base': W_base,
                            'flips': [fa, fb, (wc, bc)],
                            'hash': h_test,
                            'ops': total_ops,
                            'time': dt,
                            'attempt': attempt,
                        }

        # Phase 5: random multi-flip guided by influence
        low_influence = [pos for pos, diff in sorted_flips[:32]]  # top-32 lowest
        if len(low_influence) < 2:
            continue
        for trial in range(budget_per_attempt):
            n_flips = random.randint(2, min(6, len(low_influence)))
            flips = random.sample(low_influence, n_flips)

            W_test = list(W_base)
            for w_word, w_bit in flips:
                W_test[w_word] ^= (1 << w_bit)

            h_test = sha256_nr(W_test, n_rounds)
            total_ops += 1
            real_diff = diff_count(h_base, h_test)

            if real_diff < best_global_diff:
                best_global_diff = real_diff
                best_collision = {
                    'W_base': W_base[:4],
                    'flips': flips,
                    'real_diff': real_diff,
                }

            if real_diff == 0:
                dt = time.time() - t0
                return {
                    'found': True,
                    'type': 'MULTI CANCEL',
                    'n_rounds': n_rounds,
                    'W_base': W_base,
                    'flips': flips,
                    'hash': h_test,
                    'ops': total_ops,
                    'time': dt,
                    'attempt': attempt,
                }

    dt = time.time() - t0
    return {
        'found': False,
        'n_rounds': n_rounds,
        'best_diff': best_global_diff,
        'best': best_collision,
        'ops': total_ops,
        'time': dt,
    }


if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  RAYON CANCEL — Компенсация до коллизии                  ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Phase 1: influence analysis
    print("  INFLUENCE MAP (какой W-бит меняет сколько H-бит):")
    print("  " + "─" * 55)

    random.seed(42)
    W = [random.randint(0, M32) for _ in range(16)]

    for nr in [4, 8, 16, 32, 64]:
        influence, h = build_influence_map(W, nr)
        sizes = sorted([len(d) for d in influence.values()])
        active = min(nr, 16) * 32
        print(f"    {nr:>2} rounds ({active:>3} active W-bits): "
              f"min={sizes[0]:>3}, median={sizes[len(sizes)//2]:>3}, "
              f"max={sizes[-1]:>3} H-bits affected")

    # Phase 2: cancel search
    print()
    print("  CANCEL SEARCH:")
    print("  " + "─" * 55)

    for nr in [4, 8, 16, 24, 32]:
        budget = 100000 if nr <= 16 else 20000
        result = cancel_search(nr, n_attempts=10, budget_per_attempt=budget)

        if result['found']:
            print(f"    {nr:>2} rounds: ★ COLLISION! type={result['type']}, "
                  f"flips={len(result['flips'])}, "
                  f"{result['ops']:,} ops, {result['time']:.1f}s")
            print(f"      Flips: {result['flips']}")
            print(f"      Hash: {' '.join(f'{x:#010x}' for x in result['hash'][:4])} ...")
        else:
            best = result.get('best', {})
            print(f"    {nr:>2} rounds: best={result['best_diff']:>3}/256 diff, "
                  f"{result['ops']:,} ops, {result['time']:.1f}s")
            if best and 'flips' in best:
                print(f"      Best flips: {best['flips'][:3]}...")

    print(f"""
  ═══════════════════════════════════════════════════════
  RAYON CANCEL:

    Метод: carry-guided influence → компенсация.
    Не перебор всех комбинаций.
    СТРУКТУРНЫЙ поиск: flip A → diff → flip B → cancel.

    Carry algebra говорит ГДЕ flipать (low-influence позиции).
    XOR-линейность говорит КАК комбинировать.
    Kill-links говорят КОГДА остановиться.
  ═══════════════════════════════════════════════════════
""")
