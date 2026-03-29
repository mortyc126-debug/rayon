"""
RAYON BIOATTACK — Биологическая атака внутри цифрового пространства.

НЕ наблюдение. ПРОЕКТИРОВАНИЕ вируса.

Вирус = паттерн ? бит, размещённый так, чтобы:
  1. Заражённые биты ВЫЖИВАЮТ через все 64 раунда
  2. Пустышки (known биты) остаются чистыми
  3. На выходе: заражённые биты ОТЛИЧИМЫ от чистых

Иммунная система SHA-256:
  - Carry absorbers (G/K) — БЛОКИРУЮТ распространение
  - Ch(known_e, ?, ?) → known — УБИВАЕТ вирус
  - Maj(known, known, ?) → known — УБИВАЕТ вирус
  - XOR(?, known) → ? — вирус ПРОХОДИТ
  - ADD: carry chain — вирус РАСПРОСТРАНЯЕТСЯ через P-chain

Стратегия:
  Для конкретного W_base, carry map показывает ГДЕ absorbers.
  Размещаем ? МЕЖДУ absorbers — вирус не может распространиться
  дальше чем до следующего kill-link.

  Это УПРАВЛЯЕМОЕ ЗАРАЖЕНИЕ.
"""

import random
import time

M32 = 0xFFFFFFFF
K256 = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]
IV = (0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19)

def rotr(x, n): return ((x >> n) | (x << (32 - n))) & M32
def sigma0(x): return rotr(x,7) ^ rotr(x,18) ^ (x>>3)
def sigma1(x): return rotr(x,17) ^ rotr(x,19) ^ (x>>10)

def sha256_compress(state, W, n_rounds=64):
    Ws = list(W[:16])
    for i in range(16, max(n_rounds, 16)):
        s0 = rotr(Ws[i-15],7)^rotr(Ws[i-15],18)^(Ws[i-15]>>3)
        s1 = rotr(Ws[i-2],17)^rotr(Ws[i-2],19)^(Ws[i-2]>>10)
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


def carry_kill_map(a_val, b_val, bits=32):
    """
    Для конкретных a, b: карта G/K/P позиций при a+b.
    G (generate) = оба 1 → carry = 1 (known)
    K (kill) = оба 0 → carry = 0 (known)
    P (propagate) = разные → carry = carry_in (unknown)

    Kill-link = G или K: БЛОКИРУЕТ вирус.
    P-chain = последовательные P: вирус ПРОХОДИТ.
    """
    g = a_val & b_val
    p = a_val ^ b_val
    k = (~(a_val | b_val)) & M32

    kill_positions = []  # bit positions where carry is KNOWN (blocks virus)
    pass_chains = []     # (start, length) of P-chains (virus passes)

    chain_start = None
    chain_len = 0
    for bit in range(bits):
        if (p >> bit) & 1:
            if chain_start is None:
                chain_start = bit
                chain_len = 1
            else:
                chain_len += 1
        else:
            if chain_start is not None:
                pass_chains.append((chain_start, chain_len))
                chain_start = None
                chain_len = 0
            kill_positions.append(bit)

    if chain_start is not None:
        pass_chains.append((chain_start, chain_len))

    return {
        'kills': kill_positions,
        'pass_chains': pass_chains,
        'n_kills': len(kill_positions),
        'n_pass': sum(l for _, l in pass_chains),
    }


def virus_survivability(W_base, virus_positions, n_rounds=64):
    """
    ТОЧНОЕ измерение: для данного W_base и набора virus_positions,
    сколько выходных бит ТОЧНО зависят от virus?

    Метод: для каждого virus-бита, flip его 0→1 или 1→0.
    Если выходной бит МЕНЯЕТСЯ → он ЗАРАЖЁН этим вирусом.
    Если НЕ меняется → он ЧИСТ.

    Это НЕ tag-union (worst case).
    Это ТОЧНОЕ заражение для конкретного W.
    """
    h_base = sha256_compress(IV, W_base, n_rounds)

    # Для каждого virus-бита: какие output-биты он заражает?
    virus_reach = {}  # (w_word, w_bit) → set of (h_word, h_bit)
    total_infected = set()

    for w_word, w_bit in virus_positions:
        W_flip = list(W_base)
        W_flip[w_word] ^= (1 << w_bit)
        h_flip = sha256_compress(IV, W_flip, n_rounds)

        infected = set()
        for hw in range(8):
            diff = h_base[hw] ^ h_flip[hw]
            for hb in range(32):
                if (diff >> hb) & 1:
                    infected.add((hw, hb))

        virus_reach[(w_word, w_bit)] = infected
        total_infected |= infected

    # Чистые биты = не заражены НИ ОДНИМ virus-битом
    all_output = {(w, b) for w in range(8) for b in range(32)}
    clean = all_output - total_infected

    return {
        'virus_positions': virus_positions,
        'total_infected': len(total_infected),
        'total_clean': len(clean),
        'virus_reach': virus_reach,
        'clean_positions': clean,
    }


