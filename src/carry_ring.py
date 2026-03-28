"""
CARRY ALGEBRA — Session 2: The Carry Ring

Effective dimension = 11. We need to find:
1. The 11 principal carry modes (what combinations of rounds matter)
2. Algebraic structure on these modes
3. Parameterization: 11 parameters → 64 carry bits → SHA-256 output
"""

import numpy as np
import time
import struct
from collections import Counter
from carry_algebra_foundation import sha256_with_carries, CarrySpace, K256, IV, M32

# ════════════════════════════════════════════════════════════
# STEP 1: Extract principal carry modes via PCA
# ════════════════════════════════════════════════════════════

def collect_carry_data(n_samples=20000):
    """Collect carry patterns and corresponding hashes."""
    patterns = []
    hashes = []
    messages = []

    for _ in range(n_samples):
        W = [np.random.randint(0, 2**32) for _ in range(16)]
        H, carries, raw = sha256_with_carries(W)
        patterns.append(carries)
        hashes.append(H)
        messages.append(W)

    return np.array(patterns, dtype=np.float64), hashes, messages


def find_principal_modes(patterns):
    """PCA on carry patterns to find the 11 effective dimensions."""
    # Center the data
    mean = patterns.mean(axis=0)
    centered = patterns - mean

    # Only keep variable rounds (std > 0.001)
    variable_rounds = [r for r in range(64) if patterns[:, r].std() > 0.001]
    print(f"  Variable rounds: {len(variable_rounds)}/64")

    # PCA on variable rounds
    X = centered[:, variable_rounds]
    cov = X.T @ X / len(X)

    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    # Sort descending
    idx = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]

    # How many components needed for 95% variance?
    total_var = sum(eigenvalues)
    cumsum = 0
    n_components = 0
    for i, ev in enumerate(eigenvalues):
        cumsum += ev
        if cumsum >= 0.95 * total_var:
            n_components = i + 1
            break

    return {
        'variable_rounds': variable_rounds,
        'eigenvalues': eigenvalues,
        'eigenvectors': eigenvectors,
        'mean': mean,
        'n_components_95': n_components,
        'total_variance': total_var,
    }


def analyze_modes(pca_result, patterns):
    """Understand what each principal mode means."""
    vr = pca_result['variable_rounds']
    evecs = pca_result['eigenvectors']
    evals = pca_result['eigenvalues']
    total = pca_result['total_variance']

    print(f"\n  PRINCIPAL CARRY MODES (95% variance in {pca_result['n_components_95']} components):")
    print(f"  {'Mode':>6} {'Variance%':>10} {'Cumul%':>8} {'Top rounds (by weight)':>40}")
    print(f"  {'─'*68}")

    cumsum = 0
    modes = []
    for i in range(min(15, len(evals))):
        var_pct = evals[i] / total * 100
        cumsum += var_pct
        # Which rounds contribute most to this mode?
        weights = evecs[:, i]
        top_indices = np.argsort(np.abs(weights))[::-1][:5]
        top_rounds = [(vr[j], weights[j]) for j in top_indices]
        top_str = ', '.join(f'r{r}({w:+.2f})' for r, w in top_rounds)

        print(f"  {i+1:>6} {var_pct:>9.1f}% {cumsum:>7.1f}% {top_str:>40}")
        modes.append({
            'index': i,
            'variance_pct': var_pct,
            'top_rounds': top_rounds,
            'vector': weights,
        })

    return modes


# ════════════════════════════════════════════════════════════
# STEP 2: Project carry patterns to reduced space
# ════════════════════════════════════════════════════════════

class CarryRing:
    """
    Algebraic structure on the reduced carry space.

    Maps 64-dim carry patterns to 11-dim reduced coordinates.
    Operations in reduced space:
      - Addition (component-wise in PCA space)
      - Distance (Euclidean in PCA space)
      - Projection (from full to reduced)
      - Reconstruction (from reduced to full, approximate)
    """
    def __init__(self, pca_result, n_components=None):
        self.pca = pca_result
        self.n_comp = n_components or pca_result['n_components_95']
        self.vr = pca_result['variable_rounds']
        self.mean = pca_result['mean']
        self.basis = pca_result['eigenvectors'][:, :self.n_comp]  # (n_var, n_comp)

    def project(self, phi):
        """Map 64-dim carry pattern to reduced coordinates."""
        x = np.array(phi, dtype=np.float64)
        x_var = x[self.vr] - self.mean[self.vr]
        return x_var @ self.basis  # (n_comp,)

    def reconstruct(self, coords):
        """Map reduced coordinates back to 64-dim carry pattern (approximate)."""
        x_var = coords @ self.basis.T + self.mean[self.vr]
        full = np.array(self.mean)
        full[self.vr] = x_var
        return (full > 0.5).astype(int)  # threshold to binary

    def distance(self, phi1, phi2):
        """Distance in reduced carry space."""
        c1 = self.project(phi1)
        c2 = self.project(phi2)
        return np.linalg.norm(c1 - c2)

    def encode(self, phi):
        """Encode carry pattern as compact integer (discretized PCA coords)."""
        coords = self.project(phi)
        # Discretize to ±1
        bits = tuple(1 if c > 0 else 0 for c in coords)
        return bits

    def neighborhood_in_reduced(self, phi, n_neighbors=10):
        """Find nearby carry patterns in reduced space."""
        coords = self.project(phi)
        neighbors = []
        # Flip each PCA component
        for i in range(self.n_comp):
            new_coords = coords.copy()
            new_coords[i] = -new_coords[i]  # flip sign
            new_phi = self.reconstruct(new_coords)
            neighbors.append(new_phi)
        return neighbors


