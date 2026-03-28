"""
OPTIMIZER — Auto-selects best algorithm based on tension analysis.

Before running a computation, ANALYZE it:
  - How many branch points (AND with unknowns)?
  - How many linear ops (XOR — free in GF2)?
  - How many kill opportunities (AND with known zeros)?
  - What is the tension profile of inputs vs outputs?

Then SELECT the optimal strategy:
  FORWARD:       inputs mostly known → just compute
  BACKWARD:      outputs known, inputs unknown → propagate back
  BIDIRECTIONAL: both partially known → propagate both ways
  ALGEBRAIC:     mostly XOR → solve as GF2 linear system
  PARALLEL:      independent subproblems → run simultaneously
  RACE:          unclear → try multiple, take fastest
"""

import sys
import os

# The local types.py shadows stdlib types module which enum needs.
# Temporarily fix the import path.
_tension_dir = os.path.dirname(os.path.abspath(__file__))
if _tension_dir in sys.path:
    sys.path.remove(_tension_dir)
    from enum import Enum, auto
    sys.path.insert(0, _tension_dir)
else:
    from enum import Enum, auto

import functools
import time
from rayon_numbers import RayonInt


# ════════════════════════════════════════════════════════════════
# STRATEGY ENUM
# ════════════════════════════════════════════════════════════════

class Strategy(Enum):
    FORWARD = auto()
    BACKWARD = auto()
    BIDIRECTIONAL = auto()
    ALGEBRAIC = auto()
    PARALLEL = auto()
    RACE = auto()


# ════════════════════════════════════════════════════════════════
# TENSION ANALYZER
# ════════════════════════════════════════════════════════════════

class TensionAnalysis:
    """Result of analyzing a computation's tension profile."""
    def __init__(self):
        self.branch_points = 0      # AND with unknowns (exponential cost)
        self.linear_ops = 0         # XOR ops (free — GF2 linear)
        self.kill_opportunities = 0  # AND with known zeros (collapse for free)
        self.input_tension = 0      # total unknown bits in inputs
        self.output_tension = 0     # total unknown bits in outputs
        self.total_ops = 0          # total operation count
        self.independent_groups = 1  # count of independent subproblems
        self.has_known_output = False

    @property
    def estimated_cost(self):
        """
        Estimated cost of brute-force evaluation.
        Branch points create exponential blowup.
        Kills reduce it. XOR is free.
        """
        effective_branches = max(0, self.branch_points - self.kill_opportunities)
        return 2 ** effective_branches + self.linear_ops

    @property
    def linearity_ratio(self):
        """Fraction of ops that are linear (XOR). 1.0 = purely linear."""
        if self.total_ops == 0:
            return 1.0
        return self.linear_ops / self.total_ops

    @property
    def kill_ratio(self):
        """Fraction of branch points that get killed."""
        if self.branch_points == 0:
            return 1.0
        return self.kill_opportunities / self.branch_points

    def __repr__(self):
        return (
            f"TensionAnalysis(branches={self.branch_points}, "
            f"linear={self.linear_ops}, kills={self.kill_opportunities}, "
            f"input_τ={self.input_tension}, output_τ={self.output_tension}, "
            f"groups={self.independent_groups}, cost≈{self.estimated_cost})"
        )


