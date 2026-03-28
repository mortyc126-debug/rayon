"""
SHA-256 collision search: birthday vs наши методы.
Строим упрощённую модель SHA-256 как circuit и тестируем.
Для полного SHA-256 (256 бит) — нереально, но на уменьшенных
версиях (toy SHA) можем измерить ε.
"""
import random, math, sys

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
    return wire.get(gates[-1][3]) if gates else None

def sat_dfs(gates, n, max_nodes=5000000):
    nodes=[0]; found=[None]
    def dfs(d, fixed):
        nodes[0]+=1
        if nodes[0]>max_nodes: return
        out=propagate(gates,fixed)
        if out is not None:
            if out==1: found[0]=dict(fixed)
            return
        if d>=n: return
        fixed[d]=0; dfs(d+1,fixed)
        if found[0] or nodes[0]>max_nodes: return
        fixed[d]=1; dfs(d+1,fixed)
        if found[0]: return
        del fixed[d]
    dfs(0,{})
    return found[0], nodes[0]


# ================================================================
# Toy hash functions: упрощённые модели криптохешей
# ================================================================

def make_xor(gates, a, b, nid_ref):
    """XOR(a,b) через AND/OR/NOT."""
    nid = nid_ref[0]
    na = nid; gates.append(('NOT', a, -1, na)); nid += 1
    nb = nid; gates.append(('NOT', b, -1, nb)); nid += 1
    t1 = nid; gates.append(('AND', a, nb, t1)); nid += 1
    t2 = nid; gates.append(('AND', na, b, t2)); nid += 1
    xor = nid; gates.append(('OR', t1, t2, xor)); nid += 1
    nid_ref[0] = nid
    return xor


def build_toy_hash(input_bits, output_bits, rounds=4):
    """Toy hash: input_bits → output_bits.
    Каждый раунд: XOR + AND + rotation.
    Моделирует структуру SHA-подобного хеша."""
    n = input_bits
    gates = []; nid_ref = [n]
    state = list(range(n))

    # Сжимаем до output_bits через раунды
    for r in range(rounds):
        new_state = []
        for i in range(len(state)):
            j = (i + 1) % len(state)
            k = (i + 3) % len(state)
            # XOR(state[i], state[j])
            x = make_xor(gates, state[i], state[j], nid_ref)
            # AND(x, state[k]) — нелинейность
            nid = nid_ref[0]
            a = nid; gates.append(('AND', x, state[k], a)); nid += 1
            nid_ref[0] = nid
            # XOR(a, state[i]) — ещё перемешивание
            y = make_xor(gates, a, state[i], nid_ref)
            new_state.append(y)
        state = new_state

    # Финальное сжатие: XOR-fold до output_bits
    while len(state) > output_bits:
        new = []
        for i in range(0, len(state) - 1, 2):
            x = make_xor(gates, state[i], state[i+1], nid_ref)
            new.append(x)
        if len(state) % 2: new.append(state[-1])
        state = new

    return gates, n, state[:output_bits]


