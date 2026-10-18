"""The ``mpt`` macro: pretty-print math expressions in reports.

``mpt`` renders an expression in three phases:

  1. **Source.** The expression *exactly as written at the use site*, taken
     verbatim from the source file (no reformatting, no added or removed
     spaces or parentheses).

  2. **Substitution.** The same expression with each local variable replaced
     *in place* by its current value. Nothing is evaluated or simplified here;
     only names are textually substituted, and their order is preserved
     exactly.

  3. **Evaluation.** The expression itself is evaluated once, its value is
     printed (with the ``name := `` prefix in the assignment form, matching
     phases 1 and 2), and that value becomes the value of the whole macro call
     (so it can be assigned or printed).

Import the macro as a macro-import; the ``macros`` marker is mandatory for
mcpyrate::

    from mathprint_main import macros, mpt

For plain ``python myscript.py`` (no ``macropython``) use the one-line bootstrap
instead, which also provides the macro without the ``macros`` marker::

    from mathprint import mpt

The macro works both as a plain expression and as an assignment::

    mpt[(a + z) * 2]

    mpt[x := (a + z) * 2]

The assignment form additionally binds the name and uses it as a prefix.

Usage::

    y = 5
    z = 10
    mpt[x := y * 7 + z]

prints::

    x := y * 7 + z
    x := 5 * 7 + 10
    x := 45

and assigns ``x = 45``.

**Order guarantee (phase 2).** The substituted line is built directly from the
exact source substring of the expression. Each *loaded* name occurrence is
replaced, in place, by a positional ``str.format`` placeholder, and the
occurrences are collected in source order (by their byte offset in the file),
then sorted by that offset. The placeholders are filled, positionally, with the
values of those very same occurrences. Because the i-th placeholder is by
construction the i-th source occurrence, the i-th value necessarily lands in the
i-th slot: the order of variables in the output is identical to the order in
which they appear in the source -- regardless of the surrounding operators
(including comparisons) and regardless of what the values are (numbers, sympy
symbols, ...). No evaluation, arithmetic, or symbolic simplification happens in
this phase, so nothing can move around. Store-context names (e.g. a
comprehension target, or the target of an assignment ``mpt[name := ...]``) are
not substituted, because they are being bound, not read.

**Modules, functions and classes are not expanded (phase 2).** If a name refers
to a module, function, method, built-in or class, it is left as written:
``mpt[math.floor(y)]`` prints ``math.floor(5)`` (not ``<module 'math' …>.floor(5)``),
``mpt[f(y)]`` prints ``f(5)`` (not ``<function f at 0x…>(5)``), and
``mpt[int(y)]`` prints ``int(5)`` (not ``<class 'int'>(5)``).
"""

import ast
import copy
import importlib.util
import types

from mcpyrate.quotes import macros, q, a, u, h


# Values whose ``str`` repr is noise (``<function f at 0x…>``, ``<class 'int'>``,
# ``<module 'math' …>``). For these, phase 2 keeps the *name* used in the source
# instead of substituting the value's repr.
_OPAQUE_TYPES = (
    types.ModuleType,          # modules
    types.FunctionType,        # def / lambda
    types.BuiltinFunctionType,  # len, math.floor (builtin_function_or_method)
    types.MethodType,          # bound method of a Python object
    type,                      # classes: int, str, MyClass
)


def _render(name, value):
    """Render one substituted value in phase 2.

    Modules, functions, methods, built-ins and classes are *not* expanded: they
    keep the name used in the source (so ``math.sqrt`` stays ``math.sqrt``, ``f``
    stays ``f``, ``int`` stays ``int``), instead of dumping an opaque ``<…>``
    repr. Everything else is substituted by ``str`` of its current value.
    """
    if isinstance(value, _OPAQUE_TYPES):
        return name
    return str(value)


def _print_value(prefix, value):
    """Phase 3 helper: print the computed value and return it unchanged.

    ``prefix`` is the ``name := `` prefix for the assignment form (empty for a
    bare expression), so the value line matches phases 1 and 2 (e.g.
    ``g_m_diff := 12``). Used instead of ``(print(expr), expr)`` so that the
    expression is evaluated exactly once while still being printed.
    """
    print(f"{prefix}{value}")
    return value


def _rendered_arg(name_node):
    """Build an AST for ``_render(<name>, <name value>)``, hygienically bound."""
    return q[h[_render](u[name_node.id], a[name_node])]


class _LoadNameCollector(ast.NodeVisitor):
    """Collect loaded `Name` nodes in AST (source) order."""

    def __init__(self):
        self.names = []

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.names.append(node)


class _NamePlaceholderer(ast.NodeTransformer):
    """Replace each loaded `Name` with a positional placeholder.

    Used only as a fallback when the source text is unavailable. Names are
    numbered in AST-traversal order, which for all practical expressions is
    source order. Store-context names are left untouched.
    """

    def __init__(self):
        self.names = []

    def visit_Name(self, node):
        if not isinstance(node.ctx, ast.Load):
            return node
        index = len(self.names)
        self.names.append(node)
        placeholder = ast.Name(id=f"__mpt_value_{index}__", ctx=ast.Load())
        return ast.copy_location(placeholder, node)


