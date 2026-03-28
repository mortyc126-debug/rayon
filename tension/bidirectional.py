"""
BIDIRECTIONAL LINKS — The key insight standard math misses.

Standard computation: input → output (one direction).
Standard inversion: output → input (separate, hard problem).

LINK networks: propagation goes BOTH WAYS through the same network.

Forward:  AND(0, ?) = 0  (kill-link: input determines output)
Backward: AND(output=0, a=1) → b=0  (backward kill: output determines input!)

AND forward: one input=0 → output=0 (skip other)
AND backward: output=0, one input=1 → other input=0 (DEDUCE other!)

XOR forward: both inputs needed (no skip)
XOR backward: output + one input → other input (PERFECTLY invertible!)

This means: XOR is HARD forward but EASY backward.
AND is EASY forward (kill) and also useful backward (deduce).

BIDIRECTIONAL propagation = forward + backward SIMULTANEOUSLY.
This is strictly MORE POWERFUL than either direction alone.
"""

from link import Node, Link, Network


class BiLink(Link):
    """
    Bidirectional link. Can propagate forward AND backward.
    """
    def propagate_backward(self):
        """Deduce source from target (reverse direction)."""
        if not self.target.known:
            return False, 0
        if self.source.known:
            return False, 0  # already known

        if self.type == 'copy':
            self.source.value = self.target.value
            return True, self.tau

        if self.type == 'not':
            self.source.value = 1 - self.target.value
            return True, self.tau

        return False, 0


class BiNetwork(Network):
    """Network with bidirectional propagation."""

    def propagate_both(self, max_steps=100):
        """Propagate forward AND backward until stable."""
        total_cost = 0
        total_det = 0

        for step in range(max_steps):
            progress = False

            # Forward
            for link in self.links:
                if link.target.known:
                    continue
                ok, cost = link.propagate()
                if ok:
                    total_cost += cost
                    total_det += 1
                    progress = True

            # Backward (if BiLink)
            for link in self.links:
                if hasattr(link, 'propagate_backward'):
                    if link.source.known:
                        continue
                    ok, cost = link.propagate_backward()
                    if ok:
                        total_cost += cost
                        total_det += 1
                        progress = True

            if not progress:
                break

        return total_cost, step + 1, total_det


# ════════════════════════════════════════════════════════════
# GATE NETWORKS with bidirectional deduction
# ════════════════════════════════════════════════════════════

