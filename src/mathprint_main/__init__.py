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
``macropython``, and in Jupyter (via the ``mathprint_jupyter`` extension).

The macro works both as a plain expression and as an assignment::

    mpt[(a + z) * 2]

    mpt[x := (a + z) * 2]

The assignment form additionally binds the name and uses it as a prefix.

Several expressions can be sequenced in one call, one per comma::

    mpt[
        L_diff := (L_11 := (L_12 := 2*L_min)),
        g_m_diff := (g_m_11 := (g_m_12 := GBW * 2*pi * C_C)),
    ]

Each item is printed exactly as if it had its own ``mpt[...]`` call, in order,
and the whole call yields a tuple of the item values.

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

**Display precision (opt-in, per file).** Calling ``mpt.precision(n)`` rounds the
numbers *shown* by phases 2 and 3 to ``n`` significant digits (``3.123123412``
prints as ``3.123`` for ``n=4``). This affects only the display: the expression
is still evaluated, and the macro's return value is unrounded. ``mpt.precision()``
(or ``mpt.precision(None)``) restores the default.

**How the code is laid out.** The work is a short pipeline of single-purpose
classes, in reading order:

  * :class:`Numbers` -- round a plain number to ``n`` significant digits.
  * :class:`Latex` -- render one line as LaTeX (optional, imported lazily).
  * :class:`Printer` -- show the three lines; owns the per-scope settings
    (plain text vs LaTeX, full vs fixed precision) and the phase-2 rule that
    modules/functions/classes keep their names.
  * :class:`Source` -- the exact text of the expression being printed.
  * :class:`Expander` -- the macro itself: turn one ``mpt[...]`` into the
    three-phase form, and sequence several expressions.

``mpt`` is a one-line wrapper over :class:`Expander`. The expanded code calls
back into the class methods: ``Printer.render``, ``Printer.line``,
``Printer.show_value`` (the three phases) and ``Expander.collect`` (the
multi-expression form).
"""

import ast
import decimal
import importlib.util
import os
import sys
import types
from fractions import Fraction

from mcpyrate.core import MacroExpansionError
from mcpyrate.quotes import macros, q, a, u, h


# ---------------------------------------------------------------------------
# Numbers: display formatting of plain numbers
# ---------------------------------------------------------------------------

class Numbers:
    """Round plain numbers to ``n`` significant digits for display.

    Only plain numbers are handled (``int``, ``float``, ``complex``,
    ``Decimal``, ``Fraction`` and subclasses such as numpy floats); everything
    else -- including ``bool`` and symbolic (e.g. sympy) objects -- returns
    ``None``, so the caller falls back to ``str``. Trailing zeros are dropped
    (``23.00134`` -> ``"23"``, ``2.50`` -> ``"2.5"``); there is no padding.
    """

    @staticmethod
    def format(value, digits):
        """`value` with `digits` significant digits, or `None` if not a number."""
        if isinstance(value, bool):
            return None
        if not isinstance(value, (int, float, complex, decimal.Decimal, Fraction)):
            return None
        if isinstance(value, complex):
            real = Numbers._real(value.real, digits)
            imag = Numbers._real(abs(value.imag), digits)
            if value.imag == 0:
                return real
            return f"{real}{'-' if value.imag < 0 else '+'}{imag}j"
        return Numbers._real(value, digits)

    @staticmethod
    def _real(value, digits):
        """Format a real number with `digits` significant digits."""
        with decimal.localcontext() as ctx:
            ctx.prec = max(28, digits + 10)
            number = Numbers._to_decimal(value)
            if number == 0:
                return "0"
            exponent = number.adjusted()
            quantum = decimal.Decimal(1).scaleb(exponent - digits + 1)
            try:
                rounded = number.quantize(quantum, rounding=decimal.ROUND_HALF_EVEN)
            except decimal.InvalidOperation:
                return str(value)
            text = format(rounded, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text

    @staticmethod
    def _to_decimal(value):
        """Lossless-ish conversion of a plain number to `decimal.Decimal`."""
        if isinstance(value, decimal.Decimal):
            return value
        if isinstance(value, Fraction):
            return decimal.Decimal(value.numerator) / decimal.Decimal(value.denominator)
        if isinstance(value, int):
            return decimal.Decimal(value)
        # float subclass (e.g. numpy.float64): `float` normalizes repr quirks.
        return decimal.Decimal(repr(float(value)))


# ---------------------------------------------------------------------------
# LaTeX: optional rendering of one line
# ---------------------------------------------------------------------------

class Latex:
    """Render one printed line as LaTeX, ``display(Latex(py2tex(text)))``.

    Both ``pytexit`` and ``IPython`` are imported lazily, so the default
    plain-text path never touches them.
    """

    @staticmethod
    def show(text):
        """Show `text` as LaTeX, or print it if `py2tex` cannot convert it.

        Some operators (e.g. ``and``) are not convertible; then the line is
        printed, so one expression cannot break the run.
        """
        from IPython.display import Latex as _IpythonLatex, display

        from pytexit import py2tex  # pyright: ignore[reportMissingModuleSource]

        Latex._patch_pytexit()
        try:
            tex = py2tex(
                Latex._to_input(text),
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
        display(_IpythonLatex(tex))

    @staticmethod
    def _to_input(text):
        """Turn a printed line into a Python expression ``py2tex`` can parse.

        The assignment prefix uses ``:=``; ``py2tex`` expects a comparison, so
        it is rewritten to ``==`` (rendered as ``=``).
        """
        return text.replace(":=", "==")

    @staticmethod
    def _patch_pytexit():
        """Teach ``pytexit`` to render numeric literals on Python >= 3.8.

        ``pytexit`` 0.4.0 only defines ``visit_Num``; since Python 3.8 numeric
        literals parse to ``ast.Constant``, which falls through to
        ``generic_visit`` and raises. Add the missing visitor (a no-op on fixed
        versions). Only invoked in LaTeX mode, so the default plain-text path
        never touches ``pytexit``.
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


