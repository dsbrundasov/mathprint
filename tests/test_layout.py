"""Tests for the opt-in layout switch (``mpt.to_line()`` / ``mpt.to_column()``).

The default is a *column* of lines (source, substitution, value). ``mpt.to_line()``
switches the calling file to a single line, the name appearing once::

    x = 3 + y = 3 + 5 = 8
"""

import os

import pytest

import mathprint_main
from mathprint import mpt

_HERE = os.path.abspath(__file__)


@pytest.fixture(autouse=True)
def restore_layout_files():
    """Keep layout state isolated per test."""
    saved = set(mathprint_main.Printer.line_scopes)
    mathprint_main.Printer.line_scopes.clear()
    yield
    mathprint_main.Printer.line_scopes.clear()
    mathprint_main.Printer.line_scopes.update(saved)


# --- Default: a column ------------------------------------------------------

def test_default_is_a_column(capsys):
    y = 5
    result = mpt[x := 3 + y]
    assert capsys.readouterr().out.splitlines() == ["x := 3 + y", "x := 3 + 5", "x := 8"]
    assert result == 8


# --- The `mpt.to_line()` / `mpt.to_column()` switches -----------------------

def test_line_switch_enable_disable():
    assert mpt.to_line() == _HERE
    assert mathprint_main.Printer.line_on(_HERE)
    assert mpt.to_column() == _HERE
    assert not mathprint_main.Printer.line_on(_HERE)


def test_other_file_is_unaffected(capsys):
    mathprint_main.Printer.line_scopes.add(os.path.abspath("some_other_file.py"))
    result = mpt[2 + 3]
    assert capsys.readouterr().out.splitlines() == ["2 + 3", "2 + 3", "5"]
    assert result == 5


# --- One line: the documented shape -----------------------------------------

def test_line_assignment_matches_documented_shape(capsys):
    y = 5
    mpt.to_line()
    result = mpt[x := 3 + y]
    assert capsys.readouterr().out.splitlines() == ["x = 3 + y = 3 + 5 = 8"]
    assert result == 8


def test_line_bare_expression(capsys):
    y = 5
    mpt.to_line()
    result = mpt[3 + y]
    assert capsys.readouterr().out.splitlines() == ["3 + y = 3 + 5 = 8"]
    assert result == 8


def test_line_bare_expression_without_names(capsys):
    mpt.to_line()
    result = mpt[2 + 3]
    assert capsys.readouterr().out.splitlines() == ["2 + 3 = 2 + 3 = 5"]
    assert result == 5


def test_line_keeps_exact_parentheses(capsys):
    L_min = 3
    mpt.to_line()
    mpt[L_diff := (L_11 := (L_12 := 2 * L_min))]
    assert capsys.readouterr().out.splitlines() == [
        "L_diff = (L_11 := (L_12 := 2 * L_min)) = (L_11 := (L_12 := 2 * 3)) = 6"
    ]


def test_line_sequence(capsys):
    a = 2
    b = 3
    mpt.to_line()
    result = mpt[c := a + b, C := c * 2, c + C]
    assert capsys.readouterr().out.splitlines() == [
        "c = a + b = 2 + 3 = 5",
        "C = c * 2 = 5 * 2 = 10",
        "c + C = 5 + 10 = 15",
    ]
    assert result == (5, 10, 15)


def test_line_with_precision(capsys):
    mpt.to_line()
    mathprint_main.Printer.precision_scopes[_HERE] = 3
    try:
        result = mpt[q := 1 / 3]
        assert capsys.readouterr().out.splitlines() == ["q = 1 / 3 = 1 / 3 = 0.333"]
        assert result == 1 / 3
    finally:
        mathprint_main.Printer.precision_scopes.pop(_HERE, None)


def test_line_returns_value(capsys):
    mpt.to_line()
    y = 5
    assert mpt[x := 3 + y] == 8


# --- One line + LaTeX: join with `==` so py2tex renders `=` -----------------

def test_line_latex_joins_with_equals(monkeypatch):
    shown = []
    monkeypatch.setattr(mathprint_main.Latex, "show", shown.append)
    y = 5
    mpt.to_line()
    mpt.latex()
    try:
        mpt[x := 3 + y]
        assert shown == ["x == 3 + y == 3 + 5 == 8"]
    finally:
        mathprint_main.Printer.latex_scopes.discard(_HERE)
