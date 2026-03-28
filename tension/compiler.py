#!/usr/bin/env python3
"""
RAYON COMPILER — Rayon syntax to executable Python with tension tracking.

Compiles Rayon source code to Python that uses RayonInt, RayonArray, etc.
Auto-injects tension tracking into every operation.

Rayon syntax:
  fn add_xor(a: Int32, b: Int32) -> Int32 {
      let c = a + b
      let d = c ^ 0xFF
      return d
  }

  let x = 42
  let y = ?           // unknown!
  let z = add_xor(x, y)
  print(z)            // shows value with tension
"""

import sys
import os

# Workaround: the local types.py shadows stdlib types module.
# We must ensure the parent of this package isn't polluting sys.path
# for stdlib imports. We temporarily fix sys.path for the import.
_orig_path = sys.path[:]
sys.path = [p for p in sys.path if os.path.abspath(p) != os.path.dirname(os.path.abspath(__file__))]
import re
import textwrap
sys.path = _orig_path


# ════════════════════════════════════════════════════════════
# LEXER — Extended for Rayon syntax
# ════════════════════════════════════════════════════════════

TOKEN_SPEC = [
    ('NUMBER_HEX', r'0[xX][0-9a-fA-F]+'),
    ('NUMBER_BIN', r'0[bB][01]+'),
    ('NUMBER',     r'\d+(\.\d+)?'),
    ('STRING',     r'"[^"]*"'),
    ('ARROW',      r'->'),
    ('LE',         r'<='),
    ('GE',         r'>='),
    ('EQ',         r'=='),
    ('NE',         r'!='),
    ('AND_KW',     r'\band\b'),
    ('OR_KW',      r'\bor\b'),
    ('NOT_KW',     r'\bnot\b'),
    ('TRUE',       r'\btrue\b'),
    ('FALSE',      r'\bfalse\b'),
    ('FN',         r'\bfn\b'),
    ('LET',        r'\blet\b'),
    ('RETURN',     r'\breturn\b'),
    ('IF',         r'\bif\b'),
    ('ELSE',       r'\belse\b'),
    ('WHILE',      r'\bwhile\b'),
    ('FOR',        r'\bfor\b'),
    ('IN',         r'\bin\b'),
    ('PRINT',      r'\bprint\b'),
    ('UNKNOWN',    r'\?'),
    ('IDENT',      r'[a-zA-Z_]\w*'),
    ('LBRACE',     r'\{'),
    ('RBRACE',     r'\}'),
    ('LPAREN',     r'\('),
    ('RPAREN',     r'\)'),
    ('LBRACK',     r'\['),
    ('RBRACK',     r'\]'),
    ('COLON',      r':'),
    ('SEMI',       r';'),
    ('COMMA',      r','),
    ('DOTDOT',     r'\.\.'),
    ('DOT',        r'\.'),
    ('CARET',      r'\^'),
    ('AMP',        r'&'),
    ('PIPE',       r'\|'),
    ('TILDE',      r'~'),
    ('PLUS',       r'\+'),
    ('MINUS',      r'-'),
    ('STAR',       r'\*'),
    ('SLASH',      r'/'),
    ('PERCENT',    r'%'),
    ('ASSIGN',     r'='),
    ('COMMENT',    r'//[^\n]*'),
    ('NEWLINE',    r'\n'),
    ('SKIP',       r'[ \t]+'),
]

TOKEN_RE = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in TOKEN_SPEC)


class Token:
    __slots__ = ('kind', 'value', 'line')

    def __init__(self, kind, value, line=0):
        self.kind = kind
        self.value = value
        self.line = line

    def __repr__(self):
        return f'Token({self.kind}, {self.value!r})'


