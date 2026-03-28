"""
ПУТЬ Б: Декомпозиция произвольной схемы на XOR и AND/OR части.
Для AND/OR: constant propagation.
Для XOR: Гауссова элиминация (решение линейной системы).
Комбинация даёт determination для ЛЮБОЙ схемы?
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
        elif gtype == 'XOR':
            if v1 is not None and v2 is not None: wire[out] = v1 ^ v2
    return wire.get(gates[-1][3]) if gates else None

def measure(gates, n, k, trials=2000):
    det = 0
    for _ in range(trials):
        s = random.randint(0, n-1)
        vs = [(s+i)%n for i in range(min(k,n))]
        fixed = {v: random.randint(0,1) for v in vs}
        if propagate(gates, fixed) is not None: det += 1
    return det / trials

# ================================================================
# Идея: декомпозиция C = AND/OR часть ∘ XOR часть
# ================================================================
#
# Для Williams: дана схема C размера s.
# Шаг 1: найти все XOR-подсхемы (пары NOT-AND-OR формирующие XOR)
# Шаг 2: заменить XOR на новые переменные y_i = XOR(inputs)
# Шаг 3: constant propagation на AND/OR части (с y_i как входами)
# Шаг 4: Гаусс на линейных зависимостях y_i = XOR(x_j's)
#
# Если AND/OR часть определяется при фиксации k переменных → profit.
# XOR часть: Гаусс решает линейную систему за poly время.

def detect_xor_gates(gates, n):
    """Детектируем XOR-паттерны: OR(AND(a, NOT b), AND(NOT a, b))."""
    xor_map = {}  # out_id → (a, b) если это XOR(a, b)

    # Индекс: для каждого out_id, найти гейт
    gate_by_out = {}
    for g in gates:
        gate_by_out[g[3]] = g

    for g in gates:
        if g[0] != 'OR':
            continue
        or_out = g[3]
        in1, in2 = g[1], g[2]

        # Проверяем: in1 = AND(a, NOT b), in2 = AND(NOT a, b)?
        g1 = gate_by_out.get(in1)
        g2 = gate_by_out.get(in2)
        if g1 is None or g2 is None:
            continue
        if g1[0] != 'AND' or g2[0] != 'AND':
            continue

        # g1 = AND(x, y), g2 = AND(z, w)
        # Нужно: x = a, y = NOT b, z = NOT a, w = b
        # Или другие перестановки

        def get_literal(wire_id):
            """Возвращает (var, positive) если wire_id = var или NOT var."""
            gg = gate_by_out.get(wire_id)
            if gg is not None and gg[0] == 'NOT':
                return (gg[1], False)
            return (wire_id, True)

        l1a = get_literal(g1[1])
        l1b = get_literal(g1[2])
        l2a = get_literal(g2[1])
        l2b = get_literal(g2[2])

        # XOR(a,b) = OR(AND(a, ~b), AND(~a, b))
        # Нужно: {l1a, l1b} = {(a,T), (b,F)} и {l2a, l2b} = {(a,F), (b,T)}
        for a_var in set(x[0] for x in [l1a, l1b, l2a, l2b]):
            for b_var in set(x[0] for x in [l1a, l1b, l2a, l2b]):
                if a_var == b_var:
                    continue
                # Проверяем паттерн
                expected1 = {(a_var, True), (b_var, False)}
                expected2 = {(a_var, False), (b_var, True)}
                actual1 = {l1a, l1b}
                actual2 = {l2a, l2b}
                if (actual1 == expected1 and actual2 == expected2) or \
                   (actual1 == expected2 and actual2 == expected1):
                    xor_map[or_out] = (a_var, b_var)
                    break
            if or_out in xor_map:
                break

    return xor_map


def build_mixed_circuit(n, n_xor_layers, n_andor_layers):
    """Смешанная схема: XOR-слои + AND/OR-слои."""
    gates = []; nid = n; prev = list(range(n))

    # XOR слои
    for _ in range(n_xor_layers):
        new = []
        for i in range(0, len(prev) - 1, 2):
            # XOR через AND/OR/NOT
            a, b = prev[i], prev[i+1]
            na = nid; gates.append(('NOT', a, -1, na)); nid += 1
            nb = nid; gates.append(('NOT', b, -1, nb)); nid += 1
            t1 = nid; gates.append(('AND', a, nb, t1)); nid += 1
            t2 = nid; gates.append(('AND', na, b, t2)); nid += 1
            xor = nid; gates.append(('OR', t1, t2, xor)); nid += 1
            new.append(xor)
        if len(prev) % 2 == 1:
            new.append(prev[-1])
        prev = new

    # AND/OR слои
    for layer in range(n_andor_layers):
        new = []
        gtype = 'AND' if layer % 2 == 0 else 'OR'
        for i in range(0, len(prev) - 1, 2):
            g = nid; gates.append((gtype, prev[i], prev[i+1], g)); nid += 1
            new.append(g)
        if len(prev) % 2 == 1:
            new.append(prev[-1])
        prev = new

    # Финал: OR всех
    while len(prev) > 1:
        cur = prev[0]
        for p in prev[1:]:
            g = nid; gates.append(('OR', cur, p, g)); nid += 1; cur = g
        prev = [cur]

    return gates, n


def main():
    random.seed(42)
    print("=" * 60)
    print("  ПУТЬ Б: Декомпозиция XOR + AND/OR")
    print("=" * 60)

    # Тест 1: Детектирование XOR-паттернов
    print("\n  Тест 1: Детектирование XOR в схемах")
    print(f"  {'тип':>15} {'gates':>6} {'XOR det':>8}")
    print(f"  {'-'*32}")

    # XOR chain
    n = 10
    gates = []; nid = n; cur = 0
    for i in range(1, n):
        na = nid; gates.append(('NOT', cur, -1, na)); nid += 1
        nb = nid; gates.append(('NOT', i, -1, nb)); nid += 1
        t1 = nid; gates.append(('AND', cur, nb, t1)); nid += 1
        t2 = nid; gates.append(('AND', na, i, t2)); nid += 1
        xor = nid; gates.append(('OR', t1, t2, xor)); nid += 1
        cur = xor
    xor_map = detect_xor_gates(gates, n)
    print(f"  {'XOR chain':>15} {len(gates):6d} {len(xor_map):8d}")

    # Смешанная
    g, nv = build_mixed_circuit(n, 2, 3)
    xm = detect_xor_gates(g, nv)
    print(f"  {'Mixed 2xor+3ao':>15} {len(g):6d} {len(xm):8d}")

    # Тест 2: Pr для смешанных схем с разным соотношением XOR/AND-OR
    print("\n  Тест 2: Pr[det] vs доля XOR-слоёв (n=20)")
    print(f"  {'XOR layers':>10} {'AO layers':>10} {'Pr[det]':>8}")
    print(f"  {'-'*30}")
    for n_xor in [0, 1, 2, 3, 4]:
        for n_ao in [4 - n_xor]:
            g, nv = build_mixed_circuit(20, n_xor, max(1, n_ao))
            pr = measure(g, nv, nv//2, 2000)
            print(f"  {n_xor:10d} {max(1,n_ao):10d} {pr:8.4f}")
            sys.stdout.flush()

    # Тест 3: Масштабирование для чисто AND/OR vs mixed
    print("\n  Тест 3: Масштабирование")
    print(f"  {'n':>4} {'pure AO':>8} {'1xor+3ao':>9} {'2xor+2ao':>9} {'3xor+1ao':>9}")
    print(f"  {'-'*42}")
    for n in [8, 12, 16, 20, 32]:
        row = f"  {n:4d}"
        for xor_l, ao_l in [(0,4), (1,3), (2,2), (3,1)]:
            g, nv = build_mixed_circuit(n, xor_l, max(1, ao_l))
            pr = measure(g, nv, nv//2, 2000)
            row += f" {pr:9.4f}"
        print(row)
        sys.stdout.flush()

    # Тест 4: Если заменить XOR на новые входы (oracle для XOR)
    print("\n  Тест 4: XOR → свежие переменные (oracle)")
    print("  Идея: XOR-часть решается Гауссом → значения известны")
    print("  → подставляем как константы → AND/OR пропагирует")
    print()

    # Строим: AND/OR часть принимает n входов (часть = XOR outputs)
    # Если XOR решён → все n входов известны → AND/OR тривиально
    # Но это нечестно: Гаусс решает ТОЛЬКО если #уравнений ≥ #переменных
    #
    # В реальной схеме: XOR-часть это m линейных уравнений по k переменным.
    # После фиксации n/2 переменных: m уравнений по ≤ n/2 переменным.
    # Если m ≥ n/2: система переопределена → решение определено.
    # Если m < n/2: система недоопределена → свободные переменные остаются.

    print("  Для схемы размера s с x XOR-гейтами и a AND/OR-гейтами:")
    print("  XOR-часть: x линейных уравнений.")
    print("  После фиксации n/2 переменных: x уравн. по ≤ n/2 неизв.")
    print()
    print("  Если x ≥ n/2: Гаусс решает полностью → ВСЕ определено.")
    print("  Если x < n/2: (n/2 - x) свободных переменных остаётся.")
    print("  Нужно: AND/OR часть определяет выход при x + n/2 из n")
    print("  определённых входов.")
    print()

    # Численная проверка
    print("  Численная проверка: AND/OR-часть с extra определёнными входами")
    print(f"  {'n':>4} {'k=n/2':>6} {'k=3n/4':>7} {'k=n':>6}")
    print(f"  {'-'*26}")
    for n in [8, 12, 16, 20, 32]:
        g, nv = build_mixed_circuit(n, 0, 4)  # чисто AND/OR
        row = f"  {n:4d}"
        for frac in [0.5, 0.75, 1.0]:
            k = max(1, int(frac * n))
            pr = measure(g, nv, k, 2000)
            row += f" {pr:7.4f}"
        print(row)
        sys.stdout.flush()

    print()
    print("  ВЫВОД:")
    print("  Схему можно декомпозировать: C = AND/OR ∘ XOR.")
    print("  XOR: Гаусс за poly. AND/OR: const propagation.")
    print("  Вопрос: достаточно ли XOR-уравнений для определения?")


if __name__ == "__main__":
    main()
