"""
RAYON COMBINED — Комбинированная атака из всего арсенала.

СТРАТЕГИЯ: не пытаемся одним ударом. Комбинируем ВСЕ оружия.

COMBO 1: MULTI-BLOCK + VIRUS
  Воронки: multi-block collision работает на 4-8-16 бит (verified).
  Проблема: не масштабируется на 32-bit (цикл > 2^128).
  РЕШЕНИЕ: использовать virus reverse map для СУЖЕНИЯ перебора
  внутри multi-block framework.

COMBO 2: GF2 SCHEDULE + CARRY PAIR
  GF2: 15/16 schedule слов обнулимы (32 бита свободы).
  Carry pair: zone=2 при ≤16 раундах.
  КОМБИНАЦИЯ: GF2-контролированный schedule + carry pair в last round.

COMBO 3: NEAR-COLLISION AMPLIFICATION
  Near-collision: 2/256 бит при ≤16 раундах.
  Multi-virus cancel: 63% при 64 раундах.
  КОМБИНАЦИЯ: несколько near-collisions, компенсированных interference.

COMBO 4: BIRTHDAY В REDUCED SPACE
  Zone=128 constant → birthday на zone = 2^64.
  НО: zone=128 = стандартный avalanche.
  А ЧТО ЕСЛИ birthday не на полном hash, а на PARTIAL?
  Bioattack: 107 unique reverse-mapped бит.
  Birthday на 107 бит unique = 2^53.5.
  При 2^54 virus-комбинаций → ожидаем partial collision.
  Partial collision + interference cancel → extend?

Тестируем ВСЕ комбо.
"""

import random
import time
import struct

M32 = 0xFFFFFFFF
K256 = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]
IV = (0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19)

def rotr(x,n): return ((x>>n)|(x<<(32-n)))&M32

def sha256(W, n_rounds=64):
    Ws=list(W[:16])
    for i in range(16,max(n_rounds,16)):
        s0=rotr(Ws[i-15],7)^rotr(Ws[i-15],18)^(Ws[i-15]>>3)
        s1=rotr(Ws[i-2],17)^rotr(Ws[i-2],19)^(Ws[i-2]>>10)
        Ws.append((Ws[i-16]+s0+Ws[i-7]+s1)&M32)
    a,b,c,d,e,f,g,h=IV
    for r in range(n_rounds):
        S1=rotr(e,6)^rotr(e,11)^rotr(e,25); ch=(e&f)^((~e)&g)&M32
        t1=(h+S1+ch+K256[r]+Ws[r])&M32
        S0=rotr(a,2)^rotr(a,13)^rotr(a,22); mj=(a&b)^(a&c)^(b&c)
        t2=(S0+mj)&M32
        h,g,f,e=g,f,e,(d+t1)&M32; d,c,b,a=c,b,a,(t1+t2)&M32
    return tuple((IV[i]+x)&M32 for i,x in enumerate([a,b,c,d,e,f,g,h]))

def zone(h1,h2): return sum(bin(a^b).count('1') for a,b in zip(h1,h2))
def hkey(h): return struct.pack('>8I',*h)


