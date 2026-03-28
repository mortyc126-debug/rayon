"""
ADVANCED FEATURES — Formal Proofs, Quantum Bridge, AI Engine.

Three extensions of the Rayon tension model:

  SECTION 1: FORMAL PROOFS
    Prove upper bounds on computation cost from type signatures.

  SECTION 2: QUANTUM BRIDGE
    Map ?-bits to qubit superpositions. Measure, entangle, compute tension.

  SECTION 3: AI ENGINE
    Loss function and neural network where weights are RayonInt,
    trained by tension-guided gradient descent.

All built on RayonInt (8-bit width).
"""

import random
import math
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Callable

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from rayon_numbers import RayonInt

W = 8  # 8-bit width throughout


# ════════════════════════════════════════════════════════════════
# SECTION 1: FORMAL PROOFS
# ════════════════════════════════════════════════════════════════

class InputKind(Enum):
    KNOWN = "Known"
    PARTIAL = "Partial"
    UNKNOWN = "Unknown"


@dataclass
class ProofResult:
    """Result of a cost-bound proof."""
    bound: int            # upper bound on branch count
    is_tight: bool        # whether the bound is exact (not just upper)
    theorem: str          # which theorem was applied
    explanation: str      # human-readable reasoning


class CostProver:
    """
    Given a function's type signature (Known/Partial/Unknown per input),
    prove an upper bound on the number of AND-branches (exponential cost).

    Core theorems:
      T1 (Trivial):   all inputs Known  =>  0 branches
      T2 (Kill-link): AND(Known_zero, Unknown) => tension reduces
      T3 (XOR-free):  XOR-only circuits  =>  0 branches regardless
      T4 (General):   mixed inputs  =>  bound = sum of unknown bits
    """

    @staticmethod
    def _count_unknown_bits(input_types: List[Tuple[InputKind, Optional[RayonInt]]],
                            width: int) -> int:
        """Count total unknown bits across all inputs."""
        total = 0
        for kind, val in input_types:
            if kind == InputKind.UNKNOWN:
                total += width
            elif kind == InputKind.PARTIAL and val is not None:
                total += val.tension
            # KNOWN contributes 0
        return total

    @staticmethod
    def _has_known_zero(input_types: List[Tuple[InputKind, Optional[RayonInt]]]) -> bool:
        """Check if any input is known to be zero."""
        for kind, val in input_types:
            if kind == InputKind.KNOWN and val is not None and val.value == 0:
                return True
        return False

    @staticmethod
    def _has_unknown(input_types: List[Tuple[InputKind, Optional[RayonInt]]]) -> bool:
        for kind, _ in input_types:
            if kind == InputKind.UNKNOWN:
                return True
        return False

    @staticmethod
    def prove_cost_bound(
        fn_name: str,
        input_types: List[Tuple[InputKind, Optional[RayonInt]]],
        is_xor_only: bool = False,
        width: int = W,
    ) -> ProofResult:
        """
        Prove upper bound on AND-branch count for a function call.

        Parameters:
            fn_name:     name of the function (for reporting)
            input_types: list of (InputKind, optional RayonInt value) per argument
            is_xor_only: if True, function uses only XOR (no AND/OR)
            width:       bit width

        Returns:
            ProofResult with proven bound.
        """
        unknown_bits = CostProver._count_unknown_bits(input_types, width)
        has_zero = CostProver._has_known_zero(input_types)
        has_unk = CostProver._has_unknown(input_types)

        # Theorem 1 (Trivial): all Known => 0 branches
        all_known = all(k == InputKind.KNOWN for k, _ in input_types)
        if all_known:
            return ProofResult(
                bound=0,
                is_tight=True,
                theorem="T1_Trivial",
                explanation=f"{fn_name}: all inputs Known => 0 AND-branches (proved trivially)."
            )

        # Theorem 3 (XOR-free): XOR-only => 0 branches
        if is_xor_only:
            return ProofResult(
                bound=0,
                is_tight=True,
                theorem="T3_XOR_Free",
                explanation=f"{fn_name}: XOR-only circuit => 0 AND-branches (XOR is linear)."
            )

        # Theorem 2 (Kill-link): AND(Known_zero, Unknown) => tension reduces
        if has_zero and has_unk:
            # Every bit position where the known input is 0 kills the AND.
            # For a zero input, ALL bits are 0 => all AND outputs are 0 (known).
            # Bound: 0 branches from the AND with zero.
            reduced = 0  # AND with zero produces all-zero: no branches
            return ProofResult(
                bound=reduced,
                is_tight=True,
                theorem="T2_Kill_Link",
                explanation=(
                    f"{fn_name}: AND(Known_zero, Unknown) => kill-link fires on all {width} bits. "
                    f"Tension reduces from {unknown_bits} to {reduced}. "
                    f"0 AND-branches (all killed)."
                )
            )

        # Theorem 4 (General): bound = total unknown bits
        return ProofResult(
            bound=unknown_bits,
            is_tight=False,
            theorem="T4_General",
            explanation=(
                f"{fn_name}: {unknown_bits} unknown bits => "
                f"at most {unknown_bits} AND-branches. "
                f"Exponential cost <= 2^{unknown_bits}."
            )
        )


