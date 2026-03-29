"""
RAYON SMART VIRUS — Вирус, укреплённый нашей математикой.

5 законов ? как инструменты вируса:

  Закон 1 (Размножение): virus → 2 копии через dual path (a, e)
  Закон 2 (Каскад): копии сдвигаются: a→b→c→d, e→f→g→h
  Закон 3 (Поглощение): AND(0,?) → kill. Ch(known_e,?,?) → kill.
  Закон 4 (Интерференция): через 3 раунда копии ВСТРЕЧАЮТСЯ.
    new_e = d + t1(h,...). d = a-копия, h = e-копия.
    Если carry absorber на бите встречи → САМОУНИЧТОЖЕНИЕ.
  Закон 5 (Tension): τ на выходе — мера заражения.

SMART VIRUS = вирус, который ИСПОЛЬЗУЕТ интерференцию:
  Размещаем virus на бит k в W[r].
  Подбираем W_base так, чтобы:
    - Round r+3: d[k] и h[k] оба несут virus
    - Carry в d+t1 на бите k = absorber
    - Virus гасит сам себя → меньше spread

  Также: Ch и Maj как ОРУЖИЕ.
    Ch(e,f,g): если e[k] = known → Ch[k] = known → УБИВАЕТ virus в f,g.
    Разместим virus ТАМ, где e KNOWN → virus в f,g НЕ ПРОЙДЁТ.

  И: Σ0, Σ1 как РАЗБАВИТЕЛИ.
    Σ1(e) = ROTR(e,6) ⊕ ROTR(e,11) ⊕ ROTR(e,25)
    Virus в e[k] → 3 копии в Σ1 на позициях (k-6), (k-11), (k-25)
    Энергия virus РАЗБАВЛЯЕТСЯ (1 сильный → 3 слабых)
    НО: если две копии попадают в XOR с другим virus → интерференция.
"""

import random
import time

M32 = 0xFFFFFFFF
K256 = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]
IV = (0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19)

def rotr(x, n): return ((x >> n) | (x << (32 - n))) & M32

def sha256_with_trace(W, n_rounds=64):
    """SHA-256 returning state at every round."""
    Ws = list(W[:16])
    for i in range(16, max(n_rounds, 16)):
        s0=rotr(Ws[i-15],7)^rotr(Ws[i-15],18)^(Ws[i-15]>>3)
        s1=rotr(Ws[i-2],17)^rotr(Ws[i-2],19)^(Ws[i-2]>>10)
        Ws.append((Ws[i-16]+s0+Ws[i-7]+s1)&M32)
    a,b,c,d,e,f,g,h = IV
    trace = [(a,b,c,d,e,f,g,h)]
    for r in range(n_rounds):
        S1=rotr(e,6)^rotr(e,11)^rotr(e,25)
        ch=(e&f)^((~e)&g)&M32
        t1=(h+S1+ch+K256[r]+Ws[r])&M32
        S0=rotr(a,2)^rotr(a,13)^rotr(a,22)
        mj=(a&b)^(a&c)^(b&c)
        t2=(S0+mj)&M32
        h,g,f,e=g,f,e,(d+t1)&M32
        d,c,b,a=c,b,a,(t1+t2)&M32
        trace.append((a,b,c,d,e,f,g,h))
    return trace, Ws

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


def measure_interference_healing(W_base, w_word, w_bit, n_rounds=64):
    """
    Закон 4: Интерференция = самоисцеление.

    Virus в W[r][k] → round r → a[k], e[k].
    a → b(r+1) → c(r+2) → d(r+3). Passive shift.
    e → f(r+1) → g(r+2) → h(r+3). Passive shift.

    Round r+3: new_e = d + t1, where t1 includes h.
    d carries a-copy of virus. h carries e-copy.
    Potential interference at this meeting.

    Measure: trace virus (flip) through rounds.
    At each round: how many state bits are infected?
    If infection DECREASES at round r+3 → self-healing.
    """
    trace_base, _ = sha256_with_trace(W_base, n_rounds)

    W_flip = list(W_base)
    W_flip[w_word] ^= (1 << w_bit)
    trace_flip, _ = sha256_with_trace(W_flip, n_rounds)

    infection_per_round = []
    for r in range(n_rounds + 1):
        state_base = trace_base[r]
        state_flip = trace_flip[r]
        infected = 0
        for i in range(8):
            infected += bin(state_base[i] ^ state_flip[i]).count('1')
        infection_per_round.append(infected)

    # Find healing events: round where infection DECREASES
    healings = []
    for r in range(1, len(infection_per_round)):
        delta = infection_per_round[r] - infection_per_round[r-1]
        if delta < 0:
            healings.append((r, delta))

    return infection_per_round, healings


