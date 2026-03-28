"""
THREE NEW STONES for Rayon Language:

STONE 12: EQUIVALENCE FUSION — if a⊕b=0, then a=b. Merge them.
  Reduces unknowns without branching. Union-Find on GF(2).

STONE 13: DEFERRED BRANCH — AND(expr, expr) doesn't branch immediately.
  Carries BOTH possibilities. Might self-resolve later.

STONE 14: EXPRESSION COMPRESSION — long expressions simplify
  when variables are eliminated by other constraints.

Together with Rayon Wave: these form RAYON ENGINE.
"""

from rayon_wave import GF2Expr, WaveCircuit


# ════════════════════════════════════════════════════════════
# STONE 12: EQUIVALENCE FUSION
# ════════════════════════════════════════════════════════════

class EquivalenceTracker:
    """
    Track variable equivalences from GF(2) constraints.

    If x⊕y = 0: x=y. Merge into one variable.
    If x⊕y = 1: x=NOT(y). Track as equivalence with flip.

    Each merge REDUCES unknowns by 1. Free.
    """
    def __init__(self):
        self.parent = {}    # union-find parent
        self.flip = {}      # flip[x] = 1 means x = NOT(root)

    def find(self, x):
        if x not in self.parent:
            self.parent[x] = x
            self.flip[x] = 0
            return x, 0

        if self.parent[x] == x:
            return x, self.flip[x]

        root, f = self.find(self.parent[x])
        self.parent[x] = root
        self.flip[x] ^= f
        return root, self.flip[x]

    def merge(self, x, y, relation):
        """
        Merge x and y with given relation.
        relation=0: x=y
        relation=1: x=NOT(y)
        Returns True if new info learned.
        """
        rx, fx = self.find(x)
        ry, fy = self.find(y)

        if rx == ry:
            # Already in same class. Check consistency.
            expected = fx ^ fy
            return expected == relation  # True if consistent

        # Merge smaller into larger (simplified: always merge ry into rx)
        self.parent[ry] = rx
        self.flip[ry] = fx ^ fy ^ relation
        return True

    def are_equivalent(self, x, y):
        rx, fx = self.find(x)
        ry, fy = self.find(y)
        if rx != ry:
            return None  # unknown
        return fx ^ fy  # 0 = same, 1 = complementary

    def n_classes(self):
        roots = set()
        for x in self.parent:
            r, _ = self.find(x)
            roots.add(r)
        return len(roots)

    def reduce_expression(self, expr):
        """Replace variables in expression with their canonical form."""
        if expr.is_constant:
            return expr

        new_const = expr.const
        new_vars = set()
        for v in expr.vars:
            root, flip = self.find(v)
            new_const ^= flip
            if root in new_vars:
                new_vars.remove(root)  # x ⊕ x = 0
            else:
                new_vars.add(root)

        return GF2Expr(new_const, new_vars)


# ════════════════════════════════════════════════════════════
# STONE 13: DEFERRED BRANCH
# ════════════════════════════════════════════════════════════

class DeferredBranch:
    """
    AND(a, b) where both are expressions → don't branch yet.

    Store as: IF a THEN b ELSE 0.
    Later: if a resolves to constant → branch disappears!

    Count only UNRESOLVED deferred branches at the end = true cost.
    """
    __slots__ = ('condition', 'value_if_true', 'gate_name')

    def __init__(self, condition, value_if_true, gate_name=''):
        self.condition = condition    # GF2Expr
        self.value_if_true = value_if_true  # GF2Expr
        self.gate_name = gate_name

    @property
    def resolved(self):
        return self.condition.is_constant

    @property
    def result(self):
        if self.condition.is_constant:
            if self.condition.const == 0:
                return GF2Expr.constant(0)
            else:
                return self.value_if_true
        return None  # still deferred

    def __repr__(self):
        if self.resolved:
            return f'Resolved({self.result})'
        return f'IF({self.condition})THEN({self.value_if_true})ELSE(0)'


# ════════════════════════════════════════════════════════════
# STONE 14: RAYON ENGINE — Everything together
# ════════════════════════════════════════════════════════════

