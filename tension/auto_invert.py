"""
AUTO-INVERT: Write a function forward, automatically run it backward.

Record operations as a tape during forward execution, then replay
the tape in reverse to invert. Each operation stores its inverse.

Invertible operations (perfect recovery):
  XOR(x, key)  -> XOR(result, key)
  ADD(x, k)    -> SUB(result, k)
  SUB(x, k)    -> ADD(result, k)
  ROTL(x, n)   -> ROTR(result, n)
  ROTR(x, n)   -> ROTL(result, n)
  NOT(x)       -> NOT(result)

Partially invertible (tension increases):
  AND(x, mask) -> some bits lost (0 AND ? = 0, information destroyed)
  OR(x, mask)  -> some bits lost (1 OR ? = 1, information destroyed)

Non-invertible: tension recorded, backward returns RayonInt with ? bits.
"""

from rayon_numbers import RayonInt
from arithmetic import rotl, rotr, shl, shr


# ════════════════════════════════════════════════════════════
# TAPE: records operations for replay
# ════════════════════════════════════════════════════════════

class TapeEntry:
    """Single recorded operation on the tape."""
    __slots__ = ('op_type', 'inputs', 'output', 'inverse_fn', 'tension_cost')

    def __init__(self, op_type, inputs, output, inverse_fn, tension_cost=0):
        self.op_type = op_type        # string name
        self.inputs = inputs          # tuple of auxiliary inputs (not the main operand)
        self.output = output          # result of forward
        self.inverse_fn = inverse_fn  # callable(output, *inputs) -> original
        self.tension_cost = tension_cost  # bits of information lost

    def __repr__(self):
        return f"TapeEntry({self.op_type}, tension_cost={self.tension_cost})"


# ════════════════════════════════════════════════════════════
# INVERTIBLE PROGRAM: tape-based forward/backward execution
# ════════════════════════════════════════════════════════════

