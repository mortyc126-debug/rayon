"""
╔══════════════════════════════════════════════════════════════════════════╗
║  STRUCTURED CIRCUITS: Determination для структурированных схем          ║
║  Вопрос: XOR — контрпример, но он искусственный.                       ║
║  Работает ли обрезка для схем из РЕАЛЬНЫХ вычислений?                  ║
╚══════════════════════════════════════════════════════════════════════════╝

Ключевое наблюдение: для Williams нужны схемы, моделирующие
вычисления NEXP-машин. Такие схемы имеют СТРУКТУРУ:
  - Слоистость (layered)
  - AND/OR гейты с fan-in 2
  - Ограниченный fan-out
  - Кодирование состояний через AND/OR (не XOR!)

Тестируем:
  1. Слоистые AND/OR схемы (чередование слоёв)
  2. Схемы симуляции TM (Кука-Левина)
  3. Формулы (fan-out = 1)
  4. Схемы с ограниченным fan-out
  5. Graph Coloring, Vertex Cover
  6. Ключевой тест: ДОЛЯ AND/OR гейтов vs Pr[det]
"""

import random
import math
import sys
from itertools import combinations


def propagate(gates, fixed_vars):
    """Пропагация констант через схему."""
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


def measure_det(gates, n, k, trials=2000):
    det = 0
    for _ in range(trials):
        vs = random.sample(range(n), min(k, n))
        fixed = {v: random.randint(0, 1) for v in vs}
        if propagate(gates, fixed) is not None:
            det += 1
    return det / trials


# ====================================================================
# 1. СЛОИСТЫЕ AND/OR СХЕМЫ
# ====================================================================

