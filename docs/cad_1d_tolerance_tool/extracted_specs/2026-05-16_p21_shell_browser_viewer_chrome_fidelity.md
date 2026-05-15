# P21 Shell Browser Viewer Chrome Fidelity Evidence

Date: 2026-05-16

## Scope

This P21 pass updates only the main Qt shell, model browser chrome, viewport overlay chrome, and QSS/style treatment. Calculation semantics and report templates were not changed.

## Demo Evidence

- Frame `005`: `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-12/key_frames/005_00-04-10_main_workspace_after_import.jpg`
- Frame `006`: `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-12/key_frames/006_00-04-35_file_actions_snapshots_reports.jpg`
- Design lock: `docs/cad_1d_tolerance_tool/extracted_specs/2026-05-15_p19_evidence_crops_and_design_system_lock.md`

## Captured Current Evidence

Folder: `docs/cad_1d_tolerance_tool/extracted_specs/2026-05-16_p21_shell_browser_viewer_chrome_fidelity/`

| File | Purpose |
| --- | --- |
| `p21_sample_project_shell_grab.png` | Full Qt shell grab after loading `sample_cad_1d_project.tolproj`. Shows `File` / `Tolerance Stackup` / `View` ribbon, grouped `Stackup` / `Report` / `Data` commands, compact model browser controls, viewport chrome, right summary pane, result tabs, and status counters. |
| `p21_sample_project_viewport.png` | Viewer snapshot exported through `CadViewportHost.capture_snapshot`, proving the runtime viewport snapshot path remains nonblank. |
| `p21_sample_project_shell_summary.json` | Screenshot metadata, ribbon tab names, viewer class, displayed shape count, and sampled image-color checks. |

## Comparison Notes

- Ribbon: matches frames `005` and `006` structurally with `File`, `Tolerance Stackup`, and `View` tabs. The selected `Tolerance Stackup` page exposes grouped `Stackup`, `Report`, and `Data` commands, including disabled `Add Feature` and `Generate Report`.
- Model browser: keeps the dense left dock with `Model` header, help/close affordances, filter, assembly-view, find controls, selection styling, and XDE/display-name tree data from the loaded project.
- Viewport chrome: replaces placeholder text controls with a painted orientation cube, painted axis triad, and icon-only vertical navigation toolbar. The known full-window native OCCT compositor caveat remains; the separate viewport snapshot is the authoritative nonblank viewer proof.
- Splitters/status: uses P19 proportions for left browser, central viewport, and right analysis pane, plus a thin status bar with permanent count fields.

## Verification

```powershell
$env:PYTHONPATH="src"; python -m unittest tests.test_cad_tolerance_gui
```

Result: passed, 19 tests.

```powershell
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s -m unittest tests.test_cad_viewer_api tests.test_cad_tolerance_gui
```

Result: passed, 25 tests.

```powershell
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s tests\scripts\cad_1d_runtime_smoke.py tests\fixtures\cad_1d_tolerance\sample_cad_1d_project.tolproj --output-dir docs\cad_1d_tolerance_tool\extracted_specs\2026-05-16_p21_shell_browser_viewer_chrome_fidelity --prefix p21_sample_project --settle-ms 1800
```

Result: runtime gate passed with `OccCadViewerWidget`, 2 displayed B-Rep shapes, and no gate failures. Its desktop-region full-window capture was not retained because this desktop had another foreground window; `p21_sample_project_shell_grab.png` is the retained shell evidence.

## Remaining Differences

- The fixture project uses a small neutral STEP loop, not the full demo caster assembly, so the model browser hierarchy and live viewport geometry cannot visually match frame `005` part-for-part.
- Native OCCT child-window compositing can still appear black in Qt widget grabs on this machine. The viewport export remains nonblank and is kept as the runtime evidence.
- Independent MDTS branding is intentionally retained.
