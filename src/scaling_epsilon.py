"""
МАСШТАБИРОВАНИЕ: ε = log2(speedup)/n при n → ∞.
Вопрос: ε → 0 или ε ≥ const > 0?
Если ε ≥ const → Williams → NEXP ⊄ P/poly.
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

def sat_dfs_nodes(gates, n, max_nodes=2000000):
    """DFS с constant propagation. Возвращает число узлов."""
    nodes = [0]
    found = [False]
    def dfs(depth, fixed):
        nodes[0] += 1
        if nodes[0] > max_nodes:
            return
        out = propagate(gates, fixed)
        if out is not None:
            if out == 1: found[0] = True
            return
        if depth >= n:
            return
        fixed[depth] = 0
        dfs(depth + 1, fixed)
        if found[0]: return
        fixed[depth] = 1
        dfs(depth + 1, fixed)
        if found[0]: return
        del fixed[depth]
    dfs(0, {})
    if nodes[0] > max_nodes:
        return None
    return nodes[0]

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

def build_xor_chain(n):
    gates=[]; nid=n; cur=0
    for i in range(1,n):
        nc=nid; gates.append(('NOT',cur,-1,nc)); nid+=1
        nb=nid; gates.append(('NOT',i,-1,nb)); nid+=1
        t1=nid; gates.append(('AND',cur,nb,t1)); nid+=1
        t2=nid; gates.append(('AND',nc,i,t2)); nid+=1
        xor=nid; gates.append(('OR',t1,t2,xor)); nid+=1
        cur=xor
    return gates, n

def build_tm110(n, steps=None):
    if steps is None: steps=min(n,10)
    gates=[]; nid=n; prev=list(range(n))
    for t in range(steps):
        new=[]
        for i in range(n):
            L,C,R=prev[(i-1)%n],prev[i],prev[(i+1)%n]
            ab=nid; gates.append(('AND',L,C,ab)); nid+=1
            bc=nid; gates.append(('AND',C,R,bc)); nid+=1
            nl=nid; gates.append(('NOT',L,-1,nl)); nid+=1
            nac=nid; gates.append(('AND',nl,R,nac)); nid+=1
            t1=nid; gates.append(('OR',ab,bc,t1)); nid+=1
            r=nid; gates.append(('OR',t1,nac,r)); nid+=1
            new.append(r)
        prev=new
    cur=prev[0]
    for p in prev[1:]: gates.append(('OR',cur,p,nid)); cur=nid; nid+=1
    return gates, n

def build_random_dag(n, mult=5):
    gates=[]; nid=n
    for _ in range(mult*n):
        gtype=random.choice(['AND','OR','NOT'])
        if gtype=='NOT': i1=random.randint(0,nid-1); gates.append(('NOT',i1,-1,nid))
        else: i1=random.randint(0,nid-1); i2=random.randint(0,nid-1); gates.append((gtype,i1,i2,nid))
        nid+=1
    return gates, n

def build_and_chain(n):
    gates=[]; nid=n; cur=0
    for i in range(1,n): g=nid; gates.append(('AND',cur,i,g)); nid+=1; cur=g
    return gates, n

def build_or_chain(n):
    gates=[]; nid=n; cur=0
    for i in range(1,n): g=nid; gates.append(('OR',cur,i,g)); nid+=1; cur=g
    return gates, n

def build_3sat_hard(n, alpha=4.27):
    """3-SAT с бОльшим alpha для harder instances."""
    return build_3sat(n, alpha)

def build_mixed_andor_xor(n):
    """Смешанная: половина AND/OR, половина XOR-encoded."""
    gates=[]; nid=n
    # XOR первой половины
    cur = 0
    for i in range(1, n//2):
        nc=nid; gates.append(('NOT',cur,-1,nc)); nid+=1
        nb=nid; gates.append(('NOT',i,-1,nb)); nid+=1
        t1=nid; gates.append(('AND',cur,nb,t1)); nid+=1
        t2=nid; gates.append(('AND',nc,i,t2)); nid+=1
        xor=nid; gates.append(('OR',t1,t2,xor)); nid+=1
        cur=xor
    xor_out = cur
    # AND второй половины
    cur = n//2
    for i in range(n//2+1, n):
        g=nid; gates.append(('AND',cur,i,g)); nid+=1; cur=g
    and_out = cur
    # OR(xor_result, and_result)
    g=nid; gates.append(('OR', xor_out, and_out, g)); nid+=1
    return gates, n

def main():
    random.seed(42)
    print("=" * 72)
    print("  МАСШТАБИРОВАНИЕ: ε = log2(speedup)/n при n → ∞")
    print("  ε > 0 для всех → Williams → NEXP ⊄ P/poly")
    print("=" * 72)

    types = [
        ("3-SAT", build_3sat),
        ("XOR-chain", build_xor_chain),
        ("TM rule110", build_tm110),
        ("AND-chain", build_and_chain),
        ("OR-chain", build_or_chain),
        ("Random DAG", lambda n: build_random_dag(n,5)),
        ("Mixed XOR+AND", build_mixed_andor_xor),
        ("3-SAT hard", lambda n: build_3sat_hard(n, 5.0)),
    ]

    ns = [8, 10, 12, 14, 16, 18, 20, 22]

    for name, builder in types:
        print(f"\n  {name}:")
        print(f"  {'n':>4} {'nodes':>10} {'2^n':>10} {'speedup':>10} {'ε':>7}")
        print(f"  {'-'*44}")
        for n in ns:
            g, nv = builder(n)
            nodes = sat_dfs_nodes(g, nv, 2000000)
            two_n = 2**n
            if nodes is not None and nodes > 0:
                sp = two_n / nodes
                eps = math.log2(max(1.01, sp)) / n
                print(f"  {n:4d} {nodes:10d} {two_n:10d} {sp:10.1f}x {eps:7.4f}")
            else:
                print(f"  {n:4d} {'>2M':>10} {two_n:10d} {'timeout':>10} {'?':>7}")
            sys.stdout.flush()

    # Сводная таблица ε
    print()
    print("=" * 72)
    print("  СВОДНАЯ ТАБЛИЦА: ε(n) для каждого типа")
    print("=" * 72)
    print()

    header = f"  {'n':>4}"
    short_names = ["3SAT", "XOR", "TM110", "AND", "OR", "DAG", "Mixed", "3SAT-h"]
    for sn in short_names:
        header += f" {sn:>7}"
    print(header)
    print(f"  {'-'*4 + '-'*8*len(short_names)}")

    for n in ns:
        row = f"  {n:4d}"
        for name, builder in types:
            g, nv = builder(n)
            nodes = sat_dfs_nodes(g, nv, 2000000)
            if nodes is not None and nodes > 0:
                sp = (2**n) / nodes
                eps = math.log2(max(1.01, sp)) / n
                row += f" {eps:7.4f}"
            else:
                row += f" {'?':>7}"
        print(row)
        sys.stdout.flush()

    # Min ε по всем типам
    print()
    print("  MIN ε по всем типам для каждого n:")
    print(f"  {'n':>4} {'min ε':>8} {'worst type':>15}")
    print(f"  {'-'*30}")

    for n in ns:
        min_eps = float('inf')
        worst = ""
        for name, builder in types:
            g, nv = builder(n)
            nodes = sat_dfs_nodes(g, nv, 2000000)
            if nodes is not None and nodes > 0:
                sp = (2**n) / nodes
                eps = math.log2(max(1.01, sp)) / n
                if eps < min_eps:
                    min_eps = eps
                    worst = name
            else:
                min_eps = 0
                worst = name + " (timeout)"
                break
        if min_eps < float('inf'):
            print(f"  {n:4d} {min_eps:8.4f} {worst:>15}")
        else:
            print(f"  {n:4d} {'?':>8} {'?':>15}")
        sys.stdout.flush()

    print()
    print("=" * 72)
    print("  ИТОГ")
    print("=" * 72)
    print("""
  Если min ε(n) → 0: метод НЕ работает для Williams.
  Если min ε(n) ≥ const > 0: SAT за O(2^{n(1-ε)}) для ВСЕХ схем.
    """)

if __name__ == "__main__":
    main()
