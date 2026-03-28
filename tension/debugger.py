"""
DEBUGGER -- Visual tension flow debugger for Rayon.

Four tools for understanding how tension moves through computation:

  TensionDebugger:  step through operations, show tension before/after
  TensionHeatmap:   visual bar display of tension across an array
  BranchTracer:     find and count AND(?,?) branch points
  FlowVisualizer:   show data flow pipeline with tension coloring
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from rayon_numbers import RayonInt
from arithmetic import (
    rotr, shr, shl, sigma0, sigma1, Sigma0, Sigma1, Ch, Maj, mod_add,
)
from memory import RayonVar, RayonArray


# ════════════════════════════════════════════════════════════
# ANSI colors (print-based, no GUI)
# ════════════════════════════════════════════════════════════

GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
DIM    = "\033[2m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def _bit_bar(ri, width=None):
    """Render a bit-level bar: filled = unknown, dot = known."""
    w = width or ri.width
    chars = []
    for i in range(w):
        b = ri.bits[i] if i < len(ri.bits) else 0
        if b is None:
            chars.append("\u2588")  # full block
        else:
            chars.append("\u00b7")  # middle dot
    # display MSB on the left
    return "".join(reversed(chars))


def _skip_map(before, after):
    """
    Build a skip map: for each bit position, show what happened.
      K = killed (was ?, now known)
      B = branched (was known, now ?)
      . = unchanged
    """
    w = max(before.width, after.width)
    chars = []
    for i in range(w):
        bbit = before.bits[i] if i < len(before.bits) else 0
        abit = after.bits[i] if i < len(after.bits) else 0
        if bbit is None and abit is not None:
            chars.append(f"{GREEN}K{RESET}")
        elif bbit is not None and abit is None:
            chars.append(f"{RED}B{RESET}")
        else:
            chars.append(f"{DIM}.{RESET}")
    return "".join(reversed(chars))


# ════════════════════════════════════════════════════════════
# 1. TensionDebugger
# ════════════════════════════════════════════════════════════

class TensionDebugger:
    """
    Step through a computation, showing tension change at every operation.

    Usage:
        dbg = TensionDebugger()
        result = dbg.step("XOR", lambda: a ^ b, inputs={'a': a, 'b': b})
        result = dbg.step("AND", lambda: result & mask, inputs={'x': result, 'mask': mask})
        dbg.summary()
    """

    def __init__(self, label="Computation", width=32):
        self.label = label
        self.width = width
        self.steps = []  # list of dicts

    def step(self, name, fn, inputs=None):
        """
        Execute *fn* (a zero-arg callable returning RayonInt),
        record tension before and after, print the step, and return the result.

        *inputs* is an optional dict {name: RayonInt} for display.
        """
        # Compute total input tension
        if inputs:
            input_tensions = {k: v.tension for k, v in inputs.items()}
            total_in = sum(input_tensions.values())
        else:
            input_tensions = {}
            total_in = 0

        result = fn()

        total_out = result.tension
        delta = total_out - total_in

        record = {
            "name": name,
            "input_tensions": dict(input_tensions),
            "total_in": total_in,
            "total_out": total_out,
            "delta": delta,
            "result": result,
        }
        self.steps.append(record)

        # Find a representative input for skip map
        skip_map_str = ""
        if inputs:
            first_input = next(iter(inputs.values()))
            skip_map_str = _skip_map(first_input, result)

        # Print step
        idx = len(self.steps)
        if delta < 0:
            color = GREEN
            tag = "KILL"
        elif delta > 0:
            color = RED
            tag = "BRANCH"
        else:
            color = DIM
            tag = "----"

        in_parts = ", ".join(
            f"{k}:\u03c4={v}" for k, v in input_tensions.items()
        )

        print(
            f"  [{idx:>2}] {name:<14} "
            f"in({in_parts}) "
            f"\u2192 out:\u03c4={total_out:<3} "
            f"{color}\u0394={delta:>+3} {tag}{RESET}"
        )
        if skip_map_str:
            print(f"       skip: {skip_map_str}")

        return result

    def summary(self):
        """Print summary of all steps."""
        total_kills = sum(1 for s in self.steps if s["delta"] < 0)
        total_branches = sum(1 for s in self.steps if s["delta"] > 0)
        total_neutral = sum(1 for s in self.steps if s["delta"] == 0)
        total_delta = sum(s["delta"] for s in self.steps)

        print()
        print(f"  {BOLD}Summary: {self.label}{RESET}")
        print(f"    Steps:    {len(self.steps)}")
        print(f"    {GREEN}Kills:    {total_kills}{RESET}")
        print(f"    {RED}Branches: {total_branches}{RESET}")
        print(f"    Neutral:  {total_neutral}")
        print(f"    Net \u0394\u03c4:   {total_delta:+d}")
        if self.steps:
            print(
                f"    Final \u03c4:  {self.steps[-1]['total_out']}"
            )


# ════════════════════════════════════════════════════════════
# 2. TensionHeatmap
# ════════════════════════════════════════════════════════════

class TensionHeatmap:
    """
    Display tension of every element in a RayonArray as a visual bar.

    Example output:
        W[ 0] ........ tau=0  (fully known)
        W[ 1] ######## tau=32 (fully unknown)
        W[ 2] ##..##.. tau=16 (partial)
    """

    @staticmethod
    def display(arr, bar_width=32, name=None):
        label = name or arr.name
        print(f"  {BOLD}Tension Heatmap: {label}  (total \u03c4={arr.tension}){RESET}")
        print()

        for i, elem in enumerate(arr.elements):
            t = elem.tension
            w = elem.width

            # Scale bar to bar_width characters
            filled = round(t / w * bar_width) if w > 0 else 0
            empty = bar_width - filled

            if t == 0:
                bar = f"{DIM}{'.' * bar_width}{RESET}"
                note = "fully known"
            elif t == w:
                bar = f"{RED}{chr(0x2588) * bar_width}{RESET}"
                note = "fully unknown"
            else:
                # Build a bit-accurate bar from actual bits (scaled)
                bar_chars = []
                for bi in range(bar_width):
                    # Map bar position to bit position
                    bit_idx = int(bi * w / bar_width)
                    b = elem.bits[w - 1 - bit_idx]  # MSB first
                    if b is None:
                        bar_chars.append(f"{YELLOW}{chr(0x2588)}{RESET}")
                    else:
                        bar_chars.append(f"{DIM}.{RESET}")
                bar = "".join(bar_chars)
                note = "partial"

            print(
                f"  {label}[{i:>2}] {bar} \u03c4={t:<3} ({note})"
            )
        print()


# ════════════════════════════════════════════════════════════
# 3. BranchTracer
# ════════════════════════════════════════════════════════════

class BranchTracer:
    """
    Trace AND(?,?) branch points in a computation.

    Each AND where both inputs have unknown bits at the same position
    is a potential branch point.  Total branch count = difficulty.
    """

    def __init__(self):
        self.branches = []

    def trace_and(self, a, b, name_a="a", name_b="b", op_label="AND"):
        """
        Analyze a & b for branch points (bit positions where both are ?).
        Records them and returns the result.
        """
        w = max(a.width, b.width)
        branch_bits = []
        kill_bits = []

        for i in range(w):
            ai = a.bits[i] if i < len(a.bits) else 0
            bi = b.bits[i] if i < len(b.bits) else 0

            if ai is None and bi is None:
                branch_bits.append(i)
            elif (ai == 0 and bi is None) or (ai is None and bi == 0):
                kill_bits.append(i)

        result = a & b

        record = {
            "op": op_label,
            "name_a": name_a,
            "name_b": name_b,
            "branch_bits": branch_bits,
            "kill_bits": kill_bits,
            "tau_a": a.tension,
            "tau_b": b.tension,
            "tau_out": result.tension,
        }
        self.branches.append(record)

        return result

    def trace_ch(self, e, f, g, name_e="e", name_f="f", name_g="g"):
        """Trace Ch(e,f,g) = (e AND f) XOR (NOT(e) AND g)."""
        r1 = self.trace_and(e, f, name_e, name_f, f"Ch:AND({name_e},{name_f})")
        ne = ~e
        r2 = self.trace_and(ne, g, f"~{name_e}", name_g, f"Ch:AND(~{name_e},{name_g})")
        return r1 ^ r2

    def trace_maj(self, a, b, c, name_a="a", name_b="b", name_c="c"):
        """Trace Maj(a,b,c) = (a AND b) XOR (a AND c) XOR (b AND c)."""
        r1 = self.trace_and(a, b, name_a, name_b, f"Maj:AND({name_a},{name_b})")
        r2 = self.trace_and(a, c, name_a, name_c, f"Maj:AND({name_a},{name_c})")
        r3 = self.trace_and(b, c, name_b, name_c, f"Maj:AND({name_b},{name_c})")
        return r1 ^ r2 ^ r3

    def report(self):
        """Print branch trace report."""
        total = sum(len(b["branch_bits"]) for b in self.branches)
        total_kills = sum(len(b["kill_bits"]) for b in self.branches)

        print(f"  {BOLD}Branch Trace Report{RESET}")
        print(f"  {'=' * 60}")

        for rec in self.branches:
            n_br = len(rec["branch_bits"])
            n_kl = len(rec["kill_bits"])

            br_color = RED if n_br > 0 else DIM
            kl_color = GREEN if n_kl > 0 else DIM

            print(
                f"  {rec['op']:<30} "
                f"{br_color}branches={n_br:<3}{RESET} "
                f"{kl_color}kills={n_kl:<3}{RESET} "
                f"\u03c4: {rec['tau_a']}+{rec['tau_b']} \u2192 {rec['tau_out']}"
            )
            if n_br > 0 and n_br <= 8:
                bits_str = ",".join(str(b) for b in rec["branch_bits"])
                print(f"    branch bits: [{bits_str}]")

        print(f"  {'=' * 60}")
        print(
            f"  {RED}Total branch points: {total}{RESET}  "
            f"(difficulty ~ 2^{total})"
        )
        print(
            f"  {GREEN}Total kill points:   {total_kills}{RESET}  "
            f"(free reductions)"
        )
        print()


# ════════════════════════════════════════════════════════════
# 4. FlowVisualizer
# ════════════════════════════════════════════════════════════

class FlowVisualizer:
    """
    Show a data-flow pipeline with tension at each stage.

    Example output:
      input(tau=32) -> XOR(tau=32) -> AND(tau=16, KILL!) -> ADD(tau=24) -> output(tau=24)
    """

    def __init__(self):
        self.nodes = []

    def add(self, label, ri):
        """Record a node in the pipeline."""
        self.nodes.append((label, ri.tension))
        return ri

    def display(self, title="Flow"):
        print(f"  {BOLD}{title}{RESET}")
        parts = []
        prev_tau = None
        for label, tau in self.nodes:
            # Determine tag
            tag = ""
            color = RESET
            if prev_tau is not None:
                if tau < prev_tau:
                    tag = ", KILL!"
                    color = GREEN
                elif tau > prev_tau:
                    tag = ", BRANCH!"
                    color = RED

            parts.append(f"{color}{label}(\u03c4={tau}{tag}){RESET}")
            prev_tau = tau

        line = f" {CYAN}\u2192{RESET} ".join(parts)
        print(f"  {line}")
        print()


# ════════════════════════════════════════════════════════════
# DEMO: SHA-256-like computation with partial inputs
# ════════════════════════════════════════════════════════════

def demo_sha256_step():
    """
    Run a single SHA-256 round with mixed known/unknown inputs,
    demonstrating all four debugger views.
    """
    W = 32

    print()
    print("=" * 70)
    print(f"  {BOLD}RAYON DEBUGGER DEMO: SHA-256-like round with partial inputs{RESET}")
    print("=" * 70)
    print()

    # ── Setup: 8 state words, some known, some unknown ──
    # Simulating mid-computation: a,b,c known from constants; e,f,g partially unknown
    a = RayonInt.known(0x6a09e667, W)
    b = RayonInt.known(0xbb67ae85, W)
    c = RayonInt.known(0x3c6ef372, W)
    d = RayonInt.known(0xa54ff53a, W)
    e = RayonInt.unknown(W)       # unknown state variable
    f = RayonInt.unknown(W)       # unknown
    g = RayonInt.unknown(W)       # unknown
    h = RayonInt.known(0x5be0cd19, W)

    # Round constant and message word
    K_i = RayonInt.known(0x428a2f98, W)
    W_i = RayonInt.partial(0x61626380, 0x0000FFFF, W)  # top half known, bottom unknown

    # ── View 1: Tension Heatmap of state ──
    print(f"  {BOLD}[VIEW 1] Tension Heatmap -- SHA-256 State{RESET}")
    print()

    state = RayonArray(
        "State",
        [a, b, c, d, e, f, g, h],
        width=W,
    )
    TensionHeatmap.display(state)

    # ── View 2: Step-by-step debugger for one round ──
    print(f"  {BOLD}[VIEW 2] TensionDebugger -- One SHA-256 Round{RESET}")
    print()

    dbg = TensionDebugger("SHA-256 Round 0", width=W)

    # Sigma1(e)
    s1 = dbg.step("Sigma1(e)", lambda: Sigma1(e), inputs={"e": e})

    # Ch(e, f, g)
    ch = dbg.step("Ch(e,f,g)", lambda: Ch(e, f, g), inputs={"e": e, "f": f, "g": g})

    # T1 = h + Sigma1(e) + Ch(e,f,g) + K_i + W_i
    t1_part = dbg.step("h+S1", lambda: mod_add(h, s1), inputs={"h": h, "S1": s1})
    t1_part = dbg.step("+Ch", lambda: mod_add(t1_part, ch), inputs={"acc": t1_part, "Ch": ch})
    t1_part = dbg.step("+K_i", lambda: mod_add(t1_part, K_i), inputs={"acc": t1_part, "K_i": K_i})
    T1 = dbg.step("+W_i", lambda: mod_add(t1_part, W_i), inputs={"acc": t1_part, "W_i": W_i})

    # Sigma0(a)
    s0 = dbg.step("Sigma0(a)", lambda: Sigma0(a), inputs={"a": a})

    # Maj(a, b, c)  -- all known, so tension = 0
    maj = dbg.step("Maj(a,b,c)", lambda: Maj(a, b, c), inputs={"a": a, "b": b, "c": c})

    # T2 = Sigma0(a) + Maj(a,b,c)
    T2 = dbg.step("T2=S0+Maj", lambda: mod_add(s0, maj), inputs={"S0": s0, "Maj": maj})

    # New state
    h_new = g
    g_new = f
    f_new = e
    e_new = dbg.step("e'=d+T1", lambda: mod_add(d, T1), inputs={"d": d, "T1": T1})
    d_new = c
    c_new = b
    b_new = a
    a_new = dbg.step("a'=T1+T2", lambda: mod_add(T1, T2), inputs={"T1": T1, "T2": T2})

    dbg.summary()
    print()

    # ── View 3: Branch Tracer ──
    print(f"  {BOLD}[VIEW 3] BranchTracer -- AND operations in Ch and Maj{RESET}")
    print()

    bt = BranchTracer()
    # Re-trace Ch and Maj with the tracer
    bt.trace_ch(e, f, g, "e", "f", "g")
    bt.trace_maj(a, b, c, "a", "b", "c")
    # Also trace with partially-known e
    e_partial = RayonInt.partial(0xABCDEF00, 0x0000FFFF, W)  # top 16 known, low 16 unknown
    bt.trace_ch(e_partial, f, g, "e_partial", "f", "g")
    bt.report()

    # ── View 4: Flow Visualizer ──
    print(f"  {BOLD}[VIEW 4] FlowVisualizer -- T1 computation pipeline{RESET}")
    print()

    flow = FlowVisualizer()
    flow.add("h(known)", h)
    flow.add("Sigma1(e)", s1)
    # Recompute additions to record in flow
    acc = mod_add(h, s1)
    flow.add("h+S1", acc)
    acc = mod_add(acc, ch)
    flow.add("+Ch", acc)
    acc = mod_add(acc, K_i)
    flow.add("+K_i", acc)
    acc = mod_add(acc, W_i)
    flow.add("+W_i=T1", acc)
    flow.display("T1 = h + Sigma1(e) + Ch(e,f,g) + K_i + W_i")

    # Second flow: state update
    flow2 = FlowVisualizer()
    flow2.add("d(known)", d)
    flow2.add("T1", T1)
    flow2.add("e'=d+T1", e_new)
    flow2.display("New e = d + T1")

    flow3 = FlowVisualizer()
    flow3.add("T1", T1)
    flow3.add("T2(known)", T2)
    flow3.add("a'=T1+T2", a_new)
    flow3.display("New a = T1 + T2")

    # ── Heatmap of new state ──
    print(f"  {BOLD}[VIEW 1b] Tension Heatmap -- State AFTER round{RESET}")
    print()

    new_state = RayonArray(
        "State'",
        [a_new, b_new, c_new, d_new, e_new, f_new, g_new, h_new],
        width=W,
    )
    TensionHeatmap.display(new_state)

    # ── Message schedule heatmap ──
    print(f"  {BOLD}[VIEW 1c] Tension Heatmap -- Message Schedule W[0..15]{RESET}")
    print()

    # Simulate: first 4 words are message (unknown), rest is padding (known)
    w_elems = []
    for i in range(16):
        if i < 4:
            w_elems.append(RayonInt.unknown(W))
        elif i == 15:
            # length field: partially known (length < 2^16)
            w_elems.append(RayonInt.partial(0x00000000, 0x0000FFFF, W))
        else:
            w_elems.append(RayonInt.known(0, W))
    W_arr = RayonArray("W", w_elems, width=W)
    TensionHeatmap.display(W_arr)

    print("=" * 70)
    print(f"  {BOLD}DEBUGGER DEMO COMPLETE{RESET}")
    print("=" * 70)
    print()


if __name__ == "__main__":
    demo_sha256_step()
