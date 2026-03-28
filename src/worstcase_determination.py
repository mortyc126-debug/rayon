"""
╔══════════════════════════════════════════════════════════════════════════╗
║  WORST-CASE DETERMINATION: Работает ли обрезка для ЛЮБЫХ схем?         ║
║  Тестируем: Tseitin, PHP, случайные DAG-схемы, XOR-цепочки            ║
╚══════════════════════════════════════════════════════════════════════════╝

Вопрос: Pr[выход определён | n/2 фикс.] → 1 для ВСЕХ схем?
Или только для 3-SAT?

Если да → Williams → NEXP ⊄ P/poly.
Если нет → нужен другой подход.
"""

import random
import math
import sys
from itertools import combinations


# ====================================================================
# ОБЩИЙ ДВИЖОК: пропагация констант через произвольную схему
# ====================================================================

def propagate(gates, fixed_vars):
    """Пропагация констант. gates = [(type, in1, in2, out), ...].
    Возвращает значение выхода (последний гейт) или None."""
    wire = dict(fixed_vars)
    for gtype, i1, i2, out in gates:
        v1 = wire.get(i1)
        v2 = wire.get(i2) if i2 >= 0 else None
        if gtype == 'AND':
            if v1 == 0 or v2 == 0:
                wire[out] = 0
            elif v1 is not None and v2 is not None:
                wire[out] = v1 & v2
        elif gtype == 'OR':
            if v1 == 1 or v2 == 1:
                wire[out] = 1
            elif v1 is not None and v2 is not None:
                wire[out] = v1 | v2
        elif gtype == 'NOT':
            if v1 is not None:
                wire[out] = 1 - v1
        elif gtype == 'XOR':
            if v1 is not None and v2 is not None:
                wire[out] = v1 ^ v2
    return wire.get(gates[-1][3]) if gates else None


def measure_det(gates, n, k, trials=2000):
    """Pr[выход определён | k случайных переменных фиксированы]."""
    det = 0
    for _ in range(trials):
        vs = random.sample(range(n), min(k, n))
        fixed = {v: random.randint(0, 1) for v in vs}
        if propagate(gates, fixed) is not None:
            det += 1
    return det / trials


# ====================================================================
# ГЕНЕРАТОРЫ WORST-CASE СХЕМ
# ====================================================================

def build_tseitin(n):
    """Формулы Цейтина на цикле длины n.
    Экспоненциально трудные для резолюции.
    Каждое ребро (i, i+1 mod n) имеет переменную x_e.
    Каждая вершина: XOR входящих рёбер = 1 (нечётность).
    На цикле из n вершин с n рёбрами: UNSAT (сумма всех = 0 ≠ n mod 2).
    Кодируем XOR через AND/OR/NOT."""
    # n рёбер = n переменных
    num_vars = n
    gates = []
    nid = num_vars

    # NOT для каждой переменной
    neg = {}
    for i in range(num_vars):
        neg[i] = nid
        gates.append(('NOT', i, -1, nid))
        nid += 1

    # Для каждой вершины v: XOR(edge_v_left, edge_v_right) = 1
    # edge_v_left = v, edge_v_right = (v+1) % n
    # XOR(a,b) = OR(AND(a, NOT b), AND(NOT a, b))
    # Constraint: XOR = 1 → это просто XOR(a,b)
    # Для Tseitin: каждая вершина имеет constraint.
    # Формула = AND всех constraints.

    constraint_outs = []
    for v in range(n):
        a = v              # ребро слева
        b = (v + 1) % n    # ребро справа

        # XOR(a, b) = OR(AND(a, NOT b), AND(NOT a, b))
        # AND(a, NOT b)
        t1 = nid
        gates.append(('AND', a, neg[b], t1))
        nid += 1
        # AND(NOT a, b)
        t2 = nid
        gates.append(('AND', neg[a], b, t2))
        nid += 1
        # OR(t1, t2) = XOR(a,b)
        xor_out = nid
        gates.append(('OR', t1, t2, xor_out))
        nid += 1

        constraint_outs.append(xor_out)

    # AND всех constraints
    cur = constraint_outs[0]
    for c in constraint_outs[1:]:
        out = nid
        gates.append(('AND', cur, c, out))
        nid += 1
        cur = out

    return gates, num_vars


