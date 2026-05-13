# Overnight Subagent Plans

These plans are intended for unattended `gpt-5.5` `xhigh` worker agents. They assume the agent starts in:

```text
C:\Users\emre_\PycharmProjects\Mechanical_Design_Tool_Suite
```

## Universal Agent Rules

Every worker must reread these files at startup and after every context compaction:

- `docs/cad_1d_tolerance_tool/07_implementation_plan.md`
- `docs/cad_1d_tolerance_tool/02_requirements.md`
- `docs/cad_1d_tolerance_tool/03_ui_ux_design_spec.md`
- `docs/cad_1d_tolerance_tool/04_data_model_and_calculation_methods.md`
- `docs/cad_1d_tolerance_tool/05_architecture_and_persistence.md`
- `docs/cad_1d_tolerance_tool/06_verification_validation_plan.md`
- `docs/cad_1d_tolerance_tool/extracted_specs/2026-05-12_eztol_targeted_visual_review.md`
- The packet file assigned to that worker.

When uncertain about UI/UX, the worker must inspect:

- `output/transcribe/eztol-demo-media-1080p/EZtol-Demo_Media_1080p.viewer.html`
- `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-12/key_frames/*.jpg`
- `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-12/five_second_sheets/*.jpg`
- `output/transcribe/eztol-demo-media-1080p/visual_evidence/sheet_*.jpg`
- `docs/cad_1d_tolerance_tool/source_artifacts/transcripts/2026-05-12_eztol_demo_timestamped_transcript.md`

## Targeted Visual Review Requirement

The deeper pre-implementation visual review has already been completed. Do not start UI, workflow, result, or report implementation from the coarse visual sheets alone. Use `extracted_specs/2026-05-12_eztol_targeted_visual_review.md` as the first UI evidence source, then inspect the local key frames it references.

## Packet Order

| Packet | Purpose | Can Run In Parallel? |
| --- | --- | --- |
| P00 | Bootstrap evidence and fixture decisions | First or alongside read-only setup |
| P01 | Domain models and calculations | After P00 or immediately if docs are trusted |
| P02 | Project persistence | After P01 interfaces exist |
| P03 | Neutral CAD adapter spike | Parallel with P01 if it owns separate files |
| P04 | UI shell and view models | Parallel with P03 using mocks; refine after P01/P03 |
| P05 | Guided stackup workflow | After P01 plus enough of P03/P04 |
| P06 | Results dashboard and report generation | After P01; can use fixture projects |
| P07 | Integration, fidelity pass, and packaging spike | Last |

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
