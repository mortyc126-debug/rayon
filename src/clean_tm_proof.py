"""
╔══════════════════════════════════════════════════════════════════════════╗
║  ЧИСТОЕ ДОКАЗАТЕЛЬСТВО для Williams                                     ║
║  Три оставшихся вопроса:                                               ║
║    1. deep_cnf МЕНЯЕТ функцию → нужен НАТУРАЛЬНЫЙ acceptance          ║
║    2. Consecutive fixing — законная стратегия DFS?                      ║
║    3. Обобщение на произвольные TM-правила                             ║
╚══════════════════════════════════════════════════════════════════════════╝

ПРОБЛЕМА С deep_cnf:
  deep_cnf добавляет клозы OR(cell[t][i], cell[t][i+1]).
  Это МЕНЯЕТ функцию! SAT(C_deep_cnf) ≠ SAT(C_original).
  Нельзя использовать для Williams.

РЕШЕНИЕ:
  OR(final cells) — НАТУРАЛЬНЫЙ acceptance.
  "∃i: cell[T][i] = 1" = "TM посещает accept-state в позиции i".
  Эмпирика показала Pr → 1 для or_all + consecutive.

  НО: при T = n шагах, определённый регион ПУСТ на финальном шаге!
  (k - 2T = n/2 - 2n < 0). Нужно понять КАКОЙ механизм работает.
"""

import random
import math
import sys


def propagate_tracked(gates, n, fixed_vars):
    """Пропагация с трекингом: сколько гейтов определено на каждой глубине."""
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
    return wire


def build_tm_or_final(n, steps, rule='rule110'):
    """TM + OR(финальные ячейки). Натуральный acceptance."""
    gates = []
    nid = n
    prev = list(range(n))

    # Запоминаем gate-id ячеек каждого шага для анализа
    step_cells = [list(range(n))]

    for t in range(steps):
        new = []
        for i in range(n):
            left, center, right = prev[(i-1)%n], prev[i], prev[(i+1)%n]
            if rule == 'rule110':
                # f(a,b,c) = (a∧b) ∨ (b∧c) ∨ (¬a∧c)
                ab = nid; gates.append(('AND', left, center, ab)); nid += 1
                bc = nid; gates.append(('AND', center, right, bc)); nid += 1
                nl = nid; gates.append(('NOT', left, -1, nl)); nid += 1
                nac = nid; gates.append(('AND', nl, right, nac)); nid += 1
                t1 = nid; gates.append(('OR', ab, bc, t1)); nid += 1
                r = nid; gates.append(('OR', t1, nac, r)); nid += 1
            elif rule == 'rule30':
                # f(a,b,c) = a XOR (b OR c)
                # = (a AND NOT(b OR c)) OR (NOT a AND (b OR c))
                boc = nid; gates.append(('OR', center, right, boc)); nid += 1
                nboc = nid; gates.append(('NOT', boc, -1, nboc)); nid += 1
                t1 = nid; gates.append(('AND', left, nboc, t1)); nid += 1
                nl = nid; gates.append(('NOT', left, -1, nl)); nid += 1
                t2 = nid; gates.append(('AND', nl, boc, t2)); nid += 1
                r = nid; gates.append(('OR', t1, t2, r)); nid += 1
            elif rule == 'rule90':
                # f(a,b,c) = a XOR c = (a AND NOT c) OR (NOT a AND c)
                nc = nid; gates.append(('NOT', right, -1, nc)); nid += 1
                t1 = nid; gates.append(('AND', left, nc, t1)); nid += 1
                nl = nid; gates.append(('NOT', left, -1, nl)); nid += 1
                t2 = nid; gates.append(('AND', nl, right, t2)); nid += 1
                r = nid; gates.append(('OR', t1, t2, r)); nid += 1
            elif rule == 'majority':
                # f(a,b,c) = MAJ(a,b,c) = (a∧b) ∨ (b∧c) ∨ (a∧c)
                ab = nid; gates.append(('AND', left, center, ab)); nid += 1
                bc = nid; gates.append(('AND', center, right, bc)); nid += 1
                ac = nid; gates.append(('AND', left, right, ac)); nid += 1
                t1 = nid; gates.append(('OR', ab, bc, t1)); nid += 1
                r = nid; gates.append(('OR', t1, ac, r)); nid += 1
            elif rule == 'and_or':
                # f(a,b,c) = (a AND b) OR c — простое правило с контролирующими
                ab = nid; gates.append(('AND', left, center, ab)); nid += 1
                r = nid; gates.append(('OR', ab, right, r)); nid += 1
            new.append(r)
            nid += 1  # для r уже добавлено, но nid уже увеличен
        # Исправление: nid уже корректный
        prev = new
        step_cells.append(new)

    # OR-chain финальных ячеек
    or_start = nid
    cur = prev[0]
    for p in prev[1:]:
        gates.append(('OR', cur, p, nid))
        cur = nid
        nid += 1

    return gates, n, step_cells


