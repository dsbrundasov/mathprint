# Путь выполнения кода при получении формулы

Разбор на примере ячейки Jupyter с формулой:

```python
%load_ext mathprint_jupyter
from mathprint import mpt
mpt.configure(out_format="latex")

M_ДМФ, m_БФСС, M_P2O5 = 126.0, 0.0009458, 141.9
mpt[m_ДМФ := M_ДМФ * 2 * (0.07 * m_БФСС) / M_P2O5]
```

Путь делится на четыре этапа: подготовка, компиляция ячейки
(макропреобразование), выполнение и LaTeX.

---

## Этап 0. Подготовка: `%load_ext`

`%load_ext mathprint_jupyter` вызывает `load_ipython_extension(ipython)`
(`src/mathprint_jupyter.py`):

1. `mcpyrate.activate.activate()` — включает перехват компиляции.
2. `global_bindings["mpt"] = mathprint_main.mpt` — регистрирует макрос в
   mcpyrate, чтобы при компиляции любой ячейки имя `mpt` распознавалось как
   макрос.
3. Создаёт `_MathprintASTTransformer` и добавляет его в:
   - `ipython.ast_transformers` — `visit` будет вызываться на AST каждой ячейки;
   - `ipython.input_transformers_post` — `capture_source` будет получать точный
     текст ячейки.

Дальше строка `from mathprint import mpt` в ячейке даёт обычный объект-функцию
`mpt` (через `mathprint.__getattr__` → `_load_macro`), но **разворачивает**
вызовы именно mcpyrate по записи в `global_bindings`. В Jupyter `_bootstrap` из
`mathprint/__init__.py` сразу выходит, т.к. в globals есть `get_ipython`.

А `mpt.configure(out_format="latex")` — это уже обычный вызов во время
выполнения (не макрос): `_configure()` → `Printer.key_of_globals(...)` возвращает
`"<ipython>"` → `Printer.set_latex("<ipython>", True)` добавляет ключ в
`Printer.latex_scopes`.

---

## Этап 1. Компиляция ячейки: макропреобразование

### 1.1. `_MathprintASTTransformer.capture_source(lines)`

IPython отдаёт точный текст ячейки; он сохраняется в `self.source`. Это важно,
потому что у ячейки нет файла на диске, а фаза 1 должна печатать выражение
**дословно**.

### 1.2. `_MathprintASTTransformer.visit(node)`

Перед компиляцией:

- `activate()`;
- `mathprint_main.Source.override = self.source` — подсовывает текст ячейки как
  «источник»;
- `mcpyrate.compiler.expand(node, filename="<ipython>", self_module=None)` —
  прогоняет AST через макро-раскрытие;
- в `finally` возвращает прежний `Source.override`.

### 1.3. mcpyrate находит `mpt[...]`

Видит подписку на имя `mpt` из `global_bindings` и вызывает макрос:

```python
mathprint_main.mpt(expr, expander=<объект с filename="<ipython>">)
```

### 1.4. `mpt()` → `Expander.__init__`

```python
def mpt(expr, **kw):
    return Expander(kw.get("expander")).expand(expr)
```

В `Expander.__init__`:

- `filename = "<ipython>"`;
- `self.key = Printer.key_of("<ipython>")` → `"<ipython>"` (виртуальное имя не
  приводится к пути);
- `Source.read("<ipython>")` пытается открыть файл, получает `OSError` → `None`;
- поэтому `self.source = Source(Source.override)` — `Source` с текстом ячейки.

### 1.5. `Expander.expand(expr)` → `_item(expr)`

Тело подписки — не кортеж, поэтому не срабатывает ветка `collect`, сразу `_item`.

В `_item`:

- `expr` — это `ast.NamedExpr` (`m_ДМФ := ...`), цель — `ast.Name`, значит
  `name = "m_ДМФ"`.
- `source = self.source.segment(expr)` → `ast.get_source_segment(...)` возвращает
  **ровно**:

  ```
  m_ДМФ := M_ДМФ * 2 * (0.07*m_БФСС) / M_P2O5
  ```

### 1.6. `Source.template(source, expr)` → `Source._occurrences(expr)`

Обходит AST и собирает «вхождения», которые надо подставить:

- `ast.Name` c контекстом `Load`: `M_ДМФ`, `m_БФСС`, `M_P2O5`.
- `m_ДМФ` слева от `:=` имеет контекст `Store` и **не** подставляется (это
  связывание, а не чтение).
