"""Type stubs for the ``mathprint`` macros.

``mpt`` is a macro: it is invoked as ``mpt[expression]``, which static type
checkers would otherwise report as subscripting a function.

The module also declares the pieces the macro is built from, so tests and
advanced users get the same names and signatures at run time and in the editor.
"""

from dataclasses import dataclass
from typing import Any, Literal

class _Macro:
    """The ``mpt`` macro.

    Invoke it as ``mpt[expression]``; configure it with ``mpt.configure(...)``.
    """

    def __getitem__(self, item: Any) -> Any:
        """Print ``mpt[expression]`` in three phases and return its value.

        The three phases are the source exactly as written, the source with each
        variable replaced by its current value, and the computed value. The
        expression is evaluated exactly once.

        The assignment form ``mpt[name := expression]`` also binds ``name`` and
        prefixes the output with it. Several items (``mpt[a, b]``) are shown in
        order and yield a tuple of the values.
        """
        ...

    def configure(
        self,
        *,
        reset: bool = ...,
        out_order: Literal["column", "line"] = ...,
        out_format: Literal["text", "latex"] = ...,
        precision: int | None = ...,
        multiple_assignment_reduce: bool = ...,
        reduce_equ_stages: bool = ...,
        number_format: Literal["exp", "power"] = ...,
        additional_out: Literal["latex", "text"] | None = ...,
    ) -> str:
        """Change the display settings for the file (or notebook) this is called in.

        The settings apply to every ``mpt[...]`` in the calling scope -- the
        file, or the whole notebook in Jupyter -- and never leak into other
        modules. Every argument is optional: an omitted argument is left
        unchanged.

        Args:
            reset: ``True`` drops every option of the scope first, returning it
                to the core output; other arguments then apply on top. Default
                ``False`` (change only what is given).
            out_order: ``"column"`` (default) shows the three phases on separate
                lines; ``"line"`` joins them into one, with the name appearing
                once, e.g. ``x = 3 + y = 3 + 5 = 8``.
            out_format: ``"text"`` (default) prints plain text; ``"latex"``
                renders each line with ``pytexit`` + ``IPython.display``
                (Jupyter).
            precision: Number of significant digits shown for plain numbers:
                ``4`` shows ``3.123123412`` as ``3.123``. Only the display is
                rounded -- the expression is still evaluated and returned at
                full precision. ``None`` restores the default.
            multiple_assignment_reduce: ``True`` collapses a nested assignment
                chain such as ``ro1 := (ro := (c := 2230))`` to ``ro1 := 2230``
                in the substitution phase (phase 1 still shows the chain as
                written). Default ``False``.
            reduce_equ_stages: ``True`` drops repeated adjacent stages from a
                one-line result: ``ro1 = (ro := (...)) = 2230 = 2230`` becomes
                ``ro1 = (ro := (...)) = 2230``. Has no effect in column mode.
                Default ``False``.
            number_format: ``"exp"`` (default) leaves numbers as ``str`` shows
                them; ``"power"`` uses a power of ten: ``1.23e-09`` becomes
                ``1.23*10**-9``, and a plain decimal far from ``1`` (below
                ``10**-4`` or at/above ``10**16``) is normalized, e.g.
                ``0.0001106`` -> ``1.106*10**-4``. Applies to every phase.
            additional_out: ``None`` (default) adds nothing. ``"latex"`` prints
                the same lines again, after the main output, as raw LaTeX
                source; ``"text"`` prints them as the plain Python line. The
                additional output is never rendered and uses all other settings
                unchanged.

        Returns:
            The scope key that changed: the file's absolute path, or
            ``"<ipython>"`` in a notebook.

        Raises:
            ValueError: If a value is not one of the allowed ones.

        Example:
            ```python
            mpt.configure(out_order="line", out_format="latex", precision=4)
            ```
        """
        ...

mpt: _Macro

def configure(
    *,
    reset: bool = ...,
    out_order: Literal["column", "line"] = ...,
    out_format: Literal["text", "latex"] = ...,
    precision: int | None = ...,
    multiple_assignment_reduce: bool = ...,
    reduce_equ_stages: bool = ...,
    number_format: Literal["exp", "power"] = ...,
    additional_out: Literal["latex", "text"] | None = ...,
) -> str:
    """Change the display settings for the calling file or notebook.

    Same as :meth:`_Macro.configure`; module-level for symmetry and testing.
    """
    ...

