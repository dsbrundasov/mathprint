"""Tests for ``mpt.configure(reduce_equ_stages=True)``.

A one-line result joins the stages with ``=``. When two adjacent stages are
textually identical (typically the substitution and the value after a nested
assignment collapse), the option drops the repeat::

    ro1 = (ro := (ro_БФСС := 2230)) = 2230 = 2230   # default
    ro1 = (ro := (ro_БФСС := 2230)) = 2230          # enabled

Column mode is unaffected: it always shows one stage per line.
"""

import os

import pytest

import mathprint_main
from mathprint import mpt

_HERE = os.path.abspath(__file__)


@pytest.fixture(autouse=True)
def restore_settings():
    """Keep layout/LaTeX/reduce state isolated per test."""
    saved = (
        set(mathprint_main.Printer.line_scopes),
        set(mathprint_main.Printer.latex_scopes),
        set(mathprint_main.Printer.multiple_assignment_reduce_scopes),
        set(mathprint_main.Printer.reduce_equ_stages_scopes),
    )
    mathprint_main.Printer.line_scopes.clear()
    mathprint_main.Printer.latex_scopes.clear()
    mathprint_main.Printer.multiple_assignment_reduce_scopes.clear()
    mathprint_main.Printer.reduce_equ_stages_scopes.clear()
    yield
    mathprint_main.Printer.line_scopes.clear()
    mathprint_main.Printer.line_scopes.update(saved[0])
    mathprint_main.Printer.latex_scopes.clear()
    mathprint_main.Printer.latex_scopes.update(saved[1])
    mathprint_main.Printer.multiple_assignment_reduce_scopes.clear()
    mathprint_main.Printer.multiple_assignment_reduce_scopes.update(saved[2])
    mathprint_main.Printer.reduce_equ_stages_scopes.clear()
    mathprint_main.Printer.reduce_equ_stages_scopes.update(saved[3])


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
    monkeypatch.setattr(mathprint_main.Latex, "show", shown.append)
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
