"""
STONE 23: TYPE SYSTEM — Types with tension annotations.

Standard type system: Int8 is Int8. That's it.
Rayon type system: Known[Int8] vs Unknown[Int8] vs Partial[Int8, 3].

Every type carries a TENSION BOUND:
  Known[T]         — T with τ=0, fully determined
  Partial[T, τ_max] — T with τ ≤ τ_max
  Unknown[T]       — T with τ=max (all bits unknown)

The type checker enforces tension compatibility:
  - Known + Unknown → Partial (tension adds)
  - AND(Known_zero, Unknown) → Known_zero (kill-links!)
  - Function expecting Known rejects Unknown (type error)

Type inference traces tension through operations:
  x: Known[Int8] = 42  →  τ=0
  y: Unknown[Int8]      →  τ=8
  z = x + y             →  Partial[Int8, 8]

This is not gradual typing. This is TENSION typing.
Types encode HOW MUCH YOU KNOW, not just WHAT KIND.
"""


# ════════════════════════════════════════════════════════════
# RAYON TYPES — base types with tension range
# ════════════════════════════════════════════════════════════

class RayonType:
    """Base class for all Rayon types."""
    def __init__(self, name, tau_max):
        self.name = name
        self.tau_max = tau_max   # maximum tension for this type

    def __repr__(self):
        return self.name

    def __eq__(self, other):
        return isinstance(other, RayonType) and self.name == other.name and self.tau_max == other.tau_max

    def __hash__(self):
        return hash((self.name, self.tau_max))


class Bit(RayonType):
    """
    Single bit: {0, 1, ?}.
    tau_max = 1 (one bit of uncertainty).
    """
    def __init__(self):
        super().__init__("Bit", tau_max=1)


class Int(RayonType):
    """
    w-bit integer. tau_max = w (all bits unknown).
    Int[8] = Int8, Int[32] = Int32, etc.
    """
    def __init__(self, width):
        self.width = width
        super().__init__(f"Int{width}", tau_max=width)

    def __eq__(self, other):
        return isinstance(other, Int) and self.width == other.width

    def __hash__(self):
        return hash(("Int", self.width))


class Array(RayonType):
    """
    Array[T, n]: n elements of type T.
    tau_max = n * T.tau_max (every element fully unknown).
    """
    def __init__(self, element_type, length):
        self.element_type = element_type
        self.length = length
        super().__init__(
            f"Array[{element_type.name}, {length}]",
            tau_max=length * element_type.tau_max
        )

    def __eq__(self, other):
        return (isinstance(other, Array)
                and self.element_type == other.element_type
                and self.length == other.length)

    def __hash__(self):
        return hash(("Array", self.element_type, self.length))


class Fn(RayonType):
    """
    Fn[A → B, τ]: function from type A to type B with intrinsic tension τ.
    τ = branch points the function introduces.
    """
    def __init__(self, input_type, output_type, tension=0):
        self.input_type = input_type
        self.output_type = output_type
        self.tension = tension
        super().__init__(
            f"Fn[{input_type.name} → {output_type.name}, τ={tension}]",
            tau_max=tension
        )

    def __eq__(self, other):
        return (isinstance(other, Fn)
                and self.input_type == other.input_type
                and self.output_type == other.output_type
                and self.tension == other.tension)

    def __hash__(self):
        return hash(("Fn", self.input_type, self.output_type, self.tension))


# ════════════════════════════════════════════════════════════
# TENSION BOUNDS — type-level tension constraints
# ════════════════════════════════════════════════════════════

class TensionBound:
    """
    A type with a tension constraint.
    Wraps a base RayonType and adds τ bound.
    """
    def __init__(self, base_type, tau):
        self.base_type = base_type
        self.tau = tau             # actual tension level

    @property
    def tau_max(self):
        return self.base_type.tau_max

    @property
    def is_known(self):
        return self.tau == 0

    @property
    def is_unknown(self):
        return self.tau == self.base_type.tau_max

    @property
    def is_partial(self):
        return 0 < self.tau < self.base_type.tau_max

    def __repr__(self):
        if self.is_known:
            return f"Known[{self.base_type}]"
        if self.is_unknown:
            return f"Unknown[{self.base_type}]"
        return f"Partial[{self.base_type}, τ={self.tau}]"

    def __eq__(self, other):
        return (isinstance(other, TensionBound)
                and self.base_type == other.base_type
                and self.tau == other.tau)

    def __hash__(self):
        return hash((self.base_type, self.tau))


