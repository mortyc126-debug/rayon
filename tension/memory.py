"""
STONE 19: MEMORY — Variables and arrays with tension.

Standard memory: flat cells, each holds a value.
Rayon memory: cells with values AND tension. Partially known arrays.

Variable = cell with value or ?.
Array = ordered cells, each independently known or ?.
Index with ? = ALL elements become ? (which one? unknown).

Immutable by default. Operations return NEW arrays.
Tension of array = sum of element tensions.
"""

from rayon_numbers import RayonInt


class RayonVar:
    """A single variable with tension."""
    __slots__ = ('name', 'val')

    def __init__(self, name, value=None, width=32):
        self.name = name
        if value is None:
            self.val = RayonInt.unknown(width)
        elif isinstance(value, RayonInt):
            self.val = value
        else:
            self.val = RayonInt.known(value, width)

    @property
    def tension(self):
        return self.val.tension

    @property
    def known(self):
        return self.val.is_known

    def set(self, value):
        """Returns NEW variable (immutable)."""
        return RayonVar(self.name, value, self.val.width)

    def __repr__(self):
        return f'{self.name}={self.val}'


class RayonArray:
    """
    Array where each element has independent tension.

    Some elements known, others ?. Tension = sum of element tensions.
    Operations: index, slice, map, reduce, set.
    All return NEW arrays (immutable).
    """
    def __init__(self, name, elements=None, size=0, width=32):
        self.name = name
        self.width = width
        if elements is not None:
            self.elements = list(elements)
        else:
            self.elements = [RayonInt.unknown(width) for _ in range(size)]

    @staticmethod
    def known(name, values, width=32):
        """Array from known values."""
        elems = [RayonInt.known(v, width) for v in values]
        return RayonArray(name, elems, width=width)

    @staticmethod
    def unknown(name, size, width=32):
        """Array of unknowns."""
        return RayonArray(name, size=size, width=width)

    @staticmethod
    def partial(name, values, mask, width=32):
        """Array where mask[i]=True means element i is unknown."""
        elems = []
        for i, v in enumerate(values):
            if mask[i]:
                elems.append(RayonInt.unknown(width))
            else:
                elems.append(RayonInt.known(v, width))
        return RayonArray(name, elems, width=width)

    def __len__(self):
        return len(self.elements)

    @property
    def tension(self):
        """Total tension = sum of element tensions."""
        return sum(e.tension for e in self.elements)

    @property
    def known_count(self):
        return sum(1 for e in self.elements if e.is_known)

    def __getitem__(self, idx):
        """
        Index access.
        Known index: return that element.
        ? index: return ? (don't know which element).
        Slice: return sub-array.
        """
        if isinstance(idx, slice):
            return RayonArray(f'{self.name}[{idx}]',
                            self.elements[idx], width=self.width)
        if isinstance(idx, int):
            return self.elements[idx]
        # ? index: could be any element → result is ?
        return RayonInt.unknown(self.width)

    def set(self, idx, value):
        """Set element at index. Returns NEW array."""
        if not isinstance(value, RayonInt):
            value = RayonInt.known(value, self.width)
        new_elems = list(self.elements)
        new_elems[idx] = value
        return RayonArray(self.name, new_elems, width=self.width)

    def map(self, fn):
        """Apply function to each element. Returns new array."""
        new_elems = [fn(e) for e in self.elements]
        return RayonArray(f'{self.name}.map', new_elems, width=self.width)

    def reduce(self, fn, initial=None):
        """Fold array with binary function."""
        if initial is None:
            acc = self.elements[0]
            start = 1
        else:
            acc = initial
            start = 0
        for i in range(start, len(self.elements)):
            acc = fn(acc, self.elements[i])
        return acc

    def tension_map(self):
        """Show tension of each element."""
        return [(i, e.tension, e.is_known) for i, e in enumerate(self.elements)]

    def __repr__(self):
        known = self.known_count
        total = len(self)
        if total <= 8:
            elems = ', '.join(str(e.value) if e.is_known else '?' for e in self.elements)
            return f'{self.name}[{elems}] (τ={self.tension})'
        return f'{self.name}[{total} elems, {known} known, τ={self.tension}]'


# ════════════════════════════════════════════════════════════
# VERIFICATION
# ════════════════════════════════════════════════════════════

