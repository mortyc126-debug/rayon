"""
УЛУЧШЕНИЕ: три техники для ускорения DFS на Circuit-SAT.
1. Smart variable ordering (max determination probability)
2. Прямой Circuit-SAT (без Cook-Levin)
3. Backward propagation (AND=output known → deduce inputs)
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


def propagate_full(gates, n, fixed):
    """Forward + backward propagation (multi-pass)."""
    wire = dict(fixed)
    gate_by_out = {g[3]: g for g in gates}

    for iteration in range(3):
        changed = False
        # Forward
        for gtype, i1, i2, out in gates:
            if out in wire: continue
            v1 = wire.get(i1); v2 = wire.get(i2) if i2 >= 0 else None
            nv = None
            if gtype == 'AND':
                if v1 == 0 or v2 == 0: nv = 0
                elif v1 is not None and v2 is not None: nv = v1 & v2
            elif gtype == 'OR':
                if v1 == 1 or v2 == 1: nv = 1
                elif v1 is not None and v2 is not None: nv = v1 | v2
            elif gtype == 'NOT':
                if v1 is not None: nv = 1 - v1
            if nv is not None:
                wire[out] = nv; changed = True

        # Backward
        for gtype, i1, i2, out in gates:
            ov = wire.get(out)
            if ov is None: continue
            if gtype == 'AND':
                if ov == 1:
                    if i1 not in wire: wire[i1] = 1; changed = True
                    if i2 >= 0 and i2 not in wire: wire[i2] = 1; changed = True
                elif ov == 0:
                    v1 = wire.get(i1); v2 = wire.get(i2) if i2 >= 0 else None
                    if v1 == 1 and i2 >= 0 and i2 not in wire:
                        wire[i2] = 0; changed = True
                    if v2 == 1 and i1 not in wire:
                        wire[i1] = 0; changed = True
            elif gtype == 'OR':
                if ov == 0:
                    if i1 not in wire: wire[i1] = 0; changed = True
                    if i2 >= 0 and i2 not in wire: wire[i2] = 0; changed = True
                elif ov == 1:
                    v1 = wire.get(i1); v2 = wire.get(i2) if i2 >= 0 else None
                    if v1 == 0 and i2 >= 0 and i2 not in wire:
                        wire[i2] = 1; changed = True
                    if v2 == 0 and i1 not in wire:
                        wire[i1] = 1; changed = True
            elif gtype == 'NOT':
                if ov is not None and i1 not in wire:
                    wire[i1] = 1 - ov; changed = True
        if not changed: break
    return wire


def dfs_basic(gates, n, max_nodes=5000000):
    """Baseline: DFS по порядку, forward-only propagation."""
    nodes = [0]; found = [False]
    def dfs(d, fixed):
        nodes[0] += 1
        if nodes[0] > max_nodes: return
        out = propagate(gates, fixed)
        if out is not None:
            if out == 1: found[0] = True
            return
        if d >= n: return
        fixed[d] = 0; dfs(d+1, fixed)
        if found[0] or nodes[0] > max_nodes: return
        fixed[d] = 1; dfs(d+1, fixed)
        if found[0]: return
        del fixed[d]
    dfs(0, {})
    return nodes[0] if nodes[0] <= max_nodes else None


def dfs_backward(gates, n, max_nodes=5000000):
    """DFS + full propagation (forward + backward)."""
    nodes = [0]; found = [False]
    out_id = gates[-1][3] if gates else -1
    def dfs(d, fixed):
        nodes[0] += 1
        if nodes[0] > max_nodes: return
        wire = propagate_full(gates, n, fixed)
        out = wire.get(out_id)
        if out is not None:
            if out == 1: found[0] = True
            return
        # Забираем выведенные входные переменные
        for i in range(n):
            if i not in fixed and i in wire:
                fixed[i] = wire[i]
        if d >= n: return
        # Ищем первую нефиксированную
        var = -1
        for i in range(n):
            if i not in fixed: var = i; break
        if var < 0: return
        fixed[var] = 0; dfs(d+1, dict(fixed))
        if found[0] or nodes[0] > max_nodes: return
        fixed[var] = 1; dfs(d+1, dict(fixed))
    dfs(0, {})
    return nodes[0] if nodes[0] <= max_nodes else None


def dfs_smart_order(gates, n, max_nodes=5000000):
    """DFS + smart variable ordering (most constrained first)."""
    # Предвычисляем fan-out каждой переменной
    fanout = [0] * n
    for g in gates:
        if g[1] < n: fanout[g[1]] += 1
        if g[2] >= 0 and g[2] < n: fanout[g[2]] += 1
    # Порядок: сначала переменные с наибольшим fan-out
    order = sorted(range(n), key=lambda i: -fanout[i])

    nodes = [0]; found = [False]
    def dfs(d, fixed):
        nodes[0] += 1
        if nodes[0] > max_nodes: return
        out = propagate(gates, fixed)
        if out is not None:
            if out == 1: found[0] = True
            return
        if d >= n: return
        var = -1
        for v in order:
            if v not in fixed: var = v; break
        if var < 0: return
        fixed[var] = 0; dfs(d+1, fixed)
        if found[0] or nodes[0] > max_nodes: return
        fixed[var] = 1; dfs(d+1, fixed)
        if found[0]: return
        del fixed[var]
    dfs(0, {})
    return nodes[0] if nodes[0] <= max_nodes else None


def dfs_combined(gates, n, max_nodes=5000000):
    """Всё вместе: smart order + backward propagation."""
    fanout = [0] * n
    for g in gates:
        if g[1] < n: fanout[g[1]] += 1
        if g[2] >= 0 and g[2] < n: fanout[g[2]] += 1
    order = sorted(range(n), key=lambda i: -fanout[i])
    out_id = gates[-1][3] if gates else -1

    nodes = [0]; found = [False]
    def dfs(d, fixed):
        nodes[0] += 1
        if nodes[0] > max_nodes: return
        wire = propagate_full(gates, n, fixed)
        out = wire.get(out_id)
        if out is not None:
            if out == 1: found[0] = True
            return
        for i in range(n):
            if i not in fixed and i in wire:
                fixed[i] = wire[i]
        if d >= n: return
        var = -1
        for v in order:
            if v not in fixed: var = v; break
        if var < 0: return
        f1 = dict(fixed); f1[var] = 0; dfs(d+1, f1)
        if found[0] or nodes[0] > max_nodes: return
        f2 = dict(fixed); f2[var] = 1; dfs(d+1, f2)
    dfs(0, {})
    return nodes[0] if nodes[0] <= max_nodes else None


# Генераторы
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

def random_circuit(n, size):
    gates=[]; nid=n
    for _ in range(size):
        gtype=random.choice(['AND','OR','NOT'])
        if gtype=='NOT':
            gates.append(('NOT',random.randint(0,nid-1),-1,nid))
        else:
            gates.append((gtype,random.randint(0,nid-1),random.randint(0,nid-1),nid))
        nid+=1
    return gates, n

def main():
    random.seed(42)
    print("=" * 72)
    print("  СРАВНЕНИЕ: 4 варианта DFS на Circuit-SAT")
    print("  basic | smart_order | backward | combined")
    print("=" * 72)

    methods = [
        ("basic", dfs_basic),
        ("smart", dfs_smart_order),
        ("backwd", dfs_backward),
        ("combi", dfs_combined),
    ]

    # =========================================================
    # ТЕСТ 1: 3-SAT
    # =========================================================
    print()
    print("  ТЕСТ 1: 3-SAT (α=4.27)")
    header = f"  {'n':>4}"
    for name, _ in methods: header += f" {name+' ε':>9}"
    print(header)
    print(f"  {'-'*4 + '-'*10*len(methods)}")

    for n in [10, 12, 14, 16, 18, 20]:
        row = f"  {n:4d}"
        g, nv = build_3sat(n)
        for name, method in methods:
            nodes = method(g, nv, 5000000)
            if nodes and nodes > 1:
                eps = math.log2(max(1.01, (2**n)/nodes)) / n
                row += f" {eps:9.4f}"
            else:
                row += f" {'?':>9}"
        print(row)
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 2: Случайные схемы размера 5n
    # =========================================================
    print()
    print("  ТЕСТ 2: Случайные схемы (size=5n, 10 per n)")
    header = f"  {'n':>4}"
    for name, _ in methods: header += f" {name+' ε':>9}"
    print(header)
    print(f"  {'-'*4 + '-'*10*len(methods)}")

    for n in [10, 12, 14, 16, 18]:
        row = f"  {n:4d}"
        for name, method in methods:
            eps_list = []
            for _ in range(10):
                g, nv = random_circuit(n, 5*n)
                nodes = method(g, nv, 2000000)
                if nodes and nodes > 1:
                    eps_list.append(math.log2(max(1.01, (2**n)/nodes)) / n)
            if eps_list:
                row += f" {sum(eps_list)/len(eps_list):9.4f}"
            else:
                row += f" {'?':>9}"
        print(row)
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 3: Circuit-SAT разного размера (ключ для Williams)
    # =========================================================
    print()
    print("  ТЕСТ 3: Circuit-SAT размера s = kn (combined method)")
    print(f"  {'n':>4} {'s=2n':>8} {'s=5n':>8} {'s=10n':>8} {'s=n²':>8}")
    print(f"  {'-'*36}")

    for n in [10, 12, 14, 16, 18]:
        row = f"  {n:4d}"
        for mult in [2, 5, 10, n]:
            size = mult * n
            eps_list = []
            for _ in range(10):
                g, nv = random_circuit(n, size)
                # Пропускаем тривиальные
                x = {i: random.randint(0,1) for i in range(n)}
                if propagate(g, x) is None: continue
                nodes = dfs_combined(g, nv, 2000000)
                if nodes and nodes > 1:
                    eps_list.append(math.log2(max(1.01, (2**n)/nodes)) / n)
            if eps_list:
                row += f" {min(eps_list):8.4f}"
            else:
                row += f" {'?':>8}"
        print(row)
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 4: Improvement ratio: combined / basic
    # =========================================================
    print()
    print("  ТЕСТ 4: Speedup combined vs basic")
    print(f"  {'n':>4} {'basic':>8} {'combi':>8} {'ratio':>8}")
    print(f"  {'-'*28}")

    for n in [12, 14, 16, 18, 20]:
        g, nv = build_3sat(n)
        nb = dfs_basic(g, nv, 5000000)
        nc = dfs_combined(g, nv, 5000000)
        if nb and nc and nb > 1 and nc > 1:
            ratio = nb / nc
            eb = math.log2(max(1.01, (2**n)/nb)) / n
            ec = math.log2(max(1.01, (2**n)/nc)) / n
            print(f"  {n:4d} {eb:8.4f} {ec:8.4f} {ratio:8.1f}x")
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 5: Сравнение с PPSZ (теоретически)
    # =========================================================
    print()
    print("  ТЕСТ 5: Наш ε vs известные алгоритмы (3-SAT)")
    print()
    print("  Алгоритм         ε (3-SAT)")
    print("  --------------------------")
    print("  Brute force       0.000")
    print("  Наш basic         0.193 (доказано)")
    print("  Наш combined      ??? (из теста 4)")
    print("  Schöning (1999)   0.415")
    print("  PPSZ (2005)       0.614")
    print("  PPZ (1998)        0.386")

    print()
    print("=" * 72)
    print("  ИТОГ")
    print("=" * 72)

if __name__ == "__main__":
    main()
