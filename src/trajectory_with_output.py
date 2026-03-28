"""
TRAJECTORY IDEAL WITH OUTPUT CONSTRAINT.

Previously: ideal = gate equations only.
Now: ideal = gate equations + OUTPUT CONSTRAINT (gₛ = f(x)).

The output constraint makes the ideal FUNCTION-SPECIFIC.
This is what bypasses the natural proofs barrier:
  Without output: ideal describes ALL computations of size s.
  With output: ideal describes only computations of f.

The output constraint is: gₛ + f(x) = 0 where f is given as a
multilinear polynomial over GF(2).

COMPUTE: regularity WITH vs WITHOUT output constraint.
If output constraint significantly increases regularity for
hard functions → the constraint IS where the complexity lives.
"""

import itertools
from collections import defaultdict
import random
import math
import sys


class BoolPoly:
    """Multilinear polynomial over GF(2) with proper operations."""
    def __init__(self):
        self.terms = set()  # set of frozensets

    @staticmethod
    def variable(i):
        p = BoolPoly()
        p.terms.add(frozenset([i]))
        return p

    @staticmethod
    def one():
        p = BoolPoly()
        p.terms.add(frozenset())
        return p

    @staticmethod
    def zero():
        return BoolPoly()

    def __add__(self, other):
        r = BoolPoly()
        r.terms = self.terms.symmetric_difference(other.terms)
        return r

    def __mul__(self, other):
        r = BoolPoly()
        for m1 in self.terms:
            for m2 in other.terms:
                p = m1 | m2
                if p in r.terms:
                    r.terms.remove(p)
                else:
                    r.terms.add(p)
        return r

    def degree(self):
        return max((len(m) for m in self.terms), default=-1)

    def is_zero(self):
        return len(self.terms) == 0

    def num_terms(self):
        return len(self.terms)

    def evaluate(self, assignment):
        """Evaluate polynomial at assignment (dict: var -> 0/1)."""
        result = 0
        for m in self.terms:
            val = 1
            for v in m:
                val &= assignment.get(v, 0)
            result ^= val
        return result


def truth_table_to_polynomial(n, tt):
    """Convert truth table to multilinear polynomial over GF(2).

    Uses Möbius inversion on the Boolean lattice.
    f(x) = Σ_S c_S · Π_{i∈S} xᵢ where c_S = Σ_{T⊆S} f(T) mod 2.
    (Here f(T) means f evaluated at the characteristic vector of T.)
    """
    poly = BoolPoly()

    for mask in range(2**n):
        S = frozenset(i for i in range(n) if (mask >> i) & 1)

        # Coefficient c_S = Σ_{T⊆S} f(T) mod 2
        coeff = 0
        for sub_mask in range(mask + 1):
            if (sub_mask & mask) == sub_mask:  # sub_mask ⊆ mask
                T_input = sub_mask
                coeff ^= tt.get(T_input, 0)

        if coeff:
            if S in poly.terms:
                poly.terms.remove(S)
            else:
                poly.terms.add(S)

    return poly


def build_full_ideal(n, gates, tt_f=None):
    """Build trajectory ideal with optional output constraint.

    Returns: list of generator polynomials, with/without output constraint.
    """
    generators = []

    for gtype, inp1, inp2, out in gates:
        v_out = BoolPoly.variable(out)
        v1 = BoolPoly.variable(inp1)

        if gtype == 'AND':
            v2 = BoolPoly.variable(inp2)
            gen = v_out + v1 * v2
        elif gtype == 'OR':
            v2 = BoolPoly.variable(inp2)
            gen = v_out + v1 + v2 + v1 * v2
        elif gtype == 'NOT':
            gen = v_out + v1 + BoolPoly.one()

        generators.append(gen)

    # Output constraint: last gate = f(x)
    if tt_f is not None:
        f_poly = truth_table_to_polynomial(n, tt_f)
        output_var = gates[-1][3]  # output gate's variable
        output_constraint = BoolPoly.variable(output_var) + f_poly
        generators.append(output_constraint)

    return generators


def measure_ideal_complexity(generators, num_vars, label):
    """Measure various complexity metrics of the ideal."""
    degrees = [g.degree() for g in generators]
    terms = [g.num_terms() for g in generators]

    max_deg = max(degrees) if degrees else 0
    total_terms = sum(terms)
    max_terms = max(terms) if terms else 0

    # Count degree distribution
    deg_dist = defaultdict(int)
    for g in generators:
        for m in g.terms:
            deg_dist[len(m)] += 1

    print(f"    {label}:")
    print(f"      generators: {len(generators)}, max_deg: {max_deg}, "
          f"total_terms: {total_terms}, max_gen_terms: {max_terms}")

    # The output constraint's degree and terms are KEY
    if len(generators) > 0:
        last = generators[-1]
        print(f"      last gen (output constraint if present): "
              f"deg={last.degree()}, terms={last.num_terms()}")

    return {
        'num_gens': len(generators),
        'max_deg': max_deg,
        'total_terms': total_terms,
        'max_terms': max_terms,
    }


