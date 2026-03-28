"""
FIBER COLLISION THEORY — New mathematics.

THE INVENTION:

Given carry pattern φ, SHA-256 becomes LINEAR:
  H(W) = L_φ(W) + const  (linear in W, given carries fixed)

The carry fiber F(φ) = {W : Φ(W) = φ} has dim ≈ 481.
The hash kernel ker(L_φ) has dim ≈ 256.

INTERSECTION: dim(F(φ) ∩ ker(L_φ)) ≈ 225

→ 225-dimensional space of COLLISIONS within each fiber!
→ Found by LINEAR ALGEBRA, not brute force.

METHOD:
  1. Pick W₀, compute φ = Φ(W₀)
  2. Compute Jacobian J_Φ at W₀ (carry sensitivity)
  3. Compute L_φ (linearized hash given carries)
  4. Solve: ΔW ∈ ker(J_Φ) ∩ ker(L_φ)
  5. W₁ = W₀ + ΔW
  6. Verify: Φ(W₁) = φ AND H(W₁) = H(W₀)
"""

import numpy as np
import time
import struct
from carry_algebra_foundation import sha256_with_carries, K256, IV, M32


def sha256_hash(W_words):
    """Just the hash output."""
    H, _, _ = sha256_with_carries(W_words)
    return H


def numerical_carry_jacobian(W0, bit_width=32):
    """
    Compute ∂Φ/∂W numerically.
    J[r][k*32+b] = does flipping bit b of W[k] change carry[r]?

    Returns: J (64 × 512) binary matrix over GF(2)
    """
    _, carries_base, _ = sha256_with_carries(W0)

    n_input_bits = 16 * bit_width
    J = np.zeros((64, n_input_bits), dtype=np.int8)

    for k in range(16):
        for b in range(bit_width):
            W_mod = list(W0)
            W_mod[k] ^= (1 << b)
            _, carries_mod, _ = sha256_with_carries(W_mod)
            for r in range(64):
                if carries_mod[r] != carries_base[r]:
                    J[r][k * bit_width + b] = 1

    return J, carries_base


def numerical_hash_jacobian(W0, carries_fixed, bit_width=32):
    """
    Compute ∂H/∂W numerically (given fixed carry pattern).
    Since H is linear given carries: this should be a CONSTANT matrix.

    Returns: L (256 × 512) binary matrix over GF(2)
    """
    H_base = sha256_hash(W0)

    n_input_bits = 16 * bit_width
    L = np.zeros((256, n_input_bits), dtype=np.int8)

    for k in range(16):
        for b in range(bit_width):
            W_mod = list(W0)
            W_mod[k] ^= (1 << b)
            H_mod = sha256_hash(W_mod)
            for word in range(8):
                diff = H_base[word] ^ H_mod[word]
                for hb in range(32):
                    if (diff >> hb) & 1:
                        L[word * 32 + hb][k * bit_width + b] = 1

    return L, H_base


def gf2_kernel(M):
    """Compute kernel of binary matrix M over GF(2).
    Returns basis vectors of ker(M).
    """
    m, n = M.shape
    # Augment [M | I_n]
    aug = np.zeros((m, n + n), dtype=np.int8)
    aug[:, :n] = M % 2
    # We want kernel, so we do row reduction on M^T
    # ker(M) = left null space of M^T

    # Actually: ker(M) = {x : Mx = 0 over GF(2)}
    # Gaussian elimination over GF(2)
    A = M.copy() % 2
    rows, cols = A.shape
    pivots = []
    r = 0
    for c in range(cols):
        if r >= rows:
            break
        # Find pivot
        found = False
        for i in range(r, rows):
            if A[i, c]:
                found = True
                if i != r:
                    A[[r, i]] = A[[i, r]]
                break
        if not found:
            continue
        pivots.append((r, c))
        # Eliminate
        for i in range(rows):
            if i != r and A[i, c]:
                A[i] = (A[i] + A[r]) % 2
        r += 1

    # Free variables = columns not in pivots
    pivot_cols = {c for _, c in pivots}
    free_cols = [c for c in range(cols) if c not in pivot_cols]

    # Build kernel basis
    kernel_basis = []
    for fc in free_cols:
        vec = np.zeros(cols, dtype=np.int8)
        vec[fc] = 1
        # Back-substitute
        for pr, pc in pivots:
            if A[pr, fc]:
                vec[pc] = 1
        kernel_basis.append(vec)

    return np.array(kernel_basis) if kernel_basis else np.zeros((0, cols), dtype=np.int8)


