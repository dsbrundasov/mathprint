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
to a module, function, method, built-in, class or other callable, it is left as
written: ``mpt[math.floor(y)]`` prints ``math.floor(5)`` (not
``<module 'math' …>.floor(5)``), ``mpt[f(y)]`` prints ``f(5)`` (not
``<function f at 0x…>(5)``), and ``mpt[int(y)]`` prints ``int(5)`` (not
``<class 'int'>(5)``). A *dotted chain* rooted at a name is one occurrence and
is substituted as a unit: ``mpt[me.H.atomic_number]`` prints
``me.H.atomic_number`` then ``1``, since the chain's value is a plain number.

**Configuration (opt-in, per file).** Output is plain text, in a column, at full
precision by default. ``mpt.configure(...)`` changes these for *the file where the
call appears* (or the whole notebook in Jupyter), for every ``mpt[...]`` in that
scope::

    mpt.configure(out_order="line", out_format="latex", precision=4)

Every argument is optional; an omitted argument is left unchanged.
``out_order`` is ``"column"`` (the default: source, substitution and value on
separate lines) or ``"line"`` (one line, the name appearing once:
``x = 3 + y = 3 + 5 = 8``). ``out_format`` is ``"text"`` (the default) or
``"latex"``, in which case each line is converted with ``pytexit.py2tex`` and
shown via ``IPython.display``, the ``display(Latex(py2tex(...)))`` recipe;
nothing here imports ``pytexit`` unless LaTeX mode is actually used.
``precision=n`` rounds the numbers *shown* by phases 2 and 3 to ``n`` significant
digits (``3.123123412`` prints as ``3.123`` for ``n=4``) without affecting the
value; ``precision=None`` restores the default.
``multiple_assignment_reduce=True`` collapses a chain of assignments (e.g.
``ro1 := (ro := (ro_БФСС := 2230))``) to the value of the innermost assignment in
phase 2 (``ro1 := 2230``); phase 1 still shows the chain as written.
``mpt.configure(...)`` returns the scope key it changed.

**How the code is laid out.** The work is a short pipeline of single-purpose
classes, in reading order:

  * :class:`Numbers` -- round a plain number to ``n`` significant digits.
  * :class:`Latex` -- render one line as LaTeX (optional, imported lazily).
  * :class:`Printer` -- show the output; owns the per-scope settings (column vs
    one line, plain text vs LaTeX, full vs fixed precision) and the phase-2 rule
    that modules/functions/classes keep their names.
  * :class:`Source` -- the exact text of the expression being printed.
  * :class:`Expander` -- the macro itself: turn one ``mpt[...]`` into the
    three-phase form, and sequence several expressions.

``mpt`` is a one-line wrapper over :class:`Expander`. The expanded code calls
back into the class methods: ``Printer.render`` (one substituted name) and
``Printer.show`` (all three phases, laid out, value returned).
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
        """Teach ``pytexit`` to render literals, dotted attributes and products.

        ``pytexit`` 0.4.0 has three gaps. Two make a line silently fall back to
        plain text: it only defines ``visit_Num`` (Python >= 3.8 numeric
        literals parse to ``ast.Constant``, which lands on the buggy
        ``generic_visit`` and raises), and it has no ``visit_Attribute`` at all,
        so any dotted access (``me.H.atomic_number``) fails the same way. The
        third changes the meaning: ``visit_Mult`` returns a space, and the
        multiplication path only uses ``tex_multiplier`` when an operand looks
        like a float literal, so ``2 * (0.07 * m)`` becomes ``2 0.07\\cdot m``.
        All three are fixed here (a no-op on patched versions, except the
        multiplier which is always made explicit). Only invoked in LaTeX mode,
        so the default plain-text path never touches ``pytexit``.
        """
        try:
            from pytexit.core import core  # pyright: ignore[reportMissingModuleSource]

            visitor = core.LatexVisitor
        except Exception:  # pragma: no cover - pytexit missing or restructured
            return

        if "visit_Constant" not in visitor.__dict__:
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

        if "visit_Attribute" not in visitor.__dict__:
            def visit_Attribute(self, n):
                # No visitor for dotted access: render `me.H.atomic_number` as
                # `me.H.atomic_{number}`, each part through the normal name
                # formatting (`_` becomes a subscript, Greek names are mapped).
                attr = self.visit(ast.Name(id=n.attr, ctx=ast.Load()))
                return "{}.{}".format(self.visit(n.value), attr)

            # `setattr`, so the type checker (which does not see the patched
            # visitor on the third-party class) stays happy.
            setattr(visitor, "visit_Attribute", visit_Attribute)

        # Always show multiplication explicitly. pytexit's `visit_Mult` returns
        # a space (implicit multiplication), and its `Mult` branch only switches
        # to `tex_multiplier` when one operand looks like a float *literal* --
        # so `2 * (0.07 * m)` renders as `2 0.07\cdot m`, silently changing the
        # formula. Return the configured multiplier for every `Mult` instead.
        def visit_Mult(self, n):
            return self.tex_multiplier

        setattr(visitor, "visit_Mult", visit_Mult)


