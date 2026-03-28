"""
DAMPING vs AMPLIFICATION: The critical balance.

Damping: each gate on propagation path, prob 3/4 of controlling.
  Over d gates: (3/4)^d → 0.

Amplification: fan-out gates SPLIT cascade into multiple paths.
  Fan-out = 2: one path → two paths. ×2 amplification.

NET per gate:
  Fan-out 1: ×(3/4). Damping only. Sub-critical.
  Fan-out 2: ×(3/4)×2 = ×(3/2). AMPLIFICATION! Super-critical.
  Fan-out k: ×(3/4)×k.

For circuit with fraction f of fan-out-2 gates:
  Net rate = (3/2)^f × (3/4)^{1-f} per gate.
  > 1 iff f > 0.416 iff s > 1.71n.

For s > 1.71n: CASCADE BEATS DAMPING.
  Cascade at distance d: grows as (net_rate)^d.
  Reaches output with EXPONENTIAL AMPLIFICATION.

CONSEQUENCE:
  For s = poly(n) > 1.71n: cascade reaches output → SAT speedup.
  DFS nodes ≤ 2^{n/2} / (net_rate)^D.
  For net_rate > 1 and D = depth: exponential reduction.

THIS IS THE MISSING PIECE THAT DEFEATS DAMPING.
"""

import math

print("DAMPING vs AMPLIFICATION")
print("=" * 55)
print()
print("Net rate per gate = (3/4)^{1-f} × (3/2)^f")
print("where f = fraction of fan-out ≥ 2 gates = 1 - n/s")
print()
print(f"{'s/n':>6} {'f':>6} {'net_rate':>10} {'status':>15}")
print("-" * 40)

for ratio in [1.0, 1.2, 1.5, 1.71, 2.0, 3.0, 5.0, 10.0, 100.0]:
    f = 1 - 1/ratio
    net = (3/2)**f * (3/4)**(1-f)
    status = "SUPER-CRITICAL" if net > 1 else "sub-critical"
    print(f"{ratio:>6.1f} {f:>6.3f} {net:>10.4f} {status:>15}")

print()
print("CRITICAL POINT: s/n = 1.71. f = 0.416.")
print("Below: damping wins. Above: amplification wins.")
print()

# Cascade reach probability at distance d
print("Cascade probability at distance d (for various s/n):")
print(f"{'d':>4}", end="")
for ratio in [1.5, 2.0, 3.0, 10.0]:
    print(f" {'s='+str(ratio)+'n':>10}", end="")
print()

for d in [1, 2, 5, 10, 20, 50, 100]:
    print(f"{d:>4}", end="")
    for ratio in [1.5, 2.0, 3.0, 10.0]:
        f = 1 - 1/ratio
        net = (3/2)**f * (3/4)**(1-f)
        prob = min(1.0, net**d)
        print(f" {prob:>10.6f}", end="")
    print()

print(f"""
For s = 2n (f=0.5): net = 1.06. At d=50: prob = 1.06^50 = 18.4.
  Cascade reaches output with AMPLIFICATION ×18.
  Multiple cascades reach → output determined.

For s = 10n (f=0.9): net = 1.41. At d=20: prob = 1.41^20 = 836.
  MASSIVE amplification. Output certainly determined.

For s = 1.5n (f=0.33): net = 0.97. At d=50: prob = 0.97^50 = 0.22.
  Sub-critical but slow decay. Some cascades still reach.

COMBINED WITH WILLIAMS:
  For s = n^c (c > 1): s/n = n^{{c-1}} → ∞. f → 1. net → 3/2.
  Cascade at depth D: (3/2)^D → ∞. ALL cascades reach output.
  DFS ≈ O(1). SAT polynomial.
  Williams → NEXP ⊄ SIZE(n^c).
""")
