"""
╔══════════════════════════════════════════════════════════════════════════╗
║  КОМБИНАЦИЯ: OR(all) + локальный выбор переменных для TM-схем         ║
║  Цель: Pr[определён] → 1 при n → ∞ для TM-simulation                 ║
╚══════════════════════════════════════════════════════════════════════════╝

Два открытия из предыдущего эксперимента:
  1. OR(all cells) даёт Pr = 0.83 при n=30 (vs 0.09 для AND(first3))
  2. Локальный выбор переменных даёт 3-4x vs random

Комбинируем: OR(all) + consecutive variables + разные acceptance
"""

import random
import math
import sys


def propagate(gates, fixed_vars):
    wire = dict(fixed_vars)
    for gtype, i1, i2, out in gates:
        v1 = wire.get(i1)
        v2 = wire.get(i2) if i2 >= 0 else None
        if gtype == 'AND':
            if v1 == 0 or v2 == 0: wire[out] = 0
            elif v1 is not None and v2 is not None: wire[out] = v1 & v2
        elif gtype == 'OR':
            if v1 == 1 or v2 == 1: wire[out] = 1
            elif v1 is not None and v2 is not None: wire[out] = v1 | v2
        elif gtype == 'NOT':
            if v1 is not None: wire[out] = 1 - v1
    return wire.get(gates[-1][3]) if gates else None


def build_tm(n, steps, acceptance='or_all'):
    """TM simulation с разными acceptance conditions."""
    gates = []
    nid = n
    prev = list(range(n))

    for t in range(steps):
        new = []
        for i in range(n):
            left, center, right = prev[(i-1)%n], prev[i], prev[(i+1)%n]
            ab = nid; gates.append(('AND', left, center, ab)); nid += 1
            bc = nid; gates.append(('AND', center, right, bc)); nid += 1
            nl = nid; gates.append(('NOT', left, -1, nl)); nid += 1
            nac = nid; gates.append(('AND', nl, right, nac)); nid += 1
            t1 = nid; gates.append(('OR', ab, bc, t1)); nid += 1
            r = nid; gates.append(('OR', t1, nac, r)); nid += 1
            new.append(r)
        prev = new

    cells = prev

    if acceptance == 'or_all':
        cur = cells[0]
        for p in cells[1:]:
            gates.append(('OR', cur, p, nid)); cur = nid; nid += 1
    elif acceptance == 'and_all':
        cur = cells[0]
        for p in cells[1:]:
            gates.append(('AND', cur, p, nid)); cur = nid; nid += 1
    elif acceptance == 'or_and_mix':
        # OR(AND(cell_0, cell_1), AND(cell_2, cell_3), ...)
        # Моделирует: "хотя бы одна пара соседних ячеек обе = 1"
        and_pairs = []
        for i in range(0, len(cells) - 1, 2):
            a = nid; gates.append(('AND', cells[i], cells[i+1], a)); nid += 1
            and_pairs.append(a)
        if len(cells) % 2 == 1:
            and_pairs.append(cells[-1])
        cur = and_pairs[0]
        for p in and_pairs[1:]:
            gates.append(('OR', cur, p, nid)); cur = nid; nid += 1
    elif acceptance == 'cnf_from_cells':
        # AND(OR(cell_i, cell_{i+1})) — CNF-подобная структура
        clause_outs = []
        for i in range(len(cells)):
            j = (i + 1) % len(cells)
            c = nid; gates.append(('OR', cells[i], cells[j], c)); nid += 1
            clause_outs.append(c)
        cur = clause_outs[0]
        for c in clause_outs[1:]:
            gates.append(('AND', cur, c, nid)); cur = nid; nid += 1
    elif acceptance == 'deep_cnf':
        # Добавляем клозы из РАЗНЫХ шагов вычисления
        # Сохраним промежуточные состояния и построим CNF
        # Для этого перестраиваем
        return build_tm_deep_cnf(n, steps)
    elif acceptance == 'first3':
        cur = cells[0]
        for p in cells[1:min(3, len(cells))]:
            gates.append(('AND', cur, p, nid)); cur = nid; nid += 1

    return gates, n