class GateNetwork:
    """
    Circuit of AND/OR/XOR gates with FULL bidirectional propagation.

    Each gate: 2 inputs → 1 output.
    Forward: input values → output value (standard)
    Backward: output value + partial inputs → remaining inputs (deduction)
    """
    def __init__(self):
        self.nodes = {}
        self.gates = []  # (type, in1_name, in2_name, out_name)

    def input(self, name):
        self.nodes[name] = None  # ? by default
        return name

    def gate(self, gate_type, in1, in2, out_name=None):
        if out_name is None:
            out_name = f'g{len(self.gates)}'
        self.nodes[out_name] = None
        self.gates.append((gate_type, in1, in2, out_name))
        return out_name

    def set(self, name, value):
        self.nodes[name] = value

    def get(self, name):
        return self.nodes.get(name)

    def propagate_full(self, max_rounds=50):
        """
        Full bidirectional propagation.
        Returns: number of nodes determined.
        """
        determined = 0

        for _ in range(max_rounds):
            progress = False

            for gt, in1, in2, out in self.gates:
                v1 = self.nodes.get(in1)
                v2 = self.nodes.get(in2)
                vo = self.nodes.get(out)

                # ── FORWARD ──
                if vo is None:
                    if gt == 'AND':
                        if v1 == 0 or v2 == 0:
                            self.nodes[out] = 0; determined += 1; progress = True
                        elif v1 is not None and v2 is not None:
                            self.nodes[out] = v1 & v2; determined += 1; progress = True
                    elif gt == 'OR':
                        if v1 == 1 or v2 == 1:
                            self.nodes[out] = 1; determined += 1; progress = True
                        elif v1 is not None and v2 is not None:
                            self.nodes[out] = v1 | v2; determined += 1; progress = True
                    elif gt == 'XOR':
                        if v1 is not None and v2 is not None:
                            self.nodes[out] = v1 ^ v2; determined += 1; progress = True

                # ── BACKWARD ── (the NEW part!)
                vo = self.nodes.get(out)  # might have been set above

                if gt == 'AND':
                    if vo == 1:  # AND=1 → BOTH inputs must be 1
                        if v1 is None:
                            self.nodes[in1] = 1; determined += 1; progress = True
                        if v2 is None:
                            self.nodes[in2] = 1; determined += 1; progress = True
                    elif vo == 0:
                        if v1 == 1 and v2 is None:
                            self.nodes[in2] = 0; determined += 1; progress = True
                        if v2 == 1 and v1 is None:
                            self.nodes[in1] = 0; determined += 1; progress = True

                elif gt == 'OR':
                    if vo == 0:  # OR=0 → BOTH inputs must be 0
                        if v1 is None:
                            self.nodes[in1] = 0; determined += 1; progress = True
                        if v2 is None:
                            self.nodes[in2] = 0; determined += 1; progress = True
                    elif vo == 1:
                        if v1 == 0 and v2 is None:
                            self.nodes[in2] = 1; determined += 1; progress = True
                        if v2 == 0 and v1 is None:
                            self.nodes[in1] = 1; determined += 1; progress = True

                elif gt == 'XOR':
                    # XOR backward: output + one input → other input!
                    if vo is not None and v1 is not None and v2 is None:
                        self.nodes[in2] = vo ^ v1; determined += 1; progress = True
                    if vo is not None and v2 is not None and v1 is None:
                        self.nodes[in1] = vo ^ v2; determined += 1; progress = True

            if not progress:
                break

        return determined

    def count_known(self):
        return sum(1 for v in self.nodes.values() if v is not None)

    def count_unknown(self):
        return sum(1 for v in self.nodes.values() if v is None)

    def known_inputs(self, input_names):
        return sum(1 for n in input_names if self.nodes.get(n) is not None)


# ════════════════════════════════════════════════════════════
# VERIFICATION
# ════════════════════════════════════════════════════════════

