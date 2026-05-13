# Windows Desktop Install And Build Guide

This guide builds the Mechanical Design Tool Suite as a Windows onedir
PyInstaller package. It covers the full CAD-capable build path, including the
OCCT/pythonocc CAD viewer used by the CAD 1D tolerance prototype.

## Supported Target

Validated on:

| Component | Version |
| --- | --- |
| Windows | Windows 11 x64 |
| Conda distribution | Miniforge / conda-forge |
| Python | 3.12.13 |
| NumPy | 1.26.4 |
| PyQt6 / Qt | 6.11.0 / 6.11.0 |
| pythonocc-core | 7.9.3 `novtk` |
| OCCT | 7.9.3 `novtk` |
| PyVista / PyVistaQt / VTK | 0.48.2 / 0.11.4 / 9.6.1 |
| OpenPyXL | 3.1.5 |
| PyInstaller | 6.20.0 |

The package versions are frozen in:

- [`environment-cad312.yml`](../environment-cad312.yml): readable Conda CAD environment spec.
- [`environment-cad312-win-64.lock.txt`](../environment-cad312-win-64.lock.txt): exact Win64 Conda package URLs.
- [`requirements-windows-py312.lock.txt`](../requirements-windows-py312.lock.txt): pip constraints for runtime and build packages.

Use the readable `environment-cad312.yml` for normal development. Use the
explicit lock file when a build machine must reproduce the same Win64 Conda
packages exactly.

## 1. Install System Tools

Open PowerShell as a normal user. Install Miniforge if Conda is not already
available:

```powershell
winget install -e --id CondaForge.Miniforge3
```

If `winget` is unavailable, download the Windows x86_64 Miniforge installer:

```text
https://conda-forge.org/download/
```

After installation, open a new PowerShell or Miniforge Prompt and verify:

```powershell
conda --version
git --version
```

## 2. Get The Source

Clone the repository, or copy an existing checkout, then enter the repo root:

```powershell
git clone <repo-url> Mechanical_Design_Tool_Suite
cd Mechanical_Design_Tool_Suite
```

All remaining commands assume the current directory is the repository root.

## 3. Create The CAD-Capable Environment

Preferred readable setup:

```powershell
conda env create -f environment-cad312.yml
conda activate mdts-cad312
$env:PYTHONNOUSERSITE = "1"
```

If the environment already exists, update it:

```powershell
conda env update -f environment-cad312.yml
conda activate mdts-cad312
$env:PYTHONNOUSERSITE = "1"
```

Exact Win64 lock-file setup:

```powershell
conda create -n mdts-cad312 --file environment-cad312-win-64.lock.txt
conda activate mdts-cad312
$env:PYTHONNOUSERSITE = "1"
python -m pip install -e ".[build]" -c requirements-windows-py312.lock.txt
```

Do not install Conda `pyqt`, PyQt5, Qt5, or a non-`novtk` `pythonocc-core`
build into this environment. PyQt6 is installed by pip through the project
dependency set; OCCT/pythonocc comes from conda-forge.

## 4. Verify The Environment

Run these checks before building:

```powershell
python -s -m pip check
python -s -c "import importlib.util, numpy, pyvista, vtk, PyQt6.QtCore as QtCore, OCC; print('numpy', numpy.__version__); print('pyvista', pyvista.__version__); print('vtk', vtk.vtkVersion.GetVTKVersion()); print('PyQt6', QtCore.PYQT_VERSION_STR, QtCore.QT_VERSION_STR); print('PyQt5 present', importlib.util.find_spec('PyQt5') is not None); print('OCC.VERSION', getattr(OCC, 'VERSION', None))"
python -s -m unittest discover -s tests
```

Expected environment check highlights:

```text
numpy 1.26.4
pyvista 0.48.2
vtk 9.6.1
PyQt6 6.11.0 6.11.0
PyQt5 present False
OCC.VERSION 7.9.0
```

The full test suite should report:

```text
Ran 113 tests
OK (skipped=2)
```

## 5. Smoke-Test The CAD Viewer

Open the caster wheel fixture directly in the CAD 1D tolerance GUI:

```powershell
python -s -m mechanical_design_tool_suite.cad_tolerance_gui tests\fixtures\cad_1d_tolerance\caster_whell_v0\caster_wheel.stp
```

The model should remain open while orbiting or dragging in the viewport. This
validates the PyQt6/pythonocc mouse-event path that failed under
`pythonocc-core 7.7.2`.

