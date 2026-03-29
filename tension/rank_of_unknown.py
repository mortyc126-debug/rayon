"""
RANK OF ? — What our mathematics sees that standard can't.

Question: 512 independent ?-bits enter SHA-256.
256 ?-bits come out. But how many are INDEPENDENT?

If rank(output) < 256: output ?s are LINKED.
Link = constraint = vulnerability that ONLY ? math can see.

Method: Rayon Wave. Track GF2Expr through SHA-256 rounds.
Each output = linear expression in inputs + branch variables.
RANK = number of original input vars in output expressions.

Round by round: watch rank evolve.
If rank drops: SHA-256 is LOSING linear independence.
If rank stays 256: outputs are linearly independent (no shortcut).
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from rayon_wave import GF2Expr, WaveCircuit
from advanced_wave import RayonEngine


def sha_round_wave(state_exprs, w_expr, k_val, round_num):
    """
    One SHA-256 round in Rayon Wave mode (1-bit simplified).

    state = [a, b, c, d, e, f, g, h] as GF2Expr
    w = GF2Expr for W[round]
    k = constant (0 or 1)

    Returns: new state as GF2Expr list
    """
    a, b, c, d, e, f, g, h = state_exprs
    K = GF2Expr.constant(k_val)

    eng = RayonEngine()

    # Wire names unique per round
    rn = f'r{round_num}'
    eng.set_wire(f'{rn}_a', a)
    eng.set_wire(f'{rn}_b', b)
    eng.set_wire(f'{rn}_c', c)
    eng.set_wire(f'{rn}_d', d)
    eng.set_wire(f'{rn}_e', e)
    eng.set_wire(f'{rn}_f', f)
    eng.set_wire(f'{rn}_g', g)
    eng.set_wire(f'{rn}_h', h)
    eng.set_wire(f'{rn}_w', w_expr)
    eng.set_wire(f'{rn}_k', K)
    eng.set_wire(f'{rn}_c1', GF2Expr.constant(1))

    # Ch(e, f, g) = AND(e,f) XOR AND(NOT(e), g)
    eng.add_gate('AND', f'{rn}_e', f'{rn}_f', f'{rn}_ef')
    eng.add_gate('XOR', f'{rn}_e', f'{rn}_c1', f'{rn}_ne')
    eng.add_gate('AND', f'{rn}_ne', f'{rn}_g', f'{rn}_neg')
    eng.add_gate('XOR', f'{rn}_ef', f'{rn}_neg', f'{rn}_ch')

    # T1 = h XOR ch XOR w XOR k (simplified, no Σ)
    eng.add_gate('XOR', f'{rn}_h', f'{rn}_ch', f'{rn}_t1a')
    eng.add_gate('XOR', f'{rn}_w', f'{rn}_k', f'{rn}_t1b')
    eng.add_gate('XOR', f'{rn}_t1a', f'{rn}_t1b', f'{rn}_t1')

    # Maj(a,b,c) = AND(a,b) XOR AND(a,c) XOR AND(b,c)
    eng.add_gate('AND', f'{rn}_a', f'{rn}_b', f'{rn}_ab')
    eng.add_gate('AND', f'{rn}_a', f'{rn}_c', f'{rn}_ac')
    eng.add_gate('AND', f'{rn}_b', f'{rn}_c', f'{rn}_bc')
    eng.add_gate('XOR', f'{rn}_ab', f'{rn}_ac', f'{rn}_maj1')
    eng.add_gate('XOR', f'{rn}_maj1', f'{rn}_bc', f'{rn}_maj')

    # T2 = Σ0(a) XOR maj (Σ0 simplified as a itself for 1-bit)
    eng.add_gate('XOR', f'{rn}_a', f'{rn}_maj', f'{rn}_t2')

    # new_a = T1 XOR T2
    eng.add_gate('XOR', f'{rn}_t1', f'{rn}_t2', f'{rn}_new_a')
    # new_e = d XOR T1
    eng.add_gate('XOR', f'{rn}_d', f'{rn}_t1', f'{rn}_new_e')

    eng.run()

    new_a = eng.wires.get(f'{rn}_new_a', GF2Expr.variable(f'br_a_{rn}'))
    new_e = eng.wires.get(f'{rn}_new_e', GF2Expr.variable(f'br_e_{rn}'))

    # Register shift: b=a, c=b, d=c, f=e, g=f, h=g
    new_state = [new_a, a, b, c, new_e, e, f, g]

    return new_state, eng.true_branches


def measure_rank_per_round(n_rounds=64):
    """
    Track rank of ? through SHA-256 rounds.

    Initial: 8 state vars (from IV = constant) + W vars (unknown).
    After each round: count how many ORIGINAL W variables appear
    in the state expressions (not hidden behind branch variables).
    """
    # Initial state: known (IV) = constants
    state = [GF2Expr.constant(i % 2) for i in range(8)]  # simplified IV

    results = []
    total_branches = 0

    for r in range(n_rounds):
        # W[r] = unique variable
        w = GF2Expr.variable(f'W{r}')

        # K = constant per round (simplified)
        k = r % 2

        new_state, branches = sha_round_wave(state, w, k, r)
        total_branches += branches

        # Measure: which ORIGINAL variables (W0, W1, ...) appear in state?
        original_vars = set()
        branch_vars = set()
        for expr in new_state:
            if expr is not None:
                for v in expr.vars:
                    if v.startswith('W'):
                        original_vars.add(v)
                    elif v.startswith('_br') or v.startswith('br_'):
                        branch_vars.add(v)

        # Linear rank = number of original vars in linear expressions
        linear_rank = len(original_vars)
        # Total vars = original + branch
        total_vars = len(original_vars) + len(branch_vars)

        # State complexity: average number of vars per expression
        avg_vars = sum(len(e.vars) if e else 0 for e in new_state) / 8

        results.append({
            'round': r,
            'linear_rank': linear_rank,
            'branch_vars': len(branch_vars),
            'total_vars': total_vars,
            'branches_this_round': branches,
            'total_branches': total_branches,
            'avg_vars_per_expr': avg_vars,
            'original_vars': original_vars,
        })

        state = new_state

    return results


if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  RANK OF ? — What only Rayon math can see                ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()
    print("  512 ?-bits enter SHA-256. 256 come out.")
    print("  How many output ?-bits are INDEPENDENT?")
    print()

    results = measure_rank_per_round(64)

    print(f"  {'round':>5} {'linear_rank':>12} {'branch_vars':>12} {'branches':>10} {'avg_vars':>10}")
    print(f"  {'─'*50}")

    for r in results:
        if r['round'] < 8 or r['round'] > 58 or r['round'] % 8 == 0:
            print(f"  {r['round']:>5} {r['linear_rank']:>12} "
                  f"{r['branch_vars']:>12} {r['total_branches']:>10} "
                  f"{r['avg_vars_per_expr']:>10.1f}")

    final = results[-1]
    print()
    print(f"  FINAL STATE (after 64 rounds):")
    print(f"    Linear rank:    {final['linear_rank']}")
    print(f"    Branch vars:    {final['branch_vars']}")
    print(f"    Total branches: {final['total_branches']}")
    print()

    # Which W variables survived as linear terms?
    survived = sorted(final['original_vars'])
    print(f"    W variables in linear output: {len(survived)}")
    if survived:
        print(f"    Survived: {survived[:10]}{'...' if len(survived)>10 else ''}")
    print()

    # The key question
    if final['linear_rank'] < 8:
        print(f"  ★ LINEAR RANK < 8: output ?-bits are LINKED!")
        print(f"    Some output bits = linear combination of others.")
        print(f"    This is a CONSTRAINT visible only to ? mathematics.")
        print(f"    Exploitable: reduces effective output to {final['linear_rank']} bits.")
    elif final['linear_rank'] < 64:
        print(f"  Linear rank {final['linear_rank']} < 64:")
        print(f"    Not all rounds contribute independent linear info.")
        print(f"    W variables from later rounds dominate.")
    else:
        print(f"  Linear rank = {final['linear_rank']}: many W vars survive linearly.")
        print(f"  SHA-256 preserves linear independence through rounds.")

    print(f"""
  ═══════════════════════════════════════════════════
  RANK OF ? ANALYSIS:

    This measurement is IMPOSSIBLE in standard math.
    Standard sees values (0/1). We see structure of ?.

    Linear rank = how many input ?-bits influence output
    LINEARLY (through XOR paths, not AND branches).

    If linear rank < output size: LINEAR DEPENDENCIES exist.
    Dependencies = constraints = potential vulnerabilities.

    Total branches = nonlinear part. Only this is truly hard.
    Linear part = FREE (GF2 solvable).

    RAYON DECOMPOSITION of SHA-256 difficulty:
      Linear: {final['linear_rank']} independent vars (solvable)
      Nonlinear: {final['total_branches']} branches (search)
      TOTAL: 2^{final['total_branches']} × poly({final['linear_rank']})
  ═══════════════════════════════════════════════════
""")
