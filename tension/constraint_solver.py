"""
CONSTRAINT SOLVER — Collect constraints from bidirectional, solve algebraically.

Bidirectional propagation through a circuit produces:
  1. KNOWN values (fully determined)
  2. LINEAR constraints: a XOR b = c (solvable by GF(2) Gaussian elim)
  3. NONLINEAR constraints: a AND b = c (branching required)

Total search cost = 2^{nonlinear constraints} × poly(linear constraints)

The fewer nonlinear constraints remain: the easier the problem.
"""

import numpy as np
from bidirectional import GateNetwork


class ConstraintCollector(GateNetwork):
    """
    Extends GateNetwork to COLLECT constraints instead of just propagating.

    After bidirectional propagation: remaining unknown relationships
    are extracted as linear (XOR) and nonlinear (AND) constraints.
    """

    def __init__(self):
        super().__init__()
        self.xor_constraints = []   # (var1, var2, result_val)
        self.and_constraints = []   # (var1, var2, result_val)
        self.known_vars = {}        # var → value

    def collect_constraints(self):
        """
        After propagation: scan all gates.
        Fully known gates → skip.
        Partially known → extract constraint.
        """
        self.xor_constraints = []
        self.and_constraints = []
        self.known_vars = {k: v for k, v in self.nodes.items() if v is not None}

        unknown_vars = set(k for k, v in self.nodes.items() if v is None)

        for gt, in1, in2, out in self.gates:
            v1 = self.nodes.get(in1)
            v2 = self.nodes.get(in2)
            vo = self.nodes.get(out)

            # Count unknowns in this gate
            unknowns = sum(1 for v in [v1, v2, vo] if v is None)

            if unknowns == 0:
                continue  # fully resolved

            if gt == 'XOR':
                # XOR(a, b) = c: ONE unknown → solvable
                # TWO unknowns → linear constraint: a XOR b = c
                if unknowns == 1:
                    # One unknown: directly solvable (already handled by propagation)
                    pass
                elif unknowns == 2:
                    # Two unknowns: linear constraint
                    unknown_names = [n for n in [in1, in2, out] if self.nodes.get(n) is None]
                    known_name = [n for n in [in1, in2, out] if self.nodes.get(n) is not None]
                    if known_name:
                        self.xor_constraints.append((unknown_names[0], unknown_names[1],
                                                     self.nodes[known_name[0]]))
                elif unknowns == 3:
                    self.xor_constraints.append((in1, in2, out))  # all three unknown

            elif gt == 'AND':
                if unknowns >= 1:
                    self.and_constraints.append((in1, in2, out, v1, v2, vo))

        return len(self.xor_constraints), len(self.and_constraints)

    def solve_linear(self):
        """
        Solve XOR (linear) constraints by GF(2) Gaussian elimination.

        Each constraint: var1 XOR var2 = constant (or var3).
        This is a system of linear equations over GF(2).
        """
        if not self.xor_constraints:
            return 0

        # Collect all unknown variable names
        unknown_set = set()
        for c in self.xor_constraints:
            for name in c[:2]:
                if self.nodes.get(name) is None:
                    unknown_set.add(name)
            if len(c) == 3 and isinstance(c[2], str) and self.nodes.get(c[2]) is None:
                unknown_set.add(c[2])

        unknowns = sorted(unknown_set)
        var_idx = {name: i for i, name in enumerate(unknowns)}
        n_vars = len(unknowns)

        if n_vars == 0:
            return 0

        # Build GF(2) matrix
        equations = []
        for c in self.xor_constraints:
            row = np.zeros(n_vars + 1, dtype=np.int8)
            for name in c[:2]:
                if name in var_idx:
                    row[var_idx[name]] ^= 1

            # RHS
            if isinstance(c[2], int):
                row[n_vars] = c[2]
            elif isinstance(c[2], str):
                if c[2] in var_idx:
                    row[var_idx[c[2]]] ^= 1  # move to LHS
                elif self.nodes.get(c[2]) is not None:
                    row[n_vars] = self.nodes[c[2]]

            equations.append(row)

        if not equations:
            return 0

        A = np.array(equations, dtype=np.int8)
        m, n_cols = A.shape
        n = n_cols - 1  # number of variables

        # Gaussian elimination over GF(2)
        pivot_row = 0
        pivot_cols = []
        for col in range(n):
            found = -1
            for row in range(pivot_row, m):
                if A[row, col]:
                    found = row
                    break
            if found < 0:
                continue
            if found != pivot_row:
                A[[pivot_row, found]] = A[[found, pivot_row]]
            pivot_cols.append(col)
            for row in range(m):
                if row != pivot_row and A[row, col]:
                    A[row] = (A[row] + A[pivot_row]) % 2
            pivot_row += 1

        # Extract solutions for pivot variables
        solved = 0
        for i, col in enumerate(pivot_cols):
            rhs = A[i, n]
            # Check if this determines the variable
            other_unknowns = sum(A[i, j] for j in range(n) if j != col and j not in pivot_cols[:i+1])
            if other_unknowns == 0:
                # Variable is determined
                var_name = unknowns[col]
                self.nodes[var_name] = int(rhs)
                solved += 1

        # After solving: re-propagate
        if solved > 0:
            self.propagate_full()

        return solved

    def report(self):
        total = len(self.nodes)
        known = self.count_known()
        unknown = self.count_unknown()
        n_xor, n_and = self.collect_constraints()

        print(f"  CONSTRAINT REPORT:")
        print(f"    Total nodes:            {total}")
        print(f"    Known:                  {known}")
        print(f"    Unknown:                {unknown}")
        print(f"    XOR constraints:        {n_xor} (linear, solvable)")
        print(f"    AND constraints:        {n_and} (nonlinear, branching)")
        print(f"    Search space:           2^{n_and} × poly({n_xor})")
        print(f"    Effective difficulty:    {n_and} bits of brute force")


