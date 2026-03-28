"""
AXIOM VERIFICATION: Test each Rayon axiom against KNOWN truths.

Rule: if axiom disagrees with reality → FIX THE AXIOM.
Not: force reality into axiom.

We test on functions where exact complexity is KNOWN:
  1. Identity (trivial)
  2. AND chain (simple)
  3. XOR chain (simple, different character)
  4. 2-bit → 1-bit functions (exhaustive)
  5. Scaling test: does prediction match measurement?
"""

import numpy as np
import time
import random


def brute_force_preimage(f, target, n_bits, max_tries=None):
    """Find x such that f(x) = target by exhaustive search. Count tries."""
    if max_tries is None:
        max_tries = 2 ** n_bits
    for x in range(min(max_tries, 2 ** n_bits)):
        if f(x) == target:
            return x, x + 1  # found, tries
    return None, max_tries


def brute_force_collision(f, n_bits, max_tries=None):
    """Find x1 ≠ x2 with f(x1) = f(x2). Count tries."""
    seen = {}
    if max_tries is None:
        max_tries = 2 ** n_bits
    for x in range(min(max_tries, 2 ** n_bits)):
        h = f(x)
        if h in seen:
            return (seen[h], x), x + 1
        seen[h] = x
    return None, max_tries


def measure_tension_empirically(f, n_bits_in, n_bits_out, n_samples=10000):
    """
    Measure τ empirically: fraction of input determined after
    fixing half the input bits.

    τ = (1 - determined_fraction) / determined_fraction
    """
    determined = 0
    for _ in range(n_samples):
        # Fix random half of input bits
        x_base = random.randint(0, 2**n_bits_in - 1)
        mask = random.randint(0, 2**n_bits_in - 1)  # which bits to fix
        n_fixed = bin(mask).count('1')
        if n_fixed < n_bits_in // 4 or n_fixed > 3 * n_bits_in // 4:
            continue

        # Check if output is determined
        outputs = set()
        for _ in range(min(50, 2 ** (n_bits_in - n_fixed))):
            free_bits = random.randint(0, 2**n_bits_in - 1)
            x = (x_base & mask) | (free_bits & ~mask)
            outputs.add(f(x) & ((1 << n_bits_out) - 1))
            if len(outputs) > 1:
                break

        if len(outputs) <= 1:
            determined += 1

    rate = determined / n_samples if n_samples > 0 else 0
    if rate > 0.99:
        return 0.01
    if rate < 0.01:
        return 100.0
    return (1 - rate) / rate


print("╔═══════════════════════════════════════════════════════════╗")
print("║  AXIOM VERIFICATION — Testing against known truths       ║")
print("╚═══════════════════════════════════════════════════════════╝")
print()

# ═══════════════════════════════════════════════════════════
# TEST 1: Identity function (should have τ = 0)
# ═══════════════════════════════════════════════════════════
print("TEST 1: IDENTITY f(x) = x")
print("─" * 50)
print("  Expected: τ = 0 (Axiom 1: known → zero tension)")

f_id = lambda x: x
tau_id = measure_tension_empirically(f_id, 8, 8)
print(f"  Measured: τ = {tau_id:.4f}")
print(f"  Axiom 1: {'✓ PASS' if tau_id < 0.1 else '✗ FAIL'}")
print()

# ═══════════════════════════════════════════════════════════
# TEST 2: Constant function (should have τ = 0)
# ═══════════════════════════════════════════════════════════
print("TEST 2: CONSTANT f(x) = 42")
print("─" * 50)
print("  Expected: τ = 0 (output always known)")

f_const = lambda x: 42
tau_const = measure_tension_empirically(f_const, 8, 8)
print(f"  Measured: τ = {tau_const:.4f}")
print(f"  Axiom 1: {'✓ PASS' if tau_const < 0.1 else '✗ FAIL'}")
print()

# ═══════════════════════════════════════════════════════════
# TEST 3: AND chain — increasing difficulty
# ═══════════════════════════════════════════════════════════
print("TEST 3: AND CHAIN — f(x) = x[0] AND x[1] AND ... AND x[n-1]")
print("─" * 50)
print("  Expected: τ grows with n (more bits → harder to determine)")
print("  Axiom 5: τ(A∧B) = τ(A) + τ(B)")
print()

print(f"  {'n':>4} {'τ_measured':>12} {'τ_predicted':>14} {'match':>8}")
print(f"  {'─'*42}")

for n in [2, 4, 6, 8, 10, 12]:
    f_and = lambda x, n=n: 1 if x == (2**n - 1) else 0  # all 1s → 1
    tau_measured = measure_tension_empirically(f_and, n, 1, n_samples=5000)

    # Prediction from Axiom 5: τ(AND of n bits) = n × τ(single bit)
    # Single bit: τ = 1 (balanced, equally likely 0 or 1)
    tau_predicted = n * 1.0  # crude prediction

    match = abs(tau_measured - tau_predicted) / max(tau_predicted, 0.01) < 0.5
    print(f"  {n:>4} {tau_measured:>12.4f} {tau_predicted:>14.4f} {'~' if match else '≠':>8}")

print()

# ═══════════════════════════════════════════════════════════
# TEST 4: XOR chain — different character from AND
# ═══════════════════════════════════════════════════════════
print("TEST 4: XOR CHAIN — f(x) = x[0] XOR x[1] XOR ... XOR x[n-1]")
print("─" * 50)
print("  Expected: τ should be HIGH (XOR has no controlling value)")
print("  Axiom 6: τ(A⊕B) = τ(A) + τ(B)")
print()

