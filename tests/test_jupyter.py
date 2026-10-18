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
    _clear_scopes()
    try:
        yield ip
    finally:
        unload_ipython_extension(ip)
        _clear_scopes()
        for name in ("a", "b", "c", "k", "mt", "r", "v", "x", "y", "z"):
            ip.user_ns.pop(name, None)


def _clear_scopes():
    import mathprint_main

    mathprint_main._LATEX_FILES.discard("<ipython>")
    mathprint_main._LATEX_FILES.discard(mathprint_main._ANY_FILE)
    mathprint_main._PRECISION_FILES.pop("<ipython>", None)


def test_one_liner_in_cell(shell):
    result, out = _run(shell, "from mathprint import mpt\ny = 5\nz = 10\nmpt[x := y+z]\n")
    assert result.success, result.error_in_exec
    assert "x := y+z" in out        # phase 1: exact source
    assert "x := 5+10" in out       # phase 2: substituted in place
    assert shell.user_ns["x"] == 15


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


def test_latex_mode_in_cell(shell):
    pytest.importorskip("pytexit")
    import mathprint_main

    result, out = _run(
        shell,
        "from mathprint import mpt\n"
        "mpt.latex()\n"
        "y = 5\n"
        "z = 10\n"
        "mpt[x := y+z]\n",
    )
    assert result.success, result.error_in_exec
    # The file/notebook opted in, so plain text is no longer printed.
    assert "x := y+z" not in out
    assert mathprint_main._latex_enabled("<ipython>")
    assert shell.user_ns["x"] == 15


def test_precision_mode_in_cell(shell):
    import mathprint_main

    result, out = _run(
        shell,
        "from mathprint import mpt\n"
        "mpt.precision(4)\n"
        "v = 3.123123412\n"
        "mpt[v + 0]\n",
    )
    assert result.success, result.error_in_exec
    assert "3.123 + 0" in out          # displayed with 4 significant digits
    assert "3.123123412 + 0" not in out
    assert mathprint_main._precision_for("<ipython>") == 4
    assert shell.user_ns["v"] == 3.123123412


def test_sequence_in_cell(shell):
    result, out = _run(
        shell,
        "from mathprint import mpt\n"
        "y = 5\n"
        "z = 10\n"
        "mpt[y + z, y * z]\n",
    )
    assert result.success, result.error_in_exec
    assert "y + z" in out and "5 + 10" in out
    assert "y * z" in out and "5 * 10" in out
    assert result.result == (15, 50)   # the call yields a tuple of the values
