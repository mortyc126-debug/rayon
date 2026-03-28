#!/usr/bin/env python3
"""
TENSION LANGUAGE — Interpreter v0.1

A standalone complexity-aware programming language.

Syntax:
  problem NAME(params) {
    vars: x[N]
    constraint: EXPR
  }
  solve NAME with STRATEGY
  print EXPR

Example:
  problem triangle(N: 6) {
    vars: e[15]
    find: exists(i in 0..N, j in i+1..N, k in j+1..N) {
      e[idx(i,j)] and e[idx(i,k)] and e[idx(j,k)]
    }
  }
  solve triangle
"""

import sys
import re
import math
import time
import random
from itertools import combinations
from collections import OrderedDict


# ════════════════════════════════════════════════════════════
# LEXER
# ════════════════════════════════════════════════════════════

TOKEN_SPEC = [
    ('NUMBER',   r'\d+(\.\d+)?'),
    ('STRING',   r'"[^"]*"'),
    ('ARROW',    r'->'),
    ('LE',       r'<='),
    ('GE',       r'>='),
    ('EQ',       r'=='),
    ('NE',       r'!='),
    ('AND',      r'\band\b'),
    ('OR',       r'\bor\b'),
    ('NOT',      r'\bnot\b'),
    ('TRUE',     r'\btrue\b'),
    ('FALSE',    r'\bfalse\b'),
    ('PROBLEM',  r'\bproblem\b'),
    ('SOLVE',    r'\bsolve\b'),
    ('PRINT',    r'\bprint\b'),
    ('VARS',     r'\bvars\b'),
    ('FIND',     r'\bfind\b'),
    ('EXISTS',   r'\bexists\b'),
    ('FORALL',   r'\bforall\b'),
    ('IN',       r'\bin\b'),
    ('WITH',     r'\bwith\b'),
    ('TENSION',  r'\btension\b'),
    ('IDENT',    r'[a-zA-Z_]\w*'),
    ('LBRACE',   r'\{'),
    ('RBRACE',   r'\}'),
    ('LPAREN',   r'\('),
    ('RPAREN',   r'\)'),
    ('LBRACK',   r'\['),
    ('RBRACK',   r'\]'),
    ('COLON',    r':'),
    ('SEMI',     r';'),
    ('COMMA',    r','),
    ('DOTDOT',   r'\.\.'),
    ('DOT',      r'\.'),
    ('PLUS',     r'\+'),
    ('MINUS',    r'-'),
    ('STAR',     r'\*'),
    ('COMMENT',  r'//[^\n]*'),
    ('SLASH',    r'/'),
    ('ASSIGN',   r'='),
    ('NEWLINE',  r'\n'),
    ('SKIP',     r'[ \t]+'),
]

TOKEN_RE = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in TOKEN_SPEC)


def tokenize(source):
    tokens = []
    for m in re.finditer(TOKEN_RE, source):
        kind = m.lastgroup
        value = m.group()
        if kind in ('SKIP', 'COMMENT', 'NEWLINE'):
            continue
        if kind == 'NUMBER':
            value = float(value) if '.' in value else int(value)
        if kind == 'STRING':
            value = value[1:-1]
        tokens.append((kind, value))
    tokens.append(('EOF', None))
    return tokens