def build_php(pigeons, holes):
    """Принцип ящиков: n+1 голубей в n ящиков. UNSAT.
    Переменные: x_{i,j} = голубь i в ящике j.
    Клозы: (1) каждый голубь где-то, (2) не два голубя в одном ящике."""
    n_pigeons = pigeons
    n_holes = holes
    num_vars = n_pigeons * n_holes
    gates = []
    nid = num_vars

    def var(i, j):
        return i * n_holes + j

    # NOT
    neg = {}
    for v in range(num_vars):
        neg[v] = nid
        gates.append(('NOT', v, -1, nid))
        nid += 1

    clause_outs = []

    # Каждый голубь хотя бы в одном ящике: OR(x_{i,0}, ..., x_{i,h-1})
    for i in range(n_pigeons):
        lits = [var(i, j) for j in range(n_holes)]
        cur = lits[0]
        for l in lits[1:]:
            out = nid
            gates.append(('OR', cur, l, out))
            nid += 1
            cur = out
        clause_outs.append(cur)

    # Не два голубя в одном ящике: для каждого ящика j, пары (i1, i2):
    # NOT(x_{i1,j} AND x_{i2,j}) = OR(NOT x_{i1,j}, NOT x_{i2,j})
    for j in range(n_holes):
        for i1, i2 in combinations(range(n_pigeons), 2):
            v1 = neg[var(i1, j)]
            v2 = neg[var(i2, j)]
            out = nid
            gates.append(('OR', v1, v2, out))
            nid += 1
            clause_outs.append(out)

    # AND всех клозов
    cur = clause_outs[0]
    for c in clause_outs[1:]:
        out = nid
        gates.append(('AND', cur, c, out))
        nid += 1
        cur = out

    return gates, num_vars


def build_xor_chain(n):
    """XOR-цепочка: y = x_0 XOR x_1 XOR ... XOR x_{n-1}.
    Каждый бит КРИТИЧЕН — изменение любого меняет выход.
    Worst case для пропагации: XOR не имеет "контролирующего" значения.
    Кодируем XOR через AND/OR/NOT."""
    gates = []
    nid = n

    neg = {}
    for i in range(n):
        neg[i] = nid
        gates.append(('NOT', i, -1, nid))
        nid += 1

    # XOR(a,b) = OR(AND(a, NOT b), AND(NOT a, b))
    cur = 0  # первый вход
    for i in range(1, n):
        b = i
        # AND(cur, NOT b)
        t1 = nid
        gates.append(('AND', cur, neg[b], t1))
        nid += 1
        # AND(NOT cur, b) — нужен NOT cur
        neg_cur = nid
        gates.append(('NOT', cur, -1, neg_cur))
        nid += 1
        t2 = nid
        gates.append(('AND', neg_cur, b, t2))
        nid += 1
        # OR(t1, t2)
        xor_out = nid
        gates.append(('OR', t1, t2, xor_out))
        nid += 1
        cur = xor_out

    return gates, n


def build_random_circuit(n, size_mult=5):
    """Случайная DAG-схема (не 3-SAT структура!).
    Каждый гейт = AND/OR/NOT со случайными входами из предыдущих."""
    gates = []
    nid = n
    num_gates = size_mult * n

    for _ in range(num_gates):
        gtype = random.choice(['AND', 'OR', 'NOT'])
        if gtype == 'NOT':
            i1 = random.randint(0, nid - 1)
            gates.append(('NOT', i1, -1, nid))
        else:
            i1 = random.randint(0, nid - 1)
            i2 = random.randint(0, nid - 1)
            gates.append((gtype, i1, i2, nid))
        nid += 1

    return gates, n


def build_majority(n):
    """MAJ(x_1, ..., x_n): 1 если больше половины входов = 1.
    Реализуем как AND всех подмножеств размера ceil(n/2) ... нет, слишком много.
    Вместо: сортировочная сеть (компараторы = AND/OR пары)."""
    # Простая реализация через попарные сравнения
    # Считаем сумму через полусумматоры
    gates = []
    nid = n

    # Threshold: sum >= ceil(n/2)
    # Реализуем через цепочку полусумматоров
    # Для малых n: прямое вычисление
    threshold = (n + 1) // 2

    # Для каждого подмножества размера threshold: AND всех элементов
    # Выход = OR всех таких AND
    if n > 15:
        # Слишком много подмножеств, используем приближение
        # Берём случайные подмножества
        and_outs = []
        for _ in range(min(100, n * 5)):
            subset = random.sample(range(n), threshold)
            cur = subset[0]
            for v in subset[1:]:
                out = nid
                gates.append(('AND', cur, v, out))
                nid += 1
                cur = out
            and_outs.append(cur)
    else:
        and_outs = []
        for subset in combinations(range(n), threshold):
            cur = subset[0]
            for v in subset[1:]:
                out = nid
                gates.append(('AND', cur, v, out))
                nid += 1
                cur = out
            and_outs.append(cur)

    # OR всех AND
    cur = and_outs[0]
    for a in and_outs[1:]:
        out = nid
        gates.append(('OR', cur, a, out))
        nid += 1
        cur = out

    return gates, n


