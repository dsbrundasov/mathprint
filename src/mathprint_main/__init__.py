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

Import the macro with the one-line bootstrap::

    from mathprint import mpt

That single import works under plain ``python myscript.py``, under
``macropython``, and in Jupyter (via the ``mathprint_jupyter`` extension); it
registers ``mpt`` as a global mcpyrate macro, so it also works in imported
modules.

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

**LaTeX output (opt-in, per file).** Output is plain text by default. Calling
``mpt.latex()`` switches *the file where the call appears* to LaTeX: each line is
converted with ``pytexit.py2tex`` and shown via ``IPython.display``, the
``display(Latex(py2tex(...)))`` recipe. ``mpt.latex(False)`` switches back. The
switch is per file (or per notebook in Jupyter), and nothing here imports
``pytexit`` unless LaTeX mode is actually used.
"""

import ast
import copy
import importlib.util
import os
import sys
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


# --- Output mode: plain text (default) or LaTeX ----------------------------

# `mpt` prints plain text by default. Calling `mpt.latex()` switches the *file
# where it is called* to LaTeX output: each printed line is converted with
# `pytexit.py2tex` and shown via `IPython.display`, the classic
# `display(Latex(py2tex(...)))` recipe.
#
# The set holds normalized scope keys (`_latex_key`). The virtual `_ANY_FILE`
# key switches *every* file (used when no source file can be determined, e.g. in
# `python -c`). Because keys are per-file, `mpt.latex()` in one module never
# leaks into other modules.
_ANY_FILE = "*"
_LATEX_FILES = set()


def _latex_key(filename):
    """Map a source `filename` to the scope key used by `_LATEX_FILES`."""
    if not filename:
        return _ANY_FILE
    if filename.startswith("<") and filename.endswith(">"):
        return filename  # virtual name such as "<ipython>", not a real path
    return os.path.abspath(filename)


def _latex_enabled(key):
    """Return whether `key` (or every file, via `_ANY_FILE`) uses LaTeX output."""
    return _ANY_FILE in _LATEX_FILES or key in _LATEX_FILES


def _latex_key_for_globals(globals_):
    """Scope key for a live module/cell's globals (backing ``mpt.latex()``)."""
    if not globals_:
        return _ANY_FILE
    path = globals_.get("__file__")
    if path:
        return _latex_key(path)
    if "get_ipython" in globals_:
        return "<ipython>"
    return _ANY_FILE


def _set_latex(enabled=True):
    """Back the ``mpt.latex()`` switch: enable/disable LaTeX for the calling file.

    ``mpt.latex()`` switches the file where the call appears (or the whole
    notebook, in Jupyter) to LaTeX output; ``mpt.latex(False)`` switches it back
    to plain text. Returns the scope key that was affected.
    """
    key = _latex_key_for_globals(sys._getframe(1).f_globals)
    if enabled:
        _LATEX_FILES.add(key)
    else:
        _LATEX_FILES.discard(key)
    return key


def _emit(key, text):
    """Phase 1/2 helper: print one line, or render it as LaTeX."""
    if _latex_enabled(key):
        _display_latex(text)
    else:
        print(text)


def _print_value(key, prefix, value):
    """Phase 3 helper: print the computed value and return it unchanged.

    ``prefix`` is the ``name := `` prefix for the assignment form (empty for a
    bare expression), so the value line matches phases 1 and 2 (e.g.
    ``g_m_diff := 12``). Used instead of ``(print(expr), expr)`` so that the
    expression is evaluated exactly once while still being printed. In LaTeX
    mode the line is rendered with ``_display_latex`` instead of printed.
    """
    line = f"{prefix}{value}"
    if _latex_enabled(key):
        _display_latex(line)
    else:
        print(line)
    return value


def _pytexit_input(text):
    """Turn a printed line into a Python expression ``py2tex`` can parse.

    The assignment prefix uses ``:=``; ``py2tex`` expects a comparison, so it is
    rewritten to ``==`` (rendered as ``=``).
    """
    return text.replace(":=", "==")


def _display_latex(text):
    """Render one line as LaTeX, like ``display(Latex(py2tex(text)))``.

    If ``py2tex`` cannot convert the line (some operators are unsupported), fall
    back to printing the plain text so a single expression cannot break the run.
    """
    from IPython.display import Latex, display

    from pytexit import py2tex  # pyright: ignore[reportMissingModuleSource]

    _fix_pytexit_constants()
    try:
        tex = py2tex(
            _pytexit_input(text),
            print_latex=False,
            print_formula=False,
            # `{\cdot}` (not bare `\cdot`): py2tex emits the multiplier with no
            # separator, so `\cdot` would glue onto the next token and KaTeX
            # would read e.g. `\cdotC_L` as the undefined `\cdotC`.
            tex_multiplier=r"{\cdot}",
            simplify_output=False,
            simplify_multipliers=False,
        )
    except Exception:
        print(text)
        return
    display(Latex(tex))


def _fix_pytexit_constants():
    """Teach ``pytexit`` to render numeric literals on Python >= 3.8.

    ``pytexit`` 0.4.0 only defines ``visit_Num``; since Python 3.8 numeric
    literals parse to ``ast.Constant``, which falls through to ``generic_visit``
    and raises. Add the missing visitor (a no-op on fixed versions). Only invoked
    in LaTeX mode, so the default plain-text path never touches ``pytexit``.
    """
    try:
        from pytexit.core import core  # pyright: ignore[reportMissingModuleSource]

        visitor = core.LatexVisitor
    except Exception:  # pragma: no cover - pytexit missing or restructured
        return
    if "visit_Constant" in visitor.__dict__:
        return

    def visit_Constant(self, n):
        value = n.value
        if isinstance(value, bool):
            return str(value)
        if self.simplify_fractions and any(value == k for k in core.fracs):
            return r"{0}\frac{{{1}}}{{{2}}}".format(*core.fracs[value])
        if self.looks_like_int(value):
            return "%d" % value
        return str(value)

    visitor.visit_Constant = visit_Constant


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
    # expression is not evaluated twice. When the file opts into LaTeX output
    # (`mpt.latex()`), `_emit`/`_print_value` render each line instead of
    # printing it; `key` is the compile-time source file the calls belong to.
    key = _latex_key(filename)
    return q[(
            h[_emit](u[key], u[symbolic]),
            h[_emit](u[key], a[numeric]),
            h[_print_value](u[key], u[prefix], a[expr])
        )[-1]
    ]


# `mpt.latex()` switches the calling file (or notebook) to LaTeX output. It is
# attached here as an attribute of the macro function so it is available
# wherever `mpt` itself is (e.g. `from mathprint import mpt` in a script or a
# Jupyter cell). `mpt.latex(False)` switches back to plain text. (`setattr`, so
# the type checker, which sees `mpt` as a plain function, stays happy.)
setattr(mpt, "latex", _set_latex)
