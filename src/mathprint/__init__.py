"""The ``mpt`` macro: pretty-print math expressions in reports.

``mpt`` prints an expression twice:

  1. once symbolically, with variable names;
  2. once with the current values of those variables substituted in.

Values are looked up in the scope where the expression appears (they are
ordinary name references in the generated code), so whatever is visible at
the use site is what gets substituted.

Import the macro as a macro-import; the ``macros`` marker is mandatory for
mcpyrate::

    from mathprint import macros, mpt

The macro works both as a plain expression and as an assignment::

    mpt[(a + z) * 2]

    mpt[x := (a + z) * 2]

The assignment form additionally binds the name and uses it as a prefix on
both printed lines. In either form the macro evaluates to the value of the
expression, so the result can be assigned or printed::

    result = mpt[(a + z) * 2]

For comparison expressions (``==``, ``!=``, ``<``, ``<=``, ``>``, ``>=``,
``is``, ``in``, ...) the numeric line shows the value of each side of the
comparison (the right and left parts), instead of substituting names inside
the sides::

    from mathprint import macros, mpt
    import sympy as sp

    a = sp.symbols("a_a")
    y = 5
    z = 10
    mpt[y > (a + z) * 2]

prints::

    y > (a + z) * 2
    5 > 2*a_a + 20

Only names are substituted; no functions are evaluated. The expression
itself is evaluated exactly once, and its value is returned.

Usage::

    y = 5
    z = 10
    mpt[x := y * 7 + z]

prints::

    x := y * 7 + z
    x := 5 * 7 + 10

and assigns ``x = 45``.
"""

import ast
import copy

from mcpyrate.quotes import macros, q, a, u


_COMPARISON_OPS = {
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
    ast.Is: "is",
    ast.IsNot: "is not",
    ast.In: "in",
    ast.NotIn: "not in",
}


class _NamePlaceholderer(ast.NodeTransformer):
    """Replace each `Name` with a positional placeholder for `str.format`."""

    def __init__(self):
        self.names = []

    def visit_Name(self, node):
        index = len(self.names)
        self.names.append(node)
        placeholder = ast.Name(id=f"__mpt_value_{index}__", ctx=ast.Load())
        return ast.copy_location(placeholder, node)


def _name_template(value):
    """Return ``(template, names)`` for per-variable numeric rendering.

    `template` is a `str.format`-style template where every variable is a
    ``{}`` placeholder; `names` is the list of `Name` nodes, in the order
    the placeholders appear, to be passed to `str.format`.
    """
    placeholderer = _NamePlaceholderer()
    transformed = placeholderer.visit(copy.deepcopy(value))

    template = ast.unparse(transformed)
    # Escape literal braces (e.g. from dict/set displays) so `str.format`
    # treats them as literal text rather than as placeholders.
    template = template.replace("{", "{{").replace("}", "}}")
    for index in range(len(placeholderer.names)):
        template = template.replace(f"__mpt_value_{index}__", "{}")
    return template, placeholderer.names


def _comparison_template(value):
    """Return ``(template, sides)`` for a comparison.

    `template` renders the comparison with each side replaced by the value of
    that side, e.g. ``"{} > {}"``. `sides` is the list of operand expression
    nodes, in the order the placeholders appear, to be passed to `str.format`.
    """
    sides = [value.left, *value.comparators]
    chunks = []
    for index in range(len(sides)):
        chunks.append("{}")
        if index < len(value.ops):
            chunks.append(f" {_COMPARISON_OPS[type(value.ops[index])]} ")
    return "".join(chunks), sides


def mpt(expr, **kw):
    # Assignment form `mpt[name := expression]`; anything else (including a bare
    # expression such as `mpt[(a + z) * 2]`) is printed without a name prefix.
    if type(expr) is ast.NamedExpr and type(expr.target) is ast.Name:
        target = expr.target.id
        value = expr.value
        prefix = f"{target} := "
    else:
        value = expr
        prefix = ""

    symbolic = ast.unparse(value)

    # For a comparison, substitute the value of each side (right and left part);
    # otherwise substitute each variable name inside the expression.
    if type(value) is ast.Compare:
        template, operands = _comparison_template(value)
    else:
        template, operands = _name_template(value)

    numeric = ast.Call(func=ast.Attribute(
            value=ast.Constant(template),
            attr="format",
            ctx=ast.Load()
        ),
        args=operands,
        keywords=[]
    )

    # Runs left to right: print symbolic line, print numeric line, then
    # evaluate the original expression (assigning the name, if there is one,
    # and yielding the value, which becomes the value of the whole expression).
    return q[(
            print(u[f"{prefix}{symbolic}"]),
            print(u[prefix] + a[numeric]),
            a[expr]
        )[-1]
    ]
