# P16 Final Fidelity Audit And Roadmap

## Summary

Perform a final clone-fidelity audit after P08-P15, compare the implementation against the full video-derived requirement set, and leave a precise roadmap for anything still missing.

## Worker Prompt

You are a `gpt-5.5` `xhigh` worker in `C:\Users\emre_\PycharmProjects\Mechanical_Design_Tool_Suite`. Your task is P16 Final Fidelity Audit And Roadmap. Reread `overnight_plans/README.md`, `09_full_clone_gap_closure_plan.md`, all numbered CAD docs, P08-P15 outputs, the targeted visual review, and this packet before editing. After every context compaction, reread those files and this packet.

Use the whole video context pack. If any UI/UX detail is uncertain, inspect the local viewer, key frames, five-second sheets, and fresh full-pass sheets before deciding. If the label remains unreadable, document it as an unresolved crop requirement rather than inventing detail.

## Conservative Write Scope

- `docs/cad_1d_tolerance_tool/`
- Focused tests for acceptance gaps only
- Minimal code polish only if it is clearly required to close a documented fidelity gap and does not overlap with another active packet

## Deliverables

- Final dated coverage matrix with `met`, `partial`, `missing`, `out_of_scope`, and `roadmap` statuses.
- Screenshot/report comparison notes against key frames and contact sheets.
- Exact list of unresolved unreadable labels/glyphs needing new crops.
- List of demo capabilities intentionally not implemented and why.
- If needed, a P17+ packet proposal for remaining roadmap items.
- Final recommendation on whether PyQt6 + OCCT remains sufficient or whether a small C++ Qt6 + OCCT viewport component is warranted.

## Required Validation Scenarios

- Launch/open/import STEP and IGES.
- Load `.tolproj` with existing source, missing source, project-local assets, and `.tolpack`.
- Guided stackup creation through the UI.
- Inline tolerance edit and GD&T dialog.
- Dashboard pass/fail/warning and multi-stackup drilldown.
- Contributions view and shared-dimension markers.
- Snapshot and report generation.
- Suite launcher and direct CAD GUI launch.

## Verification

```powershell
$env:PYTHONPATH="src"; python -m unittest discover -s tests
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s -m unittest discover -s tests
```

If full CAD-runtime discovery is blocked by unrelated tests, run and report the focused CAD command set explicitly:

```powershell
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s -m unittest tests.test_cad_geometry_api tests.test_cad_viewer_api tests.test_cad_tolerance_gui tests.test_cad_stackup_workflow tests.test_cad_tolerance_report
```

## Non-Goals

- No new feature implementation unless needed for final audit closure.
- No hiding or softening unresolved gaps.
- No scope expansion into commercial CAD import or full 3D tolerance solving.

## Stop Condition

Stop when a future agent or human can see exactly how close the product is to the demo and what remains to reach the 95% fidelity objective.
