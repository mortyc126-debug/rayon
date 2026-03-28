"""
Meet-in-the-Middle + Determination Pruning.
Стандартный MITM: 2^{n/2} время, 2^{n/2} память.
Наш: на каждой половине DFS с pruning → меньше состояний.
"""
import random, math, sys, time

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


def propagate_out(gates, fixed):
    wire = propagate(gates, fixed)
    return wire.get(gates[-1][3]) if gates else None


# ================================================================
# 4 алгоритма
# ================================================================

def brute_force(gates, n):
    """Brute force: 2^n."""
    for bits in range(2**n):
        x = {i: (bits >> i) & 1 for i in range(n)}
        if propagate_out(gates, x) == 1:
            return bits, 2**n
    return None, 2**n


def dfs_pruning(gates, n, max_nodes=10**7):
    """DFS с constant propagation."""
    nodes = [0]; result = [None]
    def dfs(d, fixed):
        nodes[0] += 1
        if nodes[0] > max_nodes: return
        out = propagate_out(gates, fixed)
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


def mitm_standard(gates, n):
    """Meet-in-the-Middle стандартный.
    Фаза 1: для каждого назначения первых n/2 vars →
             запоминаем состояние (значения промежуточных гейтов).
    Фаза 2: для каждого назначения вторых n/2 vars →
             проверяем совместимость.

    Для Circuit-SAT: MITM сложнее чем для хеш-функций.
    Промежуточное состояние = значения гейтов, зависящих от обеих половин.

    Упрощённая версия: фиксируем n/2 vars, запоминаем выходы
    всех гейтов которые определены. Потом дополняем вторую половину.
    """
    half = n // 2
    # Фаза 1: перебираем первую половину
    states = {}  # hash(wire_state) → assignment
    phase1_count = 0
    for bits in range(2**half):
        fixed = {i: (bits >> i) & 1 for i in range(half)}
        wire = propagate(gates, fixed)
        out = wire.get(gates[-1][3]) if gates else None
        if out == 1:
            return fixed, 2**half  # Уже нашли!
        if out == 0:
            continue  # Обрезка!
        # Сохраняем значения определённых гейтов
        det_gates = frozenset((k, v) for k, v in wire.items() if k >= n)
        states[det_gates] = fixed
        phase1_count += 1

    # Фаза 2: перебираем вторую половину
    phase2_count = 0
    for bits in range(2**(n - half)):
        fixed2 = {half + i: (bits >> i) & 1 for i in range(n - half)}
        # Пробуем каждое совместимое состояние из фазы 1
        # (Упрощение: просто проверяем все)
        for det_state, fixed1 in states.items():
            full = {**fixed1, **fixed2}
            if propagate_out(gates, full) == 1:
                return full, phase1_count + phase2_count
            phase2_count += 1
            if phase1_count + phase2_count > 10**7:
                return None, phase1_count + phase2_count

    return None, phase1_count + phase2_count


def mitm_pruned(gates, n, max_states=10**7):
    """MITM + Determination Pruning.
    Фаза 1: DFS с pruning по первым n/2 переменным.
             Собираем ТОЛЬКО недетерминированные состояния.
    Фаза 2: Для каждого состояния — DFS с pruning по вторым n/2.
    """
    half = n // 2
    undetermined_states = []
    phase1_nodes = [0]

    # Фаза 1: DFS по первой половине с pruning
    def dfs1(d, fixed):
        phase1_nodes[0] += 1
        if phase1_nodes[0] > max_states: return
        out = propagate_out(gates, fixed)
        if out == 1:
            undetermined_states.append(('SAT', dict(fixed)))
            return
        if out == 0:
            return  # Pruned!
        if d >= half:
            # Не определён → сохраняем
            undetermined_states.append(('UNDET', dict(fixed)))
            return
        fixed[d] = 0; dfs1(d+1, fixed)
        if phase1_nodes[0] > max_states: return
        fixed[d] = 1; dfs1(d+1, fixed)
        if phase1_nodes[0] > max_states: return
        del fixed[d]

    dfs1(0, {})

    # Проверяем: нашли SAT в фазе 1?
    for tag, f in undetermined_states:
        if tag == 'SAT':
            return f, phase1_nodes[0]

    undet_count = sum(1 for tag, _ in undetermined_states if tag == 'UNDET')

    # Фаза 2: для каждого недетерминированного — DFS по второй половине
    phase2_nodes = [0]
    result = [None]

    for tag, fixed1 in undetermined_states:
        if tag != 'UNDET': continue
        if result[0]: break

        def dfs2(d, fixed):
            phase2_nodes[0] += 1
            if phase2_nodes[0] > max_states: return
            out = propagate_out(gates, fixed)
            if out is not None:
                if out == 1: result[0] = dict(fixed)
                return
            if d >= n: return
            fixed[d] = 0; dfs2(d+1, fixed)
            if result[0] or phase2_nodes[0] > max_states: return
            fixed[d] = 1; dfs2(d+1, fixed)
            if result[0]: return
            del fixed[d]

        dfs2(half, dict(fixed1))

    total = phase1_nodes[0] + phase2_nodes[0]
    return result[0], total, phase1_nodes[0], undet_count, phase2_nodes[0]


# Генераторы
def build_3sat(n, alpha=4.27):
    gates=[]; nid=n; neg={}
    for i in range(n): neg[i]=nid; gates.append(('NOT',i,-1,nid)); nid+=1
    c_outs=[]
    for _ in range(int(alpha*n)):
        vs=random.sample(range(n),3)
        cl=[(v,random.random()>0.5) for v in vs]
        lits=[v if p else neg[v] for v,p in cl]
        cur=lits[0]
        for l in lits[1:]: out=nid; gates.append(('OR',cur,l,out)); nid+=1; cur=out
        c_outs.append(cur)
    cur=c_outs[0]
    for c in c_outs[1:]: g=nid; gates.append(('AND',cur,c,g)); nid+=1; cur=g
    return gates, n

