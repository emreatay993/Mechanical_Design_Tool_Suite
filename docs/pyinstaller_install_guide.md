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

## 3. Secure Network And Nexus Setup

Use this section when the build machine is inside a company intranet where
public `repo.anaconda.com`, `conda-forge.org`, or `pypi.org` access is blocked
or slow, and Python packages must come through an internal Nexus server such as
`nexus.arge.net`.

### 3.1. Understand What Nexus Must Provide

Conda and pip do not use the same package format or the same repository layout:

| Tool | Needs | Example URL Shape |
| --- | --- | --- |
| pip | Python wheels/source distributions from a PyPI-compatible simple index | `https://nexus.arge.net/repository/pypi-proxy/simple` |
| Conda | Conda packages plus `repodata.json` for `win-64` and `noarch` subdirectories | `https://nexus.arge.net/repository/<conda-channel>/win-64/repodata.json` |

The highlighted command from the screenshot is valid for pip:

```powershell
python -m pip install -r requirements.txt --index-url https://nexus.arge.net/repository/pypi-proxy/simple --trusted-host nexus.arge.net
```

It does not configure Conda. If `conda env create` still tries
`https://repo.anaconda.com/...`, or fails while collecting `repodata.json`, the
Conda channel configuration is still pointing at public channels or Nexus does
not expose the Conda packages yet.

For this project, Nexus or another internal artifact location must provide:

- Conda packages from the readable environment or exact lock file:
  `environment-cad312.yml` or `environment-cad312-win-64.lock.txt`.
- pip packages constrained by `requirements-windows-py312.lock.txt`.
- `pythonocc-core` and OCCT from Conda, not pip. Keep the `7.9.3` `novtk`
  build to avoid pulling Conda Qt5 into the PyQt6 environment.

If the company has only a PyPI proxy and no Conda mirror, ask IT to mirror the
Conda packages in `environment-cad312-win-64.lock.txt`, or provide an offline
Conda package cache. `--trusted-host` cannot make pip install Conda packages.

### 3.2. Start From A Clean Conda Prompt

Use a fresh Miniforge or Anaconda Prompt, not an old terminal with a mixed
`PATH`. The screenshot showing `ImportError: Can't connect to HTTPS URL because
the SSL module is not available` means Conda's base Python cannot import
`ssl`; fix that before trying to create project environments.

Run:

```powershell
conda --version
where.exe conda
where.exe python
python -c "import sys, ssl; print(sys.executable); print(ssl.OPENSSL_VERSION)"
conda info
```

Expected result:

- `python -c "import ssl"` succeeds.
- `where.exe python` points inside the active Conda installation or active Conda
  environment, not another Python installation earlier on `PATH`.
- `conda info` does not end with SSL, plugin, or DLL-load errors.

If Conda itself is broken, try one diagnostic run without plugins:

```powershell
$env:CONDA_NO_PLUGINS = "true"
conda --no-plugins info
```

If that works, keep the variable only long enough to repair or create the
project environment. Typical permanent fixes are:

- Open a real Miniforge/Anaconda Prompt so Conda's `Library\bin` is first on
  `PATH`.
- Remove old Python, Qt, OpenSSL, or Conda paths that appear before the selected
  Conda installation on `PATH`.
- Reinstall Miniforge for the current user if base is read-only or Conda's
  `_ssl`, `truststore`, or solver plugins fail to import.
- Prefer a user-writable installation such as `%USERPROFILE%\miniforge3` on
  locked-down PCs.

Do not continue with project setup while base Conda cannot import `ssl`; every
HTTPS package operation will be unreliable.

### 3.3. Configure pip For Nexus

Use `python -m pip` so pip belongs to the active environment. Configure the
internal PyPI index once:

```powershell
python -m pip config set global.index-url https://nexus.arge.net/repository/pypi-proxy/simple
python -m pip config set global.trusted-host nexus.arge.net
python -m pip config set global.timeout 120
python -m pip config set global.retries 10
python -m pip config list -v
```

Then test the index with a small package used by the build toolchain:

```powershell
python -m pip index versions altgraph
```

If company policy does not allow persistent pip config, pass the same settings
per command:

```powershell
python -m pip install -e ".[build]" -c requirements-windows-py312.lock.txt --index-url https://nexus.arge.net/repository/pypi-proxy/simple --trusted-host nexus.arge.net --timeout 120 --retries 10
```

`--trusted-host nexus.arge.net` disables hostname/certificate verification for
that host. Use it only if your company requires it. The stronger long-term fix
is to install the company root certificate and configure pip/Conda to trust
that certificate instead of bypassing verification.

### 3.4. Configure Conda Channels For Nexus

First inspect the active Conda configuration:

```powershell
conda config --show-sources
conda config --show channels
```

Ask IT for the exact Nexus Conda channel URLs. They are usually different from
the PyPI URL and should contain Conda `win-64` and `noarch` metadata. Example
only:

```powershell
conda config --remove-key channels
conda config --add channels https://nexus.arge.net/repository/conda-forge
conda config --add channels https://nexus.arge.net/repository/conda-main
conda config --set channel_priority strict
conda config --set ssl_verify true
conda config --show channels
```

