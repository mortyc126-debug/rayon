"""
INTERACTION THEORY: Composition Laws and Scaling of Weighted Interaction.

Building on interaction_complexity.py, this module:
1. Proves/disproves composition laws for WI under AND/OR
2. Finds the tightest composition bound F(WI(g), WI(h))
3. Computes WI for CLIQUE-like functions
4. Determines polynomial vs exponential scaling of WI with circuit size
5. Tests alternative weightings (k!, k^k, etc.)

WI(f) = sum_S 2^{|S|} |f_hat(S)|
"""

import math
import time
from itertools import combinations
from collections import defaultdict


# ============================================================
# CORE FOURIER / WI COMPUTATION
# ============================================================

def fourier_spectrum(tt, n):
    """Compute full Fourier spectrum of truth table tt on n variables.
    Returns dict: frozenset(S) -> f_hat(S) using +/-1 convention."""
    total = 2 ** n
    spec = {}
    for k in range(n + 1):
        for S in combinations(range(n), k):
            S_mask = 0
            for i in S:
                S_mask |= (1 << i)
            coeff = 0
            for x in range(total):
                fx = 1 - 2 * ((tt >> x) & 1)  # {0,1} -> {+1,-1}
                parity = bin(x & S_mask).count('1') % 2
                chi = 1 - 2 * parity
                coeff += fx * chi
            spec[frozenset(S)] = coeff / total
    return spec


def weighted_interaction(tt, n, weight_func=None):
    """WI(f) = sum_S w(|S|) |f_hat(S)|.
    Default weight: w(k) = 2^k."""
    if weight_func is None:
        weight_func = lambda k: 2 ** k
    spec = fourier_spectrum(tt, n)
    total = 0.0
    for S, coeff in spec.items():
        total += weight_func(len(S)) * abs(coeff)
    return total


def weighted_interaction_from_spec(spec, weight_func=None):
    """Compute WI from a precomputed spectrum."""
    if weight_func is None:
        weight_func = lambda k: 2 ** k
    return sum(weight_func(len(S)) * abs(c) for S, c in spec.items())


def spectral_norm(tt, n):
    """L1 Fourier norm = sum_S |f_hat(S)|."""
    spec = fourier_spectrum(tt, n)
    return sum(abs(c) for c in spec.values())


# ============================================================
# CIRCUIT SIZE COMPUTATION (BFS closure)
# ============================================================

def compute_all_circuit_sizes(n, verbose=False):
    """Compute minimum circuit size for all functions on n variables."""
    total = 2 ** (2 ** n)

    level = {}
    cur = set()
    cur.add(0)
    cur.add(total - 1)
    for i in range(n):
        tt = 0
        for x in range(2 ** n):
            if (x >> i) & 1:
                tt |= (1 << x)
        cur.add(tt)
        cur.add((total - 1) ^ tt)
    for tt in cur:
        level[tt] = 0

    s = 0
    while len(level) < total:
        s += 1
        new = set()
        existing = list(level.keys())
        for f in existing:
            not_f = (total - 1) ^ f
            if not_f not in level:
                new.add(not_f)
            for g in existing:
                and_fg = f & g
                or_fg = f | g
                if and_fg not in level and and_fg not in new:
                    new.add(and_fg)
                if or_fg not in level and or_fg not in new:
                    new.add(or_fg)
        if not new:
            break
        for tt in new:
            level[tt] = s
        if verbose:
            print(f"  Size {s}: {len(new)} new, {len(level)} total ({len(level)/total:.1%})")
        if s > 20:
            break
    return level


def rank_correlation(x_vals, y_vals):
    """Spearman rank correlation."""
    n = len(x_vals)
    if n < 2:
        return 0.0
    ranked_x = sorted(range(n), key=lambda i: x_vals[i])
    ranked_y = sorted(range(n), key=lambda i: y_vals[i])
    rank_x = [0] * n
    rank_y = [0] * n
    for i, idx in enumerate(ranked_x):
        rank_x[idx] = i
    for i, idx in enumerate(ranked_y):
        rank_y[idx] = i
    d_sq = sum((rank_x[i] - rank_y[i]) ** 2 for i in range(n))
    return 1 - 6 * d_sq / (n * (n * n - 1))


