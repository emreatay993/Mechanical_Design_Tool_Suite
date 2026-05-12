# PyInstaller Windows Build Guide

This guide builds the GUI suite as a Windows onedir PyInstaller package.

## Prerequisites

- Windows with Python 3.10 or newer on `PATH`
- A fresh virtual environment is recommended
- Run commands from the repository root

## Build Command

```powershell
python -m pip install --upgrade pip
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -Clean
```

The build script installs the package in editable mode with the `build` extra,
runs PyInstaller with `MechanicalDesignToolSuite.spec`, and validates the expected
executables.

## Output Folder

The packaged suite is written to:

```text
dist\MechanicalDesignToolSuite
```

Expected launch files:

| Executable | Purpose |
| --- | --- |
| `MechanicalDesignToolSuite.exe` | Professional program selector shown to end users. |
| `BoltCalculationGui.exe` | Direct launch for the bolt calculation GUI. |
| `ToleranceAnalysis.exe` | Direct launch for the legacy tolerance GUI. |
| `ToleranceAnalysisVNext.exe` | Direct launch for the vNext tolerance GUI. |

Keep the full `dist\MechanicalDesignToolSuite` folder together. The executables share
the `_internal` runtime folder, Qt plugins, QML files, and bundled catalog data.

## Launch After Build

```powershell
.\dist\MechanicalDesignToolSuite\MechanicalDesignToolSuite.exe
```

To build and launch the selector in one step:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -Clean -Launch
```

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Selector opens but a program is missing | Rebuild and confirm all four expected executables are still next to each other. |
| vNext view does not open | Keep `_internal`, bundled UI files, and Qt plugin folders with the executables. |
| Spreadsheet import fails in packaged app | Rebuild after installing `openpyxl`; it is collected by the spec. |
| Build uses stale source code | Run the build from the repository root and keep the editable install step enabled. |
