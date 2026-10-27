"""The LaTeX renderer: turn one printed line into LaTeX, and display it.

This is the only module that knows about ``pytexit`` and ``IPython.display``.
Both are imported lazily, so a run without ``out_format="latex"`` never touches
them.

A ``LatexRenderer`` is a *converter*, not a strategy: the strategy that routes
the macro's lines here is :class:`mathprint_main.presentation.LatexOutput`.
"""

import ast


class LatexRenderer:
    """Convert printed lines with ``pytexit``, and optionally display them."""

    @staticmethod
    def display(text):
        """Show `text` as rendered LaTeX, or print it if it cannot be converted.

        Some operators (e.g. ``and``) are not convertible; then the line is
        printed, so one expression cannot break the run.
        """
        tex = LatexRenderer.to_source(text)
        if tex is None:
            print(text)
            return
        from IPython.display import Latex as _IpythonLatex, display

        display(_IpythonLatex(tex))

    @staticmethod
    def to_source(text):
        """Return `text` as LaTeX source (``$$...$$``), or ``None`` on failure.

        This does not display anything, so it also backs the raw
        ``additional_out="latex"`` output.  Only ``pytexit`` is needed, so it
        works outside Jupyter too.
        """
        from pytexit import py2tex  # pyright: ignore[reportMissingModuleSource]

        LatexRenderer.patch_pytexit()
        try:
            return py2tex(
                LatexRenderer.to_pytex_input(text),
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
            return None

    @staticmethod
    def to_pytex_input(text):
        """Turn a printed line into a Python expression ``py2tex`` can parse.

        The assignment prefix uses ``:=``; ``py2tex`` expects a comparison, so
        it is rewritten to ``==`` (rendered as ``=``).
        """
        return text.replace(":=", "==")

    @staticmethod
    def patch_pytexit():
        """Teach ``pytexit`` to render literals, attributes, unary operators and products.

        ``pytexit`` 0.4.0 has four gaps.  Three make a line silently fall back
        to plain text: it only defines ``visit_Num`` (Python >= 3.8 numeric
        literals parse to ``ast.Constant``, which lands on the buggy
        ``generic_visit`` and raises); it has no ``visit_Attribute`` at all, so
        any dotted access (``me.H.atomic_number``) fails the same way; and it
        has no ``visit_UnaryOp``, so a negative number (``-2.5``, ``10**-9``)
        fails too.  The fourth changes the meaning: ``visit_Mult`` returns a
        space, and the multiplication path only uses ``tex_multiplier`` when an
        operand looks like a float literal, so ``2 * (0.07 * m)`` becomes
        ``2 0.07\\cdot m``.  All four are fixed here (a no-op on patched
        versions, except the multiplier which is always made explicit).  Only
        invoked in LaTeX mode, so the default plain-text path never touches
        ``pytexit``.
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

        if "visit_UnaryOp" not in visitor.__dict__:
            def visit_UnaryOp(self, n):
                # pytexit defines `visit_USub` / `visit_UAdd` but no
                # `visit_UnaryOp`, so `-9` hits the broken `generic_visit`.
                # Combine the operator with its operand instead.  This is what
                # makes negative numbers -- including a power-of-ten exponent
                # such as `10**-9` -- render as LaTeX rather than plain text.
                operand = self.visit(n.operand)
                if isinstance(n.operand, ast.BinOp):
                    operand = self.parenthesis(operand)
                return "{}{}".format(self.visit(n.op), operand)

            setattr(visitor, "visit_UnaryOp", visit_UnaryOp)

        # Always show multiplication explicitly.  pytexit's `visit_Mult` returns
        # a space (implicit multiplication), and its `Mult` branch only switches
        # to `tex_multiplier` when one operand looks like a float *literal* --
        # so `2 * (0.07 * m)` renders as `2 0.07\cdot m`, silently changing the
        # formula.  Return the configured multiplier for every `Mult` instead.
        def visit_Mult(self, n):
            return self.tex_multiplier

        setattr(visitor, "visit_Mult", visit_Mult)

