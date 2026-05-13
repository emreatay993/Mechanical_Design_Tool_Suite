# Mechanical Design Tool Suite

Desktop suite for mechanical design calculation tools, currently including
the bolt calculator and tolerance analysis workspaces.

## Install On A New Development Machine

Use this path when the target computer does not already have the project,
PyQt6, PyVista, or OpenCascade/pythonocc installed.

### Standard install: bolt tool, STL reference parts, and non-CAD tests

This install is enough for the suite launcher, bolt calculations, the embedded
bolt 3D scene, STL reference-part loading, and the non-OCCT test suite. It does
not enable STEP/IGES import because that needs OpenCascade through
`pythonocc-core`.

```powershell
git clone https://github.com/emreatay993/Mechanical_Design_Tool_Suite.git
cd Mechanical_Design_Tool_Suite

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -e .

$env:PYTHONPATH="src"
python -m unittest discover -s tests
mechanical-design-tool-suite
```

The editable install brings in the normal GUI/runtime dependencies declared in
`pyproject.toml`, including `PyQt6`, `pyvista`, `pyvistaqt`, and `openpyxl`.
The bolt tool can load `.stl` reference parts in this setup. If `pyvistaqt` is
missing or the local Qt/OpenGL stack cannot initialize, the app still opens and
the `3D Scene` tab shows an embedded-scene placeholder instead of crashing.

### CAD install: STEP/IGES reference parts and OCCT viewer tests

Use this path when the machine needs STEP/STP or IGES/IGS import. Do not rely on
`pip install pythonocc-core` for this project; on common Windows/Python
combinations it may not be available from PyPI. Use the pinned Conda
environment instead.

If the machine does not have Conda yet, install Miniforge first. Miniforge is
the recommended lightweight Conda distribution here because it is already
configured for `conda-forge`, where `pythonocc-core` is available.

Option A, from PowerShell with Windows Package Manager:

```powershell
winget install -e --id CondaForge.Miniforge3
```

Option B, if `winget` is unavailable:

1. Open the official conda-forge Miniforge download page:
   <https://conda-forge.org/download/>
2. Download the Windows x86_64 Miniforge installer.
3. Run the installer for the current user.
4. Open a new "Miniforge Prompt" or a new PowerShell window after installation.

Confirm Conda is available:

```powershell
conda --version
```

Then create the project CAD environment from the repository root:

```powershell
conda env create -f environment-cad312.yml
conda activate mdts-cad312

$env:PYTHONNOUSERSITE="1"
$env:PYTHONPATH="src"

python -c "import OCC; from OCC.Display.backend import load_backend; load_backend('pyqt6'); print('OCCT/PyQt6 backend OK')"
python -m unittest discover -s tests
mechanical-design-tool-suite
```

`environment-cad312.yml` pins Python 3.12 and
`pythonocc-core=7.7.2=*novtk*` from `conda-forge`, then installs this package in
editable mode. Keep that `novtk` build unless you have a specific reason to
change it; it avoids pulling in Conda Qt5 while preserving STEP/IGES import,
B-Rep topology, AIS/V3d display, and selection support. PyQt6 should come from
the project dependency install, not from Conda `pyqt` or PyQt5.

After this setup:

- `.stl` reference parts load as mesh-only visual references in the bolt tool.
- `.step`, `.stp`, `.iges`, and `.igs` reference parts use the OCCT/pythonocc
  path and are converted to visual meshes for the bolt scene.
- The CAD 1D tolerance viewer can use the OCCT AIS/V3d backend when the local
  display driver supports it.

If CAD imports fail, first confirm that `conda activate mdts-cad312` is active,
`PYTHONNOUSERSITE=1` is set, and `python -c "import OCC"` succeeds in that same
terminal.

## Run The Suite Launcher

From the repository root:

```powershell
python -m pip install -e .
python scripts\run_launcher.py
```

Or install the package in editable mode and use the console entry point:

```powershell
python -m pip install -e .
mechanical-design-tool-suite
```

