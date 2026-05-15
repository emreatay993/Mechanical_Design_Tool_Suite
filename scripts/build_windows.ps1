<#
.SYNOPSIS
Builds or runs the Windows PyInstaller bundle for Mechanical Design Tool Suite.

.EXAMPLE
.\scripts\build_windows.ps1 -Clean
Builds the normal windowed bundle.

.EXAMPLE
.\scripts\build_windows.ps1 -Clean -DebugBuild
Builds console/debug executables that always write packaged logs into _internal.

.EXAMPLE
.\scripts\build_windows.ps1 -RunOnly -DebugRun -Program ToleranceVNext
Runs an existing bundled executable with packaged logging enabled.

.EXAMPLE
.\scripts\build_windows.ps1 -Clean -Program Cad1D
Builds the CAD-capable bundle and verifies Cad1DTolerance.exe is present.
#>
[CmdletBinding()]
param(
    [switch]$Launch,
    [switch]$Clean,
    [switch]$DebugBuild,
    [switch]$DebugRun,
    [switch]$RunOnly,
    [ValidateSet("Launcher", "Bolt", "Tolerance", "ToleranceVNext", "Cad1D")]
    [string]$Program = "Launcher",
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")
$specPath = Join-Path $repoRoot "MechanicalDesignToolSuite.spec"
$distDir = Join-Path $repoRoot "dist\MechanicalDesignToolSuite"
$constraintsPath = Join-Path $repoRoot "requirements-windows-py312.lock.txt"
$launcherExePath = Join-Path $distDir "MechanicalDesignToolSuite.exe"
$programExePaths = @{
    Launcher = $launcherExePath
    Bolt = Join-Path $distDir "BoltCalculationGui.exe"
    Tolerance = Join-Path $distDir "ToleranceAnalysis.exe"
    ToleranceVNext = Join-Path $distDir "ToleranceAnalysisVNext.exe"
    Cad1D = Join-Path $distDir "Cad1DTolerance.exe"
}
$selectedExePath = $programExePaths[$Program]
$expectedExePaths = @(
    $launcherExePath,
    $programExePaths["Bolt"],
    $programExePaths["Tolerance"],
    $programExePaths["ToleranceVNext"],
    $programExePaths["Cad1D"]
)
$debugFlagPaths = @(
    (Join-Path $repoRoot "build\mdts_debug_build.flag"),
    (Join-Path $distDir "_internal\mdts_debug_build.flag")
)

function Restore-ProcessEnvironment {
    param(
        [string]$Name,
        [AllowNull()]
        [string]$PreviousValue
    )

    [Environment]::SetEnvironmentVariable($Name, $PreviousValue, "Process")
}

function Start-BundledProgram {
    param(
        [string]$ExePath,
        [string]$WorkingDirectory,
        [switch]$EnableDebugLogs
    )

    if (-not (Test-Path -LiteralPath $ExePath)) {
        throw "Executable was not found: $ExePath"
    }

    $previousDebugLogs = [Environment]::GetEnvironmentVariable("MDTS_PACKAGED_ERROR_LOGS", "Process")
    try {
        if ($EnableDebugLogs) {
            [Environment]::SetEnvironmentVariable("MDTS_PACKAGED_ERROR_LOGS", "1", "Process")
            Write-Host "Debug-run logging enabled. Logs will be written under:"
            Write-Host "  $(Join-Path $WorkingDirectory "_internal")"
        }

        Start-Process -FilePath $ExePath -WorkingDirectory $WorkingDirectory
    }
    finally {
        Restore-ProcessEnvironment -Name "MDTS_PACKAGED_ERROR_LOGS" -PreviousValue $previousDebugLogs
    }
}

function Test-CadRuntimeDependencies {
    param(
        [string]$Python
    )

    Write-Host "Checking CAD runtime dependency guardrails..."
    $checkScript = @'
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path


errors = []

if sys.version_info[:2] != (3, 12):
    errors.append(f"Python 3.12 is required for the CAD runtime; found {sys.version.split()[0]}.")

try:
    import numpy
except Exception as exc:
    errors.append(f"NumPy import failed: {exc}")
else:
    if not numpy.__version__.startswith("1.26."):
        errors.append(f"NumPy 1.26.x is required; found {numpy.__version__}.")

try:
    import PyQt6.QtCore as QtCore
except Exception as exc:
    errors.append(f"PyQt6 import failed: {exc}")
else:
    if not str(QtCore.QT_VERSION_STR).startswith("6."):
        errors.append(f"Qt 6.x is required through PyQt6; found Qt {QtCore.QT_VERSION_STR}.")

if importlib.util.find_spec("PyQt5") is not None:
    errors.append("PyQt5 is present; recreate mdts-cad312 without PyQt5.")

try:
    import OCC
except Exception as exc:
    errors.append(f"OCC/pythonocc import failed: {exc}")

conda_meta = Path(sys.prefix) / "conda-meta"
conda_packages = {}
if conda_meta.exists():
    for record_path in conda_meta.glob("*.json"):
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        name = str(record.get("name", "")).lower()
        if name:
            conda_packages[name] = record

conda_pyqt = [
    name
    for name in conda_packages
    if name == "pyqt" or name.startswith("pyqt5") or name.startswith("pyqt-")
]
if conda_pyqt:
    errors.append("Conda pyqt/PyQt5 package(s) are present: " + ", ".join(sorted(conda_pyqt)))

for qt_package in ("qt", "qt-main", "qtbase"):
    record = conda_packages.get(qt_package)
    if record and str(record.get("version", "")).startswith("5."):
        errors.append(
            f"Conda Qt5 package is present: {qt_package} {record.get('version')}."
        )

pythonocc_record = conda_packages.get("pythonocc-core")
if pythonocc_record is None:
    errors.append("pythonocc-core must come from conda-forge in mdts-cad312.")
else:
    version = str(pythonocc_record.get("version", ""))
    build = str(pythonocc_record.get("build", ""))
    if version != "7.9.3":
        errors.append(f"pythonocc-core 7.9.3 is required; found {version}.")
    if "novtk" not in build.lower():
        errors.append(f"pythonocc-core must use the novtk build; found build {build!r}.")

occt_record = conda_packages.get("occt")
if occt_record is not None:
    version = str(occt_record.get("version", ""))
    build = str(occt_record.get("build", ""))
    if version != "7.9.3":
        errors.append(f"OCCT 7.9.3 is required; found {version}.")
    if "novtk" not in build.lower():
        errors.append(f"OCCT must use the novtk build; found build {build!r}.")

ffmpeg_candidates = [
    Path(sys.prefix) / "Library" / "bin" / "ffmpeg.exe",
    Path(sys.prefix) / "bin" / "ffmpeg",
]
if not any(path.exists() for path in ffmpeg_candidates) and shutil.which("ffmpeg") is None:
    errors.append("ffmpeg is required in mdts-cad312 for video/evidence tooling.")

if errors:
    print("CAD runtime dependency guard failed:")
    for error in errors:
        print(f"  - {error}")
    raise SystemExit(1)

print("CAD runtime dependency guard passed.")
'@

    $checkScriptPath = [System.IO.Path]::ChangeExtension([System.IO.Path]::GetTempFileName(), ".py")
    try {
        Set-Content -LiteralPath $checkScriptPath -Value $checkScript -Encoding UTF8
        & $Python -s $checkScriptPath
        if ($LASTEXITCODE -ne 0) {
            throw "CAD runtime dependency checks failed. Use environment-cad312.yml / mdts-cad312."
        }
    }
    finally {
        Remove-Item -LiteralPath $checkScriptPath -Force -ErrorAction SilentlyContinue
    }
}

if ($DebugRun -and -not $Launch -and -not $RunOnly) {
    $Launch = $true
}

$previousPythonNoUserSite = [Environment]::GetEnvironmentVariable("PYTHONNOUSERSITE", "Process")
Push-Location $repoRoot
try {
    [Environment]::SetEnvironmentVariable("PYTHONNOUSERSITE", "1", "Process")

    if (-not $RunOnly) {
        Write-Host "Using Python:" (& $Python --version)

        Write-Host "Installing runtime and build dependencies..."
        if (Test-Path -LiteralPath $constraintsPath) {
            & $Python -m pip install -e ".[build]" -c $constraintsPath
        }
        else {
            & $Python -m pip install -e ".[build]"
        }
        if ($LASTEXITCODE -ne 0) {
            throw "Dependency installation failed."
        }
        Test-CadRuntimeDependencies -Python $Python

        if ($Clean) {
            Write-Host "Removing previous PyInstaller outputs..."
            Remove-Item -LiteralPath (Join-Path $repoRoot "build") -Recurse -Force -ErrorAction SilentlyContinue
            Remove-Item -LiteralPath (Join-Path $repoRoot "dist") -Recurse -Force -ErrorAction SilentlyContinue
        }

        if (-not $DebugBuild) {
            Remove-Item -LiteralPath $debugFlagPaths -Force -ErrorAction SilentlyContinue
        }

        $previousPyiDebug = [Environment]::GetEnvironmentVariable("MDTS_PYI_DEBUG", "Process")
        try {
            if ($DebugBuild) {
                [Environment]::SetEnvironmentVariable("MDTS_PYI_DEBUG", "1", "Process")
                Write-Host "PyInstaller debug build enabled. The bundle will create packaged logs in _internal."
            }
            else {
                [Environment]::SetEnvironmentVariable("MDTS_PYI_DEBUG", $null, "Process")
            }

            Write-Host "Building MechanicalDesignToolSuite with PyInstaller..."
            & $Python -m PyInstaller --noconfirm $specPath
            if ($LASTEXITCODE -ne 0) {
                throw "PyInstaller build failed."
            }
        }
        finally {
            Restore-ProcessEnvironment -Name "MDTS_PYI_DEBUG" -PreviousValue $previousPyiDebug
        }

        $missingExePaths = @($expectedExePaths | Where-Object { -not (Test-Path -LiteralPath $_) })
        if ($missingExePaths.Count -gt 0) {
            throw "Expected executable(s) were not created: $($missingExePaths -join ', ')"
        }

        Write-Host "Build complete:"
        foreach ($path in $expectedExePaths) {
            Write-Host "  $path"
        }
    }
    elseif (-not (Test-Path -LiteralPath $selectedExePath)) {
        throw "Cannot run existing bundle because the selected executable does not exist: $selectedExePath"
    }

    if ($Launch -or $RunOnly) {
        Write-Host "Launching $Program..."
        Start-BundledProgram -ExePath $selectedExePath -WorkingDirectory $distDir -EnableDebugLogs:$DebugRun
    }
}
finally {
    Restore-ProcessEnvironment -Name "PYTHONNOUSERSITE" -PreviousValue $previousPythonNoUserSite
    Pop-Location
}
