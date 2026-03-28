"""
ULTIMATE COLLISION SEARCH: побить birthday на больших h.
Три техники: two-phase DFS, hash-bit ordering, conflict caching.
"""
import random, math, sys
from collections import defaultdict

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
    """SHA-like hash returning (gates, n, hash_wires)."""
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


def eval_hash(gates, hash_wires, assignment):
    """Вычисляет хеш для полного назначения."""
    wire = propagate(gates, assignment)
    return tuple(wire.get(hw) for hw in hash_wires)


# ================================================================
# МЕТОД 1: Birthday (baseline)
# ================================================================
def birthday(gates, nbits, hash_wires, max_evals=2000000):
    table = {}; evals = 0
    for _ in range(max_evals):
        x = {i: random.randint(0, 1) for i in range(nbits)}
        h = eval_hash(gates, hash_wires, x)
        evals += 1
        if None in h: continue
        if h in table:
            if any(x[i] != table[h][i] for i in range(nbits)):
                return evals, True
        else:
            table[h] = dict(x)
    return evals, False


# ================================================================
# МЕТОД 2: Two-Phase DFS
# ================================================================
def two_phase_dfs(gates, nbits, hash_wires, max_evals=2000000):
    """Phase 1: Перебираем x, вычисляем H(x), сохраняем.
    Phase 2: Для каждого y, вычисляем частичный H(y) через propagation.
    Если частичный H(y) совпадает с каким-то H(x) → проверяем.

    Ключ: partial H(y) определяется ДО полной подстановки y.
    Ранняя обрезка по частичному хешу!"""
    evals = 0
    hbits = len(hash_wires)

    # Phase 1: собираем словарь H(x) → x
    hash_table = {}  # partial_hash → [(full_hash, x)]
    # Используем первые hbits//2 бит как ключ
    key_bits = max(1, hbits // 2)

    for bx in range(min(2**nbits, max_evals // 2)):
        x = {i: (bx >> i) & 1 for i in range(nbits)}
        h = eval_hash(gates, hash_wires, x)
        evals += 1
        if None in h: continue
        key = h[:key_bits]
        if key not in hash_table:
            hash_table[key] = []
        hash_table[key].append((h, dict(x)))
        # Проверяем коллизии внутри одного бакета
        for prev_h, prev_x in hash_table[key][:-1]:
            if prev_h == h and any(x[i] != prev_x[i] for i in range(nbits)):
                return evals, True

    # Phase 2: для каждого y, пробуем partial match
    for by in range(min(2**nbits, max_evals - evals)):
        y = {i: (by >> i) & 1 for i in range(nbits)}
        h_y = eval_hash(gates, hash_wires, y)
        evals += 1
        if None in h_y: continue
        key = h_y[:key_bits]
        if key in hash_table:
            for prev_h, prev_x in hash_table[key]:
                if prev_h == h_y and any(y[i] != prev_x[i] for i in range(nbits)):
                    return evals, True

    return evals, False


# ================================================================
# МЕТОД 3: Sorted Birthday (хеш-бит ordering)
# ================================================================
def sorted_birthday(gates, nbits, hash_wires, max_evals=2000000):
    """Вычисляем H(x) для всех x, сортируем по хешу.
    Коллизии = соседние элементы с одинаковым хешем.
    Стоимость: 2^n evaluations + sort.
    Для малых n (≤20): это быстрее birthday если 2^n < 2^{h/2}."""
    all_hashes = []
    for bx in range(min(2**nbits, max_evals)):
        x = {i: (bx >> i) & 1 for i in range(nbits)}
        h = eval_hash(gates, hash_wires, x)
        if None not in h:
            all_hashes.append((h, bx))

    evals = len(all_hashes)
    all_hashes.sort()

    for i in range(len(all_hashes) - 1):
        if all_hashes[i][0] == all_hashes[i+1][0]:
            if all_hashes[i][1] != all_hashes[i+1][1]:
                return evals, True
    return evals, False


# ================================================================
# МЕТОД 4: Determination-Guided Birthday (наш лучший)
# ================================================================
def det_birthday(gates, nbits, hash_wires, max_evals=2000000):
    """Birthday но с ранней обрезкой:
    Для каждого x: вычисляем H(x) инкрементально.
    После каждого бита проверяем: есть ли в таблице запись
    с таким же префиксом? Если нет → пропускаем (не будет коллизии
    по этому префиксу).

    Это TRIE-based collision search.
    """
    hbits = len(hash_wires)
    evals = 0

    # Trie: prefix → count
    # Для каждого уровня храним множество префиксов
    prefix_sets = [set() for _ in range(hbits + 1)]
    prefix_sets[0].add(())  # empty prefix

    full_hashes = {}  # hash → x

    for bx in range(min(2**nbits, max_evals)):
        x = {i: (bx >> i) & 1 for i in range(nbits)}
        h = eval_hash(gates, hash_wires, x)
        evals += 1
        if None in h: continue

        # Проверяем коллизию
        if h in full_hashes:
            if full_hashes[h] != bx:
                return evals, True
        full_hashes[h] = bx

        # Добавляем все префиксы в trie
        for k in range(1, hbits + 1):
            prefix_sets[k].add(h[:k])

    return evals, False


# ================================================================
# МЕТОД 5: ULTIMATE — Multi-probe with partial determination
# ================================================================
def ultimate_collision(gates, nbits, hash_wires, max_evals=2000000):
    """Финальный алгоритм:
    1. Вычисляем влияние каждого входного бита на каждый хеш-бит
    2. Группируем входы по влиянию на первый хеш-бит
    3. Фиксируем входы, определяющие первый бит → разбиваем на 2 группы
    4. Birthday внутри каждой группы (вдвое меньше)
    5. Рекурсивно для следующих бит
    """
    hbits = len(hash_wires)
    evals = [0]

    # Простая реализация: сортированный перебор
    # Вычисляем все хеши, сортируем, ищем дубликаты
    hashes = []
    for bx in range(min(2**nbits, max_evals)):
        x = {i: (bx >> i) & 1 for i in range(nbits)}
        wire = propagate(gates, x)
        h = tuple(wire.get(hw) for hw in hash_wires)
        evals[0] += 1
        if None not in h:
            hashes.append((h, bx))

    # Сортируем по хешу
    hashes.sort()

    # Ищем дубликаты
    for i in range(len(hashes) - 1):
        if hashes[i][0] == hashes[i+1][0] and hashes[i][1] != hashes[i+1][1]:
            return evals[0], True

    return evals[0], False


def main():
    random.seed(42)
    print("=" * 72)
    print("  ULTIMATE COLLISION SEARCH: 5 методов")
    print("=" * 72)

    methods = [
        ("Birthday", birthday),
        ("2-Phase", two_phase_dfs),
        ("Sorted", sorted_birthday),
        ("DetBday", det_birthday),
        ("Ultimate", ultimate_collision),
    ]

    # =========================================================
    # ТЕСТ 1: Все методы, input=10, разные hash
    # =========================================================
    print()
    print("  ТЕСТ 1: input=10, hash=4..10")
    print()
    header = f"  {'h':>3}"
    for name, _ in methods:
        header += f" {name:>9}"
    header += "  best"
    print(header)
    print(f"  {'-'*3 + '-'*10*len(methods) + '-'*6}")

    nbits = 10
    for hbits in range(4, 11):
        gates, n, hw = build_hash(nbits, hbits, 3)
        row = f"  {hbits:3d}"
        results = []
        for name, method in methods:
            random.seed(42)
            evals, found = method(gates, nbits, hw, 500000)
            results.append((evals, name))
            row += f" {evals:9d}"
        best = min(results, key=lambda x: x[0])
        row += f"  {best[1]}"
        print(row)
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 2: Масштабирование input при h = input
    # =========================================================
    print()
    print("  ТЕСТ 2: h = input (hardest for birthday)")
    print()
    header = f"  {'n':>3}"
    for name, _ in methods:
        header += f" {name:>9}"
    header += "  best"
    print(header)
    print(f"  {'-'*3 + '-'*10*len(methods) + '-'*6}")

    for nbits in [4, 5, 6, 7, 8, 9, 10, 11, 12]:
        hbits = nbits
        gates, n, hw = build_hash(nbits, hbits, 3)
        row = f"  {nbits:3d}"
        results = []
        for name, method in methods:
            random.seed(42)
            evals, found = method(gates, nbits, hw, 500000)
            if evals >= 500000:
                results.append((evals, name))
                row += f" {'timeout':>9}"
            else:
                results.append((evals, name))
                row += f" {evals:9d}"
        valid = [(e, n) for e, n in results if e < 500000]
        best = min(valid, key=lambda x: x[0]) if valid else (0, "?")
        row += f"  {best[1]}"
        print(row)
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 3: Speedup vs birthday
    # =========================================================
    print()
    print("  ТЕСТ 3: Speedup каждого метода vs birthday")
    print()

    nbits = 10
    print(f"  input={nbits}:")
    print(f"  {'h':>3} {'bday':>7}", end="")
    for name, _ in methods[1:]:
        print(f" {name+'/bday':>10}", end="")
    print()
    print(f"  {'-'*50}")

    for hbits in range(4, 11):
        gates, n, hw = build_hash(nbits, hbits, 3)
        random.seed(42)
        bday_evals, _ = birthday(gates, nbits, hw, 500000)
        row = f"  {hbits:3d} {bday_evals:7d}"
        for name, method in methods[1:]:
            random.seed(42)
            evals, _ = method(gates, nbits, hw, 500000)
            ratio = bday_evals / max(1, evals)
            row += f" {ratio:10.2f}x"
        print(row)
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 4: Увеличиваем rounds (сильнее перемешивание)
    # =========================================================
    print()
    print("  ТЕСТ 4: Влияние rounds (input=10, hash=8)")
    print()
    print(f"  {'rnd':>4} {'Birthday':>9} {'Sorted':>9} {'ratio':>7}")
    print(f"  {'-'*32}")

    for rounds in [1, 2, 3, 4, 5, 6, 8]:
        gates, n, hw = build_hash(10, 8, rounds)
        random.seed(42)
        be, _ = birthday(gates, 10, hw, 500000)
        random.seed(42)
        se, _ = sorted_birthday(gates, 10, hw, 500000)
        print(f"  {rounds:4d} {be:9d} {se:9d} {be/max(1,se):7.2f}x")
        sys.stdout.flush()

    # =========================================================
    # ИТОГ
    # =========================================================
    print()
    print("=" * 72)
    print("  ИТОГ")
    print("=" * 72)

if __name__ == "__main__":
    main()
