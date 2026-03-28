"""
STONE 23: ERROR MODEL — Error handling when tension is too high, plus visual runtime.

Three components:

1. TensionOverflow: exception when tension exceeds a threshold.
   Options: approximate (resolve ? to most likely), abort, or degrade gracefully.

2. GracefulDegradation: switch from exact to probabilistic when exact solve
   is impossible. Returns partial results with confidence levels.

3. VisualRuntime: real-time progress bar showing tension reduction per step.
"""

import sys
from rayon_numbers import RayonInt


# ════════════════════════════════════════════════════════════
# 1. TensionOverflow — exception with recovery options
# ════════════════════════════════════════════════════════════

class TensionOverflow(Exception):
    """
    Raised when a computation's tension exceeds max_tension.

    Carries the partial state so recovery strategies can use it.
    """
    def __init__(self, message, current_tension, max_tension, partial_result=None):
        super().__init__(message)
        self.current_tension = current_tension
        self.max_tension = max_tension
        self.partial_result = partial_result


class OverflowPolicy:
    """Policy for handling TensionOverflow."""
    ABORT = "abort"
    APPROXIMATE = "approximate"
    DEGRADE = "degrade"


def check_tension(result, max_tension, policy=OverflowPolicy.DEGRADE):
    """
    Check if a RayonInt's tension exceeds the threshold.

    Returns the result unchanged if within limits.
    If exceeded, acts according to policy:
      - ABORT: raise TensionOverflow
      - APPROXIMATE: resolve ? bits to 0 (most likely / lowest value)
      - DEGRADE: return a DegradedResult with partial info
    """
    if result.tension <= max_tension:
        return result

    if policy == OverflowPolicy.ABORT:
        raise TensionOverflow(
            f"Tension {result.tension} exceeds limit {max_tension}",
            current_tension=result.tension,
            max_tension=max_tension,
            partial_result=result,
        )

    if policy == OverflowPolicy.APPROXIMATE:
        return approximate(result)

    if policy == OverflowPolicy.DEGRADE:
        return degrade(result)

    raise ValueError(f"Unknown policy: {policy}")


def approximate(r):
    """
    Resolve all ? bits to 0 (most likely = minimum value).
    Returns a fully known RayonInt.
    """
    bits = [(b if b is not None else 0) for b in r.bits]
    return RayonInt(bits=bits, width=r.width)


# ════════════════════════════════════════════════════════════
# 2. GracefulDegradation — partial results with confidence
# ════════════════════════════════════════════════════════════

class DegradedResult:
    """
    A partial answer: known bits are exact, unknown bits are marked.

    Attributes:
        result:      RayonInt with mix of known and ? bits
        confidence:  float in [0, 1] — fraction of bits that are known
        known_bits:  dict {position: value} for resolved bits
        unknown_pos: list of positions still unknown
    """
    def __init__(self, result):
        self.result = result
        self.width = result.width
        self.known_bits = {}
        self.unknown_pos = []
        for i, b in enumerate(result.bits):
            if b is not None:
                self.known_bits[i] = b
            else:
                self.unknown_pos.append(i)

    @property
    def confidence(self):
        """1.0 = fully known, 0.0 = fully unknown. 0.5 = balanced."""
        if self.width == 0:
            return 1.0
        return len(self.known_bits) / self.width

    @property
    def tension(self):
        return self.result.tension

    @property
    def is_exact(self):
        return self.confidence == 1.0

    @property
    def min_value(self):
        return self.result.min_value

    @property
    def max_value(self):
        return self.result.max_value

    @property
    def n_possible(self):
        return self.result.n_possible

    def best_guess(self):
        """Approximate: resolve ? to 0 (minimum value)."""
        return approximate(self.result)

    def __repr__(self):
        bits_str = ''.join(
            '?' if b is None else str(b)
            for b in reversed(self.result.bits)
        )
        return (f"DegradedResult({bits_str}, confidence={self.confidence:.2f}, "
                f"tension={self.tension}, range={self.min_value}..{self.max_value})")


