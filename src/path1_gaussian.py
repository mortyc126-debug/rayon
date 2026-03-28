"""
ПУТЬ 1: Гауссова элиминация + constant propagation (гибрид).
Каждый провод = аффинная функция c ⊕ ⊕{x_i : i ∈ S} над GF(2).
AND(affine, affine) → если L1=L2 → L; если L1=NOT L2 → 0.
"""
import random, math, sys

def propagate_hybrid(gates, n, fixed_vars):
    """Гибрид: аффинные функции + constant propagation.
    wire[id] = (const, frozenset_of_free_vars) или None."""
    wire = {}
    for v, val in fixed_vars.items():
        wire[v] = (val, frozenset())
    for v in range(n):
        if v not in wire:
            wire[v] = (0, frozenset([v]))

    for gtype, i1, i2, out in gates:
        w1 = wire.get(i1)
        w2 = wire.get(i2) if i2 >= 0 else None

        if gtype == 'NOT':
            if w1 is not None:
                wire[out] = (1 - w1[0], w1[1])

        elif gtype == 'XOR':
            if w1 is not None and w2 is not None:
                wire[out] = (w1[0] ^ w2[0], w1[1].symmetric_difference(w2[1]))

        elif gtype == 'AND':
            c1 = w1 is not None and len(w1[1]) == 0
            c2 = w2 is not None and len(w2[1]) == 0
            if c1 and w1[0] == 0:
                wire[out] = (0, frozenset())
            elif c2 and w2[0] == 0:
                wire[out] = (0, frozenset())
            elif c1 and w1[0] == 1 and w2 is not None:
                wire[out] = w2
            elif c2 and w2[0] == 1 and w1 is not None:
                wire[out] = w1
            elif w1 is not None and w2 is not None:
                # L1 = L2 → AND(L,L) = L
                if w1 == w2:
                    wire[out] = w1
                # L1 = NOT L2 → AND(L, NOT L) = 0
                elif w1[1] == w2[1] and w1[0] != w2[0]:
                    wire[out] = (0, frozenset())
                # else: нелинейно, не можем отследить

        elif gtype == 'OR':
            c1 = w1 is not None and len(w1[1]) == 0
            c2 = w2 is not None and len(w2[1]) == 0
            if c1 and w1[0] == 1:
                wire[out] = (1, frozenset())
            elif c2 and w2[0] == 1:
                wire[out] = (1, frozenset())
            elif c1 and w1[0] == 0 and w2 is not None:
                wire[out] = w2
            elif c2 and w2[0] == 0 and w1 is not None:
                wire[out] = w1
            elif w1 is not None and w2 is not None:
                if w1 == w2:
                    wire[out] = w1
                elif w1[1] == w2[1] and w1[0] != w2[0]:
                    wire[out] = (1, frozenset())

    out_w = wire.get(gates[-1][3]) if gates else None
    if out_w is not None and len(out_w[1]) == 0:
        return out_w[0]
    return None


def propagate_basic(gates, fixed_vars):
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
        elif gtype == 'XOR':
            if v1 is not None and v2 is not None: wire[out] = v1 ^ v2
    return wire.get(gates[-1][3]) if gates else None


def build_xor_chain(n, native=False):
    gates = []; nid = n; cur = 0
    for i in range(1, n):
        if native:
            gates.append(('XOR', cur, i, nid)); cur = nid; nid += 1
        else:
            nc = nid; gates.append(('NOT', cur, -1, nc)); nid += 1
            nb = nid; gates.append(('NOT', i, -1, nb)); nid += 1
            t1 = nid; gates.append(('AND', cur, nb, t1)); nid += 1
            t2 = nid; gates.append(('AND', nc, i, t2)); nid += 1
            xor = nid; gates.append(('OR', t1, t2, xor)); nid += 1
            cur = xor
    return gates, n