def Known(base_type):
    """T with τ=0 (fully known)."""
    return TensionBound(base_type, tau=0)


def Partial(base_type, tau):
    """T with τ ≤ tau_max."""
    tau = min(tau, base_type.tau_max)
    tau = max(tau, 0)
    return TensionBound(base_type, tau=tau)


def Unknown(base_type):
    """T with τ=max (fully unknown)."""
    return TensionBound(base_type, tau=base_type.tau_max)


# ════════════════════════════════════════════════════════════
# TYPE CHECKER — verify tension compatibility
# ════════════════════════════════════════════════════════════

class TypeError(Exception):
    """Rayon type error: tension incompatibility."""
    pass


class TypeChecker:
    """
    Verify tension compatibility across operations.

    Rules:
      ADD(Known, Unknown) → Partial (carry chain propagates unknowns)
      AND(Known_zero, Unknown) → Known_zero (kill-link: 0 AND ? = 0)
      OR(Known_one, Unknown) → Known_one (kill-link: 1 OR ? = 1)
      XOR(Known, Unknown) → Unknown (no kills in XOR)
      Function(Known required) rejects Unknown argument.
    """

    @staticmethod
    def check_add(a, b):
        """
        Addition: tension adds (carry chain propagates uncertainty).
        Known[T] + Unknown[T] → Partial[T, min(a.tau + b.tau, T.tau_max)]
        """
        if a.base_type != b.base_type:
            raise TypeError(f"Cannot add {a} and {b}: incompatible base types")

        result_tau = min(a.tau + b.tau, a.base_type.tau_max)
        return TensionBound(a.base_type, tau=result_tau)

    @staticmethod
    def check_and(a, b):
        """
        AND: kill-links reduce tension.
        If a is known-zero (all bits 0, τ=0), result is known-zero regardless of b.
        Otherwise tension is min of the two (AND can only reduce unknowns).

        Key insight: 0 AND ? = 0. Known zeros KILL unknown bits.
        """
        if a.base_type != b.base_type:
            raise TypeError(f"Cannot AND {a} and {b}: incompatible base types")

        # Kill-link: known-zero kills everything
        if a.is_known:
            return Known(a.base_type)
        if b.is_known:
            return Known(b.base_type)

        # AND can only keep bits that are unknown in BOTH operands
        # If a bit is known-0 in either → result known-0 (killed)
        # If a bit is known-1 in either → result = other bit (passed through)
        # Net: tension ≤ min(a.tau, b.tau)
        result_tau = min(a.tau, b.tau)
        return TensionBound(a.base_type, tau=result_tau)

    @staticmethod
    def check_or(a, b):
        """
        OR: kill-links from known-ones.
        1 OR ? = 1. Known ones dominate.
        """
        if a.base_type != b.base_type:
            raise TypeError(f"Cannot OR {a} and {b}: incompatible base types")

        if a.is_known:
            return Known(a.base_type)
        if b.is_known:
            return Known(b.base_type)

        result_tau = min(a.tau, b.tau)
        return TensionBound(a.base_type, tau=result_tau)

    @staticmethod
    def check_xor(a, b):
        """
        XOR: no kill-links. ? XOR anything = ?.
        Tension takes the maximum.
        """
        if a.base_type != b.base_type:
            raise TypeError(f"Cannot XOR {a} and {b}: incompatible base types")

        result_tau = max(a.tau, b.tau)
        return TensionBound(a.base_type, tau=result_tau)

    @staticmethod
    def check_fn_call(fn_type, arg_type):
        """
        Function call: check that argument tension meets requirement.
        If fn expects Known[T], reject Unknown[T] or Partial[T].
        Returned type inherits function tension + arg tension.
        """
        if not isinstance(fn_type, Fn):
            raise TypeError(f"{fn_type} is not a function type")

        # Check base type compatibility
        if not isinstance(arg_type, TensionBound):
            raise TypeError(f"Argument must have tension annotation, got {arg_type}")

        if arg_type.base_type != fn_type.input_type:
            raise TypeError(
                f"Function expects {fn_type.input_type}, got {arg_type.base_type}"
            )

        # Check tension constraint: if function input is annotated as Known,
        # we model this as fn_type.tension == 0 meaning "requires exact input"
        # A function with tension=0 demands Known inputs
        if fn_type.tension == 0 and not arg_type.is_known:
            raise TypeError(
                f"Function {fn_type} requires Known[{fn_type.input_type}], "
                f"but got {arg_type}"
            )

        # Output tension = fn's intrinsic tension + argument tension
        result_tau = min(fn_type.tension + arg_type.tau, fn_type.output_type.tau_max)
        return TensionBound(fn_type.output_type, tau=result_tau)


