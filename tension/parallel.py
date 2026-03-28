"""
STONE 21: PARALLELISM — Concurrent tension flows.

Tension is not sequential. Independent computations don't
add tension — they happen "at the same time." Only dependencies
force sequential accumulation.

    Independent flows: total tension = max(individual tensions)
    Dependent flows:   total tension = sum(individual tensions)

This is the parallel advantage: if you can decompose a problem
into independent parts, tension grows as the WORST part, not
the SUM of all parts.

ParallelFlow:  run independent computations simultaneously
TensionBarrier: synchronization point — all flows must resolve
MapParallel:   apply function to array elements in parallel
RaceFlow:      run multiple approaches, take the first to resolve
"""

from rayon_numbers import RayonInt


# ════════════════════════════════════════════════════════════════
# PARALLEL FLOW
# ════════════════════════════════════════════════════════════════

class FlowResult:
    """Result of a single flow: a value with its tension cost."""
    def __init__(self, value, tension, name=None):
        self.value = value
        self.tension = tension
        self.name = name or "anonymous"

    def __repr__(self):
        return f"FlowResult({self.name}: value={self.value}, τ={self.tension})"


class ParallelFlow:
    """
    Run multiple independent computations simultaneously.

    Each flow has its own tension. Because the flows are independent,
    total tension = max(individual tensions). They don't add.

    If flows are marked dependent, tension = sum instead.
    """
    def __init__(self):
        self.flows = []       # list of (name, callable)
        self.dependent = False

    def add(self, name, fn):
        """Add a named flow. fn() -> RayonInt or value with .tension."""
        self.flows.append((name, fn))
        return self

    def set_dependent(self, dep=True):
        """Mark flows as dependent (tension sums instead of maxes)."""
        self.dependent = dep
        return self

    def run(self):
        """Execute all flows and compute combined tension."""
        results = []
        for name, fn in self.flows:
            result = fn()
            if isinstance(result, RayonInt):
                results.append(FlowResult(result, result.tension, name))
            elif isinstance(result, FlowResult):
                results.append(result)
            else:
                results.append(FlowResult(result, 0, name))

        tensions = [r.tension for r in results]

        if self.dependent:
            total_tension = sum(tensions)
        else:
            total_tension = max(tensions) if tensions else 0

        return ParallelResult(results, total_tension, self.dependent)


class ParallelResult:
    """Combined result of a parallel execution."""
    def __init__(self, results, total_tension, dependent):
        self.results = results
        self.total_tension = total_tension
        self.dependent = dependent

    @property
    def individual_tensions(self):
        return [r.tension for r in self.results]

    def __repr__(self):
        mode = "dependent(sum)" if self.dependent else "independent(max)"
        return (f"ParallelResult({mode}, τ_total={self.total_tension}, "
                f"individual={self.individual_tensions})")


# ════════════════════════════════════════════════════════════════
# TENSION BARRIER
# ════════════════════════════════════════════════════════════════

class TensionBarrier:
    """
    Synchronization point where all flows must resolve.

    If any flow still has ? (tension > 0), the barrier reports
    unresolved flows. Resolution can happen by:
      - Constraining ? bits (reducing tension to 0)
      - Branching (splitting into concrete cases)

    The barrier blocks (returns unresolved) until all tensions are 0.
    """
    def __init__(self, name="barrier"):
        self.name = name

    def check(self, parallel_result):
        """
        Check if all flows have resolved (tension = 0).
        Returns (passed, unresolved_flows).
        """
        unresolved = [r for r in parallel_result.results if r.tension > 0]
        passed = len(unresolved) == 0
        return BarrierStatus(passed, unresolved, parallel_result)

    def check_values(self, values):
        """Check a list of RayonInt values directly."""
        results = []
        for i, v in enumerate(values):
            if isinstance(v, RayonInt):
                results.append(FlowResult(v, v.tension, f"flow_{i}"))
            else:
                results.append(FlowResult(v, 0, f"flow_{i}"))
        pr = ParallelResult(results, max(r.tension for r in results), False)
        return self.check(pr)


class BarrierStatus:
    """Result of a barrier check."""
    def __init__(self, passed, unresolved, parallel_result):
        self.passed = passed
        self.unresolved = unresolved
        self.parallel_result = parallel_result

    @property
    def n_unresolved(self):
        return len(self.unresolved)

    @property
    def total_unresolved_tension(self):
        return sum(u.tension for u in self.unresolved)

    def __repr__(self):
        if self.passed:
            return f"Barrier: PASSED (all resolved)"
        return (f"Barrier: BLOCKED ({self.n_unresolved} unresolved, "
                f"τ_remaining={self.total_unresolved_tension})")


# ════════════════════════════════════════════════════════════════
# MAP PARALLEL
# ════════════════════════════════════════════════════════════════

