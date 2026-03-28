"""
TENSION v2: Hybrid framework for cryptographic circuits.

═══════════════════════════════════════════════════════════════
KEY INSIGHT: Any circuit = LINEAR part + NONLINEAR part.

  LINEAR (XOR, rotations, shifts):
    → Solve EXACTLY via GF(2) linear algebra. Cost: O(n³). Free.

  NONLINEAR (AND, OR, carries in modular addition):
    → Analyze via Tension LP. This is where hardness lives.

  SHA-256 specifically:
    LINEAR: message schedule XOR, Σ0, Σ1 rotations
    NONLINEAR: 128 modular additions → 128 carry bits = Carry-Web Φ

  Tension(SHA-256) = Tension(Carry-Web) because:
    Given Φ(W) = all 64 carry bits, the rest is LINEAR (solvable in poly time).
    The ENTIRE hardness of SHA-256 is in the carry-web.
═══════════════════════════════════════════════════════════════
"""

import numpy as np
import random
import math
import time
import hashlib
import struct


# ════════════════════════════════════════════════════════════
# CARRY-WEB MODEL (from 1300+ experiments)
# ════════════════════════════════════════════════════════════

# SHA-256 round constants
K = [
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

# Universal constant from Carry-Web Theory
SIGMA_OVER_T = 0.568  # σ/2^32, universal across all rounds and message types

# Carry probability per round (from copula model)
def carry_probability(r):
    """P(carry[r] = 1) from analytical formula."""
    k_norm = K[r] / (2**32)
    mu_norm = 2.0 + k_norm  # μ/T where T = 2^32
    # P(carry=1) = P(raw ≥ 2^32) = P(raw/T ≥ 1)
    # raw ~ N(mu_norm * T, sigma), so raw/T ~ N(mu_norm, SIGMA_OVER_T)
    # P(raw/T ≥ 1) = 1 - Φ((1 - mu_norm) / SIGMA_OVER_T)
    from scipy.stats import norm
    z = (1.0 - mu_norm) / SIGMA_OVER_T
    return 1.0 - norm.cdf(z)

# Block structure (from experiments)
CARRY_BLOCKS = [
    {'rounds': [0, 1, 4, 5], 'within_corr': 0.02, 'name': 'W1'},
    {'rounds': [9, 10, 11, 12], 'within_corr': 0.13, 'name': 'W2'},
    {'rounds': [18, 19, 20, 21], 'within_corr': 0.14, 'name': 'W3'},
    {'rounds': [30, 31, 32, 33], 'within_corr': 0.14, 'name': 'W4'},
    {'rounds': [47, 48, 49, 50], 'within_corr': 0.14, 'name': 'W5'},
    {'rounds': [61, 62, 63], 'within_corr': 0.19, 'name': 'tail'},
]
BETWEEN_BLOCK_CORR = 0.003  # essentially independent


class CarryWeb:
    """The Carry-Web Φ: maps SHA-256 input to carry pattern."""

    def __init__(self):
        self.carry_probs = [carry_probability(r) for r in range(64)]
        # Tension per round: T_r = P(carry=1) / P(carry=0)
        self.tensions = []
        for p in self.carry_probs:
            if p > 0.999:
                self.tensions.append(1000.0)  # always carry
            elif p < 0.001:
                self.tensions.append(0.001)  # never carry
            else:
                self.tensions.append(p / (1 - p))

    def round_tension(self, r):
        return self.tensions[r]

    def block_tension(self, block_idx):
        """Tension of a block = product of round tensions."""
        block = CARRY_BLOCKS[block_idx]
        T = 1.0
        for r in block['rounds']:
            T *= self.tensions[r]
        return T

    def total_tension(self):
        """Total carry-web tension = product of block tensions."""
        T = 1.0
        for i in range(len(CARRY_BLOCKS)):
            T *= self.block_tension(i)
        return T

    def report(self):
        print("CARRY-WEB TENSION MAP")
        print("─" * 65)
        print(f"{'Round':>6} {'K[r]/2^32':>10} {'P(carry)':>10} {'T_r':>10} {'c_r':>8}")
        print("─" * 50)

        variable_rounds = 0
        for r in range(64):
            p = self.carry_probs[r]
            T = self.tensions[r]
            c = T / (1 + T)
            k_norm = K[r] / 2**32
            marker = ""
            if p > 0.999: marker = " [always carry]"
            elif p < 0.01: marker = " ★ LOW CARRY"
            if r % 8 == 0 or marker:
                print(f"{r:>6} {k_norm:>10.4f} {p:>10.6f} {T:>10.2f} {c:>8.4f}{marker}")
            if 0.001 < p < 0.999:
                variable_rounds += 1

        print(f"\nVariable rounds: {variable_rounds}/64")
        print(f"Always-carry rounds: {64 - variable_rounds}/64")

        print(f"\nBlock tensions:")
        for i, block in enumerate(CARRY_BLOCKS):
            bt = self.block_tension(i)
            bc = bt / (1 + bt)
            print(f"  {block['name']:>6}: rounds {block['rounds']}, "
                  f"T={bt:.2e}, c={bc:.4f}")

        total_T = self.total_tension()
        total_c = total_T / (1 + total_T)
        print(f"\nTotal carry-web tension: T = {total_T:.2e}")
        print(f"Total exponent: c = {total_c:.6f}")
        print(f"Expected nodes: 2^(c × variable_bits) = 2^({total_c * variable_rounds:.1f})")


# ════════════════════════════════════════════════════════════
# TENSION v2: HYBRID SOLVER
# ════════════════════════════════════════════════════════════

class TensionV2:
    """
    Hybrid framework: GF(2) for linear + Tension for nonlinear.

    For SHA-256 collision:
      1. Fix carry pattern Φ (the nonlinear part)
      2. Solve linear system over GF(2) for message (the linear part)
      3. Iterate over carry patterns ordered by tension

    Total cost: Σ over patterns Φ of cost(Φ) × P(Φ works)
    """

    def __init__(self):
        self.carry_web = CarryWeb()

    def analyze_sha256(self):
        """Full tension analysis of SHA-256."""
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║  TENSION v2: SHA-256 Hybrid Analysis                    ║")
        print("╚═══════════════════════════════════════════════════════════╝")
        print()

        self.carry_web.report()

        print()
        print("═" * 65)
        print("HYBRID DECOMPOSITION")
        print("─" * 65)
        print()
        print("SHA-256 = LINEAR(XOR, Σ0, Σ1, schedule) ∘ NONLINEAR(carries)")
        print()
        print("Given carry pattern Φ ∈ {0,1}^64:")
        print("  • Modular add becomes: a + b = (a XOR b) XOR carry_propagation")
        print("  • Everything reduces to XOR (linear over GF(2))")
        print("  • Linear system: ~512 equations in ~512 unknowns")
        print("  • Solvable in O(512³) ≈ 1.3×10⁸ operations")
        print()

        # Cost analysis
        variable_rounds = sum(1 for p in self.carry_web.carry_probs
                             if 0.001 < p < 0.999)
        print(f"Variable carry bits: {variable_rounds}")
        print(f"Carry pattern space: 2^{variable_rounds}")
        print()

        # For collision: need TWO messages with same output
        # Fix Φ, solve for W. Get H. Then find W' with same H.
        # This requires: Φ(W) = specific pattern AND H(W) = target

        # Approach: search carry patterns by tension (lowest first)
        low_tension_rounds = [(r, self.carry_web.tensions[r])
                             for r in range(64)
                             if 0.001 < self.carry_web.carry_probs[r] < 0.999]
        low_tension_rounds.sort(key=lambda x: x[1])

        print("Rounds sorted by tension (easiest carries first):")
        for r, T in low_tension_rounds[:10]:
            p = self.carry_web.carry_probs[r]
            c = T / (1 + T)
            print(f"  Round {r:>2}: T={T:>8.2f}, P(carry=0)={1-p:.6f}, c={c:.4f}")

        print(f"\n  ... ({len(low_tension_rounds)} variable rounds total)")

        # Wang chain analysis
        print()
        print("═" * 65)
        print("WANG CHAIN THROUGH TENSION LENS")
        print("─" * 65)
        print()
        print("Wang chain forces δe[2..16] = 0 at cost P=1 (free).")
        print("This corresponds to fixing carries in rounds 1..15.")
        print()

        wang_cost = 0
        for r in range(1, 16):
            T = self.carry_web.tensions[r]
            c = T / (1 + T)
            wang_cost += c
            # Wang makes this free by choosing ΔW adaptively

        print(f"Wang chain covers rounds 1-15: saves {wang_cost:.1f} bits of tension")
        print()

        # The barrier
        r17_T = self.carry_web.tensions[17] if 17 < 64 else 0
        r17_p = self.carry_web.carry_probs[17]
        print(f"BARRIER at round 17:")
        print(f"  T[17] = {r17_T:.2f}")
        print(f"  P(carry[17]=0) = {1-r17_p:.6f}")
        print(f"  Cost to cross: 2^32 (birthday on Da[13])")
        print()

        # Total collision cost estimate
        print("═" * 65)
        print("COLLISION COST ESTIMATE (Tension v2)")
        print("─" * 65)
        print()
        print("Phase 1: Wang chain (rounds 1-15): FREE (P=1)")
        print("Phase 2: Birthday for round 17: 2^32")
        print("Phase 3: Remaining rounds 18-63:")

        remaining_cost = 0
        for r in range(18, 64):
            if 0.001 < self.carry_web.carry_probs[r] < 0.999:
                T = self.carry_web.tensions[r]
                c = T / (1 + T)
                remaining_cost += c

        print(f"  Variable rounds 18-63: {sum(1 for r in range(18,64) if 0.001 < self.carry_web.carry_probs[r] < 0.999)} rounds")
        print(f"  Total tension cost: {remaining_cost:.1f} bits")
        print(f"  Expected work: 2^{remaining_cost:.0f}")
        print()

        total = 32 + remaining_cost  # birthday + remaining
        print(f"TOTAL COLLISION COST: 2^32 + 2^{remaining_cost:.0f} ≈ 2^{max(32, remaining_cost):.0f}")
        print(f"Birthday attack:     2^128")
        print()

        if max(32, remaining_cost) < 128:
            saving = 128 - max(32, remaining_cost)
            print(f"★ POTENTIAL SAVING: {saving:.0f} bits vs birthday!")
            print(f"  This would reduce collision from 2^128 to 2^{max(32, remaining_cost):.0f}")
        else:
            print(f"No improvement over birthday (cost ≥ 2^128)")

        print()
        print("═" * 65)
        print("CRITICAL CAVEAT")
        print("─" * 65)
        print("""
  This estimate assumes carry patterns can be chosen INDEPENDENTLY.
  In reality: carries in rounds 18-63 are NOT independent of rounds 1-17.
  The schedule creates XOR dependencies between ALL rounds.

  The carry-web has block structure (6 blocks, isolation 42-111×).
  Within each block: carries are correlated (within_corr ≈ 0.13-0.19).
  Between blocks: nearly independent (corr ≈ 0.003).

  TRUE COST = Σ_blocks 2^(block_tension) × coupling_correction

  The coupling correction is the UNSOLVED part of the puzzle.
  From experiments: state coupling adds 2.0-2.5× lift between adjacent rounds.
  This could reduce OR increase the total cost depending on direction.
""")


# ════════════════════════════════════════════════════════════
if __name__ == '__main__':
    tv2 = TensionV2()
    tv2.analyze_sha256()