def build_tm_deep_cnf(n, steps):
    """TM с CNF acceptance из ВСЕХ шагов вычисления.
    Клозы: OR(cell[t][i], cell[t][i+1]) для каждого t и i.
    AND-chain длины ≈ n × steps!"""
    gates = []
    nid = n
    prev = list(range(n))
    all_clauses = []

    # Добавляем клозы из входного слоя
    for i in range(n):
        j = (i + 1) % n
        c = nid; gates.append(('OR', prev[i], prev[j], c)); nid += 1
        all_clauses.append(c)

    for t in range(steps):
        new = []
        for i in range(n):
            left, center, right = prev[(i-1)%n], prev[i], prev[(i+1)%n]
            ab = nid; gates.append(('AND', left, center, ab)); nid += 1
            bc = nid; gates.append(('AND', center, right, bc)); nid += 1
            nl = nid; gates.append(('NOT', left, -1, nl)); nid += 1
            nac = nid; gates.append(('AND', nl, right, nac)); nid += 1
            t1 = nid; gates.append(('OR', ab, bc, t1)); nid += 1
            r = nid; gates.append(('OR', t1, nac, r)); nid += 1
            new.append(r)

        # Клозы из этого шага
        for i in range(n):
            j = (i + 1) % n
            c = nid; gates.append(('OR', new[i], new[j], c)); nid += 1
            all_clauses.append(c)

        prev = new

    # AND-chain всех клозов
    cur = all_clauses[0]
    for c in all_clauses[1:]:
        gates.append(('AND', cur, c, nid)); cur = nid; nid += 1

    return gates, n