def degrade(r):
    """Wrap a RayonInt into a DegradedResult."""
    return DegradedResult(r)


# ════════════════════════════════════════════════════════════
# 3. VisualRuntime — real-time tension progress display
# ════════════════════════════════════════════════════════════

class VisualRuntime:
    """
    Tracks and displays tension reduction across computation steps.

    Usage:
        vr = VisualRuntime(total_steps=10)
        for i in range(10):
            result = some_computation(...)
            vr.step(result.tension, label=f"round {i}")
        vr.summary()
    """
    BAR_WIDTH = 30

    def __init__(self, total_steps, initial_tension=None, stream=None):
        self.total_steps = total_steps
        self.initial_tension = initial_tension
        self.stream = stream or sys.stdout
        self.steps = []  # list of (step_number, tension, label)
        self._current_step = 0

    def step(self, tension, label=""):
        """Record one computation step and print the progress bar."""
        self._current_step += 1
        if self.initial_tension is None:
            self.initial_tension = tension

        self.steps.append((self._current_step, tension, label))

        # Compute resolution percentage
        if self.initial_tension > 0:
            resolved_frac = 1.0 - (tension / self.initial_tension)
        else:
            resolved_frac = 1.0
        resolved_frac = max(0.0, min(1.0, resolved_frac))
        pct = int(resolved_frac * 100)

        # Build the progress bar
        filled = int(resolved_frac * self.BAR_WIDTH)
        empty = self.BAR_WIDTH - filled
        bar = '\u2588' * filled + '\u2591' * empty

        # Step fraction
        step_frac = f"{self._current_step}/{self.total_steps}"

        # Tension arrow
        tau_str = (f"\u03c4={self.initial_tension}\u2192{tension}"
                   if self.initial_tension != tension
                   else f"\u03c4={tension}")

        line = f"  [{bar}] {pct:>3}% resolved, {tau_str}  (step {step_frac})"
        if label:
            line += f"  {label}"

        self.stream.write(line + "\n")
        self.stream.flush()

    def summary(self):
        """Print a final summary of the computation."""
        if not self.steps:
            self.stream.write("  (no steps recorded)\n")
            return

        first_tau = self.steps[0][1]
        last_tau = self.steps[-1][1]
        total_reduction = first_tau - last_tau

        self.stream.write("\n")
        self.stream.write(f"  VISUAL RUNTIME SUMMARY\n")
        self.stream.write(f"  {'=' * 45}\n")
        self.stream.write(f"  Steps completed : {len(self.steps)}/{self.total_steps}\n")
        self.stream.write(f"  Initial tension : {self.initial_tension}\n")
        self.stream.write(f"  Final tension   : {last_tau}\n")
        self.stream.write(f"  Total reduction : {total_reduction}\n")

        if self.initial_tension > 0:
            pct = (1.0 - last_tau / self.initial_tension) * 100
            self.stream.write(f"  Resolution      : {pct:.1f}%\n")

        self.stream.write(f"  {'=' * 45}\n")
        self.stream.flush()


# ════════════════════════════════════════════════════════════
# 4. TensionBoundedComputation — ties everything together
# ════════════════════════════════════════════════════════════

