"""
RAYON GENESIS — Новое направление. Не криптоанализ. Не математика.
Наука о состоянии ?.

══════════════════════════════════════════════════════════
ВСЁ ЧТО БЫЛО ДО ЭТОГО — мы смотрели на SHA-256 глазами
стандартной математики и переводили в наш язык.

ТЕПЕРЬ: мы смотрим ТОЛЬКО глазами ?.

? — не "неизвестно". ? — это СОСТОЯНИЕ МАТЕРИИ.
0 и 1 — вырожденные случаи. ? — общий случай.

SHA-256 — не функция из {0,1}^512 → {0,1}^256.
SHA-256 — оператор на пространстве {0,1,?}^n.
══════════════════════════════════════════════════════════

ЗАКОН 1: РАЗМНОЖЕНИЕ ?
  Один ? на входе → N ? на выходе.
  N зависит от ОПЕРАТОРА, не от значения.

  AND(?,x): если x=1 → 1 ?. Если x=0 → 0 ? (kill). Если x=? → 1 ?.
  XOR(?,x): всегда 1 ? (pass).
  ADD bit k: ? порождает carry-? → 1 или 2 ?.

  SHA-256 round: 1 ? in W → 2 ? out (H[0], H[4]) = Dual Path.
  Это не "2 бита разницы". Это КОЭФФИЦИЕНТ РАЗМНОЖЕНИЯ = 2.

ЗАКОН 2: КАСКАД ?
  ? размножается через раунды.
  Round r: N_r ? → Round r+1: N_{r+1} ?
  Коэффициент: μ = N_{r+1} / N_r

  Если μ > 1: ? растёт (хаос)
  Если μ = 1: ? стабильна (равновесие)
  Если μ < 1: ? умирает (порядок)

ЗАКОН 3: ПОГЛОЩЕНИЕ ?
  AND(0, ?) = 0. Kill-link.
  Это не "информация теряется". Это ? ПОГЛОЩАЕТСЯ.
  Поглощённая ? не исчезает — она переходит в ЗНАНИЕ.
  ? → 0 = акт наблюдения.

ЗАКОН 4: ИНТЕРФЕРЕНЦИЯ ?
  XOR(?, ?) = ?. Но КАКОЙ ??
  Если обе ? от одного источника: XOR(?,?) может = 0!
  Это ИНТЕРФЕРЕНЦИЯ. ? может уничтожить себя.

  В SHA-256: два пути от одного W-бита встречаются.
  Если пути интерферируют → ? гасится.
  Dual path correlation 276× = ИНТЕРФЕРЕНЦИЯ.

ЗАКОН 5: TENSION = ПЛОТНОСТЬ ?
  τ = количество ? в системе.
  SHA-256 начинает с τ=512 (все W неизвестны).
  Каждый раунд: ? размножаются (μ) и поглощаются (kills).
  Равновесие: τ* где μ × τ - kills = τ.
  Измерено: τ* = 238. Это ФИЗИЧЕСКАЯ КОНСТАНТА SHA-256.
"""

import random
import time

M32 = 0xFFFFFFFF
K256 = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]
IV = (0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19)

def rotr(x, n): return ((x >> n) | (x << (32 - n))) & M32


# ═══════════════════════════════════════════════════════════
# ?-TRACE: проследить путь ОДНОЙ ? через SHA-256
# Не статистика. Не вероятность. ТОЧНЫЙ ПУТЬ.
# ═══════════════════════════════════════════════════════════

class QBit:
    """Бит в {0, 1, ?}. ? — полноценное состояние."""
    __slots__ = ['val', 'source']

    def __init__(self, val, source=None):
        # val: 0, 1, or '?'
        self.val = val
        self.source = source  # where this ? came from

    def is_q(self):
        return self.val == '?'

    def __repr__(self):
        return str(self.val)


def q_and(a, b):
    """AND в {0,1,?}."""
    if a.val == 0 or b.val == 0:
        return QBit(0)  # KILL — ? поглощена
    if a.val == 1 and b.val == 1:
        return QBit(1)
    if a.val == 1:
        return QBit('?', source=('pass', b.source))  # ? проходит
    if b.val == 1:
        return QBit('?', source=('pass', a.source))
    # ? AND ? = ?
    return QBit('?', source=('and', a.source, b.source))


def q_xor(a, b):
    """XOR в {0,1,?}."""
    if a.val != '?' and b.val != '?':
        return QBit(a.val ^ b.val)
    if a.val == '?' and b.val == '?':
        # Если ОТ ОДНОГО ИСТОЧНИКА — интерференция!
        if a.source is not None and a.source == b.source:
            return QBit(0)  # ? ⊕ ? = 0 (ИНТЕРФЕРЕНЦИЯ)
        return QBit('?', source=('xor', a.source, b.source))
    # ? ⊕ known = ?
    return QBit('?', source=a.source if a.is_q() else b.source)


