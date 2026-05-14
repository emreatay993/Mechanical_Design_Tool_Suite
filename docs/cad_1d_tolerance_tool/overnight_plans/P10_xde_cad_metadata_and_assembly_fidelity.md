# P10 XDE CAD Metadata And Assembly Fidelity

## Summary

Improve neutral CAD import fidelity by using OCCT XDE/STEPCAF/XCAF metadata where available, so the model browser and report use real assembly names, colors, and hierarchy instead of synthetic bodies.

## Worker Prompt

You are a `gpt-5.5` `xhigh` worker in `C:\Users\emre_\PycharmProjects\Mechanical_Design_Tool_Suite`. Your task is P10 XDE CAD Metadata And Assembly Fidelity. Reread `overnight_plans/README.md`, `09_full_clone_gap_closure_plan.md`, `05_architecture_and_persistence.md`, `08_primary_cad_viewer_plan.md`, P08 outputs if present, and this packet before editing. After every context compaction, reread those files and this packet.

Use official OCCT XDE concepts for STEP/IGES names, colors, layers, validation properties, and assembly structure. Keep all OCCT usage behind `cad_geometry_api.py` / `cad_geometry_occ.py`.

## Conservative Write Scope

- `src/mechanical_design_tool_suite/cad_geometry_api.py`
- `src/mechanical_design_tool_suite/cad_geometry_occ.py`
- `src/mechanical_design_tool_suite/cad_tolerance_models.py` only for serializable metadata fields
- `tests/test_cad_geometry_api.py`
- `tests/fixtures/cad_1d_tolerance/`
- Fixture README updates

## Deliverables

- XDE-aware import path for STEP and IGES when OCCT modules are available.
- Assembly tree with preserved product/part/instance names where the neutral file contains them.
- Color metadata propagated to `CadDocument`/`AssemblyNode` and viewer display.
- Deterministic fallback names when metadata is absent.
- Stable mapping from XDE labels/shapes to `ShapeReference` and `FeatureReference` ids.
- Hash/source metadata unchanged and `.tolproj` compatibility preserved.
- Tests using caster STEP and small neutral fixtures in `mdts-cad312`.

## Evidence Targets

- Demo assembly browser entries such as `top_plate:1`, `axle_support:1`, `bushing:1`, `wheel:1`, repeated parts, `Relationships`, `Representations`, and `Origin`.
- Imported model colors in the caster assembly.

## Verification

```powershell
$env:PYTHONPATH="src"; python -m unittest tests.test_cad_geometry_api
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s -m unittest tests.test_cad_geometry_api
```

## Non-Goals

- No native `.CATPart`, `.CATProduct`, `.SLDASM`, Inventor, NX, Creo, JT, or direct CAD add-in import.
- No topology naming guarantee across arbitrary revised CAD files beyond documented best effort.

## Stop Condition

Stop when neutral STEP/IGES imports expose the best available assembly/name/color metadata while keeping the adapter replaceable.