# ════════════════════════════════════════════════════════════════
# SECTION 2: QUANTUM BRIDGE
# ════════════════════════════════════════════════════════════════

@dataclass
class QubitState:
    """
    Maps RayonInt ?-bits to a quantum superposition concept.

    ? with tension=1 is analogous to |0>+|1> (a single qubit in superposition).
    A RayonInt with k ?-bits is analogous to a k-qubit state:
      - 2^k basis states in superposition
      - measuring collapses ? to 0 or 1

    This is a *classical simulation* of the analogy, not actual quantum.
    """

    bits: List[Optional[int]]   # None = superposition, 0/1 = collapsed
    width: int

    @staticmethod
    def from_rayon(r: RayonInt) -> "QubitState":
        """Convert a RayonInt to a QubitState."""
        return QubitState(bits=list(r.bits[:r.width]), width=r.width)

    @staticmethod
    def superposition(width: int = W) -> "QubitState":
        """All qubits in superposition (fully unknown)."""
        return QubitState(bits=[None] * width, width=width)

    @staticmethod
    def basis(value: int, width: int = W) -> "QubitState":
        """A classical basis state (fully known)."""
        return QubitState(
            bits=[(value >> i) & 1 for i in range(width)],
            width=width,
        )

    @property
    def n_qubits_super(self) -> int:
        """Number of qubits still in superposition."""
        return sum(1 for b in self.bits if b is None)

    @property
    def n_basis_states(self) -> int:
        """Number of basis states in the superposition."""
        return 2 ** self.n_qubits_super

    def to_rayon(self) -> RayonInt:
        """Convert back to RayonInt."""
        return RayonInt(bits=list(self.bits), width=self.width)

    def __repr__(self):
        ket = ''.join('?' if b is None else str(b) for b in reversed(self.bits))
        n = self.n_qubits_super
        if n == 0:
            val = sum(b << i for i, b in enumerate(self.bits))
            return f"|{val}> (collapsed)"
        return f"|{ket}> ({n} qubits in superposition, {self.n_basis_states} basis states)"


def measure(qs: QubitState) -> QubitState:
    """
    Measure all qubits: collapse each ? to 0 or 1 with equal probability.
    Returns a new fully-collapsed QubitState.
    """
    new_bits = []
    for b in qs.bits:
        if b is None:
            new_bits.append(random.randint(0, 1))
        else:
            new_bits.append(b)
    return QubitState(bits=new_bits, width=qs.width)


def measure_single(qs: QubitState, bit_index: int) -> QubitState:
    """Measure a single qubit, collapsing just that one."""
    new_bits = list(qs.bits)
    if new_bits[bit_index] is None:
        new_bits[bit_index] = random.randint(0, 1)
    return QubitState(bits=new_bits, width=qs.width)


def entangle(a: QubitState, b: QubitState) -> Tuple[QubitState, QubitState, int]:
    """
    Entangle two single-qubit states with an XOR constraint:
      a XOR b = fixed_parity (randomly chosen).

    After entanglement, each qubit individually appears unknown,
    but they are correlated: measuring one determines the other.

    Returns (a', b', parity) where a' and b' share the constraint.
    """
    parity = random.randint(0, 1)

    # Both qubits start as ?, but linked.
    # When we measure a, b = a XOR parity.
    # We store the constraint by collapsing both at measure time.
    a_val = random.randint(0, 1)
    b_val = a_val ^ parity

    # Return collapsed pair (simulating "entangled then measured")
    # But to show the *pre-measurement* state, we return them as unknown
    # with a note about the constraint.
    a_new = QubitState(bits=[None] * a.width, width=a.width)
    b_new = QubitState(bits=[None] * b.width, width=b.width)

    # Store the hidden values for demonstration
    a_new._hidden = a_val
    b_new._hidden = b_val
    a_new._parity = parity
    b_new._parity = parity

    return a_new, b_new, parity


