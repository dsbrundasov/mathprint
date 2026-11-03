"""The exact source text of an expression, and the in-place substitution plan.

Phase 1 is served by :class:`SourceText`: it holds the file (or notebook cell)
text and returns the expression's own text byte-for-byte.  Phase 2 is served by
:class:`InPlaceSubstitution`: the same text with every *loaded* name replaced by
a positional ``str.format`` placeholder, plus the list of those name occurrences
in source order.  A dotted chain and an indexed access rooted at a name are
whole occurrences: a chain is substituted as a unit, and an access can be
substituted by its item (see ``expand_collections``).

Because the template is cut from the exact source and the placeholders are
numbered by byte offset, the i-th placeholder is necessarily the i-th occurrence
and receives the i-th value: substitution preserves the order of the names
exactly.  Nothing is evaluated or simplified at this stage (an item is read only
when the caller asks for it).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
import importlib.util

from mcpyrate.core import MacroExpansionError


@dataclass(frozen=True)
class SubscriptOccurrence:
    """One indexed access such as ``_p23["vgs"]`` or ``d["a"]["b"]``.

    The whole access is a single phase-2 occurrence.  ``base`` is the name or
    dotted chain that is substituted when the collection is expanded, ``head``
    and ``suffix`` are the literal text around it, and ``inner`` lists the
    occurrences inside the index (``d[key]``).  ``suffix`` contains ``{}``
    placeholders for ``inner``.
    """

    node: ast.Subscript
    base: ast.Name | ast.Attribute
    head: str
    suffix: str
    inner: tuple[Occurrence, ...] = ()


#: One substituted occurrence: a loaded name, a dotted chain, or an indexed access.
Occurrence = ast.Name | ast.Attribute | SubscriptOccurrence


class SourceText:
    """The text an expression was written in (a file, or a notebook cell).

    Phase 1 must print the expression verbatim, so the text is required.
    :meth:`text_of` raises if it is missing (plain REPL, ``python -c``,
    ``exec``) or if the expression cannot be located -- rather than printing
    something subtly different from what the user wrote.
    """

    #: Set by the Jupyter extension, where a cell has no backing file.
    override: str | None = None

    _cache: dict[str, str | None] = {}

    @classmethod
    def read(cls, filename: str) -> str | None:
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

    def __init__(self, text: str | None) -> None:
        self.text = text

    def text_of(self, node: ast.AST) -> str:
        """The exact source text of `node`, or raise."""
        text: str = self._required_text()
        segment: str | None = ast.get_source_segment(text, node)
        if segment is None:
            raise MacroExpansionError("mpt could not find the expression in the source text")
        return segment

    def text_around(self, stmt: ast.stmt, inner: ast.expr) -> tuple[str, str]:
        """The exact text of `stmt` before and after `inner`.

        Used by the block form: an assignment statement is exactly its
        right-hand side wrapped in this text, so phase 2 can reproduce the
        statement verbatim while substituting only the right-hand side.
        """
        raw: bytes = self._required_text().encode("utf-8")
        start: int = self._offset(stmt.lineno, stmt.col_offset)
        inner_start: int = self._offset(inner.lineno, inner.col_offset)
        if (inner.end_lineno is None or inner.end_col_offset is None
                or stmt.end_lineno is None or stmt.end_col_offset is None):
            raise MacroExpansionError(
                "mpt needs position information for the assignment statement"
            )
        inner_end: int = self._offset(inner.end_lineno, inner.end_col_offset)
        end: int = self._offset(stmt.end_lineno, stmt.end_col_offset)
        return (
            raw[start:inner_start].decode("utf-8"),
            raw[inner_end:end].decode("utf-8"),
        )

    def text_from_to(self, first: ast.expr, last: ast.expr) -> str:
        """The exact source text from the start of `first` to the end of `last`."""
        raw: bytes = self._required_text().encode("utf-8")
        start: int = self._offset(first.lineno, first.col_offset)
        if last.end_lineno is None or last.end_col_offset is None:
            raise MacroExpansionError(
                "mpt needs position information for the assignment target"
            )
        end: int = self._offset(last.end_lineno, last.end_col_offset)
        return raw[start:end].decode("utf-8")

    def _required_text(self) -> str:
        """The source text, or raise if this context has none."""
        if self.text is None:
            raise MacroExpansionError(
                "mpt needs the source file to print the expression verbatim, but this "
                "context has none (plain REPL, `python -c` and `exec` are not supported)"
            )
        return self.text

    def placeholder_template(
        self, segment: str, node: ast.expr
    ) -> tuple[str, list[Occurrence]]:
        """Build ``(template, occurrences)`` from the exact `segment` of `node`.

        Every loaded name occurrence inside `segment` becomes a positional
        ``{}`` placeholder; `occurrences` lists those occurrences in source
        order.  A dotted chain rooted at a name (``me.H.atomic_number``) is one
        occurrence -- the whole chain -- so its value is substituted as a unit.
        An indexed access rooted at a name (``_p23["vgs"]``) is also one
        occurrence, so phase 2 can substitute the *item* instead of the whole
        collection when ``expand_collections`` is off.
        """
        start: int = self._offset(node.lineno, node.col_offset)
        return self._template_for(segment, self._occurrences(node), start)

    def _template_for(
        self, segment: str, occurrences: list[Occurrence], origin: int
    ) -> tuple[str, list[Occurrence]]:
        """``(template, occurrences)`` for `segment`, whose start is `origin`."""
        raw: bytes = segment.encode("utf-8")
        spans: list[tuple[int, int, Occurrence]] = sorted(
            (*self._relative_span(n, origin), n) for n in occurrences
        )

        pieces: list[str] = []
        ordered: list[Occurrence] = []
        cursor: int = 0
        for begin, end, occurrence in spans:
            pieces.append(self._escape_braces(raw[cursor:begin].decode("utf-8")))
            pieces.append("{}")
            ordered.append(occurrence)
            cursor = end
        pieces.append(self._escape_braces(raw[cursor:].decode("utf-8")))
        return "".join(pieces), ordered

    def _occurrences(self, node: ast.expr) -> list[Occurrence]:
        """The occurrences to substitute: loaded names, chains and indexes.

        A plain loaded ``Name`` is one occurrence.  A dotted chain rooted at a
        name is *one* occurrence -- the whole chain -- so both its prefixes
        (``me.H``) and its root ``Name`` (``me``) are left out: they are
        contained in the chain and would overlap it.  An indexed access rooted
        at a name or chain (``d["x"]``, ``self.rows[0]``, ``d["a"]["b"]``) is
        likewise one occurrence, and everything inside it is described by that
        occurrence instead of being substituted separately.
        """
        subscripts: list[SubscriptOccurrence] = self._top_level_subscripts(node)
        covered: set[int] = {
            id(n) for occurrence in subscripts for n in ast.walk(occurrence.node)
        }
        chains: list[ast.Attribute] = [
            n for n in ast.walk(node)
            if isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Load)
            and SourceText._attribute_root(n) is not None
        ]
        inner: set[int] = {
            id(n.value) for n in chains if isinstance(n.value, ast.Attribute)
        }
        roots: set[int] = {id(SourceText._attribute_root(n)) for n in chains}
        names: list[ast.Name] = [
            n for n in ast.walk(node)
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
            and id(n) not in roots and id(n) not in covered
        ]
        occurrences: list[Occurrence] = list(names)
        occurrences.extend(
            n for n in chains if id(n) not in inner and id(n) not in covered
        )
        occurrences.extend(subscripts)
        return occurrences

    def _top_level_subscripts(self, node: ast.expr) -> list[SubscriptOccurrence]:
        """Indexed accesses that are not nested inside another one."""
        candidates: list[ast.Subscript] = [
            n for n in ast.walk(node)
            if isinstance(n, ast.Subscript) and isinstance(n.ctx, ast.Load)
            and self._subscript_base(n) is not None
        ]
        outermost: list[ast.Subscript] = [
            candidate for candidate in candidates
            if not any(
                candidate is not other
                and any(n is candidate for n in ast.walk(other))
                for other in candidates
            )
        ]
        return [self._subscript_occurrence(n) for n in outermost]

    def _subscript_occurrence(self, node: ast.Subscript) -> SubscriptOccurrence:
        """Describe one top-level indexed access."""
        base: ast.Name | ast.Attribute | None = self._subscript_base(node)
        if base is None:  # pragma: no cover - only called for candidates
            raise MacroExpansionError("mpt could not find the base of an index")

        start: int = self._offset(node.lineno, node.col_offset)
        base_start: int = self._offset(base.lineno, base.col_offset)
        base_end: int = self._offset(base.end_lineno or 0, base.end_col_offset or 0)
        end: int = self._offset(node.end_lineno or 0, node.end_col_offset or 0)
        raw: bytes = self._required_text().encode("utf-8")
        head: str = raw[start:base_start].decode("utf-8")
        suffix: str = raw[base_end:end].decode("utf-8")
        inner: list[Occurrence] = self._occurrences(node.slice)
        template, ordered = self._template_for(suffix, inner, base_end)
        return SubscriptOccurrence(
            node=node, base=base, head=head, suffix=template,
            inner=tuple(ordered),
        )

    def _subscript_base(self, node: ast.Subscript) -> ast.Name | ast.Attribute | None:
        """The name/chain being indexed, or ``None`` for other expressions.

        Nested indexes collapse to their root: ``d["a"]["b"]`` is indexed on
        ``d``.  A chain is accepted only when it starts at a bare name, so an
        access such as ``f(x)[0]`` is left alone (the call is not evaluated an
        extra time).
        """
        value: ast.expr = node.value
        while isinstance(value, ast.Subscript):
            value = value.value
        if isinstance(value, ast.Name):
            return value if isinstance(value.ctx, ast.Load) else None
        if isinstance(value, ast.Attribute):
            root: ast.Name | None = self._attribute_root(value)
            if isinstance(value.ctx, ast.Load) and root is not None:
                return value
        return None

    @staticmethod
    def _attribute_root(node: ast.expr) -> ast.Name | None:
        """The ``Name`` at the root of a dotted chain, or ``None`` if there is none."""
        while isinstance(node, ast.Attribute):
            node = node.value
        return node if isinstance(node, ast.Name) else None

    def _offset(self, lineno: int, col_offset: int) -> int:
        """Absolute UTF-8 byte offset of `(lineno, col_offset)` in the source."""
        text: str = self._required_text()
        lines: list[str] = text.replace("\f", "").splitlines(True)
        base: int = sum(len(line.encode("utf-8")) for line in lines[:lineno - 1])
        return base + col_offset

    def _relative_span(self, occurrence: Occurrence, origin: int) -> tuple[int, int]:
        """`occurrence`'s byte span ``(start, end)``, relative to `origin`."""
        node: ast.expr = (
            occurrence.node
            if isinstance(occurrence, SubscriptOccurrence)
            else occurrence
        )
        end_lineno: int | None = node.end_lineno
        end_col_offset: int | None = node.end_col_offset
        if end_lineno is None or end_col_offset is None:
            raise MacroExpansionError(
                "mpt needs position information for the names in the expression"
            )
        return (
            self._offset(node.lineno, node.col_offset) - origin,
            self._offset(end_lineno, end_col_offset) - origin,
        )

    @staticmethod
    def _escape_braces(text: str) -> str:
        """Escape literal braces so `str.format` treats them as literal text."""
        return text.replace("{", "{{").replace("}", "}}")


class InPlaceSubstitution:
    """Phase 2: the expression's source with its names replaced in place.

    Attributes:
        source: phase 1 text, exactly as written.
        template: the same text with ``{}`` placeholders instead of names.
        occurrences: the loaded-name / chain / indexed-access AST nodes, in
            source order; the i-th one fills the i-th placeholder.
    """

    def __init__(self, source_text: SourceText, node: ast.expr) -> None:
        self.source = source_text.text_of(node)
        self.template, self.occurrences = source_text.placeholder_template(
            self.source, node
        )
