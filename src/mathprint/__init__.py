"""One-line bootstrap for running scripts that use the ``mpt`` macro under plain ``python``.

Put this at the top of your script::

    from mathprint import mpt

Then use ``mpt[...]`` directly, without a separate macro-import line::

    from mathprint import mpt

    y = 5
    z = 10
    mpt[x := y * 7 + z]

The script then runs under both::

    python myscript.py
    macropython myscript.py

The macro implementation lives in the ``mathprint_main`` package; the classic
mcpyrate macro-import form keeps working, too::

    from mathprint_main import macros, mpt

**Why this is needed.** mcpyrate expands macros while a source file is being
compiled, but Python compiles the main script *before* running any of its code,
so the macro hook cannot be installed in time from within the script itself. On
import, this module activates the hook and re-compiles + re-runs the calling
script with the ``mpt`` macro registered. Under ``macropython`` (or on that
re-run) it does nothing, so the import is always safe.

Because the first (plain) run stops at the import and re-runs the file, put this
import **before** any other top-level side effects, ideally as line 1.

To disable mathprint in a module without touching any of its ``mpt[...]`` call
sites, import the no-op stub instead -- change only this one line::

    from mathprint.stub import mpt

See ``mathprint.stub`` for details. Importing that submodule must not activate
the macro hook, which is why ``mpt`` below is provided lazily (PEP 562).
"""

import os
import sys
from importlib.machinery import SourceFileLoader
from typing import TYPE_CHECKING, Any

__all__ = ["is_active", "mpt"]

if TYPE_CHECKING:
    # ``mpt`` exists for type checkers; at run time it is provided lazily by the
    # module-level ``__getattr__`` below.
    mpt: Any


def is_active():
    """Return whether mcpyrate's macro-aware import hook is installed."""
    return SourceFileLoader.source_to_code.__module__ == "mcpyrate.importer"


def _import_site_globals(start_frame):
    """Globals of the frame that performed the import, skipping importlib internals."""
    frame = start_frame
    while frame is not None:
        name = frame.f_globals.get("__name__", "")
        if name and name != "mathprint" and "importlib" not in name:
            return frame.f_globals
        frame = frame.f_back
    return None


def _load_macro():
    """Activate mcpyrate and return the ``mpt`` macro function."""
    try:
        from mcpyrate.activate import activate
        activate()
    except ImportError:
        pass
    import mcpyrate  # noqa: F401
    import mathprint_main
    return mathprint_main.mpt


_MISSING: Any = object()


def _run_as_main(path, macro):
    """Re-compile and re-run the top-level script with ``mpt`` available as a macro."""
    from mcpyrate.compiler import compile as mcompile
    from mcpyrate.core import global_bindings

    with open(path, "rb") as f:
        source = f.read()

    # Register the macro only while compiling the script, so that this does not
    # affect any other module imported later in the process.
    previous: Any = global_bindings.get("mpt", _MISSING)
    global_bindings["mpt"] = macro
    try:
        code = mcompile(source, filename=path, self_module="__main__")
    finally:
        if previous is _MISSING:
            global_bindings.pop("mpt", None)
        else:
            global_bindings["mpt"] = previous

    exec(code, sys.modules["__main__"].__dict__)
    sys.exit(0)


def _bootstrap(globals_, macro):
    if globals_ is None or globals_.get("__name__") != "__main__" or "__file__" not in globals_:
        return
    # In IPython / Jupyter there is no script to re-run; the notebook extension
    # (`mathprint_jupyter`) expands cells instead.
    if "get_ipython" in globals_:
        return
    if getattr(sys, "_mathprint_done", False):
        return
    setattr(sys, "_mathprint_done", True)
    _run_as_main(os.path.abspath(globals_["__file__"]), macro)


def __getattr__(name: str) -> Any:
    """Provide ``mpt`` lazily (PEP 562).

    Deferring this work to first attribute access keeps ``import
    mathprint.stub`` cheap: importing the no-op stub must *not* activate the
    macro hook or re-run the calling script.
    """
    if name != "mpt":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    macro = _load_macro()
    # Automatic bootstrap, but only for the top-level script.
    _bootstrap(_import_site_globals(sys._getframe()), macro)
    return macro