def combo1_multiblock_virus(n_rounds=64, n_blocks=100, n_first=5000):
    """
    COMBO 1: Multi-block + virus.

    Multi-block: M = [W1, W2, W2, ..., W2]
    Fix W2. Vary W1. After enough W2 blocks → state converges.

    TWIST: don't vary ALL of W1. Vary only virus-бит.
    Fewer virus bits → fewer combinations → faster birthday.

    N virus bits in W1 → 2^N distinct starting states.
    After convergence: hash determined by starting state.
    Birthday in 2^N space → collision at 2^(N/2).

    If N=40: birthday = 2^20 = 1M → feasible in Python!
    """
    random.seed(42)
    W2 = [random.randint(0, M32) for _ in range(16)]

    # Pick virus positions in W1
    virus_pos = [(random.randint(0,15), random.randint(0,31)) for _ in range(20)]
    virus_pos = list(set(virus_pos))[:20]
    N = len(virus_pos)

    W1_base = [random.randint(0, M32) for _ in range(16)]

    seen = {}
    collisions = []
    hash_ops = 0
    t0 = time.time()

    for trial in range(min(n_first, 1 << N)):
        # Random virus combo
        combo = random.getrandbits(N)
        W1 = list(W1_base)
        for i, (ww, wb) in enumerate(virus_pos):
            if (combo >> i) & 1:
                W1[ww] ^= (1 << wb)

        # Process: W1 then n_blocks of W2
        state = sha256(W1, n_rounds)
        hash_ops += 1
        for _ in range(n_blocks):
            # Compress state with W2
            Ws = list(W2[:16])
            for i in range(16, max(n_rounds,16)):
                s0=rotr(Ws[i-15],7)^rotr(Ws[i-15],18)^(Ws[i-15]>>3)
                s1=rotr(Ws[i-2],17)^rotr(Ws[i-2],19)^(Ws[i-2]>>10)
                Ws.append((Ws[i-16]+s0+Ws[i-7]+s1)&M32)
            a,b,c,d,e,f,g,h = state
            for r in range(n_rounds):
                S1=rotr(e,6)^rotr(e,11)^rotr(e,25); ch=(e&f)^((~e)&g)&M32
                t1=(h+S1+ch+K256[r]+Ws[r])&M32
                S0=rotr(a,2)^rotr(a,13)^rotr(a,22); mj=(a&b)^(a&c)^(b&c)
                t2=(S0+mj)&M32
                h,g,f,e=g,f,e,(d+t1)&M32; d,c,b,a=c,b,a,(t1+t2)&M32
            state = tuple((state[i]+x)&M32 for i,x in enumerate([a,b,c,d,e,f,g,h]))
            hash_ops += 1

        key = hkey(state)
        if key in seen:
            prev = seen[key]
            if prev != combo:
                collisions.append((prev, combo, state))
        else:
            seen[key] = combo

    dt = time.time() - t0
    return {
        'n_rounds': n_rounds,
        'n_blocks': n_blocks,
        'N_virus': N,
        'n_trials': min(n_first, 1 << N),
        'collisions': len(collisions),
        'hash_ops': hash_ops,
        'time': dt,
        'details': collisions[:3],
    }


def combo2_partial_birthday(n_rounds=64, budget=500000):
    """
    COMBO 2: Birthday на PARTIAL hash.

    Не на полном 256-bit hash. На ПОДМНОЖЕСТВЕ бит.
    Какое подмножество? → Биты, которые virus reverse map
    связывает с КОНКРЕТНЫМИ virus-битами.

    Если 2 сообщения совпадают в partial bits → partial collision.
    Стоимость: 2^(partial_bits/2).

    partial_bits = 32 (1 word) → birthday = 2^16 = 65K
    partial_bits = 64 (2 words) → birthday = 2^32 = 4B (нужен C)
    """
    random.seed(42)

    results = []
    for partial_words in [1, 2]:
        partial_bits = partial_words * 32
        seen = {}
        collisions = []
        hash_ops = 0
        t0 = time.time()

        for trial in range(budget):
            W = [random.randint(0, M32) for _ in range(16)]
            h = sha256(W, n_rounds)
            hash_ops += 1

            # Partial key: first partial_words words
            key = tuple(h[:partial_words])

            if key in seen:
                prev_W = seen[key]
                h_prev = sha256(list(prev_W), n_rounds)
                full_match = h == h_prev
                partial_match = True
                full_diff = zone(h, h_prev)
                collisions.append({
                    'full_match': full_match,
                    'full_diff': full_diff,
                })
            else:
                seen[key] = tuple(W)

        dt = time.time() - t0
        n_full = sum(1 for c in collisions if c['full_match'])
        avg_diff = sum(c['full_diff'] for c in collisions) / max(len(collisions), 1)

        results.append({
            'partial_bits': partial_bits,
            'partial_collisions': len(collisions),
            'full_collisions': n_full,
            'avg_remaining_diff': avg_diff,
            'hash_ops': hash_ops,
            'time': dt,
        })

    return results


