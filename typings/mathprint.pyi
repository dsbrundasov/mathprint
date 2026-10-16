"""Type stubs for the ``mathprint`` macros.

``mpt`` is a macro: it is invoked as ``mpt[expression]``, which static type
checkers would otherwise report as subscripting a function. ``macros`` is the
virtual marker name used by mcpyrate to macro-expand imports.
"""

from typing import Any

class _Macro:
    def __getitem__(self, item: Any) -> Any: ...
    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...

macros: Any

mpt: _Macro
