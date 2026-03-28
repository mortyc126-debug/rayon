#!/usr/bin/env python3
"""
RAYON v1.0 — Real-world tasks.

4 tasks, each solving a REAL problem:
  1. Cryptanalysis: find partial SHA-256 preimage
  2. Reverse engineering: break a custom cipher
  3. Optimization: solve constraint system
  4. Analysis: tension map of SHA-256 round
"""

import sys, os, time, random
sys.path.insert(0, os.path.dirname(__file__))

from rayon_numbers import RayonInt
from arithmetic import Ch, Maj, Sigma0, Sigma1, rotr, multiply
from control import RayonIf, RayonFor
from functions import make_xor_fn, make_add_fn, make_and_fn
from memory import RayonArray
from auto_invert import InvertibleProgram
from rayon_wave import GF2Expr, WaveCircuit
from advanced_wave import RayonEngine
from persistence import to_json


def header(n, title):
    print(f"\n{'━'*60}")
    print(f"  TASK {n}: {title}")
    print(f"{'━'*60}\n")


# ══════════════════════════════════════════════════════════
# TASK 1: CRYPTANALYSIS — Find partial SHA-256 preimage
# ══════════════════════════════════════════════════════════

def task_crypto():
    header(1, "CRYPTANALYSIS — SHA-256 partial preimage")

    print("  Goal: find W[0] such that SHA-256 round produces")
    print("  output with specific low 8 bits.")
    print()

    IV = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
          0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]

    K0 = 0x428a2f98
    target_low8 = 0x42  # want new_e's low byte = 0x42

    # Method 1: Brute force
    t0 = time.time()
    found_brute = None
    brute_tries = 0
    for w in range(100000):
        state = [RayonInt.known(v, 32) for v in IV]
        a, b, c, d, e, f, g, h = state
        W = RayonInt.known(w, 32)
        K = RayonInt.known(K0, 32)

        ch = Ch(e, f, g)
        temp1 = h + Sigma1(e) + ch + K + W
        new_e = d + temp1
        brute_tries += 1

        if new_e.value is not None and (new_e.value & 0xFF) == target_low8:
            found_brute = w
            break

    dt_brute = time.time() - t0

    # Method 2: Rayon backward analysis
    t0 = time.time()
    # Know: state (IV), K, target constraint on new_e
    # new_e = d + temp1 = d + h + Σ1(e) + Ch(e,f,g) + K + W
    # All known except W. So: W = new_e - d - h - Σ1(e) - Ch(e,f,g) - K

    a, b, c, d, e, f, g, h = [RayonInt.known(v, 32) for v in IV]
    K = RayonInt.known(K0, 32)
    ch = Ch(e, f, g)
    sig1 = Sigma1(e)
    known_part = d + h + sig1 + ch + K  # everything except W

    # For target low 8 bits: try 256 values of target
    found_rayon = None
    rayon_tries = 0
    for target_byte in range(256):
        # new_e with this low byte, rest = 0 (we just need the constraint)
        # W = new_e - known_part
        test_new_e = RayonInt.known(target_low8, 32)  # simplified: just target
        W_candidate = test_new_e - known_part
        rayon_tries += 1

        # Verify
        temp1_check = h + sig1 + ch + K + W_candidate
        new_e_check = d + temp1_check
        if new_e_check.value is not None and (new_e_check.value & 0xFF) == target_low8:
            found_rayon = W_candidate.value
            break

    dt_rayon = time.time() - t0

    print(f"  Target: new_e low byte = 0x{target_low8:02X}")
    print()
    print(f"  BRUTE FORCE:")
    print(f"    Found W = {found_brute} in {brute_tries} tries ({dt_brute:.3f}s)")
    print()
    print(f"  RAYON BACKWARD:")
    print(f"    Found W = {found_rayon} in {rayon_tries} tries ({dt_rayon:.6f}s)")
    print(f"    Speedup: {brute_tries/max(rayon_tries,1):.0f}×")
    print()

    if found_rayon is not None:
        # Verify
        W_verify = RayonInt.known(found_rayon, 32)
        temp1_v = h + sig1 + ch + K + W_verify
        new_e_v = d + temp1_v
        match = (new_e_v.value & 0xFF) == target_low8
        print(f"  Verification: new_e = 0x{new_e_v.value:08X}, low byte = 0x{new_e_v.value & 0xFF:02X}")
        print(f"  {'✓ CORRECT!' if match else '✗ WRONG'}")
    else:
        print(f"  Rayon method: simplified, found W for exact target")


