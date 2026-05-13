# P07 Integration Fidelity Packaging

## Summary

Integrate the first end-to-end CAD 1D tolerance clone path, perform a visual fidelity review, and document packaging/dependency risks.

## Worker Prompt

You are a `gpt-5.5` `xhigh` worker in `C:\Users\emre_\PycharmProjects\Mechanical_Design_Tool_Suite`. Your task is P07 Integration Fidelity Packaging. Reread `overnight_plans/README.md`, all numbered CAD docs including `08_primary_cad_viewer_plan.md`, `extracted_specs/2026-05-12_eztol_targeted_visual_review.md`, and all completed packet notes before editing. After every context compaction, reread those files and this packet. If uncertain about UI fidelity, inspect the local viewer and targeted visual review key frames before changing the UI.

## Conservative Write Scope

- Entry point wiring in `pyproject.toml`
- Integration fixtures/tests
- `docs/cad_1d_tolerance_tool/`
- Small glue fixes across CAD-specific modules created by P01-P06

## Deliverables

- Launchable CAD 1D tolerance GUI entry point.
- End-to-end fixture path: open/import or load fixture project, show summary, drill into detail, update tolerance, see results, generate report.
- UI fidelity gap list against visual evidence.
- UI fidelity gap list against the targeted visual review, including exact unreadable labels/symbols that need new crops.
- Packaging/dependency notes for the primary CAD viewer runtime: Python 3.12, `pythonocc-core 7.7.2=*novtk*`, PyQt6, `load_backend("pyqt6")`, and `qtViewer3d`/AIS/V3d. Confirm PyQt5/Qt5 and Conda `pyqt` are not introduced.
- End-to-end confirmation that viewer selection and report snapshots remain B-Rep-backed through `ShapeReference` / `FeatureReference` ids, not PyVista/VTK or mesh-only ids.
- Final verification notes.

## Verification

```powershell
$env:PYTHONPATH="src"; python -m unittest discover -s tests
```

Primary viewer/runtime verification:

```powershell
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s -m unittest discover -s tests
```

Manual smoke:

```powershell
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s -m mechanical_design_tool_suite.cad_tolerance_gui
```

## Non-Goals

- No native commercial CAD import.
- No external CAD add-ins.
- No full installer polish if OCCT dependency packaging remains unresolved.

## Stop Condition

Stop when the end-to-end prototype path is launchable or the remaining blocker is documented with exact error output and the next engineering decision.
