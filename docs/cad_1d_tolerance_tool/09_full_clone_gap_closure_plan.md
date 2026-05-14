# CAD 1D Tolerance Full Clone Gap Closure Plan

## Summary

The P00-P07 packet sequence produced a working neutral-CAD prototype, but the stated target is stricter: clone almost all visible EZtol-style UI/UX and capabilities from the demo video, with at least 95% fidelity where technically feasible.

This plan extends the packet series from prototype integration to full-clone hardening. It is based on:

- Full video context pack: `output/transcribe/eztol-demo-media-1080p/`
- Targeted visual review: `docs/cad_1d_tolerance_tool/extracted_specs/2026-05-12_eztol_targeted_visual_review.md`
- Fresh full-pass sheets: `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-14_full_pass/`
- Baseline gap matrix: `docs/cad_1d_tolerance_tool/extracted_specs/2026-05-14_full_clone_gap_matrix.md`
- Existing numbered CAD docs `01` through `08`
- Current implementation coverage in `src/mechanical_design_tool_suite/cad_*.py` and `tests/test_cad*.py`

## Key Changes

- Treat P07 as the first end-to-end prototype, not the final clone target.
- Add P08-P16 overnight packets for evidence traceability, table/GD&T editing, XDE CAD metadata, viewer annotations, guided workflow completion, result/dashboard visual fidelity, report fidelity, runtime packaging, and final audit.
- Keep PyQt6 + OCCT/pythonocc as the default architecture. Escalate only the viewport to a small C++ Qt6 + OCCT component if `qtViewer3d` blocks selection, annotation, or packaging fidelity.
- Keep STEP/IGES as the supported P0 CAD formats. Native commercial CAD import, add-ins, automatic native PMI import, and full 3D tolerance solving remain explicit non-goals unless a later roadmap changes scope.

## Public Interface Changes

- No immediate user-facing file format change is required beyond the existing `.tolproj` and `.tolpack`.
- Planned UI behavior expands substantially: editable detail table, GD&T dialog, real annotation graphics, richer result mode controls, contribution plots, source reattach status, and full report export flow.
- Planned CLI/build behavior expands to include validated CAD launcher and packaged `Cad1DTolerance.exe` flows.

## Execution Tasks

### T01 Evidence Matrix And Acceptance Reset

Goal: Create a traceable requirement/coverage matrix from the whole demo evidence.

Preconditions: P07 prototype exists and the video context pack is present.

Conservative write scope: `docs/cad_1d_tolerance_tool/`, especially extracted specs, verification plan, and overnight packet notes.

Deliverables: Refined version of `extracted_specs/2026-05-14_full_clone_gap_matrix.md`, feature/UI inventory, met/partial/missing coverage matrix, acceptance scenarios V12+, and explicit unresolved crop list.

Verification: Documentation review plus `git diff --check`.

Non-goals: Code implementation.

Packetization notes: P08.

### T02 Editable Detail Table And GD&T Workflow

Goal: Make the detail grid behave like the demo spreadsheet-like editor.

Preconditions: P01 domain models, P06 result projection, and P07 project persistence are stable.

Conservative write scope: `cad_tolerance_models.py`, `cad_tolerance_methods.py`, `cad_tolerance_viewmodels.py`, `cad_tolerance_gui.py`, targeted tests.

Deliverables: `setData` editing, delegates for numeric/tolerance/type/datum fields, manual GD&T dialog, immediate recalculation, shared-dimension warnings.

Verification: GUI/viewmodel tests for editing plus full test suite.

Non-goals: Native PMI import.

Packetization notes: P09.

### T03 XDE-Aware CAD Metadata

Goal: Preserve real STEP/IGES assembly names, colors, hierarchy, and metadata where available.

Preconditions: Existing OCCT adapter imports neutral files.

Conservative write scope: `cad_geometry_api.py`, `cad_geometry_occ.py`, fixtures, geometry tests.

Deliverables: STEPCAF/XCAF traversal, deterministic assembly tree names, color metadata, stable shape mapping, feature labels useful for UI/report.

Verification: `mdts-cad312` geometry tests with caster STEP and neutral fixtures.

Non-goals: CATIA/SOLIDWORKS/native import.

Packetization notes: P10.

### T04 Viewer Interaction And Annotation Layer

Goal: Make the viewport interaction match the demo closely enough to drive workflow and report snapshots.

Preconditions: B-Rep-backed shape references and viewer adapter are stable.

Conservative write scope: `cad_viewer_api.py`, `cad_viewer_occ.py`, small GUI host wiring, viewer tests.

Deliverables: face/edge/vertex/body filters, hover/selection colors, cross-highlighting, draggable red/blue dimension annotations, leader arrows, ViewCube/axis/navigation affordances, snapshot with overlays.

Verification: `mdts-cad312` viewer tests and manual screenshot comparison against key frames.

Non-goals: Mesh-authoritative viewer or PyVista/VTK primary path.

