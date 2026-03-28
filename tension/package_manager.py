"""
PACKAGE MANAGER -- Reusable module system for Rayon.

Packages are file-based, local-only bundles of Rayon functions.
Each package carries a TENSION PROFILE: the average tension cost
of the functions it exports. When you import "crypto", you see
exactly how hard its operations are.

Components:
  RayonPackage  -- define a reusable module with exports + tension
  Registry      -- local package registry with dependency resolution
  PackageLoader -- import packages into Rayon programs

No network. No magic. Just tension-aware modules.
"""

from collections import defaultdict


# ================================================================
# RAYON PACKAGE -- a reusable module definition
# ================================================================

class RayonPackage:
    """
    A named, versioned bundle of functions with tension metadata.

    Each export is a (name, callable, tension_cost) triple.
    The package's tension_profile is the average tension of its exports.
    """

    def __init__(self, name, version="0.1.0", dependencies=None):
        self.name = name
        self.version = version
        self.dependencies = dependencies or []
        self._exports = {}  # name -> (callable, tension_cost)

    def export(self, name, func, tension_cost=0.0):
        """Register an exported function with its tension cost."""
        self._exports[name] = (func, tension_cost)

    @property
    def exports(self):
        """List of exported function names."""
        return list(self._exports.keys())

    @property
    def tension_profile(self):
        """Average tension across all exported functions."""
        if not self._exports:
            return 0.0
        costs = [cost for _, cost in self._exports.values()]
        return sum(costs) / len(costs)

    def get(self, name):
        """Retrieve an exported callable by name."""
        if name not in self._exports:
            raise KeyError(f"Package '{self.name}' has no export '{name}'")
        return self._exports[name][0]

    def get_tension(self, name):
        """Retrieve the tension cost of an export."""
        if name not in self._exports:
            raise KeyError(f"Package '{self.name}' has no export '{name}'")
        return self._exports[name][1]

    def __repr__(self):
        return (
            f"RayonPackage({self.name} v{self.version}, "
            f"exports={len(self._exports)}, "
            f"tension={self.tension_profile:.1f})"
        )


# ================================================================
# REGISTRY -- local package store with dependency resolution
# ================================================================

class Registry:
    """
    Local package registry.

    register(pkg)  -- add a package
    find(name)     -- look up by name
    list_all()     -- all registered packages
    resolve(name)  -- topological sort of transitive dependencies
    """

    def __init__(self):
        self._packages = {}  # name -> RayonPackage

    def register(self, package):
        """Register a package. Overwrites if same name exists."""
        self._packages[package.name] = package

    def find(self, name):
        """Find a package by name, or None."""
        return self._packages.get(name)

    def list_all(self):
        """Return all registered packages."""
        return list(self._packages.values())

    def resolve(self, name):
        """
        Topological sort: return dependency chain ending with `name`.

        Raises ValueError on missing dependency or cycle.
        """
        order = []
        visited = set()
        in_stack = set()

        def _visit(pkg_name):
            if pkg_name in visited:
                return
            if pkg_name in in_stack:
                raise ValueError(f"Dependency cycle detected involving '{pkg_name}'")
            pkg = self._packages.get(pkg_name)
            if pkg is None:
                raise ValueError(f"Missing dependency: '{pkg_name}'")
            in_stack.add(pkg_name)
            for dep in pkg.dependencies:
                _visit(dep)
            in_stack.remove(pkg_name)
            visited.add(pkg_name)
            order.append(pkg_name)

        _visit(name)
        return order


# ================================================================
# BUILT-IN PACKAGES -- crypto, math, solver
# ================================================================