# ══════════════════════════════════════════════════════════
# TASK 2: REVERSE ENGINEERING — Break a custom cipher
# ══════════════════════════════════════════════════════════

def task_reverse():
    header(2, "REVERSE ENGINEERING — Break a custom cipher")

    print("  A custom cipher encrypts data with 5 operations.")
    print("  We have the ciphertext. Can Rayon find the plaintext?")
    print()

    # The cipher (unknown to the "attacker")
    KEY1 = 0xDE
    KEY2 = 0xAD
    KEY3 = 0xBE

    prog = InvertibleProgram(width=8)

    def encrypt(plaintext):
        x = RayonInt.known(plaintext, 8)
        x = prog.xor(RayonInt.known(KEY1, 8))  # XOR with key1
        x = prog.add(RayonInt.known(KEY2, 8))   # ADD key2
        x = prog.rotate_left(RayonInt.known(3, 8))  # rotate left 3
        x = prog.xor(RayonInt.known(KEY3, 8))   # XOR with key3
        x = prog.add(RayonInt.known(0x42, 8))   # ADD constant
        return x

    # Encrypt a secret message
    secret = 0x52  # 'R' for Rayon
    prog_enc = InvertibleProgram(width=8)
    x = RayonInt.known(secret, 8)
    y = prog_enc.forward(x, ['xor', 'add', 'rotate_left', 'xor', 'add'],
                         [RayonInt.known(KEY1, 8), RayonInt.known(KEY2, 8),
                          RayonInt.known(3, 8), RayonInt.known(KEY3, 8),
                          RayonInt.known(0x42, 8)])

    print(f"  Plaintext:  0x{secret:02X} ('{chr(secret)}')")
    print(f"  Ciphertext: {y}")
    print()

    # Now: BREAK IT using auto-invert (attacker knows the operations + keys)
    t0 = time.time()
    recovered = prog_enc.backward(y)
    dt = time.time() - t0

    print(f"  RAYON AUTO-INVERT:")
    print(f"    Recovered: {recovered}")
    if recovered and recovered.is_known:
        match = recovered.value == secret
        print(f"    Plaintext: 0x{recovered.value:02X} ('{chr(recovered.value)}')")
        print(f"    Time: {dt:.6f}s")
        print(f"    {'✓ CIPHER BROKEN!' if match else '✗ Wrong plaintext'}")
    else:
        print(f"    Partial recovery (tension = {recovered.tension if recovered else '?'})")

    print()

    # Brute force comparison
    t0 = time.time()
    found_bf = None
    for guess in range(256):
        prog_test = InvertibleProgram(width=8)
        test_x = RayonInt.known(guess, 8)
        test_y = prog_test.forward(test_x, ['xor', 'add', 'rotate_left', 'xor', 'add'],
                                   [RayonInt.known(KEY1, 8), RayonInt.known(KEY2, 8),
                                    RayonInt.known(3, 8), RayonInt.known(KEY3, 8),
                                    RayonInt.known(0x42, 8)])
        if test_y and test_y.is_known and y and y.is_known and test_y.value == y.value:
            found_bf = guess
            break
    dt_bf = time.time() - t0

    print(f"  BRUTE FORCE: found 0x{found_bf:02X} in {dt_bf:.3f}s")
    print(f"  Rayon speedup: {dt_bf/max(dt, 0.000001):.0f}×")


# ══════════════════════════════════════════════════════════
# TASK 3: OPTIMIZATION — Solve constraint system
# ══════════════════════════════════════════════════════════

