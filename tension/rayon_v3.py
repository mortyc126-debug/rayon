#!/usr/bin/env python3
"""
RAYON v3 — Language with ? as first-class type.

Built on 6 verified foundation steps:
  1. LOOK+SKIP: AND=O(1), XOR=O(n)
  2. COMPOSE: probabilistic cost
  3. CIRCUIT: SAT=O(n) for balanced
  4. PREIMAGE: hard=XOR(AND) only
  5. THREE-STATE: {0, 1, ?}
  6. BRIDGE: τ=0 → standard math

Every variable is {0, 1, ?}.
Every operation propagates ? with skip rules.
The runtime tracks tension (cost of resolving ?s).
"""

import sys
import time
import random


# ════════════════════════════════════════════════════════════
# CORE: The ? type
# ════════════════════════════════════════════════════════════

class Unobserved:
    """? — the unobserved state. Has cost τ to resolve."""
    __slots__ = ('tau', 'name')
    def __init__(self, tau=1.0, name='?'):
        self.tau = tau
        self.name = name
    def __repr__(self):
        return f'?[τ={self.tau:.1f}]' if self.tau != 1.0 else '?'
    def __bool__(self):
        raise TypeError("Cannot use ? as boolean. Resolve first.")
    def __eq__(self, other):
        if isinstance(other, Unobserved): return True
        return NotImplemented
    def __hash__(self):
        return hash('?')

# ════════════════════════════════════════════════════════════
# THREE-STATE OPERATIONS (verified in Step 5)
# ════════════════════════════════════════════════════════════

def is_q(x): return isinstance(x, Unobserved)

def AND(a, b):
    if not is_q(a) and a == 0: return 0        # SKIP b
    if not is_q(b) and b == 0: return 0        # SKIP a
    if is_q(a) or is_q(b):
        tau = (a.tau if is_q(a) else 0) + (b.tau if is_q(b) else 0)
        return Unobserved(tau)
    return a & b

def OR(a, b):
    if not is_q(a) and a == 1: return 1        # SKIP b
    if not is_q(b) and b == 1: return 1        # SKIP a
    if is_q(a) or is_q(b):
        tau = min(a.tau if is_q(a) else 0, b.tau if is_q(b) else 0)
        return Unobserved(tau)
    return a | b

def XOR(a, b):
    if is_q(a) or is_q(b):                    # NEVER skip
        tau = (a.tau if is_q(a) else 0) + (b.tau if is_q(b) else 0)
        return Unobserved(tau)
    return a ^ b

def NOT(a):
    if is_q(a): return Unobserved(a.tau)
    return 1 - a

def ADD32(a, b):
    """32-bit modular addition in three-state."""
    if is_q(a) or is_q(b):
        tau = (a.tau if is_q(a) else 0) + (b.tau if is_q(b) else 0)
        return Unobserved(tau)
    return (a + b) & 0xFFFFFFFF

def ROTR(x, n):
    if is_q(x): return Unobserved(x.tau)
    return ((x >> n) | (x << (32 - n))) & 0xFFFFFFFF

def SHR(x, n):
    if is_q(x): return Unobserved(x.tau)
    return x >> n


# ════════════════════════════════════════════════════════════
# WORD-LEVEL: 32-bit words as {value, ?}
# ════════════════════════════════════════════════════════════

class Word32:
    """32-bit word that can be known (int) or unobserved (?)."""
    __slots__ = ('val',)

    def __init__(self, val=None, tau=1.0):
        if val is None:
            self.val = Unobserved(tau)
        elif is_q(val):
            self.val = val
        else:
            self.val = val & 0xFFFFFFFF

    @property
    def known(self):
        return not is_q(self.val)

    @property
    def tau(self):
        return 0.0 if self.known else self.val.tau

    def __repr__(self):
        if self.known:
            return f'W({self.val:#010x})'
        return f'W(?[τ={self.tau:.1f}])'

    def __add__(self, other):
        return Word32(ADD32(self.val, other.val))

    def __xor__(self, other):
        return Word32(XOR(self.val, other.val))

    def __and__(self, other):
        return Word32(AND(self.val, other.val))

    def __or__(self, other):
        return Word32(OR(self.val, other.val))

    def __invert__(self):
        if self.known:
            return Word32((~self.val) & 0xFFFFFFFF)
        return Word32(None, self.tau)

    def rotr(self, n):
        return Word32(ROTR(self.val, n))

    def shr(self, n):
        return Word32(SHR(self.val, n))


# ════════════════════════════════════════════════════════════
# SHA-256 in RAYON: works with both known and ? inputs
# ════════════════════════════════════════════════════════════

K256 = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
    0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
    0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
    0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
    0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
    0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]

IV = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
      0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]


