# Reverse-Engineering Summary

## Purpose

Summarize what has been learned from the EZtol demo video, generated transcript/captions, and visual evidence so implementation agents can build a faithful CAD-based 1D tolerance tool without rediscovering the source material.

## Sources Reviewed

| Date | Source | Workflow | Related Artifacts | Notes |
| --- | --- | --- | --- | --- |
| 2026-05-12 | EZtol demo MP4 | Standalone CAD 1D tolerance stackup demo plus Q&A | `source_artifacts/transcripts/2026-05-12_eztol_demo_timestamped_transcript.md`, `source_artifacts/captions/2026-05-12_eztol_demo_captions.vtt`, `output/transcribe/eztol-demo-media-1080p/visual_evidence/sheet_*.jpg` | 33:26 video, 295 transcript cues, no embedded captions in source MP4. |
| 2026-05-12 | EZtol demo MP4 | Targeted UI/UX visual review | `extracted_specs/2026-05-12_eztol_targeted_visual_review.md`, `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-12/` | 58 high-resolution key frames and 28 five-second contact sheets reviewed before implementation planning. |

## Key Observations

- The demonstrated product is a dense desktop CAD analysis tool with a three-pane layout: assembly tree, 3D viewport, and right-side stackup/results pane.
- The core workflow is guided: import CAD, select measurement endpoints, choose stackup direction and annotation plane, select loop parts/constraints, then let the tool derive editable 1D contributors.
- The prototype combines CAD selection and spreadsheet editing. Users can work from geometry but still edit the tolerance table directly.
- The UI repeatedly alternates between summary dashboard and stackup detail views. This split is central to the user experience.
- The result model includes worst-case, RSS, statistical quality metrics, objective comparisons, pass/fail states, shared-dimension flags, and contribution ranking.
- The tool is explicitly 1D. It should use geometry to warn about likely 3D effects but not claim to solve angular or full 3D tolerance behavior.
- Initial CAD support should be limited to non-commercial neutral formats. Native Inventor/CATIA/NX/Creo/SOLIDWORKS/JT support seen or mentioned in the video is not a near-term clone requirement.
- The long-run CAD kernel recommendation is OCCT/OpenCascade. `pythonocc` can be used for a prototype binding, but the architecture must isolate geometry access so a C++ OCCT module or different binding can replace it.
- The targeted visual review captured exact UI details not present in the first-pass notes: open/import dialog structure, guided mini-toolbar labels, component/mating-face counters, detail table row examples, dashboard rollup badges, shared-dimension marker, browser report navigation, and late-demo sensitivity dialogs.

## Product Principles

- Faithful desktop CAD density: prioritize compact tables, dockable panes, and model-view workflows over large decorative UI.
- Evidence-first implementation: when uncertain, reread the timestamped transcript and visual evidence before inventing behavior.
- Neutral-format first: implement STEP/IGES import before considering native commercial formats.
- Manual-first GD&T: allow users to manually define runout, position, datum, and profile contributors before attempting automatic PMI interpretation.
- Explain 1D limits: surface non-1D warnings in the dashboard and stackup detail rather than hiding geometry assumptions.
- Keep calculation and CAD services testable outside the GUI.

## Open Questions

- Exact non-1D warning thresholds need engineering definition.
- Exact report format is not specified by the video; HTML/PDF generated from an HTML report is the practical first target.
- Exact dialog text and some small icons are visually fuzzy. UI implementation agents must refer to `output/transcribe/eztol-demo-media-1080p/EZtol-Demo_Media_1080p.viewer.html` and frame sheets before implementing those areas.
- STEP AP242 PMI support should be investigated, but direct PMI import is not required for the first faithful clone pass.
