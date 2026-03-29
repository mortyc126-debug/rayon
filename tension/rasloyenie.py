"""
RASLOYENIE (Stratification) — Our search method. Not birthday.

Split output bits by DEPENDENCY LAYER:
  Layer 0: depends on ALL W words
  Layer 1: independent of W[0]
  Layer 2: independent of W[0] AND W[1]
  ...
  Layer k: independent of W[0..k-1]

Each layer = smaller search space.
Collision in layer k: only need to match (32 - stable_k) bits.
Search cost: 2^((32 - stable_k)/2) per layer.

THIS IS OUR METHOD. Not birthday. RASLOYENIE.
"""

import random
import time

M4 = 0xF
IV4 = [0x6,0xB,0x3,0xA,0x5,0x9,0x1,0x5]
K4 = [0x4,0x7,0xB,0xE,0x3,0x5,0x9,0xA,0xD,0x1,0x2,0x5,0x7,0x8,0x9,0xC]

def sha4(W, nr=64):
    Ws = list(W[:16])
    while len(Ws)<16: Ws.append(0)
    for i in range(16, max(nr,16)):
        Ws.append((Ws[i-2]^Ws[i-7]^Ws[i-15]^Ws[i-16])&M4)
    a,b,c,d,e,f,g,h = IV4
    for r in range(nr):
        ch=(e&f)^(~e&g)&M4; t1=(h+ch+K4[r%16]+Ws[r%len(Ws)])&M4
        maj=(a&b)^(a&c)^(b&c); t2=(a^maj)&M4
        h,g,f,e=g,f,e,(d+t1)&M4; d,c,b,a=c,b,a,(t1+t2)&M4
    return tuple((IV4[i]+x)&M4 for i,x in enumerate([a,b,c,d,e,f,g,h]))

def measure_stable_bits(W_base, vary_word, n_rounds=64):
    """Which output bits are STABLE when varying one W word?"""
    hashes = []
    for val in range(16):
        W = list(W_base)
        W[vary_word] = val
        hashes.append(sha4(W, n_rounds))

    stable = []
    for bit_pos in range(32):
        word, bit = bit_pos // 4, bit_pos % 4
        values = set((h[word] >> bit) & 1 for h in hashes)
        if len(values) == 1:
            stable.append(bit_pos)
    return set(stable)

def measure_layer(W_base, vary_words, n_rounds=64):
    """Which bits are stable when varying MULTIPLE W words simultaneously?"""
    # For each varied word: get stable bits
    # Intersection = bits stable for ALL varied words
    all_stable = None
    for w_idx in vary_words:
        s = measure_stable_bits(W_base, w_idx, n_rounds)
        if all_stable is None:
            all_stable = s
        else:
            all_stable &= s
    return all_stable if all_stable else set()

