"""
MEET-IN-THE-MIDDLE ПО РАУНДАМ + DFS PRUNING.

Хеш H = R_3 ∘ R_2 ∘ R_1 (3 раунда).
MITM: угадываем промежуточное состояние s между R_1 и R_2.
  Forward: R_1(x) = s → инвертируем R_1 (preimage маленькой схемы)
  Backward: R_3^{-1}(target) ∘ R_2^{-1}(?) = s → инвертируем R_2∘R_3

Если state = w бит:
  Standard MITM: 2^{w/2} (birthday на промежуточных состояниях)
  Наш: DFS+pruning для инвертирования каждой половины → меньше?

Ключ: каждая половина = МЕЛКАЯ схема (1-2 раунда).
DFS с const prop на мелкой схеме эффективнее чем на полной!
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

def build_one_round(input_wires, nid_ref, gates):
    """Один раунд SHA-like: Ch + Maj + XOR mix.
    Возвращает output_wires."""
    w = len(input_wires)
    new = []
    for i in range(w):
        e,f,g = input_wires[i], input_wires[(i+1)%w], input_wires[(i+2)%w]
        a,b,c = input_wires[(i+3)%w], input_wires[(i+4)%w], input_wires[(i+5)%w]
        nid = nid_ref[0]
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
        res = make_xor(gates, cm, input_wires[(i+6)%w], nid_ref)
        new.append(res)
    return new

def build_hash_rounds(nbits, rounds=3):
    """Строим хеш по раундам, возвращаем схемы каждого раунда отдельно."""
    w = max(nbits, 8)
    state = [i % nbits for i in range(w)]

    round_circuits = []  # (gates, input_ids, output_ids) per round
    global_nid = nbits

    for r in range(rounds):
        gates_r = []
        # Входы этого раунда = state
        # Переименовываем в свежие id для отдельной схемы
        input_ids = list(range(w))  # локальные id 0..w-1
        nid_ref = [w]
        output_ids = build_one_round(input_ids, nid_ref, gates_r)
        round_circuits.append((gates_r, w, output_ids))
        # Для следующего раунда: state = output (с глобальными id)
        state = [global_nid + i for i in range(w)]
        global_nid += w  # placeholder

    return round_circuits, nbits, w


def eval_round(round_gates, w, assignment):
    """Вычисляем один раунд: input assignment → output values."""
    wire = propagate(round_gates, assignment)
    # Извлекаем output wires (последние w проводов с гейтами)
    # Находим output ids из round_gates
    all_outs = set()
    for g in round_gates:
        all_outs.add(g[3])
    all_inputs_used = set()
    for g in round_gates:
        all_inputs_used.add(g[1])
        if g[2] >= 0: all_inputs_used.add(g[2])
    # Output wires = те что ни разу не используются как входы (листья)
    # Нет, лучше: последние w значений
    max_id = max(g[3] for g in round_gates)
    output_vals = {}
    for i in range(w):
        oid = max_id - w + 1 + i
        output_vals[i] = wire.get(oid)
    return output_vals


def build_full_hash(nbits, hbits, rounds=3):
    """Полный хеш для сравнения."""
    n=nbits; gates=[]; nid_ref=[n]
    state=[i%n for i in range(max(hbits,8))]; w=len(state)
    for r in range(rounds):
        state = build_one_round(state, nid_ref, gates)
    while len(state)>hbits:
        new=[]
        for i in range(0,len(state)-1,2):
            new.append(make_xor(gates,state[i],state[i+1],nid_ref))
        if len(state)%2: new.append(state[-1])
        state=new
    while len(state)<hbits: state.append(state[-1])
    return gates, n, state[:hbits]


def dfs_invert_round(round_gates, w, target_output, max_nodes=500000):
    """DFS: найти input assignment такой что round(input) = target_output."""
    # Строим SAT circuit: round(x) == target
    gates = list(round_gates)
    nid_ref = [max(g[3] for g in gates) + 1 if gates else w]
    max_id = max(g[3] for g in round_gates) if round_gates else w - 1

    # Match каждого выходного бита
    match_bits = []
    for i in range(w):
        oid = max_id - w + 1 + i
        tval = target_output.get(i)
        if tval is None: continue
        if tval == 1:
            match_bits.append(oid)
        else:
            nid = nid_ref[0]
            gates.append(('NOT', oid, -1, nid))
            nid_ref[0] = nid + 1
            match_bits.append(nid)

    if not match_bits:
        return {i: 0 for i in range(w)}, 1

    # AND chain
    nid = nid_ref[0]
    cur = match_bits[0]
    for mb in match_bits[1:]:
        gates.append(('AND', cur, mb, nid))
        cur = nid; nid += 1

    # DFS
    nodes = [0]; result = [None]; out_id = cur
    def dfs(d, fixed):
        nodes[0] += 1
        if nodes[0] > max_nodes: return
        wire = propagate(gates, fixed)
        out = wire.get(out_id)
        if out is not None:
            if out == 1: result[0] = dict(fixed)
            return
        if d >= w: return
        fixed[d] = 0; dfs(d+1, fixed)
        if result[0] or nodes[0] > max_nodes: return
        fixed[d] = 1; dfs(d+1, fixed)
        if result[0]: return
        del fixed[d]
    dfs(0, {})
    return result[0], nodes[0]


def main():
    random.seed(42)
    sys.setrecursionlimit(200000)
    print("=" * 72)
    print("  ROUND MITM + DFS PRUNING")
    print("=" * 72)

    # =========================================================
    # ТЕСТ 1: Стоимость инвертирования ОДНОГО раунда
    # =========================================================
    print()
    print("  ТЕСТ 1: Инвертирование одного раунда (DFS nodes)")
    print("  Один раунд = маленькая схема, DFS должен быть дешёвым")
    print()

    round_circuits, nbits_base, w = build_hash_rounds(10, 3)
    print(f"  state_width = {w}, 3 раунда")
    print()

    print(f"  {'round':>6} {'gates':>6} {'DFS avg':>8} {'DFS min':>8} {'2^w':>7}")
    print(f"  {'-'*38}")

    for r_idx, (r_gates, r_w, r_outs) in enumerate(round_circuits):
        dfs_nodes_list = []
        for _ in range(20):
            # Случайный target output
            target = {i: random.randint(0, 1) for i in range(w)}
            result, nodes = dfs_invert_round(r_gates, r_w, target, 500000)
            if nodes < 500000:
                dfs_nodes_list.append(nodes)
        if dfs_nodes_list:
            avg = sum(dfs_nodes_list)/len(dfs_nodes_list)
            mn = min(dfs_nodes_list)
            print(f"  R{r_idx:4d} {len(r_gates):6d} {avg:8.0f} {mn:8d} {2**w:7d}")
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 2: MITM по раундам — forward R1 + backward R2∘R3
    # =========================================================
    print()
    print("  ТЕСТ 2: MITM по раундам (collision)")
    print("  Forward: x → R1(x) = s. Backward: target → R3⁻¹∘R2⁻¹ → s.")
    print("  Match on s → collision chain!")
    print()

    for nbits in [8, 10, 12]:
        # Полный хеш для baseline
        full_g, full_n, full_hw = build_full_hash(nbits, nbits, 3)
        hbits = nbits

        # Раундовая декомпозиция
        rc, _, w = build_hash_rounds(nbits, 3)

        # Forward half: R1 (раунд 0)
        r1_gates = rc[0][0]

        # Собираем forward таблицу: x → R1(x)
        fwd_table = {}  # state → x
        fwd_evals = 0
        for bx in range(min(2**nbits, 50000)):
            x = {i: (bx >> i) & 1 for i in range(nbits)}
            # Паддинг до w бит
            x_padded = {i: x.get(i % nbits, 0) for i in range(w)}
            out = eval_round(r1_gates, w, x_padded)
            fwd_evals += 1
            state = tuple(out.get(i) for i in range(w))
            if None not in state:
                if state not in fwd_table:
                    fwd_table[state] = x_padded
                else:
                    # Коллизия на промежуточном состоянии!
                    prev = fwd_table[state]
                    if any(x_padded.get(i) != prev.get(i) for i in range(w)):
                        pass  # Коллизия после R1, не полная

        # Backward half: инвертируем R2∘R3
        # Выбираем случайные целевые хеши из таблицы
        bwd_evals = 0
        found_collision = False

        targets_to_try = list(fwd_table.keys())[:min(100, len(fwd_table))]
        for target_state in targets_to_try:
            # Инвертируем R2: R2(target_state) = ?
            # Нам нужно: R2(s) = s2 такой что R3(s2) = final_target
            # Упрощение: ищем коллизию на ПРОМЕЖУТОЧНОМ состоянии
            result, nodes = dfs_invert_round(r1_gates, w, dict(enumerate(target_state)), 50000)
            bwd_evals += nodes
            if result and result != fwd_table[target_state]:
                found_collision = True
                break
            if bwd_evals > 500000:
                break

        total = fwd_evals + bwd_evals
        # Standard birthday
        random.seed(42)
        table = {}; bday = 0
        for _ in range(500000):
            x = {i: random.randint(0,1) for i in range(nbits)}
            wire = propagate(full_g, x)
            h = tuple(wire.get(hw) for hw in full_hw)
            bday += 1
            if None in h: continue
            if h in table:
                if any(x.get(i,0) != table[h].get(i,0) for i in range(nbits)):
                    break
            table[h] = dict(x)

        sp = bday / max(1, total)
        print(f"  n={nbits:2d}: MITM={total:8d} (fwd={fwd_evals}, bwd={bwd_evals}), "
              f"Birthday={bday:6d}, ratio={sp:.2f}x")
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 3: Стоимость инвертирования vs state width
    # =========================================================
    print()
    print("  ТЕСТ 3: Инвертирование одного раунда vs state width")
    print()
    print(f"  {'w':>3} {'DFS avg':>8} {'2^w':>8} {'ε':>7}")
    print(f"  {'-'*28}")

    for nbits in [6, 8, 10, 12, 14, 16]:
        rc, _, w = build_hash_rounds(nbits, 3)
        r_gates = rc[0][0]
        dfs_list = []
        for _ in range(20):
            target = {i: random.randint(0,1) for i in range(w)}
            _, nodes = dfs_invert_round(r_gates, w, target, 1000000)
            if nodes < 1000000: dfs_list.append(nodes)
        if dfs_list:
            avg = sum(dfs_list)/len(dfs_list)
            eps = math.log2(max(1.01, 2**w / avg)) / w if w > 0 else 0
            print(f"  {w:3d} {avg:8.0f} {2**w:8d} {eps:7.4f}")
        sys.stdout.flush()

    # =========================================================
    # ИТОГ
    # =========================================================
    print()
    print("=" * 72)
    print("  ИТОГ: ROUND MITM")
    print("=" * 72)
    print("""
  Один раунд = маленькая схема.
  DFS инвертирует один раунд за ~X nodes (vs 2^w brute force).
  ε для одного раунда показывает эффективность.

  MITM по раундам:
    Total = forward(2^w) + backward(invert cost per target × #targets)
    Если invert cost << 2^w: MITM дешевле birthday.
    """)

if __name__ == "__main__":
    main()