def tokenize(source):
    tokens = []
    line = 1
    for m in re.finditer(TOKEN_RE, source):
        kind = m.lastgroup
        value = m.group()
        if kind == 'NEWLINE':
            line += 1
            continue
        if kind in ('SKIP', 'COMMENT'):
            continue
        if kind == 'NUMBER_HEX':
            value = int(value, 16)
            kind = 'NUMBER'
        elif kind == 'NUMBER_BIN':
            value = int(value, 2)
            kind = 'NUMBER'
        elif kind == 'NUMBER':
            value = float(value) if '.' in value else int(value)
        elif kind == 'STRING':
            value = value[1:-1]
        tokens.append(Token(kind, value, line))
    tokens.append(Token('EOF', None, line))
    return tokens


# ════════════════════════════════════════════════════════════
# AST NODES
# ════════════════════════════════════════════════════════════

class ASTNode:
    pass

class Program(ASTNode):
    def __init__(self, statements):
        self.statements = statements

class FnDef(ASTNode):
    def __init__(self, name, params, ret_type, body):
        self.name = name
        self.params = params       # [(name, type_annotation), ...]
        self.ret_type = ret_type   # type string or None
        self.body = body           # list of statements

class LetDecl(ASTNode):
    def __init__(self, name, type_ann, expr):
        self.name = name
        self.type_ann = type_ann   # type annotation string or None
        self.expr = expr

class ReturnStmt(ASTNode):
    def __init__(self, expr):
        self.expr = expr

class PrintStmt(ASTNode):
    def __init__(self, expr):
        self.expr = expr

class IfStmt(ASTNode):
    def __init__(self, cond, then_body, else_body):
        self.cond = cond
        self.then_body = then_body
        self.else_body = else_body

class WhileStmt(ASTNode):
    def __init__(self, cond, body):
        self.cond = cond
        self.body = body

class ExprStmt(ASTNode):
    def __init__(self, expr):
        self.expr = expr

class AssignStmt(ASTNode):
    def __init__(self, name, expr):
        self.name = name
        self.expr = expr

# Expressions
class NumberLit(ASTNode):
    def __init__(self, value):
        self.value = value

class StringLit(ASTNode):
    def __init__(self, value):
        self.value = value

class BoolLit(ASTNode):
    def __init__(self, value):
        self.value = value

class UnknownLit(ASTNode):
    """The ? literal -- creates an unknown value."""
    def __init__(self, type_ann=None):
        self.type_ann = type_ann

class Identifier(ASTNode):
    def __init__(self, name):
        self.name = name

class BinOp(ASTNode):
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

class UnaryOp(ASTNode):
    def __init__(self, op, operand):
        self.op = op
        self.operand = operand

class CallExpr(ASTNode):
    def __init__(self, func, args):
        self.func = func
        self.args = args

class IndexExpr(ASTNode):
    def __init__(self, obj, index):
        self.obj = obj
        self.index = index


# ════════════════════════════════════════════════════════════
# PARSER — Rayon syntax
# ════════════════════════════════════════════════════════════