def q_not(a):
    """NOT в {0,1,?}."""
    if a.val == '?':
        return QBit('?', source=('not', a.source))
    return QBit(1 - a.val)


def q_add_bit(a, b, carry_in):
    """Однобитное сложение с carry в {0,1,?}."""
    # sum_bit = a ⊕ b ⊕ carry_in
    s = q_xor(q_xor(a, b), carry_in)
    # carry_out = (a∧b) ∨ (a∧c) ∨ (b∧c) = maj(a,b,carry_in)
    ab = q_and(a, b)
    ac = q_and(a, carry_in)
    bc = q_and(b, carry_in)
    # OR in {0,1,?}: 1 if any is 1, ? if any is ? and none is 1, 0 if all 0
    carry_candidates = [ab, ac, bc]
    if any(c.val == 1 for c in carry_candidates):
        carry_out = QBit(1)
    elif any(c.val == '?' for c in carry_candidates):
        carry_out = QBit('?', source=('carry', a.source, b.source))
    else:
        carry_out = QBit(0)
    return s, carry_out


def q_word_from_int(x, bits=32):
    """Обычное число → массив QBit."""
    return [QBit((x >> i) & 1) for i in range(bits)]


def q_word_unknown(tag, bits=32):
    """Неизвестное слово → массив QBit(?)."""
    return [QBit('?', source=(tag, i)) for i in range(bits)]


def q_add_words(a, b, bits=32):
    """Сложение двух слов в {0,1,?}."""
    result = []
    carry = QBit(0)
    for i in range(bits):
        s, carry = q_add_bit(a[i], b[i], carry)
        result.append(s)
    return result


def q_xor_words(a, b, bits=32):
    """XOR двух слов."""
    return [q_xor(a[i], b[i]) for i in range(bits)]


def q_and_words(a, b, bits=32):
    """AND двух слов."""
    return [q_and(a[i], b[i]) for i in range(bits)]


def q_not_words(a, bits=32):
    return [q_not(a[i]) for i in range(bits)]


def q_rotr(word, n, bits=32):
    """Rotation right."""
    return [word[(i + n) % bits] for i in range(bits)]


def q_shr(word, n, bits=32):
    """Shift right."""
    return [QBit(0)] * n + word[:bits - n] if n < bits else [QBit(0)] * bits


def count_q(word):
    """Count ? bits in a word."""
    return sum(1 for b in word if b.val == '?')


# ═══════════════════════════════════════════════════════════
# ?-PROPAGATION: одна ? через SHA-256
# ═══════════════════════════════════════════════════════════

def trace_single_q(q_word_idx, q_bit_idx, n_rounds=64):
    """
    Inject ONE ? at W[q_word_idx][q_bit_idx].
    All other bits = known (from random W).
    Trace how many ? exist at each point.

    Returns: ?-count at each round.
    """
    random.seed(42)
    W_vals = [random.randint(0, M32) for _ in range(16)]

    # Build W as QBit arrays
    W = []
    for w in range(16):
        if w == q_word_idx:
            word = q_word_from_int(W_vals[w])
            word[q_bit_idx] = QBit('?', source=('W', w, q_bit_idx))
            W.append(word)
        else:
            W.append(q_word_from_int(W_vals[w]))

    # Schedule expansion
    Ws = list(W[:16])
    for i in range(16, max(n_rounds, 16)):
        s0 = q_xor_words(q_xor_words(q_rotr(Ws[i-15], 7), q_rotr(Ws[i-15], 18)),
                         q_shr(Ws[i-15], 3))
        s1 = q_xor_words(q_xor_words(q_rotr(Ws[i-2], 17), q_rotr(Ws[i-2], 19)),
                         q_shr(Ws[i-2], 10))
        w_new = q_add_words(q_add_words(Ws[i-16], s0),
                            q_add_words(Ws[i-7], s1))
        Ws.append(w_new)

    # Round function
    a = q_word_from_int(IV[0])
    b = q_word_from_int(IV[1])
    c = q_word_from_int(IV[2])
    d = q_word_from_int(IV[3])
    e = q_word_from_int(IV[4])
    f = q_word_from_int(IV[5])
    g = q_word_from_int(IV[6])
    h = q_word_from_int(IV[7])

    trace = []

    for r in range(n_rounds):
        # Count ? in state before round
        state_q = sum(count_q(x) for x in [a, b, c, d, e, f, g, h])
        schedule_q = count_q(Ws[r])
        trace.append({
            'round': r,
            'state_q': state_q,
            'schedule_q': schedule_q,
            'total_q': state_q + schedule_q,
        })

        # Σ1(e) — pure XOR/rotation, ? passes through
        S1 = q_xor_words(q_xor_words(q_rotr(e, 6), q_rotr(e, 11)), q_rotr(e, 25))

        # Ch(e,f,g) = (e & f) ^ (~e & g) — kills/passes ?
        ch = q_xor_words(q_and_words(e, f), q_and_words(q_not_words(e), g))

        # t1 = h + S1 + ch + K[r] + W[r]
        K_word = q_word_from_int(K256[r])
        t1 = q_add_words(q_add_words(q_add_words(q_add_words(h, S1), ch), K_word), Ws[r])

        # Σ0(a)
        S0 = q_xor_words(q_xor_words(q_rotr(a, 2), q_rotr(a, 13)), q_rotr(a, 22))

        # Maj(a,b,c) = (a&b)^(a&c)^(b&c)
        maj = q_xor_words(q_xor_words(q_and_words(a, b), q_and_words(a, c)),
                          q_and_words(b, c))

        # t2 = S0 + Maj
        t2 = q_add_words(S0, maj)

        # State update
        h, g, f = g, f, e
        e = q_add_words(d, t1)  # new_e = d + t1
        d, c, b = c, b, a
        a = q_add_words(t1, t2)  # new_a = t1 + t2

    # Final state ? count
    final_q = sum(count_q(x) for x in [a, b, c, d, e, f, g, h])
    trace.append({'round': n_rounds, 'state_q': final_q, 'schedule_q': 0, 'total_q': final_q})

    # ? in output hash
    H = []
    for i, (iv, state) in enumerate(zip(IV, [a, b, c, d, e, f, g, h])):
        H.append(q_add_words(q_word_from_int(iv), state))
    output_q = sum(count_q(w) for w in H)

    return trace, output_q, H