class MapParallel:
    """
    Apply a function to array elements in parallel.

    Each element is processed independently, so the total tension
    is max(per-element tension), not the sum.

    This is the parallel map: same function, independent data,
    tension = worst case element.
    """
    def __init__(self, fn):
        self.fn = fn

    def apply(self, elements):
        """Apply fn to each element, return MapResult."""
        results = []
        for i, elem in enumerate(elements):
            out = self.fn(elem)
            if isinstance(out, RayonInt):
                results.append(FlowResult(out, out.tension, f"elem_{i}"))
            elif isinstance(out, FlowResult):
                results.append(out)
            else:
                results.append(FlowResult(out, 0, f"elem_{i}"))

        tensions = [r.tension for r in results]
        # Independent elements → max tension
        total_tension = max(tensions) if tensions else 0

        return MapResult(results, total_tension)


class MapResult:
    """Result of a parallel map."""
    def __init__(self, results, total_tension):
        self.results = results
        self.total_tension = total_tension

    @property
    def values(self):
        return [r.value for r in self.results]

    @property
    def individual_tensions(self):
        return [r.tension for r in self.results]

    def __repr__(self):
        return (f"MapResult(n={len(self.results)}, τ_total={self.total_tension}, "
                f"per_element={self.individual_tensions})")


# ════════════════════════════════════════════════════════════════
# RACE FLOW
# ════════════════════════════════════════════════════════════════

class RaceFlow:
    """
    Run multiple approaches, take the first to resolve.

    Tension = min(approach tensions) — the best approach wins.
    This models trying multiple solution strategies in parallel.

    Example: brute force (high tension) vs algebraic (low tension).
    The algebraic approach resolves first, so we take its tension.
    """
    def __init__(self):
        self.approaches = []

    def add(self, name, fn):
        """Add a named approach. fn() -> RayonInt or FlowResult."""
        self.approaches.append((name, fn))
        return self

    def run(self):
        """Run all approaches, return the one with lowest tension."""
        results = []
        for name, fn in self.approaches:
            result = fn()
            if isinstance(result, RayonInt):
                results.append(FlowResult(result, result.tension, name))
            elif isinstance(result, FlowResult):
                result.name = name
                results.append(result)
            else:
                results.append(FlowResult(result, 0, name))

        if not results:
            return RaceResult(None, [])

        # Sort by tension — lowest wins
        results.sort(key=lambda r: r.tension)
        winner = results[0]
        return RaceResult(winner, results)


class RaceResult:
    """Result of a race between approaches."""
    def __init__(self, winner, all_results):
        self.winner = winner
        self.all_results = all_results

    @property
    def tension(self):
        return self.winner.tension if self.winner else 0

    @property
    def value(self):
        return self.winner.value if self.winner else None

    def __repr__(self):
        if not self.winner:
            return "RaceResult(no approaches)"
        others = [(r.name, r.tension) for r in self.all_results if r is not self.winner]
        return (f"RaceResult(winner={self.winner.name} τ={self.winner.tension}, "
                f"beaten={others})")


# ════════════════════════════════════════════════════════════════
# VERIFICATION
# ════════════════════════════════════════════════════════════════

