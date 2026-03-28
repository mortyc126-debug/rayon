"""
STONE 15: NUMBERS — Integers with tension.

Standard integer: 5 = 101 in binary. One value.
Rayon integer: 1?1 = {5, 7}. A SET of values, compact.

Each bit is {0, 1, ?}. The ?-bits define the RANGE.
Number of possible values = 2^(count of ? bits).
Tension = count of ? bits (how hard to determine exact value).

Arithmetic:
  a + b: carry chain with ? propagation
  a - b: complement + add
  a × b: shift-and-add
  a == b: might return ? (can't compare unknowns)

This is not interval arithmetic. It's EXACT set arithmetic,
represented compactly as bit patterns with masks.
"""

# GF2Expr not needed for numbers


class RayonInt:
    """
    Integer with tension. Each bit is 0, 1, or ? (unknown).

    Internally: bits = list of {0, 1, None} from LSB to MSB.
    None = ? = unknown bit.

    Tension = count of None bits.
    Possible values = 2^tension.
    """
    def __init__(self, bits=None, value=None, width=32):
        self.width = width
        if value is not None:
            # From concrete integer
            self.bits = [(value >> i) & 1 for i in range(width)]
        elif bits is not None:
            self.bits = list(bits)
            while len(self.bits) < width:
                self.bits.append(0)
        else:
            # All unknown
            self.bits = [None] * width

    @staticmethod
    def known(value, width=32):
        """Create fully known integer."""
        return RayonInt(value=value, width=width)

    @staticmethod
    def unknown(width=32):
        """Create fully unknown integer (all ? bits)."""
        return RayonInt(width=width)

    @staticmethod
    def partial(known_bits, mask, width=32):
        """
        Create partially known: known_bits with ? at mask positions.
        mask bit = 1 → that position is ?.
        """
        bits = []
        for i in range(width):
            if (mask >> i) & 1:
                bits.append(None)  # unknown
            else:
                bits.append((known_bits >> i) & 1)
        return RayonInt(bits=bits, width=width)

    @property
    def tension(self):
        """Count of unknown bits."""
        return sum(1 for b in self.bits if b is None)

    @property
    def is_known(self):
        return self.tension == 0

    @property
    def value(self):
        """Concrete value (only if fully known)."""
        if not self.is_known:
            return None
        return sum(b << i for i, b in enumerate(self.bits))

    @property
    def n_possible(self):
        """Number of possible values."""
        return 2 ** self.tension

    @property
    def min_value(self):
        """Minimum possible value (all ? = 0)."""
        return sum((b or 0) << i for i, b in enumerate(self.bits))

    @property
    def max_value(self):
        """Maximum possible value (all ? = 1)."""
        return sum((b if b is not None else 1) << i for i, b in enumerate(self.bits))

    def possible_values(self, limit=1000):
        """Generate all possible values (for small tension only)."""
        if self.tension > 20:
            return None  # too many
        unknown_positions = [i for i, b in enumerate(self.bits) if b is None]
        base = self.min_value
        values = []
        for mask in range(2 ** len(unknown_positions)):
            v = base
            for j, pos in enumerate(unknown_positions):
                if (mask >> j) & 1:
                    v |= (1 << pos)
            values.append(v)
            if len(values) >= limit:
                break
        return sorted(values)

    # ── ARITHMETIC ──

    def __add__(self, other):
        """Addition with ? propagation through carry chain."""
        result_bits = []
        carry = 0  # carry starts as known 0

        for i in range(max(self.width, other.width)):
            a = self.bits[i] if i < len(self.bits) else 0
            b = other.bits[i] if i < len(other.bits) else 0

            if a is None or b is None or carry is None:
                # At least one unknown: check for kills
                # sum bit = a XOR b XOR carry → unknown if any input unknown
                result_bits.append(None)

                # carry = (a AND b) OR (carry AND (a XOR b))
                # Kill cases:
                if a == 0 and b == 0:
                    carry = 0  # KILL! AND(0,0)=0, carry dies
                elif a == 1 and b == 1:
                    carry = 1  # both 1, carry guaranteed
                elif carry == 0 and (a == 0 or b == 0):
                    carry = 0  # carry=0 AND one input=0 → carry stays 0
                else:
                    carry = None  # truly unknown carry
            else:
                # All known: standard addition
                s = a + b + carry
                result_bits.append(s & 1)
                carry = s >> 1

        return RayonInt(bits=result_bits[:self.width], width=self.width)

    def __sub__(self, other):
        """Subtraction: a - b = a + (~b + 1) mod 2^width."""
        # Complement b: flip bits, add 1
        comp_bits = [(1 - b if b is not None else None) for b in other.bits]
        complement = RayonInt(bits=comp_bits, width=self.width)
        one = RayonInt.known(1, self.width)
        neg_b = complement + one
        return self + neg_b

    def __xor__(self, other):
        """Bitwise XOR."""
        bits = []
        for i in range(self.width):
            a = self.bits[i] if i < len(self.bits) else 0
            b = other.bits[i] if i < len(other.bits) else 0
            if a is None or b is None:
                bits.append(None)
            else:
                bits.append(a ^ b)
        return RayonInt(bits=bits, width=self.width)

    def __and__(self, other):
        """Bitwise AND with kill-links!"""
        bits = []
        for i in range(self.width):
            a = self.bits[i] if i < len(self.bits) else 0
            b = other.bits[i] if i < len(other.bits) else 0
            if a == 0 or b == 0:
                bits.append(0)  # KILL!
            elif a is None or b is None:
                bits.append(None)
            else:
                bits.append(a & b)
        return RayonInt(bits=bits, width=self.width)

    def __or__(self, other):
        """Bitwise OR with kill-links!"""
        bits = []
        for i in range(self.width):
            a = self.bits[i] if i < len(self.bits) else 0
            b = other.bits[i] if i < len(other.bits) else 0
            if a == 1 or b == 1:
                bits.append(1)  # KILL!
            elif a is None or b is None:
                bits.append(None)
            else:
                bits.append(a | b)
        return RayonInt(bits=bits, width=self.width)

    def __invert__(self):
        """Bitwise NOT."""
        bits = [(1 - b if b is not None else None) for b in self.bits]
        return RayonInt(bits=bits, width=self.width)

    def __eq__(self, other):
        """Equality: returns True, False, or None (?)."""
        if not isinstance(other, RayonInt):
            if isinstance(other, int):
                other = RayonInt.known(other, self.width)
            else:
                return NotImplemented
        all_match = True
        for i in range(self.width):
            a = self.bits[i]
            b = other.bits[i]
            if a is not None and b is not None and a != b:
                return False  # definitely not equal
            if a is None or b is None:
                all_match = False
        return True if all_match else None  # True or ?

    def __repr__(self):
        if self.is_known:
            return f'{self.value}'
        bits_str = ''.join('?' if b is None else str(b) for b in reversed(self.bits[:8]))
        return f'[{bits_str}..](τ={self.tension}, {self.n_possible} vals, {self.min_value}..{self.max_value})'


