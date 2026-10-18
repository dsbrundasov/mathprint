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

---

## Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Jupyter / IPython](#jupyter--ipython)
- [Disabling mathprint (no-op stub)](#disabling-mathprint-no-op-stub)
- [How it works (three phases)](#how-it-works-three-phases)
- [Order guarantee](#order-guarantee)
- [Pylance / Pyright](#pylance--pyright)
- [Updating the package](#updating-the-package)
- [Development](#development)
- [Project structure](#project-structure)

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
# 45

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
- All comparison operators (`==`, `!=`, `<`, `<=`, `>`, `>=`, `is`, `in`, …) and
  chained comparisons (`0 < y < z`).
- Only **names** are substituted; functions and attributes are not evaluated.
  Assignment targets (e.g. the name left of `:=`) are not substituted.
- Module, function and class names are **not** expanded: `math.floor(y)` stays
  `math.floor(5)` (not `<module 'math' …>.floor(5)`), `f(y)` stays `f(5)` (not
  `<function f at 0x…>(5)`), and `int(y)` stays `int(5)` (not `<class 'int'>(5)`).
- Works under both `python` and `macropython`.

---

## Requirements

- Python >= 3.9
- `mcpyrate` (installed automatically as a dependency)
- Optional: `sympy` for symbolic expressions

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

### Option A — one line (recommended)

```python
from mathprint import mpt
```

`mathprint` is a helper module shipped with the package. After this import,
`mpt[...]` is available immediately:

```python
from mathprint import mpt

y = 5
z = 10
mpt[x := y * 7 + z]
```

This works under both `python` and `macropython` — no bootstrap block needed.

The macro implementation lives in the separate `mathprint_main` package;
`mathprint` registers `mpt` as a global mcpyrate macro at compile time and,
when needed, re-compiles and re-runs the script with macro expansion enabled.

### Option B — explicit mcpyrate form

```python
from mathprint_main import macros, mpt
```

The macro-import **must** start with the `macros` marker name — that is
mcpyrate's requirement. `macros` is a marker; you effectively get only `mpt`.
Importing `from mathprint_main import mpt` (without `macros`) will **not** be
recognized as a macro-import and `mpt[...]` will fail at runtime with
`'function' object is not subscriptable`. That is exactly what Option A avoids.

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
   **first line** of the script (Option A). The boot module activates the hook and
   re-runs the file with macros expanded. Under `macropython` (or on the re-run)
   it does nothing, so the import is always safe.

   Place this import before any other top-level side effects, because the first
   (plain) run stops at the import and re-runs the file.

Option A works under both `python` and `macropython`.

### Pylance / Pyright

The package ships `py.typed` and `__init__.pyi`, so `mpt[...]` is not flagged as
an error and Pylance understands the macro-call syntax — both with
`from mathprint import mpt` and `from mathprint_main import macros, mpt`.

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
# 45
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
   *in place* by its current value. Nothing is evaluated or simplified here; only
   names are textually substituted, and their order is preserved exactly.
3. **Evaluation.** The expression itself is evaluated once; its value is printed
   as the third line and also becomes the value of the macro, so it can be
   assigned or printed: `result = mpt[(a + z) * 2]`.

---

## Order guarantee

The substituted line is built directly from the exact source substring of the
expression. Each *loaded* name occurrence is replaced in place by a positional
`str.format` placeholder, and occurrences are collected in source order (by byte
offset in the file), then sorted by that offset. Placeholders are filled
positionally with the values of those very same occurrences. Because the i-th
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
an error and Pylance understands the macro-call syntax — both with
`from mathprint import mpt` and `from mathprint_main import macros, mpt`.

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

---

## Project structure

```
pyproject.toml              # package metadata and build config
README.md                   # this file
pyrightconfig.json          # Pyright/Pylance settings
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
tests/
  test_mathprint.py         # script tests
  test_jupyter.py           # Jupyter/IPython tests (skipped if IPython missing)
  test_stub.py              # no-op stub tests
examples/
  demo.py                   # script example (`from mathprint import mpt`)
  demo_stub.py              # script example (stub, prints nothing)
  demo.ipynb                # Jupyter notebook example
```

---

## Русский

### Возможности

Макрос `mpt` для [mcpyrate](https://github.com/Technologicat/mcpyrate), который
печатает математическое выражение **тремя строками**:

1. **Символьно** — в точности как записано в коде, с именами переменных.
2. **С подставленными значениями** — каждая переменная заменяется своим текущим
   значением на месте.
3. **Вычисленное значение** — выражение, посчитанное ровно один раз.

Значения берутся из той области видимости, где стоит вызов. Выражение считается
только **один раз**: напечатанное значение и возвращаемое значение макроса —
результат одного и того же вычисления.

```python
from mathprint import mpt

import sympy as sp

a = sp.symbols("a")   # символьная переменная
y = 5
z = 10

mpt[x := y * 7 + z]
# x := y * 7 + z
# x := 5 * 7 + 10
# 45

mpt[(a + z) * 2]
# (a + z) * 2
# (a + 10) * 2
# 2*a + 20

mpt[y > (a + z) * 2]
# y > (a + z) * 2
# 5 > (a + 10) * 2
# 2*a + 20 < 5
```

- Печатает **три строки**: исходник, подстановку и вычисленное значение.
  Выражение вычисляется **один раз**.
- Все операторы сравнения (`==`, `!=`, `<`, `<=`, `>`, `>=`, `is`, `in`, …)
  и цепочки (`0 < y < z`).
- Подставляются только **имена**; функции и атрибуты не вычисляются. Цели
  присваивания (имя слева от `:=`) не подставляются.
- Имена модулей, функций и классов **не** расширяются: `math.floor(y)` остаётся
  `math.floor(5)` (а не `<module 'math' …>.floor(5)`), `f(y)` — `f(5)` (а не
  `<function f at 0x…>(5)`), `int(y)` — `int(5)` (а не `<class 'int'>(5)`).
- Работает и под `python`, и под `macropython`.

### Требования

- Python >= 3.9
- `mcpyrate` (устанавливается автоматически)
- Опционально `sympy` для символьных выражений

### Установка

Откройте терминал в корне проекта (`MathPrint`) и выполните команду для того
интерпретатора/окружения, из которого будете запускать скрипты.

**Editable (рекомендуется для разработки):**
```powershell
python -m pip install -e . --no-compile
```

**Обычная (копией в site-packages):**
```powershell
python -m pip install . --no-compile
```

**С инструментами разработки (sympy, pytest):**
```powershell
python -m pip install -e ".[dev]" --no-compile
```

**Удаление:**
```powershell
python -m pip uninstall mathprint
```

> Всегда используйте `--no-compile` — mcpyrate ломает `compileall` в Python 3.14.

**Если что-то сломалось:**
```powershell
python -m pip uninstall mathprint -y
python -m pip cache purge
python -m pip install -e . --no-compile
python -c "import mathprint; print(mathprint.__file__)"
# Ожидается: ...\src\mathprint\__init__.py
```

> Если `from mathprint import mpt` выдаёт `ImportError: cannot import name 'macros'` —
> в `site-packages` остался старый пакет `mathprint/` (из до переименования).
> Закройте все процессы Python/Jupyter/VS Code и удалите каталог вручную.

### Использование

**Вариант A — одна строка (рекомендуется):**
```python
from mathprint import mpt
```

После этого `mpt[...]` сразу доступен:
```python
from mathprint import mpt

y = 5
z = 10
mpt[x := y * 7 + z]
```

Работает и под `python`, и под `macropython`.

**Вариант B — явная форма mcpyrate:**
```python
from mathprint_main import macros, mpt
```

Макро-импорт **обязан** начинаться со служебного имени `macros` — так требует
mcpyrate. Импортировать `from mathprint_main import mpt` без `macros` нельзя.

**Запуск скрипта с макросом:**
1. Через `macropython`: `macropython myscript.py`
2. Обычным `python myscript.py` — поставьте `from mathprint import mpt` первой строкой.

Важно: этот импорт должен идти **до** любого другого кода, потому что при обычном
запуске файл исполняется дважды.

### Jupyter / IPython

Ноутбуки по умолчанию не используют хук mcpyrate. Для Jupyter есть расширение:

```python
%load_ext mathprint_jupyter
```

После этого используйте макрос так же, как в скриптах:

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
# 45
x  # → 45

mt.floor(z) + z  # → mt.floor(10) + 10
```

Отключить расширение: `%unload_ext mathprint_jupyter`

Пример ноутбука: [examples/demo.ipynb](examples/demo.ipynb).

### Отключение mathprint (заглушка)

Чтобы отключить mathprint в модуле, **не трогая сами вызовы**, измените только
строку импорта:

```python
# from mathprint import mpt        # настоящий макрос (нужен mcpyrate)
from mathprint.stub import mpt     # заглушка (no-op)
```

С заглушкой `mpt[expr]` — обычная подписка:

- выражение вычисляется **один раз**, затем значение отбрасывается — `mpt[…]`
  возвращает `None` (форма `:=` по-прежнему связывает имя, т.к. walrus
  вычисляется при вычислении подписки);
- **ничего не печатается**;
- не задействуются макрораскрытие, хук импорта, `mcpyrate` и `mathprint_main`.

> Тело `__getitem__` заглушки пустое (`pass`) намеренно: так компилируется самый
> дешёвый вариант подписки, и отключённый путь остаётся максимально лёгким.

`mathprint.stub` намеренно самодостаточен — он ничего не импортирует из проекта,
даже аннотации типов, — поэтому его импорт не может активировать макро-механизм.
Удобно держать `mpt[…]` во всём коде и отключать его по файлам (например, в
проде).

> **Почему `mpt[…]`, а не `mpt(…)`?** `mpt` — макрос mcpyrate. Python разбирает
> `mpt[expr]` как подписку и передаёт макросу *невычисленное* выражение (AST) на
> этапе компиляции; вызов `mpt(expr)` вычислил бы выражение заранее и передал
> только значение. Подписка — соглашение макросов, и именно она позволяет одной
> и той же строке `mpt[expr]` работать с заглушкой.

Пример: [examples/demo_stub.py](examples/demo_stub.py).

### Как это работает (три фазы)

1. **Исходник.** Выражение *в точности так, как записано в коде*.
2. **Подстановка.** Каждая переменная заменяется своим значением *на месте*.
   Ничего не вычисляется; порядок сохраняется.
3. **Вычисление.** Выражение вычисляется один раз; его значение печатается
   третьей строкой и становится значением макроса: `result = mpt[(a + z) * 2]`.

### Гарантия порядка

Подстановочная строка строится прямо из точного исходного текста. Каждое
вхождение имени заменяется позиционным плейсхолдером (по байтовому смещению в
файле), затем плейсхолдеры заполняются значениями тех же переменных в том же
порядке. i-й плейсхолдер по построению — это i-е вхождение в исходнике, поэтому
i-е значение всегда попадает на i-е место — независимо от операторов (включая
сравнения) и от того, что за значения (числа, sympy-символы, модули, функции, …).

### Pylance / Pyright

Пакет поставляет `py.typed` и `__init__.pyi`, поэтому `mpt[...]` не
подсвечивается ошибкой.

### Обновление пакета

**Editable (`pip install -e .`):** правьте файлы в `src/` — изменения подхватятся
при следующем запуске. mcpyrate кэширует результат в `__pycache__`; при
подозрении на устаревший кэш удалите его и перезапустите Python.

**Обычная (`pip install .`):** изменения в исходниках не попадут автоматически.
Переустановите: `python -m pip install --force-reinstall . --no-compile`

### Разработка

```powershell
python examples/demo.py   # демо-скрипт
python -m pytest          # тесты (--assert=plain в pyproject.toml)
```

### Структура проекта

```
pyproject.toml              # метаданные пакета
README.md                   # этот файл
pyrightconfig.json          # настройки Pyright/Pylance
src/
  mathprint/                # модуль-помощник (one-liner bootstrap) + заглушка
    __init__.py
    stub.py                 # `from mathprint.stub import mpt` отключает mathprint
    py.typed                # маркер PEP 561
  mathprint_jupyter.py      # расширение для Jupyter/IPython
  mathprint_main/           # реализация макроса mpt
    __init__.py
    __init__.pyi            # типовые заглушки
    py.typed                # маркер PEP 561
typings/
  mcpyrate/
    quotes.pyi              # заглушки для q/u/a из mcpyrate.quotes
tests/
  test_mathprint.py         # тесты скриптов
  test_jupyter.py           # тесты Jupyter (пропускаются без IPython)
  test_stub.py              # тесты заглушки
examples/
  demo.py                   # пример скрипта
  demo_stub.py              # пример скрипта с заглушкой (ничего не печатает)
  demo.ipynb                # пример ноутбука
```
"D:\\SyncStore\\Work\\Python\\MathPrint\\README.md"