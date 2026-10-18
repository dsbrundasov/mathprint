"""Tests for the ``mpt`` macro.

Run from the project root with::

    python -m pytest
"""

from mathprint import mpt

import os

_HERE = os.path.abspath(__file__)


# --- Phase 3: evaluation ---------------------------------------------------

def test_bare_expression(capsys):
    result = mpt[2 + 3]
    out = capsys.readouterr().out.splitlines()
    assert out == ["2 + 3", "2 + 3", "5"]
    assert result == 5


def test_assignment(capsys):
    mpt[x := 2 * 3]
    out = capsys.readouterr().out.splitlines()
    assert out == ["x := 2 * 3", "x := 2 * 3", "x := 6"]
    assert x == 6


def test_assignment_value_line_has_name(capsys):
    # The value line carries the name, like phases 1 and 2.
    mpt[g_m_diff := 12]
    out = capsys.readouterr().out.splitlines()
    assert out == ["g_m_diff := 12", "g_m_diff := 12", "g_m_diff := 12"]


def test_expression_evaluated_exactly_once(capsys):
    calls = []

    def f(x):
        calls.append(x)
        return x * 2

    y = 5
    result = mpt[f(y)]
    out = capsys.readouterr().out.splitlines()
    assert out == ["f(y)", "f(5)", "10"]
    assert calls == [5]  # `f` is called once, not once for printing and once for the result
    assert result == 10


def test_variables_substituted(capsys):
    y = 5
    z = 10
    result = mpt[y * z]
    out = capsys.readouterr().out.splitlines()
    assert out == ["y * z", "5 * 10", "50"]
    assert result == 50


def test_assignment_prefix(capsys):
    y = 5
    z = 10
    mpt[x := y + z]
    out = capsys.readouterr().out.splitlines()
    assert out == ["x := y + z", "x := 5 + 10", "x := 15"]
    assert x == 15


# --- Phase 1: exact source -------------------------------------------------

def test_phase1_exact_spacing(capsys):
    mpt[  2+3 *  4 ]
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "2+3 *  4"


def test_phase1_exact_spacing_with_names(capsys):
    y = 5
    z = 10
    mpt[  y*7+z  ]
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "y*7+z"
    assert out[1] == "5*7+10"


def test_phase1_exact_assignment(capsys):
    mpt[  k:=2+2  ]
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "k:=2+2"
    assert out[1] == "k:=2+2"  # no variables -> substitution line == source line
    assert k == 4


def test_phase1_keeps_redundant_parentheses(capsys):
    y = 5
    z = 10
    mpt[(y) + (z)]
    out = capsys.readouterr().out.splitlines()
    assert out == ["(y) + (z)", "(5) + (10)", "15"]


# --- Phase 2: substitution preserves order ---------------------------------

def test_substitution_is_in_place(capsys):
    y = 5
    z = 10
    mpt[z - y + z]
    out = capsys.readouterr().out.splitlines()
    assert out == ["z - y + z", "10 - 5 + 10", "15"]


def test_order_preserved_mixed(capsys):
    z = 10
    y = 5
    mpt[(z - y) * (y + z) / z]
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "(z - y) * (y + z) / z"
    assert out[1] == "(10 - 5) * (5 + 10) / 10"


def test_order_preserved_in_assignment(capsys):
    z = 10
    y = 5
    mpt[k := z - y + z]
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "k := z - y + z"
    assert out[1] == "k := 10 - 5 + 10"


def test_order_preserved_repeated_and_nested(capsys):
    a = 1
    b = 2
    c = 3
    mpt[c - (a - (b - (c - a)))]
    out = capsys.readouterr().out.splitlines()
    assert out == ["c - (a - (b - (c - a)))", "3 - (1 - (2 - (3 - 1)))", "2"]


def test_order_preserved_deep_fraction(capsys):
    # Ten variables, assigned in *reverse* of their source order, so that any
    # reordering during substitution would be immediately visible.
    a, b, c, d, e, f, g, h, i, j = 10, 9, 8, 7, 6, 5, 4, 3, 2, 1
    mpt[a / (b + c / (d - e / (f + g / (h - i / j))))]
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "a / (b + c / (d - e / (f + g / (h - i / j))))"
    assert out[1] == "10 / (9 + 8 / (7 - 6 / (5 + 4 / (3 - 2 / 1))))"


def test_order_preserved_with_attributes(capsys):
    import math

    y = 5
    mpt[y * math.floor(y) + y]
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "y * math.floor(y) + y"
    # The name `math` refers to a module, so it is left as written (not expanded).
    assert out[1] == "5 * math.floor(5) + 5"


def test_module_names_not_expanded(capsys):
    import math as mt

    y = 5
    mpt[mt.floor(y) + mt.ceil(y)]
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "mt.floor(y) + mt.ceil(y)"
    assert out[1] == "mt.floor(5) + mt.ceil(5)"


def test_function_names_not_expanded(capsys):
    def f(x):
        return x + 1

    y = 5
    result = mpt[f(y)]
    out = capsys.readouterr().out.splitlines()
    assert out == ["f(y)", "f(5)", "6"]
    assert result == 6


def test_lambda_name_not_expanded(capsys):
    f = lambda x: x  # noqa: E731
    y = 5
    mpt[f(y)]
    out = capsys.readouterr().out.splitlines()
    assert out == ["f(y)", "f(5)", "5"]


