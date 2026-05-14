# P15 Runtime Launcher Packaging Hardening

## Summary

Harden the launch, environment, and packaging story for the CAD clone so users can run it through the suite launcher, direct entry point, and packaged build with reproducible dependencies.

## Worker Prompt

You are a `gpt-5.5` `xhigh` worker in `C:\Users\emre_\PycharmProjects\Mechanical_Design_Tool_Suite`. Your task is P15 Runtime Launcher Packaging Hardening. Reread `overnight_plans/README.md`, `09_full_clone_gap_closure_plan.md`, `08_primary_cad_viewer_plan.md`, P08-P14 outputs if present, and this packet before editing. After every context compaction, reread those files and this packet.

## Conservative Write Scope

- `environment-cad312.yml`
- `pyproject.toml`
- `MechanicalDesignToolSuite.spec`
- `scripts/build_windows.ps1`
- `scripts/run_cad_1d_tolerance.py`
- `src/mechanical_design_tool_suite/launcher.py`
- `README.md`
- `docs/pyinstaller_install_guide.md`
- launcher/build tests

## Deliverables

- CAD GUI entry point and suite launcher card validated.
- `Cad1DTolerance.exe` included in PyInstaller build outputs.
- `mdts-cad312` environment includes Python 3.12, NumPy 1.26, `pythonocc-core=7.9.3=*novtk*`, PyQt6, and `ffmpeg`.
- Explicit checks that PyQt5, Qt5 Conda `pyqt`, and non-`novtk` pythonocc are not introduced.
- Packaging notes for OCCT DLLs, Qt plugins, QML/assets, report assets, and video review tooling.
- Build script `-Program Cad1D` run path if not already present.
- Clear documentation for running launcher and direct CAD GUI with a `.step`, `.iges`, `.tolproj`, or `.tolpack`.

## Verification

```powershell
$env:PYTHONPATH="src"; python -m unittest tests.test_launcher
$env:PYTHONPATH="src"; python -m unittest discover -s tests
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s -m unittest tests.test_launcher
```

Packaged build verification if time allows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -Clean -Program Cad1D
```

## Non-Goals

- No native CAD SDK installation.
- No full installer/MSI polish.
- No dependency change that makes PyVista/VTK authoritative for CAD.

## Stop Condition

Stop when the CAD app can be launched reproducibly from source and the packaged build inputs know about it.
