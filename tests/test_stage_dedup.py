"""Tests for ``mpt.configure(reduce_equ_stages=True)``.

A one-line result joins the stages with ``=``. When two adjacent stages are
textually identical (typically the substitution and the value after a nested
assignment collapse), the option drops the repeat::

    ro1 = (ro := (ro_БФСС := 2230)) = 2230 = 2230   # default
    ro1 = (ro := (ro_БФСС := 2230)) = 2230          # enabled

Column mode is unaffected: it always shows one stage per line.
"""

from mathprint import mpt
from mathprint_main import LatexOutput


# --- Default: the repeat is kept -------------------------------------------

def test_default_keeps_the_repeat(capsys):
    mpt.configure(out_order="line")
    mpt[ro1 := (ro := (ro_БФСС := 2230))]
    assert capsys.readouterr().out.splitlines() == [
        "ro1 = (ro := (ro_БФСС := 2230))"
        " = (ro := (ro_БФСС := 2230))"
        " = 2230"
    ]


# --- Enabled ---------------------------------------------------------------

def test_enabled_drops_the_repeated_stage(capsys):
    mpt.configure(out_order="line", reduce_equ_stages=True)
    mpt[ro1 := (ro := (ro_БФСС := 2230))]
    assert capsys.readouterr().out.splitlines() == [
        "ro1 = (ro := (ro_БФСС := 2230)) = 2230"
    ]


def test_enabled_combines_with_multiple_assignment_reduce(capsys):
    mpt.configure(
        out_order="line",
        multiple_assignment_reduce=True,
        reduce_equ_stages=True,
    )
    mpt[ro1 := (ro := (ro_БФСС := 2230))]
    assert capsys.readouterr().out.splitlines() == [
        "ro1 = (ro := (ro_БФСС := 2230)) = 2230"
    ]


def test_enabled_collapses_a_fully_literal_expression(capsys):
    mpt.configure(out_order="line", reduce_equ_stages=True)
    assert mpt[2230] == 2230
    assert capsys.readouterr().out.splitlines() == ["2230"]


def test_enabled_leaves_distinct_stages_alone(capsys):
    mpt.configure(out_order="line", reduce_equ_stages=True)
    y = 5
    result = mpt[x := 3 + y]
    assert capsys.readouterr().out.splitlines() == ["x = 3 + y = 3 + 5 = 8"]
    assert result == 8


def test_enabled_drops_an_identical_source_and_substitution(capsys):
    mpt.configure(out_order="line", reduce_equ_stages=True)
    mpt[2 + 3]
    assert capsys.readouterr().out.splitlines() == ["2 + 3 = 5"]


# --- Column mode is untouched ----------------------------------------------

def test_column_mode_keeps_three_lines(capsys):
    mpt.configure(reduce_equ_stages=True)
    mpt[ro1 := (ro := (ro_БФСС := 2230))]
    assert capsys.readouterr().out.splitlines() == [
        "ro1 := (ro := (ro_БФСС := 2230))",
        "ro1 := (ro := (ro_БФСС := 2230))",
        "ro1 := 2230",
    ]


# --- LaTeX ----------------------------------------------------------------

def test_enabled_works_in_latex_line_mode(monkeypatch):
    shown = []
    monkeypatch.setattr(LatexOutput, "show", shown.append)
    mpt.configure(
        out_order="line", out_format="latex", reduce_equ_stages=True
    )
    mpt[x := 3]
    # Distinct stages only; joined with `==` for pytexit.
    assert shown == ["x == 3"]


# --- Turning it off again --------------------------------------------------

def test_can_be_disabled(capsys):
    mpt.configure(out_order="line", reduce_equ_stages=True)
    mpt.configure(reduce_equ_stages=False)
    mpt[ro1 := (ro := (ro_БФСС := 2230))]
    assert capsys.readouterr().out.splitlines() == [
        "ro1 = (ro := (ro_БФСС := 2230))"
        " = (ro := (ro_БФСС := 2230))"
        " = 2230"
    ]
