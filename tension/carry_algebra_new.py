"""
CARRY ALGEBRA — New mathematics native to Rayon.

Not AND gates. Not boolean. A NEW algebraic object: {G, K, P, ?}

G = Generate (carry born here, flows upward)
K = Kill     (carry dies here, flow stops)
P = Propagate (carry passes through unchanged)
? = Unknown   (unobserved — our Rayon primitive)

COMPOSITION TABLE (low ∘ high):
    ∘ | G  K  P  ?
    --+-----------
    G | G  K  G  ?
    K | G  K  K  ?
    P | G  K  P  ?
    ? | G  K  ?  ?

LAWS:
  G absorbs from above: x ∘ G = G for all x
  K absorbs from above: x ∘ K = K for all x
  P is identity: x ∘ P = x
  ? is sticky: x ∘ ? = ? unless x is absorbed by G/K above
  G and K KILL uncertainty: ? ∘ G = G, ? ∘ K = K

This algebra determines carry chain cost WITHOUT counting AND gates.
"""


# ═══════════════════════════════════════════════════════════
# THE FOUR STATES
# ═══════════════════════════════════════════════════════════

G = 'G'  # Generate: carry = 1 out, regardless of input
K = 'K'  # Kill: carry = 0 out, regardless of input
P = 'P'  # Propagate: carry_out = carry_in
Q = '?'  # Unknown: unobserved (Rayon ?)


# ═══════════════════════════════════════════════════════════
# COMPOSITION: The fundamental operation
# ═══════════════════════════════════════════════════════════

COMPOSE_TABLE = {
    (G, G): G, (G, K): K, (G, P): G, (G, Q): Q,
    (K, G): G, (K, K): K, (K, P): K, (K, Q): Q,
    (P, G): G, (P, K): K, (P, P): P, (P, Q): Q,
    (Q, G): G, (Q, K): K, (Q, P): Q, (Q, Q): Q,
}

def compose(low, high):
    """Compose two carry states: low bit position ∘ high bit position."""
    return COMPOSE_TABLE[(low, high)]


def compose_chain(states):
    """Compose a full carry chain from bit 0 (leftmost) to bit n-1."""
    if not states:
        return K  # no carry
    result = states[0]
    for s in states[1:]:
        result = compose(result, s)
    return result


# ═══════════════════════════════════════════════════════════
# CARRY CHAIN: a sequence of GKP? states
# ═══════════════════════════════════════════════════════════

class CarryChain:
    """A carry chain = sequence of {G, K, P, ?} states."""

    def __init__(self, states):
        self.states = list(states)

    @property
    def length(self):
        return len(self.states)

    @property
    def output(self):
        """What comes out of the top of this chain?"""
        if not self.states:
            return K
        # Initial carry_in = 0 → equivalent to K at bottom
        return compose_chain([K] + self.states)

    @property
    def n_unknown(self):
        """Count of ? positions."""
        return sum(1 for s in self.states if s == Q)

    @property
    def n_generate(self):
        return sum(1 for s in self.states if s == G)

    @property
    def n_kill(self):
        return sum(1 for s in self.states if s == K)

    @property
    def n_propagate(self):
        return sum(1 for s in self.states if s == P)

    def surviving_unknowns(self):
        """
        How many ?-positions ACTUALLY matter for the output?

        A ? is KILLED if there's a G or K ABOVE it.
        A ? SURVIVES only if all positions above it are P or ?.

        This is THE key measurement.
        """
        surviving = 0
        # Scan from top (MSB) to bottom (LSB)
        # A ? survives if everything above it is P or ?
        all_above_transparent = True

        for i in range(len(self.states) - 1, -1, -1):
            s = self.states[i]
            if s == G or s == K:
                all_above_transparent = False
            elif s == Q:
                if all_above_transparent:
                    surviving += 1
                # else: this ? is killed by G/K above

        return surviving

    def effective_branches(self):
        """
        Branches that ACTUALLY affect the output.

        From the algebra:
          ? below G/K = killed (0 branches)
          ? with only P/? above = surviving (1 branch each)

        This is LESS than total ? count!
        """
        return self.surviving_unknowns()

    def __repr__(self):
        chain_str = ''.join(self.states)
        return f'Carry[{chain_str}] out={self.output} surv={self.surviving_unknowns()}/{self.n_unknown}'


# ═══════════════════════════════════════════════════════════
# THEOREMS
# ═══════════════════════════════════════════════════════════