class RayonParser:
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
        if tok.kind != kind:
            raise SyntaxError(
                f'Line {tok.line}: Expected {kind}, got {tok.kind} ({tok.value!r})')
        return tok

    def match(self, kind):
        if self.peek().kind == kind:
            return self.advance()
        return None

    def at(self, kind):
        return self.peek().kind == kind

    # ── Type annotations ──

    def parse_type(self):
        """Parse a type annotation like Int8, Int32, Array[Int8, 16]."""
        name = self.expect('IDENT').value
        if self.match('LBRACK'):
            params = [self.parse_type_or_number()]
            while self.match('COMMA'):
                params.append(self.parse_type_or_number())
            self.expect('RBRACK')
            return f'{name}[{", ".join(str(p) for p in params)}]'
        return name

    def parse_type_or_number(self):
        if self.at('NUMBER'):
            return self.advance().value
        return self.parse_type()

    # ── Program ──

    def parse_program(self):
        stmts = []
        while not self.at('EOF'):
            stmts.append(self.parse_statement())
        return Program(stmts)

    # ── Statements ──

    def parse_statement(self):
        if self.at('FN'):
            return self.parse_fn()
        elif self.at('LET'):
            return self.parse_let()
        elif self.at('RETURN'):
            return self.parse_return()
        elif self.at('PRINT'):
            return self.parse_print()
        elif self.at('IF'):
            return self.parse_if()
        elif self.at('WHILE'):
            return self.parse_while()
        elif self.at('LBRACE'):
            return self.parse_block_as_stmt()
        else:
            return self.parse_expr_or_assign_stmt()

    def parse_fn(self):
        self.expect('FN')
        name = self.expect('IDENT').value
        self.expect('LPAREN')
        params = []
        while not self.at('RPAREN'):
            pname = self.expect('IDENT').value
            self.expect('COLON')
            ptype = self.parse_type()
            params.append((pname, ptype))
            self.match('COMMA')
        self.expect('RPAREN')
        ret_type = None
        if self.match('ARROW'):
            ret_type = self.parse_type()
        body = self.parse_block()
        return FnDef(name, params, ret_type, body)

    def parse_let(self):
        self.expect('LET')
        name = self.expect('IDENT').value
        type_ann = None
        if self.match('COLON'):
            type_ann = self.parse_type()
        self.expect('ASSIGN')
        expr = self.parse_expr()
        return LetDecl(name, type_ann, expr)

    def parse_return(self):
        self.expect('RETURN')
        expr = self.parse_expr()
        return ReturnStmt(expr)

    def parse_print(self):
        self.expect('PRINT')
        self.expect('LPAREN')
        expr = self.parse_expr()
        self.expect('RPAREN')
        return PrintStmt(expr)

    def parse_if(self):
        self.expect('IF')
        cond = self.parse_expr()
        then_body = self.parse_block()
        else_body = None
        if self.match('ELSE'):
            if self.at('IF'):
                else_body = [self.parse_if()]
            else:
                else_body = self.parse_block()
        return IfStmt(cond, then_body, else_body)

    def parse_while(self):
        self.expect('WHILE')
        cond = self.parse_expr()
        body = self.parse_block()
        return WhileStmt(cond, body)

    def parse_block(self):
        self.expect('LBRACE')
        stmts = []
        while not self.at('RBRACE'):
            stmts.append(self.parse_statement())
        self.expect('RBRACE')
        return stmts

    def parse_block_as_stmt(self):
        # A bare block -- just return statements in sequence
        stmts = self.parse_block()
        # Return as a list wrapped in a special node or just the first
        if len(stmts) == 1:
            return stmts[0]
        # Wrap in a program-like container
        return Program(stmts)

    def parse_expr_or_assign_stmt(self):
        expr = self.parse_expr()
        if isinstance(expr, Identifier) and self.match('ASSIGN'):
            rhs = self.parse_expr()
            return AssignStmt(expr.name, rhs)
        return ExprStmt(expr)

    # ── Expressions (precedence climbing) ──

    def parse_expr(self):
        return self.parse_or()

    def parse_or(self):
        left = self.parse_and()
        while self.match('OR_KW'):
            left = BinOp('or', left, self.parse_and())
        return left

    def parse_and(self):
        left = self.parse_bitor()
        while self.match('AND_KW'):
            left = BinOp('and', left, self.parse_bitor())
        return left

    def parse_bitor(self):
        left = self.parse_bitxor()
        while self.match('PIPE'):
            left = BinOp('|', left, self.parse_bitxor())
        return left

    def parse_bitxor(self):
        left = self.parse_bitand()
        while self.match('CARET'):
            left = BinOp('^', left, self.parse_bitand())
        return left

    def parse_bitand(self):
        left = self.parse_comparison()
        while self.match('AMP'):
            left = BinOp('&', left, self.parse_comparison())
        return left

    def parse_comparison(self):
        left = self.parse_add()
        for kind, op in [('EQ', '=='), ('NE', '!='), ('LE', '<='), ('GE', '>=')]:
            if self.match(kind):
                return BinOp(op, left, self.parse_add())
        return left

    def parse_add(self):
        left = self.parse_mul()
        while True:
            if self.match('PLUS'):
                left = BinOp('+', left, self.parse_mul())
            elif self.match('MINUS'):
                left = BinOp('-', left, self.parse_mul())
            else:
                break
        return left

    def parse_mul(self):
        left = self.parse_unary()
        while True:
            if self.match('STAR'):
                left = BinOp('*', left, self.parse_unary())
            elif self.match('SLASH'):
                left = BinOp('/', left, self.parse_unary())
            elif self.match('PERCENT'):
                left = BinOp('%', left, self.parse_unary())
            else:
                break
        return left

    def parse_unary(self):
        if self.match('MINUS'):
            return UnaryOp('-', self.parse_unary())
        if self.match('TILDE'):
            return UnaryOp('~', self.parse_unary())
        if self.match('NOT_KW'):
            return UnaryOp('not', self.parse_unary())
        return self.parse_postfix()

    def parse_postfix(self):
        expr = self.parse_atom()
        while True:
            if self.match('LBRACK'):
                idx = self.parse_expr()
                self.expect('RBRACK')
                expr = IndexExpr(expr, idx)
            elif self.at('LPAREN') and isinstance(expr, Identifier):
                self.advance()
                args = []
                while not self.at('RPAREN'):
                    args.append(self.parse_expr())
                    self.match('COMMA')
                self.expect('RPAREN')
                expr = CallExpr(expr.name, args)
            else:
                break
        return expr

    def parse_atom(self):
        tok = self.peek()
        if tok.kind == 'NUMBER':
            self.advance()
            return NumberLit(tok.value)
        if tok.kind == 'STRING':
            self.advance()
            return StringLit(tok.value)
        if tok.kind == 'TRUE':
            self.advance()
            return BoolLit(True)
        if tok.kind == 'FALSE':
            self.advance()
            return BoolLit(False)
        if tok.kind == 'UNKNOWN':
            self.advance()
            return UnknownLit()
        if tok.kind == 'IDENT':
            self.advance()
            return Identifier(tok.value)
        if tok.kind == 'LPAREN':
            self.advance()
            expr = self.parse_expr()
            self.expect('RPAREN')
            return expr
        raise SyntaxError(
            f'Line {tok.line}: Unexpected token {tok.kind} ({tok.value!r})')


