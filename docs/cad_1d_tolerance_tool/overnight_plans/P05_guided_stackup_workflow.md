# P05 Guided Stackup Workflow

## Summary

Implement guided stackup authoring: endpoint selection, direction, annotation plane, loop parts, constraints, and generated contributors.

## Worker Prompt

You are a `gpt-5.5` `xhigh` worker in `C:\Users\emre_\PycharmProjects\Mechanical_Design_Tool_Suite`. Your task is P05 Guided Stackup Workflow. Reread `overnight_plans/README.md`, `07_implementation_plan.md`, `02_requirements.md`, `03_ui_ux_design_spec.md`, `04_data_model_and_calculation_methods.md`, `08_primary_cad_viewer_plan.md`, and `extracted_specs/2026-05-12_eztol_targeted_visual_review.md` before editing. After every context compaction, reread those files and this packet. Use transcript timestamps `00:04:55-00:10:36` and visual review sections for workflow order.

## Conservative Write Scope

- New workflow controller module if needed, such as `cad_stackup_workflow.py`
- `cad_tolerance_viewmodels.py`
- `cad_tolerance_gui.py`
- `cad_viewer_api.py` only for workflow-facing selection/highlight protocol changes
- Domain/calculation files only for small missing fields required by the workflow
- `tests/test_cad_stackup_workflow.py`

## Deliverables

- State machine for guided workflow steps.
- Selection-filter state for endpoints, direction, plane, parts, and constraints, expressed through B-Rep-backed viewer selections.
- Endpoint, direction, plane, part, and constraint picks must persist serializable `ShapeReference` / `FeatureReference` ids from the OCCT viewer path, never mesh-only ids or raw AIS/V3d/TopoDS handles.
- Role-based viewer highlight requests for start, end, direction, analysis plane, loop member, and warning roles.
- Mini-toolbar labels/counters matching the targeted visual review: `Selection 1`, `Width 1`, `Selection 2`, `Width 2`, `Direction`, `Analysis Plane`, `Dimension Location`, component count, mating-face count, green check, red X, plus/add, dropdown/list.
- Generated contributor rows from selected mock or real features.
- Manual insert intermediate feature action.
- Annotation placement state.
- Shared-dimension marker support.

## Verification

```powershell
$env:PYTHONPATH="src"; python -m unittest tests.test_cad_stackup_workflow
```

## Non-Goals

- No production automatic loop discovery.
- No full 3D tolerance solving.

## Stop Condition

Stop when the workflow can be exercised with fixture or mock features and updates contributor rows deterministically.
