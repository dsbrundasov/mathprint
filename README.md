# mathprint

[![Python](https://img.shields.io/badge/python-%3E%3D3.9-blue)](https://www.python.org/)
[![mcpyrate](https://img.shields.io/badge/mcpyrate-%3E%3D4.0-green)](https://github.com/Technologicat/mcpyrate)

An [mcpyrate](https://github.com/Technologicat/mcpyrate) macro `mpt` that prints a mathematical expression as **three lines**:

1. **Symbolically** — exactly as written in the source code (names preserved).
2. **With values substituted** — each variable replaced in place by its current value.
3. **The computed value** — the expression, evaluated exactly once.

Values are taken from the scope where the macro is used, so the substituted line
reflects the actual runtime state. The expression is evaluated only **once**: the
printed value and the macro's return value come from that single evaluation.

> **Vibecode project** — built by iterating with an AI assistant. See
> [Vibecode project](#vibecode-project) at the end.

---

## Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Several expressions in one call](#several-expressions-in-one-call)
- [Jupyter / IPython](#jupyter--ipython)
- [Configuration](#configuration)
- [Layout: one line or a column](#layout-one-line-or-a-column)
- [LaTeX output](#latex-output)
- [Display precision](#display-precision)
- [Number format](#number-format)
- [Nested assignments](#nested-assignments)
- [Repeated stages](#repeated-stages)
- [Disabling mathprint (no-op stub)](#disabling-mathprint-no-op-stub)
- [How it works (three phases)](#how-it-works-three-phases)
- [Order guarantee](#order-guarantee)
- [Pylance / Pyright](#pylance--pyright)
- [Updating the package](#updating-the-package)
- [Development](#development)
- [Project structure](#project-structure)
- [Vibecode project](#vibecode-project)

---

## Features

```python
from mathprint import mpt

import sympy as sp

a = sp.symbols("a")   # symbolic variable
y = 5
z = 10

# Assignment: prints with name prefix and binds x.
mpt[x := y * 7 + z]
# x := y * 7 + z
# x := 5 * 7 + 10
# x := 45

# Bare expression.
mpt[(a + z) * 2]
# (a + z) * 2
# (a + 10) * 2
# 2*a + 20

# Comparison: variables substituted in place, order preserved.
mpt[y > (a + z) * 2]
# y > (a + z) * 2
# 5 > (a + 10) * 2
# 2*a + 20 < 5
```

- Prints **three lines**: the source, the substitution, and the computed value.
  The expression is evaluated **once**.
- Several expressions in one call — `mpt[a, b, ...]` — each printed as if it had
  its own `mpt[...]`, and the call yields a tuple of the values. See
  [Several expressions in one call](#several-expressions-in-one-call).
- All comparison operators (`==`, `!=`, `<`, `<=`, `>`, `>=`, `is`, `in`, …) and
  chained comparisons (`0 < y < z`).
- Only **names** and **dotted attribute chains rooted at a name** are
  substituted (`me.H.atomic_number`). Assignment targets (e.g. the name left of
  `:=`) are not substituted.
- Module, function and class names are **not** expanded: `math.floor(y)` stays
  `math.floor(5)` (not `<module 'math' …>.floor(5)`), `f(y)` stays `f(5)` (not
  `<function f at 0x…>(5)`), and `int(y)` stays `int(5)` (not `<class 'int'>(5)`).
  The same applies to any other callable, and to attribute chains whose value is
  a module/function/class/callable — but a chain that resolves to a plain value
  is substituted: `me.H.atomic_number` prints as `1`.
- Works under both `python` and `macropython`.
- Optional **one-line layout**: `mpt.configure(out_order="line")` joins the three
  phases into a single line — `x = 3 + y = 3 + 5 = 8` — per file. A column of
  lines is the default; `out_order="column"` switches back. See
  [Layout: one line or a column](#layout-one-line-or-a-column).
- Optional **LaTeX output** (Jupyter): `mpt.configure(out_format="latex")`
  renders the three lines as LaTeX via `pytexit` + `IPython.display`, per file.
  Plain text stays the default. See [LaTeX output](#latex-output).
- Optional **display precision**: `mpt.configure(precision=n)` shows numbers with
  `n` significant digits, per file, without affecting the computed value. See
  [Display precision](#display-precision).
- Optional **number format**: `mpt.configure(number_format="power")` shows
  `1.23e-09` as `1.23*10**-9` and `0.0001106` as `1.106*10**-4`, per file.
  Python's own notation stays the default (`"exp"`). See
  [Number format](#number-format).
- Optional **nested-assignment collapsing**:
  `mpt.configure(multiple_assignment_reduce=True)` shows a chain such as
  `ro1 := (ro := (ro_БФСС := 2230))` as `ro1 := 2230` in the substitution phase.
  See [Nested assignments](#nested-assignments).
- Optional **stage deduplication**: `mpt.configure(reduce_equ_stages=True)` drops
  repeated adjacent stages from a one-line result
  (`ro1 = (ro := (...)) = 2230 = 2230` → `ro1 = (ro := (...)) = 2230`). See
  [Repeated stages](#repeated-stages).

---

## Requirements

- Python >= 3.9
- `mcpyrate` (installed automatically as a dependency)
- Optional: `sympy` for symbolic expressions
- Optional: `pytexit` + `IPython` for LaTeX output (`pip install ".[latex]"`)

---

## Installation

Open a terminal in the project root (`MathPrint`) and run for the interpreter /
environment you will use.

### Editable mode (recommended for development)

```powershell
python -m pip install -e . --no-compile
```

The package is linked to these sources — edits take effect on the next run without
reinstalling. Use this if you plan to modify the code.

### Regular install (copy into site-packages)

```powershell
python -m pip install . --no-compile
```

### With dev tools (sympy, pytest)

```powershell
python -m pip install -e ".[dev]" --no-compile
```

### Uninstall

```powershell
python -m pip uninstall mathprint
```

> **Always use `--no-compile`.** mcpyrate breaks `compileall` on Python 3.14.

### Clean install / reinstall (if something broke)

```powershell
python -m pip uninstall mathprint -y
python -m pip cache purge
python -m pip install -e . --no-compile
python -c "import mathprint; print(mathprint.__file__)"
# Expected: ...\src\mathprint\__init__.py
```

> **Troubleshooting.** If `from mathprint import mpt` raises
> `ImportError: cannot import name 'macros'`, a stale `mathprint/` package
> (from before the rename) is left in `site-packages`. Close all Python/Jupyter/
> VS Code processes and delete that directory manually, then reinstall.

---

## Usage

Use a single import line:

```python
from mathprint import mpt
```

After this import, `mpt[...]` is available immediately:

```python
from mathprint import mpt

y = 5
z = 10
mpt[x := y * 7 + z]
```

`mathprint` is a small helper module shipped with the package; the macro
implementation lives in the internal `mathprint_main` package. The import
activates mcpyrate and, for a top-level script, re-runs it with `mpt` registered
as a macro.

### Running a script with macros

Macros are expanded at compile time. Python compiles the main script **before**
running any of its code, so the macro hook is not installed in time from within
the script itself. Two options:

1. **Via macropython** (no script changes):
   ```powershell
   macropython myscript.py
   # or, if the console command is unavailable:
   python -m mcpyrate.repl.macropython myscript.py
   ```

2. **Plain `python myscript.py`** — put `from mathprint import mpt` as the
   **first line** of the script. The helper activates the hook and re-runs the
   file with macros expanded. Under `macropython` (or on the re-run) it does
   nothing, so the import is always safe.

   Place this import before any other top-level side effects, because the first
   (plain) run stops at the import and re-runs the file.

Both ways work; pick whichever fits.

### Pylance / Pyright

The package ships `py.typed` and `__init__.pyi`, so `mpt[...]` is not flagged as
an error and Pylance understands the macro-call syntax. The stub also describes
`mpt.configure(...)` in full (signature, allowed values and per-argument
documentation), so hovering over `mpt.configure` in VS Code shows the settings
and what each argument does.

---

## Several expressions in one call

A single call can sequence several expressions, one per comma. Each item is
printed exactly as if it had its own `mpt[...]` call, in order, and the call
yields a **tuple** of the values:

```python
from mathprint import mpt
from math import pi

L_min = 2e-6
GBW = 10e6
C_C = 1e-12

mpt[
    L_diff := (L_11 := (L_12 := 2*L_min)),
    g_m_diff := (g_m_11 := (g_m_12 := (GBW * 2*pi * C_C))),
]
```

prints, in order:

```
L_diff := (L_11 := (L_12 := 2*L_min))
L_diff := (L_11 := (L_12 := 2*2e-06))
L_diff := 4e-06
g_m_diff := (g_m_11 := (g_m_12 := (GBW * 2*pi * C_C)))
g_m_diff := (g_m_11 := (g_m_12 := (10000000.0 * 2*3.141592653589793 * 1e-12)))
g_m_diff := 6.283185307179587e-05
```

and returns `(4e-06, 6.283185307179587e-05)`. Names bound with `name := ...`
inside an item land in the scope of the call, exactly as for a standalone
`mpt[name := ...]`, so the tuple unpacks and the inner names exist too:

```python
L_diff, g_m_diff = mpt[
    L_diff := (L_11 := (L_12 := 2*L_min)),
    g_m_diff := (g_m_11 := (g_m_12 := (GBW * 2*pi * C_C))),
]
# L_diff == 4e-06, g_m_diff == 6.28...e-05, L_11 == L_12 == 4e-06, ...
```

This is equivalent to writing one `mpt[...]` per expression.

> A tuple *value* behind a single name is still one expression: `mpt[t]` where
> `t = (1, 2, 3)` prints the tuple, it does not sequence anything. The sequence
> form is the top-level comma inside the subscript.

---

## Jupyter / IPython

Notebook cells are compiled directly by IPython and do **not** go through
mcpyrate's import hook, so `mpt[...]` is not expanded by default. A Jupyter
extension is provided:

```python
%load_ext mathprint_jupyter
```

After that, use `mpt` in any cell just like in scripts:

```python
from mathprint import mpt

import math as mt
import sympy as sp

a = sp.symbols("a")
y = 5
z = 10

mpt[x := y * 7 + z]
# x := y * 7 + z
# x := 5 * 7 + 10
# x := 45
x  # → 45

mt.floor(z) + z  # → mt.floor(10) + 10
```

> Module names are **not** expanded: `math` stays a name, not
> `<module 'math' (built-in)>`, so `mt.floor(y)` prints as `mt.floor(5)`.

Unload with:

```python
%unload_ext mathprint_jupyter
```

A complete example notebook is in [examples/demo.ipynb](examples/demo.ipynb).

---

## Configuration

All display settings are grouped in a single call, `mpt.configure(...)`. It
affects the file (or notebook) it is called in and returns the scope key that
changed (the file path, or `<ipython>` in a notebook):

```python
from mathprint import mpt

mpt.configure(out_order="line", out_format="latex", precision=4)
```

| Option | Values | Default | Meaning |
|---|---|---|---|
| `out_order` | `"column"` \| `"line"` | `"column"` | three lines, or all three phases on one line |
| `out_format` | `"text"` \| `"latex"` | `"text"` | plain text, or LaTeX (Jupyter) |
| `precision` | `int` \| `None` | `None` (full) | significant digits shown; `None` resets |
| `multiple_assignment_reduce` | `bool` | `False` | collapse a nested assignment chain in phase 2 |
| `reduce_equ_stages` | `bool` | `False` | drop repeated adjacent stages from a one-line result |
| `number_format` | `"exp"` \| `"power"` | `"exp"` | Python's notation, or a power of ten |

Every argument is optional, and **an omitted argument is left unchanged** — so
`mpt.configure(precision=2)` only touches the precision:

```python
mpt.configure(out_order="line")      # one-line layout; format and precision as they were
mpt.configure(out_format="latex")    # LaTeX; layout and precision as they were
mpt.configure(precision=None)        # full precision again
mpt.configure(multiple_assignment_reduce=True)  # collapse nested assignments
mpt.configure(reduce_equ_stages=True)          # drop repeated one-line stages
mpt.configure(number_format="power")           # 1.23*10**-9 instead of 1.23e-09
```

Invalid values raise `ValueError`. The settings are per file (or per notebook in
Jupyter), so they never leak between modules. The sections below cover each
option in detail.

---

## Layout: one line or a column

By default the three phases are a **column** — one line each. To join them into a
single line — the name appearing once — set `out_order="line"`:

```python
from mathprint import mpt

mpt.configure(out_order="line")
y = 5
mpt[x := 3 + y]
# x = 3 + y = 3 + 5 = 8

mpt[3 + y]
# 3 + y = 3 + 5 = 8
```

The phases are joined with ` = `; the source and the substitution keep their
exact spelling (parentheses included). `mpt.configure(out_order="column")`
restores the default column. Both forms affect the file (or notebook) they are
called in and return the scope key that changed.

With `out_format="latex"` also active, a one-line result is joined with `==` so
`pytexit` renders it as a chain of `=`:

```python
mpt.configure(out_order="line", out_format="latex")
mpt[x := 3 + y]
# LaTeX:  x = 3 + y = 3 + 5 = 8
```

The layout combines with the other per-file settings (`out_format`, `precision`).

---

## LaTeX output

Output is **plain text by default**. To render the three lines as LaTeX — like
`display(Latex(py2tex(...)))` — set `out_format="latex"` once in the file:

```python
%load_ext mathprint_jupyter        # Jupyter / IPython only

from mathprint import mpt
mpt.configure(out_format="latex")  # <- this file now renders LaTeX

y = 5
z = 10
mpt[x := y * 7 + z]
```

The setting applies to the file it appears in (in a notebook, the whole
notebook); other modules are unaffected. `mpt.configure(out_format="text")`
moves that file back to plain text. Both forms return the scope key that changed
(the file path, or `<ipython>` in a notebook).

Requires `pytexit` and `IPython`:

```powershell
python -m pip install ".[latex]" --no-compile
```

They are imported **lazily**, only when a line is actually rendered, so the
default plain-text path never imports them. Rendering needs a LaTeX-aware
frontend (Jupyter); outside IPython, `display` falls back to a plain repr.

> **Numbers.** `pytexit` 0.4.0 predates `ast.Constant` and fails on numeric
> literals on Python >= 3.8. mathprint patches in the missing visitor
> automatically — only in LaTeX mode, and only if it is absent.

> **Dotted names.** `pytexit` 0.4.0 also has no visitor for attribute access
> (`me.H.atomic_number`), so such a line used to fall back to plain text.
> mathprint patches in `visit_Attribute` too, rendering the chain as
> `me.H.atomic_{number}`.

> **Multiplication.** `pytexit` 0.4.0 renders `*` as a space and only uses the
> configured multiplier when an operand looks like a float literal, so
> `2 * (0.07 * m)` became `2 0.07\cdot m` — a different formula. mathprint makes
> every product explicit: `*` always renders as `{\cdot}` (`2{\cdot}0.07{\cdot}m`).

A complete example notebook is in
[examples/demo_latex.ipynb](examples/demo_latex.ipynb).

---

## Display precision

By default each number is printed with its full `str` value. To cap the
**displayed** digits, set `precision=n` — numbers are then shown rounded to
`n` significant digits:

```python
from mathprint import mpt
mpt.configure(precision=4)

v = 3.123123412
mpt[v + 0]
# v + 0
# 3.123 + 0
# 3.123

w = 23.00134
mpt[w * 1]
# w * 1
# 23 * 1
# 23
```

This affects **only the display**: the expression is still evaluated with full
precision, and `mpt[...]` returns the unrounded value (`r` above would still be
`6.246246824` for `mpt[r := v * 2]`).

It applies to plain numbers — `int`, `float`, `complex`, `Decimal`, `Fraction`
and numpy scalars. Symbolic values (e.g. sympy expressions), modules, functions
and classes are shown as usual. Trailing zeros are not padded (`23.00134` prints
as `23`, not `23.00`).

The setting is scoped to the file (or notebook) where `mpt.configure(precision=n)`
is called. `mpt.configure(precision=None)` restores the default.

---

## Number format

By default numbers are shown as Python prints them, so a small value such as
`1.23e-9` appears as `1.23e-09`. Set `number_format="power"` to show such a
number as a power of ten instead:

```python
from mathprint import mpt
mpt.configure(number_format="power")

a = 1.23e-9
mpt[a]
# a
# 1.23*10**-9
# 1.23*10**-9
```

Two kinds of numbers are rewritten:

- anything already in scientific notation — the exponent loses a `+` sign and
  leading zeros (`1e+20` → `1*10**20`, `1.5e-05` → `1.5*10**-5`);
- a plain decimal that is far from `1` — below `10**-4` or at/above `10**16` —
  is normalized, even if Python would print it without an exponent:
  `0.0001106` → `1.106*10**-4`, `7.5931e-05` → `7.5931*10**-5`.

The rule covers all three phases: a numeric literal in the source and in the
substitution is rewritten as well, not just the final value. Short numbers are
untouched (`2230`, `12345.678`, `0.001`, `0.00282`), and so are values that are
not plain real numbers — strings, complex numbers, symbolic objects. `bool` is
excluded as well.

This affects only the display: the expression is still evaluated and returned
with its original value.

`"exp"` is the default and changes nothing. The setting is scoped to the file (or
notebook) where it is called; `mpt.configure(number_format="exp")` switches back.

> If `precision=n` is also set, the rounded number is still normalized: `a` above
> with `precision=4` shows `1.23*10**-9` in every phase.

---

## Nested assignments

A chain of assignments in one call, `ro1 := (ro := (ro_БФСС := 2230))`, evaluates
to the innermost value, so by default phase 2 simply repeats the whole chain —
the same text as phase 1 (only loaded names would differ). To collapse it to the
single value instead, enable `multiple_assignment_reduce`:

```python
from mathprint import mpt
mpt.configure(multiple_assignment_reduce=True)

mpt[ro1 := (ro := (ro_БФСС := 2230))]
# ro1 := (ro := (ro_БФСС := 2230))   <- phase 1: exactly as written
# ro1 := 2230                        <- phase 2: collapsed
# ro1 := 2230                        <- phase 3: the value
```

With `out_order="line"` this is the difference between
`ro1 = (ro := (ro_БФСС := 2230)) = (ro := (ro_БФСС := 2230)) = 2230` (default)
and `ro1 = (ro := (ro_БФСС := 2230)) = 2230 = 2230` (enabled).

Names inside the innermost value are still substituted, in place:

```python
x = 5
mpt[a := (b := x + 1)]
# a := (b := x + 1)
# a := 5 + 1
# a := 6
```

Only a **direct chain** is collapsed — each assignment's right-hand side is
itself an assignment. A single assignment, or an assignment used inside a larger
expression (`mpt[(b := 3) + 1]`), keeps its ordinary phase 2. The default is
unchanged. `mpt.configure(multiple_assignment_reduce=False)` switches back.

---

## Repeated stages

On one line the stages are joined with `=`. Sometimes two adjacent stages are
textually identical — for example the substitution and the value after a chain
of assignments:

```python
from mathprint import mpt
mpt.configure(out_order="line")

mpt[ro1 := (ro := (ro_БФСС := 2230))]
# ro1 = (ro := (ro_БФСС := 2230)) = (ro := (ro_БФСС := 2230)) = 2230
```

Enable `reduce_equ_stages` to drop repeated adjacent stages:

```python
mpt.configure(reduce_equ_stages=True)

mpt[ro1 := (ro := (ro_БФСС := 2230))]
# ro1 = (ro := (ro_БФСС := 2230)) = 2230
```

This works independently of `multiple_assignment_reduce` (and combines with it:
both settings give the same line above). Stages that differ — the normal case —
are untouched, and a fully literal expression collapses to a single value
(`mpt[2230]` shows just `2230`).

The option affects only the one-line layout; a column always shows its three
lines, one stage per line. The default is unchanged.
`mpt.configure(reduce_equ_stages=False)` switches back.

---

## Disabling mathprint (no-op stub)

To switch mathprint off in a module **without touching any of its call sites**,
change only the import line:

```python
# from mathprint import mpt        # real macro (needs mcpyrate)
from mathprint.stub import mpt     # no-op
```

With this stub, `mpt[expr]` is an ordinary subscription:

- the expression is evaluated **once**, then its value is discarded — `mpt[…]`
  returns `None` (the `:=` form still binds, because the walrus runs while the
  subscript is evaluated);
- **nothing is printed**;
- no macro expansion, import hook, `mcpyrate`, or `mathprint_main` is involved.

> The stub's `__getitem__` body is empty (`pass`) on purpose: it compiles to the
> cheapest possible subscript, so the disabled path stays as light as possible.

`mathprint.stub` is deliberately self-contained — it imports nothing from the
rest of the project, not even type annotations — so importing it can never
activate the macro machinery. This makes it easy to keep `mpt[…]` throughout a
codebase and disable it per file (e.g. in production).

A complete example is in [examples/demo_stub.py](examples/demo_stub.py).

---

## How it works (three phases)

`mpt` renders an expression in three phases:

1. **Source.** The expression *exactly as written at the use site*, taken
   verbatim from the source file (no reformatting, no added/removed spaces or
   parentheses).
2. **Substitution.** The same expression with each local variable replaced
   *in place* by its current value (a dotted chain rooted at a name, such as
   `me.H.atomic_number`, is treated as one variable). Nothing is evaluated or
   simplified here; only names are textually substituted, and their order is
   preserved exactly.
3. **Evaluation.** The expression itself is evaluated once; its value is printed
   as the third line (with the `name := ` prefix in the assignment form, so all
   three lines carry the name) and also becomes the value of the macro, so it can
   be assigned or printed: `result = mpt[(a + z) * 2]`.

> **A source file is required.** Phase 1 prints the expression *verbatim*, so
> `mpt` reads the file it is being compiled from — or, in Jupyter, the captured
> cell text. Contexts with no source text (plain `python -c`, `exec`, the bare
> REPL) are not supported: there `mpt[...]` is not expanded at all, and a clear
> macro-expansion error is raised rather than a subtly reformatted line.

---

## Order guarantee

The substituted line is built directly from the exact source substring of the
expression. Each *loaded* name occurrence is replaced in place by a positional
`str.format` placeholder, and occurrences are collected in source order (by byte
offset in the file), then sorted by that offset. A dotted chain rooted at a name
(`me.H.atomic_number`) counts as one occurrence — its prefixes and root are not
separate slots. Placeholders are filled positionally with the values of those
very same occurrences. Because the i-th
placeholder is by construction the i-th source occurrence, the i-th value
necessarily lands in the i-th slot — regardless of the surrounding operators
(including comparisons) and regardless of what the values are (numbers, sympy
symbols, modules, functions, …). No evaluation, arithmetic, or symbolic
simplification happens in this phase, so nothing can move around.

Store-context names (e.g. a comprehension target, or the target of an assignment
`mpt[name := …]`) are not substituted, because they are being bound, not read.

---

## Pylance / Pyright

The package ships `py.typed` and `__init__.pyi`, so `mpt[...]` is not flagged as
an error and Pylance understands the macro-call syntax. The stub also describes
`mpt.configure(...)` in full (signature, allowed values and per-argument
documentation), so hovering over `mpt.configure` in VS Code shows the settings
and what each argument does.

---

## Updating the package

### Editable mode (`pip install -e .`)

No action needed — edit files in `src/` and changes take effect on the next run.

Notes:
- mcpyrate caches macro-expansion results in `__pycache__` next to the source.
  It tracks mtime of macro files and rebuilds on change, but if a stale version
  seems to be used, clear the cache and restart Python:
  ```powershell
  Remove-Item -Recurse -Force src\mathprint_main\__pycache__
  ```
- Macro code changes only take effect in a **new** Python process.

### Regular install (`pip install .`)

Source edits do **not** reach the installed copy automatically. Reinstall after
changes:

```powershell
python -m pip install --force-reinstall . --no-compile
```

Or bump `version` in `pyproject.toml` (e.g. `0.1.0` → `0.1.1`) and run
`python -m pip install . --no-compile`.

> Tip: use editable mode if you change code often — it avoids reinstalling.

### Multiple environments

The package is installed into a specific environment. With venv/conda, install and
update it with the same interpreter you run scripts with:

```powershell
D:\path\to\venv\Scripts\python -m pip install -e . --no-compile
```

---

## Development

```powershell
# Demo script (package must be installed)
python examples/demo.py

# Tests
python -m pytest
```

Tests run with `--assert=plain` (see `[tool.pytest.ini_options]` in
`pyproject.toml`), because pytest's assertion rewriting bypasses mcpyrate's
macro-expansion hook.

For a step-by-step walkthrough of one formula — from `mpt[...]` through macro
expansion and substitution to the final LaTeX (in Russian) — see
[docs/execution-path.md](docs/execution-path.md).

---

## Project structure

```
pyproject.toml              # package metadata and build config
README.md                   # this file
pyrightconfig.json          # Pyright/Pylance settings
docs/
  execution-path.md         # step-by-step execution path of one formula (RU)
src/
  mathprint/                # helper module (one-liner bootstrap) + no-op stub
    __init__.py
    stub.py                 # `from mathprint.stub import mpt` disables mathprint
    py.typed                # PEP 561 marker
  mathprint_jupyter.py      # Jupyter/IPython extension
  mathprint_main/           # macro implementation
    __init__.py
    __init__.pyi            # type stubs (for Pylance)
    py.typed                # PEP 561 marker
typings/
  mcpyrate/
    quotes.pyi              # stubs for q/u/a operators from mcpyrate.quotes
  pytexit/
    __init__.pyi            # stubs for the optional pytexit dependency
tests/
  test_mathprint.py         # script tests
  test_jupyter.py           # Jupyter/IPython tests (skipped if IPython missing)
  test_stub.py              # no-op stub tests
  test_latex.py             # LaTeX output mode tests
  test_precision.py         # display precision tests
  test_layout.py            # one-line / column layout tests
examples/
  demo.py                   # script example (`from mathprint import mpt`)
  demo_stub.py              # script example (stub, prints nothing)
  demo.ipynb                # Jupyter notebook example
  demo_latex.ipynb          # Jupyter notebook example (LaTeX output)
```

---

## Vibecode project

This is a **vibecode** project: it was built by iterating with an AI coding
assistant, driven by real usage rather than a formal spec. The upside is a
tight, practical tool that does exactly what was needed; the caveat is that it
is best treated as such — read the tests before depending on subtle behaviour in
production, and expect the occasional rough edge.