class TensionBoundedComputation:
    """
    Run a multi-step computation with a tension ceiling.

    Each step is a callable(RayonInt) -> RayonInt.
    If any step's output exceeds max_tension, the policy kicks in.
    Optionally displays a visual runtime.
    """
    def __init__(self, max_tension, policy=OverflowPolicy.DEGRADE, visual=False, stream=None):
        self.max_tension = max_tension
        self.policy = policy
        self.visual = visual
        self.stream = stream or sys.stdout
        self.tracker = None  # optional: attach a CostTracker externally

    def run(self, initial, steps):
        """
        Execute a pipeline of steps on initial RayonInt.

        steps: list of (label, callable) where callable takes a RayonInt
               and returns a RayonInt.

        Returns the final result (RayonInt or DegradedResult).
        """
        n = len(steps)
        vr = VisualRuntime(n, initial_tension=initial.tension, stream=self.stream) if self.visual else None

        current = initial
        for i, (label, fn) in enumerate(steps):
            current = fn(current)

            if vr:
                tau = current.tension if isinstance(current, RayonInt) else current.result.tension if isinstance(current, DegradedResult) else 0
                vr.step(tau, label=label)

            # Check tension limit
            if isinstance(current, RayonInt) and current.tension > self.max_tension:
                if self.policy == OverflowPolicy.ABORT:
                    if vr:
                        vr.summary()
                    raise TensionOverflow(
                        f"Step '{label}' produced tension {current.tension} > {self.max_tension}",
                        current_tension=current.tension,
                        max_tension=self.max_tension,
                        partial_result=current,
                    )
                elif self.policy == OverflowPolicy.APPROXIMATE:
                    current = approximate(current)
                elif self.policy == OverflowPolicy.DEGRADE:
                    current = degrade(current)
                    # Continue with the underlying RayonInt for further steps
                    # but we've recorded the degradation
                    if vr:
                        vr.summary()
                    return current

            # Unwrap DegradedResult for further steps if needed
            if isinstance(current, DegradedResult):
                if vr:
                    vr.summary()
                return current

        if vr:
            vr.summary()
        return current


# ════════════════════════════════════════════════════════════
# VERIFICATION
# ════════════════════════════════════════════════════════════

