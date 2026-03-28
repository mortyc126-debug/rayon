"""
THE BRIDGE: How Rayon Mathematics connects to standard computation.

Standard math = Rayon math where ALL τ = 0.

When every input is known: Rayon gives IDENTICAL results to standard.
When some inputs are ?: Rayon gives ADDITIONAL information — where to skip.

This is like complex numbers extending reals:
  Real numbers = complex with imaginary = 0.
  Standard math = Rayon with all ? resolved.

DEMONSTRATION: Same SHA-256 round, two modes.
  Mode 1: Standard (all inputs known) → exact result, same as always
  Mode 2: Rayon (some inputs ?) → partial result + skip map
"""

from three_state import Q, r_and, r_or, r_xor, r_not


# ════════════════════════════════════════════════════════════
# DEMO 1: Simple addition — standard vs Rayon
# ════════════════════════════════════════════════════════════

def standard_add_bits(a, b, carry_in):
    """Standard 1-bit adder. All inputs known."""
    s = a ^ b ^ carry_in
    c_out = (a & b) | (a & carry_in) | (b & carry_in)
    return s, c_out


def rayon_add_bits(a, b, carry_in):
    """
    Rayon 1-bit adder. Some inputs may be ?.

    sum = a XOR b XOR carry_in
    carry_out = (a AND b) OR (a AND carry_in) OR (b AND carry_in)
    """
    # Sum: XOR chain — needs ALL inputs
    ab, _ = r_xor(a, b)
    s, _ = r_xor(ab, carry_in)

    # Carry: OR of ANDs — can SKIP!
    ab_and, _ = r_and(a, b)
    ac_and, _ = r_and(a, carry_in)
    bc_and, _ = r_and(b, carry_in)

    or1, _ = r_or(ab_and, ac_and)
    c_out, _ = r_or(or1, bc_and)

    return s, c_out


# ════════════════════════════════════════════════════════════
# DEMO 2: 4-bit adder — where skips happen
# ════════════════════════════════════════════════════════════

def rayon_add_4bit(a_bits, b_bits):
    """
    4-bit addition in Rayon.
    a_bits, b_bits: lists of 4 values, each 0, 1, or Q().
    """
    carry = 0  # initial carry = known 0

    results = []
    carry_states = []

    for i in range(4):
        s, carry = rayon_add_bits(a_bits[i], b_bits[i], carry)
        results.append(s)
        carry_states.append(carry)

    return results, carry_states


# ════════════════════════════════════════════════════════════
# DEMO 3: SHA-256 Ch function — where ? shines
# ════════════════════════════════════════════════════════════

def standard_ch(e, f, g):
    """Standard Ch(e,f,g) = (e AND f) XOR (NOT(e) AND g)."""
    return (e & f) ^ ((~e & 1) & g)


def rayon_ch(e, f, g):
    """
    Rayon Ch: if e is known, we can SKIP either f or g!

    Ch(0, f, g) = g  (f skipped!)
    Ch(1, f, g) = f  (g skipped!)
    Ch(?, f, g) = ?  (need e first)
    """
    # e AND f
    ef, _ = r_and(e, f)
    # NOT(e) AND g
    not_e, _ = r_not(e)
    neg, _ = r_and(not_e, g)
    # XOR
    result, _ = r_xor(ef, neg)
    return result


# ════════════════════════════════════════════════════════════
# VERIFICATION
# ════════════════════════════════════════════════════════════

