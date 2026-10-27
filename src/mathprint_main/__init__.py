"""The ``mpt`` macro: pretty-print math expressions in reports.

``mpt`` renders an expression in three phases:

  1. **Source.** The expression *exactly as written at the use site*, taken
     verbatim from the source file (no reformatting, no added or removed
     spaces or parentheses).

  2. **Substitution.** The same expression with each local variable replaced
     *in place* by its current value.  Nothing is evaluated or simplified here;
     only names are textually substituted, and their order is preserved
     exactly.

  3. **Evaluation.** The expression itself is evaluated once, its value is
     printed (with the ``name := `` prefix in the assignment form, matching
     phases 1 and 2), and that value becomes the value of the whole macro call
     (so it can be assigned or printed).

Those three phases with ``str(value)`` are the **core**; every other behaviour
is an opt-in display setting (see `Configuration` below).  Import the macro with
the one-line bootstrap::

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
exact source substring of the expression.  Each *loaded* name occurrence is
replaced, in place, by a positional ``str.format`` placeholder, and the
occurrences are collected in source order (by their byte offset in the file),
then sorted by that offset.  The placeholders are filled, positionally, with the
values of those very same occurrences.  Because the i-th placeholder is by
construction the i-th source occurrence, the i-th value necessarily lands in the
i-th slot: the order of variables in the output is identical to the order in
which they appear in the source -- regardless of the surrounding operators
(including comparisons) and regardless of what the values are (numbers, sympy
symbols, ...).  No evaluation, arithmetic, or symbolic simplification happens in
this phase, so nothing can move around.  Store-context names (e.g. a
comprehension target, or the target of an assignment ``mpt[name := ...]``) are
not substituted, because they are being bound, not read.

**Modules, functions and classes are not expanded (phase 2).** If a name refers
to a module, function, method, built-in, class or other callable, it is left as
written: ``mpt[math.floor(y)]`` prints ``math.floor(5)`` (not
``<module 'math' …>.floor(5)``), ``mpt[f(y)]`` prints ``f(5)`` (not
``<function f at 0x…>(5)``), and ``mpt[int(y)]`` prints ``int(5)`` (not
``<class 'int'>(5)``).  A *dotted chain* rooted at a name is one occurrence and
is substituted as a unit: ``mpt[me.H.atomic_number]`` prints
``me.H.atomic_number`` then ``1``, since the chain's value is a plain number.

**Configuration (opt-in, per file).** Output is plain text, in a column, at full
precision by default -- that is the core.  ``mpt.configure(...)`` layers options
on top of it for *the file where the call appears* (or the whole notebook in
Jupyter), for every ``mpt[...]`` in that scope::

    mpt.configure(out_order="line", out_format="latex", precision=4)

Every argument is optional; an omitted argument is left unchanged.
``out_order`` is ``"column"`` (the default: source, substitution and value on
separate lines) or ``"line"`` (one line, the name appearing once:
``x = 3 + y = 3 + 5 = 8``).  ``out_format`` is ``"text"`` (the default) or
``"latex"``, in which case each line is converted with ``pytexit.py2tex`` and
shown via ``IPython.display``, the ``display(Latex(py2tex(...)))`` recipe;
nothing here imports ``pytexit`` unless LaTeX mode is actually used.
``precision=n`` rounds the numbers *shown* by phases 2 and 3 to ``n`` significant
digits (``3.123123412`` prints as ``3.123`` for ``n=4``) without affecting the
value; ``precision=None`` restores the default.
``multiple_assignment_reduce=True`` collapses a chain of assignments (e.g.
``ro1 := (ro := (ro_БФСС := 2230))``) to the value of the innermost assignment in
phase 2 (``ro1 := 2230``); phase 1 still shows the chain as written.
``reduce_equ_stages=True`` drops repeated adjacent stages from a one-line result
(``ro1 = (ro := (...)) = 2230 = 2230`` becomes ``ro1 = (ro := (...)) = 2230``).
``number_format="power"`` shows real numbers with a power of ten: scientific
notation becomes ``1.23*10**-9`` and a plain decimal far from ``1`` (below
``10**-4`` or at/above ``10**16``) is normalized, e.g. ``0.0001106`` ->
``1.106*10**-4``; it applies to all three phases.
``additional_out="latex"`` (or ``"text"``) prints the same lines again, after the
main output, as raw LaTeX source or plain Python; ``None`` (the default) adds
nothing.
``reset=True`` drops every option of the scope first, returning it to the core;
it can be combined with other arguments, which then apply on top.
``mpt.configure(...)`` returns the scope key it changed.

**How the code is laid out.** Each module has one job:

  * :mod:`mathprint_main.settings` -- :class:`DisplaySettings` (the options,
    defaults = the core) and :class:`SettingsStore` (scope -> settings).
  * :mod:`mathprint_main.source` -- :class:`SourceText` (the exact source) and
    :class:`InPlaceSubstitution` (phase 2's template and occurrences).
  * :mod:`mathprint_main.presentation` -- :class:`ExpressionReport` (the three
    phases), the layout/output strategies, and :class:`Presenter` (the runtime
    hooks: render a value, fill phase 2, show the report).
  * :mod:`mathprint_main.numbers` -- :class:`SignificantDigits` and
    :class:`PowerOfTen` (the two optional number formats).
  * :mod:`mathprint_main.latex` -- :class:`LatexRenderer` (the optional LaTeX
    converter, the only place that imports ``pytexit``/``IPython``);
    :class:`LatexOutput` in ``presentation`` is the strategy that routes lines
    to it.
  * :mod:`mathprint_main.expansion` -- :class:`MacroExpander`, which turns one
    ``mpt[...]`` into the run-time ``Presenter`` calls.

``mpt`` is a one-line wrapper over :class:`MacroExpander`; ``configure`` is a
one-line wrapper over :class:`SettingsStore`.  The expanded code only calls
:meth:`Presenter.name_text`, :meth:`Presenter.substituted_text` and
:meth:`Presenter.show`, so an option that is off costs one branch at run time
and nothing at expansion time.
"""

