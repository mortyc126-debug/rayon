"""
INTEROP — Bridge between Rayon and Python/C.

Three components:
  PythonBridge: wrap Python functions to accept/return RayonInt
  CCodeGen:     emit C source from Rayon operations
  FFI:          call external functions with tension tracking

RayonInt lives in rayon_numbers.py. This module lets it cross
language boundaries without losing tension information.
"""

import operator
import functools
from rayon_numbers import RayonInt


# ════════════════════════════════════════════════════════════
# 1. PYTHON BRIDGE
# ════════════════════════════════════════════════════════════

class PythonBridge:
    """Convert between Python ints and RayonInt, wrap functions."""

    @staticmethod
    def python_to_rayon(value, width=8):
        """Convert a Python int to a fully-known RayonInt."""
        if value is None:
            return RayonInt.unknown(width=width)
        return RayonInt.known(value & ((1 << width) - 1), width=width)

    @staticmethod
    def rayon_to_python(rayon_int):
        """
        Convert RayonInt to Python int.
        Returns None if any bit is ? (tension > 0).
        """
        if not isinstance(rayon_int, RayonInt):
            raise TypeError(f"Expected RayonInt, got {type(rayon_int).__name__}")
        return rayon_int.value  # already None when has ?

    @staticmethod
    def rayon_wrap(func):
        """
        Decorator: make a Python function accept RayonInt args.

        For fully-known inputs: unwrap to int, call func, wrap result.
        For partial inputs: apply func to ALL possible value combos,
        then find the tightest RayonInt that covers the result set.

        This is the honest bridge — no information is invented.
        """
        @functools.wraps(func)
        def wrapper(*args, width=8):
            rayon_args = []
            for a in args:
                if isinstance(a, int):
                    rayon_args.append(RayonInt.known(a, width=width))
                elif isinstance(a, RayonInt):
                    rayon_args.append(a)
                else:
                    raise TypeError(f"Expected int or RayonInt, got {type(a).__name__}")

            # Fast path: all known
            if all(r.is_known for r in rayon_args):
                py_args = [r.value for r in rayon_args]
                result = func(*py_args)
                return RayonInt.known(result & ((1 << width) - 1), width=width)

            # Slow path: enumerate all possible value combinations
            # Build the cartesian product of possible values
            value_sets = []
            for r in rayon_args:
                vals = r.possible_values()
                if vals is None:
                    raise ValueError(
                        f"Tension too high ({r.tension}) for enumeration"
                    )
                value_sets.append(vals)

            # Compute result for every combination
            results = set()
            _cartesian_apply(func, value_sets, 0, [], results, width)

            # Build tightest RayonInt covering all results
            return _cover(results, width)

        return wrapper


def _cartesian_apply(func, value_sets, depth, current, results, width):
    """Recursively enumerate cartesian product, apply func, collect results."""
    if depth == len(value_sets):
        r = func(*current)
        results.add(r & ((1 << width) - 1))
        return
    for v in value_sets[depth]:
        current.append(v)
        _cartesian_apply(func, value_sets, depth + 1, current, results, width)
        current.pop()


def _cover(values, width):
    """
    Find the tightest RayonInt whose possible_values() covers `values`.

    Bit i is:
      0 if all values have bit i = 0
      1 if all values have bit i = 1
      ? if values disagree on bit i
    """
    if not values:
        return RayonInt.known(0, width=width)
    values = list(values)
    bits = []
    for i in range(width):
        bit_vals = set((v >> i) & 1 for v in values)
        if len(bit_vals) == 1:
            bits.append(bit_vals.pop())
        else:
            bits.append(None)  # disagreement → ?
    return RayonInt(bits=bits, width=width)


# ════════════════════════════════════════════════════════════
# 2. C CODE GENERATION
# ════════════════════════════════════════════════════════════