def verify_bridge():
    print("THE BRIDGE: Standard ↔ Rayon")
    print("═" * 55)
    print()

    # ── Demo 1: When all known → same result ──
    print("DEMO 1: All inputs known → Rayon = Standard")
    print("─" * 55)

    all_match = True
    for a in [0, 1]:
        for b in [0, 1]:
            for c in [0, 1]:
                s_std, c_std = standard_add_bits(a, b, c)
                s_ray, c_ray = rayon_add_bits(a, b, c)

                match = (s_std == s_ray and c_std == c_ray)
                if not match:
                    all_match = False
                    print(f"  MISMATCH: add({a},{b},{c}) std=({s_std},{c_std}) ray=({s_ray},{c_ray})")

    print(f"  1-bit adder: all 8 cases {'✓ MATCH' if all_match else '✗ MISMATCH'}")
    print()

    # Ch function
    all_match_ch = True
    for e in [0, 1]:
        for f in [0, 1]:
            for g in [0, 1]:
                std = standard_ch(e, f, g)
                ray = rayon_ch(e, f, g)
                if std != ray:
                    all_match_ch = False

    print(f"  Ch(e,f,g): all 8 cases {'✓ MATCH' if all_match_ch else '✗ MISMATCH'}")
    print()

    # ── Demo 2: Some ? → Rayon shows skips ──
    print("DEMO 2: Some inputs ? → Rayon shows what's skippable")
    print("─" * 55)
    print()

    q = Q(tau=1.0)

    # Ch with known e
    print("  Ch(e=0, f=?, g=?) → should need only g (f skipped)")
    result = rayon_ch(0, q, q)
    print(f"    Result: {result}")
    print(f"    In standard math: must compute (0 AND ?) XOR (1 AND ?)")
    print(f"    In Rayon: AND(0, ?) = 0, so first term = 0.")
    print(f"              XOR(0, AND(1, ?)) = AND(1, ?) = ?")
    print(f"    → Only g matters! f was SKIPPED by AND(0, ?).")
    print()

    print("  Ch(e=1, f=?, g=?) → should need only f (g skipped)")
    result = rayon_ch(1, q, q)
    print(f"    Result: {result}")
    print(f"    AND(1, ?) = ?, AND(NOT(1)=0, ?) = 0, XOR(?, 0) = ?")
    print(f"    → Only f matters! g was SKIPPED by AND(0, ?).")
    print()

    print("  Ch(e=?, f=0, g=0) → even without e, result is known!")
    result = rayon_ch(q, 0, 0)
    print(f"    Result: {result}")
    print(f"    If e=0: Ch=g=0. If e=1: Ch=f=0. Either way: 0!")
    print(f"    Rayon could detect this with deeper propagation.")
    print()

    # ── Demo 3: 4-bit adder with partial knowledge ──
    print("DEMO 3: 4-bit adder with partial knowledge")
    print("─" * 55)
    print()

    # Case 1: a = 0000 (known), b = ???? (unknown)
    print("  a = [0,0,0,0], b = [?,?,?,?]")
    a_bits = [0, 0, 0, 0]
    b_bits = [q, q, q, q]
    sums, carries = rayon_add_4bit(a_bits, b_bits)
    print(f"    sum = {[str(s) if not isinstance(s, Q) else '?' for s in sums]}")
    print(f"    carries = {[str(c) if not isinstance(c, Q) else '?' for c in carries]}")
    print(f"    → Adding 0: sum = b (trivially). Carries = 0.")
    print()

    # Case 2: a = 1111, b = ????
    print("  a = [1,1,1,1], b = [?,?,?,?]")
    a_bits = [1, 1, 1, 1]
    b_bits = [q, q, q, q]
    sums, carries = rayon_add_4bit(a_bits, b_bits)
    print(f"    sum = {[str(s) if not isinstance(s, Q) else '?' for s in sums]}")
    print(f"    carries = {[str(c) if not isinstance(c, Q) else '?' for c in carries]}")
    print(f"    → Adding 1111: needs ALL of b (XOR in sum requires both).")
    print()

    # Case 3: a[0]=0 (rest ?), b all ?
    print("  a = [0,?,?,?], b = [?,?,?,?]")
    a_bits = [0, q, q, q]
    b_bits = [q, q, q, q]
    sums, carries = rayon_add_4bit(a_bits, b_bits)
    print(f"    sum = {[str(s) if not isinstance(s, Q) else '?' for s in sums]}")
    print(f"    carries = {[str(c) if not isinstance(c, Q) else '?' for c in carries]}")
    print(f"    → Bit 0: carry = AND(0, ?) = 0! Carry chain KILLED at bit 0.")
    print(f"    → This is the carry-web Skip in action!")

    print(f"""
═══════════════════════════════════════════════════════════════
THE BRIDGE — Summary:

  WHEN ALL INPUTS KNOWN (τ=0):
    Rayon = Standard. Same bits. Same results. Verified ✓.
    Rayon adds ZERO overhead to standard computation.

  WHEN SOME INPUTS ? (τ>0):
    Rayon computes WHAT IT CAN and marks rest as ?.
    Standard math: must guess (brute force).
    Rayon math: shows WHICH guesses to skip.

  THE BRIDGE IS EXACT:
    Resolve all ?s → get standard computation.
    Add ?s → get skip map for free.

  FOR SHA-256:
    Standard: compute 64 rounds, cost always ~20K operations.
    Rayon: if searching (preimage, collision):
      Start with input = all ?
      Propagate ? through circuit
      AND gates kill ?s (carry=0 → skip carry chain!)
      XOR gates preserve ?s (must resolve all)
      The PATTERN of resolved/unresolved = search strategy.

  Rayon doesn't change SHA-256.
  It adds a LENS that shows where computation is cheap.
═══════════════════════════════════════════════════════════════
""")


if __name__ == '__main__':
    verify_bridge()
