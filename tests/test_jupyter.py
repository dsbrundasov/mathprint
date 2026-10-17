"""Tests for the IPython / Jupyter extension.

Skipped automatically when IPython is not installed.
"""

import contextlib
import io

import pytest

pytest.importorskip("IPython")

from IPython.core.interactiveshell import InteractiveShell  # noqa: E402

from mathprint_jupyter import load_ipython_extension, unload_ipython_extension  # noqa: E402


def _run(shell, code):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = shell.run_cell(code)
    return result, buf.getvalue()


@pytest.fixture
def shell():
    ip = InteractiveShell.instance()
    load_ipython_extension(ip)
    try:
        yield ip
    finally:
        unload_ipython_extension(ip)
        for name in ("a", "b", "c", "k", "mt", "x", "y", "z"):
            ip.user_ns.pop(name, None)


def test_one_liner_in_cell(shell):
    result, out = _run(shell, "from mathprint import mpt\ny = 5\nz = 10\nmpt[x := y+z]\n")
    assert result.success, result.error_in_exec
    assert "x := y+z" in out        # phase 1: exact source
    assert "x := 5+10" in out       # phase 2: substituted in place
    assert shell.user_ns["x"] == 15


def test_macro_import_in_cell(shell):
    result, out = _run(shell, "from mathprint_main import macros, mpt\na = 2\nb = 3\nmpt[c := a*b + a]\n")
    assert result.success, result.error_in_exec
    assert "c := a*b + a" in out
    assert "c := 2*3 + 2" in out
    assert shell.user_ns["c"] == 8


def test_module_not_expanded_in_cell(shell):
    result, out = _run(shell, "import math as mt\nz = 10\nmpt[mt.floor(z) + z]\n")
    assert result.success, result.error_in_exec
    assert "mt.floor(z) + z" in out
    assert "mt.floor(10) + 10" in out


def test_comparison_order_in_cell(shell):
    result, out = _run(shell, "from mathprint import mpt\ny = 5\nz = 10\nmpt[z > (y - 1) * 2]\n")
    assert result.success, result.error_in_exec
    assert "z > (y - 1) * 2" in out
    assert "10 > (5 - 1) * 2" in out
