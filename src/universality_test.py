"""
UNIVERSALITY TEST: Is the hardness exponent c = log₂(DFS_nodes)/n
an intrinsic circuit invariant, or does it depend on the algorithm?

We test c across FIVE DFS algorithm variants:
  1. DFS with random variable ordering (10 different random orders)
  2. DFS with most-constrained variable ordering
  3. DFS with least-constrained variable ordering
  4. DFS with value ordering (try more promising value first)
  5. DFS with random restarts

Test circuits:
  - Random circuits (n=10..20, density=3..10)
  - Structured CLIQUE circuits (N=6,7,8 with k=3)

If c is stable across algorithms: it is a CIRCUIT INVARIANT → T is intrinsic.
If c varies widely: T depends on the algorithm → equation of state is not universal.
"""

import math
import random
import sys
import time
from collections import defaultdict
from itertools import combinations

# ═══════════════════════════════════════════════════════════════
# Circuit construction
# ═══════════════════════════════════════════════════════════════

def make_random_circuit(n, density, seed=42):
    """Random circuit with given density = s/n."""
    random.seed(seed)
    s = int(density * n)
    gates = []
    for i in range(s):
        gt = random.choice(['AND', 'OR'])
        available = list(range(n + i))
        i1 = random.choice(available)
        i2 = random.choice(available)
        while i2 == i1 and len(available) > 1:
            i2 = random.choice(available)
        gates.append((gt, i1, i2, n + i))
    return gates, n


def make_clique_circuit(N, k):
    """Circuit for k-CLIQUE on N vertices. Returns (gates, n_inputs)."""
    n_edges = N * (N - 1) // 2
    edge_var = {}
    idx = 0
    for u in range(N):
        for v in range(u + 1, N):
            edge_var[(u, v)] = idx
            idx += 1

    gates = []
    nid = n_edges

    clique_outputs = []
    for subset in combinations(range(N), k):
        edges = []
        for i in range(len(subset)):
            for j in range(i + 1, len(subset)):
                u, v = subset[i], subset[j]
                edges.append(edge_var[(u, v)])
        if not edges:
            continue
        cur = edges[0]
        for e in edges[1:]:
            out = nid
            gates.append(('AND', cur, e, out))
            nid += 1
            cur = out
        clique_outputs.append(cur)

    if not clique_outputs:
        return gates, n_edges
    cur = clique_outputs[0]
    for c in clique_outputs[1:]:
        out = nid
        gates.append(('OR', cur, c, out))
        nid += 1
        cur = out

    return gates, n_edges


# ═══════════════════════════════════════════════════════════════
# Propagation (cascade)
# ═══════════════════════════════════════════════════════════════

def propagate(gates, n, fixed):
    """Propagate constants through circuit. Return output value or None."""
    wv = dict(fixed)
    for gt, i1, i2, o in gates:
        v1 = wv.get(i1)
        v2 = wv.get(i2)
        if gt == 'AND':
            if v1 == 0 or v2 == 0:
                wv[o] = 0
            elif v1 is not None and v2 is not None:
                wv[o] = v1 & v2
        elif gt == 'OR':
            if v1 == 1 or v2 == 1:
                wv[o] = 1
            elif v1 is not None and v2 is not None:
                wv[o] = v1 | v2
        elif gt == 'NOT':
            if v1 is not None:
                wv[o] = 1 - v1
    return wv.get(gates[-1][3]) if gates else None


def propagate_count(gates, n, fixed):
    """Count how many gates get determined after propagation."""
    wv = dict(fixed)
    det = 0
    for gt, i1, i2, o in gates:
        v1 = wv.get(i1)
        v2 = wv.get(i2)
        d = False
        if gt == 'AND':
            if v1 == 0 or v2 == 0:
                wv[o] = 0; d = True
            elif v1 is not None and v2 is not None:
                wv[o] = v1 & v2; d = True
        elif gt == 'OR':
            if v1 == 1 or v2 == 1:
                wv[o] = 1; d = True
            elif v1 is not None and v2 is not None:
                wv[o] = v1 | v2; d = True
        elif gt == 'NOT':
            if v1 is not None:
                wv[o] = 1 - v1; d = True
        if d:
            det += 1
    return det


# ═══════════════════════════════════════════════════════════════
# DFS Algorithm Variants
# ═══════════════════════════════════════════════════════════════

NODE_LIMIT = 2_000_000  # abort if search tree exceeds this


class SearchAborted(Exception):
    pass