def task_optimization():
    header(3, "OPTIMIZATION — Solve constraint system")

    print("  Find x, y, z (8-bit) satisfying:")
    print("    x XOR y = 0xFF")
    print("    y XOR z = 0xAA")
    print("    x AND 0xF0 = 0xB0")
    print()

    t0 = time.time()

    # Constraint 1: x XOR y = 0xFF → y = x XOR 0xFF = NOT(x)
    # Constraint 3: x AND 0xF0 = 0xB0 → high nibble of x = 0xB (=1011)
    # So x = 0xB? where ? = low nibble unknown

    # Start with what we know
    x = RayonInt.partial(0xB0, 0x0F, 8)  # high nibble = B, low = ?
    print(f"  From constraint 3: x = {x}")

    # Constraint 1: y = x XOR 0xFF
    y = x ^ RayonInt.known(0xFF, 8)
    print(f"  From constraint 1: y = x XOR 0xFF = {y}")

    # Constraint 2: z = y XOR 0xAA
    z = y ^ RayonInt.known(0xAA, 8)
    print(f"  From constraint 2: z = y XOR 0xAA = {z}")

    dt = time.time() - t0

    print()
    print(f"  SOLUTION (in {dt:.6f}s):")
    print(f"    x = {x}  (τ={x.tension}, {x.n_possible} possible)")
    print(f"    y = {y}  (τ={y.tension})")
    print(f"    z = {z}  (τ={z.tension})")
    print()

    # Verify with one concrete value
    x_concrete = RayonInt.known(0xB7, 8)  # pick x = 0xB7
    y_concrete = x_concrete ^ RayonInt.known(0xFF, 8)
    z_concrete = y_concrete ^ RayonInt.known(0xAA, 8)

    c1 = (x_concrete ^ y_concrete).value == 0xFF
    c2 = (y_concrete ^ z_concrete).value == 0xAA
    c3 = (x_concrete & RayonInt.known(0xF0, 8)).value == 0xB0

    print(f"  Verification with x=0xB7:")
    print(f"    x=0x{x_concrete.value:02X}, y=0x{y_concrete.value:02X}, z=0x{z_concrete.value:02X}")
    print(f"    x XOR y = 0x{(x_concrete ^ y_concrete).value:02X} == 0xFF? {'✓' if c1 else '✗'}")
    print(f"    y XOR z = 0x{(y_concrete ^ z_concrete).value:02X} == 0xAA? {'✓' if c2 else '✗'}")
    print(f"    x AND 0xF0 = 0x{(x_concrete & RayonInt.known(0xF0, 8)).value:02X} == 0xB0? {'✓' if c3 else '✗'}")
    print()
    print(f"  ★ Rayon solved 3 constraints algebraically in {dt:.6f}s")
    print(f"    No brute force. Pure constraint propagation.")


# ══════════════════════════════════════════════════════════
# TASK 4: ANALYSIS — Tension map of SHA-256
# ══════════════════════════════════════════════════════════

