"""Custom macros for pretty-printing math expressions in reports.

The `echo` macro prints an expression twice:

  1. once symbolically, with variable names;
  2. once with the current values of those variables substituted in.

Values are looked up in the scope where the expression appears (they are
ordinary name references in the generated code), so whatever is visible at
the use site is what gets substituted.

Only names are substituted; no functions are evaluated. The expression
itself is evaluated exactly once, and its value is returned.

Usage::

    y = 5
    z = 10
    echo[x := y * 7 + z]

prints::

    x := y * 7 + z
    x := 5 * 7 + 10

and assigns ``x = 45``.
"""

import ast
import copy

from mcpyrate.quotes import macros, q, a, u


class _ValuePlaceholderer(ast.NodeTransformer):
    """Replace each `Name` with a positional placeholder for `str.format`."""

    def __init__(self):
        self.names = []

    def visit_Name(self, node):
        index = len(self.names)
        self.names.append(node)
        placeholder = ast.Name(id=f"__echo_value_{index}__", ctx=ast.Load())
        return ast.copy_location(placeholder, node)


def _numeric_template(value):
    """Return ``(template, names)`` for the runtime numeric rendering.

    `template` is a `str.format`-style template where every variable is a
    ``{}`` placeholder; `names` is the list of `Name` nodes, in the order
    the placeholders appear, to be passed to `str.format`.
    """
    placeholderer = _ValuePlaceholderer()
    transformed = placeholderer.visit(copy.deepcopy(value))

    template = ast.unparse(transformed)
    for index in range(len(placeholderer.names)):
        template = template.replace(f"__echo_value_{index}__", "{}")
    return template, placeholderer.names


def mpt(expr, **kw):
    if type(expr) is not ast.NamedExpr or type(expr.target) is not ast.Name:
        raise SyntaxError("echo: use the assignment form `echo[name := expression]`")

    target = expr.target.id
    value = expr.value

    symbolic = ast.unparse(value)
    template, names = _numeric_template(value)
    numeric = ast.Call(func=ast.Attribute(
            value=ast.Constant(template),
            attr="format",
            ctx=ast.Load()
        ),
        args=names,
        keywords=[]
    )

    # Runs left to right: print symbolic line, print numeric line, then
    # evaluate the original `name := expression` (assigning the name and
    # yielding the value, which becomes the value of the whole expression).
    return q[(
            print(u[f"{target} := {symbolic}"]),
            print(u[f"{target} := "] + a[numeric]),
            a[expr]
        )[-1]
    ]