# --- settings: options and the per-scope store ------------------------------
@dataclass(frozen=True)
class DisplaySettings:
    out_order: Literal["column", "line"] = ...
    out_format: Literal["text", "latex"] = ...
    precision: int | None = ...
    multiple_assignment_reduce: bool = ...
    reduce_equ_stages: bool = ...
    number_format: Literal["exp", "power"] = ...
    additional_out: Literal["latex", "text"] | None = ...

class SettingsStore:
    ANY_FILE: str
    scopes: dict[str, DisplaySettings]
    @classmethod
    def key_for_filename(cls, filename: Any) -> str: ...
    @classmethod
    def key_for_globals(cls, globals_: Any) -> str: ...
    @classmethod
    def settings_for(cls, key: str) -> DisplaySettings: ...
    @classmethod
    def update(cls, key: str, **changes: Any) -> DisplaySettings: ...
    @classmethod
    def reset(cls, key: str) -> DisplaySettings: ...
    @classmethod
    def snapshot(cls) -> dict[str, DisplaySettings]: ...
    @classmethod
    def restore(cls, snapshot: dict[str, DisplaySettings]) -> None: ...

# --- numbers: precision and power-of-ten notation --------------------------
def is_real_number(value: Any) -> bool: ...

class SignificantDigits:
    @staticmethod
    def format(value: Any, digits: int) -> str | None: ...

class PowerOfTen:
    SMALLEST_PLAIN_EXPONENT: int
    LARGEST_PLAIN_EXPONENT: int
    @classmethod
    def rewrite(cls, text: str) -> str: ...
    @classmethod
    def fill_template(cls, template: str, values: Any) -> str: ...

# --- LaTeX: optional rendering ---------------------------------------------
class LatexRenderer:
    @staticmethod
    def display(text: str) -> None: ...
    @staticmethod
    def to_source(text: str) -> str | None: ...
    @staticmethod
    def to_pytex_input(text: str) -> str: ...
    @staticmethod
    def patch_pytexit() -> None: ...

# --- source: exact text and in-place substitution --------------------------
class SourceText:
    override: Any
    text: str | None
    def __init__(self, text: str | None) -> None: ...
    @classmethod
    def read(cls, filename: str) -> str | None: ...
    def text_of(self, node: Any) -> str: ...
    def placeholder_template(self, segment: str, node: Any) -> tuple[str, list[Any]]: ...

class InPlaceSubstitution:
    source: str
    template: str
    occurrences: list[Any]
    def __init__(self, source_text: SourceText, node: Any) -> None: ...

# --- presentation: report, layouts, output, runtime hooks -------------------
@dataclass(frozen=True)
class ExpressionReport:
    name: str
    source_text: str
    substituted_text: str
    value_text: str

class ReportLayout:
    @staticmethod
    def for_settings(settings: DisplaySettings) -> ReportLayout: ...
    def lines(self, report: ExpressionReport, *, for_latex: bool = ...,
              drop_repeated: bool = ...) -> list[str]: ...

class ColumnLayout(ReportLayout): ...
class SingleLineLayout(ReportLayout): ...

def drop_adjacent_repeats(parts: list[str]) -> list[str]: ...

class LineOutput:
    @staticmethod
    def for_format(out_format: Literal["text", "latex"]) -> LineOutput: ...
    def show(self, text: str) -> None: ...

class PlainTextOutput(LineOutput): ...

class LatexOutput(LineOutput): ...

class Presenter:
    OPAQUE_TYPES: tuple[type, ...]
    @classmethod
    def value_text(cls, key: str, value: Any) -> str: ...
    @classmethod
    def name_text(cls, key: str, name: str, value: Any) -> str: ...
    @classmethod
    def substituted_text(cls, key: str, normal: str, reduced: str,
                         *values: str) -> str: ...
    @classmethod
    def show(cls, key: str, name: str, source: str, substituted: str,
             value: Any) -> Any: ...
    @staticmethod
    def show_raw(text: str, out_format: Literal["latex", "text"]) -> None: ...

# --- expansion: the macro itself -------------------------------------------
class MacroExpander:
    scope_key: str
    source_text: SourceText
    def __init__(self, expander: Any) -> None: ...
    def expand(self, expr: Any) -> Any: ...
    @staticmethod
    def collect(*values: Any) -> tuple[Any, ...]: ...
