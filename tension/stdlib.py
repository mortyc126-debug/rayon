"""
STONE 24: STANDARD LIBRARY — crypto, math, and solver primitives.

Four modules:
  CRYPTO: SHA-256 compression with tension-aware RayonInt
  MATH:   GF(2) solver, modular arithmetic
  SOLVER: find_preimage, find_collision using backward propagation
  IO:     hex conversion, tension visualization

All operations support partial (?) inputs natively via RayonInt.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rayon_numbers import RayonInt
from arithmetic import (
    rotr, shr, shl, mod_add,
    Sigma0, Sigma1, sigma0, sigma1, Ch, Maj,
)


# ════════════════════════════════════════════════════════════════
# SHA-256 CONSTANTS
# ════════════════════════════════════════════════════════════════

SHA256_K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]

SHA256_IV = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
]


# ════════════════════════════════════════════════════════════════
# IO MODULE
# ════════════════════════════════════════════════════════════════

class IO:
    """Hex conversion and tension visualization for RayonInt arrays."""

    @staticmethod
    def from_hex(s, word_width=32):
        """
        Parse hex string to list of RayonInt words.
        Each pair of hex chars = 8 bits. Words are word_width bits wide.
        Supports '?' in hex string (each ? = 4 unknown bits).
        """
        s = s.strip().lower()
        if s.startswith("0x"):
            s = s[2:]
        # Pad to multiple of (word_width // 4) hex chars
        chars_per_word = word_width // 4
        if len(s) % chars_per_word != 0:
            s = s.zfill(((len(s) + chars_per_word - 1) // chars_per_word) * chars_per_word)

        words = []
        for wi in range(0, len(s), chars_per_word):
            hex_chunk = s[wi:wi + chars_per_word]
            bits = []
            # Process hex chars from right (LSB) to left (MSB)
            for ci in range(len(hex_chunk) - 1, -1, -1):
                ch = hex_chunk[ci]
                if ch == '?':
                    bits.extend([None, None, None, None])
                else:
                    nib = int(ch, 16)
                    bits.extend([(nib >> b) & 1 for b in range(4)])
            words.append(RayonInt(bits=bits[:word_width], width=word_width))
        return words

    @staticmethod
    def to_hex(arr, word_width=None):
        """
        Convert list of RayonInt (or single RayonInt) to hex string.
        Unknown bits shown as '?' in the corresponding nibble.
        """
        if isinstance(arr, RayonInt):
            arr = [arr]
        parts = []
        for word in arr:
            w = word_width if word_width else word.width
            chars_per_word = w // 4
            hex_chars = []
            for ni in range(chars_per_word):
                nibble_bits = word.bits[ni * 4:(ni + 1) * 4]
                if any(b is None for b in nibble_bits):
                    hex_chars.append('?')
                else:
                    val = sum(b << i for i, b in enumerate(nibble_bits))
                    hex_chars.append(format(val, 'x'))
            # Reverse because we built LSB-first
            hex_chars.reverse()
            parts.append(''.join(hex_chars))
        return ''.join(parts)

    @staticmethod
    def print_tension(arr):
        """Visual tension map: shows each bit as 0, 1, or ? with color-like markers."""
        if isinstance(arr, RayonInt):
            arr = [arr]
        for idx, word in enumerate(arr):
            bits_str = ''.join(
                '?' if b is None else str(b)
                for b in reversed(word.bits)
            )
            t = word.tension
            total = word.width
            bar_len = 20
            known_frac = (total - t) / total if total > 0 else 1.0
            filled = int(known_frac * bar_len)
            bar = '#' * filled + '.' * (bar_len - filled)
            print(f"  [{idx:2d}] {bits_str}  tension={t:2d}/{total}  [{bar}]")


# ════════════════════════════════════════════════════════════════
# CRYPTO MODULE
# ════════════════════════════════════════════════════════════════

class Crypto:
    """SHA-256 compression with tension-aware RayonInt."""

    @staticmethod
    def _make_iv(width=32):
        """SHA-256 initial hash values as RayonInt array."""
        mask = (1 << width) - 1
        return [RayonInt.known(iv & mask, width) for iv in SHA256_IV]

    @staticmethod
    def _make_k(width=32):
        """SHA-256 round constants as RayonInt array."""
        mask = (1 << width) - 1
        return [RayonInt.known(k & mask, width) for k in SHA256_K]

    @staticmethod
    def sha256_compress(state, block, rounds=64, width=32):
        """
        One SHA-256 compression function with tension.

        state:  list of 8 RayonInt (hash state, width-bit each)
        block:  list of 16 RayonInt (message words, width-bit each)
        rounds: number of rounds (default 64, can reduce for testing)
        width:  bit width (32 for standard, 8 for fast testing)

        Returns: list of 8 RayonInt (new state)
        Supports partial (?) inputs -- tension propagates through.
        """
        K = Crypto._make_k(width)
        mask = (1 << width) - 1

        # Message schedule: expand 16 words to `rounds` words
        W = list(block[:16])
        # Pad W if fewer than 16 words provided
        while len(W) < 16:
            W.append(RayonInt.known(0, width))

        for i in range(16, rounds):
            # W[i] = sigma1(W[i-2]) + W[i-7] + sigma0(W[i-15]) + W[i-16]
            s1 = sigma1(W[i - 2])
            s0 = sigma0(W[i - 15])
            w_new = mod_add(mod_add(s1, W[i - 7], width),
                            mod_add(s0, W[i - 16], width), width)
            W.append(w_new)

        # Working variables
        a, b, c, d, e, f, g, h = list(state[:8])

        # Compression rounds
        for i in range(rounds):
            S1 = Sigma1(e)
            ch = Ch(e, f, g)
            temp1 = mod_add(
                mod_add(h, S1, width),
                mod_add(mod_add(ch, K[i % 64], width), W[i], width),
                width
            )
            S0 = Sigma0(a)
            maj = Maj(a, b, c)
            temp2 = mod_add(S0, maj, width)

            h = g
            g = f
            f = e
            e = mod_add(d, temp1, width)
            d = c
            c = b
            b = a
            a = mod_add(temp1, temp2, width)

        # Add compressed chunk to state
        new_state = [
            mod_add(state[0], a, width),
            mod_add(state[1], b, width),
            mod_add(state[2], c, width),
            mod_add(state[3], d, width),
            mod_add(state[4], e, width),
            mod_add(state[5], f, width),
            mod_add(state[6], g, width),
            mod_add(state[7], h, width),
        ]
        return new_state


# ════════════════════════════════════════════════════════════════
# MATH MODULE
# ════════════════════════════════════════════════════════════════

class Math:
    """GF(2) solver and modular arithmetic for RayonInt."""

    @staticmethod
    def gf2_solve(equations):
        """
        Solve a system of XOR (GF(2)) equations via Gaussian elimination.

        equations: list of (coefficients, rhs) where
            coefficients = list of 0/1 (one per variable)
            rhs = 0 or 1

        Returns: dict {var_index: value} or None if inconsistent.
        Free variables are assigned 0.
        """
        if not equations:
            return {}

        n_vars = len(equations[0][0])
        # Build augmented matrix
        matrix = []
        for coeffs, rhs in equations:
            row = list(coeffs) + [rhs]
            matrix.append(row)

        n_rows = len(matrix)
        n_cols = n_vars + 1

        # Forward elimination
        pivot_col = [None] * n_rows  # which column is pivot for each row
        row_idx = 0
        for col in range(n_vars):
            # Find pivot
            found = None
            for r in range(row_idx, n_rows):
                if matrix[r][col] == 1:
                    found = r
                    break
            if found is None:
                continue
            # Swap
            matrix[row_idx], matrix[found] = matrix[found], matrix[row_idx]
            pivot_col[row_idx] = col
            # Eliminate
            for r in range(n_rows):
                if r != row_idx and matrix[r][col] == 1:
                    for c in range(n_cols):
                        matrix[r][c] ^= matrix[row_idx][c]
            row_idx += 1

        # Check consistency
        for r in range(row_idx, n_rows):
            if matrix[r][n_vars] == 1:
                return None  # inconsistent: 0 = 1

        # Back-substitute: free variables get 0
        solution = [0] * n_vars
        for r in range(row_idx):
            col = pivot_col[r]
            if col is not None:
                solution[col] = matrix[r][n_vars]

        return {i: solution[i] for i in range(n_vars)}

    @staticmethod
    def mod_add(a, b, width=32):
        """Modular addition: (a + b) mod 2^width."""
        return mod_add(a, b, width)

    @staticmethod
    def mod_sub(a, b, width=32):
        """Modular subtraction: (a - b) mod 2^width."""
        from arithmetic import mod_sub as _mod_sub
        return _mod_sub(a, b, width)

    @staticmethod
    def mod_mul(a, b, width=32):
        """
        Modular multiplication: (a * b) mod 2^width.
        Uses shift-and-add from arithmetic module.
        """
        from arithmetic import multiply
        prod, _ = multiply(a, b)
        prod.bits = prod.bits[:width]
        prod.width = width
        return prod


# ════════════════════════════════════════════════════════════════
# SOLVER MODULE
# ════════════════════════════════════════════════════════════════

class Solver:
    """
    Preimage and collision finding using Rayon tension analysis.

    Strategy:
      1. Run function with unknown (?) inputs
      2. Compare output with target to collect constraints
      3. Solve linear (XOR) constraints via GF(2)
      4. Branch on remaining nonlinear (AND) constraints
    """

    @staticmethod
    def _collect_xor_constraints(output_bits, target_bits):
        """
        Given output bits (may contain None) and target bits (known),
        collect constraints. For bits where output is known and
        differs from target, the system is inconsistent.
        Returns (constraints_ok, fixed_positions) where fixed_positions
        maps bit index to required value.
        """
        fixed = {}
        for i, (ob, tb) in enumerate(zip(output_bits, target_bits)):
            if tb is None:
                continue  # target bit unknown, no constraint
            if ob is not None:
                if ob != tb:
                    return False, {}  # inconsistent
            else:
                fixed[i] = tb
        return True, fixed

    @staticmethod
    def find_preimage(fn, target, input_width=8, max_attempts=256):
        """
        Find input x such that fn(x) == target.

        fn:     function RayonInt -> RayonInt
        target: RayonInt (the desired output)
        input_width: bit width of input

        Strategy:
        1. Forward pass with unknown input to see tension propagation
        2. Try to fix bits that are already constrained
        3. Brute-force remaining bits (bounded by max_attempts)

        Returns: RayonInt (found input) or None
        """
        # Phase 1: Run with fully unknown input to get output structure
        x_unknown = RayonInt.unknown(input_width)
        y_unknown = fn(x_unknown)

        # Phase 2: Check which output bits are already determined
        ok, fixed = Solver._collect_xor_constraints(
            y_unknown.bits, target.bits
        )

        # Phase 3: For XOR-linear functions, try algebraic solve
        # Build equations: for each output bit that depends linearly on input
        # Test each input bit's effect
        equations = []
        for out_bit_idx in range(target.width):
            tb = target.bits[out_bit_idx]
            if tb is None:
                continue
            # Probe each input bit
            coeffs = []
            for in_bit_idx in range(input_width):
                # Set only this input bit to 1, rest to 0
                probe_bits = [0] * input_width
                probe_bits[in_bit_idx] = 1
                probe = RayonInt(bits=probe_bits, width=input_width)
                y_probe = fn(probe)
                # For XOR-linear: fn(e_i)[j] gives coefficient of x_i in output bit j
                coeffs.append(y_probe.bits[out_bit_idx] if y_probe.bits[out_bit_idx] is not None else 0)

            # Also get the constant term: fn(0)
            zero = RayonInt.known(0, input_width)
            y_zero = fn(zero)
            const = y_zero.bits[out_bit_idx] if y_zero.bits[out_bit_idx] is not None else 0

            rhs = tb ^ const  # target = sum(coeffs * x) + const => sum = target ^ const
            equations.append((coeffs, rhs))

        # Try GF(2) solve
        solution = Math.gf2_solve(equations)
        if solution is not None:
            # Build candidate from solution
            sol_bits = [solution.get(i, 0) for i in range(input_width)]
            candidate = RayonInt(bits=sol_bits, width=input_width)
            y_check = fn(candidate)
            if y_check.is_known and target.is_known and y_check.value == target.value:
                return candidate

        # Phase 4: Brute force fallback (for nonlinear functions)
        if target.is_known:
            target_val = target.value
            for v in range(min(max_attempts, 2 ** input_width)):
                candidate = RayonInt.known(v, input_width)
                y = fn(candidate)
                if y.is_known and y.value == target_val:
                    return candidate

        return None

    @staticmethod
    def find_collision(fn, input_width=8, max_attempts=256):
        """
        Find two distinct inputs x1, x2 such that fn(x1) == fn(x2).

        Strategy:
        1. Evaluate fn on many inputs, collect in dictionary
        2. Return first collision found

        Returns: (x1, x2) as RayonInt pair, or None
        """
        seen = {}  # output_value -> input_value
        limit = min(max_attempts, 2 ** input_width)
        for v in range(limit):
            x = RayonInt.known(v, input_width)
            y = fn(x)
            if y.is_known:
                yv = y.value
                if yv in seen:
                    x1 = RayonInt.known(seen[yv], input_width)
                    x2 = x
                    return (x1, x2)
                seen[yv] = v
        return None


# ════════════════════════════════════════════════════════════════
# VERIFICATION / TEST SUITE
# ════════════════════════════════════════════════════════════════

def _reference_sha256_compress_8bit(state_vals, block_vals, rounds):
    """
    Pure-Python reference SHA-256 compression at 8-bit width.
    Uses standard integer arithmetic (mod 256) for comparison.
    """
    # Truncated K to 8-bit
    K8 = [k & 0xFF for k in SHA256_K]
    mask = 0xFF
    width = 8

    def _rotr8(x, n):
        n = n % width
        return ((x >> n) | (x << (width - n))) & mask

    def _shr8(x, n):
        return (x >> n) & mask

    def _sigma0(x):
        return _rotr8(x, 7 % width) ^ _rotr8(x, 18 % width) ^ _shr8(x, 3)

    def _sigma1(x):
        return _rotr8(x, 17 % width) ^ _rotr8(x, 19 % width) ^ _shr8(x, 10 % width)

    def _Sigma0(x):
        return _rotr8(x, 2) ^ _rotr8(x, 13 % width) ^ _rotr8(x, 22 % width)

    def _Sigma1(x):
        return _rotr8(x, 6) ^ _rotr8(x, 11 % width) ^ _rotr8(x, 25 % width)

    def _Ch(e, f, g):
        return (e & f) ^ ((~e & mask) & g)

    def _Maj(a, b, c):
        return (a & b) ^ (a & c) ^ (b & c)

    W = list(block_vals[:16])
    while len(W) < 16:
        W.append(0)
    for i in range(16, rounds):
        W.append((_sigma1(W[i-2]) + W[i-7] + _sigma0(W[i-15]) + W[i-16]) & mask)

    a, b, c, d, e, f, g, h = state_vals[:8]
    for i in range(rounds):
        S1 = _Sigma1(e)
        ch = _Ch(e, f, g)
        temp1 = (h + S1 + ch + K8[i % 64] + W[i]) & mask
        S0 = _Sigma0(a)
        maj = _Maj(a, b, c)
        temp2 = (S0 + maj) & mask
        h = g
        g = f
        f = e
        e = (d + temp1) & mask
        d = c
        c = b
        b = a
        a = (temp1 + temp2) & mask

    return [
        (state_vals[0] + a) & mask,
        (state_vals[1] + b) & mask,
        (state_vals[2] + c) & mask,
        (state_vals[3] + d) & mask,
        (state_vals[4] + e) & mask,
        (state_vals[5] + f) & mask,
        (state_vals[6] + g) & mask,
        (state_vals[7] + h) & mask,
    ]


def verify():
    print("=" * 65)
    print("  STONE 24: STANDARD LIBRARY — crypto, math, solver, io")
    print("=" * 65)
    print()

    passed = 0
    failed = 0

    def check(name, condition):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  [PASS] {name}")
        else:
            failed += 1
            print(f"  [FAIL] {name}")

    # ── IO TESTS ──
    print("IO MODULE")
    print("-" * 50)

    # from_hex known
    words = IO.from_hex("deadbeef", word_width=32)
    check("from_hex('deadbeef') parses to 1 word",
          len(words) == 1)
    check("from_hex('deadbeef') value = 0xDEADBEEF",
          words[0].is_known and words[0].value == 0xDEADBEEF)

    # to_hex roundtrip
    hex_out = IO.to_hex(words)
    check("to_hex roundtrip = 'deadbeef'",
          hex_out == "deadbeef")

    # from_hex 8-bit
    words8 = IO.from_hex("ab", word_width=8)
    check("from_hex('ab', 8-bit) value = 0xAB",
          len(words8) == 1 and words8[0].is_known and words8[0].value == 0xAB)

    # Partial with ?
    words_partial = IO.from_hex("a?", word_width=8)
    check("from_hex('a?') has tension > 0",
          len(words_partial) == 1 and words_partial[0].tension == 4)

    hex_partial = IO.to_hex(words_partial)
    check("to_hex of partial shows '?'",
          '?' in hex_partial)

    # print_tension visual
    print()
    print("  Tension map for [0xAB, partial(0xA?), unknown]:")
    arr_demo = [
        RayonInt.known(0xAB, 8),
        words_partial[0],
        RayonInt.unknown(8),
    ]
    IO.print_tension(arr_demo)
    print()

    # ── MATH TESTS ──
    print("MATH MODULE")
    print("-" * 50)

    # GF(2) solve: x0 XOR x1 = 1, x0 XOR x2 = 0, x1 XOR x2 = 1
    eqs = [
        ([1, 1, 0], 1),  # x0 ^ x1 = 1
        ([1, 0, 1], 0),  # x0 ^ x2 = 0
        ([0, 1, 1], 1),  # x1 ^ x2 = 1
    ]
    sol = Math.gf2_solve(eqs)
    check("gf2_solve: 3-variable XOR system solved",
          sol is not None)
    if sol:
        check("gf2_solve: x0^x1=1",
              sol[0] ^ sol[1] == 1)
        check("gf2_solve: x0^x2=0",
              sol[0] ^ sol[2] == 0)
        check("gf2_solve: x1^x2=1",
              sol[1] ^ sol[2] == 1)

    # Inconsistent system
    eqs_bad = [
        ([1, 0], 0),
        ([1, 0], 1),  # x0=0 AND x0=1 — impossible
    ]
    check("gf2_solve: inconsistent system returns None",
          Math.gf2_solve(eqs_bad) is None)

    # Modular arithmetic (8-bit)
    a8 = RayonInt.known(200, 8)
    b8 = RayonInt.known(100, 8)
    s = Math.mod_add(a8, b8, 8)
    check("mod_add(200, 100, 8) = 44  (300 mod 256)",
          s.is_known and s.value == (300 & 0xFF))

    d = Math.mod_sub(a8, b8, 8)
    check("mod_sub(200, 100, 8) = 100",
          d.is_known and d.value == 100)

    m = Math.mod_mul(RayonInt.known(15, 8), RayonInt.known(17, 8), 8)
    check("mod_mul(15, 17, 8) = 255  (255 mod 256)",
          m.is_known and m.value == (15 * 17) & 0xFF)
    print()

    # ── CRYPTO TESTS ──
    print("CRYPTO MODULE")
    print("-" * 50)

    # SHA-256 compress with 8-bit words, few rounds, known inputs
    width = 8
    rounds = 4  # just a few rounds for speed

    state_vals = [iv & 0xFF for iv in SHA256_IV]
    block_vals = list(range(16))  # simple block: 0,1,2,...,15

    state_rayon = [RayonInt.known(v, width) for v in state_vals]
    block_rayon = [RayonInt.known(v, width) for v in block_vals]

    result = Crypto.sha256_compress(state_rayon, block_rayon,
                                    rounds=rounds, width=width)
    ref = _reference_sha256_compress_8bit(state_vals, block_vals, rounds)

    all_match = True
    for i in range(8):
        rv = result[i].value
        if rv != ref[i]:
            all_match = False
            print(f"    word {i}: rayon={rv}, ref={ref[i]}")

    check(f"sha256_compress (8-bit, {rounds} rounds) matches reference",
          all_match)

    # All outputs should be fully known when inputs are known
    all_known = all(r.is_known for r in result)
    check("sha256_compress: all output words fully known",
          all_known)

    # SHA-256 with partial input: some message words unknown
    block_partial = list(block_rayon)
    block_partial[0] = RayonInt.unknown(width)  # first word unknown
    result_partial = Crypto.sha256_compress(state_rayon, block_partial,
                                            rounds=rounds, width=width)
    has_tension = any(r.tension > 0 for r in result_partial)
    check("sha256_compress with partial input: output has tension",
          has_tension)
    total_tension = sum(r.tension for r in result_partial)
    print(f"    total output tension: {total_tension} bits (from 1 unknown 8-bit input word)")
    print()

    # ── SOLVER TESTS ──
    print("SOLVER MODULE")
    print("-" * 50)

    # find_preimage of XOR function
    def xor_fn(x):
        """f(x) = x XOR 0xAA (8-bit)."""
        return x ^ RayonInt.known(0xAA, 8)

    target = RayonInt.known(0xFF, 8)  # want x ^ 0xAA = 0xFF => x = 0x55
    pre = Solver.find_preimage(xor_fn, target, input_width=8)
    check("find_preimage(x^0xAA, 0xFF) found",
          pre is not None)
    if pre is not None:
        check("find_preimage result = 0x55",
              pre.is_known and pre.value == 0x55)
        y_verify = xor_fn(pre)
        check("f(preimage) == target",
              y_verify.is_known and y_verify.value == 0xFF)

    # find_preimage of AND-based function (nonlinear, uses brute force)
    def and_fn(x):
        """f(x) = (x AND 0x0F) XOR 0x03."""
        return (x & RayonInt.known(0x0F, 8)) ^ RayonInt.known(0x03, 8)

    target2 = RayonInt.known(0x0C, 8)  # want (x & 0x0F) ^ 0x03 = 0x0C => x&0x0F = 0x0F => low nibble = 0x0F
    pre2 = Solver.find_preimage(and_fn, target2, input_width=8)
    check("find_preimage of AND function found",
          pre2 is not None)
    if pre2 is not None:
        y2 = and_fn(pre2)
        check("f(preimage) == target for AND function",
              y2.is_known and y2.value == 0x0C)

    # find_collision of lossy function
    def lossy_fn(x):
        """f(x) = x AND 0xF0 (drops low 4 bits)."""
        return x & RayonInt.known(0xF0, 8)

    collision = Solver.find_collision(lossy_fn, input_width=8)
    check("find_collision of lossy function found",
          collision is not None)
    if collision is not None:
        x1, x2 = collision
        check("collision: x1 != x2",
              x1.value != x2.value)
        check("collision: f(x1) == f(x2)",
              lossy_fn(x1).value == lossy_fn(x2).value)
    print()

    # ── SUMMARY ──
    print("=" * 65)
    print(f"  STONE 24 RESULTS: {passed} passed, {failed} failed")
    print("=" * 65)
    print(f"""
  MODULES:
    Crypto  - sha256_compress with tension (full 64 rounds or reduced)
    Math    - gf2_solve (GF(2) Gaussian elimination), mod_add/sub/mul
    Solver  - find_preimage (algebraic + brute force), find_collision
    IO      - from_hex, to_hex (with ? support), print_tension

  KEY PROPERTIES:
    - Same SHA-256 code works for known AND unknown inputs
    - GF(2) solver handles XOR-linear constraints algebraically
    - Preimage finder: algebraic for linear, brute force for nonlinear
    - Collision finder: dictionary-based birthday attack
    - Hex I/O preserves tension (? nibbles)

  All operations use RayonInt natively. Tension propagates everywhere.
""")
    return failed == 0


if __name__ == '__main__':
    success = verify()
    sys.exit(0 if success else 1)