def _dfs_core(gates, n, fixed, stats, var_order_fn, val_order_fn):
    """Core DFS with pluggable variable and value ordering."""
    stats['nodes'] += 1
    if stats['nodes'] > NODE_LIMIT:
        raise SearchAborted()

    out = propagate(gates, n, fixed)
    if out is not None:
        return out == 1

    unfixed = [v for v in range(n) if v not in fixed]
    if not unfixed:
        return False

    var = var_order_fn(unfixed, gates, n, fixed)
    values = val_order_fn(var, gates, n, fixed)

    for val in values:
        fixed[var] = val
        if _dfs_core(gates, n, fixed, stats, var_order_fn, val_order_fn):
            del fixed[var]
            return True
        del fixed[var]
    return False


# --- Variable ordering strategies ---

def var_order_sequential(unfixed, gates, n, fixed):
    """Pick first unfixed variable (default DFS)."""
    return unfixed[0]


def var_order_random(seed):
    """Return a variable ordering function that uses a fixed random permutation."""
    def fn(unfixed, gates, n, fixed):
        rng = random.Random(seed + len(fixed))
        return rng.choice(unfixed)
    return fn


def var_order_most_constrained(unfixed, gates, n, fixed):
    """Pick variable appearing in most undetermined gates."""
    # Count how many undetermined gates each unfixed variable feeds
    wv = dict(fixed)
    for gt, i1, i2, o in gates:
        v1 = wv.get(i1)
        v2 = wv.get(i2)
        if gt == 'AND':
            if v1 == 0 or v2 == 0:
                wv[o] = 0
            elif v1 is not None and v2 is not None:
                wv[o] = v1 & v2
        elif gt == 'OR':
            if v1 == 1 or v2 == 1:
                wv[o] = 1
            elif v1 is not None and v2 is not None:
                wv[o] = v1 | v2

    # Find undetermined gates
    undetermined_inputs = defaultdict(int)
    for gt, i1, i2, o in gates:
        if o not in wv:  # gate not determined
            if i1 < n and i1 not in fixed:
                undetermined_inputs[i1] += 1
            if i2 < n and i2 not in fixed:
                undetermined_inputs[i2] += 1

    unfixed_set = set(unfixed)
    best = unfixed[0]
    best_count = undetermined_inputs.get(unfixed[0], 0)
    for v in unfixed[1:]:
        c = undetermined_inputs.get(v, 0)
        if c > best_count:
            best_count = c
            best = v
    return best


def var_order_least_constrained(unfixed, gates, n, fixed):
    """Pick variable appearing in fewest undetermined gates."""
    wv = dict(fixed)
    for gt, i1, i2, o in gates:
        v1 = wv.get(i1)
        v2 = wv.get(i2)
        if gt == 'AND':
            if v1 == 0 or v2 == 0:
                wv[o] = 0
            elif v1 is not None and v2 is not None:
                wv[o] = v1 & v2
        elif gt == 'OR':
            if v1 == 1 or v2 == 1:
                wv[o] = 1
            elif v1 is not None and v2 is not None:
                wv[o] = v1 | v2

    undetermined_inputs = defaultdict(int)
    for gt, i1, i2, o in gates:
        if o not in wv:
            if i1 < n and i1 not in fixed:
                undetermined_inputs[i1] += 1
            if i2 < n and i2 not in fixed:
                undetermined_inputs[i2] += 1

    best = unfixed[0]
    best_count = undetermined_inputs.get(unfixed[0], float('inf'))
    for v in unfixed[1:]:
        c = undetermined_inputs.get(v, 0)
        if c < best_count:
            best_count = c
            best = v
    return best


# --- Value ordering strategies ---

def val_order_default(var, gates, n, fixed):
    """Try 0 then 1."""
    return [0, 1]


def val_order_promising(var, gates, n, fixed):
    """Try the value that determines more gates first."""
    counts = []
    for val in [0, 1]:
        fixed[var] = val
        det = propagate_count(gates, n, fixed)
        counts.append((det, val))
        del fixed[var]
    counts.sort(reverse=True)  # more determined = try first
    return [c[1] for c in counts]


# --- High-level algorithm wrappers ---

def run_dfs_sequential(gates, n):
    """Algorithm 1: Standard DFS, sequential variable order."""
    stats = {'nodes': 0}
    try:
        _dfs_core(gates, n, {}, stats, var_order_sequential, val_order_default)
    except SearchAborted:
        pass
    return stats['nodes']


def run_dfs_random(gates, n, seed):
    """Algorithm 2: DFS with random variable ordering."""
    stats = {'nodes': 0}
    try:
        _dfs_core(gates, n, {}, stats, var_order_random(seed), val_order_default)
    except SearchAborted:
        pass
    return stats['nodes']


