# P07 Integration Fidelity Packaging

## Summary

Integrate the first end-to-end CAD 1D tolerance clone path, perform a visual fidelity review, and document packaging/dependency risks.

## Worker Prompt

You are a `gpt-5.5` `xhigh` worker in `C:\Users\emre_\PycharmProjects\Mechanical_Design_Tool_Suite`. Your task is P07 Integration Fidelity Packaging. Reread `overnight_plans/README.md`, all numbered CAD docs, `extracted_specs/2026-05-12_eztol_targeted_visual_review.md`, and all completed packet notes before editing. After every context compaction, reread those files and this packet. If uncertain about UI fidelity, inspect the local viewer and targeted visual review key frames before changing the UI.

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
- Packaging/dependency notes for OCCT binding choice.
- Final verification notes.

## Verification

```powershell
$env:PYTHONPATH="src"; python -m unittest discover -s tests
```

Manual smoke:

```powershell
$env:PYTHONPATH="src"; python -m mechanical_design_tool_suite.cad_tolerance_gui
```

## Non-Goals

- No native commercial CAD import.
- No external CAD add-ins.
- No full installer polish if OCCT dependency packaging remains unresolved.

## Stop Condition

Stop when the end-to-end prototype path is launchable or the remaining blocker is documented with exact error output and the next engineering decision.
