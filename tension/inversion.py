"""
STONE 20: INVERSION -- Running programs backward.

Standard execution: input -> f -> g -> h -> output. One direction.
Rayon inversion: output -> h^-1 -> g^-1 -> f^-1 -> input. Reverse the flow.

Given a SEQUENCE of RayonFn operations and a known output,
invert the chain to deduce the original input.

Chain rule: to invert f composed with g (i.e. g then f),
  invert f first (outermost), then invert g (innermost).

Non-invertible operations are detected and reported.
"""

from rayon_numbers import RayonInt
from functions import RayonFn, make_xor_fn, make_and_fn, make_add_fn, make_not_fn


# ================================================================
# STEP: a single operation in a chain, binding one operand
# ================================================================

class Step:
    """
    One step in a computation chain.

    Wraps a RayonFn together with any fixed operands so the chain
    becomes a sequence of single-input, single-output stages.

    For a 2-input function like ADD(x, 5):
        fn        = ADD
        fixed_arg = RayonInt(5)
        arg_pos   = 1        (the fixed arg is the second operand)

    For a 1-input function like NOT(x):
        fn        = NOT
        fixed_arg = None
    """
    def __init__(self, fn, fixed_arg=None, arg_pos=1):
        self.fn = fn
        self.fixed_arg = fixed_arg
        self.arg_pos = arg_pos  # which position the fixed arg occupies

    def forward(self, x):
        """Run forward: x -> output."""
        if self.fn.n_in == 1:
            return self.fn(x)
        if self.arg_pos == 1:
            return self.fn(x, self.fixed_arg)
        else:
            return self.fn(self.fixed_arg, x)

    def backward(self, output):
        """Run backward: output -> x."""
        if self.fn.backward is None:
            return None
        if self.fn.n_in == 1:
            return self.fn.invert(output)
        # For 2-input fns, backward(output, known_arg) -> unknown_arg
        return self.fn.invert(output, self.fixed_arg)

    @property
    def invertible(self):
        return self.fn.backward is not None

    def __repr__(self):
        if self.fixed_arg is not None:
            return f"{self.fn.name}(x, {self.fixed_arg})"
        return f"{self.fn.name}(x)"


# ================================================================
# CHAIN: a sequence of steps, invertible as a whole
# ================================================================

class Chain:
    """
    A sequence of Steps executed left-to-right (forward)
    or right-to-left (backward / inversion).

    Forward:  input -> step[0] -> step[1] -> ... -> step[n-1] -> output
    Backward: output -> step[n-1]^-1 -> ... -> step[1]^-1 -> step[0]^-1 -> input
    """
    def __init__(self, steps=None):
        self.steps = list(steps or [])

    def append(self, step):
        self.steps.append(step)

    def forward(self, x):
        """Run the full chain forward."""
        val = x
        for step in self.steps:
            val = step.forward(val)
        return val

    def invert(self, output):
        """
        Run the chain BACKWARD: invert last step first, then second-to-last, etc.
        Returns the deduced input, which may contain ? bits if any step
        is only partially invertible.
        """
        val = output
        for step in reversed(self.steps):
            result = step.backward(val)
            if result is None:
                return None  # non-invertible step blocks the whole chain
            val = result
        return val

    def invert_verbose(self, output):
        """Invert with step-by-step trace."""
        val = output
        trace = [("output", val)]
        for step in reversed(self.steps):
            result = step.backward(val)
            if result is None:
                trace.append((f"{step.fn.name}^-1", "BLOCKED"))
                return None, trace
            val = result
            trace.append((f"{step.fn.name}^-1", val))
        return val, trace

    @property
    def fully_invertible(self):
        return all(s.invertible for s in self.steps)

    def non_invertible_steps(self):
        return [s for s in self.steps if not s.invertible]

    def __repr__(self):
        names = " -> ".join(str(s) for s in self.steps)
        inv = "invertible" if self.fully_invertible else "partial"
        return f"Chain[{names}] ({inv})"


# ================================================================
# SHA-LIKE PRIMITIVES
# ================================================================