# ============================================================
# PART 1 & 2: COMPOSITION LAWS FOR AND/OR
# ============================================================

def test_composition_laws(n):
    """Exhaustively test WI composition for AND and OR on n-variable functions.
    For AND(g,h): is WI(f) <= WI(g)*WI(h)? Or WI(g)+WI(h)+cross?
    Find the tightest bound."""

    print(f"\n{'='*70}")
    print(f"PART 1 & 2: COMPOSITION LAWS (n={n}, exhaustive)")
    print(f"{'='*70}")

    total = 2 ** (2 ** n)
    num_funcs = total

    # Precompute all spectra and WI values
    print(f"  Precomputing Fourier spectra for all {num_funcs} functions on {n} variables...")
    t0 = time.time()
    all_wi = {}
    all_spec = {}
    for tt in range(num_funcs):
        spec = fourier_spectrum(tt, n)
        all_spec[tt] = spec
        all_wi[tt] = weighted_interaction_from_spec(spec)
    print(f"  Done in {time.time()-t0:.1f}s")

    # Test AND composition
    print(f"\n  Testing AND composition: {num_funcs}x{num_funcs} = {num_funcs**2} pairs...")
    t0 = time.time()

    max_ratio_and = 0.0       # max WI(f) / (WI(g)*WI(h))
    max_diff_and = 0.0        # max WI(f) - (WI(g)+WI(h))
    max_ratio_and_pair = None
    max_diff_and_pair = None

    # For tightest bound: track max WI(AND(g,h)) / F(WI(g),WI(h))
    # Try multiplicative: WI(f) / (WI(g)*WI(h))
    # Try additive: WI(f) - WI(g) - WI(h)
    # Try mixed: WI(f) / (WI(g) + WI(h))

    max_sum_ratio_and = 0.0   # max WI(f) / (WI(g)+WI(h))
    violations_mult = 0
    violations_add = 0

    # Also collect data for regression
    data_and = []

    for g in range(num_funcs):
        wi_g = all_wi[g]
        for h in range(num_funcs):
            wi_h = all_wi[h]
            f = g & h  # AND
            wi_f = all_wi[f]

            prod = wi_g * wi_h
            summ = wi_g + wi_h

            data_and.append((wi_g, wi_h, wi_f))

            if prod > 1e-12:
                ratio = wi_f / prod
                if ratio > max_ratio_and:
                    max_ratio_and = ratio
                    max_ratio_and_pair = (g, h, f)

            diff = wi_f - summ
            if diff > max_diff_and:
                max_diff_and = diff
                max_diff_and_pair = (g, h, f)

            if summ > 1e-12:
                sr = wi_f / summ
                if sr > max_sum_ratio_and:
                    max_sum_ratio_and = sr

    print(f"  Done in {time.time()-t0:.1f}s")

    print(f"\n  AND COMPOSITION RESULTS:")
    print(f"    Multiplicative: max WI(AND(g,h)) / (WI(g)*WI(h)) = {max_ratio_and:.6f}")
    if max_ratio_and_pair:
        g, h, f = max_ratio_and_pair
        print(f"      Achieved at g={g}, h={h}, f={f}")
        print(f"      WI(g)={all_wi[g]:.4f}, WI(h)={all_wi[h]:.4f}, WI(f)={all_wi[f]:.4f}")
    mult_holds = max_ratio_and <= 1.0 + 1e-9
    print(f"    WI(AND(g,h)) <= WI(g)*WI(h)? {'YES' if mult_holds else 'NO'}")

    print(f"\n    Additive: max [WI(AND(g,h)) - WI(g) - WI(h)] = {max_diff_and:.6f}")
    if max_diff_and_pair:
        g, h, f = max_diff_and_pair
        print(f"      Achieved at g={g}, h={h}, f={f}")
        print(f"      WI(g)={all_wi[g]:.4f}, WI(h)={all_wi[h]:.4f}, WI(f)={all_wi[f]:.4f}")
    add_holds = max_diff_and <= 1e-9
    print(f"    WI(AND(g,h)) <= WI(g)+WI(h)? {'YES' if add_holds else 'NO'}")

    print(f"\n    Sum-ratio: max WI(AND(g,h)) / (WI(g)+WI(h)) = {max_sum_ratio_and:.6f}")

    # Test OR composition
    print(f"\n  Testing OR composition...")
    t0 = time.time()

    max_ratio_or = 0.0
    max_diff_or = 0.0
    max_sum_ratio_or = 0.0
    max_ratio_or_pair = None
    max_diff_or_pair = None

    for g in range(num_funcs):
        wi_g = all_wi[g]
        for h in range(num_funcs):
            wi_h = all_wi[h]
            f = g | h  # OR
            wi_f = all_wi[f]

            prod = wi_g * wi_h
            summ = wi_g + wi_h

            if prod > 1e-12:
                ratio = wi_f / prod
                if ratio > max_ratio_or:
                    max_ratio_or = ratio
                    max_ratio_or_pair = (g, h, f)

            diff = wi_f - summ
            if diff > max_diff_or:
                max_diff_or = diff
                max_diff_or_pair = (g, h, f)

            if summ > 1e-12:
                sr = wi_f / summ
                if sr > max_sum_ratio_or:
                    max_sum_ratio_or = sr

    print(f"  Done in {time.time()-t0:.1f}s")

    print(f"\n  OR COMPOSITION RESULTS:")
    print(f"    Multiplicative: max WI(OR(g,h)) / (WI(g)*WI(h)) = {max_ratio_or:.6f}")
    if max_ratio_or_pair:
        g, h, f = max_ratio_or_pair
        print(f"      Achieved at g={g}, h={h}, f={f}")
        print(f"      WI(g)={all_wi[g]:.4f}, WI(h)={all_wi[h]:.4f}, WI(f)={all_wi[f]:.4f}")
    mult_holds_or = max_ratio_or <= 1.0 + 1e-9
    print(f"    WI(OR(g,h)) <= WI(g)*WI(h)? {'YES' if mult_holds_or else 'NO'}")

    print(f"\n    Additive: max [WI(OR(g,h)) - WI(g) - WI(h)] = {max_diff_or:.6f}")
    if max_diff_or_pair:
        g, h, f = max_diff_or_pair
        print(f"      Achieved at g={g}, h={h}, f={f}")
        print(f"      WI(g)={all_wi[g]:.4f}, WI(h)={all_wi[h]:.4f}, WI(f)={all_wi[f]:.4f}")
    add_holds_or = max_diff_or <= 1e-9
    print(f"    WI(OR(g,h)) <= WI(g)+WI(h)? {'YES' if add_holds_or else 'NO'}")
    print(f"\n    Sum-ratio: max WI(OR(g,h)) / (WI(g)+WI(h)) = {max_sum_ratio_or:.6f}")

    # TIGHTEST BOUND SEARCH
    # For AND: find smallest alpha such that WI(AND(g,h)) <= alpha * (WI(g) + WI(h))
    # and smallest beta such that WI(AND(g,h)) <= WI(g)*WI(h)^beta (or similar)
    print(f"\n  TIGHTEST COMPOSITION BOUNDS:")
    print(f"    AND: WI(f) <= {max_sum_ratio_and:.4f} * (WI(g) + WI(h))  [additive with multiplier]")
    print(f"    OR:  WI(f) <= {max_sum_ratio_or:.4f} * (WI(g) + WI(h))  [additive with multiplier]")

    # Also try: WI(f) <= c * max(WI(g), WI(h))
    max_maxratio_and = 0.0
    max_maxratio_or = 0.0
    for g in range(num_funcs):
        wi_g = all_wi[g]
        for h in range(num_funcs):
            wi_h = all_wi[h]
            mx = max(wi_g, wi_h)
            if mx > 1e-12:
                f_and = g & h
                f_or = g | h
                r_and = all_wi[f_and] / mx
                r_or = all_wi[f_or] / mx
                max_maxratio_and = max(max_maxratio_and, r_and)
                max_maxratio_or = max(max_maxratio_or, r_or)

    print(f"    AND: WI(f) <= {max_maxratio_and:.4f} * max(WI(g), WI(h))")
    print(f"    OR:  WI(f) <= {max_maxratio_or:.4f} * max(WI(g), WI(h))")

    return all_wi, all_spec