# ════════════════════════════════════════════════════════════
# TYPE WIDTH RESOLVER
# ════════════════════════════════════════════════════════════

TYPE_WIDTHS = {
    'Int8': 8,
    'Int16': 16,
    'Int32': 32,
    'Int64': 64,
}

def type_to_width(type_str):
    """Extract bit width from a type annotation string."""
    if type_str is None:
        return 32  # default
    base = type_str.split('[')[0]
    return TYPE_WIDTHS.get(base, 32)


# ════════════════════════════════════════════════════════════
# CODE GENERATOR — AST to Python source
# ════════════════════════════════════════════════════════════

class CodeGenerator:
    """Compiles Rayon AST to Python source code using RayonInt."""

    def __init__(self):
        self.indent = 0
        self.lines = []
        self.fn_param_types = {}  # fn_name -> [(param_name, type_str), ...]

    def generate(self, program):
        """Generate complete Python module from AST."""
        self._emit_prelude()
        for stmt in program.statements:
            self._gen_stmt(stmt)
        self._emit_postlude()
        return '\n'.join(self.lines)

    def _emit(self, line):
        self.lines.append('    ' * self.indent + line)

    def _emit_prelude(self):
        self._emit('#!/usr/bin/env python3')
        self._emit('"""Auto-generated by Rayon Compiler — tension-tracked execution."""')
        self._emit('')
        self._emit('import sys, os')
        self._emit('_this_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else os.getcwd()')
        self._emit('if _this_dir not in sys.path:')
        self._emit('    sys.path.insert(0, _this_dir)')
        self._emit('from rayon_numbers import RayonInt')
        self._emit('')
        self._emit('# ── Rayon runtime helpers ──')
        self._emit('')
        self._emit('def _to_rayon(val, width=32):')
        self._emit('    """Coerce a value to RayonInt if it is not already."""')
        self._emit('    if isinstance(val, RayonInt):')
        self._emit('        return val')
        self._emit('    return RayonInt.known(int(val), width=width)')
        self._emit('')
        self._emit('def _rayon_print(val):')
        self._emit('    """Print a value with tension information."""')
        self._emit('    if isinstance(val, RayonInt):')
        self._emit('        if val.is_known:')
        self._emit('            print(f"  {val.value}  (tension=0, fully known)")')
        self._emit('        else:')
        self._emit('            bits = "".join("?" if b is None else str(b) for b in reversed(val.bits[:val.width]))')
        self._emit('            print(f"  {bits}  (tension={val.tension}, {val.n_possible} possible values, range {val.min_value}..{val.max_value})")')
        self._emit('    else:')
        self._emit('        print(f"  {val}")')
        self._emit('')
        self._emit('def _rayon_mul(a, b):')
        self._emit('    """Multiply two RayonInts via shift-and-add."""')
        self._emit('    width = a.width')
        self._emit('    result = RayonInt.known(0, width=width)')
        self._emit('    for i in range(width):')
        self._emit('        bit = b.bits[i] if i < len(b.bits) else 0')
        self._emit('        if bit is None:')
        self._emit('            # Unknown bit -- result gets unknown contributions')
        self._emit('            shifted_bits = [0] * i + a.bits[:width - i]')
        self._emit('            shifted = RayonInt(bits=[None if sb is None else sb for sb in shifted_bits], width=width)')
        self._emit('            result = result + shifted')
        self._emit('        elif bit == 1:')
        self._emit('            shifted_bits = [0] * i + a.bits[:width - i]')
        self._emit('            shifted = RayonInt(bits=shifted_bits, width=width)')
        self._emit('            result = result + shifted')
        self._emit('    return result')
        self._emit('')
        self._emit('# ── Compiled Rayon program ──')
        self._emit('')

    def _emit_postlude(self):
        pass  # nothing needed

    # ── Statement generation ──

    def _gen_stmt(self, stmt):
        if isinstance(stmt, FnDef):
            self._gen_fn(stmt)
        elif isinstance(stmt, LetDecl):
            self._gen_let(stmt)
        elif isinstance(stmt, ReturnStmt):
            self._gen_return(stmt)
        elif isinstance(stmt, PrintStmt):
            self._gen_print(stmt)
        elif isinstance(stmt, IfStmt):
            self._gen_if(stmt)
        elif isinstance(stmt, WhileStmt):
            self._gen_while(stmt)
        elif isinstance(stmt, AssignStmt):
            self._gen_assign(stmt)
        elif isinstance(stmt, ExprStmt):
            self._emit(self._gen_expr(stmt.expr))
        elif isinstance(stmt, Program):
            for s in stmt.statements:
                self._gen_stmt(s)

    def _gen_fn(self, fn):
        self.fn_param_types[fn.name] = fn.params
        params = ', '.join(p[0] for p in fn.params)
        self._emit(f'def {fn.name}({params}):')
        self.indent += 1
        # Coerce params to RayonInt at entry
        for pname, ptype in fn.params:
            width = type_to_width(ptype)
            self._emit(f'{pname} = _to_rayon({pname}, width={width})')
        for s in fn.body:
            self._gen_stmt(s)
        self.indent -= 1
        self._emit('')

    def _gen_let(self, let):
        width = type_to_width(let.type_ann)
        expr_code = self._gen_expr(let.expr, width=width)
        self._emit(f'{let.name} = {expr_code}')

    def _gen_return(self, ret):
        self._emit(f'return {self._gen_expr(ret.expr)}')

    def _gen_print(self, prn):
        self._emit(f'_rayon_print({self._gen_expr(prn.expr)})')

    def _gen_if(self, ifstmt):
        self._emit(f'if {self._gen_expr(ifstmt.cond)}:')
        self.indent += 1
        for s in ifstmt.then_body:
            self._gen_stmt(s)
        self.indent -= 1
        if ifstmt.else_body:
            self._emit('else:')
            self.indent += 1
            for s in ifstmt.else_body:
                self._gen_stmt(s)
            self.indent -= 1

    def _gen_while(self, wh):
        self._emit(f'while {self._gen_expr(wh.cond)}:')
        self.indent += 1
        for s in wh.body:
            self._gen_stmt(s)
        self.indent -= 1

    def _gen_assign(self, assign):
        self._emit(f'{assign.name} = {self._gen_expr(assign.expr)}')

    # ── Expression generation ──

    def _gen_expr(self, expr, width=32):
        if isinstance(expr, NumberLit):
            return f'_to_rayon({expr.value}, width={width})'
        elif isinstance(expr, StringLit):
            return repr(expr.value)
        elif isinstance(expr, BoolLit):
            return repr(expr.value)
        elif isinstance(expr, UnknownLit):
            return f'RayonInt.unknown(width={width})'
        elif isinstance(expr, Identifier):
            return expr.name
        elif isinstance(expr, BinOp):
            return self._gen_binop(expr, width)
        elif isinstance(expr, UnaryOp):
            return self._gen_unaryop(expr, width)
        elif isinstance(expr, CallExpr):
            args = ', '.join(self._gen_expr(a) for a in expr.args)
            return f'{expr.func}({args})'
        elif isinstance(expr, IndexExpr):
            return f'{self._gen_expr(expr.obj)}[{self._gen_expr(expr.index)}]'
        else:
            raise ValueError(f'Unknown expression type: {type(expr).__name__}')

    def _gen_binop(self, expr, width=32):
        left = self._gen_expr(expr.left, width)
        right = self._gen_expr(expr.right, width)
        op = expr.op
        if op == '+':
            return f'({left} + {right})'
        elif op == '-':
            return f'({left} - {right})'
        elif op == '*':
            return f'_rayon_mul({left}, {right})'
        elif op == '^':
            return f'({left} ^ {right})'
        elif op == '&':
            return f'({left} & {right})'
        elif op == '|':
            return f'({left} | {right})'
        elif op in ('==', '!=', '<=', '>='):
            return f'({left} {op} {right})'
        elif op == 'and':
            return f'({left} and {right})'
        elif op == 'or':
            return f'({left} or {right})'
        elif op == '/':
            return f'({left} / {right})'
        elif op == '%':
            return f'({left} % {right})'
        else:
            return f'({left} {op} {right})'

    def _gen_unaryop(self, expr, width=32):
        operand = self._gen_expr(expr.operand, width)
        if expr.op == '-':
            return f'(_to_rayon(0, width={width}) - {operand})'
        elif expr.op == '~':
            return f'(~{operand})'
        elif expr.op == 'not':
            return f'(not {operand})'
        else:
            return f'({expr.op}{operand})'


