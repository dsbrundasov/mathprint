"""The macro itself: turn one ``mpt[...]`` into run-time calls.

One ``mpt[expression]`` becomes::

    Presenter.show(
        key,                      # which scope's settings to use
        name,                     # "x" for `mpt[x := ...]`, else ""
        source,                   # phase 1, baked in from the source file
        Presenter.substituted_text(key, normal, reduced, *occurrences),
        expression,               # evaluated exactly once, last
    )

``mpt[a, b, ...]`` expands each item that way and wraps them in
``MacroExpander.collect(...)``, which returns a tuple.

The expansion only *describes* the work; the decisions (layout, format,
precision, ...) are made at run time by :class:`Presenter` from the scope's
settings.  That is what lets ``mpt.configure(...)`` affect code expanded
earlier, and what keeps the core -- substitution plus one Python evaluation --
independent of every optional feature.
"""

import ast

from mcpyrate.quotes import macros, q, a, u, h

from .presentation import Presenter
from .settings import SettingsStore
from .source import InPlaceSubstitution, SourceText


class MacroExpander:
    """Expand the body of one ``mpt[...]`` call.

    ``expander`` is the object mcpyrate passes to a macro function; it carries
    the filename, which is how the expansion finds the exact source text and the
    scope key.  The class is instantiated per ``mpt`` call and only reads the
    source; everything else happens in the expanded code.
    """

    def __init__(self, expander):
        filename = getattr(expander, "filename", None)
        self.scope_key = SettingsStore.key_for_filename(filename)
        self.source_text = self._source_text_for(filename)

    @staticmethod
    def _source_text_for(filename):
        """The text of `filename`, or the notebook override when there is no file."""
        file_text = SourceText.read(filename) if filename else None
        if file_text is None:
            file_text = SourceText.override
        return SourceText(file_text)

    def expand(self, expr):
        """Expand the subscript body: one expression, or a tuple of them."""
        if type(expr) is ast.Tuple:
            items = [self._expand_one(element) for element in expr.elts]
            call = ast.Call(
                func=q[h[MacroExpander].collect], args=items, keywords=[]
            )
            return ast.fix_missing_locations(call)
        return self._expand_one(expr)

    def _expand_one(self, expr):
        """Expand one item into its ``Presenter.show(...)`` call."""
        name = self._assignment_name(expr)
        substitution = InPlaceSubstitution(self.source_text, expr)
        # The arguments are evaluated left to right, so phase 2 is rendered
        # from the *old* values before `expr` itself is evaluated.
        return q[h[Presenter].show(
            u[self.scope_key],
            u[name],
            u[substitution.source],
            a[self._substituted_text_call(expr, name, substitution)],
            a[expr],
        )]

    @staticmethod
    def _assignment_name(expr):
        """``"x"`` for ``x := expression``, else ``""``."""
        if type(expr) is ast.NamedExpr and type(expr.target) is ast.Name:
            return expr.target.id
        return ""

    def _substituted_text_call(self, expr, name, substitution):
        """AST for ``Presenter.substituted_text(key, normal, reduced, ...)``.

        `normal` is the phase-2 template of the whole expression.  `reduced`
        differs only for a nested assignment chain such as
        ``ro1 := (ro := (ro_БФСС := 2230))``: it then collapses to
        ``ro1 := 2230``.  Both are built here, and :class:`Presenter` picks one
        from the settings at run time; the occurrences are shared, because they
        all live in the innermost value either way.
        """
        occurrences = [
            self._occurrence_argument(node) for node in substitution.occurrences
        ]
        normal = substitution.template
        reduced = normal
        inner = self._innermost_assignment_value(expr) if name else None
        if inner is not None:
            collapsed = InPlaceSubstitution(self.source_text, inner)
            reduced = f"{name} := {collapsed.template}"

        args: list[ast.expr] = [
            ast.Constant(self.scope_key),
            ast.Constant(normal),
            ast.Constant(reduced),
        ]
        args += occurrences
        return ast.Call(
            func=q[h[Presenter].substituted_text], args=args, keywords=[]
        )

    def _occurrence_argument(self, node):
        """AST for one rendered name occurrence, hygienically bound."""
        if isinstance(node, ast.Attribute):
            name = ast.unparse(node)
        else:
            name = node.id
        return q[h[Presenter].name_text(u[self.scope_key], u[name], a[node])]

    @staticmethod
    def _innermost_assignment_value(expr):
        """`expr` with its nested assignment wrappers removed, or ``None``.

        Only a *direct* chain is handled -- an assignment whose right-hand side
        is itself an assignment, recursively, as in
        ``ro1 := (ro := (ro_БФСС := 2230))``.  The innermost value is what the
        whole chain evaluates to, and it is also where all loaded names live,
        so the same rendered values fill either phase-2 template.  Anything else
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
    def collect(*values):
        """Gather a sequenced ``mpt[a, b, ...]`` into a tuple.

        Each item is evaluated (and shown) left to right, in the *caller's*
        scope, so a ``name := ...`` inside one binds the name there, just like a
        standalone ``mpt[name := ...]``.
        """
        return values
