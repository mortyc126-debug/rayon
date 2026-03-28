"""
STONE 22: COST MODEL — Formal cost semantics for Rayon.

Every Rayon computation has an EXACT cost, countable in bit-operations:

  - n_looks:    number of bit observations (reading a bit value)
  - n_skips:    number of bits skipped via kill-links (AND with known 0, OR with known 1)
  - n_branches: number of AND(?,?) branch points (both inputs unknown)
  - n_linear:   number of XOR operations (free in GF(2), linear)

Total cost = 2^n_branches * poly(n_linear)

The key insight: XOR is FREE (linear algebra), AND BRANCHES (exponential).
But AND with a known 0 KILLS — it doesn't branch, it skips.
So the cost depends not on circuit size but on TENSION topology.
"""

import functools
import time
from rayon_numbers import RayonInt


# ════════════════════════════════════════════════════════════
# 1. CostTracker — counts exact costs of bit operations
# ════════════════════════════════════════════════════════════

class CostTracker:
    """
    Wraps RayonInt computations and counts exact operation costs.

    Usage:
        tracker = CostTracker()
        result = tracker.xor(a, b)
        result = tracker.and_op(a, b)
        print(tracker.report())
    """

    def __init__(self):
        self.n_looks = 0      # bit observations
        self.n_skips = 0      # bits killed (AND w/ 0, OR w/ 1)
        self.n_branches = 0   # AND(?,?) branch points
        self.n_linear = 0     # XOR operations (free)
        self._log = []        # operation log

    def reset(self):
        self.n_looks = 0
        self.n_skips = 0
        self.n_branches = 0
        self.n_linear = 0
        self._log = []

    # ── Primitive bit operations with cost tracking ──

    def look(self, bit):
        """Observe a single bit. Cost: 1 look."""
        self.n_looks += 1
        return bit

    def xor_bits(self, a, b):
        """XOR two bits. Cost: 1 linear op (free)."""
        self.n_linear += 1
        self.n_looks += 2
        if a is None or b is None:
            return None
        return a ^ b

    def and_bits(self, a, b):
        """
        AND two bits. Cost depends on values:
          - known 0 in either: SKIP (kill-link), cost = 0
          - both known: 1 look each
          - both unknown: BRANCH, cost = exponential contribution
        """
        self.n_looks += 2
        if a == 0 or b == 0:
            self.n_skips += 1
            self._log.append("SKIP(AND kill)")
            return 0
        if a is None and b is None:
            self.n_branches += 1
            self._log.append("BRANCH(AND ?,?)")
            return None
        if a is None or b is None:
            # One known (must be 1), one unknown: result unknown but no branch
            self._log.append("AND(1,?)")
            return None
        return a & b

    def or_bits(self, a, b):
        """
        OR two bits. Cost depends on values:
          - known 1 in either: SKIP (kill-link), cost = 0
          - both unknown: BRANCH
        """
        self.n_looks += 2
        if a == 1 or b == 1:
            self.n_skips += 1
            self._log.append("SKIP(OR kill)")
            return 1
        if a is None and b is None:
            self.n_branches += 1
            self._log.append("BRANCH(OR ?,?)")
            return None
        if a is None or b is None:
            self._log.append("OR(0,?)")
            return None
        return a | b

    # ── Word-level operations (operate on RayonInt) ──

    def xor(self, a, b):
        """Bitwise XOR of two RayonInts. Linear — free."""
        width = max(a.width, b.width)
        bits = []
        for i in range(width):
            ab = a.bits[i] if i < len(a.bits) else 0
            bb = b.bits[i] if i < len(b.bits) else 0
            bits.append(self.xor_bits(ab, bb))
        self._log.append(f"XOR({width}b)")
        return RayonInt(bits=bits, width=width)

    def and_op(self, a, b):
        """Bitwise AND of two RayonInts. Counts kills and branches."""
        width = max(a.width, b.width)
        bits = []
        for i in range(width):
            ab = a.bits[i] if i < len(a.bits) else 0
            bb = b.bits[i] if i < len(b.bits) else 0
            bits.append(self.and_bits(ab, bb))
        self._log.append(f"AND({width}b)")
        return RayonInt(bits=bits, width=width)

    def or_op(self, a, b):
        """Bitwise OR of two RayonInts. Counts kills and branches."""
        width = max(a.width, b.width)
        bits = []
        for i in range(width):
            ab = a.bits[i] if i < len(a.bits) else 0
            bb = b.bits[i] if i < len(b.bits) else 0
            bits.append(self.or_bits(ab, bb))
        self._log.append(f"OR({width}b)")
        return RayonInt(bits=bits, width=width)

    def add(self, a, b):
        """
        Addition with carry-chain cost tracking.
        Carry = AND + OR of partial results, so branches may accumulate.
        """
        width = max(a.width, b.width)
        result_bits = []
        carry = 0

        for i in range(width):
            ab = a.bits[i] if i < len(a.bits) else 0
            bb = b.bits[i] if i < len(b.bits) else 0

            self.n_looks += 2  # observe a, b

            if ab is None or bb is None or carry is None:
                # Sum bit = a XOR b XOR carry
                self.n_linear += 1
                result_bits.append(None)

                # Carry logic with cost tracking
                if ab == 0 and bb == 0:
                    self.n_skips += 1  # AND(0,0) = 0, carry killed
                    carry = 0
                elif ab == 1 and bb == 1:
                    carry = 1  # guaranteed carry
                    self.n_looks += 1
                elif carry == 0 and (ab == 0 or bb == 0):
                    self.n_skips += 1  # carry stays 0
                    carry = 0
                else:
                    self.n_branches += 1  # unknown carry propagation
                    carry = None
            else:
                s = ab + bb + carry
                result_bits.append(s & 1)
                carry = s >> 1
                self.n_linear += 1

        self._log.append(f"ADD({width}b)")
        return RayonInt(bits=result_bits[:width], width=width)

    # ── Cost computation ──

    @property
    def total_cost(self):
        """
        Total cost = 2^n_branches * poly(n_linear).
        poly(n) = max(1, n) — linear operations are O(n) but free in GF(2).
        """
        poly = max(1, self.n_linear)
        return (2 ** self.n_branches) * poly

    def report(self):
        """Human-readable cost report."""
        lines = [
            f"  n_looks    = {self.n_looks}",
            f"  n_skips    = {self.n_skips}",
            f"  n_branches = {self.n_branches}",
            f"  n_linear   = {self.n_linear}",
            f"  total_cost = 2^{self.n_branches} * poly({self.n_linear}) = {self.total_cost}",
        ]
        return "\n".join(lines)


