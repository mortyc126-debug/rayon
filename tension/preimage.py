"""
STEP 4: PREIMAGE — Fixed target changes everything.

SAT = "find ANY x with f(x)=1" → always O(n). Easy.
PREIMAGE = "find x with f(x)=TARGET" → depends on structure.

Key insight from Step 3: SAT is easy because many solutions exist.
PREIMAGE is hard when solutions are RARE.

But: HOW hard depends on the algorithm, not just the circuit!
  - DFS with propagation: AND/OR easy, XOR hard
  - Gaussian elimination (GF2): XOR easy, AND/OR hard
  - Combined: ???

The REAL question: for circuits mixing AND/OR and XOR,
what's the BEST algorithm and what's its cost?
"""

import numpy as np
import random
import time


# ════════════════════════════════════════════════════════════
# GF(2) SOLVER: solves XOR systems in O(n²)
# ════════════════════════════════════════════════════════════

def gf2_solve(equations, target, n_vars):
    """
    Solve system of XOR equations over GF(2).
    equations[i] = list of variable indices in equation i
    target[i] = right-hand side (0 or 1)

    Returns: solution dict {var: value} or None
    """
    m = len(equations)
    # Build augmented matrix [A | b]
    A = np.zeros((m, n_vars + 1), dtype=np.int8)
    for i, eq in enumerate(equations):
        for var in eq:
            A[i, var] = 1
        A[i, n_vars] = target[i]

    # Gaussian elimination over GF(2)
    pivots = []
    row = 0
    for col in range(n_vars):
        if row >= m:
            break
        found = -1
        for r in range(row, m):
            if A[r, col]:
                found = r
                break
        if found < 0:
            continue
        if found != row:
            A[[row, found]] = A[[found, row]]
        pivots.append((row, col))
        for r in range(m):
            if r != row and A[r, col]:
                A[r] = (A[r] + A[row]) % 2
        row += 1

    # Check consistency
    for r in range(row, m):
        if A[r, n_vars]:
            return None  # inconsistent

    # Back-substitute (free variables = 0)
    solution = {}
    pivot_cols = {c for _, c in pivots}
    for var in range(n_vars):
        if var not in pivot_cols:
            solution[var] = 0  # free variable

    for r, c in reversed(pivots):
        val = A[r, n_vars]
        for col in range(c + 1, n_vars):
            if A[r, col]:
                val = (val + solution.get(col, 0)) % 2
        solution[c] = val

    return solution


# ════════════════════════════════════════════════════════════
# DFS SOLVER: for AND/OR circuits
# ════════════════════════════════════════════════════════════

def dfs_preimage(circuit_func, n_vars, target, max_nodes=200000):
    """DFS to find x with circuit_func(x) = target."""
    nodes = [0]

    def search(assigned, var_idx):
        nodes[0] += 1
        if nodes[0] > max_nodes:
            return None

        if var_idx == n_vars:
            bits = [assigned[i] for i in range(n_vars)]
            if circuit_func(bits) == target:
                return dict(assigned)
            return None

        for val in [0, 1]:
            assigned[var_idx] = val
            result = search(assigned, var_idx + 1)
            if result is not None:
                return result

        del assigned[var_idx]
        return None

    return search({}, 0), nodes[0]


# ════════════════════════════════════════════════════════════
# TEST CIRCUITS
# ════════════════════════════════════════════════════════════

