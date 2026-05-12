# P02 Project Persistence

## Summary

Add versioned `.tolproj` JSON persistence for CAD 1D tolerance projects.

## Worker Prompt

You are a `gpt-5.5` `xhigh` worker in `C:\Users\emre_\PycharmProjects\Mechanical_Design_Tool_Suite`. Your task is P02 Project Persistence. Reread `overnight_plans/README.md`, `07_implementation_plan.md`, `04_data_model_and_calculation_methods.md`, `05_architecture_and_persistence.md`, and P01 outputs before editing. After every context compaction, reread those files and this packet.

## Conservative Write Scope

- `src/mechanical_design_tool_suite/cad_tolerance_project_io.py`
- `tests/test_cad_tolerance_project_io.py`
- Fixture JSON files under `tests/fixtures/` if useful
- Minimal docs updates under `docs/cad_1d_tolerance_tool/`

## Deliverables

- Save/load functions for `project_type = "cad_1d_tolerance"`.
- Schema version field and migration hook.
- Round-trip support for CAD source metadata, stackups, contributors, manual GD&T rows, settings, warnings, snapshots, and report metadata.
- Tests for round-trip, missing fields, invalid schema, and forward-compatible unknown fields where appropriate.

## Verification

```powershell
$env:PYTHONPATH="src"; python -m unittest tests.test_cad_tolerance_project_io
```

## Non-Goals

- No CAD kernel import.
- No GUI.

## Stop Condition

Stop when a fixture project round-trips and P01 domain objects remain independent of Qt/OCCT.
