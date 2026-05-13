# P04A Primary CAD Viewer Spike

## Summary

Prove the final-product CAD viewer direction: OCCT AIS/V3d embedded in PyQt6, fed by live OCCT B-Rep shapes from the P03 geometry adapter.

## Worker Prompt

You are a `gpt-5.5` `xhigh` worker in `C:\Users\emre_\PycharmProjects\Mechanical_Design_Tool_Suite`. Your task is P04A Primary CAD Viewer Spike. Reread `overnight_plans/README.md`, `07_implementation_plan.md`, `02_requirements.md`, `03_ui_ux_design_spec.md`, `05_architecture_and_persistence.md`, `06_verification_validation_plan.md`, `08_primary_cad_viewer_plan.md`, and `extracted_specs/2026-05-12_eztol_targeted_visual_review.md` before editing. After every context compaction, reread those files and this packet.

Use `environment-cad312.yml` or an equivalent Python 3.12 runtime with `pythonocc-core 7.9.3=*novtk*`, NumPy 1.26, and PyQt6. The viewer must call `OCC.Display.backend.load_backend("pyqt6")` before importing `OCC.Display.qtDisplay.qtViewer3d`.

## Conservative Write Scope

- `src/mechanical_design_tool_suite/cad_viewer_api.py`
- `src/mechanical_design_tool_suite/cad_viewer_occ.py`
- `src/mechanical_design_tool_suite/cad_tolerance_gui.py` only for a minimal host or smoke entry point
- `tests/test_cad_viewer*.py`
- `docs/cad_1d_tolerance_tool/` for viewer spike notes only if needed

## Deliverables

- Minimal PyQt6 viewer widget using `load_backend("pyqt6")`, `qtViewer3d`, and OCCT AIS/V3d.
- Display of at least one imported STEP fixture from `OccCadGeometrySession`.
- A viewer API boundary for camera state, selection events, highlight roles, and snapshot requests.
- Mapping plan or prototype from displayed AIS objects back to serializable `ShapeReference.id` values.
- Fit all, pan, zoom, orbit, and shaded display basics where available through pythonocc.
- Verification that PyQt5/Qt5 is not imported or installed into the primary CAD runtime.
- Documented blocker with exact error output if the PyQt6 `qtViewer3d` path fails.

## Verification

```powershell
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s -m unittest discover -s tests -p "test_cad_viewer*.py"
```

Also run a manual smoke harness that imports and displays `tests/fixtures/cad_1d_tolerance/neutral_step_two_part_loop.step` as nonblank shaded geometry.

## Non-Goals

- No full guided stackup workflow.
- No production annotation editing.
- No native commercial CAD import.
- No PyVista/VTK or mesh-only primary viewer fallback.
- No C++ fallback implementation unless pythonocc is proven unusable and the blocker is documented.

## Stop Condition

Stop when the fixture displays through a PyQt6 AIS/V3d viewer with a stable API boundary, or when an exact blocker is documented with the next engineering path to a C++ Qt6 + OCCT viewport adapter.