def run_dfs_most_constrained(gates, n):
    """Algorithm 3: DFS with most-constrained variable ordering."""
    stats = {'nodes': 0}
    try:
        _dfs_core(gates, n, {}, stats, var_order_most_constrained, val_order_default)
    except SearchAborted:
        pass
    return stats['nodes']


def run_dfs_least_constrained(gates, n):
    """Algorithm 4: DFS with least-constrained variable ordering."""
    stats = {'nodes': 0}
    try:
        _dfs_core(gates, n, {}, stats, var_order_least_constrained, val_order_default)
    except SearchAborted:
        pass
    return stats['nodes']


def run_dfs_value_ordering(gates, n):
    """Algorithm 5: DFS with value ordering (try promising value first)."""
    stats = {'nodes': 0}
    try:
        _dfs_core(gates, n, {}, stats, var_order_sequential, val_order_promising)
    except SearchAborted:
        pass
    return stats['nodes']


def run_dfs_random_restarts(gates, n, num_restarts=5, budget_per_restart=None):
    """Algorithm 6: DFS with random restarts."""
    if budget_per_restart is None:
        budget_per_restart = NODE_LIMIT // num_restarts

    best_nodes = None
    for restart in range(num_restarts):
        stats = {'nodes': 0}
        limit = budget_per_restart

        def var_fn(unfixed, gates, n, fixed, _seed=restart * 9999):
            rng = random.Random(_seed + len(fixed))
            return rng.choice(unfixed)

        try:
            old_limit = NODE_LIMIT
            # Use a local abort mechanism
            found = [False]

            def _dfs_restart(gates, n, fixed, stats, var_fn, limit_ref):
                stats['nodes'] += 1
                if stats['nodes'] > limit_ref[0]:
                    raise SearchAborted()
                out = propagate(gates, n, fixed)
                if out is not None:
                    return out == 1
                unfixed = [v for v in range(n) if v not in fixed]
                if not unfixed:
                    return False
                var = var_fn(unfixed, gates, n, fixed)
                for val in [0, 1]:
                    fixed[var] = val
                    if _dfs_restart(gates, n, fixed, stats, var_fn, limit_ref):
                        del fixed[var]
                        return True
                    del fixed[var]
                return False

            _dfs_restart(gates, n, {}, stats, var_fn, [budget_per_restart])
        except SearchAborted:
            pass

        if best_nodes is None or stats['nodes'] < best_nodes:
            best_nodes = stats['nodes']

    return best_nodes if best_nodes is not None else 1


# ═══════════════════════════════════════════════════════════════
# Main experiment
# ═══════════════════════════════════════════════════════════════

def compute_c(nodes, n):
    """Compute hardness exponent c = log2(nodes) / n."""
    if nodes <= 1:
        return 0.0
    return math.log2(nodes) / n


def run_all_algorithms(gates, n, label="", timeout=10.0):
    """Run all algorithm variants on the given circuit.
    Returns dict of {algorithm_name: c_value}."""
    results = {}

    algorithms = [
        ("sequential", lambda g, n_: run_dfs_sequential(g, n_)),
        ("most_constr", lambda g, n_: run_dfs_most_constrained(g, n_)),
        ("least_constr", lambda g, n_: run_dfs_least_constrained(g, n_)),
        ("value_order", lambda g, n_: run_dfs_value_ordering(g, n_)),
        ("restart", lambda g, n_: run_dfs_random_restarts(g, n_)),
    ]

    # Add 10 random orderings
    for seed in range(10):
        algorithms.append(
            (f"random_{seed}", lambda g, n_, s=seed: run_dfs_random(g, n_, s))
        )

    t_start = time.time()
    for name, fn in algorithms:
        if time.time() - t_start > timeout:
            break
        t0 = time.time()
        nodes = fn(gates, n)
        dt = time.time() - t0
        c = compute_c(nodes, n)
        results[name] = {'nodes': nodes, 'c': c, 'time': dt}

    return results


def analyze_universality(results):
    """Analyze whether c is invariant across algorithms."""
    c_vals = [r['c'] for r in results.values() if r['c'] > 0]
    if len(c_vals) < 2:
        return None

    c_min = min(c_vals)
    c_max = max(c_vals)
    c_mean = sum(c_vals) / len(c_vals)
    c_var = sum((c - c_mean) ** 2 for c in c_vals) / len(c_vals)
    c_std = math.sqrt(c_var)
    ratio = c_min / c_max if c_max > 0 else 1.0
    cv = c_std / c_mean if c_mean > 0 else 0.0  # coefficient of variation

    return {
        'c_min': c_min,
        'c_max': c_max,
        'c_mean': c_mean,
        'c_std': c_std,
        'ratio': ratio,
        'cv': cv,
        'n_algs': len(c_vals),
    }