Validate the channel before creating the project environment:

```powershell
conda search pythonocc-core=7.9.3
conda search occt=7.9.3
conda search ffmpeg
```

If SSL inspection requires a company certificate bundle, prefer:

```powershell
conda config --set ssl_verify C:\path\to\company-ca-bundle.pem
```

Use `ssl_verify false` only as a temporary IT-approved diagnostic because it
turns off certificate validation for Conda.

### 3.5. Create The Project Environment On The Intranet

When Conda channels and pip are both configured, create the environment:

```powershell
conda env create -f environment-cad312.yml
conda activate mdts-cad312
$env:PYTHONNOUSERSITE = "1"
python -m pip config list
python -m pip install -e ".[build]" -c requirements-windows-py312.lock.txt
```

For a reproducible build machine, use the exact Win64 Conda lock file:

```powershell
conda create -n mdts-cad312 --file environment-cad312-win-64.lock.txt
conda activate mdts-cad312
$env:PYTHONNOUSERSITE = "1"
python -m pip install -e ".[build]" -c requirements-windows-py312.lock.txt
```

If the lock-file command downloads from public URLs, the lock file was created
against public Conda channels and the secure PC cannot reach them. In that case,
either:

- have IT mirror those exact package URLs into Nexus and provide matching
  internal channel URLs, or
- build the Conda package cache on an allowed machine, copy the package cache to
  the secure PC, and create the environment from that offline cache according
  to company policy.

After creation, use the verification commands in section 5 before running
PyInstaller.

### 3.6. PyCharm Terminal Checks

Most PyCharm failures come from the terminal using a different Python than the
configured project interpreter. In the PyCharm terminal, run:

```powershell
conda activate mdts-cad312
where.exe python
python -c "import sys; print(sys.executable)"
python -m pip --version
python -m pip config list
```

Always install with:

```powershell
python -m pip install ...
```

Do not rely on bare `pip install ...`; on Windows it can resolve to another
Python installation. If PyCharm opens PowerShell without Conda initialized,
open a Miniforge Prompt once and run:

```powershell
conda init powershell
```

Then close and reopen PyCharm.

## 4. Create The CAD-Capable Environment

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

## 5. Verify The Environment

Run these checks before building:

```powershell
python -s -m pip check
python -s -c "import importlib.util, numpy, pyvista, vtk, PyQt6.QtCore as QtCore, OCC; print('numpy', numpy.__version__); print('pyvista', pyvista.__version__); print('vtk', vtk.vtkVersion.GetVTKVersion()); print('PyQt6', QtCore.PYQT_VERSION_STR, QtCore.QT_VERSION_STR); print('PyQt5 present', importlib.util.find_spec('PyQt5') is not None); print('OCC.VERSION', getattr(OCC, 'VERSION', None))"
python -s -m unittest discover -s tests
```

The build wrapper runs the same guardrail class before PyInstaller. It fails if
the selected Python is not 3.12, NumPy is not 1.26.x, PyQt6/Qt6 is unavailable,
PyQt5 is importable, Conda `pyqt` or Conda Qt5 is installed, `pythonocc-core` or
OCCT is not `7.9.3` with a `novtk` build string, or `ffmpeg` is missing.

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

## 6. Smoke-Test The CAD Viewer

Open the caster wheel fixture directly in the CAD 1D tolerance GUI:

```powershell
python -s -m mechanical_design_tool_suite.cad_tolerance_gui tests\fixtures\cad_1d_tolerance\caster_whell_v0\caster_wheel.stp
```

The model should remain open while orbiting or dragging in the viewport. This
validates the PyQt6/pythonocc mouse-event path that failed under
`pythonocc-core 7.7.2`.

The same entry point accepts STEP/STP, IGES/IGS, `.tolproj`, and `.tolpack`
startup files:

```powershell
python -s scripts\run_cad_1d_tolerance.py tests\fixtures\cad_1d_tolerance\caster_whell_v0\caster_wheel.stp
python -s -m mechanical_design_tool_suite.cad_tolerance_gui tests\fixtures\cad_1d_tolerance\neutral_iges_single_part.igs
python -s -m mechanical_design_tool_suite.cad_tolerance_gui tests\fixtures\cad_1d_tolerance\sample_cad_1d_project.tolproj
python -s -m mechanical_design_tool_suite.cad_tolerance_gui path\to\project_package.tolpack
```

## 7. Build The Windows Package

Build from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -Clean -Python "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe"
```

The build script:

1. Installs this repo in editable mode with the pinned `build` extra.
2. Applies `requirements-windows-py312.lock.txt` as pip constraints.
3. Sets `PYTHONNOUSERSITE=1` so user-level Python packages cannot contaminate the build.
4. Verifies the CAD runtime guardrails for Python, NumPy, PyQt6/Qt6,
   `pythonocc-core`/OCCT `novtk`, forbidden Qt5/PyQt5 packages, and `ffmpeg`.
5. Cleans `build\` and `dist\` when `-Clean` is passed.
6. Runs PyInstaller with `MechanicalDesignToolSuite.spec`.
7. Verifies that all expected executables were produced, including
   `Cad1DTolerance.exe`.

To build the package and make the CAD executable the selected run target for a
later `-Launch` or `-RunOnly` step:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -Clean -Program Cad1D -Python "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe"
```