class InvertibleProgram:
    """
    Records a sequence of operations as a tape, then replays backward.

    Usage:
        prog = InvertibleProgram(width=8)
        prog.xor(key)      # record XOR
        prog.add(constant)  # record ADD
        prog.rotl(3)        # record ROTL

        result = prog.forward(input_val)
        recovered = prog.backward(result)
        assert recovered.value == input_val.value
    """

    def __init__(self, width=8):
        self.width = width
        self.ops = []  # list of (op_name, args) to execute
        self.tape = []  # filled during forward, consumed during backward

    def _ensure_rayon(self, x):
        """Convert int to RayonInt if needed."""
        if isinstance(x, int):
            return RayonInt.known(x, self.width)
        return x

    # ── Register operations ──

    def xor(self, key):
        """XOR with key. Perfectly invertible: XOR is its own inverse."""
        self.ops.append(('xor', (key,)))
        return self

    def add(self, constant):
        """ADD constant. Perfectly invertible: inverse is SUB."""
        self.ops.append(('add', (constant,)))
        return self

    def sub(self, constant):
        """SUB constant. Perfectly invertible: inverse is ADD."""
        self.ops.append(('sub', (constant,)))
        return self

    def rotate_left(self, n):
        """ROTL by n. Perfectly invertible: inverse is ROTR."""
        self.ops.append(('rotl', (n,)))
        return self

    def rotate_right(self, n):
        """ROTR by n. Perfectly invertible: inverse is ROTL."""
        self.ops.append(('rotr', (n,)))
        return self

    def bit_not(self):
        """NOT. Perfectly invertible: NOT is its own inverse."""
        self.ops.append(('not', ()))
        return self

    def bit_and(self, mask):
        """AND with mask. PARTIALLY invertible: 0-bits in mask destroy info."""
        self.ops.append(('and', (mask,)))
        return self

    def bit_or(self, mask):
        """OR with mask. PARTIALLY invertible: 1-bits in mask destroy info."""
        self.ops.append(('or', (mask,)))
        return self

    # ── Forward execution ──

    def forward(self, x, *extra_args):
        """Execute all ops forward, recording tape."""
        x = self._ensure_rayon(x)
        self.tape = []

        for op_name, args in self.ops:
            # Resolve args: if int, convert to RayonInt
            resolved = []
            for a in args:
                if isinstance(a, int) and op_name not in ('rotl', 'rotr'):
                    resolved.append(RayonInt.known(a, self.width))
                else:
                    resolved.append(a)

            entry = self._execute_forward(op_name, x, resolved)
            self.tape.append(entry)
            x = entry.output

        return x

    def _execute_forward(self, op_name, x, args):
        """Execute one operation forward, return TapeEntry."""
        if op_name == 'xor':
            key = args[0]
            output = x ^ key
            inv = lambda out, k=key: out ^ k  # XOR is self-inverse
            return TapeEntry('xor', (key,), output, inv, tension_cost=0)

        elif op_name == 'add':
            k = args[0]
            output = x + k
            # Truncate to width
            output.bits = output.bits[:self.width]
            output.width = self.width
            inv = lambda out, k=k: _mod_sub(out, k, self.width)
            return TapeEntry('add', (k,), output, inv, tension_cost=0)

        elif op_name == 'sub':
            k = args[0]
            output = x - k
            output.bits = output.bits[:self.width]
            output.width = self.width
            inv = lambda out, k=k: _mod_add(out, k, self.width)
            return TapeEntry('sub', (k,), output, inv, tension_cost=0)

        elif op_name == 'rotl':
            n = args[0]
            output = rotl(x, n)
            inv = lambda out, n=n: rotr(out, n)
            return TapeEntry('rotl', (n,), output, inv, tension_cost=0)

        elif op_name == 'rotr':
            n = args[0]
            output = rotr(x, n)
            inv = lambda out, n=n: rotl(out, n)
            return TapeEntry('rotr', (n,), output, inv, tension_cost=0)

        elif op_name == 'not':
            output = ~x
            inv = lambda out: ~out
            return TapeEntry('not', (), output, inv, tension_cost=0)

        elif op_name == 'and':
            mask = args[0]
            output = x & mask
            # Tension: bits where mask is 0 are destroyed
            destroyed = sum(1 for i in range(self.width) if mask.bits[i] == 0)
            inv = lambda out, m=mask, w=self.width: _invert_and(out, m, w)
            return TapeEntry('and', (mask,), output, inv, tension_cost=destroyed)

        elif op_name == 'or':
            mask = args[0]
            output = x | mask
            destroyed = sum(1 for i in range(self.width) if mask.bits[i] == 1)
            inv = lambda out, m=mask, w=self.width: _invert_or(out, m, w)
            return TapeEntry('or', (mask,), output, inv, tension_cost=destroyed)

        else:
            raise ValueError(f"Unknown op: {op_name}")

    # ── Backward execution ──

    def backward(self, y, *extra_args):
        """Replay tape in reverse, applying inverses."""
        y = self._ensure_rayon(y)

        for entry in reversed(self.tape):
            y = entry.inverse_fn(y)
            # Ensure width
            y.bits = y.bits[:self.width]
            y.width = self.width

        return y

    @property
    def total_tension_cost(self):
        """Total information lost across all tape entries."""
        return sum(e.tension_cost for e in self.tape)


# ════════════════════════════════════════════════════════════
# HELPERS for inversion
# ════════════════════════════════════════════════════════════

def _mod_add(a, b, width):
    """Modular add, truncated to width."""
    result = a + b
    result.bits = result.bits[:width]
    result.width = width
    return result

def _mod_sub(a, b, width):
    """Modular sub, truncated to width."""
    result = a - b
    result.bits = result.bits[:width]
    result.width = width
    return result

def _invert_and(output, mask, width):
    """
    Invert AND: output = x & mask.
    Where mask bit = 1: output bit = x bit (recovered).
    Where mask bit = 0: output bit = 0 regardless of x -> x bit = ? (lost).
    """
    bits = []
    for i in range(width):
        if mask.bits[i] == 1:
            # This bit passed through: recovered
            bits.append(output.bits[i])
        else:
            # Mask was 0: AND killed this bit. Original could be anything.
            bits.append(None)  # ? = unknown
    return RayonInt(bits=bits, width=width)

def _invert_or(output, mask, width):
    """
    Invert OR: output = x | mask.
    Where mask bit = 0: output bit = x bit (recovered).
    Where mask bit = 1: output bit = 1 regardless of x -> x bit = ? (lost).
    """
    bits = []
    for i in range(width):
        if mask.bits[i] == 0:
            bits.append(output.bits[i])
        else:
            bits.append(None)  # lost
    return RayonInt(bits=bits, width=width)


# ════════════════════════════════════════════════════════════
# @invertible DECORATOR
# ════════════════════════════════════════════════════════════

