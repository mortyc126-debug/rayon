"""
RAYON CONTAINMENT — Carry kill-links как стены контейнмента.

Вирус заражает ~50% output при 64 раундах потому что
carry chains НЕСУТ его через ВСЕ биты слова.

Контейнмент: окружить virus-бит стенами G/K.
G/K = carry ИЗВЕСТЕН → virus ОСТАНАВЛИВАЕТСЯ.

Если bit k = virus(?), а bit k-1 = K и bit k+1 = G:
  → virus не распространяется ни вниз, ни вверх через carry.
  → зона заражения = РОВНО 2 бита (carry pair).

Вопрос: можно ли ВЫБРАТЬ W_base так, чтобы
carry kill map создавал контейнмент на нужных позициях
через все 64 раунда?
"""

import random
import time

M32 = 0xFFFFFFFF
K256 = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]
IV = (0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19)

def rotr(x, n): return ((x >> n) | (x << (32 - n))) & M32

def sha256_compress(state, W, n_rounds=64):
    Ws = list(W[:16])
    for i in range(16, max(n_rounds, 16)):
        s0=rotr(Ws[i-15],7)^rotr(Ws[i-15],18)^(Ws[i-15]>>3)
        s1=rotr(Ws[i-2],17)^rotr(Ws[i-2],19)^(Ws[i-2]>>10)
        Ws.append((Ws[i-16]+s0+Ws[i-7]+s1)&M32)
    a,b,c,d,e,f,g,h = state
    for r in range(n_rounds):
        S1=rotr(e,6)^rotr(e,11)^rotr(e,25)
        ch=(e&f)^((~e)&g)&M32
        t1=(h+S1+ch+K256[r]+Ws[r])&M32
        S0=rotr(a,2)^rotr(a,13)^rotr(a,22)
        mj=(a&b)^(a&c)^(b&c)
        t2=(S0+mj)&M32
        h,g,f,e=g,f,e,(d+t1)&M32
        d,c,b,a=c,b,a,(t1+t2)&M32
    return tuple((state[i]+x)&M32 for i,x in enumerate([a,b,c,d,e,f,g,h]))


def infection_zone(W_base, w_word, w_bit, n_rounds=64):
    h0 = sha256_compress(IV, W_base, n_rounds)
    W2 = list(W_base); W2[w_word] ^= (1 << w_bit)
    h1 = sha256_compress(IV, W2, n_rounds)
    zone = set()
    for hw in range(8):
        d = h0[hw] ^ h1[hw]
        for hb in range(32):
            if (d >> hb) & 1:
                zone.add((hw, hb))
    return zone


def measure_containment(n_rounds, n_trials=500):
    """
    Для каждого W_base и каждого W-бита: зона заражения.
    Ищем пары (W_base, bit_position) с МИНИМАЛЬНОЙ зоной.

    Минимум = 2 (carry pair). Это идеальный контейнмент.
    Средне = ~128 (50% выхода).
    Максимум = ~150.
    """
    random.seed(42)

    # Measure: for many W_base, find bits with zone=2
    zone2_count = 0
    zone2_examples = []
    zone_hist = [0] * 257
    total_measured = 0

    for trial in range(n_trials):
        W = [random.randint(0, M32) for _ in range(16)]
        active = min(n_rounds, 16)

        for ww in range(active):
            # Sample bits
            for wb in range(0, 32, 2):
                zone = infection_zone(W, ww, wb, n_rounds)
                zsize = len(zone)
                zone_hist[zsize] += 1
                total_measured += 1

                if zsize == 2:
                    zone2_count += 1
                    if len(zone2_examples) < 10:
                        zone2_examples.append((trial, ww, wb, zone))

    return {
        'zone2_count': zone2_count,
        'total': total_measured,
        'zone2_rate': zone2_count / max(total_measured, 1),
        'zone2_examples': zone2_examples,
        'zone_hist': zone_hist,
    }


