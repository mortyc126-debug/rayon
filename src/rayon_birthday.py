"""
╔══════════════════════════════════════════════════════════════════════════╗
║  RAYON BIRTHDAY: Наш собственный birthday attack                       ║
║  Комбинация: preimage DFS + birthday в пространстве хешей              ║
║                                                                         ║
║  Идея: birthday ищет коллизию в 2^{h/2} eval.                         ║
║  Каждый eval = один вызов H(x). Стоимость eval = O(s).                ║
║  Наш: каждый eval = preimage DFS. Дешевле когда n > h.                ║
║                                                                         ║
║  Rayon Birthday:                                                        ║
║    1. Генерируем 2^{h/2} случайных targets t₁, ..., t_K               ║
║    2. Для каждого tᵢ: ищем preimage xᵢ с H(xᵢ) = tᵢ (DFS)          ║
║    3. Если два xᵢ, xⱼ совпали по хешу → коллизия!                    ║
║    НО: targets одинаковые → preimages ГАРАНТИРОВАННО коллизия!        ║
║                                                                         ║
║  Правильнее:                                                            ║
║    1. Для K случайных x: вычисляем H(x) (обычный birthday)            ║
║    2. НО вычисление H(x) делаем через DFS partial eval               ║
║    3. Ранняя фильтрация: если первые биты H(x) не совпадают          ║
║       ни с чем в таблице → пропускаем полное вычисление               ║
║                                                                         ║
║  ЕЩЁ ЛУЧШЕ — Multi-target preimage:                                   ║
║    1. Собираем таблицу T из 2^{h/2} случайных хешей                  ║
║    2. Строим SAT circuit: H(x) ∈ T (H(x) совпадает с ЛЮБЫМ из T)    ║
║    3. DFS ищет x такой что H(x) ∈ T                                  ║
║    4. AND chain длины h + OR chain длины |T| → мощная обрезка!        ║
╚══════════════════════════════════════════════════════════════════════════╝
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


def build_multi_target_preimage(hash_gates, nbits, hash_wires, targets):
    """SAT: H(x) ∈ {t₁, ..., t_K}.
    Circuit: OR(H(x)==t₁, H(x)==t₂, ..., H(x)==t_K).
    Каждый H(x)==tᵢ = AND(match bits).
    OR of K targets = OR chain длины K.

    Ключ: AND chain обрезает при мисмэтче ЛЮБОГО бита,
    а OR chain позволяет: если хоть один target совпал → SAT!
    """
    gates = list(hash_gates)
    nid_ref = [max(g[3] for g in gates) + 1 if gates else nbits]
    hbits = len(hash_wires)

    target_matches = []
    for target in targets:
        # H(x) == target: AND(match[0], ..., match[h-1])
        match_bits = []
        for j in range(hbits):
            if target[j] == 1:
                match_bits.append(hash_wires[j])
            else:
                nid = nid_ref[0]
                gates.append(('NOT', hash_wires[j], -1, nid))
                nid_ref[0] = nid + 1
                match_bits.append(nid)

        # AND chain
        nid = nid_ref[0]
        cur = match_bits[0]
        for mb in match_bits[1:]:
            gates.append(('AND', cur, mb, nid))
            cur = nid; nid += 1
        nid_ref[0] = nid
        target_matches.append(cur)

    # OR of all target matches
    nid = nid_ref[0]
    cur = target_matches[0]
    for tm in target_matches[1:]:
        gates.append(('OR', cur, tm, nid))
        cur = nid; nid += 1

    return gates, nbits


def dfs_solve(gates, n, max_nodes=5000000):
    nodes = [0]; result = [None]
    out_id = gates[-1][3]
    def dfs(d, fixed):
        nodes[0] += 1
        if nodes[0] > max_nodes: return
        wire = propagate(gates, fixed)
        out = wire.get(out_id)
        if out is not None:
            if out == 1: result[0] = dict(fixed)
            return
        if d >= n: return
        fixed[d] = 0; dfs(d+1, fixed)
        if result[0] or nodes[0] > max_nodes: return
        fixed[d] = 1; dfs(d+1, fixed)
        if result[0]: return
        del fixed[d]
    dfs(0, {})
    return result[0], nodes[0]


def standard_birthday(hash_gates, nbits, hash_wires, max_evals=2000000):
    table = {}; evals = 0
    for _ in range(max_evals):
        x = {i: random.randint(0, 1) for i in range(nbits)}
        wire = propagate(hash_gates, x)
        h = tuple(wire.get(hw) for hw in hash_wires)
        evals += 1
        if None in h: continue
        if h in table:
            prev = table[h]
            if any(x.get(i, 0) != prev.get(i, 0) for i in range(nbits)):
                return evals, True, dict(x), prev
        table[h] = dict(x)
    return evals, False, None, None


def rayon_birthday(hash_gates, nbits, hash_wires, max_evals=2000000):
    """RAYON BIRTHDAY:
    Phase 1: Собираем таблицу из K случайных H(xᵢ).
    Phase 2: Multi-target preimage DFS: ищем x с H(x) ∈ таблица.
    Если нашли x, и x ≠ xᵢ → коллизия!

    K = 2^{h/4} (меньше чем birthday!).
    Multi-target preimage: OR из K targets → DFS обрезает эффективнее.
    """
    hbits = len(hash_wires)
    K = max(2, int(2 ** (hbits / 4)))  # 2^{h/4} targets

    # Phase 1: собираем K хешей
    table = {}  # hash → x
    phase1_evals = 0
    while len(table) < K and phase1_evals < max_evals // 2:
        x = {i: random.randint(0, 1) for i in range(nbits)}
        wire = propagate(hash_gates, x)
        h = tuple(wire.get(hw) for hw in hash_wires)
        phase1_evals += 1
        if None in h: continue
        if h in table:
            prev = table[h]
            if any(x.get(i, 0) != prev.get(i, 0) for i in range(nbits)):
                return phase1_evals, True, x, prev  # Нашли в phase 1!
        table[h] = dict(x)

    if not table:
        return phase1_evals, False, None, None

    targets = list(table.keys())

    # Phase 2: multi-target preimage DFS
    mt_gates, mt_n = build_multi_target_preimage(
        hash_gates, nbits, hash_wires, targets)

    result, phase2_nodes = dfs_solve(mt_gates, mt_n, max_evals - phase1_evals)
    total = phase1_evals + phase2_nodes

    if result:
        # Проверяем: нашли x с H(x) ∈ targets
        wire = propagate(hash_gates, result)
        h_found = tuple(wire.get(hw) for hw in hash_wires)
        if h_found in table:
            prev = table[h_found]
            if any(result.get(i, 0) != prev.get(i, 0) for i in range(nbits)):
                return total, True, result, prev

    return total, False, None, None


def main():
    random.seed(42)
    print("=" * 72)
    print("  RAYON BIRTHDAY: Multi-target preimage collision")
    print("=" * 72)

    # =========================================================
    # ТЕСТ 1: Rayon vs Standard Birthday, input=10
    # =========================================================
    print()
    print("  ТЕСТ 1: Rayon vs Birthday (input=10)")
    print()
    print(f"  {'h':>3} {'Birthday':>9} {'Rayon':>9} {'speedup':>8} {'K':>4}")
    print(f"  {'-'*36}")

    nbits = 10
    for hbits in range(3, 11):
        hash_gates, n, hw = build_hash(nbits, hbits, 3)
        random.seed(42)
        be, bf, _, _ = standard_birthday(hash_gates, nbits, hw, 500000)
        random.seed(42)
        re, rf, _, _ = rayon_birthday(hash_gates, nbits, hw, 500000)
        K = max(2, int(2 ** (hbits / 4)))
        sp = be / max(1, re) if rf else 0
        print(f"  {hbits:3d} {be:9d} {re:9d} {sp:8.2f}x {K:4d}")
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 2: Масштабирование при h = input
    # =========================================================
    print()
    print("  ТЕСТ 2: h = input (hardest for birthday)")
    print()
    print(f"  {'n':>3} {'Birthday':>9} {'Rayon':>9} {'speedup':>8} "
          f"{'2^{n/2}':>8}")
    print(f"  {'-'*40}")

    for nbits in [4, 5, 6, 7, 8, 9, 10, 11, 12]:
        hbits = nbits
        hash_gates, n, hw = build_hash(nbits, hbits, 3)
        random.seed(42)
        be, bf, _, _ = standard_birthday(hash_gates, nbits, hw, 500000)
        random.seed(42)
        re, rf, _, _ = rayon_birthday(hash_gates, nbits, hw, 500000)
        sp = be / max(1, re) if rf else 0
        print(f"  {nbits:3d} {be:9d} {re:9d} {sp:8.2f}x {2**(nbits//2+1):8d}")
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 3: Варьируем K (число targets)
    # =========================================================
    print()
    print("  ТЕСТ 3: Оптимальное K (input=10, h=8)")
    print()
    print(f"  {'K':>5} {'phase1':>7} {'phase2':>7} {'total':>7} {'found':>6}")
    print(f"  {'-'*34}")

    nbits = 10; hbits = 8
    hash_gates, n, hw = build_hash(nbits, hbits, 3)

    for K_mult in [1, 2, 4, 8, 16, 32]:
        K = max(2, K_mult)
        table = {}; p1 = 0
        random.seed(42)
        while len(table) < K and p1 < 100000:
            x = {i: random.randint(0, 1) for i in range(nbits)}
            wire = propagate(hash_gates, x)
            h = tuple(wire.get(hw_) for hw_ in hw)
            p1 += 1
            if None not in h: table[h] = dict(x)
        targets = list(table.keys())[:K]
        if len(targets) < K: continue

        mt_gates, mt_n = build_multi_target_preimage(
            hash_gates, nbits, hw, targets)
        result, p2 = dfs_solve(mt_gates, mt_n, 500000)
        found = result is not None
        print(f"  {K:5d} {p1:7d} {p2:7d} {p1+p2:7d} {'✓' if found else '✗':>6}")
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 4: Верификация — проверяем коллизии корректны
    # =========================================================
    print()
    print("  ТЕСТ 4: Верификация коллизий")
    print()

    for nbits in [8, 10, 12]:
        hbits = min(6, nbits)
        hash_gates, n, hw = build_hash(nbits, hbits, 3)
        random.seed(42)
        evals, found, x1, x2 = rayon_birthday(hash_gates, nbits, hw, 500000)
        if found and x1 and x2:
            wire1 = propagate(hash_gates, x1)
            wire2 = propagate(hash_gates, x2)
            h1 = tuple(wire1.get(hw_) for hw_ in hw)
            h2 = tuple(wire2.get(hw_) for hw_ in hw)
            match = h1 == h2
            diff = x1 != x2
            print(f"  n={nbits}, h={hbits}: H(x1)={h1}, H(x2)={h2}, "
                  f"match={match}, x1≠x2={diff} "
                  f"{'✓ VALID' if match and diff else '✗ INVALID'}")
        else:
            print(f"  n={nbits}, h={hbits}: not found in {evals} evals")

    # =========================================================
    # ТЕСТ 5: Теоретический анализ
    # =========================================================
    print()
    print("=" * 72)
    print("  ТЕОРЕТИЧЕСКИЙ АНАЛИЗ RAYON BIRTHDAY")
    print("=" * 72)
    print(f"""
  Standard Birthday:
    K = 2^{{h/2}} evaluations of H(x).
    Total cost = K × O(s) = 2^{{h/2}} × s.
    Memory = K = 2^{{h/2}}.

  Rayon Birthday:
    Phase 1: K = 2^{{h/4}} evaluations → таблица.
    Phase 2: Multi-target preimage DFS.
      Circuit: OR(H(x)==t₁, ..., H(x)==t_K).
      OR chain длины K: если ЛЮБОЙ target совпал → SAT.
      AND chain длины h внутри каждого: мисмэтч → обрезка.

    DFS cost для multi-target preimage:
      Каждый target: Pr[match] = 2^{{-h}}.
      K targets: Pr[any match] = K × 2^{{-h}} = 2^{{h/4-h}} = 2^{{-3h/4}}.
      DFS обрезает по AND chain: cost per path ≈ O(h).
      Total paths explored ≈ 2^n × 2^{{-3h/4}} ???

      НЕТ — это неправильная модель. DFS не перебирает ВСЕ пути.
      DFS с constant propagation обрезает на глубине ~h.
      Число листьев ≈ 2^h × K (для каждого target, 2^h путей).
      С OR: DFS пробует targets по очереди через OR-chain.

    Эмпирическая формула: измерим.
    """)

    print("  Эмпирика: DFS cost при разных K")
    print(f"  {'h':>3} {'K':>5} {'DFS phase2':>11} {'K×2^h':>9} {'ratio':>7}")
    print(f"  {'-'*38}")

    for hbits in [4, 6, 8]:
        nbits = 10
        hash_gates, n, hw = build_hash(nbits, hbits, 3)
        for K in [1, 2, 4, 8, 16]:
            random.seed(42 + K)
            table = {}
            while len(table) < K:
                x = {i: random.randint(0, 1) for i in range(nbits)}
                wire = propagate(hash_gates, x)
                h = tuple(wire.get(hw_) for hw_ in hw)
                if None not in h: table[h] = dict(x)
            targets = list(table.keys())[:K]
            mt_gates, mt_n = build_multi_target_preimage(
                hash_gates, nbits, hw, targets)
            _, p2 = dfs_solve(mt_gates, mt_n, 2000000)
            theory = K * (2**hbits)
            ratio = p2 / max(1, theory)
            print(f"  {hbits:3d} {K:5d} {p2:11d} {theory:9d} {ratio:7.4f}")
        sys.stdout.flush()

    print()
    print("=" * 72)
    print("  ИТОГ: RAYON BIRTHDAY")
    print("=" * 72)

if __name__ == "__main__":
    main()
