[CmdletBinding()]
param(
    [switch]$Launch,
    [switch]$Clean,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")
$specPath = Join-Path $repoRoot "MechanicalDesignToolSuite.spec"
$distDir = Join-Path $repoRoot "dist\MechanicalDesignToolSuite"
$launcherExePath = Join-Path $distDir "MechanicalDesignToolSuite.exe"
$expectedExePaths = @(
    $launcherExePath,
    (Join-Path $distDir "BoltCalculationGui.exe"),
    (Join-Path $distDir "ToleranceAnalysis.exe"),
    (Join-Path $distDir "ToleranceAnalysisVNext.exe")
)

Push-Location $repoRoot
try {
    Write-Host "Using Python:" (& $Python --version)

    Write-Host "Installing runtime and build dependencies..."
    & $Python -m pip install -e ".[build]"
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed."
    }

    if ($Clean) {
        Write-Host "Removing previous PyInstaller outputs..."
        Remove-Item -LiteralPath (Join-Path $repoRoot "build") -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath (Join-Path $repoRoot "dist") -Recurse -Force -ErrorAction SilentlyContinue
    }

    Write-Host "Building MechanicalDesignToolSuite with PyInstaller..."
    & $Python -m PyInstaller --noconfirm $specPath
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed."
    }

    $missingExePaths = @($expectedExePaths | Where-Object { -not (Test-Path -LiteralPath $_) })
    if ($missingExePaths.Count -gt 0) {
        throw "Expected executable(s) were not created: $($missingExePaths -join ', ')"
    }

    Write-Host "Build complete:"
    foreach ($path in $expectedExePaths) {
        Write-Host "  $path"
    }

    if ($Launch) {
        Write-Host "Launching program selector..."
        Start-Process -FilePath $launcherExePath -WorkingDirectory $distDir
    }
}
finally {
    Pop-Location
}
