"""Tests for the grouped display settings (``mpt.configure(...)``).

All settings -- layout (``out_order``), format (``out_format``), display
precision (``precision``) and nested-assignment collapsing
(``multiple_assignment_reduce``) -- are changed through one call, scoped to the
file (or notebook) it appears in. Omitted arguments must be left unchanged.
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
        set(mathprint_main.Printer.multiple_assignment_reduce_scopes),
        set(mathprint_main.Printer.reduce_equ_stages_scopes),
    )
    mathprint_main.Printer.line_scopes.clear()
    mathprint_main.Printer.latex_scopes.clear()
    mathprint_main.Printer.precision_scopes.clear()
    mathprint_main.Printer.multiple_assignment_reduce_scopes.clear()
    mathprint_main.Printer.reduce_equ_stages_scopes.clear()
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


# --- Defaults ---------------------------------------------------------------

def test_defaults():
    assert not mathprint_main.Printer.line_on(_HERE)
    assert not mathprint_main.Printer.latex_on(_HERE)
    assert mathprint_main.Printer.precision_of(_HERE) is None
    assert not mathprint_main.Printer.multiple_assignment_reduce_on(_HERE)
    assert not mathprint_main.Printer.reduce_equ_stages_on(_HERE)


# --- Grouped call -----------------------------------------------------------

def test_returns_scope_key():
    assert mpt.configure(out_order="line") == _HERE


def test_applies_several_options_at_once():
    assert mpt.configure(
        out_order="line",
        out_format="latex",
        precision=4,
        multiple_assignment_reduce=True,
        reduce_equ_stages=True,
    ) == _HERE
    assert mathprint_main.Printer.line_on(_HERE)
    assert mathprint_main.Printer.latex_on(_HERE)
    assert mathprint_main.Printer.precision_of(_HERE) == 4
    assert mathprint_main.Printer.multiple_assignment_reduce_on(_HERE)
    assert mathprint_main.Printer.reduce_equ_stages_on(_HERE)


def test_no_arguments_changes_nothing():
    mpt.configure(
        out_order="line",
        out_format="latex",
        precision=4,
        multiple_assignment_reduce=True,
        reduce_equ_stages=True,
    )
    assert mpt.configure() == _HERE
    assert mathprint_main.Printer.line_on(_HERE)
    assert mathprint_main.Printer.latex_on(_HERE)
    assert mathprint_main.Printer.precision_of(_HERE) == 4
    assert mathprint_main.Printer.multiple_assignment_reduce_on(_HERE)
    assert mathprint_main.Printer.reduce_equ_stages_on(_HERE)


# --- Omitted options stay unchanged ----------------------------------------

def test_omitted_option_stays_unchanged():
    mpt.configure(
        out_order="line",
        out_format="latex",
        precision=4,
        multiple_assignment_reduce=True,
        reduce_equ_stages=True,
    )
    mpt.configure(precision=2)
    assert mathprint_main.Printer.line_on(_HERE)
    assert mathprint_main.Printer.latex_on(_HERE)
    assert mathprint_main.Printer.precision_of(_HERE) == 2
    assert mathprint_main.Printer.multiple_assignment_reduce_on(_HERE)
    assert mathprint_main.Printer.reduce_equ_stages_on(_HERE)


def test_each_option_can_be_set_alone():
    mpt.configure(out_order="line")
    assert mathprint_main.Printer.line_on(_HERE)
    assert not mathprint_main.Printer.latex_on(_HERE)
    assert mathprint_main.Printer.precision_of(_HERE) is None
    assert not mathprint_main.Printer.multiple_assignment_reduce_on(_HERE)
    assert not mathprint_main.Printer.reduce_equ_stages_on(_HERE)

    mpt.configure(out_format="latex")
    assert mathprint_main.Printer.line_on(_HERE)
    assert mathprint_main.Printer.latex_on(_HERE)
    assert mathprint_main.Printer.precision_of(_HERE) is None
    assert not mathprint_main.Printer.multiple_assignment_reduce_on(_HERE)
    assert not mathprint_main.Printer.reduce_equ_stages_on(_HERE)

    mpt.configure(precision=4)
    assert mathprint_main.Printer.line_on(_HERE)
    assert mathprint_main.Printer.latex_on(_HERE)
    assert mathprint_main.Printer.precision_of(_HERE) == 4
    assert not mathprint_main.Printer.multiple_assignment_reduce_on(_HERE)
    assert not mathprint_main.Printer.reduce_equ_stages_on(_HERE)

    mpt.configure(multiple_assignment_reduce=True)
    assert mathprint_main.Printer.line_on(_HERE)
    assert mathprint_main.Printer.latex_on(_HERE)
    assert mathprint_main.Printer.precision_of(_HERE) == 4
    assert mathprint_main.Printer.multiple_assignment_reduce_on(_HERE)
    assert not mathprint_main.Printer.reduce_equ_stages_on(_HERE)

    mpt.configure(reduce_equ_stages=True)
    assert mathprint_main.Printer.line_on(_HERE)
    assert mathprint_main.Printer.latex_on(_HERE)
    assert mathprint_main.Printer.precision_of(_HERE) == 4
    assert mathprint_main.Printer.multiple_assignment_reduce_on(_HERE)
    assert mathprint_main.Printer.reduce_equ_stages_on(_HERE)


# --- Turning options back off ----------------------------------------------

def test_values_can_be_restored():
    mpt.configure(
        out_order="line",
        out_format="latex",
        precision=4,
        multiple_assignment_reduce=True,
        reduce_equ_stages=True,
    )
    mpt.configure(
        out_order="column",
        out_format="text",
        precision=None,
        multiple_assignment_reduce=False,
        reduce_equ_stages=False,
    )
    assert not mathprint_main.Printer.line_on(_HERE)
    assert not mathprint_main.Printer.latex_on(_HERE)
    assert mathprint_main.Printer.precision_of(_HERE) is None
    assert not mathprint_main.Printer.multiple_assignment_reduce_on(_HERE)
    assert not mathprint_main.Printer.reduce_equ_stages_on(_HERE)


# --- Validation -------------------------------------------------------------

def test_rejects_unknown_out_order():
    with pytest.raises(ValueError, match="out_order"):
        mpt.configure(out_order="rows")  # pyright: ignore[reportArgumentType]
    assert not mathprint_main.Printer.line_on(_HERE)


def test_rejects_unknown_out_format():
    with pytest.raises(ValueError, match="out_format"):
        mpt.configure(out_format="html")  # pyright: ignore[reportArgumentType]
    assert not mathprint_main.Printer.latex_on(_HERE)


def test_rejects_non_positive_precision():
    with pytest.raises(ValueError):
        mpt.configure(precision=0)
    assert mathprint_main.Printer.precision_of(_HERE) is None


def test_rejects_non_bool_multiple_assignment_reduce():
    with pytest.raises(ValueError, match="multiple_assignment_reduce"):
        mpt.configure(multiple_assignment_reduce="yes")  # pyright: ignore[reportArgumentType]
    assert not mathprint_main.Printer.multiple_assignment_reduce_on(_HERE)


def test_rejects_non_bool_reduce_equ_stages():
    with pytest.raises(ValueError, match="reduce_equ_stages"):
        mpt.configure(reduce_equ_stages="yes")  # pyright: ignore[reportArgumentType]
    assert not mathprint_main.Printer.reduce_equ_stages_on(_HERE)


def test_rejects_positional_arguments():
    with pytest.raises(TypeError):
        mpt.configure("line")  # pyright: ignore[reportCallIssue]


# --- The old per-setting API is gone ---------------------------------------

@pytest.mark.parametrize("name", ["to_line", "to_column", "latex", "precision"])
def test_old_api_is_absent(name):
    assert not hasattr(mpt, name)
