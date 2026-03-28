"""
LINK — The fundamental primitive. Deeper than LOOK.

LOOK was about observing ONE bit.
LINK is about CONNECTION between two things.

Before LOOK there is LINK:
  You can look at something only if you're LINKED to it.
  The cost of looking = the tension of the link.

  τ = 0:  rigid link (looking is free)
  τ > 0:  elastic link (looking costs effort)
  τ = ∞:  no link (can never observe)

From LINK, everything emerges:
  LOOK = traverse one link
  SKIP = ignore a link because another link resolved the question
  Number = count of links
  Space = network of links with metric = tension
"""


# ════════════════════════════════════════════════════════════
# STEP 1: LINK — the only primitive
# ════════════════════════════════════════════════════════════

class Node:
    """A point in the network. Has a state: known value, or ?."""
    __slots__ = ('name', 'value')

    def __init__(self, name, value=None):
        self.name = name
        self.value = value  # None = unobserved (?)

    @property
    def known(self):
        return self.value is not None

    def __repr__(self):
        return f'{self.name}={self.value}' if self.known else f'{self.name}=?'


class Link:
    """
    Connection between two nodes. Has tension τ.

    τ = 0:  rigid — if source known, target is instantly known
    τ > 0:  elastic — target costs τ to determine from source
    τ = ∞:  broken — target independent of source

    type: how source determines target
      'copy':  target = source
      'not':   target = NOT(source)
      'kill':  if source = kill_val → target = forced_val (AND/OR skip)
      'pass':  source gives info but doesn't determine target alone
    """
    def __init__(self, source, target, tau=1.0, link_type='pass',
                 kill_val=None, forced_val=None):
        self.source = source
        self.target = target
        self.tau = tau
        self.type = link_type
        self.kill_val = kill_val
        self.forced_val = forced_val

    def can_determine(self):
        """Can this link determine target from source alone?"""
        if not self.source.known:
            return False
        if self.type == 'copy':
            return True
        if self.type == 'not':
            return True
        if self.type == 'kill' and self.source.value == self.kill_val:
            return True  # SKIP!
        return False

    def propagate(self):
        """
        Push value through link. Returns (determined, cost).

        determined: True if target value was set
        cost: tension spent
        """
        if not self.source.known:
            return False, 0

        if self.type == 'copy':
            self.target.value = self.source.value
            return True, self.tau

        if self.type == 'not':
            self.target.value = 1 - self.source.value
            return True, self.tau

        if self.type == 'kill':
            if self.source.value == self.kill_val:
                self.target.value = self.forced_val
                return True, self.tau  # SKIP the other input!

        return False, 0

    def __repr__(self):
        return f'Link({self.source.name}→{self.target.name}, τ={self.tau}, {self.type})'


# ════════════════════════════════════════════════════════════
# STEP 2: NETWORK — nodes connected by links
# ════════════════════════════════════════════════════════════

class Network:
    """
    A set of nodes connected by links.
    Computation = propagation through the network.
    """
    def __init__(self, name='net'):
        self.name = name
        self.nodes = {}
        self.links = []

    def node(self, name, value=None):
        n = Node(name, value)
        self.nodes[name] = n
        return n

    def link(self, source, target, tau=1.0, link_type='pass', **kw):
        l = Link(source, target, tau, link_type, **kw)
        self.links.append(l)
        return l

    def propagate(self, max_steps=100):
        """
        Propagate known values through all links until stable.
        Returns: (total_cost, steps, nodes_determined)
        """
        total_cost = 0
        determined = 0

        for step in range(max_steps):
            progress = False
            for link in self.links:
                if link.target.known:
                    continue  # already determined
                ok, cost = link.propagate()
                if ok:
                    total_cost += cost
                    determined += 1
                    progress = True

            if not progress:
                break

        return total_cost, step + 1, determined

    def unknown_count(self):
        return sum(1 for n in self.nodes.values() if not n.known)

    def known_count(self):
        return sum(1 for n in self.nodes.values() if n.known)

    def tension_total(self):
        """Total tension of all unresolved links."""
        return sum(l.tau for l in self.links
                   if l.source.known and not l.target.known)


# ════════════════════════════════════════════════════════════
# STEP 3: Derive AND, OR, XOR from links
# ════════════════════════════════════════════════════════════

def make_and_network(name='AND'):
    """
    AND as a network:
      a ──kill(0→0)──→ output
      b ──kill(0→0)──→ output
      (a,b) ──pass──→ output [only if both known and non-zero]
    """
    net = Network(name)
    a = net.node('a')
    b = net.node('b')
    out = net.node('out')

    # Kill links: if a=0 or b=0, output=0 (SKIP!)
    net.link(a, out, tau=0, link_type='kill', kill_val=0, forced_val=0)
    net.link(b, out, tau=0, link_type='kill', kill_val=0, forced_val=0)

    return net, a, b, out


def make_or_network(name='OR'):
    """OR: kill links at value 1."""
    net = Network(name)
    a = net.node('a')
    b = net.node('b')
    out = net.node('out')

    net.link(a, out, tau=0, link_type='kill', kill_val=1, forced_val=1)
    net.link(b, out, tau=0, link_type='kill', kill_val=1, forced_val=1)

    return net, a, b, out


def make_xor_network(name='XOR'):
    """XOR: NO kill links. Always needs both inputs."""
    net = Network(name)
    a = net.node('a')
    b = net.node('b')
    out = net.node('out')

    # Only 'pass' links — neither input alone determines output
    net.link(a, out, tau=1, link_type='pass')
    net.link(b, out, tau=1, link_type='pass')

    return net, a, b, out


