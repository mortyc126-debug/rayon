"""
RAYON CORE — The mathematical engine.

Every value in Rayon carries TENSION: how hard it is to determine.
Every operation transforms tension according to the 7 Axioms.
The runtime traces tension flow and finds minimum-tension paths.

This is not a library ON TOP of Python.
This is a new computational model IMPLEMENTED in Python.
"""

import math
from functools import reduce


# ════════════════════════════════════════════════════════════
# PRIMITIVE: TENSION VALUE
# ════════════════════════════════════════════════════════════

class T:
    """
    Tension Value — the fundamental primitive of Rayon Mathematics.

    Not a number. Not a boolean. A measure of HOW HARD TO KNOW.

    τ = 0: fully known (still)
    τ = ∞: fully unknown (dark)
    τ ∈ (0, ∞): partially known (flowing)
    """
    __slots__ = ('value', 'tau', '_origin')

    def __init__(self, value=None, tau=0.0):
        self.value = value        # the actual value (if known)
        self.tau = tau            # tension: how hard to determine
        self._origin = None       # trace: where this tension came from

    @staticmethod
    def still(value):
        """Axiom 1: Known value → zero tension."""
        return T(value=value, tau=0.0)

    @staticmethod
    def dark():
        """Axiom 2: Unknown → infinite tension."""
        return T(value=None, tau=float('inf'))

    @staticmethod
    def partial(tau):
        """Partially known with given tension."""
        return T(value=None, tau=tau)

    @property
    def c(self):
        """Axiom 7: Equilibrium — darkness fraction."""
        if self.tau == float('inf'):
            return 1.0
        return self.tau / (1.0 + self.tau)

    @property
    def known(self):
        return self.tau == 0.0 and self.value is not None

    @property
    def impossible(self):
        return self.tau == float('inf')

    def __repr__(self):
        if self.known:
            return f'T({self.value}, τ=0)'
        if self.impossible:
            return f'T(?, τ=∞)'
        return f'T(?, τ={self.tau:.2f}, c={self.c:.3f})'


# ════════════════════════════════════════════════════════════
# OPERATIONS: The 7 Axioms as code
# ════════════════════════════════════════════════════════════

def flow(f_tau, g_tau):
    """Axiom 3: Sequential composition MULTIPLIES tension."""
    return f_tau * g_tau

def branch(a_tau, b_tau):
    """Axiom 4: Choice (OR) — MINIMUM tension."""
    return min(a_tau, b_tau)

def bind(a_tau, b_tau):
    """Axiom 5: Joint requirement (AND) — SUM tension."""
    return a_tau + b_tau

def entangle(a_tau, b_tau):
    """Axiom 6: Mixing (XOR) — SUM tension (no shortcut)."""
    return a_tau + b_tau

def equilibrium(tau):
    """Axiom 7: Darkness fraction."""
    if tau == float('inf'):
        return 1.0
    return tau / (1.0 + tau)

def inverse_tension(tau, dim_in, dim_out):
    """Rayon Inverse: τ(f⁻¹) = τ^(dim_out/dim_in)."""
    if tau == 0:
        return 0.0
    if tau == float('inf'):
        return float('inf')
    exponent = dim_out / dim_in
    return tau ** exponent


# ════════════════════════════════════════════════════════════
# FLOW: Computation as tension propagation
# ════════════════════════════════════════════════════════════

class Flow:
    """
    A computation seen as tension flow.

    Not a function — a FLOW with measurable resistance.
    """
    def __init__(self, name, dim_in, dim_out, stages=None):
        self.name = name
        self.dim_in = dim_in
        self.dim_out = dim_out
        self.stages = stages or []  # list of (name, tau) per stage

    def add_stage(self, name, tau):
        """Add a computation stage with given tension."""
        self.stages.append((name, tau))

    @property
    def tau(self):
        """Total tension = product of stage tensions (Axiom 3)."""
        if not self.stages:
            return 0.0
        result = 1.0
        for _, t in self.stages:
            result = flow(result, t)
            if result == float('inf'):
                break
        return result

    @property
    def tau_inverse(self):
        """Tension of inverting this flow."""
        return inverse_tension(self.tau, self.dim_in, self.dim_out)

    @property
    def c(self):
        return equilibrium(self.tau)

    @property
    def c_inverse(self):
        return equilibrium(self.tau_inverse)

    def tension_map(self):
        """Map of tension at each stage — find the weak points."""
        result = []
        cumulative = 1.0
        for name, t in self.stages:
            cumulative = flow(cumulative, t)
            c = equilibrium(cumulative)
            result.append((name, t, cumulative, c))
        return result

    def weakest_stage(self):
        """Stage with lowest tension = easiest to attack."""
        if not self.stages:
            return None
        return min(self.stages, key=lambda s: s[1])

    def strongest_stage(self):
        """Stage with highest tension = hardest barrier."""
        if not self.stages:
            return None
        return max(self.stages, key=lambda s: s[1])

    def rayon_inverse(self):
        """Create the inverse flow."""
        inv = Flow(f'{self.name}⁻¹', self.dim_out, self.dim_in)
        # Inverse stages: reversed, with transformed tensions
        ratio = self.dim_out / self.dim_in
        for name, t in reversed(self.stages):
            inv.add_stage(f'{name}⁻¹', t ** ratio)
        return inv

    def __repr__(self):
        return (f'Flow({self.name}: {self.dim_in}→{self.dim_out}, '
                f'τ={self.tau:.2e}, c={self.c:.4f})')


