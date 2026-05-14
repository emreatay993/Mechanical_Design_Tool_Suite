# P12 Guided Workflow Completion

## Summary

Complete the in-canvas guided stackup workflow so users can create and refine stackups from CAD selections with the same sequence, prompts, counters, and controls shown in the demo.

## Worker Prompt

You are a `gpt-5.5` `xhigh` worker in `C:\Users\emre_\PycharmProjects\Mechanical_Design_Tool_Suite`. Your task is P12 Guided Workflow Completion. Reread `overnight_plans/README.md`, `09_full_clone_gap_closure_plan.md`, P08/P09/P10/P11 outputs if present, the targeted visual review, and this packet before editing. After every context compaction, reread those files and this packet.

Use transcript/video evidence `00:04:55-00:10:55`, key frames `007-023`, and five-second sheets `003-005`.

## Conservative Write Scope

- `src/mechanical_design_tool_suite/cad_stackup_workflow.py`
- `src/mechanical_design_tool_suite/cad_tolerance_gui.py`
- `src/mechanical_design_tool_suite/cad_tolerance_viewmodels.py` only for workflow-facing updates
- `src/mechanical_design_tool_suite/cad_viewer_api.py` only for selection/highlight protocol gaps
- `tests/test_cad_stackup_workflow.py`
- `tests/test_cad_tolerance_gui.py`

## Deliverables

- Floating mini-toolbar states: `Selection 1`, `Width 1`, `Selection 2`, `Width 2`, `Direction`, `Analysis Plane`, `Dimension Location`, loop components, mating faces.
- Green check, red X, plus/add, dropdown/list controls wired to workflow actions.
- Prompt text matching the demo where legible.
- Loop component counters such as `1 Components`, `5 Components`, `6 of 8 Mating Faces`.
- Selection filtering by current part, expected shape kind, and stackup direction.
- Direction and analysis plane persisted in stackup/annotation state.
- Add Feature flow that inserts intermediate features and preserves reused part dimension schemes.
- Deterministic contributor generation from selected features with clear warnings where automatic mate inference is not implemented.

## Verification

```powershell
$env:PYTHONPATH="src"; python -m unittest tests.test_cad_stackup_workflow tests.test_cad_tolerance_gui
$env:PYTHONPATH="src"; python -m unittest discover -s tests
```

Manual smoke with caster STEP in `mdts-cad312` is required if viewer wiring changes.

## Non-Goals

- No full automatic native CAD mate graph import.
- No hidden dependence on commercial CAD constraints.
- No new CAD formats.

## Stop Condition

Stop when the guided stackup flow can be exercised end-to-end from the GUI without tests mutating controller internals directly.
