# P11 Viewer Interaction And Annotations

## Summary

Make the OCCT AIS/V3d viewport behave like the demo CAD workspace: selection filters, hover/selection highlights, annotation graphics, ViewCube/axis/navigation affordances, and snapshot-ready overlays.

## Worker Prompt

You are a `gpt-5.5` `xhigh` worker in `C:\Users\emre_\PycharmProjects\Mechanical_Design_Tool_Suite`. Your task is P11 Viewer Interaction And Annotations. Reread `overnight_plans/README.md`, `09_full_clone_gap_closure_plan.md`, `08_primary_cad_viewer_plan.md`, P08/P10 outputs if present, the targeted visual review, and this packet before editing. After every context compaction, reread those files and this packet.

Use video evidence around `00:04:10-00:06:52`, `00:15:45-00:16:48`, key frames `005-013`, `034-036`, and five-second sheets `002-005`.

## Conservative Write Scope

- `src/mechanical_design_tool_suite/cad_viewer_api.py`
- `src/mechanical_design_tool_suite/cad_viewer_occ.py`
- `src/mechanical_design_tool_suite/cad_tolerance_gui.py` only for viewer host/toolbar/overlay wiring
- `tests/test_cad_viewer_api.py`
- `tests/scripts/cad_viewer_smoke.py`

## Deliverables

- B-Rep-backed body/face/edge/vertex selection filters exposed through the viewer API.
- Hover and selected highlight roles matching demo colors: green eligible, red active/selected, yellow warning/alternate where useful.
- Cross-highlighting from table row to model shape and model selection to table row.
- Draggable red stackup dimensions and blue contributor dimensions with leader lines/arrows and numeric labels such as `0.000`.
- Basic ViewCube/orientation widget, axis triad, and vertical navigation toolbar that remain visible and non-overlapping.
- Snapshot/export path that captures CAD viewport plus annotation overlays for reports.
- Clear fallback behavior if pythonocc cannot support a requested overlay natively.

## Verification

```powershell
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s -m unittest discover -s tests -p "test_cad_viewer*.py"
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s tests\scripts\cad_viewer_smoke.py
```

Manual smoke must open caster STEP and compare against the targeted visual review.

## Non-Goals

- No PyVista/VTK primary viewer.
- No mesh-only selection ids.
- No full 3D variation animation.

## Stop Condition

Stop when viewer interaction is B-Rep-backed, visibly closer to the demo, and report snapshots can include annotations.