# ---------------------------------------------------------------------------
# Printer: the three lines, plain text or LaTeX, per scope
# ---------------------------------------------------------------------------

class Printer:
    """Show the output of an ``mpt`` call, per *scope*.

    A scope is a file (keyed by its absolute path), a notebook (``"<ipython>"``)
    or the "no file" case (:attr:`ANY_FILE`). Each scope independently picks:

    * the layout -- a column of lines (default), or one line
      (``mpt.configure(out_order="line")``),
    * the format -- plain text (default) or LaTeX
      (``mpt.configure(out_format="latex")``), and
    * the display precision -- full, or ``n`` significant digits
      (``mpt.configure(precision=n)``), and
    * whether phase 2 collapses a nested assignment chain
      (``mpt.configure(multiple_assignment_reduce=True)``).

    So the settings never leak between files. They live in :attr:`line_scopes`,
    :attr:`latex_scopes`, :attr:`precision_scopes` and
    :attr:`multiple_assignment_reduce_scopes`; the ``key_of*`` methods
    map a file or a live module to a scope key; and :meth:`render`, :meth:`text`,
    :meth:`emit` and :meth:`show` are the runtime hooks the expanded code calls
    (see :class:`Expander`).
    """

    #: Scope key meaning "every file" (used when no filename is known).
    ANY_FILE = "*"

    #: Scope keys shown on a single line (see ``out_order="line"``); others columns.
    line_scopes = set()

    #: Scope keys that opted into LaTeX output (see ``out_format="latex"``).
    latex_scopes = set()

    #: Scope keys that set a display precision, mapped to significant digits.
    precision_scopes = {}

    #: Scope keys whose phase 2 collapses a nested assignment chain to the value
    #: of the innermost assignment (see ``multiple_assignment_reduce=True``).
    multiple_assignment_reduce_scopes = set()

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

    # --- the display settings (back `mpt.configure`) ------------------------

    @classmethod
    def set_line(cls, key, on=True):
        """Enable (or disable) one-line layout for `key`; return `key`."""
        if on:
            cls.line_scopes.add(key)
        else:
            cls.line_scopes.discard(key)
        return key

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
                raise ValueError(
                    "mpt.configure(precision=...) needs a positive number of significant digits"
                )
            cls.precision_scopes[key] = digits
        return key

    @classmethod
    def set_multiple_assignment_reduce(cls, key, on=True):
        """Enable (or disable) nested-assignment collapsing for `key`; return `key`."""
        if on:
            cls.multiple_assignment_reduce_scopes.add(key)
        else:
            cls.multiple_assignment_reduce_scopes.discard(key)
        return key

    @classmethod
    def line_on(cls, key):
        """Whether `key` (or every file, via ``ANY_FILE``) uses one-line layout."""
        return cls.ANY_FILE in cls.line_scopes or key in cls.line_scopes

    @classmethod
    def latex_on(cls, key):
        """Whether `key` (or every file, via ``ANY_FILE``) uses LaTeX output."""
        return cls.ANY_FILE in cls.latex_scopes or key in cls.latex_scopes

    @classmethod
    def precision_of(cls, key):
        """Significant digits to show for `key`, or ``None`` for the default."""
        return cls.precision_scopes.get(key)

    @classmethod
    def multiple_assignment_reduce_on(cls, key):
        """Whether `key` collapses a nested assignment chain in phase 2."""
        return (
            cls.ANY_FILE in cls.multiple_assignment_reduce_scopes
            or key in cls.multiple_assignment_reduce_scopes
        )

    # --- the runtime hooks (called by the expanded code) --------------------

    @classmethod
    def render(cls, key, name, value):
        """Phase 2: the text that replaces one name occurrence.

        Modules, functions, methods, built-ins, classes and other callables are
        *not* expanded: they keep the name used in the source (so ``math.sqrt``
        stays ``math.sqrt``, ``f`` stays ``f``, ``int`` stays ``int``, an
        attribute holding a function such as ``np.sin`` stays ``np.sin``)
        instead of dumping an opaque ``<…>`` repr. Everything else is shown by
        :meth:`text` -- including a dotted attribute chain such as
        ``me.H.atomic_number``, whose value becomes the plain number.
        """
        if isinstance(value, cls.OPAQUE_TYPES) or callable(value):
            return name
        return cls.text(key, value)

    @classmethod
    def text(cls, key, value):
        """`value` as shown (``str``, with the scope's precision applied)."""
        digits = cls.precision_of(key)
        if digits is not None:
            shown = Numbers.format(value, digits)
            if shown is not None:
                return shown
        return str(value)

    @classmethod
    def substituted(cls, key, normal, reduced, *values):
        """Phase 2 for a nested assignment chain: fill one of two templates.

        `normal` is the full substitution (the whole chain), `reduced` is the
        chain collapsed to the innermost value (``ro1 := 2230``). Which one is
        used is a runtime setting, so the macro passes both; `values` are the
        rendered occurrences, evaluated once and shared by both templates.
        """
        template = reduced if cls.multiple_assignment_reduce_on(key) else normal
        return template.format(*values)

    @classmethod
    def emit(cls, key, text):
        """Show one line: as LaTeX, or printed."""
        if cls.latex_on(key):
            Latex.show(text)
        else:
            print(text)

    @classmethod
    def show(cls, key, name, source, substituted, value):
        """Show the whole call -- source, substitution and value -- and return it.

        In a *column* (the default) the three are separate lines, each carrying
        the ``name := `` prefix of the assignment form. On *one line* they are
        joined (``x = 3 + y = 3 + 5 = 8``), the name appearing once. ``name`` is
        the assignment target (``""`` for a bare expression) and ``source`` /
        ``substituted`` already contain the name, so the joined line just drops
        it (everything up to the first ``:=``).
        """
        shown = cls.text(key, value)
        if cls.line_on(key):
            if name:
                source = source.split(":=", 1)[1].strip()
                substituted = substituted.split(":=", 1)[1].strip()
            joiner = " == " if cls.latex_on(key) else " = "
            cls.emit(key, joiner.join(([name] if name else []) + [source, substituted, shown]))
        else:
            cls.emit(key, source)
            cls.emit(key, substituted)
            cls.emit(key, f"{name} := {shown}" if name else shown)
        return value


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
        ``{}`` placeholder; `names` lists those occurrences in source order. A
        dotted chain rooted at a name (``me.H.atomic_number``) is one occurrence
        -- the whole chain -- so its value is substituted as a unit.
        """
        start = self._offset(node.lineno, node.col_offset)
        raw = segment.encode("utf-8")
        spans = sorted(
            (self._offset(n.lineno, n.col_offset) - start,
             self._offset(n.end_lineno, n.end_col_offset) - start,
             n)
            for n in self._occurrences(node)
        )

        pieces = []
        names = []
        cursor = 0
        for s, e, name in spans:
            pieces.append(self._escape_braces(raw[cursor:s].decode("utf-8")))
            pieces.append("{}")
            names.append(name)
            cursor = e
        pieces.append(self._escape_braces(raw[cursor:].decode("utf-8")))
        return "".join(pieces), names

    @staticmethod
    def _occurrences(node):
        """The occurrences to substitute: loaded names and dotted chains.

        A plain loaded ``Name`` is one occurrence. A dotted chain rooted at a
        name (``me.H.atomic_number``) is *one* occurrence -- the whole chain --
        so both its prefixes (``me.H``) and its root ``Name`` (``me``) are left
        out: they are contained in the chain and would overlap it. Chains whose
        root is not a bare name (``f(x).attr``) are left alone, so the call is
        not evaluated an extra time.
        """
        chains = [
            n for n in ast.walk(node)
            if isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Load)
            and Source._attribute_root(n) is not None
        ]
        inner = {id(n.value) for n in chains if isinstance(n.value, ast.Attribute)}
        roots = {id(Source._attribute_root(n)) for n in chains}
        names = [
            n for n in ast.walk(node)
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
            and id(n) not in roots
        ]
        return names + [n for n in chains if id(n) not in inner]

    @staticmethod
    def _attribute_root(node):
        """The ``Name`` at the root of a dotted chain, or ``None`` if there is none."""
        while isinstance(node, ast.Attribute):
            node = node.value
        return node if isinstance(node, ast.Name) else None

    def _offset(self, lineno, col_offset):
        """Absolute UTF-8 byte offset of `(lineno, col_offset)` in the source."""
        lines = self.text.replace("\f", "").splitlines(True)
        base = sum(len(line.encode("utf-8")) for line in lines[:lineno - 1])
        return base + col_offset

    @staticmethod
    def _escape_braces(text):
        """Escape literal braces so `str.format` treats them as literal text."""
        return text.replace("{", "{{").replace("}", "}}")


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
        """Expand a single item into its runtime ``Printer.show`` call."""
        key = self.key

        # Assignment form `mpt[name := expression]` carries the name; anything
        # else (including a bare expression such as `mpt[(a + z) * 2]`) has none.
        if type(expr) is ast.NamedExpr and type(expr.target) is ast.Name:
            name = expr.target.id
        else:
            name = ""

        # Phase 1 is the expression exactly as written at the use site; phase 2
        # is that same text with each loaded name replaced, in place, by that
        # name's value (a `str.format` template plus one argument per name).
        source = self.source.segment(expr)
        template, names = self.source.template(source, expr)
        rendered = [self._rendered_arg(key, node) for node in names]

        inner = self._innermost_assignment_value(expr) if name else None
        if inner is None:
            substituted = ast.Call(func=ast.Attribute(
                    value=ast.Constant(template),
                    attr="format",
                    ctx=ast.Load()
                ),
                args=rendered,
                keywords=[]
            )
        else:
            # A chain such as `ro1 := (ro := (ro_БФСС := 2230))`. Phase 1 keeps
            # the full chain; phase 2 can collapse it to `ro1 := 2230`. Which
            # one is shown is a runtime setting, so both templates are built
            # here and `Printer.substituted` picks one; the occurrences (which
            # are all inside the innermost value either way) are rendered once.
            inner_source = self.source.segment(inner)
            inner_template = self.source.template(inner_source, inner)[0]
            call_args: list[ast.expr] = [
                ast.Constant(key),
                ast.Constant(template),
                ast.Constant(f"{name} := {inner_template}"),
            ]
            call_args += rendered
            substituted = ast.Call(
                func=q[h[Printer].substituted], args=call_args, keywords=[]
            )

        # `show` prints the source, the substitution and (phase 3) the value, and
        # returns the value. The arguments are evaluated left to right, so the
        # substitution is built from the *old* values before `expr` runs.
        return q[h[Printer].show(u[key], u[name], u[source], a[substituted], a[expr])]

    @staticmethod
    def _innermost_assignment_value(expr):
        """`expr` with its nested assignment wrappers removed, or ``None``.

        Only a *direct* chain is handled -- an assignment whose right-hand side
        is itself an assignment, recursively, as in
        ``ro1 := (ro := (ro_БФСС := 2230))``. The innermost value is what the
        whole chain evaluates to, and it is also where all loaded names live,
        so the same rendered values fill either phase-2 template. Anything else
        (``mpt[(a := 3) + 1]``, or a single assignment) returns ``None`` and
        keeps the ordinary phase 2.
        """
        if type(expr) is not ast.NamedExpr or type(expr.value) is not ast.NamedExpr:
            return None
        node = expr.value
        while type(node) is ast.NamedExpr:
            node = node.value
        return node

    @staticmethod
    def _rendered_arg(key, name_node):
        """AST for ``Printer.render(<key>, "<name>", <name>)``, hygienically bound.

        The ``<name>`` string is the identifier for a plain name, or the dotted
        text for an attribute chain (``me.H.atomic_number``).
        """
        if isinstance(name_node, ast.Attribute):
            name = ast.unparse(name_node)
        else:
            name = name_node.id
        return q[h[Printer].render(u[key], u[name], a[name_node])]

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


_UNSET = object()


def _configure(*, out_order=_UNSET, out_format=_UNSET, precision=_UNSET,
               multiple_assignment_reduce=_UNSET):
    """Change the display settings for the file (or notebook) this is called in.

    The settings apply to every ``mpt[...]`` in the calling scope -- the file,
    or the whole notebook in Jupyter -- and never leak into other modules. Every
    argument is optional: an omitted argument is left unchanged.

    Args:
        out_order: ``"column"`` (default) shows the three phases on separate
            lines; ``"line"`` joins them into one, with the name appearing once,
            e.g. ``x = 3 + y = 3 + 5 = 8``.
        out_format: ``"text"`` (default) prints plain text; ``"latex"`` renders
            each line with ``pytexit`` + ``IPython.display`` (Jupyter).
        precision: Number of significant digits shown for plain numbers: ``4``
            shows ``3.123123412`` as ``3.123``. Only the display is rounded --
            the expression is still evaluated and returned at full precision.
            ``None`` restores the default.
        multiple_assignment_reduce: ``True`` collapses a nested assignment chain
            such as ``ro1 := (ro := (c := 2230))`` to ``ro1 := 2230`` in the
            substitution phase (phase 1 still shows the chain as written).
            Default ``False``.

    Returns:
        The scope key that changed: the file's absolute path, or ``"<ipython>"``
        in a notebook.

    Raises:
        ValueError: If a value is not one of the allowed ones.
    """
    key = Printer.key_of_globals(sys._getframe(1).f_globals)
    if out_order is not _UNSET:
        if out_order not in ("column", "line"):
            raise ValueError(
                'mpt.configure(out_order=...) expects "column" or "line"'
            )
        Printer.set_line(key, out_order == "line")
    if out_format is not _UNSET:
        if out_format not in ("text", "latex"):
            raise ValueError(
                'mpt.configure(out_format=...) expects "text" or "latex"'
            )
        Printer.set_latex(key, out_format == "latex")
    if precision is not _UNSET:
        Printer.set_precision(key, precision)
    if multiple_assignment_reduce is not _UNSET:
        if not isinstance(multiple_assignment_reduce, bool):
            raise ValueError(
                "mpt.configure(multiple_assignment_reduce=...) expects True or False"
            )
        Printer.set_multiple_assignment_reduce(key, multiple_assignment_reduce)
    return key


# `mpt.configure(...)` groups the per-file display settings. It is attached as an
# attribute of the macro function, so it is available wherever `mpt` itself is
# (e.g. `from mathprint import mpt`). (`setattr`, so the type checker, which sees
# `mpt` as a plain function, stays happy.)
setattr(mpt, "configure", _configure)