# ════════════════════════════════════════════════════════════
# TEST: Build circuits and measure constraint reduction
# ════════════════════════════════════════════════════════════

def test_constraint_solver():
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  CONSTRAINT SOLVER — Algebraic solving after propagation ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Test 1: Pure XOR circuit → all linear → fully solvable
    print("TEST 1: Pure XOR (should be fully solvable)")
    print("─" * 50)

    c = ConstraintCollector()
    for i in range(8): c.input(f'x{i}')

    # XOR chain: y = x0 ^ x1 ^ ... ^ x7
    prev = 'x0'
    for i in range(1, 8):
        prev = c.gate('XOR', prev, f'x{i}')

    c.set(prev, 1)   # output = 1
    c.set('x0', 0)   # one input known

    c.propagate_full()
    n_xor, n_and = c.collect_constraints()
    solved = c.solve_linear()

    print(f"  After propagation: {c.count_known()} known, {c.count_unknown()} unknown")
    print(f"  XOR constraints: {n_xor}, AND constraints: {n_and}")
    print(f"  Linear solve: {solved} variables determined")
    c.propagate_full()
    print(f"  After solve: {c.count_known()} known, {c.count_unknown()} unknown")
    print()

    # Test 2: Mixed AND/XOR → some linear, some nonlinear
    print("TEST 2: Mixed AND/XOR")
    print("─" * 50)

    c2 = ConstraintCollector()
    for i in range(6): c2.input(f'x{i}')

    # x0 XOR x1 = a, x2 XOR x3 = b, AND(a, b) = c, c XOR x4 = d, d XOR x5 = out
    a = c2.gate('XOR', 'x0', 'x1', 'a')
    b = c2.gate('XOR', 'x2', 'x3', 'b')
    cc = c2.gate('AND', a, b, 'c')
    d = c2.gate('XOR', cc, 'x4', 'd')
    out = c2.gate('XOR', d, 'x5', 'out')

    c2.set('out', 1)
    c2.set('x0', 1)

    c2.propagate_full()
    n_xor, n_and = c2.collect_constraints()
    solved = c2.solve_linear()
    c2.propagate_full()
    n_xor2, n_and2 = c2.collect_constraints()

    print(f"  Before solve: XOR={n_xor}, AND={n_and}")
    print(f"  Linear solved: {solved}")
    print(f"  After solve: XOR={n_xor2}, AND={n_and2}")
    print(f"  Known: {c2.count_known()}, Unknown: {c2.count_unknown()}")
    c2.report()
    print()

    # Test 3: SHA-256-like mini circuit
    print("TEST 3: SHA-256-like (Ch + T1 + output)")
    print("─" * 50)

    c3 = ConstraintCollector()
    for name in ['e', 'f', 'g', 'h', 'W', 'K', 'd', 'c1']:
        c3.input(name)

    # Ch(e,f,g)
    ef = c3.gate('AND', 'e', 'f', 'ef')
    not_e = c3.gate('XOR', 'e', 'c1', 'not_e')
    neg = c3.gate('AND', 'not_e', 'g', 'neg')
    ch = c3.gate('XOR', ef, neg, 'ch')

    # T1 = h XOR ch XOR W XOR K
    t1a = c3.gate('XOR', 'h', ch, 't1a')
    t1b = c3.gate('XOR', 'W', 'K', 't1b')
    T1 = c3.gate('XOR', t1a, t1b, 'T1')

    # e_new = d XOR T1
    e_new = c3.gate('XOR', 'd', T1, 'e_new')

    # Know: e (state), h, d, K, const, output
    c3.set('e', 1); c3.set('h', 0); c3.set('d', 1)
    c3.set('K', 1); c3.set('c1', 1); c3.set('e_new', 0)
    # Unknown: f, g, W

    c3.propagate_full()
    n_xor_before, n_and_before = c3.collect_constraints()
    solved = c3.solve_linear()
    c3.propagate_full()
    n_xor_after, n_and_after = c3.collect_constraints()

    print(f"  Before: XOR={n_xor_before}, AND={n_and_before}, unknown={c3.count_unknown()}")
    print(f"  Linear solved: {solved}")
    print(f"  After:  XOR={n_xor_after}, AND={n_and_after}, unknown={c3.count_unknown()}")
    print(f"  f={c3.get('f')}, g={c3.get('g')}, W={c3.get('W')}")
    c3.report()

    print(f"""
═══════════════════════════════════════════════════════════════
CONSTRAINT SOLVER RESULTS:

  Phase 1: Bidirectional propagation → resolve what we can
  Phase 2: Collect remaining constraints (XOR + AND)
  Phase 3: Solve XOR constraints (GF(2) linear algebra)
  Phase 4: Count remaining AND constraints = REAL difficulty

  COST = 2^{{remaining AND constraints}} × poly

  For SHA-256 full:
    512 input bits, 256 output bits, ~20K gates
    After constraint solving: remaining AND = actual search space
    If remaining AND < 128: BETTER than birthday attack!

  THIS IS THE RAYON APPROACH:
    Don't brute force. Don't just propagate.
    COLLECT constraints algebraically. SOLVE the linear part.
    BRANCH only on the nonlinear remainder.
═══════════════════════════════════════════════════════════════
""")


if __name__ == '__main__':
    test_constraint_solver()