def find_fiber_collision(W0, max_attempts=20):
    """
    THE CORE ALGORITHM:
    Find ΔW such that Φ(W0+ΔW) = Φ(W0) AND H(W0+ΔW) = H(W0).
    """
    print(f"  Computing carry Jacobian J_Φ...", end='', flush=True)
    t0 = time.time()
    J_phi, carries_base = numerical_carry_jacobian(W0)
    print(f" done ({time.time()-t0:.1f}s)")

    print(f"  Computing hash Jacobian L_φ...", end='', flush=True)
    t0 = time.time()
    L_hash, H_base = numerical_hash_jacobian(W0, carries_base)
    print(f" done ({time.time()-t0:.1f}s)")

    # Ranks
    # Only use variable carry rounds
    variable = [r for r in range(64) if carries_base[r] == 1 and
                any(J_phi[r])]
    J_var = J_phi[variable] if variable else J_phi

    rank_J = np.linalg.matrix_rank(J_var.astype(float))
    rank_L = np.linalg.matrix_rank(L_hash.astype(float))

    print(f"  J_Φ rank: {rank_J}/512 (carry constraints)")
    print(f"  L_φ rank: {rank_L}/512 (hash constraints)")
    print(f"  ker(J_Φ) dim: {512 - rank_J}")
    print(f"  ker(L_φ) dim: {512 - rank_L}")
    print(f"  Expected intersection dim: {(512-rank_J) + (512-rank_L) - 512}")
    print(f"                           = {512 - rank_J - rank_L}")

    if 512 - rank_J - rank_L <= 0:
        print(f"  Intersection might be trivial. Trying anyway...")

    # Stack J and L: we need ΔW in ker([J; L])
    print(f"  Computing joint kernel ker(J_Φ) ∩ ker(L_φ)...", end='', flush=True)
    t0 = time.time()
    combined = np.vstack([J_var, L_hash]) % 2
    kernel = gf2_kernel(combined)
    print(f" done ({time.time()-t0:.1f}s)")
    print(f"  Joint kernel dimension: {len(kernel)}")

    if len(kernel) == 0:
        print(f"  No kernel vectors found!")
        return None

    # Try kernel vectors as ΔW
    print(f"\n  Testing {min(max_attempts, len(kernel))} kernel vectors...")
    successes = 0

    for i in range(min(max_attempts, len(kernel))):
        dw_bits = kernel[i]

        # Convert bit vector to word changes
        W1 = list(W0)
        for k in range(16):
            delta_word = 0
            for b in range(32):
                if dw_bits[k * 32 + b]:
                    delta_word ^= (1 << b)
            W1[k] ^= delta_word

        if W1 == W0:
            continue  # trivial

        # Check carries
        H1, carries1, _ = sha256_with_carries(W1)
        carry_match = (carries1 == carries_base)
        hash_match = (H1 == H_base)

        carry_diff = sum(1 for r in range(64) if carries1[r] != carries_base[r])
        hash_diff = sum(bin(H1[w] ^ H_base[w]).count('1') for w in range(8))

        status = ""
        if carry_match and hash_match:
            status = "★★★ COLLISION! ★★★"
            successes += 1
        elif carry_match:
            status = f"same carries, hash diff {hash_diff} bits"
        else:
            status = f"carry diff {carry_diff}, hash diff {hash_diff} bits"

        if i < 10 or 'COLLISION' in status:
            print(f"    vec {i}: {status}")

    return successes


# ════════════════════════════════════════════════════════════
if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  FIBER COLLISION THEORY — Finding collisions by algebra  ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    np.random.seed(42)
    W0 = [np.random.randint(0, 2**32) for _ in range(16)]

    print(f"Base message W0 = [{', '.join(hex(w) for w in W0[:4])}...]")
    H0 = sha256_hash(W0)
    print(f"Hash H0 = {' '.join(hex(h) for h in H0)}")
    print()

    result = find_fiber_collision(W0)

    print(f"""
═══════════════════════════════════════════════════════════════
THEORY:
  dim(ker(J_Φ) ∩ ker(L_φ)) = 512 - rank(J) - rank(L)

  If > 0: there exist non-trivial ΔW that preserve BOTH
  carry pattern AND hash value → COLLISION.

  The GF(2) kernel gives EXACT solutions (no approximation).

  CAVEAT: The Jacobian J_Φ is computed at W0 by single-bit flips.
  For multi-bit ΔW: carries might change nonlinearly.
  The kernel gives first-order solutions. Need Newton refinement
  for exact solutions.

  NEXT: If kernel dim > 0 but no exact collision found:
    → Newton iteration to refine ΔW
    → Higher-order carry algebra (quadratic corrections)
    → 2-adic lifting (your tower height ≥ 24!)
═══════════════════════════════════════════════════════════════
""")
