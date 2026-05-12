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

## Neutral CAD Constraint

P0 CAD support is limited to non-commercial neutral formats: STEP AP203/AP214/AP242 and IGES. Native Inventor, CATIA, NX, Creo, SOLIDWORKS, JT, and direct CAD add-ins are out of scope for initial implementation.

## Stack Decision

The CAD kernel target is OCCT/OpenCascade. `pythonocc-core` may be used as the first prototype binding, but every implementation must keep CAD access behind `cad_geometry_api.py` so a C++ OCCT adapter or different binding can replace it later.
