"""
ПУТЬ А: NEXP-схемы не содержат XOR.
Cook-Levin кодирует TM через AND/OR/NOT.
Проверяем: можно ли ЛЮБУЮ TM закодировать без XOR-паттернов
так что constant propagation даёт Pr → 1?
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

def measure(gates, n, k, trials=2000):
    det = 0
    for _ in range(trials):
        s = random.randint(0, n-1)
        vs = [(s+i)%n for i in range(min(k,n))]
        fixed = {v: random.randint(0,1) for v in vs}
        if propagate(gates, fixed) is not None: det += 1
    return det / trials

# ================================================================
# Cook-Levin: кодирование ПРОИЗВОЛЬНОЙ TM
# ================================================================
# TM с q состояниями, Γ символов ленты.
# Конфигурация: (state, head_pos, tape).
# Кодируем в битах: state = ceil(log2(q)) бит, каждая ячейка = ceil(log2(Γ)) бит.
#
# Переходная функция δ(state, symbol) = (new_state, new_symbol, direction).
# Кодирование через AND/OR/NOT:
#   Для каждого (s, σ): "если state=s И symbol=σ → ..."
#   Это IF-THEN = AND(state_decoder, symbol_decoder) → new_state_encoder
#
# Каждый IF-THEN имеет контролирующие значения!
# state ≠ s → decoder = 0 → AND = 0 → не влияет.
# Это ЧИСТАЯ AND/OR структура без XOR.

def build_cook_levin_tm(n_tape, steps, num_states=4, num_symbols=2):
    """Схема Cook-Levin для TM с num_states состояниями.
    Входы: начальная лента (n_tape бит).
    Кодирование: каждая ячейка = 1 бит (бинарный алфавит).
    Состояние = ceil(log2(num_states)) бит, one-hot кодировка для простоты.
    """
    gates = []; nid = n_tape

    # Начальное состояние: state[0] = q0 (one-hot)
    # state_bits[t][q] = провод: "на шаге t состояние = q"
    # Начальный state: q0 = 1, остальные = 0
    state_bits = {}
    for q in range(num_states):
        state_bits[(0, q)] = nid
        if q == 0:
            # Создаём константу 1: OR(x0, NOT x0)
            not_x0 = nid; gates.append(('NOT', 0, -1, not_x0)); nid += 1
            const1 = nid; gates.append(('OR', 0, not_x0, const1)); nid += 1
            state_bits[(0, 0)] = const1
        else:
            # Константа 0: AND(x0, NOT x0)
            not_x0_id = nid; gates.append(('NOT', 0, -1, not_x0_id)); nid += 1
            const0 = nid; gates.append(('AND', 0, not_x0_id, const0)); nid += 1
            state_bits[(0, q)] = const0

    # Начальная позиция головки: pos = 0 (one-hot)
    head_bits = {}
    for p in range(n_tape):
        head_bits[(0, p)] = nid
        if p == 0:
            not_x0 = nid; gates.append(('NOT', 0, -1, not_x0)); nid += 1
            c1 = nid; gates.append(('OR', 0, not_x0, c1)); nid += 1
            head_bits[(0, 0)] = c1
        else:
            not_x0 = nid; gates.append(('NOT', 0, -1, not_x0)); nid += 1
            c0 = nid; gates.append(('AND', 0, not_x0, c0)); nid += 1
            head_bits[(0, p)] = c0

    # Начальная лента: tape[0][i] = input[i]
    tape_bits = {}
    for i in range(n_tape):
        tape_bits[(0, i)] = i  # входные переменные

    # Случайная переходная функция
    random.seed(123)  # фиксированный seed для воспроизводимости
    delta = {}  # delta[(state, symbol)] = (new_state, new_symbol, direction)
    for q in range(num_states - 1):  # последнее состояние = accept
        for s in range(num_symbols):
            nq = random.randint(0, num_states - 1)
            ns = random.randint(0, num_symbols - 1)
            d = random.choice([-1, 1])  # left/right
            delta[(q, s)] = (nq, ns, d)

    accept_state = num_states - 1

    # Шаги вычисления
    for t in range(steps):
        # Для каждого перехода (q, σ) → (q', σ', d):
        # guard[q][σ] = state_bits[t][q] AND head_at_pos AND tape[pos] = σ

        # Новое состояние, лента, головка
        # new_state[q'] = OR over all (q,σ) mapping to q'
        # new_tape[i][s'] = tape[i] if head ≠ i, else new_symbol
        # new_head[p'] = head[p ± d]

        new_state_contribs = {q: [] for q in range(num_states)}
        new_tape_contribs = {i: {'keep': [], 'write0': [], 'write1': []}
                             for i in range(n_tape)}
        new_head_contribs = {p: [] for p in range(n_tape)}

        for q in range(num_states - 1):
            for sigma in range(num_symbols):
                if (q, sigma) not in delta:
                    continue
                nq, ns, d = delta[(q, sigma)]

                for pos in range(n_tape):
                    # guard = state=q AND head=pos AND tape[pos]=sigma
                    sq = state_bits[(t, q)]
                    hp = head_bits[(t, pos)]
                    tp = tape_bits[(t, pos)]

                    g1 = nid; gates.append(('AND', sq, hp, g1)); nid += 1

                    if sigma == 1:
                        g2 = nid; gates.append(('AND', g1, tp, g2)); nid += 1
                    else:
                        not_tp = nid; gates.append(('NOT', tp, -1, not_tp)); nid += 1
                        g2 = nid; gates.append(('AND', g1, not_tp, g2)); nid += 1

                    # guard = g2
                    new_state_contribs[nq].append(g2)

                    new_pos = (pos + d) % n_tape
                    new_head_contribs[new_pos].append(g2)

                    if ns == 1:
                        new_tape_contribs[pos]['write1'].append(g2)
                    else:
                        new_tape_contribs[pos]['write0'].append(g2)

                    # Для всех других позиций: лента не меняется
                    for other in range(n_tape):
                        if other != pos:
                            new_tape_contribs[other]['keep'].append(g2)

        # Собираем новое состояние
        for q in range(num_states):
            contribs = new_state_contribs[q]
            if not contribs:
                # Никогда не достигается: 0
                not_x0 = nid; gates.append(('NOT', 0, -1, not_x0)); nid += 1
                c0 = nid; gates.append(('AND', 0, not_x0, c0)); nid += 1
                state_bits[(t+1, q)] = c0
            elif len(contribs) == 1:
                state_bits[(t+1, q)] = contribs[0]
            else:
                cur = contribs[0]
                for c in contribs[1:]:
                    r = nid; gates.append(('OR', cur, c, r)); nid += 1; cur = r
                state_bits[(t+1, q)] = cur

        # Головка (упрощённо)
        for p in range(n_tape):
            contribs = new_head_contribs[p]
            if not contribs:
                not_x0 = nid; gates.append(('NOT', 0, -1, not_x0)); nid += 1
                c0 = nid; gates.append(('AND', 0, not_x0, c0)); nid += 1
                head_bits[(t+1, p)] = c0
            elif len(contribs) == 1:
                head_bits[(t+1, p)] = contribs[0]
            else:
                cur = contribs[0]
                for c in contribs[1:]:
                    r = nid; gates.append(('OR', cur, c, r)); nid += 1; cur = r
                head_bits[(t+1, p)] = cur

        # Лента (упрощённо: tape[t+1][i] = OR(write1 guards) OR (tape[t][i] AND NOT(any_write guard)))
        for i in range(n_tape):
            w1 = new_tape_contribs[i]['write1']
            w0 = new_tape_contribs[i]['write0']

            # any_write = OR(all write guards for position i)
            all_writes = w1 + w0
            if all_writes:
                cur_aw = all_writes[0]
                for w in all_writes[1:]:
                    r = nid; gates.append(('OR', cur_aw, w, r)); nid += 1; cur_aw = r
                any_write = cur_aw

                # keep = tape[t][i] AND NOT(any_write)
                naw = nid; gates.append(('NOT', any_write, -1, naw)); nid += 1
                keep = nid; gates.append(('AND', tape_bits[(t, i)], naw, keep)); nid += 1

                # write1 = OR of w1 guards
                if w1:
                    cur_w1 = w1[0]
                    for w in w1[1:]:
                        r = nid; gates.append(('OR', cur_w1, w, r)); nid += 1; cur_w1 = r
                    # new tape = OR(keep, write1)
                    result = nid; gates.append(('OR', keep, cur_w1, result)); nid += 1
                else:
                    result = keep
            else:
                result = tape_bits[(t, i)]

            tape_bits[(t+1, i)] = result

    # Acceptance: state = accept_state в любом шаге
    accept_wires = []
    for t in range(steps + 1):
        accept_wires.append(state_bits[(t, accept_state)])

    cur = accept_wires[0]
    for a in accept_wires[1:]:
        r = nid; gates.append(('OR', cur, a, r)); nid += 1; cur = r

    return gates, n_tape


def main():
    random.seed(42)
    print("=" * 60)
    print("  ПУТЬ А: Cook-Levin TM (чистый AND/OR/NOT)")
    print("  Вопрос: Pr → 1 для РЕАЛЬНОЙ TM-симуляции?")
    print("=" * 60)

    print()
    print("  Схема Cook-Levin: state one-hot, head one-hot")
    print("  Acceptance = OR(state=accept на любом шаге)")
    print()

    print(f"  {'n':>4} {'steps':>6} {'gates':>7} {'Pr cons':>8} {'Pr rand':>8}")
    print(f"  {'-'*38}")

    for n in [6, 8, 10, 12, 15]:
        for steps in [3, min(n, 8)]:
            try:
                gates, nv = build_cook_levin_tm(n, steps, num_states=4)
                pc = measure(gates, nv, nv//2, 2000)
                pr = measure(gates, nv, nv//2, 1000)
                print(f"  {n:4d} {steps:6d} {len(gates):7d} {pc:8.4f} {pr:8.4f}")
            except Exception as e:
                print(f"  {n:4d} {steps:6d} {'ERR':>7} {str(e)[:30]}")
            sys.stdout.flush()

    # Масштабирование
    print()
    print("  Масштабирование (steps=5, 4 states):")
    print(f"  {'n':>4} {'Pr[det]':>8} {'тренд':>6}")
    print(f"  {'-'*20}")
    prev = None
    for n in [6, 8, 10, 12, 15, 18]:
        try:
            gates, nv = build_cook_levin_tm(n, 5, num_states=4)
            pr = measure(gates, nv, nv//2, 2000)
            trend = ""
            if prev is not None:
                trend = "↑" if pr > prev + 0.01 else ("↓" if pr < prev - 0.01 else "≈")
            prev = pr
            print(f"  {n:4d} {pr:8.4f} {trend:>6}")
        except Exception as e:
            print(f"  {n:4d} {'ERR':>8}")
        sys.stdout.flush()

    print()
    print("  ВЫВОД: Cook-Levin кодирование — чистый AND/OR/NOT.")
    print("  Нет XOR → constant propagation должна работать.")


if __name__ == "__main__":
    main()