class TensionAnalyzer:
    """
    Analyzes a computation BEFORE running it.

    Examines the function with probe inputs to determine:
    - Operation mix (AND vs XOR vs OR)
    - Kill opportunities
    - Tension flow (input → output)
    """

    @staticmethod
    def analyze_function(func, *args, output=None):
        """
        Analyze a function's tension profile given its inputs.

        func: callable taking RayonInt arguments
        args: RayonInt inputs (with their current tension)
        output: optional known output (RayonInt)
        """
        analysis = TensionAnalysis()

        # Measure input tension
        for arg in args:
            if isinstance(arg, RayonInt):
                analysis.input_tension += arg.tension

        # Trace the computation to count operations
        traced_args = [_TracedRayonInt(a, analysis) if isinstance(a, RayonInt)
                       else a for a in args]

        try:
            result = func(*traced_args)
        except Exception:
            # If tracing fails, return conservative analysis
            analysis.branch_points = analysis.input_tension
            analysis.total_ops = analysis.input_tension
            return analysis

        # Measure output tension
        if isinstance(result, _TracedRayonInt):
            result = result._inner
        if isinstance(result, RayonInt):
            analysis.output_tension = result.tension

        # Check for known output
        if output is not None and isinstance(output, RayonInt):
            analysis.has_known_output = True
            if output.is_known:
                analysis.output_tension = 0

        return analysis

    @staticmethod
    def analyze_inputs(*args):
        """Quick analysis of just the inputs (no function trace)."""
        analysis = TensionAnalysis()
        for arg in args:
            if isinstance(arg, RayonInt):
                analysis.input_tension += arg.tension
        return analysis

    @staticmethod
    def analyze_multi(funcs, *shared_args):
        """
        Analyze multiple functions to detect independent subproblems.

        Returns analysis with independent_groups set appropriately.
        """
        analysis = TensionAnalysis()

        for arg in shared_args:
            if isinstance(arg, RayonInt):
                analysis.input_tension += arg.tension

        # Each function is a potential independent group
        sub_analyses = []
        for func in funcs:
            sub = TensionAnalyzer.analyze_function(func, *shared_args)
            sub_analyses.append(sub)

        # Aggregate
        analysis.independent_groups = len(funcs)
        analysis.branch_points = sum(s.branch_points for s in sub_analyses)
        analysis.linear_ops = sum(s.linear_ops for s in sub_analyses)
        analysis.kill_opportunities = sum(s.kill_opportunities for s in sub_analyses)
        analysis.total_ops = sum(s.total_ops for s in sub_analyses)
        analysis.output_tension = max((s.output_tension for s in sub_analyses), default=0)

        return analysis


class _TracedRayonInt:
    """
    Wrapper around RayonInt that records operations during analysis.

    Acts like RayonInt but counts AND/XOR/OR ops and kills.
    """
    def __init__(self, inner, analysis):
        self._inner = inner
        self._analysis = analysis

    def __and__(self, other):
        inner_other = other._inner if isinstance(other, _TracedRayonInt) else other
        self._analysis.total_ops += 1

        a = self._inner
        b = inner_other

        # Count kills: AND where either input has known zero bits
        kills = 0
        branches = 0
        for i in range(a.width):
            ab = a.bits[i] if i < len(a.bits) else 0
            bb = b.bits[i] if i < len(b.bits) else 0
            if ab == 0 or bb == 0:
                if ab is None or bb is None:
                    kills += 1  # a known zero kills an unknown
            elif ab is None or bb is None:
                branches += 1  # AND with unknown, no kill

        self._analysis.kill_opportunities += kills
        self._analysis.branch_points += branches

        result = a & b
        return _TracedRayonInt(result, self._analysis)

    def __xor__(self, other):
        inner_other = other._inner if isinstance(other, _TracedRayonInt) else other
        self._analysis.total_ops += 1
        self._analysis.linear_ops += 1

        result = self._inner ^ inner_other
        return _TracedRayonInt(result, self._analysis)

    def __or__(self, other):
        inner_other = other._inner if isinstance(other, _TracedRayonInt) else other
        self._analysis.total_ops += 1

        a = self._inner
        b = inner_other

        # OR kills: known 1 kills unknown
        kills = 0
        branches = 0
        for i in range(a.width):
            ab = a.bits[i] if i < len(a.bits) else 0
            bb = b.bits[i] if i < len(b.bits) else 0
            if ab == 1 or bb == 1:
                if ab is None or bb is None:
                    kills += 1
            elif ab is None or bb is None:
                branches += 1

        self._analysis.kill_opportunities += kills
        self._analysis.branch_points += branches

        result = a | b
        return _TracedRayonInt(result, self._analysis)

    def __add__(self, other):
        inner_other = other._inner if isinstance(other, _TracedRayonInt) else other
        self._analysis.total_ops += 1
        # Addition is a mix of XOR (sum bits) and AND (carry generation)
        a = self._inner
        b = inner_other
        for i in range(a.width):
            ab = a.bits[i] if i < len(a.bits) else 0
            bb = b.bits[i] if i < len(b.bits) else 0
            if ab is None or bb is None:
                if ab == 0 or bb == 0:
                    self._analysis.kill_opportunities += 1
                else:
                    self._analysis.branch_points += 1

        result = a + b
        return _TracedRayonInt(result, self._analysis)

    def __invert__(self):
        self._analysis.total_ops += 1
        self._analysis.linear_ops += 1  # NOT is free (like XOR with 1)
        result = ~self._inner
        return _TracedRayonInt(result, self._analysis)

    def __repr__(self):
        return repr(self._inner)