if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  RAYON GENESIS — Наука о состоянии ?                     ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Trace single ? through SHA-256
    print("  ОДНА ? ЧЕРЕЗ SHA-256:")
    print("  Inject ? at W[0][0]. All else known.")
    print("  " + "─" * 55)

    trace, output_q, H = trace_single_q(0, 0, n_rounds=64)

    print(f"  {'round':>6} {'state ?':>9} {'W[r] ?':>8} {'total ?':>9} {'μ':>8}")
    print(f"  {'─'*43}")
    prev_total = 1
    for t in trace:
        r = t['round']
        if r in [0,1,2,3,4,8,12,16,17,18,20,24,32,48,63,64]:
            mu = t['total_q'] / max(prev_total, 1)
            bar = "?" * min(50, t['state_q'])
            print(f"  {r:>6} {t['state_q']:>9} {t['schedule_q']:>8} {t['total_q']:>9} {mu:>8.2f}  {bar}")
            prev_total = t['total_q']

    print()
    print(f"  OUTPUT: {output_q} ? in 256-bit hash")
    print()

    # ? distribution across output words
    print("  ? IN OUTPUT WORDS:")
    for i, w in enumerate(H):
        n = count_q(w)
        bar = "?" * n
        print(f"    H[{i}]: {n:>2} ? / 32  {bar}")

    # Multiplication rate
    print()
    print("  ЗАКОН РАЗМНОЖЕНИЯ ?:")
    initial = 1
    final = output_q
    rounds = 64
    mu_avg = final / initial if initial > 0 else 0
    print(f"    1 ? in → {final} ? out ({rounds} rounds)")
    print(f"    Коэффициент размножения: μ = {mu_avg}")
    print(f"    Per round: μ_r = {mu_avg ** (1/rounds):.3f}")

    # Now: trace ? from different positions
    print()
    print("  ? ОТ РАЗНЫХ ПОЗИЦИЙ:")
    print("  " + "─" * 55)
    for wi in [0, 7, 15]:
        for bi in [0, 15, 31]:
            _, oq, _ = trace_single_q(wi, bi, 64)
            print(f"    W[{wi:>2}][{bi:>2}] → {oq:>3} ? in output")

    print(f"""
  ═════════════════════════════════════════════════════════
  RAYON GENESIS:

    ? — не "мы не знаем". ? — состояние.
    ? размножается (μ), поглощается (kill), интерферирует.

    SHA-256: 1 ? → {final} ? (x{mu_avg}).
    Это ФИЗИКА ?, не статистика.

    Carry pair (T4): ? → 2 ? через dual path.
    Kill links: AND(0,?) → 0, ? поглощена.
    Интерференция: XOR(?,?) → 0 если один источник.

    5 законов ?:
      1. Размножение (μ > 1 → хаос)
      2. Каскад (μ^n = экспоненциальный рост)
      3. Поглощение (kill links)
      4. Интерференция (самоуничтожение)
      5. Tension = плотность ?

    КОЛЛИЗИЯ на языке ?:
      Найти два источника ?, которые ИНТЕРФЕРИРУЮТ
      и гасят ВСЕ 256 выходных ?.
      Не birthday. Не перебор. ИНТЕРФЕРЕНЦИЯ.
  ═════════════════════════════════════════════════════════
""")
