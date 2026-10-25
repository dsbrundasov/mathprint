"""Tests for the optional LaTeX output mode (``mpt.configure(out_format="latex")``).

The plain-text default must stay untouched, and LaTeX mode must route the three
lines through ``mathprint_main.Latex.show`` instead of ``print``. The actual
rendering needs ``pytexit`` + ``IPython``; those tests skip when ``pytexit`` is
missing (the plain-text path never imports it).
"""

import os

import pytest

import mathprint_main
from mathprint import mpt

_HERE = os.path.abspath(__file__)


@pytest.fixture(autouse=True)
def restore_latex_files():
    """Keep LaTeX-mode state isolated per test."""
    saved = set(mathprint_main.Printer.latex_scopes)
    mathprint_main.Printer.latex_scopes.clear()
    yield
    mathprint_main.Printer.latex_scopes.clear()
    mathprint_main.Printer.latex_scopes.update(saved)


@pytest.fixture
def shown(monkeypatch):
    """Capture the lines that would be rendered as LaTeX."""
    collected = []
    monkeypatch.setattr(mathprint_main.Latex, "show", collected.append)
    return collected


# --- Default: unchanged plain text -----------------------------------------

def test_default_is_plain_text(capsys):
    result = mpt[2 + 3]
    assert capsys.readouterr().out.splitlines() == ["2 + 3", "2 + 3", "5"]
    assert result == 5


def test_other_file_is_unaffected(capsys):
    mathprint_main.Printer.latex_scopes.add(os.path.abspath("some_other_file.py"))
    result = mpt[2 + 3]
    assert capsys.readouterr().out.splitlines() == ["2 + 3", "2 + 3", "5"]
    assert result == 5


# --- The `out_format` option -----------------------------------------------

def test_latex_option_enable_disable():
    assert mpt.configure(out_format="latex") == _HERE
    assert mathprint_main.Printer.latex_on(_HERE)
    assert mpt.configure(out_format="text") == _HERE
    assert not mathprint_main.Printer.latex_on(_HERE)


# --- Enabled: routes to LaTeX ----------------------------------------------

def test_enabled_routes_all_three_lines(shown):
    mpt.configure(out_format="latex")
    result = mpt[2 + 3]
    assert shown == ["2 + 3", "2 + 3", "5"]
    assert result == 5


def test_enabled_assignment_carries_name(shown):
    mpt.configure(out_format="latex")
    mpt[g_latex := 2 * 3]
    assert shown == ["g_latex := 2 * 3", "g_latex := 2 * 3", "g_latex := 6"]
    assert g_latex == 6


def test_enabled_prints_nothing_to_stdout(capsys, shown):
    mpt.configure(out_format="latex")
    mpt[1 + 1]
    assert capsys.readouterr().out == ""


def test_any_file_key_enables_everything(shown):
    mathprint_main.Printer.latex_scopes.add(mathprint_main.Printer.ANY_FILE)
    mpt[1 + 1]
    assert shown == ["1 + 1", "1 + 1", "2"]


# --- Keys and helpers -------------------------------------------------------

def test_latex_key_normalization():
    assert mathprint_main.Printer.key_of(None) == "*"
    assert mathprint_main.Printer.key_of("<ipython>") == "<ipython>"
    assert mathprint_main.Printer.key_of("x.py") == os.path.abspath("x.py")


def test_latex_enabled_membership():
    assert not mathprint_main.Printer.latex_on(os.path.abspath("x.py"))
    mathprint_main.Printer.latex_scopes.add(os.path.abspath("x.py"))
    assert mathprint_main.Printer.latex_on(os.path.abspath("x.py"))
    assert not mathprint_main.Printer.latex_on(os.path.abspath("y.py"))


def test_pytexit_input_rewrites_walrus():
    assert mathprint_main.Latex._to_input("x := 5") == "x == 5"
    assert mathprint_main.Latex._to_input("y + 2") == "y + 2"


def test_latex_switch_scopes_to_calling_file(tmp_path):
    import subprocess
    import sys
    from pathlib import Path

    script = tmp_path / "uselatex.py"
    script.write_text(
        "import os\n"
        "import mathprint_main\n"
        "from mathprint import mpt\n"
        "key = mpt.configure(out_format='latex')\n"
        "assert key == os.path.abspath(__file__), (key, __file__)\n"
        "assert mathprint_main.Printer.latex_on(os.path.abspath(__file__))\n"
        "print('ok')\n",
        encoding="utf-8",
    )
    src_root = Path(__file__).resolve().parents[1] / "src"
    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(src_root) + (os.pathsep + existing if existing else "")

    proc = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, env=env
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "ok"


# --- Rendering (requires pytexit) ------------------------------------------