def random_circuit(n, size):
    gates=[]; nid=n
    for _ in range(size):
        gtype=random.choice(['AND','OR','NOT'])
        if gtype=='NOT': gates.append(('NOT',random.randint(0,nid-1),-1,nid))
        else: gates.append((gtype,random.randint(0,nid-1),random.randint(0,nid-1),nid))
        nid+=1
    return gates, n


def main():
    random.seed(42)
    print("=" * 72)
    print("  MITM + DETERMINATION PRUNING")
    print("  Цель: быстрее birthday (2^{n/2})?")
    print("=" * 72)

    # =========================================================
    # ТЕСТ 1: 3-SAT — 4 алгоритма
    # =========================================================
    print()
    print("  ТЕСТ 1: 3-SAT (α=4.27)")
    print(f"  {'n':>4} {'brute':>9} {'DFS':>9} {'MITM-P':>9} "
          f"{'2^n':>9} {'2^{n/2}':>9}")
    print(f"  {'-'*52}")

    for n in [10, 12, 14, 16, 18, 20]:
        g, nv = build_3sat(n)
        two_n = 2**n
        two_half = 2**(n//2)

        _, dfs_n = dfs_pruning(g, nv, 10**7)

        r = mitm_pruned(g, nv, 10**7)
        if len(r) == 5:
            _, mitm_n, p1, undet, p2 = r
        else:
            mitm_n = r[1]; p1 = 0; undet = 0; p2 = 0

        print(f"  {n:4d} {two_n:9d} {dfs_n:9d} {mitm_n:9d} "
              f"{two_n:9d} {two_half:9d}")
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 2: ε для каждого метода
    # =========================================================
    print()
    print("  ТЕСТ 2: ε = log2(speedup)/n")
    print(f"  {'n':>4} {'DFS ε':>8} {'MITM-P ε':>9} {'birthday':>9}")
    print(f"  {'-'*32}")

    for n in [10, 12, 14, 16, 18, 20, 22]:
        g, nv = build_3sat(n)
        two_n = 2**n

        _, dfs_n = dfs_pruning(g, nv, 10**7)
        r = mitm_pruned(g, nv, 10**7)
        mitm_n = r[1]

        eps_dfs = math.log2(max(1.01, two_n / dfs_n)) / n if dfs_n else 0
        eps_mitm = math.log2(max(1.01, two_n / mitm_n)) / n if mitm_n else 0

        print(f"  {n:4d} {eps_dfs:8.4f} {eps_mitm:9.4f} {'0.5000':>9}")
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 3: Детали MITM-pruned — куда уходят ноды
    # =========================================================
    print()
    print("  ТЕСТ 3: Детали MITM-pruned (3-SAT)")
    print(f"  {'n':>4} {'phase1':>8} {'undet':>7} {'phase2':>8} "
          f"{'total':>8} {'2^{n/2}':>8}")
    print(f"  {'-'*44}")

    for n in [10, 12, 14, 16, 18, 20]:
        g, nv = build_3sat(n)
        r = mitm_pruned(g, nv, 10**7)
        if len(r) == 5:
            _, total, p1, undet, p2 = r
            print(f"  {n:4d} {p1:8d} {undet:7d} {p2:8d} "
                  f"{total:8d} {2**(n//2):8d}")
        sys.stdout.flush()

    # =========================================================
    # ТЕСТ 4: Random circuits
    # =========================================================
    print()
    print("  ТЕСТ 4: Random circuits (size=5n)")
    print(f"  {'n':>4} {'DFS ε':>8} {'MITM-P ε':>9}")
    print(f"  {'-'*22}")

    for n in [10, 12, 14, 16, 18]:
        eps_d = []; eps_m = []
        for _ in range(5):
            g, nv = random_circuit(n, 5*n)
            _, dfs_n = dfs_pruning(g, nv, 10**7)
            r = mitm_pruned(g, nv, 10**7)
            mitm_n = r[1]
            two_n = 2**n
            if dfs_n and dfs_n > 1:
                eps_d.append(math.log2(max(1.01, two_n/dfs_n))/n)
            if mitm_n and mitm_n > 1:
                eps_m.append(math.log2(max(1.01, two_n/mitm_n))/n)
        ed = sum(eps_d)/len(eps_d) if eps_d else 0
        em = sum(eps_m)/len(eps_m) if eps_m else 0
        print(f"  {n:4d} {ed:8.4f} {em:9.4f}")
        sys.stdout.flush()

    # =========================================================
    # ИТОГ
    # =========================================================
    print()
    print("=" * 72)
    print("  ИТОГ: MITM + Determination Pruning")
    print("=" * 72)
    print("""
  MITM-Pruned:
    Фаза 1: DFS с pruning по n/2 vars → S₁ недетерм. состояний
    Фаза 2: для каждого — DFS по оставшимся n/2 vars → S₂ узлов

    Если S₁ << 2^{n/2}: фаза 1 дешевле birthday.
    Если S₂ << 2^{n/2}: фаза 2 тоже дешевле.
    Total = S₁ + S₁ × S₂ < S₁ × S₂ если S₁,S₂ << 2^{n/2}.

  СРАВНЕНИЕ С BIRTHDAY:
    Birthday:    2^{n/2} время, 2^{n/2} память.
    MITM-Pruned: S₁ + S₁×S₂ время, S₁ память.
    DFS-Pruned:  ~2^{0.81n} время, O(n) память.
    """)


if __name__ == "__main__":
    main()