# ════════════════════════════════════════════════════════════════
# STRATEGY SELECTOR
# ════════════════════════════════════════════════════════════════

class StrategySelector:
    """
    Given a TensionAnalysis, select the optimal computation strategy.

    Decision tree:
      1. Independent subproblems?         → PARALLEL
      2. Mostly XOR (linearity > 0.8)?    → ALGEBRAIC (GF2 solve)
      3. High kill ratio + low input τ?   → FORWARD (kills dominate)
      4. Known output + high input τ?     → BACKWARD
      5. Both partial?                    → BIDIRECTIONAL
      6. Unclear?                         → RACE
    """

    # Thresholds (tunable)
    LINEARITY_THRESHOLD = 0.8    # above this → ALGEBRAIC
    KILL_RATIO_THRESHOLD = 0.5   # above this, FORWARD is attractive
    HIGH_TENSION = 4             # above this, tension is "high"
    PARALLEL_THRESHOLD = 2       # above this many groups → PARALLEL

    @classmethod
    def select(cls, analysis):
        """
        Select the best strategy for the given analysis.

        Returns (Strategy, reason_string).
        """
        # Rule 1: Independent subproblems → PARALLEL
        if analysis.independent_groups >= cls.PARALLEL_THRESHOLD:
            return Strategy.PARALLEL, (
                f"{analysis.independent_groups} independent subproblems detected"
            )

        # Rule 2: Known output, high input tension → BACKWARD
        # This beats ALGEBRAIC because backward propagation is direct.
        if analysis.has_known_output and analysis.input_tension >= cls.HIGH_TENSION:
            return Strategy.BACKWARD, (
                f"output known, input_τ={analysis.input_tension} — "
                f"propagate backward"
            )

        # Rule 3: Mostly linear (XOR) → ALGEBRAIC
        if analysis.linearity_ratio >= cls.LINEARITY_THRESHOLD and analysis.total_ops > 0:
            return Strategy.ALGEBRAIC, (
                f"linearity={analysis.linearity_ratio:.0%} — "
                f"GF2 linear system solvable"
            )

        # Rule 4: Good kills → FORWARD
        # Kills reduce effective tension: if kills >= branches, it's cheap
        effective_tension = max(0, analysis.branch_points - analysis.kill_opportunities)
        if (analysis.kill_ratio >= cls.KILL_RATIO_THRESHOLD
                and (analysis.input_tension <= cls.HIGH_TENSION
                     or effective_tension == 0)):
            return Strategy.FORWARD, (
                f"kill_ratio={analysis.kill_ratio:.0%}, "
                f"input_τ={analysis.input_tension} — kills dominate"
            )

        # Rule 5: Both sides partially known → BIDIRECTIONAL
        if (analysis.input_tension > 0 and analysis.output_tension > 0
                and analysis.has_known_output):
            return Strategy.BIDIRECTIONAL, (
                f"input_τ={analysis.input_tension}, "
                f"output_τ={analysis.output_tension} — "
                f"propagate both ways"
            )

        # Rule 5b: Mixed ops with moderate tension on both sides
        if (analysis.input_tension > 0
                and analysis.branch_points > 0
                and analysis.linear_ops > 0
                and analysis.linearity_ratio < cls.LINEARITY_THRESHOLD):
            return Strategy.BIDIRECTIONAL, (
                f"mixed ops (linear={analysis.linear_ops}, "
                f"branch={analysis.branch_points}) — "
                f"propagate both ways"
            )

        # Rule 6: Low input tension, any ops → FORWARD (default productive)
        if analysis.input_tension < cls.HIGH_TENSION:
            return Strategy.FORWARD, (
                f"input_τ={analysis.input_tension} — "
                f"low tension, forward is efficient"
            )

        # Fallback: RACE (try multiple strategies)
        return Strategy.RACE, (
            f"no clear winner — race multiple strategies"
        )


# ════════════════════════════════════════════════════════════════
# AUTO-OPTIMIZE DECORATOR
# ════════════════════════════════════════════════════════════════