import ast
import sys
from typing import Any, Literal, TypeVar

from .expansion import MacroExpander
from .latex import LatexRenderer
from .numbers import PowerOfTen, SignificantDigits, is_real_number
from .presentation import (
    ColumnLayout,
    ExpressionReport,
    LatexOutput,
    Presenter,
    SingleLineLayout,
)
from .settings import DisplaySettings, SettingsStore
from .source import InPlaceSubstitution, SourceText


def mpt(expr: ast.expr, **kw: Any) -> ast.expr:
    """The ``mpt`` macro.

    A single ``mpt[expression]`` prints three lines and yields the value.  The
    multi-expression form ``mpt[a, b, ...]`` prints each item exactly as if it
    had its own ``mpt[...]`` call -- in order -- and yields a tuple of the
    values, one per item.
    """
    return MacroExpander(kw.get("expander")).expand(expr)


class _Unset:
    """The type of :data:`_UNSET`: "this ``configure`` argument was not given"."""


#: Default for every ``configure`` argument: "this option was not given", so it
#: must be left unchanged.  A given value is validated at run time (the public
#: types live in `__init__.pyi`).
_UNSET = _Unset()


def configure(
    *,
    reset: bool = False,
    out_order: Literal["column", "line"] | _Unset = _UNSET,
    out_format: Literal["text", "latex"] | _Unset = _UNSET,
    precision: int | None | _Unset = _UNSET,
    multiple_assignment_reduce: bool | _Unset = _UNSET,
    reduce_equ_stages: bool | _Unset = _UNSET,
    number_format: Literal["exp", "power"] | _Unset = _UNSET,
    additional_out: Literal["latex", "text"] | None | _Unset = _UNSET,
) -> str:
    """Change the display settings for the file (or notebook) this is called in.

    The settings apply to every ``mpt[...]`` in the calling scope -- the file,
    or the whole notebook in Jupyter -- and never leak into other modules. Every
    argument is optional: an omitted argument is left unchanged.

    Args:
        reset: ``True`` drops every option of the scope first, returning it to
            the core output; other arguments then apply on top. Default
            ``False`` (change only what is given).
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
        reduce_equ_stages: ``True`` drops repeated adjacent stages from a
            one-line result: ``ro1 = (ro := (...)) = 2230 = 2230`` becomes
            ``ro1 = (ro := (...)) = 2230``. Has no effect in column mode.
            Default ``False``.
        number_format: ``"exp"`` (default) keeps ``str``'s numbers as they are;
            ``"power"`` shows real numbers with a power of ten: scientific
            notation becomes ``1.23*10**-9`` and a plain decimal far from ``1``
            (below ``10**-4`` or at/above ``10**16``) is normalized, e.g.
            ``0.0001106`` -> ``1.106*10**-4``. Applies to every phase.
        additional_out: ``None`` (default) adds nothing. ``"latex"`` prints the
            same lines again, after the main output, as raw LaTeX source;
            ``"text"`` prints them as the plain Python line. The additional
            output is never rendered and uses every other setting unchanged.

    Returns:
        The scope key that changed: the file's absolute path, or ``"<ipython>"``
        in a notebook.

    Raises:
        ValueError: If a value is not one of the allowed ones.
    """
    key = SettingsStore.key_for_globals(sys._getframe(1).f_globals)

    # Validate every given option first, so that a bad value changes nothing.
    if not isinstance(reset, bool):
        raise ValueError("mpt.configure(reset=...) expects True or False")

    changes: dict[str, Any] = {}
    if not isinstance(out_order, _Unset):
        changes["out_order"] = _require_choice(
            "out_order", out_order, ("column", "line")
        )
    if not isinstance(out_format, _Unset):
        changes["out_format"] = _require_choice(
            "out_format", out_format, ("text", "latex")
        )
    if not isinstance(precision, _Unset):
        changes["precision"] = _require_positive_digits_or_none(
            "precision", precision
        )
    if not isinstance(multiple_assignment_reduce, _Unset):
        changes["multiple_assignment_reduce"] = _require_bool(
            "multiple_assignment_reduce", multiple_assignment_reduce
        )
    if not isinstance(reduce_equ_stages, _Unset):
        changes["reduce_equ_stages"] = _require_bool(
            "reduce_equ_stages", reduce_equ_stages
        )
    if not isinstance(number_format, _Unset):
        changes["number_format"] = _require_choice(
            "number_format", number_format, ("exp", "power")
        )
    if not isinstance(additional_out, _Unset):
        changes["additional_out"] = _require_choice(
            "additional_out", additional_out, (None, "latex", "text")
        )

    # Apply: `reset=True` drops the scope's own entry, then the new options
    # (if any) are stored on top of whatever the scope falls back to.
    if reset:
        SettingsStore.reset(key)
    if changes:
        SettingsStore.update(key, **changes)
    return key


