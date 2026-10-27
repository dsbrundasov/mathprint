# AGENTS.md — working instructions for AI agents

## Environment: use ONLY the `work` environment

All checks — tests, type checking, running examples, notebooks — **must** run in
the conda environment `work`. Do not use the system Python or `work_3_14_6`, even
though a few packages may also be importable from the user-site
(`C:\Users\dsbru\AppData\Roaming\Python\Python314`).

    interpreter:  C:\Users\dsbru\.conda\envs\work\python.exe

That environment has everything the project needs (`mcpyrate`, `pytexit`,
`IPython`, `nbclient`/`nbformat`/`nbconvert`, `pytest`, `pyright`) plus the
project installed in editable mode with `pip install -e .`. Use only that
interpreter — other ones (the system Python, `work_3_14_6`) may lack `pytexit`
or the editable install.

## Running the checks (from the project root)

```powershell
# clear mcpyrate's cached macro expansions, then run the tests
Get-ChildItem -Path src,tests,examples -Recurse -Directory -Filter __pycache__ |
    Remove-Item -Recurse -Force
& "C:\Users\dsbru\.conda\envs\work\python.exe" -m pytest -q

# static types
& "C:\Users\dsbru\.conda\envs\work\python.exe" -m pyright

# runnable example (needs the source tree on PYTHONPATH)
$env:PYTHONPATH = "$PWD\src"
& "C:\Users\dsbru\.conda\envs\work\python.exe" examples\demo.py

# execute the LaTeX example notebook (needs pytexit)
& "C:\Users\dsbru\.conda\envs\work\python.exe" -c "import nbformat; from nbclient import NotebookClient; NotebookClient(nbformat.read('examples/demo_latex.ipynb', as_version=4), timeout=120).execute(); print('notebook ok')"
```

`mcpyrate` caches macro expansions in `__pycache__`. **After changing the macro
(`src/mathprint_main/`), clear the `src`/`tests`/`examples` `__pycache__` and run
in a fresh process**, or you may test stale expansions.

## What the project is

`mathprint` is a **vibecode** project: a `mcpyrate` macro `mpt` that prints an
expression in three phases — the exact source, the source with each variable
replaced by its current value (in place, order preserved), and the value.
Display settings (layout, plain text vs LaTeX, display precision) are opt-in,
grouped in `mpt.configure(...)`, and scoped per file. See `README.md`
for the user-facing description and `src/mathprint_main/__init__.py` for the
implementation.

The implementation is a rigid pipeline, one module per job:

| module | contents |
| --- | --- |
| `settings.py` | `DisplaySettings` (the options; defaults = the core) and `SettingsStore` (scope → settings) |
| `source.py` | `SourceText` (exact source text) and `InPlaceSubstitution` (phase-2 template + occurrences) |
| `numbers.py` | `SignificantDigits` (`precision`) and `PowerOfTen` (`number_format="power"`) |
| `latex.py` | `LatexRenderer` — the only place that imports `pytexit`/`IPython` |
| `presentation.py` | `ExpressionReport`, `ColumnLayout`/`SingleLineLayout`, `PlainTextOutput`/`LatexOutput`, `Presenter` (runtime hooks) |
| `expansion.py` | `MacroExpander` — turns one `mpt[...]` into `Presenter` calls |

The core is "substitute, evaluate once, `str(value)`": everything else is a
strategy chosen at run time from `DisplaySettings`, so it can be switched off
(field by field, or all at once with `mpt.configure(reset=True)`).
`src/mathprint_main/__init__.pyi` is the public, typed API.

## Conventions

- Keep the import exactly `from mathprint import mpt` (a no-op stub lives in
  `src/mathprint/stub.py`).
- User-facing settings are grouped in `mpt.configure(out_order=..., out_format=...,
  precision=...)` — each affects the file (or notebook) it is called in.
- The expression must be evaluated **exactly once**. The source is required:
  there is no fallback (a clear `MacroExpansionError` is raised when it is
  missing).

## Session data

Keep session data inside the project folder, so work can continue on another
computer: OpenCode's own database is global and cannot be moved per project, so
export the transcript with `.\tools\session-save.ps1` (writes
`.opencode/sessions/<id>.json`); restore it elsewhere with
`.\tools\session-load.ps1 <file>`. See `docs/sessions.md`. Export before
handing the project over, and do not commit the JSON files unless the transfer
goes through Git.
