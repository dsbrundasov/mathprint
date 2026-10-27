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

Имена классов — по одному модулю на задачу (`src/mathprint_main/`):

| Модуль | Классы |
|---|---|
| `expansion.py` | `MacroExpander` — раскрытие `mpt[...]` |
| `source.py` | `SourceText` — точный исходник; `InPlaceSubstitution` — шаблон фазы 2 |
| `presentation.py` | `ExpressionReport`, `ColumnLayout`/`SingleLineLayout`, `PlainTextOutput`/`LatexOutput`, `Presenter` — хуки рантайма |
| `settings.py` | `DisplaySettings` — опции; `SettingsStore` — настройки на файл/ячейку |
| `numbers.py` | `SignificantDigits`, `PowerOfTen` — необязательные форматы чисел |
| `latex.py` | `LatexRenderer` — единственное место, где импортируются `pytexit`/`IPython` |

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
выполнения (не макрос):

- `configure()` берёт ключ области через
  `SettingsStore.key_for_globals(globals)` → `"<ipython>"`;
- проверяет значение и одним вызовом
  `SettingsStore.update("<ipython>", out_format="latex")` кладёт
  `DisplaySettings(out_format="latex")` в `SettingsStore.scopes`.

---

## Этап 1. Компиляция ячейки: макропреобразование

### 1.1. `_MathprintASTTransformer.capture_source(lines)`

IPython отдаёт точный текст ячейки; он сохраняется в `self.source`. Это важно,
потому что у ячейки нет файла на диске, а фаза 1 должна печатать выражение
**дословно**.

### 1.2. `_MathprintASTTransformer.visit(node)`

Перед компиляцией:

- `activate()`;
- `mathprint_main.SourceText.override = self.source` — подсовывает текст ячейки
  как «источник»;
- `mcpyrate.compiler.expand(node, filename="<ipython>", self_module=None)` —
  прогоняет AST через макро-раскрытие;
- в `finally` возвращает прежний `SourceText.override`.

### 1.3. mcpyrate находит `mpt[...]`

Видит подписку на имя `mpt` из `global_bindings` и вызывает макрос:

```python
mathprint_main.mpt(expr, expander=<объект с filename="<ipython>">)
```

### 1.4. `mpt()` → `MacroExpander.__init__`

```python
def mpt(expr, **kw):
    return MacroExpander(kw.get("expander")).expand(expr)
```

В `MacroExpander.__init__`:

- `filename = "<ipython>"`;
- `self.scope_key = SettingsStore.key_for_filename("<ipython>")` → `"<ipython>"`
  (виртуальное имя не приводится к пути);
- `SourceText.read("<ipython>")` пытается открыть файл, получает `OSError` →
  `None`;
- поэтому `self.source_text = SourceText(SourceText.override)` — `SourceText` с
  текстом ячейки.

### 1.5. `MacroExpander.expand(expr)` → `_expand_one(expr)`

Тело подписки — не кортеж, поэтому ветка `collect` не срабатывает, сразу
`_expand_one`.

В `_expand_one`:

- `expr` — это `ast.NamedExpr` (`m_ДМФ := ...`), цель — `ast.Name`, значит
  `name = "m_ДМФ"`;
- `InPlaceSubstitution(self.source_text, expr)` считает:
  - `source = self.source_text.text_of(expr)` → `ast.get_source_segment(...)`
    возвращает **ровно**:

    ```
    m_ДМФ := M_ДМФ * 2 * (0.07*m_БФСС) / M_P2O5
    ```

  - `template, occurrences = self.source_text.placeholder_template(source, expr)`.

### 1.6. `SourceText.placeholder_template(segment, node)` → `_occurrences(node)`

Обходит AST и собирает «вхождения», которые надо подставить:

- `ast.Name` c контекстом `Load`: `M_ДМФ`, `m_БФСС`, `M_P2O5`.
- `m_ДМФ` слева от `:=` имеет контекст `Store` и **не** подставляется (это
  связывание, а не чтение).
- Цепочек-атрибутов здесь нет.

Затем `placeholder_template` сортирует вхождения по байтовому смещению в
исходнике и строит `str.format`-шаблон, заменяя каждое вхождение на `{}`:

