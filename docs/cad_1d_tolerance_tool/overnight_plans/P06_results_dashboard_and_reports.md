# P06 Results Dashboard And Reports

## Summary

Implement dashboard result projection, contribution views, warnings, snapshots, and browser-style HTML reports.

## Worker Prompt

You are a `gpt-5.5` `xhigh` worker in `C:\Users\emre_\PycharmProjects\Mechanical_Design_Tool_Suite`. Your task is P06 Results Dashboard And Reports. Reread `overnight_plans/README.md`, `07_implementation_plan.md`, `02_requirements.md`, `03_ui_ux_design_spec.md`, `04_data_model_and_calculation_methods.md`, `06_verification_validation_plan.md`, and `extracted_specs/2026-05-12_eztol_targeted_visual_review.md` before editing. After every context compaction, reread those files and this packet. Use transcript timestamps `00:13:49-00:23:36` and targeted visual review sections for result/report behavior.

## Conservative Write Scope

- `src/mechanical_design_tool_suite/cad_tolerance_report.py`
- `cad_tolerance_viewmodels.py`
- `cad_tolerance_gui.py`
- `tests/test_cad_tolerance_report.py`
- Report template assets only if needed and independently authored

## Deliverables

- Summary table projection with pass/fail/warning states.
- Result bar or plot data models for worst-case/RSS/statistical views.
- Dashboard rollup badges for objectives met, objectives not met, and predicted/target sigma rollup.
- Contribution ranking view model.
- Non-1D warning display.
- HTML report generator with dark left nav, summary, snapshots, stackup table, result section, contribution section, and warning text matching the targeted visual review structure.

## Verification

```powershell
$env:PYTHONPATH="src"; python -m unittest tests.test_cad_tolerance_report
```

## Non-Goals

- No PDF export unless HTML is complete and deterministic.
- No browser automation requirement unless local verification is needed.

## Stop Condition

Stop when a fixture project can generate deterministic HTML and dashboard/contribution data models are tested.
