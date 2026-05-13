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
