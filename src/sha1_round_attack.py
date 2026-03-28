"""
Попытка пробить SHA-1 раунд через circuit DFS.
SHA-1 round: 32-bit words, modular addition, rotation, Ch/Maj/Parity.
Строим ТОЧНУЮ схему одного раунда и измеряем ε.
Честный тест: работает или нет.
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

def make_xor(gates, a, b, nid):
    na=nid; gates.append(('NOT',a,-1,na)); nid+=1
    nb=nid; gates.append(('NOT',b,-1,nb)); nid+=1
    t1=nid; gates.append(('AND',a,nb,t1)); nid+=1
    t2=nid; gates.append(('AND',na,b,t2)); nid+=1
    xor=nid; gates.append(('OR',t1,t2,xor)); nid+=1
    return xor, nid+1

def make_full_adder(gates, a, b, cin, nid):
    """Full adder: sum = a XOR b XOR cin, cout = MAJ(a,b,cin)."""
    # a XOR b
    axb, nid = make_xor(gates, a, b, nid)
    # sum = axb XOR cin
    s, nid = make_xor(gates, axb, cin, nid)
    # cout = (a AND b) OR (cin AND (a XOR b))
    ab = nid; gates.append(('AND', a, b, ab)); nid += 1
    caxb = nid; gates.append(('AND', cin, axb, caxb)); nid += 1
    cout = nid; gates.append(('OR', ab, caxb, cout)); nid += 1
    return s, cout, nid + 1

def make_adder(gates, a_bits, b_bits, nid):
    """32-bit ripple carry adder. a_bits, b_bits = lists of wire ids (LSB first)."""
    w = len(a_bits)
    sum_bits = []
    # carry начинается с 0
    not0 = nid; gates.append(('NOT', a_bits[0], -1, not0)); nid += 1
    carry = nid; gates.append(('AND', a_bits[0], not0, carry)); nid += 1  # const 0

    for i in range(w):
        s, carry, nid = make_full_adder(gates, a_bits[i], b_bits[i], carry, nid)
        sum_bits.append(s)
    return sum_bits, nid

def make_ch(gates, e, f, g, nid):
    """Ch(e,f,g) = (e AND f) XOR (NOT e AND g). Per bit."""
    ef = nid; gates.append(('AND', e, f, ef)); nid += 1
    ne = nid; gates.append(('NOT', e, -1, ne)); nid += 1
    neg = nid; gates.append(('AND', ne, g, neg)); nid += 1
    # XOR(ef, neg) = OR(AND(ef, NOT neg), AND(NOT ef, neg))
    # Для скорости используем OR (это Ch через AND/OR, не XOR!)
    # Ch = (e AND f) OR (NOT e AND g) — эквивалентно!
    ch = nid; gates.append(('OR', ef, neg, ch)); nid += 1
    return ch, nid + 1

def build_sha1_round(word_size=8):
    """Один раунд SHA-1 с уменьшенным word_size.
    Настоящий SHA-1: word_size=32. Мы тестируем 4,6,8,10,12.

    Вход: 5 слов (a,b,c,d,e) + 1 слово (w) = 6 × word_size бит.
    Выход: 5 слов (a',b',c',d',e') = 5 × word_size бит.

    SHA-1 round:
      temp = ROTL5(a) + Ch(b,c,d) + e + K + w
      e' = d
      d' = c
      c' = ROTL30(b)
      b' = a
      a' = temp
    """
    w = word_size
    n = 6 * w  # 5 state words + 1 message word
    gates = []
    nid = n

    # Входные слова (LSB first)
    a_bits = list(range(0, w))
    b_bits = list(range(w, 2*w))
    c_bits = list(range(2*w, 3*w))
    d_bits = list(range(3*w, 4*w))
    e_bits = list(range(4*w, 5*w))
    w_bits = list(range(5*w, 6*w))  # message word

    # ROTL5(a): сдвиг на 5 (или word_size % 5)
    rot = min(5, w-1) if w > 5 else 1
    rotl_a = a_bits[rot:] + a_bits[:rot]

    # Ch(b,c,d) per bit
    ch_bits = []
    for i in range(w):
        ch, nid = make_ch(gates, b_bits[i], c_bits[i], d_bits[i], nid)
        ch_bits.append(ch)

    # temp = ROTL5(a) + Ch(b,c,d) + e + w
    # Делаем последовательно: t1 = rotl_a + ch
    t1, nid = make_adder(gates, rotl_a, ch_bits, nid)
    # t2 = t1 + e
    t2, nid = make_adder(gates, t1, e_bits, nid)
    # temp = t2 + w
    temp, nid = make_adder(gates, t2, w_bits, nid)

    # Выходные слова:
    # a' = temp, b' = a, c' = ROTL30(b), d' = c, e' = d
    rot30 = w - (30 % w) if w > 1 else 0  # ROTL30
    rotl_b = b_bits[rot30:] + b_bits[:rot30] if rot30 > 0 else b_bits

    out_a = temp
    out_b = a_bits
    out_c = rotl_b
    out_d = c_bits
    out_e = d_bits

    all_out = out_a + out_b + out_c + out_d + out_e
    return gates, n, all_out, w


def build_preimage_circuit(hash_gates, n, out_wires, target_bits):
    """SAT: output == target."""
    gates = list(hash_gates)
    nid = max(g[3] for g in gates) + 1 if gates else n

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


def main():
    random.seed(42)
    sys.setrecursionlimit(500000)
    print("=" * 72)
    print("  SHA-1 ROUND ATTACK: честный тест")
    print("=" * 72)

    # =========================================================
    # ТЕСТ 1: Построить раунд, измерить размер схемы
    # =========================================================
    print()
    print("  ТЕСТ 1: Размер схемы SHA-1 раунда")
    print()
    print(f"  {'w':>3} {'n input':>8} {'gates':>7} {'out bits':>9}")
    print(f"  {'-'*30}")
    for w in [4, 6, 8, 10, 12]:
        gates, n, out, ws = build_sha1_round(w)
        print(f"  {w:3d} {n:8d} {len(gates):7d} {len(out):9d}")

    # =========================================================
    # ТЕСТ 2: Preimage для SHA-1 раунда
    # =========================================================
    print()
    print("  ТЕСТ 2: Preimage DFS для 1 раунда SHA-1")
    print()
    print(f"  {'w':>3} {'n':>5} {'DFS avg':>8} {'DFS min':>8} "
          f"{'2^n':>12} {'ε':>7}")
    print(f"  {'-'*46}")

    for w in [4, 6, 8, 10, 12]:
        gates_r, n, out_wires, ws = build_sha1_round(w)
        dfs_list = []
        for trial in range(10):
            # Случайный вход → вычисляем выход → preimage
            x = {i: random.randint(0,1) for i in range(n)}
            wire = {}
            wire.update(x)
            for gtype, i1, i2, outw in gates_r:
                v1=wire.get(i1); v2=wire.get(i2) if i2>=0 else None
                if gtype=='AND':
                    if v1==0 or v2==0: wire[outw]=0
                    elif v1 is not None and v2 is not None: wire[outw]=v1&v2
                elif gtype=='OR':
                    if v1==1 or v2==1: wire[outw]=1
                    elif v1 is not None and v2 is not None: wire[outw]=v1|v2
                elif gtype=='NOT':
                    if v1 is not None: wire[outw]=1-v1

            target = [wire.get(ow, 0) for ow in out_wires]

            pg, pn = build_preimage_circuit(gates_r, n, out_wires, target)
            _, nodes = dfs_solve(pg, pn, 5000000)
            if nodes < 5000000:
                dfs_list.append(nodes)

        if dfs_list:
            avg = sum(dfs_list)/len(dfs_list)
            mn = min(dfs_list)
            eps = math.log2(max(1.01, 2**n / avg)) / n
            print(f"  {w:3d} {n:5d} {avg:8.0f} {mn:8d} {2**n:12d} {eps:7.4f}")
        else:
            print(f"  {w:3d} {n:5d} {'timeout':>8}")
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 3: Partial preimage — фиксируем часть выхода
    # =========================================================
    print()
    print("  ТЕСТ 3: Partial preimage (match только первые k бит)")
    print("  w=8 (n=48)")
    print()
    print(f"  {'match':>6} {'DFS':>8} {'2^n':>10} {'ε':>7}")
    print(f"  {'-'*34}")

    w = 8
    gates_r, n, out_wires, ws = build_sha1_round(w)
    x = {i: random.randint(0,1) for i in range(n)}
    wire = dict(x)
    for gtype, i1, i2, outw in gates_r:
        v1=wire.get(i1); v2=wire.get(i2) if i2>=0 else None
        if gtype=='AND':
            if v1==0 or v2==0: wire[outw]=0
            elif v1 is not None and v2 is not None: wire[outw]=v1&v2
        elif gtype=='OR':
            if v1==1 or v2==1: wire[outw]=1
            elif v1 is not None and v2 is not None: wire[outw]=v1|v2
        elif gtype=='NOT':
            if v1 is not None: wire[outw]=1-v1
    full_target = [wire.get(ow, 0) for ow in out_wires]

    for match_bits in [4, 8, 12, 16, 20, 24, 32, 40]:
        if match_bits > len(out_wires): break
        target = full_target[:match_bits]
        pg, pn = build_preimage_circuit(gates_r, n, out_wires[:match_bits], target)
        _, nodes = dfs_solve(pg, pn, 5000000)
        if nodes < 5000000:
            eps = math.log2(max(1.01, 2**n / nodes)) / n
            print(f"  {match_bits:6d} {nodes:8d} {2**n:10d} {eps:7.4f}")
        else:
            print(f"  {match_bits:6d} {'timeout':>8}")
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 4: Масштабирование preimage ε vs word size
    # =========================================================
    print()
    print("  ТЕСТ 4: ε preimage vs word size (full output match)")
    print()
    print(f"  {'w':>3} {'n':>5} {'out':>5} {'ε':>7} {'тренд':>6}")
    print(f"  {'-'*28}")
    prev = None
    for w in [4, 5, 6, 7, 8, 9, 10]:
        gates_r, n, out_wires, ws = build_sha1_round(w)
        dfs_list = []
        for _ in range(5):
            x = {i: random.randint(0,1) for i in range(n)}
            wire = dict(x)
            for gtype, i1, i2, outw in gates_r:
                v1=wire.get(i1); v2=wire.get(i2) if i2>=0 else None
                if gtype=='AND':
                    if v1==0 or v2==0: wire[outw]=0
                    elif v1 is not None and v2 is not None: wire[outw]=v1&v2
                elif gtype=='OR':
                    if v1==1 or v2==1: wire[outw]=1
                    elif v1 is not None and v2 is not None: wire[outw]=v1|v2
                elif gtype=='NOT':
                    if v1 is not None: wire[outw]=1-v1
            target = [wire.get(ow,0) for ow in out_wires]
            pg, pn = build_preimage_circuit(gates_r, n, out_wires, target)
            _, nd = dfs_solve(pg, pn, 5000000)
            if nd < 5000000: dfs_list.append(nd)
        if dfs_list:
            avg = sum(dfs_list)/len(dfs_list)
            eps = math.log2(max(1.01, 2**n / avg)) / n
            t = ""
            if prev is not None:
                t = "↑" if eps > prev+0.01 else ("↓" if eps < prev-0.01 else "≈")
            prev = eps
            print(f"  {w:3d} {n:5d} {len(out_wires):5d} {eps:7.4f} {t:>6}")
        else:
            print(f"  {w:3d} {n:5d} {'timeout':>5}")
        sys.stdout.flush()

    # =========================================================
    # ИТОГ
    # =========================================================
    print()
    print("=" * 72)
    print("  ИТОГ: SHA-1 ROUND ATTACK")
    print("=" * 72)

if __name__ == "__main__":
    main()
