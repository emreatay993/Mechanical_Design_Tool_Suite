# Source Artifact Manifest

Use this manifest to reference local-only or external source artifacts without committing raw media to Git.

| Date | Source | Workflow | Artifact Type | Storage Location | Notes |
| --- | --- | --- | --- | --- | --- |
| 2026-05-12 | EZtol demo video | CAD 1D tolerance analysis demo | Local-only MP4 | `output/transcribe/eztol-demo-media-1080p/EZtol-Demo_Media_1080p.mp4` | Original source file remains under `docs/cad_1d_tolerance_tool/source_artifacts/demos/`; copied context-pack MP4 hash matched original. Do not track raw video. |
| 2026-05-12 | EZtol demo video | Transcription | Timestamped transcript | `docs/cad_1d_tolerance_tool/source_artifacts/transcripts/2026-05-12_eztol_demo_timestamped_transcript.md` | Generated from extracted speech audio; 295 cues, coverage `00:00:00.000` to `00:32:32.000`. |
| 2026-05-12 | EZtol demo video | Transcription | Plain transcript and segment table | `docs/cad_1d_tolerance_tool/source_artifacts/transcripts/2026-05-12_eztol_demo_transcript.txt`, `docs/cad_1d_tolerance_tool/source_artifacts/transcripts/2026-05-12_eztol_demo_segments.tsv` | Segment table preserves cue number, start/end time, and text. |
| 2026-05-12 | EZtol demo video | Captions | SRT/VTT captions | `docs/cad_1d_tolerance_tool/source_artifacts/captions/2026-05-12_eztol_demo_captions.srt`, `docs/cad_1d_tolerance_tool/source_artifacts/captions/2026-05-12_eztol_demo_captions.vtt` | Captions copied from the local context pack for repeatable review. |
| 2026-05-12 | EZtol demo video | Visual evidence | Local-only frame contact sheets | `output/transcribe/eztol-demo-media-1080p/visual_evidence/sheet_*.jpg` | 10-second cadence frame sheets with burned-in timestamps. Do not track screenshots unless explicitly needed. |
| 2026-05-12 | EZtol demo video | Targeted visual review | Local-only key frames and five-second sheets | `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-12/` | 58 high-resolution workflow key frames, 28 five-second UI contact sheets, and `key_frame_manifest.tsv`. Findings are tracked in `extracted_specs/2026-05-12_eztol_targeted_visual_review.md`. |
| 2026-05-12 | EZtol demo video | Context pack | Local viewer and raw transcription JSON | `output/transcribe/eztol-demo-media-1080p/README.md` | Bundles copied MP4, generated captions, transcript, raw JSON, and clickable local viewer. |

## P00 Evidence Lock

Checked on 2026-05-12 for the CAD 1D tolerance P00/P01 implementation pass:

- Transcript directory exists: `docs/cad_1d_tolerance_tool/source_artifacts/transcripts/`
- Caption directory exists: `docs/cad_1d_tolerance_tool/source_artifacts/captions/`
- Timestamped transcript exists: `docs/cad_1d_tolerance_tool/source_artifacts/transcripts/2026-05-12_eztol_demo_timestamped_transcript.md`
- Targeted visual review exists: `docs/cad_1d_tolerance_tool/extracted_specs/2026-05-12_eztol_targeted_visual_review.md`
- Key frame directory exists: `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-12/key_frames/`
- Five-second sheet directory exists: `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-12/five_second_sheets/`
- Context-pack viewer exists: `output/transcribe/eztol-demo-media-1080p/EZtol-Demo_Media_1080p.viewer.html`

Later UI, workflow, result, and report agents must use the targeted visual review as the first evidence source, then inspect the referenced local key frames or five-second sheets before deciding visible labels, colors, table columns, status treatments, or report layout.