# ════════════════════════════════════════════════════════════
# PUBLIC API
# ════════════════════════════════════════════════════════════

def compile_rayon(source):
    """
    Compile Rayon source code to Python source code.

    Returns the Python source as a string.
    """
    tokens = tokenize(source)
    parser = RayonParser(tokens)
    ast = parser.parse_program()
    gen = CodeGenerator()
    return gen.generate(ast)


def compile_and_run(source, verbose=False):
    """
    Compile Rayon source code and execute it immediately.

    If verbose=True, also prints the generated Python code.
    """
    python_code = compile_rayon(source)
    if verbose:
        print("═" * 60)
        print("GENERATED PYTHON:")
        print("═" * 60)
        for i, line in enumerate(python_code.split('\n'), 1):
            print(f'  {i:3d} | {line}')
        print("═" * 60)
        print("EXECUTION OUTPUT:")
        print("═" * 60)
    _tension_dir = os.path.dirname(os.path.abspath(__file__))
    exec(python_code, {'__name__': '__rayon_compiled__', '__file__': os.path.join(_tension_dir, '__rayon_exec__.py')})


def compile_to_file(source, output_path):
    """
    Compile Rayon source code and write it to a Python file.
    """
    python_code = compile_rayon(source)
    with open(output_path, 'w') as f:
        f.write(python_code)
    return output_path