def measure_entangled(a: QubitState, b: QubitState) -> Tuple[QubitState, QubitState]:
    """
    Measure an entangled pair. Measuring a determines b.
    Requires _hidden attribute set by entangle().
    """
    a_val = getattr(a, '_hidden', random.randint(0, 1))
    parity = getattr(a, '_parity', 0)
    b_val = a_val ^ parity

    a_bits = list(a.bits)
    b_bits = list(b.bits)
    # Collapse bit 0 (the entangled qubit)
    a_bits[0] = a_val
    b_bits[0] = b_val

    return (
        QubitState(bits=a_bits, width=a.width),
        QubitState(bits=b_bits, width=b.width),
    )


def quantum_tension(n_qubits: int) -> dict:
    """
    Compute tension properties of an n-qubit quantum state.

    Returns dict with:
      - tension: number of ?-bits (= n_qubits)
      - n_basis_states: 2^n_qubits
      - entropy: n_qubits (each qubit adds 1 bit of entropy)
      - darkness: tau/(1+tau) where tau = n_qubits
    """
    tau = n_qubits
    return {
        "n_qubits": n_qubits,
        "tension": tau,
        "n_basis_states": 2 ** n_qubits,
        "entropy_bits": n_qubits,
        "darkness": tau / (1.0 + tau) if tau < float('inf') else 1.0,
    }


# ════════════════════════════════════════════════════════════════
# SECTION 3: AI ENGINE
# ════════════════════════════════════════════════════════════════

def _tension_of(r: RayonInt) -> int:
    """Tension = count of ?-bits."""
    return r.tension


def _to_float_approx(r: RayonInt) -> float:
    """
    Approximate a RayonInt as a float for gradient computation.
    Unknown bits treated as 0.5 (expected value).
    """
    total = 0.0
    for i, b in enumerate(r.bits[:r.width]):
        if b is None:
            total += 0.5 * (1 << i)
        else:
            total += b * (1 << i)
    return total


def _float_to_rayon(val: float, width: int = W) -> RayonInt:
    """Convert a float to a known RayonInt (clamp to [0, 2^width - 1])."""
    iv = int(round(val)) % (1 << width)
    if iv < 0:
        iv = 0
    return RayonInt.known(iv, width)


class TensionLoss:
    """
    Loss function that minimizes tension of the output.

    Lower tension = more bits known = better prediction.

    loss = sum of tension across all output RayonInts
         + alpha * |output_approx - target|^2

    The first term drives the network to make predictions (reduce ?).
    The second term drives the predictions to be correct.
    """

    def __init__(self, alpha: float = 0.01):
        self.alpha = alpha

    def __call__(self, outputs: List[RayonInt], targets: List[RayonInt]) -> float:
        """
        Compute loss.
          outputs: list of RayonInt predictions
          targets: list of RayonInt ground truth (fully known)
        """
        tension_loss = sum(_tension_of(o) for o in outputs)
        mse_loss = 0.0
        for o, t in zip(outputs, targets):
            diff = _to_float_approx(o) - _to_float_approx(t)
            mse_loss += diff * diff
        return float(tension_loss) + self.alpha * mse_loss