def design_virus(W_base, n_rounds=64, max_virus_bits=16):
    """
    СПРОЕКТИРОВАТЬ вирус: выбрать позиции в W так, чтобы
    заражение было МИНИМАЛЬНЫМ (вирус не расплывается).

    Стратегия:
      1. Для каждого W-бита: измерить "зону поражения" (сколько H-бит он заражает)
      2. Выбрать биты с МИНИМАЛЬНОЙ зоной → "тихий вирус"
      3. Проверить: заражённые зоны ПЕРЕСЕКАЮТСЯ или РАЗДЕЛЬНЫ?
      4. Если раздельны → каждый virus-бит контролирует свою зону
         → по output можно определить input (обратная карта!)
    """
    # Phase 1: measure infection zone for each W-bit
    h_base = sha256_compress(IV, W_base, n_rounds)
    infection_zones = {}

    active = min(n_rounds, 16)
    for w_word in range(active):
        for w_bit in range(32):
            W_flip = list(W_base)
            W_flip[w_word] ^= (1 << w_bit)
            h_flip = sha256_compress(IV, W_flip, n_rounds)

            zone = 0
            for hw in range(8):
                zone += bin(h_base[hw] ^ h_flip[hw]).count('1')

            infection_zones[(w_word, w_bit)] = zone

    # Phase 2: sort by infection zone size (smallest = quietest virus)
    sorted_zones = sorted(infection_zones.items(), key=lambda x: x[1])

    # Phase 3: select virus bits with SEPARATE zones
    selected = []
    selected_infected = set()

    for (w_word, w_bit), zone_size in sorted_zones:
        if len(selected) >= max_virus_bits:
            break

        # Compute actual zone
        W_flip = list(W_base)
        W_flip[w_word] ^= (1 << w_bit)
        h_flip = sha256_compress(IV, W_flip, n_rounds)

        zone = set()
        for hw in range(8):
            diff = h_base[hw] ^ h_flip[hw]
            for hb in range(32):
                if (diff >> hb) & 1:
                    zone.add((hw, hb))

        # Check overlap with already selected
        overlap = zone & selected_infected
        overlap_ratio = len(overlap) / max(len(zone), 1)

        selected.append({
            'pos': (w_word, w_bit),
            'zone_size': zone_size,
            'zone': zone,
            'overlap': len(overlap),
            'overlap_ratio': overlap_ratio,
        })
        selected_infected |= zone

    return selected, sorted_zones


def virus_reverse_map(W_base, virus_positions, n_rounds=64):
    """
    ОБРАТНАЯ КАРТА: по output-биту определить input virus-бит.

    Для каждого output-бита: какие virus-биты его заражают?
    Если output-бит заражён РОВНО ОДНИМ virus → однозначная связь.
    Если несколькими → неоднозначно.
    Если нулём → чистый.
    """
    h_base = sha256_compress(IV, W_base, n_rounds)

    # Map: output bit → set of virus bits that infect it
    reverse = {}
    for hw in range(8):
        for hb in range(32):
            reverse[(hw, hb)] = set()

    for w_word, w_bit in virus_positions:
        W_flip = list(W_base)
        W_flip[w_word] ^= (1 << w_bit)
        h_flip = sha256_compress(IV, W_flip, n_rounds)

        for hw in range(8):
            diff = h_base[hw] ^ h_flip[hw]
            for hb in range(32):
                if (diff >> hb) & 1:
                    reverse[(hw, hb)].add((w_word, w_bit))

    # Classify output bits
    unique = 0     # exactly 1 virus source → identifiable
    ambiguous = 0  # multiple virus sources
    clean = 0      # no virus → known

    unique_map = {}  # output → virus bit (for unique ones)

    for pos, sources in reverse.items():
        if len(sources) == 0:
            clean += 1
        elif len(sources) == 1:
            unique += 1
            unique_map[pos] = list(sources)[0]
        else:
            ambiguous += 1

    return {
        'unique': unique,
        'ambiguous': ambiguous,
        'clean': clean,
        'unique_map': unique_map,
        'reverse': reverse,
    }


