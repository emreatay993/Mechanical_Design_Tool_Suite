# P08 Full Clone Evidence Coverage Reset

## Summary

Create a complete, traceable feature/UI coverage matrix for the 95% EZtol-style clone target before further implementation. P07 is a prototype baseline; this packet defines what remains to reach a faithful product.

## Worker Prompt

You are a `gpt-5.5` `xhigh` worker in `C:\Users\emre_\PycharmProjects\Mechanical_Design_Tool_Suite`. Your task is P08 Full Clone Evidence Coverage Reset. Reread `overnight_plans/README.md`, `09_full_clone_gap_closure_plan.md`, all numbered CAD docs, `extracted_specs/2026-05-12_eztol_targeted_visual_review.md`, the timestamped transcript, and all completed packet notes before editing. After every context compaction, reread those files and this packet.

Use the whole video context pack, not only prior summaries:

- `output/transcribe/eztol-demo-media-1080p/EZtol-Demo_Media_1080p.viewer.html`
- `output/transcribe/eztol-demo-media-1080p/EZtol-Demo_Media_1080p.timestamped_transcript.md`
- `output/transcribe/eztol-demo-media-1080p/EZtol-Demo_Media_1080p.segments.tsv`
- `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-12/key_frame_manifest.tsv`
- `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-12/key_frames/*.jpg`
- `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-12/five_second_sheets/*.jpg`
- `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-14_full_pass/full_10sec_sheet_*.jpg`

When uncertain, inspect the MP4 through the viewer and regenerate crops with `ffmpeg` in `mdts-cad312`.

## Conservative Write Scope

- `docs/cad_1d_tolerance_tool/`
- `tests/fixtures/cad_1d_tolerance/README.md` only if fixture requirements need clearer traceability

## Deliverables

- A dated evidence/coverage matrix under `docs/cad_1d_tolerance_tool/extracted_specs/`.
- Refine `extracted_specs/2026-05-14_full_clone_gap_matrix.md` rather than starting from a blank matrix.
- Each video-derived requirement marked `met`, `partial`, `missing`, `deferred`, or `out_of_scope`.
- Evidence references for each requirement: transcript timestamp, key frame, contact sheet, or numbered doc section.
- Clear distinction between P0 neutral-CAD clone scope and non-goals: native commercial CAD import, CAD add-ins, native PMI import, thermal expansion, and full 3D tolerance solving.
- Updated verification plan with any missing acceptance cases.
- Updated overnight README if packet order or rules need clarification.

## Required Coverage Areas

- Launch/open/import flow, import options, source reference/reattach behavior.
- Main workspace, ribbon, model browser, viewport, right analysis pane, status bars.
- Guided mini-toolbar and all step states.
- Selection filtering, highlights, annotations, ViewCube, axis triad, navigation toolbar.
- Generated detail table, inline edits, tolerance-type dropdown, GD&T dialog, datum rows.
- Worst Case, RSS, Statistical modes, Cpk/Sigma/Yield quality metrics, pass/fail/warning states.
- Multi-stackup dashboard, shared-dimension markers/tooltips, contributions.
- Snapshot and report generation, report save dialog, browser report layout.
- Late-demo SolidWorks/CETOL references that should influence future roadmap but not P0 implementation.

## Verification

```powershell
git diff --check
```

Optional evidence tooling:

```powershell
& "C:\ProgramData\miniforge3\envs\mdts-cad312\Library\bin\ffprobe.exe" -v error -show_entries format=duration:stream=index,codec_type,codec_name,width,height,r_frame_rate,duration -of json output\transcribe\eztol-demo-media-1080p\EZtol-Demo_Media_1080p.mp4
```

## Non-Goals

- No product code changes.
- No broad UI redesign beyond evidence extraction.
- No commitment to native commercial CAD formats.

## Stop Condition

Stop when the next implementation packets can use one traceable coverage matrix without rediscovering the video.
