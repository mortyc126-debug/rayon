"""
SHA-1 с MESSAGE SCHEDULE. Честный тест.
Вход: 16 слов × w бит = 16w бит (реальный SHA-1: 16×32=512).
Message schedule: W[t] = ROTL1(W[t-3] XOR W[t-8] XOR W[t-14] XOR W[t-16]).
Это XOR-chain между раундами — наш БАРЬЕР.
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
    return wire

def make_xor(g, a, b, nid):
    na=nid;g.append(('NOT',a,-1,na));nid+=1
    nb=nid;g.append(('NOT',b,-1,nb));nid+=1
    t1=nid;g.append(('AND',a,nb,t1));nid+=1
    t2=nid;g.append(('AND',na,b,t2));nid+=1
    x=nid;g.append(('OR',t1,t2,x));nid+=1
    return x, nid+1

def make_full_adder(g, a, b, cin, nid):
    axb,nid=make_xor(g,a,b,nid)
    s,nid=make_xor(g,axb,cin,nid)
    ab=nid;g.append(('AND',a,b,ab));nid+=1
    cx=nid;g.append(('AND',cin,axb,cx));nid+=1
    co=nid;g.append(('OR',ab,cx,co));nid+=1
    return s,co,nid+1

def make_adder(g, a, b, nid):
    w=len(a);sums=[]
    n0=nid;g.append(('NOT',a[0],-1,n0));nid+=1
    carry=nid;g.append(('AND',a[0],n0,carry));nid+=1
    for i in range(w):
        s,carry,nid=make_full_adder(g,a[i],b[i],carry,nid)
        sums.append(s)
    return sums,nid

def make_ch(g, e, f, gg, nid):
    ef=nid;g.append(('AND',e,f,ef));nid+=1
    ne=nid;g.append(('NOT',e,-1,ne));nid+=1
    ng=nid;g.append(('AND',ne,gg,ng));nid+=1
    ch=nid;g.append(('OR',ef,ng,ch));nid+=1
    return ch,nid+1

def make_const(g, val, ref_wire, nid):
    """Создаём константу 0 или 1."""
    t=nid;g.append(('NOT',ref_wire,-1,t));nid+=1
    if val==1:
        c=nid;g.append(('OR',ref_wire,t,c));nid+=1
    else:
        c=nid;g.append(('AND',ref_wire,t,c));nid+=1
    return c,nid+1

def build_sha1_real(w, R):
    """SHA-1 с message schedule.
    Вход: 16 слов × w бит. Message schedule для t ≥ 16.
    R раундов всего (SHA-1: R=80)."""
    n = 16 * w  # 16 message words
    gates = []; nid = n

    # Message words W[0..15] = входы
    W = []
    for t in range(16):
        W.append(list(range(t*w, (t+1)*w)))

    # Message schedule: W[t] = ROTL1(W[t-3] XOR W[t-8] XOR W[t-14] XOR W[t-16])
    for t in range(16, R):
        # XOR chain: W[t-3] XOR W[t-8] XOR W[t-14] XOR W[t-16]
        tmp = list(W[t-16])
        for dt in [14, 8, 3]:
            new_tmp = []
            for i in range(w):
                x, nid = make_xor(gates, tmp[i], W[t-dt][i], nid)
                new_tmp.append(x)
            tmp = new_tmp
        # ROTL1
        rot = 1 if w > 1 else 0
        rotated = tmp[rot:] + tmp[:rot]
        W.append(rotated)

    # IV: фиксированные значения (как в SHA-1)
    random.seed(0xDEAD)
    iv_vals = [[random.randint(0,1) for _ in range(w)] for _ in range(5)]
    a=[]; b=[]; c=[]; d=[]; e=[]
    for word, bits in [(iv_vals[0],a),(iv_vals[1],b),(iv_vals[2],c),
                        (iv_vals[3],d),(iv_vals[4],e)]:
        for v in word:
            cv, nid = make_const(gates, v, 0, nid)
            bits.append(cv)

    # R раундов
    for t in range(R):
        rot5 = min(5, w-1) if w > 5 else 1
        rotl_a = a[rot5:] + a[:rot5]
        ch_bits = []
        for i in range(w):
            ch, nid = make_ch(gates, b[i], c[i], d[i], nid)
            ch_bits.append(ch)
        t1, nid = make_adder(gates, rotl_a, ch_bits, nid)
        t2, nid = make_adder(gates, t1, e, nid)
        temp, nid = make_adder(gates, t2, W[t], nid)
        rot30 = w-(30%w) if w>1 else 0
        new_c = b[rot30:]+b[:rot30] if rot30>0 else list(b)
        e=list(d); d=list(c); c=new_c; b=list(a); a=list(temp)

    out_wires = a + b + c + d + e
    return gates, n, out_wires

def dfs_solve(gates, n, max_nodes=5000000):
    nodes=[0]; result=[None]; out_id=gates[-1][3]
    def dfs(d, fixed):
        nodes[0]+=1
        if nodes[0]>max_nodes: return
        out=propagate(gates,fixed)
        if out is not None:
            if out==1: result[0]=dict(fixed)
            return
        if d>=n: return
        fixed[d]=0; dfs(d+1,fixed)
        if result[0] or nodes[0]>max_nodes: return
        fixed[d]=1; dfs(d+1,fixed)
        if result[0]: return
        del fixed[d]
    dfs(0,{})
    return result[0], nodes[0]

def eval_full(gates, x):
    wire = dict(x)
    for gtype, i1, i2, out in gates:
        v1=wire.get(i1); v2=wire.get(i2) if i2>=0 else None
        if gtype=='AND':
            if v1==0 or v2==0: wire[out]=0
            elif v1 is not None and v2 is not None: wire[out]=v1&v2
        elif gtype=='OR':
            if v1==1 or v2==1: wire[out]=1
            elif v1 is not None and v2 is not None: wire[out]=v1|v2
        elif gtype=='NOT':
            if v1 is not None: wire[out]=1-v1
    return wire

def build_preimage(hash_gates, n, out_wires, target):
    gates=list(hash_gates)
    nid=max(g[3] for g in gates)+1 if gates else n
    match=[]
    for i,ow in enumerate(out_wires):
        if i>=len(target): break
        if target[i]==1: match.append(ow)
        else: gates.append(('NOT',ow,-1,nid)); match.append(nid); nid+=1
    cur=match[0]
    for m in match[1:]:
        gates.append(('AND',cur,m,nid)); cur=nid; nid+=1
    return gates, n

def main():
    random.seed(42)
    sys.setrecursionlimit(1000000)
    print("=" * 72)
    print("  SHA-1 С MESSAGE SCHEDULE: честный тест")
    print("=" * 72)

    # =========================================================
    # ТЕСТ 1: Размеры
    # =========================================================
    print()
    print(f"  {'w':>3} {'R':>3} {'n':>5} {'gates':>7} {'out':>5}")
    print(f"  {'-'*26}")
    for w in [4, 6]:
        for R in [16, 20, 40]:
            g, n, ow = build_sha1_real(w, R)
            print(f"  {w:3d} {R:3d} {n:5d} {len(g):7d} {len(ow):5d}")

    # =========================================================
    # ТЕСТ 2: Preimage DFS с message schedule
    # =========================================================
    print()
    print("  ТЕСТ 2: Preimage (message schedule, w=4, n=64)")
    print()
    print(f"  {'R':>3} {'n':>5} {'DFS avg':>8} {'2^n':>14} {'ε':>7} {'тренд':>6}")
    print(f"  {'-'*44}")

    prev = None
    for R in [16, 17, 18, 19, 20, 24, 30, 40]:
        w = 4
        gates_h, n, out_w = build_sha1_real(w, R)
        dfs_list = []
        for trial in range(3):
            random.seed(42+trial+R*100)
            x = {i: random.randint(0,1) for i in range(n)}
            wire = eval_full(gates_h, x)
            target = [wire.get(ow, 0) for ow in out_w]
            pg, pn = build_preimage(gates_h, n, out_w, target)
            _, nd = dfs_solve(pg, pn, 5000000)
            if nd < 5000000: dfs_list.append(nd)
        if dfs_list:
            avg = sum(dfs_list)/len(dfs_list)
            eps = math.log2(max(1.01, 2**n/avg))/n
            t=""
            if prev is not None:
                t="↑" if eps>prev+0.01 else("↓" if eps<prev-0.01 else "≈")
            prev=eps
            print(f"  {R:3d} {n:5d} {avg:8.0f} {2**n:14d} {eps:7.4f} {t:>6}")
        else:
            print(f"  {R:3d} {n:5d} {'timeout':>8}")
            prev=0
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 3: w=6 с message schedule
    # =========================================================
    print()
    print("  ТЕСТ 3: w=6, n=96, message schedule")
    print()
    print(f"  {'R':>3} {'DFS avg':>8} {'ε':>7} {'тренд':>6}")
    print(f"  {'-'*26}")

    prev = None
    for R in [16, 18, 20, 24, 30, 40]:
        w = 6
        gates_h, n, out_w = build_sha1_real(w, R)
        dfs_list = []
        for trial in range(3):
            random.seed(42+trial+R*100)
            x = {i: random.randint(0,1) for i in range(n)}
            wire = eval_full(gates_h, x)
            target = [wire.get(ow, 0) for ow in out_w]
            pg, pn = build_preimage(gates_h, n, out_w, target)
            _, nd = dfs_solve(pg, pn, 5000000)
            if nd < 5000000: dfs_list.append(nd)
        if dfs_list:
            avg = sum(dfs_list)/len(dfs_list)
            eps = math.log2(max(1.01, 2**n/avg))/n
            t=""
            if prev is not None:
                t="↑" if eps>prev+0.01 else("↓" if eps<prev-0.01 else "≈")
            prev=eps
            print(f"  {R:3d} {avg:8.0f} {eps:7.4f} {t:>6}")
        else:
            print(f"  {R:3d} {'timeout':>8}")
            prev=0
        sys.stdout.flush()

    print()
    print("=" * 72)
    print("  ИТОГ")
    print("=" * 72)

if __name__ == "__main__":
    main()
