"""Tests for the optional LaTeX output mode (``import mathprint.latex``).

The plain-text default must stay untouched, and LaTeX mode must route the three
lines through ``mathprint_main._display_latex`` instead of ``print``. The actual
rendering needs ``pytexit`` + ``IPython``; those tests skip when ``pytexit`` is
missing (the plain-text path never imports it).
"""

import os

import pytest

import mathprint_main
from mathprint_main import macros, mpt  # noqa: F401  (``macros`` is mcpyrate's marker)

_HERE = os.path.abspath(__file__)


@pytest.fixture(autouse=True)
def restore_latex_files():
    """Keep LaTeX-mode state isolated per test."""
    saved = set(mathprint_main._LATEX_FILES)
    mathprint_main._LATEX_FILES.clear()
    yield
    mathprint_main._LATEX_FILES.clear()
    mathprint_main._LATEX_FILES.update(saved)


@pytest.fixture
def shown(monkeypatch):
    """Capture the lines that would be rendered as LaTeX."""
    collected = []
    monkeypatch.setattr(mathprint_main, "_display_latex", collected.append)
    return collected


# --- Default: unchanged plain text -----------------------------------------

def test_default_is_plain_text(capsys):
    result = mpt[2 + 3]
    assert capsys.readouterr().out.splitlines() == ["2 + 3", "2 + 3", "5"]
    assert result == 5


def test_other_file_is_unaffected(capsys):
    mathprint_main._LATEX_FILES.add(os.path.abspath("some_other_file.py"))
    result = mpt[2 + 3]
    assert capsys.readouterr().out.splitlines() == ["2 + 3", "2 + 3", "5"]
    assert result == 5


# --- Enabled: routes to LaTeX ----------------------------------------------

def test_enabled_routes_all_three_lines(shown):
    mathprint_main._LATEX_FILES.add(_HERE)
    result = mpt[2 + 3]
    assert shown == ["2 + 3", "2 + 3", "5"]
    assert result == 5


def test_enabled_assignment_carries_name(shown):
    mathprint_main._LATEX_FILES.add(_HERE)
    mpt[g_latex := 2 * 3]
    assert shown == ["g_latex := 2 * 3", "g_latex := 2 * 3", "g_latex := 6"]
    assert g_latex == 6


def test_enabled_prints_nothing_to_stdout(capsys, shown):
    mathprint_main._LATEX_FILES.add(_HERE)
    mpt[1 + 1]
    assert capsys.readouterr().out == ""


def test_any_file_key_enables_everything(shown):
    mathprint_main._LATEX_FILES.add(mathprint_main._ANY_FILE)
    mpt[1 + 1]
    assert shown == ["1 + 1", "1 + 1", "2"]


# --- Keys and helpers -------------------------------------------------------

def test_latex_key_normalization():
    assert mathprint_main._latex_key(None) == "*"
    assert mathprint_main._latex_key("<ipython>") == "<ipython>"
    assert mathprint_main._latex_key("x.py") == os.path.abspath("x.py")


def test_latex_enabled_membership():
    assert not mathprint_main._latex_enabled(os.path.abspath("x.py"))
    mathprint_main._LATEX_FILES.add(os.path.abspath("x.py"))
    assert mathprint_main._latex_enabled(os.path.abspath("x.py"))
    assert not mathprint_main._latex_enabled(os.path.abspath("y.py"))


def test_pytexit_input_rewrites_walrus():
    assert mathprint_main._pytexit_input("x := 5") == "x == 5"
    assert mathprint_main._pytexit_input("y + 2") == "y + 2"


# --- The `mathprint.latex` module -------------------------------------------

def test_module_enable_disable():
    from mathprint import latex

    latex.disable()
    assert not mathprint_main._latex_enabled(_HERE)
    assert latex.enable() == _HERE
    assert mathprint_main._latex_enabled(_HERE)
    assert latex.is_enabled()
    latex.disable()
    assert not mathprint_main._latex_enabled(_HERE)


def test_module_enable_explicit_target():
    from mathprint import latex

    latex.enable("some_other_file.py")
    assert mathprint_main._latex_enabled(os.path.abspath("some_other_file.py"))
    latex.disable("some_other_file.py")
    assert not mathprint_main._latex_enabled(os.path.abspath("some_other_file.py"))


def test_import_enables_calling_file(tmp_path):
    import subprocess
    import sys
    from pathlib import Path

    script = tmp_path / "uselatex.py"
    script.write_text(
        "import os\n"
        "import mathprint_main\n"
        "from mathprint import latex\n"
        "assert mathprint_main._latex_enabled(os.path.abspath(__file__)), mathprint_main._LATEX_FILES\n"
        "assert mathprint_main._LATEX_FILES == {os.path.abspath(__file__)}, mathprint_main._LATEX_FILES\n"
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
    mathprint_main._fix_pytexit_constants()
    from pytexit import py2tex  # pyright: ignore[reportMissingModuleSource]

    tex = py2tex(
        mathprint_main._pytexit_input("x := 5 * 7 + 10"),
        print_latex=False,
        print_formula=False,
        tex_multiplier=r"\cdot",
        simplify_output=False,
        simplify_multipliers=False,
    )
    assert "5" in tex
    assert "10" in tex
    assert "=" in tex


def test_display_latex_shows_a_latex_object(monkeypatch):
    pytest.importorskip("pytexit")
    import IPython.display as ipython_display
    from IPython.display import Latex

    calls = []
    monkeypatch.setattr(ipython_display, "display", lambda obj: calls.append(obj))

    mathprint_main._display_latex("x := 5")

    assert len(calls) == 1
    assert isinstance(calls[0], Latex)
