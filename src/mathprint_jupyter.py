"""IPython / Jupyter extension: run ``mpt`` macros in notebook cells.

Notebook and IPython cells are compiled directly by IPython, not imported
through mcpyrate's import hook, so macro invocations would not be expanded by
default. This extension installs an IPython AST transformer that routes each
cell through ``mcpyrate``'s macro expander.

Usage in a notebook::

    %load_ext mathprint_jupyter

Then, in any cell::

    from mathprint import mpt

    y = 5
    z = 10
    mpt[x := y * 7 + z]

Display options are grouped in ``mpt.configure(...)``; call it in any cell (it
applies to the rest of the notebook)::

    mpt.configure(out_format="latex")

Use ``out_order="line"`` for the one-line layout, and ``precision=n`` to show
numbers with ``n`` significant digits::

    mpt.configure(out_order="line", precision=4)

``multiple_assignment_reduce=True`` collapses a nested assignment chain such as
``ro1 := (ro := (c := 2230))`` to ``ro1 := 2230`` in the substitution phase.
``reduce_equ_stages=True`` drops repeated adjacent stages from a one-line result.

Unload with::

    %unload_ext mathprint_jupyter
"""

import ast

__all__ = ["load_ipython_extension", "unload_ipython_extension"]


class _MathprintASTTransformer(ast.NodeTransformer):
    """Route each cell's AST through mcpyrate's macro expander.

    Also captures the exact cell source, so that phase 1 of ``mpt`` can print
    the expression verbatim (a notebook cell has no source file to read).
    """

    def __init__(self):
        self.source = ""

    def capture_source(self, lines):
        """IPython ``input_transformers_post`` hook: remember the exact cell text."""
        self.source = "".join(lines)
        return lines

    def visit(self, node):
        try:
            from mcpyrate.activate import activate
            activate()
        except ImportError:
            pass
        import mathprint_main
        from mcpyrate.compiler import expand

        previous = mathprint_main.Source.override
        mathprint_main.Source.override = self.source
        try:
            return expand(node, filename="<ipython>", self_module=None)
        finally:
            mathprint_main.Source.override = previous


def load_ipython_extension(ipython):
    """Install the extension. Called by ``%load_ext mathprint_jupyter``."""
    try:
        from mcpyrate.activate import activate
        activate()
    except ImportError:
        pass
    import mcpyrate  # noqa: F401
    import mathprint_main
    from mcpyrate.core import global_bindings

    # Make `mpt` available as a macro everywhere in the kernel, so that the
    # one-liner `from mathprint import mpt` also works in cells.
    global_bindings["mpt"] = mathprint_main.mpt  # pyright: ignore[reportArgumentType]

    transformer = _MathprintASTTransformer()
    if transformer not in ipython.ast_transformers:
        ipython.ast_transformers.append(transformer)
    ipython.input_transformers_post.append(transformer.capture_source)


def unload_ipython_extension(ipython):
    """Remove the extension. Called by ``%unload_ext mathprint_jupyter``."""
    from mcpyrate.core import global_bindings

    for transformer in list(ipython.ast_transformers):
        if isinstance(transformer, _MathprintASTTransformer):
            ipython.ast_transformers.remove(transformer)
            try:
                ipython.input_transformers_post.remove(transformer.capture_source)
            except ValueError:
                pass
    global_bindings.pop("mpt", None)
