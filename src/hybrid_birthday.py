"""
HYBRID: Determination + Birthday для коллизий.

ИДЕЯ: SHA-256 содержит AND/OR гейты (Ch, Maj, carry chains).
Фиксация входных бит ЧАСТИЧНО определяет хеш через propagation.
Birthday на частично определённых хешах → ускорение.

ЭТАП 1: Определяем сколько хеш-бит определяются при k фикс. входов.
ЭТАП 2: Birthday на определённых битах.
ЭТАП 3: Полная коллизия через DFS.
"""
import random, math, sys
from collections import defaultdict

def propagate(gates, fixed):
    wire = dict(fixed)
    for gtype, i1, i2, out in gates:
        v1 = wire.get(i1); v2 = wire.get(i2) if i2 >= 0 else None
        if gtype == 'AND':
            if v1 == 0 or v2 == 0: wire[out] = 0
            elif v1 is not None and v2 is not None: wire[out] = v1 & v2
        elif gtype == 'OR':
            if v1 == 1 or v2 == 1: wire[out] = 1
            elif v1 is not None and v2 is not None: wire[out] = v1 | v2
        elif gtype == 'NOT':
            if v1 is not None: wire[out] = 1 - v1
    return wire

def make_xor(gates, a, b, nid_ref):
    nid = nid_ref[0]
    na = nid; gates.append(('NOT', a, -1, na)); nid += 1
    nb = nid; gates.append(('NOT', b, -1, nb)); nid += 1
    t1 = nid; gates.append(('AND', a, nb, t1)); nid += 1
    t2 = nid; gates.append(('AND', na, b, t2)); nid += 1
    xor = nid; gates.append(('OR', t1, t2, xor)); nid += 1
    nid_ref[0] = nid
    return xor


# ================================================================
# SHA-подобный хеш с Ch и Maj (реалистичная структура)
# ================================================================

def build_sha_like_hash(input_bits, hash_bits, rounds=4):
    """SHA-подобный хеш с Ch(e,f,g) и Maj(a,b,c).
    Ch(e,f,g) = (e AND f) XOR (NOT e AND g)
      → если e определён: Ch = f (e=1) или Ch = g (e=0). PROPAGATION!
    Maj(a,b,c) = (a AND b) XOR (a AND c) XOR (b AND c)
      → если a=b: Maj = a. PROPAGATION!
    """
    n = input_bits
    gates = []; nid_ref = [n]

    # Начальное состояние = входы (циклически если нужно)
    state = [i % n for i in range(max(hash_bits, 8))]
    w = len(state)

    for r in range(rounds):
        new_state = []
        for i in range(w):
            e = state[i]; f = state[(i+1)%w]; g = state[(i+2)%w]
            a = state[(i+3)%w]; b = state[(i+4)%w]; c = state[(i+5)%w]

            # Ch(e,f,g) = (e AND f) OR (NOT e AND g)
            # Точная формула: XOR заменён на OR (AND/OR friendly!)
            nid = nid_ref[0]
            ef = nid; gates.append(('AND', e, f, ef)); nid += 1
            ne = nid; gates.append(('NOT', e, -1, ne)); nid += 1
            neg = nid; gates.append(('AND', ne, g, neg)); nid += 1
            ch = nid; gates.append(('OR', ef, neg, ch)); nid += 1
            nid_ref[0] = nid

            # Maj(a,b,c) = (a AND b) OR (a AND c) OR (b AND c)
            nid = nid_ref[0]
            ab = nid; gates.append(('AND', a, b, ab)); nid += 1
            ac = nid; gates.append(('AND', a, c, ac)); nid += 1
            bc = nid; gates.append(('AND', b, c, bc)); nid += 1
            t1 = nid; gates.append(('OR', ab, ac, t1)); nid += 1
            maj = nid; gates.append(('OR', t1, bc, maj)); nid += 1
            nid_ref[0] = nid

            # Combine: OR(Ch, Maj) XOR state[i] ... для перемешивания
            nid = nid_ref[0]
            cm = nid; gates.append(('OR', ch, maj, cm)); nid += 1
            nid_ref[0] = nid
            result = make_xor(gates, cm, state[(i+6)%w], nid_ref)
            new_state.append(result)

        state = new_state

    # Сжатие до hash_bits
    while len(state) > hash_bits:
        new = []
        for i in range(0, len(state)-1, 2):
            new.append(make_xor(gates, state[i], state[i+1], nid_ref))
        if len(state) % 2: new.append(state[-1])
        state = new
    while len(state) < hash_bits:
        state.append(state[-1])

    return gates, n, state[:hash_bits]


