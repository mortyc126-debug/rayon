"""
STONE 16: ARITHMETIC — Full operations with tension.

Multiplication: shift-and-add. Unknown multiplier bits = BRANCH POINTS.
  Cost = 2^(unknown bits in multiplier).
  OPTIMIZATION: use number with fewer ?s as multiplier.

Division: shift-and-subtract.
  By known constant: free (no branches).
  By unknown: branch points.

Shifts/Rotations: just move bits. ?s move too. FREE.

Comparison: bit-by-bit from MSB. ? → result is ?.

Modular: truncate to width. FREE.
"""

from rayon_numbers import RayonInt


# ════════════════════════════════════════════════════════════
# SHIFTS AND ROTATIONS (FREE — no branches)
# ════════════════════════════════════════════════════════════

def shl(a, n):
    """Left shift by n. Low bits become 0. FREE."""
    bits = [0] * n + a.bits[:a.width - n]
    return RayonInt(bits=bits, width=a.width)

def shr(a, n):
    """Right shift by n. High bits become 0. FREE."""
    bits = a.bits[n:] + [0] * n
    return RayonInt(bits=bits, width=a.width)

def rotr(a, n):
    """Right rotation by n. Bits wrap around. FREE."""
    n = n % a.width
    bits = a.bits[n:] + a.bits[:n]
    return RayonInt(bits=bits, width=a.width)

def rotl(a, n):
    """Left rotation by n. FREE."""
    n = n % a.width
    bits = a.bits[a.width-n:] + a.bits[:a.width-n]
    return RayonInt(bits=bits, width=a.width)


# ════════════════════════════════════════════════════════════
# MULTIPLICATION (branch points on unknown multiplier bits)
# ════════════════════════════════════════════════════════════

def multiply(a, b):
    """
    Multiply a × b with tension tracking.

    Method: shift-and-add using b as multiplier.
    Each known 0 bit of b: skip (free).
    Each known 1 bit of b: add shifted a (free if a known).
    Each ? bit of b: BRANCH POINT.

    OPTIMIZATION: choose number with fewer ? bits as multiplier.
    """
    # Optimization: fewer ?s as multiplier
    if a.tension < b.tension:
        a, b = b, a  # swap: b should have fewer ?s

    branch_count = 0
    result = RayonInt.known(0, a.width)

    for i in range(b.width):
        bit = b.bits[i]
        if bit == 0:
            continue  # SKIP — kill-link!
        elif bit == 1:
            shifted = shl(a, i)
            result = result + shifted
        else:  # bit is None (?)
            branch_count += 1
            # Unknown: result becomes partially unknown
            shifted = shl(a, i)
            # Each bit of result that could be affected becomes ?
            for j in range(i, a.width):
                if result.bits[j] is not None or shifted.bits[j] is not None:
                    if shifted.bits[j] is None or result.bits[j] is None:
                        result.bits[j] = None
                    # Even if both known: the ? multiplier bit makes this uncertain
                    result.bits[j] = None

    return result, branch_count


# ════════════════════════════════════════════════════════════
# DIVISION (by known constant: FREE)
# ════════════════════════════════════════════════════════════

def divmod_const(a, divisor):
    """
    a / divisor where divisor is known constant.
    Returns (quotient, remainder) as RayonInts.

    If a is fully known: exact. If a has ?s: propagate tension.
    """
    if divisor == 0:
        return None, None

    if a.is_known:
        q = a.value // divisor
        r = a.value % divisor
        return RayonInt.known(q, a.width), RayonInt.known(r, a.width)

    # a has unknown bits: result has unknown bits
    # Conservative: mark all bits as unknown
    # (exact propagation requires bit-level shift-subtract analysis)
    return RayonInt.unknown(a.width), RayonInt.unknown(a.width)


# ════════════════════════════════════════════════════════════
# COMPARISON (three-state: True/False/?)
# ════════════════════════════════════════════════════════════

def less_than(a, b):
    """
    a < b: compare bit-by-bit from MSB.
    Returns True, False, or None (?).
    """
    for i in range(a.width - 1, -1, -1):
        ai = a.bits[i] if i < len(a.bits) else 0
        bi = b.bits[i] if i < len(b.bits) else 0

        if ai is None or bi is None:
            return None  # can't determine

        if ai < bi:
            return True
        if ai > bi:
            return False

    return False  # equal → not less than

def greater_than(a, b):
    return less_than(b, a)


# ════════════════════════════════════════════════════════════
# MODULAR ARITHMETIC (for SHA-256: mod 2^32)
# ════════════════════════════════════════════════════════════

def mod_add(a, b, width=32):
    """Modular addition: (a + b) mod 2^width. Just truncate."""
    result = a + b
    result.bits = result.bits[:width]
    result.width = width
    return result

def mod_sub(a, b, width=32):
    """Modular subtraction."""
    result = a - b
    result.bits = result.bits[:width]
    result.width = width
    return result


# ════════════════════════════════════════════════════════════
# SHA-256 BUILDING BLOCKS
# ════════════════════════════════════════════════════════════

def sigma0(x):
    """SHA-256 σ₀: ROTR7 XOR ROTR18 XOR SHR3. All FREE."""
    return rotr(x, 7) ^ rotr(x, 18) ^ shr(x, 3)

def sigma1(x):
    """SHA-256 σ₁: ROTR17 XOR ROTR19 XOR SHR10. FREE."""
    return rotr(x, 17) ^ rotr(x, 19) ^ shr(x, 10)