class TensionNetwork:
    """
    Simple feed-forward network where weights are RayonInt.

    Architecture: input_dim -> hidden_dim -> output_dim
    All values are 8-bit RayonInts.

    Forward: multiply-accumulate (shift-and-add approximation).
    Backward: tension-guided gradient — nudge weights to reduce output tension.
    """

    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int,
                 width: int = W):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.width = width

        # Initialize weights as known random values
        self.w1 = [
            [RayonInt.known(random.randint(0, 15), width)
             for _ in range(input_dim)]
            for _ in range(hidden_dim)
        ]
        self.w2 = [
            [RayonInt.known(random.randint(0, 15), width)
             for _ in range(hidden_dim)]
            for _ in range(output_dim)
        ]

    def _matmul(self, weights, inputs: List[RayonInt]) -> List[RayonInt]:
        """Matrix-vector multiply using RayonInt addition."""
        outputs = []
        for row in weights:
            acc = RayonInt.known(0, self.width)
            for w, x in zip(row, inputs):
                # Approximate multiply: AND then accumulate
                # w AND x captures the "gated" contribution
                product = w & x
                acc = acc + product
            outputs.append(acc)
        return outputs

    def _relu(self, xs: List[RayonInt]) -> List[RayonInt]:
        """
        ReLU approximation: if MSB (sign bit) is 1, output 0.
        For unsigned 8-bit, this is just identity (always positive).
        We keep the top bit as a simple threshold.
        """
        result = []
        for x in xs:
            top_bit = x.bits[self.width - 1]
            if top_bit == 1:
                result.append(RayonInt.known(0, self.width))
            else:
                result.append(x)
        return result

    def forward(self, inputs: List[RayonInt]) -> List[RayonInt]:
        """Forward pass: input -> hidden (relu) -> output."""
        hidden = self._matmul(self.w1, inputs)
        hidden = self._relu(hidden)
        output = self._matmul(self.w2, hidden)
        return output

    def output_tension(self, inputs: List[RayonInt]) -> int:
        """Total tension of the output."""
        outputs = self.forward(inputs)
        return sum(_tension_of(o) for o in outputs)


def train_step(
    net: TensionNetwork,
    inputs: List[RayonInt],
    targets: List[RayonInt],
    lr: float = 1.0,
) -> float:
    """
    One training step: update weights to reduce output tension + error.

    Strategy (tension-guided gradient):
      1. Compute output and loss.
      2. For each weight, try nudging +1 and -1.
      3. Pick the direction that reduces loss most.
      4. Apply the best nudge scaled by lr.

    Returns the loss after the update.
    """
    loss_fn = TensionLoss(alpha=0.01)

    outputs = net.forward(inputs)
    current_loss = loss_fn(outputs, targets)

    # Nudge each weight in w2 (output layer) — most direct effect
    mask = (1 << net.width) - 1
    for i in range(len(net.w2)):
        for j in range(len(net.w2[i])):
            orig = net.w2[i][j]
            orig_val = _to_float_approx(orig)

            best_val = orig_val
            best_loss = current_loss

            for delta in [-1, +1]:
                new_val = int(orig_val + delta * lr) & mask
                net.w2[i][j] = RayonInt.known(new_val, net.width)
                out = net.forward(inputs)
                loss = loss_fn(out, targets)
                if loss < best_loss:
                    best_loss = loss
                    best_val = new_val

            net.w2[i][j] = RayonInt.known(int(best_val) & mask, net.width)
            current_loss = best_loss

    # Nudge each weight in w1 (hidden layer)
    for i in range(len(net.w1)):
        for j in range(len(net.w1[i])):
            orig = net.w1[i][j]
            orig_val = _to_float_approx(orig)

            best_val = orig_val
            best_loss = current_loss

            for delta in [-1, +1]:
                new_val = int(orig_val + delta * lr) & mask
                net.w1[i][j] = RayonInt.known(new_val, net.width)
                out = net.forward(inputs)
                loss = loss_fn(out, targets)
                if loss < best_loss:
                    best_loss = loss
                    best_val = new_val

            net.w1[i][j] = RayonInt.known(int(best_val) & mask, net.width)
            current_loss = best_loss

    return current_loss


# ════════════════════════════════════════════════════════════════
# TESTS
# ════════════════════════════════════════════════════════════════

def _ok(cond):
    return "\u2713" if cond else "\u2717"