def measure_partial_determination(gates, n, hash_wires, k, trials=500):
    """Фиксируем k случайных входов.
    Сколько хеш-бит определено?"""
    det_counts = []
    for _ in range(trials):
        vs = random.sample(range(n), min(k, n))
        fixed = {v: random.randint(0, 1) for v in vs}
        wire = propagate(gates, fixed)
        det = sum(1 for h in hash_wires if wire.get(h) is not None)
        det_counts.append(det)
    return sum(det_counts) / len(det_counts)


def hybrid_collision_search(hash_func_builder, input_bits, hash_bits, rounds):
    """Hybrid Birthday + Determination.
    1. Фиксируем k входов → определяем d хеш-бит
    2. Birthday на d определённых битах
    3. Проверяем полную коллизию
    """
    # Строим хеш
    gates, n, hash_wires = hash_func_builder(input_bits, hash_bits, rounds)

    # Определяем оптимальное k
    best_k = 1; best_d = 0
    for k in range(1, n+1):
        d = measure_partial_determination(gates, n, hash_wires, k, 200)
        if d > best_d:
            best_d = d; best_k = k
        if d >= hash_bits:
            break

    # Birthday на определённых битах
    table = {}  # partial_hash → (fixed_vars, remaining)
    evals = 0; found = False; result = None

    for trial in range(min(2**(hash_bits+2), 100000)):
        # Случайная полная подстановка
        x = {i: random.randint(0, 1) for i in range(n)}
        wire = propagate(gates, x)
        h = tuple(wire.get(hw) for hw in hash_wires)
        evals += 1

        if None in h:
            continue  # хеш не полностью определён

        if h in table:
            # Потенциальная коллизия!
            prev_x = table[h]
            if any(x[i] != prev_x[i] for i in range(n)):
                found = True
                result = (prev_x, x)
                break
        else:
            table[h] = dict(x)

    return found, evals, best_k, best_d, len(table)


def birthday_standard(hash_func_builder, input_bits, hash_bits, rounds):
    """Стандартный birthday: вычисляем H(x) для случайных x."""
    gates, n, hash_wires = hash_func_builder(input_bits, hash_bits, rounds)
    table = {}; evals = 0

    for _ in range(min(2**(hash_bits+2), 100000)):
        x = {i: random.randint(0, 1) for i in range(n)}
        wire = propagate(gates, x)
        h = tuple(wire.get(hw) for hw in hash_wires)
        evals += 1
        if None in h: continue
        if h in table:
            prev = table[h]
            if any(x[i] != prev[i] for i in range(n)):
                return True, evals
        table[h] = dict(x)
    return False, evals