def _name_template(value):
    """Fallback: ``(template, names)`` from an unparsed expression.

    `template` is a `str.format`-style template where every variable is a
    ``{}`` placeholder; `names` is the list of `Name` nodes, in the order the
    placeholders appear.
    """
    placeholderer = _NamePlaceholderer()
    transformed = placeholderer.visit(copy.deepcopy(value))

    template = ast.unparse(transformed)
    template = _escape_braces(template)
    for index in range(len(placeholderer.names)):
        template = template.replace(f"__mpt_value_{index}__", "{}")
    return template, placeholderer.names


def _escape_braces(text):
    """Escape literal braces so `str.format` treats them as literal text."""
    return text.replace("{", "{{").replace("}", "}}")


_SOURCE_CACHE = {}

# Set by the Jupyter extension (`mathprint_main.jupyter`), where the code being
# expanded has no backing source file; see `_exact_source`.
_SOURCE_OVERRIDE = None


def _read_source(filename):
    """Read and decode the source file being compiled, or return `None`."""
    if filename in _SOURCE_CACHE:
        return _SOURCE_CACHE[filename]
    try:
        with open(filename, "rb") as f:
            source = importlib.util.decode_source(f.read())
    except (OSError, SyntaxError, ValueError):
        source = None
    _SOURCE_CACHE[filename] = source
    return source


def _splitlines_no_ff(source):
    """Split lines, dropping form feeds, exactly like `ast.get_source_segment`."""
    idx = source.find("\f")
    while idx != -1:
        source = source[:idx] + source[idx + 1:]
        idx = source.find("\f", idx)
    return source.splitlines(True)


def _offset(source, lineno, col_offset):
    """Absolute UTF-8 byte offset of `(lineno, col_offset)` in `source`."""
    lines = _splitlines_no_ff(source)
    base = sum(len(line.encode("utf-8")) for line in lines[:lineno - 1])
    return base + col_offset


def _exact_template(segment, node, source):
    """Build ``(template, names)`` from the exact source `segment` of `node`.

    Every loaded name occurrence inside `segment` becomes a positional ``{}``
    placeholder; `names` lists those occurrences in source order.
    """
    collector = _LoadNameCollector()
    collector.visit(node)

    start = _offset(source, node.lineno, node.col_offset)
    segment_bytes = segment.encode("utf-8")

    spans = []
    for name in collector.names:
        s = _offset(source, name.lineno, name.col_offset) - start
        e = _offset(source, name.end_lineno, name.end_col_offset) - start
        spans.append((s, e, name))
    spans.sort(key=lambda span: span[0])

    pieces = []
    names = []
    cursor = 0
    for s, e, name in spans:
        if s < cursor:  # pragma: no cover - impossible for well-formed expressions
            return None, []
        pieces.append(_escape_braces(segment_bytes[cursor:s].decode("utf-8")))
        pieces.append("{}")
        names.append(name)
        cursor = e
    pieces.append(_escape_braces(segment_bytes[cursor:].decode("utf-8")))
    return "".join(pieces), names


def mpt(expr, **kw):
    expander = kw.get("expander")

    # Assignment form `mpt[name := expression]`; anything else (including a bare
    # expression such as `mpt[(a + z) * 2]`) is printed without a name prefix.
    if type(expr) is ast.NamedExpr and type(expr.target) is ast.Name:
        value = expr.value
        prefix = f"{expr.target.id} := "
        fallback_symbolic = f"{prefix}{ast.unparse(value)}"
    else:
        value = expr
        prefix = ""
        fallback_symbolic = ast.unparse(expr)

    filename = getattr(expander, "filename", None)
    source = _read_source(filename) if filename else None
    if source is None:
        source = _SOURCE_OVERRIDE

    # Phase 1: the original expression, exactly as written at the use site.
    # Phase 2: the same source with each variable substituted in place.
    symbolic = None
    numeric_template = None
    names = []
    if source is not None:
        try:
            symbolic = ast.get_source_segment(source, expr)
        except Exception:
            symbolic = None
        if symbolic is not None:
            try:
                numeric_template, names = _exact_template(symbolic, expr, source)
            except Exception:
                numeric_template = None

    if symbolic is None:
        symbolic = fallback_symbolic
    if numeric_template is None:
        template, names = _name_template(value)
        numeric_template = prefix + template

    numeric = ast.Call(func=ast.Attribute(
            value=ast.Constant(numeric_template),
            attr="format",
            ctx=ast.Load()
        ),
        args=[_rendered_arg(name) for name in names],
        keywords=[]
    )

    # Phase 3: runs left to right: print source line, print substituted line,
    # then evaluate the original expression once and print its value (with the
    # `name := ` prefix in the assignment form, so the value line matches phases
    # 1 and 2), yielding the value. `_print_value` prints and returns it, so the
    # expression is not evaluated twice.
    return q[(
            print(u[symbolic]),
            print(a[numeric]),
            h[_print_value](u[prefix], a[expr])
        )[-1]
    ]
