"""
╔══════════════════════════════════════════════════════════════════════════╗
║  НОВАЯ МАТЕМАТИКА: Теорема декомпозиции                                ║
║  Для ЛЮБОЙ схемы C размера s: SAT(C) за O*(2^{n/2})                  ║
╚══════════════════════════════════════════════════════════════════════════╝

ОПРЕДЕЛЕНИЕ: AND-depth(C) = максимальная длина пути из AND/OR-гейтов
от входа до выхода, где каждый шаг проходит через AND или OR
(НЕ считая NOT как шаг "глубины").

ГИПОТЕЗА (Decomposition Conjecture):
  Для схемы C размера s = n^c на n входах:

  СЛУЧАЙ 1: AND-depth(C) ≥ αn (линейная глубина).
    → Pr[выход определён | n/2 consecutive фикс.] ≥ 1 - e^{-Ω(n)}
    → SAT(C) за O(2^{n/2} × poly)

  СЛУЧАЙ 2: AND-depth(C) < αn.
    → C вычисляет функцию с "малой" чувствительностью
    → SAT(C) за poly(s) или O(2^{AND-depth} × poly)

  В обоих случаях: SAT(C) за O(2^{n(1-ε)} × poly).

ВЕРИФИКАЦИЯ: Проверяем корреляцию AND-depth ↔ Pr[det] и
AND-depth ↔ сложность SAT.
"""
import random, math, sys
from itertools import product

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

def measure_det(gates, n, k, trials=2000):
    det = 0
    for _ in range(trials):
        s = random.randint(0, n-1)
        vs = [(s+i)%n for i in range(min(k,n))]
        fixed = {v: random.randint(0,1) for v in vs}
        if propagate(gates, fixed) is not None: det += 1
    return det / trials

def compute_and_depth(gates, n):
    """AND-depth: максимальная длина AND/OR пути от входа до выхода."""
    depth = {i: 0 for i in range(n)}
    for gtype, i1, i2, out in gates:
        d1 = depth.get(i1, 0)
        d2 = depth.get(i2, 0) if i2 >= 0 else 0
        if gtype in ('AND', 'OR'):
            depth[out] = max(d1, d2) + 1
        elif gtype == 'NOT':
            depth[out] = d1  # NOT не увеличивает AND-depth
    if gates:
        return depth.get(gates[-1][3], 0)
    return 0

def compute_sensitivity(gates, n):
    """Средняя чувствительность: сколько входов влияют на выход."""
    if n > 16:
        trials = 1000
        total_sens = 0
        for _ in range(trials):
            x = {i: random.randint(0,1) for i in range(n)}
            base = propagate(gates, x)
            if base is None: continue
            s = 0
            for i in range(n):
                flipped = dict(x); flipped[i] = 1 - flipped[i]
                f = propagate(gates, flipped)
                if f is not None and f != base: s += 1
            total_sens += s
        return total_sens / max(1, trials)
    else:
        total_sens = 0; count = 0
        for bits in range(2**n):
            x = {i: (bits>>i)&1 for i in range(n)}
            base = propagate(gates, x)
            if base is None: continue
            count += 1
            for i in range(n):
                flipped = dict(x); flipped[i] = 1 - flipped[i]
                f = propagate(gates, flipped)
                if f is not None and f != base: total_sens += 1
        return total_sens / max(1, count)

def sat_fraction(gates, n):
    """Доля выполняющих назначений (для малых n)."""
    if n > 20: return None
    sat = 0
    for bits in range(2**n):
        x = {i: (bits>>i)&1 for i in range(n)}
        if propagate(gates, x) == 1: sat += 1
    return sat / 2**n

# ================================================================
# Генераторы разных типов схем
# ================================================================

