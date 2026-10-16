"""Pytest configuration.

Importing ``mcpyrate`` installs its macro-aware source-to-bytecode hook, which
must be active before the test modules are compiled so that their ``mpt[...]``
macro invocations are expanded.
"""

import mcpyrate  # noqa: F401