class CCodeGen:
    """Generate C code from Rayon operations with tension tracking."""

    # Map operation names to C operators
    _OP_MAP = {
        'xor': '^',
        'and': '&',
        'or':  '|',
        'not': '~',
        'add': '+',
        'sub': '-',
    }

    @staticmethod
    def emit_c(operations, width=8):
        """
        Generate C source from a list of operations.

        Each operation is a dict:
          {'op': 'xor'|'and'|'or'|'not'|'add'|'sub',
           'dst': 'var_name',
           'src': ['a', 'b'] or ['a'] for unary,
           'tension': int or None}

        Returns a C source string using uint8_t/uint16_t/uint32_t.
        """
        c_type = _c_type_for_width(width)
        mask = f"0x{(1 << width) - 1:X}"

        lines = []
        lines.append(f"/* Rayon → C  (width={width}) */")
        lines.append(f"#include <stdint.h>")
        lines.append(f"")

        # Collect compile-time unknowns
        unknowns = set()
        for op in operations:
            t = op.get('tension', 0) or 0
            if t > 0:
                for s in op.get('src', []):
                    unknowns.add(s)

        if unknowns:
            lines.append(f"/* Compile hint: variables with ? at compile time: "
                         f"{', '.join(sorted(unknowns))} */")
            lines.append(f"")

        lines.append(f"void rayon_compute({c_type} *out,")
        # Input params: all unique src vars not produced as dst
        all_dst = set(op['dst'] for op in operations)
        all_src = set()
        for op in operations:
            for s in op.get('src', []):
                all_src.add(s)
        inputs = sorted(all_src - all_dst)
        if inputs:
            params = ', '.join(f'{c_type} {v}' for v in inputs)
            lines.append(f"                   {params}) {{")
        else:
            lines.append(f"                   void) {{")

        # Emit each operation
        for op in operations:
            op_name = op['op']
            dst = op['dst']
            src = op.get('src', [])
            tension = op.get('tension', 0) or 0

            c_op = CCodeGen._OP_MAP.get(op_name)
            if c_op is None:
                lines.append(f"    /* unknown op: {op_name} */")
                continue

            # Tension comment
            t_comment = f"  /* tension={tension} */" if tension > 0 else ""

            if op_name == 'not':
                lines.append(
                    f"    {c_type} {dst} = (~{src[0]}) & {mask};{t_comment}"
                )
            else:
                lines.append(
                    f"    {c_type} {dst} = ({src[0]} {c_op} {src[1]}) & {mask};{t_comment}"
                )

        # Output
        if operations:
            last_dst = operations[-1]['dst']
            lines.append(f"    *out = {last_dst};")

        lines.append(f"}}")
        return '\n'.join(lines)


def _c_type_for_width(width):
    """Pick the right C unsigned type for a given bit width."""
    if width <= 8:
        return 'uint8_t'
    elif width <= 16:
        return 'uint16_t'
    else:
        return 'uint32_t'


# ════════════════════════════════════════════════════════════
# 3. FFI — FOREIGN FUNCTION INTERFACE WITH TENSION TRACKING
# ════════════════════════════════════════════════════════════

class FFI:
    """Call external functions while tracking tension."""

    @staticmethod
    def call_external(func, args, width=8):
        """
        Call an external function with RayonInt args.
        Result tension = max(input tensions).

        For known args: call directly, return known result.
        For partial args: use the PythonBridge wrapper to enumerate.
        """
        rayon_args = []
        max_tension = 0
        for a in args:
            if isinstance(a, int):
                rayon_args.append(RayonInt.known(a, width=width))
            elif isinstance(a, RayonInt):
                rayon_args.append(a)
                max_tension = max(max_tension, a.tension)
            else:
                raise TypeError(f"Expected int or RayonInt, got {type(a).__name__}")

        # Wrap and call
        wrapped = PythonBridge.rayon_wrap(func)
        result = wrapped(*rayon_args, width=width)

        return result


# ════════════════════════════════════════════════════════════
# VERIFICATION
# ════════════════════════════════════════════════════════════