def find_contained_virus(n_rounds=64, budget=2000):
    """
    Найти вирус с МИНИМАЛЬНОЙ зоной при полных n раундах.

    На 1-16 раундах: зона=2 (carry pair) гарантирована в W[n-1].
    На 64 раундах: зона≈128. Но может ли быть МЕНЬШЕ для
    специально подобранного W_base?

    Если да → контейнмент работает на полных раундах.
    Если нет → контейнмент работает только в Зоне I (≤16 раундов).
    """
    random.seed(42)

    best_zone_size = 256
    best_W = None
    best_pos = None
    best_zone = None

    zone_sizes = []

    for trial in range(budget):
        W = [random.randint(0, M32) for _ in range(16)]

        # Sample 8 bit positions per trial
        for _ in range(8):
            ww = random.randint(0, min(n_rounds, 16) - 1)
            wb = random.randint(0, 31)

            zone = infection_zone(W, ww, wb, n_rounds)
            zs = len(zone)
            zone_sizes.append(zs)

            if zs < best_zone_size:
                best_zone_size = zs
                best_W = W[:]
                best_pos = (ww, wb)
                best_zone = zone

    return {
        'best_zone_size': best_zone_size,
        'best_W': best_W,
        'best_pos': best_pos,
        'best_zone': best_zone,
        'zone_sizes': zone_sizes,
        'min': min(zone_sizes),
        'avg': sum(zone_sizes) / len(zone_sizes),
        'max': max(zone_sizes),
    }


def containment_wall_analysis(W_base, n_rounds=64):
    """
    Для данного W_base: анализ carry kill map через все раунды.

    Вопрос: если разместить virus на позиции k в последнем раунде,
    какие СТЕНЫ (G/K) окружают его?

    Carry propagation:
      bit k-1 = G или K → стена СНИЗУ (virus не получит carry-?)
      bit k+1 = G или K → стена СВЕРХУ (virus carry не пройдёт выше)

    Если обе стены → virus изолирован в 1 бит
    → зона = 2 (carry pair: bit k в new_a и new_e)
    """
    Ws = list(W_base[:16])
    for i in range(16, max(n_rounds, 16)):
        s0=rotr(Ws[i-15],7)^rotr(Ws[i-15],18)^(Ws[i-15]>>3)
        s1=rotr(Ws[i-2],17)^rotr(Ws[i-2],19)^(Ws[i-2]>>10)
        Ws.append((Ws[i-16]+s0+Ws[i-7]+s1)&M32)

    a,b,c,d,e,f,g,h = IV
    wall_data = []

    for r in range(n_rounds):
        S1=rotr(e,6)^rotr(e,11)^rotr(e,25)
        ch_val=(e&f)^((~e)&g)&M32
        t1=(h+S1+ch_val+K256[r]+Ws[r])&M32
        S0=rotr(a,2)^rotr(a,13)^rotr(a,22)
        mj=(a&b)^(a&c)^(b&c)
        t2=(S0+mj)&M32

        # Carry map for new_a = t1 + t2
        g_a = t1 & t2
        p_a = t1 ^ t2
        k_a = (~(t1 | t2)) & M32
        absorber_a = g_a | k_a

        # Carry map for new_e = d + t1
        g_e = d & t1
        p_e = d ^ t1
        k_e = (~(d | t1)) & M32
        absorber_e = g_e | k_e

        # For each bit: is it CONTAINED? (absorbers on both sides)
        contained_a = 0
        contained_e = 0
        for bit in range(32):
            wall_below = (bit == 0) or ((absorber_a >> (bit-1)) & 1)
            wall_above = (bit == 31) or ((absorber_a >> (bit+1)) & 1)
            if wall_below and wall_above:
                contained_a += 1

            wall_below_e = (bit == 0) or ((absorber_e >> (bit-1)) & 1)
            wall_above_e = (bit == 31) or ((absorber_e >> (bit+1)) & 1)
            if wall_below_e and wall_above_e:
                contained_e += 1

        # Dual containment: contained in BOTH paths
        dual_contained = 0
        for bit in range(32):
            wa_below = (bit == 0) or ((absorber_a >> (bit-1)) & 1)
            wa_above = (bit == 31) or ((absorber_a >> (bit+1)) & 1)
            we_below = (bit == 0) or ((absorber_e >> (bit-1)) & 1)
            we_above = (bit == 31) or ((absorber_e >> (bit+1)) & 1)
            if wa_below and wa_above and we_below and we_above:
                dual_contained += 1

        wall_data.append({
            'round': r,
            'contained_a': contained_a,
            'contained_e': contained_e,
            'dual_contained': dual_contained,
            'absorber_rate_a': bin(absorber_a).count('1') / 32,
            'absorber_rate_e': bin(absorber_e).count('1') / 32,
        })

        h,g,f,e=g,f,e,(d+t1)&M32
        d,c,b,a=c,b,a,(t1+t2)&M32

    return wall_data


