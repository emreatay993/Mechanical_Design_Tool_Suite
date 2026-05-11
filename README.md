# Bolt Calculation Tool

Prototype PyQt6 Fusion light GUI and calculation backend for the documented
`ExampleScenario` circumferential flange bolt checks.

## Run The GUI

From the repository root:

```powershell
python -m pip install -e .
python scripts\run_gui.py
```

Or install the package in editable mode and use the console entry point:

```powershell
python -m pip install -e .
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

The vNext app defaults to Qt Quick Fusion light styling. More modern Qt Quick
Controls styles can be selected when available:

```powershell
tolerance-analysis-vnext-gui --quick-style Material
tolerance-analysis-vnext-gui --quick-style Universal
```

The same style preference is also available from the vNext header. Changes are
saved as an app UI preference and applied on the next launch.

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

## Build Windows Executable

Build a PyInstaller onedir executable from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -Clean
```

The executable is written to:

```text
dist\BoltCalculationTool\BoltCalculationTool.exe
```

To build and launch it in one step:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -Clean -Launch
```
