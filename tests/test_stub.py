"""Tests for the no-op ``mathprint.stub`` replacement.

The stub must make ``mpt[...]`` behave as a printing-free no-op: the bracketed
expression is evaluated once, the value is discarded (``mpt[...]`` returns
``None``), nothing is printed, and none of the project's machinery is pulled in.

These tests run in a fresh interpreter on purpose. The test session registers
``mpt`` as a global mcpyrate macro (see ``conftest.py``); if the stub's uses of
``mpt[...]`` were compiled in that session, mcpyrate would expand them as the
*real* macro. Real code never has that global registration in effect for a
``mathprint.stub`` module, so the subprocess reflects reality.
"""

import os
import subprocess
import sys
from pathlib import Path


def _run(code):
    """Run `code` in a fresh interpreter that can import the local sources."""
    src_root = Path(__file__).resolve().parents[1] / "src"
    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(src_root) + (os.pathsep + existing if existing else "")
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
    )


def _assert_ok(proc):
    assert proc.returncode == 0, proc.stderr
    # The stub prints nothing; only our own marker may appear on stdout.
    assert proc.stdout == "ok\n", repr(proc.stdout)


# --- Behaviour: printing-free no-op ----------------------------------------

def test_prints_nothing_and_returns_none():
    _assert_ok(_run(
        "from mathprint.stub import mpt\n"
        "y = 5\n"
        "z = 10\n"
        "result = mpt[y + z]\n"
        "assert result is None, result\n"
        "print('ok')\n"
    ))


def test_expression_still_evaluated_once():
    _assert_ok(_run(
        "from mathprint.stub import mpt\n"
        "calls = []\n"
        "def touch(v):\n"
        "    calls.append(v)\n"
        "    return v\n"
        "mpt[touch(3)]\n"
        "assert calls == [3], calls\n"
        "print('ok')\n"
    ))


def test_assignment_form_still_binds():
    _assert_ok(_run(
        "from mathprint.stub import mpt\n"
        "mpt[x := 2 * 3]\n"
        "assert x == 6, x\n"
        "print('ok')\n"
    ))


def test_any_subscript_is_accepted():
    _assert_ok(_run(
        "from mathprint.stub import mpt\n"
        "assert mpt[123, 234, 'qwe'] is None\n"
        "assert mpt[2 + 3] is None\n"
        "print('ok')\n"
    ))


# --- Isolation: nothing from the project is loaded -------------------------

def test_import_stub_is_self_contained():
    """In a fresh interpreter, importing the stub loads neither mcpyrate nor
    ``mathprint_main`` and installs no import hook."""
    _assert_ok(_run(
        "import sys\n"
        "from mathprint.stub import mpt\n"
        "assert 'mcpyrate' not in sys.modules, "
        "[m for m in sys.modules if 'mcpy' in m]\n"
        "assert 'mathprint_main' not in sys.modules, 'mathprint_main was imported'\n"
        "assert mpt[2 + 3] is None\n"
        "print('ok')\n"
    ))