# ============================================================
# PART 3: WI FOR CLIQUE-LIKE FUNCTIONS
# ============================================================

def build_clique_truth_table(N, k):
    """Build truth table for k-CLIQUE on N vertices.
    Input variables: one per edge = N*(N-1)/2 bits.
    Output: 1 iff there exists a k-clique in the graph.

    Variable ordering: edge (i,j) for i<j, lexicographic.
    """
    num_edges = N * (N - 1) // 2
    if num_edges > 20:
        print(f"    WARNING: {num_edges} edges, truth table has 2^{num_edges} entries -- too large")
        return None, num_edges

    edges = []
    for i in range(N):
        for j in range(i + 1, N):
            edges.append((i, j))
    edge_index = {e: idx for idx, e in enumerate(edges)}

    # All k-subsets of vertices
    clique_sets = list(combinations(range(N), k))

    # For each k-clique, compute the set of edges that must be present
    clique_edge_masks = []
    for verts in clique_sets:
        mask = 0
        for a in range(len(verts)):
            for b in range(a + 1, len(verts)):
                e = (verts[a], verts[b])
                mask |= (1 << edge_index[e])
        clique_edge_masks.append(mask)

    # Build truth table
    tt = 0
    num_inputs = 2 ** num_edges
    ones = 0
    for x in range(num_inputs):
        # Check if any k-clique has all edges present
        has_clique = False
        for mask in clique_edge_masks:
            if (x & mask) == mask:
                has_clique = True
                break
        if has_clique:
            tt |= (1 << x)
            ones += 1

    return tt, num_edges