def find_self_healing_virus(n_rounds=64, n_trials=500):
    """
    Найти virus-бит + W_base с МАКСИМАЛЬНЫМ самоисцелением.

    Самоисцеление = раунд где infection уменьшается.
    Лучший virus = максимальное суммарное уменьшение.
    """
    random.seed(42)

    best_healing = 0
    best_result = None

    for trial in range(n_trials):
        W = [random.randint(0, M32) for _ in range(16)]
        ww = random.randint(0, min(n_rounds, 16) - 1)
        wb = random.randint(0, 31)

        inf, healings = measure_interference_healing(W, ww, wb, n_rounds)

        total_healing = sum(-d for _, d in healings)
        if total_healing > best_healing:
            best_healing = total_healing
            best_result = {
                'W': W,
                'pos': (ww, wb),
                'infection': inf,
                'healings': healings,
                'total_healing': total_healing,
                'final_infection': inf[-1],
                'peak_infection': max(inf),
            }

    return best_result


def ch_kill_analysis(W_base, n_rounds=64):
    """
    Закон 3: Ch как оружие вируса.

    Ch(e,f,g) = (e & f) ^ (~e & g)
    Если e[k] = 0: Ch[k] = g[k] (f[k] убита)
    Если e[k] = 1: Ch[k] = f[k] (g[k] убита)

    Virus в f или g: УБИТ если e[k] known.
    Virus в e: ПРОХОДИТ (Ch зависит от e).

    Подсчёт: на каждом раунде, сколько бит e = known?
    Это определяет kill-rate для virus в f и g.
    """
    trace, _ = sha256_with_trace(W_base, n_rounds)

    # e at each round
    e_known_bits = []
    for r in range(n_rounds):
        e_val = trace[r][4]  # e is index 4
        # All bits are "known" for a specific W — but we want to know
        # how many bits of e are UNAFFECTED by a particular virus.
        # This is input-dependent. For now: measure e entropy.
        e_known_bits.append(32)  # all known for specific W

    return e_known_bits


def sigma_dilution(w_bit):
    """
    Σ1(e) dilution: virus at e[k] → 3 positions in Σ1.

    Σ1(e) = ROTR(e,6) ⊕ ROTR(e,11) ⊕ ROTR(e,25)
    Virus e[k] appears at Σ1 bits: (k-6)%32, (k-11)%32, (k-25)%32

    These 3 positions: do any OVERLAP for specific k?
    (k-6) = (k-11) mod 32 → 6=11 → NO
    (k-6) = (k-25) mod 32 → 6=25 → NO
    (k-11) = (k-25) mod 32 → 11=25 → NO
    Never overlap → always 3 distinct positions → dilution factor = 3.

    Σ0(a) = ROTR(a,2) ⊕ ROTR(a,13) ⊕ ROTR(a,22)
    Same: always 3 distinct → dilution = 3.
    """
    s1_positions = [(w_bit - 6) % 32, (w_bit - 11) % 32, (w_bit - 25) % 32]
    s0_positions = [(w_bit - 2) % 32, (w_bit - 13) % 32, (w_bit - 22) % 32]
    return {
        'sigma1_positions': s1_positions,
        'sigma0_positions': s0_positions,
        'sigma1_overlap': len(s1_positions) != len(set(s1_positions)),
        'sigma0_overlap': len(s0_positions) != len(set(s0_positions)),
    }


def multi_virus_interference(W_base, positions, n_rounds=64):
    """
    Несколько virus-бит: их пути ПЕРЕСЕКАЮТСЯ?

    Если virus A и virus B пересекаются в XOR → сложная ?.
    Если в ADD с absorber → возможна частичная cancel.

    Мера: infection(A+B) vs infection(A) + infection(B).
    Если infection(A+B) < infection(A) + infection(B) → INTERFERENCE.
    Разница = количество самоуничтоженных ?.
    """
    h_base = sha256_compress(IV, W_base, n_rounds)

    # Individual infections
    individual_infections = {}
    for ww, wb in positions:
        W2 = list(W_base); W2[ww] ^= (1 << wb)
        h2 = sha256_compress(IV, W2, n_rounds)
        zone = sum(bin(h_base[i] ^ h2[i]).count('1') for i in range(8))
        individual_infections[(ww, wb)] = zone

    # Combined infection
    W_all = list(W_base)
    for ww, wb in positions:
        W_all[ww] ^= (1 << wb)
    h_all = sha256_compress(IV, W_all, n_rounds)
    combined = sum(bin(h_base[i] ^ h_all[i]).count('1') for i in range(8))

    sum_individual = sum(individual_infections.values())
    interference = sum_individual - combined

    return {
        'individual': individual_infections,
        'sum_individual': sum_individual,
        'combined': combined,
        'interference': interference,
        'interference_rate': interference / max(sum_individual, 1),
    }


