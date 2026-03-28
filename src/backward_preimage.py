"""
BACKWARD PREIMAGE: знаем target → propagate backward → определяем входы.
Это РЕВОЛЮЦИЯ: не нужен DFS по всем 2^n. Backward определяет биты БЕСПЛАТНО.

Для хеша H с h выходных бит:
  Знаем H(x)[i] = target[i] для всех i.
  Backward через каждый гейт:
    AND(a,b) = 1 → a=1, b=1
    AND(a,b) = 0, a=1 → b=0
    OR(a,b) = 0 → a=0, b=0
    OR(a,b) = 1, a=0 → b=1
    NOT(a) = v → a=1-v

  Multi-pass: forward+backward до стабилизации.
  Определённые входные биты → уменьшенный DFS.
"""
import random, math, sys

def propagate_bidirectional(gates, n, fixed, known_outputs=None):
    """Forward + backward propagation до стабилизации.
    known_outputs: dict {wire_id: value} — известные значения выходов.
    """
    wire = dict(fixed)
    if known_outputs:
        wire.update(known_outputs)

    for iteration in range(20):
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
            if nv is not None: wire[out] = nv; changed = True

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
                    if i2 >= 0 and v2 == 1 and i1 not in wire:
                        wire[i1] = 0; changed = True
            elif gtype == 'OR':
                if ov == 0:
                    if i1 not in wire: wire[i1] = 0; changed = True
                    if i2 >= 0 and i2 not in wire: wire[i2] = 0; changed = True
                elif ov == 1:
                    v1 = wire.get(i1); v2 = wire.get(i2) if i2 >= 0 else None
                    if v1 == 0 and i2 >= 0 and i2 not in wire:
                        wire[i2] = 1; changed = True
                    if i2 >= 0 and v2 == 0 and i1 not in wire:
                        wire[i1] = 1; changed = True
            elif gtype == 'NOT':
                if ov is not None and i1 not in wire:
                    wire[i1] = 1 - ov; changed = True
                elif wire.get(i1) is not None and out not in wire:
                    wire[out] = 1 - wire[i1]; changed = True

        if not changed: break

    return wire


def propagate_forward(gates, fixed):
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


def backward_preimage(hash_gates, nbits, hash_wires, target, max_nodes=5000000):
    """Preimage через backward propagation + DFS на оставшихся битах.

    Шаг 1: Устанавливаем hash_wires = target.
    Шаг 2: Backward propagation → определяем часть входных бит.
    Шаг 3: DFS только по неопределённым входным битам.
    """
    # Шаг 1-2: backward от target
    known = {hash_wires[i]: target[i] for i in range(len(target))}
    wire = propagate_bidirectional(hash_gates, nbits, {}, known)

    # Какие входные биты определены?
    determined_inputs = {}
    free_inputs = []
    for i in range(nbits):
        if i in wire:
            determined_inputs[i] = wire[i]
        else:
            free_inputs.append(i)

    n_det = len(determined_inputs)
    n_free = len(free_inputs)

    # Шаг 3: DFS по свободным битам
    nodes = [0]; result = [None]
    def dfs(idx, fixed):
        nodes[0] += 1
        if nodes[0] > max_nodes: return
        # Forward propagation с текущими фиксациями
        w = propagate_forward(hash_gates, fixed)
        # Проверяем: все хеш-биты совпадают?
        all_match = True; any_mismatch = False
        for i, hw in enumerate(hash_wires):
            val = w.get(hw)
            if val is not None and val != target[i]:
                any_mismatch = True; break
            if val is None:
                all_match = False
        if any_mismatch: return  # prune
        if all_match:
            result[0] = dict(fixed); return  # found!
        if idx >= len(free_inputs): return
        var = free_inputs[idx]
        fixed[var] = 0; dfs(idx+1, fixed)
        if result[0] or nodes[0] > max_nodes: return
        fixed[var] = 1; dfs(idx+1, fixed)
        if result[0]: return
        del fixed[var]

    dfs(0, dict(determined_inputs))
    return result[0], nodes[0], n_det, n_free