def analyze_clique_functions():
    """Compute WI for small CLIQUE functions."""
    print(f"\n{'='*70}")
    print(f"PART 3: WI FOR CLIQUE-LIKE FUNCTIONS")
    print(f"{'='*70}")

    results = []
    configs = [
        (4, 3),  # 4 vertices, 3-clique (triangle), 6 edge variables
        (5, 3),  # 5 vertices, 3-clique, 10 edge variables
    ]

    for N, k in configs:
        num_edges = N * (N - 1) // 2
        print(f"\n  {k}-CLIQUE on N={N} vertices ({num_edges} edge variables):")

        if num_edges > 16:
            print(f"    Skipping: 2^{num_edges} = {2**num_edges} inputs too large for exact computation")
            continue

        t0 = time.time()
        tt, ne = build_clique_truth_table(N, k)
        if tt is None:
            continue

        ones = bin(tt).count('1')
        total_inputs = 2 ** ne
        print(f"    Truth table computed: {ones}/{total_inputs} inputs are 1 ({ones/total_inputs:.4f})")

        # Compute WI
        print(f"    Computing Fourier spectrum ({ne} variables)...")
        spec = fourier_spectrum(tt, ne)
        wi = weighted_interaction_from_spec(spec)
        l1 = sum(abs(c) for c in spec.values())

        # Level-by-level analysis
        level_l1 = defaultdict(float)
        level_wi = defaultdict(float)
        level_count = defaultdict(int)
        level_nonzero = defaultdict(int)
        for S, c in spec.items():
            k_level = len(S)
            level_l1[k_level] += abs(c)
            level_wi[k_level] += (2 ** k_level) * abs(c)
            level_count[k_level] += 1
            if abs(c) > 1e-12:
                level_nonzero[k_level] += 1

        print(f"    WI = {wi:.6f}")
        print(f"    L1 = {l1:.6f}")
        print(f"    WI/L1 ratio = {wi/l1:.4f}" if l1 > 0 else "    L1 = 0")
        print(f"    Time: {time.time()-t0:.1f}s")

        print(f"\n    Level-by-level breakdown:")
        print(f"    {'level k':>8} {'C(n,k)':>8} {'nonzero':>8} {'L1(k)':>12} {'2^k*L1(k)':>12} {'frac of WI':>12}")
        for kk in sorted(level_l1.keys()):
            frac = level_wi[kk] / wi if wi > 0 else 0
            print(f"    {kk:>8} {level_count[kk]:>8} {level_nonzero[kk]:>8} "
                  f"{level_l1[kk]:>12.6f} {level_wi[kk]:>12.6f} {frac:>12.4f}")

        results.append((N, k, ne, wi, l1))

    # Also compute WI for some simpler structured functions for comparison
    print(f"\n  COMPARISON: WI for simple structured functions")
    for ne in [6, 10]:
        if ne > 16:
            continue
        total = 2 ** ne
        # OR of all variables
        tt_or = 0
        for x in range(1, 2 ** ne):
            tt_or |= (1 << x)
        spec_or = fourier_spectrum(tt_or, ne)
        wi_or = weighted_interaction_from_spec(spec_or)

        # AND of all variables
        tt_and = 1 << ((2 ** ne) - 1)
        spec_and = fourier_spectrum(tt_and, ne)
        wi_and = weighted_interaction_from_spec(spec_and)

        # PARITY
        tt_par = 0
        for x in range(2 ** ne):
            if bin(x).count('1') % 2 == 1:
                tt_par |= (1 << x)
        spec_par = fourier_spectrum(tt_par, ne)
        wi_par = weighted_interaction_from_spec(spec_par)

        # MAJORITY (if odd ne)
        tt_maj = 0
        for x in range(2 ** ne):
            if bin(x).count('1') > ne // 2:
                tt_maj |= (1 << x)
        spec_maj = fourier_spectrum(tt_maj, ne)
        wi_maj = weighted_interaction_from_spec(spec_maj)

        print(f"\n    n={ne} variables:")
        print(f"      OR:       WI = {wi_or:.4f}")
        print(f"      AND:      WI = {wi_and:.4f}")
        print(f"      PARITY:   WI = {wi_par:.4f}")
        print(f"      MAJORITY: WI = {wi_maj:.4f}")

    return results