def make_ch_fn(width=8):
    """
    SHA-256 Ch function: Ch(x, y, z) = (x AND y) XOR (NOT x AND z).
    3 inputs -> 1 output. Lossy in general, but partially invertible
    when some inputs are known.

    For inversion with x known: given output and x,
    we can recover y at positions where x=1, and z where x=0.
    """
    def fwd(x, y, z):
        return (x & y) ^ (~x & z)

    return RayonFn('Ch', fwd, 3, 1, width, backward_fn=None)


def make_ch_step(x_val, y_val, width=8):
    """
    Create a Step that computes Ch(x, y, z) with x and y fixed.
    The variable input is z.
    Ch(x, y, z) = (x AND y) XOR (NOT x AND z)
    When x and y are known, this is: constant XOR (NOT_x AND z).
    Invertible for z at bit positions where NOT_x = 1 (i.e. x = 0).
    """
    ch_fn_name = f"Ch({x_val},{y_val},_)"

    def fwd_z(z):
        x = RayonInt.known(x_val, width)
        y = RayonInt.known(y_val, width)
        return (x & y) ^ (~x & z)

    def bwd_z(output):
        x = RayonInt.known(x_val, width)
        y = RayonInt.known(y_val, width)
        # output = (x AND y) XOR (NOT_x AND z)
        # (NOT_x AND z) = output XOR (x AND y)
        # At positions where NOT_x bit = 1 (x bit = 0): z bit = (output XOR (x AND y)) bit
        # At positions where NOT_x bit = 0 (x bit = 1): z is unknown (AND killed it)
        xy = x & y
        rhs = output ^ xy  # this equals NOT_x AND z
        bits = []
        for i in range(width):
            xi = x.bits[i]
            if xi == 0:
                # NOT_x bit = 1, so z bit = rhs bit
                bits.append(rhs.bits[i])
            else:
                # NOT_x bit = 0, AND killed z -> can't recover
                bits.append(None)
        return RayonInt(bits=bits, width=width)

    fn = RayonFn(ch_fn_name, fwd_z, 1, 1, width, backward_fn=bwd_z)
    return Step(fn)


# ================================================================
# VERIFICATION
# ================================================================

def mark(ok):
    return "\u2713" if ok else "\u2717"