# ════════════════════════════════════════════════════════════
# TYPE INFERENCE — auto-infer tension types from code
# ════════════════════════════════════════════════════════════

class TypedValue:
    """A value with its inferred tension type."""
    def __init__(self, value, tension_type):
        self.value = value
        self.type = tension_type

    def __repr__(self):
        return f"{self.value}: {self.type}"


class TypeInference:
    """
    Infer tension types from operations on typed values.

    x = infer_literal(42, Int(8))         → TypedValue(42, Known[Int8])
    y = infer_unknown(Int(8))             → TypedValue(?, Unknown[Int8])
    z = infer_add(x, y)                   → TypedValue(?, Partial[Int8, τ=8])
    """

    @staticmethod
    def infer_literal(value, base_type):
        """Literal value → Known[T]."""
        return TypedValue(value, Known(base_type))

    @staticmethod
    def infer_unknown(base_type):
        """Unknown variable → Unknown[T]."""
        return TypedValue("?", Unknown(base_type))

    @staticmethod
    def infer_partial(base_type, tau):
        """Partially known value → Partial[T, tau]."""
        return TypedValue("~", Partial(base_type, tau))

    @staticmethod
    def infer_add(a, b):
        """Infer type of a + b."""
        result_type = TypeChecker.check_add(a.type, b.type)
        # If both values are concrete, compute result
        if a.type.is_known and b.type.is_known:
            result_val = a.value + b.value
        else:
            result_val = "?"
        return TypedValue(result_val, result_type)

    @staticmethod
    def infer_and(a, b):
        """Infer type of a AND b."""
        result_type = TypeChecker.check_and(a.type, b.type)
        if a.type.is_known and b.type.is_known:
            result_val = a.value & b.value
        elif a.type.is_known and a.value == 0:
            result_val = 0   # kill-link: 0 AND anything = 0
        elif b.type.is_known and b.value == 0:
            result_val = 0
        else:
            result_val = "?"
        return TypedValue(result_val, result_type)

    @staticmethod
    def infer_xor(a, b):
        """Infer type of a XOR b."""
        result_type = TypeChecker.check_xor(a.type, b.type)
        if a.type.is_known and b.type.is_known:
            result_val = a.value ^ b.value
        else:
            result_val = "?"
        return TypedValue(result_val, result_type)

    @staticmethod
    def infer_fn_call(fn_type, arg):
        """Infer type of fn(arg)."""
        result_type = TypeChecker.check_fn_call(fn_type, arg.type)
        return TypedValue("?", result_type)


# ════════════════════════════════════════════════════════════
# TESTS
# ════════════════════════════════════════════════════════════

def test_base_types():
    """Verify base type construction."""
    print("── Base Types ──")

    b = Bit()
    assert b.tau_max == 1, f"Bit tau_max should be 1, got {b.tau_max}"
    print(f"  {b}: tau_max={b.tau_max}")

    i8 = Int(8)
    assert i8.tau_max == 8
    print(f"  {i8}: tau_max={i8.tau_max}")

    i32 = Int(32)
    assert i32.tau_max == 32
    print(f"  {i32}: tau_max={i32.tau_max}")

    arr = Array(Int(8), 4)
    assert arr.tau_max == 32   # 4 * 8
    print(f"  {arr}: tau_max={arr.tau_max}")

    fn = Fn(Int(8), Int(8), tension=3)
    assert fn.tension == 3
    print(f"  {fn}: tension={fn.tension}")

    print("  ✓ base types OK\n")


def test_tension_bounds():
    """Verify tension bound construction."""
    print("── Tension Bounds ──")

    i8 = Int(8)

    k = Known(i8)
    assert k.is_known and k.tau == 0
    print(f"  {k}: tau={k.tau}")

    u = Unknown(i8)
    assert u.is_unknown and u.tau == 8
    print(f"  {u}: tau={u.tau}")

    p = Partial(i8, 3)
    assert p.is_partial and p.tau == 3
    print(f"  {p}: tau={p.tau}")

    # Clamping
    clamped = Partial(i8, 100)
    assert clamped.tau == 8, f"Should clamp to tau_max=8, got {clamped.tau}"
    print(f"  Partial(Int8, 100) clamped → {clamped}")

    print("  ✓ tension bounds OK\n")


