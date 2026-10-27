# Portable sessions

OpenCode stores its session database in the global data directory
(`~/.local/share/opencode/opencode.db` on Linux/macOS, `%LOCALAPPDATA%\opencode`
on Windows). A checkout alone therefore does not carry the conversation to
another computer, and OpenCode has no "keep sessions in the project" setting.

Instead, sessions are exported into the project on demand, using OpenCode's own
`session export` / `session import` commands:

```powershell
# Save the newest session of this project
.\tools\session-save.ps1

# Save a specific session (see `opencode session list`)
.\tools\session-save.ps1 -Session ses_eb0632606ffe8TslWls1mqow85

# On the other computer, after syncing/cloning the project
.\tools\session-load.ps1 .opencode\sessions\ses_eb0632606ffe8TslWls1mqow85.json
```

The exports are written to `.opencode/sessions/<session-id>.json`, so they live
inside the project folder. The export contains the whole transcript (messages,
tool calls, outputs), which is what makes it possible to continue the work.

`.opencode/` is ignored by Git (see `.gitignore`): the files stay local to the
project directory and travel with whatever syncs that directory. If the project
is transferred through Git instead, add the session file to the allowlist or
commit it explicitly.