def verify():
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  STONE 21: PARALLELISM — Concurrent tension flows        ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    W = 8  # 8-bit RayonInt

    # ── TEST 1: Independent XOR operations ──
    print("TEST 1: Four independent XOR operations")
    print("─" * 50)

    # Four independent XOR ops, each with some unknown bits
    # Each has tension from its ? bits, but they're independent
    # so total = max, not sum.

    a1 = RayonInt.known(0b10110011, W)
    b1 = RayonInt.partial(0b00000000, 0b00000011, W)  # 2 unknown bits → τ=2

    a2 = RayonInt.known(0b11001100, W)
    b2 = RayonInt.partial(0b00000000, 0b00001111, W)  # 4 unknown bits → τ=4

    a3 = RayonInt.known(0b11110000, W)
    b3 = RayonInt.partial(0b00000000, 0b00000001, W)  # 1 unknown bit → τ=1

    a4 = RayonInt.known(0b01010101, W)
    b4 = RayonInt.partial(0b00000000, 0b00000111, W)  # 3 unknown bits → τ=3

    pf = ParallelFlow()
    pf.add("xor_1", lambda: a1 ^ b1)
    pf.add("xor_2", lambda: a2 ^ b2)
    pf.add("xor_3", lambda: a3 ^ b3)
    pf.add("xor_4", lambda: a4 ^ b4)

    result = pf.run()
    individual = result.individual_tensions
    sum_tensions = sum(individual)
    max_tension = max(individual)

    print(f"  Individual tensions: {individual}")
    print(f"  Sum would be:  {sum_tensions}")
    print(f"  Max (parallel): {max_tension}")
    print(f"  Total tension:  {result.total_tension}")

    t1_pass = (result.total_tension == max_tension and
               result.total_tension < sum_tensions)
    print(f"  Total = max (not sum): {result.total_tension} == {max_tension} "
          f"{'✓' if t1_pass else '✗'}")
    print()

    # Show that dependent flows would sum
    pf_dep = ParallelFlow()
    pf_dep.set_dependent(True)
    pf_dep.add("xor_1", lambda: a1 ^ b1)
    pf_dep.add("xor_2", lambda: a2 ^ b2)
    pf_dep.add("xor_3", lambda: a3 ^ b3)
    pf_dep.add("xor_4", lambda: a4 ^ b4)

    result_dep = pf_dep.run()
    t1b_pass = result_dep.total_tension == sum_tensions
    print(f"  Dependent mode: {result_dep.total_tension} == sum({sum_tensions}) "
          f"{'✓' if t1b_pass else '✗'}")
    print()

    # ── TEST 2: MapParallel over [known, ?, ?, known] ──
    print("TEST 2: MapParallel over [known, ?, ?, known]")
    print("─" * 50)

    elements = [
        RayonInt.known(0xAA, W),                          # known, τ=0
        RayonInt.partial(0b00000000, 0b00111100, W),      # 4 unknown bits, τ=4
        RayonInt.partial(0b00000000, 0b11000000, W),      # 2 unknown bits, τ=2
        RayonInt.known(0x55, W),                          # known, τ=0
    ]

    # Apply NOT (invert) — preserves tension per element
    mapper = MapParallel(lambda x: ~x)
    map_result = mapper.apply(elements)

    print(f"  Input tensions:  {[e.tension for e in elements]}")
    print(f"  Output tensions: {map_result.individual_tensions}")
    print(f"  Total tension:   {map_result.total_tension}")

    # Tension should come from the ? elements: max(0, 4, 2, 0) = 4
    expected_map_tension = max(e.tension for e in elements)
    t2_pass = map_result.total_tension == expected_map_tension
    print(f"  Total = max of element tensions: {map_result.total_tension} == "
          f"{expected_map_tension} {'✓' if t2_pass else '✗'}")
    print()

    # ── TEST 3: Barrier check ──
    print("TEST 3: TensionBarrier — synchronization point")
    print("─" * 50)

    barrier = TensionBarrier("sync_point")

    # Check before resolution
    status = barrier.check(result)
    print(f"  Before resolution: {status}")
    t3a_pass = not status.passed
    print(f"  Barrier blocks (has unresolved): {'✓' if t3a_pass else '✗'}")

    # Check with all-known values
    all_known = ParallelFlow()
    all_known.add("a", lambda: RayonInt.known(42, W))
    all_known.add("b", lambda: RayonInt.known(99, W))
    all_known.add("c", lambda: RayonInt.known(7, W))
    known_result = all_known.run()

    status2 = barrier.check(known_result)
    print(f"  All known: {status2}")
    t3b_pass = status2.passed
    print(f"  Barrier passes (all resolved): {'✓' if t3b_pass else '✗'}")
    print()

    # ── TEST 4: RaceFlow ──
    print("TEST 4: RaceFlow — brute force vs algebraic")
    print("─" * 50)

    # Scenario: solve a ^ key = target
    target = RayonInt.known(0b11001010, W)

    # Brute force: unknown key, XOR with known → still unknown → high tension
    def brute_force():
        key = RayonInt.unknown(W)  # τ=8: try all 256 keys
        result = key ^ target
        return FlowResult(result, key.tension, "brute_force")

    # Algebraic: key = target ^ target = 0 when target known → tension 0
    # More realistically: partial knowledge reduces tension
    def algebraic():
        # "Algebraic" approach: we know 6 of 8 bits, only 2 unknown
        key = RayonInt.partial(0b11001000, 0b00000010, W)  # τ=1
        result = key ^ target
        return FlowResult(result, key.tension, "algebraic")

    race = RaceFlow()
    race.add("brute_force", brute_force)
    race.add("algebraic", algebraic)

    race_result = race.run()

    bf_tension = next(r.tension for r in race_result.all_results if r.name == "brute_force")
    alg_tension = next(r.tension for r in race_result.all_results if r.name == "algebraic")

    print(f"  Brute force tension: {bf_tension}")
    print(f"  Algebraic tension:   {alg_tension}")
    print(f"  Winner: {race_result.winner.name} (τ={race_result.tension})")

    t4_pass = (race_result.tension == min(bf_tension, alg_tension) and
               race_result.winner.name == "algebraic" and
               race_result.tension < bf_tension)
    print(f"  Tension = min(approaches): {race_result.tension} == "
          f"{min(bf_tension, alg_tension)} {'✓' if t4_pass else '✗'}")
    print()

    # ── SUMMARY ──
    all_pass = all([t1_pass, t1b_pass, t2_pass, t3a_pass, t3b_pass, t4_pass])

    print(f"""
═══════════════════════════════════════════════════════════════
STONE 21: PARALLELISM — {"ALL TESTS PASSED" if all_pass else "SOME TESTS FAILED"}

  ParallelFlow:   independent flows → τ = max  ✓
                  dependent flows   → τ = sum  ✓
  MapParallel:    per-element parallel → τ = max  ✓
  TensionBarrier: blocks until all τ = 0        ✓
  RaceFlow:       best approach wins → τ = min  ✓

  KEY INSIGHT: Parallelism reduces tension.
    Sequential: tension ADDS (each step compounds uncertainty)
    Parallel:   tension MAXES (only worst case matters)
    Racing:     tension MINS (best approach wins)

  Tension is not just about information —
  it's about the STRUCTURE of computation.
═══════════════════════════════════════════════════════════════
""")


if __name__ == '__main__':
    verify()
