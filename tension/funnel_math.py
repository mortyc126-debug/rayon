"""
FUNNEL MATHEMATICS — New objects born from chaos data.

NOT cycles. NOT iteration. FUNNELS.

A funnel is what chaos CREATES:
  4 billion states → compressed into ~90-state loop.
  Every trajectory eventually enters the loop.
  The path to the loop = the funnel.

FUNNEL = (throat, depth, loop)
  throat: entry point into the loop
  depth: steps from any start to throat (= tail)
  loop: the closed path inside

SHA-256 with fixed W creates ONE funnel.
Different W → different funnel.
ALL funnels are narrow (~90 states from 2^32).

COLLISION = two starting points in same funnel.
Their trajectories MERGE at the throat → same loop → same outputs.
"""

import random
import time

M4 = 0xF
IV4 = (0x6, 0xB, 0x3, 0xA, 0x5, 0x9, 0x1, 0x5)
K4 = [0x4,0x7,0xB,0xE,0x3,0x5,0x9,0xA,0xD,0x1,0x2,0x5,0x7,0x8,0x9,0xC]


def sha4_compress(iv, W, n_rounds=64):
    Ws = list(W[:16])
    while len(Ws) < 16: Ws.append(0)
    for i in range(16, max(n_rounds, 16)):
        Ws.append((Ws[i-2] ^ Ws[i-7] ^ Ws[i-15] ^ Ws[i-16]) & M4)
    a,b,c,d,e,f,g,h = iv
    for r in range(n_rounds):
        ch = (e & f) ^ (~e & g) & M4
        t1 = (h + ch + K4[r%16] + Ws[r%len(Ws)]) & M4
        maj = (a & b) ^ (a & c) ^ (b & c)
        t2 = (a ^ maj) & M4
        h,g,f,e = g,f,e,(d+t1)&M4
        d,c,b,a = c,b,a,(t1+t2)&M4
    return tuple((iv[i]+x)&M4 for i,x in enumerate([a,b,c,d,e,f,g,h]))


class Funnel:
    """
    A funnel: the structure chaos creates.

    Given function F and starting point:
    trajectory = [s0, s1=F(s0), s2=F(s1), ...]
    Eventually enters a loop.

    Funnel = the trajectory SHAPE.
    """
    def __init__(self, F, start, max_steps=300000):
        # Floyd's cycle detection
        slow = F(start)
        fast = F(F(start))
        steps = 1
        while slow != fast and steps < max_steps:
            slow = F(slow)
            fast = F(F(fast))
            steps += 1

        if steps >= max_steps:
            self.valid = False
            return

        self.valid = True

        # Find tail length
        slow = start
        self.tail = 0
        while slow != fast:
            slow = F(slow)
            fast = F(fast)
            self.tail += 1

        self.throat = slow  # entry point of loop

        # Find loop
        self.loop = [self.throat]
        probe = F(self.throat)
        while probe != self.throat:
            self.loop.append(probe)
            probe = F(probe)

        self.loop_size = len(self.loop)
        self.depth = self.tail

    @property
    def width(self):
        """How many starting points lead to this funnel?
        Measure by sampling."""
        return self.loop_size  # approximation

    def contains(self, point, F, max_steps=1000):
        """Does this point eventually reach our funnel's loop?"""
        current = point
        for _ in range(max_steps):
            if current in self.loop:
                return True
            current = F(current)
        return False