Packetization notes: P11.

### T05 Guided Stackup Completion

Goal: Turn the guided toolbar from a prototype state machine into a practical CAD authoring flow.

Preconditions: Viewer selection callbacks and feature references are available.

Conservative write scope: `cad_stackup_workflow.py`, `cad_tolerance_gui.py`, workflow-facing tests.

Deliverables: OK/X/list controls, loop-part counters, mating-face counters, direction/plane/label persistence, Add Feature reuse, production-quality contributor creation from selected geometry.

Verification: workflow tests plus manual caster STEP smoke.

Non-goals: Fully automatic mate graph solving from native CAD constraints.

Packetization notes: P12.

### T06 Dashboard And Result Visual Fidelity

Goal: Match the summary/detail/result/contribution presentation in the demo.

Preconditions: Editable contributors and calculation projection are stable.

Conservative write scope: `cad_tolerance_methods.py`, `cad_tolerance_viewmodels.py`, `cad_tolerance_gui.py`, focused tests.

Deliverables: pass/fail badges, worst-case/RSS/statistical controls, red/green range bar, bell curve, contribution bars, shared-dimension tooltip, non-1D warning states.

Verification: viewmodel tests, GUI tests, visual comparison against key frames 030-046.

Non-goals: Full 3D CETOL-style solve or angular results.

Packetization notes: P13.

### T07 Report And Snapshot Fidelity

Goal: Make generated reports look and behave like the browser report in the video.

Preconditions: snapshot overlays and dashboard projections exist.

Conservative write scope: `cad_tolerance_report.py`, `cad_tolerance_project_io.py`, GUI report actions, report tests.

Deliverables: dark left nav, summary table, per-stackup result plots, contribution plots, annotated CAD images, deterministic assets, save/open behavior.

Verification: deterministic report tests and browser/manual comparison against key frames 047-051.

Non-goals: Vendor branding or proprietary assets.

Packetization notes: P14.

### T08 Runtime, Launcher, And Packaging Hardening

Goal: Make the full clone launchable and packageable without undermining the CAD runtime.

Preconditions: CAD GUI entry point and launcher card exist.

Conservative write scope: `environment-cad312.yml`, `pyproject.toml`, `MechanicalDesignToolSuite.spec`, `scripts/build_windows.ps1`, README/build docs, launcher tests.

Deliverables: reproducible CAD environment with `ffmpeg`, validated launcher, packaged `Cad1DTolerance.exe`, explicit OCC/PyQt6 DLL collection notes, no Qt5/PyQt5/Conda `pyqt`.

Verification: standard tests, CAD-runtime tests, packaged build smoke when feasible.

Non-goals: Full installer polish.

Packetization notes: P15.

### T09 Final Fidelity Audit And Roadmap Split

Goal: Close the loop against all video-derived requirements and leave only explicit roadmap items.

Preconditions: P08-P15 complete or blockers documented.

Conservative write scope: docs, tests for acceptance gaps, minimal polish fixes.

Deliverables: final coverage matrix, screenshot sheet comparison, unresolved crop list, P17+ roadmap if required.

Verification: full test suite, CAD runtime test suite, GUI smoke, report smoke, final visual evidence review.

Non-goals: New feature families not shown or derived from the demo.

Packetization notes: P16.

## Work Packet Conversion Map

| Task | Packet | Purpose |
| --- | --- | --- |
| T01 | P08 | Evidence and acceptance reset |
| T02 | P09 | Editable table and GD&T workflow |
| T03 | P10 | XDE assembly metadata and CAD fidelity |
| T04 | P11 | Viewer interaction and annotations |
| T05 | P12 | Guided workflow completion |
| T06 | P13 | Dashboard and result visual fidelity |
| T07 | P14 | Report and snapshot fidelity |
| T08 | P15 | Runtime, launcher, and packaging hardening |
| T09 | P16 | Final fidelity audit |

## Test Plan

Baseline:

```powershell
$env:PYTHONPATH="src"; python -m unittest discover -s tests
```

CAD runtime:

```powershell
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s -m unittest discover -s tests
```

Manual smoke:

```powershell
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s -m mechanical_design_tool_suite.cad_tolerance_gui "tests\fixtures\cad_1d_tolerance\caster_whell_v0\caster_wheel.stp"
```

Evidence regeneration:

```powershell
& "C:\ProgramData\miniforge3\envs\mdts-cad312\Library\bin\ffmpeg.exe" -hide_banner -i output\transcribe\eztol-demo-media-1080p\EZtol-Demo_Media_1080p.mp4
```

## Assumptions

- The target remains a standalone neutral-CAD clone, not a commercial CAD add-in.
- STEP/IGES support is enough for the current clone scope.
- PyQt6 + OCCT/pythonocc remains viable unless P11/P15 uncover a concrete blocker.
- Full 3D tolerance analysis, thermal expansion, native PMI import, and commercial CAD formats are roadmap items, not current overnight packet goals.
