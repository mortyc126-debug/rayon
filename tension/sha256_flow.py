"""
SHA-256 as a FLOW in Rayon Mathematics.

Not 64 rounds of bit manipulation.
A tension flow with 64 stages, each with measurable resistance.
"""

from core import T, Flow, CollisionNavigator, flow, bind, entangle, equilibrium
import math


# SHA-256 round constants → round tensions
# τ_r = P(carry=1) / P(carry=0) from Carry-Web Theory
# σ/T = 0.568 (universal constant)

K256 = [
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

SIGMA = 0.568  # Universal carry-web constant

def round_tension(r):
    """Tension of SHA-256 round r from Carry-Web Theory."""
    from scipy.stats import norm
    k_norm = K256[r] / (2**32)
    mu = 2.0 + k_norm
    z = (1.0 - mu) / SIGMA
    p0 = norm.cdf(z)  # P(carry=0)
    p1 = 1.0 - p0     # P(carry=1)
    if p0 < 1e-10:
        return 1000.0  # effectively infinite (always carries)
    return p1 / p0


def build_sha256_flow():
    """Construct SHA-256 as a tension flow."""
    sha = Flow('SHA-256', dim_in=512, dim_out=256)

    for r in range(64):
        tau_r = round_tension(r)
        sha.add_stage(f'round_{r}', tau_r)

    return sha


def build_reduced_sha(n_rounds):
    """SHA-256 reduced to n rounds."""
    sha = Flow(f'SHA-{n_rounds}', dim_in=512, dim_out=256)
    for r in range(n_rounds):
        sha.add_stage(f'round_{r}', round_tension(r))
    return sha


if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  SHA-256 AS RAYON FLOW                                   ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Full SHA-256
    sha = build_sha256_flow()
    print(f"  {sha}")
    print(f"  Inverse: τ⁻¹ = {sha.tau_inverse:.2e}")
    print(f"  c_inverse = {sha.c_inverse:.6f}")
    print()

    # Collision analysis
    nav = CollisionNavigator(sha)
    nav.report()

    # Reduced SHA-256 at various round counts
    print("\n  REDUCED SHA-256: How tension grows with rounds")
    print(f"  {'rounds':>8} {'τ':>12} {'c':>8} {'τ⁻¹':>12} {'collision 2^x':>14}")
    print(f"  {'─'*58}")

    for n_rounds in [1, 2, 4, 8, 16, 24, 32, 48, 64]:
        sha_r = build_reduced_sha(n_rounds)
        nav_r = CollisionNavigator(sha_r)
        col_tau = nav_r.estimate_collision_tension()
        log_col = math.log2(col_tau) if col_tau > 0 and col_tau < float('inf') else 999

        print(f"  {n_rounds:>8} {sha_r.tau:>12.2e} {sha_r.c:>8.6f} "
              f"{sha_r.tau_inverse:>12.2e} {log_col:>13.1f}")

    # Weakest points
    print(f"\n  WEAKEST STAGES (lowest tension = easiest to attack):")
    tensions = [(f'round_{r}', round_tension(r)) for r in range(64)]
    tensions.sort(key=lambda x: x[1])
    for name, tau in tensions[:10]:
        print(f"    {name}: τ = {tau:.2f} (c = {equilibrium(tau):.4f})")

    print(f"""
═══════════════════════════════════════════════════════════════
RAYON ANALYSIS OF SHA-256:

  Forward:  τ = {sha.tau:.2e} → c = {sha.c:.6f} (fully dark)
  Inverse:  τ⁻¹ = {sha.tau_inverse:.2e} → c⁻¹ = {sha.c_inverse:.6f}

  The Rayon Inverse τ⁻¹ = τ^(256/512) = √τ.
  This is FINITE — inversion has measurable tension.

  Weakest rounds: those with smallest K[r] (smallest τ_r).
  These are the points where tension flow is thinnest.

  In Rayon Mathematics: SHA-256 is not a "black box."
  It's a flow with 64 measured resistances.
  The total resistance determines the cost of any operation.
═══════════════════════════════════════════════════════════════
""")
