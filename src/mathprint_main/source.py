"""The exact source text of an expression, and the in-place substitution plan.

Phase 1 is served by :class:`SourceText`: it holds the file (or notebook cell)
text and returns the expression's own text byte-for-byte.  Phase 2 is served by
:class:`InPlaceSubstitution`: the same text with every *loaded* name replaced by
a positional ``str.format`` placeholder, plus the list of those name occurrences
in source order.

Because the template is cut from the exact source and the placeholders are
numbered by byte offset, the i-th placeholder is necessarily the i-th occurrence
and receives the i-th value: substitution preserves the order of the names
exactly.  Nothing is evaluated or simplified at this stage.
"""

import ast
import importlib.util

from mcpyrate.core import MacroExpansionError

#: One substituted occurrence: a loaded name, or a whole dotted chain.
Occurrence = ast.Name | ast.Attribute


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

    def text_of(self, node: ast.expr) -> str:
        """The exact source text of `node`, or raise."""
        text = self._required_text()
        segment = ast.get_source_segment(text, node)
        if segment is None:
            raise MacroExpansionError("mpt could not find the expression in the source text")
        return segment

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
        """
        start = self._offset(node.lineno, node.col_offset)
        raw = segment.encode("utf-8")
        spans = sorted(
            (*self._relative_span(n, start), n) for n in self._occurrences(node)
        )

        pieces: list[str] = []
        occurrences: list[Occurrence] = []
        cursor = 0
        for begin, end, name in spans:
            pieces.append(self._escape_braces(raw[cursor:begin].decode("utf-8")))
            pieces.append("{}")
            occurrences.append(name)
            cursor = end
        pieces.append(self._escape_braces(raw[cursor:].decode("utf-8")))
        return "".join(pieces), occurrences

    def _occurrences(self, node: ast.expr) -> list[Occurrence]:
        """The occurrences to substitute: loaded names and dotted chains.

        A plain loaded ``Name`` is one occurrence.  A dotted chain rooted at a
        name is *one* occurrence -- the whole chain -- so both its prefixes
        (``me.H``) and its root ``Name`` (``me``) are left out: they are
        contained in the chain and would overlap it.  Chains whose root is not
        a bare name (``f(x).attr``) are left alone, so the call is not evaluated
        an extra time.
        """
        chains = [
            n for n in ast.walk(node)
            if isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Load)
            and SourceText._attribute_root(n) is not None
        ]
        inner = {id(n.value) for n in chains if isinstance(n.value, ast.Attribute)}
        roots = {id(SourceText._attribute_root(n)) for n in chains}
        names = [
            n for n in ast.walk(node)
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
            and id(n) not in roots
        ]
        occurrences: list[Occurrence] = list(names)
        occurrences.extend(n for n in chains if id(n) not in inner)
        return occurrences

    @staticmethod
    def _attribute_root(node: ast.expr) -> ast.Name | None:
        """The ``Name`` at the root of a dotted chain, or ``None`` if there is none."""
        while isinstance(node, ast.Attribute):
            node = node.value
        return node if isinstance(node, ast.Name) else None

    def _offset(self, lineno: int, col_offset: int) -> int:
        """Absolute UTF-8 byte offset of `(lineno, col_offset)` in the source."""
        text = self._required_text()
        lines = text.replace("\f", "").splitlines(True)
        base = sum(len(line.encode("utf-8")) for line in lines[:lineno - 1])
        return base + col_offset

    def _relative_span(self, node: Occurrence, origin: int) -> tuple[int, int]:
        """`node`'s byte span ``(start, end)``, relative to `origin`."""
        end_lineno = node.end_lineno
        end_col_offset = node.end_col_offset
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
        occurrences: the loaded-name AST nodes, in source order; the i-th one
            fills the i-th placeholder.
    """

    def __init__(self, source_text: SourceText, node: ast.expr) -> None:
        self.source = source_text.text_of(node)
        self.template, self.occurrences = source_text.placeholder_template(
            self.source, node
        )