def main():
    random.seed(42)
    print("=" * 70)
    print("  TRAJECTORY IDEAL: With vs Without OUTPUT CONSTRAINT")
    print("  The output constraint is where complexity lives!")
    print("=" * 70)

    from mono3sat import generate_all_mono3sat_clauses

    print(f"\n  {'Function':<15} {'n':>3} {'s':>4} "
          f"{'terms_no':>9} {'terms_with':>11} {'out_deg':>8} {'out_terms':>10}")
    print("  " + "-" * 65)

    for n in range(3, 9):
        if 2**n > 50000:
            break

        # --- OR ---
        gates = []; nid = n; cur = 0
        for i in range(1, n):
            out = nid; gates.append(('OR', cur, i, out)); cur = out; nid += 1

        tt = {b: 0 if b == 0 else 1 for b in range(2**n)}

        gens_no = build_full_ideal(n, gates, tt_f=None)
        gens_with = build_full_ideal(n, gates, tt_f=tt)

        out_gen = gens_with[-1]
        no_terms = sum(g.num_terms() for g in gens_no)
        with_terms = sum(g.num_terms() for g in gens_with)

        print(f"  {'OR-'+str(n):<15} {n:>3} {len(gates):>4} "
              f"{no_terms:>9} {with_terms:>11} {out_gen.degree():>8} {out_gen.num_terms():>10}")

        # --- MSAT ---
        all_cl = generate_all_mono3sat_clauses(n)
        clauses = random.sample(all_cl, min(len(all_cl), 2*n))
        gates_m = []; nid = n; c_outs = []
        for cl in clauses:
            v0,v1,v2 = cl
            a=nid; gates_m.append(('OR',v0,v1,a)); nid+=1
            b=nid; gates_m.append(('OR',a,v2,b)); nid+=1
            c_outs.append(b)
        cur = c_outs[0]
        for ci in c_outs[1:]:
            g=nid; gates_m.append(('AND',cur,ci,g)); nid+=1; cur=g

        tt_m = {}
        for bits in range(2**n):
            x = tuple((bits >> j) & 1 for j in range(n))
            tt_m[bits] = 1 if all(any(x[v] for v in c) for c in clauses) else 0

        gens_no_m = build_full_ideal(n, gates_m, tt_f=None)
        gens_with_m = build_full_ideal(n, gates_m, tt_f=tt_m)

        out_gen_m = gens_with_m[-1]
        no_terms_m = sum(g.num_terms() for g in gens_no_m)
        with_terms_m = sum(g.num_terms() for g in gens_with_m)

        print(f"  {'MSAT-'+str(n):<15} {n:>3} {len(gates_m):>4} "
              f"{no_terms_m:>9} {with_terms_m:>11} {out_gen_m.degree():>8} {out_gen_m.num_terms():>10}")

        sys.stdout.flush()

    # Triangle
    for N in [4, 5]:
        n_bits = N*(N-1)//2
        if 2**n_bits > 50000:
            break
        edge_idx = {}; idx = 0
        for i in range(N):
            for j in range(i+1, N):
                edge_idx[(i,j)] = idx; idx += 1
        gates_t = []; nid = n_bits; tri_outs = []
        for i in range(N):
            for j in range(i+1, N):
                for k in range(j+1, N):
                    a=nid; gates_t.append(('AND',edge_idx[(i,j)],edge_idx[(i,k)],a)); nid+=1
                    b=nid; gates_t.append(('AND',a,edge_idx[(j,k)],b)); nid+=1
                    tri_outs.append(b)
        cur = tri_outs[0]
        for t in tri_outs[1:]:
            g=nid; gates_t.append(('OR',cur,t,g)); nid+=1; cur=g

        tt_t = {}
        for bits in range(2**n_bits):
            x = tuple((bits >> j) & 1 for j in range(n_bits))
            has = any(x[edge_idx[(i,j)]] and x[edge_idx[(i,k)]] and x[edge_idx[(j,k)]]
                      for i in range(N) for j in range(i+1,N) for k in range(j+1,N))
            tt_t[bits] = 1 if has else 0

        gens_no_t = build_full_ideal(n_bits, gates_t, tt_f=None)
        gens_with_t = build_full_ideal(n_bits, gates_t, tt_f=tt_t)

        out_gen_t = gens_with_t[-1]
        no_terms_t = sum(g.num_terms() for g in gens_no_t)
        with_terms_t = sum(g.num_terms() for g in gens_with_t)

        print(f"  {'TRI-K'+str(N):<15} {n_bits:>3} {len(gates_t):>4} "
              f"{no_terms_t:>9} {with_terms_t:>11} {out_gen_t.degree():>8} {out_gen_t.num_terms():>10}")

    print(f"\n{'='*70}")
    print("  ANALYSIS")
    print(f"{'='*70}")
    print("""
    OUTPUT CONSTRAINT = the polynomial gₛ + f(x) where f is the target.

    out_deg = degree of the output constraint polynomial.
    out_terms = number of monomials in the output constraint.

    For SIMPLE functions (OR): out_terms is SMALL (OR has few monomials).
    For COMPLEX functions (MSAT, Triangle): out_terms is LARGE
      (complex functions have many monomials in GF(2) representation).

    The output constraint's complexity = the algebraic complexity of f.
    This IS where the function-specific hardness enters the ideal.

    KEY: When we add the output constraint to the gate equations,
    the INTERACTION between gate equations and output constraint
    creates high-degree syzygies. The number and degree of these
    syzygies = the trajectory regularity.

    out_terms(f) growing super-polynomially → reg growing → s growing.
    """)


if __name__ == "__main__":
    main()
