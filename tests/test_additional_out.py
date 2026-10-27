"""Tests for ``mpt.configure(additional_out=...)``.

The option prints the same expression again after the main output, as raw text:

* ``"text"`` -- the plain Python line;
* ``"latex"`` -- the LaTeX source that ``py2tex`` produces (never rendered).

All other settings (layout, precision, number format, stage reductions) apply
to the additional output unchanged.
"""

import pytest

from mathprint import mpt


def _lines(capsys):
    return capsys.readouterr().out.splitlines()


def _capture_display(monkeypatch):
    """Replace ``IPython.display.display`` and return the list of shown objects."""
    import IPython.display as ipython_display

    shown = []
    monkeypatch.setattr(ipython_display, "display", shown.append)
    return shown


# --- Default: nothing extra ------------------------------------------------

def test_default_adds_nothing(capsys):
    mpt[x := 5]
    assert _lines(capsys) == ["x := 5", "x := 5", "x := 5"]


# --- Raw text --------------------------------------------------------------

def test_text_repeats_the_column(capsys):
    mpt.configure(additional_out="text")
    mpt[x := 5]
    assert _lines(capsys) == [
        "x := 5", "x := 5", "x := 5",
        "x := 5", "x := 5", "x := 5",
    ]


def test_text_repeats_a_one_line_layout(capsys):
    mpt.configure(out_order="line", additional_out="text")
    mpt[x := 3 + 2]
    line = "x = 3 + 2 = 3 + 2 = 5"
    assert _lines(capsys) == [line, line]


def test_text_additional_after_rendered_latex(capsys, monkeypatch):
    shown = _capture_display(monkeypatch)
    mpt.configure(out_format="latex", additional_out="text")
    mpt[x := 5]
    assert len(shown) == 3
    assert _lines(capsys) == ["x := 5", "x := 5", "x := 5"]


def test_text_additional_after_latex_line_uses_python_syntax(capsys, monkeypatch):
    # The main line is built with `==` for py2tex; the raw Python copy must use
    # a single `=`, just as the plain-text layout does.
    shown = _capture_display(monkeypatch)
    mpt.configure(out_order="line", out_format="latex", additional_out="text")
    mpt[x := 3 + 2]
    assert len(shown) == 1
    assert _lines(capsys) == ["x = 3 + 2 = 3 + 2 = 5"]


# --- Raw LaTeX ------------------------------------------------------------

def test_latex_prints_the_raw_source_after_plain_text(capsys):
    pytest.importorskip("pytexit")
    mpt.configure(additional_out="latex")
    mpt[x := 5]
    assert _lines(capsys) == [
        "x := 5", "x := 5", "x := 5",
        "$$x=5$$", "$$x=5$$", "$$x=5$$",
    ]


def test_latex_prints_the_raw_source_after_rendered_latex(capsys, monkeypatch):
    pytest.importorskip("pytexit")
    shown = _capture_display(monkeypatch)
    mpt.configure(out_format="latex", additional_out="latex")
    mpt[x := 5]
    assert len(shown) == 3
    assert _lines(capsys) == ["$$x=5$$", "$$x=5$$", "$$x=5$$"]


def test_latex_additional_uses_the_line_layout(capsys):
    pytest.importorskip("pytexit")
    mpt.configure(out_order="line", additional_out="latex")
    mpt[x := 5]
    assert _lines(capsys) == [
        "x = 5 = 5 = 5",
        "$$x=5=5=5$$",
    ]


# --- All other settings apply ---------------------------------------------

def test_precision_and_number_format_apply_to_raw_text(capsys):
    mpt.configure(
        out_order="line",
        precision=4,
        number_format="power",
        additional_out="text",
    )
    a = 1.23e-9
    mpt[x := a]
    line = "x = a = 1.23*10**-9 = 1.23*10**-9"
    assert _lines(capsys) == [line, line]


def test_precision_and_number_format_apply_to_raw_latex(capsys):
    pytest.importorskip("pytexit")
    mpt.configure(
        out_order="line",
        precision=4,
        number_format="power",
        additional_out="latex",
    )
    a = 1.23e-9
    mpt[x := a]
    lines = _lines(capsys)
    assert lines[0] == "x = a = 1.23*10**-9 = 1.23*10**-9"
    assert lines[1].startswith("$$")
    assert "10}^{-9}" in lines[1]


def test_reduce_equ_stages_applies_to_both_outputs(capsys):
    mpt.configure(
        out_order="line",
        reduce_equ_stages=True,
        additional_out="text",
    )
    mpt[ro1 := (ro := (ro_БФСС := 2230))]
    line = "ro1 = (ro := (ro_БФСС := 2230)) = 2230"
    assert _lines(capsys) == [line, line]


# --- Turning it off again -------------------------------------------------

def test_none_removes_the_additional_output(capsys):
    mpt.configure(additional_out="text")
    mpt.configure(additional_out=None)
    mpt[x := 5]
    assert _lines(capsys) == ["x := 5", "x := 5", "x := 5"]