if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  RAYON CONTAINMENT — Стены из carry kill-links           ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # 1. Wall analysis: how many contained positions per round?
    random.seed(42)
    W = [random.randint(0, M32) for _ in range(16)]

    print("  СТЕНЫ КОНТЕЙНМЕНТА (carry kill map):")
    print("  " + "─" * 55)
    walls = containment_wall_analysis(W, 64)

    print(f"  {'round':>6} {'cont_a':>7} {'cont_e':>7} {'dual':>6} {'abs_a%':>7} {'abs_e%':>7}")
    print(f"  {'─'*42}")
    for w in walls:
        r = w['round']
        if r in [0,1,3,7,15,31,47,63]:
            print(f"  {r:>6} {w['contained_a']:>7} {w['contained_e']:>7} "
                  f"{w['dual_contained']:>6} {w['absorber_rate_a']:>6.0%} {w['absorber_rate_e']:>6.0%}")

    avg_dual = sum(w['dual_contained'] for w in walls) / len(walls)
    print(f"  Avg dual-contained per round: {avg_dual:.1f} / 32")

    # 2. Minimum zone search at various rounds
    print()
    print("  МИНИМАЛЬНАЯ ЗОНА ЗАРАЖЕНИЯ:")
    print("  " + "─" * 55)

    for nr in [4, 8, 16, 24, 32, 64]:
        result = find_contained_virus(nr, budget=1000)
        print(f"    {nr:>2} rounds: min={result['min']:>3}, "
              f"avg={result['avg']:>6.1f}, max={result['max']:>3}  "
              f"best at W[{result['best_pos'][0]}][{result['best_pos'][1]}]")

    # 3. Containment rate over rounds
    print()
    print("  ZONE=2 RATE (carry pair containment):")
    print("  " + "─" * 55)

    for nr in [1, 4, 8, 16, 17, 18, 20, 24, 32, 64]:
        cm = measure_containment(nr, n_trials=100)
        rate = cm['zone2_rate'] * 100
        bar = "█" * int(rate)
        print(f"    {nr:>2} rounds: {cm['zone2_count']:>4}/{cm['total']:>5} = {rate:>5.1f}%  {bar}")

    # 4. Key: what is minimum zone achievable at 64 rounds?
    print()
    print("  DEEP SEARCH: minimum zone at 64 rounds (5000 samples)")
    result = find_contained_virus(64, budget=5000)
    print(f"    MINIMUM zone found: {result['best_zone_size']} bits")
    print(f"    At W[{result['best_pos'][0]}][{result['best_pos'][1]}]")
    if result['best_zone']:
        zone_words = {}
        for hw, hb in result['best_zone']:
            zone_words[hw] = zone_words.get(hw, 0) + 1
        print(f"    Zone distribution: {dict(sorted(zone_words.items()))}")

    # Distribution of zone sizes at 64 rounds
    from collections import Counter
    buckets = Counter()
    for zs in result['zone_sizes']:
        if zs <= 10: buckets['1-10'] += 1
        elif zs <= 50: buckets['11-50'] += 1
        elif zs <= 100: buckets['51-100'] += 1
        elif zs <= 130: buckets['101-130'] += 1
        elif zs <= 160: buckets['131-160'] += 1
        else: buckets['161+'] += 1

    print(f"    Zone size distribution at 64 rounds:")
    for bucket in ['1-10', '11-50', '51-100', '101-130', '131-160', '161+']:
        count = buckets.get(bucket, 0)
        bar = "█" * (count // 10)
        print(f"      {bucket:>8}: {count:>5}  {bar}")

    min_zone = result['best_zone_size']
    print(f"""
  ═════════════════════════════════════════════════════════
  RAYON CONTAINMENT — ИТОГИ:

    Стены контейнмента (G/K absorbers):
      Avg dual-contained: {avg_dual:.1f}/32 позиций на раунд
      Absorber rate: ~50% (T1 invariant)

    Минимальная зона заражения:
      ≤ 16 раундов: zone = 2 (carry pair, ~25% шанс)
      17 раунд: zone прыгает (schedule)
      64 раунда: min zone = {min_zone}

    {'★ КОНТЕЙНМЕНТ РАБОТАЕТ на 64 раундах!' if min_zone <= 10 else ''}
    {'Контейнмент эффективен только на ≤16 раундах.' if min_zone > 50 else ''}
    {'Частичный контейнмент на 64 раундах.' if 10 < min_zone <= 50 else ''}

    Вирус с контейнментом:
      zone = {min_zone} → {min_zone} уравнений на 1 virus-бит
      Для 256 unique: нужно ~{256 // max(min_zone, 1)} virus-бит
      → перебор 2^{256 // max(min_zone, 1)}
  ═════════════════════════════════════════════════════════
""")