def test_builtin_function_names_not_expanded(capsys):
    y = 5
    result = mpt[len(str(y)) * 2]
    out = capsys.readouterr().out.splitlines()
    # Both `len` (built-in function) and `str` (class) stay as written.
    assert out == ["len(str(y)) * 2", "len(str(5)) * 2", "2"]
    assert result == 2


def test_class_names_not_expanded(capsys):
    class Point:
        def __init__(self, x):
            self.x = x

    p = Point(3)
    y = 5
    result = mpt[int(y)]
    out = capsys.readouterr().out.splitlines()
    assert out == ["int(y)", "int(5)", "5"]
    assert result == 5


def test_bound_method_name_not_expanded(capsys):
    class Counter:
        def add(self, x):
            return x + 1

    counter = Counter()
    add = counter.add
    y = 5
    result = mpt[add(y)]
    out = capsys.readouterr().out.splitlines()
    assert out == ["add(y)", "add(5)", "6"]
    assert result == 6


# --- Phase 2: comparisons are substituted, not evaluated -------------------

def test_comparison_shows_side_values_when_single_names(capsys):
    y = 5
    z = 10
    result = mpt[y > z]
    out = capsys.readouterr().out.splitlines()
    assert out == ["y > z", "5 > 10", "False"]
    assert result is False


def test_comparison_is_substituted_not_evaluated(capsys):
    y = 5
    z = 10
    result = mpt[y < z * 2]
    out = capsys.readouterr().out.splitlines()
    assert out == ["y < z * 2", "5 < 10 * 2", "True"]
    assert result is True


def test_comparison_keeps_order(capsys):
    a = 2
    z = 10
    mpt[a + z > a * z]
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "a + z > a * z"
    assert out[1] == "2 + 10 > 2 * 10"


def test_chained_comparison(capsys):
    y = 5
    z = 10
    mpt[0 < y < z]
    out = capsys.readouterr().out.splitlines()
    assert out == ["0 < y < z", "0 < 5 < 10", "True"]


# --- Several expressions in one call: `mpt[a, b, ...]` ---------------------

def test_sequence_prints_each_item_in_order(capsys):
    y = 5
    z = 10
    result = mpt[y + z, y * z]
    out = capsys.readouterr().out.splitlines()
    assert out == [
        "y + z", "5 + 10", "15",
        "y * z", "5 * 10", "50",
    ]
    # One value per item, gathered into a tuple.
    assert result == (15, 50)


def test_sequence_matches_separate_calls(capsys):
    y = 5
    z = 10

    mpt[y + z]
    mpt[y * z]
    separate = capsys.readouterr().out

    mpt[y + z, y * z]
    sequenced = capsys.readouterr().out

    assert sequenced == separate


def test_sequence_assignment_binds_in_caller_scope(capsys):
    L_min = 3
    result = mpt[
        L_diff := (L_11 := (L_12 := 2 * L_min)),
        g_m_diff := (g_m_11 := (g_m_12 := (10 * 2 * L_min))),
    ]
    out = capsys.readouterr().out.splitlines()
    assert out == [
        "L_diff := (L_11 := (L_12 := 2 * L_min))",
        "L_diff := (L_11 := (L_12 := 2 * 3))",
        "L_diff := 6",
        "g_m_diff := (g_m_11 := (g_m_12 := (10 * 2 * L_min)))",
        "g_m_diff := (g_m_11 := (g_m_12 := (10 * 2 * 3)))",
        "g_m_diff := 60",
    ]
    assert result == (6, 60)
    # Every name bound by the walrus chains exists in *this* scope.
    assert (L_diff, L_11, L_12) == (6, 6, 6)
    assert (g_m_diff, g_m_11, g_m_12) == (60, 60, 60)


def test_sequence_trailing_comma(capsys):
    y = 5
    z = 10
    result = mpt[y + z, y * z, ]
    out = capsys.readouterr().out.splitlines()
    assert out == ["y + z", "5 + 10", "15", "y * z", "5 * 10", "50"]
    assert result == (15, 50)


def test_sequence_with_precision(capsys):
    import mathprint_main

    mathprint_main._PRECISION_FILES[_HERE] = 4
    try:
        v = 3.123123412
        result = mpt[v + 0, v * 1]
        out = capsys.readouterr().out.splitlines()
        assert out == ["v + 0", "3.123 + 0", "3.123", "v * 1", "3.123 * 1", "3.123"]
        assert result == (3.123123412, 3.123123412)
    finally:
        mathprint_main._PRECISION_FILES.pop(_HERE, None)


def test_tuple_value_is_a_single_expression(capsys):
    # A tuple *value* behind a name is still one expression, not a sequence.
    t = (1, 2, 3)
    result = mpt[t]
    out = capsys.readouterr().out.splitlines()
    assert out == ["t", "(1, 2, 3)", "(1, 2, 3)"]
    assert result == (1, 2, 3)


# --- No source text: clear error, no silent fallback -----------------------

def test_missing_source_raises_clear_error(monkeypatch):
    import ast

    import pytest

    import mathprint_main
    from mcpyrate.core import MacroExpansionError

    class _Expander:
        filename = None

    node = ast.parse("y + 0", mode="eval").body
    monkeypatch.setattr(mathprint_main, "_SOURCE_OVERRIDE", None)
    with pytest.raises(MacroExpansionError):
        mathprint_main.mpt(node, expander=_Expander())
