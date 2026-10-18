# AGENTS.md — working instructions for AI agents

## Environment: use ONLY the `work` environment

All checks — tests, type checking, running examples, notebooks — **must** run in
the conda environment `work`. Do not use any other interpreter (not the system
Python, not `C:\Python314`, not the `Roaming\Python` site-packages).

    interpreter:  C:\ProgramData\miniforge3\envs\work\python.exe

That environment has everything the project needs (`mcpyrate`, `pytexit`,
`IPython`, `nbclient`/`nbformat`/`nbconvert`) plus a single-file checkout
installed with `pip install -e .`. There is no `pytest` in any other interpreter
you should touch.

## Running the checks (from the project root)

```powershell
# clear mcpyrate's cached macro expansions, then run the tests
Get-ChildItem -Path src,tests,examples -Recurse -Directory -Filter __pycache__ |
    Remove-Item -Recurse -Force
& "C:\ProgramData\miniforge3\envs\work\python.exe" -m pytest -q

# static types
& "C:\ProgramData\miniforge3\envs\work\python.exe" -m pyright

# runnable example (needs the source tree on PYTHONPATH)
$env:PYTHONPATH = "$PWD\src"
& "C:\ProgramData\miniforge3\envs\work\python.exe" examples\demo.py
```

`mcpyrate` caches macro expansions in `__pycache__`. **After changing the macro
(`src/mathprint_main/`), clear the `src`/`tests`/`examples` `__pycache__` and run
in a fresh process**, or you may test stale expansions.

## What the project is

`mathprint` is a **vibecode** project: a `mcpyrate` macro `mpt` that prints an
expression in three phases — the exact source, the source with each variable
replaced by its current value (in place, order preserved), and the value. It is
opt-in LaTeX and opt-in display precision, all settings per file. See `README.md`
for the user-facing description and `src/mathprint_main/__init__.py` for the
implementation, which is a short pipeline of single-purpose classes (`Numbers`,
`Latex`, `Printer`, `Source`, `Expander`).

## Conventions

- Keep the import exactly `from mathprint import mpt` (a no-op stub lives in
  `src/mathprint/stub.py`).
- User-facing switches are `mpt.to_line()` / `mpt.to_column()`, `mpt.latex()`
  and `mpt.precision(n)` — each affects the file (or notebook) it is called in.
- The expression must be evaluated **exactly once**. The source is required:
  there is no fallback (a clear `MacroExpansionError` is raised when it is
  missing).
