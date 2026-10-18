"""Pytest configuration.

Importing ``mcpyrate`` installs its macro-aware source-to-bytecode hook, and
``from mathprint import mpt`` registers ``mpt`` as a global macro. Both must
happen before the test modules are compiled so that their ``mpt[...]`` macro
invocations are expanded -- exactly as in real code, where the same one-line
import is all that is needed.
"""

import mcpyrate  # noqa: F401

from mathprint import mpt  # noqa: F401
