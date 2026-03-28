"""
Вариант 2: Unit propagation (как в SAT-solver'ах).
Constant propagation: знаем значение → подставляем.
Unit propagation: если в OR(a,b,...) все кроме одного = 0 → последний = 1.
Это МОЩНЕЕ constant propagation.
"""
import random, math, sys

def propagate_constant(gates, fixed):
    """Стандартная constant propagation."""
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


def propagate_unit(gates, n, fixed):
    """Unit propagation: итеративно.
    1. Constant propagation (вперёд)
    2. Если гейт AND(a,b) = 1 → a=1, b=1 (обратно)
    3. Если OR(a,b) = 0 → a=0, b=0 (обратно)
    4. Если AND(a,b) и a=1 и out=0 → b=0 (обратно)
    5. Если OR(a,b) и a=0 и out=1 → b=1 (обратно)
    Повторяем до стабилизации.
    """
    wire = dict(fixed)
    gate_by_out = {g[3]: g for g in gates}

    # Также нужен обратный индекс: для каждого провода, какие гейты его используют
    used_by = {}
    for g in gates:
        for inp in [g[1], g[2]]:
            if inp >= 0:
                if inp not in used_by:
                    used_by[inp] = []
                used_by[inp].append(g)

    changed = True
    iterations = 0
    max_iter = 10  # ограничиваем для скорости

    while changed and iterations < max_iter:
        changed = False
        iterations += 1

        # Forward pass
        for gtype, i1, i2, out in gates:
            if out in wire:
                continue
            v1 = wire.get(i1); v2 = wire.get(i2) if i2 >= 0 else None

            new_val = None
            if gtype == 'AND':
                if v1 == 0 or v2 == 0: new_val = 0
                elif v1 is not None and v2 is not None: new_val = v1 & v2
            elif gtype == 'OR':
                if v1 == 1 or v2 == 1: new_val = 1
                elif v1 is not None and v2 is not None: new_val = v1 | v2
            elif gtype == 'NOT':
                if v1 is not None: new_val = 1 - v1

            if new_val is not None:
                wire[out] = new_val
                changed = True

        # Backward pass
        for gtype, i1, i2, out in gates:
            out_val = wire.get(out)
            if out_val is None:
                continue

            if gtype == 'AND':
                if out_val == 1:
                    # AND = 1 → оба входа = 1
                    if i1 not in wire:
                        wire[i1] = 1; changed = True
                    if i2 >= 0 and i2 not in wire:
                        wire[i2] = 1; changed = True
                elif out_val == 0:
                    v1 = wire.get(i1); v2 = wire.get(i2) if i2 >= 0 else None
                    # AND = 0 и один вход = 1 → другой = 0
                    if v1 == 1 and i2 >= 0 and i2 not in wire:
                        wire[i2] = 0; changed = True
                    if v2 == 1 and i1 not in wire:
                        wire[i1] = 0; changed = True

            elif gtype == 'OR':
                if out_val == 0:
                    # OR = 0 → оба входа = 0
                    if i1 not in wire:
                        wire[i1] = 0; changed = True
                    if i2 >= 0 and i2 not in wire:
                        wire[i2] = 0; changed = True
                elif out_val == 1:
                    v1 = wire.get(i1); v2 = wire.get(i2) if i2 >= 0 else None
                    # OR = 1 и один = 0 → другой = 1
                    if v1 == 0 and i2 >= 0 and i2 not in wire:
                        wire[i2] = 1; changed = True
                    if v2 == 0 and i1 not in wire:
                        wire[i1] = 1; changed = True

            elif gtype == 'NOT':
                if out_val is not None and i1 not in wire:
                    wire[i1] = 1 - out_val; changed = True
                elif wire.get(i1) is not None and out not in wire:
                    wire[out] = 1 - wire[i1]; changed = True

    return wire


def build_tm(n, steps):
    """Rule 202 TM + OR(final)."""
    gates = []; nid = n; prev = list(range(n))
    for t in range(steps):
        new = []
        for i in range(n):
            L,C,R = prev[(i-1)%n], prev[i], prev[(i+1)%n]
            ab = nid; gates.append(('AND', L, C, ab)); nid += 1
            bc = nid; gates.append(('AND', C, R, bc)); nid += 1
            nl = nid; gates.append(('NOT', L, -1, nl)); nid += 1
            nac = nid; gates.append(('AND', nl, R, nac)); nid += 1
            t1 = nid; gates.append(('OR', ab, bc, t1)); nid += 1
            r = nid; gates.append(('OR', t1, nac, r)); nid += 1
            new.append(r)
        prev = new
    cur = prev[0]
    for p in prev[1:]:
        gates.append(('OR', cur, p, nid)); cur = nid; nid += 1
    return gates, n


