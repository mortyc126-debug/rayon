"""
ПЕРЕБОР ПАРОЛЕЙ: точное измерение ускорения.
Тестируем реалистичные сценарии:
  1. PIN код (4-8 цифр)
  2. Password с policy rules
  3. Access control logic (AND/OR правила)
  4. Password + простой хеш (XOR checksum)
  5. Password matching (сравнение побитовое)
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

def dfs_solve(gates, n, max_nodes=10000000):
    nodes=[0]; result=[None]
    out_id = gates[-1][3] if gates else -1
    def dfs(d, fixed):
        nodes[0]+=1
        if nodes[0]>max_nodes: return
        out=propagate(gates,fixed)
        if out is not None:
            if out==1: result[0]=dict(fixed)
            return
        if d>=n: return
        fixed[d]=0; dfs(d+1,fixed)
        if result[0] or nodes[0]>max_nodes: return
        fixed[d]=1; dfs(d+1,fixed)
        if result[0]: return
        del fixed[d]
    dfs(0,{})
    return result[0], nodes[0]

def make_xor(gates, a, b, nid_ref):
    nid=nid_ref[0]
    na=nid; gates.append(('NOT',a,-1,na)); nid+=1
    nb=nid; gates.append(('NOT',b,-1,nb)); nid+=1
    t1=nid; gates.append(('AND',a,nb,t1)); nid+=1
    t2=nid; gates.append(('AND',na,b,t2)); nid+=1
    xor=nid; gates.append(('OR',t1,t2,xor)); nid+=1
    nid_ref[0]=nid; return xor


# ================================================================
# СЦЕНАРИЙ 1: PIN код
# ================================================================
def build_pin_check(num_digits, correct_pin):
    """PIN = num_digits × 4 бита (BCD). Проверка: input == correct_pin.
    Circuit: AND(XNOR(bit_i, correct_i) for all bits).
    Это AND-chain длины num_digits × 4!"""
    n = num_digits * 4  # 4 бита на цифру
    gates = []; nid_ref = [n]

    correct_bits = []
    for d in correct_pin:
        for b in range(4):
            correct_bits.append((d >> b) & 1)

    match_parts = []
    for i in range(n):
        if correct_bits[i] == 1:
            match_parts.append(i)  # XNOR(x_i, 1) = x_i
        else:
            nid = nid_ref[0]
            gates.append(('NOT', i, -1, nid))
            nid_ref[0] = nid + 1
            match_parts.append(nid)  # XNOR(x_i, 0) = NOT x_i

    # AND chain
    nid = nid_ref[0]
    cur = match_parts[0]
    for mp in match_parts[1:]:
        gates.append(('AND', cur, mp, nid))
        cur = nid; nid += 1

    return gates, n


# ================================================================
# СЦЕНАРИЙ 2: Password policy
# ================================================================
def build_password_policy(length_bits):
    """Password = length_bits бит.
    Policy: AND(rule1, rule2, rule3, ...).
    rule1: хотя бы один бит в позициях 0-3 = 1 (has uppercase)
    rule2: хотя бы один бит в позициях 4-7 = 1 (has digit)
    rule3: bit[0] == 0 (starts with specific)
    rule4: NOT(all bits same) — не тривиальный пароль
    """
    n = length_bits
    gates = []; nid_ref = [n]

    rules = []

    # Rule 1: OR(bit[0], bit[1], bit[2], bit[3]) — has "uppercase"
    nid = nid_ref[0]
    cur = 0
    for i in range(1, min(4, n)):
        gates.append(('OR', cur, i, nid)); cur = nid; nid += 1
    nid_ref[0] = nid
    rules.append(cur)

    # Rule 2: OR(bit[4], bit[5], bit[6], bit[7]) — has "digit"
    if n > 4:
        nid = nid_ref[0]; cur = 4
        for i in range(5, min(8, n)):
            gates.append(('OR', cur, i, nid)); cur = nid; nid += 1
        nid_ref[0] = nid
        rules.append(cur)

    # Rule 3: bit[n-1] == 1 (ends with specific)
    if n > 8:
        rules.append(n - 1)

    # Rule 4: NOT(AND(all bits)) — не все единицы
    if n > 4:
        nid = nid_ref[0]; cur = 0
        for i in range(1, n):
            gates.append(('AND', cur, i, nid)); cur = nid; nid += 1
        not_all = nid; gates.append(('NOT', cur, -1, not_all)); nid += 1
        nid_ref[0] = nid
        rules.append(not_all)

    # Rule 5: NOT(all zeros)
    nid = nid_ref[0]; cur = 0
    for i in range(1, n):
        gates.append(('OR', cur, i, nid)); cur = nid; nid += 1
    nid_ref[0] = nid
    rules.append(cur)

    # AND всех rules
    nid = nid_ref[0]; cur = rules[0]
    for r in rules[1:]:
        gates.append(('AND', cur, r, nid)); cur = nid; nid += 1

    return gates, n


# ================================================================
# СЦЕНАРИЙ 3: Access control
# ================================================================
def build_access_control(n):
    """Access control: сложная AND/OR логика.
    role_admin = bit[0] AND bit[1]
    role_user = bit[2] OR bit[3]
    time_ok = bit[4] AND NOT bit[5]
    ip_ok = bit[6] OR bit[7]
    access = (role_admin OR (role_user AND time_ok)) AND ip_ok AND ...
    """
    gates = []; nid_ref = [n]

    # role_admin = AND(bit[0], bit[1])
    nid = nid_ref[0]
    ra = nid; gates.append(('AND', 0, 1, ra)); nid += 1

    # role_user = OR(bit[2], bit[3])
    ru = nid; gates.append(('OR', 2 % n, 3 % n, ru)); nid += 1

    # time_ok = AND(bit[4], NOT bit[5])
    nb5 = nid; gates.append(('NOT', 5 % n, -1, nb5)); nid += 1
    tok = nid; gates.append(('AND', 4 % n, nb5, tok)); nid += 1

    # ip_ok = OR(bit[6], bit[7])
    ipok = nid; gates.append(('OR', 6 % n, 7 % n, ipok)); nid += 1

    # user_access = AND(role_user, time_ok)
    ua = nid; gates.append(('AND', ru, tok, ua)); nid += 1

    # any_role = OR(role_admin, user_access)
    ar = nid; gates.append(('OR', ra, ua, ar)); nid += 1

    # Добавляем больше правил для больших n
    cur = ar
    for i in range(8, n, 2):
        # Дополнительное правило: AND(cur, OR(bit[i], bit[i+1]))
        if i + 1 < n:
            or_g = nid; gates.append(('OR', i, i+1, or_g)); nid += 1
            and_g = nid; gates.append(('AND', cur, or_g, and_g)); nid += 1
            cur = and_g
        else:
            and_g = nid; gates.append(('AND', cur, i, and_g)); nid += 1
            cur = and_g

    # Final: AND(access, ip_ok)
    final = nid; gates.append(('AND', cur, ipok, final)); nid += 1
    nid_ref[0] = nid

    return gates, n


# ================================================================
# СЦЕНАРИЙ 4: Password + XOR checksum
# ================================================================
def build_password_checksum(nbits, checksum_bits=4):
    """Password проверяется через XOR checksum.
    checksum = XOR(chunks). Задан target checksum."""
    n = nbits
    gates = []; nid_ref = [n]

    # XOR-fold до checksum_bits
    state = list(range(n))
    while len(state) > checksum_bits:
        new = []
        for i in range(0, len(state)-1, 2):
            new.append(make_xor(gates, state[i], state[i+1], nid_ref))
        if len(state) % 2: new.append(state[-1])
        state = new

    # Match с target checksum (random)
    random.seed(99)
    target = [random.randint(0, 1) for _ in range(checksum_bits)]

    match_parts = []
    for i in range(min(len(state), checksum_bits)):
        if target[i] == 1:
            match_parts.append(state[i])
        else:
            nid = nid_ref[0]
            gates.append(('NOT', state[i], -1, nid))
            nid_ref[0] = nid + 1
            match_parts.append(nid)

    nid = nid_ref[0]; cur = match_parts[0]
    for mp in match_parts[1:]:
        gates.append(('AND', cur, mp, nid)); cur = nid; nid += 1

    return gates, n


# ================================================================
# СЦЕНАРИЙ 5: Direct password comparison
# ================================================================
def build_password_compare(nbits, target_password):
    """Прямое сравнение пароля побитово.
    AND(XNOR(input[i], target[i])) — AND chain длины n."""
    n = nbits; gates = []; nid_ref = [n]
    match_parts = []
    for i in range(n):
        tv = (target_password >> i) & 1
        if tv == 1:
            match_parts.append(i)
        else:
            nid = nid_ref[0]
            gates.append(('NOT', i, -1, nid))
            nid_ref[0] = nid + 1
            match_parts.append(nid)
    nid = nid_ref[0]; cur = match_parts[0]
    for mp in match_parts[1:]:
        gates.append(('AND', cur, mp, nid)); cur = nid; nid += 1
    return gates, n


def main():
    random.seed(42)
    sys.setrecursionlimit(500000)
    print("=" * 72)
    print("  ПЕРЕБОР ПАРОЛЕЙ: точное ускорение")
    print("=" * 72)

    # =========================================================
    # СЦЕНАРИЙ 1: PIN код
    # =========================================================
    print()
    print("  СЦЕНАРИЙ 1: PIN код (BCD, 4 бита/цифра)")
    print()
    print(f"  {'digits':>6} {'n bits':>7} {'DFS':>8} {'brute':>9} "
          f"{'speedup':>8} {'ε':>7}")
    print(f"  {'-'*50}")

    for num_digits in [4, 5, 6, 7, 8, 10, 12]:
        correct = [random.randint(0, 9) for _ in range(num_digits)]
        gates, n = build_pin_check(num_digits, correct)
        _, dfs_nodes = dfs_solve(gates, n, 10000000)
        brute = 2 ** n
        sp = brute / max(1, dfs_nodes)
        eps = math.log2(max(1.01, sp)) / n
        print(f"  {num_digits:6d} {n:7d} {dfs_nodes:8d} {brute:9d} "
              f"{sp:8.0f}x {eps:7.4f}")
        sys.stdout.flush()

    # =========================================================
    # СЦЕНАРИЙ 2: Password policy
    # =========================================================
    print()
    print("  СЦЕНАРИЙ 2: Password policy (AND/OR rules)")
    print()
    print(f"  {'n bits':>7} {'DFS':>8} {'brute':>9} {'speedup':>8} {'ε':>7}")
    print(f"  {'-'*42}")

    for nbits in [8, 10, 12, 14, 16, 18, 20, 24]:
        gates, n = build_password_policy(nbits)
        _, dfs_nodes = dfs_solve(gates, n, 10000000)
        if dfs_nodes >= 10000000:
            print(f"  {nbits:7d} {'timeout':>8}")
            continue
        brute = 2 ** n
        sp = brute / max(1, dfs_nodes)
        eps = math.log2(max(1.01, sp)) / n
        print(f"  {nbits:7d} {dfs_nodes:8d} {brute:9d} {sp:8.0f}x {eps:7.4f}")
        sys.stdout.flush()

    # =========================================================
    # СЦЕНАРИЙ 3: Access control
    # =========================================================
    print()
    print("  СЦЕНАРИЙ 3: Access control (AND/OR rules)")
    print()
    print(f"  {'n bits':>7} {'DFS':>8} {'brute':>9} {'speedup':>8} {'ε':>7}")
    print(f"  {'-'*42}")

    for nbits in [8, 10, 12, 14, 16, 18, 20, 24, 28, 32]:
        gates, n = build_access_control(nbits)
        _, dfs_nodes = dfs_solve(gates, n, 10000000)
        if dfs_nodes >= 10000000:
            print(f"  {nbits:7d} {'timeout':>8}")
            continue
        brute = 2 ** n
        sp = brute / max(1, dfs_nodes)
        eps = math.log2(max(1.01, sp)) / n
        print(f"  {nbits:7d} {dfs_nodes:8d} {brute:9d} {sp:8.0f}x {eps:7.4f}")
        sys.stdout.flush()

    # =========================================================
    # СЦЕНАРИЙ 4: XOR checksum
    # =========================================================
    print()
    print("  СЦЕНАРИЙ 4: Password + XOR checksum (4 бита)")
    print()
    print(f"  {'n bits':>7} {'DFS':>8} {'brute':>9} {'speedup':>8} {'ε':>7}")
    print(f"  {'-'*42}")

    for nbits in [8, 12, 16, 20, 24, 28, 32]:
        gates, n = build_password_checksum(nbits, 4)
        _, dfs_nodes = dfs_solve(gates, n, 10000000)
        if dfs_nodes >= 10000000:
            print(f"  {nbits:7d} {'timeout':>8}")
            continue
        brute = 2 ** n
        sp = brute / max(1, dfs_nodes)
        eps = math.log2(max(1.01, sp)) / n
        print(f"  {nbits:7d} {dfs_nodes:8d} {brute:9d} {sp:8.0f}x {eps:7.4f}")
        sys.stdout.flush()

    # =========================================================
    # СЦЕНАРИЙ 5: Direct password comparison
    # =========================================================
    print()
    print("  СЦЕНАРИЙ 5: Побитовое сравнение пароля (AND chain)")
    print()
    print(f"  {'n bits':>7} {'DFS':>8} {'brute':>12} {'speedup':>10} {'ε':>7}")
    print(f"  {'-'*48}")

    for nbits in [8, 12, 16, 20, 24, 28, 32, 40, 48]:
        target = random.getrandbits(nbits)
        gates, n = build_password_compare(nbits, target)
        _, dfs_nodes = dfs_solve(gates, n, 10000000)
        if dfs_nodes >= 10000000:
            print(f"  {nbits:7d} {'timeout':>8}")
            continue
        brute = 2 ** n
        sp = brute / max(1, dfs_nodes)
        eps = math.log2(max(1.01, sp)) / n
        print(f"  {nbits:7d} {dfs_nodes:8d} {brute:12d} {sp:10.0f}x {eps:7.4f}")
        sys.stdout.flush()

    # =========================================================
    # ИТОГ
    # =========================================================
    print()
    print("=" * 72)
    print("  ИТОГ: УСКОРЕНИЕ ПЕРЕБОРА ПАРОЛЕЙ")
    print("=" * 72)
    print("""
  ╔═══════════════════════════════════════════════════════════════╗
  ║  Сценарий              │ Ускорение  │ ε       │ Применимость ║
  ╠═══════════════════════════════════════════════════════════════╣
  ║  PIN код (побитовый)   │            │         │              ║
  ║  Password policy       │            │         │              ║
  ║  Access control        │            │         │              ║
  ║  XOR checksum          │            │         │              ║
  ║  Побитовое сравнение   │            │         │              ║
  ╚═══════════════════════════════════════════════════════════════╝
    """)

if __name__ == "__main__":
    main()