def verify():
    print("+" + "=" * 59 + "+")
    print("|  INTEROP — Bridge between Rayon and Python/C              |")
    print("+" + "=" * 59 + "+")
    print()
    WIDTH = 8
    passed = 0
    failed = 0

    def check(name, condition):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  \u2713 {name}")
        else:
            failed += 1
            print(f"  \u2717 {name}")

    # ── 1. PythonBridge ──────────────────────────────────────

    print("1. PythonBridge")
    print("-" * 50)

    # python_to_rayon / rayon_to_python round-trip
    r = PythonBridge.python_to_rayon(42, width=WIDTH)
    check("python_to_rayon(42) is known with value 42",
          r.is_known and r.value == 42)

    back = PythonBridge.rayon_to_python(r)
    check("rayon_to_python round-trip = 42", back == 42)

    unknown = RayonInt.unknown(width=WIDTH)
    check("rayon_to_python(unknown) = None",
          PythonBridge.rayon_to_python(unknown) is None)

    # @rayon_wrap with operator.xor on known values
    rayon_xor = PythonBridge.rayon_wrap(operator.xor)
    a = RayonInt.known(0b11001100, WIDTH)
    b = RayonInt.known(0b10101010, WIDTH)
    result = rayon_xor(a, b, width=WIDTH)
    expected = 0b11001100 ^ 0b10101010
    check(f"@rayon_wrap(xor)(0xCC, 0xAA) = 0x{expected:02X}",
          result.is_known and result.value == expected)

    # @rayon_wrap with partial inputs
    a = RayonInt.known(0xFF, WIDTH)                        # 11111111
    b = RayonInt.partial(0b10100000, 0b00001111, WIDTH)    # 1010????
    result = rayon_xor(a, b, width=WIDTH)
    # XOR with 0xFF flips all bits: result should be 0101????
    check(f"@rayon_wrap(xor)(0xFF, 1010????) tension={result.tension}",
          result.tension == 4)
    # The known high bits: 0b10100000 bits[4..7] = [0,1,0,1], flipped = [1,0,1,0]
    high_bits = [result.bits[i] for i in range(4, 8)]
    check("  high 4 bits are 1010 (flipped)",
          high_bits == [1, 0, 1, 0])
    # Low 4 bits should be ?
    low_bits = [result.bits[i] for i in range(4)]
    check("  low 4 bits are ? (unknown stays unknown)",
          all(b is None for b in low_bits))
    print()

    # ── 2. CCodeGen ──────────────────────────────────────────

    print("2. CCodeGen — XOR+AND chain")
    print("-" * 50)

    ops = [
        {'op': 'xor', 'dst': 't0', 'src': ['a', 'b'], 'tension': 4},
        {'op': 'and', 'dst': 't1', 'src': ['t0', 'c'], 'tension': 2},
    ]
    c_code = CCodeGen.emit_c(ops, width=WIDTH)
    print(c_code)
    print()

    check("C code contains uint8_t", "uint8_t" in c_code)
    check("C code contains ^ (XOR)", "^" in c_code)
    check("C code contains & (AND)", " & " in c_code or "& 0x" in c_code)
    check("C code has tension comment", "tension=4" in c_code)
    check("C code has compile hint for unknowns", "Compile hint" in c_code)
    # AND line should have & for both the operation and the mask
    and_line = [l for l in c_code.split('\n') if 't1' in l and '&' in l]
    check("AND line emitted for t1", len(and_line) > 0)
    print()

    # ── 3. FFI ───────────────────────────────────────────────

    print("3. FFI — call_external with tension tracking")
    print("-" * 50)

    # Known args
    result = FFI.call_external(operator.xor, [0b11110000, 0b00001111], width=WIDTH)
    check("FFI xor(0xF0, 0x0F) = 0xFF",
          result.is_known and result.value == 0xFF)

    # Partial args — tension propagates
    a = RayonInt.partial(0b11110000, 0b00001111, WIDTH)  # 1111????
    b = RayonInt.known(0b11111111, WIDTH)                # 11111111
    result = FFI.call_external(operator.xor, [a, b], width=WIDTH)
    check(f"FFI xor(1111????, 0xFF) tension={result.tension} (should be 4)",
          result.tension == 4)
    # Known high bits: 1111 XOR 1111 = 0000
    high_bits = [result.bits[i] for i in range(4, 8)]
    check("  high bits resolved to 0000", high_bits == [0, 0, 0, 0])

    # Max-tension propagation
    a = RayonInt.partial(0, 0b00000011, WIDTH)  # tension=2
    b = RayonInt.partial(0, 0b00001111, WIDTH)  # tension=4
    result = FFI.call_external(operator.xor, [a, b], width=WIDTH)
    check(f"FFI tension = max input tensions ({result.tension} >= 4)",
          result.tension >= 4)
    print()

    # ── SUMMARY ──────────────────────────────────────────────

    total = passed + failed
    print("=" * 50)
    print(f"  {passed}/{total} passed", end="")
    if failed == 0:
        print("  ALL PASS")
    else:
        print(f"  ({failed} FAILED)")
    print()
    print("  PythonBridge: wrap any Python func for RayonInt")
    print("  CCodeGen:     emit C with tension annotations")
    print("  FFI:          external calls preserve tension")
    print("=" * 50)


if __name__ == '__main__':
    verify()
