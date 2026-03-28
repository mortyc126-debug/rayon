"""
╔══════════════════════════════════════════════════════════════════════════╗
║  ТРИ НАПРАВЛЕНИЯ усиления determination для глубоких схем              ║
║  1. Длинный AND-chain на выходе                                        ║
║  2. Алгебраическая пропагация (XOR + AND/OR)                          ║
║  3. Умный выбор переменных (influential-first)                         ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import random
import math
import sys
from collections import defaultdict


# ====================================================================
# БАЗОВЫЙ ДВИЖОК
# ====================================================================

def propagate_basic(gates, fixed_vars):
    """Стандартная constant propagation."""
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
    return wire.get(gates[-1][3]) if gates else None


def propagate_algebraic(gates, n, fixed_vars):
    """Алгебраическая пропагация: отслеживаем линейные зависимости.

    Каждый провод может быть:
      - Константа: (val, None)           — определён
      - Линейная: (coeff, frozenset)      — XOR переменных + const
      - Неизвестно: None

    XOR(a, b) с линейными входами → линейный выход.
    AND/OR с константным входом → пропагация.
    AND/OR с линейными входами → иногда можно определить.
    """
    # wire[id] = (value, deps) или None
    # value = 0 или 1, deps = frozenset переменных (XOR)
    # Если deps is None: чистая константа
    # Если deps: value XOR (XOR переменных в deps)
    wire = {}

    for v, val in fixed_vars.items():
        wire[v] = (val, None)  # константа

    for v in range(n):
        if v not in wire:
            wire[v] = (0, frozenset([v]))  # x_v = 0 XOR x_v

    for gtype, i1, i2, out in gates:
        w1 = wire.get(i1)
        w2 = wire.get(i2) if i2 >= 0 else None

        if gtype == 'NOT':
            if w1 is not None:
                val, deps = w1
                wire[out] = (1 - val, deps)  # NOT(a XOR S) = (1-a) XOR S
            # else: None

        elif gtype == 'AND':
            if w1 is not None and w1[1] is None and w1[0] == 0:
                wire[out] = (0, None)  # 0 AND x = 0
            elif w2 is not None and w2[1] is None and w2[0] == 0:
                wire[out] = (0, None)
            elif (w1 is not None and w1[1] is None and w1[0] == 1 and
                  w2 is not None):
                wire[out] = w2  # 1 AND x = x
            elif (w2 is not None and w2[1] is None and w2[0] == 1 and
                  w1 is not None):
                wire[out] = w1
            elif w1 is not None and w2 is not None:
                if w1[1] is None and w2[1] is None:
                    wire[out] = (w1[0] & w2[0], None)
                # Линейные: AND(a XOR S1, b XOR S2) — нелинейно, не отслеживаем
                # НО: если одинаковые зависимости, можем
                elif w1[1] is not None and w1[1] == w2[1]:
                    # AND(a XOR S, b XOR S) = AND(a,b) XOR (a AND S) XOR ...
                    # Слишком сложно, оставляем None
                    pass

        elif gtype == 'OR':
            if w1 is not None and w1[1] is None and w1[0] == 1:
                wire[out] = (1, None)  # 1 OR x = 1
            elif w2 is not None and w2[1] is None and w2[0] == 1:
                wire[out] = (1, None)
            elif (w1 is not None and w1[1] is None and w1[0] == 0 and
                  w2 is not None):
                wire[out] = w2  # 0 OR x = x
            elif (w2 is not None and w2[1] is None and w2[0] == 0 and
                  w1 is not None):
                wire[out] = w1
            elif w1 is not None and w2 is not None:
                if w1[1] is None and w2[1] is None:
                    wire[out] = (w1[0] | w2[0], None)

    out_wire = wire.get(gates[-1][3]) if gates else None
    if out_wire is not None and out_wire[1] is None:
        return out_wire[0]  # чистая константа
    return None


def compute_influence(gates, n):
    """Вычисляем влияние каждой переменной на выход.
    Influence(x_i) = Pr_{x}[f(x) ≠ f(x ⊕ e_i)]."""
    if n > 18:
        # Сэмплируем
        trials = 2000
        influence = [0] * n
        for _ in range(trials):
            x = [random.randint(0, 1) for _ in range(n)]
            base_fixed = {i: x[i] for i in range(n)}
            base_out = propagate_basic(gates, base_fixed)
            if base_out is None:
                continue
            for i in range(n):
                flipped = dict(base_fixed)
                flipped[i] = 1 - flipped[i]
                flip_out = propagate_basic(gates, flipped)
                if flip_out is not None and flip_out != base_out:
                    influence[i] += 1
        return [inf / max(1, trials) for inf in influence]
    else:
        influence = [0] * n
        total = 0
        for bits in range(2 ** n):
            x = {i: (bits >> i) & 1 for i in range(n)}
            base = propagate_basic(gates, x)
            if base is None:
                continue
            total += 1
            for i in range(n):
                flipped = dict(x)
                flipped[i] = 1 - flipped[i]
                f = propagate_basic(gates, flipped)
                if f is not None and f != base:
                    influence[i] += 1
        return [inf / max(1, total) for inf in influence]


def measure_det_smart(gates, n, k, trials=2000, order='random'):
    """Determination с разными стратегиями выбора переменных."""
    if order == 'influential':
        influence = compute_influence(gates, n)
        ranked = sorted(range(n), key=lambda i: -influence[i])
    elif order == 'anti_influential':
        influence = compute_influence(gates, n)
        ranked = sorted(range(n), key=lambda i: influence[i])

    det = 0
    for _ in range(trials):
        if order == 'random':
            vs = random.sample(range(n), min(k, n))
        elif order == 'influential':
            vs = ranked[:k]
        elif order == 'anti_influential':
            vs = ranked[:k]
        elif order == 'first_k':
            vs = list(range(k))

        fixed = {v: random.randint(0, 1) for v in vs}

        if propagate_basic(gates, fixed) is not None:
            det += 1
    return det / trials


def measure_det_algebraic(gates, n, k, trials=2000):
    """Determination с алгебраической пропагацией."""
    det = 0
    for _ in range(trials):
        vs = random.sample(range(n), min(k, n))
        fixed = {v: random.randint(0, 1) for v in vs}
        if propagate_algebraic(gates, n, fixed) is not None:
            det += 1
    return det / trials


# ====================================================================
# ГЕНЕРАТОРЫ СХЕМ
# ====================================================================

def build_tm(n, steps, acceptance='all'):
    """TM simulation: Rule 110-подобная.
    acceptance: 'first3', 'all', 'half', 'or_all'."""
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

    if acceptance == 'first3':
        cells = prev[:min(3, n)]
    elif acceptance == 'all':
        cells = prev
    elif acceptance == 'half':
        cells = prev[:n//2]
    elif acceptance == 'or_all':
        # OR вместо AND!
        cur = prev[0]
        for p in prev[1:]:
            gates.append(('OR', cur, p, nid)); cur = nid; nid += 1
        return gates, n

    # AND-цепочка
    cur = cells[0]
    for p in cells[1:]:
        gates.append(('AND', cur, p, nid)); cur = nid; nid += 1
    return gates, n


def build_tm_cnf_style(n, steps):
    """TM simulation но с CNF-подобным acceptance:
    Для каждого шага t, проверяем несколько conditions.
    Формула = AND всех conditions по всем шагам × ячейкам.
    Это даёт AND-chain длины n × steps!"""
    gates = []
    nid = n
    prev = list(range(n))

    all_conditions = []

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

            # Condition: OR(cell_new, некоторый другой провод)
            # Это "мягкое" условие, как клоз
            if random.random() < 0.3:
                other = random.choice(prev)
                cond = nid; gates.append(('OR', r, other, cond)); nid += 1
                all_conditions.append(cond)

        prev = new

    # Добавляем conditions из последнего шага
    for cell in prev:
        neg_cell = nid; gates.append(('NOT', cell, -1, neg_cell)); nid += 1
        # Условие: cell OR NOT(cell) = 1 всегда... нет, давай осмысленно
        # OR(cell[i], cell[(i+1)%n]) — соседние ячейки
    for i in range(n):
        cond = nid
        gates.append(('OR', prev[i], prev[(i+1)%n], cond))
        nid += 1
        all_conditions.append(cond)

    if not all_conditions:
        all_conditions = prev

    # AND-chain всех conditions
    cur = all_conditions[0]
    for c in all_conditions[1:]:
        gates.append(('AND', cur, c, nid)); cur = nid; nid += 1

    return gates, n, len(all_conditions)


def build_xor_chain_native(n):
    """XOR-цепочка через нативные XOR-гейты (для алгебраической пропагации)."""
    gates = []
    nid = n
    cur = 0
    for i in range(1, n):
        # Кодируем через AND/OR/NOT но МАРКИРУЕМ для алгебры
        # XOR(a,b) = OR(AND(a, NOT b), AND(NOT a, b))
        neg_cur = nid; gates.append(('NOT', cur, -1, neg_cur)); nid += 1
        neg_b = nid; gates.append(('NOT', i, -1, neg_b)); nid += 1
        t1 = nid; gates.append(('AND', cur, neg_b, t1)); nid += 1
        t2 = nid; gates.append(('AND', neg_cur, i, t2)); nid += 1
        xor_out = nid; gates.append(('OR', t1, t2, xor_out)); nid += 1
        cur = xor_out
    return gates, n


def build_xor_chain_xor_gates(n):
    """XOR-цепочка через XOR-гейты (для тестирования алгебраической пропагации)."""
    gates = []
    nid = n
    cur = 0
    for i in range(1, n):
        gates.append(('XOR', cur, i, nid))
        cur = nid
        nid += 1
    return gates, n


# ====================================================================
# НАПРАВЛЕНИЕ 1: Длинный AND-chain
# ====================================================================

def test_direction1():
    print("=" * 72)
    print("  НАПРАВЛЕНИЕ 1: Длинный AND-chain на выходе TM")
    print("  Гипотеза: AND(всех n ячеек) → AND-chain = n → Pr растёт")
    print("=" * 72)
    print()

    print(f"  {'n':>4} {'first3':>8} {'half':>8} {'all':>8} {'or_all':>8} {'cnf':>8}")
    print(f"  {'-'*44}")

    for n in [8, 10, 12, 15, 18, 20, 25, 30]:
        row = f"  {n:4d}"
        for acc in ['first3', 'half', 'all', 'or_all']:
            g, nv = build_tm(n, n, acc)
            pr = measure_det_smart(g, nv, nv // 2, 2000, 'random')
            row += f" {pr:8.4f}"

        # CNF-style
        g, nv, num_cond = build_tm_cnf_style(n, n)
        pr = measure_det_smart(g, nv, nv // 2, 2000, 'random')
        row += f" {pr:8.4f}"
        print(row)
        sys.stdout.flush()

    # Масштабирование AND(all)
    print()
    print("  TM + AND(all): масштабирование")
    print(f"  {'n':>4} {'AND-chain':>10} {'Pr[det]':>8} {'тренд':>6}")
    print(f"  {'-'*32}")
    prev = None
    for n in [8, 10, 15, 20, 25, 30, 35, 40]:
        g, nv = build_tm(n, n, 'all')
        pr = measure_det_smart(g, nv, nv // 2, 2000, 'random')
        trend = ""
        if prev is not None:
            trend = "↑" if pr > prev + 0.01 else ("↓" if pr < prev - 0.01 else "≈")
        prev = pr
        print(f"  {n:4d} {n:10d} {pr:8.4f} {trend:>6}")
        sys.stdout.flush()


# ====================================================================
# НАПРАВЛЕНИЕ 2: Алгебраическая пропагация
# ====================================================================

def test_direction2():
    print()
    print("=" * 72)
    print("  НАПРАВЛЕНИЕ 2: Алгебраическая пропагация")
    print("  Отслеживаем линейные зависимости (XOR) + константы")
    print("=" * 72)
    print()

    # Тест на XOR-цепочке (через AND/OR/NOT)
    print("  А) XOR-цепочка через AND/OR/NOT:")
    print(f"  {'n':>4} {'basic':>8} {'algebraic':>10}")
    print(f"  {'-'*24}")
    for n in [6, 8, 10, 12, 15, 20]:
        g, nv = build_xor_chain_native(n)
        pr_basic = measure_det_smart(g, nv, nv // 2, 2000, 'random')
        pr_alg = measure_det_algebraic(g, nv, nv // 2, 2000)
        print(f"  {n:4d} {pr_basic:8.4f} {pr_alg:10.4f}")
        sys.stdout.flush()

    # Тест на XOR с нативными XOR-гейтами
    print()
    print("  Б) XOR-цепочка с нативными XOR-гейтами:")

    # Для нативных XOR нужен расширенный propagator
    def propagate_xor_native(gates, n, fixed_vars):
        """Пропагация с поддержкой XOR-гейтов + линейная алгебра."""
        # Каждый провод: (const, set_of_free_vars) означает const XOR (XOR vars)
        wire = {}
        for v, val in fixed_vars.items():
            wire[v] = (val, frozenset())
        for v in range(n):
            if v not in wire:
                wire[v] = (0, frozenset([v]))

        for gtype, i1, i2, out in gates:
            w1 = wire.get(i1)
            w2 = wire.get(i2) if i2 >= 0 else None

            if gtype == 'XOR':
                if w1 is not None and w2 is not None:
                    # XOR: (a XOR S1) XOR (b XOR S2) = (a^b) XOR (S1 △ S2)
                    new_const = w1[0] ^ w2[0]
                    new_deps = w1[1].symmetric_difference(w2[1])
                    wire[out] = (new_const, new_deps)
            elif gtype == 'NOT':
                if w1 is not None:
                    wire[out] = (1 - w1[0], w1[1])
            elif gtype == 'AND':
                if w1 is not None and len(w1[1]) == 0 and w1[0] == 0:
                    wire[out] = (0, frozenset())
                elif w2 is not None and len(w2[1]) == 0 and w2[0] == 0:
                    wire[out] = (0, frozenset())
                elif (w1 is not None and len(w1[1]) == 0 and w1[0] == 1
                      and w2 is not None):
                    wire[out] = w2
                elif (w2 is not None and len(w2[1]) == 0 and w2[0] == 1
                      and w1 is not None):
                    wire[out] = w1
                elif w1 is not None and w2 is not None:
                    if len(w1[1]) == 0 and len(w2[1]) == 0:
                        wire[out] = (w1[0] & w2[0], frozenset())
            elif gtype == 'OR':
                if w1 is not None and len(w1[1]) == 0 and w1[0] == 1:
                    wire[out] = (1, frozenset())
                elif w2 is not None and len(w2[1]) == 0 and w2[0] == 1:
                    wire[out] = (1, frozenset())
                elif (w1 is not None and len(w1[1]) == 0 and w1[0] == 0
                      and w2 is not None):
                    wire[out] = w2
                elif (w2 is not None and len(w2[1]) == 0 and w2[0] == 0
                      and w1 is not None):
                    wire[out] = w1
                elif w1 is not None and w2 is not None:
                    if len(w1[1]) == 0 and len(w2[1]) == 0:
                        wire[out] = (w1[0] | w2[0], frozenset())

        out_w = wire.get(gates[-1][3]) if gates else None
        if out_w is not None and len(out_w[1]) == 0:
            return out_w[0]
        return None

    print(f"  {'n':>4} {'basic':>8} {'algebraic':>10}")
    print(f"  {'-'*24}")
    for n in [6, 8, 10, 12, 15, 20, 30]:
        g, nv = build_xor_chain_xor_gates(n)
        # basic: пропагация не знает XOR
        det_basic = 0
        det_alg = 0
        trials = 2000
        for _ in range(trials):
            vs = random.sample(range(nv), nv // 2)
            fixed = {v: random.randint(0, 1) for v in vs}
            if propagate_basic(g, fixed) is not None:
                det_basic += 1
            if propagate_xor_native(g, nv, fixed) is not None:
                det_alg += 1
        print(f"  {n:4d} {det_basic/trials:8.4f} {det_alg/trials:10.4f}")
        sys.stdout.flush()

    # Тест на TM-simulation
    print()
    print("  В) TM-simulation с алгебраической пропагацией:")
    print(f"  {'n':>4} {'basic':>8} {'algebraic':>10}")
    print(f"  {'-'*24}")
    for n in [8, 10, 12, 15, 20]:
        g, nv = build_tm(n, n, 'all')
        pr_basic = measure_det_smart(g, nv, nv // 2, 2000, 'random')
        pr_alg = measure_det_algebraic(g, nv, nv // 2, 2000)
        print(f"  {n:4d} {pr_basic:8.4f} {pr_alg:10.4f}")
        sys.stdout.flush()


# ====================================================================
# НАПРАВЛЕНИЕ 3: Умный выбор переменных
# ====================================================================

def test_direction3():
    print()
    print("=" * 72)
    print("  НАПРАВЛЕНИЕ 3: Умный выбор переменных")
    print("  Стратегии: random, influential-first, anti-influential")
    print("=" * 72)
    print()

    # TM simulation
    print("  А) TM-simulation (n=20, steps=20, acceptance=all):")
    g_tm, nv_tm = build_tm(20, 20, 'all')

    # Compute influence
    influence = compute_influence(g_tm, nv_tm)
    print(f"  Influence: min={min(influence):.4f}, max={max(influence):.4f}, "
          f"mean={sum(influence)/len(influence):.4f}")
    print()

    print(f"  {'k/n':>5} {'random':>8} {'influen':>8} {'anti-inf':>8} {'first_k':>8}")
    print(f"  {'-'*38}")
    for frac in [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
        k = max(1, int(frac * nv_tm))
        pr_rand = measure_det_smart(g_tm, nv_tm, k, 2000, 'random')
        pr_inf = measure_det_smart(g_tm, nv_tm, k, 2000, 'influential')
        pr_anti = measure_det_smart(g_tm, nv_tm, k, 2000, 'anti_influential')
        pr_first = measure_det_smart(g_tm, nv_tm, k, 2000, 'first_k')
        print(f"  {frac:5.1f} {pr_rand:8.4f} {pr_inf:8.4f} {pr_anti:8.4f} {pr_first:8.4f}")
        sys.stdout.flush()

    # Масштабирование influential при k=n/2
    print()
    print("  Б) Масштабирование: influential-first при k=n/2")
    print(f"  {'n':>4} {'random':>8} {'influen':>8} {'ratio':>8}")
    print(f"  {'-'*30}")
    for n in [8, 10, 12, 15, 18, 20, 25]:
        g, nv = build_tm(n, n, 'all')
        pr_rand = measure_det_smart(g, nv, nv // 2, 2000, 'random')
        pr_inf = measure_det_smart(g, nv, nv // 2, 2000, 'influential')
        ratio = pr_inf / max(0.001, pr_rand)
        print(f"  {n:4d} {pr_rand:8.4f} {pr_inf:8.4f} {ratio:8.2f}x")
        sys.stdout.flush()

    # XOR-цепочка
    print()
    print("  В) XOR-цепочка: influential-first")
    print(f"  {'n':>4} {'random':>8} {'influen':>8}")
    print(f"  {'-'*22}")
    for n in [8, 10, 12, 15, 20]:
        g, nv = build_xor_chain_native(n)
        pr_rand = measure_det_smart(g, nv, nv // 2, 2000, 'random')
        pr_inf = measure_det_smart(g, nv, nv // 2, 2000, 'influential')
        print(f"  {n:4d} {pr_rand:8.4f} {pr_inf:8.4f}")
        sys.stdout.flush()

    # Случайные DAG
    print()
    print("  Г) Случайные DAG-схемы: influential-first")
    print(f"  {'n':>4} {'random':>8} {'influen':>8} {'ratio':>8}")
    print(f"  {'-'*30}")
    for n in [10, 15, 20, 25, 30]:
        gates = []
        nid = n
        for _ in range(5 * n):
            gtype = random.choice(['AND', 'OR', 'NOT'])
            if gtype == 'NOT':
                i1 = random.randint(0, nid - 1)
                gates.append(('NOT', i1, -1, nid))
            else:
                i1 = random.randint(0, nid - 1)
                i2 = random.randint(0, nid - 1)
                gates.append((gtype, i1, i2, nid))
            nid += 1
        pr_rand = measure_det_smart(gates, n, n // 2, 2000, 'random')
        pr_inf = measure_det_smart(gates, n, n // 2, 2000, 'influential')
        ratio = pr_inf / max(0.001, pr_rand)
        print(f"  {n:4d} {pr_rand:8.4f} {pr_inf:8.4f} {ratio:8.2f}x")
        sys.stdout.flush()


# ====================================================================
# КОМБИНИРОВАННЫЙ ТЕСТ: все три направления вместе
# ====================================================================

def test_combined():
    print()
    print("=" * 72)
    print("  КОМБИНАЦИЯ: AND-chain + алгебра + influential-first")
    print("  на TM-simulation")
    print("=" * 72)
    print()

    print(f"  {'n':>4} {'basic':>8} {'AND-all':>8} {'alg':>8} "
          f"{'influen':>8} {'ALL':>8}")
    print(f"  {'-'*48}")

    for n in [8, 10, 12, 15, 18, 20, 25]:
        k = n // 2

        # Basic: TM + first3 + random + basic propagation
        g_basic, nv = build_tm(n, n, 'first3')
        pr_basic = measure_det_smart(g_basic, nv, k, 2000, 'random')

        # Direction 1: AND(all) + random + basic
        g_all, nv = build_tm(n, n, 'all')
        pr_andall = measure_det_smart(g_all, nv, k, 2000, 'random')

        # Direction 2: AND(all) + algebraic
        pr_alg = measure_det_algebraic(g_all, nv, k, 2000)

        # Direction 3: AND(all) + influential
        pr_inf = measure_det_smart(g_all, nv, k, 2000, 'influential')

        # ALL combined: AND(all) + algebraic + influential
        # Нужен комбинированный propagator
        influence = compute_influence(g_all, nv)
        ranked = sorted(range(nv), key=lambda i: -influence[i])
        det_all = 0
        trials = 2000
        for _ in range(trials):
            vs = ranked[:k]
            fixed = {v: random.randint(0, 1) for v in vs}
            if propagate_algebraic(g_all, nv, fixed) is not None:
                det_all += 1
        pr_all = det_all / trials

        print(f"  {n:4d} {pr_basic:8.4f} {pr_andall:8.4f} {pr_alg:8.4f} "
              f"{pr_inf:8.4f} {pr_all:8.4f}")
        sys.stdout.flush()


# ====================================================================
# MAIN
# ====================================================================

def main():
    random.seed(42)

    print("=" * 72)
    print("  ТРИ НАПРАВЛЕНИЯ УСИЛЕНИЯ DETERMINATION")
    print("=" * 72)

    test_direction1()
    test_direction2()
    test_direction3()
    test_combined()

    print()
    print("=" * 72)
    print("  ФИНАЛЬНЫЙ ИТОГ")
    print("=" * 72)
    print("""
  Направление 1 (AND-chain): ???
  Направление 2 (Алгебра):  ???
  Направление 3 (Influential): ???
  Комбинация: ???
    """)


if __name__ == "__main__":
    main()
