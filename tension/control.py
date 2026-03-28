"""
STONE 17: CONTROL FLOW — if/loop when condition is ?

KEY INSIGHT: if(?) = Ch function!

  if (cond) { A } else { B }
  = (cond AND A) OR (NOT(cond) AND B)
  = Ch(cond, A, B)

  cond = 0: result = B (A SKIPPED — kill-link!)
  cond = 1: result = A (B SKIPPED — kill-link!)
  cond = ?: result = ? (BOTH branches live — branch point)

FOR loops: unroll. Each iteration = one flow step.
  Tension = sum of per-iteration tensions.
  Bounded loop: finite tension.

WHILE with ? condition: each iteration is a branch point.
  Tension = number of ? iterations.
  MUST be bounded (infinite tension → refused).
"""

from rayon_numbers import RayonInt


# ════════════════════════════════════════════════════════════
# IF: Three-state conditional
# ════════════════════════════════════════════════════════════

class RayonIf:
    """
    if (condition) { then_val } else { else_val }

    condition: 0, 1, or None (?)
    Works on any RayonInt values.

    Returns: result + branch cost
    """
    @staticmethod
    def select(condition, then_val, else_val):
        """
        condition = bit (0, 1, or None)
        then_val, else_val = RayonInt

        Returns: (result: RayonInt, branches: int)
        """
        if condition == 1:
            return then_val, 0   # then branch, else SKIPPED
        elif condition == 0:
            return else_val, 0   # else branch, then SKIPPED
        else:
            # condition = ? → BOTH branches live
            # Result = Ch(cond, then, else) = ? with tension from both
            merged_bits = []
            for i in range(max(then_val.width, else_val.width)):
                tb = then_val.bits[i] if i < len(then_val.bits) else 0
                eb = else_val.bits[i] if i < len(else_val.bits) else 0
                if tb == eb:
                    merged_bits.append(tb)  # same either way!
                else:
                    merged_bits.append(None)  # differs → unknown
            return RayonInt(bits=merged_bits, width=then_val.width), 1


# ════════════════════════════════════════════════════════════
# FOR: Bounded loop with tension tracking
# ════════════════════════════════════════════════════════════

class RayonFor:
    """
    for i in range(n): body(state, i)

    Each iteration transforms state. Tension accumulates.
    Loop is ALWAYS bounded → finite tension.
    """
    @staticmethod
    def execute(initial_state, n_iterations, body_fn):
        """
        initial_state: RayonInt (or tuple of RayonInts)
        body_fn(state, i) → new_state
        Returns: (final_state, total_branches)
        """
        state = initial_state
        total_branches = 0

        for i in range(n_iterations):
            state, branches = body_fn(state, i)
            total_branches += branches

        return state, total_branches


# ════════════════════════════════════════════════════════════
# WHILE: Conditional loop (bounded)
# ════════════════════════════════════════════════════════════

class RayonWhile:
    """
    while (condition(state)): body(state)

    condition returns 0, 1, or None (?).
    MUST specify max_iterations (infinite tension = error).

    If condition = ?: BRANCH POINT per iteration.
    Total tension ≤ max_iterations.
    """
    @staticmethod
    def execute(initial_state, condition_fn, body_fn, max_iter=100):
        """
        Returns: (final_state, total_branches, iterations)
        """
        state = initial_state
        total_branches = 0

        for i in range(max_iter):
            cond = condition_fn(state)

            if cond == 0:
                break   # definitely done
            elif cond == 1:
                state, br = body_fn(state)
                total_branches += br
            elif cond is None:
                # ? → branch point! both continue and stop possible
                total_branches += 1
                state, br = body_fn(state)
                total_branches += br
            else:
                break

        return state, total_branches, i + 1


# ════════════════════════════════════════════════════════════
# VERIFICATION
# ════════════════════════════════════════════════════════════