def build_collision_circuit(input_bits, hash_bits, rounds=4):
    """Схема коллизии: C(x, y) = 1 iff H(x) == H(y) AND x ≠ y.
    Входы: x (input_bits) + y (input_bits) = 2 × input_bits.
    """
    n = 2 * input_bits
    gates = []; nid_ref = [n]

    # H(x): входы 0..input_bits-1
    # Строим хеш для x
    gates_x = []; nid_x = [input_bits]
    state_x = list(range(input_bits))
    for r in range(rounds):
        new = []
        for i in range(len(state_x)):
            j = (i+1) % len(state_x); k = (i+3) % len(state_x)
            xr = make_xor(gates, state_x[i], state_x[j], nid_ref)
            nid = nid_ref[0]
            a = nid; gates.append(('AND', xr, state_x[k], a)); nid += 1
            nid_ref[0] = nid
            y = make_xor(gates, a, state_x[i], nid_ref)
            new.append(y)
        state_x = new
    while len(state_x) > hash_bits:
        new = []
        for i in range(0, len(state_x)-1, 2):
            new.append(make_xor(gates, state_x[i], state_x[i+1], nid_ref))
        if len(state_x)%2: new.append(state_x[-1])
        state_x = new
    # Pad if needed
    while len(state_x) < hash_bits:
        state_x.append(state_x[-1])
    hash_x = state_x[:hash_bits]

    # H(y): входы input_bits..2*input_bits-1
    state_y = list(range(input_bits, 2*input_bits))
    for r in range(rounds):
        new = []
        for i in range(len(state_y)):
            j = (i+1) % len(state_y); k = (i+3) % len(state_y)
            xr = make_xor(gates, state_y[i], state_y[j], nid_ref)
            nid = nid_ref[0]
            a = nid; gates.append(('AND', xr, state_y[k], a)); nid += 1
            nid_ref[0] = nid
            y = make_xor(gates, a, state_y[i], nid_ref)
            new.append(y)
        state_y = new
    while len(state_y) > hash_bits:
        new = []
        for i in range(0, len(state_y)-1, 2):
            new.append(make_xor(gates, state_y[i], state_y[i+1], nid_ref))
        if len(state_y)%2: new.append(state_y[-1])
        state_y = new
    while len(state_y) < hash_bits:
        state_y.append(state_y[-1])
    hash_y = state_y[:hash_bits]

    # H(x) == H(y): AND(XNOR(h_x[i], h_y[i]) for all i)
    eq_bits = []
    for i in range(hash_bits):
        # XNOR = NOT XOR
        xor_bit = make_xor(gates, hash_x[i], hash_y[i], nid_ref)
        nid = nid_ref[0]
        xnor = nid; gates.append(('NOT', xor_bit, -1, xnor)); nid += 1
        nid_ref[0] = nid
        eq_bits.append(xnor)

    # AND всех eq_bits
    nid = nid_ref[0]
    cur = eq_bits[0]
    for e in eq_bits[1:]:
        g = nid; gates.append(('AND', cur, e, g)); nid += 1; cur = g
    hash_equal = cur
    nid_ref[0] = nid

    # x ≠ y: OR(XOR(x[i], y[i]) for all i)
    neq_bits = []
    for i in range(input_bits):
        xor_bit = make_xor(gates, i, input_bits + i, nid_ref)
        neq_bits.append(xor_bit)
    nid = nid_ref[0]
    cur = neq_bits[0]
    for nb in neq_bits[1:]:
        g = nid; gates.append(('OR', cur, nb, g)); nid += 1; cur = g
    x_neq_y = cur
    nid_ref[0] = nid

    # Выход: H(x)==H(y) AND x≠y
    nid = nid_ref[0]
    output = nid; gates.append(('AND', hash_equal, x_neq_y, output)); nid += 1

    return gates, n