# ---------------------------------------------------------------------------
# Printer: the three lines, plain text or LaTeX, per scope
# ---------------------------------------------------------------------------

class Printer:
    """Show the three lines of an ``mpt`` call, per *scope*.

    A scope is a file (keyed by its absolute path), a notebook (``"<ipython>"``)
    or the "no file" case (:attr:`ANY_FILE`). Each scope independently picks:

    * the format -- plain text (default) or LaTeX (``mpt.latex()``), and
    * the display precision -- full, or ``n`` significant digits
      (``mpt.precision(n)``).

    So the two settings never leak between files. The settings live in
    :attr:`latex_scopes` and :attr:`precision_scopes`; the ``key_of*`` methods
    map a file or a live module to a scope key; and :meth:`render`,
    :meth:`line` and :meth:`show_value` are the runtime hooks the expanded code
    calls (see :class:`Expander`).
    """

    #: Scope key meaning "every file" (used when no filename is known).
    ANY_FILE = "*"

    #: Scope keys that opted into LaTeX output (see ``mpt.latex()``).
    latex_scopes = set()

    #: Scope keys that set a display precision, mapped to significant digits.
    precision_scopes = {}

    #: Values whose ``str`` repr is noise (``<function f at 0x…>``,
    #: ``<class 'int'>``, ``<module 'math' …>``). For these, phase 2 keeps the
    #: *name* used in the source instead of substituting the value's repr.
    OPAQUE_TYPES = (
        types.ModuleType,           # modules
        types.FunctionType,         # def / lambda
        types.BuiltinFunctionType,  # len, math.floor (builtin_function_or_method)
        types.MethodType,           # bound method of a Python object
        type,                       # classes: int, str, MyClass
    )

    # --- scope keys ---------------------------------------------------------

    @classmethod
    def key_of(cls, filename):
        """Map a source `filename` to a scope key."""
        if not filename:
            return cls.ANY_FILE
        if filename.startswith("<") and filename.endswith(">"):
            return filename  # virtual name such as "<ipython>", not a real path
        return os.path.abspath(filename)

    @classmethod
    def key_of_globals(cls, globals_):
        """Scope key for a live module/cell's globals (backs the switches)."""
        if not globals_:
            return cls.ANY_FILE
        path = globals_.get("__file__")
        if path:
            return cls.key_of(path)
        if "get_ipython" in globals_:
            return "<ipython>"
        return cls.ANY_FILE

    # --- the two display switches (back `mpt.latex` / `mpt.precision`) ------

    @classmethod
    def set_latex(cls, key, enabled=True):
        """Enable (or disable) LaTeX output for `key`; return `key`."""
        if enabled:
            cls.latex_scopes.add(key)
        else:
            cls.latex_scopes.discard(key)
        return key

    @classmethod
    def set_precision(cls, key, digits=None):
        """Set `digits` displayed significant digits for `key` (``None`` resets)."""
        if digits is None:
            cls.precision_scopes.pop(key, None)
        else:
            digits = int(digits)
            if digits < 1:
                raise ValueError("mpt.precision needs a positive number of significant digits")
            cls.precision_scopes[key] = digits
        return key

    @classmethod
    def latex_on(cls, key):
        """Whether `key` (or every file, via ``ANY_FILE``) uses LaTeX output."""
        return cls.ANY_FILE in cls.latex_scopes or key in cls.latex_scopes

    @classmethod
    def precision_of(cls, key):
        """Significant digits to show for `key`, or ``None`` for the default."""
        return cls.precision_scopes.get(key)

    # --- the three runtime hooks (called by the expanded code) --------------

    @classmethod
    def render(cls, key, name, value):
        """Phase 2: the text that replaces one name occurrence.

        Modules, functions, methods, built-ins and classes are *not* expanded:
        they keep the name used in the source (so ``math.sqrt`` stays
        ``math.sqrt``, ``f`` stays ``f``, ``int`` stays ``int``) instead of
        dumping an opaque ``<…>`` repr. Everything else is substituted by
        ``str`` of its value, except plain numbers in a scope that opted into
        ``mpt.precision(n)``: those are shown rounded to ``n`` significant
        digits.
        """
        if isinstance(value, cls.OPAQUE_TYPES):
            return name
        shown = cls.number(key, value)
        return str(value) if shown is None else shown

    @classmethod
    def line(cls, key, text):
        """Phase 1/2: show one source/substitution line."""
        if cls.latex_on(key):
            Latex.show(text)
        else:
            print(text)

    @classmethod
    def show_value(cls, key, prefix, value):
        """Phase 3: show the value line (with the assignment prefix) and return it.

        Used instead of ``(print(value), value)`` so the expression is evaluated
        exactly once while still being shown. ``prefix`` is the ``name := ``
        prefix of the assignment form (empty for a bare expression), so the
        value line matches phases 1 and 2.
        """
        shown = cls.number(key, value)
        cls.line(key, f"{prefix}{value if shown is None else shown}")
        return value

    @classmethod
    def number(cls, key, value):
        """`value` rounded to the scope's precision, or ``None`` (default: ``str``)."""
        digits = cls.precision_of(key)
        if digits is None:
            return None
        return Numbers.format(value, digits)


