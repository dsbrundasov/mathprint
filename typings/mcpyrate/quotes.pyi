"""Type stubs for the macro operators exported by ``mcpyrate.quotes``.

These are not real values at run time. The mcpyrate importer recognizes
``from mcpyrate.quotes import macros, q, a, u`` and injects the actual macro
implementations during macro expansion. The stubs exist only so that static
type checkers (Pylance/Pyright) understand the ``q[...]`` / ``a[...]`` /
``u[...]`` macro-invocation syntax instead of reporting it as subscripting a
function.
"""

from typing import Any

class _Macro:
    def __getitem__(self, item: Any) -> Any: ...
    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...

macros: Any

q: _Macro
u: _Macro
n: _Macro
a: _Macro
s: _Macro
t: _Macro
h: _Macro