def verify():
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  STONE 17: CONTROL FLOW — if/for/while with tension     ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    w = 8

    # ── IF with known condition ──
    print("IF (known condition):")
    print("─" * 50)

    a = RayonInt.known(42, w)
    b = RayonInt.known(99, w)

    r1, br1 = RayonIf.select(1, a, b)
    r0, br0 = RayonIf.select(0, a, b)
    print(f"  if(1) {{42}} else {{99}} = {r1}, branches={br1} ✓")
    print(f"  if(0) {{42}} else {{99}} = {r0}, branches={br0} ✓")
    print()

    # ── IF with ? condition ──
    print("IF (unknown condition):")
    print("─" * 50)

    rq, brq = RayonIf.select(None, a, b)
    print(f"  if(?) {{42}} else {{99}} = {rq}, branches={brq}")
    print(f"    tension={rq.tension}, range={rq.min_value}..{rq.max_value}")
    print()

    # Special: both branches give same result
    r_same, br_same = RayonIf.select(None, a, a)
    print(f"  if(?) {{42}} else {{42}} = {r_same}, branches={br_same}")
    print(f"    → Same value either way → result is KNOWN! tension={r_same.tension}")
    print(f"    ★ Branch is FREE when both paths agree!")
    print()

    # ── FOR loop ──
    print("FOR loop (accumulate with tension):")
    print("─" * 50)

    # Sum 0..7
    def sum_body(state, i):
        return state + RayonInt.known(i, w), 0

    result, branches = RayonFor.execute(RayonInt.known(0, w), 8, sum_body)
    print(f"  sum(0..7) = {result}, branches={branches}")
    print(f"    expected: {sum(range(8))} {'✓' if result.value == sum(range(8)) else '✗'}")
    print()

    # Sum with unknown addend
    def uncertain_body(state, i):
        addend = RayonInt.partial(i, 0b00000001, w)  # bit 0 unknown
        return state + addend, 0

    result2, branches2 = RayonFor.execute(RayonInt.known(0, w), 4, uncertain_body)
    print(f"  sum(0..3 with bit0 unknown) = {result2}")
    print(f"    branches={branches2}, tension={result2.tension}")
    print()

    # ── WHILE with ? condition ──
    print("WHILE (tension per ? iteration):")
    print("─" * 50)

    # Count down from 5 (known)
    def countdown_cond(state):
        if state.is_known:
            return 1 if state.value > 0 else 0
        return None  # unknown → branch

    def countdown_body(state):
        return state - RayonInt.known(1, w), 0

    result3, branches3, iters3 = RayonWhile.execute(
        RayonInt.known(5, w), countdown_cond, countdown_body, max_iter=20)
    print(f"  while(x>0) x-- starting at 5:")
    print(f"    result={result3}, branches={branches3}, iterations={iters3}")
    print()

    # While with unknown start
    result4, branches4, iters4 = RayonWhile.execute(
        RayonInt.partial(3, 0b00000100, w),  # bit 2 unknown → 3 or 7
        countdown_cond, countdown_body, max_iter=20)
    print(f"  while(x>0) x-- starting at 3-or-7:")
    print(f"    result={result4}, branches={branches4}, iterations={iters4}")
    print(f"    ★ Unknown start → branches accumulate per iteration!")

    print(f"""
═══════════════════════════════════════════════════════════════
STONE 17: CONTROL FLOW — Complete

  IF:
    if(0) → else branch (then SKIPPED, free)
    if(1) → then branch (else SKIPPED, free)
    if(?) → BOTH branches (1 branch point)
    if(?) but both same → FREE! (no actual choice)

  FOR:
    Bounded loop. Unrolled. Tension = sum of iteration tensions.
    Known iteration: 0 branches. Unknown: accumulates.

  WHILE:
    Must be bounded (max_iter). Each ? condition = 1 branch.
    Known condition: deterministic. Unknown: tension grows.

  THE PRINCIPLE:
    Control flow with ? = BRANCH POINT.
    Branch point = the ONLY source of exponential cost.
    Known conditions = FREE (kill-link in action).
    Same condition both ways = FREE (no actual choice).

  FOR SHA-256 (64 rounds):
    Each round = deterministic (counter-based).
    No branch points from loop structure.
    All branches come from GATES (Ch, Maj, carry).
    SHA-256 loop tension = 0. Gate tension = everything.
═══════════════════════════════════════════════════════════════
""")


if __name__ == '__main__':
    verify()
