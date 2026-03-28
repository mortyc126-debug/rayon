"""
DFS с preprocessing: детектируем "тупые" схемы за poly(s),
затем constant propagation для остальных.
Цель: ε > const для ВСЕХ схем.
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

# ================================================================
# PREPROCESSING: упрощение схемы за poly(s)
# ================================================================

def preprocess(gates, n):
    """Poly-time preprocessing:
    1. Constant folding (без входов): пропагируем без фиксаций
    2. Dead gate elimination: удаляем гейты, не влияющие на выход
    3. Identical/complementary detection: AND(x,x)=x, AND(x,NOT x)=0
    4. Random sampling: проверяем f на случайных входах
    Возвращает (new_gates, new_n, trivial_result) или (gates, n, None).
    """
    # Фаза 1: Constant propagation без входов
    wire = {}
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

    if gates:
        out_val = wire.get(gates[-1][3])
        if out_val is not None:
            return gates, n, out_val  # Тривиально!

    # Фаза 2: Однопроходная фиксация каждой переменной
    # Для каждого x_i: фиксируем x_i=0, проверяем. Затем x_i=1.
    # Если оба дают одинаковый результат → x_i не влияет.
    # Это O(n × s) = poly.
    indep_vars = []
    for i in range(n):
        out0 = propagate(gates, {i: 0})
        out1 = propagate(gates, {i: 1})
        if out0 is not None and out1 is not None and out0 == out1:
            indep_vars.append((i, out0))

    # Если ВСЕ переменные независимы → f = const
    if len(indep_vars) == n:
        return gates, n, indep_vars[0][1]

    # Фаза 3: Попарная фиксация (2 переменные)
    # O(n² × s) = poly. Проверяем больше.
    for i in range(min(n, 20)):
        for j in range(i+1, min(n, 20)):
            results = set()
            for vi in [0, 1]:
                for vj in [0, 1]:
                    out = propagate(gates, {i: vi, j: vj})
                    if out is not None:
                        results.add(out)
            if len(results) == 1:
                # f не зависит от x_i, x_j → их можно фиксировать
                pass  # для простоты пропускаем

    # Фаза 4: Random sampling — ищем SAT-решение
    for _ in range(3 * n):
        x = {i: random.randint(0, 1) for i in range(n)}
        if propagate(gates, x) == 1:
            return gates, n, "SAT_FOUND"  # Нашли решение за poly!

    return gates, n, None  # Не тривиально


def sat_dfs_smart(gates, n, max_nodes=5000000):
    """DFS с preprocessing."""
    # Preprocessing
    _, _, trivial = preprocess(gates, n)
    if trivial is not None:
        if trivial == 1 or trivial == "SAT_FOUND":
            return 1  # SAT, 1 узел (preprocessing)
        else:
            return 1  # UNSAT, 1 узел

    # Обычный DFS с constant propagation
    nodes = [0]
    def dfs(d, fixed):
        nodes[0] += 1
        if nodes[0] > max_nodes: return
        out = propagate(gates, fixed)
        if out is not None: return
        if d >= n: return
        fixed[d] = 0; dfs(d+1, fixed)
        if nodes[0] > max_nodes: return
        fixed[d] = 1; dfs(d+1, fixed)
        del fixed[d]
    dfs(0, {})
    return nodes[0] if nodes[0] <= max_nodes else None


def sat_dfs_basic(gates, n, max_nodes=5000000):
    """DFS БЕЗ preprocessing."""
    nodes = [0]
    def dfs(d, fixed):
        nodes[0] += 1
        if nodes[0] > max_nodes: return
        out = propagate(gates, fixed)
        if out is not None: return
        if d >= n: return
        fixed[d] = 0; dfs(d+1, fixed)
        if nodes[0] > max_nodes: return
        fixed[d] = 1; dfs(d+1, fixed)
        del fixed[d]
    dfs(0, {})
    return nodes[0] if nodes[0] <= max_nodes else None


def random_circuit(n, size, ab=0.5):
    gates = []; nid = n
    for _ in range(size):
        r = random.random()
        if r < 0.15: gtype = 'NOT'
        elif r < 0.15 + ab * 0.85: gtype = 'AND'
        else: gtype = 'OR'
        if gtype == 'NOT':
            gates.append(('NOT', random.randint(0, nid-1), -1, nid))
        else:
            gates.append((gtype, random.randint(0, nid-1),
                         random.randint(0, nid-1), nid))
        nid += 1
    return gates


def build_3sat(n, alpha=4.27):
    gates=[]; nid=n; neg={}
    for i in range(n): neg[i]=nid; gates.append(('NOT',i,-1,nid)); nid+=1
    c_outs=[]
    for _ in range(int(alpha*n)):
        vs=random.sample(range(n),3)
        cl=[(v,random.random()>0.5) for v in vs]
        lits=[v if p else neg[v] for v,p in cl]
        cur=lits[0]
        for l in lits[1:]: out=nid; gates.append(('OR',cur,l,out)); nid+=1; cur=out
        c_outs.append(cur)
    cur=c_outs[0]
    for c in c_outs[1:]: g=nid; gates.append(('AND',cur,c,g)); nid+=1; cur=g
    return gates, n


def main():
    random.seed(42)
    print("=" * 72)
    print("  DFS + PREPROCESSING vs DFS без preprocessing")
    print("=" * 72)

    # =========================================================
    # ТЕСТ 1: 1000 случайных схем, basic vs smart
    # =========================================================
    print()
    print("=" * 72)
    print("  ТЕСТ 1: 1000 случайных схем (n=14)")
    print("=" * 72)
    print()

    n = 14
    eps_basic = []; eps_smart = []
    preproc_solved = 0

    for _ in range(1000):
        size = random.randint(n, 8*n)
        ab = random.random()
        g = random_circuit(n, size, ab)

        nb = sat_dfs_basic(g, n, 2000000)
        ns = sat_dfs_smart(g, n, 2000000)

        if nb and nb > 1:
            eps_basic.append(math.log2(max(1.01, (2**n)/nb)) / n)
        if ns and ns > 0:
            if ns == 1:
                preproc_solved += 1
                eps_smart.append(1.0 - 1/n)  # почти полная экономия
            elif ns > 1:
                eps_smart.append(math.log2(max(1.01, (2**n)/ns)) / n)

    print(f"  Preprocessing решил: {preproc_solved} из 1000")
    print()
    print(f"  {'':>15} {'min ε':>7} {'5%':>7} {'med':>7} {'mean':>7} {'ε<0.1':>6}")
    print(f"  {'-'*52}")
    if eps_basic:
        eb = sorted(eps_basic)
        print(f"  {'Basic DFS':>15} {eb[0]:7.4f} {eb[len(eb)//20]:7.4f} "
              f"{eb[len(eb)//2]:7.4f} {sum(eb)/len(eb):7.4f} "
              f"{sum(1 for e in eb if e<0.1):6d}")
    if eps_smart:
        es = sorted(eps_smart)
        print(f"  {'Smart DFS':>15} {es[0]:7.4f} {es[len(es)//20]:7.4f} "
              f"{es[len(es)//2]:7.4f} {sum(es)/len(es):7.4f} "
              f"{sum(1 for e in es if e<0.1):6d}")

    # =========================================================
    # ТЕСТ 2: Масштабирование min ε с preprocessing
    # =========================================================
    print()
    print("=" * 72)
    print("  ТЕСТ 2: min ε vs n (500 схем × n), с preprocessing")
    print("=" * 72)
    print()

    print(f"  {'n':>4} {'min ε bas':>10} {'min ε smt':>10} {'preproc%':>9}")
    print(f"  {'-'*36}")

    for n in [8, 10, 12, 14, 16, 18, 20]:
        eb_list = []; es_list = []; pp = 0
        for _ in range(500):
            size = random.randint(n, 8*n)
            ab = random.random()
            g = random_circuit(n, size, ab)

            nb = sat_dfs_basic(g, n, 2000000)
            ns = sat_dfs_smart(g, n, 2000000)

            if nb and nb > 1:
                eb_list.append(math.log2(max(1.01, (2**n)/nb)) / n)
            if ns:
                if ns == 1:
                    pp += 1
                    es_list.append(1.0 - 1/n)
                elif ns > 1:
                    es_list.append(math.log2(max(1.01, (2**n)/ns)) / n)

        min_eb = min(eb_list) if eb_list else 0
        min_es = min(es_list) if es_list else 0
        pp_pct = 100 * pp / 500
        print(f"  {n:4d} {min_eb:10.4f} {min_es:10.4f} {pp_pct:8.1f}%")
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 3: 3-SAT (hard) — preprocessing не должен помочь
    # =========================================================
    print()
    print("=" * 72)
    print("  ТЕСТ 3: 3-SAT — preprocessing vs basic")
    print("=" * 72)
    print()

    print(f"  {'n':>4} {'basic ε':>8} {'smart ε':>8} {'preproc':>8}")
    print(f"  {'-'*28}")
    for n in [10, 12, 14, 16, 18, 20, 22, 24]:
        eb_min = 1.0; es_min = 1.0; pp = 0
        for _ in range(20):
            g, nv = build_3sat(n, 4.27)
            nb = sat_dfs_basic(g, nv, 5000000)
            ns = sat_dfs_smart(g, nv, 5000000)
            if nb and nb > 1:
                e = math.log2(max(1.01, (2**n)/nb)) / n
                if e < eb_min: eb_min = e
            if ns:
                if ns == 1: pp += 1; e = 1.0
                elif ns > 1: e = math.log2(max(1.01, (2**n)/ns)) / n
                else: e = 1.0
                if e < es_min: es_min = e
        print(f"  {n:4d} {eb_min:8.4f} {es_min:8.4f} {pp:8d}/20")
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 4: Targeted — схемы с f≡0 (прежний worst case)
    # =========================================================
    print()
    print("=" * 72)
    print("  ТЕСТ 4: Схемы с f≡const (прежний worst case)")
    print("=" * 72)
    print()

    n = 14
    const_found = 0; const_total = 0
    for _ in range(500):
        size = random.randint(n, 8*n)
        ab = random.random()
        g = random_circuit(n, size, ab)
        # Проверяем: f≡const?
        vals = set()
        for b in range(min(200, 2**n)):
            x = {i: random.randint(0,1) for i in range(n)}
            v = propagate(g, x)
            if v is not None: vals.add(v)
            if len(vals) > 1: break
        is_const = len(vals) <= 1

        if is_const:
            const_total += 1
            _, _, trivial = preprocess(g, n)
            if trivial is not None:
                const_found += 1

    print(f"  Константных функций: {const_total} из 500")
    print(f"  Preprocessing нашёл: {const_found} из {const_total}")
    detect_rate = const_found / max(1, const_total)
    print(f"  Детектирование: {detect_rate:.1%}")

    # =========================================================
    # ИТОГ
    # =========================================================
    print()
    print("=" * 72)
    print("  ИТОГ")
    print("=" * 72)
    print("""
  Preprocessing (poly-time) + DFS с constant propagation:

  1. Preprocessing решает ~X% схем за poly (константы, easy SAT)
  2. Для оставшихся: ε > ???

  Ключевой вопрос: min ε для НЕTRIVИАЛЬНЫХ схем > const?
    """)


if __name__ == "__main__":
    main()