def verify():
    W = 8
    all_pass = True

    print("+" + "=" * 63 + "+")
    print("|  STONE 23: ERROR MODEL — tension overflow + graceful degrade   |")
    print("+" + "=" * 63 + "+")
    print()

    # ── Test 1: TensionOverflow / ABORT ──
    print("TEST 1: TensionOverflow with ABORT policy")
    print("-" * 55)

    a = RayonInt.unknown(W)  # tension = 8
    caught = False
    try:
        check_tension(a, max_tension=4, policy=OverflowPolicy.ABORT)
    except TensionOverflow as e:
        caught = True
        t1_tension_ok = e.current_tension == 8
        t1_max_ok = e.max_tension == 4
        t1_partial_ok = e.partial_result is a

    t1 = caught and t1_tension_ok and t1_max_ok and t1_partial_ok
    print(f"  unknown(8) with max_tension=4:")
    print(f"    Exception raised: {'yes' if caught else 'no'}")
    print(f"    current_tension=8: {t1_tension_ok}")
    print(f"    partial_result preserved: {t1_partial_ok}")
    print(f"  TensionOverflow ABORT: {'✓' if t1 else '✗'}")
    if not t1:
        all_pass = False
    print()

    # ── Test 2: APPROXIMATE policy ──
    print("TEST 2: APPROXIMATE policy — resolve ? to 0")
    print("-" * 55)

    # partial: top 4 known = 1010, bottom 4 = ????
    a = RayonInt.partial(0b10100000, 0b00001111, W)
    result = check_tension(a, max_tension=2, policy=OverflowPolicy.APPROXIMATE)

    t2_known = result.is_known
    t2_val = result.value == 0b10100000  # ? bits resolved to 0
    t2_tension = result.tension == 0

    t2 = t2_known and t2_val and t2_tension
    print(f"  partial(1010????) with max_tension=2, APPROXIMATE:")
    print(f"    Result known: {t2_known}, value=0b{result.value:08b} ({result.value})")
    print(f"    All ? resolved to 0: {t2_val}")
    print(f"    Tension reduced to 0: {t2_tension}")
    print(f"  APPROXIMATE policy: {'✓' if t2 else '✗'}")
    if not t2:
        all_pass = False
    print()

    # ── Test 3: DEGRADE policy — partial result with confidence ──
    print("TEST 3: DEGRADE policy — partial result with confidence")
    print("-" * 55)

    # 6 known bits, 2 unknown → confidence = 6/8 = 0.75
    a = RayonInt.partial(0b10100000, 0b00000011, W)  # bits 0,1 unknown
    result = check_tension(a, max_tension=1, policy=OverflowPolicy.DEGRADE)

    t3_degraded = isinstance(result, DegradedResult)
    t3_conf = False
    t3_known = False
    t3_range = False
    if t3_degraded:
        t3_conf = abs(result.confidence - 0.75) < 0.01
        t3_known = len(result.known_bits) == 6
        t3_range = result.min_value == 0b10100000 and result.max_value == 0b10100011

    t3 = t3_degraded and t3_conf and t3_known and t3_range
    print(f"  partial(101000??) with max_tension=1, DEGRADE:")
    print(f"    Is DegradedResult: {t3_degraded}")
    if t3_degraded:
        print(f"    Confidence: {result.confidence:.2f} (expected 0.75): {t3_conf}")
        print(f"    Known bits: {len(result.known_bits)} (expected 6): {t3_known}")
        print(f"    Range: {result.min_value}..{result.max_value}: {t3_range}")
        print(f"    {result}")
    print(f"  DEGRADE policy: {'✓' if t3 else '✗'}")
    if not t3:
        all_pass = False
    print()

    # ── Test 4: Within limit — no intervention ──
    print("TEST 4: Within tension limit — pass through unchanged")
    print("-" * 55)

    a = RayonInt.partial(0b10100000, 0b00000011, W)  # tension = 2
    result = check_tension(a, max_tension=4, policy=OverflowPolicy.ABORT)

    t4 = result is a  # exact same object, no wrapping
    print(f"  partial(tension=2) with max_tension=4:")
    print(f"    Returned unchanged: {t4}")
    print(f"  Pass-through: {'✓' if t4 else '✗'}")
    if not t4:
        all_pass = False
    print()

    # ── Test 5: Multi-step computation exceeds limit → graceful degradation ──
    print("TEST 5: Multi-step computation → graceful degradation")
    print("-" * 55)

    # Start with low tension, each step ADDS uncertainty (simulating
    # a computation that progressively loses information).
    initial = RayonInt.known(42, W)  # tension 0

    def add_noise(label, noise_mask):
        """Return a step that ORs unknown bits into the result."""
        def step(r):
            noise = RayonInt.partial(0, noise_mask, W)
            # XOR with partial-unknown injects ? bits
            return r ^ noise
        return (label, step)

    steps = [
        add_noise("inject bit 0", 0b00000001),   # tension -> 1
        add_noise("inject bit 1", 0b00000010),   # tension -> 2
        add_noise("inject bit 2", 0b00000100),   # tension -> 3
        add_noise("inject bit 3", 0b00001000),   # tension -> 4
        add_noise("inject bit 4", 0b00010000),   # tension -> 5  (exceeds limit=4)
        add_noise("inject bit 5", 0b00100000),   # would be 6
        add_noise("inject bit 6", 0b01000000),   # would be 7
        add_noise("inject bit 7", 0b10000000),   # would be 8
    ]

    comp = TensionBoundedComputation(max_tension=4, policy=OverflowPolicy.DEGRADE, visual=True)
    result = comp.run(initial, steps)

    t5_degraded = isinstance(result, DegradedResult)
    t5_partial = False
    t5_conf = False
    if t5_degraded:
        # Should have degraded at step 5 (tension=5 > limit=4)
        t5_partial = result.tension == 5
        t5_conf = result.confidence < 1.0
        print(f"    Result: {result}")
        print(f"    Tension at degradation: {result.tension}")
        print(f"    Confidence: {result.confidence:.2f}")
        print(f"    Known bits preserved: {len(result.known_bits)}")
        print(f"    Best guess: {result.best_guess().value}")

    t5 = t5_degraded and t5_partial and t5_conf
    print(f"  Graceful degradation from multi-step: {'✓' if t5 else '✗'}")
    if not t5:
        all_pass = False
    print()

    # ── Test 6: VisualRuntime on a 10-step tension reduction ──
    print("TEST 6: VisualRuntime — 10-step tension reduction")
    print("-" * 55)

    # Simulate: start with all-unknown 8-bit, progressively AND with
    # known values to kill ? bits (reduce tension).
    vr = VisualRuntime(total_steps=10, initial_tension=8)

    current = RayonInt.unknown(W)  # tension = 8
    masks = [
        ("AND kill bit 7", 0b01111111),
        ("AND kill bit 6", 0b10111111),
        ("AND kill bit 5", 0b11011111),
        ("AND kill bit 4", 0b11101111),
        ("AND kill bit 3", 0b11110111),
        ("AND kill bit 2", 0b11111011),
        ("AND kill bit 1", 0b11111101),
        ("AND kill bit 0", 0b11111110),
        ("verify known",   0b11111111),
        ("final check",    0b11111111),
    ]

    for label, mask in masks:
        mask_val = RayonInt.known(mask, W)
        current = current & mask_val
        vr.step(current.tension, label=label)

    vr.summary()

    # After ANDing with all those masks, bits at 0-positions are killed
    t6_resolved = current.tension == 0
    t6_known = current.is_known and current.value == 0
    t6_steps = len(vr.steps) == 10

    t6 = t6_resolved and t6_known and t6_steps
    print(f"  Final tension: {current.tension}")
    print(f"  Final value: {current.value}")
    print(f"  All 10 steps recorded: {t6_steps}")
    print(f"  VisualRuntime 10-step: {'✓' if t6 else '✗'}")
    if not t6:
        all_pass = False
    print()

    # ── Test 7: DegradedResult confidence levels ──
    print("TEST 7: Confidence levels — known=1.0, balanced=0.5, unknown=0.0")
    print("-" * 55)

    d_full = degrade(RayonInt.known(42, W))
    d_half = degrade(RayonInt.partial(0, 0b00001111, W))  # 4 of 8 unknown
    d_none = degrade(RayonInt.unknown(W))

    t7a = abs(d_full.confidence - 1.0) < 0.01
    t7b = abs(d_half.confidence - 0.5) < 0.01
    t7c = abs(d_none.confidence - 0.0) < 0.01

    print(f"  Fully known:   confidence={d_full.confidence:.2f} (expect 1.00): {t7a}")
    print(f"  Half known:    confidence={d_half.confidence:.2f} (expect 0.50): {t7b}")
    print(f"  Fully unknown: confidence={d_none.confidence:.2f} (expect 0.00): {t7c}")

    t7 = t7a and t7b and t7c
    print(f"  Confidence levels: {'✓' if t7 else '✗'}")
    if not t7:
        all_pass = False
    print()

    # ── Summary ──
    print("=" * 64)
    print("STONE 23: ERROR MODEL")
    print(f"  Test 1 — TensionOverflow ABORT:           {'✓' if t1 else '✗'}")
    print(f"  Test 2 — APPROXIMATE policy:              {'✓' if t2 else '✗'}")
    print(f"  Test 3 — DEGRADE policy:                  {'✓' if t3 else '✗'}")
    print(f"  Test 4 — Pass-through (within limit):     {'✓' if t4 else '✗'}")
    print(f"  Test 5 — Multi-step graceful degradation: {'✓' if t5 else '✗'}")
    print(f"  Test 6 — VisualRuntime 10-step:           {'✓' if t6 else '✗'}")
    print(f"  Test 7 — Confidence levels:               {'✓' if t7 else '✗'}")
    print()
    if all_pass:
        print("  ALL TESTS PASSED")
    else:
        print("  SOME TESTS FAILED")
    print("=" * 64)


if __name__ == "__main__":
    verify()