def test_pytexit_renders_numeric_lines():
    pytest.importorskip("pytexit")
    mathprint_main.Latex._patch_pytexit()
    from pytexit import py2tex  # pyright: ignore[reportMissingModuleSource]

    tex = py2tex(
        mathprint_main.Latex._to_input("x := 5 * 7 + 10"),
        print_latex=False,
        print_formula=False,
        tex_multiplier=r"{\cdot}",
        simplify_output=False,
        simplify_multipliers=False,
    )
    assert "5" in tex
    assert "10" in tex
    assert "=" in tex


def test_pytexit_multiplier_does_not_glue_tokens():
    # Regression: a bare `\cdot` glues onto the next name (`\cdotC_L`), which
    # KaTeX rejects as an undefined control sequence.
    pytest.importorskip("pytexit")
    from pytexit import py2tex  # pyright: ignore[reportMissingModuleSource]

    tex = py2tex(
        "C_C == 0.22 * C_L",
        print_latex=False,
        print_formula=False,
        tex_multiplier=r"{\cdot}",
        simplify_output=False,
        simplify_multipliers=False,
    )
    assert r"\cdotC" not in tex
    assert r"{\cdot}" in tex


def test_pytexit_renders_dotted_attributes():
    # Regression: pytexit has no `visit_Attribute`, so a dotted line used to hit
    # its broken `generic_visit` and fall back to plain text in LaTeX mode.
    pytest.importorskip("pytexit")
    mathprint_main.Latex._patch_pytexit()
    from pytexit import py2tex  # pyright: ignore[reportMissingModuleSource]

    tex = py2tex(
        "me.H.atomic_number",
        print_latex=False,
        print_formula=False,
        tex_multiplier=r"{\cdot}",
        simplify_output=False,
        simplify_multipliers=False,
    )
    assert "me.H" in tex
    assert "atomic" in tex


def test_pytexit_keeps_every_multiplication_sign():
    # Regression: pytexit's `visit_Mult` returns a space and its `Mult` branch
    # switched to `tex_multiplier` only for float-literal operands, so
    # `2 * (0.07 * m)` rendered as `2 0.07\cdot m` -- a different formula.
    pytest.importorskip("pytexit")
    mathprint_main.Latex._patch_pytexit()
    from pytexit import py2tex  # pyright: ignore[reportMissingModuleSource]

    tex = py2tex(
        "M * 2 * (0.07 * m) / P",
        print_latex=False,
        print_formula=False,
        tex_multiplier=r"{\cdot}",
        simplify_output=False,
        simplify_multipliers=False,
    )
    assert "2 0.07" not in tex
    assert tex.count(r"{\cdot}") == 3   # M*2, 2*(...), 0.07*m


def test_pytexit_keeps_explicit_times_one():
    pytest.importorskip("pytexit")
    mathprint_main.Latex._patch_pytexit()
    from pytexit import py2tex  # pyright: ignore[reportMissingModuleSource]

    tex = py2tex(
        "1 * x",
        print_latex=False,
        print_formula=False,
        tex_multiplier=r"{\cdot}",
        simplify_output=False,
        simplify_multipliers=False,
    )
    assert r"1{\cdot}x" in tex


def test_latex_mode_keeps_multiplication_end_to_end(monkeypatch):
    pytest.importorskip("pytexit")
    import IPython.display as ipython_display

    calls = []
    monkeypatch.setattr(ipython_display, "display", lambda obj: calls.append(obj))

    mpt.configure(out_format="latex")
    a = 2
    b = 0.07
    mpt[a * (b * 3)]

    assert len(calls) == 3
    substituted = calls[1].data
    assert "2 0.07" not in substituted
    assert substituted.count(r"{\cdot}") == 2


def test_display_latex_handles_dotted_attribute(capsys, monkeypatch):
    pytest.importorskip("pytexit")
    import IPython.display as ipython_display
    from IPython.display import Latex

    calls = []
    monkeypatch.setattr(ipython_display, "display", lambda obj: calls.append(obj))

    mathprint_main.Latex.show("me.H.atomic_number")

    assert len(calls) == 1         # rendered as LaTeX, not printed as plain text
    assert isinstance(calls[0], Latex)
    assert capsys.readouterr().out == ""


def test_display_latex_shows_a_latex_object(monkeypatch):
    pytest.importorskip("pytexit")
    import IPython.display as ipython_display
    from IPython.display import Latex

    calls = []
    monkeypatch.setattr(ipython_display, "display", lambda obj: calls.append(obj))

    mathprint_main.Latex.show("x := 5")

    assert len(calls) == 1
    assert isinstance(calls[0], Latex)


def test_display_latex_falls_back_to_plain_text(capsys, monkeypatch):
    pytest.importorskip("pytexit")
    import IPython.display as ipython_display

    calls = []
    monkeypatch.setattr(ipython_display, "display", lambda obj: calls.append(obj))

    # `and` is not convertible by py2tex; the line must be printed, not crash.
    mathprint_main.Latex.show("x == (y and z)")

    assert calls == []
    assert capsys.readouterr().out.strip() == "x == (y and z)"