```
"m_ДМФ := {} * 2 * (0.07*{}) / {}"
occurrences = [M_ДМФ, m_БФСС, M_P2O5]
```

Литеральные `{`/`}` в тексте экранируются `_escape_braces` (здесь их нет).

### 1.7. `MacroExpander._substituted_text_call` строит AST подстановки

Для каждого имени — `_occurrence_argument`, то есть вызов `Presenter.name_text`:

```python
Presenter.name_text("<ipython>", "M_ДМФ",  M_ДМФ)
Presenter.name_text("<ipython>", "m_БФСС", m_БФСС)
Presenter.name_text("<ipython>", "M_P2O5", M_P2O5)
```

Все они становятся аргументами одного вызова `Presenter.substituted_text`.
Итоговый узел, который возвращает `_expand_one`:

```python
q[h[Presenter].show(
    u["<ipython>"],
    u["m_ДМФ"],
    u[<точный исходник>],
    a[Presenter.substituted_text(
        "<ipython>",
        "<шаблон>",        # normal
        "<шаблон>",        # reduced: цепочки вложенных := здесь нет
        Presenter.name_text("<ipython>", "M_ДМФ",  M_ДМФ),
        Presenter.name_text("<ipython>", "m_БФСС", m_БФСС),
        Presenter.name_text("<ipython>", "M_P2O5", M_P2O5),
    )],
    a[(m_ДМФ := M_ДМФ * 2 * (0.07*m_БФСС) / M_P2O5)],
)]
```

То есть в рантайме будет выполнено (эквивалент):

```python
Presenter.show(
    "<ipython>",
    "m_ДМФ",
    "m_ДМФ := M_ДМФ * 2 * (0.07*m_БФСС) / M_P2O5",
    Presenter.substituted_text(
        "<ipython>",
        "m_ДМФ := {} * 2 * (0.07*{}) / {}",
        "m_ДМФ := {} * 2 * (0.07*{}) / {}",
        Presenter.name_text("<ipython>", "M_ДМФ",  M_ДМФ),
        Presenter.name_text("<ipython>", "m_БФСС", m_БФСС),
        Presenter.name_text("<ipython>", "M_P2O5", M_P2O5),
    ),
    (m_ДМФ := M_ДМФ * 2 * (0.07*m_БФСС) / M_P2O5),
)
```

Два шаблона (`normal` и `reduced`) передаются всегда, потому что выбор между
ними — настройка `multiple_assignment_reduce`, известная только в рантайме.

### 1.8. Возврат в mcpyrate/IPython

`mcpyrate` возвращает перестроенный AST, IPython компилирует и запускает его.

---

## Этап 2. Выполнение

### 2.1. Порядок аргументов

Аргументы `Presenter.show(...)` вычисляются слева направо:

1. константы `key`, `name`, `source`;
2. `substituted` — внутри него слева направо вызываются `Presenter.name_text`
   для `M_ДМФ`, `m_БФСС`, `M_P2O5`;
3. последним — само выражение с `:=` (один раз).

### 2.2. `Presenter.name_text(key, name, value)`

Для каждого вхождения:

1. проверка `isinstance(value, cls.OPAQUE_TYPES) or callable(value)`:
   - модули, функции, методы, классы и прочие вызываемые объекты оставляют своё
     имя;
2. иначе `Presenter.value_text(key, value)`:
   - `settings = SettingsStore.settings_for(key)`; `precision` здесь `None`;
   - `number_format` — `"exp"`, поэтому число не переписывается;
   - возвращает `str(value)`.

Получаем:

```
Presenter.name_text("<ipython>", "M_ДМФ",  126.0)     -> "126.0"
Presenter.name_text("<ipython>", "m_БФСС", 0.0009458) -> "0.0009458"
Presenter.name_text("<ipython>", "M_P2O5", 141.9)     -> "141.9"
```

### 2.3. `Presenter.substituted_text(key, normal, reduced, *values)`

- `settings = SettingsStore.settings_for(key)`;
- `multiple_assignment_reduce` — `False`, значит берётся `normal`;
- `number_format` — не `"power"`, поэтому просто `template.format(*values)`.

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

