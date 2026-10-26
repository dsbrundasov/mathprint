"""Type stubs for the ``mathprint`` macros.

``mpt`` is a macro: it is invoked as ``mpt[expression]``, which static type
checkers would otherwise report as subscripting a function.
"""

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
        out_order: Literal["column", "line"] = ...,
        out_format: Literal["text", "latex"] = ...,
        precision: int | None = ...,
        multiple_assignment_reduce: bool = ...,
        reduce_equ_stages: bool = ...,
        number_format: Literal["exp", "power"] = ...,
    ) -> str:
        """Change the display settings for the file (or notebook) this is called in.

        The settings apply to every ``mpt[...]`` in the calling scope -- the
        file, or the whole notebook in Jupyter -- and never leak into other
        modules. Every argument is optional: an omitted argument is left
        unchanged.

        Args:
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

# --- Numbers: display formatting of plain numbers -------------------------
class Numbers:
    @staticmethod
    def is_real_number(value: Any) -> bool: ...
    @staticmethod
    def format(value: Any, digits: int) -> str | None: ...
    @staticmethod
    def to_power(text: str) -> str: ...

# --- LaTeX: optional rendering of one line --------------------------------
class Latex:
    @staticmethod
    def show(text: str) -> None: ...
    @staticmethod
    def _to_input(text: str) -> str: ...
    @staticmethod
    def _patch_pytexit() -> None: ...

# --- Printer: the output, per scope ---------------------------------------
class Printer:
    ANY_FILE: str
    line_scopes: set[str]
    latex_scopes: set[str]
    precision_scopes: dict[str, int]
    multiple_assignment_reduce_scopes: set[str]
    reduce_equ_stages_scopes: set[str]
    power_number_scopes: set[str]
    OPAQUE_TYPES: tuple[type, ...]
    @classmethod
    def key_of(cls, filename: Any) -> str: ...
    @classmethod
    def key_of_globals(cls, globals_: Any) -> str: ...
    @classmethod
    def set_line(cls, key: str, on: bool = ...) -> str: ...
    @classmethod
    def set_latex(cls, key: str, enabled: bool = ...) -> str: ...
    @classmethod
    def set_precision(cls, key: str, digits: int | None = ...) -> str: ...
    @classmethod
    def set_multiple_assignment_reduce(cls, key: str, on: bool = ...) -> str: ...
    @classmethod
    def set_reduce_equ_stages(cls, key: str, on: bool = ...) -> str: ...
    @classmethod
    def set_number_format(cls, key: str, number_format: Literal["exp", "power"] = ...) -> str: ...
    @classmethod
    def line_on(cls, key: str) -> bool: ...
    @classmethod
    def latex_on(cls, key: str) -> bool: ...
    @classmethod
    def precision_of(cls, key: str) -> int | None: ...
    @classmethod
    def multiple_assignment_reduce_on(cls, key: str) -> bool: ...
    @classmethod
    def reduce_equ_stages_on(cls, key: str) -> bool: ...
    @classmethod
    def number_format_of(cls, key: str) -> Literal["exp", "power"]: ...
    @classmethod
    def render(cls, key: str, name: str, value: Any) -> str: ...
    @classmethod
    def text(cls, key: str, value: Any) -> str: ...
    @classmethod
    def _apply_number_format(cls, key: str, value: Any, shown: str) -> str: ...
    @classmethod
    def substituted(cls, key: str, normal: str, reduced: str, *values: str) -> str: ...
    @classmethod
    def emit(cls, key: str, text: str) -> None: ...
    @classmethod
    def show(cls, key: str, name: str, source: str, substituted: str, value: Any) -> Any: ...

# --- Source: the exact text an expression was written in ------------------
class Source:
    # Set by the Jupyter extension during cell expansion.
    override: Any
    def __init__(self, text: str | None) -> None: ...
    @classmethod
    def read(cls, filename: str) -> str | None: ...
    def segment(self, node: Any) -> str: ...
    def template(self, segment: str, node: Any) -> tuple[str, list[Any]]: ...

# --- Expander: the macro itself -------------------------------------------
class Expander:
    def __init__(self, expander: Any) -> None: ...
    def expand(self, expr: Any) -> Any: ...
    @staticmethod
    def collect(*values: Any) -> tuple[Any, ...]: ...

# --- The macro ------------------------------------------------------------
def _configure(
    *,
    out_order: str = ...,
    out_format: str = ...,
    precision: int | None = ...,
    multiple_assignment_reduce: bool = ...,
    reduce_equ_stages: bool = ...,
    number_format: Literal["exp", "power"] = ...,
) -> str: ...