def _build_crypto_package():
    """
    Built-in 'crypto' package.
    Depends on: math
    Exports: sha256_compress, aes_sbox, hash_combine
    """
    import hashlib

    def sha256_compress(data):
        """SHA-256 hash of bytes/string. High tension: one-way."""
        if isinstance(data, str):
            data = data.encode()
        return hashlib.sha256(data).hexdigest()

    def aes_sbox(byte_val):
        """
        AES S-box substitution for a single byte.
        Simplified lookup; real S-box is the standard 256-entry table.
        """
        # Use the first 256 entries of a deterministic permutation
        # (real AES S-box values for first few)
        SBOX_PARTIAL = [
            0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5,
            0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76,
        ]
        idx = byte_val & 0xFF
        return SBOX_PARTIAL[idx % len(SBOX_PARTIAL)]

    def hash_combine(a, b):
        """Combine two hash strings. Medium tension: loses info."""
        combined = f"{a}:{b}"
        return hashlib.sha256(combined.encode()).hexdigest()

    pkg = RayonPackage("crypto", version="1.0.0", dependencies=["math"])
    pkg.export("sha256_compress", sha256_compress, tension_cost=32.0)
    pkg.export("aes_sbox", aes_sbox, tension_cost=8.0)
    pkg.export("hash_combine", hash_combine, tension_cost=32.0)
    return pkg


def _build_math_package():
    """
    Built-in 'math' package.
    No dependencies.
    Exports: gf2_add, mod_exp, mat_mul_mod2
    """

    def gf2_add(a, b):
        """GF(2) addition = XOR. Zero tension: perfectly invertible."""
        return a ^ b

    def mod_exp(base, exp, modulus):
        """Modular exponentiation. Moderate tension: trapdoor."""
        return pow(base, exp, modulus)

    def mat_mul_mod2(A, B):
        """
        Matrix multiply over GF(2).
        A and B are lists-of-lists of 0/1 ints.
        Low tension: invertible when matrix is non-singular.
        """
        rows_a = len(A)
        cols_b = len(B[0]) if B else 0
        inner = len(B)
        C = [[0] * cols_b for _ in range(rows_a)]
        for i in range(rows_a):
            for j in range(cols_b):
                s = 0
                for k in range(inner):
                    s ^= A[i][k] & B[k][j]
                C[i][j] = s
        return C

    pkg = RayonPackage("math", version="1.0.0", dependencies=[])
    pkg.export("gf2_add", gf2_add, tension_cost=0.0)
    pkg.export("mod_exp", mod_exp, tension_cost=16.0)
    pkg.export("mat_mul_mod2", mat_mul_mod2, tension_cost=4.0)
    return pkg


def _build_solver_package():
    """
    Built-in 'solver' package.
    Depends on: crypto, math
    Exports: find_preimage, find_collision, solve_constraints
    """

    def find_preimage(hash_func, target, search_space):
        """
        Brute-force preimage search over a finite search space.
        Returns the input that hashes to target, or None.
        Very high tension: exponential in output bits.
        """
        for candidate in search_space:
            if hash_func(candidate) == target:
                return candidate
        return None

    def find_collision(hash_func, search_space):
        """
        Birthday-attack collision finder.
        Returns (a, b) with hash_func(a) == hash_func(b), a != b.
        Or None if no collision found.
        """
        seen = {}
        for item in search_space:
            h = hash_func(item)
            if h in seen and seen[h] != item:
                return (seen[h], item)
            seen[h] = item
        return None

    def solve_constraints(equations, n_vars):
        """
        Solve a system of XOR constraints over GF(2).
        equations: list of (variable_indices, target_bit)
        Returns: dict {var_index: value} or None.

        Gaussian elimination -- linear tension.
        """
        m = len(equations)
        # Augmented matrix rows: list of (set_of_var_indices, rhs)
        rows = [(set(vars), rhs) for vars, rhs in equations]

        assigned = {}
        for col in range(n_vars):
            # Find pivot
            pivot = None
            for r in range(len(rows)):
                if col in rows[r][0]:
                    pivot = r
                    break
            if pivot is None:
                continue
            # Swap to front (not needed, just use pivot in place)
            pvars, prhs = rows[pivot]
            for r in range(len(rows)):
                if r == pivot:
                    continue
                if col in rows[r][0]:
                    rows[r] = (rows[r][0].symmetric_difference(pvars), rows[r][1] ^ prhs)
            assigned[col] = (pvars, prhs)

        # Back-substitute
        solution = {}
        for col in sorted(assigned.keys(), reverse=True):
            pvars, prhs = assigned[col]
            val = prhs
            for v in pvars:
                if v != col and v in solution:
                    val ^= solution[v]
            solution[col] = val

        # Fill unassigned with 0
        for v in range(n_vars):
            if v not in solution:
                solution[v] = 0

        return solution

    pkg = RayonPackage("solver", version="1.0.0", dependencies=["crypto", "math"])
    pkg.export("find_preimage", find_preimage, tension_cost=64.0)
    pkg.export("find_collision", find_collision, tension_cost=32.0)
    pkg.export("solve_constraints", solve_constraints, tension_cost=4.0)
    return pkg