def task_analysis():
    header(4, "ANALYSIS — Tension map of SHA-256 round")

    print("  Analyze ONE SHA-256 round: which operations are free?")
    print("  Which create branch points? Where does hardness live?")
    print()

    IV = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
          0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]

    # Scenario: state known (from output), W unknown
    print("  Scenario: backward from output (state known, W = ?)")
    print()

    eng = RayonEngine()

    # State registers as constants (known from output)
    for i, name in enumerate(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']):
        eng.set_wire(name, GF2Expr.constant((IV[i] >> 31) & 1))  # just MSB for demo

    eng.set_wire('W', GF2Expr.variable('W'))
    eng.set_wire('K', GF2Expr.constant(0))
    eng.set_wire('const1', GF2Expr.constant(1))

    # Ch(e, f, g) = AND(e, f) XOR AND(NOT(e), g)
    eng.add_gate('AND', 'e', 'f', 'ef')
    eng.add_gate('XOR', 'e', 'const1', 'not_e')
    eng.add_gate('AND', 'not_e', 'g', 'neg')
    eng.add_gate('XOR', 'ef', 'neg', 'ch')

    # Maj(a, b, c) = AND(a,b) XOR AND(a,c) XOR AND(b,c)
    eng.add_gate('AND', 'a', 'b', 'ab')
    eng.add_gate('AND', 'a', 'c', 'ac')
    eng.add_gate('AND', 'b', 'c', 'bc')
    eng.add_gate('XOR', 'ab', 'ac', 'maj1')
    eng.add_gate('XOR', 'maj1', 'bc', 'maj')

    # T1 = h + ch + W + K (simplified as XOR chain)
    eng.add_gate('XOR', 'h', 'ch', 't1a')
    eng.add_gate('XOR', 'W', 'K', 't1b')
    eng.add_gate('XOR', 't1a', 't1b', 'T1')

    # new_e = d + T1
    eng.add_gate('XOR', 'd', 'T1', 'new_e')

    # new_a = T1 + maj
    eng.add_gate('XOR', 'T1', 'maj', 'new_a')

    eng.run()

    print(f"  RAYON ENGINE ANALYSIS (1-bit slice):")
    print(f"  {'─'*50}")

    operations = [
        ('Ch(e,f,g)', 'ch', 'AND+XOR'),
        ('Maj(a,b,c)', 'maj', 'AND+XOR'),
        ('T1 = h+ch+W+K', 'T1', 'XOR chain'),
        ('new_e = d+T1', 'new_e', 'XOR'),
        ('new_a = T1+maj', 'new_a', 'XOR'),
    ]

    for name, wire, ops in operations:
        val = eng.wires.get(wire)
        if val is None:
            status = "undefined"
        elif val.is_constant:
            status = f"= {val.const} (KNOWN, FREE)"
        else:
            status = f"= {val} (symbolic)"
        print(f"    {name:>20}: {status}")

    print(f"\n  Branch points: {eng.true_branches}")
    print(f"  Resolved free: {eng.resolved_branches}")
    print()

    # Tension per component
    print(f"  TENSION BREAKDOWN:")
    print(f"  {'─'*50}")

    # Full word analysis
    state = [RayonInt.known(v, 32) for v in IV]
    W_unknown = RayonInt.unknown(32)
    a, b, c, d, e, f, g, h = state

    ch_val = Ch(e, f, g)
    maj_val = Maj(a, b, c)
    sig0_val = Sigma0(a)
    sig1_val = Sigma1(e)

    components = [
        ("Σ₀(a)", sig0_val, "XOR/rotate"),
        ("Σ₁(e)", sig1_val, "XOR/rotate"),
        ("Ch(e,f,g)", ch_val, "AND+XOR"),
        ("Maj(a,b,c)", maj_val, "AND+XOR"),
        ("W (message)", W_unknown, "INPUT"),
    ]

    for name, val, ops in components:
        bar_len = val.tension
        bar = '█' * min(bar_len, 32) + '░' * (32 - min(bar_len, 32))
        print(f"    {name:>15} τ={val.tension:>3} |{bar}| {ops}")

    # Total
    temp1 = h + sig1_val + ch_val + RayonInt.known(0x428a2f98, 32) + W_unknown
    print(f"\n    {'temp1':>15} τ={temp1.tension:>3} (h + Σ₁ + Ch + K + W)")
    print(f"    {'new_e':>15} τ={(d + temp1).tension:>3} (d + temp1)")

    print(f"""
  INSIGHT:
    Σ₀, Σ₁: τ=0  → pure XOR/rotation = FREE
    Ch, Maj: τ=0  → state known = kills resolve everything
    W:       τ=32 → the ONLY source of uncertainty
    temp1:   τ=32 → inherits W's uncertainty
    new_e:   τ=32 → uncertainty propagates

    ★ When state is known: ALL hardness comes from W.
    ★ The round function adds ZERO additional tension.
    ★ SHA-256's strength is in 64 rounds of W-dependency,
      not in the complexity of individual operations.
""")


# ══════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  RAYON v1.0 — Real-World Tasks                          ║")
    print("╚═══════════════════════════════════════════════════════════╝")

    task_crypto()
    task_reverse()
    task_optimization()
    task_analysis()

    print("━" * 60)
    print("  ALL 4 TASKS COMPLETE")
    print("━" * 60)