- Цепочек-атрибутов здесь нет.

Затем `template` сортирует вхождения по байтовому смещению в исходнике и строит
`str.format`-шаблон, заменяя каждое вхождение на `{}`:

```
"m_ДМФ := {} * 2 * (0.07*{}) / {}"
names = [M_ДМФ, m_БФСС, M_P2O5]
```

Литеральные `{`/`}` в тексте экранируются `_escape_braces` (здесь их нет).

### 1.7. `Expander._item` строит AST подстановки

Для каждого имени — `Expander._rendered_arg`:

```python
Printer.render("<ipython>", "M_ДМФ",  M_ДМФ)
Printer.render("<ipython>", "m_БФСС", m_БФСС)
Printer.render("<ipython>", "M_P2O5", M_P2O5)
```

и оборачивает в вызов `.format(...)`. Итоговый узел:

```python
q[h[Printer].show(
    u["<ipython>"],
    u["m_ДМФ"],
    u[<точный исходник>],
    a[<строка-шаблон>.format(
        Printer.render("<ipython>", "M_ДМФ",  M_ДМФ),
        Printer.render("<ipython>", "m_БФСС", m_БФСС),
        Printer.render("<ipython>", "M_P2O5", M_P2O5),
    )],
    a[(m_ДМФ := M_ДМФ * 2 * (0.07*m_БФСС) / M_P2O5)],
)]
```

То есть в рантайме будет выполнено (эквивалент):

```python
Printer.show(
    "<ipython>",
    "m_ДМФ",
    "m_ДМФ := M_ДМФ * 2 * (0.07*m_БФСС) / M_P2O5",
    "m_ДМФ := {} * 2 * (0.07*{}) / {}".format(
        Printer.render("<ipython>", "M_ДМФ",  M_ДМФ),
        Printer.render("<ipython>", "m_БФСС", m_БФСС),
        Printer.render("<ipython>", "M_P2O5", M_P2O5),
    ),
    (m_ДМФ := M_ДМФ * 2 * (0.07*m_БФСС) / M_P2O5),
)
```

### 1.8. Возврат в mcpyrate/IPython

`mcpyrate` возвращает перестроенный AST, IPython компилирует и запускает его.

---

## Этап 2. Выполнение

### 2.1. Порядок аргументов

Аргументы `Printer.show(...)` вычисляются слева направо:

1. константы `key`, `name`, `source`;
2. `substituted` — внутри него слева направо вызываются `Printer.render` для
   `M_ДМФ`, `m_БФСС`, `M_P2O5`;
3. последним — само выражение с `:=` (один раз).

### 2.2. `Printer.render(key, name, value)`

Для каждого вхождения:

1. проверка `isinstance(value, OPAQUE_TYPES) or callable(value)`:
   - модули, функции, методы, классы и прочие вызываемые объекты оставляют своё
     имя;
2. иначе `Printer.text(key, value)`:
   - `digits = cls.precision_of(key)` — здесь `None` (`precision` не
     задавался);
   - возвращает `str(value)`.

Получаем:

```
Printer.render("<ipython>", "M_ДМФ",  126.0)     -> "126.0"
Printer.render("<ipython>", "m_БФСС", 0.0009458) -> "0.0009458"
Printer.render("<ipython>", "M_P2O5", 141.9)     -> "141.9"
```

### 2.3. `str.format`

Шаблон заполняется позиционно, в порядке исходника:

```
"m_ДМФ := 126.0 * 2 * (0.07*0.0009458) / 141.9"
```

Порядок подстановки гарантирован тем, что i-й `{}` — это i-е вхождение по
байтовому смещению, а i-й аргумент — значение именно этого вхождения.

### 2.4. Вычисление выражения

Вычисляется `m_ДМФ := M_ДМФ * 2 * (0.07*m_БФСС) / M_P2O5`:

- walrus связывает `m_ДМФ` в области ячейки;
- значение — `0.00011757513742071883`.

Выражение вычисляется **один раз**.

### 2.5. `Printer.show(key, name, source, substituted, value)`

- `shown = Printer.text(key, value)` → `"0.00011757513742071883"`;
- `line_on(key)` → `False` (колонка по умолчанию, `out_order` не задавался);
- три раза вызывает `Printer.emit(key, text)`:
  1. исходник;
  2. подстановка;
  3. `f"{name} := {shown}"` → `m_ДМФ := 0.00011757513742071883`.

