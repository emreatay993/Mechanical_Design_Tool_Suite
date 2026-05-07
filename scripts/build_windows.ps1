[CmdletBinding()]
param(
    [switch]$Launch,
    [switch]$Clean,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")
$specPath = Join-Path $repoRoot "BoltCalculationTool.spec"
$exePath = Join-Path $repoRoot "dist\BoltCalculationTool\BoltCalculationTool.exe"

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

    Write-Host "Building BoltCalculationTool with PyInstaller..."
    & $Python -m PyInstaller --noconfirm $specPath
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed."
    }

    if (-not (Test-Path -LiteralPath $exePath)) {
        throw "Expected executable was not created: $exePath"
    }

    Write-Host "Build complete:"
    Write-Host "  $exePath"

    if ($Launch) {
        Write-Host "Launching built executable..."
        Start-Process -FilePath $exePath -WorkingDirectory (Split-Path -Parent $exePath)
    }
}
finally {
    Pop-Location
}