def build_3sat(n, alpha=4.27):
    gates = []; nid = n; neg = {}
    for i in range(n):
        neg[i] = nid; gates.append(('NOT', i, -1, nid)); nid += 1
    c_outs = []
    for _ in range(int(alpha * n)):
        vs = random.sample(range(n), 3)
        cl = [(v, random.random() > 0.5) for v in vs]
        lits = [v if p else neg[v] for v, p in cl]
        cur = lits[0]
        for l in lits[1:]:
            out = nid; gates.append(('OR', cur, l, out)); nid += 1; cur = out
        c_outs.append(cur)
    cur = c_outs[0]
    for c in c_outs[1:]:
        g = nid; gates.append(('AND', cur, c, g)); nid += 1; cur = g
    return gates, n

def build_xor_chain(n):
    gates = []; nid = n; cur = 0
    for i in range(1, n):
        nc = nid; gates.append(('NOT', cur, -1, nc)); nid += 1
        nb = nid; gates.append(('NOT', i, -1, nb)); nid += 1
        t1 = nid; gates.append(('AND', cur, nb, t1)); nid += 1
        t2 = nid; gates.append(('AND', nc, i, t2)); nid += 1
        xor = nid; gates.append(('OR', t1, t2, xor)); nid += 1
        cur = xor
    return gates, n

def build_tm_rule110(n, steps=None):
    if steps is None: steps = n
    gates = []; nid = n; prev = list(range(n))
    for t in range(steps):
        new = []
        for i in range(n):
            L,C,R = prev[(i-1)%n], prev[i], prev[(i+1)%n]
            ab = nid; gates.append(('AND', L, C, ab)); nid += 1
            bc = nid; gates.append(('AND', C, R, bc)); nid += 1
            nl = nid; gates.append(('NOT', L, -1, nl)); nid += 1
            nac = nid; gates.append(('AND', nl, R, nac)); nid += 1
            t1 = nid; gates.append(('OR', ab, bc, t1)); nid += 1
            r = nid; gates.append(('OR', t1, nac, r)); nid += 1
            new.append(r)
        prev = new
    cur = prev[0]
    for p in prev[1:]:
        gates.append(('OR', cur, p, nid)); cur = nid; nid += 1
    return gates, n

def build_random_dag(n, mult=5):
    gates = []; nid = n
    for _ in range(mult * n):
        gtype = random.choice(['AND', 'OR', 'NOT'])
        if gtype == 'NOT':
            i1 = random.randint(0, nid-1)
            gates.append(('NOT', i1, -1, nid))
        else:
            i1 = random.randint(0, nid-1)
            i2 = random.randint(0, nid-1)
            gates.append((gtype, i1, i2, nid))
        nid += 1
    return gates, n

def build_shallow_wide(n):
    """Мелкая широкая схема: depth O(log n), size O(n)."""
    gates = []; nid = n; prev = list(range(n))
    # Один слой AND, один OR
    and_layer = []
    for i in range(0, n-1, 2):
        g = nid; gates.append(('AND', prev[i], prev[i+1], g)); nid += 1
        and_layer.append(g)
    if n % 2: and_layer.append(prev[-1])
    # OR всех
    cur = and_layer[0]
    for a in and_layer[1:]:
        g = nid; gates.append(('OR', cur, a, g)); nid += 1; cur = g
    return gates, n

def build_deep_and_chain(n):
    """Глубокая AND-цепочка: AND(x0, AND(x1, AND(x2, ...)))."""
    gates = []; nid = n; cur = 0
    for i in range(1, n):
        g = nid; gates.append(('AND', cur, i, g)); nid += 1; cur = g
    return gates, n

def build_deep_or_chain(n):
    """Глубокая OR-цепочка."""
    gates = []; nid = n; cur = 0
    for i in range(1, n):
        g = nid; gates.append(('OR', cur, i, g)); nid += 1; cur = g
    return gates, n

# ================================================================
# ГЛАВНЫЙ ЭКСПЕРИМЕНТ
# ================================================================

