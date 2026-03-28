"""
МАСШТАБИРОВАНИЕ Hybrid Birthday: точная формула speedup.
Когда hybrid > birthday? На сколько? Растёт ли с n?
"""
import random, math, sys
from collections import defaultdict

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
    return wire

def make_xor(gates, a, b, nid_ref):
    nid = nid_ref[0]
    na=nid; gates.append(('NOT',a,-1,na)); nid+=1
    nb=nid; gates.append(('NOT',b,-1,nb)); nid+=1
    t1=nid; gates.append(('AND',a,nb,t1)); nid+=1
    t2=nid; gates.append(('AND',na,b,t2)); nid+=1
    xor=nid; gates.append(('OR',t1,t2,xor)); nid+=1
    nid_ref[0]=nid; return xor

def build_sha_hash(nbits, hbits, rounds=3):
    """SHA-like: Ch + Maj + XOR mix."""
    n=nbits; gates=[]; nid_ref=[n]
    state=[i%n for i in range(max(hbits,8))]; w=len(state)
    for r in range(rounds):
        new=[]
        for i in range(w):
            e,f,g=state[i],state[(i+1)%w],state[(i+2)%w]
            a,b,c=state[(i+3)%w],state[(i+4)%w],state[(i+5)%w]
            nid=nid_ref[0]
            ef=nid; gates.append(('AND',e,f,ef)); nid+=1
            ne=nid; gates.append(('NOT',e,-1,ne)); nid+=1
            neg_=nid; gates.append(('AND',ne,g,neg_)); nid+=1
            ch=nid; gates.append(('OR',ef,neg_,ch)); nid+=1
            ab=nid; gates.append(('AND',a,b,ab)); nid+=1
            ac=nid; gates.append(('AND',a,c,ac)); nid+=1
            bc=nid; gates.append(('AND',b,c,bc)); nid+=1
            t1=nid; gates.append(('OR',ab,ac,t1)); nid+=1
            maj=nid; gates.append(('OR',t1,bc,maj)); nid+=1
            cm=nid; gates.append(('OR',ch,maj,cm)); nid+=1
            nid_ref[0]=nid
            res=make_xor(gates,cm,state[(i+6)%w],nid_ref)
            new.append(res)
        state=new
    while len(state)>hbits:
        new=[]
        for i in range(0,len(state)-1,2):
            new.append(make_xor(gates,state[i],state[i+1],nid_ref))
        if len(state)%2: new.append(state[-1])
        state=new
    while len(state)<hbits: state.append(state[-1])
    return gates, n, state[:hbits]

def build_collision_sat(nbits, hbits, rounds=3):
    """SAT: H(x)==H(y) AND x≠y. Входы: x(nbits) + y(nbits)."""
    total_n = 2*nbits
    gates=[]; nid_ref=[total_n]
    # H(x)
    gx=[]; nx=[total_n]; sx=list(range(nbits))
    # reuse builder logic inline
    def hash_block(start, nbits, hbits, rounds):
        state=[start+i%nbits for i in range(max(hbits,8))]; w=len(state)
        for r in range(rounds):
            new=[]
            for i in range(w):
                e,f,g=state[i],state[(i+1)%w],state[(i+2)%w]
                a,b,c=state[(i+3)%w],state[(i+4)%w],state[(i+5)%w]
                nid=nid_ref[0]
                ef=nid; gates.append(('AND',e,f,ef)); nid+=1
                ne=nid; gates.append(('NOT',e,-1,ne)); nid+=1
                neg_=nid; gates.append(('AND',ne,g,neg_)); nid+=1
                ch=nid; gates.append(('OR',ef,neg_,ch)); nid+=1
                ab=nid; gates.append(('AND',a,b,ab)); nid+=1
                ac=nid; gates.append(('AND',a,c,ac)); nid+=1
                bc=nid; gates.append(('AND',b,c,bc)); nid+=1
                t1=nid; gates.append(('OR',ab,ac,t1)); nid+=1
                maj=nid; gates.append(('OR',t1,bc,maj)); nid+=1
                cm=nid; gates.append(('OR',ch,maj,cm)); nid+=1
                nid_ref[0]=nid
                res=make_xor(gates,cm,state[(i+6)%w],nid_ref)
                new.append(res)
            state=new
        while len(state)>hbits:
            new=[]
            for i in range(0,len(state)-1,2):
                new.append(make_xor(gates,state[i],state[i+1],nid_ref))
            if len(state)%2: new.append(state[-1])
            state=new
        while len(state)<hbits: state.append(state[-1])
        return state[:hbits]

    hx = hash_block(0, nbits, hbits, rounds)
    hy = hash_block(nbits, nbits, hbits, rounds)

    # H(x)==H(y): AND of XNOR
    eq_parts=[]
    for i in range(hbits):
        xor=make_xor(gates,hx[i],hy[i],nid_ref)
        nid=nid_ref[0]
        xnor=nid; gates.append(('NOT',xor,-1,xnor)); nid+=1
        nid_ref[0]=nid
        eq_parts.append(xnor)
    nid=nid_ref[0]
    cur=eq_parts[0]
    for e in eq_parts[1:]:
        g=nid; gates.append(('AND',cur,e,g)); nid+=1; cur=g
    hash_eq=cur

    # x≠y
    neq=[]
    for i in range(nbits):
        xor=make_xor(gates,i,nbits+i,nid_ref)
        neq.append(xor)
    nid=nid_ref[0]
    cur=neq[0]
    for ne in neq[1:]:
        g=nid; gates.append(('OR',cur,ne,g)); nid+=1; cur=g
    x_neq_y=cur

    output=nid; gates.append(('AND',hash_eq,x_neq_y,output)); nid+=1
    nid_ref[0]=nid
    return gates, total_n

