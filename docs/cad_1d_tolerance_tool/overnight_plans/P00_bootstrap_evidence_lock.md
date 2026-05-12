# P00 Bootstrap Evidence Lock

## Summary

Prepare the repo for implementation by making evidence, fixture decisions, and acceptance criteria explicit.

## Worker Prompt

You are a `gpt-5.5` `xhigh` worker in `C:\Users\emre_\PycharmProjects\Mechanical_Design_Tool_Suite`. Your task is P00 Bootstrap Evidence Lock. Reread `docs/cad_1d_tolerance_tool/overnight_plans/README.md`, `07_implementation_plan.md`, and all numbered CAD spec docs before editing. After every context compaction, reread the same files and this packet.

## Conservative Write Scope

- `docs/cad_1d_tolerance_tool/`
- `tests/fixtures/` only if creating tiny neutral CAD fixture placeholders or fixture README files

## Deliverables

- Confirm source artifact manifest paths are valid.
- Add or refine fixture requirements for STEP/IGES files.
- Add a small traceability checklist if any requirement lacks evidence.
- Do not write application code.

## Verification

```powershell
Get-ChildItem docs/cad_1d_tolerance_tool/source_artifacts/transcripts
Get-ChildItem docs/cad_1d_tolerance_tool/source_artifacts/captions
git status --short
```

## Stop Condition

Stop when docs clearly tell later agents which evidence files to reread, what fixtures are needed, and which requirements are P0.