def combo3_reduced_round_extend(budget=200000):
    """
    COMBO 3: Коллизия на reduced rounds → extend.

    1 round: 37 коллизий за 500K (доказано).
    Вопрос: коллизия на r раундах — сколько бит совпадают при r+1?

    Если r-round collision → partial match at r+1 → extend chain.
    """
    random.seed(42)

    for target_rounds in [1, 2]:
        seen = {}
        collisions = []
        hash_ops = 0

        # Find collision at target_rounds
        for trial in range(budget):
            W = [random.randint(0, M32) for _ in range(16)]
            h = sha256(W, target_rounds)
            hash_ops += 1

            key = hkey(h)
            if key in seen:
                prev_W = seen[key]
                collisions.append((list(prev_W), W))
                if len(collisions) >= 20:
                    break
            else:
                seen[key] = tuple(W)

        print(f"    {target_rounds}-round: {len(collisions)} collisions in {hash_ops:,} ops")

        # For each collision: how many bits match at higher rounds?
        if collisions:
            for ext_rounds in [target_rounds+1, target_rounds+2, target_rounds+4, 8, 16, 64]:
                diffs = []
                for W_a, W_b in collisions[:10]:
                    h_a = sha256(W_a, ext_rounds)
                    h_b = sha256(W_b, ext_rounds)
                    diffs.append(zone(h_a, h_b))
                avg = sum(diffs) / len(diffs)
                print(f"      → at {ext_rounds:>2} rounds: avg diff = {avg:.1f}/256 bits")


def combo4_all_weapons(n_rounds=64, budget=1000000):
    """
    COMBO 4: ВСЁ ВМЕСТЕ.

    1. Birthday на partial hash (32 бит = H[0])
    2. Для каждой partial collision: проверяем virus reverse map
    3. Используем interference cancel для оставшихся бит
    4. Проверяем полный hash

    Pipeline:
      Random W → H[0] birthday → partial collision →
      check H[4] (dual path correlation?) →
      check remaining 192 bits
    """
    random.seed(42)
    t0 = time.time()

    # Stage 1: Birthday on H[0] (32 bits) → need ~2^16 = 65K
    seen_h0 = {}
    partial_collisions = []
    hash_ops = 0

    for trial in range(budget):
        W = [random.randint(0, M32) for _ in range(16)]
        h = sha256(W, n_rounds)
        hash_ops += 1

        key = h[0]  # just first word (32 bits)
        if key in seen_h0:
            prev_W = seen_h0[key]
            h_prev = sha256(list(prev_W), n_rounds)
            # Check: how many MORE words match?
            matching_words = sum(1 for a, b in zip(h, h_prev) if a == b)
            total_diff = zone(h, h_prev)
            partial_collisions.append({
                'matching_words': matching_words,
                'total_diff': total_diff,
                'h': h,
                'h_prev': h_prev,
            })
        else:
            seen_h0[key] = tuple(W)

    dt = time.time() - t0

    # Analysis
    n_partial = len(partial_collisions)
    if n_partial > 0:
        # How many words match on average?
        avg_match = sum(c['matching_words'] for c in partial_collisions) / n_partial
        avg_diff = sum(c['total_diff'] for c in partial_collisions) / n_partial
        max_match = max(c['matching_words'] for c in partial_collisions)
        min_diff = min(c['total_diff'] for c in partial_collisions)

        # Check dual path: if H[0] matches, does H[4] tend to match too?
        h4_matches = sum(1 for c in partial_collisions
                        if c['h'][4] == c['h_prev'][4])

        full_collisions = sum(1 for c in partial_collisions
                             if c['total_diff'] == 0)
    else:
        avg_match = avg_diff = max_match = min_diff = 0
        h4_matches = full_collisions = 0

    return {
        'budget': budget,
        'hash_ops': hash_ops,
        'partial_collisions_h0': n_partial,
        'full_collisions': full_collisions,
        'avg_matching_words': avg_match,
        'avg_diff': avg_diff,
        'max_matching_words': max_match,
        'min_diff': min_diff,
        'h4_also_matches': h4_matches,
        'dual_path_rate': h4_matches / max(n_partial, 1),
        'time': dt,
    }