To build and immediately launch the selector:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -Clean -Launch -Python "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe"
```

## 8. Output Folder

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
`MechanicalDesignToolSuite.spec` collects the Python packages, `OCC` extension
modules, PyQt6 modules, and Conda `Library\bin` DLL dependencies reachable from
pythonocc. Do not move OCCT DLLs, Qt plugin folders, QML/assets, report output
assets, or the bundled `_internal` folder away from the executables.

Report CSS, JavaScript, manifests, and snapshot images are generated next to the
selected `.tolproj` or inside exported `.tolpack` packages at runtime. They are
not installer resources; keep those project-local folders together when sharing
engineering reports.

Video review tooling for clone/fidelity work uses `ffmpeg`/`ffprobe` from
`mdts-cad312`. Those tools are required for the build/runtime verification
environment, but they are not treated as a native CAD SDK or as a viewer
dependency.

## 9. Run Packaged Programs

Normal selector launch:

```powershell
.\dist\MechanicalDesignToolSuite\MechanicalDesignToolSuite.exe
```

Direct CAD launch:

```powershell
.\dist\MechanicalDesignToolSuite\Cad1DTolerance.exe
```

Direct CAD launch with startup files:

```powershell
.\dist\MechanicalDesignToolSuite\Cad1DTolerance.exe tests\fixtures\cad_1d_tolerance\caster_whell_v0\caster_wheel.stp
.\dist\MechanicalDesignToolSuite\Cad1DTolerance.exe tests\fixtures\cad_1d_tolerance\neutral_iges_single_part.igs
.\dist\MechanicalDesignToolSuite\Cad1DTolerance.exe tests\fixtures\cad_1d_tolerance\sample_cad_1d_project.tolproj
.\dist\MechanicalDesignToolSuite\Cad1DTolerance.exe path\to\project_package.tolpack
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

## 10. Debug Builds And Error Logs

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

## 11. Troubleshooting

| Symptom | Check |
| --- | --- |
| `ImportError: Can't connect to HTTPS URL because the SSL module is not available` | Conda's base Python cannot import `ssl`. Open a clean Miniforge/Anaconda Prompt, check `where.exe python`, and verify `python -c "import ssl"`. Fix PATH or reinstall Miniforge before creating the project env. |
| `Error while loading conda entry point ... DLL load failed` | Start with `$env:CONDA_NO_PLUGINS="true"` and `conda --no-plugins info`. If that works, repair the base Conda installation, remove conflicting PATH entries, or use a fresh user-writable Miniforge install. |
| Conda still contacts `repo.anaconda.com` | Configure Conda channels separately from pip. `--index-url https://nexus.arge.net/repository/pypi-proxy/simple` affects pip only. Run `conda config --show-sources` and replace public channels with IT-provided Nexus Conda channels. |
| `ReadTimeoutError` while pip reads `nexus.arge.net` | Confirm the URL opens from the secure PC, then retry with `python -m pip ... --timeout 120 --retries 10`. If only large packages time out, ask IT to check Nexus cache/proxy health and package availability. |
| pip says package not found in Nexus | Test with `python -m pip index versions <package>`. The Nexus PyPI proxy may not have cached or whitelisted the required wheel from `requirements-windows-py312.lock.txt`. |
| Conda cannot find `pythonocc-core=7.9.3` or `occt=7.9.3` | The Nexus Conda mirror is incomplete. Ask IT to mirror the packages in `environment-cad312-win-64.lock.txt`, including `win-64` and `noarch` metadata. |
| PyCharm terminal says pip is installed but imports still fail | In the PyCharm terminal run `where.exe python`, `python -m pip --version`, and `python -c "import sys; print(sys.executable)"`. Install with `python -m pip`, not bare `pip`. |
| Corporate certificate errors | Prefer installing the company root certificate and setting `conda config --set ssl_verify C:\path\to\company-ca-bundle.pem`. Use `--trusted-host` or `ssl_verify false` only when company policy explicitly allows it. |
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

### 11.1. Copy-Paste Diagnostic Block

When asking IT or another developer for help, run this in the same terminal
where the build fails and share the output:

```powershell
Write-Host "=== PATH TOOLS ==="
where.exe conda
where.exe python
where.exe pip

Write-Host "=== PYTHON SSL ==="
python -c "import sys, ssl; print(sys.executable); print(sys.version); print(ssl.OPENSSL_VERSION)"

Write-Host "=== CONDA ==="
conda --version
conda info
conda config --show-sources
conda config --show channels

Write-Host "=== PIP ==="
python -m pip --version
python -m pip config list -v
python -m pip index versions altgraph

Write-Host "=== PROJECT ENV ==="
python -s -m pip check
python -s -c "import importlib.util, numpy; print('numpy', numpy.__version__); print('PyQt5 present', importlib.util.find_spec('PyQt5') is not None)"
```
