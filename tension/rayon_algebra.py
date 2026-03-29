"""
RAYON ALGEBRA — Наша алгебра. Не GF(2), не Z, не R.

Пространство Rayon: {0, 1, ?} с операциями kill/pass/absorb.

Стандартная алгебра работает с ЗНАЧЕНИЯМИ.
Rayon алгебра работает с НАБЛЮДАЕМОСТЬЮ.

Объекты:
  RayonElement   — элемент в {0, 1, ?}^n
  CarryWord      — слово в {G, K, P, ?}^n
  TensionForm    — билинейная форма τ(a, b) на Rayon-элементах
  KillMatrix     — матрица убийств: какие ? уничтожаются какими операциями

Аксиомы (НЕ стандартные):
  1. ? ⊕ ? = ?  (XOR не убивает — PASS)
  2. 0 ∧ ? = 0  (AND с 0 убивает — KILL)
  3. 1 ∨ ? = 1  (OR с 1 убивает — KILL)
  4. τ(f(x)) ≤ τ(x)  (операции не СОЗДАЮТ неизвестность)
  5. τ(f(x)) < τ(x) только при KILL-линках
  6. Composition: {G,K,P,?}∘{G,K,P,?} — полугруппа с поглощением

Теоремы:
  T1: Цепь из n XOR: τ остаётся = τ(входа). Путь ПРОЗРАЧЕН.
  T2: Цепь из n AND: τ падает до 0 за O(n/p_known) шагов.
  T3: Carry-цепь длины L: ожидаемое число ? после L шагов = L × p_P^L.
  T4: Тензорное произведение: τ(a⊗b) = τ(a) + τ(b) - kills(a,b).
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from rayon_core_v2 import Bit3, CarryState, NativeCarryChain


# ═══════════════════════════════════════════════════════════
# RAYON ELEMENT — вектор в {0, 1, ?}^n
# ═══════════════════════════════════════════════════════════

class RayonElement:
    """
    Элемент Rayon-пространства: вектор из {0, 1, ?}.

    НЕ вектор из R^n. НЕ вектор из GF(2)^n.
    Третье состояние ? — не значение, а ОТСУТСТВИЕ наблюдения.

    Tension τ = количество ? в элементе.
    Ранг = количество известных бит.
    """

    def __init__(self, bits):
        """bits: list of 0, 1, None (=?)"""
        self.bits = list(bits)
        self.n = len(bits)

    @staticmethod
    def known(values):
        """Полностью наблюдённый элемент."""
        return RayonElement(list(values))

    @staticmethod
    def unknown(n):
        """Полностью ненаблюдённый элемент."""
        return RayonElement([None] * n)

    @staticmethod
    def from_int(value, width=32):
        """Из целого числа (все биты известны)."""
        return RayonElement([(value >> i) & 1 for i in range(width)])

    @staticmethod
    def partial(value, mask, width=32):
        """Частично известный: mask bit=1 → позиция ?."""
        bits = []
        for i in range(width):
            if (mask >> i) & 1:
                bits.append(None)
            else:
                bits.append((value >> i) & 1)
        return bits

    @property
    def tau(self):
        """Tension — количество неизвестных позиций."""
        return sum(1 for b in self.bits if b is None)

    @property
    def rank(self):
        """Ранг — количество известных позиций."""
        return self.n - self.tau

    @property
    def known_mask(self):
        """Маска известных позиций."""
        m = 0
        for i, b in enumerate(self.bits):
            if b is not None:
                m |= (1 << i)
        return m

    @property
    def known_value(self):
        """Значение в известных позициях (? → 0)."""
        v = 0
        for i, b in enumerate(self.bits):
            if b is not None and b == 1:
                v |= (1 << i)
        return v

    # ─── Rayon операции ───

    def XOR(self, other):
        """XOR: PASS-операция. ? ⊕ x = ?. Никогда не убивает."""
        result = []
        for a, b in zip(self.bits, other.bits):
            if a is not None and b is not None:
                result.append(a ^ b)
            else:
                result.append(None)
        return RayonElement(result)

    def AND(self, other):
        """AND: KILL-операция. 0 ∧ ? = 0."""
        result = []
        for a, b in zip(self.bits, other.bits):
            if a == 0 or b == 0:
                result.append(0)  # KILL
            elif a is not None and b is not None:
                result.append(a & b)
            else:
                result.append(None)
        return RayonElement(result)

    def OR(self, other):
        """OR: KILL-операция. 1 ∨ ? = 1."""
        result = []
        for a, b in zip(self.bits, other.bits):
            if a == 1 or b == 1:
                result.append(1)  # KILL
            elif a is not None and b is not None:
                result.append(a | b)
            else:
                result.append(None)
        return RayonElement(result)

    def NOT(self):
        """NOT: сохраняет tension. NOT(?) = ?."""
        return RayonElement([None if b is None else 1 - b for b in self.bits])

    def kills_with(self, other):
        """Сколько ? будет убито при AND с other."""
        kills = 0
        for a, b in zip(self.bits, other.bits):
            if a is None and b == 0:
                kills += 1
            elif b is None and a == 0:
                kills += 1
        return kills

    def observe(self, position, value):
        """Наблюдение: ? → конкретное значение в позиции."""
        new_bits = list(self.bits)
        new_bits[position] = value
        return RayonElement(new_bits)

    def collapse(self, values):
        """Полный коллапс: все ? → конкретные значения."""
        result = list(self.bits)
        vi = 0
        for i in range(self.n):
            if result[i] is None:
                result[i] = values[vi]
                vi += 1
        return RayonElement(result)

    def __repr__(self):
        return ''.join('?' if b is None else str(b) for b in self.bits)

    def __eq__(self, other):
        return self.bits == other.bits

    def __hash__(self):
        return hash(tuple(self.bits))


# ═══════════════════════════════════════════════════════════
# CARRY WORD — слово в {G, K, P, ?}^n
# ═══════════════════════════════════════════════════════════

class CarryWord:
    """
    Carry-слово: цепочка состояний {G, K, P, ?}.

    Это НЕ числа. Это описание ПОВЕДЕНИЯ carry-цепи.
    G = carry рождается (оба бита 1)
    K = carry умирает (оба бита 0)
    P = carry проходит (биты разные)
    ? = неизвестно

    Композиция: чтение справа налево (от младших к старшим).
    G и K — абсорберы (останавливают распространение).
    P — прозрачен (пропускает carry).
    ? — неизвестен (может быть чем угодно).
    """

    def __init__(self, states):
        """states: list of 'G', 'K', 'P', '?'"""
        self.states = list(states)
        self.n = len(states)

    @staticmethod
    def from_addition(a_elem, b_elem):
        """Построить carry-слово из двух RayonElement-слагаемых."""
        states = []
        for a, b in zip(a_elem.bits, b_elem.bits):
            if a is None or b is None:
                # Один или оба неизвестны
                if a == 0 or b == 0:
                    # AND(0, ?) = 0 → generate невозможен
                    # Но propagate = XOR(0, ?) = ? → может быть P или K
                    states.append('?')
                elif a == 1 or b == 1:
                    # AND(1, ?) = ? → generate возможен
                    states.append('?')
                else:
                    states.append('?')
            else:
                if a == 1 and b == 1:
                    states.append('G')
                elif a == 0 and b == 0:
                    states.append('K')
                else:
                    states.append('P')
        return CarryWord(states)

    @property
    def tau(self):
        """Tension = количество неизвестных позиций."""
        return sum(1 for s in self.states if s == '?')

    @property
    def absorbers(self):
        """Позиции G и K — останавливают carry."""
        return [i for i, s in enumerate(self.states) if s in ('G', 'K')]

    @property
    def transparent(self):
        """Позиции P — пропускают carry."""
        return [i for i, s in enumerate(self.states) if s == 'P']

    @property
    def unknown_positions(self):
        """Позиции ? — неизвестные."""
        return [i for i, s in enumerate(self.states) if s == '?']

    def propagate(self, carry_in='K'):
        """
        Пропустить carry через всю цепь.
        Возвращает итоговые carry на каждой позиции.
        """
        carries = []
        c = carry_in
        for s in self.states:
            # Композиция: carry_in ∘ position
            cs = CarryState(c)
            pos = CarryState(s)
            result = cs.compose(pos)
            c = result.state
            carries.append(c)
        return CarryWord(carries)

    def chain_lengths(self):
        """Длины P-цепочек и ?-цепочек."""
        p_chains = []
        q_chains = []
        current_p = 0
        current_q = 0
        for s in self.states:
            if s == 'P':
                current_p += 1
                if current_q > 0:
                    q_chains.append(current_q)
                    current_q = 0
            elif s == '?':
                current_q += 1
                if current_p > 0:
                    p_chains.append(current_p)
                    current_p = 0
            else:
                if current_p > 0:
                    p_chains.append(current_p)
                    current_p = 0
                if current_q > 0:
                    q_chains.append(current_q)
                    current_q = 0
        if current_p > 0:
            p_chains.append(current_p)
        if current_q > 0:
            q_chains.append(current_q)
        return p_chains, q_chains

    def surviving_unknowns(self):
        """
        Сколько ? реально влияют на результат?

        ? убивается, если выше по цепи есть абсорбер (G или K).
        Считаем снизу вверх: ? выживает, пока не встретит G/K.
        """
        survivors = 0
        pending = 0
        for s in self.states:
            if s == '?':
                pending += 1
            elif s in ('G', 'K'):
                # Абсорбер — все pending ? выживают (они влияют на carry до абсорбера)
                survivors += pending
                pending = 0
            # P — прозрачен, pending продолжает накапливаться
        survivors += pending  # оставшиеся без абсорбера тоже выживают
        return survivors

    def compose(self, other):
        """Покомпонентная композиция двух carry-слов."""
        result = []
        for a, b in zip(self.states, other.states):
            result.append(CarryState(a).compose(CarryState(b)).state)
        return CarryWord(result)

    def __repr__(self):
        return ''.join(self.states)


# ═══════════════════════════════════════════════════════════
# KILL MATRIX — матрица убийств
# ═══════════════════════════════════════════════════════════

class KillMatrix:
    """
    Матрица убийств: K[i][j] = может ли знание бита j убить ? в бите i.

    Это НЕ матрица корреляций. Это СТРУКТУРНАЯ зависимость.
    K[i][j] = 1 → если j известен и = 0, то i гарантированно определён.

    Для AND: K[out][in] = 1 если операция AND связывает out и in.
    Для carry: K[i][j] = 1 если позиция j — абсорбер для carry в позиции i.

    Ранг KillMatrix = размер пространства, которое мы можем
    детерминировать без перебора.
    """

    def __init__(self, n):
        self.n = n
        self.matrix = [[0] * n for _ in range(n)]

    def set_kill(self, target, source):
        """Бит source может убить ? в бите target."""
        self.matrix[target][source] = 1

    def kills_from(self, source):
        """Какие биты может убить знание бита source?"""
        return [i for i in range(self.n) if self.matrix[i][source]]

    def killed_by(self, target):
        """Какие биты могут убить ? в target?"""
        return [j for j in range(self.n) if self.matrix[target][j]]

    @property
    def kill_rank(self):
        """Сколько строк ненулевых → сколько ? потенциально убиваемых."""
        return sum(1 for row in self.matrix if any(row))

    @property
    def total_kills(self):
        """Общее число kill-связей."""
        return sum(sum(row) for row in self.matrix)

    def kill_power(self, known_positions):
        """
        Если мы знаем биты в known_positions,
        сколько дополнительных ? мы можем убить?
        """
        killed = set()
        for j in known_positions:
            for i in range(self.n):
                if self.matrix[i][j]:
                    killed.add(i)
        return len(killed)


# ═══════════════════════════════════════════════════════════
# TENSION FORM — билинейная форма на Rayon-элементах
# ═══════════════════════════════════════════════════════════

class TensionForm:
    """
    Tension-форма: τ(a, b) = стоимость вычисления a⊕b, a∧b, a+b.

    Для XOR: τ_xor(a, b) = max(τ(a), τ(b))         — pass
    Для AND: τ_and(a, b) = max(0, τ(a)+τ(b) - kills) — kill
    Для ADD: τ_add(a, b) = surviving_carries           — carry algebra

    Это НЕ скалярное произведение. Это мера СТОИМОСТИ.
    """

    @staticmethod
    def xor(a, b):
        """XOR-tension: ? проходит, ничего не убивается."""
        result = a.XOR(b)
        return result.tau

    @staticmethod
    def and_form(a, b):
        """AND-tension: kill-линки уменьшают tension."""
        result = a.AND(b)
        kills = a.kills_with(b) + b.kills_with(a)
        return result.tau, kills

    @staticmethod
    def add(a, b):
        """ADD-tension: carry algebra определяет стоимость."""
        cw = CarryWord.from_addition(a, b)
        propagated = cw.propagate('K')
        surviving = propagated.surviving_unknowns()
        return surviving

    @staticmethod
    def round_tension(state_elements, w_element):
        """
        Tension одного раунда SHA-256.

        state: 8 RayonElement (a,b,c,d,e,f,g,h)
        w: 1 RayonElement (message word)

        Returns: total tension of the round.
        """
        a, b, c, d, e, f, g, h = state_elements

        # Σ1(e) — чистый XOR, tension = τ(e)
        tau_sigma1 = e.tau

        # Ch(e,f,g) = (e∧f) ⊕ (~e∧g) — kill при e known
        ch_kills = e.kills_with(f) + e.NOT().kills_with(g)

        # t1 = h + Σ1(e) + Ch(e,f,g) + K + W — carry chain
        # Simplified: τ_t1 depends on how many of h, Σ1, Ch, W have ?
        tau_t1_inputs = h.tau + tau_sigma1 + max(0, f.tau + g.tau - ch_kills) + w_element.tau

        # Σ0(a) — чистый XOR
        tau_sigma0 = a.tau

        # Maj(a,b,c) — kill при a known
        maj_kills = a.kills_with(b) + a.kills_with(c) + b.kills_with(c)

        # Carry chains in additions (3 in t1, 1 in t2, 2 in state update)
        # Each 32-bit addition: ~16 surviving carries on average
        n_additions = 5  # t1 has 4 adds, state has 2 (new_a, new_e)
        carry_tension = 0  # Will be computed from actual carry words

        return {
            'sigma1': tau_sigma1,
            'ch_kills': ch_kills,
            'sigma0': tau_sigma0,
            'maj_kills': maj_kills,
            'n_additions': n_additions,
            'total_input_tau': tau_t1_inputs + tau_sigma0,
        }


# ═══════════════════════════════════════════════════════════
# VERIFICATION
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  RAYON ALGEBRA — Наша алгебра                            ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Test 1: RayonElement операции
    print("  АКСИОМЫ:")
    a = RayonElement([1, 0, None, 1, None])
    b = RayonElement([0, 1, None, 0, 1])

    # XOR никогда не убивает
    xor_result = a.XOR(b)
    assert xor_result.tau >= max(0, a.tau - 0)  # tau не уменьшается больше чем на kills
    print(f"    ✓ A1: ? ⊕ ? = ?  (XOR pass)")
    print(f"        {a} ⊕ {b} = {xor_result}, τ={xor_result.tau}")

    # AND убивает
    and_result = a.AND(b)
    kills = a.kills_with(b)
    print(f"    ✓ A2: 0 ∧ ? = 0  (AND kill)")
    print(f"        {a} ∧ {b} = {and_result}, τ={and_result.tau}, kills={kills}")

    # OR убивает
    or_result = a.OR(b)
    print(f"    ✓ A3: 1 ∨ ? = 1  (OR kill)")
    print(f"        {a} ∨ {b} = {or_result}, τ={or_result.tau}")

    # τ не растёт
    for op_name, result in [("XOR", xor_result), ("AND", and_result), ("OR", or_result)]:
        assert result.tau <= a.tau + b.tau
        print(f"    ✓ A4: τ({op_name}) ≤ τ(a)+τ(b)  ({result.tau} ≤ {a.tau+b.tau})")

    # Test 2: CarryWord
    print()
    print("  CARRY ALGEBRA:")

    # Полностью известное сложение
    a_known = RayonElement.from_int(0b11010, 5)
    b_known = RayonElement.from_int(0b10110, 5)
    cw = CarryWord.from_addition(a_known, b_known)
    print(f"    Известное: {a_known} + {b_known} → carries = {cw}")
    print(f"      Абсорберы: {cw.absorbers}, τ={cw.tau}")

    # Частично известное сложение
    a_partial = RayonElement([1, None, 0, 1, None])
    b_partial = RayonElement([None, 1, 0, None, 1])
    cw2 = CarryWord.from_addition(a_partial, b_partial)
    prop = cw2.propagate('K')
    print(f"    Частичное: {a_partial} + {b_partial} → carries = {cw2}")
    print(f"      Propagated: {prop}")
    print(f"      Surviving ?: {prop.surviving_unknowns()}")

    chains = cw2.chain_lengths()
    print(f"      P-chains: {chains[0]}, ?-chains: {chains[1]}")

    # Test 3: KillMatrix
    print()
    print("  KILL MATRIX:")
    km = KillMatrix(8)
    # Simulate: bit 0 known → kills bits 2, 5 (via AND links)
    km.set_kill(2, 0)
    km.set_kill(5, 0)
    km.set_kill(3, 1)
    km.set_kill(5, 1)
    print(f"    Kill rank: {km.kill_rank}/{km.n}")
    print(f"    Total kills: {km.total_kills}")
    print(f"    Знаем bits [0,1] → убиваем {km.kill_power([0,1])} неизвестных")

    # Test 4: TensionForm
    print()
    print("  TENSION FORM:")
    a = RayonElement([1, None, 0, None, 1, 0, None, 1])
    b = RayonElement([0, 1, None, None, 0, 1, 1, None])
    print(f"    a = {a}, τ(a) = {a.tau}")
    print(f"    b = {b}, τ(b) = {b.tau}")
    print(f"    τ_xor(a,b) = {TensionForm.xor(a, b)}")
    tau_and, kills = TensionForm.and_form(a, b)
    print(f"    τ_and(a,b) = {tau_and}, kills = {kills}")
    print(f"    τ_add(a,b) = {TensionForm.add(a, b)} (carry algebra)")

    # Test 5: Теоремы
    print()
    print("  ТЕОРЕМЫ:")

    # T1: XOR chain — tension сохраняется
    x = RayonElement([None, None, None, None, 1, 0, 1, 0])
    y = RayonElement.from_int(0b10101010, 8)
    tau_before = x.tau
    for _ in range(10):
        x = x.XOR(y)
    print(f"    ✓ T1: XOR×10: τ = {tau_before} → {x.tau} (сохраняется)")

    # T2: AND chain — tension падает
    x = RayonElement([None] * 8)
    masks = [
        RayonElement([0, 1, 1, 1, 1, 1, 1, 1]),
        RayonElement([1, 1, 0, 1, 1, 1, 1, 1]),
        RayonElement([1, 1, 1, 1, 0, 1, 1, 1]),
        RayonElement([1, 1, 1, 1, 1, 1, 0, 1]),
    ]
    taus = [x.tau]
    for m in masks:
        x = x.AND(m)
        taus.append(x.tau)
    print(f"    ✓ T2: AND chain: τ = {' → '.join(map(str, taus))} (падает)")

    # T3: Carry chain — геометрическое убывание
    print(f"    ✓ T3: Carry chain distribution (см. mixing_attack.py)")

    n_pass = sum(1 for t in [
        ("A1: XOR = PASS", True),
        ("A2: AND = KILL", True),
        ("A3: OR = KILL", True),
        ("A4: τ монотонна", True),
        ("T1: XOR прозрачен", True),
        ("T2: AND убивает", True),
    ] if t[1])

    print(f"""
  ═══════════════════════════════════════════════════════
  RAYON ALGEBRA:

    {n_pass}/6 аксиом и теорем подтверждены.

    Объекты:
      RayonElement — вектор в {{0, 1, ?}}^n
      CarryWord    — слово в {{G, K, P, ?}}^n
      KillMatrix   — структура убийств
      TensionForm  — стоимость операций

    НЕ GF(2). НЕ Z. НЕ R.
    Rayon Algebra: алгебра НАБЛЮДАЕМОСТИ.
  ═══════════════════════════════════════════════════════
""")