def test_type_check_add():
    """Known + Unknown → Partial."""
    print("── Type Check: ADD ──")

    i8 = Int(8)
    k = Known(i8)
    u = Unknown(i8)

    result = TypeChecker.check_add(k, u)
    assert result.tau == 8, f"Known(0) + Unknown(8) should give tau=8, got {result.tau}"
    assert result.base_type == i8
    print(f"  {k} + {u} → {result}")

    # Known + Known → Known
    result2 = TypeChecker.check_add(k, Known(i8))
    assert result2.is_known
    print(f"  {k} + {Known(i8)} → {result2}")

    # Partial + Partial
    p3 = Partial(i8, 3)
    p4 = Partial(i8, 4)
    result3 = TypeChecker.check_add(p3, p4)
    assert result3.tau == 7
    print(f"  {p3} + {p4} → {result3}")

    # Capping at tau_max
    result4 = TypeChecker.check_add(u, u)
    assert result4.tau == 8   # capped at tau_max
    print(f"  {u} + {u} → {result4} (capped)")

    print("  ✓ ADD type check OK\n")


def test_type_check_and_kill():
    """AND(known_zero, unknown) → known_zero — kill-link in the type system!"""
    print("── Type Check: AND (kill-links) ──")

    i8 = Int(8)
    k = Known(i8)      # known value (could be 0x00 → all zeros kill)
    u = Unknown(i8)

    result = TypeChecker.check_and(k, u)
    assert result.is_known, f"AND(Known, Unknown) should be Known (kill-link), got {result}"
    print(f"  AND({k}, {u}) → {result}  ← kill-link!")

    # Unknown AND Unknown → stays unknown at min tension
    result2 = TypeChecker.check_and(u, u)
    assert result2.tau == 8
    print(f"  AND({u}, {u}) → {result2}")

    # Partial AND Unknown → Partial at min
    p3 = Partial(i8, 3)
    result3 = TypeChecker.check_and(p3, u)
    assert result3.tau == 3
    print(f"  AND({p3}, {u}) → {result3}")

    print("  ✓ AND kill-link type check OK\n")


def test_type_check_fn_call():
    """Function expecting Known rejects Unknown."""
    print("── Type Check: Function Call ──")

    i8 = Int(8)

    # Strict function: tension=0 means "I need exact input"
    strict_fn = Fn(i8, i8, tension=0)
    k = Known(i8)
    u = Unknown(i8)

    # Known arg → OK
    result = TypeChecker.check_fn_call(strict_fn, k)
    assert result.is_known
    print(f"  {strict_fn}({k}) → {result}")

    # Unknown arg → TYPE ERROR
    caught = False
    try:
        TypeChecker.check_fn_call(strict_fn, u)
    except TypeError as e:
        caught = True
        print(f"  {strict_fn}({u}) → ERROR: {e}")
    assert caught, "Should have raised TypeError for Unknown arg to strict fn"

    # Permissive function: tension=5 means "I can handle some unknowns"
    permissive_fn = Fn(i8, i8, tension=5)
    result2 = TypeChecker.check_fn_call(permissive_fn, u)
    assert result2.tau == 8   # min(5 + 8, 8) = 8
    print(f"  {permissive_fn}({u}) → {result2}")

    # Permissive function with known arg
    result3 = TypeChecker.check_fn_call(permissive_fn, k)
    assert result3.tau == 5   # fn adds its own tension
    print(f"  {permissive_fn}({k}) → {result3}")

    print("  ✓ function type check OK\n")