# ============================================================
# PART 4: POLYNOMIAL VS EXPONENTIAL SCALING
# ============================================================

def analyze_wi_vs_circuit_size():
    """Key question: does WI grow polynomially or exponentially with circuit size?"""
    print(f"\n{'='*70}")
    print(f"PART 4: WI vs CIRCUIT SIZE SCALING")
    print(f"{'='*70}")

    for n in [3, 4]:
        print(f"\n  n = {n}:")
        t0 = time.time()
        sizes = compute_all_circuit_sizes(n, verbose=False)
        print(f"    Circuit sizes computed in {time.time()-t0:.1f}s")

        total = 2 ** (2 ** n)

        # Compute WI for all functions (n=3) or sample (n=4)
        if n <= 3:
            sample = list(range(total))
        else:
            import random
            random.seed(42)
            sample = random.sample(range(total), min(3000, total))

        print(f"    Computing WI for {len(sample)} functions...")
        t0 = time.time()
        wi_vals = {}
        for tt in sample:
            wi_vals[tt] = weighted_interaction(tt, n)
        print(f"    Done in {time.time()-t0:.1f}s")

        # Group by circuit size
        by_size = defaultdict(list)
        for tt in sample:
            if tt in sizes:
                by_size[sizes[tt]].append(wi_vals[tt])

        print(f"\n    {'size s':>8} {'count':>8} {'avg WI':>12} {'max WI':>12} {'log2(avg)':>12} {'log2(max)':>12}")
        print(f"    {'-'*68}")

        size_vals = []
        avg_wi_vals = []
        max_wi_vals = []

        for s in sorted(by_size.keys()):
            wis = by_size[s]
            avg_w = sum(wis) / len(wis)
            max_w = max(wis)
            log_avg = math.log2(avg_w) if avg_w > 0 else float('-inf')
            log_max = math.log2(max_w) if max_w > 0 else float('-inf')
            print(f"    {s:>8} {len(wis):>8} {avg_w:>12.4f} {max_w:>12.4f} {log_avg:>12.4f} {log_max:>12.4f}")
            if s > 0 and avg_w > 0:
                size_vals.append(s)
                avg_wi_vals.append(avg_w)
                max_wi_vals.append(max_w)

        # Fit: is WI ~ c^s (exponential) or WI ~ s^k (polynomial)?
        # For exponential: log(WI) ~ s * log(c) => linear in s
        # For polynomial: log(WI) ~ k * log(s) => linear in log(s)
        if len(size_vals) >= 3:
            log_wi = [math.log(w) for w in avg_wi_vals]
            log_s = [math.log(s) for s in size_vals]

            # Linear regression: log(WI) vs s
            n_pts = len(size_vals)
            mean_s = sum(size_vals) / n_pts
            mean_logwi = sum(log_wi) / n_pts
            cov_s_logwi = sum((size_vals[i] - mean_s) * (log_wi[i] - mean_logwi) for i in range(n_pts))
            var_s = sum((size_vals[i] - mean_s) ** 2 for i in range(n_pts))
            if var_s > 0:
                slope_exp = cov_s_logwi / var_s
                intercept_exp = mean_logwi - slope_exp * mean_s
                # R^2
                ss_res = sum((log_wi[i] - (slope_exp * size_vals[i] + intercept_exp)) ** 2 for i in range(n_pts))
                ss_tot = sum((log_wi[i] - mean_logwi) ** 2 for i in range(n_pts))
                r2_exp = 1 - ss_res / ss_tot if ss_tot > 0 else 0

                print(f"\n    Exponential fit: log(WI) = {slope_exp:.4f} * s + {intercept_exp:.4f}")
                print(f"      => WI ~ {math.exp(intercept_exp):.4f} * {math.exp(slope_exp):.4f}^s")
                print(f"      R^2 = {r2_exp:.6f}")

            # Linear regression: log(WI) vs log(s)
            mean_logs = sum(log_s) / n_pts
            cov_logs_logwi = sum((log_s[i] - mean_logs) * (log_wi[i] - mean_logwi) for i in range(n_pts))
            var_logs = sum((log_s[i] - mean_logs) ** 2 for i in range(n_pts))
            if var_logs > 0:
                slope_poly = cov_logs_logwi / var_logs
                intercept_poly = mean_logwi - slope_poly * mean_logs
                ss_res_p = sum((log_wi[i] - (slope_poly * log_s[i] + intercept_poly)) ** 2 for i in range(n_pts))
                ss_tot_p = sum((log_wi[i] - mean_logwi) ** 2 for i in range(n_pts))
                r2_poly = 1 - ss_res_p / ss_tot_p if ss_tot_p > 0 else 0

                print(f"\n    Polynomial fit: log(WI) = {slope_poly:.4f} * log(s) + {intercept_poly:.4f}")
                print(f"      => WI ~ {math.exp(intercept_poly):.4f} * s^{slope_poly:.4f}")
                print(f"      R^2 = {r2_poly:.6f}")

            print(f"\n    VERDICT for n={n}:")
            if r2_exp > r2_poly + 0.01:
                print(f"      EXPONENTIAL fit is better (R2_exp={r2_exp:.4f} > R2_poly={r2_poly:.4f})")
                print(f"      => WI grows EXPONENTIALLY with circuit size")
                print(f"      => log(WI) gives at most LINEAR lower bound on s")
            elif r2_poly > r2_exp + 0.01:
                print(f"      POLYNOMIAL fit is better (R2_poly={r2_poly:.4f} > R2_exp={r2_exp:.4f})")
                print(f"      => WI grows POLYNOMIALLY with circuit size")
                print(f"      => WI^{{1/k}} gives direct lower bound on s")
            else:
                print(f"      INCONCLUSIVE: R2_exp={r2_exp:.4f}, R2_poly={r2_poly:.4f}")
                print(f"      Need larger n to distinguish")

    # Theoretical analysis from composition law
    print(f"\n  THEORETICAL ANALYSIS:")
    print(f"    If WI(AND(g,h)) <= C * (WI(g) + WI(h)) for constant C:")
    print(f"      A circuit of size s applies s AND/OR gates.")
    print(f"      Starting from WI(x_i) = O(1) for input variables,")
    print(f"      after s gates: WI <= C^s * O(1)  [if purely multiplicative]")
    print(f"                 or: WI <= s * C * max_input_WI  [if sub-additive]")
    print(f"    The composition constant C determines the growth rate.")