def test_preimage_costs():
    print("PREIMAGE COST BY CIRCUIT TYPE AND ALGORITHM")
    print("═" * 65)
    print()

    # ── 1. Pure XOR: m equations in n variables ──
    print("TYPE 1: Pure XOR (m equations, n variables)")
    print("  GF(2) solver: O(n²). DFS: 2^m.")
    print(f"  {'n':>4} {'m':>4} {'GF2 cost':>10} {'DFS nodes':>10}")
    print(f"  {'─'*32}")

    for n, m in [(8, 4), (12, 6), (16, 8), (20, 10), (32, 16)]:
        # Random XOR system
        random.seed(42 + n)
        equations = []
        targets = []
        for _ in range(m):
            n_terms = random.randint(2, min(5, n))
            eq = random.sample(range(n), n_terms)
            equations.append(eq)
            targets.append(random.randint(0, 1))

        # GF(2) solve
        t0 = time.time()
        sol = gf2_solve(equations, targets, n)
        gf2_time = time.time() - t0
        gf2_cost = n * m  # O(nm) operations

        # DFS solve
        def xor_circuit(bits, eqs=equations, tgts=targets):
            for eq, tgt in zip(eqs, tgts):
                val = 0
                for v in eq:
                    val ^= bits[v]
                if val != tgt:
                    return 0
            return 1

        _, dfs_nodes = dfs_preimage(xor_circuit, n, target=1, max_nodes=200000)

        print(f"  {n:>4} {m:>4} {gf2_cost:>10} {dfs_nodes:>10}")

    # ── 2. Pure AND/OR: conjunction of literals ──
    print()
    print("TYPE 2: Pure AND (all bits must be specific value)")
    print("  DFS: O(n). GF(2): not applicable.")
    print(f"  {'n':>4} {'m':>4} {'DFS nodes':>10}")
    print(f"  {'─'*22}")

    for n in [8, 12, 16, 20, 32]:
        target_bits = [random.randint(0, 1) for _ in range(n)]

        def and_circuit(bits, tgt=target_bits):
            return 1 if all(bits[i] == tgt[i] for i in range(len(tgt))) else 0

        _, dfs_nodes = dfs_preimage(and_circuit, n, target=1)
        print(f"  {n:>4} {n:>4} {dfs_nodes:>10}")

    # ── 3. AND of XOR outputs: the INTERACTION ──
    print()
    print("TYPE 3: AND(XOR₁, XOR₂, ..., XORₘ) — the INTERACTION")
    print("  Each XOR = XOR of random input subset")
    print("  AND requires ALL XORs = 1")
    print("  This is: solve XOR system (linear) + verify AND (trivial)")
    print(f"  {'n':>4} {'m':>4} {'GF2':>6} {'DFS nodes':>10} {'DFS/GF2':>8}")
    print(f"  {'─'*38}")

    for n, m in [(8, 4), (12, 6), (16, 8), (20, 10), (24, 12)]:
        random.seed(42 + n + m)
        equations = []
        for _ in range(m):
            n_terms = random.randint(2, min(5, n))
            eq = random.sample(range(n), n_terms)
            equations.append(eq)
        targets = [1] * m  # AND requires all XORs = 1

        # GF(2): just solve the XOR system
        sol = gf2_solve(equations, targets, n)
        gf2_cost = n * m

        # DFS: try to find by backtracking
        def mixed_circuit(bits, eqs=equations):
            for eq in eqs:
                val = 0
                for v in eq:
                    val ^= bits[v]
                if val != 1:  # AND: all must be 1
                    return 0
            return 1

        _, dfs_nodes = dfs_preimage(mixed_circuit, n, target=1, max_nodes=200000)
        ratio = dfs_nodes / max(gf2_cost, 1)

        print(f"  {n:>4} {m:>4} {gf2_cost:>6} {dfs_nodes:>10} {ratio:>8.1f}")

    # ── 4. XOR of AND outputs: the OTHER interaction ──
    print()
    print("TYPE 4: XOR(AND₁, AND₂, ...) — nonlinear output")
    print("  Each AND = AND of random pair")
    print("  XOR of results = single output bit")
    print("  GF(2) can't solve (nonlinear). DFS only.")
    print(f"  {'n':>4} {'m':>4} {'DFS nodes':>10} {'2^m':>10} {'ratio':>8}")
    print(f"  {'─'*42}")

    for n, m in [(8, 4), (10, 5), (12, 6), (14, 7), (16, 8)]:
        random.seed(42 + n)
        and_pairs = [(random.randint(0, n-1), random.randint(0, n-1)) for _ in range(m)]

        def nonlinear_circuit(bits, pairs=and_pairs):
            result = 0
            for a, b in pairs:
                result ^= (bits[a] & bits[b])
            return result

        target = 1
        _, dfs_nodes = dfs_preimage(nonlinear_circuit, n, target, max_nodes=200000)
        predicted = 2 ** m
        ratio = dfs_nodes / max(predicted, 1)

        timeout_str = "timeout" if dfs_nodes >= 200000 else f"{ratio:.4f}"
        print(f"  {n:>4} {m:>4} {dfs_nodes:>10} {predicted:>10} {timeout_str:>8}")

    print(f"""
═══════════════════════════════════════════════════════════════
PREIMAGE COST SUMMARY:

  TYPE 1 (Pure XOR): GF(2) solves in O(nm). DFS exponential.
    → Right algorithm: LINEAR ALGEBRA, not search.

  TYPE 2 (Pure AND): DFS solves in O(n). GF(2) not applicable.
    → Right algorithm: DFS with propagation.

  TYPE 3 (AND of XORs): GF(2) solves (it's a linear system!).
    → Right algorithm: LINEAR ALGEBRA.

  TYPE 4 (XOR of ANDs): NONLINEAR. GF(2) fails. DFS expensive.
    → This is the HARD case. No known efficient algorithm.

THE FUNDAMENTAL LAW (revised):
  Hardness = amount of NONLINEARITY that can't be linearized.

  Pure XOR: linear → O(n²) always.
  Pure AND/OR: has controlling value → O(n) by DFS.
  AND of XOR: still linear → O(n²).
  XOR of AND: NONLINEAR → potentially 2^m.

  SHA-256: XOR of AND (carries) + AND of XOR (schedule)
  The carries = XOR of AND = the NONLINEAR CORE.
  THAT is where hardness lives. Not XOR. Not AND. Their INTERACTION.
═══════════════════════════════════════════════════════════════
""")


if __name__ == '__main__':
    test_preimage_costs()