print(f"  {'n':>4} {'τ_measured':>12} {'τ_predicted':>14} {'match':>8}")
print(f"  {'─'*42}")

for n in [2, 4, 6, 8, 10, 12]:
    f_xor = lambda x, n=n: bin(x & ((1 << n) - 1)).count('1') % 2
    tau_measured = measure_tension_empirically(f_xor, n, 1, n_samples=5000)
    tau_predicted = n * 1.0  # Axiom 6: same as AND

    match = abs(tau_measured - tau_predicted) / max(tau_predicted, 0.01) < 0.5
    print(f"  {n:>4} {tau_measured:>12.4f} {tau_predicted:>14.4f} {'~' if match else '≠':>8}")

print()

# ═══════════════════════════════════════════════════════════
# TEST 5: Composition — Axiom 3 (multiply)
# ═══════════════════════════════════════════════════════════
print("TEST 5: COMPOSITION — f∘g, does τ multiply?")
print("─" * 50)
print("  Axiom 3: τ(f∘g) = τ(f) × τ(g)")
print()

# f = first 4 bits → AND of them (1 bit)
# g = that bit → replicate 4 times
# f∘g = AND(x[0..3]) replicated
def f_inner(x):
    return 1 if (x & 0xF) == 0xF else 0

def g_inner(x):
    return x & 0xF  # just pass through low 4 bits

def fg_composed(x):
    return f_inner(g_inner(x))

tau_f = measure_tension_empirically(f_inner, 8, 1, n_samples=5000)
tau_g = measure_tension_empirically(g_inner, 8, 4, n_samples=5000)
tau_fg = measure_tension_empirically(fg_composed, 8, 1, n_samples=5000)
tau_predicted = tau_f * tau_g

print(f"  τ(f) = {tau_f:.4f}")
print(f"  τ(g) = {tau_g:.4f}")
print(f"  τ(f∘g) measured = {tau_fg:.4f}")
print(f"  τ(f) × τ(g) predicted = {tau_predicted:.4f}")
print(f"  Axiom 3: {'✓ PASS' if abs(tau_fg - tau_predicted)/max(tau_predicted,0.01) < 0.5 else '✗ FAIL — AXIOM 3 NEEDS REVISION'}")
print()

# ═══════════════════════════════════════════════════════════
# TEST 6: Preimage cost — does τ predict actual difficulty?
# ═══════════════════════════════════════════════════════════
print("TEST 6: PREIMAGE COST — does τ predict actual difficulty?")
print("─" * 50)
print("  For f: {0,1}^n → {0,1}^m:")
print("  Predicted cost = 2^(c×m) where c = τ/(1+τ)")
print()

test_functions = [
    ("AND(4)", 4, 1, lambda x: 1 if (x & 0xF) == 0xF else 0),
    ("OR(4)", 4, 1, lambda x: 1 if (x & 0xF) != 0 else 0),
    ("XOR(4)", 4, 1, lambda x: bin(x & 0xF).count('1') % 2),
    ("low 2 bits", 8, 2, lambda x: x & 3),
    ("low 4 bits", 8, 4, lambda x: x & 0xF),
    ("AND+OR", 8, 1, lambda x: ((x & 0xF) == 0xF) or ((x >> 4) == 0)),
]

print(f"  {'func':>12} {'τ':>8} {'c':>8} {'pred 2^x':>10} {'actual':>8} {'match':>8}")
print(f"  {'─'*58}")

for name, n_in, n_out, func in test_functions:
    tau = measure_tension_empirically(func, n_in, n_out, n_samples=3000)
    c = tau / (1 + tau)
    predicted_cost = 2 ** (c * n_out)

    # Actual: brute force to find preimage of 0
    actual_cost = 0
    for trial in range(100):
        target = random.randint(0, (1 << n_out) - 1)
        _, tries = brute_force_preimage(func, target, n_in, max_tries=2**n_in)
        actual_cost += tries
    actual_cost /= 100

    log_pred = c * n_out
    log_actual = np.log2(actual_cost) if actual_cost > 0 else 0

    match = abs(log_pred - log_actual) < 2
    print(f"  {name:>12} {tau:>8.2f} {c:>8.3f} {log_pred:>9.1f} {log_actual:>7.1f} "
          f"{'✓' if match else '✗':>8}")

print(f"""
═══════════════════════════════════════════════════════════════
AXIOM VERIFICATION SUMMARY:

  Each ✓ = axiom matches reality for this test case.
  Each ✗ = axiom DISAGREES → needs revision.

  Axiom 1 (Stillness): τ(known) = 0           → test identity/constant
  Axiom 3 (Flow): τ(f∘g) = τ(f)·τ(g)         → test composition
  Axiom 5 (Binding): τ(A∧B) = τ(A)+τ(B)      → test AND chain
  Axiom 6 (Entanglement): τ(A⊕B) = τA+τB     → test XOR chain
  Axiom 7 (Equilibrium): c = τ/(1+τ)          → test preimage cost

  Only axioms that PASS all tests survive.
  Failed axioms get REVISED with correct formulas.

  This is the FOUNDATION. No rushing to SHA-256 until every
  axiom stands on verified ground.
═══════════════════════════════════════════════════════════════
""")