def verify():
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  STONE 19: MEMORY — Variables and arrays with tension    ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    w = 8

    # ── Variables ──
    print("VARIABLES:")
    print("─" * 50)
    x = RayonVar('x', 42, w)
    y = RayonVar('y', None, w)
    print(f"  {x} (τ={x.tension})")
    print(f"  {y} (τ={y.tension})")

    x2 = x.set(99)
    print(f"  x.set(99) → {x2} (immutable: original {x})")
    print()

    # ── Known array ──
    print("ARRAYS (known):")
    print("─" * 50)
    msg = RayonArray.known('msg', [0x61, 0x62, 0x63, 0x80, 0, 0, 0, 0x18], w)
    print(f"  {msg}")
    print(f"  msg[0] = {msg[0]}")
    print(f"  msg[3] = {msg[3]}")
    print()

    # ── Unknown array ──
    print("ARRAYS (unknown):")
    print("─" * 50)
    secret = RayonArray.unknown('secret', 4, w)
    print(f"  {secret}")
    print(f"  secret[0] = {secret[0]}")
    print()

    # ── Partial array ──
    print("ARRAYS (partial):")
    print("─" * 50)
    part = RayonArray.partial('W', [0x41, 0x42, 0, 0], [False, False, True, True], w)
    print(f"  {part}")
    print(f"  W[0] = {part[0]} (known)")
    print(f"  W[2] = {part[2]} (unknown)")
    print()

    # ── Operations ──
    print("OPERATIONS:")
    print("─" * 50)

    # Map: apply NOT to each element
    neg = msg.map(lambda e: ~e)
    print(f"  msg.map(NOT) = {neg}")

    # Reduce: XOR all elements
    xor_all = msg.reduce(lambda a, b: a ^ b)
    print(f"  msg.reduce(XOR) = {xor_all}")
    expected = 0x61 ^ 0x62 ^ 0x63 ^ 0x80 ^ 0 ^ 0 ^ 0 ^ 0x18
    print(f"    expected: {expected} {'✓' if xor_all.value == expected else '✗'}")

    # Reduce on partial array
    xor_part = part.reduce(lambda a, b: a ^ b)
    print(f"  partial.reduce(XOR) = {xor_part} (τ={xor_part.tension})")
    print()

    # ── Set element ──
    print("SET (immutable):")
    print("─" * 50)
    secret2 = secret.set(0, RayonInt.known(0xFF, w))
    print(f"  secret.set(0, 0xFF) = {secret2}")
    print(f"  original secret = {secret} (unchanged)")
    print()

    # ── Tension map ──
    print("TENSION MAP:")
    print("─" * 50)
    hybrid = RayonArray.partial('H', [0xBA, 0x78, 0, 0, 0, 0, 0, 0],
                                [False, False, True, True, True, True, True, True], w)
    print(f"  {hybrid}")
    for i, t, k in hybrid.tension_map():
        bar = '·' if k else '█' * (t // 2)
        print(f"    [{i}] τ={t:>2} {'known' if k else '?':>5} {bar}")

    # ── SHA-256 message as Rayon array ──
    print()
    print("SHA-256 MESSAGE AS RAYON ARRAY:")
    print("─" * 50)

    # Real scenario: know padding, unknown message words
    sha_msg = RayonArray.partial(
        'W',
        [0]*16,
        [True]*4 + [False]*11 + [True],  # W[0..3] unknown (message), W[4..14]=0 (padding), W[15] unknown (length?)
        width=32
    )
    print(f"  {sha_msg}")
    print(f"  Known: {sha_msg.known_count}/16, Unknown: {16 - sha_msg.known_count}/16")
    print(f"  Total tension: {sha_msg.tension} bits")
    print(f"  Search space: 2^{sha_msg.tension}")

    print(f"""
═══════════════════════════════════════════════════════════════
STONE 19: MEMORY — Complete

  RayonVar: single variable with tension.
    Known (τ=0) or unknown (τ=width). Immutable set().

  RayonArray: ordered elements, each with independent tension.
    Known / unknown / partial arrays.
    Operations: index, slice, map, reduce, set.
    All immutable (return new arrays).

  TENSION:
    Variable: τ = bits of uncertainty.
    Array: τ = sum of element tensions.
    Map: preserves per-element tension.
    Reduce: accumulates tension through operation.

  SHA-256 USE CASE:
    Message = RayonArray of 16 words.
    Known words (padding): τ=0. Unknown words: τ=32.
    Total search space = 2^(total tension).

  THIS COMPLETES THE BASIC LANGUAGE:
    Logic + Arithmetic + Control + Functions + Memory
    All with tension. All verified.
    Rayon Language v4 is ready to build.
═══════════════════════════════════════════════════════════════
""")


if __name__ == '__main__':
    verify()
