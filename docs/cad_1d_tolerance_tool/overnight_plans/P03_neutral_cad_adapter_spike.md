# P03 Neutral CAD Adapter Spike

## Summary

Prove the neutral CAD import and geometry adapter boundary using OCCT. Use `pythonocc-core` only behind the adapter if it is the fastest workable path.

## Worker Prompt

You are a `gpt-5.5` `xhigh` worker in `C:\Users\emre_\PycharmProjects\Mechanical_Design_Tool_Suite`. Your task is P03 Neutral CAD Adapter Spike. Reread `overnight_plans/README.md`, `07_implementation_plan.md`, `02_requirements.md`, `05_architecture_and_persistence.md`, and `08_primary_cad_viewer_plan.md` before editing. After every context compaction, reread those files and this packet. If `pythonocc-core` blocks progress, document the blocker and leave the API stable enough for a C++ OCCT adapter.

## Conservative Write Scope

- `src/mechanical_design_tool_suite/cad_geometry_api.py`
- `src/mechanical_design_tool_suite/cad_geometry_occ.py`
- `tests/test_cad_geometry_api.py`
- `tests/fixtures/` for small neutral CAD fixtures or fixture README
- Optional dependency notes in `pyproject.toml` only if validated

## Deliverables

- Kernel-neutral geometry API.
- OCCT-backed import attempt for STEP and IGES.
- Assembly/shape traversal enough to populate an assembly browser.
- Shape/feature reference extraction for bodies, faces, edges, vertices where available.
- Live OCCT shape access behind the adapter for the future PyQt6 AIS/V3d viewer; do not expose viewer handles or add UI code in P03.
- Basic measurement helpers for planar and cylindrical feature pairs.
- Tests that skip clearly when optional CAD dependency is unavailable.

## Verification

```powershell
$env:PYTHONPATH="src"; python -m unittest tests.test_cad_geometry_api
```

## Non-Goals

- No native commercial CAD import.
- No direct PMI interpretation.
- No production topological naming solution.
- No full UI.

## Stop Condition

Stop when the adapter boundary is clear and either imports neutral fixtures or documents a concrete dependency blocker with the next technical path.
