"""Pytest configuration.

Importing ``mcpyrate`` installs its macro-aware source-to-bytecode hook, and
registering ``mpt`` in mcpyrate's ``global_bindings`` makes the test modules'
one-line ``from mathprint import mpt`` expand. Both must happen before the test
modules are compiled. (Real code gets this from the bootstrap for the top-level
script or from the Jupyter extension; a test session sets it explicitly. The
no-op stub tests run in subprocesses, so this global binding never reaches them.)
"""

import mcpyrate  # noqa: F401

from mcpyrate.core import global_bindings

import mathprint_main

global_bindings["mpt"] = mathprint_main.mpt  # pyright: ignore[reportArgumentType]