### 2.5. `Presenter.show(key, name, source, substituted, value)`

1. `settings = SettingsStore.settings_for(key)` — здесь `out_format="latex"`.
2. `number_format` — `"exp"`, поэтому исходник не переписывается.
3. Собирается `ExpressionReport(name, source_text, substituted_text, value_text)`,
   где `value_text = Presenter.value_text(key, value)` →
   `"0.00011757513742071883"`.
4. `layout = ReportLayout.for_settings(settings)` → `ColumnLayout` (колонка по
   умолчанию, `out_order` не задавался).
5. `output = LineOutput.for_format(settings.out_format)` → `LatexOutput`.
6. `layout.lines(report, for_latex=True, drop_repeated=False)` даёт три строки:
   1. исходник;
   2. подстановка;
   3. `f"{name} := {value_text}"` → `m_ДМФ := 0.00011757513742071883`.
7. Каждая строка уходит в `output.show(line)`.

### 2.6. `LatexOutput.show(text)`

`out_format="latex"`, поэтому `LineOutput.for_format` вернул `LatexOutput`, и
строка уходит в `LatexRenderer.display(text)`. В обычном текстовом режиме здесь
был бы `PlainTextOutput.show` → `print(text)`.

`additional_out` — `None`, поэтому второй проход (сырой вывод) не выполняется.

---

## Этап 3. Рендер одной строки в LaTeX: `LatexRenderer.display`

Для каждой из трёх строк:

### 3.1. Ленивые импорты

`IPython.display.Latex`, `display` и `pytexit.py2tex` импортируются только здесь
(в обычном текстовом режиме `pytexit` вообще не трогается).

### 3.2. `LatexRenderer.to_source(text)`

`LatexRenderer.patch_pytexit()` достраивает `LatexVisitor` из `pytexit` (один раз,
дальше методы уже на месте):

- `visit_Constant` — числовые литералы на Python ≥ 3.8 (иначе `generic_visit`
  падает);
- `visit_Attribute` — точечные обращения (`me.H.atomic_number`);
- `visit_UnaryOp` — отрицательные числа (`-2.5`, `10**-9`);
- `visit_Mult` — всегда возвращает `self.tex_multiplier`, т.е. `{\cdot}`, чтобы
  знаки умножения никогда не терялись.

### 3.3. `LatexRenderer.to_pytex_input(text)`

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

`IPython.display.display` показывает формулу в ячейке. Если строка не
конвертируется (например, содержит `and`), `LatexRenderer.display` печатает её
как есть — одно выражение не может сломать выполнение.

---

## Этап 4. Возврат значения

`Presenter.show` возвращает `value` (то самое `0.00011757513742071883`). Поэтому
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
        MacroExpander.__init__
          SettingsStore.key_for_filename
          SourceText.read / SourceText.override
        MacroExpander.expand -> MacroExpander._expand_one
          InPlaceSubstitution
            SourceText.text_of
            SourceText.placeholder_template -> SourceText._occurrences
          MacroExpander._substituted_text_call
            MacroExpander._occurrence_argument
          q[Presenter.show(...)]

выполнение
  Presenter.name_text (для каждого вхождения)
    Presenter.value_text
  Presenter.substituted_text
    str.format
  вычисление выражения (один раз)
  Presenter.show
    Presenter.value_text
    ReportLayout.for_settings -> ColumnLayout.lines
    LineOutput.for_format -> LatexOutput.show
      LatexRenderer.display
        LatexRenderer.to_source
          LatexRenderer.patch_pytexit
          LatexRenderer.to_pytex_input
          py2tex
        display(Latex(...))
```

Ключевая идея: **фаза 1 и фаза 2 — это строки, собранные на этапе компиляции**
(исходник дословно и `str.format`-шаблон с рантайм-значениями), а **фаза 3 —
однократное вычисление того же выражения**. Всё, что выше подстановки и
однократного вычисления (layout, LaTeX, точность, формат чисел, дополнительный
вывод), — это стратегии, которые `Presenter` выбирает в рантайме по
`DisplaySettings` своей области. Поэтому любую из них можно выключить, не трогая
ядро, вплоть до `mpt.configure(reset=True)`.