def main():
    random.seed(42)
    print("=" * 72)
    print("  ТЕОРЕМА ДЕКОМПОЗИЦИИ: AND-depth vs Pr[det] vs SAT")
    print("=" * 72)

    # Тест 1: Корреляция AND-depth ↔ Pr[det]
    print()
    print("=" * 72)
    print("  ТЕСТ 1: AND-depth ↔ Pr[det] для разных типов схем (n=15)")
    print("=" * 72)
    print()

    n = 15
    circuits = [
        ("AND-chain", build_deep_and_chain),
        ("OR-chain", build_deep_or_chain),
        ("Shallow-wide", build_shallow_wide),
        ("XOR-chain", build_xor_chain),
        ("Random DAG", lambda n: build_random_dag(n, 5)),
        ("3-SAT", build_3sat),
        ("TM rule110", lambda n: build_tm_rule110(n, n)),
    ]

    print(f"  {'тип':<15} {'depth':>6} {'Pr[det]':>8} {'sens':>6} {'sat%':>6}")
    print(f"  {'-'*44}")

    data_points = []
    for name, builder in circuits:
        g, nv = builder(n)
        ad = compute_and_depth(g, nv)
        pr = measure_det(g, nv, nv//2, 2000)
        sens = compute_sensitivity(g, nv)
        sf = sat_fraction(g, nv)
        sf_str = f"{sf:.3f}" if sf is not None else "?"
        print(f"  {name:<15} {ad:6d} {pr:8.4f} {sens:6.2f} {sf_str:>6}")
        data_points.append((name, ad, pr, sens, sf))
        sys.stdout.flush()

    # Тест 2: Систематический тест — случайные схемы разной глубины
    print()
    print("=" * 72)
    print("  ТЕСТ 2: Случайные схемы с контролируемой AND-depth")
    print("=" * 72)
    print()

    n = 15
    print(f"  {'target_depth':>12} {'actual':>7} {'Pr[det]':>8} {'sens':>6}")
    print(f"  {'-'*36}")

    for target_depth in [2, 5, 10, 15, 20, 30, 50]:
        # Строим схему фиксированной глубины
        gates = []; nid = n; prev = list(range(n))
        for d in range(target_depth):
            gtype = 'AND' if d % 2 == 0 else 'OR'
            new = []
            for i in range(len(prev)):
                j = random.randint(0, len(prev)-1)
                g = nid; gates.append((gtype, prev[i], prev[j], g)); nid += 1
                new.append(g)
            # Добавим NOT для разнообразия
            for i in range(min(3, len(new))):
                idx = random.randint(0, len(new)-1)
                g = nid; gates.append(('NOT', new[idx], -1, g)); nid += 1
                new[idx] = g
            prev = new
        # OR финал
        cur = prev[0]
        for p in prev[1:]:
            g = nid; gates.append(('OR', cur, p, g)); nid += 1; cur = g

        ad = compute_and_depth(gates, n)
        pr = measure_det(gates, n, n//2, 2000)
        sens = compute_sensitivity(gates, n)
        print(f"  {target_depth:12d} {ad:7d} {pr:8.4f} {sens:6.2f}")
        sys.stdout.flush()

    # Тест 3: КЛЮЧЕВОЙ — SAT-сложность vs AND-depth
    print()
    print("=" * 72)
    print("  ТЕСТ 3: Когда AND-depth мал — SAT проще?")
    print("  Измеряем: размер DFS-дерева для решения SAT")
    print("=" * 72)
    print()

    def sat_dfs_nodes(gates, n, max_nodes=100000):
        """Число узлов DFS для решения SAT (brute force с обрезкой)."""
        nodes = [0]
        def dfs(depth, fixed):
            nodes[0] += 1
            if nodes[0] > max_nodes: return None
            out = propagate(gates, fixed)
            if out is not None:
                return out == 1  # determined
            if depth >= n:
                return False
            # Try both values
            fixed[depth] = 0
            r0 = dfs(depth + 1, fixed)
            if r0 is True: return True
            fixed[depth] = 1
            r1 = dfs(depth + 1, fixed)
            del fixed[depth]
            return r0 or r1
        dfs(0, {})
        return nodes[0]

    n = 14  # маленький для полного DFS
    print(f"  n={n}")
    print(f"  {'тип':<15} {'depth':>6} {'DFS nodes':>10} {'2^n':>8} {'speedup':>8}")
    print(f"  {'-'*50}")

    two_n = 2 ** n
    for name, builder in circuits:
        g, nv = builder(n)
        ad = compute_and_depth(g, nv)
        nodes = sat_dfs_nodes(g, nv)
        if nodes is not None:
            speedup = two_n / max(1, nodes)
            print(f"  {name:<15} {ad:6d} {nodes:10d} {two_n:8d} {speedup:8.1f}x")
        else:
            print(f"  {name:<15} {ad:6d} {'>100k':>10} {two_n:8d} {'<1':>8}")
        sys.stdout.flush()

    # Тест 4: Масштабирование speedup vs n
    print()
    print("=" * 72)
    print("  ТЕСТ 4: Speedup vs n для разных типов")
    print("=" * 72)
    print()

    print(f"  {'n':>4} {'3SAT sp':>8} {'XOR sp':>8} {'TM sp':>8} {'AND sp':>8} {'DAG sp':>8}")
    print(f"  {'-'*44}")

    for n in [8, 10, 12, 14, 16]:
        row = f"  {n:4d}"
        two_n = 2**n
        for builder in [build_3sat, build_xor_chain,
                        lambda n: build_tm_rule110(n, min(n,8)),
                        build_deep_and_chain,
                        lambda n: build_random_dag(n, 3)]:
            g, nv = builder(n)
            nodes = sat_dfs_nodes(g, nv, 500000)
            if nodes is not None and nodes > 0:
                sp = two_n / nodes
                row += f" {sp:8.1f}x"
            else:
                row += f" {'?':>8}"
        print(row)
        sys.stdout.flush()

    # Тест 5: Гипотеза — SAT-speedup ≥ 2^{εn} для ВСЕХ типов?
    print()
    print("=" * 72)
    print("  ТЕСТ 5: log2(speedup) / n для каждого типа")
    print("  Если > 0 для всех → SAT за O(2^{n(1-ε)})")
    print("=" * 72)
    print()

    print(f"  {'тип':<15} {'n=10':>7} {'n=12':>7} {'n=14':>7} {'n=16':>7}")
    print(f"  {'-'*42}")

    type_builders = [
        ("3-SAT", build_3sat),
        ("XOR-chain", build_xor_chain),
        ("TM rule110", lambda n: build_tm_rule110(n, min(n,8))),
        ("AND-chain", build_deep_and_chain),
        ("OR-chain", build_deep_or_chain),
        ("Random DAG", lambda n: build_random_dag(n, 3)),
        ("Shallow", build_shallow_wide),
    ]

    for name, builder in type_builders:
        row = f"  {name:<15}"
        for n in [10, 12, 14, 16]:
            g, nv = builder(n)
            nodes = sat_dfs_nodes(g, nv, 500000)
            if nodes is not None and nodes > 0:
                sp = (2**n) / nodes
                eps = math.log2(max(1.01, sp)) / n
                row += f" {eps:7.4f}"
            else:
                row += f" {'?':>7}"
        print(row)
        sys.stdout.flush()

    # ИТОГ
    print()
    print("=" * 72)
    print("  ИТОГ: ТЕОРЕМА ДЕКОМПОЗИЦИИ")
    print("=" * 72)
    print("""
  Для ЛЮБОЙ схемы C размера s на n входах:

  СЛУЧАЙ 1: AND-depth ≥ Ω(n)
    → Длинная AND/OR цепочка → determination → SAT за 2^{n/2}

  СЛУЧАЙ 2: AND-depth < o(n)
    → DFS с constant propagation даёт speedup > ???

  КЛЮЧЕВОЙ ВОПРОС: speedup > 2^{εn} для ВСЕХ схем?
    """)

if __name__ == "__main__":
    main()