if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  RAYON COMBINED — Все оружия вместе                      ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # COMBO 3: Reduced round extension
    print("  COMBO 3: REDUCED ROUND → EXTEND")
    print("  " + "─" * 55)
    combo3_reduced_round_extend(500000)

    # COMBO 2: Partial birthday
    print()
    print("  COMBO 2: PARTIAL BIRTHDAY")
    print("  " + "─" * 55)
    r2 = combo2_partial_birthday(64, 500000)
    for r in r2:
        print(f"    {r['partial_bits']:>3}-bit partial: "
              f"{r['partial_collisions']} partial, {r['full_collisions']} full, "
              f"avg remaining diff={r['avg_remaining_diff']:.1f}, "
              f"{r['time']:.1f}s")

    # COMBO 4: All weapons pipeline
    print()
    print("  COMBO 4: ALL WEAPONS PIPELINE (64 rounds)")
    print("  " + "─" * 55)
    r4 = combo4_all_weapons(64, 500000)
    print(f"    H[0] partial collisions: {r4['partial_collisions_h0']}")
    print(f"    Full collisions: {r4['full_collisions']}")
    print(f"    Avg matching words: {r4['avg_matching_words']:.2f}/8")
    print(f"    Avg diff: {r4['avg_diff']:.1f}/256")
    print(f"    Max matching words: {r4['max_matching_words']}/8")
    print(f"    Min diff: {r4['min_diff']}/256")
    print(f"    Dual path H[4]: {r4['h4_also_matches']}/{r4['partial_collisions_h0']} "
          f"= {r4['dual_path_rate']:.4f}")
    print(f"    Time: {r4['time']:.1f}s, Ops: {r4['hash_ops']:,}")

    # COMBO 1: Multi-block virus (reduced budget for speed)
    print()
    print("  COMBO 1: MULTI-BLOCK + VIRUS (64 rounds, 50 blocks)")
    print("  " + "─" * 55)
    r1 = combo1_multiblock_virus(64, n_blocks=50, n_first=2000)
    print(f"    {r1['N_virus']} virus bits, {r1['n_blocks']} blocks, "
          f"{r1['n_trials']} trials")
    print(f"    Collisions: {r1['collisions']}")
    print(f"    Hash ops: {r1['hash_ops']:,}, Time: {r1['time']:.1f}s")

    # Summary
    print(f"""
  ═════════════════════════════════════════════════════════
  RAYON COMBINED — ВСЕ КОМБО РЕЗУЛЬТАТЫ:

    COMBO 1 (Multi-block + virus):
      {r1['collisions']} collisions. Multi-block convergence + virus freedom.

    COMBO 2 (Partial birthday):
      32-bit: {r2[0]['partial_collisions']} partial collisions
      64-bit: {r2[1]['partial_collisions']} partial collisions
      Full: {r2[0]['full_collisions'] + r2[1]['full_collisions']}

    COMBO 3 (Reduced round extend):
      1-round collision → extends to higher rounds with diff.

    COMBO 4 (All weapons pipeline):
      {r4['partial_collisions_h0']} H[0]-collisions, max {r4['max_matching_words']}/8 words match.
      Dual path: {r4['dual_path_rate']:.4f} (independent at 64 rounds).
      Min diff: {r4['min_diff']}/256 bits.

    BEST ATTACK: Partial birthday on 32-bit H[0]
      → {r2[0]['partial_collisions']} partial collisions
      → avg {r2[0]['avg_remaining_diff']:.0f} remaining diff bits
      → need to resolve ~{r2[0]['avg_remaining_diff']:.0f} bits
  ═════════════════════════════════════════════════════════
""")
