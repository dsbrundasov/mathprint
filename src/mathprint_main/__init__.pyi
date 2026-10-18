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

# Set by the Jupyter extension during cell expansion.
_SOURCE_OVERRIDE: Any

# --- LaTeX output mode ----------------------------------------------------
# Scope keys of files that opted into LaTeX output (see `mathprint.latex`).
_LATEX_FILES: set[str]
_ANY_FILE: str

def _latex_key(filename: Any) -> str: ...
def _latex_enabled(key: str) -> bool: ...
def _emit(key: str, text: str) -> None: ...
def _print_value(key: str, prefix: str, value: Any) -> Any: ...
def _pytexit_input(text: str) -> str: ...
def _display_latex(text: str) -> None: ...
def _fix_pytexit_constants() -> None: ...