# ════════════════════════════════════════════════════════════
# PARSER
# ════════════════════════════════════════════════════════════

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos]

    def advance(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, kind):
        tok = self.advance()
        if tok[0] != kind:
            raise SyntaxError(f'Expected {kind}, got {tok[0]} ({tok[1]})')
        return tok

    def match(self, kind):
        if self.peek()[0] == kind:
            return self.advance()
        return None

    def parse_program(self):
        statements = []
        while self.peek()[0] != 'EOF':
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)
        return ('program', statements)

    def parse_statement(self):
        tok = self.peek()
        if tok[0] == 'PROBLEM':
            return self.parse_problem()
        elif tok[0] == 'SOLVE':
            return self.parse_solve()
        elif tok[0] == 'PRINT':
            return self.parse_print()
        elif tok[0] == 'TENSION':
            return self.parse_tension()
        else:
            raise SyntaxError(f'Unexpected token: {tok}')

    def parse_problem(self):
        self.expect('PROBLEM')
        name = self.expect('IDENT')[1]
        self.expect('LPAREN')
        params = self.parse_params()
        self.expect('RPAREN')
        self.expect('LBRACE')

        body = {}
        while self.peek()[0] != 'RBRACE':
            tok = self.advance()
            key = tok[1]
            self.expect('COLON')
            if key == 'vars':
                body['vars'] = self.parse_var_decl()
            elif key == 'find':
                body['find'] = self.parse_expr()
            elif key == 'constraint':
                body['find'] = self.parse_expr()
            else:
                body[key] = self.parse_expr()

        self.expect('RBRACE')
        return ('problem', name, params, body)

    def parse_params(self):
        params = OrderedDict()
        while self.peek()[0] != 'RPAREN':
            name = self.expect('IDENT')[1]
            self.expect('COLON')
            val = self.expect('NUMBER')[1]
            params[name] = val
            self.match('COMMA')
        return params

    def parse_var_decl(self):
        name = self.expect('IDENT')[1]
        self.expect('LBRACK')
        size = self.parse_expr()
        self.expect('RBRACK')
        return ('vardecl', name, size)

    def parse_expr(self):
        return self.parse_or()

    def parse_or(self):
        left = self.parse_and()
        while self.match('OR'):
            right = self.parse_and()
            left = ('or', left, right)
        return left

    def parse_and(self):
        left = self.parse_not()
        while self.match('AND'):
            right = self.parse_not()
            left = ('and', left, right)
        return left

    def parse_not(self):
        if self.match('NOT'):
            return ('not', self.parse_not())
        return self.parse_comparison()

    def parse_comparison(self):
        left = self.parse_add()
        for op in ('EQ', 'NE', 'LE', 'GE'):
            if self.match(op):
                right = self.parse_add()
                return (op.lower(), left, right)
        return left

    def parse_add(self):
        left = self.parse_mul()
        while True:
            if self.match('PLUS'):
                left = ('add', left, self.parse_mul())
            elif self.match('MINUS'):
                left = ('sub', left, self.parse_mul())
            else:
                break
        return left

    def parse_mul(self):
        left = self.parse_atom()
        while True:
            if self.match('STAR'):
                left = ('mul', left, self.parse_atom())
            elif self.match('SLASH'):
                left = ('div', left, self.parse_atom())
            else:
                break
        return left

    def parse_atom(self):
        tok = self.peek()

        if tok[0] == 'NUMBER':
            self.advance()
            return ('num', tok[1])

        if tok[0] == 'TRUE':
            self.advance()
            return ('bool', True)

        if tok[0] == 'FALSE':
            self.advance()
            return ('bool', False)

        if tok[0] == 'STRING':
            self.advance()
            return ('str', tok[1])

        if tok[0] == 'EXISTS':
            return self.parse_exists()

        if tok[0] == 'FORALL':
            return self.parse_forall()

        if tok[0] == 'IDENT':
            name = self.advance()[1]
            if self.match('LBRACK'):
                idx = self.parse_expr()
                self.expect('RBRACK')
                return ('index', name, idx)
            if self.match('LPAREN'):
                args = []
                while self.peek()[0] != 'RPAREN':
                    args.append(self.parse_expr())
                    self.match('COMMA')
                self.expect('RPAREN')
                return ('call', name, args)
            return ('var', name)

        if self.match('LPAREN'):
            expr = self.parse_expr()
            self.expect('RPAREN')
            return expr

        raise SyntaxError(f'Unexpected in expression: {tok}')

    def parse_exists(self):
        self.expect('EXISTS')
        self.expect('LPAREN')
        bindings = self.parse_bindings()
        self.expect('RPAREN')
        self.expect('LBRACE')
        body = self.parse_expr()
        self.expect('RBRACE')
        return ('exists', bindings, body)

    def parse_forall(self):
        self.expect('FORALL')
        self.expect('LPAREN')
        bindings = self.parse_bindings()
        self.expect('RPAREN')
        self.expect('LBRACE')
        body = self.parse_expr()
        self.expect('RBRACE')
        return ('forall', bindings, body)

    def parse_bindings(self):
        bindings = []
        while self.peek()[0] != 'RPAREN':
            name = self.expect('IDENT')[1]
            self.expect('IN')
            lo = self.parse_expr()
            self.expect('DOTDOT')
            hi = self.parse_expr()
            bindings.append((name, lo, hi))
            self.match('COMMA')
        return bindings

    def parse_solve(self):
        self.expect('SOLVE')
        name = self.expect('IDENT')[1]
        strategy = 'auto'
        if self.match('WITH'):
            strategy = self.expect('IDENT')[1]
        return ('solve', name, strategy)

    def parse_print(self):
        self.expect('PRINT')
        expr = self.parse_expr()
        return ('print', expr)

    def parse_tension(self):
        self.expect('TENSION')
        name = self.expect('IDENT')[1]
        return ('tension', name)