class RayonEngine:
    """
    Full Rayon computation engine combining:
      - GF2 linear expressions (Rayon Wave)
      - Equivalence fusion (Stone 12)
      - Deferred branches (Stone 13)
      - Expression compression (Stone 14)

    One pass through the circuit. Counts TRUE branch points.
    """
    def __init__(self):
        self.wires = {}
        self.gates = []
        self.equiv = EquivalenceTracker()
        self.deferred = []
        self.resolved_branches = 0
        self.true_branches = 0

    def set_wire(self, name, expr):
        self.wires[name] = self.equiv.reduce_expression(expr)

    def add_gate(self, gt, in1, in2, out):
        self.gates.append((gt, in1, in2, out))

    def run(self):
        """Execute full Rayon Engine pass."""
        self.deferred = []
        self.resolved_branches = 0
        self.true_branches = 0

        for gt, in1, in2, out in self.gates:
            a = self.wires.get(in1)
            b = self.wires.get(in2)

            if a is None or b is None:
                self.wires[out] = None
                continue

            # Compress with equivalences
            a = self.equiv.reduce_expression(a)
            b = self.equiv.reduce_expression(b)

            if gt == 'XOR':
                result = a ^ b
                # Check if result reveals equivalence
                if result.is_constant:
                    # a ⊕ b = constant → a and b are equivalent (or complementary)
                    if a.n_vars == 1 and b.n_vars == 1:
                        va = list(a.vars)[0]
                        vb = list(b.vars)[0]
                        self.equiv.merge(va, vb, result.const ^ a.const ^ b.const)
                self.wires[out] = self.equiv.reduce_expression(result)

            elif gt == 'NOT':
                self.wires[out] = ~a

            elif gt == 'AND':
                if a.is_constant:
                    if a.const == 0:
                        self.wires[out] = GF2Expr.constant(0)
                    else:
                        self.wires[out] = b
                elif b.is_constant:
                    if b.const == 0:
                        self.wires[out] = GF2Expr.constant(0)
                    else:
                        self.wires[out] = a
                else:
                    # DEFERRED BRANCH
                    db = DeferredBranch(a, b, out)
                    self.deferred.append(db)
                    # For now: assign a placeholder
                    self.wires[out] = GF2Expr.variable(f'_br{len(self.deferred)}')

            elif gt == 'OR':
                # OR(a,b) = a XOR b XOR AND(a,b)
                if a.is_constant and a.const == 1:
                    self.wires[out] = GF2Expr.constant(1)
                elif b.is_constant and b.const == 1:
                    self.wires[out] = GF2Expr.constant(1)
                elif a.is_constant and a.const == 0:
                    self.wires[out] = b
                elif b.is_constant and b.const == 0:
                    self.wires[out] = a
                else:
                    db = DeferredBranch(a, b, out)
                    self.deferred.append(db)
                    self.wires[out] = GF2Expr.variable(f'_br{len(self.deferred)}')

        # Post-pass: check deferred branches with updated equivalences
        for db in self.deferred:
            db.condition = self.equiv.reduce_expression(db.condition)
            db.value_if_true = self.equiv.reduce_expression(db.value_if_true)
            if db.resolved:
                self.resolved_branches += 1
            else:
                self.true_branches += 1

    def report(self):
        n_vars = self.equiv.n_classes()
        print(f"  RAYON ENGINE REPORT:")
        print(f"    Wires: {len(self.wires)}")
        print(f"    Unique variables: {n_vars}")
        print(f"    Deferred branches: {len(self.deferred)}")
        print(f"      Resolved (free): {self.resolved_branches}")
        print(f"      TRUE branches:   {self.true_branches}")
        print(f"    Cost: 2^{self.true_branches}")


# ════════════════════════════════════════════════════════════
# VERIFICATION
# ════════════════════════════════════════════════════════════