def build_layered_andor(n, depth, width=None):
    """Слоистая схема: чередование AND и OR слоёв.
    Слой 0: входы. Слой d: AND/OR от пар из слоя d-1.
    Моделирует типичные вычислительные схемы."""
    if width is None:
        width = n
    gates = []
    nid = n
    prev_layer = list(range(n))

    for d in range(depth):
        gtype = 'AND' if d % 2 == 0 else 'OR'
        new_layer = []
        # Каждый гейт берёт 2 случайных входа из предыдущего слоя
        layer_size = max(2, width // (2 ** (d // 2)))  # сужаем
        for _ in range(layer_size):
            i1 = random.choice(prev_layer)
            i2 = random.choice(prev_layer)
            gates.append((gtype, i1, i2, nid))
            new_layer.append(nid)
            nid += 1
        prev_layer = new_layer

    # Финальное объединение: AND всех выходов последнего слоя
    cur = prev_layer[0]
    for p in prev_layer[1:]:
        gates.append(('AND', cur, p, nid))
        cur = nid
        nid += 1

    return gates, n


def build_layered_strict(n, depth):
    """Строго слоистая: каждый слой ровно n/2^d гейтов,
    каждый гейт — пара соседних из предыдущего слоя."""
    gates = []
    nid = n
    prev = list(range(n))

    for d in range(depth):
        gtype = 'AND' if d % 2 == 0 else 'OR'
        new = []
        for i in range(0, len(prev) - 1, 2):
            gates.append((gtype, prev[i], prev[i + 1], nid))
            new.append(nid)
            nid += 1
        if len(prev) % 2 == 1:
            new.append(prev[-1])
        prev = new
        if len(prev) <= 1:
            break

    # Если осталось несколько, AND
    while len(prev) > 1:
        gates.append(('AND', prev[0], prev[1], nid))
        prev = [nid] + prev[2:]
        nid += 1

    return gates, n


# ====================================================================
# 2. СХЕМА СИМУЛЯЦИИ МАШИНЫ ТЬЮРИНГА (Кук-Левин)
# ====================================================================

def build_tm_simulation(n, steps=None):
    """Схема типа Кука-Левина: симуляция TM на n битах входа.
    Переменные: x[t][i] = содержимое ячейки i на шаге t.
    Переходы: x[t+1][i] = f(x[t][i-1], x[t][i], x[t][i+1]).
    f = локальная функция через AND/OR/NOT.

    Это ТОЧНАЯ модель схем из NEXP → P/poly."""
    if steps is None:
        steps = n  # линейное число шагов

    tape_size = n
    gates = []
    nid = n  # входы: 0..n-1

    # NOT для всех входов
    neg = {}
    for i in range(n):
        neg[i] = nid
        gates.append(('NOT', i, -1, nid))
        nid += 1

    prev_tape = list(range(n))  # начальная лента = входы

    for t in range(steps):
        new_tape = []
        for i in range(tape_size):
            # Локальная функция: x[t+1][i] зависит от x[t][i-1], x[t][i], x[t][i+1]
            left = prev_tape[(i - 1) % tape_size]
            center = prev_tape[i]
            right = prev_tape[(i + 1) % tape_size]

            # f(a,b,c) = (a AND b) OR (b AND c) OR (NOT a AND c)
            # Это Rule 110-подобная функция (Тьюринг-полная!)

            # a AND b
            ab = nid
            gates.append(('AND', left, center, ab))
            nid += 1

            # b AND c
            bc = nid
            gates.append(('AND', center, right, bc))
            nid += 1

            # NOT a
            not_left = nid
            gates.append(('NOT', left, -1, not_left))
            nid += 1

            # NOT a AND c
            nac = nid
            gates.append(('AND', not_left, right, nac))
            nid += 1

            # OR(ab, bc)
            t1 = nid
            gates.append(('OR', ab, bc, t1))
            nid += 1

            # OR(t1, nac)
            result = nid
            gates.append(('OR', t1, nac, result))
            nid += 1

            new_tape.append(result)

        prev_tape = new_tape

    # Выход: AND первых нескольких ячеек (acceptance condition)
    cur = prev_tape[0]
    for p in prev_tape[1:min(3, tape_size)]:
        gates.append(('AND', cur, p, nid))
        cur = nid
        nid += 1

    return gates, n


# ====================================================================
# 3. ФОРМУЛЫ (fan-out = 1)
# ====================================================================

def build_random_formula(n, size_mult=5):
    """Случайная формула: каждый гейт используется ровно один раз.
    Fan-out = 1 → это дерево."""
    gates = []
    nid = n
    # Пул доступных проводов
    pool = list(range(n))

    for _ in range(size_mult * n):
        if len(pool) < 2:
            break
        gtype = random.choice(['AND', 'OR', 'NOT'])
        if gtype == 'NOT':
            i1 = pool.pop(random.randint(0, len(pool) - 1))
            gates.append(('NOT', i1, -1, nid))
        else:
            idx1 = random.randint(0, len(pool) - 1)
            i1 = pool.pop(idx1)
            idx2 = random.randint(0, len(pool) - 1)
            i2 = pool.pop(idx2)
            gates.append((gtype, i1, i2, nid))
        pool.append(nid)
        nid += 1

    return gates, n


# ====================================================================
# 4. ОГРАНИЧЕННЫЙ FAN-OUT
# ====================================================================

def build_bounded_fanout(n, max_fanout=2, size_mult=5):
    """Схема с ограниченным fan-out: каждый провод используется ≤ max_fanout раз."""
    gates = []
    nid = n
    fanout_count = {i: 0 for i in range(n)}
    available = list(range(n))

    for _ in range(size_mult * n):
        if len(available) < 2:
            break
        gtype = random.choice(['AND', 'OR', 'NOT'])
        if gtype == 'NOT':
            i1 = random.choice(available)
            fanout_count[i1] = fanout_count.get(i1, 0) + 1
            if fanout_count[i1] >= max_fanout:
                available.remove(i1)
            gates.append(('NOT', i1, -1, nid))
        else:
            i1 = random.choice(available)
            i2 = random.choice(available)
            fanout_count[i1] = fanout_count.get(i1, 0) + 1
            fanout_count[i2] = fanout_count.get(i2, 0) + 1
            if fanout_count[i1] >= max_fanout and i1 in available:
                available.remove(i1)
            if fanout_count[i2] >= max_fanout and i2 in available:
                available.remove(i2)
            gates.append((gtype, i1, i2, nid))
        fanout_count[nid] = 0
        available.append(nid)
        nid += 1

    return gates, n


# ====================================================================
# 5. GRAPH COLORING
# ====================================================================

def build_graph_coloring(num_vertices, num_edges, num_colors=3):
    """k-раскраска графа. Переменные: x_{v,c} = вершина v имеет цвет c.
    Клозы: (1) каждая вершина ровно один цвет, (2) соседи разного цвета."""
    n_vars = num_vertices * num_colors
    gates = []
    nid = n_vars

    def var(v, c):
        return v * num_colors + c

    neg = {}
    for i in range(n_vars):
        neg[i] = nid
        gates.append(('NOT', i, -1, nid))
        nid += 1

    clause_outs = []

    # Каждая вершина хотя бы один цвет
    for v in range(num_vertices):
        lits = [var(v, c) for c in range(num_colors)]
        cur = lits[0]
        for l in lits[1:]:
            out = nid
            gates.append(('OR', cur, l, out))
            nid += 1
            cur = out
        clause_outs.append(cur)

    # Генерируем рёбра
    all_edges = list(combinations(range(num_vertices), 2))
    edges = random.sample(all_edges, min(num_edges, len(all_edges)))

    # Соседи разного цвета: для ребра (u,v), цвета c: NOT(x_{u,c} AND x_{v,c})
    for u, v in edges:
        for c in range(num_colors):
            # OR(NOT x_{u,c}, NOT x_{v,c})
            out = nid
            gates.append(('OR', neg[var(u, c)], neg[var(v, c)], out))
            nid += 1
            clause_outs.append(out)

    # AND всех
    cur = clause_outs[0]
    for cl in clause_outs[1:]:
        out = nid
        gates.append(('AND', cur, cl, out))
        nid += 1
        cur = out

    return gates, n_vars


# ====================================================================
# 6. VERTEX COVER
# ====================================================================

def build_vertex_cover(num_vertices, num_edges, cover_size):
    """Vertex Cover: выбрать ≤ k вершин, покрывающих все рёбра.
    Переменные: x_v = вершина v в покрытии.
    Клозы: для каждого ребра (u,v): x_u OR x_v."""
    n_vars = num_vertices
    gates = []
    nid = n_vars

    neg = {}
    for i in range(n_vars):
        neg[i] = nid
        gates.append(('NOT', i, -1, nid))
        nid += 1

    clause_outs = []

    # Рёбра
    all_edges = list(combinations(range(num_vertices), 2))
    edges = random.sample(all_edges, min(num_edges, len(all_edges)))

    # Каждое ребро покрыто
    for u, v in edges:
        out = nid
        gates.append(('OR', u, v, out))
        nid += 1
        clause_outs.append(out)

    # Ограничение на размер: не более cover_size вершин
    # Кодируем: для каждого подмножества размера cover_size+1: NOT(AND всех)
    if num_vertices <= 15:
        for subset in combinations(range(num_vertices), cover_size + 1):
            cur = subset[0]
            for s in subset[1:]:
                out = nid
                gates.append(('AND', cur, s, out))
                nid += 1
                cur = out
            # NOT(AND всех)
            notall = nid
            gates.append(('NOT', cur, -1, notall))
            nid += 1
            clause_outs.append(notall)

    # AND всех клозов
    if not clause_outs:
        return gates, n_vars
    cur = clause_outs[0]
    for cl in clause_outs[1:]:
        out = nid
        gates.append(('AND', cur, cl, out))
        nid += 1
        cur = out

    return gates, n_vars


# ====================================================================
# ГЛАВНЫЙ ЭКСПЕРИМЕНТ
# ====================================================================

def main():
    random.seed(42)

    print("=" * 72)
    print("  STRUCTURED CIRCUITS: Determination для структурированных схем")
    print("=" * 72)

    # ------------------------------------------------------------------
    # ТЕСТ 1: Слоистые AND/OR
    # ------------------------------------------------------------------
    print()
    print("=" * 72)
    print("  ТЕСТ 1: Слоистые AND/OR схемы (модель реальных вычислений)")
    print("=" * 72)
    print()

    print("  А) Случайная слоистая схема (random wiring)")
    print(f"  {'n':>5} {'depth':>6} {'size':>6} {'Pr[det]':>8}")
    print(f"  {'-'*30}")
    for n in [10, 15, 20, 30, 40, 50]:
        depth = int(math.log2(n)) + 2
        gates, nv = build_layered_andor(n, depth)
        pr = measure_det(gates, nv, nv // 2, 3000)
        print(f"  {n:5d} {depth:6d} {len(gates):6d} {pr:8.4f}")
        sys.stdout.flush()

    print()
    print("  Б) Строго слоистая схема (tree-like, пары соседей)")
    print(f"  {'n':>5} {'Pr[det]':>8}")
    print(f"  {'-'*16}")
    for n in [8, 16, 32, 64, 128]:
        depth = int(math.log2(n))
        gates, nv = build_layered_strict(n, depth)
        pr = measure_det(gates, nv, nv // 2, 3000)
        print(f"  {n:5d} {pr:8.4f}")
        sys.stdout.flush()

    # ------------------------------------------------------------------
    # ТЕСТ 2: Симуляция TM (Кук-Левин)
    # ------------------------------------------------------------------
    print()
    print("=" * 72)
    print("  ТЕСТ 2: Симуляция TM (Rule 110-подобная, Кук-Левин)")
    print("  ЭТО ТОЧНАЯ МОДЕЛЬ для Williams!")
    print("=" * 72)
    print()

    print(f"  {'n':>5} {'steps':>6} {'size':>7} {'Pr[det] k=n/2':>14} {'тренд':>6}")
    print(f"  {'-'*42}")
    prev = None
    for n in [6, 8, 10, 12, 15, 18, 20, 25, 30]:
        steps = n
        gates, nv = build_tm_simulation(n, steps)
        pr = measure_det(gates, nv, nv // 2, 3000)
        trend = ""
        if prev is not None:
            trend = "↑" if pr > prev + 0.01 else ("↓" if pr < prev - 0.01 else "≈")
        prev = pr
        print(f"  {n:5d} {steps:6d} {len(gates):7d} {pr:14.4f} {trend:>6}")
        sys.stdout.flush()

    # Pr vs k/n для TM
    print()
    print("  TM simulation: Pr vs k/n")
    n_tm = 20
    gates_tm, nv_tm = build_tm_simulation(n_tm, n_tm)
    print(f"  n={n_tm}, steps={n_tm}, size={len(gates_tm)}")
    print(f"  {'k/n':>5} {'Pr[det]':>8}")
    print(f"  {'-'*16}")
    for frac in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        k = max(1, int(frac * n_tm))
        pr = measure_det(gates_tm, nv_tm, k, 3000)
        print(f"  {frac:5.1f} {pr:8.4f}")
    sys.stdout.flush()

    # ------------------------------------------------------------------
    # ТЕСТ 3: Формулы (fan-out = 1)
    # ------------------------------------------------------------------
    print()
    print("=" * 72)
    print("  ТЕСТ 3: Формулы (fan-out = 1, деревья)")
    print("=" * 72)
    print()

    print(f"  {'n':>5} {'size':>6} {'Pr[det]':>8} {'тренд':>6}")
    print(f"  {'-'*28}")
    prev = None
    for n in [8, 10, 15, 20, 25, 30, 40]:
        gates, nv = build_random_formula(n, 5)
        pr = measure_det(gates, nv, nv // 2, 3000)
        trend = ""
        if prev is not None:
            trend = "↑" if pr > prev + 0.01 else ("↓" if pr < prev - 0.01 else "≈")
        prev = pr
        print(f"  {n:5d} {len(gates):6d} {pr:8.4f} {trend:>6}")
        sys.stdout.flush()

    # ------------------------------------------------------------------
    # ТЕСТ 4: Ограниченный fan-out
    # ------------------------------------------------------------------
    print()
    print("=" * 72)
    print("  ТЕСТ 4: Ограниченный fan-out (f ≤ 2, 3, 5)")
    print("=" * 72)
    print()

    for max_fo in [2, 3, 5]:
        print(f"  Fan-out ≤ {max_fo}:")
        print(f"    {'n':>5} {'Pr[det]':>8}")
        prev = None
        for n in [10, 20, 30, 40]:
            gates, nv = build_bounded_fanout(n, max_fo, 5)
            pr = measure_det(gates, nv, nv // 2, 3000)
            print(f"    {n:5d} {pr:8.4f}")
        print()
        sys.stdout.flush()

    # ------------------------------------------------------------------
    # ТЕСТ 5: NP-задачи (Graph Coloring, Vertex Cover)
    # ------------------------------------------------------------------
    print()
    print("=" * 72)
    print("  ТЕСТ 5: NP-задачи (Graph Coloring, Vertex Cover)")
    print("=" * 72)
    print()

    print("  Graph 3-Coloring:")
    print(f"  {'V':>4} {'E':>4} {'n_vars':>7} {'Pr[det]':>8}")
    print(f"  {'-'*28}")
    for V in [5, 7, 9, 11, 13]:
        E = int(1.5 * V)
        gates, nv = build_graph_coloring(V, E, 3)
        pr = measure_det(gates, nv, nv // 2, 3000)
        print(f"  {V:4d} {E:4d} {nv:7d} {pr:8.4f}")
        sys.stdout.flush()

    print()
    print("  Vertex Cover:")
    print(f"  {'V':>4} {'E':>4} {'k':>4} {'Pr[det]':>8}")
    print(f"  {'-'*24}")
    for V in [6, 8, 10, 12, 14]:
        E = int(1.5 * V)
        k_cover = V // 3
        gates, nv = build_vertex_cover(V, E, k_cover)
        pr = measure_det(gates, nv, nv // 2, 3000)
        print(f"  {V:4d} {E:4d} {k_cover:4d} {pr:8.4f}")
        sys.stdout.flush()

    # ------------------------------------------------------------------
    # ТЕСТ 6: Ключевой анализ — ЧТО определяет Pr?
    # ------------------------------------------------------------------
    print()
    print("=" * 72)
    print("  ТЕСТ 6: ЧТО определяет Pr[det]?")
    print("  Гипотеза: AND/OR-цепочки в конце схемы — ключ")
    print("=" * 72)
    print()

    # Считаем: для каждого типа схемы, какая доля гейтов — AND и OR
    types = [
        ("3-SAT (n=30)", lambda: build_3sat_circuit(30)),
        ("Tseitin (n=30)", lambda: build_tseitin_circuit(30)),
        ("TM-sim (n=20)", lambda: build_tm_simulation(20, 20)),
        ("Layered (n=30)", lambda: build_layered_andor(30, 6)),
        ("Formula (n=30)", lambda: build_random_formula(30, 5)),
    ]

    def build_3sat_circuit(n):
        alpha = 4.27
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
            vars_ = random.sample(range(n), 3)
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

    def build_tseitin_circuit(n):
        num_vars = n
        gates = []
        nid = num_vars
        neg = {}
        for i in range(num_vars):
            neg[i] = nid
            gates.append(('NOT', i, -1, nid))
            nid += 1
        constraint_outs = []
        for v in range(n):
            a, b = v, (v + 1) % n
            t1 = nid; gates.append(('AND', a, neg[b], t1)); nid += 1
            t2 = nid; gates.append(('AND', neg[a], b, t2)); nid += 1
            xor_out = nid; gates.append(('OR', t1, t2, xor_out)); nid += 1
            constraint_outs.append(xor_out)
        cur = constraint_outs[0]
        for c in constraint_outs[1:]:
            out = nid; gates.append(('AND', cur, c, out)); nid += 1; cur = out
        return gates, num_vars

    print(f"  {'Тип':<20} {'AND%':>6} {'OR%':>6} {'NOT%':>6} "
          f"{'AND-chain':>10} {'Pr[det]':>8}")
    print(f"  {'-'*60}")

    for name, builder in types:
        gates, nv = builder()
        total = len(gates)
        n_and = sum(1 for g in gates if g[0] == 'AND')
        n_or = sum(1 for g in gates if g[0] == 'OR')
        n_not = sum(1 for g in gates if g[0] == 'NOT')

        # Длина AND-цепочки от выхода
        and_chain = 0
        out_id = gates[-1][3]
        seen = {out_id}
        queue = [out_id]
        while queue:
            gid = queue.pop(0)
            for g in gates:
                if g[3] == gid and g[0] == 'AND':
                    and_chain += 1
                    for inp in [g[1], g[2]]:
                        if inp >= nv and inp not in seen:
                            seen.add(inp)
                            queue.append(inp)
                    break

        pr = measure_det(gates, nv, nv // 2, 3000)

        print(f"  {name:<20} {100*n_and/total:5.1f}% {100*n_or/total:5.1f}% "
              f"{100*n_not/total:5.1f}% {and_chain:10d} {pr:8.4f}")
        sys.stdout.flush()

    # ------------------------------------------------------------------
    # ИТОГ
    # ------------------------------------------------------------------
    print()
    print("=" * 72)
    print("  ИТОГ: СТРУКТУРИРОВАННЫЕ СХЕМЫ")
    print("=" * 72)
    print("""
  Ключевые результаты:

  1. Слоистые AND/OR: Pr → ? (зависит от структуры)
  2. TM-симуляция:    Pr → ? (КРИТИЧЕСКИЙ тест для Williams)
  3. Формулы:         Pr → ? (fan-out = 1)
  4. NP-задачи:       Pr → ? (реальные задачи)

  ВОПРОС: Есть ли универсальный механизм для структурированных схем?
    """)


if __name__ == "__main__":
    main()
