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

The block form ``with mpt:`` uses the same machinery: each statement of the
body is expanded as if it had its own ``mpt[...]`` call, except that an
assignment statement can be written with ``=`` (phases 1 and 2 are the exact
statement text with only the right-hand side substituted; phase 3 uses
``operator="="``).
"""

import ast
from typing import Any

from mcpyrate.core import MacroExpansionError
from mcpyrate.quotes import macros, q, a, u, h

from .presentation import Presenter
from .settings import SettingsStore
from .source import (
    InPlaceSubstitution,
    Occurrence,
    SourceText,
    SubscriptOccurrence,
)


class MacroExpander:
    """Expand the body of one ``mpt[...]`` call.

    ``expander`` is the object mcpyrate passes to a macro function; it carries
    the filename, which is how the expansion finds the exact source text and the
    scope key.  The class is instantiated per ``mpt`` call and only reads the
    source; everything else happens in the expanded code.
    """

    def __init__(self, expander: Any) -> None:
        filename: str | None = getattr(expander, "filename", None)
        self.scope_key = SettingsStore.key_for_filename(filename)
        self.source_text = self._source_text_for(filename)

    @staticmethod
    def _source_text_for(filename: str | None) -> SourceText:
        """The text of `filename`, or the notebook override when there is no file."""
        file_text: str | None = SourceText.read(filename) if filename else None
        if file_text is None:
            file_text = SourceText.override
        return SourceText(file_text)

    def expand(self, expr: ast.expr) -> ast.expr:
        """Expand the subscript body: one expression, or a tuple of them."""
        if type(expr) is ast.Tuple:
            items: list[ast.expr] = [
                self._expand_one(element) for element in expr.elts
            ]
            call: ast.Call = ast.Call(
                func=q[h[MacroExpander].collect], args=items, keywords=[]
            )
            return ast.fix_missing_locations(call)
        return self._expand_one(expr)

    # --- block form: `with mpt:` -------------------------------------------

    def expand_block(self, body: list[ast.stmt],
                     optional_vars: ast.expr | None = None, *,
                     has_other_items: bool = False) -> list[ast.stmt]:
        """Expand the body of ``with mpt:``, statement by statement.

        Every statement is treated exactly as if it had its own ``mpt[...]``
        call: an expression statement prints its three phases, and an
        assignment prints them with ``=`` instead of ``:=``.  Anything else
        (``if``, ``for``, ``def``, ``x += 1``, ...) stays untouched -- the
        block does not invent display rules that ``mpt[...]`` does not have.

        ``with mpt as result:`` is rejected: the block is a statement, so it
        has no value to bind.
        """
        if optional_vars is not None:
            raise MacroExpansionError(
                "mpt: `with mpt as ...` is not supported; the block form does "
                "not produce a value. Use `mpt[expression]` where a value is "
                "needed."
            )
        if has_other_items:
            # `with mpt, lock:` -- mcpyrate removed `mpt` and handed back the
            # remaining `with`. Keep it (and its run-time behaviour), but show
            # the statements in its body.
            node: ast.stmt = body[0]
            if isinstance(node, ast.With):
                node.body = self._expand_body(node.body)
            return [node]
        return self._expand_body(body)

    def _expand_body(self, statements: list[ast.stmt]) -> list[ast.stmt]:
        """Expand each statement of a block, keeping the source order."""
        expanded: list[ast.stmt] = []
        for stmt in statements:
            expanded.extend(self._expand_statement(stmt))
        return expanded

    def _expand_statement(self, stmt: ast.stmt) -> list[ast.stmt]:
        """Turn one statement of a ``with mpt:`` block into its display form."""
        if type(stmt) is ast.Assign:
            return [self._expand_assign(stmt)]
        if type(stmt) is ast.Expr and not self._is_mpt_expression(stmt.value):
            # The same rule as `mpt[expression]`, applied to a statement.
            shown: ast.Expr = ast.Expr(value=self.expand(stmt.value))
            ast.copy_location(shown, stmt)
            return [ast.fix_missing_locations(shown)]
        return [stmt]

    def _expand_assign(self, stmt: ast.Assign) -> ast.Assign:
        """Expand ``target = expression`` with the ``=`` display form.

        Phase 1 is the statement exactly as written; phase 2 is the same text
        with only the right-hand side substituted.  The target is not
        substituted: it is written, not read, and showing
        ``<object at 0x...>`` there would be noise.
        """
        before, after = self.source_text.text_around(stmt, stmt.value)
        name: str = self.source_text.text_from_to(
            stmt.targets[0], stmt.targets[-1]
        )
        substitution = InPlaceSubstitution(self.source_text, stmt.value)
        call: ast.Call = q[h[Presenter].show(
            u[self.scope_key],
            u[name],
            u[self.source_text.text_of(stmt)],
            a[self._substituted_text_call(
                stmt.value, "", substitution, before=before, after=after
            )],
            a[stmt.value],
        )]
        call.keywords.append(ast.keyword(arg="operator", value=ast.Constant("=")))
        result: ast.Assign = ast.Assign(
            targets=stmt.targets, value=ast.fix_missing_locations(call),
            type_comment=stmt.type_comment,
        )
        ast.copy_location(result, stmt)
        return ast.fix_missing_locations(result)

    @staticmethod
    def _is_mpt_expression(expr: ast.expr) -> bool:
        """Whether `expr` is already an ``mpt[...]`` / ``mpt.configure(...)``.

        Such a statement is left for mcpyrate (or for the run time), so it is
        not displayed twice.
        """
        if isinstance(expr, ast.Subscript):
            head: ast.expr = expr.value
        elif isinstance(expr, ast.Call):
            head = expr.func
        else:
            return False
        while isinstance(head, ast.Attribute):
            head = head.value
        return isinstance(head, ast.Name) and head.id == "mpt"

    def _expand_one(self, expr: ast.expr) -> ast.expr:
        """Expand one item into its ``Presenter.show(...)`` call."""
        name: str = self._assignment_name(expr)
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
    def _assignment_name(expr: ast.expr) -> str:
        """``"x"`` for ``x := expression``, else ``""``."""
        if type(expr) is ast.NamedExpr and type(expr.target) is ast.Name:
            return expr.target.id
        return ""

    def _substituted_text_call(self, expr: ast.expr, name: str,
                               substitution: InPlaceSubstitution, *,
                               before: str = "", after: str = "") -> ast.Call:
        """AST for ``Presenter.substituted_text(key, normal, reduced, ...)``.

        `normal` is the phase-2 template of the whole expression; `before` and
        `after` wrap it when the expression is the right-hand side of a block
        assignment (``x = `` / ``)``).  `reduced` differs only for a nested
        assignment chain such as ``ro1 := (ro := (ro_БФСС := 2230))``: it then
        collapses to ``ro1 := 2230``.  Both are built here, and
        :class:`Presenter` picks one from the settings at run time; the
        occurrences are shared, because they all live in the innermost value
        either way.
        """
        occurrences: list[ast.expr] = [
            self._occurrence_argument(node) for node in substitution.occurrences
        ]
        normal: str = before + substitution.template + after
        reduced: str = normal
        inner: ast.expr | None = (
            self._innermost_assignment_value(expr) if name else None
        )
        if inner is not None:
            collapsed: InPlaceSubstitution = InPlaceSubstitution(
                self.source_text, inner
            )
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

    def _occurrence_argument(self, node: Occurrence) -> ast.expr:
        """AST for one rendered occurrence, hygienically bound."""
        if isinstance(node, SubscriptOccurrence):
            return self._subscript_argument(node)
        name: str
        if isinstance(node, ast.Attribute):
            name = ast.unparse(node)
        else:
            name = node.id
        return q[h[Presenter].name_text(u[self.scope_key], u[name], a[node])]

    def _subscript_argument(self, node: SubscriptOccurrence) -> ast.expr:
        """AST for one indexed access: ``Presenter.subscript_text(...)``.

        The item is a zero-argument lambda, so it is evaluated only when
        ``expand_collections=False``; the collection-expanded path keeps the
        old behaviour and never indexes anything during phase 2.
        """
        base_name: str = (
            ast.unparse(node.base)
            if isinstance(node.base, ast.Attribute)
            else node.base.id
        )
        item: ast.Lambda = ast.Lambda(
            args=ast.arguments(
                posonlyargs=[], args=[], vararg=None,
                kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[],
            ),
            body=node.node,
        )
        inner: list[ast.expr] = [
            self._occurrence_argument(occurrence) for occurrence in node.inner
        ]
        args: list[ast.expr] = [
            ast.Constant(self.scope_key),
            ast.Constant(node.head),
            ast.Constant(base_name),
            ast.Constant(node.suffix),
            node.base,
            item,
        ]
        args += inner
        call: ast.Call = ast.Call(
            func=q[h[Presenter].subscript_text], args=args, keywords=[]
        )
        return ast.fix_missing_locations(call)

    @staticmethod
    def _innermost_assignment_value(expr: ast.expr) -> ast.expr | None:
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
        node: ast.expr = expr.value
        while type(node) is ast.NamedExpr:
            node = node.value
        return node

    @staticmethod
    def collect(*values: Any) -> tuple[Any, ...]:
        """Gather a sequenced ``mpt[a, b, ...]`` into a tuple.

        Each item is evaluated (and shown) left to right, in the *caller's*
        scope, so a ``name := ...`` inside one binds the name there, just like a
        standalone ``mpt[name := ...]``.
        """
        return values