# ============================================================
# PART 5: ALTERNATIVE WEIGHTINGS
# ============================================================

def test_alternative_weightings():
    """Test different weighting functions for correlation with circuit size."""
    print(f"\n{'='*70}")
    print(f"PART 5: ALTERNATIVE WEIGHTINGS")
    print(f"{'='*70}")

    # Define weighting functions
    def w_2k(k):
        return 2 ** k

    def w_factorial(k):
        return math.factorial(k) if k > 0 else 1

    def w_kk(k):
        return k ** k if k > 0 else 1

    def w_exp_k(k):
        return math.exp(k)

    def w_k2(k):
        return k * k if k > 0 else 1

    def w_3k(k):
        return 3 ** k

    def w_k_plus_1(k):
        return k + 1

    def w_binom(k):
        """Binomial-inspired: C(n, k) * 2^k -- but n varies, so just 2^k * (k+1)"""
        return (2 ** k) * (k + 1)

    weightings = [
        ("2^k (standard WI)", w_2k),
        ("k!", w_factorial),
        ("k^k", w_kk),
        ("e^k", w_exp_k),
        ("k^2", w_k2),
        ("3^k", w_3k),
        ("k+1", w_k_plus_1),
        ("2^k*(k+1)", w_binom),
        ("1 (L1 norm)", lambda k: 1),
    ]

    for n in [3, 4]:
        print(f"\n  n = {n}:")
        t0 = time.time()
        sizes = compute_all_circuit_sizes(n, verbose=False)
        print(f"    Circuit sizes computed in {time.time()-t0:.1f}s")

        total = 2 ** (2 ** n)
        if n <= 3:
            sample = list(range(total))
        else:
            import random
            random.seed(42)
            sample = random.sample(range(total), min(2000, total))

        # Precompute spectra
        print(f"    Computing spectra for {len(sample)} functions...")
        t0 = time.time()
        spectra = {}
        for tt in sample:
            spectra[tt] = fourier_spectrum(tt, n)
        print(f"    Done in {time.time()-t0:.1f}s")

        circuit_sizes = [sizes[tt] for tt in sample if tt in sizes]
        sample_with_size = [tt for tt in sample if tt in sizes]

        print(f"\n    {'Weighting':>20} {'rho (Spearman)':>16} {'max WI':>12}")
        print(f"    {'-'*52}")

        best_rho = -1
        best_name = ""

        for name, wfunc in weightings:
            wi_vals = [weighted_interaction_from_spec(spectra[tt], wfunc) for tt in sample_with_size]
            sz_vals = [sizes[tt] for tt in sample_with_size]
            rho = rank_correlation(wi_vals, sz_vals)
            max_wi = max(wi_vals) if wi_vals else 0
            print(f"    {name:>20} {rho:>16.4f} {max_wi:>12.4f}")
            if rho > best_rho:
                best_rho = rho
                best_name = name

        print(f"\n    BEST weighting for n={n}: {best_name} (rho={best_rho:.4f})")


