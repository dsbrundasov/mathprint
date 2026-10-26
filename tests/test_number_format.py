"""Tests for ``mpt.configure(number_format=...)``.

``"exp"`` (the default) keeps ``str``'s scientific notation (``1.23e-09``).
``"power"`` shows a plain real number that would use that notation as a power
of ten instead::

    a = 1.23e-9
    mpt[a]      # 1.23*10**-9  (phase 2 and phase 3)

Only plain real numbers (``int``, ``float``, ``Decimal``, ``Fraction``; not
``bool``) are rewritten, and only text that actually contains an exponent.
"""

import os
from decimal import Decimal

import pytest

import mathprint_main
from mathprint import mpt

_HERE = os.path.abspath(__file__)


@pytest.fixture(autouse=True)
def restore_settings():
    """Keep layout/format/precision/number-format state isolated per test."""
    saved = (
        set(mathprint_main.Printer.line_scopes),
        set(mathprint_main.Printer.latex_scopes),
        dict(mathprint_main.Printer.precision_scopes),
        set(mathprint_main.Printer.multiple_assignment_reduce_scopes),
        set(mathprint_main.Printer.reduce_equ_stages_scopes),
        set(mathprint_main.Printer.power_number_scopes),
    )
    mathprint_main.Printer.line_scopes.clear()
    mathprint_main.Printer.latex_scopes.clear()
    mathprint_main.Printer.precision_scopes.clear()
    mathprint_main.Printer.multiple_assignment_reduce_scopes.clear()
    mathprint_main.Printer.reduce_equ_stages_scopes.clear()
    mathprint_main.Printer.power_number_scopes.clear()
    yield
    mathprint_main.Printer.line_scopes.clear()
    mathprint_main.Printer.line_scopes.update(saved[0])
    mathprint_main.Printer.latex_scopes.clear()
    mathprint_main.Printer.latex_scopes.update(saved[1])
    mathprint_main.Printer.precision_scopes.clear()
    mathprint_main.Printer.precision_scopes.update(saved[2])
    mathprint_main.Printer.multiple_assignment_reduce_scopes.clear()
    mathprint_main.Printer.multiple_assignment_reduce_scopes.update(saved[3])
    mathprint_main.Printer.reduce_equ_stages_scopes.clear()
    mathprint_main.Printer.reduce_equ_stages_scopes.update(saved[4])
    mathprint_main.Printer.power_number_scopes.clear()
    mathprint_main.Printer.power_number_scopes.update(saved[5])


def _lines(capsys):
    return capsys.readouterr().out.splitlines()


# --- Default: scientific notation ------------------------------------------

def test_default_is_exp(capsys):
    a = 1.23e-9
    mpt[a]
    assert _lines(capsys) == ["a", "1.23e-09", "1.23e-09"]


def test_exp_is_explicitly_accepted(capsys):
    mpt.configure(number_format="exp")
    a = 1.23e-9
    mpt[a]
    assert _lines(capsys) == ["a", "1.23e-09", "1.23e-09"]


# --- Power format -----------------------------------------------------------

def test_power_in_column_mode(capsys):
    mpt.configure(number_format="power")
    a = 1.23e-9
    assert mpt[a] == a
    assert _lines(capsys) == ["a", "1.23*10**-9", "1.23*10**-9"]


def test_power_in_line_mode(capsys):
    mpt.configure(out_order="line", number_format="power")
    a = 1.23e-9
    mpt[x := a]
    assert _lines(capsys) == [
        "x = a = 1.23*10**-9 = 1.23*10**-9"
    ]


def test_power_applies_to_plain_values(capsys):
    mpt.configure(number_format="power")
    mpt[1e20]
    assert _lines(capsys) == ["1e20", "1e20", "1*10**20"]


# --- Exponent normalization -------------------------------------------------

def test_positive_exponent_loses_the_sign_and_zero_padding(capsys):
    mpt.configure(number_format="power")
    mpt[1e20]
    assert _lines(capsys)[-1] == "1*10**20"


def test_negative_exponent_keeps_the_minus(capsys):
    mpt.configure(number_format="power")
    mpt[1.5e-5]
    assert _lines(capsys)[-1] == "1.5*10**-5"


def test_negative_number_keeps_the_sign(capsys):
    mpt.configure(number_format="power")
    mpt[(-1) * 2.5e-7]
    assert _lines(capsys)[-1] == "-2.5*10**-7"


def test_decimal_is_supported(capsys):
    mpt.configure(number_format="power")
    mpt[Decimal("1.23E-9")]
    assert _lines(capsys)[-1] == "1.23*10**-9"


def test_decimal_large_exponent(capsys):
    mpt.configure(number_format="power")
    mpt[Decimal("1.23456E20")]
    assert _lines(capsys)[-1] == "1.23456*10**20"


# --- Values without scientific notation stay as they are --------------------

@pytest.mark.parametrize("value, expected", [
    (2230, "2230"),
    (12345.678, "12345.678"),
    (0.001, "0.001"),
    (-42.5, "-42.5"),
])
def test_plain_numbers_are_unchanged(capsys, value, expected):
    mpt.configure(number_format="power")
    mpt[value]
    assert _lines(capsys)[-1] == expected


# --- Only plain real numbers are rewritten ---------------------------------

def test_strings_are_not_rewritten(capsys):
    mpt.configure(number_format="power")
    text = "1e-9"
    mpt[text]
    assert _lines(capsys)[-1] == "1e-9"


def test_complex_is_not_rewritten(capsys):
    mpt.configure(number_format="power")
    mpt[1e-9 + 0j]
    assert _lines(capsys)[-1] == "(1e-09+0j)"


def test_bool_is_not_rewritten(capsys):
    mpt.configure(number_format="power")
    mpt[True]
    assert _lines(capsys)[-1] == "True"


# --- Interaction with precision --------------------------------------------

def test_precision_output_passes_through(capsys):
    mpt.configure(precision=4, number_format="power")
    a = 1.23e-9
    mpt[a]
    # Precision shows plain decimal digits, so there is no exponent to rewrite.
    assert _lines(capsys) == ["a", "0.00000000123", "0.00000000123"]


# --- LaTeX ----------------------------------------------------------------

def test_power_renders_as_latex(monkeypatch):
    pytest.importorskip("pytexit")
    import IPython.display as ipython_display

    calls = []
    monkeypatch.setattr(ipython_display, "display", lambda obj: calls.append(obj))

    mpt.configure(out_format="latex", number_format="power")
    a = 1.23e-9
    mpt[a]

    assert len(calls) == 3
    assert "10}^{-9}" in calls[-1].data


# --- Turning it off again ---------------------------------------------------

def test_can_be_restored_to_exp(capsys):
    mpt.configure(number_format="power")
    mpt.configure(number_format="exp")
    a = 1.23e-9
    mpt[a]
    assert _lines(capsys) == ["a", "1.23e-09", "1.23e-09"]
