# Extracted Specs

Use this directory for raw observations extracted from demos, captions, transcripts, screenshots, and related artifacts before they are promoted into the numbered product specification documents.

## Current Extracts

| File | Source | Purpose |
| --- | --- | --- |
| `2026-05-12_eztol_demo_extracted_spec.md` | Local EZtol demo context pack and copied transcript/captions | Evidence-backed requirements, UI/UX observations, and open questions used to populate the numbered spec documents. |
| `2026-05-12_eztol_targeted_visual_review.md` | Targeted high-resolution key frames and five-second sheets extracted from the MP4 | Detailed UI/UX and report findings required before implementation. |
| `2026-05-14_full_clone_gap_matrix.md` | P08 full-clone evidence reset using the full context pack, targeted review, transcript, full-pass sheets, numbered docs, and P07-era implementation state | Traceable `FCE-*` coverage matrix used by P09-P16 for status, evidence anchors, packet routing, and P0 scope guardrails. |
| `2026-05-15_final_fidelity_audit_and_roadmap.md` | P16 final audit after P08-P15 using canonical docs, video evidence, implementation/test coverage, and selected key-frame review | Final dated coverage matrix, screenshot/report comparison notes, unresolved unreadable-label list, intentional non-implementation list, P17+ roadmap, and PyQt6 + OCCT recommendation. |

## Review Rule

When later agents are uncertain about UI behavior, data fields, or workflow order, they must reread:

- `docs/cad_1d_tolerance_tool/source_artifacts/transcripts/2026-05-12_eztol_demo_timestamped_transcript.md`
- `docs/cad_1d_tolerance_tool/extracted_specs/2026-05-12_eztol_targeted_visual_review.md`
- `docs/cad_1d_tolerance_tool/extracted_specs/2026-05-14_full_clone_gap_matrix.md`
- `output/transcribe/eztol-demo-media-1080p/visual_evidence/sheet_*.jpg`
- `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-12/key_frames/*.jpg`
- `output/transcribe/eztol-demo-media-1080p/EZtol-Demo_Media_1080p.viewer.html`