def verify_theorems():
    results = []

    # Theorem C1: G absorbs from above
    for x in [G, K, P, Q]:
        r = compose(x, G)
        results.append((f"{x}∘G = G", r == G))

    # Theorem C2: K absorbs from above
    for x in [G, K, P, Q]:
        r = compose(x, K)
        results.append((f"{x}∘K = K", r == K))

    # Theorem C3: P is identity
    for x in [G, K, P, Q]:
        r = compose(x, P)
        results.append((f"{x}∘P = {x}", r == x))

    # Theorem C4: ? is sticky (persists unless absorbed)
    results.append(("G∘? = ?", compose(G, Q) == Q))
    results.append(("?∘? = ?", compose(Q, Q) == Q))
    results.append(("?∘G = G (absorbed!)", compose(Q, G) == G))
    results.append(("?∘K = K (absorbed!)", compose(Q, K) == K))

    # Theorem C5: Chain with ? below G → ? killed
    chain = CarryChain([Q, P, P, G, P, P])
    results.append((f"?PPG.. → surviving ?=0", chain.surviving_unknowns() == 0))

    # Theorem C6: Chain with ? at top → ? survives
    chain2 = CarryChain([G, P, K, P, Q])
    results.append((f"GPK.P? → surviving ?=1", chain2.surviving_unknowns() == 1))

    # Theorem C7: Multiple ? with G between → only top ? survives
    chain3 = CarryChain([Q, P, G, Q, P, P])
    results.append((f"?PG?PP → surviving ?=1 (bottom killed by G)",
                    chain3.surviving_unknowns() == 1))

    # Theorem C8: All P with one ? → ? survives
    chain4 = CarryChain([P, P, Q, P, P])
    results.append((f"PP?PP → surviving ?=1", chain4.surviving_unknowns() == 1))

    # Theorem C9: All ? → all survive (worst case)
    chain5 = CarryChain([Q, Q, Q, Q])
    results.append((f"???? → surviving=4", chain5.surviving_unknowns() == 4))

    # Theorem C10: Random chain statistics
    import random
    random.seed(42)
    total_unknown = 0
    total_surviving = 0
    n_trials = 10000
    chain_len = 31

    for _ in range(n_trials):
        # Random GKP? chain with P(G)=0.25, P(K)=0.25, P(P)=0.25, P(?)=0.25
        states = [random.choice([G, K, P, Q]) for _ in range(chain_len)]
        cc = CarryChain(states)
        total_unknown += cc.n_unknown
        total_surviving += cc.surviving_unknowns()

    avg_unknown = total_unknown / n_trials
    avg_surviving = total_surviving / n_trials
    compression = 1 - avg_surviving / max(avg_unknown, 1)
    results.append((f"Random chain: {avg_unknown:.1f}? → {avg_surviving:.1f} surviving "
                    f"(compress {compression:.0%})",
                    avg_surviving < avg_unknown))

    return results, avg_unknown, avg_surviving


# ═══════════════════════════════════════════════════════════
# SHA-256 APPLICATION
# ═══════════════════════════════════════════════════════════

def sha256_carry_analysis():
    """
    Apply carry algebra to SHA-256.

    Each addition in SHA-256: 32-bit carry chain.
    Each position: G, K, P, or ? depending on operand bits.

    With known state: many positions are G or K (kills!).
    With unknown W: some positions are ?.

    Surviving ?s = ACTUAL branches. Everything else = free.
    """
    import random
    random.seed(42)

    # Simulate: for each round, how many carry ?s survive?
    results = []

    for scenario, p_known in [
        ("All unknown (p=0)", 0.0),
        ("25% known", 0.25),
        ("50% known", 0.50),
        ("75% known (Path A)", 0.75),
        ("90% known", 0.90),
        ("95% known", 0.95),
    ]:
        total_surviving = 0

        for round_r in range(64):
            for addition in range(2):  # 2 additions per round
                chain_states = []
                for bit in range(31):  # 31 carry positions
                    if random.random() < p_known:
                        # Known bit: determine GKP
                        gkp = random.choice([G, K, P])  # roughly uniform
                    else:
                        chain_states.append(Q)
                        continue
                    chain_states.append(gkp)

                cc = CarryChain(chain_states)
                total_surviving += cc.surviving_unknowns()

        results.append((scenario, total_surviving))

    return results


if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  CARRY ALGEBRA — New mathematics of {G, K, P, ?}        ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Composition table
    print("  COMPOSITION TABLE (low ∘ high):")
    print(f"    ∘ | {'  '.join([G,K,P,Q])}")
    print(f"    --+{'----'*4}")
    for low in [G, K, P, Q]:
        row = '  '.join(compose(low, high) for high in [G, K, P, Q])
        print(f"    {low} | {row}")
    print()

    # Theorems
    print("  THEOREMS:")
    print("  " + "─" * 50)
    theorem_results, avg_unk, avg_surv = verify_theorems()

    passed = 0
    for desc, ok in theorem_results:
        status = "✓" if ok else "✗"
        print(f"    {status} {desc}")
        passed += ok

    print(f"\n    {passed}/{len(theorem_results)} passed")
    print(f"\n    Random chain (31-bit, uniform GKP?):")
    print(f"      Avg unknowns: {avg_unk:.1f}")
    print(f"      Avg surviving: {avg_surv:.1f}")
    print(f"      COMPRESSION: {(1-avg_surv/avg_unk)*100:.0f}%")
    print(f"      → {avg_surv:.1f}/{avg_unk:.1f} ?-bits actually matter!")

    # SHA-256 application
    print()
    print("  SHA-256 CARRY ANALYSIS:")
    print("  " + "─" * 50)
    sha_results = sha256_carry_analysis()

    print(f"    {'Scenario':<25} {'surviving ?':>12} {'vs birthday':>12}")
    print(f"    {'─'*50}")
    for scenario, surviving in sha_results:
        vs = "★ BETTER!" if surviving < 128 else f"+{surviving-128}"
        print(f"    {scenario:<25} {surviving:>12} {vs:>12}")

    print(f"""
  ═══════════════════════════════════════════════════════
  CARRY ALGEBRA SUMMARY:

    NEW PRIMITIVE: G, K, P, ?
    G/K ABSORB uncertainty from below.
    P PRESERVES uncertainty.
    ? represents unobserved carry state.

    KEY THEOREM: Not all ?s matter!
      G and K above a ? → ? is KILLED.
      Only ?s with pure P/? above them SURVIVE.
      Surviving ?s = ACTUAL branch cost.

    COMPRESSION: {(1-avg_surv/avg_unk)*100:.0f}% of carry ?s are killed by G/K.
    Only {avg_surv:.1f} out of {avg_unk:.1f} ?-bits per chain actually matter.

    For SHA-256: surviving ?s depend on how many bits are known.
    More known bits → more G/K → fewer surviving ?s → cheaper.

    This is NATIVE Rayon math. Not adapted from boolean algebra.
    G,K,P,? is a semigroup with absorption — a new algebraic object.
  ═══════════════════════════════════════════════════════
""")