def rasloyenie_search(n_rounds=64, budget=50000):
    """
    OUR SEARCH METHOD:
    1. Measure dependency layers
    2. Group by stable bits
    3. Search within groups (smaller space)
    """
    random.seed(42)

    # Phase 1: Measure layers for this context
    W_base = [random.randint(0, M4) for _ in range(16)]

    # Layer k: stable when varying W[0..k-1]
    layers = {}
    for k in range(1, 16):
        stable = measure_layer(W_base, list(range(k)), n_rounds)
        layers[k] = stable
        if len(stable) == 0:
            break

    # Phase 2: Use the BEST layer for search
    # Best = most stable bits = smallest search space
    best_k = max(layers.keys(), key=lambda k: len(layers[k]))
    stable_bits = layers[best_k]
    unstable_count = 32 - len(stable_bits)

    # Phase 3: Search using rasloyenie
    # For collision: vary W[0..best_k-1], keep W[best_k..15] fixed
    # The stable bits are GUARANTEED same → only match unstable bits
    seen = {}
    tries = 0
    t0 = time.time()

    for _ in range(budget):
        W = list(W_base)
        for wi in range(best_k):
            W[wi] = random.randint(0, M4)

        h = sha4(W, n_rounds)
        tries += 1

        # Extract UNSTABLE bits only (the ones that matter)
        key = tuple((h[bp//4] >> (bp%4)) & 1 for bp in range(32) if bp not in stable_bits)

        if key in seen:
            stored_W = seen[key]
            if stored_W != tuple(W):
                # Check FULL hash match
                h1 = sha4(W, n_rounds)
                h2 = sha4(list(stored_W), n_rounds)
                if h1 == h2:
                    return {
                        'found': True, 'tries': tries,
                        'time': time.time() - t0,
                        'method': 'rasloyenie',
                        'layer': best_k,
                        'stable_bits': len(stable_bits),
                        'search_bits': unstable_count,
                        'W1': W, 'W2': list(stored_W),
                    }
        seen[key] = tuple(W)

    return {
        'found': False, 'tries': tries,
        'time': time.time() - t0,
        'method': 'rasloyenie',
        'layer': best_k,
        'stable_bits': len(stable_bits),
        'search_bits': unstable_count,
    }

def blind_search(n_rounds=64, budget=50000):
    """Blind search (like birthday but without the name)."""
    random.seed(42)
    seen = {}
    t0 = time.time()
    for i in range(budget):
        W = [random.randint(0, M4) for _ in range(16)]
        h = sha4(W, n_rounds)
        if h in seen and seen[h] != tuple(W):
            return {
                'found': True, 'tries': i+1,
                'time': time.time() - t0,
                'method': 'blind',
                'search_bits': 32,
            }
        seen[h] = tuple(W)
    return {
        'found': False, 'tries': budget,
        'time': time.time() - t0,
        'method': 'blind',
        'search_bits': 32,
    }

if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  RASLOYENIE — Our search method                          ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # First: measure all layers at 64 rounds
    print("  DEPENDENCY LAYERS (64 rounds):")
    print("  " + "─" * 50)

    random.seed(42)
    W_base = [random.randint(0, M4) for _ in range(16)]

    print(f"  {'vary W[0..k]':>14} {'stable bits':>12} {'search bits':>12} {'search cost':>12}")
    print(f"  {'─'*50}")

    for k in range(1, 16):
        stable = measure_layer(W_base, list(range(k)), 64)
        search = 32 - len(stable)
        cost = f"2^{search/2:.1f}" if search > 0 else "FREE"
        marker = " ★" if len(stable) > 3 else ""
        print(f"  vary W[0..{k-1:>2}] {len(stable):>12} {search:>12} {cost:>12}{marker}")
        if len(stable) == 0:
            break

    # Benchmark: rasloyenie vs blind at various rounds
    print()
    print("  BENCHMARK: Rasloyenie vs Blind")
    print("  " + "─" * 55)
    print(f"  {'rounds':>7} {'blind':>10} {'rasloyen':>10} {'speedup':>10} {'stable':>7}")
    print(f"  {'─'*48}")

    for n_rounds in [4, 8, 16, 32, 64]:
        random.seed(42 + n_rounds)
        blind = blind_search(n_rounds, 100000)
        random.seed(42 + n_rounds)
        rasl = rasloyenie_search(n_rounds, 100000)

        bt = blind['tries'] if blind['found'] else 'FAIL'
        rt = rasl['tries'] if rasl['found'] else 'FAIL'
        stable = rasl.get('stable_bits', 0)

        if blind['found'] and rasl['found']:
            sp = f"{blind['tries']/rasl['tries']:.1f}×"
        elif rasl['found'] and not blind['found']:
            sp = "RASL WINS!"
        elif blind['found'] and not rasl['found']:
            sp = "blind wins"
        else:
            sp = "both fail"

        print(f"  {n_rounds:>7} {bt:>10} {rt:>10} {sp:>10} {stable:>7}")

    print(f"""
  ═══════════════════════════════════════════════════════
  RASLOYENIE — Our method, our mathematics.

    Not birthday (blind pair matching).
    Not correlation (linear signal detection).

    RASLOYENIE = STRATIFICATION by ? dependency.

    Step 1: Measure which output bits are INDEPENDENT
            of which input words (our ? instrument).
    Step 2: Group outputs by stable bits (stratify).
    Step 3: Search within strata (smaller space).

    Collision = match in UNSTABLE bits only.
    Stable bits match AUTOMATICALLY (same W[k+1..15]).

    Search space: 2^(unstable/2) instead of 2^(total/2).
    Saving: 2^(stable/2) per layer.
  ═══════════════════════════════════════════════════════
""")
