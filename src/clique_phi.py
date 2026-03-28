"""
Φ for CLIQUE vs MSAT vs P-functions: the critical comparison.

If Φ(CLIQUE) grows exponentially while Φ(P-functions) grows polynomially,
the Computational Potential framework separates them.

Also: test circuits WITH fan-out (shared gates) to see how
gate fan-out affects the Φ profile.
"""

import itertools
from collections import defaultdict
import random
import math
import sys


def compute_phi(n, tt, num_trials=200):
    total = 2**n
    boundary = []
    for bits in range(total):
        for j in range(n):
            nb = bits ^ (1 << j)
            if bits < nb and tt[bits] != tt[nb]:
                boundary.append((bits, nb))

    if not boundary:
        return 0

    best = 0
    for _ in range(num_trials):
        k = random.randint(1, min(n-1, 7))
        coords = random.sample(range(n), k)
        block_of = {}
        sigs_dict = defaultdict(list)
        for bits in range(total):
            bid = sum((1 << ci) for ci, c in enumerate(coords) if (bits >> c) & 1)
            block_of[bits] = bid
            sigs_dict[bid].append(tt[bits])
        cross = sum(1 for b1, b2 in boundary if block_of[b1] != block_of[b2])
        sigs = set(tuple(v) for v in sigs_dict.values())
        cons = max(1, cross)
        comp = max(1, len(sigs))
        depth = max(1, int(math.ceil(math.log2(max(2, comp)))))
        best = max(best, cons * comp * depth)
    return best


def triangle_func(N):
    """Triangle detection function on N vertices."""
    n = N * (N-1) // 2
    edge_idx = {}
    idx = 0
    for i in range(N):
        for j in range(i+1, N):
            edge_idx[(i,j)] = idx
            edge_idx[(j,i)] = idx
            idx += 1

    def func_tt():
        tt = {}
        for bits in range(2**n):
            x = tuple((bits >> j) & 1 for j in range(n))
            has_tri = False
            for i in range(N):
                for j in range(i+1, N):
                    for k in range(j+1, N):
                        if x[edge_idx[(i,j)]] and x[edge_idx[(i,k)]] and x[edge_idx[(j,k)]]:
                            has_tri = True
                            break
                    if has_tri:
                        break
                if has_tri:
                    break
            tt[bits] = 1 if has_tri else 0
        return tt, n

    return func_tt


def clique_k_func(N, k):
    """k-clique detection on N vertices."""
    n = N * (N-1) // 2
    edge_idx = {}
    idx = 0
    for i in range(N):
        for j in range(i+1, N):
            edge_idx[(i,j)] = idx
            edge_idx[(j,i)] = idx
            idx += 1

    def func_tt():
        tt = {}
        for bits in range(2**n):
            x = tuple((bits >> j) & 1 for j in range(n))
            has_clique = False
            for combo in itertools.combinations(range(N), k):
                is_clique = True
                for a in range(len(combo)):
                    for b in range(a+1, len(combo)):
                        if not x[edge_idx[(combo[a], combo[b])]]:
                            is_clique = False
                            break
                    if not is_clique:
                        break
                if is_clique:
                    has_clique = True
                    break
            tt[bits] = 1 if has_clique else 0
        return tt, n

    return func_tt


def mono3sat_func(n, clauses):
    """MONO-3SAT evaluation."""
    def func_tt():
        tt = {}
        for bits in range(2**n):
            x = tuple((bits >> j) & 1 for j in range(n))
            sat = all(any(x[v] for v in c) for c in clauses)
            tt[bits] = 1 if sat else 0
        return tt, n
    return func_tt


def p_func_or(n):
    def func_tt():
        tt = {bits: 1 if bits > 0 else 0 for bits in range(2**n)}
        return tt, n
    return func_tt


def p_func_maj(n):
    def func_tt():
        tt = {}
        for bits in range(2**n):
            tt[bits] = 1 if bin(bits).count('1') > n/2 else 0
        return tt, n
    return func_tt


def p_func_th2(n):
    def func_tt():
        tt = {}
        for bits in range(2**n):
            tt[bits] = 1 if bin(bits).count('1') >= 2 else 0
        return tt, n
    return func_tt


