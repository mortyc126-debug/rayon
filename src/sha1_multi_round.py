"""
SHA-1 MULTI-ROUND: как ε падает с числом раундов?
Строим 1,2,3,...,R раундов SHA-1 и измеряем preimage DFS.
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

def make_xor(gates, a, b, nid):
    na=nid; gates.append(('NOT',a,-1,na)); nid+=1
    nb=nid; gates.append(('NOT',b,-1,nb)); nid+=1
    t1=nid; gates.append(('AND',a,nb,t1)); nid+=1
    t2=nid; gates.append(('AND',na,b,t2)); nid+=1
    xor=nid; gates.append(('OR',t1,t2,xor)); nid+=1
    return xor, nid+1

def make_full_adder(gates, a, b, cin, nid):
    axb, nid = make_xor(gates, a, b, nid)
    s, nid = make_xor(gates, axb, cin, nid)
    ab = nid; gates.append(('AND', a, b, ab)); nid += 1
    caxb = nid; gates.append(('AND', cin, axb, caxb)); nid += 1
    cout = nid; gates.append(('OR', ab, caxb, cout)); nid += 1
    return s, cout, nid + 1

def make_adder(gates, a_bits, b_bits, nid):
    w = len(a_bits)
    sum_bits = []
    not0 = nid; gates.append(('NOT', a_bits[0], -1, not0)); nid += 1
    carry = nid; gates.append(('AND', a_bits[0], not0, carry)); nid += 1
    for i in range(w):
        s, carry, nid = make_full_adder(gates, a_bits[i], b_bits[i], carry, nid)
        sum_bits.append(s)
    return sum_bits, nid

def make_ch(gates, e, f, g, nid):
    ef = nid; gates.append(('AND', e, f, ef)); nid += 1
    ne = nid; gates.append(('NOT', e, -1, ne)); nid += 1
    neg_ = nid; gates.append(('AND', ne, g, neg_)); nid += 1
    ch = nid; gates.append(('OR', ef, neg_, ch)); nid += 1
    return ch, nid + 1

def build_sha1_multi_round(word_size, num_rounds):
    """SHA-1 с num_rounds раундами.
    Вход: 5 слов состояния + num_rounds слов сообщения.
    Каждый раунд использует своё слово w[r]."""
    w = word_size
    n = (5 + num_rounds) * w
    gates = []
    nid = n

    a = list(range(0, w))
    b = list(range(w, 2*w))
    c = list(range(2*w, 3*w))
    d = list(range(3*w, 4*w))
    e = list(range(4*w, 5*w))

    for r in range(num_rounds):
        w_bits = list(range((5+r)*w, (6+r)*w))
        rot = min(5, w-1) if w > 5 else 1
        rotl_a = a[rot:] + a[:rot]

        ch_bits = []
        for i in range(w):
            ch, nid = make_ch(gates, b[i], c[i], d[i], nid)
            ch_bits.append(ch)

        t1, nid = make_adder(gates, rotl_a, ch_bits, nid)
        t2, nid = make_adder(gates, t1, e, nid)
        temp, nid = make_adder(gates, t2, w_bits, nid)

        rot30 = w - (30 % w) if w > 1 else 0
        new_c = b[rot30:] + b[:rot30] if rot30 > 0 else list(b)

        e = list(d)
        d = list(c)
        c = new_c
        b = list(a)
        a = list(temp)

    out_wires = a + b + c + d + e
    return gates, n, out_wires

def dfs_solve(gates, n, max_nodes=5000000):
    nodes=[0]; result=[None]; out_id=gates[-1][3]
    def dfs(d, fixed):
        nodes[0]+=1
        if nodes[0]>max_nodes: return
        out = propagate(gates, fixed)
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

def eval_circuit(gates, assignment):
    wire = dict(assignment)
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

def build_preimage(hash_gates, n, out_wires, target_bits):
    gates = list(hash_gates)
    nid = max(g[3] for g in gates)+1 if gates else n
    match = []
    for i, ow in enumerate(out_wires):
        if i >= len(target_bits): break
        if target_bits[i] == 1:
            match.append(ow)
        else:
            gates.append(('NOT', ow, -1, nid))
            match.append(nid); nid += 1
    cur = match[0]
    for m in match[1:]:
        gates.append(('AND', cur, m, nid))
        cur = nid; nid += 1
    return gates, n

def main():
    random.seed(42)
    sys.setrecursionlimit(1000000)
    print("=" * 72)
    print("  SHA-1 MULTI-ROUND: ε vs число раундов")
    print("=" * 72)

    # =========================================================
    # ТЕСТ 1: w=6, раунды 1..12
    # =========================================================
    print()
    print("  ТЕСТ 1: w=6 (n = 36 + 6R), раунды 1..12")
    print()
    print(f"  {'R':>3} {'n':>5} {'gates':>7} {'DFS':>8} {'2^n':>12} "
          f"{'ε':>7} {'тренд':>6}")
    print(f"  {'-'*50}")

    prev = None
    for R in range(1, 13):
        w = 6
        gates_h, n, out_w = build_sha1_multi_round(w, R)
        dfs_list = []
        for trial in range(5):
            x = {i: random.randint(0,1) for i in range(n)}
            wire = eval_circuit(gates_h, x)
            target = [wire.get(ow, 0) for ow in out_w]
            pg, pn = build_preimage(gates_h, n, out_w, target)
            _, nd = dfs_solve(pg, pn, 5000000)
            if nd < 5000000: dfs_list.append(nd)
        if dfs_list:
            avg = sum(dfs_list)/len(dfs_list)
            eps = math.log2(max(1.01, 2**n / avg)) / n
            t = ""
            if prev is not None:
                t = "↑" if eps > prev+0.01 else ("↓" if eps < prev-0.01 else "≈")
            prev = eps
            print(f"  {R:3d} {n:5d} {len(gates_h):7d} {avg:8.0f} "
                  f"{2**n:12d} {eps:7.4f} {t:>6}")
        else:
            print(f"  {R:3d} {n:5d} {len(gates_h):7d} {'timeout':>8}")
            prev = 0
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 2: w=8, раунды 1..8
    # =========================================================
    print()
    print("  ТЕСТ 2: w=8 (n = 48 + 8R)")
    print()
    print(f"  {'R':>3} {'n':>5} {'DFS avg':>8} {'2^n':>14} {'ε':>7} {'тренд':>6}")
    print(f"  {'-'*44}")

    prev = None
    for R in range(1, 9):
        w = 8
        gates_h, n, out_w = build_sha1_multi_round(w, R)
        dfs_list = []
        for trial in range(5):
            x = {i: random.randint(0,1) for i in range(n)}
            wire = eval_circuit(gates_h, x)
            target = [wire.get(ow, 0) for ow in out_w]
            pg, pn = build_preimage(gates_h, n, out_w, target)
            _, nd = dfs_solve(pg, pn, 5000000)
            if nd < 5000000: dfs_list.append(nd)
        if dfs_list:
            avg = sum(dfs_list)/len(dfs_list)
            eps = math.log2(max(1.01, 2**n / avg)) / n
            t = ""
            if prev is not None:
                t = "↑" if eps > prev+0.01 else ("↓" if eps < prev-0.01 else "≈")
            prev = eps
            print(f"  {R:3d} {n:5d} {avg:8.0f} {2**n:14d} {eps:7.4f} {t:>6}")
        else:
            print(f"  {R:3d} {n:5d} {'timeout':>8}")
            prev = 0
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 3: w=4, раунды 1..20 (быстрая проверка)
    # =========================================================
    print()
    print("  ТЕСТ 3: w=4 (n = 24 + 4R), до 20 раундов")
    print()
    print(f"  {'R':>3} {'n':>5} {'DFS':>8} {'ε':>7} {'тренд':>6}")
    print(f"  {'-'*32}")

    prev = None
    for R in range(1, 21):
        w = 4
        gates_h, n, out_w = build_sha1_multi_round(w, R)
        dfs_list = []
        for trial in range(5):
            x = {i: random.randint(0,1) for i in range(n)}
            wire = eval_circuit(gates_h, x)
            target = [wire.get(ow, 0) for ow in out_w]
            pg, pn = build_preimage(gates_h, n, out_w, target)
            _, nd = dfs_solve(pg, pn, 5000000)
            if nd < 5000000: dfs_list.append(nd)
        if dfs_list:
            avg = sum(dfs_list)/len(dfs_list)
            eps = math.log2(max(1.01, 2**n / avg)) / n
            t = ""
            if prev is not None:
                t = "↑" if eps > prev+0.005 else ("↓" if eps < prev-0.005 else "≈")
            prev = eps
            print(f"  {R:3d} {n:5d} {avg:8.0f} {eps:7.4f} {t:>6}")
        else:
            print(f"  {R:3d} {n:5d} {'timeout':>8}")
            break
        sys.stdout.flush()

    print()
    print("=" * 72)
    print("  ИТОГ")
    print("=" * 72)

if __name__ == "__main__":
    main()