def dfs_count(gates, n, max_nodes=500000):
    nodes=[0]; found=[False]
    def dfs(d,f):
        nodes[0]+=1
        if nodes[0]>max_nodes: return
        wire=propagate(gates,f)
        out=wire.get(gates[-1][3]) if gates else None
        if out is not None:
            if out==1: found[0]=True
            return
        if d>=n: return
        f[d]=0; dfs(d+1,f)
        if found[0] or nodes[0]>max_nodes: return
        f[d]=1; dfs(d+1,f)
        if found[0]: return
        del f[d]
    dfs(0,{})
    return nodes[0] if nodes[0]<=max_nodes else None, found[0]

def birthday_count(gates, n, nbits, hash_wires, max_evals=500000):
    """Birthday: eval H(x) for random x, find collision."""
    table={}; evals=0
    for _ in range(max_evals):
        x={i:random.randint(0,1) for i in range(nbits)}
        wire=propagate(gates,x)
        h=tuple(wire.get(hw) for hw in hash_wires)
        evals+=1
        if None in h: continue
        if h in table:
            prev=table[h]
            if any(x.get(i)!=prev.get(i) for i in range(nbits)):
                return evals, True
        table[h]=dict(x)
    return evals, False

def main():
    random.seed(42)
    print("=" * 72)
    print("  МАСШТАБИРОВАНИЕ: Hybrid vs Birthday — точная граница")
    print("=" * 72)

    # =========================================================
    # ТЕСТ 1: Фиксированный input, растущий hash
    # =========================================================
    print()
    print("  ТЕСТ 1: input=10, hash растёт. DFS-SAT vs Birthday.")
    print()
    print(f"  {'h':>3} {'n=2×in':>7} {'DFS':>8} {'bday':>8} "
          f"{'2^n':>9} {'DFS/bday':>9} {'DFS win':>8}")
    print(f"  {'-'*56}")

    nbits = 10
    for hbits in range(3, 11):
        gates_sat, n_sat = build_collision_sat(nbits, hbits, 3)
        gates_h, _, hw = build_sha_hash(nbits, hbits, 3)

        dfs_n, dfs_found = dfs_count(gates_sat, n_sat, 500000)
        bday_n, bday_found = birthday_count(gates_h, nbits, nbits, hw, 500000)

        if dfs_n and bday_n:
            ratio = dfs_n / bday_n
            win = "✓ DFS" if dfs_n < bday_n else "bday"
            print(f"  {hbits:3d} {n_sat:7d} {dfs_n:8d} {bday_n:8d} "
                  f"{2**n_sat:9d} {ratio:9.2f}x {win:>8}")
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 2: h/n ratio — crossover point
    # =========================================================
    print()
    print("  ТЕСТ 2: Crossover point (h/n ratio)")
    print()

    for nbits in [8, 10, 12]:
        print(f"  input={nbits}:")
        print(f"    {'h/in':>5} {'h':>3} {'DFS':>8} {'bday':>8} {'winner':>8}")
        for hbits in range(2, nbits+1):
            ratio_hn = hbits / nbits
            gates_sat, n_sat = build_collision_sat(nbits, hbits, 3)
            gates_h, _, hw = build_sha_hash(nbits, hbits, 3)
            dfs_n, _ = dfs_count(gates_sat, n_sat, 500000)
            bday_n, _ = birthday_count(gates_h, nbits, nbits, hw, 500000)
            if dfs_n and bday_n:
                win = "DFS" if dfs_n < bday_n else "bday"
                print(f"    {ratio_hn:5.2f} {hbits:3d} {dfs_n:8d} {bday_n:8d} {win:>8}")
            sys.stdout.flush()
        print()

    # =========================================================
    # ТЕСТ 3: Масштабирование при h = input (worst for birthday)
    # =========================================================
    print()
    print("  ТЕСТ 3: h = input (birthday = 2^{n/2}, DFS = ?)")
    print()
    print(f"  {'in':>3} {'h':>3} {'n':>5} {'DFS':>8} {'bday':>8} "
          f"{'2^{n/2}':>8} {'DFS ε':>7}")
    print(f"  {'-'*48}")

    for nbits in [4, 5, 6, 7, 8, 9, 10]:
        hbits = nbits
        gates_sat, n_sat = build_collision_sat(nbits, hbits, 3)
        gates_h, _, hw = build_sha_hash(nbits, hbits, 3)
        dfs_n, _ = dfs_count(gates_sat, n_sat, 2000000)
        bday_n, _ = birthday_count(gates_h, nbits, nbits, hw, 500000)
        two_half = 2**(n_sat//2)
        if dfs_n and dfs_n > 1:
            eps = math.log2(max(1.01, (2**n_sat)/dfs_n)) / n_sat
            print(f"  {nbits:3d} {hbits:3d} {n_sat:5d} {dfs_n:8d} "
                  f"{bday_n:8d} {two_half:8d} {eps:7.4f}")
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 4: DFS speedup formula: DFS ≈ O(n × 2^{h/2})?
    # =========================================================
    print()
    print("  ТЕСТ 4: Формула DFS для collision")
    print("  Гипотеза: DFS ≈ C × 2^{h} (NOT 2^{2n})")
    print("  Потому что AND(XNOR) chain длины h обрезает при мисмэтче")
    print()
    print(f"  {'in':>3} {'h':>3} {'DFS':>8} {'2^h':>8} {'DFS/2^h':>8}")
    print(f"  {'-'*32}")

    for nbits in [6, 7, 8, 9, 10]:
        for hbits in [4, 6, nbits]:
            gates_sat, n_sat = build_collision_sat(nbits, hbits, 3)
            dfs_n, _ = dfs_count(gates_sat, n_sat, 2000000)
            if dfs_n:
                ratio = dfs_n / (2**hbits)
                print(f"  {nbits:3d} {hbits:3d} {dfs_n:8d} {2**hbits:8d} {ratio:8.4f}")
            sys.stdout.flush()

    # =========================================================
    # ИТОГ
    # =========================================================
    print()
    print("=" * 72)
    print("  ИТОГ")
    print("=" * 72)
    print("""
  DFS для collision через SAT circuit:
    Circuit = AND(XNOR(h_x[i], h_y[i])) AND (x ≠ y)
    AND-chain длины h → FALSE при первом несовпавшем бите → обрезка!

  DFS cost ≈ C × 2^h (пропорционально пространству хешей, НЕ входов)
  Birthday cost ≈ 2^{h/2}

  DFS выигрывает когда: C × 2^h < 2^{h/2}
  → C < 2^{-h/2} → невозможно для C > 1.

  НО при h > n: birthday = 2^{h/2} > 2^{n/2},
  а DFS ≈ 2^n (полный перебор входов).
  Тогда DFS < birthday когда 2^n < 2^{h/2}, т.е. h > 2n.
    """)

if __name__ == "__main__":
    main()