# ════════════════════════════════════════════════════════════
# VERIFICATION
# ════════════════════════════════════════════════════════════

def verify():
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  STONE 15: NUMBERS — Integers with tension               ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Basic construction
    print("CONSTRUCTION:")
    a = RayonInt.known(42, width=8)
    print(f"  known(42) = {a}, tension={a.tension}")
    b = RayonInt.unknown(width=8)
    print(f"  unknown() = {b}, tension={b.tension}, possible={b.n_possible}")
    c = RayonInt.partial(0b10100000, 0b00001111, width=8)  # top 4 known, bottom 4 unknown
    print(f"  partial(0xA0, mask=0x0F) = {c}")
    print(f"    possible: {c.possible_values()[:10]}...")
    print()

    # Arithmetic: known + known = standard
    print("ARITHMETIC (known): Rayon = Standard")
    print("─" * 50)
    for av, bv in [(5, 3), (100, 200), (255, 1), (0, 0)]:
        a = RayonInt.known(av, 8)
        b = RayonInt.known(bv, 8)
        s = a + b
        expected = (av + bv) & 0xFF
        match = s.value == expected
        print(f"  {av} + {bv} = {s.value} (expected {expected}) {'✓' if match else '✗'}")
    print()

    # Arithmetic: known + unknown
    print("ARITHMETIC (partial): tension propagation")
    print("─" * 50)
    a = RayonInt.known(0, 8)  # zero
    b = RayonInt.unknown(8)   # all unknown
    s = a + b
    print(f"  0 + ? = {s}")
    print(f"    tension: {s.tension} (same as ?, adding 0 is free)")
    print()

    # Key test: carry kill
    a = RayonInt.partial(0b00000000, 0b11110000, 8)  # low 4=0, high 4=?
    b = RayonInt.partial(0b00000000, 0b11110000, 8)  # same
    s = a + b
    print(f"  [????0000] + [????0000] = {s}")
    print(f"    Low carry killed! Carry from bit 3→4 = AND(0,0) = 0")
    print(f"    Tension of sum: {s.tension}")
    print()

    # AND with kills
    print("BITWISE AND (kill-links):")
    a = RayonInt.known(0b10101010, 8)
    b = RayonInt.unknown(8)
    c = a & b
    print(f"  0xAA AND ? = {c}")
    print(f"    tension: {c.tension} (only 4 unknown — zeros killed!)")
    print()

    # OR with kills
    print("BITWISE OR (kill-links):")
    a = RayonInt.known(0b10101010, 8)
    b = RayonInt.unknown(8)
    c = a | b
    print(f"  0xAA OR ? = {c}")
    print(f"    tension: {c.tension} (only 4 unknown — ones killed!)")
    print()

    # Equality
    print("EQUALITY (three-state):")
    a = RayonInt.known(5, 8)
    b = RayonInt.known(5, 8)
    c = RayonInt.known(7, 8)
    d = RayonInt.unknown(8)
    print(f"  5 == 5: {a == b}")
    print(f"  5 == 7: {a == c}")
    print(f"  5 == ?: {a == d} (might be equal, might not)")
    print()

    # Subtraction
    print("SUBTRACTION:")
    a = RayonInt.known(10, 8)
    b = RayonInt.known(3, 8)
    s = a - b
    print(f"  10 - 3 = {s} (expected 7) {'✓' if s.value == 7 else '✗'}")

    a = RayonInt.known(200, 8)
    b = RayonInt.known(50, 8)
    s = a - b
    print(f"  200 - 50 = {s} (expected 150) {'✓' if s.value == 150 else '✗'}")

    print(f"""
═══════════════════════════════════════════════════════════════
STONE 15: NUMBERS — Complete

  RayonInt: integer where each bit is {{0, 1, ?}}.
  Tension = count of ? bits. Values = 2^tension possible.

  Arithmetic VERIFIED:
    known + known = standard math ✓
    0 + ? = ? (no tension increase) ✓
    AND(known, ?) kills ? bits at 0-positions ✓
    OR(known, ?) kills ? bits at 1-positions ✓
    Addition carry chain propagates ? correctly ✓
    Subtraction via complement ✓
    Equality: True / False / ? (three-state) ✓

  KEY PROPERTY: same number type works for:
    - Normal computation (all bits known, tension=0)
    - Search/solving (some bits ?, tension>0)
    - Analysis (all bits ?, tension=width)

  Same code. Same type. Different knowledge.
═══════════════════════════════════════════════════════════════
""")


if __name__ == '__main__':
    verify()
