# Overnight Subagent Plans

These plans are intended for unattended `gpt-5.5` `xhigh` worker agents. They assume the agent starts in:

```text
C:\Users\emre_\PycharmProjects\Mechanical_Design_Tool_Suite
```

## Universal Agent Rules

Every worker must reread these files at startup and after every context compaction:

- `docs/cad_1d_tolerance_tool/07_implementation_plan.md`
- `docs/cad_1d_tolerance_tool/09_full_clone_gap_closure_plan.md`
- `docs/cad_1d_tolerance_tool/02_requirements.md`
- `docs/cad_1d_tolerance_tool/03_ui_ux_design_spec.md`
- `docs/cad_1d_tolerance_tool/04_data_model_and_calculation_methods.md`
- `docs/cad_1d_tolerance_tool/05_architecture_and_persistence.md`
- `docs/cad_1d_tolerance_tool/06_verification_validation_plan.md`
- `docs/cad_1d_tolerance_tool/08_primary_cad_viewer_plan.md`
- `docs/cad_1d_tolerance_tool/extracted_specs/2026-05-12_eztol_demo_extracted_spec.md`
- `docs/cad_1d_tolerance_tool/extracted_specs/2026-05-12_eztol_targeted_visual_review.md`
- `docs/cad_1d_tolerance_tool/extracted_specs/2026-05-14_full_clone_gap_matrix.md`
- `docs/cad_1d_tolerance_tool/source_artifacts/transcripts/2026-05-12_eztol_demo_timestamped_transcript.md`
- The packet file assigned to that worker.

When uncertain about UI/UX, the worker must inspect:

- `output/transcribe/eztol-demo-media-1080p/EZtol-Demo_Media_1080p.viewer.html`
- `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-12/key_frames/*.jpg`
- `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-12/five_second_sheets/*.jpg`
- `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-14_full_pass/full_10sec_sheet_*.jpg`
- `output/transcribe/eztol-demo-media-1080p/visual_evidence/sheet_*.jpg`
- `docs/cad_1d_tolerance_tool/source_artifacts/transcripts/2026-05-12_eztol_demo_timestamped_transcript.md`

Do not invent unreadable UI labels. If a crop, transcript line, or sheet does not resolve a label or state, implement the behavior conservatively and record the fidelity gap in the active packet notes.

## Targeted Visual Review Requirement

The deeper pre-implementation visual review has already been completed. Do not start UI, workflow, result, or report implementation from the coarse visual sheets alone. Use `extracted_specs/2026-05-12_eztol_targeted_visual_review.md` as the first UI evidence source, then inspect the local key frames it references.

## Primary CAD Viewer Decision

The primary CAD viewer path is OCCT/OpenCascade B-Rep presentation through AIS/V3d embedded in PyQt6. Future packets must use `OCC.Display.backend.load_backend("pyqt6")` before importing `OCC.Display.qtDisplay.qtViewer3d`, and feed the viewer with live OCCT shapes exposed by `OccCadGeometrySession.kernel_shape()`.

Do not implement PyVista, VTK, STL/OBJ, or tessellated meshes as the authoritative CAD viewer path. Meshes may be secondary diagnostics only. Selection, measurement, stackup references, persistence, and reports must remain tied to B-Rep-backed `ShapeReference` and `FeatureReference` ids.

Use `environment-cad312.yml` or an equivalent Python 3.12 environment with `pythonocc-core 7.9.3=*novtk*`, NumPy 1.26, PyQt6, and `ffmpeg`. Do not install Conda `pyqt`, PyQt5, Qt5, or a non-`novtk` pythonocc build into the primary CAD runtime. If pythonocc's PyQt6 `qtViewer3d` path proves unstable, preserve `cad_viewer_api.py` and escalate to a small C++ Qt6 + OCCT viewport component rather than switching the primary viewer to a mesh-only stack.

## Packet Order