class InvertibleContext:
    """
    Context provided to @invertible functions for recording operations.

    The decorated function uses ctx.xor(), ctx.add(), etc. instead of
    raw operators, so the tape is recorded automatically.
    """
    def __init__(self, width=8):
        self.width = width
        self.tape = []

    def _ensure_rayon(self, x):
        if isinstance(x, int):
            return RayonInt.known(x, self.width)
        return x

    def xor(self, x, key):
        x = self._ensure_rayon(x)
        key = self._ensure_rayon(key)
        output = x ^ key
        self.tape.append(TapeEntry('xor', (key,), output,
                                   lambda out, k=key: out ^ k, 0))
        return output

    def add(self, x, k):
        x = self._ensure_rayon(x)
        k = self._ensure_rayon(k)
        output = x + k
        output.bits = output.bits[:self.width]
        output.width = self.width
        self.tape.append(TapeEntry('add', (k,), output,
                                   lambda out, k=k: _mod_sub(out, k, self.width), 0))
        return output

    def sub(self, x, k):
        x = self._ensure_rayon(x)
        k = self._ensure_rayon(k)
        output = x - k
        output.bits = output.bits[:self.width]
        output.width = self.width
        self.tape.append(TapeEntry('sub', (k,), output,
                                   lambda out, k=k: _mod_add(out, k, self.width), 0))
        return output

    def rotl(self, x, n):
        x = self._ensure_rayon(x)
        output = rotl(x, n)
        self.tape.append(TapeEntry('rotl', (n,), output,
                                   lambda out, n=n: rotr(out, n), 0))
        return output

    def rotr(self, x, n):
        x = self._ensure_rayon(x)
        output = rotr(x, n)
        self.tape.append(TapeEntry('rotr', (n,), output,
                                   lambda out, n=n: rotl(out, n), 0))
        return output

    def bit_not(self, x):
        x = self._ensure_rayon(x)
        output = ~x
        self.tape.append(TapeEntry('not', (), output,
                                   lambda out: ~out, 0))
        return output

    def bit_and(self, x, mask):
        x = self._ensure_rayon(x)
        mask = self._ensure_rayon(mask)
        output = x & mask
        destroyed = sum(1 for i in range(self.width) if mask.bits[i] == 0)
        self.tape.append(TapeEntry('and', (mask,), output,
                                   lambda out, m=mask: _invert_and(out, m, self.width),
                                   tension_cost=destroyed))
        return output

    def bit_or(self, x, mask):
        x = self._ensure_rayon(x)
        mask = self._ensure_rayon(mask)
        output = x | mask
        destroyed = sum(1 for i in range(self.width) if mask.bits[i] == 1)
        self.tape.append(TapeEntry('or', (mask,), output,
                                   lambda out, m=mask: _invert_or(out, m, self.width),
                                   tension_cost=destroyed))
        return output

    def replay_backward(self, y):
        """Replay tape in reverse."""
        y = self._ensure_rayon(y)
        for entry in reversed(self.tape):
            y = entry.inverse_fn(y)
            y.bits = y.bits[:self.width]
            y.width = self.width
        return y


class InvertibleFunction:
    """Wrapper returned by @invertible. Has .forward() and .backward()."""

    def __init__(self, fn, width=8):
        self.fn = fn
        self.width = width
        self._last_ctx = None

    def forward(self, x, *args):
        """Run function forward, recording tape for later backward pass."""
        ctx = InvertibleContext(width=self.width)
        if isinstance(x, int):
            x = RayonInt.known(x, self.width)
        result = self.fn(ctx, x, *args)
        self._last_ctx = ctx
        return result

    def backward(self, y, *args):
        """
        Run backward using the tape from the last forward call.

        If no forward was called yet, runs forward with a dummy to build
        the tape structure, then inverts. For functions whose tape depends
        on the auxiliary args (like key), we re-run forward with the args
        to build the correct tape, then invert.
        """
        if self._last_ctx is None:
            # Need to build tape: run forward with unknown input
            ctx = InvertibleContext(width=self.width)
            dummy = RayonInt.unknown(self.width)
            self.fn(ctx, dummy, *args)
            self._last_ctx = ctx

        if isinstance(y, int):
            y = RayonInt.known(y, self.width)
        return self._last_ctx.replay_backward(y)

    @property
    def tape(self):
        if self._last_ctx:
            return self._last_ctx.tape
        return []

    @property
    def total_tension_cost(self):
        if self._last_ctx:
            return sum(e.tension_cost for e in self._last_ctx.tape)
        return 0

    def __call__(self, *args, **kwargs):
        """Default: forward execution."""
        return self.forward(*args, **kwargs)


