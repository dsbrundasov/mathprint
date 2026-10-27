"""Per-scope display settings: everything ``mpt.configure(...)`` can change.

The core of the macro is always the same: take the expression's source text,
substitute the current values of its names, evaluate the expression once and
show the value as Python prints it.  :class:`DisplaySettings` describes the
optional extras layered on top of that core; its defaults are exactly the core,
so ``DisplaySettings()`` means "three plain text lines in a column".

A setting belongs to a *scope*: a source file (keyed by its absolute path), a
notebook (``"<ipython>"``), or :attr:`SettingsStore.ANY_FILE` when no file is
known.  The expanded code asks the store for one :class:`DisplaySettings`
object per ``mpt`` call, so the rest of the package never has to know which
options exist or where they are stored.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any, ClassVar, Literal


@dataclass(frozen=True)
class DisplaySettings:
    """One scope's display options.  The defaults are the core behaviour.

    Every field matches the ``mpt.configure(...)`` argument of the same name.
    """

    #: ``"column"``: source, substitution and value on separate lines.
    #: ``"line"``: all three joined into one line (``x = 3 + y = 3 + 5 = 8``).
    out_order: Literal["column", "line"] = "column"

    #: ``"text"``: plain lines.  ``"latex"``: each line rendered as LaTeX.
    out_format: Literal["text", "latex"] = "text"

    #: Significant digits shown for plain numbers, or ``None`` for full precision.
    precision: int | None = None

    #: Collapse a nested assignment chain in the substitution phase.
    multiple_assignment_reduce: bool = False

    #: Drop repeated adjacent stages from a one-line result.
    reduce_equ_stages: bool = False

    #: ``"exp"``: Python's notation.  ``"power"``: show a power of ten.
    number_format: Literal["exp", "power"] = "exp"

    #: Repeat the lines as raw text after the main output (``"latex"`` or
    #: ``"text"``), or ``None`` for no extra output.
    additional_out: Literal["latex", "text"] | None = None


class SettingsStore:
    """The scope -> :class:`DisplaySettings` registry.

    This is the only mutable state of the package.  A scope without its own
    entry falls back to :attr:`ANY_FILE`, which is what makes the settings of a
    notebook (``"<ipython>"``) or of "no file" work.
    """

    #: Scope key meaning "every file" (used when no filename is known).
    ANY_FILE: ClassVar[str] = "*"

    #: Scope key -> settings, for scopes that changed at least one option.
    scopes: ClassVar[dict[str, DisplaySettings]] = {}

    # --- scope keys ---------------------------------------------------------

    @classmethod
    def key_for_filename(cls, filename: str | None) -> str:
        """Map a source `filename` to a scope key."""
        if not filename:
            return cls.ANY_FILE
        if filename.startswith("<") and filename.endswith(">"):
            return filename  # virtual name such as "<ipython>", not a real path
        return os.path.abspath(filename)

    @classmethod
    def key_for_globals(cls, globals_: Mapping[str, Any]) -> str:
        """Scope key for a live module/cell's globals (backs ``mpt.configure``)."""
        if not globals_:
            return cls.ANY_FILE
        path = globals_.get("__file__")
        if isinstance(path, str):
            return cls.key_for_filename(path)
        if "get_ipython" in globals_:
            return "<ipython>"
        return cls.ANY_FILE

    # --- reading and writing settings ---------------------------------------

    @classmethod
    def settings_for(cls, key: str) -> DisplaySettings:
        """`key`'s settings, or the :attr:`ANY_FILE` fallback, or the defaults."""
        settings = cls.scopes.get(key)
        if settings is not None:
            return settings
        return cls.scopes.get(cls.ANY_FILE, DisplaySettings())

    @classmethod
    def update(cls, key: str, **changes: Any) -> DisplaySettings:
        """Return `key`'s settings with `changes` applied, and store them."""
        settings = replace(cls.settings_for(key), **changes)
        cls.scopes[key] = settings
        return settings

    @classmethod
    def reset(cls, key: str) -> DisplaySettings:
        """Drop `key`'s own entry, so it uses the :attr:`ANY_FILE` fallback."""
        cls.scopes.pop(key, None)
        return cls.settings_for(key)

    # --- test helpers -------------------------------------------------------

    @classmethod
    def snapshot(cls) -> dict[str, DisplaySettings]:
        """A copy of the registry, for restoring it after a test."""
        return dict(cls.scopes)

    @classmethod
    def restore(cls, snapshot: dict[str, DisplaySettings]) -> None:
        """Replace the registry with a :meth:`snapshot` taken earlier."""
        cls.scopes.clear()
        cls.scopes.update(snapshot)