def forward_only_preimage(hash_gates, nbits, hash_wires, target, max_nodes=5000000):
    """Preimage БЕЗ backward — только forward propagation."""
    nodes = [0]; result = [None]
    def dfs(d, fixed):
        nodes[0] += 1
        if nodes[0] > max_nodes: return
        w = propagate_forward(hash_gates, fixed)
        all_match = True; any_mismatch = False
        for i, hw in enumerate(hash_wires):
            val = w.get(hw)
            if val is not None and val != target[i]:
                any_mismatch = True; break
            if val is None: all_match = False
        if any_mismatch: return
        if all_match: result[0] = dict(fixed); return
        if d >= nbits: return
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
    print("  BACKWARD PREIMAGE: определяем входы из target")
    print("=" * 72)

    # =========================================================
    # ТЕСТ 1: Сколько входных бит backward определяет?
    # =========================================================
    print()
    print("  ТЕСТ 1: Backward determination — входные биты")
    print()
    print(f"  {'n':>3} {'h':>3} {'det avg':>8} {'free avg':>9} "
          f"{'det%':>6} {'n_free':>7}")
    print(f"  {'-'*40}")

    for nbits in [8, 10, 12, 14, 16, 20]:
        for hbits in [4, 8, min(12, nbits)]:
            if hbits > nbits: continue
            hash_g, n, hw = build_hash(nbits, hbits, 3)
            det_list = []; free_list = []
            for _ in range(20):
                x = {i: random.randint(0,1) for i in range(nbits)}
                w = propagate_forward(hash_g, x)
                target = tuple(w.get(h) for h in hw)
                if None in target: continue
                _, _, nd, nf = backward_preimage(hash_g, nbits, hw, target, 1)
                det_list.append(nd); free_list.append(nf)
            if det_list:
                ad = sum(det_list)/len(det_list)
                af = sum(free_list)/len(free_list)
                print(f"  {nbits:3d} {hbits:3d} {ad:8.1f} {af:9.1f} "
                      f"{100*ad/nbits:5.1f}% {af:7.1f}")
            sys.stdout.flush()

    # =========================================================
    # ТЕСТ 2: Forward-only vs Backward preimage DFS
    # =========================================================
    print()
    print("  ТЕСТ 2: Forward-only vs Backward preimage (DFS nodes)")
    print()
    print(f"  {'n':>3} {'h':>3} {'forward':>8} {'backward':>9} "
          f"{'speedup':>8} {'free':>5}")
    print(f"  {'-'*38}")

    for nbits in [10, 12, 14, 16, 18, 20]:
        for hbits in [4, 8, min(12, nbits)]:
            if hbits > nbits: continue
            hash_g, n, hw = build_hash(nbits, hbits, 3)
            fwd_list = []; bwd_list = []; free_avg = []
            for _ in range(10):
                x = {i: random.randint(0,1) for i in range(nbits)}
                w = propagate_forward(hash_g, x)
                target = tuple(w.get(h) for h in hw)
                if None in target: continue
                r1, n1 = forward_only_preimage(hash_g, nbits, hw, target, 2000000)
                r2, n2, nd, nf = backward_preimage(hash_g, nbits, hw, target, 2000000)
                if n1 < 2000000: fwd_list.append(n1)
                if n2 < 2000000: bwd_list.append(n2)
                free_avg.append(nf)
            if fwd_list and bwd_list:
                af = sum(fwd_list)/len(fwd_list)
                ab = sum(bwd_list)/len(bwd_list)
                sp = af / max(1, ab)
                fr = sum(free_avg)/len(free_avg)
                print(f"  {nbits:3d} {hbits:3d} {af:8.0f} {ab:9.0f} "
                      f"{sp:8.1f}x {fr:5.1f}")
            sys.stdout.flush()

    # =========================================================
    # ТЕСТ 3: Масштабирование backward preimage vs h
    # =========================================================
    print()
    print("  ТЕСТ 3: Backward preimage nodes vs h (n=16)")
    print()
    print(f"  {'h':>3} {'backward':>9} {'forward':>9} {'speedup':>8} "
          f"{'det':>4} {'free':>5} {'2^free':>7}")
    print(f"  {'-'*48}")

    nbits = 16
    for hbits in [4, 6, 8, 10, 12, 14, 16]:
        if hbits > nbits: continue
        hash_g, n, hw = build_hash(nbits, hbits, 3)
        fwd_l = []; bwd_l = []; det_l = []; free_l = []
        for _ in range(10):
            x = {i: random.randint(0,1) for i in range(nbits)}
            w = propagate_forward(hash_g, x)
            tgt = tuple(w.get(h) for h in hw)
            if None in tgt: continue
            _, nf = forward_only_preimage(hash_g, nbits, hw, tgt, 2000000)
            _, nb, nd, nfr = backward_preimage(hash_g, nbits, hw, tgt, 2000000)
            if nf < 2000000: fwd_l.append(nf)
            if nb < 2000000: bwd_l.append(nb)
            det_l.append(nd); free_l.append(nfr)
        if bwd_l:
            ab = sum(bwd_l)/len(bwd_l)
            af = sum(fwd_l)/len(fwd_l) if fwd_l else float('inf')
            sp = af / max(1, ab) if fwd_l else 0
            ad = sum(det_l)/len(det_l)
            afr = sum(free_l)/len(free_l)
            print(f"  {hbits:3d} {ab:9.0f} {af:9.0f} {sp:8.1f}x "
                  f"{ad:4.0f} {afr:5.0f} {2**afr:7.0f}")
        else:
            print(f"  {hbits:3d} {'timeout':>9}")
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 4: Rayon Birthday с backward preimage
    # =========================================================
    print()
    print("  ТЕСТ 4: Rayon Birthday + Backward (n=16)")
    print()

    def rayon_backward(hash_g, nbits, hw, K, max_total=5000000):
        hbits = len(hw)
        table = {}; p1 = 0
        while len(table) < K and p1 < max_total // 2:
            x = {i: random.randint(0,1) for i in range(nbits)}
            w = propagate_forward(hash_g, x)
            h = tuple(w.get(h_) for h_ in hw)
            p1 += 1
            if None in h: continue
            if h in table:
                prev = table[h]
                if any(x.get(i,0) != prev.get(i,0) for i in range(nbits)):
                    return p1, 0, True
            table[h] = dict(x)
        # Multi-target backward preimage
        p2_total = 0
        for target in table:
            _, p2, _, _ = backward_preimage(hash_g, nbits, hw, target,
                                             max_total - p1 - p2_total)
            p2_total += p2
            if p2_total + p1 > max_total: break
        # Check if any new preimage collides
        # (simplified: just return cost)
        return p1, p2_total, False  # simplified

    print(f"  {'h':>3} {'K':>4} {'p1':>6} {'p2':>8} {'total':>8} "
          f"{'birthday':>9}")
    print(f"  {'-'*42}")

    nbits = 16
    for hbits in [4, 6, 8, 10, 12]:
        K = max(2, int(2**(hbits/4)))
        hash_g, n, hw = build_hash(nbits, hbits, 3)
        random.seed(42)
        p1, p2, found = rayon_backward(hash_g, nbits, hw, K, 5000000)

        # Standard birthday
        random.seed(42)
        table = {}; be = 0
        for _ in range(500000):
            x = {i: random.randint(0,1) for i in range(nbits)}
            w = propagate_forward(hash_g, x)
            h = tuple(w.get(h_) for h_ in hw)
            be += 1
            if None in h: continue
            if h in table:
                if any(x.get(i,0) != table[h].get(i,0) for i in range(nbits)):
                    break
            table[h] = dict(x)

        print(f"  {hbits:3d} {K:4d} {p1:6d} {p2:8d} {p1+p2:8d} {be:9d}")
        sys.stdout.flush()

    # =========================================================
    # ИТОГ
    # =========================================================
    print()
    print("=" * 72)
    print("  ИТОГ: BACKWARD PREIMAGE")
    print("=" * 72)

if __name__ == "__main__":
    main()