# ════════════════════════════════════════════════════════════
# STEP 3: Hash variation across carry modes
# ════════════════════════════════════════════════════════════

def hash_variation_by_mode(patterns, hashes, ring):
    """How much does the hash change when we move along each mode?"""
    print(f"\n  HASH SENSITIVITY TO CARRY MODES:")
    print(f"  {'Mode':>6} {'ΔH (bits)':>10} {'H[7] corr':>10} {'Meaning'}")
    print(f"  {'─'*50}")

    coords = np.array([ring.project(p) for p in patterns])
    h7_bits = np.array([h[7] & 1 for h in hashes])  # LSB of H[7]

    for mode in range(min(ring.n_comp, 10)):
        # Correlation between this mode's coordinate and hash bits
        c = coords[:, mode]
        if c.std() > 0.001:
            corr = np.corrcoef(c, h7_bits)[0, 1]
        else:
            corr = 0

        # Average hash distance between high/low mode values
        median = np.median(c)
        high = patterns[c > median]
        low = patterns[c <= median]

        # Hamming distance of hashes
        h_high = [hashes[i] for i in range(len(patterns)) if c[i] > median]
        h_low = [hashes[i] for i in range(len(patterns)) if c[i] <= median]

        if h_high and h_low:
            # Average bit difference in H[7]
            diff_bits = np.mean([bin(h_high[i][7] ^ h_low[i % len(h_low)][7]).count('1')
                                for i in range(min(100, len(h_high)))])
        else:
            diff_bits = 0

        meaning = ""
        if abs(corr) > 0.05:
            meaning = f"← INFLUENCES hash!"
        print(f"  {mode+1:>6} {diff_bits:>9.1f} {corr:>10.4f} {meaning}")


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  CARRY RING — Session 2: Principal Modes & Algebra       ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Collect data
    print("Step 1: Collecting carry data...")
    t0 = time.time()
    patterns, hashes, messages = collect_carry_data(n_samples=10000)
    print(f"  Done in {time.time()-t0:.1f}s")

    # PCA
    print("\nStep 2: Principal Component Analysis...")
    pca = find_principal_modes(patterns)
    modes = analyze_modes(pca, patterns)

    # Build ring
    print(f"\nStep 3: Building Carry Ring (dim={pca['n_components_95']})...")
    ring = CarryRing(pca)

    # Encode all patterns
    encoded = [ring.encode(p) for p in patterns]
    unique_codes = len(set(encoded))
    print(f"  Unique encoded patterns: {unique_codes}")
    print(f"  Compression: 64 bits → {ring.n_comp} bits → {unique_codes} distinct values")

    # Hash sensitivity
    print("\nStep 4: Hash sensitivity analysis...")
    hash_variation_by_mode(patterns, hashes, ring)

    # Test reconstruction
    print("\nStep 5: Reconstruction quality...")
    errors = []
    for p in patterns[:100]:
        coords = ring.project(p)
        recon = ring.reconstruct(coords)
        error = sum(abs(p[r] - recon[r]) for r in range(64))
        errors.append(error)
    avg_error = np.mean(errors)
    print(f"  Average reconstruction error: {avg_error:.2f} bits out of 64")
    print(f"  Reconstruction accuracy: {(64-avg_error)/64*100:.1f}%")

    # Key finding: which rounds are in the "controllable" subspace?
    print(f"\nStep 6: Controllable subspace...")
    # Rounds with high weight in the first few PCA components = controllable
    importance = np.zeros(len(pca['variable_rounds']))
    for i in range(ring.n_comp):
        importance += np.abs(pca['eigenvectors'][:, i]) * pca['eigenvalues'][i]

    controllable = [(pca['variable_rounds'][j], importance[j])
                    for j in range(len(importance))]
    controllable.sort(key=lambda x: -x[1])

    print(f"  Most controllable rounds:")
    for r, imp in controllable[:10]:
        print(f"    Round {r:>2}: importance = {imp:.4f}")

    print(f"""
═══════════════════════════════════════════════════════════════
SESSION 2 COMPLETE: Carry Ring

  Principal modes found: {ring.n_comp}
  Compression: 64 → {ring.n_comp} dimensions ({unique_codes} distinct patterns)
  Reconstruction accuracy: {(64-avg_error)/64*100:.1f}%

  The {ring.n_comp} modes define a RING on carry space:
    - Project: φ ∈ {{0,1}}^64 → c ∈ R^{ring.n_comp}
    - Reconstruct: c → φ (approximate)
    - Distance: ||c₁ - c₂||
    - Navigate: move along modes to explore carry space

  NEXT: Session 3 — use these modes to NAVIGATE carry space
  efficiently. Instead of searching 2^64: search 2^{ring.n_comp}.
═══════════════════════════════════════════════════════════════
""")
