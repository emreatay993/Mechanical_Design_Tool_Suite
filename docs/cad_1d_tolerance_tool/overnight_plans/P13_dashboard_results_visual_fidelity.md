# P13 Dashboard Results Visual Fidelity

## Summary

Bring the summary dashboard, detail result panel, statistical displays, shared markers, and contributions view close to the demo presentation.

## Worker Prompt

You are a `gpt-5.5` `xhigh` worker in `C:\Users\emre_\PycharmProjects\Mechanical_Design_Tool_Suite`. Your task is P13 Dashboard Results Visual Fidelity. Reread `overnight_plans/README.md`, `09_full_clone_gap_closure_plan.md`, P08/P09/P12 outputs if present, the targeted visual review, and this packet before editing. After every context compaction, reread those files and this packet.

Use video evidence `00:10:55-00:16:48` and `00:19:40-00:21:54`, key frames `023-036` and `040-046`.

## Conservative Write Scope

- `src/mechanical_design_tool_suite/cad_tolerance_methods.py`
- `src/mechanical_design_tool_suite/cad_tolerance_viewmodels.py`
- `src/mechanical_design_tool_suite/cad_tolerance_gui.py`
- `src/mechanical_design_tool_suite/cad_tolerance_report.py` only for shared chart helpers if needed
- `tests/test_cad_tolerance_domain.py`
- `tests/test_cad_tolerance_gui.py`
- `tests/test_cad_tolerance_report.py`

## Deliverables

- Summary dashboard with observed columns, pass/fail/warning icons, pale red failing rows, pale blue selection rows, and `#Dims`.
- Large pass/fail/sigma badges for multi-stackup projects.
- Detail result panel for Worst Case, RSS, and Statistical modes.
- Red/green range bar with objective/result markers and labels.
- Statistical bell curve with mean, standard deviation, Cpk/Sigma/Yield labels where supported.
- Shared-dimension marker and tooltip listing affected stackups.
- Contributions tab with sorted blue horizontal bars and percentages.
- Non-1D warning presentation with yellow triangle and demo warning text.

## Verification

```powershell
$env:PYTHONPATH="src"; python -m unittest tests.test_cad_tolerance_domain tests.test_cad_tolerance_gui tests.test_cad_tolerance_report
$env:PYTHONPATH="src"; python -m unittest discover -s tests
```

Visual check must compare against key frames `031-046`.

## Non-Goals

- No full 3D CETOL solver.
- No thermal expansion.
- No exact proprietary statistical submenu labels unless legible from evidence.

## Stop Condition

Stop when the dashboard/result/contribution views can represent the full multi-stackup caster scenario with demo-like density and status language.
