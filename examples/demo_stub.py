# Demo of disabling `mpt` with the no-op stub.
#
# The call sites below are identical to `examples/demo.py`; only the import
# differs. To turn mathprint off in a module, replace
#
#     from mathprint import mpt
#
# with
#
#     from mathprint.stub import mpt
#
# Result: `mpt[...]` evaluates its argument once but prints nothing and returns
# None; no mcpyrate import hook is involved.
#
# Run with plain python:
#     python examples/demo_stub.py
from mathprint.stub import mpt

y = 5
z = 10

# The assignment form still binds x: `:=` runs while the subscript is evaluated.
mpt[x := y * 7 + z]
print("x =", x)  # 45 -- no "x := ..." lines are printed

mpt[(y + z) * 2]  # silently evaluated once; value discarded

print("result =", mpt[y > z])  # None -- the stub discards the value
