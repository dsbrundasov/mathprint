# pyright: reportUnusedExpression=false
"""Tests for the block form ``with mpt:``.

The block applies the same three-phase display as ``mpt[...]`` to every
statement in its body.  The one addition is that an assignment may use a plain
``=`` (the expression form needs the walrus ``:=`` to bind a name)::

    with mpt:
        x = 3 + y
        obj.field = x * 2

A bare expression is displayed exactly as ``mpt[expression]`` would display it.
Statements that have no expression form (``if``, ``for``, ``def``, ``+=``,
annotated assignments) are left untouched.
"""

import ast

import pytest
from mcpyrate.core import MacroExpansionError

import mathprint_main
from mathprint import mpt
from mathprint_main import LatexOutput, LatexRenderer


class _Expander:
    """Stands in for mcpyrate's expander in a direct macro call."""

    filename = None


# --- Assignments ------------------------------------------------------------

def test_assignment_is_a_column(capsys):
    y = 5
    with mpt:
        x = 3 + y
    assert capsys.readouterr().out.splitlines() == [
        "x = 3 + y", "x = 3 + 5", "x = 8",
    ]
    assert x == 8


def test_several_statements_keep_source_order(capsys):
    y = 5
    with mpt:
        x = y + 1
        x * 2
        x = x + 10
    assert capsys.readouterr().out.splitlines() == [
        "x = y + 1", "x = 5 + 1", "x = 6",
        "x * 2", "6 * 2", "12",
        "x = x + 10", "x = 6 + 10", "x = 16",
    ]


def test_attribute_target(capsys):
    class Box:
        f = 0

    box = Box()
    with mpt:
        box.f = 3 + 4
    assert capsys.readouterr().out.splitlines() == [
        "box.f = 3 + 4", "box.f = 3 + 4", "box.f = 7",
    ]
    assert box.f == 7


def test_subscript_target(capsys):
    y = 5
    data = {}
    with mpt:
        data["k"] = 2 * y
    assert capsys.readouterr().out.splitlines() == [
        'data["k"] = 2 * y',
        'data["k"] = 2 * 5',
        'data["k"] = 10',
    ]
    assert data == {"k": 10}


def test_chained_assignment(capsys):
    y = 5
    with mpt:
        a = b = y + 1
    assert capsys.readouterr().out.splitlines() == [
        "a = b = y + 1", "a = b = 5 + 1", "a = b = 6",
    ]
    assert (a, b) == (6, 6)


def test_tuple_unpacking(capsys):
    with mpt:
        p, q = 1, 2
    assert capsys.readouterr().out.splitlines() == [
        "p, q = 1, 2", "p, q = 1, 2", "p, q = (1, 2)",
    ]
    assert (p, q) == (1, 2)


def test_parenthesized_rhs_is_reproduced(capsys):
    y = 5
    with mpt:
        x = (y + 1)
    assert capsys.readouterr().out.splitlines() == [
        "x = (y + 1)", "x = (5 + 1)", "x = 6",
    ]


# --- Bare expressions: the same rule as `mpt[...]` --------------------------

def test_bare_expression_is_displayed(capsys):
    y = 5
    with mpt:
        y + 2
    assert capsys.readouterr().out.splitlines() == ["y + 2", "5 + 2", "7"]


def test_bare_walrus_is_displayed(capsys):
    y = 5
    with mpt:
        (x := y + 1)
    assert capsys.readouterr().out.splitlines() == [
        "x := y + 1", "x := 5 + 1", "x := 6",
    ]
    assert x == 6


def test_sequence_expression_is_displayed_as_mpt_sequence(capsys):
    y = 2
    with mpt:
        y + 1, y * 2
    assert capsys.readouterr().out.splitlines() == [
        "y + 1", "2 + 1", "3",
        "y * 2", "2 * 2", "4",
    ]


# --- Everything that is not an expression form is left alone ----------------

def test_compound_statement_is_left_untouched(capsys):
    y = 1
    z = 0
    with mpt:
        if y:
            z = y + 1
    assert capsys.readouterr().out.splitlines() == []
    assert z == 2


def test_annotated_assignment_is_left_untouched(capsys):
    y = 1
    with mpt:
        x: int = y + 1
    assert capsys.readouterr().out.splitlines() == []
    assert x == 2


def test_augmented_assignment_is_left_untouched(capsys):
    x = 1
    with mpt:
        x += 1
    assert capsys.readouterr().out.splitlines() == []
    assert x == 2


