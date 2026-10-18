"""Tests for the ``mpt`` macro.

Run from the project root with::

    python -m pytest
"""

from mathprint_main import macros, mpt


# --- Phase 3: evaluation ---------------------------------------------------

def test_bare_expression(capsys):
    result = mpt[2 + 3]
    out = capsys.readouterr().out.splitlines()
    assert out == ["2 + 3", "2 + 3"]
    assert result == 5


def test_assignment(capsys):
    mpt[x := 2 * 3]
    capsys.readouterr()
    assert x == 6


def test_variables_substituted(capsys):
    y = 5
    z = 10
    result = mpt[y * z]
    out = capsys.readouterr().out.splitlines()
    assert out == ["y * z", "5 * 10"]
    assert result == 50


def test_assignment_prefix(capsys):
    y = 5
    z = 10
    mpt[x := y + z]
    out = capsys.readouterr().out.splitlines()
    assert out == ["x := y + z", "x := 5 + 10"]
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
    assert out == ["(y) + (z)", "(5) + (10)"]


# --- Phase 2: substitution preserves order ---------------------------------

def test_substitution_is_in_place(capsys):
    y = 5
    z = 10
    mpt[z - y + z]
    out = capsys.readouterr().out.splitlines()
    assert out == ["z - y + z", "10 - 5 + 10"]


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
    assert out == ["c - (a - (b - (c - a)))", "3 - (1 - (2 - (3 - 1)))"]


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
    assert out == ["f(y)", "f(5)"]
    assert result == 6


def test_lambda_name_not_expanded(capsys):
    f = lambda x: x  # noqa: E731
    y = 5
    mpt[f(y)]
    out = capsys.readouterr().out.splitlines()
    assert out == ["f(y)", "f(5)"]


def test_builtin_function_names_not_expanded(capsys):
    y = 5
    result = mpt[len(str(y)) * 2]
    out = capsys.readouterr().out.splitlines()
    # Both `len` (built-in function) and `str` (class) stay as written.
    assert out == ["len(str(y)) * 2", "len(str(5)) * 2"]
    assert result == 2


def test_class_names_not_expanded(capsys):
    class Point:
        def __init__(self, x):
            self.x = x

    p = Point(3)
    y = 5
    result = mpt[int(y)]
    out = capsys.readouterr().out.splitlines()
    assert out == ["int(y)", "int(5)"]
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
    assert out == ["add(y)", "add(5)"]
    assert result == 6


# --- Phase 2: comparisons are substituted, not evaluated -------------------

def test_comparison_shows_side_values_when_single_names(capsys):
    y = 5
    z = 10
    result = mpt[y > z]
    out = capsys.readouterr().out.splitlines()
    assert out == ["y > z", "5 > 10"]
    assert result is False


def test_comparison_is_substituted_not_evaluated(capsys):
    y = 5
    z = 10
    result = mpt[y < z * 2]
    out = capsys.readouterr().out.splitlines()
    assert out == ["y < z * 2", "5 < 10 * 2"]
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
    assert out == ["0 < y < z", "0 < 5 < 10"]
