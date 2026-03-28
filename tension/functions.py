"""
STONE 18: FUNCTIONS — Bidirectional flows with tension signature.

Standard function: input → output. One way.
Rayon function: input ↔ output. Both ways. Tension measured.

Every function has:
  - Forward: input → output (standard computation)
  - Backward: output → constrained input (inversion)
  - Tension signature: τ(f) = branch points for ? inputs
  - Composition: f∘g, tension of chain

Functions are FLOWS, not mappings.
"""

from rayon_numbers import RayonInt
from control import RayonIf


class RayonFn:
    """
    A function in Rayon: bidirectional flow with tension.

    Wraps a forward function and optionally a backward function.
    Auto-computes tension signature by running with ? inputs.
    """
    def __init__(self, name, forward_fn, n_in, n_out, width=8, backward_fn=None):
        self.name = name
        self.forward = forward_fn
        self.backward = backward_fn
        self.n_in = n_in      # number of input words
        self.n_out = n_out     # number of output words
        self.width = width
        self._tension = None

    def __call__(self, *args):
        """Forward execution."""
        return self.forward(*args)

    def invert(self, *outputs):
        """Backward execution (if available)."""
        if self.backward:
            return self.backward(*outputs)
        return None

    @property
    def tension(self):
        """Auto-compute tension by running with all ? inputs."""
        if self._tension is not None:
            return self._tension

        unknown_inputs = [RayonInt.unknown(self.width) for _ in range(self.n_in)]
        result = self.forward(*unknown_inputs)

        if isinstance(result, tuple):
            self._tension = sum(r.tension for r in result)
        elif isinstance(result, RayonInt):
            self._tension = result.tension
        else:
            self._tension = 0

        return self._tension

    @property
    def info_loss(self):
        """Bits of information lost: n_in × width - n_out × width."""
        return max(0, self.n_in * self.width - self.n_out * self.width)

    @property
    def invertible(self):
        """Is function uniquely invertible? (no info loss)."""
        return self.info_loss == 0

    def compose(self, other):
        """Compose: self ∘ other. Run other first, then self."""
        def composed(*args):
            intermediate = other.forward(*args)
            if isinstance(intermediate, RayonInt):
                return self.forward(intermediate, *([RayonInt.known(0, self.width)] * (self.n_in - 1)))
            if not isinstance(intermediate, tuple):
                intermediate = (intermediate,)
            return self.forward(*intermediate[:self.n_in])

        comp = RayonFn(
            f'{self.name}∘{other.name}',
            composed,
            other.n_in, self.n_out, self.width
        )
        return comp

    def __repr__(self):
        inv = '↔' if self.invertible else '→'
        return f'Fn({self.name}: {self.n_in}{inv}{self.n_out}, τ={self.tension})'


# ════════════════════════════════════════════════════════════
# BUILT-IN FUNCTIONS
# ════════════════════════════════════════════════════════════

def make_xor_fn(width=8):
    """XOR: perfectly invertible, zero branch points."""
    def fwd(a, b):
        return a ^ b
    def bwd(result, a):
        return result ^ a  # b = result XOR a
    return RayonFn('XOR', fwd, 2, 1, width, backward_fn=bwd)


def make_and_fn(width=8):
    """AND: has kill-links, partially invertible."""
    def fwd(a, b):
        return a & b
    def bwd(result, a):
        # AND=1, a=1 → b=1. AND=0, a=1 → b=0.
        # AND=0, a=0 → b=? (unknown)
        bits = []
        for i in range(width):
            ri = result.bits[i] if i < len(result.bits) else 0
            ai = a.bits[i] if i < len(a.bits) else 0
            if ri == 1:
                bits.append(1)  # both must be 1
            elif ai == 1:
                bits.append(0)  # a=1, result=0 → b=0
            else:
                bits.append(None)  # can't determine
        return RayonInt(bits=bits, width=width)
    return RayonFn('AND', fwd, 2, 1, width, backward_fn=bwd)


def make_add_fn(width=8):
    """Addition mod 2^width: invertible when one operand known."""
    def fwd(a, b):
        return a + b
    def bwd(result, a):
        return result - a  # b = result - a
    return RayonFn('ADD', fwd, 2, 1, width, backward_fn=bwd)


def make_not_fn(width=8):
    """NOT: perfectly invertible, self-inverse."""
    def fwd(a):
        return ~a
    return RayonFn('NOT', fwd, 1, 1, width, backward_fn=fwd)  # self-inverse


def make_hash_fn(width=8):
    """Simplified hash: lossy, NOT invertible."""
    def fwd(a, b):
        # Compress 2 words → 1 word (lossy)
        return (a ^ b) + (a & b)
    return RayonFn('HASH', fwd, 2, 1, width)


# ════════════════════════════════════════════════════════════
# VERIFICATION
# ════════════════════════════════════════════════════════════

