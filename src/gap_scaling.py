"""
GAP SCALING: How does triangle/non-triangle gap ratio scale with N?

For small N (4-6): ratio ≈ 1.36-1.52 from exact computation.
Question: does it stay > 1 for large N, or converge to 1?

Method: SAMPLE random graphs instead of enumerating all 2^n.
This scales to N = 20, 50, 100+.

For each random graph:
  1. Check if it contains a k-clique
  2. Record edge presence conditioned on clique/no-clique
  3. Compute gaps for single edges, edge pairs, edge triples
"""

import random
import math
from itertools import combinations
from collections import defaultdict
import time


def has_k_clique(adj, N, k):
    """Check if adjacency matrix has a k-clique."""
    for subset in combinations(range(N), k):
        if all(adj[a][b] for a in subset for b in subset if a < b):
            return True
    return False


def sample_gap_statistics(N, k, n_samples=10000):
    """Sample random graphs and compute conditional gap statistics."""
    n_edges = N * (N - 1) // 2

    # Statistics accumulators
    edge_count_clique = defaultdict(int)      # edge (u,v) present when clique exists
    edge_count_no_clique = defaultdict(int)    # edge (u,v) present when no clique
    pair_count_clique = defaultdict(int)       # pair of edges both present, clique
    pair_count_no_clique = defaultdict(int)    # pair of edges both present, no clique
    triple_count_clique = defaultdict(int)     # triple of edges all present, clique
    triple_count_no_clique = defaultdict(int)  # triple of edges all present, no clique

    n_clique = 0
    n_no_clique = 0

    # Edge index
    edge_list = []
    edge_idx = {}
    idx = 0
    for u in range(N):
        for v in range(u + 1, N):
            edge_list.append((u, v))
            edge_idx[(u, v)] = idx
            idx += 1

    # Identify triangle edge triples
    triangle_triples = set()
    non_triangle_triples = set()
    for subset in combinations(range(N), 3):
        a, b, c = subset
        e1 = edge_idx[(min(a,b), max(a,b))]
        e2 = edge_idx[(min(a,c), max(a,c))]
        e3 = edge_idx[(min(b,c), max(b,c))]
        triple = tuple(sorted([e1, e2, e3]))
        triangle_triples.add(triple)

    # Sample a few non-triangle triples for comparison
    all_triples_sample = []
    for _ in range(min(100, n_edges * 3)):
        t = tuple(sorted(random.sample(range(n_edges), 3)))
        if t not in triangle_triples:
            non_triangle_triples.add(t)
        all_triples_sample.append(t)

    for _ in range(n_samples):
        # Random graph G(N, 1/2)
        adj = [[False] * N for _ in range(N)]
        edges_present = set()
        for u in range(N):
            for v in range(u + 1, N):
                if random.random() < 0.5:
                    adj[u][v] = adj[v][u] = True
                    edges_present.add(edge_idx[(u, v)])

        clique = has_k_clique(adj, N, k)

        if clique:
            n_clique += 1
            for e in edges_present:
                edge_count_clique[e] += 1
            # Triangle triples
            for triple in triangle_triples:
                if all(e in edges_present for e in triple):
                    triple_count_clique[triple] += 1
            # Non-triangle triples (sample)
            for triple in list(non_triangle_triples)[:50]:
                if all(e in edges_present for e in triple):
                    triple_count_no_clique[triple] = triple_count_no_clique.get(triple, 0)  # init
                    triple_count_clique[triple] = triple_count_clique.get(triple, 0) + 1
        else:
            n_no_clique += 1
            for e in edges_present:
                edge_count_no_clique[e] += 1
            for triple in triangle_triples:
                if all(e in edges_present for e in triple):
                    triple_count_no_clique[triple] += 1
            for triple in list(non_triangle_triples)[:50]:
                if all(e in edges_present for e in triple):
                    triple_count_no_clique[triple] = triple_count_no_clique.get(triple, 0) + 1

    if n_clique == 0 or n_no_clique == 0:
        return None

    # Compute gaps
    # Single edge gap
    single_gaps = []
    for e in range(n_edges):
        p1 = edge_count_clique.get(e, 0) / n_clique
        p0 = edge_count_no_clique.get(e, 0) / n_no_clique
        single_gaps.append(p1 - p0)

    # Triangle triple gap
    tri_gaps = []
    for triple in triangle_triples:
        p1 = triple_count_clique.get(triple, 0) / n_clique
        p0 = triple_count_no_clique.get(triple, 0) / n_no_clique
        tri_gaps.append(p1 - p0)

    # Non-triangle triple gap
    nontri_gaps = []
    for triple in list(non_triangle_triples)[:50]:
        p1 = triple_count_clique.get(triple, 0) / n_clique
        p0 = triple_count_no_clique.get(triple, 0) / n_no_clique
        nontri_gaps.append(p1 - p0)

    return {
        'N': N, 'k': k, 'n_clique': n_clique, 'n_no_clique': n_no_clique,
        'balance': n_clique / n_samples,
        'avg_single_gap': sum(abs(g) for g in single_gaps) / len(single_gaps),
        'avg_triangle_gap': sum(abs(g) for g in tri_gaps) / len(tri_gaps) if tri_gaps else 0,
        'avg_nontri_gap': sum(abs(g) for g in nontri_gaps) / len(nontri_gaps) if nontri_gaps else 0,
        'n_triangles': len(triangle_triples),
        'amplification': 1.0 / (sum(abs(g) for g in single_gaps) / len(single_gaps)) if single_gaps else 0,
    }


print("GAP SCALING WITH N FOR k-CLIQUE")
print("═" * 70)
print()
print(f"{'N':>4} {'k':>3} {'balance':>8} {'single_gap':>11} {'tri_gap':>10} {'nontri_gap':>11} {'ratio':>7} {'#tri':>6} {'time':>6}")
print("-" * 70)

for N in [4, 5, 6, 7, 8, 9, 10, 12, 15]:
    k = 3
    n_samples = 20000 if N <= 8 else (5000 if N <= 12 else 2000)

    t0 = time.time()
    result = sample_gap_statistics(N, k, n_samples)
    dt = time.time() - t0

    if result is None:
        print(f"{N:>4} {k:>3}  (all graphs have/lack clique, skip)")
        continue

    ratio = result['avg_triangle_gap'] / result['avg_nontri_gap'] if result['avg_nontri_gap'] > 1e-6 else float('inf')

    print(f"{N:>4} {k:>3} {result['balance']:>8.4f} {result['avg_single_gap']:>11.6f} "
          f"{result['avg_triangle_gap']:>10.6f} {result['avg_nontri_gap']:>11.6f} "
          f"{ratio:>7.3f} {result['n_triangles']:>6} {dt:>5.1f}s")

print()
print("SCALING ANALYSIS:")
print("  If ratio → 1: gap argument fails (non-triangle can substitute)")
print("  If ratio stays > 1: potential for lower bound proof")
print("  If ratio grows: even stronger argument possible")
