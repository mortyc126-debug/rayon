"""
RAYON ADAPTIVE VIRUS — Живой вирус внутри SHA-256.

Не статический flip. ОРГАНИЗМ с поведением:
  - SPREAD: когда путь свободен (P-chain) → заражать
  - HIDE: когда immune давит (G/K absorber) → прятаться
  - WAIT: когда Ch/Maj убивает → выжидать в безопасной позиции
  - EMERGE: когда условия меняются → активироваться

Реализация:
  Для данного W_base, вирус "живёт" в state bits.
  Каждый раунд: для каждого state-бита определяем:
    SAFE = virus может существовать здесь (не будет убит)
    DANGER = Ch/Maj/absorber убьёт virus здесь
    DORMANT = virus спрятался (в shift-регистре, не обрабатывается)

  Shift-регистры = УКРЫТИЯ:
    a→b→c→d: вирус в b,c,d СПИТ (не участвует в вычислениях до d→new_e)
    e→f→g→h: вирус в f,g СПИТ (участвует только в Ch, где может быть убит)

  h = САМОЕ БЕЗОПАСНОЕ МЕСТО:
    h входит ТОЛЬКО в t1 = h + Σ1(e) + Ch(e,f,g) + K + W
    Сложение h + ... → virus в h проходит через carry chain
    НО: virus в h НЕ проходит через Ch или Maj!
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


def map_immune_system(W_base, n_rounds=64):
    """
    Карта иммунной системы SHA-256 для данного W.

    Для каждого раунда, для каждого бита в каждом state-слове:
      SAFE: virus может здесь жить
      KILL: Ch/Maj/absorber убьёт virus

    Shift-регистры:
      a: ACTIVE (обрабатывается Σ0, Maj) → опасно для Maj
      b,c: DORMANT (только сдвигается, входит в Maj) → полу-безопасно
      d: DORMANT→ACTIVE (входит в new_e = d + t1) → carry risk
      e: ACTIVE (обрабатывается Σ1, Ch) → опасно для Ch
      f,g: DORMANT (входит в Ch) → опасно если e[k] known
      h: DORMANT→ACTIVE (входит в t1 = h + ...) → carry risk only
    """
    Ws = list(W_base[:16])
    for i in range(16, max(n_rounds, 16)):
        s0=rotr(Ws[i-15],7)^rotr(Ws[i-15],18)^(Ws[i-15]>>3)
        s1=rotr(Ws[i-2],17)^rotr(Ws[i-2],19)^(Ws[i-2]>>10)
        Ws.append((Ws[i-16]+s0+Ws[i-7]+s1)&M32)

    a,b,c,d,e,f,g,h = IV
    immune_map = []

    for r in range(n_rounds):
        # Ch kill zones: where e[k] is 0 → kills virus in f[k], passes g[k]
        #                where e[k] is 1 → passes f[k], kills virus in g[k]
        # Either way: Ch SELECTS. Virus in f or g: 50% kill chance per bit.
        # Virus in e: ALWAYS passes (Ch depends on e).
        ch_kills_f = ~e & M32  # e[k]=0 → f[k] killed (g passes)
        ch_kills_g = e          # e[k]=1 → g[k] killed (f passes)

        # Maj kill zones: Maj(a,b,c) = majority.
        # If 2 of 3 are known and agree → Maj is determined → virus killed.
        # If virus is the TIE-BREAKER → virus passes.
        # Complex: for simplicity, measure directly later.

        # Carry kill zones in new_a = t1 + t2
        S1=rotr(e,6)^rotr(e,11)^rotr(e,25)
        ch_val=(e&f)^((~e)&g)&M32
        t1=(h+S1+ch_val+K256[r]+Ws[r])&M32
        S0=rotr(a,2)^rotr(a,13)^rotr(a,22)
        mj=(a&b)^(a&c)^(b&c)
        t2=(S0+mj)&M32

        carry_absorber_a = (t1 & t2) | (~(t1 | t2) & M32)  # G or K
        carry_absorber_e = (d & t1) | (~(d | t1) & M32)

        immune_map.append({
            'round': r,
            'ch_kills_f': ch_kills_f,
            'ch_kills_g': ch_kills_g,
            'carry_absorber_a': carry_absorber_a,
            'carry_absorber_e': carry_absorber_e,
            'e_val': e,
            'state': (a,b,c,d,e,f,g,h),
        })

        h,g,f,e=g,f,e,(d+t1)&M32
        d,c,b,a=c,b,a,(t1+t2)&M32

    return immune_map


def find_hiding_spots(immune_map):
    """
    Найти УКРЫТИЯ: позиции где virus может спрятаться на нескольких раундах.

    Укрытие = bit position k в state-слове X, где:
      - X не обрабатывается (b,c — только shift)
      - ИЛИ X обрабатывается но immune не убивает (e в Ch)
      - ИЛИ carry absorber НЕ на позиции k

    Последовательность укрытий = ПУТЬ ВЫЖИВАНИЯ вируса.
    """
    # For each bit position k (0..31), trace the "safest" path through rounds
    # State word safety (lower = safer):
    #   h: enters t1 addition only → carry risk. Safety = depends on absorber.
    #   b,c: pure shift, enters Maj → some risk.
    #   d: shift, enters new_e addition → carry risk.
    #   e: enters Σ1 (safe, XOR) + Ch (virus in e PASSES) → SAFE for virus.
    #   f: enters Ch, killed if e[k]=0 → CONDITIONAL.
    #   g: enters Ch, killed if e[k]=1 → CONDITIONAL.
    #   a: enters Σ0 (safe, XOR) + Maj → CONDITIONAL.

    paths = []
    for k in range(32):
        safe_rounds = 0
        danger_rounds = 0

        for rd in immune_map:
            # Virus at bit k in various positions:
            # In e: safe (Ch depends on e, doesn't kill it)
            # In h: depends on carry absorber in t1 computation
            h_safe = not ((rd['carry_absorber_a'] >> k) & 1)  # if NOT absorber → virus passes
            e_safe = True  # virus in e always passes Ch

            # f safe if e[k]=1 (Ch selects f when e=1)
            f_safe = (rd['e_val'] >> k) & 1

            # g safe if e[k]=0 (Ch selects g when e=0)
            g_safe = not ((rd['e_val'] >> k) & 1)

            any_safe = e_safe  # at minimum, e is always safe
            safe_rounds += 1 if any_safe else 0

        paths.append({
            'bit': k,
            'safe_rounds': safe_rounds,
            'total_rounds': len(immune_map),
        })

    return paths


def adaptive_virus_search(n_rounds=64, n_trials=200):
    """
    Поиск адаптивного вируса: набор ΔW-бит, которые
    СОВМЕСТНО дают минимальное заражение при максимуме unique.

    Адаптивность = используем интерференцию (63% cancel).
    Чем больше вирусов интерферируют → чем меньше combined infection.

    КЛЮЧЕВАЯ ИДЕЯ: найти набор N бит, где
    combined_infection ≈ 128 и unique ≈ 128.
    Тогда: 128 уравнений в N неизвестных.
    Если N ≤ 128 → перебор 2^N ≤ 2^128 = birthday.
    Если combined < 128 → ЛУЧШЕ birthday.
    """
    random.seed(42)

    best_efficiency = 0
    best_result = None

    for trial in range(n_trials):
        W = [random.randint(0, M32) for _ in range(16)]

        # Greedy: add virus bits, maximizing cancellation
        virus_bits = []
        combined_zone = set()

        h_base = sha256_compress(IV, W, n_rounds)

        for step in range(20):
            best_gain = -1
            best_bit = None
            best_new_zone = None

            # Sample candidate bits
            candidates = [(random.randint(0, min(n_rounds,16)-1), random.randint(0, 31)) for _ in range(64)]

            for ww, wb in candidates:
                if (ww, wb) in virus_bits:
                    continue

                # Compute combined zone with this new bit
                W_test = list(W)
                for vw, vb in virus_bits:
                    W_test[vw] ^= (1 << vb)
                W_test[ww] ^= (1 << wb)
                h_test = sha256_compress(IV, W_test, n_rounds)

                new_zone = set()
                for hw in range(8):
                    d = h_base[hw] ^ h_test[hw]
                    for hb in range(32):
                        if (d >> hb) & 1:
                            new_zone.add((hw, hb))

                # We want: small combined zone + many virus bits
                # Efficiency = virus_bits / combined_zone_size
                if len(new_zone) > 0:
                    gain = len(virus_bits) + 1 - len(new_zone) / 256 * (len(virus_bits) + 1)
                    # Prefer: more virus bits with same zone size
                    # Or: same virus bits with smaller zone
                    if len(new_zone) < len(combined_zone) or (len(new_zone) <= len(combined_zone) + 5):
                        if len(new_zone) <= 200:  # don't add if zone too big
                            gain = (len(virus_bits) + 1) / max(len(new_zone), 1)
                            if gain > best_gain:
                                best_gain = gain
                                best_bit = (ww, wb)
                                best_new_zone = new_zone

            if best_bit is None:
                break

            virus_bits.append(best_bit)
            combined_zone = best_new_zone

            if len(virus_bits) >= 10:
                break

        # Measure final quality
        if virus_bits and combined_zone:
            n_virus = len(virus_bits)
            zone_size = len(combined_zone)
            efficiency = n_virus / max(zone_size, 1)

            # Also measure unique (reverse map)
            W_flipped_all = list(W)
            for vw, vb in virus_bits:
                W_flipped_all[vw] ^= (1 << vb)

            # Unique: bits where exactly 1 virus has effect
            unique = 0
            for hw in range(8):
                for hb in range(32):
                    # How many individual viruses affect this bit?
                    count = 0
                    for vw, vb in virus_bits:
                        W2 = list(W); W2[vw] ^= (1 << vb)
                        h2 = sha256_compress(IV, W2, n_rounds)
                        if (h_base[hw] ^ h2[hw]) >> hb & 1:
                            count += 1
                    if count == 1:
                        unique += 1

            score = unique / max(n_virus, 1)  # unique per virus bit

            if score > best_efficiency:
                best_efficiency = score
                best_result = {
                    'W': W,
                    'virus_bits': virus_bits,
                    'n_virus': n_virus,
                    'combined_zone': zone_size,
                    'unique': unique,
                    'efficiency': efficiency,
                    'score': score,
                    'trial': trial,
                }

    return best_result


if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  RAYON ADAPTIVE VIRUS — Живой организм внутри SHA-256    ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # 1. Immune system map
    random.seed(42)
    W = [random.randint(0, M32) for _ in range(16)]

    print("  КАРТА ИММУННОЙ СИСТЕМЫ:")
    print("  " + "─" * 55)

    immune = map_immune_system(W, 64)
    for r in [0, 1, 3, 7, 15, 31, 63]:
        rd = immune[r]
        abs_a = bin(rd['carry_absorber_a']).count('1')
        abs_e = bin(rd['carry_absorber_e']).count('1')
        ch_f = bin(rd['ch_kills_f']).count('1')
        ch_g = bin(rd['ch_kills_g']).count('1')
        print(f"    Round {r:>2}: carry_walls_a={abs_a:>2}/32, "
              f"carry_walls_e={abs_e:>2}/32, "
              f"Ch_kills_f={ch_f:>2}/32, Ch_kills_g={ch_g:>2}/32")

    # 2. Hiding spots
    print()
    print("  УКРЫТИЯ (safe positions for virus):")
    print("  " + "─" * 55)
    paths = find_hiding_spots(immune)
    # e is ALWAYS safe for virus at every bit
    for p in paths[:8]:
        print(f"    Bit {p['bit']:>2}: safe {p['safe_rounds']}/{p['total_rounds']} rounds "
              f"({'★ ALWAYS SAFE' if p['safe_rounds'] == p['total_rounds'] else ''})")
    print(f"    → Position 'e' is ALWAYS SAFE for virus (Ch depends on e)")
    print(f"    → Virus path: W → t1 → new_e → f(r+1) → g(r+2) → h(r+3) → t1(r+3)")

    # 3. Adaptive virus search
    print()
    print("  АДАПТИВНЫЙ ВИРУС (максимальная эффективность):")
    print("  " + "─" * 55)

    for nr in [16, 64]:
        result = adaptive_virus_search(nr, n_trials=100)
        if result:
            print(f"    {nr} rounds:")
            print(f"      Virus bits: {result['n_virus']}")
            print(f"      Combined zone: {result['combined_zone']}/256")
            print(f"      Unique (identifiable): {result['unique']}")
            print(f"      Score (unique/virus): {result['score']:.1f}")
            print(f"      Positions: {result['virus_bits'][:6]}...")
            print()

    # 4. The adaptive virus strategy summary
    print(f"""
  ═════════════════════════════════════════════════════════
  RAYON ADAPTIVE VIRUS:

    BEHAVIOUR MODEL:
      SPREAD: через XOR (Σ0, Σ1) — бесплатно, 1→3 dilution
      HIDE:   в shift-регистрах b,c,d — dormant 1-3 раунда
      WAIT:   в позиции 'e' — Ch НЕ УБИВАЕТ virus в e (ВСЕГДА safe)
      EMERGE: через t1 = h + ... когда carry path свободен

    SHA-256 SAFE ZONES для вируса:
      e: ВСЕГДА safe (Ch зависит от e, не убивает его)
      h: safe если carry absorber отсутствует
      b,c: dormant (просто shift, Maj — conditional)

    ПУТЬ ВИРУСА (цикл 4 раунда):
      Round r:   W[r] → t1 → new_a, new_e ← ВИРУС РОЖДАЕТСЯ
      Round r+1: a→b (sleep), e→f (Ch conditional)
      Round r+2: b→c (sleep), f→g (Ch conditional)
      Round r+3: c→d (wake), g→h (safe!)
      Round r+3: h → t1, d → new_e ← ВИРУС ВСТРЕЧАЕТ СЕБЯ

    Вирус в 'e' = НЕУБИВАЕМЫЙ.
    Ch(e,f,g): e — это УПРАВЛЯЮЩИЙ бит.
    Вирус В e определяет, что Ch делает.
    Он не жертва иммунной системы — он ЕЁ КОМАНДИР.
  ═════════════════════════════════════════════════════════
""")