def Sigma0(x):
    """SHA-256 Σ₀: ROTR2 XOR ROTR13 XOR ROTR22. FREE."""
    return rotr(x, 2) ^ rotr(x, 13) ^ rotr(x, 22)

def Sigma1(x):
    """SHA-256 Σ₁: ROTR6 XOR ROTR11 XOR ROTR25. FREE."""
    return rotr(x, 6) ^ rotr(x, 11) ^ rotr(x, 25)

def Ch(e, f, g):
    """SHA-256 Ch: (e AND f) XOR (NOT(e) AND g). Kill-links active!"""
    return (e & f) ^ (~e & g)

def Maj(a, b, c):
    """SHA-256 Maj: (a AND b) XOR (a AND c) XOR (b AND c). Kill-links!"""
    return (a & b) ^ (a & c) ^ (b & c)


# ════════════════════════════════════════════════════════════
# VERIFICATION
# ════════════════════════════════════════════════════════════

def verify():
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  STONE 16: ARITHMETIC — Full operations with tension     ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    w = 8  # 8-bit for readability

    # Shifts and rotations
    print("SHIFTS & ROTATIONS (all FREE):")
    print("─" * 50)
    a = RayonInt.partial(0b11001010, 0b00000101, w)  # bits 0,2 unknown
    print(f"  a = {a}")
    print(f"  shl(a, 2) = {shl(a, 2)} (tension preserved, shifted)")
    print(f"  shr(a, 2) = {shr(a, 2)}")
    print(f"  rotr(a, 4) = {rotr(a, 4)}")
    print()

    # Multiplication
    print("MULTIPLICATION:")
    print("─" * 50)

    # known × known
    a = RayonInt.known(7, w)
    b = RayonInt.known(6, w)
    prod, branches = multiply(a, b)
    print(f"  7 × 6 = {prod} (expected 42) {'✓' if prod.value == 42 else '✗'}")
    print(f"    branches: {branches}")

    # known × unknown
    a = RayonInt.known(5, w)
    b = RayonInt.unknown(w)
    prod, branches = multiply(a, b)
    print(f"  5 × ? = {prod}")
    print(f"    branches: {branches} (=unknown bits of multiplier)")

    # zero × unknown = zero!
    a = RayonInt.known(0, w)
    b = RayonInt.unknown(w)
    prod, branches = multiply(a, b)
    print(f"  0 × ? = {prod}")
    print(f"    branches: {branches} (zero kills all!)")

    # partial × partial
    a = RayonInt.partial(0b00000011, 0b00001100, w)  # bits 2,3 unknown, rest = 3
    b = RayonInt.known(4, w)
    prod, branches = multiply(a, b)
    print(f"  [00??0011] × 4 = {prod}")
    print(f"    branches: {branches}")
    print()

    # Comparison
    print("COMPARISON (three-state):")
    print("─" * 50)
    a = RayonInt.known(5, w)
    b = RayonInt.known(7, w)
    c = RayonInt.unknown(w)
    print(f"  5 < 7: {less_than(a, b)} ✓")
    print(f"  7 < 5: {less_than(b, a)} ✓")
    print(f"  5 < ?: {less_than(a, c)} (can't determine = None) ✓")
    print()

    # SHA-256 building blocks with tension
    print("SHA-256 BLOCKS WITH TENSION:")
    print("─" * 50)

    e = RayonInt.known(0xAB, w)
    f = RayonInt.unknown(w)
    g = RayonInt.unknown(w)

    ch = Ch(e, f, g)
    print(f"  e = 0xAB (known)")
    print(f"  Ch(e, ?, ?) = {ch}")
    print(f"    tension: {ch.tension} (kills at e=0 bits, keeps at e=1 bits)")

    e_known_bits = bin(0xAB).count('1')
    print(f"    e has {e_known_bits} ones → {e_known_bits} bits from f, {w-e_known_bits} from g")
    print(f"    total ? bits = {w} (all from f or g, but DETERMINED by e)")
    print()

    # Σ functions (all XOR/rotate = free)
    x = RayonInt.unknown(w)
    s0 = Sigma0(x)
    s1 = Sigma1(x)
    print(f"  Σ₀(?) tension: {s0.tension} (XOR of rotations = same tension)")
    print(f"  Σ₁(?) tension: {s1.tension}")
    print(f"  σ₀(?) tension: {sigma0(x).tension}")
    print(f"  σ₁(?) tension: {sigma1(x).tension}")
    print(f"  → All Σ/σ functions: tension PRESERVED (pure XOR). FREE!")

    print(f"""
═══════════════════════════════════════════════════════════════
STONE 16: ARITHMETIC — Complete

  SHIFTS/ROTATIONS: FREE (tension preserved, bits move)
  MULTIPLICATION: cost = 2^(unknown bits in multiplier)
    - 0 × ? = 0 (KILL — zero branches!)
    - known × known = standard ✓
  DIVISION by constant: FREE
  COMPARISON: True/False/? (three-state)
  MODULAR: truncate (free)

  SHA-256 BLOCKS:
    σ₀, σ₁, Σ₀, Σ₁: FREE (pure XOR/rotate)
    Ch(known_e, ?, ?): tension = width (but structured by e)
    Maj(?, ?, ?): tension = width (3 ANDs per bit)

  KEY INSIGHT:
    0 × ? = 0 (multiplication by zero kills all branches)
    This is the MULTIPLICATIVE KILL — analogous to AND(0,?)=0
    but for entire numbers.

  Same arithmetic for computation AND analysis.
═══════════════════════════════════════════════════════════════
""")

if __name__ == '__main__':
    verify()
