"""Turning one macro call into visible lines.

The macro's runtime contract is small.  The expanded code builds an
:class:`ExpressionReport` -- phase 1 text, phase 2 text and phase 3 value -- and
:class:`Presenter` shows it according to the scope's :class:`DisplaySettings`.

The report is the *data*; the strategies are the policy:

* :class:`ColumnLayout` / :class:`SingleLineLayout` decide where the three
  phases go;
* :class:`PlainTextOutput` / :class:`LatexOutput` decide how one line is shown;
* :class:`PowerOfTen` and :class:`SignificantDigits` decide how a number looks.

The default report layout and output need no optional feature at all: they are
exactly "print the source, print the substitution, print ``str(value)``".
"""

from dataclasses import dataclass
import types

from .latex import LatexRenderer
from .numbers import PowerOfTen, SignificantDigits, is_real_number
from .settings import DisplaySettings, SettingsStore


@dataclass(frozen=True)
class ExpressionReport:
    """What one ``mpt`` call knows at run time: its three phases.

    All three are text: the value was rendered by :class:`Presenter` before the
    report is built, so a layout never has to know how a value is displayed.
    """

    #: Assignment target (``""`` when the call is a bare expression).
    name: str

    #: Phase 1: the expression exactly as written.
    source_text: str

    #: Phase 2: the same text with each loaded name replaced by its value.
    substituted_text: str

    #: Phase 3: the evaluated value, already rendered as text.
    value_text: str


class ReportLayout:
    """Place the three phases of a report on one or more lines."""

    @staticmethod
    def for_settings(settings: DisplaySettings) -> "ReportLayout":
        """The layout chosen by `settings`."""
        if settings.out_order == "line":
            return SingleLineLayout()
        return ColumnLayout()

    def lines(self, report: ExpressionReport, *, for_latex: bool,
              drop_repeated: bool) -> list[str]:
        """The lines to show.

        `for_latex` selects the one-line joiner (``==`` is what ``py2tex``
        renders as ``=``); it does not render anything.  `drop_repeated` is
        honored by :class:`SingleLineLayout` only.
        """
        raise NotImplementedError


class ColumnLayout(ReportLayout):
    """One line per phase, each carrying the ``name := `` prefix."""

    def lines(self, report, *, for_latex=False, drop_repeated=False):
        # Column mode ignores both flags: one stage per line, never repeated.
        value_line = (
            f"{report.name} := {report.value_text}"
            if report.name else report.value_text
        )
        return [report.source_text, report.substituted_text, value_line]


class SingleLineLayout(ReportLayout):
    """All three phases on one line, the name appearing once.

    ``name := 3 + y`` and ``name := 3 + 5`` lose their prefix; the joined line
    is ``name = 3 + y = 3 + 5 = 8``.
    """

    def lines(self, report, *, for_latex=False, drop_repeated=False):
        source = report.source_text
        substituted = report.substituted_text
        if report.name:
            source = source.split(":=", 1)[1].strip()
            substituted = substituted.split(":=", 1)[1].strip()
        parts = ([report.name] if report.name else []) + [
            source, substituted, report.value_text
        ]
        if drop_repeated:
            parts = drop_adjacent_repeats(parts)
        joiner = " == " if for_latex else " = "
        return [joiner.join(parts)]


def drop_adjacent_repeats(parts):
    """Keep the first part of every run of equal adjacent parts.

    ``ro1 = (ro := (...)) = 2230 = 2230`` becomes
    ``ro1 = (ro := (...)) = 2230``.
    """
    kept = []
    for part in parts:
        if not kept or kept[-1] != part:
            kept.append(part)
    return kept


class LineOutput:
    """Show one finished line (plain text, or rendered LaTeX)."""

    @staticmethod
    def for_format(out_format) -> "LineOutput":
        """The output chosen by ``out_format`` (``"text"`` or ``"latex"``)."""
        if out_format == "latex":
            return LatexOutput()
        return PlainTextOutput()

    def show(self, text):
        raise NotImplementedError


class PlainTextOutput(LineOutput):
    """Print one line with ``print``."""

    def show(self, text):
        print(text)


class LatexOutput(LineOutput):
    """Show one line as rendered LaTeX, via :class:`LatexRenderer`."""

    def show(self, text):
        LatexRenderer.display(text)


