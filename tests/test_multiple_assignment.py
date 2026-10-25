"""Tests for ``mpt.configure(multiple_assignment_reduce=True)``.

A direct chain of assignments in one ``mpt[...]`` call, such as
``ro1 := (ro := (ro_БФСС := 2230))``, evaluates to the innermost value. By
default phase 2 repeats the whole chain; with the option enabled it collapses to
``ro1 := 2230``, like a single assignment. Phase 1 always keeps the chain as
written.
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
    )
    mathprint_main.Printer.line_scopes.clear()
    mathprint_main.Printer.latex_scopes.clear()
    mathprint_main.Printer.multiple_assignment_reduce_scopes.clear()
    yield
    mathprint_main.Printer.line_scopes.clear()
    mathprint_main.Printer.line_scopes.update(saved[0])
    mathprint_main.Printer.latex_scopes.clear()
    mathprint_main.Printer.latex_scopes.update(saved[1])
    mathprint_main.Printer.multiple_assignment_reduce_scopes.clear()
    mathprint_main.Printer.multiple_assignment_reduce_scopes.update(saved[2])


# --- Default: the chain is repeated ----------------------------------------

def test_default_column_repeats_the_chain(capsys):
    result = mpt[ro1 := (ro := (ro_БФСС := 2230))]
    assert capsys.readouterr().out.splitlines() == [
        "ro1 := (ro := (ro_БФСС := 2230))",
        "ro1 := (ro := (ro_БФСС := 2230))",
        "ro1 := 2230",
    ]
    assert result == 2230
    assert ro1 == 2230 and ro == 2230 and ro_БФСС == 2230


def test_default_line_repeats_the_chain(capsys):
    mpt.configure(out_order="line")
    mpt[ro1 := (ro := (ro_БФСС := 2230))]
    assert capsys.readouterr().out.splitlines() == [
        "ro1 = (ro := (ro_БФСС := 2230))"
        " = (ro := (ro_БФСС := 2230))"
        " = 2230"
    ]


# --- Enabled: phase 2 collapses to the innermost value ---------------------

def test_enabled_column_collapses_the_chain(capsys):
    mpt.configure(multiple_assignment_reduce=True)
    result = mpt[ro1 := (ro := (ro_БФСС := 2230))]
    assert capsys.readouterr().out.splitlines() == [
        "ro1 := (ro := (ro_БФСС := 2230))",
        "ro1 := 2230",
        "ro1 := 2230",
    ]
    assert result == 2230


def test_enabled_line_collapses_the_chain(capsys):
    mpt.configure(out_order="line", multiple_assignment_reduce=True)
    mpt[ro1 := (ro := (ro_БФСС := 2230))]
    assert capsys.readouterr().out.splitlines() == [
        "ro1 = (ro := (ro_БФСС := 2230)) = 2230 = 2230"
    ]


def test_enabled_substitutes_names_in_the_collapsed_form(capsys):
    x = 5
    mpt.configure(multiple_assignment_reduce=True)
    mpt[a := (b := x + 1)]
    assert capsys.readouterr().out.splitlines() == [
        "a := (b := x + 1)",
        "a := 5 + 1",
        "a := 6",
    ]


def test_default_substitutes_names_in_the_full_chain(capsys):
    x = 5
    mpt[a := (b := x + 1)]
    assert capsys.readouterr().out.splitlines() == [
        "a := (b := x + 1)",
        "a := (b := 5 + 1)",
        "a := 6",
    ]


def test_enabled_handles_a_deeper_chain(capsys):
    mpt.configure(multiple_assignment_reduce=True)
    mpt[d := (c := (b := 2230))]
    assert capsys.readouterr().out.splitlines() == [
        "d := (c := (b := 2230))",
        "d := 2230",
        "d := 2230",
    ]


# --- Everything else is left alone ----------------------------------------

def test_single_assignment_is_unaffected(capsys):
    x = 5
    mpt.configure(multiple_assignment_reduce=True)
    mpt[a := x + 1]
    assert capsys.readouterr().out.splitlines() == [
        "a := x + 1",
        "a := 5 + 1",
        "a := 6",
    ]


def test_assignment_inside_a_larger_expression_is_unaffected(capsys):
    mpt.configure(multiple_assignment_reduce=True)
    mpt[(b := 3) + 1]
    assert capsys.readouterr().out.splitlines() == [
        "(b := 3) + 1",
        "(b := 3) + 1",
        "4",
    ]
    assert b == 3


# --- Turning it off again --------------------------------------------------

def test_can_be_disabled(capsys):
    mpt.configure(multiple_assignment_reduce=True)
    mpt.configure(multiple_assignment_reduce=False)
    mpt[ro1 := (ro := (ro_БФСС := 2230))]
    assert capsys.readouterr().out.splitlines() == [
        "ro1 := (ro := (ro_БФСС := 2230))",
        "ro1 := (ro := (ro_БФСС := 2230))",
        "ro1 := 2230",
    ]


# --- Each occurrence is still rendered only once ---------------------------

def test_occurrences_are_rendered_once(capsys):
    class Box:
        calls = 0

        @property
        def value(self):
            Box.calls += 1
            return 7

    box = Box()
    mpt.configure(multiple_assignment_reduce=True)
    mpt[a := (b := box.value)]
    # Once for phase 2, once for the evaluation itself.
    assert Box.calls == 2
