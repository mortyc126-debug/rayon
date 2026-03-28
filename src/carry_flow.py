"""
CARRY ALGEBRA — Session 3: W → Carry Flow

KEY QUESTION: How do message words W[0..15] control carry modes?

If W → carry_coordinates is LINEAR: we can solve for W given target carries.
If SMOOTH: we can use gradient descent.
If CHAOTIC: we need different approach.

From Carry-Web Theory: W[0] dominates early blocks, W[1..15] add to later blocks.
The schedule W[16..63] = XOR combinations of W[0..15].
So carry[r] depends on W[0..15] through schedule + state chain.

MEASUREMENT PLAN:
1. Correlation: corr(W[k], carry_mode[j]) — which words control which modes?
2. Linearity: R² of linear model W → carry_coords
3. Sensitivity: ∂carry_mode[j]/∂W[k] (numerical Jacobian)
4. Controllability: can we reach arbitrary carry patterns by choosing W?
"""

import numpy as np
import time
from carry_algebra_foundation import sha256_with_carries, K256, IV, M32
from carry_ring import collect_carry_data, find_principal_modes, CarryRing


def measure_w_to_carry_control(n_samples=15000):
    """Measure how message words W[0..15] control carry modes."""
    print("Collecting W → carry data...", flush=True)
    t0 = time.time()

    W_data = []
    carry_data = []
    hash_data = []

    for _ in range(n_samples):
        W = [np.random.randint(0, 2**32) for _ in range(16)]
        H, carries, raw = sha256_with_carries(W)
        # Normalize W to [0,1]
        W_norm = [w / (2**32) for w in W]
        W_data.append(W_norm)
        carry_data.append(carries)
        hash_data.append(H)

    W_arr = np.array(W_data)  # (n_samples, 16)
    carry_arr = np.array(carry_data, dtype=np.float64)  # (n_samples, 64)
    print(f"  Done in {time.time()-t0:.1f}s")

    return W_arr, carry_arr, hash_data


def correlation_analysis(W_arr, carry_arr, pca_result):
    """Correlation between W words and carry modes."""
    ring = CarryRing(pca_result, n_components=min(15, pca_result['n_components_95']))

    # Project carries to mode coordinates
    coords = np.array([ring.project(carry_arr[i]) for i in range(len(carry_arr))])

    print("\n  W[k] → Carry Mode CORRELATION MATRIX:")
    print(f"  {'':>6}", end='')
    for j in range(min(10, coords.shape[1])):
        print(f" {'M'+str(j+1):>7}", end='')
    print()
    print(f"  {'─'*80}")

    corr_matrix = np.zeros((16, coords.shape[1]))
    for k in range(16):
        print(f"  W[{k:>2}]", end='')
        for j in range(min(10, coords.shape[1])):
            c = np.corrcoef(W_arr[:, k], coords[:, j])[0, 1]
            corr_matrix[k, j] = c
            marker = '■' if abs(c) > 0.1 else '·'
            print(f" {c:>+6.3f}{marker}", end='')
        print()

    return corr_matrix, ring, coords


def linearity_test(W_arr, coords):
    """Test if W → carry_coords is approximately linear."""
    print(f"\n  LINEARITY TEST: W → carry_modes")
    print(f"  {'Mode':>6} {'R² (linear)':>12} {'R² (quadratic)':>16} {'Linear?':>10}")
    print(f"  {'─'*48}")

    r2_scores = []
    for j in range(min(10, coords.shape[1])):
        y = coords[:, j]

        # Linear: y = W @ β
        X = np.column_stack([W_arr, np.ones(len(W_arr))])
        beta, res, _, _ = np.linalg.lstsq(X, y, rcond=None)
        y_pred = X @ beta
        ss_res = np.sum((y - y_pred)**2)
        ss_tot = np.sum((y - y.mean())**2)
        r2_lin = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        # Quadratic: add W[k]² and W[k]*W[j] terms
        X2_cols = [W_arr]
        for k in range(16):
            X2_cols.append((W_arr[:, k:k+1])**2)
        X2 = np.column_stack(X2_cols + [np.ones(len(W_arr))])
        beta2, _, _, _ = np.linalg.lstsq(X2, y, rcond=None)
        y_pred2 = X2 @ beta2
        ss_res2 = np.sum((y - y_pred2)**2)
        r2_quad = 1 - ss_res2 / ss_tot if ss_tot > 0 else 0

        linear = "YES" if r2_lin > 0.5 else ("partial" if r2_lin > 0.1 else "no")
        r2_scores.append(r2_lin)

        print(f"  {j+1:>6} {r2_lin:>11.4f} {r2_quad:>15.4f} {linear:>10}")

    return r2_scores