if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  RAYON SMART VIRUS — Укреплён нашей математикой          ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # 1. Self-healing (Law 4: Interference)
    print("  ЗАКОН 4: САМОИСЦЕЛЕНИЕ (interference healing)")
    print("  " + "─" * 55)

    for nr in [8, 16, 64]:
        result = find_self_healing_virus(nr, n_trials=300)
        if result:
            print(f"    {nr:>2} rounds: healing={result['total_healing']:>3} bits, "
                  f"peak={result['peak_infection']:>3}, final={result['final_infection']:>3}")
            if result['healings'][:5]:
                healing_rounds = [(r, d) for r, d in result['healings'][:5]]
                print(f"      Healing events: {healing_rounds}")

            # Show infection curve
            inf = result['infection']
            print(f"      Curve: ", end='')
            for r in range(0, min(nr + 1, 20)):
                print(f"{inf[r]:>3}", end=' ')
            if nr > 20:
                print(f"... {inf[-1]:>3}", end='')
            print()
        print()

    # 2. Σ dilution (Law 1: Multiplication → dilution)
    print("  ЗАКОН 1: Σ-РАЗБАВЛЕНИЕ")
    print("  " + "─" * 55)
    for k in [0, 5, 10, 15, 20, 25, 31]:
        dil = sigma_dilution(k)
        print(f"    Virus at bit {k:>2}: "
              f"Σ1→{dil['sigma1_positions']}, Σ0→{dil['sigma0_positions']}")

    # 3. Multi-virus interference (Law 4 + Law 1)
    print()
    print("  ЗАКОН 4+1: MULTI-VIRUS INTERFERENCE")
    print("  " + "─" * 55)

    random.seed(42)
    W = [random.randint(0, M32) for _ in range(16)]

    for nr in [4, 16, 64]:
        # Pairs
        pairs_tested = 0
        total_interference = 0
        max_interference = 0
        max_pair = None

        for ww1 in range(min(nr, 16)):
            for wb1 in range(0, 32, 8):
                for ww2 in range(ww1, min(nr, 16)):
                    start_wb2 = wb1 + 8 if ww2 == ww1 else 0
                    for wb2 in range(start_wb2, 32, 8):
                        result = multi_virus_interference(W, [(ww1, wb1), (ww2, wb2)], nr)
                        pairs_tested += 1
                        total_interference += result['interference']
                        if result['interference'] > max_interference:
                            max_interference = result['interference']
                            max_pair = ((ww1, wb1), (ww2, wb2))
                            max_result = result

        avg_int = total_interference / max(pairs_tested, 1)
        print(f"    {nr:>2} rounds: {pairs_tested} pairs, "
              f"avg interference={avg_int:.1f} bits, max={max_interference}")
        if max_pair:
            r = max_result
            print(f"      Best: W[{max_pair[0][0]}][{max_pair[0][1]}]+W[{max_pair[1][0]}][{max_pair[1][1]}]"
                  f" → individual={r['sum_individual']}, combined={r['combined']}, "
                  f"cancelled={r['interference']} ({r['interference_rate']:.0%})")
        print()

    # 4. Search for maximum cancellation at 64 rounds
    print("  DEEP SEARCH: максимальная интерференция при 64 раундах")
    print("  " + "─" * 55)

    random.seed(42)
    best_cancel = 0
    best_cancel_result = None

    for trial in range(500):
        W = [random.randint(0, M32) for _ in range(16)]
        # Try 10 random pairs per W
        for _ in range(10):
            ww1 = random.randint(0, 15)
            wb1 = random.randint(0, 31)
            ww2 = random.randint(0, 15)
            wb2 = random.randint(0, 31)
            if (ww1, wb1) == (ww2, wb2):
                continue

            r = multi_virus_interference(W, [(ww1, wb1), (ww2, wb2)], 64)
            if r['interference'] > best_cancel:
                best_cancel = r['interference']
                best_cancel_result = {
                    'W': W[:4],
                    'pair': ((ww1, wb1), (ww2, wb2)),
                    'result': r,
                }

    if best_cancel_result:
        r = best_cancel_result['result']
        p = best_cancel_result['pair']
        print(f"    Best cancellation: {best_cancel} bits ({r['interference_rate']:.0%})")
        print(f"    Pair: W[{p[0][0]}][{p[0][1]}] + W[{p[1][0]}][{p[1][1]}]")
        print(f"    Individual sum: {r['sum_individual']}, Combined: {r['combined']}")

    print(f"""
  ═════════════════════════════════════════════════════════
  RAYON SMART VIRUS — Укреплён 5 законами ?

    Закон 1 (Размножение→Разбавление):
      Σ1, Σ0: virus diluted 1→3 at known positions.

    Закон 3 (Поглощение):
      Ch(known_e, ?, ?): kills virus in f/g.
      Known e bits = viral kill zones.

    Закон 4 (Интерференция):
      Dual path copies meet at round r+3 (register shift).
      Multi-virus: combined infection < sum of individual.
      Max cancellation: {best_cancel} bits = self-healing.

    SMART = virus that uses SHA-256's structure
    FOR its own benefit, not AGAINST it.
  ═════════════════════════════════════════════════════════
""")