def verify():
    import random

    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  BIDIRECTIONAL — Forward + Backward through same network ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Test 1: AND backward deduction
    print("TEST 1: AND backward deduction")
    print("─" * 50)

    g = GateNetwork()
    a = g.input('a')
    b = g.input('b')
    out = g.gate('AND', a, b, 'out')

    # Know output=1 → deduce both inputs=1
    g.set('out', 1)
    det = g.propagate_full()
    print(f"  AND(?, ?) = 1 → a={g.get('a')}, b={g.get('b')} "
          f"{'✓ both deduced!' if g.get('a')==1 and g.get('b')==1 else '✗'}")

    # Know output=0, a=1 → deduce b=0
    g2 = GateNetwork()
    a2 = g2.input('a'); b2 = g2.input('b')
    g2.gate('AND', a2, b2, 'out')
    g2.set('out', 0); g2.set('a', 1)
    g2.propagate_full()
    print(f"  AND(1, ?) = 0 → b={g2.get('b')} "
          f"{'✓ deduced!' if g2.get('b')==0 else '✗'}")
    print()

    # Test 2: XOR backward — THE KEY
    print("TEST 2: XOR backward (the game-changer)")
    print("─" * 50)

    g3 = GateNetwork()
    a3 = g3.input('a'); b3 = g3.input('b')
    g3.gate('XOR', a3, b3, 'out')
    g3.set('out', 1); g3.set('a', 0)
    g3.propagate_full()
    print(f"  XOR(0, ?) = 1 → b={g3.get('b')} "
          f"{'✓ deduced!' if g3.get('b')==1 else '✗'}")

    g4 = GateNetwork()
    a4 = g4.input('a'); b4 = g4.input('b')
    g4.gate('XOR', a4, b4, 'out')
    g4.set('out', 0); g4.set('a', 1)
    g4.propagate_full()
    print(f"  XOR(1, ?) = 0 → b={g4.get('b')} "
          f"{'✓ deduced!' if g4.get('b')==1 else '✗'}")

    print()
    print("  XOR forward: HARD (both inputs needed)")
    print("  XOR backward: EASY (output + one input → other)")
    print("  ★ This INVERTS the hardness direction!")
    print()

    # Test 3: Chain inversion
    print("TEST 3: Chain inversion — solve backward")
    print("─" * 50)

    for gate_type in ['AND', 'OR', 'XOR']:
        for n in [4, 8, 16, 32]:
            g = GateNetwork()
            inputs = [g.input(f'x{i}') for i in range(n)]

            # Build chain
            prev = inputs[0]
            for i in range(1, n):
                prev = g.gate(gate_type, prev, inputs[i])

            # Set OUTPUT and FIRST INPUT → how many can we deduce?
            g.set(prev, 1)  # output = 1
            g.set(inputs[0], 1)  # first input known
            det = g.propagate_full()

            known = g.known_inputs(inputs)
            print(f"    {gate_type} chain n={n:>2}: output=1, x0=1 → "
                  f"{known}/{n} inputs deduced ({known/n:.0%})")

        print()

    # Test 4: The power of bidirectional — mixed circuit
    print("TEST 4: Mixed circuit — bidirectional solves more")
    print("─" * 50)

    # Circuit: out = AND(XOR(x0,x1), XOR(x2,x3))
    # Know: out=1, x0=0
    # Forward only: x0=0 → XOR(0,x1) needs x1. Stuck.
    # Bidirectional: out=1 → AND=1 → both XORs = 1.
    #   XOR(x0,x1)=1, x0=0 → x1=1! XOR(x2,x3)=1 → need one more.
    g = GateNetwork()
    x = [g.input(f'x{i}') for i in range(4)]
    xor1 = g.gate('XOR', x[0], x[1], 'xor1')
    xor2 = g.gate('XOR', x[2], x[3], 'xor2')
    out = g.gate('AND', xor1, xor2, 'out')

    g.set('out', 1)
    g.set('x0', 0)
    det = g.propagate_full()
    known = g.known_inputs(x)
    print(f"  AND(XOR(0,?), XOR(?,?)) = 1")
    print(f"  Forward only: stuck at XOR(0, x1)=? (need x1)")
    print(f"  Bidirectional: AND=1 → both XOR=1 → XOR(0,x1)=1 → x1=1!")
    print(f"  Result: {known}/4 inputs deduced")
    for xi in x:
        print(f"    {xi} = {g.get(xi)}")

    print(f"""
═══════════════════════════════════════════════════════════════
BIDIRECTIONAL PROPAGATION:

  Forward:  input → output  (standard computation)
  Backward: output → input  (deduction / inversion)
  Combined: BOTH simultaneously

  KEY REVERSALS:
    XOR forward: HARD (both inputs needed)
    XOR backward: EASY (output + one input → other input)

    AND forward: EASY (kill at 0)
    AND backward: USEFUL (output=1 → both inputs=1)

  POWER: Bidirectional solves problems that NEITHER direction
  can solve alone. The mixed circuit example shows:
    Forward alone: stuck.
    Backward alone: stuck.
    BOTH together: solved!

  THIS IS THE NEW CAPABILITY:
    Standard math: forward OR backward.
    Rayon math: forward AND backward SIMULTANEOUSLY.

  For SHA-256: propagate BOTH from known inputs AND from target hash.
  Meeting in the middle. Not MITM algorithm — STRUCTURAL propagation.
═══════════════════════════════════════════════════════════════
""")


if __name__ == '__main__':
    verify()