def build_cook_levin_compact(n, steps):
    """Компактная Cook-Levin TM."""
    gates = []; nid = n; prev = list(range(n))
    active = []
    for i in range(n):
        if i == 0:
            nt = nid; gates.append(('NOT', 0, -1, nt)); nid += 1
            c = nid; gates.append(('OR', 0, nt, c)); nid += 1
            active.append(c)
        else:
            nt = nid; gates.append(('NOT', 0, -1, nt)); nid += 1
            c = nid; gates.append(('AND', 0, nt, c)); nid += 1
            active.append(c)

    random.seed(77)
    tr = {0: (1, 1), 1: (0, 0)}  # простое правило

    for t in range(steps):
        new_data = []; new_active = []
        for i in range(n):
            # MUX: new_data = active ? f(data) : data
            not_a = nid; gates.append(('NOT', active[i], -1, not_a)); nid += 1
            not_d = nid; gates.append(('NOT', prev[i], -1, not_d)); nid += 1
            # f(data): если tr[0][0]==1 и tr[1][0]==0 → f = NOT data
            # tr[0]=(1,1), tr[1]=(0,0) → f(0)=1, f(1)=0 → f = NOT data
            t1 = nid; gates.append(('AND', active[i], not_d, t1)); nid += 1
            t2 = nid; gates.append(('AND', not_a, prev[i], t2)); nid += 1
            nd = nid; gates.append(('OR', t1, t2, nd)); nid += 1
            new_data.append(nd)

            # Active moves: right when data=0, left when data=1
            contribs = []
            # from left (j=i-1): needs dir=right(1) → data[j]=0 → tr[0][1]=1 ✓
            j = (i-1) % n
            nd_j = nid; gates.append(('NOT', prev[j], -1, nd_j)); nid += 1
            c = nid; gates.append(('AND', active[j], nd_j, c)); nid += 1
            contribs.append(c)
            # from right (j=i+1): needs dir=left(0) → data[j]=1 → tr[1][1]=0 ✓
            j = (i+1) % n
            c = nid; gates.append(('AND', active[j], prev[j], c)); nid += 1
            contribs.append(c)

            cur = contribs[0]
            for cc in contribs[1:]:
                r = nid; gates.append(('OR', cur, cc, r)); nid += 1; cur = r
            new_active.append(cur)

        prev = new_data; active = new_active

    # Accept: OR(AND(active[i], data[i]))
    terms = []
    for i in range(n):
        t = nid; gates.append(('AND', active[i], prev[i], t)); nid += 1
        terms.append(t)
    cur = terms[0]
    for tt in terms[1:]:
        r = nid; gates.append(('OR', cur, tt, r)); nid += 1; cur = r
    return gates, n


def measure_both(gates, n, k, trials=2000):
    det_c = 0; det_u = 0
    for _ in range(trials):
        s = random.randint(0, n-1)
        vs = [(s+i)%n for i in range(min(k,n))]
        fixed = {v: random.randint(0,1) for v in vs}

        wc = propagate_constant(gates, fixed)
        out_c = wc.get(gates[-1][3])
        if out_c is not None: det_c += 1

        wu = propagate_unit(gates, n, fixed)
        out_u = wu.get(gates[-1][3])
        if out_u is not None: det_u += 1

    return det_c / trials, det_u / trials


def main():
    random.seed(42)
    print("=" * 60)
    print("  Вариант 2: Unit propagation vs Constant propagation")
    print("=" * 60)

    # Тест 1: Rule202 TM
    print(f"\n  Rule202 TM + OR(final), consecutive:")
    print(f"  {'n':>4} {'const':>8} {'unit':>8} {'улучш':>8}")
    print(f"  {'-'*30}")
    for n in [8, 10, 15, 20, 25, 30]:
        g, nv = build_tm(n, n)
        pc, pu = measure_both(g, nv, nv//2, 2000)
        improv = pu - pc
        print(f"  {n:4d} {pc:8.4f} {pu:8.4f} {improv:+8.4f}")
        sys.stdout.flush()

    # Тест 2: Compact Cook-Levin
    print(f"\n  Compact Cook-Levin TM, consecutive:")
    print(f"  {'n':>4} {'const':>8} {'unit':>8} {'улучш':>8}")
    print(f"  {'-'*30}")
    for n in [6, 8, 10, 12, 15, 20, 25]:
        g, nv = build_cook_levin_compact(n, min(n, 10))
        pc, pu = measure_both(g, nv, nv//2, 1500)
        improv = pu - pc
        print(f"  {n:4d} {pc:8.4f} {pu:8.4f} {improv:+8.4f}")
        sys.stdout.flush()

    # Тест 3: XOR chain (помогает ли unit?)
    print(f"\n  XOR chain:")
    print(f"  {'n':>4} {'const':>8} {'unit':>8}")
    print(f"  {'-'*22}")
    for n in [6, 8, 10]:
        gates = []; nid = n; cur = 0
        for i in range(1, n):
            nc = nid; gates.append(('NOT', cur, -1, nc)); nid += 1
            nb = nid; gates.append(('NOT', i, -1, nb)); nid += 1
            t1 = nid; gates.append(('AND', cur, nb, t1)); nid += 1
            t2 = nid; gates.append(('AND', nc, i, t2)); nid += 1
            xor = nid; gates.append(('OR', t1, t2, xor)); nid += 1
            cur = xor
        pc, pu = measure_both(gates, n, n//2, 2000)
        print(f"  {n:4d} {pc:8.4f} {pu:8.4f}")
        sys.stdout.flush()

    # Тест 4: Масштабирование unit на Cook-Levin
    print(f"\n  Cook-Levin + unit prop, масштабирование:")
    print(f"  {'n':>4} {'Pr unit':>8} {'тренд':>6}")
    print(f"  {'-'*20}")
    prev = None
    for n in [6, 8, 10, 12, 15, 20, 25, 30]:
        g, nv = build_cook_levin_compact(n, min(n, 10))
        _, pu = measure_both(g, nv, nv//2, 1500)
        trend = ""
        if prev is not None:
            trend = "↑" if pu > prev + 0.01 else ("↓" if pu < prev - 0.01 else "≈")
        prev = pu
        print(f"  {n:4d} {pu:8.4f} {trend:>6}")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