# ============================================================
# MAIN EXECUTION
# ============================================================

if __name__ == "__main__":
    print("INTERACTION THEORY: Composition Laws and Scaling")
    print("=" * 70)

    # Part 1 & 2: Composition laws (n=3 only -- n=4 has 65536 functions, 4 billion pairs)
    all_wi_3, all_spec_3 = test_composition_laws(n=3)

    # Part 3: Clique functions
    clique_results = analyze_clique_functions()

    # Part 4: Polynomial vs exponential scaling
    analyze_wi_vs_circuit_size()

    # Part 5: Alternative weightings
    test_alternative_weightings()

    # ============================================================
    # FINAL SUMMARY
    # ============================================================
    print(f"\n{'='*70}")
    print(f"FINAL SUMMARY AND CONCLUSIONS")
    print(f"{'='*70}")
    print(f"""
  1. COMPOSITION LAW:
     The AND/OR composition results above determine whether WI is
     sub-multiplicative, sub-additive, or neither.

  2. TIGHTEST BOUND:
     The smallest constant C such that WI(op(g,h)) <= C * (WI(g) + WI(h))
     is reported above for both AND and OR.

  3. CLIQUE:
     WI values for k-CLIQUE functions on small N are computed.
     The level-by-level breakdown shows where the complexity concentrates.

  4. SCALING:
     The R^2 comparison between exponential and polynomial fits
     determines whether WI gives polynomial or super-polynomial bounds.
     KEY: If exponential fit wins, log(WI) is the useful quantity.
           If polynomial fit wins, WI itself bounds circuit size.

  5. BEST WEIGHTING:
     The weighting with highest Spearman correlation to circuit size
     is the most promising candidate for lower bounds.
""")