if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  RAYON BIOATTACK — Проектирование вируса                 ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    random.seed(42)
    W_base = [random.randint(0, M32) for _ in range(16)]

    # Phase 1: design virus at various round counts
    for n_rounds in [1, 2, 4, 8, 16, 64]:
        print(f"  ══════ {n_rounds} РАУНДОВ ══════")

        selected, all_zones = design_virus(W_base, n_rounds, max_virus_bits=8)

        # Show quietest virus bits
        print(f"  Тихий вирус (8 бит с минимальной зоной):")
        for v in selected:
            pos = v['pos']
            print(f"    W[{pos[0]:>2}][{pos[1]:>2}]: зона={v['zone_size']:>3} бит, "
                  f"overlap={v['overlap']:>3}")

        # Show infection map
        virus_pos = [v['pos'] for v in selected]
        surv = virus_survivability(W_base, virus_pos, n_rounds)
        print(f"  Заражено: {surv['total_infected']}/256, "
              f"чисто: {surv['total_clean']}/256")

        # Reverse map
        rmap = virus_reverse_map(W_base, virus_pos, n_rounds)
        print(f"  Обратная карта: unique={rmap['unique']}, "
              f"ambiguous={rmap['ambiguous']}, clean={rmap['clean']}")

        if rmap['unique'] > 0:
            print(f"  ★ {rmap['unique']} output-бит ОДНОЗНАЧНО связаны с virus-битами!")
            # Show first few
            for (hw, hb), (vw, vb) in list(rmap['unique_map'].items())[:5]:
                print(f"    H[{hw}][{hb}] ← W[{vw}][{vb}]")

        # Virus survival rate
        zone_sizes = [v['zone_size'] for v in selected]
        avg_zone = sum(zone_sizes) / len(zone_sizes)
        print(f"  Avg infection zone: {avg_zone:.1f}/256 бит")
        print(f"  Вирус {'ВЫЖИВАЕТ' if surv['total_clean'] > 0 else 'РАСТЁКСЯ'}: "
              f"{surv['total_clean']} чистых бит")
        print()

    # Phase 2: find the OPTIMAL virus — maximum unique reverse map
    print("  ══════ ОПТИМАЛЬНЫЙ ВИРУС (64 раунда) ══════")
    print()

    # Try different W_base values — some may have better kill-link structure
    best_unique = 0
    best_clean = 0
    best_W = None

    for trial in range(200):
        W_trial = [random.randint(0, M32) for _ in range(16)]
        selected, _ = design_virus(W_trial, 64, max_virus_bits=4)
        virus_pos = [v['pos'] for v in selected]
        rmap = virus_reverse_map(W_trial, virus_pos, 64)

        if rmap['unique'] > best_unique or (rmap['unique'] == best_unique and rmap['clean'] > best_clean):
            best_unique = rmap['unique']
            best_clean = rmap['clean']
            best_W = W_trial
            best_virus = virus_pos
            best_rmap = rmap

    print(f"  Best W found: unique={best_unique}, clean={best_clean}")
    if best_unique > 0:
        print(f"  Virus positions: {best_virus}")
        print(f"  ★ ВИРУС ВЫЖИЛ: {best_unique} output-бит однозначно идентифицируемы!")
        for (hw, hb), (vw, vb) in list(best_rmap['unique_map'].items())[:10]:
            print(f"    H[{hw}][{hb}] ← W[{vw}][{vb}]")
    else:
        print(f"  Вирус не выжил при 64 раундах (все зоны перекрываются)")

    print(f"""
  ═════════════════════════════════════════════════════════
  RAYON BIOATTACK:

    Вирус = ? биты, размещённые стратегически.
    Carry absorbers (G/K) = иммунная система → блокируют.
    P-chains = каналы заражения → вирус распространяется.

    Обратная карта: output-бит → input virus-бит.
    Unique = однозначная связь (вирус идентифицирован).
    Ambiguous = несколько вирусов (перекрытие зон).
    Clean = здоровый бит (не заражён).

    Для коллизии: если вирус выживает и unique > 0,
    мы знаем КАКИЕ input-биты влияют на КАКИЕ output-биты.
    Это ОБРАТНАЯ СВЯЗЬ через хаос.
  ═════════════════════════════════════════════════════════
""")