| Packet | Purpose | Can Run In Parallel? |
| --- | --- | --- |
| P00 | Bootstrap evidence and fixture decisions | First or alongside read-only setup |
| P01 | Domain models and calculations | After P00 or immediately if docs are trusted |
| P02 | Project persistence | After P01 interfaces exist |
| P03 | Neutral CAD adapter spike | Parallel with P01 if it owns separate files |
| P04A | Primary OCCT AIS/V3d viewer spike | After P03; before full P04/P05 viewer coupling |
| P04 | UI shell and view models | Parallel with P03 using mocks; refine after P01/P03/P04A |
| P05 | Guided stackup workflow | After P01 plus enough of P03/P04 |
| P06 | Results dashboard and report generation | After P01; can use fixture projects |
| P07 | Integration, fidelity pass, and packaging spike | Prototype closeout after P06 |
| P08 | Full-clone evidence and acceptance reset | After P07 |
| P09 | Editable detail table and manual GD&T workflow | After P08; can run before P10/P11 if write scopes stay disjoint |
| P10 | XDE CAD metadata and assembly fidelity | After P08; parallel with P09 |
| P11 | Viewer interaction and annotation fidelity | After P08 and enough geometry/viewer API stability |
| P12 | Guided stackup workflow completion | After P09/P11 interfaces are available |
| P13 | Dashboard and result visual fidelity | After P09; can use fixture projects |
| P14 | Report and snapshot fidelity | After P11/P13 |
| P15 | Runtime, launcher, and packaging hardening | After P10/P11 enough for smoke tests |
| P16 | Final fidelity audit and roadmap split | Last after P08-P15 or documented blockers |

## Full Clone Packet Rules

P08-P16 are intended to move the product from a working prototype toward the requested 95% demo clone target. These packets must:

- Treat P07 as the first end-to-end path, not the final feature target.
- Compare behavior against `09_full_clone_gap_closure_plan.md`, the targeted visual review, and the full video context pack.
- Record unresolved visual or transcript ambiguity as a fidelity gap instead of silently guessing.
- Keep STEP/IGES as the supported P0 CAD formats.
- Keep native commercial CAD import, external CAD add-ins, automatic native PMI import, full 3D tolerance solving, and thermal expansion out of scope unless a later packet explicitly changes the roadmap.
- Preserve P06 report/dashboard behavior unless the active packet is intentionally improving the same behavior with tests.

## Completed Packet Contracts

### P02 Project Persistence

P02 is implemented and pushed in commit `d91e321` (`Add CAD tolerance project persistence`). Later packets must use the existing CAD persistence module instead of creating a parallel JSON shape or alternate serializer:

- API: `src/mechanical_design_tool_suite/cad_tolerance_project_io.py`
- Public functions: `save_project(project, path)`, `load_project(path)`, and `migrate_project_data(data)`
- Project suffix: `.tolproj`
- Required envelope: `project_type = "cad_1d_tolerance"` and current `schema_version = 2`
- Serialization authority: P01 `CadToleranceProject.to_dict()` / `CadToleranceProject.from_dict()` and nested domain object serializers
- Migration policy: load through `migrate_project_data`; schema v1 is migrated to v2, unsupported future schema versions fail explicitly
- Forward-compatible fields: unknown keys under a valid known schema are ignored by the domain loader
- Fixture: `tests/fixtures/cad_1d_tolerance/sample_cad_1d_project.tolproj`
- Verification: `$env:PYTHONPATH="src"; python -m unittest tests.test_cad_tolerance_project_io`

Future UI, workflow, report, and integration packets should round-trip projects through `load_project` / `save_project` and extend the P01 domain model deliberately if new persisted fields are needed. Do not persist Qt, OCCT, AIS/V3d, or other runtime handles in `.tolproj`; store serializable ids, metadata, references, snapshots, and report manifest entries only.

## Neutral CAD Constraint

P0 CAD support is limited to non-commercial neutral formats: STEP AP203/AP214/AP242 and IGES. Native Inventor, CATIA, NX, Creo, SOLIDWORKS, JT, and direct CAD add-ins are out of scope for initial implementation.

## Stack Decision

The CAD kernel target is OCCT/OpenCascade. `pythonocc-core` may be used as the first prototype binding, but every implementation must keep CAD access behind `cad_geometry_api.py` so a C++ OCCT adapter or different binding can replace it later.

The primary viewer target is OCCT AIS/V3d in PyQt6 behind `cad_viewer_api.py` / `cad_viewer_occ.py`. Use `load_backend("pyqt6")`, `qtViewer3d`, and live OCCT shapes from the geometry adapter. Keep PyVista/VTK and mesh exports out of the authoritative viewer, selection, measurement, and persistence path.
