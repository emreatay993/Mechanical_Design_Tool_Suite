# Mechanical Design Tool Suite

Desktop suite for mechanical design calculation tools, currently including
the bolt calculator and tolerance analysis workspaces.

## Run The Suite Launcher

From the repository root:

```powershell
python -m pip install -e .
python scripts\run_gui.py
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

The editable install also installs the PyVista dependency used by the 3D node
contour window.

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