### 2.6. `Printer.emit`

- `latex_on(key)` → `True`, т.к. ранее `mpt.configure(out_format="latex")`
  добавил `"<ipython>"` в `Printer.latex_scopes`;
- поэтому вместо `print(text)` вызывается `Latex.show(text)`.

---

## Этап 3. Рендер одной строки в LaTeX: `Latex.show`

Для каждой из трёх строк:

### 3.1. Ленивые импорты

`IPython.display.Latex`, `display` и `pytexit.py2tex` импортируются только здесь
(в обычном текстовом режиме `pytexit` вообще не трогается).

### 3.2. `Latex._patch_pytexit()`

Достраивает `LatexVisitor` из `pytexit` (один раз, дальше методы уже на месте):

- `visit_Constant` — числовые литералы на Python ≥ 3.8 (иначе `generic_visit`
  падает);
- `visit_Attribute` — точечные обращения (`me.H.atomic_number`);
- `visit_Mult` — всегда возвращает `self.tex_multiplier`, т.е. `{\cdot}`, чтобы
  знаки умножения никогда не терялись.

### 3.3. `Latex._to_input(text)`

Заменяет `:=` на `==`, потому что `py2tex` ожидает сравнение, а рендерит его как
`=`:

```
"m_ДМФ := 126.0 * 2 * (0.07*0.0009458) / 141.9"
→ "m_ДМФ == 126.0 * 2 * (0.07*0.0009458) / 141.9"
```

### 3.4. `py2tex(...)`

С параметрами:

```python
py2tex(..., print_latex=False, print_formula=False,
       tex_multiplier=r"{\cdot}",
       simplify_output=False, simplify_multipliers=False)
```

Внутри:

1. `preprocessing` — нормализация текста;
2. `ast.parse`;
3. обход `LatexVisitor`:
   - `visit_Name` → индексы через `_`: `m_ДМФ` → `m_{ДМФ}`, `M_P2O5` →
     `M_{P2O5}`;
   - `visit_Constant` → числа (`126.0` → `126`, `141.9` → `141.9`);
   - `visit_BinOp` + `Div` → `\frac{...}{...}`;
   - `visit_BinOp` + `Mult` → `{\cdot}` (патч);
   - `visit_Compare` для `==` → `=`;
4. результат оборачивается в `$$...$$`.

Например для строки подстановки:

```latex
$$m_{ДМФ}=\frac{126{\cdot}2{\cdot}0.07{\cdot}0.0009458}{141.9}$$
```

### 3.5. `display(Latex(tex))`

`IPython.display.display` показывает формулу в ячейке.

---

## Этап 4. Возврат значения

`Printer.show` возвращает `value` (то самое `0.00011757513742071883`). Поэтому
`mpt[...]` — это выражение, и его можно присвоить:

```python
res = mpt[m_ДМФ := ...]   # res == 0.0001175...
```

Побочный эффект — `m_ДМФ` уже связан walrus'ом в области ячейки.

---

## Короткая последовательность вызовов

```
%load_ext
  load_ipython_extension
    activate()
    global_bindings["mpt"] = mathprint_main.mpt
    ast_transformers += _MathprintASTTransformer
    input_transformers_post += capture_source

компиляция ячейки
  capture_source
  _MathprintASTTransformer.visit
    mcpyrate.compiler.expand
      mathprint_main.mpt
        Expander.__init__
          Printer.key_of
          Source.read / Source.override
        Expander.expand -> Expander._item
          Source.segment
          Source.template -> Source._occurrences
          Expander._rendered_arg
          q[Printer.show(...)]

выполнение
  Printer.render (для каждого вхождения)
    Printer.text
  str.format
  вычисление выражения (один раз)
  Printer.show
    Printer.text
    Printer.emit x3
      Latex.show
        Latex._patch_pytexit
        Latex._to_input
        py2tex
        display(Latex(...))
```

Ключевая идея: **фаза 1 и фаза 2 — это строки, собранные на этапе компиляции**
(исходник дословно и `str.format`-шаблон с рантайм-значениями), а **фаза 3 —
однократное вычисление того же выражения**. LaTeX-слой получает уже готовые
строки и только переводит их в разметку, ничего не вычисляя и не переставляя.