def test_mpt_statement_is_not_displayed_twice(capsys):
    y = 5
    with mpt:
        mpt[z := y + 1]
        z + 1
    assert capsys.readouterr().out.splitlines() == [
        "z := y + 1", "z := 5 + 1", "z := 6",
        "z + 1", "6 + 1", "7",
    ]


def test_mpt_configure_statement_is_left_alone(capsys):
    y = 5
    with mpt:
        mpt.configure(out_order="line")
        x = y + 1
    assert capsys.readouterr().out.splitlines() == ["x = y + 1 = 5 + 1 = 6"]


# --- The other settings still apply ----------------------------------------

def test_line_layout(capsys):
    y = 5
    mpt.configure(out_order="line")
    with mpt:
        x = 3 + y
        x * 2
    assert capsys.readouterr().out.splitlines() == [
        "x = 3 + y = 3 + 5 = 8",
        "x * 2 = 8 * 2 = 16",
    ]


def test_line_layout_attribute(capsys):
    class Box:
        f = 0

    box = Box()
    y = 5
    mpt.configure(out_order="line")
    with mpt:
        box.f = 2 * y
    assert capsys.readouterr().out.splitlines() == [
        "box.f = 2 * y = 2 * 5 = 10",
    ]
    assert box.f == 10


def test_latex_line_keeps_every_chained_simple_target(monkeypatch):
    # The text passed to show() keeps plain `=` from the assignment targets;
    # LatexRenderer.to_source converts them to comparisons for py2tex.
    shown = []
    monkeypatch.setattr(LatexOutput, "show", shown.append)
    mpt.configure(out_order="line", out_format="latex")
    with mpt:
        aa = bb = cc = dd = 2
    assert shown == ["aa = bb = cc = dd == 2 == 2 == 2"]
    tex = LatexRenderer.to_source(shown[0])
    assert tex is not None
    for target in ("aa", "bb", "cc", "dd"):
        assert target in tex


def test_latex_line_keeps_every_chained_attribute_target(monkeypatch):
    # Regression: a chained block assignment rendered as `M21.l = M24.l = ...`;
    # py2tex saw an assignment and dropped M22/M23.
    shown = []
    monkeypatch.setattr(LatexOutput, "show", shown.append)

    class Box:
        l = 0

    M21 = M22 = M23 = M24 = Box()
    mpt.configure(out_order="line", out_format="latex")
    with mpt:
        M21.l = M22.l = M23.l = M24.l = 2
    assert shown == ["M21.l = M22.l = M23.l = M24.l == 2 == 2 == 2"]
    tex = LatexRenderer.to_source(shown[0])
    assert tex is not None
    for target in ("M21", "M22", "M23", "M24"):
        assert target in tex


def test_latex_line_keeps_every_walrus_target(monkeypatch):
    shown = []
    monkeypatch.setattr(LatexOutput, "show", shown.append)
    mpt.configure(out_order="line", out_format="latex")
    mpt[a := (b := (c := 2))]
    # The text passed to show() already has `:=` -> `==` from the expander.
    assert shown == ["a == (b := (c := 2)) == (b := (c := 2)) == 2"]
    tex = LatexRenderer.to_source(shown[0])
    assert tex is not None
    for target in ("a", "b", "c"):
        assert target in tex


def test_precision_in_block(capsys):
    mpt.configure(precision=3)
    with mpt:
        x = 1 / 3
    assert capsys.readouterr().out.splitlines() == [
        "x = 1 / 3", "x = 1 / 3", "x = 0.333",
    ]


# --- `with mpt, other_context_manager:` -------------------------------------

def test_other_context_manager_is_kept(capsys):
    events = []

    class CM:
        def __enter__(self):
            events.append("enter")
            return self

        def __exit__(self, *exc):
            events.append("exit")
            return False

    y = 5
    with mpt, CM():
        x = y + 1
    assert events == ["enter", "exit"]
    assert capsys.readouterr().out.splitlines() == [
        "x = y + 1", "x = 5 + 1", "x = 6",
    ]
    assert x == 6


# --- Rejected invocation forms ---------------------------------------------

def test_as_form_is_rejected():
    optional_vars = ast.Name(id="result", ctx=ast.Store())
    with pytest.raises(MacroExpansionError, match="as"):
        mathprint_main.mpt(
            [ast.Pass()],
            syntax="block",
            optional_vars=optional_vars,
            expander=_Expander(),
        )  # pyright: ignore[reportCallIssue]


def test_decorator_form_is_rejected():
    with pytest.raises(MacroExpansionError, match="decorator"):
        mathprint_main.mpt(
            ast.Pass(),
            syntax="decorator",
            expander=_Expander(),
        )  # pyright: ignore[reportCallIssue]