# ---------------------------------------------------------------------------
# Source: the exact text an expression was written in
# ---------------------------------------------------------------------------

class Source:
    """The source text an expression was written in (a file, or a notebook cell).

    Phase 1 prints the expression verbatim, so the text is required.
    :meth:`segment` raises if it is missing (plain REPL, ``python -c``,
    ``exec``) or if the expression cannot be located -- rather than printing
    something subtly different from what the user wrote.
    """

    #: Set by the Jupyter extension, where a cell has no backing file.
    override = None

    _cache = {}

    @classmethod
    def read(cls, filename):
        """Read and decode `filename`, cached; ``None`` if it cannot be read."""
        if filename in cls._cache:
            return cls._cache[filename]
        try:
            with open(filename, "rb") as f:
                text = importlib.util.decode_source(f.read())
        except (OSError, SyntaxError, ValueError):
            text = None
        cls._cache[filename] = text
        return text

    def __init__(self, text):
        self.text = text

    def segment(self, node):
        """The exact source text of `node` (phase 1), or raise."""
        if self.text is None:
            raise MacroExpansionError(
                "mpt needs the source file to print the expression verbatim, but this "
                "context has none (plain REPL, `python -c` and `exec` are not supported)"
            )
        segment = ast.get_source_segment(self.text, node)
        if segment is None:
            raise MacroExpansionError("mpt could not find the expression in the source text")
        return segment

    def template(self, segment, node):
        """Build ``(template, names)`` from the exact source `segment` of `node`.

        Every loaded name occurrence inside `segment` becomes a positional
        ``{}`` placeholder; `names` lists those occurrences in source order.
        """
        collector = self._NameCollector()
        collector.visit(node)

        start = self._offset(node.lineno, node.col_offset)
        segment_bytes = segment.encode("utf-8")

        spans = []
        for name in collector.names:
            s = self._offset(name.lineno, name.col_offset) - start
            e = self._offset(name.end_lineno, name.end_col_offset) - start
            spans.append((s, e, name))
        spans.sort(key=lambda span: span[0])

        pieces = []
        names = []
        cursor = 0
        for s, e, name in spans:
            if s < cursor:  # pragma: no cover - impossible for well-formed expressions
                raise MacroExpansionError("mpt: overlapping names in the expression")
            pieces.append(self._escape_braces(segment_bytes[cursor:s].decode("utf-8")))
            pieces.append("{}")
            names.append(name)
            cursor = e
        pieces.append(self._escape_braces(segment_bytes[cursor:].decode("utf-8")))
        return "".join(pieces), names

    def _offset(self, lineno, col_offset):
        """Absolute UTF-8 byte offset of `(lineno, col_offset)` in the source."""
        lines = self._splitlines_no_ff(self.text)
        base = sum(len(line.encode("utf-8")) for line in lines[:lineno - 1])
        return base + col_offset

    @staticmethod
    def _splitlines_no_ff(text):
        """Split lines, dropping form feeds, exactly like `ast.get_source_segment`."""
        idx = text.find("\f")
        while idx != -1:
            text = text[:idx] + text[idx + 1:]
            idx = text.find("\f", idx)
        return text.splitlines(True)

    @staticmethod
    def _escape_braces(text):
        """Escape literal braces so `str.format` treats them as literal text."""
        return text.replace("{", "{{").replace("}", "}}")

    class _NameCollector(ast.NodeVisitor):
        """Collect loaded `Name` nodes in AST (source) order."""

        def __init__(self):
            self.names = []

        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Load):
                self.names.append(node)


