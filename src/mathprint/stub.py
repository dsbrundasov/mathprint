"""No-op stand-in for the ``mpt`` macro.

Switch mathprint off in a module without touching any of its call sites -- you
change only the import line::

    # from mathprint import mpt        # real macro (needs mcpyrate)
    from mathprint.stub import mpt     # no-op (pure Python, no dependencies)

With this stub, ``mpt[expr]`` is an ordinary subscription: the bracketed
expression is still evaluated -- once -- but its value is discarded and ``mpt``
returns ``None``. Nothing is printed, and no macro expansion, import hook,
``mcpyrate``, or ``mathprint_main`` is involved.

Because the value is discarded, use the stub where the *value* of an ``mpt[...]``
call is not consumed. The assignment form ``mpt[name := expr]`` still works: the
``:=`` executes while the subscript is evaluated, independently of what ``mpt``
returns.

The subscript body is empty on purpose: ``pass`` compiles to a single
``LOAD_CONST None`` / ``RETURN_VALUE``, the cheapest possible ``__getitem__``
body (measurably faster than ``return item``), keeping the disabled path as
light as possible. This module is also deliberately self-contained: it imports
nothing from the rest of the project -- not even type annotations -- so
importing it can never activate the macro machinery.

**Why subscript syntax?** A macro such as ``mpt`` is invoked as ``mpt[expr]``,
not ``mpt(expr)``. Python parses ``mpt[expr]`` as a subscription, which hands
the *un-evaluated* expression AST to the macro at compile time (mcpyrate
replaces the whole ``mpt[...]`` node during expansion). A plain call ``mpt(expr)``
would instead evaluate ``expr`` eagerly and pass only its *value* at run time, so
the macro could not see the source text or the variable names. Subscript is
therefore mcpyrate's convention for macro invocations, and it lets the very same
``mpt[expr]`` line keep working when replaced by this stub.
"""

from typing import Any

__all__ = ["mpt"]


class _Stub:
    """A printing-free no-op replacement for the ``mpt`` macro.

    ``mpt`` is invoked with subscript syntax, ``mpt[expression]``. Python parses
    that as a subscription, so the expression is evaluated and handed to
    ``__getitem__``; the stub discards it and returns ``None``. The expression is
    still evaluated exactly once, matching the single evaluation of the real
    macro's phase 3.
    """

    __slots__ = ()

    def __getitem__(self, item: Any) -> None:
        pass


mpt = _Stub()