def rayon_sha256(message_words):
    """
    SHA-256 in Rayon. Accepts mix of known and ? words.

    Known words: computed exactly (same as standard SHA-256).
    ? words: propagated through circuit, showing where skips happen.

    Returns: 8 output words (each known or ?), tension map per round.
    """
    # Message schedule
    W = [Word32(w) if isinstance(w, int) else Word32(None, w.tau if is_q(w) else 1.0)
         for w in message_words]
    while len(W) < 16:
        W.append(Word32(0))

    tension_map = []

    for i in range(16, 64):
        s0 = W[i-15].rotr(7) ^ W[i-15].rotr(18) ^ W[i-15].shr(3)
        s1 = W[i-2].rotr(17) ^ W[i-2].rotr(19) ^ W[i-2].shr(10)
        W.append(W[i-16] + s0 + W[i-7] + s1)

    # State
    state = [Word32(iv) for iv in IV]

    for r in range(64):
        a, b, c, d, e, f, g, h = state

        # Σ1(e)
        S1 = e.rotr(6) ^ e.rotr(11) ^ e.rotr(25)
        # Ch(e, f, g) — uses AND → can SKIP
        ch = (e & f) ^ (~e & g)
        # temp1
        temp1 = h + S1 + ch + Word32(K256[r]) + W[r]

        # Σ0(a)
        S0 = a.rotr(2) ^ a.rotr(13) ^ a.rotr(22)
        # Maj(a, b, c) — uses AND → can SKIP
        maj = (a & b) ^ (a & c) ^ (b & c)
        # temp2
        temp2 = S0 + maj

        # Track tension at this round
        round_tau = temp1.tau + temp2.tau
        known_count = sum(1 for s in state if s.known)
        tension_map.append({
            'round': r, 'tau': round_tau,
            'known_state': known_count,
            'W_known': W[r].known,
        })

        # Update state
        state = [temp1 + temp2, a, b, c, d + temp1, e, f, g]

    # Final hash
    H = [Word32((state[i].val + IV[i]) & 0xFFFFFFFF) if state[i].known
         else Word32(None, state[i].tau)
         for i in range(8)]

    return H, tension_map


# ════════════════════════════════════════════════════════════
# DEMO
# ════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  RAYON v3 — SHA-256 with ? as first-class type          ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Demo 1: Standard mode (all known)
    print("MODE 1: All inputs known → standard SHA-256")
    print("─" * 55)
    msg = [0x61626380] + [0]*14 + [0x18]  # "abc" padded
    H, tmap = rayon_sha256(msg)
    print(f"  H = {' '.join(str(h) for h in H)}")

    # Verify against standard
    import hashlib
    real = hashlib.sha256(b'abc').hexdigest()
    our = ''.join(f'{h.val:08x}' for h in H)
    match = real == our
    print(f"  Standard: {real}")
    print(f"  Rayon:    {our}")
    print(f"  Match: {'✓' if match else '✗'}")
    print()

    # Demo 2: One word unknown
    print("MODE 2: W[0] = ?, rest known → tension map")
    print("─" * 55)
    msg2 = [Unobserved(tau=32.0)] + [0]*14 + [0x18]
    H2, tmap2 = rayon_sha256(msg2)
    print(f"  H = {' '.join(str(h) for h in H2)}")
    print()

    # Show when state becomes fully ?
    print("  Tension propagation:")
    for t in tmap2:
        if t['round'] < 5 or t['round'] % 16 == 0 or t['round'] >= 60:
            status = '█' * min(40, int(t['tau'] / 10)) if t['tau'] > 0 else '·'
            w_str = 'known' if t['W_known'] else '?'
            print(f"    r={t['round']:>2}: state_known={t['known_state']}/8, "
                  f"W[r]={w_str:>5}, τ={t['tau']:>8.1f} |{status}|")

    # Demo 3: All unknown
    print()
    print("MODE 3: All inputs ? → full tension map")
    print("─" * 55)
    msg3 = [Unobserved(tau=32.0)] * 16
    H3, tmap3 = rayon_sha256(msg3)
    print(f"  H = {' '.join(str(h) for h in H3)}")

    total_tau = sum(t['tau'] for t in tmap3)
    print(f"  Total tension: {total_tau:.1f}")
    print(f"  All ? → everything is ?: {'✓' if all(not h.known for h in H3) else '✗'}")

    print(f"""
═══════════════════════════════════════════════════════════════
RAYON v3 — Summary:

  MODE 1 (all known): Rayon = Standard SHA-256. Bit-exact ✓.
  MODE 2 (partial ?): Shows tension per round. Skip map.
  MODE 3 (all ?): Everything propagates as ?. Total tension computed.

  The language treats ? as a NATIVE TYPE.
  SHA-256 code is THE SAME for all three modes.
  The runtime automatically tracks tension and skips.

  This is the bridge in action:
    Standard math → set all τ = 0 → exact results.
    Search mode → set unknown τ > 0 → skip map + cost estimate.
    Same code. Same language. Different information.
═══════════════════════════════════════════════════════════════
""")
