"""
IDEA 30: Energy landscape of circuit search.

E(C, f) = |{x : C(x) ≠ f(x)}| = number of errors.

For each "circuit specification" (gate types + wiring):
  E = how far circuit is from computing f.

Landscape: E as function of circuit specification.
Local minimum: circuit where changing any single gate increases E.

If landscape SMOOTH: few local minima → optimization finds global min → P=NP.
If landscape RUGGED: many local minima → optimization stuck → P≠NP.

EXPERIMENT: For small n, sample random circuits, do local search,
count distinct local minima found.
"""

import random
import math
import sys


def evaluate_circuit(n, gate_specs, x_int):
    """Evaluate circuit on input x. gate_specs = [(type, inp1, inp2), ...]."""
    wire = [(x_int >> j) & 1 for j in range(n)]
    for gtype, inp1, inp2 in gate_specs:
        if gtype == 0:  # AND
            wire.append(wire[inp1] & wire[inp2])
        elif gtype == 1:  # OR
            wire.append(wire[inp1] | wire[inp2])
        elif gtype == 2:  # NOT
            wire.append(1 - wire[inp1])
    return wire[-1] if gate_specs else 0


def compute_error(n, gate_specs, target_tt):
    """Count number of inputs where circuit disagrees with target."""
    errors = 0
    for x in range(2**n):
        if evaluate_circuit(n, gate_specs, x) != target_tt[x]:
            errors += 1
    return errors


def random_circuit(n, s):
    """Generate random circuit of size s on n inputs."""
    specs = []
    for i in range(s):
        num_wires = n + i
        gtype = random.randint(0, 2)  # AND, OR, NOT
        inp1 = random.randint(0, num_wires - 1)
        inp2 = random.randint(0, num_wires - 1) if gtype < 2 else 0
        specs.append((gtype, inp1, inp2))
    return specs


def local_search(n, s, target_tt, max_steps=1000):
    """Local search: start from random circuit, greedily improve."""
    specs = random_circuit(n, s)
    error = compute_error(n, specs, target_tt)

    for step in range(max_steps):
        if error == 0:
            return specs, error, step  # found perfect circuit!

        # Try changing one random gate
        gate_idx = random.randint(0, s - 1)
        old_spec = specs[gate_idx]

        # Random new specification
        num_wires = n + gate_idx
        new_type = random.randint(0, 2)
        new_inp1 = random.randint(0, num_wires - 1)
        new_inp2 = random.randint(0, num_wires - 1) if new_type < 2 else 0

        specs[gate_idx] = (new_type, new_inp1, new_inp2)
        new_error = compute_error(n, specs, target_tt)

        if new_error <= error:
            error = new_error  # accept improvement or equal
        else:
            specs[gate_idx] = old_spec  # revert

    return specs, error, max_steps


def measure_landscape(n, s, target_tt, num_runs=100):
    """Run local search many times, collect statistics."""
    min_errors = []
    steps_to_converge = []
    final_circuits = []

    for _ in range(num_runs):
        specs, error, steps = local_search(n, s, target_tt, 2000)
        min_errors.append(error)
        steps_to_converge.append(steps)
        if error == 0:
            final_circuits.append(tuple(tuple(g) for g in specs))

    # Count distinct local minima (by error level)
    error_dist = {}
    for e in min_errors:
        error_dist[e] = error_dist.get(e, 0) + 1

    # Count perfect solutions found
    perfect = sum(1 for e in min_errors if e == 0)
    distinct_perfect = len(set(final_circuits))

    return {
        'avg_error': sum(min_errors) / len(min_errors),
        'min_error': min(min_errors),
        'perfect': perfect,
        'distinct_perfect': distinct_perfect,
        'error_dist': dict(sorted(error_dist.items())),
        'num_runs': num_runs,
    }


def main():
    random.seed(42)
    print("=" * 60)
    print("  META-LANDSCAPE: Circuit search for small functions")
    print("  Smooth = P=NP direction, Rugged = P≠NP direction")
    print("=" * 60)

    # Target functions
    targets = {}

    # OR on n=4
    targets['OR-4'] = (4, {b: 0 if b == 0 else 1 for b in range(16)})

    # MAJ on n=4
    targets['MAJ-4'] = (4, {b: 1 if bin(b).count('1') >= 2 else 0 for b in range(16)})

    # Triangle K4 (n=6)
    N = 4; nn = 6
    eidx = {}; idx = 0
    for i in range(N):
        for j in range(i+1, N):
            eidx[(i,j)] = idx; eidx[(j,i)] = idx; idx += 1
    tt_tri = {}
    for b in range(2**nn):
        x = tuple((b>>j)&1 for j in range(nn))
        has = any(x[eidx[(i,j)]] and x[eidx[(i,k)]] and x[eidx[(j,k)]]
                  for i in range(N) for j in range(i+1,N) for k in range(j+1,N))
        tt_tri[b] = 1 if has else 0
    targets['TRI-K4'] = (nn, tt_tri)

    print(f"\n  {'Function':<12} {'n':>3} {'s':>4} {'avg_err':>8} {'min_err':>8} "
          f"{'perfect':>8} {'distinct':>8}")
    print("  " + "-" * 55)

    for name, (n, tt) in targets.items():
        for s in [n, 2*n, 3*n]:
            result = measure_landscape(n, s, tt, 200)
            print(f"  {name:<12} {n:>3} {s:>4} {result['avg_error']:>8.1f} "
                  f"{result['min_error']:>8} {result['perfect']:>8} "
                  f"{result['distinct_perfect']:>8}")
        sys.stdout.flush()

    print(f"\n  INTERPRETATION:")
    print(f"  'perfect' = runs finding E=0 circuit (out of 200).")
    print(f"  'distinct' = unique perfect circuits found.")
    print(f"  High perfect + few distinct = SMOOTH landscape (easy).")
    print(f"  Low perfect + many distinct = RUGGED landscape (hard).")
    print(f"  Zero perfect = no solution at this size (or search stuck).")


if __name__ == "__main__":
    main()