# ════════════════════════════════════════════════════════════
# VERIFICATION
# ════════════════════════════════════════════════════════════

def verify():
    import random

    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  LINK — The fundamental primitive                        ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Test AND network
    print("AND as network of links:")
    print("─" * 40)
    for a_val in [0, 1, None]:
        for b_val in [0, 1, None]:
            net, a, b, out = make_and_network()
            a.value = a_val
            b.value = b_val
            cost, steps, det = net.propagate()

            a_str = str(a_val) if a_val is not None else '?'
            b_str = str(b_val) if b_val is not None else '?'
            o_str = str(out.value) if out.known else '?'
            skip = ' ← SKIP!' if out.known and (a_val is None or b_val is None) else ''
            skip = ' ← SKIP!' if out.known and not (a_val is not None and b_val is not None) else ''
            if out.known and (a_val == 0 and b_val is None):
                skip = ' ← SKIP b!'
            if out.known and (b_val == 0 and a_val is None):
                skip = ' ← SKIP a!'
            print(f"  AND({a_str}, {b_str}) = {o_str}{skip}")

    # Test OR network
    print()
    print("OR as network of links:")
    print("─" * 40)
    for a_val in [0, 1, None]:
        for b_val in [0, 1, None]:
            net, a, b, out = make_or_network()
            a.value = a_val
            b.value = b_val
            cost, steps, det = net.propagate()
            a_str = str(a_val) if a_val is not None else '?'
            b_str = str(b_val) if b_val is not None else '?'
            o_str = str(out.value) if out.known else '?'
            skip = ''
            if out.known and a_val == 1 and b_val is None:
                skip = ' ← SKIP b!'
            if out.known and b_val == 1 and a_val is None:
                skip = ' ← SKIP a!'
            print(f"  OR({a_str}, {b_str}) = {o_str}{skip}")

    # Test XOR network
    print()
    print("XOR as network of links:")
    print("─" * 40)
    for a_val in [0, 1, None]:
        for b_val in [0, 1, None]:
            net, a, b, out = make_xor_network()
            a.value = a_val
            b.value = b_val
            cost, steps, det = net.propagate()
            a_str = str(a_val) if a_val is not None else '?'
            b_str = str(b_val) if b_val is not None else '?'
            o_str = str(out.value) if out.known else '?'
            print(f"  XOR({a_str}, {b_str}) = {o_str}")

    # The deep test: chain networks and measure propagation
    print()
    print("CHAIN PROPAGATION:")
    print("═" * 50)

    for gate_type, maker in [('AND', make_and_network),
                              ('OR', make_or_network),
                              ('XOR', make_xor_network)]:
        print(f"\n  {gate_type} chain (n nodes, first = 0):")
        print(f"  {'n':>4} {'determined':>12} {'unknown':>10} {'skip_rate':>10}")
        print(f"  {'─'*38}")

        for n in [4, 8, 16, 32, 64]:
            # Build chain: node0 → gate → node1 → gate → ... → output
            big_net = Network(f'{gate_type}_chain')
            nodes = [big_net.node(f'x{i}') for i in range(n)]
            output = big_net.node('output')

            # Chain: each pair feeds a gate, result feeds next
            prev = nodes[0]
            for i in range(1, n):
                gate_out = big_net.node(f'g{i}')
                if gate_type == 'AND':
                    big_net.link(prev, gate_out, tau=0, link_type='kill',
                                kill_val=0, forced_val=0)
                    big_net.link(nodes[i], gate_out, tau=0, link_type='kill',
                                kill_val=0, forced_val=0)
                elif gate_type == 'OR':
                    big_net.link(prev, gate_out, tau=0, link_type='kill',
                                kill_val=1, forced_val=1)
                    big_net.link(nodes[i], gate_out, tau=0, link_type='kill',
                                kill_val=1, forced_val=1)
                else:  # XOR
                    big_net.link(prev, gate_out, tau=1, link_type='pass')
                    big_net.link(nodes[i], gate_out, tau=1, link_type='pass')
                prev = gate_out

            # Set first node to controlling value
            if gate_type == 'AND':
                nodes[0].value = 0  # kills AND chain
            elif gate_type == 'OR':
                nodes[0].value = 1  # kills OR chain
            else:
                nodes[0].value = 0  # XOR: doesn't help

            cost, steps, det = big_net.propagate()
            total = len(big_net.nodes)
            known = big_net.known_count()
            unknown = big_net.unknown_count()
            skip_rate = (det) / max(n - 1, 1)

            print(f"  {n:>4} {det:>12} {unknown:>10} {skip_rate:>10.2%}")

    print(f"""
═══════════════════════════════════════════════════════════════
THE LINK PRIMITIVE:

  Everything is nodes connected by links.
  Every link has tension τ.
  Propagation flows through links.

  Kill links: AND(0,?) = 0, OR(1,?) = 1. Skip the other.
  Pass links: XOR(a,?) = ?. Both needed. No skip.

  THIS IS DEEPER THAN LOOK:
    LOOK = traversing a single link.
    SKIP = kill link resolves target without traversing other links.
    Network = many links = circuit = computation.

  AND chain: one kill propagates through entire chain → O(1).
  XOR chain: no kills → every link must be traversed → O(n).

  The topology of kill-links vs pass-links determines ALL costs.
  This is the GEOMETRY of computation.
═══════════════════════════════════════════════════════════════
""")


if __name__ == '__main__':
    verify()