def build_tm_rule(n, steps, rule='rule30'):
    gates = []; nid = n; prev = list(range(n))
    for t in range(steps):
        new = []
        for i in range(n):
            L, C, R = prev[(i-1)%n], prev[i], prev[(i+1)%n]
            if rule == 'rule30':
                boc = nid; gates.append(('OR', C, R, boc)); nid += 1
                nboc = nid; gates.append(('NOT', boc, -1, nboc)); nid += 1
                t1 = nid; gates.append(('AND', L, nboc, t1)); nid += 1
                nl = nid; gates.append(('NOT', L, -1, nl)); nid += 1
                t2 = nid; gates.append(('AND', nl, boc, t2)); nid += 1
                r = nid; gates.append(('OR', t1, t2, r)); nid += 1
            elif rule == 'rule110':
                ab = nid; gates.append(('AND', L, C, ab)); nid += 1
                bc = nid; gates.append(('AND', C, R, bc)); nid += 1
                nl = nid; gates.append(('NOT', L, -1, nl)); nid += 1
                nac = nid; gates.append(('AND', nl, R, nac)); nid += 1
                t1 = nid; gates.append(('OR', ab, bc, t1)); nid += 1
                r = nid; gates.append(('OR', t1, nac, r)); nid += 1
            new.append(r)
        prev = new
    # OR(all)
    cur = prev[0]
    for p in prev[1:]:
        gates.append(('OR', cur, p, nid)); cur = nid; nid += 1
    return gates, n


def measure(gates, n, k, method='basic', trials=2000):
    det = 0
    for _ in range(trials):
        vs = random.sample(range(n), min(k, n))
        fixed = {v: random.randint(0, 1) for v in vs}
        if method == 'basic':
            r = propagate_basic(gates, fixed)
        else:
            r = propagate_hybrid(gates, n, fixed)
        if r is not None:
            det += 1
    return det / trials


def main():
    random.seed(42)
    print("=" * 60)
    print("  ПУТЬ 1: Гибрид (Гаусс + constant propagation)")
    print("=" * 60)

    # Тест 1: XOR-цепочка
    print("\n  XOR-цепочка (нативные XOR-гейты):")
    print(f"  {'n':>4} {'basic':>8} {'hybrid':>8}")
    print(f"  {'-'*22}")
    for n in [6, 8, 10, 15, 20]:
        g, nv = build_xor_chain(n, native=True)
        pb = measure(g, nv, nv//2, 'basic', 2000)
        ph = measure(g, nv, nv//2, 'hybrid', 2000)
        print(f"  {n:4d} {pb:8.4f} {ph:8.4f}")

    # Тест 2: XOR через AND/OR/NOT
    print("\n  XOR-цепочка (AND/OR/NOT encoding):")
    print(f"  {'n':>4} {'basic':>8} {'hybrid':>8}")
    print(f"  {'-'*22}")
    for n in [6, 8, 10, 15, 20]:
        g, nv = build_xor_chain(n, native=False)
        pb = measure(g, nv, nv//2, 'basic', 2000)
        ph = measure(g, nv, nv//2, 'hybrid', 2000)
        print(f"  {n:4d} {pb:8.4f} {ph:8.4f}")

    # Тест 3: Rule30 TM (XOR-подобное)
    print("\n  Rule30 TM + OR(final) + consecutive:")
    print(f"  {'n':>4} {'basic':>8} {'hybrid':>8}")
    print(f"  {'-'*22}")
    for n in [8, 10, 12, 15, 20]:
        g, nv = build_tm_rule(n, n, 'rule30')
        pb = measure(g, nv, nv//2, 'basic', 2000)
        ph = measure(g, nv, nv//2, 'hybrid', 2000)
        print(f"  {n:4d} {pb:8.4f} {ph:8.4f}")
        sys.stdout.flush()

    # Тест 4: Rule110 TM (для сравнения)
    print("\n  Rule110 TM + OR(final) (контроль):")
    print(f"  {'n':>4} {'basic':>8} {'hybrid':>8}")
    print(f"  {'-'*22}")
    for n in [8, 10, 15, 20]:
        g, nv = build_tm_rule(n, n, 'rule110')
        pb = measure(g, nv, nv//2, 'basic', 2000)
        ph = measure(g, nv, nv//2, 'hybrid', 2000)
        print(f"  {n:4d} {pb:8.4f} {ph:8.4f}")
        sys.stdout.flush()

    print("\n  ИТОГ ПУТИ 1:")
    print("  XOR-цепочка: hybrid помогает? ...")
    print("  Rule30: hybrid помогает? ...")

if __name__ == "__main__":
    main()