def main():
    print("=" * 78)
    print("  UNIVERSALITY TEST: Is c = log2(DFS_nodes)/n a circuit invariant?")
    print("=" * 78)
    print()

    all_analyses = []

    # ── Part A: Random circuits ──────────────────────────────────────────
    print("PART A: RANDOM CIRCUITS")
    print("-" * 78)
    print(f"{'circuit':<22} {'n':>3} {'d':>3} "
          f"{'c_min':>7} {'c_max':>7} {'c_mean':>7} {'c_std':>7} "
          f"{'min/max':>7} {'CV':>7} {'#alg':>5}")
    print("-" * 78)

    for n in [10, 12, 14, 16, 18, 20]:
        for density in [3, 5, 8, 10]:
            gates, n_inp = make_random_circuit(n, density, seed=n * 100 + density)

            # Quick check: skip if trivial or too hard
            test_stats = {'nodes': 0}
            t0 = time.time()
            try:
                _dfs_core(gates, n_inp, {}, test_stats,
                          var_order_sequential, val_order_default)
            except SearchAborted:
                pass
            dt = time.time() - t0

            if test_stats['nodes'] <= 2:
                continue  # trivial
            if test_stats['nodes'] >= NODE_LIMIT:
                continue  # too hard for full comparison

            # Run all algorithms
            timeout = max(30.0, dt * 20)
            results = run_all_algorithms(gates, n_inp,
                                         label=f"rand_n{n}_d{density}",
                                         timeout=timeout)
            analysis = analyze_universality(results)
            if analysis is None:
                continue

            label = f"rand_n{n}_d{density}"
            print(f"{label:<22} {n:>3} {density:>3} "
                  f"{analysis['c_min']:>7.3f} {analysis['c_max']:>7.3f} "
                  f"{analysis['c_mean']:>7.3f} {analysis['c_std']:>7.3f} "
                  f"{analysis['ratio']:>7.3f} {analysis['cv']:>7.3f} "
                  f"{analysis['n_algs']:>5}")
            analysis['label'] = label
            analysis['n'] = n
            analysis['type'] = 'random'
            all_analyses.append(analysis)

    # ── Part B: CLIQUE circuits ──────────────────────────────────────────
    print()
    print("PART B: CLIQUE CIRCUITS (structured)")
    print("-" * 78)
    print(f"{'circuit':<22} {'n':>3} {'d':>3} "
          f"{'c_min':>7} {'c_max':>7} {'c_mean':>7} {'c_std':>7} "
          f"{'min/max':>7} {'CV':>7} {'#alg':>5}")
    print("-" * 78)

    for N in [6, 7, 8]:
        k = 3
        gates, n_inp = make_clique_circuit(N, k)
        n_gates = len(gates)
        label = f"CLIQUE_{N}_k{k}"

        # Quick feasibility check
        test_stats = {'nodes': 0}
        t0 = time.time()
        try:
            _dfs_core(gates, n_inp, {}, test_stats,
                      var_order_sequential, val_order_default)
        except SearchAborted:
            pass
        dt = time.time() - t0

        if test_stats['nodes'] <= 2:
            print(f"{label:<22} {n_inp:>3} {n_gates//max(n_inp,1):>3}  "
                  f"TRIVIAL (nodes={test_stats['nodes']})")
            continue

        timeout = max(60.0, dt * 20)
        results = run_all_algorithms(gates, n_inp, label=label, timeout=timeout)
        analysis = analyze_universality(results)
        if analysis is None:
            print(f"{label:<22} {n_inp:>3}    INSUFFICIENT DATA")
            continue

        dens = n_gates // max(n_inp, 1)
        print(f"{label:<22} {n_inp:>3} {dens:>3} "
              f"{analysis['c_min']:>7.3f} {analysis['c_max']:>7.3f} "
              f"{analysis['c_mean']:>7.3f} {analysis['c_std']:>7.3f} "
              f"{analysis['ratio']:>7.3f} {analysis['cv']:>7.3f} "
              f"{analysis['n_algs']:>5}")
        analysis['label'] = label
        analysis['n'] = n_inp
        analysis['type'] = 'clique'
        all_analyses.append(analysis)

        # Print per-algorithm detail for CLIQUE
        print(f"  {'algorithm':<18} {'nodes':>10} {'c':>8} {'time':>8}")
        for alg_name, r in sorted(results.items(), key=lambda x: x[1]['c']):
            print(f"  {alg_name:<18} {r['nodes']:>10} {r['c']:>8.4f} "
                  f"{r['time']:>7.3f}s")

    # ── Summary statistics ───────────────────────────────────────────────
    print()
    print("=" * 78)
    print("  SUMMARY: UNIVERSALITY ANALYSIS")
    print("=" * 78)
    print()

    if not all_analyses:
        print("  No data collected (circuits were trivial or too hard).")
        return

    # Overall statistics
    ratios = [a['ratio'] for a in all_analyses]
    cvs = [a['cv'] for a in all_analyses]

    print(f"  Total circuits tested: {len(all_analyses)}")
    print(f"  c_min / c_max ratio (universality measure):")
    print(f"    Average:  {sum(ratios)/len(ratios):.4f}")
    print(f"    Minimum:  {min(ratios):.4f}")
    print(f"    Maximum:  {max(ratios):.4f}")
    print()
    print(f"  Coefficient of variation of c (lower = more universal):")
    print(f"    Average:  {sum(cvs)/len(cvs):.4f}")
    print(f"    Maximum:  {max(cvs):.4f}")
    print()

    # Convergence with n
    random_analyses = [a for a in all_analyses if a['type'] == 'random']
    if random_analyses:
        n_groups = defaultdict(list)
        for a in random_analyses:
            n_groups[a['n']].append(a['ratio'])

        print("  Convergence of ratio with n (random circuits):")
        print(f"  {'n':>5} {'avg ratio':>10} {'count':>6}")
        for n_val in sorted(n_groups.keys()):
            rs = n_groups[n_val]
            print(f"  {n_val:>5} {sum(rs)/len(rs):>10.4f} {len(rs):>6}")

    print()

    # Verdict
    avg_ratio = sum(ratios) / len(ratios)
    avg_cv = sum(cvs) / len(cvs)

    print("  " + "=" * 60)
    if avg_ratio > 0.7 and avg_cv < 0.3:
        print("  VERDICT: UNIVERSALITY APPEARS TO HOLD")
        print(f"  c varies by only ~{(1-avg_ratio)*100:.0f}% across algorithms.")
        print("  c is approximately a CIRCUIT INVARIANT.")
        print("  T = c/(1-c) is therefore also approximately invariant.")
        print()
        print("  IMPLICATION: The equation of state c = T/(1+T)")
        print("  captures an intrinsic property of the circuit,")
        print("  not an artifact of the specific DFS variant used.")
    elif avg_ratio > 0.4:
        print("  VERDICT: PARTIAL UNIVERSALITY")
        print(f"  c varies by ~{(1-avg_ratio)*100:.0f}% across algorithms.")
        print("  c is roughly stable but not precisely invariant.")
        print("  The equation of state is approximately correct")
        print("  but algorithm choice introduces a constant factor.")
        print()
        print("  IMPLICATION: T = c/(1-c) is qualitatively invariant")
        print("  (same order of magnitude), supporting the framework")
        print("  for proving hardness up to constant factors.")
    else:
        print("  VERDICT: UNIVERSALITY DOES NOT HOLD")
        print(f"  c varies by ~{(1-avg_ratio)*100:.0f}% across algorithms.")
        print("  c depends significantly on the algorithm.")
        print("  T = c/(1-c) is NOT an intrinsic circuit quantity.")
        print()
        print("  IMPLICATION: The equation of state is algorithm-specific.")
        print("  Cannot use it to prove P != NP without fixing the algorithm.")
    print("  " + "=" * 60)
    print()

    # Compute T from c for representative cases
    print("  DERIVED T = c/(1-c) VALUES:")
    print(f"  {'circuit':<22} {'c_min':>7} {'c_max':>7} "
          f"{'T_min':>7} {'T_max':>7} {'T_ratio':>8}")
    for a in all_analyses:
        c_lo, c_hi = a['c_min'], a['c_max']
        T_lo = c_lo / (1 - c_lo) if c_lo < 0.999 else 999
        T_hi = c_hi / (1 - c_hi) if c_hi < 0.999 else 999
        T_ratio = T_lo / T_hi if T_hi > 0 else 0
        print(f"  {a['label']:<22} {c_lo:>7.3f} {c_hi:>7.3f} "
              f"{T_lo:>7.3f} {T_hi:>7.3f} {T_ratio:>8.3f}")


if __name__ == "__main__":
    main()
