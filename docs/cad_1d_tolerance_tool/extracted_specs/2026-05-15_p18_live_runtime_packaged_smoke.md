# P18 Live Runtime And Packaged Smoke

Date: 2026-05-15

Branch: `codex/cad1d-p18-live-runtime-packaged-smoke`

## Summary

P18 closed the launch/import/report/package smoke evidence gap for the CAD 1D tolerance tool where the current stack supports it. Source-runtime STEP, IGES, `.tolproj`, and generated `.tolpack` startup paths all loaded through the PyQt6 + OCCT runtime in `mdts-cad312`, rehydrated CAD sources where applicable, and produced nonblank OCCT viewport exports.

The packaged `Cad1DTolerance.exe` build completed with the existing PyInstaller configuration, and direct packaged executable runs with `.tolproj` and `.tolpack` arguments remained alive past the 10 second startup window.

The remaining blocker is specific and evidence-backed: full-window screenshots of the embedded native `qtViewer3d` viewport still show a black model area even when the same runtime session reports live displayed shapes and `ExportToImage` produces a nonblank shaded geometry snapshot. This reproduces the P17 native child-window capture/composition gap and is not a packaged-launch blocker.

## Evidence Folder

All command transcripts, generated runtime summaries, screenshots, report/package outputs, and packaged run logs are under:

`docs/cad_1d_tolerance_tool/extracted_specs/2026-05-15_p18_live_runtime_packaged_smoke/`

The reusable source smoke harness added for this pass is:

`tests/scripts/cad_1d_runtime_smoke.py`

## Pass / Fail / Blocker Table

| Scenario | Command / Evidence | Result | Notes |
| --- | --- | --- | --- |
| Source GUI runtime with STEP fixture | `source_step_runtime.log`, `source_step_runtime_summary.json`, `source_step_runtime_viewport.png`, `source_step_runtime_full_window.png` | PASS with blocker | Loaded `neutral_step_two_part_loop.step`; `OccCadViewerWidget`; `displayed_shape_count=2`; viewport export nonblank. Full-window native capture shows black model pane. |
| Source GUI runtime with IGES fixture | `source_iges_runtime.log`, `source_iges_runtime_summary.json`, `source_iges_runtime_viewport.png`, `source_iges_runtime_full_window.png` | PASS with blocker | Loaded `neutral_iges_single_part.igs`; `displayed_shape_count=1`; viewport export nonblank. Full-window native capture shows black model pane. |
| Source GUI runtime with committed `.tolproj` fixture | `source_tolproj_fixture_runtime.log`, `source_tolproj_fixture_runtime_summary.json`, `source_tolproj_fixture_runtime_viewport.png` | PASS with blocker | Loaded `tests/fixtures/cad_1d_tolerance/sample_cad_1d_project.tolproj`; status `Reloaded CAD source: neutral_step_two_part_loop.step`; viewport export nonblank. |
| Generate safe report/package smoke project | `report_tolpack_generation.log`, `p18_runtime_project/p18_runtime_project.tolproj`, `p18_runtime_project/p18_runtime_project_assets/reports/report.html` | PASS | Generated report assets and project-local CAD asset beside a safe P18 `.tolproj`. |
| Export generated `.tolpack` | `report_tolpack_generation.log`, `p18_runtime_project/p18_runtime_project.tolpack` | PASS | Zip entries include `assets/cad/neutral_step_two_part_loop.step`, report CSS/JS/HTML/manifest, `manifest.json`, and `project.tolproj`; manifest check reported `contains_abs_repo_path=False`. |
| Export committed sample `.tolproj` directly | `tolpack_export_attempt.log` | EXPECTED FAIL | The committed fixture references missing `snapshots/bushing_alignment.png`; this is why P18 generated a safe package fixture instead of mutating the sample. |
| Source GUI runtime with generated `.tolproj` | `source_tolproj_runtime.log`, `source_tolproj_runtime_summary.json`, `source_tolproj_runtime_viewport.png` | PASS with blocker | Loaded `p18_runtime_project.tolproj`; status `Reloaded CAD source: neutral_step_two_part_loop.step`; viewport export nonblank. |
| Source GUI runtime with generated `.tolpack` | `source_tolpack_runtime.log`, `source_tolpack_runtime_summary.json`, `source_tolpack_runtime_viewport.png` | PASS with blocker | Imported `p18_runtime_project.tolpack` to a normal project folder, rehydrated packaged CAD asset, and exported a nonblank viewport snapshot. |
| PyInstaller CAD package build | `packaged_build_cad1d.log` | PASS | `scripts/build_windows.ps1 -Clean -Program Cad1D -Python C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe` produced `dist/MechanicalDesignToolSuite/Cad1DTolerance.exe`. |
| Packaged executable run with `.tolproj` | `packaged_run_tolproj.log` | PASS | Process stayed alive after 10 seconds and was intentionally stopped. |
| Packaged executable run with `.tolpack` | `packaged_run_tolpack.log` | PASS | Process stayed alive after 10 seconds and was intentionally stopped. |

