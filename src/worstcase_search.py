"""
Целенаправленный поиск worst-case схем и масштабирование до n=30.
Если найдём схему с ε → 0 — это контрпример.
Если не найдём — усиливает гипотезу.
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
    nodes = [0]; found = [False]
    def dfs(d, fixed):
        nodes[0] += 1
        if nodes[0] > max_nodes: return
        out = propagate(gates, fixed)
        if out is not None:
            if out == 1: found[0] = True
            return
        if d >= n: return
        fixed[d] = 0
        dfs(d+1, fixed)
        if found[0]: return
        fixed[d] = 1
        dfs(d+1, fixed)
        if found[0]: return
        del fixed[d]
    dfs(0, {})
    return nodes[0] if nodes[0] <= max_nodes else None

# ================================================================
# Worst-case кандидаты
# ================================================================

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

def build_tseitin(n):
    """Tseitin на цикле — UNSAT, hard для resolution."""
    gates=[]; nid=n; neg={}
    for i in range(n): neg[i]=nid; gates.append(('NOT',i,-1,nid)); nid+=1
    c_outs=[]
    for v in range(n):
        a,b = v, (v+1)%n
        t1=nid; gates.append(('AND',a,neg[b],t1)); nid+=1
        t2=nid; gates.append(('AND',neg[a],b,t2)); nid+=1
        xor=nid; gates.append(('OR',t1,t2,xor)); nid+=1
        c_outs.append(xor)
    cur=c_outs[0]
    for c in c_outs[1:]: g=nid; gates.append(('AND',cur,c,g)); nid+=1; cur=g
    return gates, n

def build_php(p, h):
    """Pigeonhole: p pigeons, h holes. UNSAT when p > h."""
    nv = p*h; gates=[]; nid=nv; neg={}
    for i in range(nv): neg[i]=nid; gates.append(('NOT',i,-1,nid)); nid+=1
    def var(i,j): return i*h+j
    c_outs=[]
    for i in range(p):
        lits=[var(i,j) for j in range(h)]
        cur=lits[0]
        for l in lits[1:]: out=nid; gates.append(('OR',cur,l,out)); nid+=1; cur=out
        c_outs.append(cur)
    from itertools import combinations
    for j in range(h):
        for i1,i2 in combinations(range(p),2):
            out=nid; gates.append(('OR',neg[var(i1,j)],neg[var(i2,j)],out)); nid+=1
            c_outs.append(out)
    cur=c_outs[0]
    for c in c_outs[1:]: g=nid; gates.append(('AND',cur,c,g)); nid+=1; cur=g
    return gates, nv

def build_balanced_xor_and(n):
    """Сбалансированная: XOR-дерево + AND-дерево → OR.
    XOR-часть сложна для propagation, AND-часть тоже."""
    gates=[]; nid=n
    # XOR-дерево первой половины
    half = n//2
    layer = list(range(half))
    while len(layer) > 1:
        new = []
        for i in range(0, len(layer)-1, 2):
            a,b = layer[i], layer[i+1]
            na=nid; gates.append(('NOT',a,-1,na)); nid+=1
            nb=nid; gates.append(('NOT',b,-1,nb)); nid+=1
            t1=nid; gates.append(('AND',a,nb,t1)); nid+=1
            t2=nid; gates.append(('AND',na,b,t2)); nid+=1
            xor=nid; gates.append(('OR',t1,t2,xor)); nid+=1
            new.append(xor)
        if len(layer)%2: new.append(layer[-1])
        layer = new
    xor_out = layer[0]
    # AND-дерево второй половины
    layer = list(range(half, n))
    while len(layer) > 1:
        new = []
        for i in range(0, len(layer)-1, 2):
            g=nid; gates.append(('AND',layer[i],layer[i+1],g)); nid+=1
            new.append(g)
        if len(layer)%2: new.append(layer[-1])
        layer = new
    and_out = layer[0]
    # OR
    g=nid; gates.append(('OR', xor_out, and_out, g)); nid+=1
    return gates, n

def build_nested_xor_sat(n):
    """XOR внутри SAT-клозов: OR(XOR(x0,x1), XOR(x2,x3), XOR(x4,x5))
    AND-цепочка клозов. Каждый клоз = XOR pair."""
    gates=[]; nid=n
    def make_xor(a, b):
        nonlocal nid
        na=nid; gates.append(('NOT',a,-1,na)); nid+=1
        nb=nid; gates.append(('NOT',b,-1,nb)); nid+=1
        t1=nid; gates.append(('AND',a,nb,t1)); nid+=1
        t2=nid; gates.append(('AND',na,b,t2)); nid+=1
        xor=nid; gates.append(('OR',t1,t2,xor)); nid+=1
        return xor

    c_outs = []
    for i in range(0, n-2, 3):
        # Клоз: OR(XOR(xi,xi+1), xi+2) — смесь XOR и plain
        if i+2 < n:
            xor = make_xor(i, i+1)
            cl = nid; gates.append(('OR', xor, i+2, cl)); nid+=1
            c_outs.append(cl)
        elif i+1 < n:
            xor = make_xor(i, i+1)
            c_outs.append(xor)

    if not c_outs: return gates, n
    cur = c_outs[0]
    for c in c_outs[1:]:
        g=nid; gates.append(('AND',cur,c,g)); nid+=1; cur=g
    return gates, n

def build_expander_circuit(n):
    """Схема на основе expander-графа: каждый гейт берёт
    входы из 'далёких' позиций. Максимальное перемешивание."""
    gates=[]; nid=n; prev=list(range(n))
    for layer in range(int(math.log2(n))+2):
        new = []
        gtype = 'AND' if layer%2==0 else 'OR'
        shift = max(1, n//(2**(layer+1)))
        for i in range(n):
            j = (i + shift) % n
            g=nid; gates.append((gtype, prev[i], prev[j], g)); nid+=1
            new.append(g)
        # NOT на нечётных
        for i in range(0, n, 3):
            ng = nid; gates.append(('NOT', new[i], -1, ng)); nid+=1
            new[i] = ng
        prev = new
    cur = prev[0]
    for p in prev[1:]:
        g=nid; gates.append(('OR',cur,p,g)); nid+=1; cur=g
    return gates, n

def main():
    random.seed(42)
    print("=" * 72)
    print("  WORST-CASE ПОИСК + МАСШТАБИРОВАНИЕ до n=30")
    print("=" * 72)

    # Расширенный набор типов
    types = [
        ("3-SAT α=4.27", lambda n: build_3sat(n, 4.27)),
        ("3-SAT α=5.0", lambda n: build_3sat(n, 5.0)),
        ("3-SAT α=6.0", lambda n: build_3sat(n, 6.0)),
        ("Tseitin", build_tseitin),
        ("Balanced XOR+AND", build_balanced_xor_and),
        ("Nested XOR-SAT", build_nested_xor_sat),
        ("Expander", build_expander_circuit),
    ]

    # Тест 1: Все типы, n=10..22
    print()
    print("=" * 72)
    print("  ТЕСТ 1: ε для worst-case кандидатов")
    print("=" * 72)
    print()

    ns = [10, 12, 14, 16, 18, 20, 22]
    header = f"  {'n':>4}"
    snames = ["3S4.3","3S5.0","3S6.0","Tseit","BalXA","NstXS","Expnd"]
    for s in snames: header += f" {s:>7}"
    print(header)
    print(f"  {'-'*4+'-'*8*len(snames)}")

    for n in ns:
        row = f"  {n:4d}"
        for name, builder in types:
            g, nv = builder(n)
            nodes = sat_dfs(g, nv, 5000000)
            if nodes and nodes > 0:
                eps = math.log2(max(1.01, (2**n)/nodes)) / n
                row += f" {eps:7.4f}"
            else:
                row += f" {'?':>7}"
        print(row)
        sys.stdout.flush()

    # Тест 2: PHP — знаменитый hard case
    print()
    print("  PHP (Pigeonhole):")
    print(f"  {'p→h':>6} {'n_vars':>7} {'nodes':>10} {'2^n':>12} {'ε':>7}")
    print(f"  {'-'*46}")
    for h in [3, 4, 5, 6, 7]:
        p = h + 1
        g, nv = build_php(p, h)
        nodes = sat_dfs(g, nv, 5000000)
        two_n = 2**nv
        if nodes and nodes > 0:
            eps = math.log2(max(1.01, two_n/nodes)) / nv
            print(f"  {p}→{h}   {nv:7d} {nodes:10d} {two_n:12d} {eps:7.4f}")
        else:
            print(f"  {p}→{h}   {nv:7d} {'timeout':>10} {two_n:12d} {'?':>7}")
        sys.stdout.flush()

    # Тест 3: Масштабирование worst-case до n=28
    print()
    print("=" * 72)
    print("  ТЕСТ 3: Масштабирование 3-SAT (worst) до n=28")
    print("=" * 72)
    print()

    print(f"  {'n':>4} {'α=4.27':>10} {'α=5.0':>10} {'α=6.0':>10}")
    print(f"  {'-'*36}")
    for n in [10, 12, 14, 16, 18, 20, 22, 24, 26, 28]:
        row = f"  {n:4d}"
        for alpha in [4.27, 5.0, 6.0]:
            g, nv = build_3sat(n, alpha)
            nodes = sat_dfs(g, nv, 5000000)
            if nodes and nodes > 0:
                eps = math.log2(max(1.01, (2**n)/nodes)) / n
                row += f" {eps:10.4f}"
            else:
                row += f" {'timeout':>10}"
        print(row)
        sys.stdout.flush()

    # Тест 4: Много случайных 3-SAT для статистики
    print()
    print("=" * 72)
    print("  ТЕСТ 4: 20 случайных 3-SAT инстансов, n=18")
    print("=" * 72)
    print()

    n = 18
    epsilons = []
    for trial in range(20):
        g, nv = build_3sat(n, 4.27)
        nodes = sat_dfs(g, nv, 5000000)
        if nodes and nodes > 0:
            eps = math.log2(max(1.01, (2**n)/nodes)) / n
            epsilons.append(eps)
            print(f"  trial {trial:2d}: nodes={nodes:8d}, ε={eps:.4f}")
        else:
            print(f"  trial {trial:2d}: timeout")
        sys.stdout.flush()

    if epsilons:
        print(f"\n  min ε = {min(epsilons):.4f}")
        print(f"  max ε = {max(epsilons):.4f}")
        print(f"  mean ε = {sum(epsilons)/len(epsilons):.4f}")
        print(f"  median ε = {sorted(epsilons)[len(epsilons)//2]:.4f}")

    # Тест 5: min ε по ВСЕМ типам для каждого n
    print()
    print("=" * 72)
    print("  ТЕСТ 5: АБСОЛЮТНЫЙ min ε")
    print("=" * 72)
    print()

    all_types = types + [
        ("PHP", lambda n: build_php(int(n**0.5)+1, int(n**0.5)) if n >= 9 else ([], n)),
    ]

    print(f"  {'n':>4} {'min ε':>8} {'worst':>20}")
    print(f"  {'-'*36}")
    for n in [10, 12, 14, 16, 18, 20, 22]:
        min_e = float('inf'); worst = ""
        for name, builder in all_types:
            try:
                g, nv = builder(n)
                if not g: continue
                nodes = sat_dfs(g, nv, 5000000)
                if nodes and nodes > 0:
                    eps = math.log2(max(1.01, (2**nv)/nodes)) / nv
                    if eps < min_e: min_e = eps; worst = name
                else:
                    min_e = 0; worst = name+" (timeout)"; break
            except: pass
        print(f"  {n:4d} {min_e:8.4f} {worst:>20}")
        sys.stdout.flush()

    print()
    print("=" * 72)
    print("  ИТОГ")
    print("=" * 72)

if __name__ == "__main__":
    main()