def measure(gates, n, k, strategy='consecutive', trials=2000):
    det = 0
    for _ in range(trials):
        if strategy == 'random':
            vs = random.sample(range(n), min(k, n))
        elif strategy == 'consecutive':
            s = random.randint(0, n - 1)
            vs = [(s + i) % n for i in range(min(k, n))]
        fixed = {v: random.randint(0, 1) for v in vs}
        wire = dict(fixed)
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
        if wire.get(gates[-1][3]) is not None:
            det += 1
    return det / trials


def main():
    random.seed(42)

    print("=" * 72)
    print("  ЧИСТОЕ ДОКАЗАТЕЛЬСТВО: OR(final) + consecutive")
    print("  Без deep_cnf, натуральный acceptance для Williams")
    print("=" * 72)

    # ==================================================================
    # ВОПРОС 1: Механизм — КАК or_all работает при пустом регионе?
    # ==================================================================
    print()
    print("=" * 72)
    print("  ВОПРОС 1: Механизм определения при пустом регионе")
    print("  k = n/2, T = n шагов. Регион пуст на шаге n/4+")
    print("  Но Pr[det] → 1! Почему?")
    print("=" * 72)
    print()

    n = 20; k = 10; steps = 20
    gates, nv, step_cells = build_tm_or_final(n, steps, 'rule110')

    # Трекинг: сколько ячеек определено на каждом шаге
    trials = 500
    det_counts_per_step = {t: [] for t in range(steps + 1)}
    det_zero_per_step = {t: [] for t in range(steps + 1)}

    for _ in range(trials):
        s = random.randint(0, n - 1)
        vs = [(s + i) % n for i in range(k)]
        fixed = {v: random.randint(0, 1) for v in vs}

        wire = propagate_tracked(gates, n, fixed)

        for t in range(steps + 1):
            cells = step_cells[t]
            det_count = sum(1 for c in cells if wire.get(c) is not None)
            zero_count = sum(1 for c in cells if wire.get(c) == 0)
            det_counts_per_step[t].append(det_count)
            det_zero_per_step[t].append(zero_count)

    print(f"  {'step':>5} {'det cells':>10} {'=0 cells':>10} "
          f"{'region':>7} {'механизм':>20}")
    print(f"  {'-'*56}")
    for t in range(min(steps + 1, 15)):
        avg_det = sum(det_counts_per_step[t]) / trials
        avg_zero = sum(det_zero_per_step[t]) / trials
        region = max(0, k - 2*t)
        mechanism = ""
        if avg_det > region + 0.5:
            mechanism = f"СВЕРХ региона (+{avg_det - region:.1f})"
        elif avg_det < region - 0.5:
            mechanism = f"меньше региона"
        else:
            mechanism = "= регион"
        print(f"  {t:5d} {avg_det:10.1f} {avg_zero:10.1f} "
              f"{region:7d} {mechanism:>20}")
    # Последние шаги
    for t in [steps - 2, steps - 1, steps]:
        if t >= 0 and t <= steps:
            avg_det = sum(det_counts_per_step[t]) / trials
            avg_zero = sum(det_zero_per_step[t]) / trials
            region = max(0, k - 2*t)
            print(f"  {t:5d} {avg_det:10.1f} {avg_zero:10.1f} "
                  f"{region:7d} {'ФИНАЛ':>20}")

    # ==================================================================
    # ВОПРОС 1б: Механизм при РАЗНОМ числе шагов
    # ==================================================================
    print()
    print("  Механизм: Pr[det] vs число шагов (n=20, k=10)")
    print(f"  {'steps':>6} {'Pr[det]':>8} {'fin_det':>8} {'fin_zero':>9}")
    print(f"  {'-'*34}")

    for steps in [1, 2, 3, 5, 8, 10, 15, 20, 30]:
        gates, nv, sc = build_tm_or_final(n, steps, 'rule110')
        pr = measure(gates, nv, k, 'consecutive', 2000)

        # Среднее число определённых ячеек на финальном шаге
        det_fin = 0; zero_fin = 0; tr = 500
        for _ in range(tr):
            s = random.randint(0, n - 1)
            vs = [(s + i) % n for i in range(k)]
            fixed = {v: random.randint(0, 1) for v in vs}
            wire = propagate_tracked(gates, nv, fixed)
            cells = sc[steps]
            det_fin += sum(1 for c in cells if wire.get(c) is not None)
            zero_fin += sum(1 for c in cells if wire.get(c) == 0)
        print(f"  {steps:6d} {pr:8.4f} {det_fin/tr:8.1f} {zero_fin/tr:9.1f}")
        sys.stdout.flush()

    # ==================================================================
    # ВОПРОС 2: Consecutive = законная стратегия DFS
    # ==================================================================
    print()
    print("=" * 72)
    print("  ВОПРОС 2: Consecutive fixing = законная стратегия DFS")
    print("=" * 72)
    print("""
  DFS перебирает переменные в ЛЮБОМ порядке. Порядок — свободный
  параметр алгоритма. Consecutive = фиксированный порядок x_0, x_1, ...

  Это СТАНДАРТНАЯ стратегия: DPLL с фиксированным порядком переменных.
  Никаких проблем с законностью. ✓

  Для Williams: алгоритм SAT может выбрать ЛЮБОЙ порядок переменных.
  Мы выбираем consecutive → получаем ускорение.
    """)

    # ==================================================================
    # ВОПРОС 3: Обобщение на разные TM-правила
    # ==================================================================
    print()
    print("=" * 72)
    print("  ВОПРОС 3: Обобщение на разные TM-правила")
    print("  or_all + consecutive, k=n/2")
    print("=" * 72)
    print()

    rules = ['rule110', 'rule30', 'rule90', 'majority', 'and_or']

    # Масштабирование для каждого правила
    header = f"  {'n':>4}"
    for r in rules:
        header += f"  {r:>10}"
    print(header)
    print(f"  {'-'*4 + '-'*12*len(rules)}")

    for n in [8, 10, 12, 15, 20, 25, 30]:
        row = f"  {n:4d}"
        for rule in rules:
            try:
                gates, nv, sc = build_tm_or_final(n, n, rule)
                pr = measure(gates, nv, nv // 2, 'consecutive', 2000)
                row += f"  {pr:10.4f}"
            except Exception as e:
                row += f"  {'ERR':>10}"
        print(row)
        sys.stdout.flush()

    # Подробнее по best/worst rule
    print()
    print("  Детальное масштабирование для каждого правила:")
    for rule in rules:
        print(f"\n  {rule}:")
        print(f"    {'n':>4} {'consec':>8} {'random':>8}")
        prev_c = None
        for n in [10, 15, 20, 25, 30, 40]:
            try:
                gates, nv, sc = build_tm_or_final(n, n, rule)
                pr_c = measure(gates, nv, nv // 2, 'consecutive', 2000)
                pr_r = measure(gates, nv, nv // 2, 'random', 2000)
                trend = ""
                if prev_c is not None:
                    trend = "↑" if pr_c > prev_c + 0.01 else ("↓" if pr_c < prev_c - 0.01 else "≈")
                prev_c = pr_c
                print(f"    {n:4d} {pr_c:8.4f} {pr_r:8.4f} {trend}")
            except:
                print(f"    {n:4d} {'ERR':>8}")
            sys.stdout.flush()

    # ==================================================================
    # ВОПРОС 3б: Какие свойства правила определяют Pr?
    # ==================================================================
    print()
    print("=" * 72)
    print("  ВОПРОС 3б: Свойства правила → Pr[det]")
    print("  Гипотеза: правила с контролирующими значениями → лучше")
    print("=" * 72)
    print()

    # Для каждого правила: подсчитаем долю входов дающих 0
    rules_info = {
        'rule110': lambda a,b,c: (a&b)|(b&c)|((1-a)&c),
        'rule30': lambda a,b,c: a^(b|c),
        'rule90': lambda a,b,c: a^c,
        'majority': lambda a,b,c: (a&b)|(b&c)|(a&c),
        'and_or': lambda a,b,c: (a&b)|c,
    }

    print(f"  {'rule':>10} {'Pr[f=0]':>8} {'Pr[f=1]':>8} {'ctrl_0':>7} {'ctrl_1':>7}")
    print(f"  {'-'*44}")
    for name, f in rules_info.items():
        count_0 = sum(1 for a in [0,1] for b in [0,1] for c in [0,1] if f(a,b,c) == 0)
        count_1 = 8 - count_0
        # Контролирующие: ∃ позиция и значение, фиксация которых определяет выход
        ctrl_0 = 0  # число (pos, val) пар, фиксация которых → f = 0
        ctrl_1 = 0
        for pos in range(3):
            for val in [0, 1]:
                outputs = set()
                for a in [0,1]:
                    for b in [0,1]:
                        for c in [0,1]:
                            args = [a, b, c]
                            if args[pos] == val:
                                outputs.add(f(a, b, c))
                if len(outputs) == 1:
                    if 0 in outputs: ctrl_0 += 1
                    else: ctrl_1 += 1
        print(f"  {name:>10} {count_0/8:8.3f} {count_1/8:8.3f} {ctrl_0:7d} {ctrl_1:7d}")

    # ==================================================================
    # ГЛАВНЫЙ ТЕСТ: or_all + consecutive, масштабирование до n=60
    # ==================================================================
    print()
    print("=" * 72)
    print("  ГЛАВНЫЙ ТЕСТ: or_all + consecutive, rule110")
    print("  Масштабирование до больших n")
    print("=" * 72)
    print()

    print(f"  {'n':>4} {'Pr[det]':>8} {'1-Pr':>10} {'ln(1-Pr)':>10} {'-ln/n':>7}")
    print(f"  {'-'*42}")

    for n in [8, 10, 12, 15, 20, 25, 30, 35, 40, 50, 60]:
        steps = n
        gates, nv, sc = build_tm_or_final(n, steps, 'rule110')
        tr = 5000 if n <= 40 else 3000
        pr = measure(gates, nv, nv // 2, 'consecutive', tr)
        gap = max(1 - pr, 0.5 / tr)
        lg = math.log(gap)
        c = -lg / n
        print(f"  {n:4d} {pr:8.4f} {gap:10.6f} {lg:10.4f} {c:7.4f}")
        sys.stdout.flush()

    # ==================================================================
    # ИТОГ
    # ==================================================================
    print()
    print("=" * 72)
    print("  ИТОГ: ТРИ ВОПРОСА")
    print("=" * 72)
    print("""
  ВОПРОС 1 (deep_cnf): РЕШЁН.
    deep_cnf не нужен. OR(final cells) — натуральный acceptance.
    Механизм: ???  (определить из данных выше)

  ВОПРОС 2 (consecutive): РЕШЁН.
    Consecutive = стандартный порядок DPLL. Законная стратегия DFS. ✓

  ВОПРОС 3 (обобщение): ???
    Зависит от TM-правила. Результаты выше.
    """)


if __name__ == "__main__":
    main()
