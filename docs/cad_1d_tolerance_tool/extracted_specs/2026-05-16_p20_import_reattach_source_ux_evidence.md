# P20 Import Reattach And Project Source UX Evidence

Date: 2026-05-16

## Evidence Reviewed

- `docs/cad_1d_tolerance_tool/overnight_plans/README.md`
- `docs/cad_1d_tolerance_tool/10_full_clone_productization_plan.md`
- `docs/cad_1d_tolerance_tool/overnight_plans/P20_import_reattach_and_project_source_ux.md`
- `docs/cad_1d_tolerance_tool/02_requirements.md`
- `docs/cad_1d_tolerance_tool/03_ui_ux_design_spec.md`
- `docs/cad_1d_tolerance_tool/05_architecture_and_persistence.md`
- `docs/cad_1d_tolerance_tool/extracted_specs/2026-05-12_eztol_targeted_visual_review.md`
- Transcript cues `00:02:35-00:04:55`
- Frames:
  - `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-12/key_frames/003_00-02-50_open_file_flow.jpg`
  - `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-12/key_frames/004_00-03-20_import_options_dialog.jpg`
  - `output/transcribe/eztol-demo-media-1080p/visual_evidence/sheet_002.jpg`

## Implemented Behavior

- Added typed CAD source statuses: present, missing, relocated, changed hash, changed topology, project-local package asset, and unknown.
- Added persisted `CadDocument` source metadata for status, status message, last checked timestamp, and topology hash.
- Added schema v2 to v3 migration defaults for source metadata.
- Added topology fingerprint/hash validation over serializable shape and feature references. Runtime CAD handles remain out of persistence.
- Stamped imported OCC geometry documents with topology hashes.
- Added project-load refresh validation for missing, relocated, package-local, hash-changed, and topology-changed source states.
- Added explicit Data ribbon actions for `Refresh Source` and `Reattach Source`.
- Added a persistent model-browser source status label.
- Added neutral import dialog parity improvements:
  - `Options` and `Select` tabs retained.
  - STEP/IGES-only OK enablement.
  - source reference vs converted neutral geometry wording.
  - units, object filters, assembly/part options, file name/location/type fields.
  - import settings are now passed to the geometry adapter.

## Manual Workflow Steps

1. Open a `.tolproj` with a valid STEP source path. The project loads analysis data, refreshes the CAD source, displays the viewer session, and shows `Source: Present`.
2. Open a `.tolproj` whose source file is missing. The analysis tables remain visible, the viewer clears, and the source label/status bar report the missing file by name.
3. Move the expected STEP file beside the project under a different relative folder. Project load finds the same file name, reloads it, and marks the source as relocated.
4. Package a project to `.tolpack` and import it. The packaged project uses `assets/cad/...` and marks the source as a project-local package asset.
5. Refresh a project after the STEP bytes change but topology is equivalent. The source status reports changed hash without treating topology as changed.
6. Refresh a project after the serializable topology fingerprint changes. The source status reports changed topology and keeps the previous topology baseline until explicit reattach.
7. Use `Reattach Source` with a replacement STEP/IGES path. The document source path, file hash, topology baseline, assembly root, and viewer session update in memory.

## Verification

```powershell
$env:PYTHONPATH="src"; python -m unittest tests.test_cad_tolerance_project_io tests.test_cad_tolerance_gui tests.test_cad_geometry_api
```

Result: passed, 51 tests, 4 skipped.

```powershell
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s -m unittest tests.test_cad_geometry_api tests.test_cad_tolerance_project_io tests.test_cad_tolerance_gui
```

Result: passed, 51 tests, 1 skipped.

## Scope Notes

- No native Inventor, CATIA, NX, Creo, SOLIDWORKS, JT, or CAD add-in import was added.
- No automatic native PMI import was added.
- The source topology hash is a validation aid for neutral source refresh/reattach, not a replacement for B-Rep-backed `ShapeReference` and `FeatureReference` persistence.