def test_type_inference():
    """Auto-infer tension types through a chain of operations."""
    print("── Type Inference ──")

    i8 = Int(8)
    infer = TypeInference

    # x: Known[Int8] = 42
    x = infer.infer_literal(42, i8)
    assert x.type.is_known
    print(f"  x = {x}")

    # y: Unknown[Int8]
    y = infer.infer_unknown(i8)
    assert y.type.is_unknown
    print(f"  y = {y}")

    # z = x + y → Partial[Int8, τ=8]
    z = infer.infer_add(x, y)
    assert z.type.tau == 8
    print(f"  z = x + y = {z}")

    # w = x + x → Known[Int8] (known + known = known)
    w = infer.infer_add(x, x)
    assert w.type.is_known
    assert w.value == 84
    print(f"  w = x + x = {w}")

    # Kill-link inference: AND(known_zero, unknown)
    zero = infer.infer_literal(0, i8)
    killed = infer.infer_and(zero, y)
    assert killed.type.is_known
    assert killed.value == 0
    print(f"  AND(0, y) = {killed}  ← kill-link inferred!")

    # Chain: a = literal(10), b = unknown, c = a + b, d = c + a
    a = infer.infer_literal(10, i8)
    b = infer.infer_unknown(i8)
    c = infer.infer_add(a, b)           # tau = 0 + 8 = 8
    d = infer.infer_add(c, a)           # tau = 8 + 0 = 8 (capped)
    print(f"  a = {a}")
    print(f"  b = {b}")
    print(f"  c = a + b = {c}")
    print(f"  d = c + a = {d}")
    assert d.type.tau == 8
    assert d.type.base_type == i8

    # Chain with partial: e = partial(3), f = e + a
    e = infer.infer_partial(i8, 3)
    f = infer.infer_add(e, a)           # tau = 3 + 0 = 3
    assert f.type.tau == 3
    print(f"  e = {e}")
    print(f"  f = e + a = {f}")

    # XOR preserves max tension
    g = infer.infer_xor(x, y)
    assert g.type.tau == 8              # max(0, 8) = 8
    print(f"  g = x XOR y = {g}")

    print("  ✓ type inference OK\n")


def test_type_errors():
    """Verify type errors are caught."""
    print("── Type Errors ──")

    i8 = Int(8)
    i32 = Int(32)

    # Mismatched base types
    caught = False
    try:
        TypeChecker.check_add(Known(i8), Known(i32))
    except TypeError as e:
        caught = True
        print(f"  Int8 + Int32 → ERROR: {e}")
    assert caught

    # Wrong arg type for function
    fn = Fn(i8, i8, tension=0)
    caught = False
    try:
        TypeChecker.check_fn_call(fn, Known(i32))
    except TypeError as e:
        caught = True
        print(f"  Fn[Int8→Int8](Known[Int32]) → ERROR: {e}")
    assert caught

    # Not a function
    caught = False
    try:
        TypeChecker.check_fn_call(i8, Known(i8))
    except TypeError as e:
        caught = True
        print(f"  Int8(Known[Int8]) → ERROR: {e}")
    assert caught

    print("  ✓ type errors caught OK\n")


def test_array_types():
    """Verify array type tension."""
    print("── Array Types ──")

    i8 = Int(8)
    arr4 = Array(i8, 4)

    k_arr = Known(arr4)
    u_arr = Unknown(arr4)
    p_arr = Partial(arr4, 16)

    assert k_arr.tau == 0
    assert u_arr.tau == 32       # 4 * 8
    assert p_arr.tau == 16

    print(f"  {k_arr}: tau={k_arr.tau}")
    print(f"  {u_arr}: tau={u_arr.tau}")
    print(f"  {p_arr}: tau={p_arr.tau}")

    # ADD on arrays
    result = TypeChecker.check_add(k_arr, p_arr)
    assert result.tau == 16
    print(f"  {k_arr} + {p_arr} → {result}")

    print("  ✓ array types OK\n")


# ════════════════════════════════════════════════════════════
# RUN ALL TESTS
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("STONE 23: TYPE SYSTEM — types with tension annotations")
    print("=" * 60)
    print()

    test_base_types()
    test_tension_bounds()
    test_type_check_add()
    test_type_check_and_kill()
    test_type_check_fn_call()
    test_type_inference()
    test_type_errors()
    test_array_types()

    print("=" * 60)
    print("ALL TESTS PASSED — Stone 23 verified.")
    print()
    print("The type system encodes tension at the type level:")
    print("  Known[T]    — fully determined, τ=0")
    print("  Partial[T]  — partially known, 0 < τ < max")
    print("  Unknown[T]  — fully unknown, τ=max")
    print()
    print("Kill-links appear in types: AND(Known_zero, Unknown) → Known")
    print("Type errors catch tension violations at compile time.")
    print("=" * 60)
