# P17 Visual Evidence Closeout

## Summary

Capture current CAD 1D tolerance UI/report screenshots, compare them directly against the EZtol demo key frames identified by P16, and make only tightly scoped fidelity fixes that are supported by visual evidence. This packet exists because P16 confirmed that the clone is functionally broad but still visually different from the demo in layout density, icon/ribbon treatment, live screenshot proof, report comparison, and unresolved small labels.

## Worker Prompt

You are a `gpt-5.5` `xhigh` worker in `C:\Users\emre_\PycharmProjects\Mechanical_Design_Tool_Suite`. Your task is P17 Visual Evidence Closeout. Reread `overnight_plans/README.md`, `09_full_clone_gap_closure_plan.md`, all numbered CAD docs, `extracted_specs/2026-05-14_full_clone_gap_matrix.md`, `extracted_specs/2026-05-15_final_fidelity_audit_and_roadmap.md`, the targeted visual review, the full video context pack, and this packet before editing. After every context compaction, reread those files and this packet.

Use the current implementation as the comparison subject. Do not assume automated tests imply visual fidelity. Launch or render the actual CAD tool/report where feasible, capture screenshots, compare them against the source demo frames, and document the exact visible differences before changing UI code.

## Conservative Write Scope

- `docs/cad_1d_tolerance_tool/`
- `src/mechanical_design_tool_suite/cad_tolerance_gui.py` only for small, evidence-backed visual polish
- `src/mechanical_design_tool_suite/cad_tolerance_viewmodels.py` only for table/display text or row decoration polish
- `src/mechanical_design_tool_suite/cad_tolerance_report.py` only for report visual parity fixes
- `src/mechanical_design_tool_suite/cad_viewer_api.py` / `cad_viewer_occ.py` only for minor overlay/snapshot visual fixes
- Focused GUI/report/viewer tests only when a code change is made
- Optional screenshot helper under `tests/scripts/` or `scripts/` if it reduces manual steps and does not destabilize runtime tests

## Deliverables

- A dated visual evidence closeout note under `docs/cad_1d_tolerance_tool/extracted_specs/`.
- Captured current screenshots for:
  - main workspace after opening/importing a CAD fixture
  - guided stackup/detail table view
  - result/statistical/dashboard view
  - generated browser report summary
  - generated browser report annotated stackup/contribution section
- Side-by-side or table-form comparison notes against key frames `005`, `019`, `033`, `049`, and `051`.
- A visible-difference list split into:
  - fixed in P17
  - still partial
  - unresolved because source labels/glyphs are unreadable
  - intentionally different because of independent branding or P0 scope
- Small UI/report polish fixes where the correct target is unambiguous from the evidence.
- Updated P16/P08 references only if P17 changes a status with real implementation evidence.

## Evidence Targets

- `005_00-04-10_main_workspace_after_import.jpg`: ribbon density, model browser, central light-gray viewport, right summary pane, axis triad, ViewCube, navigation toolbar, result tabs.
- `019_00-09-05_tolerance_type_dropdown.jpg`: detail table density, selected row/cell styling, tolerance dropdown structure. Exact dropdown labels remain unresolved unless fresh crops prove them.
- `033_00-15-18_statistical_quality_bell_curve.jpg`: statistical result title, Cpk/mean/std-dev text, green bell curve, red/black limits, non-1D warning placement.
- `049_00-22-55_browser_report_open.jpg`: dark fixed report nav, white report canvas, report title/snapshot layout, summary/dashboard mirroring.
- `051_00-23-38_report_contribution_section.jpg`: annotated caster image, blue contributor dimensions, red result dimension, report table/section spacing.

## Required Visual Review Steps

1. Inspect the source demo frames listed above and cite them in the P17 closeout note.
2. Launch or render the current tool/report using committed fixtures. Prefer `mdts-cad312` for CAD viewport work.
3. Capture screenshots with stable filenames under a dated evidence folder.
4. Compare screenshot dimensions, pane structure, typography density, colors, toolbar/icon arrangement, table rows, and report layout.
5. Make only small fixes where the target is obvious. If a visual difference needs larger design work, record it as a follow-up instead of forcing it into P17.
6. Preserve independent branding. Do not copy EZtol/Sigmetrix marks.

## Verification

Documentation-only minimum:

```powershell
git diff --check
```

If UI/report/viewer code changes:

```powershell
$env:PYTHONPATH="src"; python -m unittest tests.test_cad_tolerance_gui tests.test_cad_tolerance_report tests.test_cad_viewer_api
$env:PYTHONPATH="src"; python -m unittest discover -s tests
```

CAD-runtime verification:

```powershell
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s -m unittest discover -s tests
```

If the full CAD-runtime discovery crashes on unrelated native Qt/OCCT ordering, run and report the focused commands split by subsystem:

```powershell
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s -m unittest tests.test_cad_geometry_api tests.test_cad_viewer_api
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s -m unittest tests.test_cad_tolerance_gui tests.test_cad_stackup_workflow tests.test_cad_tolerance_report
```

Manual visual smoke:

```powershell
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s -m mechanical_design_tool_suite.cad_tolerance_gui "tests\fixtures\cad_1d_tolerance\caster_whell_v0\caster_wheel.stp"
```

## Non-Goals

- No native commercial CAD import.
- No CAD add-ins.
- No automatic native PMI import.
- No full 3D tolerance solving, angular deviation calculation, thermal expansion, or CETOL-style animation.
- No broad UI redesign or framework change.
- No proprietary logos, names, or assets.
- No C++ Qt6 + OCCT viewport spike unless the visual smoke exposes a concrete pythonocc blocker that cannot be isolated.

## Stop Condition

Stop when a future agent or human can open the P17 evidence note and see why the current program visually differs from the demo, which differences were fixed, and which remaining differences are deliberate, unreadable-source gaps, or explicit P18+ work.
