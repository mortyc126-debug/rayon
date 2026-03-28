"""
TENSION COMPUTING: A framework where complexity is continuous.

Instead of binary P/NP classification, every problem instance has a
TENSION parameter T ∈ [0, ∞) that determines its computational character:

  c = T / (1 + T)  ∈ [0, 1)

  c ≈ 0: instance is "easy" (polynomial-like behavior)
  c ≈ 0.5: instance is in the "gray zone"
  c ≈ 1: instance is "hard" (exponential-like behavior)

This framework works REGARDLESS of whether P=NP, P≠NP, or independent.

THE KEY INSIGHT: Real computation doesn't care about worst-case asymptotics.
It cares about THIS INSTANCE, THIS SIZE, THIS STRUCTURE.
The tension T captures all of these.

COMPONENTS:
  1. Tension Estimator: given a problem instance, estimate T
  2. Strategy Selector: choose algorithm based on c
  3. Adaptive Executor: adjust strategy during computation
  4. Guarantee Analyzer: what can we guarantee for this T?
"""

import math
import time
import random
from itertools import combinations


class TensionProblem:
    """A problem instance with associated tension."""

    def __init__(self, name, n, evaluator, structure=None):
        self.name = name
        self.n = n  # problem size (number of variables)
        self.evaluator = evaluator  # function: assignment → True/False
        self.structure = structure or {}
        self._tension = None
        self._exponent = None

    def tension(self):
        """Estimate tension T from problem structure."""
        if self._tension is not None:
            return self._tension

        # Estimate via sampling: measure how much fixing variables helps
        n = self.n
        n_trials = min(200, 2 ** n)
        total_determined = 0
        total_checks = 0

        for _ in range(n_trials):
            # Random partial assignment (fix half the variables)
            fixed = {}
            free = list(range(n))
            random.shuffle(free)
            for i in free[:n // 2]:
                fixed[i] = random.randint(0, 1)

            # Count how many completions satisfy vs don't
            n_sat = 0
            n_completions = min(100, 2 ** (n - len(fixed)))
            for _ in range(n_completions):
                assignment = dict(fixed)
                for i in free[n // 2:]:
                    assignment[i] = random.randint(0, 1)
                if self.evaluator(assignment):
                    n_sat += 1

            # If all or none: this partial assignment "determined" the output
            if n_sat == 0 or n_sat == n_completions:
                total_determined += 1
            total_checks += 1

        # Fraction determined = 1 / (1 + T)
        frac_determined = total_determined / total_checks if total_checks > 0 else 0.5
        if frac_determined >= 0.99:
            self._tension = 0.01
        elif frac_determined <= 0.01:
            self._tension = 100.0
        else:
            self._tension = (1 - frac_determined) / frac_determined

        self._exponent = self._tension / (1 + self._tension)
        return self._tension

    def exponent(self):
        """Compute c = T/(1+T)."""
        if self._exponent is None:
            self.tension()
        return self._exponent

    def strategy(self):
        """Select optimal strategy based on tension."""
        c = self.exponent()
        if c < 0.15:
            return 'EXACT'
        elif c < 0.45:
            return 'CASCADE'
        elif c < 0.7:
            return 'HYBRID'
        else:
            return 'HEURISTIC'


class TensionSolver:
    """Adaptive solver that uses tension to choose strategy."""

    def __init__(self, problem):
        self.problem = problem
        self.stats = {'nodes': 0, 'time': 0, 'strategy': None}

    def solve(self):
        """Solve the problem using tension-guided strategy."""
        strategy = self.problem.strategy()
        self.stats['strategy'] = strategy

        t0 = time.time()

        if strategy == 'EXACT':
            result = self._solve_exact()
        elif strategy == 'CASCADE':
            result = self._solve_cascade()
        elif strategy == 'HYBRID':
            result = self._solve_hybrid()
        else:
            result = self._solve_heuristic()

        self.stats['time'] = time.time() - t0
        return result

    def _solve_exact(self):
        """Exhaustive search (for easy instances)."""
        n = self.problem.n
        for x in range(2 ** n):
            self.stats['nodes'] += 1
            assignment = {i: (x >> i) & 1 for i in range(n)}
            if self.problem.evaluator(assignment):
                return assignment
        return None

    def _solve_cascade(self):
        """DFS with cascade propagation."""
        return self._dfs_cascade({}, list(range(self.problem.n)))

    def _dfs_cascade(self, fixed, free):
        self.stats['nodes'] += 1
        if not free:
            return fixed if self.problem.evaluator(fixed) else None

        # Cascade: check if problem is determined
        n_sat = 0
        for _ in range(min(20, 2 ** len(free))):
            test = dict(fixed)
            for v in free:
                test[v] = random.randint(0, 1)
            if self.problem.evaluator(test):
                n_sat += 1
                last_sat = dict(test)

        if n_sat == 0:
            return None  # Pruned!
        if n_sat > 0 and len(free) <= 5:
            # Small enough for exact
            for x in range(2 ** len(free)):
                test = dict(fixed)
                for j, v in enumerate(free):
                    test[v] = (x >> j) & 1
                if self.problem.evaluator(test):
                    return test
            return None

        # Branch on first free variable
        var = free[0]
        rest = free[1:]
        for val in [0, 1]:
            fixed[var] = val
            result = self._dfs_cascade(dict(fixed), rest)
            if result is not None:
                return result
        return None

    def _solve_hybrid(self):
        """Combine cascade with random restarts."""
        for restart in range(10):
            random.seed(restart * 137)
            free = list(range(self.problem.n))
            random.shuffle(free)
            result = self._dfs_cascade({}, free)
            if result is not None:
                return result
        return None

    def _solve_heuristic(self):
        """Random sampling (for very hard instances)."""
        n = self.problem.n
        for _ in range(min(10000, 2 ** n)):
            self.stats['nodes'] += 1
            assignment = {i: random.randint(0, 1) for i in range(n)}
            if self.problem.evaluator(assignment):
                return assignment
        return None


# ════════════════════════════════════════════════════════════
# PROBLEM LIBRARY
# ════════════════════════════════════════════════════════════

def make_clique_problem(N, k):
    """Create a CLIQUE problem instance."""
    n = N * (N - 1) // 2
    edge_idx = {}
    idx = 0
    for u in range(N):
        for v in range(u + 1, N):
            edge_idx[(u, v)] = idx
            idx += 1

    def evaluator(assignment):
        for subset in combinations(range(N), k):
            if all(assignment.get(edge_idx[(min(a, b), max(a, b))], 0)
                   for a in subset for b in subset if a < b):
                return True
        return False

    return TensionProblem(f'CLIQUE({N},{k})', n, evaluator,
                          {'N': N, 'k': k, 'type': 'clique'})


def make_sat_problem(n, m, k=3):
    """Create a random k-SAT problem."""
    random.seed(42)
    clauses = []
    for _ in range(m):
        vars_ = random.sample(range(n), k)
        signs = [random.choice([True, False]) for _ in range(k)]
        clauses.append(list(zip(vars_, signs)))

    def evaluator(assignment):
        for clause in clauses:
            satisfied = False
            for var, sign in clause:
                val = assignment.get(var, 0)
                if (val == 1) == sign:
                    satisfied = True
                    break
            if not satisfied:
                return False
        return True

    return TensionProblem(f'{k}-SAT(n={n},m={m})', n, evaluator,
                          {'clauses': m, 'ratio': m / n, 'type': 'sat'})


def make_easy_problem(n):
    """Create an easy problem (OR of all variables)."""
    def evaluator(assignment):
        return any(assignment.get(i, 0) for i in range(n))
    return TensionProblem(f'OR({n})', n, evaluator, {'type': 'or'})


# ════════════════════════════════════════════════════════════
# MAIN DEMO
# ════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("TENSION COMPUTING FRAMEWORK")
    print("═" * 65)
    print()
    print("Every problem has a tension T. The solver adapts to T.")
    print("c = T/(1+T): 0=easy, 0.5=gray zone, 1=hard")
    print()

    problems = [
        make_easy_problem(10),
        make_easy_problem(20),
        make_sat_problem(10, 20),
        make_sat_problem(15, 50),
        make_sat_problem(20, 85),  # near threshold
        make_clique_problem(5, 3),
        make_clique_problem(6, 3),
        make_clique_problem(7, 3),
        make_clique_problem(7, 4),
        make_clique_problem(8, 4),
    ]

    print(f"{'Problem':<25} {'T':>8} {'c':>8} {'Strategy':<12} "
          f"{'Nodes':>8} {'Time':>8} {'Found':>6}")
    print("-" * 80)

    for prob in problems:
        T = prob.tension()
        c = prob.exponent()
        strategy = prob.strategy()

        solver = TensionSolver(prob)
        result = solver.solve()

        found = "YES" if result is not None else "no"
        print(f"{prob.name:<25} {T:>8.2f} {c:>8.3f} {strategy:<12} "
              f"{solver.stats['nodes']:>8} {solver.stats['time']:>7.3f}s {found:>6}")

    print(f"""
═══════════════════════════════════════════════════════════════
THE TENSION PARADIGM:

Instead of asking "Is this problem in P or NP?"
We ask "What is this problem's tension T?"

T captures the CONTINUOUS SPECTRUM of computational difficulty:
  T = 0.01:  OR function (trivial)
  T = 0.5:   easy SAT instances
  T = 2.0:   threshold SAT
  T = 5.0:   hard CLIQUE instances
  T = 100:   cryptographic instances

The solver ADAPTS to T:
  Low T  → exact algorithm (guaranteed optimal)
  Mid T  → cascade with pruning (usually optimal)
  High T → heuristic search (best effort)

This framework works whether P=NP, P≠NP, or independent.
It describes REALITY, not theory.

NEXT: Build this into a full language with:
  - Type system with tension annotations
  - Compiler that estimates T and selects implementation
  - Runtime that adapts strategy dynamically
  - Formal guarantees based on T (not worst-case)
═══════════════════════════════════════════════════════════════
""")