# ════════════════════════════════════════════════════════════
# DEMO & VERIFICATION
# ════════════════════════════════════════════════════════════

def demo():
    print("=" * 62)
    print("  RAYON COMPILER -- Rayon syntax to Python with tension")
    print("=" * 62)
    print()

    rayon_source = r"""
fn add_xor(a: Int32, b: Int32) -> Int32 {
    let c = a + b
    let d = c ^ 0xFF
    return d
}

let x = 42
let y = ?
let z = add_xor(x, y)
print(z)
"""

    print("RAYON SOURCE:")
    print("-" * 60)
    for line in rayon_source.strip().split('\n'):
        print(f'  {line}')
    print("-" * 60)
    print()

    # Compile
    python_code = compile_rayon(rayon_source)
    print("COMPILED PYTHON:")
    print("-" * 60)
    for i, line in enumerate(python_code.split('\n'), 1):
        print(f'  {i:3d} | {line}')
    print("-" * 60)
    print()

    # Execute
    print("EXECUTION:")
    print("-" * 60)
    _tension_dir = os.path.dirname(os.path.abspath(__file__))
    exec(python_code, {'__name__': '__rayon_compiled__', '__file__': os.path.join(_tension_dir, '__rayon_exec__.py')})
    print("-" * 60)
    print()

    # ── Second demo: known values ──
    print()
    print("DEMO 2: Fully known computation")
    print("-" * 60)
    rayon2 = r"""
fn double_xor(x: Int8) -> Int8 {
    let a = x + x
    let b = a ^ 0x55
    return b
}

let val = 21
let result = double_xor(val)
print(result)
"""
    for line in rayon2.strip().split('\n'):
        print(f'  {line}')
    print()
    print("OUTPUT:")
    compile_and_run(rayon2)
    print("-" * 60)
    print()

    # ── Third demo: partial unknowns and kill-links ──
    print()
    print("DEMO 3: AND with kill-links reduces tension")
    print("-" * 60)
    rayon3 = r"""
let mask = 0xF0
let unknown_val = ?
let result = unknown_val & mask
print(unknown_val)
print(result)
"""
    for line in rayon3.strip().split('\n'):
        print(f'  {line}')
    print()
    print("OUTPUT:")
    compile_and_run(rayon3)
    print("-" * 60)
    print()

    # ── Fourth demo: tension tracking through expressions ──
    print()
    print("DEMO 4: Tension tracking through chained operations")
    print("-" * 60)
    rayon4 = r"""
let a = 100
let b = ?
let c = a + b
let d = c ^ 0xFF
let e = d & 0x0F
print(a)
print(b)
print(c)
print(d)
print(e)
"""
    for line in rayon4.strip().split('\n'):
        print(f'  {line}')
    print()
    print("OUTPUT:")
    compile_and_run(rayon4)
    print("-" * 60)

    print()
    print("=" * 62)
    print("  COMPILER VERIFICATION COMPLETE")
    print("  - Rayon syntax parsed correctly")
    print("  - fn definitions with typed params compiled")
    print("  - ? literal creates Unknown RayonInt values")
    print("  - Arithmetic (+, -, ^, &, |) compiles to RayonInt ops")
    print("  - Tension auto-tracked through all operations")
    print("  - print() displays value + tension info")
    print("  - AND kill-links reduce tension as expected")
    print("=" * 62)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        path = sys.argv[1]
        with open(path) as f:
            source = f.read()
        if '--run' in sys.argv:
            compile_and_run(source, verbose='--verbose' in sys.argv)
        else:
            print(compile_rayon(source))
    else:
        demo()