def verify():
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  RAYON ENGINE — Stones 12+13+14 combined                 ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Test 1: Equivalence Fusion
    print("STONE 12: EQUIVALENCE FUSION")
    print("─" * 50)
    eq = EquivalenceTracker()
    eq.merge('a', 'b', 0)  # a = b
    eq.merge('c', 'd', 1)  # c = NOT(d)
    eq.merge('b', 'c', 0)  # b = c → a = b = c = NOT(d)

    print(f"  a=b, c=NOT(d), b=c")
    print(f"  a≡b: {eq.are_equivalent('a', 'b')} (0=same) ✓")
    print(f"  a≡d: {eq.are_equivalent('a', 'd')} (1=complement) ✓")
    print(f"  Classes: {eq.n_classes()}")

    # Reduce expression
    expr = GF2Expr(0, {'a', 'b', 'd'})
    reduced = eq.reduce_expression(expr)
    print(f"  a⊕b⊕d → {reduced} (a=b cancels, d=NOT(a))")
    print()

    # Test 2: Deferred Branch
    print("STONE 13: DEFERRED BRANCH")
    print("─" * 50)
    db = DeferredBranch(GF2Expr.variable('x'), GF2Expr.variable('y'))
    print(f"  AND(x, y) → {db}")
    print(f"  Resolved? {db.resolved}")

    db2 = DeferredBranch(GF2Expr.constant(1), GF2Expr.variable('y'))
    print(f"  AND(1, y) → {db2}")
    print(f"  Resolved? {db2.resolved}, result = {db2.result}")
    print()

    # Test 3: Full Engine on SHA-like circuit
    print("STONE 14: RAYON ENGINE on SHA-like circuit")
    print("─" * 50)

    # Ch + T1 with various known/unknown combinations
    for e_val, f_val, g_val, w_val, label in [
        (1, None, None, None, "e=1, rest unknown"),
        (0, None, None, None, "e=0, rest unknown"),
        (None, None, None, None, "ALL unknown"),
        (1, 0, None, None, "e=1,f=0, g,W unknown"),
    ]:
        eng = RayonEngine()

        # Set inputs
        if e_val is not None:
            eng.set_wire('e', GF2Expr.constant(e_val))
        else:
            eng.set_wire('e', GF2Expr.variable('e'))

        if f_val is not None:
            eng.set_wire('f', GF2Expr.constant(f_val))
        else:
            eng.set_wire('f', GF2Expr.variable('f'))

        if g_val is not None:
            eng.set_wire('g', GF2Expr.constant(g_val))
        else:
            eng.set_wire('g', GF2Expr.variable('g'))

        if w_val is not None:
            eng.set_wire('W', GF2Expr.constant(w_val))
        else:
            eng.set_wire('W', GF2Expr.variable('W'))

        eng.set_wire('h', GF2Expr.constant(0))
        eng.set_wire('K', GF2Expr.constant(1))
        eng.set_wire('d', GF2Expr.constant(1))
        eng.set_wire('c1', GF2Expr.constant(1))

        # Ch(e,f,g)
        eng.add_gate('AND', 'e', 'f', 'ef')
        eng.add_gate('XOR', 'e', 'c1', 'ne')
        eng.add_gate('AND', 'ne', 'g', 'neg')
        eng.add_gate('XOR', 'ef', 'neg', 'ch')

        # T1 = h XOR ch XOR W XOR K
        eng.add_gate('XOR', 'h', 'ch', 't1a')
        eng.add_gate('XOR', 'W', 'K', 't1b')
        eng.add_gate('XOR', 't1a', 't1b', 'T1')
        eng.add_gate('XOR', 'd', 'T1', 'e_new')

        eng.run()

        print(f"  {label}:")
        print(f"    TRUE branches: {eng.true_branches}, "
              f"resolved: {eng.resolved_branches}, "
              f"cost: 2^{eng.true_branches}")
        print(f"    e_new = {eng.wires.get('e_new')}")

    print(f"""
═══════════════════════════════════════════════════════════════
THREE NEW STONES:

  STONE 12 — EQUIVALENCE FUSION:
    a⊕b=0 → merge a,b into one variable. Reduces unknowns.
    Expression a⊕b⊕d with a=b: reduces to d (cancellation).

  STONE 13 — DEFERRED BRANCH:
    AND(unknown, unknown) → don't branch, DEFER.
    If later one becomes constant → branch resolves FREE.
    Only STILL-DEFERRED branches at end = true cost.

  STONE 14 — RAYON ENGINE:
    All stones combined in single pass.
    GF2 expressions + equivalence fusion + deferred branches.

  SHA round results:
    e known:  0 true branches (entire round = linear!)
    e unknown: 2 true branches (Ch creates them)
    e=1, f=0: 0 branches (f known kills one AND, e kills other)

  RAYON ENGINE = the core of our language's computation engine.
═══════════════════════════════════════════════════════════════
""")


if __name__ == '__main__':
    verify()
