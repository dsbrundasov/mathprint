# run: macropython test.py

from mathprint import macros, mpt
import sympy as sp

a = sp.symbols('a_a')

y = 5
z = 10

mpt[x := y * 7 + z]
print("x =", x)

mpt[k := (a + z) * 2]
print("a =", a)
print(type(a))