def verify():
    print("=" * 62)
    print("  STONE 20: INVERSION -- Running programs backward")
    print("=" * 62)
    print()

    W = 8
    mask = (1 << W) - 1

    # ----------------------------------------------------------
    # TEST 1: Chain add(5) then xor(3), invert from output=6
    # Forward: 0 -> add(5) -> 5 -> xor(3) -> 6
    # Backward: 6 -> xor^-1(3) -> 5 -> sub(5) -> 0
    # ----------------------------------------------------------
    print("TEST 1: add(5) then xor(3) -- chain inversion")
    print("-" * 50)

    add_fn = make_add_fn(W)
    xor_fn = make_xor_fn(W)

    five = RayonInt.known(5, W)
    three = RayonInt.known(3, W)

    chain = Chain([
        Step(add_fn, fixed_arg=five, arg_pos=1),
        Step(xor_fn, fixed_arg=three, arg_pos=1),
    ])

    # Verify forward
    inp = RayonInt.known(0, W)
    fwd_result = chain.forward(inp)
    print(f"  Forward: 0 -> add(5) -> xor(3) -> {fwd_result.value}")

    # Invert from output=6
    output = RayonInt.known(6, W)
    recovered, trace = chain.invert_verbose(output)

    print(f"  Backward trace:")
    for label, val in trace:
        if isinstance(val, str):
            print(f"    {label}: {val}")
        else:
            print(f"    {label}: {val}")

    ok1 = recovered is not None and recovered.value == 0
    print(f"  Recovered input: {recovered.value if recovered else 'FAILED'} (expected 0) {mark(ok1)}")
    print()

    # ----------------------------------------------------------
    # TEST 2: Longer chain: not -> add(10) -> xor(0xAA)
    # Forward: 42 -> NOT -> 213 -> add(10) -> 223 -> xor(0xAA) -> 117
    # Backward: 117 -> xor^-1(0xAA) -> 223 -> sub(10) -> 213 -> NOT^-1 -> 42
    # ----------------------------------------------------------
    print("TEST 2: NOT -> add(10) -> xor(0xAA) -- three-step inversion")
    print("-" * 50)

    not_fn = make_not_fn(W)
    ten = RayonInt.known(10, W)
    aa = RayonInt.known(0xAA, W)

    chain2 = Chain([
        Step(not_fn),
        Step(add_fn, fixed_arg=ten, arg_pos=1),
        Step(xor_fn, fixed_arg=aa, arg_pos=1),
    ])

    inp2 = RayonInt.known(42, W)
    fwd2 = chain2.forward(inp2)
    # NOT(42) = 213, 213+10 = 223, 223 XOR 0xAA = 223^170 = 117
    expected_fwd = ((~42 & mask) + 10) & mask
    expected_fwd = expected_fwd ^ 0xAA
    print(f"  Forward: 42 -> NOT -> add(10) -> xor(0xAA) -> {fwd2.value} (expected {expected_fwd})")

    output2 = RayonInt.known(fwd2.value, W)
    recovered2, trace2 = chain2.invert_verbose(output2)

    print(f"  Backward trace:")
    for label, val in trace2:
        if isinstance(val, str):
            print(f"    {label}: {val}")
        else:
            print(f"    {label}: {val}")

    ok2 = recovered2 is not None and recovered2.value == 42
    print(f"  Recovered input: {recovered2.value if recovered2 else 'FAILED'} (expected 42) {mark(ok2)}")
    print()

    # ----------------------------------------------------------
    # TEST 3: SHA-like: Ch(x,y,z) then add then xor
    # Ch with x=0b11001100, y=0b10101010 fixed; z is the unknown.
    # Then add(7), then xor(0x55).
    # ----------------------------------------------------------
    print("TEST 3: SHA-like chain: Ch(0xCC,0xAA,z) -> add(7) -> xor(0x55)")
    print("-" * 50)

    x_val = 0xCC
    y_val = 0xAA
    z_val = 0x37  # the value we want to recover

    ch_step = make_ch_step(x_val, y_val, W)
    seven = RayonInt.known(7, W)
    h55 = RayonInt.known(0x55, W)

    chain3 = Chain([
        ch_step,
        Step(add_fn, fixed_arg=seven, arg_pos=1),
        Step(xor_fn, fixed_arg=h55, arg_pos=1),
    ])

    z_input = RayonInt.known(z_val, W)
    fwd3 = chain3.forward(z_input)
    print(f"  Forward: z=0x{z_val:02X} -> Ch -> add(7) -> xor(0x55) -> {fwd3.value} (0x{fwd3.value:02X})")

    output3 = RayonInt.known(fwd3.value, W)
    recovered3, trace3 = chain3.invert_verbose(output3)

    print(f"  Backward trace:")
    for label, val in trace3:
        if isinstance(val, str):
            print(f"    {label}: {val}")
        else:
            v_str = f"{val.value} (0x{val.value:02X})" if hasattr(val, 'value') and val.value is not None else str(val)
            print(f"    {label}: {v_str}")

    # Ch is partially invertible: at x=1 positions, z is unknown
    if recovered3 is not None:
        # Check known bits match
        match_bits = 0
        total_known = 0
        for i in range(W):
            if recovered3.bits[i] is not None:
                total_known += 1
                if recovered3.bits[i] == ((z_val >> i) & 1):
                    match_bits += 1
        ok3 = match_bits == total_known and total_known > 0
        print(f"  Recovered: {recovered3} (tension={recovered3.tension})")
        print(f"  Known bits: {total_known}/{W}, all correct: {mark(ok3)}")
        # Verify the unknown bits correspond to x=1 positions
        x_ones = bin(x_val).count('1')
        print(f"  Unknown bits: {recovered3.tension} (= {x_ones} positions where x=1)")
        ok3_tension = recovered3.tension == x_ones
        print(f"  Tension matches x=1 count: {mark(ok3_tension)}")
    else:
        ok3 = False
        ok3_tension = False
        print(f"  Inversion BLOCKED")
    print()

    # ----------------------------------------------------------
    # TEST 4: Detect non-invertible operation (AND with both unknown)
    # ----------------------------------------------------------
    print("TEST 4: Non-invertible detection -- AND with no backward")
    print("-" * 50)

    and_fn = make_and_fn(W)
    # AND's backward needs a known operand. If we build a chain with AND
    # but provide NO fixed argument, the Step can't invert.
    # We simulate: the hash function has no backward at all.
    from functions import make_hash_fn
    hash_fn = make_hash_fn(W)

    # A chain with a non-invertible step
    chain4 = Chain([
        Step(xor_fn, fixed_arg=three, arg_pos=1),
        Step(hash_fn, fixed_arg=five, arg_pos=1),  # HASH has no backward
        Step(add_fn, fixed_arg=ten, arg_pos=1),
    ])

    print(f"  Chain: {chain4}")
    print(f"  Fully invertible: {chain4.fully_invertible}")
    non_inv = chain4.non_invertible_steps()
    print(f"  Non-invertible steps: {[str(s) for s in non_inv]}")

    output4 = RayonInt.known(99, W)
    recovered4, trace4 = chain4.invert_verbose(output4)

    print(f"  Backward trace:")
    for label, val in trace4:
        if isinstance(val, str):
            print(f"    {label}: {val}")
        else:
            print(f"    {label}: {val}")

    ok4 = recovered4 is None
    print(f"  Inversion correctly blocked: {mark(ok4)}")
    print()

    # ----------------------------------------------------------
    # TEST 5: AND partial invertibility -- backward works but has ? bits
    # ----------------------------------------------------------
    print("TEST 5: AND partial inversion -- known bits recovered, unknown marked ?")
    print("-" * 50)

    # AND(x, 0b10101010): at positions where fixed=0, result is always 0
    # so x is unknown there. At positions where fixed=1, x = result bit.
    and_fixed = RayonInt.known(0xAA, W)
    and_step = Step(and_fn, fixed_arg=and_fixed, arg_pos=1)

    chain5 = Chain([and_step])

    x_in = RayonInt.known(0xFF, W)
    fwd5 = chain5.forward(x_in)
    print(f"  Forward: AND(0xFF, 0xAA) = {fwd5.value} (0x{fwd5.value:02X})")

    output5 = RayonInt.known(fwd5.value, W)
    recovered5 = chain5.invert(output5)

    if recovered5 is not None:
        known_correct = all(
            recovered5.bits[i] == ((0xFF >> i) & 1)
            for i in range(W) if recovered5.bits[i] is not None
        )
        unknown_count = recovered5.tension
        # At positions where 0xAA has 0, x is unknown (4 positions)
        zeros_in_mask = bin(0xAA ^ 0xFF).count('1')  # positions where AA=0
        ok5 = known_correct and unknown_count == zeros_in_mask
        print(f"  Recovered: {recovered5} (tension={recovered5.tension})")
        print(f"  Known bits correct: {mark(known_correct)}")
        print(f"  Unknown bits = {unknown_count} (expected {zeros_in_mask}): {mark(unknown_count == zeros_in_mask)}")
    else:
        ok5 = False
        print(f"  Inversion failed unexpectedly")
    print()

    # ----------------------------------------------------------
    # SUMMARY
    # ----------------------------------------------------------
    results = [
        ("Chain: add(5)->xor(3), invert from 6 to 0", ok1),
        ("Three-step: NOT->add(10)->xor(0xAA), recover 42", ok2),
        ("SHA-like: Ch->add->xor, partial recovery", ok3 and ok3_tension),
        ("Non-invertible detection (HASH blocks chain)", ok4),
        ("AND partial inversion (? at kill positions)", ok5),
    ]

    print("=" * 62)
    print("  SUMMARY")
    print("=" * 62)
    for desc, ok in results:
        print(f"  {mark(ok)} {desc}")

    all_pass = all(ok for _, ok in results)
    print()
    print(f"  {'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}")
    print()
    print("  INVERSION PRINCIPLE:")
    print("    Forward:  input -> f -> g -> h -> output")
    print("    Backward: output -> h^-1 -> g^-1 -> f^-1 -> input")
    print("    Chain rule: invert outermost first, work inward.")
    print("    Non-invertible steps block the chain.")
    print("    Partially invertible steps produce ? bits (tension).")
    print("=" * 62)
    print()


if __name__ == '__main__':
    verify()
