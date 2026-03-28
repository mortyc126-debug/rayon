"""
RAYON BIRTHDAY: масштабирование до больших h.
Проверяем: phase2 = O(n) сохраняется при h=12,16,20?
Если да → 2^{h/4} подтверждено.
Если нет → нужно понять где ломается.
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

def make_xor(gates, a, b, nid_ref):
    nid=nid_ref[0]
    na=nid; gates.append(('NOT',a,-1,na)); nid+=1
    nb=nid; gates.append(('NOT',b,-1,nb)); nid+=1
    t1=nid; gates.append(('AND',a,nb,t1)); nid+=1
    t2=nid; gates.append(('AND',na,b,t2)); nid+=1
    xor=nid; gates.append(('OR',t1,t2,xor)); nid+=1
    nid_ref[0]=nid; return xor

def build_hash(nbits, hbits, rounds=3):
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
            ab_=nid; gates.append(('AND',a,b,ab_)); nid+=1
            ac_=nid; gates.append(('AND',a,c,ac_)); nid+=1
            bc_=nid; gates.append(('AND',b,c,bc_)); nid+=1
            t1=nid; gates.append(('OR',ab_,ac_,t1)); nid+=1
            maj=nid; gates.append(('OR',t1,bc_,maj)); nid+=1
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

def build_mt_preimage(hash_gates, nbits, hash_wires, targets):
    gates = list(hash_gates)
    nid_ref = [max(g[3] for g in gates)+1 if gates else nbits]
    hbits = len(hash_wires)
    target_matches = []
    for target in targets:
        match_bits = []
        for j in range(hbits):
            if target[j] == 1:
                match_bits.append(hash_wires[j])
            else:
                nid=nid_ref[0]
                gates.append(('NOT', hash_wires[j], -1, nid))
                nid_ref[0]=nid+1
                match_bits.append(nid)
        nid=nid_ref[0]; cur=match_bits[0]
        for mb in match_bits[1:]:
            gates.append(('AND',cur,mb,nid)); cur=nid; nid+=1
        nid_ref[0]=nid
        target_matches.append(cur)
    nid=nid_ref[0]; cur=target_matches[0]
    for tm in target_matches[1:]:
        gates.append(('OR',cur,tm,nid)); cur=nid; nid+=1
    return gates, nbits

def dfs_solve(gates, n, max_nodes=10000000):
    nodes=[0]; result=[None]; out_id=gates[-1][3]
    def dfs(d, fixed):
        nodes[0]+=1
        if nodes[0]>max_nodes: return
        wire=propagate(gates,fixed)
        out=wire.get(out_id)
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

def rayon_birthday(hash_gates, nbits, hash_wires, K, max_total=10000000):
    """Rayon Birthday с заданным K."""
    hbits = len(hash_wires)
    table = {}; p1 = 0
    while len(table) < K and p1 < max_total // 2:
        x = {i: random.randint(0, 1) for i in range(nbits)}
        wire = propagate(hash_gates, x)
        h = tuple(wire.get(hw) for hw in hash_wires)
        p1 += 1
        if None in h: continue
        if h in table:
            prev = table[h]
            if any(x.get(i,0) != prev.get(i,0) for i in range(nbits)):
                return p1, 0, True  # collision in phase1
        table[h] = dict(x)
    if not table:
        return p1, 0, False
    targets = list(table.keys())
    mt_gates, mt_n = build_mt_preimage(hash_gates, nbits, hash_wires, targets)
    result, p2 = dfs_solve(mt_gates, mt_n, max_total - p1)
    found = False
    if result:
        wire = propagate(hash_gates, result)
        h_f = tuple(wire.get(hw) for hw in hash_wires)
        if h_f in table:
            prev = table[h_f]
            if any(result.get(i,0) != prev.get(i,0) for i in range(nbits)):
                found = True
    return p1, p2, found

def std_birthday(hash_gates, nbits, hash_wires, max_evals=10000000):
    table={}; evals=0
    for _ in range(max_evals):
        x={i:random.randint(0,1) for i in range(nbits)}
        wire=propagate(hash_gates,x)
        h=tuple(wire.get(hw) for hw in hash_wires)
        evals+=1
        if None in h: continue
        if h in table:
            prev=table[h]
            if any(x.get(i,0)!=prev.get(i,0) for i in range(nbits)):
                return evals, True
        table[h]=dict(x)
    return evals, False

def main():
    random.seed(42)
    sys.setrecursionlimit(100000)
    print("=" * 72)
    print("  RAYON BIRTHDAY: МАСШТАБИРОВАНИЕ")
    print("=" * 72)

    # =========================================================
    # ТЕСТ 1: Phase2 cost vs h (фиксированный input=16)
    # =========================================================
    print()
    print("  ТЕСТ 1: Phase2 (multi-target DFS) vs h")
    print("  input=16, K=4, 5 trials each")
    print()
    print(f"  {'h':>3} {'p2 avg':>8} {'p2 min':>8} {'p2 max':>8} {'O(n)?':>6}")
    print(f"  {'-'*36}")

    nbits = 16
    for hbits in [4, 6, 8, 10, 12]:
        hash_g, n, hw = build_hash(nbits, hbits, 3)
        p2_list = []
        for trial in range(5):
            random.seed(42 + trial)
            K = 4
            table = {}
            while len(table) < K:
                x = {i: random.randint(0,1) for i in range(nbits)}
                wire = propagate(hash_g, x)
                h = tuple(wire.get(hw_) for hw_ in hw)
                if None not in h: table[h] = dict(x)
            targets = list(table.keys())[:K]
            mt_g, mt_n = build_mt_preimage(hash_g, nbits, hw, targets)
            _, p2 = dfs_solve(mt_g, mt_n, 5000000)
            if p2 < 5000000:
                p2_list.append(p2)
        if p2_list:
            avg = sum(p2_list)/len(p2_list)
            is_on = "✓" if avg < 5 * nbits else "✗"
            print(f"  {hbits:3d} {avg:8.0f} {min(p2_list):8d} "
                  f"{max(p2_list):8d} {is_on:>6}")
        else:
            print(f"  {hbits:3d} {'timeout':>8}")
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 2: Phase2 vs input size (h=8, K=4)
    # =========================================================
    print()
    print("  ТЕСТ 2: Phase2 vs input size (h=8, K=4)")
    print()
    print(f"  {'n':>3} {'p2 avg':>8} {'n×c':>6}")
    print(f"  {'-'*20}")

    for nbits in [10, 12, 14, 16, 18, 20]:
        hbits = 8
        hash_g, n, hw = build_hash(nbits, hbits, 3)
        p2_list = []
        for trial in range(5):
            random.seed(42 + trial)
            table = {}
            while len(table) < 4:
                x = {i: random.randint(0,1) for i in range(nbits)}
                wire = propagate(hash_g, x)
                h = tuple(wire.get(hw_) for hw_ in hw)
                if None not in h: table[h] = dict(x)
            targets = list(table.keys())[:4]
            mt_g, mt_n = build_mt_preimage(hash_g, nbits, hw, targets)
            _, p2 = dfs_solve(mt_g, mt_n, 5000000)
            if p2 < 5000000: p2_list.append(p2)
        if p2_list:
            avg = sum(p2_list)/len(p2_list)
            print(f"  {nbits:3d} {avg:8.0f} {nbits*3:6d}")
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 3: Full Rayon vs Birthday — масштабирование
    # =========================================================
    print()
    print("  ТЕСТ 3: Rayon (K=2^{h/4}) vs Birthday")
    print()
    print(f"  {'n':>3} {'h':>3} {'K':>5} {'Rayon':>9} {'Bday':>9} "
          f"{'speedup':>8} {'2^{h/4}':>8}")
    print(f"  {'-'*50}")

    for nbits in [10, 12, 14, 16]:
        for hbits in [4, 6, 8, min(10, nbits)]:
            K = max(2, int(2**(hbits/4)))
            hash_g, n, hw = build_hash(nbits, hbits, 3)
            random.seed(42)
            p1, p2, found_r = rayon_birthday(hash_g, nbits, hw, K, 5000000)
            rayon_total = p1 + p2
            random.seed(42)
            bday_total, found_b = std_birthday(hash_g, nbits, hw, 5000000)
            sp = bday_total / max(1, rayon_total) if found_r else 0
            two_h4 = 2**(hbits//4 + 1)
            f_r = "✓" if found_r else "✗"
            print(f"  {nbits:3d} {hbits:3d} {K:5d} {rayon_total:9d}{f_r} "
                  f"{bday_total:9d} {sp:8.2f}x {two_h4:8d}")
            sys.stdout.flush()

    # =========================================================
    # ТЕСТ 4: Оптимизация K — ищем sweet spot
    # =========================================================
    print()
    print("  ТЕСТ 4: Оптимальное K (n=14, h=8)")
    print()
    print(f"  {'K':>5} {'p1':>6} {'p2':>8} {'total':>8} {'found':>6}")
    print(f"  {'-'*36}")

    nbits = 14; hbits = 8
    hash_g, n, hw = build_hash(nbits, hbits, 3)
    for K in [1, 2, 3, 4, 6, 8, 12, 16, 24, 32]:
        random.seed(42)
        p1, p2, found = rayon_birthday(hash_g, nbits, hw, K, 5000000)
        total = p1 + p2
        print(f"  {K:5d} {p1:6d} {p2:8d} {total:8d} "
              f"{'✓' if found else '✗':>6}")
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 5: Большие h — stress test
    # =========================================================
    print()
    print("  ТЕСТ 5: Большие h (stress test)")
    print()
    print(f"  {'n':>3} {'h':>3} {'K':>5} {'Rayon':>9} {'found':>6}")
    print(f"  {'-'*28}")

    for nbits, hbits in [(16,8), (16,10), (16,12), (18,8), (18,10),
                          (20,8), (20,10), (20,12)]:
        K = max(2, int(2**(hbits/4)))
        hash_g, n, hw = build_hash(nbits, hbits, 3)
        random.seed(42)
        p1, p2, found = rayon_birthday(hash_g, nbits, hw, K, 5000000)
        total = p1 + p2
        print(f"  {nbits:3d} {hbits:3d} {K:5d} {total:9d} "
              f"{'✓' if found else '✗':>6}")
        sys.stdout.flush()

    # =========================================================
    # ИТОГ
    # =========================================================
    print()
    print("=" * 72)
    print("  ИТОГ МАСШТАБИРОВАНИЯ")
    print("=" * 72)

if __name__ == "__main__":
    main()
