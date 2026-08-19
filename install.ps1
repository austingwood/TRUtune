[CmdletBinding()]
param(
    [switch]$SkipShortcuts,
    [switch]$StartAfterInstall
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPath = Join-Path $projectRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
$requirementsPath = Join-Path $projectRoot "requirements.txt"

function Find-Python311 {
    $candidates = @(
        (Join-Path $env:LocalAppData "Programs\Python\Python311\python.exe"),
        "C:\Program Files\Python311\python.exe"
    )

    $pythonLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($null -ne $pythonLauncher) {
        try {
            $launcherResult = & $pythonLauncher.Source -3.11 -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0) {
                return $launcherResult.Trim()
            }
        }
        catch {
        }
    }

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    return $null
}

function New-Shortcut($shortcutPath, $targetPath) {
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $targetPath
    $shortcut.WorkingDirectory = $projectRoot
    $shortcut.Save()
}

Write-Host "TRUtune setup"
Write-Host "Project: $projectRoot"

$pythonPath = Find-Python311
if ($null -eq $pythonPath) {
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if ($null -eq $winget) {
        throw "Python 3.11 was not found. Install Python 3.11 from https://www.python.org/downloads/ and run this installer again."
    }

    Write-Host "Python 3.11 not found. Installing it with Windows Package Manager..."
    & $winget.Source install --id Python.Python.3.11 -e --scope user --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "Python 3.11 installation failed."
    }
    $pythonPath = Find-Python311
}

if ($null -eq $pythonPath) {
    throw "Python 3.11 was installed but could not be located. Restart PowerShell and run install.bat again."
}

$pythonVersion = (& $pythonPath --version 2>&1).ToString()
if ($pythonVersion -notmatch "Python 3\.11\.") {
    throw "TRUtune requires Python 3.11; found $pythonVersion."
}
Write-Host "Using $pythonPath ($pythonVersion)"

if (Test-Path $venvPython) {
    $venvVersion = (& $venvPython --version 2>&1).ToString()
    if ($LASTEXITCODE -ne 0 -or $venvVersion -notmatch "Python 3\.11\.") {
        Write-Host "Replacing the existing venv ($venvVersion)..."
        Remove-Item $venvPath -Recurse -Force
    }
}

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating .venv..."
    & $pythonPath -m venv $venvPath
}

Write-Host "Installing dependencies..."
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r $requirementsPath

Write-Host "Validating pyo and WxPython..."
& $venvPython -c "import wx, pyo; print('WxPython', wx.VERSION_STRING); print('pyo', pyo.getVersion())"
if ($LASTEXITCODE -ne 0) {
    throw "Dependency validation failed."
}

if (-not $SkipShortcuts) {
    $startScript = Join-Path $projectRoot "start_trutune.vbs"
    $guiScript = Join-Path $projectRoot "start_trutune_gui.vbs"
    $stopScript = Join-Path $projectRoot "stop_trutune.vbs"
    $desktop = [Environment]::GetFolderPath("Desktop")
    $startMenu = Join-Path ([Environment]::GetFolderPath("StartMenu")) "Programs\TRUtune"
    New-Item -ItemType Directory -Path $startMenu -Force | Out-Null
    New-Shortcut (Join-Path $desktop "TRUtune.lnk") $startScript
    New-Shortcut (Join-Path $startMenu "TRUtune.lnk") $startScript
    New-Shortcut (Join-Path $startMenu "TRUtune GUI.lnk") $guiScript
    New-Shortcut (Join-Path $startMenu "Stop TRUtune.lnk") $stopScript
    Write-Host "Shortcuts created on the Desktop and Start Menu."
}

Write-Host ""
Write-Host "TRUtune is ready. Double-click TRUtune.lnk or start_trutune.vbs to run silently."

if ($StartAfterInstall) {
    $startScript = Join-Path $projectRoot "start_trutune.vbs"
    Start-Process "wscript.exe" -ArgumentList "//nologo", "`"$startScript`""
    Write-Host "TRUtune started in the background."
}
