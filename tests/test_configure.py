"""Tests for the grouped display settings (``mpt.configure(...)``).

All settings -- layout (``out_order``), format (``out_format``), display
precision (``precision``), nested-assignment collapsing
(``multiple_assignment_reduce``), one-line stage deduplication
(``reduce_equ_stages``), the number format (``number_format``) and the extra
output (``additional_out``) -- are changed through one call, scoped to the file
(or notebook) it appears in. Omitted arguments must be left unchanged, and
``reset=True`` must return the scope to the core defaults.

The per-test isolation fixture lives in ``conftest.py``.
"""

import os
from dataclasses import replace

import pytest

from mathprint import mpt
from mathprint_main import DisplaySettings, SettingsStore

_HERE = os.path.abspath(__file__)

#: Every option set away from its default, for "nothing changed" assertions.
_ALL_SETTINGS = DisplaySettings(
    out_order="line",
    out_format="latex",
    precision=4,
    multiple_assignment_reduce=True,
    reduce_equ_stages=True,
    number_format="power",
    additional_out="text",
)


def _settings():
    """The settings of the file this test lives in."""
    return SettingsStore.settings_for(_HERE)


def _configure_all():
    """Turn every option away from its default."""
    return mpt.configure(
        out_order="line",
        out_format="latex",
        precision=4,
        multiple_assignment_reduce=True,
        reduce_equ_stages=True,
        number_format="power",
        additional_out="text",
    )


# --- Defaults ---------------------------------------------------------------

def test_defaults_are_the_core():
    assert _settings() == DisplaySettings()
    assert DisplaySettings().out_order == "column"
    assert DisplaySettings().out_format == "text"
    assert DisplaySettings().precision is None
    assert DisplaySettings().multiple_assignment_reduce is False
    assert DisplaySettings().reduce_equ_stages is False
    assert DisplaySettings().number_format == "exp"
    assert DisplaySettings().additional_out is None


def test_unknown_file_uses_the_fallback():
    assert SettingsStore.settings_for(os.path.abspath("nowhere.py")) == DisplaySettings()


def test_any_file_fallback_applies_to_a_file_without_its_own_entry(capsys):
    SettingsStore.update(SettingsStore.ANY_FILE, out_order="line")
    mpt[2 + 3]
    assert capsys.readouterr().out.splitlines() == ["2 + 3 = 2 + 3 = 5"]


# --- Grouped call -----------------------------------------------------------

def test_returns_scope_key():
    assert mpt.configure(out_order="line") == _HERE


def test_applies_several_options_at_once():
    assert _configure_all() == _HERE
    assert _settings() == _ALL_SETTINGS


def test_no_arguments_changes_nothing():
    _configure_all()
    assert mpt.configure() == _HERE
    assert _settings() == _ALL_SETTINGS


# --- Omitted options stay unchanged ----------------------------------------

def test_omitted_option_stays_unchanged():
    _configure_all()
    mpt.configure(precision=2)
    assert _settings() == replace(_ALL_SETTINGS, precision=2)


def test_each_option_can_be_set_alone():
    """Each option can be turned on without losing the ones before it."""
    expected = DisplaySettings()

    def check(apply_option, **changes):
        nonlocal expected
        apply_option()
        expected = replace(expected, **changes)
        assert _settings() == expected

    check(lambda: mpt.configure(out_order="line"), out_order="line")
    check(lambda: mpt.configure(out_format="latex"), out_format="latex")
    check(lambda: mpt.configure(precision=4), precision=4)
    check(
        lambda: mpt.configure(multiple_assignment_reduce=True),
        multiple_assignment_reduce=True,
    )
    check(lambda: mpt.configure(reduce_equ_stages=True), reduce_equ_stages=True)
    check(lambda: mpt.configure(number_format="power"), number_format="power")
    check(lambda: mpt.configure(additional_out="latex"), additional_out="latex")


# --- Turning options back off ----------------------------------------------

def test_values_can_be_restored():
    _configure_all()
    mpt.configure(
        out_order="column",
        out_format="text",
        precision=None,
        multiple_assignment_reduce=False,
        reduce_equ_stages=False,
        number_format="exp",
        additional_out=None,
    )
    assert _settings() == DisplaySettings()


# --- reset=True -------------------------------------------------------------

def test_reset_returns_the_scope_to_the_core():
    _configure_all()
    assert mpt.configure(reset=True) == _HERE
    assert _settings() == DisplaySettings()


def test_reset_can_be_combined_with_new_options():
    _configure_all()
    mpt.configure(reset=True, out_format="latex")
    assert _settings() == DisplaySettings(out_format="latex")


def test_reset_keeps_the_fallback_untouched():
    SettingsStore.update(SettingsStore.ANY_FILE, precision=4)
    mpt.configure(out_order="line")
    mpt.configure(reset=True)
    assert _settings() == DisplaySettings(precision=4)


def test_rejects_non_bool_reset():
    with pytest.raises(ValueError, match="reset"):
        mpt.configure(reset="yes")  # pyright: ignore[reportArgumentType]


# --- Validation -------------------------------------------------------------

def test_rejects_unknown_out_order():
    with pytest.raises(ValueError, match="out_order"):
        mpt.configure(out_order="rows")  # pyright: ignore[reportArgumentType]
    assert _settings() == DisplaySettings()


def test_rejects_unknown_out_format():
    with pytest.raises(ValueError, match="out_format"):
        mpt.configure(out_format="html")  # pyright: ignore[reportArgumentType]
    assert _settings() == DisplaySettings()


def test_rejects_non_positive_precision():
    with pytest.raises(ValueError):
        mpt.configure(precision=0)
    assert _settings() == DisplaySettings()


def test_rejects_non_bool_multiple_assignment_reduce():
    with pytest.raises(ValueError, match="multiple_assignment_reduce"):
        mpt.configure(multiple_assignment_reduce="yes")  # pyright: ignore[reportArgumentType]
    assert _settings() == DisplaySettings()


def test_rejects_non_bool_reduce_equ_stages():
    with pytest.raises(ValueError, match="reduce_equ_stages"):
        mpt.configure(reduce_equ_stages="yes")  # pyright: ignore[reportArgumentType]
    assert _settings() == DisplaySettings()


def test_rejects_unknown_number_format():
    with pytest.raises(ValueError, match="number_format"):
        mpt.configure(number_format="si")  # pyright: ignore[reportArgumentType]
    assert _settings() == DisplaySettings()


def test_rejects_unknown_additional_out():
    with pytest.raises(ValueError, match="additional_out"):
        mpt.configure(additional_out="html")  # pyright: ignore[reportArgumentType]
    assert _settings() == DisplaySettings()


def test_rejects_positional_arguments():
    with pytest.raises(TypeError):
        mpt.configure("line")  # pyright: ignore[reportCallIssue]


def test_a_bad_value_changes_nothing():
    # Validation happens before anything is stored, so a partly-bad call is a
    # no-op rather than a half-applied change.
    with pytest.raises(ValueError, match="out_format"):
        mpt.configure(out_order="line", out_format="html")  # pyright: ignore[reportArgumentType]
    assert _settings() == DisplaySettings()


# --- The old per-setting API is gone ---------------------------------------

@pytest.mark.parametrize("name", ["to_line", "to_column", "latex", "precision"])
def test_old_api_is_absent(name):
    assert not hasattr(mpt, name)
