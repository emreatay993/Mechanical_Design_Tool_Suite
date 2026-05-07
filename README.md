# Bolt Calculation Tool

Prototype GUI and calculation backend for the documented `ExampleScenario`
circumferential flange bolt checks.

## Run The GUI

From the repository root:

```powershell
python scripts\run_gui.py
```

Or install the package in editable mode and use the console entry point:

```powershell
python -m pip install -e .
bolt-calc-gui
```

The prototype supports pasted or imported CSV/TSV/TXT tables with `FX`, `FY`,
`FZ`, `MX`, `MY`, and `MZ` columns. Optional `NodeID`, `X`, `Y`, and `Z`
columns are retained for result labels and visualization. Header units such as
`FX[kN]`, `MX[N.m]`, and `X[mm]` are converted into the documented internal
units before calculation.

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

Optional 3D node contour visualization uses PyVista:

```powershell
python -m pip install -e ".[visualization]"
```
