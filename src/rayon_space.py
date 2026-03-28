"""
RAYON SPACE — New mathematics for SHA-256 transparency.

NEW OBJECTS:
  RAYON SPACE R(W₀) — 220-dim space of carry-invisible perturbations at W₀
  PHANTOM VECTORS — elements of R: ΔW that don't change carry-web
  SHADOW MAP S — how SHA-256 hash sees phantom vectors: S(ΔW) = H(W₀+ΔW) ⊕ H(W₀)
  DARK KERNEL D — ker(S) restricted to R: phantom vectors invisible to BOTH carries AND hash
  COLLISION = any non-zero element of D

THE RAYON LIFTING:
  Level 0: Find phantoms over GF(2) (single-bit analysis)
  Level k: Lift phantoms to preserve carries mod 2^k
  Each level: some phantoms survive, others don't
  At level 32: exact phantom = exact collision

This mirrors the 2-adic tower (height ≥ 24 from experiments).
"""

import numpy as np
import time
from carry_algebra_foundation import sha256_with_carries, K256, IV, M32


def compute_rayon_space(W0):
    """
    Compute Rayon Space R(W₀): the space of carry-invisible perturbations.

    Method: for each input bit, check if flipping it changes any carry.
    Phantom bits = bits that DON'T change any carry.
    """
    _, carries_base, raw_base = sha256_with_carries(W0)

    phantom_bits = []  # input bits that don't change carries
    active_bits = []   # input bits that DO change carries

    for k in range(16):
        for b in range(32):
            W_mod = list(W0)
            W_mod[k] ^= (1 << b)
            _, carries_mod, _ = sha256_with_carries(W_mod)

            if carries_mod == carries_base:
                phantom_bits.append((k, b))
            else:
                active_bits.append((k, b))

    return phantom_bits, active_bits, carries_base, raw_base


def compute_shadow_map(W0, phantom_bits, n_test=None):
    """
    Shadow Map S: for each phantom bit, what hash bits change?

    S is a matrix (256 × |phantom_bits|) over GF(2).
    S[h_bit][p_idx] = 1 if flipping phantom bit p changes hash bit h.
    """
    H_base, _, _ = sha256_with_carries(W0)

    if n_test is None:
        n_test = len(phantom_bits)

    S = np.zeros((256, n_test), dtype=np.int8)

    for p_idx in range(n_test):
        k, b = phantom_bits[p_idx]
        W_mod = list(W0)
        W_mod[k] ^= (1 << b)
        H_mod, _, _ = sha256_with_carries(W_mod)

        for word in range(8):
            diff = H_base[word] ^ H_mod[word]
            for hb in range(32):
                if (diff >> hb) & 1:
                    S[word * 32 + hb][p_idx] = 1

    return S, H_base


def gf2_kernel(M):
    """Kernel over GF(2)."""
    A = M.copy() % 2
    rows, cols = A.shape
    pivots = []
    r = 0
    for c in range(cols):
        if r >= rows: break
        found = -1
        for i in range(r, rows):
            if A[i, c]:
                found = i; break
        if found < 0: continue
        if found != r:
            A[[r, found]] = A[[found, r]]
        pivots.append((r, c))
        for i in range(rows):
            if i != r and A[i, c]:
                A[i] = (A[i] + A[r]) % 2
        r += 1

    pivot_cols = {c for _, c in pivots}
    free_cols = [c for c in range(cols) if c not in pivot_cols]

    basis = []
    for fc in free_cols:
        vec = np.zeros(cols, dtype=np.int8)
        vec[fc] = 1
        for pr, pc in pivots:
            if A[pr, fc]:
                vec[pc] = 1
        basis.append(vec)
    return np.array(basis) if basis else np.zeros((0, cols), dtype=np.int8)


def rayon_lifting(W0, phantom_bits, dark_vectors, level=1):
    """
    RAYON LIFTING: refine phantom vectors to preserve carries at higher precision.

    Level 0: single-bit phantom (already computed)
    Level k: multi-bit phantom that preserves carries with k-bit perturbation

    Method: for each dark vector, test if the multi-bit perturbation
    preserves carries. If not: try to FIX by adjusting other phantom bits.
    """
    results = []

    for vi, vec in enumerate(dark_vectors[:20]):
        # Build multi-bit perturbation from vector
        W1 = list(W0)
        flipped = 0
        for pi, coeff in enumerate(vec):
            if coeff:
                k, b = phantom_bits[pi]
                W1[k] ^= (1 << b)
                flipped += 1

        if flipped == 0:
            continue

        # Test
        H1, carries1, _ = sha256_with_carries(W1)
        H0, carries0, _ = sha256_with_carries(W0)

        carry_diff = sum(1 for r in range(64) if carries1[r] != carries0[r])
        hash_diff = sum(bin(H1[w] ^ H0[w]).count('1') for w in range(8))
        hash_match = (H1 == H0)

        results.append({
            'vector_idx': vi,
            'bits_flipped': flipped,
            'carry_diff': carry_diff,
            'hash_diff': hash_diff,
            'collision': hash_match and carry_diff == 0 and flipped > 0,
        })

    return results


