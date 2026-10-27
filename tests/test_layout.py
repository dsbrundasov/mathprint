"""Tests for the opt-in layout switch (``mpt.configure(out_order=...)``).

The default is a *column* of lines (source, substitution, value).
``mpt.configure(out_order="line")`` switches the calling file to a single line,
the name appearing once::

    x = 3 + y = 3 + 5 = 8
"""

import os

from mathprint import mpt
from mathprint_main import LatexOutput, SettingsStore

_HERE = os.path.abspath(__file__)


# --- Default: a column ------------------------------------------------------

def test_default_is_a_column(capsys):
    y = 5
    result = mpt[x := 3 + y]
    assert capsys.readouterr().out.splitlines() == ["x := 3 + y", "x := 3 + 5", "x := 8"]
    assert result == 8


# --- The `out_order` option ------------------------------------------------

def test_line_option_enable_disable():
    assert mpt.configure(out_order="line") == _HERE
    assert SettingsStore.settings_for(_HERE).out_order == "line"
    assert mpt.configure(out_order="column") == _HERE
    assert SettingsStore.settings_for(_HERE).out_order == "column"


def test_other_file_is_unaffected(capsys):
    SettingsStore.update(os.path.abspath("some_other_file.py"), out_order="line")
    result = mpt[2 + 3]
    assert capsys.readouterr().out.splitlines() == ["2 + 3", "2 + 3", "5"]
    assert result == 5


# --- One line: the documented shape -----------------------------------------

def test_line_assignment_matches_documented_shape(capsys):
    y = 5
    mpt.configure(out_order="line")
    result = mpt[x := 3 + y]
    assert capsys.readouterr().out.splitlines() == ["x = 3 + y = 3 + 5 = 8"]
    assert result == 8


def test_line_bare_expression(capsys):
    y = 5
    mpt.configure(out_order="line")
    result = mpt[3 + y]
    assert capsys.readouterr().out.splitlines() == ["3 + y = 3 + 5 = 8"]
    assert result == 8


def test_line_bare_expression_without_names(capsys):
    mpt.configure(out_order="line")
    result = mpt[2 + 3]
    assert capsys.readouterr().out.splitlines() == ["2 + 3 = 2 + 3 = 5"]
    assert result == 5


def test_line_keeps_exact_parentheses(capsys):
    L_min = 3
    mpt.configure(out_order="line")
    mpt[L_diff := (L_11 := (L_12 := 2 * L_min))]
    assert capsys.readouterr().out.splitlines() == [
        "L_diff = (L_11 := (L_12 := 2 * L_min)) = (L_11 := (L_12 := 2 * 3)) = 6"
    ]


def test_line_sequence(capsys):
    a = 2
    b = 3
    mpt.configure(out_order="line")
    result = mpt[c := a + b, C := c * 2, c + C]
    assert capsys.readouterr().out.splitlines() == [
        "c = a + b = 2 + 3 = 5",
        "C = c * 2 = 5 * 2 = 10",
        "c + C = 5 + 10 = 15",
    ]
    assert result == (5, 10, 15)


def test_line_with_precision(capsys):
    mpt.configure(out_order="line", precision=3)
    result = mpt[q := 1 / 3]
    assert capsys.readouterr().out.splitlines() == ["q = 1 / 3 = 1 / 3 = 0.333"]
    assert result == 1 / 3


def test_line_returns_value(capsys):
    mpt.configure(out_order="line")
    y = 5
    assert mpt[x := 3 + y] == 8


# --- One line + LaTeX: join with `==` so py2tex renders `=` -----------------

def test_line_latex_joins_with_equals(monkeypatch):
    shown = []
    monkeypatch.setattr(LatexOutput, "show", shown.append)
    y = 5
    mpt.configure(out_order="line", out_format="latex")
    mpt[x := 3 + y]
    assert shown == ["x == 3 + y == 3 + 5 == 8"]