def jacobian_analysis(n_samples=5000):
    """Numerical Jacobian: ∂carry/∂W."""
    print(f"\n  JACOBIAN: ∂carry[r]/∂W[k] (bit-flip sensitivity)")

    # For each W[k], flip one bit and measure carry change
    sensitivity = np.zeros((16, 64))
    n_trials = n_samples

    for _ in range(n_trials):
        W = [np.random.randint(0, 2**32) for _ in range(16)]
        _, carries_base, _ = sha256_with_carries(W)

        for k in range(16):
            # Flip a random bit in W[k]
            bit = np.random.randint(0, 32)
            W_mod = list(W)
            W_mod[k] ^= (1 << bit)
            _, carries_mod, _ = sha256_with_carries(W_mod)

            for r in range(64):
                if carries_mod[r] != carries_base[r]:
                    sensitivity[k][r] += 1

    sensitivity /= n_trials

    print(f"  {'':>6}", end='')
    for r in range(0, 64, 8):
        print(f" {'r'+str(r):>6}", end='')
    print()

    for k in range(16):
        print(f"  W[{k:>2}]", end='')
        for r in range(0, 64, 8):
            s = sensitivity[k][r]
            marker = '█' if s > 0.1 else ('▓' if s > 0.05 else ('░' if s > 0.01 else ' '))
            print(f" {s:>5.3f}{marker}", end='')
        print()

    # Which W words have most influence?
    total_sens = sensitivity.sum(axis=1)
    print(f"\n  Total sensitivity per word:")
    ranked = sorted(range(16), key=lambda k: -total_sens[k])
    for k in ranked[:5]:
        top_rounds = np.argsort(sensitivity[k])[::-1][:5]
        rounds_str = ','.join(f'r{r}' for r in top_rounds)
        print(f"    W[{k:>2}]: total={total_sens[k]:.3f}, top rounds: {rounds_str}")

    return sensitivity


def controllability_test(W_arr, carry_arr, coords, ring):
    """Can we reach arbitrary carry patterns by choosing W?"""
    print(f"\n  CONTROLLABILITY: Can W reach arbitrary carry targets?")

    # Test: pick a random target in carry-mode space, find nearest actual
    n_targets = 100
    reached = 0
    min_dists = []

    for _ in range(n_targets):
        # Random target in mode space (within observed range)
        target = np.array([np.random.uniform(coords[:, j].min(), coords[:, j].max())
                          for j in range(coords.shape[1])])

        # Find nearest observed point
        dists = np.linalg.norm(coords - target, axis=1)
        min_dist = dists.min()
        min_dists.append(min_dist)

        # Is it "reachable"? (within typical inter-point distance)
        typical_dist = np.median([np.linalg.norm(coords[i] - coords[i+1])
                                  for i in range(0, min(100, len(coords)-1))])
        if min_dist < typical_dist:
            reached += 1

    reach_pct = reached / n_targets * 100
    avg_min_dist = np.mean(min_dists)

    print(f"    Targets reachable: {reached}/{n_targets} ({reach_pct:.0f}%)")
    print(f"    Average min distance to target: {avg_min_dist:.4f}")
    print(f"    {'GOOD controllability' if reach_pct > 50 else 'LIMITED controllability'}")

    # Key test: can we move along ONE mode while keeping others fixed?
    print(f"\n    Mode independence test:")
    for mode in range(min(5, coords.shape[1])):
        # Sort by this mode's coordinate
        order = np.argsort(coords[:, mode])
        low = coords[order[:len(order)//4]]
        high = coords[order[-len(order)//4:]]
        # Are other modes similar between low and high?
        other_drift = 0
        for other in range(min(10, coords.shape[1])):
            if other == mode: continue
            drift = abs(low[:, other].mean() - high[:, other].mean())
            other_drift += drift
        print(f"    Mode {mode+1}: other-mode drift = {other_drift:.4f} "
              f"({'independent' if other_drift < 0.5 else 'COUPLED'})")


if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  CARRY FLOW — Session 3: W Controls Carry Modes          ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Collect data
    W_arr, carry_arr, hash_data = measure_w_to_carry_control(n_samples=10000)

    # PCA
    print("\n  Computing PCA...")
    pca = find_principal_modes(carry_arr)

    # Correlation
    corr_matrix, ring, coords = correlation_analysis(W_arr, carry_arr, pca)

    # Find dominant W → mode connections
    print(f"\n  STRONGEST W → MODE CONNECTIONS:")
    connections = []
    for k in range(16):
        for j in range(min(15, corr_matrix.shape[1])):
            connections.append((abs(corr_matrix[k, j]), k, j, corr_matrix[k, j]))
    connections.sort(reverse=True)
    for _, k, j, c in connections[:10]:
        print(f"    W[{k:>2}] → Mode {j+1:>2}: corr = {c:>+.4f}")

    # Linearity
    r2 = linearity_test(W_arr, coords)

    # Jacobian
    sensitivity = jacobian_analysis(n_samples=3000)

    # Controllability
    controllability_test(W_arr, carry_arr, coords, ring)

    print(f"""
═══════════════════════════════════════════════════════════════
SESSION 3 COMPLETE: W → Carry Flow

  CORRELATION: W[k] controls specific carry modes
  LINEARITY: R² scores show how predictable each mode is
  JACOBIAN: bit-flip sensitivity maps W → carry changes
  CONTROLLABILITY: can we reach arbitrary carry targets?

  KEY INSIGHT: If R² > 0.5 for some modes → those modes are
  LINEARLY controllable through W. We can solve for W using
  simple linear regression.

  If modes are independent: we can control each separately.
  If modes are coupled: we need to solve jointly.

  NEXT SESSION 4: Use these control maps to INVERT the carry-web.
  Given target carry pattern → solve for W → get SHA-256 preimage.
═══════════════════════════════════════════════════════════════
""")