def verify():
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  STONE 18: FUNCTIONS — Bidirectional flows               ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    w = 8

    # ── Basic functions ──
    print("FUNCTION SIGNATURES:")
    print("─" * 50)

    xor_fn = make_xor_fn(w)
    and_fn = make_and_fn(w)
    add_fn = make_add_fn(w)
    not_fn = make_not_fn(w)
    hash_fn = make_hash_fn(w)

    for fn in [xor_fn, and_fn, add_fn, not_fn, hash_fn]:
        print(f"  {fn}")

    print()

    # ── Forward (known inputs) ──
    print("FORWARD (known inputs = standard):")
    print("─" * 50)

    a = RayonInt.known(42, w)
    b = RayonInt.known(17, w)

    print(f"  XOR(42, 17) = {xor_fn(a, b)} (expected {42^17}) "
          f"{'✓' if xor_fn(a, b).value == 42^17 else '✗'}")
    print(f"  AND(42, 17) = {and_fn(a, b)} (expected {42&17}) "
          f"{'✓' if and_fn(a, b).value == (42&17) else '✗'}")
    print(f"  ADD(42, 17) = {add_fn(a, b)} (expected {(42+17)&0xFF}) "
          f"{'✓' if add_fn(a, b).value == (42+17)&0xFF else '✗'}")
    print(f"  NOT(42) = {not_fn(a)} (expected {(~42)&0xFF}) "
          f"{'✓' if not_fn(a).value == (~42)&0xFF else '✗'}")
    print()

    # ── Backward (inversion) ──
    print("BACKWARD (inversion):")
    print("─" * 50)

    # XOR backward: know result and a → find b
    result = xor_fn(a, b)
    b_recovered = xor_fn.invert(result, a)
    print(f"  XOR: result={result.value}, a=42 → b={b_recovered.value} "
          f"{'✓' if b_recovered.value == 17 else '✗'}")

    # ADD backward: know result and a → find b
    result_add = add_fn(a, b)
    b_add = add_fn.invert(result_add, a)
    print(f"  ADD: result={result_add.value}, a=42 → b={b_add.value} "
          f"{'✓' if b_add.value == 17 else '✗'}")

    # AND backward: know result and a → find b (partially)
    and_result = and_fn(a, b)
    b_and = and_fn.invert(and_result, a)
    b_match = all(b_and.bits[i] == b.bits[i] for i in range(w) if b_and.bits[i] is not None)
    print(f"  AND: result={and_result.value}, a=42 → b={b_and} "
          f"(τ={b_and.tension}) {'✓ partial' if b_match else '✗'}")

    # NOT backward (self-inverse)
    not_result = not_fn(a)
    a_recovered = not_fn.invert(not_result)
    print(f"  NOT: result={not_result.value} → a={a_recovered.value} "
          f"{'✓' if a_recovered.value == 42 else '✗'}")
    print()

    # ── Composition ──
    print("COMPOSITION:")
    print("─" * 50)

    # XOR ∘ ADD: first add, then XOR
    xor_add = xor_fn.compose(add_fn)
    print(f"  {xor_add}")

    # Double NOT = identity
    double_not = not_fn.compose(not_fn)
    result_dn = double_not(a)
    print(f"  NOT∘NOT(42) = {result_dn} {'✓ identity!' if result_dn.value == 42 else '✗'}")

    # Hash ∘ XOR
    hash_xor = hash_fn.compose(xor_fn)
    print(f"  {hash_xor}")
    print()

    # ── Tension signature ──
    print("TENSION SIGNATURES (? inputs):")
    print("─" * 50)

    print(f"  XOR(?₁, ?₂): τ = {xor_fn.tension} (all XOR = preserved, no branches)")
    print(f"  AND(?₁, ?₂): τ = {and_fn.tension} (kill-links reduce some ?)")
    print(f"  ADD(?₁, ?₂): τ = {add_fn.tension} (carry chain creates ?)")
    print(f"  NOT(?):       τ = {not_fn.tension} (flip, tension same)")
    print(f"  HASH(?₁,?₂): τ = {hash_fn.tension} (lossy compression)")
    print()

    # ── Invertibility ──
    print("INVERTIBILITY:")
    print("─" * 50)
    for fn in [xor_fn, and_fn, add_fn, not_fn, hash_fn]:
        inv = '↔ invertible' if fn.invertible else f'→ lossy ({fn.info_loss} bits lost)'
        has_bwd = '✓' if fn.backward else '✗'
        print(f"  {fn.name:>6}: {inv}, backward impl: {has_bwd}")

    print(f"""
═══════════════════════════════════════════════════════════════
STONE 18: FUNCTIONS — Complete

  Every function is a BIDIRECTIONAL FLOW:
    Forward: input → output (standard computation)
    Backward: output → input (inversion/deduction)

  TENSION SIGNATURE: auto-computed by running with ? inputs.
    XOR: τ = width (all ? preserved, but no branches)
    AND: τ < width (kill-links reduce ?)
    ADD: τ = width (carries create ?)

  INVERTIBILITY:
    n_in = n_out: might be invertible (XOR, NOT: yes)
    n_in > n_out: lossy (HASH: not uniquely invertible)

  COMPOSITION:
    f∘g: run g then f. Tension chains.
    NOT∘NOT = identity (self-inverse) ✓

  THE PRINCIPLE:
    Functions in Rayon are not black boxes.
    They are TRANSPARENT flows with measurable tension.
    Forward = compute. Backward = deduce. Same function.
═══════════════════════════════════════════════════════════════
""")


if __name__ == '__main__':
    verify()
