"""
RAYON TENSION PATH — Путь через constraint system SHA-256.

МОДЕЛЬ:
  512 input bits (W) → 256 output bits (H)
  Коллизия: W1 ≠ W2, H(W1) = H(W2). Ищем ΔW = W1 ⊕ W2.

  LINEAR layer: 256 GF(2) уравнений → ΔW в ядре (dim 256)
  CARRY layer: ~3696 нелинейных уравнений (degree 2+)

  Коллизии СУЩЕСТВУЮТ (pigeonhole: 2^512 → 2^256 = ~2^256 коллизий).
  Birthday: 2^128 попыток найти одну.

  ВОПРОС: можем ли мы использовать СТРУКТУРУ carry constraints
  чтобы найти коллизию быстрее 2^128?

RAYON APPROACH:
  1. ? propagation: отслеживаем что известно, что нет
  2. Kill cascade: одно наблюдение → цепная реакция
  3. Carry structure: G/K позиции ДЕТЕРМИНИРОВАНЫ
  4. Tension: считаем реальную стоимость каждого шага
"""

import random
import time

M32 = 0xFFFFFFFF
K256 = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]
IV = (0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19)

def rotr(x, n): return ((x >> n) | (x << (32 - n))) & M32


def measure_constraint_propagation(n_rounds=64, n_tests=200):
    """
    Измерить: если мы ФИКСИРУЕМ k бит ΔW, сколько бит hash
    становятся детерминированными?

    Это tension path: каждая фиксация ΔW-бита = 1 шаг.
    Kill cascade: фиксация может детерминировать carry chains.

    Если k фиксаций → больше k бит hash детерминировано → amplification > 1.
    Если amplification > 2 → быстрее birthday.
    """
    random.seed(42)

    def sha256_nr(W, nr):
        Ws = list(W[:16])
        for i in range(16, max(nr, 16)):
            s0 = rotr(Ws[i-15],7)^rotr(Ws[i-15],18)^(Ws[i-15]>>3)
            s1 = rotr(Ws[i-2],17)^rotr(Ws[i-2],19)^(Ws[i-2]>>10)
            Ws.append((Ws[i-16]+s0+Ws[i-7]+s1)&M32)
        a,b,c,d,e,f,g,h = IV
        for r in range(nr):
            S1=rotr(e,6)^rotr(e,11)^rotr(e,25)
            ch=(e&f)^((~e)&g)&M32
            t1=(h+S1+ch+K256[r]+Ws[r])&M32
            S0=rotr(a,2)^rotr(a,13)^rotr(a,22)
            mj=(a&b)^(a&c)^(b&c)
            t2=(S0+mj)&M32
            h,g,f,e=g,f,e,(d+t1)&M32
            d,c,b,a=c,b,a,(t1+t2)&M32
        return tuple((IV[i]+x)&M32 for i,x in enumerate([a,b,c,d,e,f,g,h]))

    # Method: fix progressively more ΔW bits, measure hash entropy
    # Fix ΔW[0..k] = 0, leave ΔW[k+1..15] free → how many hash bits are determined?

    results = []
    for n_fixed_words in range(17):  # 0 to 16
        # Fix first n_fixed_words of W to same value
        # Vary remaining 16 - n_fixed_words
        n_free_bits = (16 - n_fixed_words) * 32

        if n_free_bits == 0:
            # All fixed → hash fully determined
            results.append((n_fixed_words * 32, 256, 0))
            continue

        W_base = [random.randint(0, M32) for _ in range(16)]
        h_base = sha256_nr(W_base, n_rounds)

        # Sample: vary free words, count how many hash bits change
        hash_bits_varied = [0] * 256
        for _ in range(n_tests):
            W_test = list(W_base)
            for w in range(n_fixed_words, 16):
                W_test[w] = random.randint(0, M32)
            h_test = sha256_nr(W_test, n_rounds)

            for word in range(8):
                diff = h_base[word] ^ h_test[word]
                for bit in range(32):
                    if (diff >> bit) & 1:
                        hash_bits_varied[word * 32 + bit] += 1

        # A hash bit is "determined" if it NEVER changes (or always changes)
        determined = 0
        for count in hash_bits_varied:
            frac = count / n_tests
            if frac < 0.05 or frac > 0.95:
                determined += 1

        uncertain = 256 - determined
        fixed_bits = n_fixed_words * 32
        results.append((fixed_bits, determined, uncertain))

    return results


