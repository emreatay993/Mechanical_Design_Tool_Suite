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

## Debug Builds And Error Logs

Normal builds are windowed and do not create packaged debug logs unless you ask
for them. To build console/debug executables that always write logs, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -Clean -DebugBuild
```

Debug builds place a flag file in the bundled `_internal` folder. Each packaged
executable then writes logs to:

```text
dist\MechanicalDesignToolSuite\_internal
```

Log files include the executable name, timestamp, and process id:

```text
MechanicalDesignToolSuite_YYYYMMDD_HHMMSS_PID.log
MechanicalDesignToolSuite_YYYYMMDD_HHMMSS_PID_faults.log
```

The main `.log` file captures Python logging, standard output, standard error,
unhandled Python exceptions, thread exceptions, and unraisable exceptions. The
`_faults.log` file is used by Python's `faulthandler` for lower-level crashes
that happen after the Python runtime has started.

## Debug Run Without Rebuilding

To run an existing bundle with debug logging enabled for that launch only, use
`-RunOnly -DebugRun`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -RunOnly -DebugRun -Program Launcher
```

Valid `-Program` values are:

| Program | Executable |
| --- | --- |
| `Launcher` | `MechanicalDesignToolSuite.exe` |
| `Bolt` | `BoltCalculationGui.exe` |
| `Tolerance` | `ToleranceAnalysis.exe` |
| `ToleranceVNext` | `ToleranceAnalysisVNext.exe` |

You can also build and launch with temporary debug-run logging in one command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -Clean -DebugRun -Program ToleranceVNext
```

When the packaged selector is running with debug logging enabled, it passes that
logging setting to any child GUI executable launched from the selector.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Selector opens but a program is missing | Rebuild and confirm all four expected executables are still next to each other. |
| vNext view does not open | Keep `_internal`, bundled UI files, and Qt plugin folders with the executables. |
| Spreadsheet import fails in packaged app | Rebuild after installing `openpyxl`; it is collected by the spec. |
| Build uses stale source code | Run the build from the repository root and keep the editable install step enabled. |
| Packaged app closes without a visible error | Re-run with `-DebugRun` or rebuild with `-DebugBuild`, then inspect `_internal\*.log`. |
| No log file appears | Confirm the `_internal` folder is writable and that the bundle is not installed under a protected location such as `Program Files`. |

Debug logging starts after PyInstaller's bootloader has started Python. It can
capture application exceptions and many Python runtime failures, but not every
early bootloader failure or native crash.
