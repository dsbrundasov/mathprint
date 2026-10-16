# run: macropython test.py

from mathprint import macros, mpt
import sympy as sp

a = sp.symbols('a_a')

y = 5
z = 10

mpt[x := y * 7 + z]
print("x =", x)

# Bare expression, no assignment.
mpt[(a + z) * 2]

# Comparison without assignment: the numeric line shows each side's value.
mpt[y > (a + z) * 2]

# Comparison with assignment.
mpt[k := (a + z) > 2]
print("k =", k)

# The macro evaluates to the value of the expression.
print("result =", mpt[y > (a + z) * 2])

# Chained comparison.
mpt[0 < y < (a + z) * 2]

print(type(a))