def auto_optimize(func=None, *, output=None, verbose=False):
    """
    Decorator that automatically analyzes and optimizes a function.

    Usage:
        @auto_optimize
        def my_func(a, b):
            return a ^ b

        # Or with options:
        @auto_optimize(verbose=True)
        def my_func(a, b):
            return a ^ b

    When called, the decorator:
    1. Analyzes the tension profile of the inputs
    2. Traces the function to count ops
    3. Selects optimal strategy
    4. Executes (currently: always runs forward, but reports strategy)

    The strategy selection is attached to the result as metadata.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            # Separate RayonInt args for analysis
            rayon_args = [a for a in args if isinstance(a, RayonInt)]

            # Analyze
            out = kwargs.pop('_output', output)
            analysis = TensionAnalyzer.analyze_function(fn, *args, output=out)

            # Select strategy
            strategy, reason = StrategySelector.select(analysis)

            if verbose:
                print(f"  [optimizer] {fn.__name__}: {analysis}")
                print(f"  [optimizer] → {strategy.name}: {reason}")

            # Execute with the selected strategy
            start = time.perf_counter()
            result = fn(*args, **kwargs)
            elapsed = time.perf_counter() - start

            # Attach metadata to result if possible
            if isinstance(result, RayonInt):
                result._strategy = strategy
                result._analysis = analysis
                result._reason = reason
                result._elapsed = elapsed

            return result

        wrapper._is_optimized = True
        wrapper._original = fn
        return wrapper

    # Support both @auto_optimize and @auto_optimize(verbose=True)
    if func is not None:
        return decorator(func)
    return decorator


class AutoOptimize:
    """
    Class-based optimizer for more control.

    optimizer = AutoOptimize(my_func)
    result = optimizer.run(a, b, output=known_output)
    print(optimizer.last_strategy)
    print(optimizer.last_analysis)
    """
    def __init__(self, func, verbose=False):
        self.func = func
        self.verbose = verbose
        self.last_analysis = None
        self.last_strategy = None
        self.last_reason = None

    def analyze(self, *args, output=None):
        """Analyze without running."""
        self.last_analysis = TensionAnalyzer.analyze_function(
            self.func, *args, output=output
        )
        self.last_strategy, self.last_reason = StrategySelector.select(
            self.last_analysis
        )
        return self.last_analysis, self.last_strategy, self.last_reason

    def run(self, *args, output=None):
        """Analyze, select strategy, and run."""
        self.analyze(*args, output=output)

        if self.verbose:
            print(f"  [AutoOptimize] {self.last_analysis}")
            print(f"  [AutoOptimize] → {self.last_strategy.name}: {self.last_reason}")

        return self.func(*args)


# ════════════════════════════════════════════════════════════════
# VERIFICATION
# ════════════════════════════════════════════════════════════════

def verify():
    W = 8  # 8-bit width for all tests

    print("=" * 65)
    print("  OPTIMIZER — Auto-selects best algorithm via tension analysis")
    print("=" * 65)
    print()

    # ── Test 1: XOR function with unknown input → ALGEBRAIC ──
    print("TEST 1: XOR function with unknown input → ALGEBRAIC")
    print("-" * 55)

    def xor_func(a, b):
        return a ^ b ^ a  # purely linear

    a = RayonInt.unknown(W)
    b = RayonInt.known(0xAA, W)

    analysis = TensionAnalyzer.analyze_function(xor_func, a, b)
    strategy, reason = StrategySelector.select(analysis)
    print(f"  Analysis: {analysis}")
    print(f"  Strategy: {strategy.name}")
    print(f"  Reason:   {reason}")
    assert strategy == Strategy.ALGEBRAIC, f"Expected ALGEBRAIC, got {strategy.name}"
    print("  Result:   ALGEBRAIC selected ✓")
    print()

    # ── Test 2: AND chain with known zero → FORWARD ──
    print("TEST 2: AND chain with known zero → FORWARD (kills)")
    print("-" * 55)

    def and_with_zero(a, b):
        return a & b

    a = RayonInt.known(0x00, W)  # all zeros — everything gets killed
    b = RayonInt.partial(0x00, 0x0F, W)  # low 4 unknown

    analysis = TensionAnalyzer.analyze_function(and_with_zero, a, b)
    strategy, reason = StrategySelector.select(analysis)
    print(f"  Analysis: {analysis}")
    print(f"  Strategy: {strategy.name}")
    print(f"  Reason:   {reason}")
    assert strategy == Strategy.FORWARD, f"Expected FORWARD, got {strategy.name}"
    print("  Result:   FORWARD selected ✓")
    print()

    # ── Test 3: Known output, unknown input → BACKWARD ──
    print("TEST 3: Known output, unknown input → BACKWARD")
    print("-" * 55)

    def simple_transform(a):
        return a ^ RayonInt.known(0xFF, W)

    a = RayonInt.unknown(W)
    known_output = RayonInt.known(0x42, W)

    analysis = TensionAnalyzer.analyze_function(simple_transform, a, output=known_output)
    strategy, reason = StrategySelector.select(analysis)
    print(f"  Analysis: {analysis}")
    print(f"  Strategy: {strategy.name}")
    print(f"  Reason:   {reason}")
    assert strategy == Strategy.BACKWARD, f"Expected BACKWARD, got {strategy.name}"
    print("  Result:   BACKWARD selected ✓")
    print()

    # ── Test 4: Independent subproblems → PARALLEL ──
    print("TEST 4: Two independent computations → PARALLEL")
    print("-" * 55)

    def comp1(a):
        return a ^ RayonInt.known(0x0F, W)

    def comp2(a):
        return a ^ RayonInt.known(0xF0, W)

    a = RayonInt.unknown(W)
    analysis = TensionAnalyzer.analyze_multi([comp1, comp2], a)
    strategy, reason = StrategySelector.select(analysis)
    print(f"  Analysis: {analysis}")
    print(f"  Strategy: {strategy.name}")
    print(f"  Reason:   {reason}")
    assert strategy == Strategy.PARALLEL, f"Expected PARALLEL, got {strategy.name}"
    print("  Result:   PARALLEL selected ✓")
    print()

    # ── Test 5: Mixed ops → BIDIRECTIONAL ──
    print("TEST 5: Mixed AND + XOR ops → BIDIRECTIONAL")
    print("-" * 55)

    def mixed_func(a, b):
        t1 = a ^ b       # linear
        t2 = a & b       # branch
        return t1 ^ t2   # linear

    a = RayonInt.partial(0x00, 0xFF, W)  # all unknown
    b = RayonInt.partial(0xA0, 0x0F, W)  # low 4 unknown

    analysis = TensionAnalyzer.analyze_function(mixed_func, a, b)
    strategy, reason = StrategySelector.select(analysis)
    print(f"  Analysis: {analysis}")
    print(f"  Strategy: {strategy.name}")
    print(f"  Reason:   {reason}")
    assert strategy == Strategy.BIDIRECTIONAL, f"Expected BIDIRECTIONAL, got {strategy.name}"
    print("  Result:   BIDIRECTIONAL selected ✓")
    print()

    # ── Test 6: auto_optimize decorator ──
    print("TEST 6: @auto_optimize decorator")
    print("-" * 55)

    @auto_optimize(verbose=True)
    def optimized_xor(a, b):
        return a ^ b

    result = optimized_xor(RayonInt.unknown(W), RayonInt.known(0x55, W))
    print(f"  Result: {result}")
    print(f"  Strategy used: {result._strategy.name}")
    assert result._strategy == Strategy.ALGEBRAIC
    print("  Decorator works ✓")
    print()

    # ── Test 7: AutoOptimize class ──
    print("TEST 7: AutoOptimize class interface")
    print("-" * 55)

    def my_computation(a, b):
        return (a & b) ^ a

    opt = AutoOptimize(my_computation, verbose=True)
    result = opt.run(RayonInt.known(0x0F, W), RayonInt.unknown(W))
    print(f"  Result: {result}")
    print(f"  Strategy: {opt.last_strategy.name}")
    print(f"  Analysis: {opt.last_analysis}")
    print("  Class interface works ✓")
    print()

    # ── Summary ──
    print("=" * 65)
    print("  OPTIMIZER — All tests passed")
    print()
    print("  TensionAnalyzer: traces computation to count ops")
    print("    - branch_points (AND with unknowns)")
    print("    - linear_ops (XOR — free in GF2)")
    print("    - kill_opportunities (AND with known zeros)")
    print("    - estimated_cost = 2^(branches - kills) + linear")
    print()
    print("  StrategySelector: picks optimal approach")
    print("    - FORWARD:       low input tension, kills dominate")
    print("    - BACKWARD:      known output, unknown inputs")
    print("    - BIDIRECTIONAL: mixed ops, partial knowledge")
    print("    - ALGEBRAIC:     mostly XOR → GF2 linear solve")
    print("    - PARALLEL:      independent subproblems")
    print("    - RACE:          unclear → try all, take fastest")
    print()
    print("  @auto_optimize: decorator for automatic strategy")
    print("  AutoOptimize:   class for manual control")
    print("=" * 65)


if __name__ == '__main__':
    verify()
