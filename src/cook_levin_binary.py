"""
Вариант 1: Binary кодирование Cook-Levin (вместо one-hot).
One-hot: n_tape проводов на состояние → огромная схема.
Binary: log2(states) бит → компактнее, меньше guards.
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

def measure(gates, n, k, strategy='consecutive', trials=2000):
    det = 0
    for _ in range(trials):
        if strategy == 'consecutive':
            s = random.randint(0, n-1)
            vs = [(s+i)%n for i in range(min(k,n))]
        else:
            vs = random.sample(range(n), min(k,n))
        fixed = {v: random.randint(0,1) for v in vs}
        if propagate(gates, fixed) is not None: det += 1
    return det / trials


def build_compact_tm(n_tape, steps, num_states=4):
    """Компактная TM: binary state, NO head tracking.
    Упрощённая модель: каждая ячейка обновляется локально,
    state кодируется в самих ячейках (как в cellular automaton).

    Кодирование: 2 бита на ячейку (1 бит данные + 1 бит 'active').
    active[i]=1: головка на позиции i.
    Переход: активная ячейка смотрит на себя и соседей,
    вычисляет новое значение и перемещает active.

    Это эквивалентно TM, но кодируется компактнее.
    """
    # 2n входных переменных: data[0..n-1], active[0..n-1]
    # Но для простоты: входы = data[0..n-1], active[0]=1, остальные=0
    n_vars = n_tape  # только данные — входы
    gates = []
    nid = n_vars

    # Начальные data = входы
    data = list(range(n_vars))

    # Начальный active: active[0] = 1, остальные = 0
    active = []
    for i in range(n_tape):
        if i == 0:
            # Константа 1: x0 OR NOT x0
            not0 = nid; gates.append(('NOT', 0, -1, not0)); nid += 1
            c1 = nid; gates.append(('OR', 0, not0, c1)); nid += 1
            active.append(c1)
        else:
            not0 = nid; gates.append(('NOT', 0, -1, not0)); nid += 1
            c0 = nid; gates.append(('AND', 0, not0, c0)); nid += 1
            active.append(c0)

    # Случайная transition table (для детерминированности)
    random.seed(77)
    # transition[data_val] = (new_data, direction)
    # direction: 0=left, 1=right
    transitions = {}
    for d in range(2):
        transitions[d] = (random.randint(0, 1), random.randint(0, 1))

    for t in range(steps):
        new_data = []
        new_active = []

        for i in range(n_tape):
            # Если active[i] = 1: обновляем data[i] и перемещаем active
            # Если active[i] = 0: data[i] не меняется

            # new_data[i]:
            # = transition[data[i]].new_data  если active[i] = 1
            # = data[i]                       если active[i] = 0
            # = OR(AND(active[i], transition_result), AND(NOT active[i], data[i]))

            # transition_result когда data[i]=0: transitions[0][0]
            # transition_result когда data[i]=1: transitions[1][0]
            # = MUX(data[i], tr[1][0], tr[0][0])

            tr0_data, tr0_dir = transitions[0]
            tr1_data, tr1_dir = transitions[1]

            # MUX(sel, val_if_1, val_if_0) = OR(AND(sel, val_if_1), AND(NOT sel, val_if_0))
            not_d = nid; gates.append(('NOT', data[i], -1, not_d)); nid += 1

            if tr0_data == tr1_data:
                # Оба одинаковы: tr_result = const
                if tr0_data == 1:
                    not_x0 = nid; gates.append(('NOT', 0, -1, not_x0)); nid += 1
                    tr_result = nid; gates.append(('OR', 0, not_x0, tr_result)); nid += 1
                else:
                    not_x0 = nid; gates.append(('NOT', 0, -1, not_x0)); nid += 1
                    tr_result = nid; gates.append(('AND', 0, not_x0, tr_result)); nid += 1
            else:
                if tr1_data == 1:
                    tr_result = data[i]  # MUX(d, 1, 0) = d
                else:
                    tr_result = not_d  # MUX(d, 0, 1) = NOT d

            # new_data[i] = MUX(active[i], tr_result, data[i])
            not_a = nid; gates.append(('NOT', active[i], -1, not_a)); nid += 1
            t1 = nid; gates.append(('AND', active[i], tr_result, t1)); nid += 1
            t2 = nid; gates.append(('AND', not_a, data[i], t2)); nid += 1
            nd = nid; gates.append(('OR', t1, t2, nd)); nid += 1
            new_data.append(nd)

            # new_active[i]: active передвигается
            # active[i] становится 1 если сосед слева/справа был active
            # и направление указывало сюда
            # new_active[i] = OR over j ∈ neighbors: (active[j] AND direction_from_j_to_i)

            contribs = []
            for j in [i-1, i+1]:
                jj = j % n_tape
                # active[jj] хочет переместиться сюда?
                # direction зависит от data[jj]
                tr0_d, tr0_dir = transitions[0]
                tr1_d, tr1_dir = transitions[1]

                # dir_from_j = MUX(data[jj], tr1_dir, tr0_dir)
                if j == i - 1:  # сосед слева: нужен dir=right (1)
                    need_dir = 1
                else:  # сосед справа: нужен dir=left (0)
                    need_dir = 0

                if tr0_dir == need_dir and tr1_dir == need_dir:
                    # Всегда идёт сюда: contrib = active[jj]
                    contribs.append(active[jj])
                elif tr0_dir == need_dir and tr1_dir != need_dir:
                    # Идёт сюда когда data[jj]=0: AND(active[jj], NOT data[jj])
                    nd_jj = nid; gates.append(('NOT', data[jj], -1, nd_jj)); nid += 1
                    c = nid; gates.append(('AND', active[jj], nd_jj, c)); nid += 1
                    contribs.append(c)
                elif tr0_dir != need_dir and tr1_dir == need_dir:
                    # Идёт сюда когда data[jj]=1
                    c = nid; gates.append(('AND', active[jj], data[jj], c)); nid += 1
                    contribs.append(c)
                # else: никогда не идёт сюда

            if contribs:
                cur = contribs[0]
                for c in contribs[1:]:
                    r = nid; gates.append(('OR', cur, c, r)); nid += 1; cur = r
                new_active.append(cur)
            else:
                not_x0 = nid; gates.append(('NOT', 0, -1, not_x0)); nid += 1
                c0 = nid; gates.append(('AND', 0, not_x0, c0)); nid += 1
                new_active.append(c0)

        data = new_data
        active = new_active

    # Acceptance: OR(AND(active[i], data[i])) для всех i
    # "Головка на ячейке с данными = 1"
    acc_terms = []
    for i in range(n_tape):
        t = nid; gates.append(('AND', active[i], data[i], t)); nid += 1
        acc_terms.append(t)

    cur = acc_terms[0]
    for a in acc_terms[1:]:
        r = nid; gates.append(('OR', cur, a, r)); nid += 1; cur = r

    return gates, n_vars


def main():
    random.seed(42)
    print("=" * 60)
    print("  Вариант 1: Компактная TM (binary, NOT one-hot)")
    print("=" * 60)

    print(f"\n  {'n':>4} {'steps':>6} {'gates':>7} {'cons':>7} {'rand':>7}")
    print(f"  {'-'*34}")
    for n in [6, 8, 10, 12, 15, 20, 25, 30]:
        steps = min(n, 10)
        g, nv = build_compact_tm(n, steps)
        pc = measure(g, nv, nv//2, 'consecutive', 2000)
        pr = measure(g, nv, nv//2, 'random', 2000)
        print(f"  {n:4d} {steps:6d} {len(g):7d} {pc:7.4f} {pr:7.4f}")
        sys.stdout.flush()

    print(f"\n  Масштабирование (steps=n):")
    print(f"  {'n':>4} {'gates':>7} {'Pr cons':>8} {'тренд':>6}")
    print(f"  {'-'*28}")
    prev = None
    for n in [6, 8, 10, 12, 15, 20, 25, 30, 40]:
        steps = n
        g, nv = build_compact_tm(n, steps)
        pr = measure(g, nv, nv//2, 'consecutive', 2000)
        trend = ""
        if prev is not None:
            trend = "↑" if pr > prev + 0.01 else ("↓" if pr < prev - 0.01 else "≈")
        prev = pr
        print(f"  {n:4d} {len(g):7d} {pr:8.4f} {trend:>6}")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