# ---------------------------------------------------------------------------
# Expander: the macro itself
# ---------------------------------------------------------------------------

class Expander:
    """Turn one ``mpt[...]`` into its three-phase form.

    The three phases (see the module docstring) come from the exact source text
    (:class:`Source`) and the runtime hooks (:class:`Printer`). The
    multi-expression form ``mpt[a, b, ...]`` expands each item the same way and
    gathers their values into a tuple (see :meth:`collect`).
    """

    def __init__(self, expander):
        filename = getattr(expander, "filename", None)
        self.key = Printer.key_of(filename)
        text = Source.read(filename) if filename else None
        self.source = Source(text if text is not None else Source.override)

    def expand(self, expr):
        """Expand the subscript body: one expression, or a tuple of them."""
        if type(expr) is ast.Tuple:
            parts = [self._item(element) for element in expr.elts]
            call = ast.Call(func=q[h[Expander].collect], args=parts, keywords=[])
            return ast.fix_missing_locations(call)
        return self._item(expr)

    def _item(self, expr):
        """Expand a single item into its three-phase sequence."""
        key = self.key

        # Assignment form `mpt[name := expression]`; anything else (including a
        # bare expression such as `mpt[(a + z) * 2]`) has no name prefix.
        if type(expr) is ast.NamedExpr and type(expr.target) is ast.Name:
            prefix = f"{expr.target.id} := "
        else:
            prefix = ""

        # Phase 1: the expression exactly as written at the use site.
        symbolic = self.source.segment(expr)

        # Phase 2: that same text with each loaded name replaced, in place, by a
        # positional placeholder; `template` returns the placeholder string and
        # the name nodes those placeholders stand for.
        template, names = self.source.template(symbolic, expr)

        numeric = ast.Call(func=ast.Attribute(
                value=ast.Constant(template),
                attr="format",
                ctx=ast.Load()
            ),
            args=[self._rendered_arg(key, name) for name in names],
            keywords=[]
        )

        # Phase 3: runs left to right -- show the source line, show the
        # substituted line, then evaluate the original expression once and show
        # its value (with the `name := ` prefix in the assignment form, so the
        # value line matches phases 1 and 2), yielding the value.
        return q[(
                h[Printer].line(u[key], u[symbolic]),
                h[Printer].line(u[key], a[numeric]),
                h[Printer].show_value(u[key], u[prefix], a[expr])
            )[-1]
        ]

    @staticmethod
    def _rendered_arg(key, name_node):
        """AST for ``Printer.render(<key>, "<name>", <name>)``, hygienically bound."""
        return q[h[Printer].render(u[key], u[name_node.id], a[name_node])]

    @staticmethod
    def collect(*values):
        """Gather the values of a sequenced ``mpt[a, b, ...]`` into a tuple.

        Each item is evaluated (and shown) left to right, in the *caller's*
        scope, so a `name := ...` inside one binds the name there, just like a
        standalone ``mpt[name := ...]``.
        """
        return values