# ════════════════════════════════════════════════════════════
# 2. CostAnnotation — decorator for auto-tracking
# ════════════════════════════════════════════════════════════

# Thread-local-ish tracker stack for nested tracking
_tracker_stack = []


def get_current_tracker():
    """Get the active CostTracker, or None."""
    return _tracker_stack[-1] if _tracker_stack else None


def cost_tracked(func):
    """
    Decorator that auto-tracks the cost of a function.

    The decorated function receives a CostTracker as its first argument
    (after self, if it's a method). The tracker is available as
    func.last_tracker after the call.

    Usage:
        @cost_tracked
        def my_xor_chain(tracker, a, b, c):
            r = tracker.xor(a, b)
            return tracker.xor(r, c)

        result = my_xor_chain(a, b, c)
        print(my_xor_chain.last_tracker.report())
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        tracker = CostTracker()
        _tracker_stack.append(tracker)
        try:
            result = func(tracker, *args, **kwargs)
        finally:
            _tracker_stack.pop()
        wrapper.last_tracker = tracker
        return result

    wrapper.last_tracker = None
    return wrapper


# ════════════════════════════════════════════════════════════
# 3. CostCompare — compare two approaches
# ════════════════════════════════════════════════════════════

class CostCompare:
    """
    Compare two approaches to the same problem.
    Run both, report which has lower cost.
    """

    @staticmethod
    def compare(name_a, func_a, name_b, func_b, *args, **kwargs):
        """
        Run func_a and func_b with the same args.
        Both must be @cost_tracked or accept a CostTracker as first arg.

        Returns (result_a, tracker_a, result_b, tracker_b, winner).
        """
        # Run approach A
        tracker_a = CostTracker()
        _tracker_stack.append(tracker_a)
        try:
            result_a = func_a(tracker_a, *args, **kwargs)
        finally:
            _tracker_stack.pop()

        # Run approach B
        tracker_b = CostTracker()
        _tracker_stack.append(tracker_b)
        try:
            result_b = func_b(tracker_b, *args, **kwargs)
        finally:
            _tracker_stack.pop()

        cost_a = tracker_a.total_cost
        cost_b = tracker_b.total_cost

        if cost_a < cost_b:
            winner = name_a
        elif cost_b < cost_a:
            winner = name_b
        else:
            winner = "TIE"

        # Print report
        print(f"  [{name_a}]")
        print(tracker_a.report())
        print(f"  [{name_b}]")
        print(tracker_b.report())
        print(f"  Winner: {winner} (cost {min(cost_a, cost_b)} vs {max(cost_a, cost_b)})")

        return result_a, tracker_a, result_b, tracker_b, winner


# ════════════════════════════════════════════════════════════
# VERIFICATION
# ════════════════════════════════════════════════════════════

def verify():
    W = 8  # 8-bit width for tests

    print("+" + "=" * 59 + "+")
    print("|  STONE 22: COST MODEL - Formal cost semantics              |")
    print("+" + "=" * 59 + "+")
    print()

    # ── Test 1: XOR chain has zero branches, O(n) cost ──
    print("TEST 1: XOR chain — n_branches=0, cost=O(n)")
    print("-" * 50)

    a = RayonInt.known(0b10101010, W)
    b = RayonInt.known(0b01010101, W)
    c = RayonInt.known(0b11110000, W)
    d = RayonInt.known(0b00001111, W)

    tracker = CostTracker()
    r = tracker.xor(a, b)
    r = tracker.xor(r, c)
    r = tracker.xor(r, d)

    ok = tracker.n_branches == 0
    print(f"  4-way XOR chain:")
    print(tracker.report())
    print(f"  n_branches == 0: {tracker.n_branches} {'[PASS]' if ok else '[FAIL]'}")

    # Cost should be linear in n_linear
    linear_ok = tracker.total_cost == max(1, tracker.n_linear)
    print(f"  total_cost == poly(n_linear): {tracker.total_cost} == {max(1, tracker.n_linear)} {'[PASS]' if linear_ok else '[FAIL]'}")
    t1 = ok and linear_ok
    print(f"  XOR chain cost=O(n): {'✓' if t1 else '✗'}")
    print()

    # ── Test 2: AND chain with known 0 — all kills ──
    print("TEST 2: AND chain with known 0 — n_skips=n-1, cost=O(1)")
    print("-" * 50)

    zero = RayonInt.known(0, W)  # all zero bits
    u1 = RayonInt.unknown(W)
    u2 = RayonInt.unknown(W)
    u3 = RayonInt.unknown(W)

    tracker = CostTracker()
    r = tracker.and_op(zero, u1)  # 0 AND ? = 0 for every bit: 8 kills
    r = tracker.and_op(r, u2)     # result is all 0, so again 8 kills
    r = tracker.and_op(r, u3)     # same

    # After AND with 0, result is all 0 — every subsequent AND also kills
    skips_ok = tracker.n_skips >= W * 3  # at least 8 skips per AND, 3 ANDs
    branches_ok = tracker.n_branches == 0
    result_ok = r.is_known and r.value == 0

    print(f"  0 AND ? AND ? AND ? (chain of 3 ANDs):")
    print(tracker.report())
    print(f"  Result is known 0: {r.value} {'[PASS]' if result_ok else '[FAIL]'}")
    print(f"  n_skips >= {W * 3}: {tracker.n_skips} {'[PASS]' if skips_ok else '[FAIL]'}")
    print(f"  n_branches == 0: {tracker.n_branches} {'[PASS]' if branches_ok else '[FAIL]'}")
    t2 = skips_ok and branches_ok and result_ok
    print(f"  AND chain with 0 cost=O(1): {'✓' if t2 else '✗'}")
    print()

    # ── Test 3: Mixed circuit — count branches vs skips accurately ──
    print("TEST 3: Mixed circuit — accurate branch/skip counting")
    print("-" * 50)

    # Mix: some bits known, some unknown
    # a = 1010???? — top 4 known, bottom 4 unknown
    a = RayonInt.partial(0b10100000, 0b00001111, W)
    # b = ????1010 — top 4 unknown, bottom 4 known
    b = RayonInt.partial(0b00001010, 0b11110000, W)

    tracker = CostTracker()
    r_and = tracker.and_op(a, b)

    # Bit-by-bit analysis for AND(a, b):
    # bit 0: a=? b=0 -> SKIP    bit 4: a=0 b=? -> SKIP
    # bit 1: a=? b=1 -> ?       bit 5: a=0 b=? -> SKIP
    # bit 2: a=? b=0 -> SKIP    bit 6: a=1 b=? -> ?
    # bit 3: a=? b=1 -> ?       bit 7: a=1 b=? -> ?
    # Skips: bits 0,2,4,5 = 4 skips
    # Non-branching unknowns: bits 1,3,6,7 (AND(1,?) or AND(?,1)) = 0 branches
    expected_skips = 4
    expected_branches = 0

    skips_match = tracker.n_skips == expected_skips
    branches_match = tracker.n_branches == expected_branches

    print(f"  AND(1010????, ????1010):")
    print(tracker.report())
    print(f"  n_skips == {expected_skips}: {tracker.n_skips} {'[PASS]' if skips_match else '[FAIL]'}")
    print(f"  n_branches == {expected_branches}: {tracker.n_branches} {'[PASS]' if branches_match else '[FAIL]'}")

    # Now AND two fully unknown values — every bit is a branch
    u1 = RayonInt.unknown(W)
    u2 = RayonInt.unknown(W)
    tracker2 = CostTracker()
    r_and2 = tracker2.and_op(u1, u2)

    all_branch = tracker2.n_branches == W
    print(f"  AND(????????, ????????):")
    print(tracker2.report())
    print(f"  n_branches == {W}: {tracker2.n_branches} {'[PASS]' if all_branch else '[FAIL]'}")

    t3 = skips_match and branches_match and all_branch
    print(f"  Mixed circuit counting: {'✓' if t3 else '✗'}")
    print()

    # ── Test 4: CostAnnotation decorator ──
    print("TEST 4: @cost_tracked decorator")
    print("-" * 50)

    @cost_tracked
    def xor_chain(tracker, a, b, c):
        r = tracker.xor(a, b)
        return tracker.xor(r, c)

    a = RayonInt.known(0xAA, W)
    b = RayonInt.known(0x55, W)
    c = RayonInt.known(0x0F, W)
    result = xor_chain(a, b, c)

    has_tracker = xor_chain.last_tracker is not None
    correct_linear = xor_chain.last_tracker.n_linear == W * 2  # 2 XORs of 8 bits
    correct_result = result.is_known and result.value == (0xAA ^ 0x55 ^ 0x0F)

    print(f"  @cost_tracked xor_chain(0xAA, 0x55, 0x0F):")
    print(f"  Result: {result.value} (expected {0xAA ^ 0x55 ^ 0x0F}) {'[PASS]' if correct_result else '[FAIL]'}")
    print(f"  Tracker attached: {'[PASS]' if has_tracker else '[FAIL]'}")
    print(xor_chain.last_tracker.report())
    print(f"  n_linear == {W * 2}: {xor_chain.last_tracker.n_linear} {'[PASS]' if correct_linear else '[FAIL]'}")
    t4 = has_tracker and correct_linear and correct_result
    print(f"  @cost_tracked decorator: {'✓' if t4 else '✗'}")
    print()

    # ── Test 5: CostCompare — brute force vs backward propagation for ADD inversion ──
    print("TEST 5: CostCompare — brute force vs backward propagation")
    print("-" * 50)
    print("  Problem: find x such that x + 37 = 100 (mod 256), x is 8-bit")
    print()

    target_sum = 100
    known_b = 37

    def brute_force_add_invert(tracker, target, b_val, width):
        """Try all 2^width values, AND-check each one."""
        b = RayonInt.known(b_val, width)
        target_r = RayonInt.known(target, width)
        found = None
        for candidate in range(2 ** width):
            x = RayonInt.known(candidate, width)
            s = tracker.add(x, b)
            # Compare: XOR with target, check if zero
            diff = tracker.xor(s, target_r)
            # Each comparison costs looks
            tracker.n_looks += width  # checking each bit
            if diff.is_known and diff.value == 0:
                found = x
                break
        return found

    def backward_propagation(tracker, target, b_val, width):
        """
        Algebraic: x = target - b. Single subtraction.
        In Rayon: backward propagation through add.
        """
        t = RayonInt.known(target, width)
        b = RayonInt.known(b_val, width)
        # x = target - b = target + (~b + 1)
        # Complement b
        comp_bits = [(1 - bit) for bit in b.bits]
        comp = RayonInt(bits=comp_bits, width=width)
        one = RayonInt.known(1, width)
        neg_b = tracker.add(comp, one)
        result = tracker.add(t, neg_b)
        return result

    _, tr_brute, _, tr_back, winner = CostCompare.compare(
        "brute_force", brute_force_add_invert,
        "backward_prop", backward_propagation,
        target_sum, known_b, W
    )

    backward_wins = winner == "backward_prop"
    cost_ratio = tr_brute.total_cost / max(1, tr_back.total_cost)
    print(f"  Cost ratio (brute/backward): {cost_ratio:.1f}x")
    print(f"  Backward propagation wins: {'[PASS]' if backward_wins else '[FAIL]'}")
    t5 = backward_wins
    print(f"  CostCompare brute vs backward: {'✓' if t5 else '✗'}")
    print()

    # ── Test 6: Addition with partial knowledge — carry kills reduce cost ──
    print("TEST 6: Carry-kill cost reduction in addition")
    print("-" * 50)

    def add_no_kills(tracker, width):
        """Add two fully unknown values — maximum carry uncertainty."""
        a = RayonInt.unknown(width)
        b = RayonInt.unknown(width)
        return tracker.add(a, b)

    def add_with_kills(tracker, width):
        """Add values with low bits known 0 — carry killed early."""
        # a = ????0000, b = ????0000
        a = RayonInt.partial(0, 0b11110000, width)
        b = RayonInt.partial(0, 0b11110000, width)
        return tracker.add(a, b)

    _, tr_no, _, tr_with, winner = CostCompare.compare(
        "no_kills", add_no_kills,
        "with_kills", add_with_kills,
        W
    )

    kills_cheaper = tr_with.total_cost < tr_no.total_cost
    print(f"  Carry-kills make it cheaper: {'[PASS]' if kills_cheaper else '[FAIL]'}")
    t6 = kills_cheaper
    print(f"  Carry-kill cost reduction: {'✓' if t6 else '✗'}")
    print()

    # ── Summary ──
    all_pass = all([t1, t2, t3, t4, t5, t6])
    print("=" * 60)
    print(f"STONE 22: COST MODEL")
    print(f"  Test 1 — XOR chain O(n):              {'✓' if t1 else '✗'}")
    print(f"  Test 2 — AND chain with 0 O(1):       {'✓' if t2 else '✗'}")
    print(f"  Test 3 — Mixed circuit counting:       {'✓' if t3 else '✗'}")
    print(f"  Test 4 — @cost_tracked decorator:      {'✓' if t4 else '✗'}")
    print(f"  Test 5 — Brute vs backward compare:    {'✓' if t5 else '✗'}")
    print(f"  Test 6 — Carry-kill cost reduction:    {'✓' if t6 else '✗'}")
    print()
    print(f"  FORMAL COST SEMANTICS:")
    print(f"    cost = 2^n_branches * poly(n_linear)")
    print(f"    XOR is FREE (linear, no branching)")
    print(f"    AND(0,?) is FREE (kill-link, skip)")
    print(f"    AND(?,?) is EXPENSIVE (branch, exponential)")
    print(f"    The cost of a computation = its TENSION TOPOLOGY")
    print()
    if all_pass:
        print(f"  ALL TESTS PASSED")
    else:
        print(f"  SOME TESTS FAILED")
    print("=" * 60)


if __name__ == "__main__":
    verify()
