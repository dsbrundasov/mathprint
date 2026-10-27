<#
.SYNOPSIS
    Import a saved session into OpenCode for this project.

.DESCRIPTION
    Counterpart of `tools/session-save.ps1`: reads a JSON export and creates the
    session in the current project, so work can continue on another computer
    after syncing or cloning the project folder.

.PARAMETER File
    The JSON file to import (for example `.opencode/sessions/<id>.json`).

.PARAMETER Directory
    Project to import the session into. Defaults to the repository root.

.EXAMPLE
    .\tools\session-load.ps1 .opencode\sessions\ses_eb0632606ffe8TslWls1mqow85.json
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$File,
    [string]$Directory = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"

& opencode session import $File --directory $Directory

Write-Host "Imported $File into $Directory"