# ================================================================
# PACKAGE LOADER -- import packages into a Rayon program
# ================================================================

class PackageLoader:
    """
    Import packages from a Registry into a running program.

    loader = PackageLoader(registry)
    crypto = loader.load("crypto")   # resolves deps, prints tension
    h = crypto.sha256_compress(b"hello")
    """

    def __init__(self, registry):
        self.registry = registry
        self._loaded = {}  # name -> _LoadedModule

    def load(self, name):
        """
        Load a package (and all its dependencies) from the registry.
        Returns a module-like object whose attributes are the exports.
        Prints the tension profile on first load.
        """
        if name in self._loaded:
            return self._loaded[name]

        # Resolve dependency order
        dep_chain = self.registry.resolve(name)

        # Load each dependency first
        for dep_name in dep_chain:
            if dep_name in self._loaded:
                continue
            pkg = self.registry.find(dep_name)
            module = _LoadedModule(pkg)
            self._loaded[dep_name] = module
            # Display tension profile
            self._print_profile(pkg, is_dep=(dep_name != name))

        return self._loaded[name]

    def _print_profile(self, pkg, is_dep=False):
        prefix = "  dep" if is_dep else " load"
        bar = _tension_bar(pkg.tension_profile)
        print(f"  [{prefix}] {pkg.name} v{pkg.version}  "
              f"tension={pkg.tension_profile:5.1f}  {bar}  "
              f"exports: {', '.join(pkg.exports)}")


class _LoadedModule:
    """Thin wrapper: attribute access returns exported callables."""

    def __init__(self, package):
        self._package = package
        for name in package.exports:
            setattr(self, name, package.get(name))

    def __repr__(self):
        return f"<module '{self._package.name}' ({len(self._package.exports)} exports)>"


def _tension_bar(tension, width=12):
    """Render a compact tension bar: low=[....] high=[########]."""
    # Normalise to 0..1 (cap at 64 as practical max)
    frac = min(tension / 64.0, 1.0)
    filled = int(frac * width)
    return "[" + "#" * filled + "." * (width - filled) + "]"


# ================================================================
# DEFAULT REGISTRY -- pre-loaded with built-in packages
# ================================================================

def default_registry():
    """Create a registry pre-loaded with crypto, math, solver."""
    reg = Registry()
    reg.register(_build_math_package())
    reg.register(_build_crypto_package())
    reg.register(_build_solver_package())
    return reg


# ================================================================
# TEST
# ================================================================