_T = TypeVar("_T")


def _require_choice(option_name: str, value: Any, allowed: tuple[_T, ...]) -> _T:
    """`value` if it is one of `allowed`, else raise a ``ValueError``."""
    if value not in allowed:
        options = ", ".join(repr(option) for option in allowed)
        raise ValueError(
            f"mpt.configure({option_name}=...) expects one of: {options}"
        )
    return value


def _require_bool(option_name: str, value: Any) -> bool:
    """`value` if it is a ``bool``, else raise a ``ValueError``."""
    if not isinstance(value, bool):
        raise ValueError(f"mpt.configure({option_name}=...) expects True or False")
    return value


def _require_positive_digits_or_none(option_name: str, value: Any) -> int | None:
    """`value` as a positive ``int``, or ``None`` for full precision."""
    if value is None:
        return None
    digits = int(value)
    if digits < 1:
        raise ValueError(
            f"mpt.configure({option_name}=...) needs a positive number of "
            "significant digits"
        )
    return digits


# `mpt.configure(...)` groups the per-file display settings. It is attached as an
# attribute of the macro function, so it is available wherever `mpt` itself is
# (e.g. `from mathprint import mpt`). (`setattr`, so the type checker, which sees
# `mpt` as a plain function, stays happy.)
setattr(mpt, "configure", configure)