The launcher opens the program selector used by packaged builds. To open only
the bolt calculation GUI:

```powershell
bolt-calc-gui
```

## Run The Standalone Tolerance Analysis GUI

The Five Flute-style tolerance stackup calculator clone is available as a
separate PyQt6 app:

```powershell
python scripts\run_tolerance_analysis.py
```

Or through the editable-install entry point:

```powershell
tolerance-analysis-gui
```

The next-version joint-driven tolerance workspace is available as:

```powershell
python scripts\run_tolerance_vnext_analysis.py
```

Or through the editable-install entry point:

```powershell
tolerance-analysis-vnext-gui
```

The vNext app defaults to Fusion light styling. More modern UI styles can be
selected when available:

```powershell
tolerance-analysis-vnext-gui --quick-style Material
tolerance-analysis-vnext-gui --quick-style Universal
```

The same style preference is also available from the vNext header. Changes are
saved as an app UI preference and applied on the next launch.

The vNext workspace supports asymmetric `-Tol` / `+Tol` entry, optional seeded
Monte Carlo simulation, and full-project stackup import from `.csv` or `.xlsx`
tables. Import tables use flat rows with `joint`, `sub_joint`, `item_type`,
`item_name`, `nominal_thickness`, and either `tolerance` or
`tolerance_minus` / `tolerance_plus` columns.

Design documents for the tolerance analysis GUI are in
[`docs/tolerance_tool`](docs/tolerance_tool/README.md).

The prototype supports pasted or imported CSV/TSV/TXT tables with `FX`, `FY`,
`FZ`, `MX`, `MY`, and `MZ` columns. Optional `NodeID`, `X`, `Y`, and `Z`
columns are retained for result labels and visualization. Header units such as
`FX[kN]`, `MX[N.m]`, and `X[mm]` are converted into the documented internal
units before calculation.

The GUI opens with the reference ExampleScenario already calculated. Result
actions enable only when valid data is available, and selecting a result row
updates the trace panel with that bolt's detailed calculation breakdown.
The bolt `3D Scene` tab can add visual reference parts. STL files are unitless,
so select the STL source units (`mm`, `m`, or `inch`) before import; the mesh is
scaled into the bolt tool's internal millimeter coordinate system. The same
panel can also show or hide the X, Y, and Z scene axes, and adjust bolt node
size with the slider or `Ctrl++` / `Ctrl+-`.

The implemented calculation path is the documented `.2500-28` ExampleScenario
reference case. Other bolt sizes appear in source lookup formulas, but complete
prototype constants are only documented for `.2500-28`.

## Verification

Run the existing standalone document benchmarks:

```powershell
python scripts\benchmark_example_scenario_bolt_strength.py
python scripts\benchmark_example_scenario_interaction_curve.py
```

Run the package backend tests:

```powershell
$env:PYTHONPATH="src"; python -m unittest discover -s tests
```

The standard editable install covers PyVista/PyVistaQt visualization and skips
OCCT-specific tests when OpenCascade/pythonocc is not installed. To run the real
STEP/IGES and OCCT viewer paths, use the `mdts-cad312` environment described
above.

## Build Windows Executables

Build the PyInstaller onedir GUI suite from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -Clean
```

The program selector is written to:

```text
dist\MechanicalDesignToolSuite\MechanicalDesignToolSuite.exe
```

The same folder also contains direct launchers for the bolt calculation GUI,
the legacy tolerance GUI, and the vNext tolerance GUI. See
[`docs/pyinstaller_install_guide.md`](docs/pyinstaller_install_guide.md) for the
full build and troubleshooting guide.

To build and launch it in one step:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -Clean -Launch
```

For a debug bundle that opens console windows and writes packaged error logs
under `dist\MechanicalDesignToolSuite\_internal`, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -Clean -DebugBuild
```

To run an existing packaged executable with temporary debug logging enabled:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -RunOnly -DebugRun -Program Launcher
```

Valid `-Program` values are `Launcher`, `Bolt`, `Tolerance`, and
`ToleranceVNext`.
