# Схема выполнения макроса `mpt`

Короткая визуальная схема: что происходит **один раз при компиляции** и что —
**при каждом выполнении**. Подробный разбор на конкретной ячейке Jupyter — в
[execution-path.md](execution-path.md).

Ключевое разделение:

```
компиляция (mcpyrate) ──────────►│ выполнение (обычный Python) ──────────►
mpt[expr]  →  готовый AST        name_text × N → substituted_text → expr → show
```

---

## 1. Компиляция: `mpt[...]` превращается в вызовы `Presenter`

```
ИСХОДНЫЙ КОД                     mpt[x := y * 7 + z]
                                       │
                                       │  mcpyrate видит mpt[...]
                                       ▼
mpt(expr, expander)  ──────────► MacroExpander.__init__          expansion.py
  __init__.py                      ├─ scope_key   ← SettingsStore.key_for_filename(...)
                                   └─ source_text ← SourceText(файл или текст ячейки)
                                       │
                                       ▼
                                MacroExpander.expand(expr)
                                   ├─ ast.Tuple? → _expand_one для каждого
                                   │                + MacroExpander.collect(...)
                                   └─ иначе      → _expand_one(expr)
                                       │
                                       ▼
                                InPlaceSubstitution(source_text, expr)
                                   ├─ source    = text_of(expr)            ← фаза 1
                                   └─ template, occurrences = placeholder_template(...)
                                                                           ← фаза 2
                                       │
                                       ▼
                                q[h[Presenter].show(key, name, source,
                                     a[Presenter.substituted_text(
                                           key, normal, reduced, *name_text(...)
                                       )],
                                     a[expr])]
```

На этом этапе **ничего не вычисляется**: в AST вшиты только строки (исходник и
шаблон `str.format`) и ссылки на значения-вхождения.

---

## 2. Выполнение: аргументы `Presenter.show` вычисляются слева направо

Сначала вычисляются аргументы (именно в этом порядке — поэтому подстановка
видит **старые** значения, а выражение вычисляется один раз):

```
Presenter.show(                                   ← 5. вызов после аргументов
    key, name, source,                            ← 1. константы из раскрытия
    Presenter.substituted_text(                   ← 3. фаза 2
        key, normal, reduced,
        Presenter.name_text(key, "y", y),         ← 2a. по вызову на вхождение
        Presenter.name_text(key, "z", z),         ← 2b
    ),
    (x := y * 7 + z),                             ← 4. фаза 3, ровно один раз
)
```

Внутри хуков:

```
Presenter.name_text(key, имя, значение)
     └─ значение модуль/функция/класс/callable? → оставить имя
        иначе → Presenter.value_text(key, значение)

Presenter.value_text(key, значение)
     ├─ text = str(значение)
     ├─ precision?              → SignificantDigits.format(...)
     └─ number_format=="power"? → PowerOfTen.rewrite(text)

Presenter.substituted_text(key, normal, reduced, *значения)
     ├─ template = multiple_assignment_reduce ? reduced : normal
     ├─ number_format=="power"? → PowerOfTen.fill_template(template, значения)
     └─ иначе                   → template.format(*значения)

Presenter.show(key, name, source, substituted, value)
     ├─ value_text(key, value) → ExpressionReport(имя, фаза 1, фаза 2, фаза 3)
     ├─ ReportLayout.for_settings  → ColumnLayout | SingleLineLayout
     ├─ LineOutput.for_format      → PlainTextOutput | LatexOutput
     ├─ for line in layout.lines(report, ...): output.show(line)
     │      └─ print | LatexRenderer.display
     ├─ additional_out? → show_raw(...) для тех же строк, без рендера
     └─ return value
```

---

## 3. Что фиксируется на каком этапе

| Когда | Что | Где |
| --- | --- | --- |
| компиляция | ключ области, имя присваивания, точный исходник (фаза 1), шаблон и список вхождений (фаза 2) | `expansion.py`, `source.py` |
| выполнение | текст значений, выбор `normal`/`reduced`, формат чисел, раскладка, способ вывода, точность, дополнительный вывод | `presentation.py`, `numbers.py`, `latex.py` |

Поэтому `mpt.configure(...)`, вызванный **после** раскрытия макроса, всё равно
влияет на вывод: раскрытый код спрашивает настройки в рантайме.

---

## 4. Стратегии: одна настройка — один класс

| `mpt.configure(...)` | Включённое значение | Кто выполняет |
| --- | --- | --- |
| `out_order` | `"line"` / `"column"` | `SingleLineLayout` / `ColumnLayout` |
| `out_format` | `"latex"` / `"text"` | `LatexOutput` / `PlainTextOutput` |
| `precision` | число значащих цифр | `SignificantDigits` |
| `number_format` | `"power"` | `PowerOfTen` |
| `multiple_assignment_reduce` | `True` | `Presenter.substituted_text` (шаблон `reduced`) |
| `reduce_equ_stages` | `True` | `drop_adjacent_repeats` |
| `additional_out` | `"latex"` / `"text"` | `Presenter.show_raw` |

---

## 5. Ядро и надстройки

```
ядро =  фаза 1: точный исходник
      + фаза 2: подстановка имён на месте, порядок сохранён
      + фаза 3: одно вычисление выражения + str(value)
```

Всё, что выше, — стратегии, выбранные в рантайме из `DisplaySettings`.
`mpt.configure(reset=True)` убирает их все и возвращает ровно ядро.

---

## 6. Пример раскрытия

Исходник:

```python
mpt[x := y * 7 + z]
```

Эквивалент того, что выполняется (пути и шаблоны сокращены):

```python
Presenter.show(
    "<scope>", "x", "x := y * 7 + z",
    Presenter.substituted_text(
        "<scope>",
        "x := {} * 7 + {}",        # normal
        "x := {} * 7 + {}",        # reduced (цепочек := нет)
        Presenter.name_text("<scope>", "y", y),
        Presenter.name_text("<scope>", "z", z),
    ),
    (x := y * 7 + z),
)
```

`x` слева от `:=` имеет контекст `Store`, поэтому **не** подставляется: это
связывание, а не чтение.
