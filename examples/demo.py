# Demo of the `mpt` macro. Requires the package to be installed, e.g.
#     python -m pip install -e .
#
# Run with either:
#     python examples/demo.py
#     macropython examples/demo.py
from mathprint import mpt  # one line: enables macros and provides `mpt`
import sympy as sp
import math as mt

a = sp.symbols("a_a")

y = 5
z = 10

# Phase 1 is the source exactly as written; phase 2 substitutes values in place.
mpt[x := y * 7 + z]
print("x =", x)

mpt[x := mt.sqrt(y * 7) + z**2 / ((z - 10**8) / (y**z - 12*z))]
print("x =", x)

mpt[x :=
    mt.sqrt(y * 7 + z**2)/(
        (z - 10**8) / (y**z - 12*z)
    )
]
print("x =", x)

# Bare expression, no assignment.
mpt[(a + z) * 2]

# Comparison: variables are substituted in place, order preserved (no evaluation).
mpt[y > (a + z) * 2]

# Comparison with assignment.
mpt[k := (a + z + 14) > 2 + 10]
print("k =", k)

# The macro evaluates to the value of the expression.
print("result =", mpt[y > (a + z) * 2])

# Chained comparison.
mpt[0 < y < (a + z) * 2]

# Spacing in the source line is preserved exactly.
mpt[  y*(z - y)+z  ]

# Function and class names are not expanded either (like module names):
# `area` and `int` stay as written, not `<function ...>` / `<class ...>`.
def area(r):
    return 3.14159 * r * r

mpt[area(y) + int(z)]

# Several expressions in one call: each item is printed in order, exactly as if
# it had its own `mpt[...]`, and the call yields a tuple of the values.
mpt[
    s_diff := (s_11 := (s_12 := y + z)),
    p_diff := (p_11 := (p_12 := y * z)),
]
print("returned tuple:", s_diff, p_diff)