def main():
    random.seed(42)
    print("=" * 70)
    print("  Φ COMPARISON: CLIQUE vs MSAT vs P-FUNCTIONS")
    print("  Critical test: does Φ separate complexity classes?")
    print("=" * 70)

    results = []

    # Triangle (3-clique) on various N
    print(f"\n{'Function':<25} {'n bits':>7} {'Φ':>10} {'Φ/n':>10} {'Φ/n²':>10}")
    print("-" * 65)

    for N in range(4, 9):
        n = N * (N-1) // 2
        if 2**n > 200000:
            break
        tt, n_bits = triangle_func(N)()
        phi = compute_phi(n_bits, tt, 300)
        results.append(('TRI-'+str(N), n_bits, phi))
        print(f"{'Triangle K'+str(N):<25} {n_bits:>7} {phi:>10} "
              f"{phi/n_bits:>10.1f} {phi/n_bits**2:>10.2f}")
        sys.stdout.flush()

    # 4-clique on various N
    for N in range(5, 8):
        n = N * (N-1) // 2
        if 2**n > 200000:
            break
        tt, n_bits = clique_k_func(N, 4)()
        phi = compute_phi(n_bits, tt, 300)
        results.append(('4CLQ-'+str(N), n_bits, phi))
        print(f"{'4-Clique K'+str(N):<25} {n_bits:>7} {phi:>10} "
              f"{phi/n_bits:>10.1f} {phi/n_bits**2:>10.2f}")
        sys.stdout.flush()

    # MONO-3SAT
    from mono3sat import generate_all_mono3sat_clauses
    for n in range(5, 13):
        if 2**n > 200000:
            break
        all_clauses = generate_all_mono3sat_clauses(n)
        k = min(len(all_clauses), 3*n)
        clauses = random.sample(all_clauses, k)
        tt, n_bits = mono3sat_func(n, clauses)()
        phi = compute_phi(n_bits, tt, 300)
        results.append(('MSAT-'+str(n), n_bits, phi))
        print(f"{'MSAT n='+str(n):<25} {n_bits:>7} {phi:>10} "
              f"{phi/n_bits:>10.1f} {phi/n_bits**2:>10.2f}")
        sys.stdout.flush()

    # P-functions for comparison
    for n in [6, 8, 10, 12, 15]:
        if 2**n > 200000:
            break

        tt_or, _ = p_func_or(n)()
        phi_or = compute_phi(n, tt_or, 200)
        results.append(('OR-'+str(n), n, phi_or))
        print(f"{'OR n='+str(n):<25} {n:>7} {phi_or:>10} "
              f"{phi_or/n:>10.1f} {phi_or/n**2:>10.2f}")

        tt_maj, _ = p_func_maj(n)()
        phi_maj = compute_phi(n, tt_maj, 200)
        results.append(('MAJ-'+str(n), n, phi_maj))
        print(f"{'MAJ n='+str(n):<25} {n:>7} {phi_maj:>10} "
              f"{phi_maj/n:>10.1f} {phi_maj/n**2:>10.2f}")

        tt_th, _ = p_func_th2(n)()
        phi_th = compute_phi(n, tt_th, 200)
        results.append(('TH2-'+str(n), n, phi_th))
        print(f"{'TH2 n='+str(n):<25} {n:>7} {phi_th:>10} "
              f"{phi_th/n:>10.1f} {phi_th/n**2:>10.2f}")

        sys.stdout.flush()

    # GROWTH RATE ANALYSIS
    print(f"\n\n{'='*70}")
    print("  GROWTH RATE ANALYSIS")
    print(f"{'='*70}")

    families = defaultdict(list)
    for name, n, phi in results:
        prefix = name.split('-')[0]
        families[prefix].append((n, phi))

    for family in ['TRI', '4CLQ', 'MSAT', 'OR', 'MAJ', 'TH2']:
        if family not in families:
            continue
        data = sorted(families[family])
        if len(data) < 2:
            continue

        print(f"\n  {family}:")
        print(f"    {'n':>5} {'Φ':>10} {'Φ/n':>10} {'Φ/n²':>10} {'Φ/n³':>10}")
        for n, phi in data:
            print(f"    {n:5d} {phi:10d} {phi/n:10.1f} "
                  f"{phi/n**2:10.2f} {phi/n**3:10.4f}")

        # Fit: Φ ≈ C × n^α
        if len(data) >= 3:
            ns = [d[0] for d in data]
            phis = [d[1] for d in data]
            log_ns = [math.log(n) for n in ns]
            log_phis = [math.log(max(1, p)) for p in phis]

            # Linear regression on log-log
            m = len(log_ns)
            sx = sum(log_ns); sy = sum(log_phis)
            sxy = sum(x*y for x,y in zip(log_ns, log_phis))
            sxx = sum(x*x for x in log_ns)
            if m * sxx - sx * sx != 0:
                alpha = (m * sxy - sx * sy) / (m * sxx - sx * sx)
                log_C = (sy - alpha * sx) / m
                C = math.exp(log_C)
                print(f"    FIT: Φ ≈ {C:.2f} × n^{alpha:.2f}")

                if alpha > 3.5:
                    print(f"    >>> SUPER-CUBIC growth!")
                elif alpha > 2.5:
                    print(f"    >>> CUBIC growth")
                elif alpha > 1.5:
                    print(f"    >>> QUADRATIC growth")
                elif alpha > 0.5:
                    print(f"    >>> LINEAR growth")
                else:
                    print(f"    >>> SUB-LINEAR growth")


if __name__ == "__main__":
    main()
