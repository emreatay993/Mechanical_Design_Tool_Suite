# CAD 1D Tolerance Tool

This folder is the planning and reverse-engineering workspace for a standalone CAD-based 1D tolerance analysis product.

Keep this area focused on observed behavior, derived requirements, independent design decisions, and implementation plans. Do not copy proprietary source assets, UI text, branding, binary files, or vendor-owned media into tracked documents unless there is an explicit legal reason to do so.

## Structure

```text
cad_1d_tolerance_tool/
  source_artifacts/
    demos/
    transcripts/
    captions/
    screenshots/
  mockups/
  extracted_specs/
  01_reverse_engineering_summary.md
  02_requirements.md
  03_ui_ux_design_spec.md
  04_data_model_and_calculation_methods.md
  05_architecture_and_persistence.md
  06_verification_validation_plan.md
  07_implementation_plan.md
```

## Naming

Use stable, date-prefixed names so artifacts remain traceable:

```text
YYYY-MM-DD_<source>_<workflow>_demo.mp4
YYYY-MM-DD_<source>_<workflow>_transcript.md
YYYY-MM-DD_<source>_<workflow>_captions.vtt
YYYY-MM-DD_<concept>_mockup.html
```

## Tracking Policy

- Track independent specs, requirements, mockups, implementation plans, transcripts, captions, and manifests when they are safe to share in this repository.
- Do not track raw demo videos or source screenshots. Those folders are ignored by Git.
- For local-only source media, record a short entry in `source_artifacts/manifest.md` with the source, date, workflow, storage location, and notes needed to reproduce the analysis.
