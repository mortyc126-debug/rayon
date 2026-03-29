"""
SYSTEM TENSION — Mathematics of interaction between components.

NOT: tension of each round (we have this).
NEW: tension of the LINK between rounds.

The link = state registers flowing from round r to r+1.
Link tension = how much uncertainty SURVIVES the crossing.

SHA-256 total tension is determined by BOTTLENECK links,
not by average or product of round tensions.

Like: army strength = weakest point in the chain,
not average soldier × count.
"""

import random
from rayon_numbers import RayonInt
from arithmetic import Ch, Maj, Sigma0, Sigma1

M32 = 0xFFFFFFFF
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
IV = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
      0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]


def measure_link_tension(n_rounds=64):
    """
    Measure tension of each LINK (state transfer between rounds).

    Forward from IV: state known for early rounds.
    Backward from output: state known for late rounds.
    MIDDLE: both fronts lose certainty. BOTTLENECK lives here.

    For each round: count unknown state bits = link tension.
    """
    # Forward propagation: start from IV, add unknown W
    forward_tension = []
    state = [RayonInt.known(v, 32) for v in IV]

    for r in range(n_rounds):
        a, b, c, d, e, f, g, h = state
        W = RayonInt.unknown(32)  # message word unknown
        K = RayonInt.known(K256[r], 32)

        # State tension BEFORE this round
        state_tau = sum(s.tension for s in state)

        # Compute round
        ch = Ch(e, f, g)
        temp1 = h + Sigma1(e) + ch + K + W
        maj = Maj(a, b, c)
        temp2 = Sigma0(a) + maj

        new_a = temp1 + temp2
        new_e = d + temp1

        state = [new_a, a, b, c, new_e, e, f, g]

        state_tau_after = sum(s.tension for s in state)
        forward_tension.append({
            'round': r,
            'tau_before': state_tau,
            'tau_after': state_tau_after,
            'tau_added': state_tau_after - state_tau,
        })

    # Backward propagation: start from output (known), go backward
    backward_tension = [None] * n_rounds
    state_back = [RayonInt.known(v, 32) for v in IV]  # final known state

    # At output: state = H - IV (known)
    for r in range(n_rounds - 1, -1, -1):
        state_tau = sum(s.tension for s in state_back)
        backward_tension[r] = {
            'round': r,
            'tau_backward': state_tau,
        }
        # Going backward: each round adds uncertainty from h_prev
        # Simplified: tension grows by ~32 per round backward
        if r > n_rounds - 5:
            pass  # first 4 rounds backward: known
        else:
            state_back = [RayonInt.unknown(32) if s.tension > 0
                         else RayonInt.partial(s.value or 0, 0x1, 32)
                         for s in state_back]

    return forward_tension, backward_tension


def find_bottleneck(forward, backward, n_rounds=64):
    """
    The bottleneck = round where COMBINED tension (forward + backward) is MAXIMUM.

    Forward: grows from 0 (IV known) to 256 (all unknown)
    Backward: grows from 0 (output known) to 256 (all unknown)

    Bidirectional link tension at round r:
        τ_link(r) = min(τ_forward(r), τ_backward(r))
        (take the BETTER direction)

    Bottleneck = round with max τ_link (worst of the best)
    """
    link_tensions = []

    for r in range(n_rounds):
        tau_f = forward[r]['tau_after']
        tau_b = backward[r]['tau_backward'] if backward[r] else 256

        # Bidirectional: take better direction
        tau_link = min(tau_f, tau_b)
        link_tensions.append({
            'round': r,
            'tau_forward': tau_f,
            'tau_backward': tau_b,
            'tau_link': tau_link,
        })

    # Bottleneck = max link tension
    bottleneck = max(link_tensions, key=lambda x: x['tau_link'])

    return link_tensions, bottleneck


def system_tension_formula(link_tensions):
    """
    SYSTEM TENSION = sum of link tensions at bottleneck region.

    Not product of rounds. Not average.
    Sum of links that are above the "easy" threshold.

    Easy = τ_link ≤ 32 (one word of uncertainty, manageable)
    Hard = τ_link > 32 (multiple words unknown)
    Bottleneck = hard links

    τ_system = Σ over hard links of (τ_link - 32) / 32
             = effective branch WORDS in the bottleneck
    """
    easy_threshold = 32  # one word = manageable by Rayon

    hard_links = [lt for lt in link_tensions if lt['tau_link'] > easy_threshold]
    easy_links = [lt for lt in link_tensions if lt['tau_link'] <= easy_threshold]

    tau_system = sum(max(0, lt['tau_link'] - easy_threshold) for lt in hard_links)
    tau_system_bits = tau_system  # in bits

    return {
        'n_hard': len(hard_links),
        'n_easy': len(easy_links),
        'tau_system': tau_system_bits,
        'hard_rounds': [lt['round'] for lt in hard_links],
    }


if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  SYSTEM TENSION — Interaction between rounds             ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    n_rounds = 64
    forward, backward = measure_link_tension(n_rounds)
    links, bottleneck = find_bottleneck(forward, backward, n_rounds)

    # Tension map
    print("  LINK TENSION MAP (per round):")
    print("  " + "─" * 55)
    print(f"  {'r':>3} {'τ_fwd':>7} {'τ_bwd':>7} {'τ_link':>7} {'visual'}")
    print("  " + "─" * 55)

    for lt in links:
        r = lt['round']
        if r < 6 or r > 58 or r % 8 == 0 or lt == bottleneck:
            bar_f = '→' * min(lt['tau_forward'] // 16, 8)
            bar_b = '←' * min(lt['tau_backward'] // 16, 8)
            bar = '█' * min(lt['tau_link'] // 16, 8)
            marker = " ★ BOTTLENECK" if lt == bottleneck else ""
            print(f"  {r:>3} {lt['tau_forward']:>7} {lt['tau_backward']:>7} "
                  f"{lt['tau_link']:>7} |{bar:<8}|{marker}")

    # System analysis
    system = system_tension_formula(links)

    print(f"""
  SYSTEM ANALYSIS:
  ────────────────────────────────────────────────
    Easy links (τ ≤ 32):   {system['n_easy']}/{n_rounds} rounds
    Hard links (τ > 32):   {system['n_hard']}/{n_rounds} rounds
    Bottleneck rounds:     {system['hard_rounds'][:10]}{'...' if len(system['hard_rounds'])>10 else ''}

    SYSTEM TENSION: {system['tau_system']} bits
    Birthday:       128 bits
    {"★ BELOW BIRTHDAY!" if system['tau_system'] < 128 else f"Gap: {system['tau_system'] - 128} bits above birthday"}

  KEY INSIGHT:
    Forward from IV: tension GROWS (unknown W enters)
    Backward from output: tension GROWS (unknown h_prev enters)
    MIDDLE: both directions have high tension = BOTTLENECK

    The bottleneck is at round {bottleneck['round']}:
      Forward τ = {bottleneck['tau_forward']}
      Backward τ = {bottleneck['tau_backward']}
      Link τ = {bottleneck['tau_link']}

    System tension is NOT: product of 64 rounds.
    System tension IS: sum of bottleneck links.
    The non-bottleneck rounds are FREE (easily solved from either direction).

  THIS IS THE REAL COST:
    Only {system['n_hard']} rounds out of {n_rounds} are truly hard.
    The rest are solved by forward or backward propagation.
    Focus ALL effort on the {system['n_hard']} bottleneck rounds.
""")