# ---------------------------------------------------------------------------
# The macro (its runtime interface is the `Printer` / `Expander` methods above)
# ---------------------------------------------------------------------------

def mpt(expr, **kw):
    """The ``mpt`` macro.

    A single ``mpt[expression]`` prints three lines and yields the value. The
    multi-expression form ``mpt[a, b, ...]`` prints each item exactly as if it
    had its own ``mpt[...]`` call -- in order -- and yields a tuple of the
    values, one per item.
    """
    return Expander(kw.get("expander")).expand(expr)


def _set_latex(enabled=True):
    """Back the ``mpt.latex()`` switch: enable/disable LaTeX for the calling file.

    ``mpt.latex()`` switches the file where the call appears (or the whole
    notebook, in Jupyter) to LaTeX output; ``mpt.latex(False)`` switches it back
    to plain text. Returns the scope key that was affected.
    """
    key = Printer.key_of_globals(sys._getframe(1).f_globals)
    return Printer.set_latex(key, enabled)


def _set_precision(digits=None):
    """Back the ``mpt.precision()`` switch: set displayed significant digits.

    ``mpt.precision(n)`` shows numbers in the calling file (or notebook) rounded
    to ``n`` significant digits; ``mpt.precision(None)`` restores the default
    (full ``str`` of the value). Returns the scope key that was affected.
    """
    key = Printer.key_of_globals(sys._getframe(1).f_globals)
    return Printer.set_precision(key, digits)


# `mpt.latex()` switches the calling file (or notebook) to LaTeX output, and
# `mpt.precision(n)` sets the displayed significant digits for it. They are
# attached here as attributes of the macro function so they are available
# wherever `mpt` itself is (e.g. `from mathprint import mpt` in a script or a
# Jupyter cell). (`setattr`, so the type checker, which sees `mpt` as a plain
# function, stays happy.)
setattr(mpt, "latex", _set_latex)
setattr(mpt, "precision", _set_precision)
