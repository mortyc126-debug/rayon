"""
ПУТЬ 2: NEXP-схемы не содержат XOR?
Аргумент: в Cook-Levin, TM-правило кодируется через AND/OR/NOT.
XOR появляется только если СПЕЦИАЛЬНО добавлено.
Покажем: для ЛЮБОЙ TM, переходная функция реализуема без XOR-паттернов
так, что constant propagation работает.
"""
import random, math, sys

def propagate(gates, fixed_vars):
    wire = dict(fixed_vars)
    for gtype, i1, i2, out in gates:
        v1 = wire.get(i1)
        v2 = wire.get(i2) if i2 >= 0 else None
        if gtype == 'AND':
            if v1 == 0 or v2 == 0: wire[out] = 0
            elif v1 is not None and v2 is not None: wire[out] = v1 & v2
        elif gtype == 'OR':
            if v1 == 1 or v2 == 1: wire[out] = 1
            elif v1 is not None and v2 is not None: wire[out] = v1 | v2
        elif gtype == 'NOT':
            if v1 is not None: wire[out] = 1 - v1
    return wire.get(gates[-1][3]) if gates else None


def build_tm_generic(n, steps, truth_table):
    """TM с ПРОИЗВОЛЬНЫМ правилом f: {0,1}^3 → {0,1}.
    truth_table = [f(0,0,0), f(0,0,1), ..., f(1,1,1)] (8 бит).
    Реализация через DNF (OR of AND minterms) — гарантированно
    без XOR-паттернов, с контролирующими значениями в AND/OR."""
    gates = []; nid = n
    prev = list(range(n))

    # NOT для входов
    neg_cache = {}
    def get_neg(x):
        if x not in neg_cache:
            nonlocal nid
            neg_cache[x] = nid
            gates.append(('NOT', x, -1, nid)); nid += 1
        return neg_cache[x]

    for t in range(steps):
        new = []; neg_cache = {}
        for i in range(n):
            L, C, R = prev[(i-1)%n], prev[i], prev[(i+1)%n]

            # DNF реализация: OR всех минтермов где f = 1
            minterms = []
            for a in range(2):
                for b in range(2):
                    for c in range(2):
                        idx = a * 4 + b * 2 + c
                        if truth_table[idx] == 1:
                            # Минтерм: AND(lit_a, lit_b, lit_c)
                            la = L if a == 1 else get_neg(L)
                            lb = C if b == 1 else get_neg(C)
                            lc = R if c == 1 else get_neg(R)
                            t1 = nid; gates.append(('AND', la, lb, t1)); nid += 1
                            t2 = nid; gates.append(('AND', t1, lc, t2)); nid += 1
                            minterms.append(t2)

            if not minterms:
                # f ≡ 0
                r = nid; gates.append(('AND', L, get_neg(L), r)); nid += 1  # always 0
            elif len(minterms) == 1:
                r = minterms[0]
            else:
                cur = minterms[0]
                for m in minterms[1:]:
                    r = nid; gates.append(('OR', cur, m, r)); nid += 1; cur = r
                r = cur
            new.append(r)
        prev = new

    # OR(all final cells)
    cur = prev[0]
    for p in prev[1:]:
        gates.append(('OR', cur, p, nid)); cur = nid; nid += 1
    return gates, n


def measure(gates, n, k, strategy='consecutive', trials=2000):
    det = 0
    for _ in range(trials):
        if strategy == 'consecutive':
            s = random.randint(0, n-1)
            vs = [(s+i) % n for i in range(min(k, n))]
        else:
            vs = random.sample(range(n), min(k, n))
        fixed = {v: random.randint(0, 1) for v in vs}
        if propagate(gates, fixed) is not None:
            det += 1
    return det / trials


