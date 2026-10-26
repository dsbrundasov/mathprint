"""Tests for ``mpt.configure(number_format=...)``.

``"exp"`` (the default) keeps ``str``'s representation (``1.23e-09``).
``"power"`` shows real numbers with a power of ten::

    a = 1.23e-9
    mpt[a]      # 1.23*10**-9  (all three phases)

A plain decimal far from ``1`` is normalized as well (``0.0001106`` ->
``1.106*10**-4``), even when Python would print it without an exponent. Only
plain real numbers (``int``, ``float``, ``Decimal``, ``Fraction``; not ``bool``)
are rewritten; string contents and complex numbers are not.
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
    # The source literal is rewritten as well as the substituted value.
    assert _lines(capsys) == ["1*10**20", "1*10**20", "1*10**20"]


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


def test_small_plain_number_is_normalized(capsys):
    # Not scientific in ``str``, but far enough from 1 to use the power form.
    mpt.configure(number_format="power")
    mpt[0.0001106]
    assert _lines(capsys) == [
        "1.106*10**-4", "1.106*10**-4", "1.106*10**-4"
    ]


def test_small_decimal_is_normalized(capsys):
    mpt.configure(number_format="power")
    mpt[Decimal("0.0001106")]
    assert _lines(capsys)[-1] == "1.106*10**-4"


def test_source_literals_are_rewritten(capsys):
    mpt.configure(number_format="power")
    mpt[2.4e-6 * 1]
    assert _lines(capsys) == [
        "2.4*10**-6 * 1",
        "2.4*10**-6 * 1",
        "2.4*10**-6",
    ]


def test_smallest_plain_decimal_is_rewritten(capsys):
    mpt.configure(number_format="power")
    mpt[0.0001]
    assert _lines(capsys)[-1] == "1*10**-4"


def test_plain_decimal_above_the_threshold_is_untouched(capsys):
    mpt.configure(number_format="power")
    mpt[0.001]
    assert _lines(capsys) == ["0.001", "0.001", "0.001"]


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
    assert _lines(capsys) == ["text", "1e-9", "1e-9"]


def test_string_literal_in_the_source_is_not_rewritten(capsys):
    mpt.configure(number_format="power")
    mpt["1e-9"]
    assert _lines(capsys) == ['"1e-9"', '"1e-9"', "1e-9"]


def test_complex_is_not_rewritten(capsys):
    mpt.configure(number_format="power")
    mpt[1e-9 + 0j]
    assert _lines(capsys)[-1] == "(1e-09+0j)"


def test_bool_is_not_rewritten(capsys):
    mpt.configure(number_format="power")
    mpt[True]
    assert _lines(capsys)[-1] == "True"


# --- Interaction with precision --------------------------------------------

def test_precision_output_is_converted_to_power(capsys):
    mpt.configure(precision=4, number_format="power")
    a = 1.23e-9
    mpt[a]
    # Precision's plain decimal is normalized to a power of ten as well.
    assert _lines(capsys) == ["a", "1.23*10**-9", "1.23*10**-9"]


def test_precision_large_number_is_normalized(capsys):
    mpt.configure(precision=4, number_format="power")
    a = 1.23e20
    mpt[a]
    assert _lines(capsys) == ["a", "1.23*10**20", "1.23*10**20"]


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