## 6. Build The Windows Package

Build from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -Clean -Python "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe"
```

The build script:

1. Installs this repo in editable mode with the pinned `build` extra.
2. Applies `requirements-windows-py312.lock.txt` as pip constraints.
3. Sets `PYTHONNOUSERSITE=1` so user-level Python packages cannot contaminate the build.
4. Cleans `build\` and `dist\` when `-Clean` is passed.
5. Runs PyInstaller with `MechanicalDesignToolSuite.spec`.
6. Verifies that all expected executables were produced.

To build and immediately launch the selector:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -Clean -Launch -Python "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe"
```

## 7. Output Folder

The packaged suite is written to:

```text
dist\MechanicalDesignToolSuite
```

Expected launch files:

| Executable | Purpose |
| --- | --- |
| `MechanicalDesignToolSuite.exe` | Program selector shown to end users. |
| `BoltCalculationGui.exe` | Direct launch for the bolt calculation GUI. |
| `ToleranceAnalysis.exe` | Direct launch for the legacy tolerance GUI. |
| `ToleranceAnalysisVNext.exe` | Direct launch for the vNext tolerance GUI. |
| `Cad1DTolerance.exe` | Direct launch for the CAD 1D tolerance GUI. |

Keep the full `dist\MechanicalDesignToolSuite` folder together. The executables
share the `_internal` runtime folder, Qt plugins, QML files, and bundled data.

## 8. Run Packaged Programs

Normal selector launch:

```powershell
.\dist\MechanicalDesignToolSuite\MechanicalDesignToolSuite.exe
```

Direct CAD launch:

```powershell
.\dist\MechanicalDesignToolSuite\Cad1DTolerance.exe
```

Build script launch helpers:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -RunOnly -Program Launcher
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -RunOnly -Program Cad1D
```

Valid `-Program` values:

| Program | Executable |
| --- | --- |
| `Launcher` | `MechanicalDesignToolSuite.exe` |
| `Bolt` | `BoltCalculationGui.exe` |
| `Tolerance` | `ToleranceAnalysis.exe` |
| `ToleranceVNext` | `ToleranceAnalysisVNext.exe` |
| `Cad1D` | `Cad1DTolerance.exe` |

## 9. Debug Builds And Error Logs

Normal builds are windowed and do not create packaged debug logs unless requested.
To build console/debug executables that always write logs:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -Clean -DebugBuild -Python "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe"
```

Debug builds place a flag file in the bundled `_internal` folder. Each packaged
executable writes logs to:

```text
dist\MechanicalDesignToolSuite\_internal
```

Log files include executable name, timestamp, and process id:

```text
MechanicalDesignToolSuite_YYYYMMDD_HHMMSS_PID.log
MechanicalDesignToolSuite_YYYYMMDD_HHMMSS_PID_faults.log
```

To run an existing bundle with debug logging enabled for one launch:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -RunOnly -DebugRun -Program Cad1D
```

## 10. Troubleshooting

| Symptom | Check |
| --- | --- |
| `pythonocc-core` is unavailable | Use Miniforge/conda-forge, not `pip install pythonocc-core`. |
| CAD viewport closes while interacting | Confirm `pythonocc-core 7.9.3` and `PyQt6 6.11.0`; old `7.7.2` pythonocc event handlers use stale Qt enum names. |
| PyQt5 appears in checks | Recreate the env; do not install Conda `pyqt`, PyQt5, or Qt5. |
| VTK/PyVista tests fail under offscreen Qt | Confirm NumPy is `1.26.4` and the repo includes the offscreen PyVistaQt guard. |
| Selector opens but a program is missing | Rebuild and confirm all five expected executables are next to each other. |
| vNext view does not open | Keep `_internal`, bundled QML files, and Qt plugin folders with the executables. |
| Spreadsheet import fails | Rebuild after installing `openpyxl`; it is part of the pinned runtime set. |
| Build uses stale source code | Run the build from the repository root and keep the editable install step enabled. |
| Packaged app closes without a visible error | Re-run with `-DebugRun` or rebuild with `-DebugBuild`, then inspect `_internal\*.log`. |
| No log file appears | Confirm `_internal` is writable and the bundle is not under `Program Files`. |

PyInstaller debug logging starts after the bootloader has started Python. It can
capture application exceptions and many Python runtime failures, but not every
early bootloader failure or native crash.
