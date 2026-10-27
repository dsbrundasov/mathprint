<#
.SYNOPSIS
    Save an OpenCode session as a JSON file inside this project.

.DESCRIPTION
    OpenCode keeps its session database outside the project (in the global data
    directory), so a checkout alone cannot carry a conversation to another
    computer. `opencode session export` / `import` can, though, and this script
    puts the export where the project can carry it: `.opencode/sessions/`.

    By default the newest session of this project is exported. Pass -Session to
    export a specific one (see `opencode session list`).

.PARAMETER Session
    Session ID to export. Omit to export the newest session of this project.

.PARAMETER Directory
    Project directory. Defaults to the repository root (the parent of tools/).

.EXAMPLE
    .\tools\session-save.ps1

.EXAMPLE
    .\tools\session-save.ps1 -Session ses_eb0632606ffe8TslWls1mqow85
#>
param(
    [string]$Session,
    [string]$Directory = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"

Push-Location $Directory
try {
    if (-not $Session) {
        $first = & opencode session list | Select-Object -First 1
        if (-not $first) {
            throw "No OpenCode sessions found for $Directory"
        }
        $Session = ($first -split "`t")[0]
    }
    $json = & opencode session export $Session
} finally {
    Pop-Location
}

if (-not $json) {
    throw "opencode session export $Session produced no output"
}

$outDir = Join-Path $Directory ".opencode\sessions"
New-Item -ItemType Directory -Force $outDir | Out-Null
$path = Join-Path $outDir "$Session.json"
$utf8 = New-Object System.Text.UTF8Encoding($false)  # no BOM: plain JSON
[System.IO.File]::WriteAllText($path, ($json -join "`n"), $utf8)

Write-Host "Saved session $Session to $path"
