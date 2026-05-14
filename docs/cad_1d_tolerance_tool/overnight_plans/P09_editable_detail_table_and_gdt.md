# P09 Editable Detail Table And GD&T

## Summary

Make the stackup detail table behave like the spreadsheet-style editor in the demo, including inline tolerance edits, tolerance type changes, datum fields, manual GD&T/GPS contributor entry, and immediate recalculation.

## Worker Prompt

You are a `gpt-5.5` `xhigh` worker in `C:\Users\emre_\PycharmProjects\Mechanical_Design_Tool_Suite`. Your task is P09 Editable Detail Table And GD&T. Reread `overnight_plans/README.md`, `09_full_clone_gap_closure_plan.md`, all numbered CAD docs, P08 outputs if present, the targeted visual review, and this packet before editing. After every context compaction, reread those files and this packet.

Use video evidence around `00:07:05-00:13:55`, key frames `014-029`, and the transcript sections for linear tolerance editing and GD&T/GPS entry.

## Conservative Write Scope

- `src/mechanical_design_tool_suite/cad_tolerance_models.py`
- `src/mechanical_design_tool_suite/cad_tolerance_methods.py`
- `src/mechanical_design_tool_suite/cad_tolerance_viewmodels.py`
- `src/mechanical_design_tool_suite/cad_tolerance_gui.py`
- `tests/test_cad_tolerance_domain.py`
- `tests/test_cad_tolerance_gui.py`
- New focused tests if needed, such as `tests/test_cad_tolerance_editing.py`

## Deliverables

- Editable `Name`, `Nominal`, `Tolerance`, `Datum`, and tolerance-type fields where appropriate.
- Qt model `flags()` / `setData()` behavior with validation and user-visible rejection status.
- Delegates or compact controls for symmetric, limits/asymmetric, and geometric/manual tolerance modes.
- Manual `Add Geometric Tolerance` dialog with controlled feature, GD&T symbol/type selector, tolerance value, datum/reference input, disabled OK until valid, OK/Cancel behavior.
- Support for runout, position, profile-equivalent/manual geometric contributors shown in the demo.
- Datum feature rows such as `A` and GD&T rows that survive `.tolproj` save/load.
- Immediate recalculation and dashboard/detail update after edits.
- Shared-dimension impact messaging when an edited contributor affects multiple stackups.

## Evidence Targets

- Detail columns: `Name`, `Sens`, `Nominal`, `Tolerance`, `Datum`.
- Rows like `bushing:2`, `Hole1`, `Dimension1`, `Shaft2`, `axle_support:2`, `Face5`, `Dimension3`.
- Linear edits: `+/-0.05`, `58.000 +/-0.075`, `+/-0.25`.
- GD&T examples: runout `0.1` to datum `A`, position `0.15` to datum `A`, profile-equivalent `0.5`.

## Verification

```powershell
$env:PYTHONPATH="src"; python -m unittest tests.test_cad_tolerance_domain tests.test_cad_tolerance_gui
$env:PYTHONPATH="src"; python -m unittest discover -s tests
```

## Non-Goals

- No automatic native PMI/GD&T import.
- No native CAD add-ins.
- No viewer annotation implementation beyond table/dialog wiring.

## Stop Condition

Stop when a loaded fixture project can be edited through the detail table/dialog and recalculates results without direct object mutation in tests.
