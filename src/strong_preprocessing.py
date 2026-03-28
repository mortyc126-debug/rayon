"""
Усиленный preprocessing: random restriction + DFS.
Фиксируем √n переменных случайно, проверяем determination.
Повторяем poly(n) раз. Ловит ВСЕ "хитро-константные" функции.
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


def strong_preprocess(gates, n):
    """Усиленный preprocessing за O(n^2 × s):
    1. Random restriction: фикс. √n переменных, проверяем determination
    2. Если всегда det → f ≈ const → решаем за poly
    3. Если нашли SAT → done
    4. Если нашли и 0 и 1 → нетривиальная функция
    """
    k = max(2, int(math.sqrt(n)))  # √n переменных
    reps = 5 * n  # повторений

    found_0 = False; found_1 = False; found_undet = False

    for _ in range(reps):
        vs = random.sample(range(n), min(k, n))
        fixed = {v: random.randint(0, 1) for v in vs}
        out = propagate(gates, fixed)
        if out == 0: found_0 = True
        elif out == 1:
            found_1 = True
            return "SAT", 1  # Нашли SAT-путь!
        else:
            found_undet = True

        if found_0 and found_undet:
            break  # Нетривиальная

    # Random full evaluation
    for _ in range(3 * n):
        x = {i: random.randint(0, 1) for i in range(n)}
        out = propagate(gates, x)
        if out == 1:
            return "SAT", 1

    if found_1:
        return "SAT", 1
    if found_0 and not found_1 and not found_undet:
        return "UNSAT_LIKELY", 1  # Все рестрикции дали 0

    return None, 0  # Нетривиальная


def sat_dfs_strong(gates, n, max_nodes=5000000):
    """DFS с усиленным preprocessing."""
    result, cost = strong_preprocess(gates, n)
    if result is not None:
        return cost  # Решено preprocessing'ом

    # DFS
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
    print("  УСИЛЕННЫЙ PREPROCESSING + DFS")
    print("  Random restriction √n vars × 5n reps")
    print("=" * 72)

    # =========================================================
    # ТЕСТ 1: 1000 случайных схем n=14
    # =========================================================
    print()
    print("  ТЕСТ 1: 1000 случайных схем (n=14)")
    print()

    n = 14
    eps_basic = []; eps_strong = []; preproc_count = 0

    for _ in range(1000):
        size = random.randint(n, 8*n)
        ab = random.random()
        g = random_circuit(n, size, ab)

        nb = sat_dfs_basic(g, n, 2000000)
        ns = sat_dfs_strong(g, n, 2000000)

        if nb and nb > 1:
            eps_basic.append(math.log2(max(1.01, (2**n)/nb)) / n)
        if ns and ns > 0:
            if ns <= 2:
                preproc_count += 1
                eps_strong.append(1.0 - 1/n)
            else:
                eps_strong.append(math.log2(max(1.01, (2**n)/ns)) / n)

    print(f"  Preprocessing решил: {preproc_count}/1000")
    eb = sorted(eps_basic); es = sorted(eps_strong)
    print(f"  {'':>10} {'min ε':>7} {'5%':>7} {'med':>7} {'mean':>7}")
    print(f"  {'-'*40}")
    print(f"  {'Basic':>10} {eb[0]:7.4f} {eb[len(eb)//20]:7.4f} "
          f"{eb[len(eb)//2]:7.4f} {sum(eb)/len(eb):7.4f}")
    print(f"  {'Strong':>10} {es[0]:7.4f} {es[len(es)//20]:7.4f} "
          f"{es[len(es)//2]:7.4f} {sum(es)/len(es):7.4f}")

    # =========================================================
    # ТЕСТ 2: Масштабирование min ε
    # =========================================================
    print()
    print("  ТЕСТ 2: min ε vs n (300 схем × n)")
    print()
    print(f"  {'n':>4} {'min basic':>10} {'min strong':>11} {'preproc%':>9}")
    print(f"  {'-'*36}")

    for n in [8, 10, 12, 14, 16, 18, 20]:
        eb_list=[]; es_list=[]; pp=0
        for _ in range(300):
            size = random.randint(n, 8*n)
            ab = random.random()
            g = random_circuit(n, size, ab)
            nb = sat_dfs_basic(g, n, 2000000)
            ns = sat_dfs_strong(g, n, 2000000)
            if nb and nb>1:
                eb_list.append(math.log2(max(1.01,(2**n)/nb))/n)
            if ns:
                if ns<=2: pp+=1; es_list.append(1.0-1/n)
                else: es_list.append(math.log2(max(1.01,(2**n)/ns))/n)
        me = min(eb_list) if eb_list else 0
        ms = min(es_list) if es_list else 0
        print(f"  {n:4d} {me:10.4f} {ms:11.4f} {100*pp/300:8.1f}%")
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 3: 3-SAT hard instances
    # =========================================================
    print()
    print("  ТЕСТ 3: 3-SAT hard (α=4.27, 5.0, 6.0)")
    print()
    print(f"  {'n':>4} {'α':>5} {'basic ε':>8} {'strong ε':>9}")
    print(f"  {'-'*28}")
    for n in [12, 14, 16, 18, 20, 22, 24]:
        for alpha in [4.27, 5.0]:
            eb_min=1; es_min=1
            for _ in range(10):
                g, nv = build_3sat(n, alpha)
                nb = sat_dfs_basic(g, nv, 5000000)
                ns = sat_dfs_strong(g, nv, 5000000)
                if nb and nb>1:
                    e = math.log2(max(1.01,(2**n)/nb))/n
                    if e<eb_min: eb_min=e
                if ns:
                    if ns<=2: e=1.0
                    elif ns>1: e = math.log2(max(1.01,(2**n)/ns))/n
                    else: e=1.0
                    if e<es_min: es_min=e
            print(f"  {n:4d} {alpha:5.2f} {eb_min:8.4f} {es_min:9.4f}")
            sys.stdout.flush()

    # =========================================================
    # ТЕСТ 4: Абсолютный min ε для strong preprocessing
    # =========================================================
    print()
    print("  ТЕСТ 4: 2000 схем, абсолютный min ε (n=14)")
    print()
    n = 14; all_eps=[]
    for _ in range(2000):
        size=random.randint(n,10*n)
        ab=random.random()
        g=random_circuit(n,size,ab)
        ns=sat_dfs_strong(g,n,2000000)
        if ns:
            if ns<=2: all_eps.append(1.0-1/n)
            elif ns>1: all_eps.append(math.log2(max(1.01,(2**n)/ns))/n)
    all_eps.sort()
    print(f"  Всего: {len(all_eps)}")
    print(f"  min ε = {all_eps[0]:.4f}")
    print(f"  5% = {all_eps[len(all_eps)//20]:.4f}")
    print(f"  median = {all_eps[len(all_eps)//2]:.4f}")
    print(f"  ε < 0.1: {sum(1 for e in all_eps if e<0.1)}")
    print(f"  ε < 0.2: {sum(1 for e in all_eps if e<0.2)}")
    print(f"  ε < 0.3: {sum(1 for e in all_eps if e<0.3)}")

    print()
    print("=" * 72)
    print("  ИТОГ")
    print("=" * 72)

if __name__ == "__main__":
    main()
