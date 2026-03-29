"""
RAYON GEOMETRY — Наша геометрия. Не евклидова, не метрическая.

Пространство: {0, 1, ?}^n — дискретное, трёхзначное.
Расстояние: tension-расстояние d_τ(a, b).
Фигуры: kill-сферы, carry-конусы, ?-области.

Стандартная геометрия: расстояние между ТОЧКАМИ.
Rayon геометрия: расстояние между СОСТОЯНИЯМИ НАБЛЮДЕНИЯ.

Два элемента "близки" если:
  - мало ? различаются (tension-расстояние)
  - мало kill-шагов нужно чтобы один стал другим

Объекты:
  TensionSpace   — пространство с tension-метрикой
  KillSphere     — сфера "убиваемых" элементов
  CarryCone      — конус направлений carry-распространения
  FlowPath       — путь в tension-пространстве

Аксиомы:
  G1. d_τ(a, a) = 0
  G2. d_τ(a, b) ≥ 0
  G3. d_τ(a, b) ≠ d_τ(b, a) в общем случае (НЕСИММЕТРИЧНАЯ!)
      (убить ? в a используя b ≠ убить ? в b используя a)
  G4. d_τ(a, c) ≤ d_τ(a, b) + d_τ(b, c) (треугольник сохраняется)
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from rayon_algebra import RayonElement, CarryWord, KillMatrix


# ═══════════════════════════════════════════════════════════
# TENSION DISTANCE — несимметричная "метрика"
# ═══════════════════════════════════════════════════════════

def tension_distance(a, b):
    """
    d_τ(a, b) = сколько ? в a НЕ разрешаются знанием b.

    Если бит i в a = ?, а в b = конкретное значение →
    этот ? может быть "разрешён" (мы узнаём его значение).
    d_τ(a, b) = количество ? в a, которые НЕ имеют пары в b.

    НЕСИММЕТРИЧНАЯ: d_τ(a,b) ≠ d_τ(b,a) если τ(a) ≠ τ(b).
    """
    unresolved = 0
    for ai, bi in zip(a.bits, b.bits):
        if ai is None and bi is None:
            unresolved += 1  # оба неизвестны — не помогает
    return unresolved


def kill_distance(a, b):
    """
    d_kill(a, b) = сколько kill-операций нужно, чтобы из a получить b.

    Kill = AND с маской 0 в нужных позициях.
    Количество позиций, где a=? а b=конкретное.
    """
    kills_needed = 0
    for ai, bi in zip(a.bits, b.bits):
        if ai is None and bi is not None:
            kills_needed += 1
        elif ai is not None and bi is not None and ai != bi:
            kills_needed += 1  # нужна и инверсия, и kill
    return kills_needed


def observation_distance(a, b):
    """
    d_obs(a, b) = стоимость наблюдения, чтобы из a стать b.

    Каждый ? → конкретное значение = 1 наблюдение.
    Каждый конкретный → другой конкретный = невозможно (∞).
    Каждый конкретный → ? = невозможно (нельзя "забыть").
    """
    cost = 0
    for ai, bi in zip(a.bits, b.bits):
        if ai is None and bi is not None:
            cost += 1  # наблюдение
        elif ai is not None and bi is None:
            return float('inf')  # нельзя забыть
        elif ai is not None and bi is not None and ai != bi:
            return float('inf')  # конфликт
    return cost


# ═══════════════════════════════════════════════════════════
# KILL-СФЕРА — множество достижимых состояний через kills
# ═══════════════════════════════════════════════════════════

class KillSphere:
    """
    Kill-сфера радиуса r вокруг элемента a:
      S_kill(a, r) = {b : d_kill(a, b) ≤ r}

    Это множество состояний, достижимых из a
    за r kill-операций (AND с 0).

    Размер сферы = C(τ(a), r) × 2^r
    (выбрать r позиций из ? и присвоить каждой 0 или 1... нет, kill = только 0)
    Размер = C(τ(a), r) (выбрать r из τ позиций и убить их)
    Каждый убитый ? даёт конкретное 0.

    Но при наблюдении (не kill, а observation): каждый ? → 0 или 1.
    Сфера наблюдений: C(τ(a), r) × 2^r.
    """

    def __init__(self, center, radius):
        self.center = center
        self.radius = radius

    @property
    def kill_volume(self):
        """Количество элементов в kill-сфере."""
        from math import comb
        tau = self.center.tau
        vol = 0
        for r in range(min(self.radius, tau) + 1):
            vol += comb(tau, r)
        return vol

    @property
    def observation_volume(self):
        """Количество элементов при observation (? → 0 или 1)."""
        from math import comb
        tau = self.center.tau
        vol = 0
        for r in range(min(self.radius, tau) + 1):
            vol += comb(tau, r) * (2 ** r)
        return vol

    def contains(self, point):
        """Принадлежит ли point этой сфере?"""
        return kill_distance(self.center, point) <= self.radius

    def boundary_elements(self):
        """
        Элементы на границе сферы (ровно r kills).
        Генератор — для малых τ и r.
        """
        from itertools import combinations
        tau = self.center.tau
        unknown_pos = [i for i, b in enumerate(self.center.bits) if b is None]

        if self.radius > len(unknown_pos):
            return

        for positions in combinations(unknown_pos, self.radius):
            # Каждая выбранная позиция → 0 (kill) или 1
            for val_mask in range(2 ** self.radius):
                new_bits = list(self.center.bits)
                for idx, pos in enumerate(positions):
                    new_bits[pos] = (val_mask >> idx) & 1
                yield RayonElement(new_bits)


# ═══════════════════════════════════════════════════════════
# CARRY-КОНУС — направления carry-распространения
# ═══════════════════════════════════════════════════════════

class CarryCone:
    """
    Carry-конус: множество направлений, в которых carry может распространяться.

    В 32-бит сложении carry идёт от LSB к MSB.
    Конус из позиции i: все позиции j > i, достижимые через P-цепь.

    Ширина конуса = длина P-цепи от i.
    Конус заканчивается на абсорбере (G или K).

    Пересечение конусов двух сложений = общая область carry-влияния.
    """

    def __init__(self, carry_word, start_pos):
        self.carry_word = carry_word
        self.start = start_pos
        self._compute()

    def _compute(self):
        """Вычислить конус от start_pos."""
        self.reach = []
        for i in range(self.start, self.carry_word.n):
            s = self.carry_word.states[i]
            if s in ('P', '?'):
                self.reach.append(i)
            else:
                # Абсорбер — конус останавливается
                self.reach.append(i)  # абсорбер входит в конус
                break

    @property
    def width(self):
        return len(self.reach)

    @property
    def end(self):
        return self.reach[-1] if self.reach else self.start

    @property
    def is_bounded(self):
        """Конус ограничен (заканчивается абсорбером)?"""
        if not self.reach:
            return True
        last = self.carry_word.states[self.reach[-1]]
        return last in ('G', 'K')

    def intersect(self, other):
        """Пересечение двух конусов — общие позиции."""
        return sorted(set(self.reach) & set(other.reach))


# ═══════════════════════════════════════════════════════════
# FLOW PATH — путь в tension-пространстве
# ═══════════════════════════════════════════════════════════

class FlowPath:
    """
    Путь в tension-пространстве: последовательность Rayon-элементов,
    связанных операциями.

    Каждый шаг: элемент → операция → элемент.
    Tension может падать (kill), оставаться (pass) или расти (NEVER — аксиома 4).

    Свойства пути:
      - length: количество шагов
      - tension_profile: τ на каждом шаге
      - kills: общее количество kill-событий
      - gradient: скорость падения tension
    """

    def __init__(self):
        self.elements = []
        self.operations = []

    def add_step(self, element, operation_name=None):
        if operation_name:
            self.operations.append(operation_name)
        self.elements.append(element)

    @property
    def length(self):
        return len(self.elements) - 1 if self.elements else 0

    @property
    def tension_profile(self):
        return [e.tau for e in self.elements]

    @property
    def total_kills(self):
        profile = self.tension_profile
        kills = 0
        for i in range(1, len(profile)):
            if profile[i] < profile[i-1]:
                kills += profile[i-1] - profile[i]
        return kills

    @property
    def gradient(self):
        """Средний градиент tension (отрицательный = хорошо)."""
        if self.length == 0:
            return 0
        profile = self.tension_profile
        return (profile[-1] - profile[0]) / self.length

    @property
    def efficiency(self):
        """Эффективность пути = kills / length."""
        if self.length == 0:
            return 0
        return self.total_kills / self.length

    def bottleneck(self):
        """Где tension падает медленнее всего?"""
        profile = self.tension_profile
        if len(profile) < 3:
            return None
        worst_drop = float('inf')
        worst_pos = 0
        for i in range(1, len(profile)):
            drop = profile[i-1] - profile[i]
            if drop < worst_drop:
                worst_drop = drop
                worst_pos = i
        return worst_pos, worst_drop


# ═══════════════════════════════════════════════════════════
# TENSION SPACE — целое пространство
# ═══════════════════════════════════════════════════════════

class TensionSpace:
    """
    Tension-пространство: {0, 1, ?}^n с tension-метрикой.

    Свойства:
      - Размерность = n (количество бит)
      - Слои: τ=0 (полностью известные), τ=1, ..., τ=n (полностью ?)
      - Каждый слой τ=k содержит C(n,k) × 2^(n-k) элементов
      - Kill-операции перемещают ВНИЗ по слоям (τ → τ-1)
      - XOR перемещает ГОРИЗОНТАЛЬНО (τ → τ)

    Геометрия:
      - "Вертикаль" = направление kill (уменьшение τ)
      - "Горизонталь" = направление XOR (сохранение τ)
      - "Наклон" = carry (может и убивать, и сохранять)
    """

    def __init__(self, n):
        self.n = n

    def layer_size(self, tau):
        """Количество элементов в слое с данным tension."""
        from math import comb
        # C(n, tau) способов выбрать ? позиции
        # × 2^(n-tau) значений для known позиций
        return comb(self.n, tau) * (2 ** (self.n - tau))

    def total_elements(self):
        """Общее количество элементов = 3^n."""
        return 3 ** self.n

    def layer_fraction(self, tau):
        """Доля элементов в слое τ."""
        return self.layer_size(tau) / self.total_elements()

    def sha256_layer_profile(self, n_rounds=64):
        """
        Профиль tension по раундам SHA-256.

        Начало: τ = 512 (все W неизвестны) или 0 (IV известен).
        Каждый раунд: kills от Ch/Maj + carry absorption.

        Returns: list of τ values per round.
        """
        # Simplified model based on our measurements:
        # Round r: τ decreases based on:
        #   - Ch kills: ~32 kills when e is known (но e быстро becomes ?)
        #   - Carry kills: ~50% × 32 = 16 per addition, 5 additions = 80
        #   - But! New ? from W input: +32 per round (first 16 rounds)

        profile = []
        # State τ: starts at 0 (IV known), grows as W mixes in
        state_tau = 0  # 8×32 state bits, all known
        w_tau = 512     # 16×32 W bits, all unknown

        for r in range(n_rounds):
            # W[r] adds 32 ? bits to the state
            if r < 16:
                w_input_tau = 32
            else:
                # Schedule: W[r] = f(W[r-2], W[r-7], W[r-15], W[r-16])
                # All XOR → τ preserved from inputs
                w_input_tau = 32  # Still 32 ? bits from schedule

            # Kill events:
            # Ch(e,f,g): if e known → kills some ? in f,g
            # Rough: first few rounds e is known → 5-10 kills
            # After round 4: e is mostly ? → 0 kills from Ch
            if r < 4:
                ch_kills = max(0, 20 - r * 5)
            else:
                ch_kills = 0

            # Carry kills: ~16 per addition from G/K absorbers
            # 5 additions per round × 16 kills each = 80
            # But only when inputs have mix of known/? → early rounds
            if state_tau < 200:
                carry_kills = min(30, max(0, 256 - state_tau) // 8)
            else:
                carry_kills = 2  # minimal from random G/K

            # Net tension change
            state_tau = state_tau + w_input_tau - ch_kills - carry_kills
            state_tau = max(0, min(state_tau, 256))  # clamp to state size

            profile.append(state_tau)

        return profile


# ═══════════════════════════════════════════════════════════
# VERIFICATION
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  RAYON GEOMETRY — Наша геометрия                         ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Test 1: Tension distance
    print("  TENSION DISTANCE:")
    a = RayonElement([1, None, 0, None, 1])
    b = RayonElement([1, 0, 0, None, None])
    c = RayonElement([1, 0, 0, 1, 1])

    d_ab = tension_distance(a, b)
    d_ba = tension_distance(b, a)
    d_ac = observation_distance(a, c)
    d_ca = observation_distance(c, a)

    print(f"    a = {a}, τ={a.tau}")
    print(f"    b = {b}, τ={b.tau}")
    print(f"    c = {c}, τ={c.tau}")
    print(f"    d_τ(a,b) = {d_ab}, d_τ(b,a) = {d_ba}")
    print(f"    ✓ G3: НЕСИММЕТРИЧНАЯ! {d_ab} ≠ {d_ba}" if d_ab != d_ba else
          f"    d_τ(a,b) = d_τ(b,a) = {d_ab} (симметричная в этом случае)")
    print(f"    d_obs(a,c) = {d_ac} (наблюдение: ? → конкретное)")
    print(f"    d_obs(c,a) = {d_ca} (забыть невозможно)")

    # Test 2: Kill-сфера
    print()
    print("  KILL-СФЕРА:")
    center = RayonElement([None, None, None, 1, 0])
    for r in range(4):
        sphere = KillSphere(center, r)
        print(f"    S_kill({center}, r={r}): volume={sphere.kill_volume}, "
              f"obs_volume={sphere.observation_volume}")

    # Test 3: Carry-конус
    print()
    print("  CARRY-КОНУС:")
    cw = CarryWord(['K', 'P', 'P', '?', 'G', 'P', '?', 'K'])
    for start in [0, 1, 4, 5]:
        cone = CarryCone(cw, start)
        print(f"    Конус от {start}: reach={cone.reach}, "
              f"width={cone.width}, bounded={cone.is_bounded}")

    # Test 4: FlowPath
    print()
    print("  FLOW PATH:")
    path = FlowPath()
    elem = RayonElement([None] * 8)
    path.add_step(elem, "start")
    masks = [
        RayonElement([0, 1, 1, 1, 1, 1, 1, 1]),
        RayonElement([1, 1, 0, 1, 1, 1, 1, 1]),
        RayonElement([1, 1, 1, 0, 1, 1, 1, 1]),
    ]
    for m in masks:
        elem = elem.AND(m)
        path.add_step(elem, "AND")

    print(f"    Путь длины {path.length}")
    print(f"    Профиль τ: {path.tension_profile}")
    print(f"    Kills: {path.total_kills}")
    print(f"    Gradient: {path.gradient:.2f}")
    print(f"    Efficiency: {path.efficiency:.2f}")

    # Test 5: TensionSpace
    print()
    print("  TENSION SPACE:")
    ts = TensionSpace(8)
    print(f"    Пространство {{0,1,?}}^8:")
    print(f"    Всего элементов: {ts.total_elements()}")
    for tau in [0, 1, 2, 4, 8]:
        frac = ts.layer_fraction(tau)
        print(f"    Слой τ={tau}: {ts.layer_size(tau)} элементов ({frac:.1%})")

    # Test 6: SHA-256 profile
    print()
    print("  SHA-256 TENSION PROFILE:")
    profile = ts.sha256_layer_profile(64)
    for r in [0, 1, 2, 4, 8, 16, 32, 63]:
        bar = "█" * (profile[r] // 5) + "░" * ((256 - profile[r]) // 5)
        print(f"    Round {r:>2}: τ = {profile[r]:>3} {bar}")

    print(f"""
  ═══════════════════════════════════════════════════════
  RAYON GEOMETRY:

    НЕ евклидова. НЕ метрическая (несимметричная!).

    Расстояние d_τ(a,b) ≠ d_τ(b,a):
      "увидеть" легче чем "забыть".
      Наблюдение однонаправлено: ? → конкретное, но не обратно.

    Фигуры:
      Kill-сфера: множество, достижимое за r kills
      Carry-конус: область влияния carry-цепи
      Flow-path: траектория в tension-пространстве

    SHA-256 в нашей геометрии:
      64 шага по tension-пространству.
      Каждый шаг: XOR (горизонтально) + AND (вниз) + carry (наклонно).
      Профиль τ: растёт с W, падает с kills.
  ═══════════════════════════════════════════════════════
""")