## Commands

Representative source-runtime command:

```powershell
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s tests\scripts\cad_1d_runtime_smoke.py tests\fixtures\cad_1d_tolerance\neutral_step_two_part_loop.step --output-dir docs\cad_1d_tolerance_tool\extracted_specs\2026-05-15_p18_live_runtime_packaged_smoke --prefix source_step_runtime --settle-ms 2000
```

Report/package generation used the public project/report/package APIs plus `_upsert_report_manifest_entry` to record generated report assets in the smoke project before package export.

Packaged build command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -Clean -Program Cad1D -Python "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe"
```

Packaged run attempts used `Start-Process` with `dist\MechanicalDesignToolSuite\Cad1DTolerance.exe` and the generated `.tolproj` / `.tolpack` paths, waited 10 seconds, then force-stopped the still-running GUI process.

## Native Qt / OCCT Investigation

P18 reproduced the P17 black full-window capture symptom with a narrower runtime harness:

- Source runtime summaries report `viewer_class=OccCadViewerWidget`.
- STEP/IGES/project/package runs report nonzero `displayed_shape_count`.
- `viewport_snapshot` images generated through `self._display.ExportToImage(...)` are nonblank and show shaded geometry.
- `full_window_snapshot` images captured from the desktop/window region show the surrounding Qt UI and native viewport overlays, but the central OCCT model area is black.
- A small attempted redraw/context-refresh hardening did not change the full-window evidence, so it was removed rather than committed.

Conclusion: this is a native `qtViewer3d` on-screen composition/capture blocker for full-window evidence. It does not block source import, report snapshot export, `.tolproj`/`.tolpack` load, or packaged executable startup.

## Verification

Executed on 2026-05-15:

```powershell
git diff --check
```

Result: passed with line-ending warnings only.

```powershell
$env:PYTHONPATH="src"; python -m unittest tests.test_cad_tolerance_gui tests.test_cad_tolerance_report tests.test_cad_viewer_api
```

Result: passed, 25 tests run, 2 skipped.

```powershell
$env:PYTHONPATH="src"; python -m unittest discover -s tests
```

Result: passed, 135 tests run, 7 skipped.

```powershell
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s -m unittest discover -s tests
```

Result: passed, 135 tests run, 2 skipped. The full CAD-runtime discovery did not crash, so the P17/P18 split fallback commands were not required.

## Status Updates

- `FCE-010`: packaged `Cad1DTolerance.exe` build and direct packaged run smoke are now evidenced for `.tolproj` and `.tolpack`.
- `FCE-011` / `FCE-012`: source STEP/IGES runtime import/display is now evidenced through the GUI harness; exact Windows open dialog and import-option parity remain partial.
- `FCE-016`: `.tolproj` and generated `.tolpack` source-runtime load, package asset portability, and packaged executable launch are evidenced.
- `FCE-023`: keep partial for final visual acceptance because full-window native viewport composition remains black, even though live OCCT shape display and export snapshots pass.
- `FCE-071` / `FCE-072`: report HTML/CSS/JS/manifest generation and package inclusion are evidenced; browser screenshot parity and exact Save Report dialog remain separate visual proof items.
