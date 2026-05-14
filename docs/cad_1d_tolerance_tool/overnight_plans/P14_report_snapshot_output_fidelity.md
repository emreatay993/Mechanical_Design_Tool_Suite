# P14 Report Snapshot Output Fidelity

## Summary

Upgrade report generation and snapshot handling so generated output resembles the demo browser report, including annotated CAD images, dark navigation, summary/detail sections, result plots, and contribution plots.

## Worker Prompt

You are a `gpt-5.5` `xhigh` worker in `C:\Users\emre_\PycharmProjects\Mechanical_Design_Tool_Suite`. Your task is P14 Report Snapshot Output Fidelity. Reread `overnight_plans/README.md`, `09_full_clone_gap_closure_plan.md`, P08/P11/P13 outputs if present, the targeted visual review, and this packet before editing. After every context compaction, reread those files and this packet.

Use video evidence `00:22:09-00:23:38`, key frames `047-051`, and report sections in the targeted visual review.

## Conservative Write Scope

- `src/mechanical_design_tool_suite/cad_tolerance_report.py`
- `src/mechanical_design_tool_suite/cad_tolerance_gui.py`
- `src/mechanical_design_tool_suite/cad_tolerance_project_io.py` only for report/snapshot asset paths
- `src/mechanical_design_tool_suite/cad_viewer_api.py` only for snapshot metadata contract gaps
- `tests/test_cad_tolerance_report.py`
- `tests/test_cad_tolerance_project_io.py`

## Deliverables

- Report save flow that creates a portable report folder with deterministic assets.
- Dark left navigation with links to Summary and each stackup.
- White report canvas, title page, date/time metadata, summary dashboard table.
- Per-stackup result sections with plots matching in-app projections.
- Per-stackup contribution sections with blue bars.
- Annotated CAD snapshot images with dimensions/callouts when available.
- Report manifest entries persisted in `.tolproj`.
- No absolute machine-specific paths inside project-local report assets or `.tolpack`.

## Verification

```powershell
$env:PYTHONPATH="src"; python -m unittest tests.test_cad_tolerance_report tests.test_cad_tolerance_project_io
$env:PYTHONPATH="src"; python -m unittest discover -s tests
```

Manual report smoke should open generated `report.html` and compare against key frames `049-051`.

## Non-Goals

- No vendor branding.
- No requirement to generate PDF unless a later packet adds it.
- No browser automation requirement unless it is already available and useful.

## Stop Condition

Stop when a generated HTML report is useful as an engineering artifact and visually close to the demo report layout.