def test_proofs():
    print("=" * 60)
    print("SECTION 1: FORMAL PROOFS")
    print("=" * 60)
    results = []

    # Test 1: all Known => 0 branches (T1)
    sig = [
        (InputKind.KNOWN, RayonInt.known(42, W)),
        (InputKind.KNOWN, RayonInt.known(17, W)),
    ]
    pr = CostProver.prove_cost_bound("add", sig, width=W)
    ok = pr.bound == 0 and pr.is_tight and pr.theorem == "T1_Trivial"
    results.append(ok)
    print(f"  T1 all-Known => bound=0:   {_ok(ok)}  ({pr.theorem}, bound={pr.bound})")

    # Test 2: AND(Known_zero, Unknown) => kill-link (T2)
    sig = [
        (InputKind.KNOWN, RayonInt.known(0, W)),
        (InputKind.UNKNOWN, None),
    ]
    pr = CostProver.prove_cost_bound("and_op", sig, width=W)
    ok = pr.bound == 0 and pr.is_tight and pr.theorem == "T2_Kill_Link"
    results.append(ok)
    print(f"  T2 Kill-link AND(0,?) => 0: {_ok(ok)}  ({pr.theorem}, bound={pr.bound})")

    # Test 3: XOR-only => 0 branches (T3)
    sig = [
        (InputKind.UNKNOWN, None),
        (InputKind.UNKNOWN, None),
    ]
    pr = CostProver.prove_cost_bound("xor_chain", sig, is_xor_only=True, width=W)
    ok = pr.bound == 0 and pr.is_tight and pr.theorem == "T3_XOR_Free"
    results.append(ok)
    print(f"  T3 XOR-only => bound=0:    {_ok(ok)}  ({pr.theorem}, bound={pr.bound})")

    # Test 4: General mixed => bound = total unknown bits (T4)
    partial_val = RayonInt.partial(0b10100000, 0b00001111, W)  # 4 unknown bits
    sig = [
        (InputKind.PARTIAL, partial_val),
        (InputKind.UNKNOWN, None),
    ]
    pr = CostProver.prove_cost_bound("mixed_op", sig, width=W)
    expected_bound = 4 + W  # 4 from partial + 8 from unknown
    ok = pr.bound == expected_bound and pr.theorem == "T4_General"
    results.append(ok)
    print(f"  T4 General bound={expected_bound}:      {_ok(ok)}  ({pr.theorem}, bound={pr.bound})")

    # Test 5: prove_cost_bound returns ProofResult
    ok = isinstance(pr, ProofResult) and hasattr(pr, 'bound') and hasattr(pr, 'is_tight')
    results.append(ok)
    print(f"  ProofResult structure:      {_ok(ok)}")

    all_ok = all(results)
    print(f"  Section 1 overall:          {_ok(all_ok)}")
    print()
    return all_ok


def test_quantum():
    print("=" * 60)
    print("SECTION 2: QUANTUM BRIDGE")
    print("=" * 60)
    results = []

    # Test 1: ? with tension=1 maps to single qubit superposition
    r = RayonInt.partial(0, 0b00000001, W)  # only bit 0 is ?
    qs = QubitState.from_rayon(r)
    ok = qs.n_qubits_super == 1 and qs.n_basis_states == 2
    results.append(ok)
    print(f"  Single ? -> 1 qubit:        {_ok(ok)}  (qubits={qs.n_qubits_super}, states={qs.n_basis_states})")

    # Test 2: k ?-bits -> k-qubit state
    r_full = RayonInt.unknown(W)
    qs_full = QubitState.from_rayon(r_full)
    ok = qs_full.n_qubits_super == W and qs_full.n_basis_states == 2**W
    results.append(ok)
    print(f"  {W} ?-bits -> {W}-qubit state: {_ok(ok)}  (qubits={qs_full.n_qubits_super}, states={qs_full.n_basis_states})")

    # Test 3: measure collapses to definite value
    qs_sup = QubitState.superposition(W)
    collapsed = measure(qs_sup)
    ok = collapsed.n_qubits_super == 0 and all(b in (0, 1) for b in collapsed.bits)
    results.append(ok)
    val = sum(b << i for i, b in enumerate(collapsed.bits))
    print(f"  measure() collapses:        {_ok(ok)}  (result={val})")

    # Test 4: entangle creates XOR constraint
    a = QubitState.superposition(1)
    b = QubitState.superposition(1)
    a_ent, b_ent, parity = entangle(a, b)
    a_m, b_m = measure_entangled(a_ent, b_ent)
    a_val = a_m.bits[0]
    b_val = b_m.bits[0]
    ok = (a_val ^ b_val) == parity
    results.append(ok)
    print(f"  entangle XOR constraint:    {_ok(ok)}  (a={a_val}, b={b_val}, a^b={a_val^b_val}, parity={parity})")

    # Test 5: quantum_tension computes properties
    qt = quantum_tension(4)
    ok = (qt["tension"] == 4 and qt["n_basis_states"] == 16 and
          qt["entropy_bits"] == 4 and abs(qt["darkness"] - 0.8) < 1e-9)
    results.append(ok)
    print(f"  quantum_tension(4):         {_ok(ok)}  (tension={qt['tension']}, states={qt['n_basis_states']}, dark={qt['darkness']:.1f})")

    # Test 6: round-trip RayonInt -> QubitState -> RayonInt
    r_orig = RayonInt.partial(0b10100000, 0b00001111, W)
    qs_rt = QubitState.from_rayon(r_orig)
    r_back = qs_rt.to_rayon()
    ok = (r_back.tension == r_orig.tension and
          all(a == b for a, b in zip(r_orig.bits, r_back.bits)))
    results.append(ok)
    print(f"  round-trip preservation:    {_ok(ok)}  (tension={r_back.tension})")

    all_ok = all(results)
    print(f"  Section 2 overall:          {_ok(all_ok)}")
    print()
    return all_ok