def main():
    random.seed(42)
    print("=" * 60)
    print("  ПУТЬ 2: Все 256 правил через DNF (без XOR)")
    print("=" * 60)

    # Все 256 правил f: {0,1}^3 → {0,1}
    n = 20; steps = 10; k = n // 2

    print(f"\n  n={n}, steps={steps}, k={k}, consecutive, OR(final)")
    print(f"\n  Тестируем все 256 правил...")
    print()

    results = []
    for rule_num in range(256):
        tt = [(rule_num >> i) & 1 for i in range(8)]
        # Пропускаем тривиальные (f≡0 или f≡1)
        if sum(tt) == 0 or sum(tt) == 8:
            continue
        gates, nv = build_tm_generic(n, steps, tt)
        pr = measure(gates, nv, k, 'consecutive', 500)
        results.append((rule_num, tt, pr))

    # Сортируем по Pr
    results.sort(key=lambda x: x[2])

    # Худшие 15
    print("  ХУДШИЕ 15 правил (минимальная Pr[det]):")
    print(f"  {'rule':>5} {'truth_table':>12} {'Pr[det]':>8} {'#ones':>6}")
    print(f"  {'-'*34}")
    for rule, tt, pr in results[:15]:
        print(f"  {rule:5d} {''.join(map(str,tt)):>12} {pr:8.4f} {sum(tt):6d}")

    # Лучшие 15
    print(f"\n  ЛУЧШИЕ 15 правил:")
    print(f"  {'rule':>5} {'truth_table':>12} {'Pr[det]':>8} {'#ones':>6}")
    print(f"  {'-'*34}")
    for rule, tt, pr in results[-15:]:
        print(f"  {rule:5d} {''.join(map(str,tt)):>12} {pr:8.4f} {sum(tt):6d}")

    # Статистика
    prs = [pr for _, _, pr in results]
    zeros = sum(1 for p in prs if p < 0.01)
    high = sum(1 for p in prs if p > 0.5)
    print(f"\n  Всего правил: {len(results)}")
    print(f"  Pr < 0.01 (не работает): {zeros} ({100*zeros/len(results):.0f}%)")
    print(f"  Pr > 0.50 (работает):    {high} ({100*high/len(results):.0f}%)")
    print(f"  Медиана Pr: {sorted(prs)[len(prs)//2]:.4f}")

    # XOR-содержащие vs нет
    print(f"\n  Анализ: XOR-подобные правила")
    # rule90 = XOR(a,c) = [0,1,1,0,0,1,1,0]
    # rule30 = XOR(a, b|c)
    xor_rules = {90, 150, 60, 102, 30, 86, 106, 120}  # известные XOR-heavy
    print(f"  {'rule':>5} {'XOR?':>5} {'Pr[det]':>8}")
    print(f"  {'-'*20}")
    for rule, tt, pr in results[:30]:
        is_xor = rule in xor_rules
        print(f"  {rule:5d} {'YES' if is_xor else 'no':>5} {pr:8.4f}")

    # Масштабирование для rule110 DNF vs direct
    print(f"\n  Масштабирование: Rule 110 через DNF")
    print(f"  {'n':>4} {'Pr consec':>10} {'Pr random':>10}")
    print(f"  {'-'*26}")
    # rule110 truth table: f(0,0,0)=0, f(0,0,1)=1, f(0,1,0)=0, f(0,1,1)=1,
    #                       f(1,0,0)=0, f(1,0,1)=0, f(1,1,0)=1, f(1,1,1)=1
    tt_110 = [0, 1, 0, 1, 0, 0, 1, 1]
    for n in [10, 15, 20, 25, 30, 40]:
        gates, nv = build_tm_generic(n, n, tt_110)
        pc = measure(gates, nv, nv//2, 'consecutive', 2000)
        pr = measure(gates, nv, nv//2, 'random', 2000)
        print(f"  {n:4d} {pc:10.4f} {pr:10.4f}")
        sys.stdout.flush()

    print("\n  ИТОГ ПУТИ 2:")
    print("  Какая доля правил даёт Pr → 1?")
    print("  Ключевой вопрос: NEXP-схемы используют какие правила?")

if __name__ == "__main__":
    main()
