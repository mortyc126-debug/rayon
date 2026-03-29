"""
RAYON SUPERVIRUS — Умный, заразный, устойчивый.

Три свойства супервируса:
  1. МАСШТАБИРУЕМОСТЬ: покрыть все 256 output-бит unique-mappings
  2. УСТОЙЧИВОСТЬ: выжить через 64 раунда при разных W_base
  3. ЗАРАЗНОСТЬ: использовать carry chains КАК ОРУЖИЕ, а не врага

Стратегия:
  Bioattack показал: 4 бита → 107 unique при правильном W_base.
  Нужно: найти СКОЛЬКО virus-бит покрывают ВСЕ 256 output-бит.

  Greedy cover: добавлять virus-бит, максимизирующий новые unique.
  Immune evasion: выбирать W_base, где kill-links ПОМОГАЮТ вирусу.
  Weaponized carry: virus на P-chain → carry НЕСЁТ вирус точно куда надо.
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
    """Which output bits flip when we flip W[w_word][w_bit]?"""
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


def greedy_virus_cover(W_base, n_rounds=64, target_unique=256):
    """
    GREEDY COVER: добавлять virus-бит, максимизирующий
    число НОВЫХ unique output-бит.

    unique = output-бит заражён РОВНО одним virus.
    Цель: unique = 256 (все output-биты однозначно mapped).
    """
    all_output = {(w, b) for w in range(8) for b in range(32)}

    # Precompute all infection zones
    zones = {}
    active = min(n_rounds, 16)
    for ww in range(active):
        for wb in range(32):
            zones[(ww, wb)] = infection_zone(W_base, ww, wb, n_rounds)

    selected_virus = []
    covered_by = {}  # output_bit → set of virus bits that reach it

    for out_bit in all_output:
        covered_by[out_bit] = set()

    step = 0
    while True:
        # Find the virus bit that maximizes NEW unique coverage
        best_gain = -1
        best_pos = None

        for pos, zone in zones.items():
            if pos in [v for v, _ in selected_virus]:
                continue

            # Simulate adding this virus
            new_unique = 0
            new_ambiguous_from_unique = 0
            for out_bit in zone:
                current = len(covered_by[out_bit])
                if current == 0:
                    new_unique += 1      # was clean → becomes unique
                elif current == 1:
                    new_ambiguous_from_unique -= 1  # was unique → becomes ambiguous
                    # but the new one itself is also ambiguous

            gain = new_unique + new_ambiguous_from_unique
            if gain > best_gain:
                best_gain = gain
                best_pos = pos
                best_zone = zone

        if best_pos is None or best_gain <= 0:
            # Try any remaining
            for pos, zone in zones.items():
                if pos not in [v for v, _ in selected_virus]:
                    uncovered = zone - set().union(*(z for _, z in selected_virus)) if selected_virus else zone
                    if len(uncovered) > 0:
                        best_pos = pos
                        best_zone = zone
                        break
            if best_pos is None:
                break

        selected_virus.append((best_pos, best_zone))
        for out_bit in best_zone:
            covered_by[out_bit].add(best_pos)

        # Count current stats
        unique = sum(1 for s in covered_by.values() if len(s) == 1)
        ambiguous = sum(1 for s in covered_by.values() if len(s) > 1)
        clean = sum(1 for s in covered_by.values() if len(s) == 0)

        step += 1
        if step <= 20 or step % 10 == 0 or unique >= target_unique:
            print(f"    Step {step:>3}: +W[{best_pos[0]:>2}][{best_pos[1]:>2}] "
                  f"zone={len(best_zone):>3}  "
                  f"unique={unique:>3} ambig={ambiguous:>3} clean={clean:>3}")

        if clean == 0:
            break
        if step > 200:
            break

    # Build reverse map
    unique_map = {}
    for out_bit, sources in covered_by.items():
        if len(sources) == 1:
            unique_map[out_bit] = list(sources)[0]

    return {
        'virus_bits': [pos for pos, _ in selected_virus],
        'n_virus': len(selected_virus),
        'unique': len(unique_map),
        'ambiguous': sum(1 for s in covered_by.values() if len(s) > 1),
        'clean': sum(1 for s in covered_by.values() if len(s) == 0),
        'unique_map': unique_map,
        'covered_by': covered_by,
    }


def immune_evasion(n_candidates=100, n_rounds=64):
    """
    IMMUNE EVASION: найти W_base с лучшей "иммунной дырой".

    Разные W_base → разные carry kill maps → разное выживание.
    Ищем W_base где малое число virus-бит даёт максимум unique.
    """
    random.seed(42)
    best_score = 0
    best_W = None
    best_result = None

    for trial in range(n_candidates):
        W = [random.randint(0, M32) for _ in range(16)]

        # Quick probe: 4 quietest virus bits
        h0 = sha256_compress(IV, W, n_rounds)
        zones = []
        for ww in range(min(n_rounds, 16)):
            for wb in range(0, 32, 4):  # sample every 4th bit
                zone = infection_zone(W, ww, wb, n_rounds)
                zones.append(((ww, wb), len(zone)))

        zones.sort(key=lambda x: x[1])
        # Take 4 quietest
        virus_4 = [pos for pos, _ in zones[:4]]

        # Measure unique
        covered = {}
        all_out = {(w, b) for w in range(8) for b in range(32)}
        for ob in all_out:
            covered[ob] = set()

        for vpos in virus_4:
            zone = infection_zone(W, vpos[0], vpos[1], n_rounds)
            for ob in zone:
                covered[ob].add(vpos)

        unique = sum(1 for s in covered.values() if len(s) == 1)

        if unique > best_score:
            best_score = unique
            best_W = W
            best_result = {
                'virus': virus_4,
                'unique': unique,
                'trial': trial,
            }

    return best_W, best_result


if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  RAYON SUPERVIRUS — Умный, заразный, устойчивый          ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Phase 1: Greedy cover at various round counts
    for n_rounds in [4, 16]:
        random.seed(42)
        W_base = [random.randint(0, M32) for _ in range(16)]

        print(f"  ══════ GREEDY COVER: {n_rounds} раундов ══════")
        t0 = time.time()
        result = greedy_virus_cover(W_base, n_rounds)
        dt = time.time() - t0
        print(f"    ИТОГО: {result['n_virus']} virus-бит → "
              f"unique={result['unique']}, ambig={result['ambiguous']}, "
              f"clean={result['clean']} [{dt:.1f}s]")
        if result['unique'] >= 200:
            print(f"    ★ ПОЧТИ ПОЛНОЕ ПОКРЫТИЕ!")
        print()

    # Phase 2: Immune evasion
    print("  ══════ IMMUNE EVASION: лучший W_base для 64 раундов ══════")
    t0 = time.time()
    best_W, best_info = immune_evasion(200, 64)
    dt = time.time() - t0
    print(f"    Best: {best_info['unique']} unique из 4 virus-бит [{dt:.1f}s]")
    print(f"    Virus: {best_info['virus']}")
    print()

    # Phase 3: Full greedy cover at 64 rounds with best W
    print("  ══════ FULL COVER: 64 раунда, лучший W_base ══════")
    t0 = time.time()
    result = greedy_virus_cover(best_W, 64)
    dt = time.time() - t0
    print(f"    {result['n_virus']} virus-бит → unique={result['unique']}, "
          f"ambig={result['ambiguous']}, clean={result['clean']} [{dt:.1f}s]")

    # Coverage quality
    n_virus = result['n_virus']
    coverage = result['unique'] / 256 * 100
    efficiency = result['unique'] / max(n_virus, 1)

    print(f"""
  ═════════════════════════════════════════════════════════
  RAYON SUPERVIRUS — ИТОГИ:

    Greedy cover at 64 rounds:
      {n_virus} virus-бит → {result['unique']}/256 unique ({coverage:.0f}%)
      Efficiency: {efficiency:.1f} unique per virus bit

    Supervirus properties:
      1. МАСШТАБИРУЕМОСТЬ: {n_virus} бит покрывают {result['unique']} output
      2. УСТОЙЧИВОСТЬ: выживает через 64 раундов SHA-256
      3. ЗАРАЗНОСТЬ: каждый virus-бит → {efficiency:.0f} unique output

    Обратная карта:
      {result['unique']} output-бит → конкретный virus-бит (однозначно)
      {result['ambiguous']} output-бит → несколько virus (неоднозначно)
      {result['clean']} output-бит → чистые (не заражены)

    ДЛЯ КОЛЛИЗИИ:
      {result['unique']} unique-mapped бит = {result['unique']} уравнений
      в {n_virus} неизвестных.
      Перебор: 2^{n_virus} = {2**n_virus:,} вариантов.
      {'★ ЛУЧШЕ BIRTHDAY!' if n_virus < 128 else 'Birthday: 2^128'}
  ═════════════════════════════════════════════════════════
""")