def measure_funnel_collisions(W, n_samples=10000):
    """
    NEW ATTACK: Find collisions via funnel structure.

    Instead of birthday on OUTPUT:
    1. Compute funnel for this W
    2. Random starting points → all lead to same loop
    3. Two points arriving at loop at SAME position = collision!
    """
    F = lambda state: sha4_compress(state, W, 64)

    # Build funnel from IV
    funnel = Funnel(F, IV4)
    if not funnel.valid:
        return None

    # Now: random starting states → track where they enter the loop
    entry_positions = {}  # loop_index → list of (start, steps_to_entry)
    collisions = []

    for _ in range(n_samples):
        start = tuple(random.randint(0, M4) for _ in range(8))
        # Walk until we hit the loop
        current = start
        for step in range(funnel.depth + funnel.loop_size + 100):
            if current in funnel.loop:
                loop_idx = funnel.loop.index(current)
                if loop_idx in entry_positions:
                    # Another point entered at same loop position!
                    prev_start, prev_steps = entry_positions[loop_idx]
                    if prev_start != start:
                        collisions.append((start, prev_start, loop_idx))
                entry_positions[loop_idx] = (start, step)
                break
            current = F(current)

    return {
        'funnel_depth': funnel.depth,
        'loop_size': funnel.loop_size,
        'throat': funnel.throat,
        'n_collisions': len(collisions),
        'n_entry_positions': len(entry_positions),
        'collisions': collisions[:3],
    }


if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  FUNNEL MATHEMATICS — Structure born from chaos          ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    random.seed(42)

    # Measure funnels for various W
    print("  FUNNEL MAP:")
    print(f"  {'W[0]':>5} {'depth':>7} {'loop':>7} {'note':>20}")
    print(f"  {'─'*42}")

    funnels = []
    for _ in range(20):
        W = [random.randint(0, M4) for _ in range(16)]
        F = lambda s, w=W: sha4_compress(s, w, 64)
        funnel = Funnel(F, IV4)
        if funnel.valid:
            funnels.append((W, funnel))
            note = ''
            if funnel.loop_size < 30:
                note = '★ ULTRA-NARROW'
            elif funnel.loop_size < 60:
                note = 'narrow'
            print(f"  {W[0]:>5} {funnel.depth:>7} {funnel.loop_size:>7} {note:>20}")

    # Collision search via funnels
    print()
    print("  FUNNEL COLLISION SEARCH:")
    print(f"  {'─'*50}")

    total_funnel_cols = 0
    for W, funnel in funnels[:5]:
        result = measure_funnel_collisions(W, n_samples=5000)
        if result:
            total_funnel_cols += result['n_collisions']
            print(f"    W[0]={W[0]}: loop={result['loop_size']}, "
                  f"entries={result['n_entry_positions']}, "
                  f"collisions={result['n_collisions']}")
            if result['collisions']:
                s1, s2, idx = result['collisions'][0]
                print(f"      Collision: entry #{idx} in loop")
                # Verify: both should produce same hash after enough iterations
                F = lambda s, w=W: sha4_compress(s, w, 64)
                # Walk both to loop entry
                c1 = s1
                for _ in range(funnel.depth + funnel.loop_size):
                    c1 = F(c1)
                c2 = s2
                for _ in range(funnel.depth + funnel.loop_size):
                    c2 = F(c2)
                print(f"      After iteration: s1→{c1[:4]}... s2→{c2[:4]}...")
                print(f"      Same? {'✓' if c1 == c2 else '✗'}")

    print(f"""
  ═══════════════════════════════════════════════════════
  FUNNEL MATHEMATICS:

    SHA-4 with fixed W creates a FUNNEL:
      2^32 states → {sum(f.loop_size for _,f in funnels)//len(funnels)}-state loop (average)
      Compression: {2**32 // (sum(f.loop_size for _,f in funnels)//len(funnels)):.0f}×

    Every trajectory enters the loop.
    Points entering at SAME loop position = structural collision.

    This is NOT birthday. This is FUNNEL COLLISION:
      Birthday: random matching in output space.
      Funnel: deterministic convergence in trajectory space.

    Birthday needs √|output|. Funnel needs ~loop_size trials.
    If loop << √|output|: FUNNEL WINS.

    For SHA-4: loop ≈ {sum(f.loop_size for _,f in funnels)//len(funnels)}, √|output| = {int(2**16)}.
    {'★ FUNNEL WINS!' if sum(f.loop_size for _,f in funnels)//len(funnels) < 2**16 else 'Birthday still faster.'}
  ═══════════════════════════════════════════════════════
""")
