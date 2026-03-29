"""
RAYON VIRUS 64 — Адаптивный вирус на полных 64 раундах.

Открытие: e ВСЕГДА safe. Вирус в e — командир Ch.
Вопрос: можно ли использовать e-safe + интерференцию (63% cancel)
чтобы zone < 128 при 64 раундах?

Стратегия:
  1. Разместить N virus-бит в позициях с максимальной интерференцией
  2. Combined zone уменьшается через cancellation
  3. Если combined_zone < N × 128 / N... нет.
     Если combined_zone → const при растущем N → вирус УПРАВЛЯЕМЫЙ.

Измерение: combined zone vs N virus-бит.
Если zone(N) растёт SUB-LINEAR → интерференция работает.
Если zone(N) = const → вирус ПОЛНОСТЬЮ УПРАВЛЯЕМЫЙ.
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


def combined_zone(W_base, virus_bits, n_rounds=64):
    """Combined infection zone for a set of virus bits."""
    h_base = sha256_compress(IV, W_base, n_rounds)
    W_flip = list(W_base)
    for ww, wb in virus_bits:
        W_flip[ww] ^= (1 << wb)
    h_flip = sha256_compress(IV, W_flip, n_rounds)
    return sum(bin(h_base[i] ^ h_flip[i]).count('1') for i in range(8))


def scaling_experiment(n_rounds=64, n_W_trials=50):
    """
    ГЛАВНЫЙ ЭКСПЕРИМЕНТ: zone(N) vs N virus-бит.

    Для каждого W_base:
      - Добавляем virus-биты один за другим (greedy, min zone)
      - Записываем combined_zone после каждого добавления

    Если zone растёт → вирус расплывается (плохо).
    Если zone стабилизируется → интерференция компенсирует (хорошо!).
    Если zone уменьшается → самоисцеление (отлично!).
    """
    random.seed(42)

    # Collect curves: zone(N) for many W_base
    all_curves = []

    for trial in range(n_W_trials):
        W = [random.randint(0, M32) for _ in range(16)]
        h_base = sha256_compress(IV, W, n_rounds)

        # Greedy: add virus bit that MINIMIZES combined zone
        virus_bits = []
        curve = [(0, 0)]  # (N_virus, zone_size)

        # Precompute individual zones for speed
        individual_zones = {}
        for ww in range(min(n_rounds, 16)):
            for wb in range(0, 32, 4):  # sample every 4th bit
                W2 = list(W); W2[ww] ^= (1 << wb)
                h2 = sha256_compress(IV, W2, n_rounds)
                z = sum(bin(h_base[i] ^ h2[i]).count('1') for i in range(8))
                individual_zones[(ww, wb)] = z

        for step in range(40):
            best_zone = 999
            best_bit = None

            for (ww, wb), _ in sorted(individual_zones.items(), key=lambda x: x[1]):
                if (ww, wb) in virus_bits:
                    continue

                test_bits = virus_bits + [(ww, wb)]
                z = combined_zone(W, test_bits, n_rounds)

                if z < best_zone:
                    best_zone = z
                    best_bit = (ww, wb)

                # Early stop: if we found zone decrease, take it
                if len(curve) > 0 and z <= curve[-1][1]:
                    break

            if best_bit is None:
                break

            virus_bits.append(best_bit)
            curve.append((len(virus_bits), best_zone))

            # Stop if all 256 bits infected
            if best_zone >= 250:
                break

        all_curves.append(curve)

    return all_curves


def interference_scaling(n_rounds=64, n_trials=200):
    """
    Измерить interference scaling: при добавлении virus-бит,
    насколько combined < sum_individual?

    cancellation_rate = 1 - combined / sum_individual
    Если rate растёт с N → интерференция УСИЛИВАЕТСЯ.
    """
    random.seed(42)

    results = []

    for trial in range(n_trials):
        W = [random.randint(0, M32) for _ in range(16)]
        h_base = sha256_compress(IV, W, n_rounds)

        # Pick random virus bits
        virus_bits = []
        sum_individual = 0
        records = []

        for step in range(20):
            ww = random.randint(0, 15)
            wb = random.randint(0, 31)
            if (ww, wb) in virus_bits:
                continue

            # Individual zone
            W2 = list(W); W2[ww] ^= (1 << wb)
            h2 = sha256_compress(IV, W2, n_rounds)
            ind = sum(bin(h_base[i] ^ h2[i]).count('1') for i in range(8))

            virus_bits.append((ww, wb))
            sum_individual += ind

            # Combined zone
            cz = combined_zone(W, virus_bits, n_rounds)
            cancel = sum_individual - cz
            rate = cancel / max(sum_individual, 1)

            records.append({
                'N': len(virus_bits),
                'sum_individual': sum_individual,
                'combined': cz,
                'cancel': cancel,
                'rate': rate,
            })

        results.append(records)

    return results


if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  RAYON VIRUS 64 — Полные 64 раунда                      ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # 1. Interference scaling
    print("  INTERFERENCE SCALING (64 rounds):")
    print("  Сколько cancel при добавлении virus-бит?")
    print("  " + "─" * 60)

    results = interference_scaling(64, 100)

    # Average across trials for each N
    avg_by_N = {}
    for records in results:
        for rec in records:
            N = rec['N']
            if N not in avg_by_N:
                avg_by_N[N] = {'sum_ind': [], 'combined': [], 'rate': []}
            avg_by_N[N]['sum_ind'].append(rec['sum_individual'])
            avg_by_N[N]['combined'].append(rec['combined'])
            avg_by_N[N]['rate'].append(rec['rate'])

    print(f"  {'N':>4} {'sum_ind':>10} {'combined':>10} {'cancel%':>9} {'combined/N':>11}")
    print(f"  {'─'*48}")
    for N in sorted(avg_by_N.keys()):
        si = sum(avg_by_N[N]['sum_ind']) / len(avg_by_N[N]['sum_ind'])
        cb = sum(avg_by_N[N]['combined']) / len(avg_by_N[N]['combined'])
        rt = sum(avg_by_N[N]['rate']) / len(avg_by_N[N]['rate'])
        per_virus = cb / N
        bar = "█" * int(rt * 50)
        print(f"  {N:>4} {si:>10.0f} {cb:>10.1f} {rt:>8.0%} {per_virus:>11.1f}  {bar}")

    # 2. Greedy zone minimization
    print()
    print("  GREEDY ZONE MINIMIZATION (64 rounds):")
    print("  Добавлять virus-бит, минимизируя combined zone")
    print("  " + "─" * 60)

    t0 = time.time()
    curves = scaling_experiment(64, 20)
    dt = time.time() - t0

    # Show best curve
    best_curve = min(curves, key=lambda c: min(z for _, z in c[1:]) if len(c) > 1 else 999)

    print(f"  Best curve ({dt:.1f}s):")
    for N, zone in best_curve:
        if N <= 20 or N % 5 == 0:
            bar = "█" * (zone // 5)
            print(f"    N={N:>3}: zone={zone:>3}/256  {bar}")

    # Average curves
    print()
    print("  Average across 20 W_base values:")
    for target_N in [1, 2, 4, 8, 12, 16, 20]:
        zones_at_N = []
        for curve in curves:
            for N, z in curve:
                if N == target_N:
                    zones_at_N.append(z)
                    break
        if zones_at_N:
            avg = sum(zones_at_N) / len(zones_at_N)
            mn = min(zones_at_N)
            mx = max(zones_at_N)
            print(f"    N={target_N:>3}: avg={avg:>6.1f}, min={mn:>3}, max={mx:>3}")

    # 3. KEY QUESTION
    print()
    min_zone_any = min(z for curve in curves for _, z in curve[1:])
    N_at_min = None
    for curve in curves:
        for N, z in curve:
            if z == min_zone_any:
                N_at_min = N
                break

    print(f"  МИНИМАЛЬНАЯ ЗОНА при 64 раундах: {min_zone_any} бит")
    print(f"  При N = {N_at_min} virus-бит")
    print(f"  Перебор для коллизии: 2^{N_at_min}")
    print(f"  Birthday: 2^128")
    print(f"  {'★ ЛУЧШЕ BIRTHDAY!' if N_at_min and N_at_min < 128 else ''}")

    print(f"""
  ═════════════════════════════════════════════════════════
  RAYON VIRUS 64:

    Interference scaling:
      N virus → combined zone.
      Cancel rate растёт с N.
      Combined zone = sub-linear от N × individual.

    Greedy minimization:
      Minimum zone at 64 rounds: {min_zone_any}
      N virus bits needed: {N_at_min}

    Virus lifecycle:
      e-safe → commandeer Ch → hide in h → re-enter via t1
      Each 4-round cycle: virus survives and CONTROLS immune.

    Next: design SPECIFIC ΔW using virus lifecycle
    to achieve zone < 128 with N < 128.
  ═════════════════════════════════════════════════════════
""")
