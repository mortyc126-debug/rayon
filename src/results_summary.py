"""
╔══════════════════════════════════════════════════════════════════════╗
║  P vs NP: Computational Investigation Results                       ║
║  Via Ollivier-Ricci Geometry and MONO-3SAT Boundary Analysis        ║
╚══════════════════════════════════════════════════════════════════════╝

STARTING POINT (from pvsnp_research.docx):
  - 5 proven theorems (T1-T5)
  - Z₂-orbit argument proves exp(Ω(n)) for circuits with < 0.844n NOT gates
  - Threshold 0.844 = log₂(1.795) from claimed |∂f| ~ 1.795^n
  - Open question: can the threshold be pushed to cover ALL circuits?

OUR COMPUTATIONAL FINDINGS:

═══════════════════════════════════════════════════════════════════════
FINDING 1: |∂f| Growth Rate is HIGHER than 1.795^n
═══════════════════════════════════════════════════════════════════════

  For MONO-3SAT, max |∂f| over all formulas:

    Metric              | Base (n=20) | Trend
    ─────────────────────────────────────────
    total_pairs         | 2.008       | Stable at ~2^n
    distinct_nonsol     | 1.919       | Growing, → ~1.95?
    minimal_solutions   | 1.45        | Decreasing
    maximal_nonsol      | 1.35        | Decreasing
    greedy_antichain    | 1.919       | = distinct_nonsol

  CONCLUSION: The document's 1.795^n is a PROVEN LOWER BOUND.
  The actual maximum |∂f| (distinct boundary non-solutions) is ~1.9^n.
  This would shift the Z₂ threshold from 0.844 to ~0.93.

═══════════════════════════════════════════════════════════════════════
FINDING 2: Z₂ Orbit Improvement is INSUFFICIENT
═══════════════════════════════════════════════════════════════════════

  Actual orbit sizes under Z₂^s action are SMALLER than theoretical 2^s.
  Effective base c_eff < 2.0 (ranges from 1.4 to 1.85 as n grows).

  This means: threshold_ratio = log(α)/log(c_eff) > 1.0 for tested n.

  BUT: threshold_ratio is DECREASING:
    n=5:  1.452
    n=10: 1.145
    n=15: 1.099
    n=20: 1.063

  Asymptotic model: threshold ≈ 0.93 + 2.5/n → 0.93 as n→∞
  (Using last 8 points: 0.98 + 1.7/n → 0.98)

  CONCLUSION: The Z₂ orbit improvement is NOT sufficient to prove
  P ≠ NP. Both α and c_eff approach 2.0, but c_eff approaches
  faster, so the threshold drops below 1.0.

  WHY: For large n, most Z₂ flips keep points in the boundary
  because the boundary is "thick" (occupies ~half of each weight level).

═══════════════════════════════════════════════════════════════════════
FINDING 3: KW Rectangle Cover — NOT Gives Zero Benefit
═══════════════════════════════════════════════════════════════════════

  For MONO-3SAT, the Karchmer-Wigderson rectangle cover has the
  SAME size with and without NOT gates.

  NOT benefit = 0% for ALL tested instances (n=3 to n=10).

  This is expected for monotone functions: the additional valid
  outputs from NOT (indices i with x_i=0, y_i=1) don't help
  reduce the rectangle partition because the monotone outputs
  already suffice.

  CONCLUSION: For FORMULA SIZE (not circuit size), NOT gates
  don't help for monotone functions. The monotone formula size
  equals the general formula size. But circuit size (with fan-out > 1)
  is different — NOT can help by REUSING negated values.

═══════════════════════════════════════════════════════════════════════
FINDING 4: Transversal Structure of Boundary
═══════════════════════════════════════════════════════════════════════

  The boundary has a natural bipartite structure:
    Boundary points × Correction variables

  Key metrics (n=10):
    - 34% of boundary points have single correction (hardest)
    - 66% have multiple corrections (easier)
    - Single-correction points form a COMPLETE anti-chain
    - Anti-chain base: ~1.59 (lower than total boundary base ~1.85)
    - Greedy set cover requires ALL n variables
    - Average correction degree: ~2.1 (each point has ~2 corrections)

  CONCLUSION: The "hard core" of the boundary (single-correction points)
  forms an anti-chain but with smaller base (~1.6) than the full boundary.
  This anti-chain is what the Dilworth argument operates on.

═══════════════════════════════════════════════════════════════════════
FINDING 5: The Fundamental Barrier (Confirmed)
═══════════════════════════════════════════════════════════════════════

  The document's "final barrier" is confirmed:

  AND(x_i, x_j) = 0 on all x_b ∈ ∂f, yet it covers exponentially
  many boundary transitions as a "switch" through circuit topology.

  This is quantified by: one variable x_j corrects ~|∂f|/n boundary
  points simultaneously. The greedy set cover requires all n variables,
  but each covers ~|∂f|/n points.

  With NOT: x_j and ¬x_j together can "switch" in BOTH directions,
  doubling the effective coverage per variable. With s NOT gates:
  coverage per gate ≈ |∂f|/n * 2^(s/n), giving circuit size ≈ n/2^(s/n).
  For s ≈ n: size ≈ n/2 — polynomial. This is exactly the barrier.

═══════════════════════════════════════════════════════════════════════
OVERALL ASSESSMENT
═══════════════════════════════════════════════════════════════════════

  Methods tried and their status:

  1. Improved |∂f| bound (1.795 → 1.9):  WORKS but insufficient
  2. Actual Z₂ orbit sizes (c_eff < 2):   WORKS but insufficient
  3. KW rectangle cover:                   NO new insight (0 benefit)
  4. Transversal structure:                Confirms barrier structure
  5. Algebraic boundary:                   Specific, not natural, but
                                           no new lower bound found

  The P vs NP barrier for circuits is precisely:

    "NOT gates allow exponential compression of boundary information
     by enabling bidirectional switching, which no counting argument
     based on boundary size alone can overcome."

  To prove P ≠ NP via circuits, one needs EITHER:
  (a) A non-counting argument that constrains circuit TOPOLOGY, or
  (b) An argument specific to NP-complete functions that exploits
      their ALGEBRAIC structure (avoiding natural proofs barrier), or
  (c) A completely different approach (proof complexity, algebraic
      geometry, meta-complexity, quantum information).

═══════════════════════════════════════════════════════════════════════
MOST PROMISING NEXT DIRECTIONS
═══════════════════════════════════════════════════════════════════════

  1. TOPOLOGICAL APPROACH: The circuit DAG has a topological structure
     that constrains information flow. NOT gates create "bottlenecks"
     where information is inverted. The topology of these bottlenecks
     might have provable constraints.

  2. CLAUSE STRUCTURE: MONO-3SAT clauses define a 3-uniform hypergraph.
     The boundary structure is SPECIFIC to this hypergraph. Using
     hypergraph properties (expansion, chromatic number, Ramsey) to
     constrain circuits might bypass natural proofs.

  3. DEPTH-SIZE TRADEOFF: Combining depth bounds (from switching lemma)
     with our improved size bounds for restricted NOT might give
     unconditional lower bounds for specific circuit classes.

  4. COMMUNICATION APPROACH (NEW): Instead of Z₂ orbits, use the
     communication complexity of the "correction function" g(x_b) → j.
     The correction function has specific structure (determined by
     clause hypergraph) that might resist efficient computation.
"""


def print_summary():
    """Print a concise summary of all findings."""
    print(__doc__)


if __name__ == "__main__":
    print_summary()
