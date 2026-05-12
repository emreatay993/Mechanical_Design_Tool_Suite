# Implementation Plan

## Summary

Implement a standalone EZtol-style CAD 1D tolerance analysis tool using the existing Python/Qt repo as the base. The plan prioritizes neutral CAD import, a dense Qt Widgets desktop shell, guided stackup authoring, editable tolerance contributors, analysis results, and browser-style reporting.

Every overnight agent must reread this file after context compaction, then reread the specific referenced spec files before editing.

Targeted visual review is complete and tracked in `extracted_specs/2026-05-12_eztol_targeted_visual_review.md`. UI, workflow, dashboard, and report workers must inspect that file and the referenced key frames before implementation.

## Key Changes

- Add CAD-specific tolerance domain models and calculations alongside the existing vNext tolerance modules.
- Add a neutral CAD geometry adapter boundary with an OCCT-backed implementation spike.
- Build a Qt Widgets main window that matches the demonstrated three-pane CAD workflow.
- Implement guided stackup creation and dense table editing.
- Add result dashboard, contribution ranking, warnings, snapshots, and report generation.
- Extend tests for domain, persistence, CAD fixtures, UI model/view behavior, and report output.

## Public Interface Changes

- New script entry point candidate: `cad-1d-tolerance-gui = "mechanical_design_tool_suite.cad_tolerance_gui:main"`.
- New project type: `.tolproj` JSON with `project_type = "cad_1d_tolerance"`.
- New optional CAD dependency group should be considered, such as `cad = [...]`, once the OCCT binding choice is proven.
- New docs and overnight plans live under `docs/cad_1d_tolerance_tool/`.

## Execution Tasks

### T01 Evidence Lock And Fixture Preparation

Goal: Make the source evidence and neutral CAD fixture expectations explicit before implementation.

Preconditions: Read `01_reverse_engineering_summary.md`, `02_requirements.md`, `03_ui_ux_design_spec.md`, and `extracted_specs/2026-05-12_eztol_demo_extracted_spec.md`.

Conservative write scope: `docs/cad_1d_tolerance_tool/`, `tests/fixtures/` if creating small neutral CAD placeholders.

Deliverables: Updated traceability notes, selected fixture list, and any missing acceptance criteria.

Verification: Confirm source artifact paths exist and `git status --short` shows only intentional docs/fixture changes.

Non-goals: No application code.

Packetization notes: Can run before all implementation packets.

### T02 CAD Domain And Calculation Core

Goal: Add pure Python CAD 1D tolerance models and calculations.

Preconditions: Read `04_data_model_and_calculation_methods.md` and existing `tolerance_models.py` / `tolerance_methods.py`.

Conservative write scope: new `src/mechanical_design_tool_suite/cad_tolerance_models.py`, `src/mechanical_design_tool_suite/cad_tolerance_methods.py`, and matching tests.

Deliverables: Dataclasses/enums, worst-case/RSS/statistical result functions, contribution ranking, non-1D warning data structures, deterministic tests.

Verification: `$env:PYTHONPATH="src"; python -m unittest discover -s tests -p "test_cad_tolerance*.py"`.

Non-goals: CAD file import, Qt UI, report rendering.

Packetization notes: Must land before UI and persistence packets depend on domain types.

### T03 Project Persistence

Goal: Save/load CAD tolerance projects using versioned JSON.

Preconditions: T02 domain types exist. Read existing `tolerance_project_io.py`.

Conservative write scope: new `cad_tolerance_project_io.py`, tests, sample fixture JSON.

Deliverables: Round-trip project persistence, schema version, migration hook, CAD source metadata, stackup/contributor serialization.

Verification: Round-trip tests and invalid-schema tests.

Non-goals: CAD kernel integration.

Packetization notes: Can run after T02 and in parallel with early UI mock shell if interfaces are stable.

### T04 Neutral CAD Kernel Spike

Goal: Prove a replaceable OCCT-based geometry adapter for STEP/IGES import and basic selection-ready metadata.

Preconditions: Read `05_architecture_and_persistence.md`. Confirm dependency install path for `pythonocc-core` or an equivalent OCCT binding.

Conservative write scope: `cad_geometry_api.py`, `cad_geometry_occ.py`, `tests/test_cad_geometry*.py`, small fixture files.

Deliverables: Import STEP/IGES, traverse assembly/product structure where available, expose shape references, measure planar/cylindrical feature basics.

Verification: CAD fixture tests; no Qt UI dependency in geometry API tests.

