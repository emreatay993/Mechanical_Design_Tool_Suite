# P04 UI Shell And View Models

## Summary

Build the high-fidelity EZtol-style Qt desktop shell and model/view foundations.

## Worker Prompt

You are a `gpt-5.5` `xhigh` worker in `C:\Users\emre_\PycharmProjects\Mechanical_Design_Tool_Suite`. Your task is P04 UI Shell And View Models. Reread `overnight_plans/README.md`, `07_implementation_plan.md`, `02_requirements.md`, `03_ui_ux_design_spec.md`, and `extracted_specs/2026-05-12_eztol_targeted_visual_review.md` before editing. After every context compaction, reread those files and this packet. If uncertain about UI/UX, inspect the video viewer and targeted visual review key frames before choosing.

## Conservative Write Scope

- `src/mechanical_design_tool_suite/cad_tolerance_gui.py`
- `src/mechanical_design_tool_suite/cad_tolerance_viewmodels.py`
- `src/mechanical_design_tool_suite/data/` or `qml/assets/icons/` only if adding independent icons
- `tests/test_cad_tolerance_gui.py`
- `pyproject.toml` only for the new script entry point if the GUI module exists

## Deliverables

- Launchable Qt Widgets main window.
- Ribbon-like top tabs `Stackup`, `Report`, `Data`.
- Left assembly tree view.
- Center viewport host placeholder or adapter-host widget.
- Right summary/detail pane.
- Required summary columns: `OK`, `Name`, `Nominal`, `Objective`, `Target Quality`, `Results`, `Predicted Quality`, `#Dims`.
- Required detail columns: `Name`, `Sens`, `Nominal`, `Tolerance`, `Datum`.
- Results/contributions tab placeholders with correct visual structure.
- Observed row colors, badge structure, non-1D warning treatment, and open/import dialog structure from the targeted visual review.
- Fidelity gap notes for any small labels or symbols that remain unreadable.

## Verification

```powershell
$env:PYTHONPATH="src"; python -m unittest tests.test_cad_tolerance_gui
```

Manual verification should compare against `extracted_specs/2026-05-12_eztol_targeted_visual_review.md` and the referenced key frames.

## Non-Goals

- No full CAD picking workflow.
- No full report generation.

## Stop Condition

Stop when the app shell and model/view contracts exist, tests pass, and UI gaps are documented.