def measure(gates, n, k, strategy='random', trials=2000, start=0):
    """Измерение Pr[det] с разными стратегиями."""
    det = 0
    for _ in range(trials):
        if strategy == 'random':
            vs = random.sample(range(n), min(k, n))
        elif strategy == 'consecutive':
            # Последовательные переменные начиная с случайной позиции
            s = random.randint(0, n - 1)
            vs = [(s + i) % n for i in range(min(k, n))]
        elif strategy == 'consecutive_fixed':
            # Фиксированная начальная позиция
            vs = [(start + i) % n for i in range(min(k, n))]
        elif strategy == 'spread':
            # Равномерно распределённые
            step = max(1, n // k)
            s = random.randint(0, step - 1)
            vs = [(s + i * step) % n for i in range(min(k, n))]

        fixed = {v: random.randint(0, 1) for v in vs}
        if propagate(gates, fixed) is not None:
            det += 1
    return det / trials


def main():
    random.seed(42)

    print("=" * 72)
    print("  КОМБИНАЦИЯ: acceptance + стратегия выбора переменных")
    print("  для TM-simulation схем")
    print("=" * 72)

    # ==================================================================
    # ТЕСТ 1: Все acceptance × все стратегии при k=n/2
    # ==================================================================
    print()
    print("=" * 72)
    print("  ТЕСТ 1: acceptance × strategy grid (n=20, k=n/2)")
    print("=" * 72)
    print()

    n = 20
    k = n // 2
    acceptances = ['first3', 'and_all', 'or_all', 'or_and_mix',
                    'cnf_from_cells', 'deep_cnf']
    strategies = ['random', 'consecutive', 'spread']

    print(f"  {'acceptance':<16}", end="")
    for s in strategies:
        print(f" {s:>12}", end="")
    print()
    print(f"  {'-'*52}")

    for acc in acceptances:
        gates, nv = build_tm(n, n, acc)
        print(f"  {acc:<16}", end="")
        for strat in strategies:
            pr = measure(gates, nv, k, strat, 2000)
            print(f" {pr:12.4f}", end="")
        print()
        sys.stdout.flush()

    # ==================================================================
    # ТЕСТ 2: Масштабирование лучших комбинаций
    # ==================================================================
    print()
    print("=" * 72)
    print("  ТЕСТ 2: Масштабирование лучших комбинаций при k=n/2")
    print("=" * 72)
    print()

    combos = [
        ('first3', 'random'),       # baseline
        ('or_all', 'random'),        # направление 1
        ('and_all', 'consecutive'),  # направление 1+3
        ('or_all', 'consecutive'),   # направление 1+3
        ('cnf_from_cells', 'consecutive'),
        ('deep_cnf', 'random'),      # длинный AND-chain
        ('deep_cnf', 'consecutive'), # всё вместе
    ]

    header = f"  {'n':>4}"
    for acc, strat in combos:
        label = f"{acc[:6]}+{strat[:4]}"
        header += f" {label:>12}"
    print(header)
    print(f"  {'-'*4 + '-'*12*len(combos)}")

    for n in [8, 10, 12, 15, 18, 20, 25, 30]:
        row = f"  {n:4d}"
        for acc, strat in combos:
            gates, nv = build_tm(n, n, acc)
            pr = measure(gates, nv, nv // 2, strat, 2000)
            row += f" {pr:12.4f}"
        print(row)
        sys.stdout.flush()

    # ==================================================================
    # ТЕСТ 3: deep_cnf + consecutive — детальное масштабирование
    # ==================================================================
    print()
    print("=" * 72)
    print("  ТЕСТ 3: deep_cnf + consecutive — Pr → 1?")
    print("  AND-chain длины n×(steps+1), consecutive vars")
    print("=" * 72)
    print()

    print(f"  {'n':>4} {'chain_len':>10} {'Pr[det]':>8} {'тренд':>6}")
    print(f"  {'-'*32}")
    prev_pr = None
    for n in [6, 8, 10, 12, 15, 18, 20, 25, 30, 35, 40]:
        steps = n
        gates, nv = build_tm_deep_cnf(n, steps)
        chain_len = n * (steps + 1)
        pr = measure(gates, nv, nv // 2, 'consecutive', 3000)
        trend = ""
        if prev_pr is not None:
            trend = "↑" if pr > prev_pr + 0.01 else ("↓" if pr < prev_pr - 0.01 else "≈")
        prev_pr = pr
        print(f"  {n:4d} {chain_len:10d} {pr:8.4f} {trend:>6}")
        sys.stdout.flush()

    # ==================================================================
    # ТЕСТ 4: Pr vs k/n для лучшей комбинации
    # ==================================================================
    print()
    print("=" * 72)
    print("  ТЕСТ 4: Pr vs k/n для deep_cnf + consecutive (n=30)")
    print("=" * 72)
    print()

    n = 30
    gates, nv = build_tm_deep_cnf(n, n)
    print(f"  n={n}, chain_len={n*(n+1)}")
    print(f"  {'k/n':>5} {'consec':>8} {'random':>8} {'ratio':>6}")
    print(f"  {'-'*30}")
    for frac in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
        k = max(1, int(frac * n))
        pr_c = measure(gates, nv, k, 'consecutive', 3000)
        pr_r = measure(gates, nv, k, 'random', 3000)
        ratio = pr_c / max(0.001, pr_r)
        print(f"  {frac:5.1f} {pr_c:8.4f} {pr_r:8.4f} {ratio:5.1f}x")
        sys.stdout.flush()

    # ==================================================================
    # ТЕСТ 5: or_all + consecutive — тоже масштабирование
    # ==================================================================
    print()
    print("=" * 72)
    print("  ТЕСТ 5: or_all + consecutive — масштабирование")
    print("=" * 72)
    print()

    print(f"  {'n':>4} {'or+rand':>8} {'or+cons':>8} {'and+cons':>9} {'deep+cons':>10}")
    print(f"  {'-'*42}")
    for n in [8, 10, 12, 15, 20, 25, 30, 35, 40]:
        g_or, nv = build_tm(n, n, 'or_all')
        g_and, _ = build_tm(n, n, 'and_all')
        g_deep, _ = build_tm_deep_cnf(n, n)

        pr_or_r = measure(g_or, nv, nv//2, 'random', 2000)
        pr_or_c = measure(g_or, nv, nv//2, 'consecutive', 2000)
        pr_and_c = measure(g_and, nv, nv//2, 'consecutive', 2000)
        pr_deep_c = measure(g_deep, nv, nv//2, 'consecutive', 2000)

        print(f"  {n:4d} {pr_or_r:8.4f} {pr_or_c:8.4f} {pr_and_c:9.4f} {pr_deep_c:10.4f}")
        sys.stdout.flush()

    # ==================================================================
    # ТЕСТ 6: Разные число шагов TM (steps vs n)
    # ==================================================================
    print()
    print("=" * 72)
    print("  ТЕСТ 6: Влияние глубины (steps) при фикс. n=20")
    print("  deep_cnf + consecutive, k=n/2")
    print("=" * 72)
    print()

    n = 20
    print(f"  {'steps':>6} {'chain':>8} {'Pr[det]':>8}")
    print(f"  {'-'*24}")
    for steps in [1, 2, 5, 10, 15, 20, 30, 40]:
        gates, nv = build_tm_deep_cnf(n, steps)
        chain = n * (steps + 1)
        pr = measure(gates, nv, nv//2, 'consecutive', 2000)
        print(f"  {steps:6d} {chain:8d} {pr:8.4f}")
        sys.stdout.flush()

    # ==================================================================
    # ИТОГ
    # ==================================================================
    print()
    print("=" * 72)
    print("  ИТОГ")
    print("=" * 72)
    print("""
  Результаты трёх направлений на TM-simulation:

  1. OR(all cells): мощный acceptance, Pr до 0.83 при n=30
  2. deep_cnf: AND-chain длины n², максимум клозов
  3. Consecutive vars: 3-4x лучше random (локальность!)

  КЛЮЧЕВОЙ ВОПРОС: Pr → 1 при n → ∞?
  Или стабилизируется на const < 1?
    """)


if __name__ == "__main__":
    main()