Non-goals: Full viewer polish, native CAD import, robust topological naming across revisions.

Packetization notes: This is the key risk packet. If Python binding blocks progress, document the blocker and propose C++ OCCT adapter scope.

### T05 Qt Desktop Shell And View Models

Goal: Build the EZtol-style three-pane desktop shell.

Preconditions: Read `03_ui_ux_design_spec.md`, `extracted_specs/2026-05-12_eztol_targeted_visual_review.md`, and inspect visual review key frames for the shell, open/import flow, summary table, detail table, result plots, and report views.

Conservative write scope: `cad_tolerance_gui.py`, `cad_tolerance_viewmodels.py`, Qt resources/icons if needed, GUI tests.

Deliverables: Main window, ribbon-like tabs/actions, left assembly tree, center placeholder or live viewport host, right summary/detail pane, table models with required columns, observed row colors, dashboard badges, non-1D warning treatment, and documented fidelity gaps for unreadable labels.

Verification: GUI model tests; screenshot review against visual evidence.

Non-goals: Full CAD selection workflow if T04 is not ready.

Packetization notes: Can begin with a viewport abstraction/mock if T04 is still underway.

### T06 Guided Stackup Workflow And Annotations

Goal: Implement guided endpoint/direction/plane/loop selection and annotation state.

Preconditions: T02 and enough of T04/T05 exist.

Conservative write scope: workflow controller module, annotation model, relevant GUI/viewmodel files, tests.

Deliverables: Step prompts, selection filters, guided mini-toolbar labels/counters from the targeted visual review, generated contributor rows, editable annotation positions, shared-dimension flags.

Verification: Workflow state tests and manual UI smoke test with fixture CAD.

Non-goals: Production-grade auto-loop discovery.

Packetization notes: Keep workflow controller independent enough to test without live mouse picks.

### T07 Results Dashboard And Reporting

Goal: Implement summary results, contribution view, warning display, snapshots, and HTML reports.

Preconditions: T02/T03 plus UI shell from T05.

Conservative write scope: report generator, dashboard viewmodels, result widgets, tests.

Deliverables: Summary table statuses, result bars/plots, dashboard rollup badges, contribution ranking view, browser-style HTML report matching the targeted visual review structure.

Verification: deterministic report test, dashboard model tests, visual review.

Non-goals: PDF export until HTML is stable.

Packetization notes: Can use fixture projects independent from live CAD import.

### T08 Integration, Fidelity Pass, And Packaging Spike

Goal: Integrate the first end-to-end clone path and identify packaging risks.

Preconditions: T02-T07 substantially complete.

Conservative write scope: entry point wiring, pyproject optional dependency updates, docs, integration tests, packaging notes.

Deliverables: Launchable CAD 1D tolerance GUI, fixture demo project, UI fidelity gap list, dependency/packaging decision.

Verification: full unit test suite, manual smoke run, screenshot comparison against visual evidence, packaging dry run if dependency stack permits.

Non-goals: Native CAD import, external CAD add-ins, full installer polish.

Packetization notes: Final overnight closeout packet.

## Work Packet Conversion Map

| Task | Packet | Suggested Agent |
| --- | --- | --- |
| T01 | P00 Bootstrap and evidence lock | gpt-5.5 xhigh |
| T02 | P01 Domain/calculation core | gpt-5.5 xhigh |
| T03 | P02 Persistence | gpt-5.5 xhigh |
| T04 | P03 Neutral CAD adapter spike | gpt-5.5 xhigh |
| T05 | P04 UI shell and view models | gpt-5.5 xhigh |
| T06 | P05 Guided stackup workflow | gpt-5.5 xhigh |
| T07 | P06 Results and reports | gpt-5.5 xhigh |
| T08 | P07 Integration and closeout | gpt-5.5 xhigh |

## Test Plan

- Run existing suite before major changes when feasible.
- Add isolated tests per packet.
- Keep CAD-kernel tests skipped with an explicit reason if the optional CAD dependency is unavailable.
- Use visual evidence sheets for UI review and record gaps in docs.
- For UI/report packets, record which targeted visual review key frames were used.

## Assumptions

- Neutral CAD formats are enough for the first clone.
- OCCT is the preferred CAD kernel; `pythonocc` is a prototype binding, not an irreversible product decision.
- Qt Widgets are preferred over QML for the CAD clone because the UI is dense, table-heavy, and dock-heavy.
- Existing vNext tolerance modules provide patterns but should not be forced to carry CAD-specific concepts if sibling modules are cleaner.
