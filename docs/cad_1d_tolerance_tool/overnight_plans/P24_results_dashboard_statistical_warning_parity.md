# P24 Results Dashboard Statistical Warning Parity

## Summary

Match the demo's worst-case, RSS, statistical, dashboard, non-1D warning, sigma rollup, and contribution visuals and semantics.

## Worker Prompt

You are a `gpt-5.5` `xhigh` worker in `C:\Users\emre_\PycharmProjects\Mechanical_Design_Tool_Suite`. Your task is P24 Results Dashboard Statistical Warning Parity. Work on branch `codex/p24-results-dashboard`, based from P23 if it has landed; otherwise base from the planning baseline and keep table API changes minimal.

Reread `overnight_plans/README.md`, `10_full_clone_productization_plan.md`, `02_requirements.md`, `03_ui_ux_design_spec.md`, `04_data_model_and_calculation_methods.md`, targeted visual review sections `00:12:00-00:21:54`, transcript `00:13:49-00:22:09`, frames `023`, `024`, `030-036`, `040-046`, `057`, `058`, and this packet before editing. After every context compaction, reread those files and this packet.

## Conservative Write Scope

- `src/mechanical_design_tool_suite/cad_tolerance_methods.py`
- `src/mechanical_design_tool_suite/cad_tolerance_viewmodels.py`
- `src/mechanical_design_tool_suite/cad_tolerance_gui.py`
- Focused calculation/viewmodel/GUI tests
- `docs/cad_1d_tolerance_tool/` for evidence notes

## Deliverables

- Worst-case and RSS result bars with requirement/result markers matching demo semantics.
- Statistical quality panel with compact green bell curve, limit markers, Cpk/Cp/Sigma/Yield display modes where supported, and two-way target-vs-achieved interpretation.
- Dashboard summary rows and rollup badges matching observed columns and colors.
- Non-1D warning heuristics and user-facing warning presentation based on evidence, with thresholds documented when inferred.
- Contribution ranking view with blue bars, percentages, row selection, and shared-dimension interactions.
- Updated tests for all result modes and status colors/states.

## Verification

```powershell
$env:PYTHONPATH="src"; python -m unittest tests.test_cad_tolerance_domain tests.test_cad_tolerance_gui tests.test_cad_tolerance_report
```

## Non-Goals

- No full 3D solving.
- No angular deviation calculation.
- No thermal expansion.
- No CETOL animation.

## Stop Condition

Stop when users can interpret pass/fail/statistical/non-1D/contribution states the way the demo explains them, with unresolved statistical menu labels documented rather than guessed.

## 2026-05-16 Implementation Evidence

- Implemented computed non-1D warning heuristics in stackup calculation for lateral feature offsets, weak direction alignment, rotational constraints, multi-interface loops, and sensitive projected contributors. Persisted warning rows are preserved and deduplicated against computed warnings.
- Preserved objective/quality failure precedence: failed objectives still show `FAIL`; warning-only passing stackups show `WARN`; empty stackups remain `INCOMPLETE`.
- Added statistical result display fields for Cp, Cpk, Sigma, Yield, actual-at-objective quality, and target-quality result envelope. The PyQt statistical plot now uses the calculated standard deviation for the compact green bell curve and marks target-result limits distinctly from objective limits.
- Updated dashboard row treatment so warning rows receive visible warning coloring/icon treatment while passing warning rows still count as objectives met; incomplete rows no longer count as met.
- Updated contribution interactions so selecting a blue contribution bar selects the matching contributor row, highlights the contribution row, and reports affected shared stackups.
- Verification run: `$env:PYTHONPATH="src"; python -m unittest tests.test_cad_tolerance_domain tests.test_cad_tolerance_gui tests.test_cad_tolerance_report` passed, 44 tests.
- Regression run: `$env:PYTHONPATH="src"; python -m unittest discover -s tests` passed, 155 tests with 7 skips. `git diff --check` passed with only Git line-ending warnings.

Remaining fidelity notes:

- Statistical submenu labels beyond `Worst Case`, `RSS`, and `Statistical` remain unresolved in the source evidence and are intentionally not invented.
- Non-1D thresholds are the documented configurable engineering thresholds in `AnalysisSettings`; they warn only and do not attempt CETOL-level 3D solving, angular deviation, thermal expansion, or animation.