# ════════════════════════════════════════════════════════════
# COLLISION FINDER: Navigation through tension space
# ════════════════════════════════════════════════════════════

class CollisionNavigator:
    """
    Find collisions by navigating tension landscape.

    Instead of brute force: find MINIMUM TENSION PATH
    from one input to another with same output.
    """
    def __init__(self, flow_obj):
        self.flow = flow_obj

    def estimate_collision_tension(self):
        """
        Estimate tension of finding a collision.

        Collision = two inputs with same output.
        Fiber dimension = dim_in - dim_out.
        Collision tension = τ_inverse / fiber_factor.
        """
        fiber_dim = self.flow.dim_in - self.flow.dim_out
        if fiber_dim <= 0:
            return float('inf')  # injective, no collisions

        tau_inv = self.flow.tau_inverse
        # Fiber factor: each fiber dimension reduces tension
        fiber_factor = 2.0 ** fiber_dim
        collision_tau = tau_inv / fiber_factor

        return collision_tau

    def optimal_strategy(self):
        """Determine the best collision strategy from tension analysis."""
        tau_col = self.estimate_collision_tension()
        c_col = equilibrium(tau_col)

        # Birthday bound for comparison
        birthday_cost = 2.0 ** (self.flow.dim_out / 2)
        birthday_tau = birthday_cost  # rough estimate

        strategies = []

        # Strategy 1: Birthday (baseline)
        strategies.append(('birthday', birthday_tau, self.flow.dim_out / 2))

        # Strategy 2: Rayon Inverse
        tau_inv = self.flow.tau_inverse
        strategies.append(('rayon_inverse', tau_inv,
                          math.log2(tau_inv) if tau_inv > 0 else 0))

        # Strategy 3: Minimum tension path (through weakest stages)
        weak = self.flow.weakest_stage()
        if weak:
            weak_name, weak_tau = weak
            # Attack through weakest point
            strategies.append(('weak_point', weak_tau,
                              math.log2(weak_tau) if weak_tau > 1 else 0))

        # Strategy 4: Tension collision
        strategies.append(('tension_collision', tau_col,
                          math.log2(tau_col) if tau_col > 0 else float('-inf')))

        strategies.sort(key=lambda s: s[1])
        return strategies

    def report(self):
        """Full collision analysis report."""
        print(f"\n  COLLISION ANALYSIS: {self.flow.name}")
        print(f"  {'─'*50}")
        print(f"  Flow: {self.flow.dim_in} → {self.flow.dim_out} bits")
        print(f"  Fiber dimension: {self.flow.dim_in - self.flow.dim_out}")
        print(f"  Forward tension: τ = {self.flow.tau:.2e} (c = {self.flow.c:.6f})")
        print(f"  Inverse tension: τ⁻¹ = {self.flow.tau_inverse:.2e}")
        print(f"  Collision tension: τ_col = {self.estimate_collision_tension():.2e}")
        print()
        print(f"  STRATEGIES (sorted by tension):")
        for name, tau, log_cost in self.optimal_strategy():
            c = equilibrium(tau) if tau < float('inf') else 1.0
            print(f"    {name:>20}: τ={tau:.2e}, cost≈2^{log_cost:.1f}")
        print()

        # Tension map
        print(f"  TENSION MAP (per stage):")
        tmap = self.flow.tension_map()
        for name, stage_tau, cum_tau, cum_c in tmap[:10]:
            bar = '█' * int(cum_c * 40)
            print(f"    {name:>12}: τ_stage={stage_tau:>8.1f}, "
                  f"cumul={cum_tau:.1e}, c={cum_c:.4f} |{bar}|")
        if len(tmap) > 10:
            print(f"    ... ({len(tmap)} stages total)")
        print(f"    {'TOTAL':>12}: τ={self.flow.tau:.2e}, c={self.flow.c:.6f}")
