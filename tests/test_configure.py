"""Tests for the grouped display settings (``mpt.configure(...)``).

All three settings -- layout (``out_order``), format (``out_format``) and display
precision (``precision``) -- are changed through one call, scoped to the file (or
notebook) it appears in. Omitted arguments must be left unchanged.
"""

import os

import pytest

import mathprint_main
from mathprint import mpt

_HERE = os.path.abspath(__file__)


@pytest.fixture(autouse=True)
def restore_settings():
    """Keep all display settings isolated per test."""
    saved = (
        set(mathprint_main.Printer.line_scopes),
        set(mathprint_main.Printer.latex_scopes),
        dict(mathprint_main.Printer.precision_scopes),
    )
    mathprint_main.Printer.line_scopes.clear()
    mathprint_main.Printer.latex_scopes.clear()
    mathprint_main.Printer.precision_scopes.clear()
    yield
    mathprint_main.Printer.line_scopes.clear()
    mathprint_main.Printer.line_scopes.update(saved[0])
    mathprint_main.Printer.latex_scopes.clear()
    mathprint_main.Printer.latex_scopes.update(saved[1])
    mathprint_main.Printer.precision_scopes.clear()
    mathprint_main.Printer.precision_scopes.update(saved[2])


# --- Defaults ---------------------------------------------------------------

def test_defaults():
    assert not mathprint_main.Printer.line_on(_HERE)
    assert not mathprint_main.Printer.latex_on(_HERE)
    assert mathprint_main.Printer.precision_of(_HERE) is None


# --- Grouped call -----------------------------------------------------------

def test_returns_scope_key():
    assert mpt.configure(out_order="line") == _HERE


def test_applies_several_options_at_once():
    assert mpt.configure(out_order="line", out_format="latex", precision=4) == _HERE
    assert mathprint_main.Printer.line_on(_HERE)
    assert mathprint_main.Printer.latex_on(_HERE)
    assert mathprint_main.Printer.precision_of(_HERE) == 4


def test_no_arguments_changes_nothing():
    mpt.configure(out_order="line", out_format="latex", precision=4)
    assert mpt.configure() == _HERE
    assert mathprint_main.Printer.line_on(_HERE)
    assert mathprint_main.Printer.latex_on(_HERE)
    assert mathprint_main.Printer.precision_of(_HERE) == 4


# --- Omitted options stay unchanged ----------------------------------------

def test_omitted_option_stays_unchanged():
    mpt.configure(out_order="line", out_format="latex", precision=4)
    mpt.configure(precision=2)
    assert mathprint_main.Printer.line_on(_HERE)
    assert mathprint_main.Printer.latex_on(_HERE)
    assert mathprint_main.Printer.precision_of(_HERE) == 2


def test_each_option_can_be_set_alone():
    mpt.configure(out_order="line")
    assert mathprint_main.Printer.line_on(_HERE)
    assert not mathprint_main.Printer.latex_on(_HERE)
    assert mathprint_main.Printer.precision_of(_HERE) is None

    mpt.configure(out_format="latex")
    assert mathprint_main.Printer.line_on(_HERE)
    assert mathprint_main.Printer.latex_on(_HERE)
    assert mathprint_main.Printer.precision_of(_HERE) is None

    mpt.configure(precision=4)
    assert mathprint_main.Printer.line_on(_HERE)
    assert mathprint_main.Printer.latex_on(_HERE)
    assert mathprint_main.Printer.precision_of(_HERE) == 4


# --- Turning options back off ----------------------------------------------

def test_values_can_be_restored():
    mpt.configure(out_order="line", out_format="latex", precision=4)
    mpt.configure(out_order="column", out_format="text", precision=None)
    assert not mathprint_main.Printer.line_on(_HERE)
    assert not mathprint_main.Printer.latex_on(_HERE)
    assert mathprint_main.Printer.precision_of(_HERE) is None


# --- Validation -------------------------------------------------------------

def test_rejects_unknown_out_order():
    with pytest.raises(ValueError, match="out_order"):
        mpt.configure(out_order="rows")
    assert not mathprint_main.Printer.line_on(_HERE)


def test_rejects_unknown_out_format():
    with pytest.raises(ValueError, match="out_format"):
        mpt.configure(out_format="html")
    assert not mathprint_main.Printer.latex_on(_HERE)


def test_rejects_non_positive_precision():
    with pytest.raises(ValueError):
        mpt.configure(precision=0)
    assert mathprint_main.Printer.precision_of(_HERE) is None


def test_rejects_positional_arguments():
    with pytest.raises(TypeError):
        mpt.configure("line")  # pyright: ignore[reportCallIssue]


# --- The old per-setting API is gone ---------------------------------------

@pytest.mark.parametrize("name", ["to_line", "to_column", "latex", "precision"])
def test_old_api_is_absent(name):
    assert not hasattr(mpt, name)
