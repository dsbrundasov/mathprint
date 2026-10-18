"""Tests for the no-op ``mathprint.stub`` replacement.

The stub must make ``mpt[...]`` behave as a printing-free no-op: the bracketed
expression is evaluated once, the value is discarded (``mpt[...]`` returns
``None``), nothing is printed, and none of the project's machinery is pulled in.
"""

import os
import subprocess
import sys
from pathlib import Path

from mathprint.stub import mpt


# --- Behaviour: printing-free no-op ----------------------------------------

def test_prints_nothing_and_returns_none(capsys):
    y = 5
    z = 10
    result = mpt[y + z]
    assert capsys.readouterr().out == ""
    assert result is None


def test_expression_still_evaluated_once(capsys):
    calls = []

    def touch(value):
        calls.append(value)
        return value

    mpt[touch(3)]
    assert capsys.readouterr().out == ""
    assert calls == [3]


def test_assignment_form_still_binds(capsys):
    # The `:=` runs while the subscript is evaluated, regardless of the return
    # value of `mpt[...]`.
    mpt[x := 2 * 3]
    assert capsys.readouterr().out == ""
    assert x == 6


def test_any_subscript_is_accepted(capsys):
    assert mpt[123, 234, "qwe"] is None
    assert mpt[2 + 3] is None
    assert capsys.readouterr().out == ""


# --- Isolation: nothing from the project is loaded -------------------------

def test_import_stub_is_self_contained():
    """In a fresh interpreter, importing the stub loads neither mcpyrate nor
    ``mathprint_main`` and installs no import hook."""
    src_root = Path(__file__).resolve().parents[1] / "src"
    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(src_root) + (os.pathsep + existing if existing else "")

    code = (
        "import sys\n"
        "from mathprint.stub import mpt\n"
        "assert 'mcpyrate' not in sys.modules, "
        "[m for m in sys.modules if 'mcpy' in m]\n"
        "assert 'mathprint_main' not in sys.modules, 'mathprint_main was imported'\n"
        "assert mpt[2 + 3] is None\n"
        "print('ok')\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "ok"
