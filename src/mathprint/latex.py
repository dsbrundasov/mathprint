"""Enable LaTeX rendering of ``mpt`` output, per file.

By default ``mpt`` prints plain text (three lines). Importing this module at the
top of a file switches **that file's** ``mpt`` output to LaTeX: each line is
converted with ``pytexit.py2tex`` and shown via ``IPython.display`` -- the classic
``display(Latex(py2tex(...)))`` recipe::

    from mathprint import mpt
    import mathprint.latex          # <- this file now renders LaTeX

The switch is scoped to the file (or, in a notebook, to the whole notebook), so
importing it here never affects other modules. To toggle it explicitly::

    import mathprint.latex as mpl

    mpl.enable()     # enable for the calling file (or notebook)
    mpl.disable()    # back to plain text
    mpl.is_enabled() # check the current state

Or target a specific file: ``mpl.enable("/path/to/file.py")``.

Requirements: LaTeX output needs ``pytexit`` and ``IPython`` -- the plain-text
path does not, and nothing here is imported until LaTeX mode is actually used
(``pytexit`` is imported lazily the first time a line is rendered).

Outside Jupyter / IPython, or when ``pytexit`` is unavailable, rendering raises
the usual ``ImportError``; import this module only where you want LaTeX.
"""

import os
import sys

__all__ = ["enable", "disable", "is_enabled"]


def _site_globals():
    """Globals of the module that imported (or called into) us."""
    from mathprint import _import_site_globals

    return _import_site_globals(sys._getframe())


def _normalize(target):
    """Normalize a file path the same way `mathprint_main._latex_key` does."""
    if target in ("*", "<ipython>"):
        return target
    return os.path.abspath(target)


def _site_key():
    """Scope key of the calling module: its file, or ``<ipython>`` in a notebook."""
    globals_ = _site_globals()
    if not globals_:
        return "*"
    path = globals_.get("__file__")
    if path:
        return os.path.abspath(path)
    if "get_ipython" in globals_:
        return "<ipython>"
    return "*"


def _resolve(target):
    return _site_key() if target is None else _normalize(target)


def enable(target=None):
    """Turn on LaTeX output for ``target`` (default: the calling file)."""
    import mathprint_main

    key = _resolve(target)
    mathprint_main._LATEX_FILES.add(key)
    return key


def disable(target=None):
    """Turn off LaTeX output for ``target`` (default: the calling file)."""
    import mathprint_main

    key = _resolve(target)
    mathprint_main._LATEX_FILES.discard(key)
    return key


def is_enabled(target=None):
    """Return whether LaTeX output is active for ``target`` (default: this file)."""
    import mathprint_main

    return mathprint_main._latex_enabled(_resolve(target))


# Importing the module switches the importing file to LaTeX output.
enable()