def invertible(fn=None, width=8):
    """
    Decorator: makes a function auto-invertible.

    The decorated function receives (ctx, x, *args) where ctx provides
    ctx.xor(), ctx.add(), ctx.rotl(), etc. for tracked operations.

    Usage:
        @invertible
        def encrypt(ctx, x, key):
            x = ctx.xor(x, key)
            x = ctx.add(x, 0x42)
            x = ctx.rotl(x, 3)
            return x

        encrypted = encrypt.forward(plaintext, key)
        decrypted = encrypt.backward(encrypted, key)
    """
    def decorator(f):
        return InvertibleFunction(f, width=width)

    if fn is not None:
        # @invertible without parens
        return InvertibleFunction(fn, width=8)
    else:
        # @invertible(width=16)
        return decorator


# ════════════════════════════════════════════════════════════
# VERIFICATION
# ════════════════════════════════════════════════════════════

def verify():
    print("=" * 65)
    print("  AUTO-INVERT: Write forward, run backward automatically")
    print("=" * 65)
    print()

    WIDTH = 8
    MASK = 0xFF

    # ── Test 1: XOR + ADD + ROTR chain ──
    print("TEST 1: XOR + ADD + ROTR chain — forward then backward")
    print("-" * 55)

    prog = InvertibleProgram(width=WIDTH)
    prog.xor(0xAA)
    prog.add(0x42)
    prog.rotate_right(3)

    original = RayonInt.known(0x37, WIDTH)
    encrypted = prog.forward(original)
    recovered = prog.backward(encrypted)

    print(f"  Original:  0x{original.value:02X} ({original.value})")
    print(f"  Encrypted: 0x{encrypted.value:02X} ({encrypted.value})")
    print(f"  Recovered: 0x{recovered.value:02X} ({recovered.value})")
    print(f"  Tension cost: {prog.total_tension_cost}")
    ok1 = recovered.value == original.value
    print(f"  Round-trip: {'PASS' if ok1 else 'FAIL'}")
    assert ok1, f"Expected {original.value}, got {recovered.value}"
    print()

    # ── Test 2: @invertible encrypt/decrypt ──
    print("TEST 2: @invertible encrypt/decrypt round-trip")
    print("-" * 55)

    @invertible
    def encrypt(ctx, x, key):
        x = ctx.xor(x, key)
        x = ctx.add(x, 0x42)
        x = ctx.rotl(x, 3)
        return x

    key = RayonInt.known(0xDE, WIDTH)
    plaintext = RayonInt.known(0x55, WIDTH)

    ciphertext = encrypt.forward(plaintext, key)
    decrypted = encrypt.backward(ciphertext, key)

    print(f"  Key:        0x{key.value:02X}")
    print(f"  Plaintext:  0x{plaintext.value:02X}")
    print(f"  Ciphertext: 0x{ciphertext.value:02X}")
    print(f"  Decrypted:  0x{decrypted.value:02X}")
    print(f"  Tape length: {len(encrypt.tape)} operations")
    print(f"  Tension cost: {encrypt.total_tension_cost}")
    ok2 = decrypted.value == plaintext.value
    print(f"  Round-trip: {'PASS' if ok2 else 'FAIL'}")
    assert ok2, f"Expected {plaintext.value}, got {decrypted.value}"
    print()

    # ── Test 3: Partial inversion with AND ──
    print("TEST 3: Partial inversion with AND — some bits recovered")
    print("-" * 55)

    prog2 = InvertibleProgram(width=WIDTH)
    prog2.xor(0x55)            # invertible
    prog2.bit_and(0b11110000)  # kills low 4 bits!
    prog2.add(0x01)            # invertible

    original2 = RayonInt.known(0xAB, WIDTH)
    result2 = prog2.forward(original2)
    recovered2 = prog2.backward(result2)

    print(f"  Original: 0x{original2.value:02X} = {bin(original2.value)}")
    print(f"  After XOR(0x55) + AND(0xF0) + ADD(0x01): 0x{result2.value:02X}")
    print(f"  Backward result: {recovered2}")
    print(f"  Tension cost: {prog2.total_tension_cost} bits lost")

    # Check which bits were recovered
    recovered_bits = []
    unknown_bits = []
    for i in range(WIDTH):
        if recovered2.bits[i] is None:
            unknown_bits.append(i)
        else:
            recovered_bits.append(i)

    print(f"  Recovered bit positions: {recovered_bits}")
    print(f"  Unknown (?) bit positions: {unknown_bits}")
    ok3 = len(unknown_bits) == 4  # AND(0xF0) kills 4 low bits
    print(f"  Partial inversion (4 bits lost): {'PASS' if ok3 else 'FAIL'}")

    # Verify recovered bits match original
    bits_match = True
    for i in recovered_bits:
        if recovered2.bits[i] != original2.bits[i]:
            bits_match = False
    print(f"  Recovered bits match original: {'PASS' if bits_match else 'FAIL'}")
    assert ok3, f"Expected 4 unknown bits, got {len(unknown_bits)}"
    assert bits_match, "Recovered bits don't match original"
    print()

    # ── Test 4: Non-invertible operation detected ──
    print("TEST 4: Non-invertible operation — tension increases")
    print("-" * 55)

    prog3 = InvertibleProgram(width=WIDTH)
    prog3.bit_and(0b10101010)  # kills 4 bits
    prog3.bit_and(0b11001100)  # kills 4 more (some overlap)

    original3 = RayonInt.known(0xFF, WIDTH)
    result3 = prog3.forward(original3)
    recovered3 = prog3.backward(result3)

    total_tension = prog3.total_tension_cost
    actual_tension = recovered3.tension

    print(f"  Original: 0x{original3.value:02X} = {bin(original3.value)}")
    print(f"  After AND(0xAA) AND(0xCC): 0x{result3.value:02X} = {bin(result3.value)}")
    print(f"  Backward: {recovered3}")
    print(f"  Tape tension cost: {total_tension} bits")
    print(f"  Actual tension in result: {actual_tension} ? bits")
    print(f"  Non-invertible detected: {'PASS' if total_tension > 0 else 'FAIL'}")
    print(f"  Tension increased: {'PASS' if actual_tension > 0 else 'FAIL'}")
    assert total_tension > 0, "Should detect non-invertible ops"
    assert actual_tension > 0, "Should have tension in result"
    print()

    # ── Test 5: Multiple keys / complex chain ──
    print("TEST 5: Complex multi-key encrypt/decrypt")
    print("-" * 55)

    @invertible
    def complex_encrypt(ctx, x, k1, k2):
        x = ctx.xor(x, k1)
        x = ctx.rotl(x, 2)
        x = ctx.add(x, k2)
        x = ctx.rotl(x, 5)
        x = ctx.xor(x, k1)
        x = ctx.sub(x, k2)
        x = ctx.bit_not(x)
        return x

    k1 = RayonInt.known(0x3C, WIDTH)
    k2 = RayonInt.known(0x7E, WIDTH)

    for pt_val in [0x00, 0x55, 0xAA, 0xFF, 0x42]:
        pt = RayonInt.known(pt_val, WIDTH)
        ct = complex_encrypt.forward(pt, k1, k2)
        dt = complex_encrypt.backward(ct, k1, k2)
        ok = dt.value == pt.value
        print(f"  0x{pt_val:02X} -> 0x{ct.value:02X} -> 0x{dt.value:02X}  {'PASS' if ok else 'FAIL'}")
        assert ok, f"Round-trip failed for 0x{pt_val:02X}"

    print(f"  Tape: {len(complex_encrypt.tape)} ops, tension cost: {complex_encrypt.total_tension_cost}")
    print()

    # ── Summary ──
    print("=" * 65)
    print("  AUTO-INVERT: All tests passed")
    print()
    print("  - XOR + ADD + ROTR chain: forward/backward recovers original")
    print("  - @invertible encrypt/decrypt: automatic round-trip")
    print("  - Partial inversion with AND: ? marks lost bits exactly")
    print("  - Non-invertible ops: detected, tension increased")
    print("  - Complex multi-key chains: all round-trips verified")
    print()
    print("  KEY INSIGHT: Every operation records its inverse on a tape.")
    print("  Backward = replay tape reversed. Information loss = tension.")
    print("  AND/OR destroy bits -> ? bits in backward pass.")
    print("  XOR/ADD/ROT/NOT are perfectly invertible (tension cost = 0).")
    print("=" * 65)


if __name__ == '__main__':
    verify()