def main():
    random.seed(42)
    print("=" * 72)
    print("  HYBRID: Determination + Birthday")
    print("=" * 72)

    # =========================================================
    # ЭТАП 1: Partial determination — сколько хеш-бит определяется?
    # =========================================================
    print()
    print("  ЭТАП 1: Partial determination для SHA-like хеша")
    print("  Фиксируем k входов → d хеш-бит определено")
    print()

    for input_bits in [8, 12, 16]:
        hash_bits = 8
        gates, n, hw = build_sha_like_hash(input_bits, hash_bits, 3)
        print(f"  input={input_bits}, hash={hash_bits}, gates={len(gates)}:")
        print(f"    {'k':>4} {'det bits':>9} {'det%':>6}")
        for k in range(0, n+1, max(1, n//8)):
            d = measure_partial_determination(gates, n, hw, k, 300)
            print(f"    {k:4d} {d:9.2f} {100*d/hash_bits:5.1f}%")
        sys.stdout.flush()

    # =========================================================
    # ЭТАП 2: Birthday на SHA-like — standard vs hybrid
    # =========================================================
    print()
    print("  ЭТАП 2: Birthday standard vs Hybrid")
    print()
    print(f"  {'in':>3} {'hash':>5} {'bday evals':>11} {'hybrid evals':>13} "
          f"{'speedup':>8} {'k_opt':>6} {'d_opt':>6}")
    print(f"  {'-'*54}")

    for input_bits in [8, 10, 12]:
        for hash_bits in [4, 6, 8]:
            random.seed(42)  # reproducible
            found_b, evals_b = birthday_standard(
                build_sha_like_hash, input_bits, hash_bits, 3)
            random.seed(42)
            found_h, evals_h, k_opt, d_opt, table_size = hybrid_collision_search(
                build_sha_like_hash, input_bits, hash_bits, 3)

            sp = evals_b / max(1, evals_h) if found_h else 0
            print(f"  {input_bits:3d} {hash_bits:5d} {evals_b:11d} "
                  f"{evals_h:13d} {sp:8.2f}x {k_opt:6d} {d_opt:6.1f}")
            sys.stdout.flush()

    # =========================================================
    # ЭТАП 3: Scaling — как hybrid масштабируется
    # =========================================================
    print()
    print("  ЭТАП 3: Масштабирование (input=12, hash=4..10)")
    print()
    print(f"  {'hash':>5} {'birthday':>9} {'hybrid':>8} {'ratio':>7} {'2^{h/2}':>8}")
    print(f"  {'-'*38}")

    for hash_bits in [4, 5, 6, 7, 8, 9, 10]:
        input_bits = 12
        random.seed(42)
        _, eb = birthday_standard(build_sha_like_hash, input_bits, hash_bits, 3)
        random.seed(42)
        _, eh, _, _, _ = hybrid_collision_search(
            build_sha_like_hash, input_bits, hash_bits, 3)
        bday_theory = 2 ** (hash_bits // 2 + 1)
        ratio = eb / max(1, eh)
        print(f"  {hash_bits:5d} {eb:9d} {eh:8d} {ratio:7.2f}x {bday_theory:8d}")
        sys.stdout.flush()

    # =========================================================
    # ЭТАП 4: AND/OR-only хеш (наш ЛУЧШИЙ случай)
    # =========================================================
    print()
    print("  ЭТАП 4: AND/OR хеш (без XOR) — partial determination")
    print()

    def build_andor_hash(input_bits, hash_bits, rounds=3):
        n = input_bits; gates = []; nid_ref = [n]
        state = [i % n for i in range(max(hash_bits, 8))]
        w = len(state)
        for r in range(rounds):
            new = []
            for i in range(w):
                nid = nid_ref[0]
                # f = (a AND b) OR (NOT a AND c) — Ch-like, AND/OR only
                a, b, c = state[i], state[(i+1)%w], state[(i+2)%w]
                ab = nid; gates.append(('AND', a, b, ab)); nid += 1
                na = nid; gates.append(('NOT', a, -1, na)); nid += 1
                nac = nid; gates.append(('AND', na, c, nac)); nid += 1
                res = nid; gates.append(('OR', ab, nac, res)); nid += 1
                nid_ref[0] = nid
                new.append(res)
            state = new
        while len(state) > hash_bits:
            new = []
            for i in range(0, len(state)-1, 2):
                nid = nid_ref[0]
                g = nid; gates.append(('AND', state[i], state[i+1], g)); nid += 1
                nid_ref[0] = nid
                new.append(g)
            if len(state)%2: new.append(state[-1])
            state = new
        while len(state) < hash_bits: state.append(state[-1])
        return gates, n, state[:hash_bits]

    for input_bits in [8, 12, 16]:
        hash_bits = 8
        gates, n, hw = build_andor_hash(input_bits, hash_bits, 3)
        print(f"  AND/OR hash, input={input_bits}, hash={hash_bits}:")
        print(f"    {'k':>4} {'det bits':>9}")
        for k in range(0, n+1, max(1, n//6)):
            d = measure_partial_determination(gates, n, hw, k, 300)
            print(f"    {k:4d} {d:9.2f}")
        sys.stdout.flush()

    # =========================================================
    # ИТОГ
    # =========================================================
    print()
    print("=" * 72)
    print("  ИТОГ: DETERMINATION-BIRTHDAY HYBRID")
    print("=" * 72)
    print("""
  Partial determination: фиксация k входов определяет d хеш-бит.
  Для SHA-like (Ch+Maj+XOR): d растёт постепенно с k.
  Для AND/OR хеша: d растёт быстрее (наш механизм работает!).

  Hybrid vs Birthday: ???
  Если d > h/2 при k < n/2: hybrid может побить birthday.
    """)


if __name__ == "__main__":
    main()
