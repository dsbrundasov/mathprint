"""Tests for the ``mpt`` macro.

Run from the project root with::

    python -m pytest
"""

from mathprint import macros, mpt


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


def test_comparison_shows_side_values(capsys):
    y = 5
    z = 10
    result = mpt[y > z]
    out = capsys.readouterr().out.splitlines()
    assert out == ["y > z", "5 > 10"]
    assert result is False


def test_comparison_evaluates_sides(capsys):
    y = 5
    z = 10
    result = mpt[y < z * 2]
    out = capsys.readouterr().out.splitlines()
    assert out == ["y < z * 2", "5 < 20"]
    assert result is True


def test_chained_comparison(capsys):
    y = 5
    z = 10
    mpt[0 < y < z]
    out = capsys.readouterr().out.splitlines()
    assert out == ["0 < y < z", "0 < 5 < 10"]