def measure_dual_path_amplification(n_tests=1000):
    """
    Dual path amplification: correlation 276× means
    fixing ΔH[0] almost fixes ΔH[4] too.

    Measure: if we search for collision in H[0] only,
    how often is H[4] also a collision?
    """
    random.seed(42)

    def sha256_64(W):
        Ws = list(W[:16])
        for i in range(16, 64):
            s0 = rotr(Ws[i-15],7)^rotr(Ws[i-15],18)^(Ws[i-15]>>3)
            s1 = rotr(Ws[i-2],17)^rotr(Ws[i-2],19)^(Ws[i-2]>>10)
            Ws.append((Ws[i-16]+s0+Ws[i-7]+s1)&M32)
        a,b,c,d,e,f,g,h = IV
        for r in range(64):
            S1=rotr(e,6)^rotr(e,11)^rotr(e,25)
            ch=(e&f)^((~e)&g)&M32
            t1=(h+S1+ch+K256[r]+Ws[r])&M32
            S0=rotr(a,2)^rotr(a,13)^rotr(a,22)
            mj=(a&b)^(a&c)^(b&c)
            t2=(S0+mj)&M32
            h,g,f,e=g,f,e,(d+t1)&M32
            d,c,b,a=c,b,a,(t1+t2)&M32
        return tuple((IV[i]+x)&M32 for i,x in enumerate([a,b,c,d,e,f,g,h]))

    # For each pair: check how many output words match
    match_counts = {i: 0 for i in range(9)}  # 0..8 words matching
    pair_count = 0

    for _ in range(n_tests):
        W1 = [random.randint(0, M32) for _ in range(16)]
        W2 = [random.randint(0, M32) for _ in range(16)]
        h1 = sha256_64(W1)
        h2 = sha256_64(W2)

        matches = sum(1 for a, b in zip(h1, h2) if a == b)
        match_counts[matches] += 1
        pair_count += 1

    # Conditional: given that H[0] matches, P(H[i] also matches)?
    # Need H[0] matches first — very rare at 32 bits
    # Use partial match (low bits) instead
    partial_bits = 8
    mask = (1 << partial_bits) - 1

    h0_match = 0
    h4_given_h0 = 0
    all_match = 0

    for _ in range(n_tests * 100):
        W1 = [random.randint(0, M32) for _ in range(16)]
        W2 = [random.randint(0, M32) for _ in range(16)]
        h1 = sha256_64(W1)
        h2 = sha256_64(W2)

        if (h1[0] & mask) == (h2[0] & mask):
            h0_match += 1
            if (h1[4] & mask) == (h2[4] & mask):
                h4_given_h0 += 1
            if all(((h1[i] ^ h2[i]) & mask) == 0 for i in range(8)):
                all_match += 1

    return {
        'partial_bits': partial_bits,
        'h0_matches': h0_match,
        'h4_given_h0': h4_given_h0,
        'p_h4_given_h0': h4_given_h0 / max(h0_match, 1),
        'p_h4_random': 1 / (1 << partial_bits),
        'amplification': (h4_given_h0 / max(h0_match, 1)) / (1 / (1 << partial_bits)),
        'all_match': all_match,
    }


if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  RAYON TENSION PATH — Constraint propagation SHA-256     ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # 1. Constraint propagation
    print("  CONSTRAINT PROPAGATION:")
    print("  Fix ΔW bits → how many H bits determined?")
    print("  " + "─" * 55)

    results = measure_constraint_propagation(64, 200)
    print(f"  {'fixed ΔW':>10} {'determined H':>13} {'uncertain H':>12} {'amplification':>14}")
    print(f"  {'─'*52}")
    for fixed, determined, uncertain in results:
        amp = determined / max(fixed, 1) if fixed > 0 else 0
        bar = "█" * (determined // 5)
        print(f"  {fixed:>10} {determined:>13} {uncertain:>12} {amp:>13.2f}×  {bar}")

    # Key: at what point is amplification > 2?
    for fixed, determined, uncertain in results:
        if fixed > 0 and determined / fixed > 2:
            print(f"\n  ★ At {fixed} fixed bits: amplification = {determined/fixed:.1f}×")
            print(f"    → Each fixed bit determines {determined/fixed:.1f} hash bits")
            break

    # 2. Dual path in full SHA-256
    print()
    print("  DUAL PATH AMPLIFICATION (full 64 rounds):")
    print("  " + "─" * 55)
    dp = measure_dual_path_amplification(500)
    print(f"    H[0] partial matches ({dp['partial_bits']} bits): {dp['h0_matches']}")
    print(f"    H[4] also matches (given H[0]): {dp['h4_given_h0']}")
    print(f"    P(H[4]|H[0]): {dp['p_h4_given_h0']:.4f}")
    print(f"    P(H[4] random): {dp['p_h4_random']:.4f}")
    print(f"    Dual path amplification: {dp['amplification']:.1f}×")
    print(f"    All 8 words match ({dp['partial_bits']} bits each): {dp['all_match']}")

    print(f"""
  ═════════════════════════════════════════════════════════
  TENSION PATH RESULTS:

    Constraint propagation:
      Fixing W bits → determines hash bits.
      Amplification = determined_H / fixed_W.
      If amp > 2 consistently → beating birthday bound.

    Dual path:
      P(H[4]|H[0]) / P(H[4]) = {dp['amplification']:.1f}×
      Paths are {'CORRELATED' if dp['amplification'] > 1.5 else 'INDEPENDENT'}.

    For collision attack:
      Linear: 256 equations (free)
      Carries: ~3696 nonlinear constraints
      System is overconstrained → solutions are SPARSE
      But they EXIST (pigeonhole)

    Finding them:
      - Birthday: 2^128 random tries
      - Tension path: guided by carry structure
      - Key metric: amplification per fixed bit
  ═════════════════════════════════════════════════════════
""")