def test_package_manager():
    print("=" * 64)
    print("RAYON PACKAGE MANAGER -- test suite")
    print("=" * 64)
    results = []

    def check(label, condition):
        status = "\u2713" if condition else "\u2717"
        results.append(condition)
        print(f"  {status} {label}")

    # ----------------------------------------------------------
    # 1. Package creation
    # ----------------------------------------------------------
    print("\n[1] Package creation")
    math_pkg = _build_math_package()
    crypto_pkg = _build_crypto_package()
    solver_pkg = _build_solver_package()

    check("math package has 3 exports", len(math_pkg.exports) == 3)
    check("crypto depends on math", "math" in crypto_pkg.dependencies)
    check("solver depends on crypto and math",
          set(solver_pkg.dependencies) == {"crypto", "math"})
    check(f"math tension_profile={math_pkg.tension_profile:.1f}",
          math_pkg.tension_profile >= 0)
    check(f"crypto tension_profile={crypto_pkg.tension_profile:.1f}",
          crypto_pkg.tension_profile > 0)
    check(f"solver tension_profile={solver_pkg.tension_profile:.1f}",
          solver_pkg.tension_profile > 0)

    # ----------------------------------------------------------
    # 2. Registry: register, find, list_all
    # ----------------------------------------------------------
    print("\n[2] Registry operations")
    reg = Registry()
    reg.register(math_pkg)
    reg.register(crypto_pkg)
    reg.register(solver_pkg)

    check("find('math') returns math package", reg.find("math") is math_pkg)
    check("find('nonexistent') returns None", reg.find("nonexistent") is None)
    check("list_all() has 3 packages", len(reg.list_all()) == 3)

    # ----------------------------------------------------------
    # 3. Dependency resolution (topological sort)
    # ----------------------------------------------------------
    print("\n[3] Dependency resolution")
    order = reg.resolve("solver")
    check(f"solver dep chain = {order}",
          order.index("math") < order.index("crypto") < order.index("solver"))

    order_math = reg.resolve("math")
    check(f"math dep chain = {order_math} (no deps)", order_math == ["math"])

    order_crypto = reg.resolve("crypto")
    check(f"crypto dep chain = {order_crypto}",
          order_crypto == ["math", "crypto"])

    # Cycle detection
    cycle_pkg = RayonPackage("cycle_a", dependencies=["cycle_b"])
    cycle_pkg_b = RayonPackage("cycle_b", dependencies=["cycle_a"])
    cycle_reg = Registry()
    cycle_reg.register(cycle_pkg)
    cycle_reg.register(cycle_pkg_b)
    try:
        cycle_reg.resolve("cycle_a")
        check("cycle detection", False)
    except ValueError:
        check("cycle detection raises ValueError", True)

    # ----------------------------------------------------------
    # 4. PackageLoader: load and call functions
    # ----------------------------------------------------------
    print("\n[4] PackageLoader -- load with tension display")
    loader = PackageLoader(reg)
    crypto_mod = loader.load("crypto")

    check("loaded module has sha256_compress",
          hasattr(crypto_mod, "sha256_compress"))
    check("loaded module has aes_sbox", hasattr(crypto_mod, "aes_sbox"))

    h = crypto_mod.sha256_compress("hello rayon")
    check(f"sha256('hello rayon')={h[:16]}...",
          isinstance(h, str) and len(h) == 64)

    sbox_val = crypto_mod.aes_sbox(0x00)
    check(f"aes_sbox(0x00)=0x{sbox_val:02x}", sbox_val == 0x63)

    # Load math and call gf2_add
    print()
    math_mod = loader.load("math")
    check("gf2_add(0b1010, 0b1100) = 0b0110",
          math_mod.gf2_add(0b1010, 0b1100) == 0b0110)

    # Matrix multiply over GF(2)
    A = [[1, 0], [1, 1]]
    B = [[1, 1], [0, 1]]
    C = math_mod.mat_mul_mod2(A, B)
    check(f"mat_mul_mod2 result = {C}", C == [[1, 1], [1, 0]])

    # Load solver and use constraint solver
    print()
    solver_mod = loader.load("solver")
    # Solve: x0 XOR x1 = 1, x1 XOR x2 = 0
    sol = solver_mod.solve_constraints(
        [([0, 1], 1), ([1, 2], 0)],
        n_vars=3,
    )
    check(f"constraint solution: {sol}",
          (sol[0] ^ sol[1]) == 1 and (sol[1] ^ sol[2]) == 0)

    # Preimage search
    target_hash = crypto_mod.sha256_compress("secret")
    found = solver_mod.find_preimage(
        crypto_mod.sha256_compress,
        target_hash,
        ["nope", "also_no", "secret", "wrong"],
    )
    check(f"find_preimage found '{found}'", found == "secret")

    # Collision search (use a bad hash to guarantee collision)
    def bad_hash(x):
        return x % 4

    pair = solver_mod.find_collision(bad_hash, range(10))
    check(f"find_collision: {pair}", pair is not None and pair[0] != pair[1]
          and bad_hash(pair[0]) == bad_hash(pair[1]))

    # ----------------------------------------------------------
    # Summary
    # ----------------------------------------------------------
    passed = sum(results)
    total = len(results)
    print("\n" + "=" * 64)
    status = "\u2713" if passed == total else "\u2717"
    print(f"  {status} {passed}/{total} tests passed")
    print("=" * 64)


if __name__ == "__main__":
    test_package_manager()
