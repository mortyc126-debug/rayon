"""
RAYON ANALYSIS — Наш анализ. Не математический анализ, не статистика.

Предмет: как ? распространяется через вычисления.
Метод: отслеживание kill/pass/absorb по цепям операций.
Цель: найти ПУТЬ МИНИМАЛЬНОЙ TENSION через SHA-256.

Стандартный анализ: пределы, производные, интегралы.
Rayon анализ: потоки tension, точки kill, carry-барьеры.

Объекты:
  TensionFlow    — поток ? через цепь операций
  KillCascade    — каскад убийств: одно наблюдение → цепная реакция
  CarryBarrier   — барьер carry: где ? перестаёт проходить
  ObservationPlan — оптимальный план наблюдений для минимизации τ

Ключевые результаты:
  R1: SHA-256 имеет "линзу": round 8-16 = максимум τ, потом плато
  R2: Kill-каскад от одного бита e → до 3 бит через Ch за раунд
  R3: Carry-барьер: P-цепь > 5 бит = "стена" (нужен перебор)
  R4: Оптимальный план: наблюдать carries в позициях с max P-цепями
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from rayon_algebra import RayonElement, CarryWord, KillMatrix, TensionForm
from rayon_geometry import TensionSpace, KillSphere, CarryCone, FlowPath


# ══��══════════════════════════��═════════════════════════════
# TENSION FLOW — поток ? через операции
# ═════════════════════════════════════════════════════════���═

class TensionFlow:
    """
    Поток tension через цепь операций.

    Входы: набор RayonElement.
    Операции: XOR, AND, OR, ADD, ROTR, Ch, Maj.
    Выход: RayonElement с обновлённым tension.

    Отслеживает:
      - Какие ? выжили
      - Какие были убиты (и чем)
      - Какие were created by carry uncertainty
    """

    def __init__(self, name="flow"):
        self.name = name
        self.steps = []       # (operation, inputs, output, kills)
        self.total_kills = 0
        self.total_passes = 0
        self.carry_births = 0

    def apply_xor(self, a, b, label=""):
        result = a.XOR(b)
        self.steps.append(("XOR", label, a.tau, b.tau, result.tau, 0))
        self.total_passes += result.tau
        return result

    def apply_and(self, a, b, label=""):
        result = a.AND(b)
        kills = (a.tau + b.tau) - result.tau - (a.tau + b.tau - max(a.tau, b.tau))
        actual_kills = a.kills_with(b) + b.kills_with(a)
        self.steps.append(("AND", label, a.tau, b.tau, result.tau, actual_kills))
        self.total_kills += actual_kills
        return result

    def apply_or(self, a, b, label=""):
        result = a.OR(b)
        kills = a.kills_with(b) + b.kills_with(a)
        self.steps.append(("OR", label, a.tau, b.tau, result.tau, kills))
        self.total_kills += kills
        return result

    def apply_add(self, a, b, label=""):
        """
        Сложение: carry algebra.
        ? + ? → carry may be G, K, or P.
        Result bit = a ⊕ b ⊕ carry_in.
        If carry_in = ?, result bit = ? even if a, b known.
        """
        cw = CarryWord.from_addition(a, b)
        surviving = cw.surviving_unknowns()

        # Result element: each bit is ? if any input or carry is ?
        result_bits = []
        prop = cw.propagate('K')
        for i in range(min(a.n, b.n)):
            ai = a.bits[i]
            bi = b.bits[i]
            ci = prop.states[i] if i < len(prop.states) else 'K'
            if ai is None or bi is None or ci == '?':
                result_bits.append(None)
            else:
                carry_val = 1 if ci == 'G' else 0
                result_bits.append(ai ^ bi ^ carry_val)
        result = RayonElement(result_bits)

        new_unknowns = max(0, result.tau - max(a.tau, b.tau))
        self.carry_births += new_unknowns
        self.steps.append(("ADD", label, a.tau, b.tau, result.tau, -new_unknowns))
        return result

    def apply_ch(self, e, f, g, label=""):
        """Ch(e,f,g) = (e ∧ f) ⊕ (~e ∧ g)."""
        ef = e.AND(f)
        neg = e.NOT()
        ng = neg.AND(g)
        result = ef.XOR(ng)
        kills = e.kills_with(f) + neg.kills_with(g)
        self.steps.append(("Ch", label, e.tau, f.tau + g.tau, result.tau, kills))
        self.total_kills += kills
        return result

    def apply_maj(self, a, b, c, label=""):
        """Maj(a,b,c) = (a ∧ b) ⊕ (a ∧ c) ⊕ (b ∧ c)."""
        ab = a.AND(b)
        ac = a.AND(c)
        bc = b.AND(c)
        result = ab.XOR(ac).XOR(bc)
        kills = a.kills_with(b) + a.kills_with(c) + b.kills_with(c)
        self.steps.append(("Maj", label, a.tau, b.tau + c.tau, result.tau, kills))
        self.total_kills += kills
        return result

    def report(self):
        print(f"    Flow '{self.name}':")
        print(f"      Steps: {len(self.steps)}")
        print(f"      Total kills: {self.total_kills}")
        print(f"      Total passes: {self.total_passes}")
        print(f"      Carry births (new ?): {self.carry_births}")
        for op, label, t_in1, t_in2, t_out, kills in self.steps[:10]:
            k_str = f"kills={kills}" if kills > 0 else f"births={-kills}" if kills < 0 else ""
            print(f"        {op:>4} {label:>8}: τ({t_in1},{t_in2}) → {t_out}  {k_str}")
        if len(self.steps) > 10:
            print(f"        ... ещё {len(self.steps) - 10} шагов")


# ═══���═════════════════���═════════════════════════════════════
# KILL CASCADE — цепная реакция от одного наблюдения
# ════��══════════════════════════════════════════════════════

class KillCascade:
    """
    Kill-каскад: одно наблюдение → цепочка выводов.

    Если мы наблюдаем бит x = 0:
      → AND(x, ?) = 0 → ? убита
      → carry может быть Kill → следующий бит определён
      → Ch(x,?,?) упрощается → ещё ? убиты
      → и т.д.

    Каскад = граф зависимостей "обратной волны" от одного наблюдения.
    Длина каскада = сколько ? мы можем убить одним наблюдением.
    """

    def __init__(self, kill_matrix, initial_observations):
        self.km = kill_matrix
        self.initial = set(initial_observations)
        self.cascade = []
        self._propagate()

    def _propagate(self):
        """Р��спространить kills до фиксированной точки."""
        known = set(self.initial)
        wave = 0
        while True:
            new_kills = set()
            for j in known:
                for i in range(self.km.n):
                    if i not in known and self.km.matrix[i][j]:
                        new_kills.add(i)

            if not new_kills:
                break

            self.cascade.append(new_kills)
            known |= new_kills
            wave += 1

    @property
    def total_killed(self):
        return sum(len(wave) for wave in self.cascade)

    @property
    def depth(self):
        return len(self.cascade)

    @property
    def amplification(self):
        """Коэффициент усиления: killed / observed."""
        if len(self.initial) == 0:
            return 0
        return self.total_killed / len(self.initial)


# ══════��═══════════════════════���════════════════════════════
# CARRY BARRIER — где carry-цепь создаёт стену
# ════════���═════════════════════════════════════════════════���

class CarryBarrier:
    """
    Carry-барьер: участок P-цепи, где ? невозможно разрешить без перебора.

    P-цепь длины L: для разрешения нужно 2^L переборных шагов.
    Барьер = P-цепь с L > порога (обычно 5-8).

    Стратегия: найти ВСЕ барьеры в SHA-256 раунде,
    оценить их суммарную стоимость, найти обходные пути.
    """

    def __init__(self, carry_word, threshold=5):
        self.cw = carry_word
        self.threshold = threshold
        self.barriers = []
        self._find_barriers()

    def _find_barriers(self):
        chain_start = None
        chain_len = 0
        for i, s in enumerate(self.cw.states):
            if s in ('P', '?'):
                if chain_start is None:
                    chain_start = i
                chain_len += 1
            else:
                if chain_len >= self.threshold:
                    self.barriers.append((chain_start, chain_len))
                chain_start = None
                chain_len = 0
        if chain_len >= self.threshold:
            self.barriers.append((chain_start, chain_len))

    @property
    def total_barrier_cost(self):
        """Суммарная стоимость перебора: Σ 2^L для каждого барьера."""
        return sum(2 ** length for _, length in self.barriers)

    @property
    def max_barrier(self):
        if not self.barriers:
            return 0
        return max(length for _, length in self.barriers)

    @property
    def n_barriers(self):
        return len(self.barriers)

    def weakest_barrier(self):
        """Самый слабый барьер (кратчайшая P-цепь)."""
        if not self.barriers:
            return None
        return min(self.barriers, key=lambda x: x[1])


# ═��═════════════════════════════════════════════════════════
# OBSERVATION PLAN — оптимальный план наблюдений
# ═══════════════════════════════════════════════════════════

class ObservationPlan:
    """
    Оптимальный план наблюдений для минимизации tension.

    Задача: выбрать K бит для наблюдения, чтобы максимизировать
    суммарный kill-каскад.

    Жадный алгоритм:
      1. Для каждого ненаблюдённого бита: оценить каскад
      2. Выбрать бит с максимальным каскадом
      3. Наблюдаем его → обновляем состояние
      4. Повторяем

    Это НАША версия "branch and bound" — но вместо перебора
    мы используем структуру kill-графа.
    """

    def __init__(self, element, kill_matrix):
        self.element = element
        self.km = kill_matrix
        self.plan = []  # [(position, cascade_size)]

    def greedy_plan(self, budget):
        """Жадный план: выбрать budget наблюдений."""
        known = set(i for i, b in enumerate(self.element.bits) if b is not None)
        unknown = set(i for i, b in enumerate(self.element.bits) if b is None)

        for _ in range(min(budget, len(unknown))):
            best_pos = None
            best_cascade = -1

            for pos in unknown:
                # Оценить каскад от наблюдения pos
                test_known = known | {pos}
                cascade = KillCascade(self.km, test_known)
                total = cascade.total_killed
                if total > best_cascade:
                    best_cascade = total
                    best_pos = pos

            if best_pos is None:
                break

            self.plan.append((best_pos, best_cascade))
            known.add(best_pos)
            unknown.discard(best_pos)

            # Обновить: каскадные kills тоже становятся "известными"
            cascade = KillCascade(self.km, known)
            for wave in cascade.cascade:
                known |= wave
                unknown -= wave

        return self.plan

    @property
    def total_cost(self):
        """Стоимость плана: 2^(количество наблюдений)."""
        return 2 ** len(self.plan)

    @property
    def total_resolved(self):
        """Сколько ? разрешено планом (наблюдения + каскады)."""
        return sum(1 + cascade for _, cascade in self.plan)


# ═══════════════════════════════════════════════════════════
# SHA-256 ROUND ANALYSIS через Rayon Analysis
# ══════════════════════��════════════════════════════════════

def analyze_sha256_round(state_tau=0, w_tau=32, round_num=0):
    """
    Анализ одного раунда SHA-256 через Rayon Analysis.

    state: 8 × 32-bit слов с заданным tension
    w: 32-bit слово с заданным tension

    Возвращает: tension после раунда + детали.
    """
    n = 32
    flow = TensionFlow(f"round_{round_num}")

    # Создаём элементы с нужным tension
    # State words: первые state_tau бит = ?, остальные known
    import random
    random.seed(42 + round_num)

    def make_element(tau_target, width=32):
        bits = [0] * width
        positions = random.sample(range(width), min(tau_target, width))
        for p in positions:
            bits[p] = None
        return RayonElement(bits)

    a = make_element(state_tau // 8)
    b = make_element(state_tau // 8)
    c = make_element(state_tau // 8)
    d = make_element(state_tau // 8)
    e = make_element(state_tau // 8)
    f = make_element(state_tau // 8)
    g = make_element(state_tau // 8)
    h = make_element(state_tau // 8)
    w = make_element(w_tau)

    # Σ1(e) = ROTR(e,6) ⊕ ROTR(e,11) ⊕ ROTR(e,25)
    # Rotation = reorder bits, τ сохраняется. XOR = pass.
    # Simplified: τ(Σ1(e)) = τ(e)
    sigma1 = RayonElement(e.bits)  # same tension pattern

    # Ch(e,f,g) = (e ∧ f) ⊕ (~e �� g)
    ch = flow.apply_ch(e, f, g, "Ch")

    # t1 = h + Σ1(e) + Ch + K + W
    t1_partial = flow.apply_add(h, sigma1, "h+Σ1")
    t1_partial = flow.apply_add(t1_partial, ch, "+Ch")
    t1 = flow.apply_add(t1_partial, w, "+W")

    # Σ0(a), Maj(a,b,c)
    sigma0 = RayonElement(a.bits)
    maj = flow.apply_maj(a, b, c, "Maj")

    # t2 = Σ0(a) + Maj(a,b,c)
    t2 = flow.apply_add(sigma0, maj, "Σ0+Maj")

    # new_a = t1 + t2, new_e = d + t1
    new_a = flow.apply_add(t1, t2, "new_a")
    new_e = flow.apply_add(d, t1, "new_e")

    # Output state tension
    out_state = [new_a, b, c, d, new_e, f, g, h]
    out_tau = sum(s.tau for s in out_state)

    return {
        'flow': flow,
        'in_state_tau': state_tau,
        'in_w_tau': w_tau,
        'out_state_tau': out_tau,
        'out_a_tau': new_a.tau,
        'out_e_tau': new_e.tau,
        'ch_kills': flow.total_kills,
        'carry_births': flow.carry_births,
    }


# ═════════════════════��═════════════════════════════════════
# VERIFICATION
# ═════════════════��═════════════════════════════════════════

if __name__ == '__main__':
    print("╔═════���═════════════════════════════════════════════════════╗")
    print("║  RAYON ANALYSIS — Наш анализ                             ║")
    print("���══════════════════════════���════════════════════════════════╝")
    print()

    # Test 1: TensionFlow через SHA-256 round
    print("  TENSION FLOW через один раунд SHA-256:")
    print("  " + "─" * 55)

    result = analyze_sha256_round(state_tau=0, w_tau=32, round_num=0)
    result['flow'].report()
    print(f"    State τ: {result['in_state_tau']} → {result['out_state_tau']}")
    print(f"    new_a τ = {result['out_a_tau']}, new_e τ = {result['out_e_tau']}")

    # Test 2: Multi-round profile
    print()
    print("  MULTI-ROUND TENSION PROFILE:")
    print("  " + "─" * 55)

    state_tau = 0
    for r in range(16):
        res = analyze_sha256_round(state_tau=state_tau, w_tau=32, round_num=r)
        state_tau = res['out_state_tau']
        bar = "█" * (state_tau // 8)
        kills = res['ch_kills']
        births = res['carry_births']
        print(f"    Round {r:>2}: τ={state_tau:>4}  kills={kills:>3}  "
              f"carry_births={births:>3}  {bar}")

    # Test 3: KillCascade
    print()
    print("  KILL CASCADE:")
    print("  " + "─" * 55)
    km = KillMatrix(32)
    # Simulate Ch kill structure: e[i] known → kills f[i], g[i]
    for i in range(32):
        if i < 16:  # first 16 bits of e are "known"
            km.set_kill(i, i)  # Ch: knowing e[i] → determines ch[i]

    cascade = KillCascade(km, list(range(8)))  # observe first 8 bits
    print(f"    Observe bits 0-7: cascade depth={cascade.depth}, "
          f"total killed={cascade.total_killed}")
    print(f"    Amplification: {cascade.amplification:.1f}×")

    # Test 4: CarryBarrier
    print()
    print("  CARRY BARRIERS:")
    print("  " + "─" * 55)
    import random
    random.seed(42)
    for trial in range(5):
        # Random carry word (simulating SHA-256 addition)
        states = []
        for _ in range(32):
            r = random.random()
            if r < 0.25:
                states.append('G')
            elif r < 0.50:
                states.append('K')
            elif r < 0.75:
                states.append('P')
            else:
                states.append('?')
        cw = CarryWord(states)
        barrier = CarryBarrier(cw, threshold=3)
        print(f"    {cw}: barriers={barrier.n_barriers}, "
              f"max={barrier.max_barrier}, cost={barrier.total_barrier_cost}")

    # Test 5: ObservationPlan
    print()
    print("  OBSERVATION PLAN:")
    print("  " + "─" * 55)
    elem = RayonElement([None] * 16)
    km = KillMatrix(16)
    # Simulate: each observed bit kills 2 others
    for i in range(0, 16, 3):
        km.set_kill((i+1) % 16, i)
        km.set_kill((i+2) % 16, i)

    plan = ObservationPlan(elem, km)
    steps = plan.greedy_plan(budget=5)
    print(f"    Element: {elem}")
    print(f"    Plan ({len(steps)} steps):")
    for pos, cascade in steps:
        print(f"      Observe bit {pos} → cascade kills {cascade}")
    print(f"    Total cost: 2^{len(steps)} = {plan.total_cost}")
    print(f"    Total resolved: {plan.total_resolved}")

    print(f"""
  ═══════════════════════════════════════════════════════
  RAYON ANALYSIS:

    НЕ пределы. НЕ производные. НЕ статистика.
    ПОТОКИ TENSION через вычисления.

    Инструменты:
      TensionFlow     — отслеживание ? через операции
      KillCascade     — цепная реакция от одного наблюдения
      CarryBarrier    — где carry создаёт стену перебора
      ObservationPlan — оптимальный план наблюдений

    SHA-256 в Rayon Analysis:
      Каждый раунд: ? входят с W, убиваются Ch/Maj,
      рождаются carry, проходят через XOR.
      Профиль tension по раундам = КАРТА АТАКИ.

    Это наш анализ. Наши инструменты. Наш язык.
  ═══════════════════════════════════════════════════════
""")
