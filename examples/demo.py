# Demo of the `mpt` macro. Requires the package to be installed, e.g.
#     python -m pip install -e .
#
# Run with either:
#     python examples/demo.py
#     macropython examples/demo.py
import os
import sys

# --- Bootstrap so that plain `python demo.py` works -------------------------
# mcpyrate expands macros while a source file is being compiled. Plain Python
# compiles the main script before running any of its code, so the hook cannot be
# installed in time from within the script itself. When we detect that mcpyrate
# is not active, install it and re-execute this file once through the (now
# macro-aware) import machinery.
from importlib.machinery import SourceFileLoader

if SourceFileLoader.source_to_code.__module__ != "mcpyrate.importer":
    import importlib.util
    import mcpyrate  # noqa: F401  installs the macro-aware source -> bytecode hook

    _spec = importlib.util.spec_from_file_location("__main__", os.path.abspath(__file__))
    if _spec is None or _spec.loader is None:
        raise ImportError(f"could not load {__file__!r} as a module")
    _module = importlib.util.module_from_spec(_spec)
    sys.modules["__main__"] = _module
    _spec.loader.exec_module(_module)
    sys.exit(0)
# ----------------------------------------------------------------------------

from mathprint import macros, mpt
import sympy as sp

a = sp.symbols("a_a")

y = 5
z = 10

# Assignment form: prints the expression with a name prefix, and binds the name.
mpt[x := y * 7 + z]
print("x =", x)

# Bare expression, no assignment.
mpt[(a + z) * 2]

# Comparison without assignment: the numeric line shows each side's value.
mpt[y > (a + z) * 2]

# Comparison with assignment.
mpt[k := (a + z) > 2]
print("k =", k)

# The macro evaluates to the value of the expression.
print("result =", mpt[y > (a + z) * 2])

# Chained comparison.
mpt[0 < y < (a + z) * 2]