def build_3sat(n, alpha=4.27):
    """Случайная 3-SAT для сравнения."""
    m = int(alpha * n)
    gates = []
    nid = n
    neg = {}
    for i in range(n):
        neg[i] = nid
        gates.append(('NOT', i, -1, nid))
        nid += 1
    c_outs = []
    for _ in range(m):
        vars_ = random.sample(range(n), min(3, n))
        clause = [(v, random.random() > 0.5) for v in vars_]
        lits = [v if p else neg[v] for v, p in clause]
        cur = lits[0]
        for l in lits[1:]:
            out = nid
            gates.append(('OR', cur, l, out))
            nid += 1
            cur = out
        c_outs.append(cur)
    cur = c_outs[0]
    for ci in c_outs[1:]:
        g = nid
        gates.append(('AND', cur, ci, g))
        nid += 1
        cur = g
    return gates, n


# ====================================================================
# ГЛАВНЫЙ ЭКСПЕРИМЕНТ
# ====================================================================

def main():
    random.seed(42)

    print("=" * 72)
    print("  WORST-CASE DETERMINATION PROBABILITY")
    print("  Работает ли Pr → 1 для ЛЮБЫХ схем?")
    print("=" * 72)

    # ------------------------------------------------------------------
    # ТЕСТ 1: Сравнение типов схем при фиксированном n
    # ------------------------------------------------------------------
    print()
    print("=" * 72)
    print("  ТЕСТ 1: Pr[определён | k=n/2] для разных типов схем")
    print("=" * 72)
    print()

    circuit_types = [
        ("Random 3-SAT", build_3sat),
        ("Tseitin (цикл)", build_tseitin),
        ("XOR-цепочка", build_xor_chain),
        ("Случайная DAG", build_random_circuit),
    ]

    print(f"  {'Тип схемы':<20}", end="")
    for n in [8, 12, 16, 20, 25, 30]:
        print(f"  {'n='+str(n):>7}", end="")
    print()
    print(f"  {'-'*72}")

    for name, builder in circuit_types:
        print(f"  {name:<20}", end="")
        for n in [8, 12, 16, 20, 25, 30]:
            try:
                gates, num_vars = builder(n)
                k = num_vars // 2
                pr = measure_det(gates, num_vars, k, 3000)
                print(f"  {pr:7.3f}", end="")
            except Exception as e:
                print(f"  {'ERR':>7}", end="")
        print()
        sys.stdout.flush()

    # PHP отдельно (другое число переменных)
    print(f"  {'PHP (p=h+1)':<20}", end="")
    for h in [3, 4, 5, 6, 7, 8]:
        p = h + 1
        gates, num_vars = build_php(p, h)
        k = num_vars // 2
        pr = measure_det(gates, num_vars, k, 3000)
        n_eff = num_vars
        print(f"  {pr:7.3f}", end="")
    print(f"   (n={num_vars})")

    # Majority
    print(f"  {'Majority':<20}", end="")
    for n in [5, 7, 9, 11, 13, 15]:
        gates, num_vars = build_majority(n)
        k = num_vars // 2
        pr = measure_det(gates, num_vars, k, 3000)
        print(f"  {pr:7.3f}", end="")
    print()
    sys.stdout.flush()

    # ------------------------------------------------------------------
    # ТЕСТ 2: XOR — worst case? Pr vs k/n
    # ------------------------------------------------------------------
    print()
    print("=" * 72)
    print("  ТЕСТ 2: XOR-цепочка — WORST CASE?")
    print("  XOR не имеет контролирующего значения → пропагация трудна")
    print("=" * 72)
    print()

    print(f"  {'k/n':>5}", end="")
    for n in [8, 12, 16, 20, 30]:
        print(f"  {'n='+str(n):>7}", end="")
    print()
    print(f"  {'-'*45}")

    for frac in [0.3, 0.5, 0.7, 0.8, 0.9, 1.0]:
        print(f"  {frac:5.1f}", end="")
        for n in [8, 12, 16, 20, 30]:
            gates, nv = build_xor_chain(n)
            k = max(1, int(frac * n))
            pr = measure_det(gates, nv, k, 3000)
            print(f"  {pr:7.3f}", end="")
        print()
        sys.stdout.flush()

    # ------------------------------------------------------------------
    # ТЕСТ 3: Tseitin — масштабирование
    # ------------------------------------------------------------------
    print()
    print("=" * 72)
    print("  ТЕСТ 3: Tseitin — масштабирование Pr vs n при k=n/2")
    print("=" * 72)
    print()

    print(f"  {'n':>5} {'Pr[det]':>8} {'тренд':>8}")
    print(f"  {'-'*25}")
    prev = None
    for n in [8, 10, 12, 15, 18, 20, 25, 30, 35, 40]:
        gates, nv = build_tseitin(n)
        k = nv // 2
        pr = measure_det(gates, nv, k, 3000)
        trend = ""
        if prev is not None:
            if pr > prev + 0.01:
                trend = "↑"
            elif pr < prev - 0.01:
                trend = "↓"
            else:
                trend = "≈"
        prev = pr
        print(f"  {n:5d} {pr:8.4f} {trend:>8}")
        sys.stdout.flush()

    # ------------------------------------------------------------------
    # ТЕСТ 4: Случайные DAG-схемы — масштабирование
    # ------------------------------------------------------------------
    print()
    print("=" * 72)
    print("  ТЕСТ 4: Случайные DAG-схемы — масштабирование")
    print("=" * 72)
    print()

    print(f"  {'n':>5} {'size':>6} {'Pr[det]':>8} {'тренд':>8}")
    print(f"  {'-'*30}")
    prev = None
    for n in [8, 10, 12, 15, 20, 25, 30, 40, 50]:
        gates, nv = build_random_circuit(n, size_mult=5)
        k = nv // 2
        pr = measure_det(gates, nv, k, 3000)
        trend = ""
        if prev is not None:
            if pr > prev + 0.01:
                trend = "↑"
            elif pr < prev - 0.01:
                trend = "↓"
            else:
                trend = "≈"
        prev = pr
        print(f"  {n:5d} {len(gates):6d} {pr:8.4f} {trend:>8}")
        sys.stdout.flush()

    # ------------------------------------------------------------------
    # ТЕСТ 5: Поиск контрпримера — минимальная Pr среди типов
    # ------------------------------------------------------------------
    print()
    print("=" * 72)
    print("  ТЕСТ 5: Минимальная Pr[det] среди ВСЕХ типов при k=n/2")
    print("=" * 72)
    print()

    n_test = 20
    results = []

    # Много разных схем
    for trial in range(10):
        # Random 3-SAT
        g, nv = build_3sat(n_test)
        pr = measure_det(g, nv, nv // 2, 2000)
        results.append(("3-SAT", pr))

        # Random circuit
        for mult in [3, 5, 10]:
            g, nv = build_random_circuit(n_test, mult)
            pr = measure_det(g, nv, nv // 2, 2000)
            results.append((f"DAG×{mult}", pr))

    # Fixed types
    g, nv = build_tseitin(n_test)
    pr = measure_det(g, nv, nv // 2, 3000)
    results.append(("Tseitin", pr))

    g, nv = build_xor_chain(n_test)
    pr = measure_det(g, nv, nv // 2, 3000)
    results.append(("XOR-chain", pr))

    g, nv = build_php(6, 5)  # 30 переменных, closest to n=20
    pr = measure_det(g, nv, nv // 2, 3000)
    results.append(("PHP(6,5)", pr))

    g, nv = build_majority(n_test)
    pr = measure_det(g, nv, nv // 2, 3000)
    results.append(("Majority", pr))

    results.sort(key=lambda x: x[1])
    print(f"  {'Тип':<15} {'Pr[det]':>8}")
    print(f"  {'-'*25}")
    for name, pr in results[:15]:
        marker = " ← MIN" if pr == results[0][1] else ""
        print(f"  {name:<15} {pr:8.4f}{marker}")

    worst_name, worst_pr = results[0]

    # ------------------------------------------------------------------
    # ИТОГ
    # ------------------------------------------------------------------
    print()
    print("=" * 72)
    print("  ИТОГ: WORST-CASE ANALYSIS")
    print("=" * 72)
    print(f"""
  Худший случай при n≈{n_test}, k=n/2: {worst_name} с Pr = {worst_pr:.4f}

  ВОПРОС: Pr → 1 для ВСЕХ типов при n → ∞?
  Или XOR-цепочка / другие дают Pr → const < 1?

  Если Pr → 1 для всех: → Williams → NEXP ⊄ P/poly.
  Если Pr ↛ 1 для XOR:  → нужен другой подход для worst-case.
    """)


if __name__ == "__main__":
    main()