# ════════════════════════════════════════════════════════════
# INTERPRETER
# ════════════════════════════════════════════════════════════

class TensionInterpreter:
    def __init__(self):
        self.problems = {}
        self.env = {}

    def run(self, ast):
        if ast[0] == 'program':
            for stmt in ast[1]:
                self.exec_stmt(stmt)

    def exec_stmt(self, stmt):
        if stmt[0] == 'problem':
            self.define_problem(stmt)
        elif stmt[0] == 'solve':
            self.solve_problem(stmt)
        elif stmt[0] == 'print':
            val = self.eval_expr(stmt[1], {})
            print(f'  → {val}')
        elif stmt[0] == 'tension':
            self.show_tension(stmt[1])

    def define_problem(self, stmt):
        _, name, params, body = stmt
        self.problems[name] = {'params': params, 'body': body}
        print(f'  Defined problem: {name}({", ".join(f"{k}={v}" for k,v in params.items())})')

    def solve_problem(self, stmt):
        _, name, strategy = stmt
        if name not in self.problems:
            print(f'  Error: unknown problem {name}')
            return

        prob = self.problems[name]
        params = prob['params']
        body = prob['body']

        # Extract vars
        var_decl = body.get('vars')
        if var_decl:
            var_name = var_decl[1]
            n = int(self.eval_expr(var_decl[2], dict(params)))
        else:
            n = int(list(params.values())[0]) if params else 10

        find_expr = body.get('find')

        # Build constraint function
        def constraint(assignment):
            env = dict(params)
            env['__assignment'] = assignment
            env['__var_name'] = var_decl[1] if var_decl else 'x'
            try:
                return bool(self.eval_expr(find_expr, env))
            except:
                return False

        # Estimate tension
        t0 = time.time()
        T = self.estimate_tension(n, constraint)
        c = T / (1 + T)

        label = 'POLY' if c < 0.1 else 'EASY' if c < 0.4 else 'GRAY' if c < 0.7 else 'HARD' if c < 0.9 else 'EXTREME'
        print(f'  Tension: T={T:.2f}, c={c:.3f} [{label}]')

        # Select strategy
        if strategy == 'auto':
            if c < 0.4:
                strategy = 'systematic'
            elif c < 0.7:
                strategy = 'adaptive'
            else:
                strategy = 'portfolio'
        print(f'  Strategy: {strategy}')

        # Solve
        t0 = time.time()
        result, nodes = self.execute_solver(n, constraint, strategy)
        dt = time.time() - t0

        if result is not None:
            # Format output
            if var_decl:
                vals = [result.get(i, 0) for i in range(n)]
                compact = ''.join(str(v) for v in vals)
                print(f'  Solution: {var_decl[1]} = [{compact}]')
            print(f'  Solved in {nodes} nodes, {dt:.3f}s ✓')
        else:
            print(f'  No solution found ({nodes} nodes, {dt:.3f}s) ✗')

    def show_tension(self, name):
        if name not in self.problems:
            print(f'  Error: unknown problem {name}')
            return
        prob = self.problems[name]
        params = prob['params']
        body = prob['body']
        var_decl = body.get('vars')
        n = int(self.eval_expr(var_decl[2], dict(params))) if var_decl else 10
        find_expr = body.get('find')

        def constraint(assignment):
            env = dict(params)
            env['__assignment'] = assignment
            env['__var_name'] = var_decl[1] if var_decl else 'x'
            try:
                return bool(self.eval_expr(find_expr, env))
            except:
                return False

        T = self.estimate_tension(n, constraint)
        c = T / (1 + T)
        print(f'  Problem: {name}')
        print(f'  Variables: {n}')
        print(f'  Tension T = {T:.4f}')
        print(f'  Exponent c = {c:.4f}')
        print(f'  Expected 2^(cn) = 2^({c*n:.1f}) = {2**(c*n):.0f} nodes')
        print(f'  Equation of state: c = T/(1+T) = {T:.2f}/{1+T:.2f} = {c:.4f} ✓')

    def eval_expr(self, expr, env):
        if expr is None:
            return None
        tag = expr[0]

        if tag == 'num':
            return expr[1]
        if tag == 'bool':
            return expr[1]
        if tag == 'str':
            return expr[1]
        if tag == 'var':
            name = expr[1]
            if name in env:
                return env[name]
            return 0
        if tag == 'index':
            name, idx_expr = expr[1], expr[2]
            idx = int(self.eval_expr(idx_expr, env))
            assignment = env.get('__assignment', {})
            return assignment.get(idx, 0)
        if tag == 'call':
            name, args = expr[1], expr[2]
            evaluated = [self.eval_expr(a, env) for a in args]
            if name == 'idx':
                # Edge index for complete graph
                i, j = int(evaluated[0]), int(evaluated[1])
                if i > j: i, j = j, i
                N = int(env.get('N', 10))
                idx = 0
                for u in range(N):
                    for v in range(u + 1, N):
                        if u == i and v == j:
                            return idx
                        idx += 1
                return 0
            return 0
        if tag == 'add':
            return self.eval_expr(expr[1], env) + self.eval_expr(expr[2], env)
        if tag == 'sub':
            return self.eval_expr(expr[1], env) - self.eval_expr(expr[2], env)
        if tag == 'mul':
            return self.eval_expr(expr[1], env) * self.eval_expr(expr[2], env)
        if tag == 'div':
            r = self.eval_expr(expr[2], env)
            return self.eval_expr(expr[1], env) / r if r else 0
        if tag == 'and':
            return self.eval_expr(expr[1], env) and self.eval_expr(expr[2], env)
        if tag == 'or':
            return self.eval_expr(expr[1], env) or self.eval_expr(expr[2], env)
        if tag == 'not':
            return not self.eval_expr(expr[1], env)
        if tag == 'eq':
            return self.eval_expr(expr[1], env) == self.eval_expr(expr[2], env)
        if tag == 'exists':
            return self.eval_quantifier(expr, env, any)
        if tag == 'forall':
            return self.eval_quantifier(expr, env, all)
        return 0

    def eval_quantifier(self, expr, env, aggregator):
        _, bindings, body = expr
        return self._eval_bindings(bindings, 0, body, dict(env), aggregator)

    def _eval_bindings(self, bindings, idx, body, env, aggregator):
        if idx >= len(bindings):
            return self.eval_expr(body, env)
        name, lo_expr, hi_expr = bindings[idx]
        lo = int(self.eval_expr(lo_expr, env))
        hi = int(self.eval_expr(hi_expr, env))

        def gen():
            for val in range(lo, hi):
                env[name] = val
                yield self._eval_bindings(bindings, idx + 1, body, env, aggregator)

        return aggregator(gen())

    def estimate_tension(self, n, constraint, samples=200):
        determined = 0
        for _ in range(samples):
            fixed = {}
            free = list(range(n))
            random.shuffle(free)
            for i in free[:n // 2]:
                fixed[i] = random.randint(0, 1)
            results = set()
            for _ in range(min(30, 2 ** (n - n // 2))):
                a = dict(fixed)
                for i in free[n // 2:]:
                    a[i] = random.randint(0, 1)
                results.add(constraint(a))
                if len(results) > 1:
                    break
            if len(results) == 1:
                determined += 1

        rate = determined / samples
        if rate > 0.99: return 0.01
        if rate < 0.01: return 100.0
        return (1 - rate) / rate

    def execute_solver(self, n, constraint, strategy):
        nodes = [0]

        def dfs(fixed, free):
            nodes[0] += 1
            if nodes[0] > 100000:
                return None
            if not free:
                return dict(fixed) if constraint(fixed) else None
            # Probe
            if len(free) > 10:
                sat = False
                for _ in range(20):
                    t = dict(fixed)
                    for v in free: t[v] = random.randint(0, 1)
                    if constraint(t):
                        sat = True
                        if strategy != 'systematic':
                            return t
                if not sat and strategy != 'systematic':
                    return None
            var = free[0]
            for val in [1, 0]:
                fixed[var] = val
                r = dfs(dict(fixed), free[1:])
                if r is not None: return r
            return None

        if strategy == 'portfolio':
            # Try random first
            for _ in range(5000):
                nodes[0] += 1
                a = {i: random.randint(0, 1) for i in range(n)}
                if constraint(a): return a, nodes[0]
            # Then greedy
            fixed = {}
            for var in range(n):
                best, best_s = 0, -1
                for val in [0, 1]:
                    fixed[var] = val
                    s = sum(1 for _ in range(20)
                            if constraint({**fixed, **{i: random.randint(0, 1) for i in range(n) if i not in fixed}}))
                    nodes[0] += 1
                    if s > best_s: best_s, best = s, val
                fixed[var] = best
            if constraint(fixed): return fixed, nodes[0]
            return None, nodes[0]
        else:
            free = list(range(n))
            if strategy == 'adaptive':
                random.shuffle(free)
            r = dfs({}, free)
            return r, nodes[0]


# ════════════════════════════════════════════════════════════
# REPL & FILE EXECUTION
# ════════════════════════════════════════════════════════════

def run_file(filename):
    with open(filename) as f:
        source = f.read()
    tokens = tokenize(source)
    parser = Parser(tokens)
    ast = parser.parse_program()
    interp = TensionInterpreter()
    interp.run(ast)

def run_source(source):
    tokens = tokenize(source)
    parser = Parser(tokens)
    ast = parser.parse_program()
    interp = TensionInterpreter()
    interp.run(ast)

def repl():
    print("╔═══════════════════════════════════════════════╗")
    print("║  TENSION LANG v0.1 — Interactive REPL        ║")
    print("║  Type 'help' for commands, 'quit' to exit    ║")
    print("╚═══════════════════════════════════════════════╝")
    print()

    interp = TensionInterpreter()
    buffer = []

    while True:
        try:
            prompt = '>>> ' if not buffer else '... '
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print('\nBye!')
            break

        if line.strip() == 'quit':
            break
        if line.strip() == 'help':
            print('  Commands:')
            print('    problem NAME(params) { vars: x[N]  find: EXPR }')
            print('    solve NAME')
            print('    solve NAME with systematic|adaptive|portfolio')
            print('    tension NAME')
            print('    print EXPR')
            print('    quit')
            continue

        buffer.append(line)
        source = '\n'.join(buffer)

        # Check if complete (balanced braces)
        if source.count('{') > source.count('}'):
            continue

        try:
            tokens = tokenize(source)
            parser = Parser(tokens)
            ast = parser.parse_program()
            interp.run(ast)
        except SyntaxError as e:
            print(f'  Syntax error: {e}')
        except Exception as e:
            print(f'  Error: {e}')

        buffer = []


if __name__ == '__main__':
    if len(sys.argv) > 1:
        run_file(sys.argv[1])
    else:
        repl()
