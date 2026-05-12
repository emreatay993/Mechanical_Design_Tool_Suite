# P01 Domain Models And Calculations

## Summary

Implement pure Python domain models and calculation functions for CAD 1D tolerance stackups.

## Worker Prompt

You are a `gpt-5.5` `xhigh` worker in `C:\Users\emre_\PycharmProjects\Mechanical_Design_Tool_Suite`. Your task is P01 Domain Models And Calculations. Reread `overnight_plans/README.md`, `07_implementation_plan.md`, `02_requirements.md`, and `04_data_model_and_calculation_methods.md` before editing. After every context compaction, reread those files and this packet.

## Conservative Write Scope

- `src/mechanical_design_tool_suite/cad_tolerance_models.py`
- `src/mechanical_design_tool_suite/cad_tolerance_methods.py`
- `tests/test_cad_tolerance_domain.py`
- Minimal docs updates under `docs/cad_1d_tolerance_tool/` if implementation decisions need recording

## Deliverables

- Dataclasses/enums for CAD documents, assembly nodes, shape/feature references, stackup requirements, contributors, GD&T rows, results, warnings, and snapshots.
- Worst-case, RSS, quality metric placeholder/implementation, contribution ranking, and non-1D warning data structures.
- Deterministic unit tests covering symmetric and asymmetric tolerances, sensitivity signs, contribution ordering, empty stackups, and objective pass/fail.

## Verification

```powershell
$env:PYTHONPATH="src"; python -m unittest tests.test_cad_tolerance_domain
```

## Non-Goals

- No CAD import.
- No Qt UI.
- No report rendering.

## Stop Condition

Stop when the pure domain/calculation layer is tested and can be imported without optional CAD or Qt dependencies.
