"""
MCSP IDEAL: Encode "∃ circuit of size s computing f?" as polynomial system.

Variables:
  g[i] ∈ {AND, OR, NOT}: type of gate i (3 choices → 2 Boolean vars per gate)
  w[i][1], w[i][2]: input wires (encoded as Boolean vectors)
  v[i][x]: value of gate i on input x (Boolean)

Constraints:
  Gate consistency: v[i][x] = gate_function(g[i], v[w[i][1]][x], v[w[i][2]][x])
  Output: v[s][x] = f(x) for all x
  Boolean: all variables in {0,1}

Total variables: O(s × (log s + 2^n))
Total constraints: O(s × 2^n)

For TINY parameters (n=3, s=3): compute and analyze ideal.
"""

import itertools
import time


def mcsp_check_brute_force(n, target_tt, s):
    """Brute force: does ∃ circuit of ≤ s gates computing target?

    For tiny parameters: enumerate all circuits.
    Return: number of valid circuits found, total checked.
    """
    gate_types = [0, 1, 2]  # AND, OR, NOT
    total_checked = 0
    valid = 0

    def evaluate(gates_spec, x):
        wire = [(x >> j) & 1 for j in range(n)]
        for gtype, inp1, inp2 in gates_spec:
            if gtype == 0:  # AND
                wire.append(wire[inp1] & wire[inp2])
            elif gtype == 1:  # OR
                wire.append(wire[inp1] | wire[inp2])
            elif gtype == 2:  # NOT
                wire.append(1 - wire[inp1])
        return wire[-1] if gates_spec else 0

    def search(depth, gates_so_far):
        nonlocal total_checked, valid

        if depth == s:
            total_checked += 1
            # Check if circuit computes target
            correct = True
            for x in range(2**n):
                if evaluate(gates_so_far, x) != target_tt[x]:
                    correct = False
                    break
            if correct:
                valid += 1
            return

        num_wires = n + depth
        for gtype in gate_types:
            if gtype == 2:  # NOT
                for inp1 in range(num_wires):
                    search(depth + 1, gates_so_far + [(gtype, inp1, 0)])
            else:  # AND, OR
                for inp1 in range(num_wires):
                    for inp2 in range(inp1, num_wires):
                        search(depth + 1, gates_so_far + [(gtype, inp1, inp2)])

    search(0, [])
    return valid, total_checked


def main():
    print("=" * 55)
    print("  MCSP BRUTE FORCE: Circuit existence for tiny params")
    print("=" * 55)

    # n=3 functions
    functions = {
        'AND3': {b: 1 if b == 7 else 0 for b in range(8)},
        'OR3': {b: 0 if b == 0 else 1 for b in range(8)},
        'MAJ3': {b: 1 if bin(b).count('1') >= 2 else 0 for b in range(8)},
        'XOR3': {b: bin(b).count('1') % 2 for b in range(8)},
    }

    print(f"\n  {'Function':<10} {'s':>3} {'valid':>8} {'checked':>10} "
          f"{'density':>10} {'time':>6}")
    print("  " + "-" * 50)

    for name, tt in functions.items():
        for s in range(1, 5):
            t0 = time.time()
            v, c = mcsp_check_brute_force(3, tt, s)
            dt = time.time() - t0
            density = v / c if c > 0 else 0
            print(f"  {name:<10} {s:>3} {v:>8} {c:>10} {density:>10.6f} {dt:>6.1f}s")

            if dt > 10:
                break
        print()

    print(f"  INTERPRETATION:")
    print(f"  'valid' = number of size-s circuits computing f.")
    print(f"  'density' = valid/total = fraction of solution space.")
    print(f"  LOW density → MCSP landscape RUGGED (hard to find).")
    print(f"  HIGH density → MCSP landscape SMOOTH (easy to find).")
    print()
    print(f"  Density DIFFERENCE between functions =")
    print(f"  proxy for relative circuit complexity.")
    print(f"  If AND3 high density, XOR3 low density:")
    print(f"  → AND3 easy to implement, XOR3 hard.")


if __name__ == "__main__":
    main()