class Presenter:
    """Show an :class:`ExpressionReport` according to its scope's settings.

    The class methods are the runtime hooks called by the expanded code:
    :meth:`name_text` renders one substituted occurrence, :meth:`substituted_text`
    fills the phase-2 template, and :meth:`show` emits the report and returns the
    original value.
    """

    #: Values whose ``str`` repr is noise (``<function f at 0x…>``,
    #: ``<class 'int'>``, ``<module 'math' …>``).  For these, phase 2 keeps the
    #: *name* used in the source instead of substituting the value's repr.
    OPAQUE_TYPES = (
        types.ModuleType,           # modules
        types.FunctionType,         # def / lambda
        types.BuiltinFunctionType,  # len, math.floor (builtin_function_or_method)
        types.MethodType,           # bound method of a Python object
        type,                       # classes: int, str, MyClass
    )

    # --- rendering values ---------------------------------------------------

    @classmethod
    def value_text(cls, key, value):
        """`value` as text, with the scope's precision and number format applied."""
        settings = SettingsStore.settings_for(key)
        text = str(value)
        if settings.precision is not None:
            rounded = SignificantDigits.format(value, settings.precision)
            if rounded is not None:
                text = rounded
        if settings.number_format == "power" and is_real_number(value):
            text = PowerOfTen.rewrite(text)
        return text

    @classmethod
    def name_text(cls, key, name, value):
        """What replaces one name occurrence in phase 2.

        Modules, functions, methods, built-ins, classes and other callables are
        *not* expanded: they keep the name used in the source (``math.sqrt``
        stays ``math.sqrt``, ``f`` stays ``f``, ``int`` stays ``int``).  Every
        other value is rendered by :meth:`value_text`.
        """
        if isinstance(value, cls.OPAQUE_TYPES) or callable(value):
            return name
        return cls.value_text(key, value)

    # --- phase 2 ------------------------------------------------------------

    @classmethod
    def substituted_text(cls, key, normal, reduced, *values):
        """Fill the phase-2 template with the rendered occurrences.

        `normal` is the full substitution; `reduced` is a nested assignment
        chain collapsed to its innermost value.  Which one is used is a runtime
        setting, so the macro passes both and `values` is evaluated once.

        The template is formatted on its own, before the rendered values are
        inserted, so ``number_format="power"`` rewrites the source's numeric
        literals without touching a substituted string value.
        """
        settings = SettingsStore.settings_for(key)
        template = reduced if settings.multiple_assignment_reduce else normal
        if settings.number_format == "power":
            return PowerOfTen.fill_template(template, values)
        return template.format(*values)

    # --- phases 1-3 ---------------------------------------------------------

    @classmethod
    def show(cls, key, name, source, substituted, value):
        """Show the whole call and return `value`.

        Column mode shows the three phases on separate lines; one-line mode
        joins them (see :class:`ReportLayout`).  ``reduce_equ_stages`` drops
        repeated adjacent stages of a one-line result.

        With ``additional_out=...`` the same lines are printed again, after the
        main output, as raw text: LaTeX source (``"latex"``) or Python
        (``"text"``).
        """
        settings = SettingsStore.settings_for(key)
        if settings.number_format == "power":
            # Phase 1 is the source, whose numeric literals are shown in the
            # same format (the phase-2 template does this in `substituted_text`).
            source = PowerOfTen.rewrite(source)
        report = ExpressionReport(
            name=name,
            source_text=source,
            substituted_text=substituted,
            value_text=cls.value_text(key, value),
        )

        layout = ReportLayout.for_settings(settings)
        main_output = LineOutput.for_format(settings.out_format)
        for line in layout.lines(
            report,
            for_latex=settings.out_format == "latex",
            drop_repeated=settings.reduce_equ_stages,
        ):
            main_output.show(line)

        if settings.additional_out is not None:
            # The raw copy is laid out again, because it follows its own
            # format's joining rule; the report itself is unchanged.
            for line in layout.lines(
                report,
                for_latex=settings.additional_out == "latex",
                drop_repeated=settings.reduce_equ_stages,
            ):
                cls.show_raw(line, settings.additional_out)
        return value

    @staticmethod
    def show_raw(text, out_format):
        """Print one line raw: LaTeX source, or the plain Python line.

        Raw output is never rendered: ``"latex"`` prints the ``py2tex`` result
        itself (falling back to `text` if it cannot convert), and ``"text"``
        prints the Python line.
        """
        if out_format == "latex":
            tex = LatexRenderer.to_source(text)
            print(text if tex is None else tex)
        else:
            print(text)
