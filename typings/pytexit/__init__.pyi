"""Minimal type stubs for ``pytexit`` (only what mathprint's LaTeX mode uses).

``pytexit`` is an optional dependency, absent from the type-checking
environment, so these stubs let Pylance/Pyright resolve the imports.
"""

from typing import Any

def py2tex(expr: str, **kwargs: Any) -> str: ...