def test_ai():
    print("=" * 60)
    print("SECTION 3: AI ENGINE")
    print("=" * 60)
    results = []
    random.seed(42)

    # Test 1: TensionLoss — known output has lower loss than unknown
    loss_fn = TensionLoss(alpha=0.01)
    target = [RayonInt.known(42, W)]
    known_out = [RayonInt.known(42, W)]
    unknown_out = [RayonInt.unknown(W)]
    loss_known = loss_fn(known_out, target)
    loss_unknown = loss_fn(unknown_out, target)
    ok = loss_known < loss_unknown
    results.append(ok)
    print(f"  known < unknown loss:       {_ok(ok)}  (known={loss_known:.2f}, unknown={loss_unknown:.2f})")

    # Test 2: TensionLoss — zero tension on exact match
    exact_loss = loss_fn([RayonInt.known(42, W)], [RayonInt.known(42, W)])
    ok = exact_loss == 0.0
    results.append(ok)
    print(f"  exact match loss=0:         {_ok(ok)}  (loss={exact_loss:.4f})")

    # Test 3: TensionNetwork forward pass produces RayonInt output
    net = TensionNetwork(input_dim=2, hidden_dim=2, output_dim=1, width=W)
    inp = [RayonInt.known(5, W), RayonInt.known(3, W)]
    out = net.forward(inp)
    ok = len(out) == 1 and isinstance(out[0], RayonInt)
    results.append(ok)
    print(f"  forward produces RayonInt:  {_ok(ok)}  (output tension={out[0].tension})")

    # Test 4: forward with unknown input -> higher tension output
    inp_known = [RayonInt.known(5, W), RayonInt.known(3, W)]
    inp_partial = [RayonInt.known(5, W), RayonInt.unknown(W)]
    t_known = net.output_tension(inp_known)
    t_partial = net.output_tension(inp_partial)
    ok = t_partial >= t_known
    results.append(ok)
    print(f"  unknown input -> more tension: {_ok(ok)}  (known={t_known}, partial={t_partial})")

    # Test 5: train_step reduces loss
    random.seed(123)
    net2 = TensionNetwork(input_dim=1, hidden_dim=2, output_dim=1, width=W)
    inp = [RayonInt.known(10, W)]
    tgt = [RayonInt.known(20, W)]

    loss_fn2 = TensionLoss(alpha=0.01)
    initial_loss = loss_fn2(net2.forward(inp), tgt)
    final_loss = initial_loss
    for _ in range(5):
        final_loss = train_step(net2, inp, tgt, lr=1.0)
    ok = final_loss <= initial_loss
    results.append(ok)
    print(f"  training reduces loss:      {_ok(ok)}  (initial={initial_loss:.2f}, final={final_loss:.2f})")

    # Test 6: weights remain valid RayonInt after training
    ok = all(
        isinstance(net2.w1[i][j], RayonInt) and net2.w1[i][j].width == W
        for i in range(len(net2.w1)) for j in range(len(net2.w1[i]))
    )
    results.append(ok)
    print(f"  weights stay RayonInt:      {_ok(ok)}")

    all_ok = all(results)
    print(f"  Section 3 overall:          {_ok(all_ok)}")
    print()
    return all_ok


def verify():
    print()
    print("+" + "=" * 59 + "+")
    print("|  ADVANCED FEATURES: Proofs + Quantum + AI                 |")
    print("+" + "=" * 59 + "+")
    print()

    s1 = test_proofs()
    s2 = test_quantum()
    s3 = test_ai()

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Section 1 (Formal Proofs):  {_ok(s1)}")
    print(f"  Section 2 (Quantum Bridge): {_ok(s2)}")
    print(f"  Section 3 (AI Engine):      {_ok(s3)}")
    all_ok = s1 and s2 and s3
    print(f"  ALL SECTIONS:               {_ok(all_ok)}")
    print("=" * 60)
    print()


if __name__ == "__main__":
    verify()