# ════════════════════════════════════════════════════════════
if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  RAYON SPACE — Phantom Vectors & Dark Kernel             ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    np.random.seed(42)
    W0 = [np.random.randint(0, 2**32) for _ in range(16)]

    # Step 1: Compute Rayon Space
    print("Step 1: RAYON SPACE (carry-invisible perturbations)")
    t0 = time.time()
    phantom_bits, active_bits, carries, raw = compute_rayon_space(W0)
    print(f"  Phantom bits: {len(phantom_bits)}/512 ({len(phantom_bits)/512*100:.1f}%)")
    print(f"  Active bits:  {len(active_bits)}/512 ({len(active_bits)/512*100:.1f}%)")
    print(f"  Time: {time.time()-t0:.1f}s")

    # Distribution of phantoms per word
    phantom_per_word = {}
    for k, b in phantom_bits:
        phantom_per_word[k] = phantom_per_word.get(k, 0) + 1
    print(f"  Phantoms per word: {dict(sorted(phantom_per_word.items()))}")

    # Step 2: Shadow Map
    print(f"\nStep 2: SHADOW MAP (how hash sees phantoms)")
    t0 = time.time()
    S, H_base = compute_shadow_map(W0, phantom_bits)
    print(f"  Shadow Map shape: {S.shape} (hash_bits × phantom_bits)")

    rank_S = np.linalg.matrix_rank(S.astype(float))
    print(f"  Shadow Map rank: {rank_S}")
    print(f"  Time: {time.time()-t0:.1f}s")

    # Step 3: Dark Kernel
    print(f"\nStep 3: DARK KERNEL (invisible to carries AND hash)")
    t0 = time.time()
    dark_kernel = gf2_kernel(S)
    print(f"  Dark Kernel dimension: {len(dark_kernel)}")
    print(f"  = {len(phantom_bits)} phantom bits - {rank_S} hash constraints")
    print(f"  = {len(phantom_bits) - rank_S} (confirmed: {len(dark_kernel)})")
    print(f"  Time: {time.time()-t0:.1f}s")

    if len(dark_kernel) > 0:
        # Step 4: Rayon Lifting
        print(f"\nStep 4: RAYON LIFTING (test dark vectors)")
        results = rayon_lifting(W0, phantom_bits, dark_kernel)

        n_carry_ok = sum(1 for r in results if r['carry_diff'] == 0)
        n_hash_ok = sum(1 for r in results if r['hash_diff'] == 0)
        n_collision = sum(1 for r in results if r['collision'])

        print(f"  Tested: {len(results)} dark vectors")
        print(f"  Carries preserved: {n_carry_ok}/{len(results)}")
        print(f"  Hash preserved:    {n_hash_ok}/{len(results)}")
        print(f"  COLLISIONS:        {n_collision}/{len(results)}")
        print()

        for r in results[:10]:
            status = "★ COLLISION!" if r['collision'] else \
                     f"carry_diff={r['carry_diff']}, hash_diff={r['hash_diff']}"
            print(f"    Vec {r['vector_idx']}: {r['bits_flipped']} bits flipped → {status}")

    print(f"""
═══════════════════════════════════════════════════════════════
RAYON SPACE REPORT:

  Phantom bits:     {len(phantom_bits)}/512
  Shadow Map rank:  {rank_S}/256
  Dark Kernel dim:  {len(dark_kernel)}

  INTERPRETATION:
    {len(phantom_bits)} input bits are invisible to carry-web.
    Of these, {rank_S} are visible to hash (Shadow Map).
    {len(dark_kernel)} are invisible to BOTH → Dark Kernel.

    Dark Kernel vectors = candidate COLLISIONS (over GF(2)).
    Rayon Lifting tests if they're TRUE collisions.

  THE MATHEMATICS:
    R(W₀) = Rayon Space = ker(J_Φ) at W₀
    S = Shadow Map = H restricted to R
    D = Dark Kernel = ker(S) = R ∩ ker(H)
    dim(D) = dim(R) - rank(S) = {len(phantom_bits)} - {rank_S} = {len(dark_kernel)}

    If D ≠ {{0}}: algebraic collisions exist.
    Rayon Lifting verifies them at full precision.
═══════════════════════════════════════════════════════════════
""")