def main():
    random.seed(42)
    print("=" * 72)
    print("  SHA-256 COLLISION: Toy model attack")
    print("=" * 72)

    # =========================================================
    # ТЕСТ 1: Toy hash, маленькие параметры
    # =========================================================
    print()
    print("  ТЕСТ 1: Collision finding на toy hash")
    print("  input_bits → hash_bits, ищем коллизию")
    print()
    print(f"  {'in':>3} {'hash':>5} {'n=2×in':>7} {'gates':>7} "
          f"{'DFS':>8} {'2^n':>9} {'2^{h/2}':>8} {'ε':>7}")
    print(f"  {'-'*58}")

    for input_bits in [4, 5, 6, 7, 8, 9, 10]:
        for hash_bits in [3, 4]:
            if hash_bits >= input_bits: continue
            gates, n = build_collision_circuit(input_bits, hash_bits, rounds=3)
            birthday_cost = 2 ** (hash_bits // 2 + 1)  # ~2^{h/2}
            two_n = 2 ** n

            result, dfs_nodes = sat_dfs(gates, n, 5000000)
            if dfs_nodes > 5000000:
                print(f"  {input_bits:3d} {hash_bits:5d} {n:7d} {len(gates):7d} "
                      f"{'timeout':>8} {two_n:9d} {birthday_cost:8d}")
                continue

            eps = math.log2(max(1.01, two_n / dfs_nodes)) / n if dfs_nodes > 0 else 0
            found = "✓" if result else "✗"

            print(f"  {input_bits:3d} {hash_bits:5d} {n:7d} {len(gates):7d} "
                  f"{dfs_nodes:8d} {two_n:9d} {birthday_cost:8d} {eps:7.4f} {found}")
            sys.stdout.flush()

    # =========================================================
    # ТЕСТ 2: Сравнение DFS vs Birthday для collision
    # =========================================================
    print()
    print("  ТЕСТ 2: DFS nodes vs Birthday cost")
    print()
    print(f"  {'in':>3} {'hash':>5} {'DFS':>8} {'birthday':>9} {'DFS лучше?':>11}")
    print(f"  {'-'*38}")

    for input_bits in [4, 5, 6, 7, 8, 9, 10]:
        hash_bits = 4
        if hash_bits >= input_bits: continue
        gates, n = build_collision_circuit(input_bits, hash_bits, rounds=3)
        birthday_cost = 2 ** (hash_bits // 2 + 1)
        result, dfs_nodes = sat_dfs(gates, n, 5000000)
        if dfs_nodes <= 5000000:
            better = "ДА" if dfs_nodes < birthday_cost else "нет"
            print(f"  {input_bits:3d} {hash_bits:5d} {dfs_nodes:8d} "
                  f"{birthday_cost:9d} {better:>11}")
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 3: Увеличиваем hash_bits — что с DFS?
    # =========================================================
    print()
    print("  ТЕСТ 3: Масштабирование по hash_bits (input=8)")
    print()
    print(f"  {'hash':>5} {'n':>5} {'DFS':>8} {'2^{h/2}':>8} {'ε':>7} {'DFS<bday':>9}")
    print(f"  {'-'*44}")

    for hash_bits in [2, 3, 4, 5, 6, 7, 8]:
        input_bits = 8
        gates, n = build_collision_circuit(input_bits, hash_bits, rounds=3)
        birthday = 2 ** (hash_bits // 2 + 1)
        result, dfs_nodes = sat_dfs(gates, n, 5000000)
        if dfs_nodes <= 5000000:
            eps = math.log2(max(1.01, (2**n) / dfs_nodes)) / n
            better = "✓" if dfs_nodes < birthday else "✗"
            print(f"  {hash_bits:5d} {n:5d} {dfs_nodes:8d} "
                  f"{birthday:8d} {eps:7.4f} {better:>9}")
        else:
            print(f"  {hash_bits:5d} {n:5d} {'timeout':>8}")
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 4: Разные числа раундов (влияние перемешивания)
    # =========================================================
    print()
    print("  ТЕСТ 4: Влияние числа раундов (input=7, hash=4)")
    print()
    print(f"  {'rounds':>6} {'DFS':>8} {'2^{h/2}':>8} {'ε':>7}")
    print(f"  {'-'*32}")

    for rounds in [1, 2, 3, 4, 5, 6, 8]:
        gates, n = build_collision_circuit(7, 4, rounds)
        birthday = 2 ** 3
        result, dfs_nodes = sat_dfs(gates, n, 5000000)
        if dfs_nodes <= 5000000:
            eps = math.log2(max(1.01, (2**n) / dfs_nodes)) / n
            print(f"  {rounds:6d} {dfs_nodes:8d} {birthday:8d} {eps:7.4f}")
        else:
            print(f"  {rounds:6d} {'timeout':>8}")
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 5: AND-heavy hash (убираем XOR)
    # =========================================================
    print()
    print("  ТЕСТ 5: AND/OR hash (без XOR) vs XOR hash")
    print("  Наш метод ДОЛЖЕН работать на AND/OR хешах!")
    print()

    def build_andor_collision(input_bits, hash_bits, rounds=3):
        """Хеш без XOR: только AND, OR, NOT."""
        n = 2 * input_bits
        gates = []; nid_ref = [n]

        for start in [0, input_bits]:
            state = list(range(start, start + input_bits))
            for r in range(rounds):
                new = []
                for i in range(len(state)):
                    j = (i+1) % len(state); k = (i+3) % len(state)
                    nid = nid_ref[0]
                    # AND(state[i], state[j])
                    a1 = nid; gates.append(('AND', state[i], state[j], a1)); nid += 1
                    # OR(a1, state[k])
                    o1 = nid; gates.append(('OR', a1, state[k], o1)); nid += 1
                    # NOT, AND, OR для нелинейности
                    n1 = nid; gates.append(('NOT', state[i], -1, n1)); nid += 1
                    a2 = nid; gates.append(('AND', n1, state[k], a2)); nid += 1
                    o2 = nid; gates.append(('OR', o1, a2, o2)); nid += 1
                    nid_ref[0] = nid
                    new.append(o2)
                state = new
            # Fold
            while len(state) > hash_bits:
                new = []
                for i in range(0, len(state)-1, 2):
                    nid = nid_ref[0]
                    g = nid; gates.append(('AND', state[i], state[i+1], g)); nid += 1
                    nid_ref[0] = nid
                    new.append(g)
                if len(state)%2: new.append(state[-1])
                state = new
            while len(state) < hash_bits:
                state.append(state[-1])
            if start == 0:
                hash_x = state[:hash_bits]
            else:
                hash_y = state[:hash_bits]

        # Equality + inequality
        eq_parts = []
        nid = nid_ref[0]
        for i in range(hash_bits):
            # XNOR без XOR: AND(a,b) OR AND(NOT a, NOT b)
            na = nid; gates.append(('NOT', hash_x[i], -1, na)); nid += 1
            nb = nid; gates.append(('NOT', hash_y[i], -1, nb)); nid += 1
            a1 = nid; gates.append(('AND', hash_x[i], hash_y[i], a1)); nid += 1
            a2 = nid; gates.append(('AND', na, nb, a2)); nid += 1
            xnor = nid; gates.append(('OR', a1, a2, xnor)); nid += 1
            eq_parts.append(xnor)
        cur = eq_parts[0]
        for e in eq_parts[1:]:
            g = nid; gates.append(('AND', cur, e, g)); nid += 1; cur = g
        hash_eq = cur

        # x ≠ y
        neq_parts = []
        for i in range(input_bits):
            na = nid; gates.append(('NOT', i, -1, na)); nid += 1
            nb = nid; gates.append(('NOT', input_bits+i, -1, nb)); nid += 1
            a1 = nid; gates.append(('AND', i, nb, a1)); nid += 1
            a2 = nid; gates.append(('AND', na, input_bits+i, a2)); nid += 1
            diff = nid; gates.append(('OR', a1, a2, diff)); nid += 1
            neq_parts.append(diff)
        cur = neq_parts[0]
        for ne in neq_parts[1:]:
            g = nid; gates.append(('OR', cur, ne, g)); nid += 1; cur = g
        x_neq_y = cur

        output = nid; gates.append(('AND', hash_eq, x_neq_y, output)); nid += 1
        nid_ref[0] = nid
        return gates, n

    print(f"  {'type':>8} {'in':>3} {'hash':>5} {'DFS':>8} {'bday':>6} {'ε':>7} {'DFS<bday':>9}")
    print(f"  {'-'*50}")

    for input_bits in [5, 6, 7, 8, 9, 10]:
        hash_bits = 4
        # XOR hash
        g1, n1 = build_collision_circuit(input_bits, hash_bits, 3)
        _, dfs1 = sat_dfs(g1, n1, 5000000)
        # AND/OR hash
        g2, n2 = build_andor_collision(input_bits, hash_bits, 3)
        _, dfs2 = sat_dfs(g2, n2, 5000000)
        bday = 2 ** (hash_bits//2 + 1)

        for tag, dfs_n, nn in [("XOR", dfs1, n1), ("AND/OR", dfs2, n2)]:
            if dfs_n <= 5000000:
                eps = math.log2(max(1.01, (2**nn)/dfs_n)) / nn
                better = "✓" if dfs_n < bday else "✗"
                print(f"  {tag:>8} {input_bits:3d} {hash_bits:5d} "
                      f"{dfs_n:8d} {bday:6d} {eps:7.4f} {better:>9}")
            else:
                print(f"  {tag:>8} {input_bits:3d} {hash_bits:5d} "
                      f"{'timeout':>8} {bday:6d}")
        sys.stdout.flush()

    # =========================================================
    # ИТОГ
    # =========================================================
    print()
    print("=" * 72)
    print("  ИТОГ")
    print("=" * 72)

if __name__ == "__main__":
    main()
