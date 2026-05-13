# P07 Integration Fidelity Packaging

## Summary

Integrate the first end-to-end CAD 1D tolerance clone path, perform a visual fidelity review, and document packaging/dependency risks.

## Worker Prompt

You are a `gpt-5.5` `xhigh` worker in `C:\Users\emre_\PycharmProjects\Mechanical_Design_Tool_Suite`. Your task is P07 Integration Fidelity Packaging. Reread `overnight_plans/README.md`, all numbered CAD docs including `08_primary_cad_viewer_plan.md`, `extracted_specs/2026-05-12_eztol_targeted_visual_review.md`, and all completed packet notes before editing. After every context compaction, reread those files and this packet. If uncertain about UI fidelity, inspect the local viewer and targeted visual review key frames before changing the UI.

Make the saved-project path behave like a real CAD tolerance application, not a table-only loader. When a user opens a `.tolproj`, the app must load the tolerance/project data and also try to reload the referenced STEP/IGES CAD file into the OCCT AIS/V3d viewer. If the CAD file cannot be found, show a clear missing-source message/status instead of silently leaving the viewport blank. This is the practical meaning of the P07 end-to-end fixture path.

Prefer a project-local asset layout for portable studies. A `.tolproj` should be able to live beside a managed assets directory containing the CAD files, snapshots, generated report assets, and other durable project artifacts. External CAD references may still be supported, but the end-to-end fixture should prove the portable case first.

Add a packaged-project export/import path for sharing or archiving a study. Use `.tolpack` as the preferred package extension unless a later naming review chooses a better one. A `.tolpack` is a single portable archive that contains the `.tolproj` plus its managed project assets.

## Conservative Write Scope

- Entry point wiring in `pyproject.toml`
- Integration fixtures/tests
- `docs/cad_1d_tolerance_tool/`
- Small glue fixes across CAD-specific modules created by P01-P06

## Deliverables

- Launchable CAD 1D tolerance GUI entry point.
- End-to-end fixture path: open/import or load fixture project, show summary, drill into detail, update tolerance, see results, generate report.
- `.tolproj` CAD rehydration: loading a project must resolve persisted `CadDocument.source_path` values, reimport/display the referenced neutral CAD document in the OCCT AIS/V3d viewer when the file exists, and show a clear missing-source status when it does not.
- Project-local assets: support a portable layout where CAD files, snapshots, and generated report assets are stored beside the `.tolproj` under a predictable assets directory, and persisted paths are relative when possible.
- Packaged project export/import: support packaging a `.tolproj` and its managed assets into a single `.tolpack` archive, and loading/unpacking that archive back into an equivalent project folder.
- UI fidelity gap list against visual evidence.
- UI fidelity gap list against the targeted visual review, including exact unreadable labels/symbols that need new crops.
- Packaging/dependency notes for the primary CAD viewer runtime: Python 3.12, `pythonocc-core 7.7.2=*novtk*`, PyQt6, `load_backend("pyqt6")`, and `qtViewer3d`/AIS/V3d. Confirm PyQt5/Qt5 and Conda `pyqt` are not introduced.
- End-to-end confirmation that viewer selection and report snapshots remain B-Rep-backed through `ShapeReference` / `FeatureReference` ids, not PyVista/VTK or mesh-only ids.
- Final verification notes.

## Practical `.tolproj` Load Behavior

The expected user-visible behavior is:

1. User opens `caster_study.tolproj`.
2. The app loads saved stackups, contributors, warnings, snapshots, reports, and dashboard rows.
3. The app reads each persisted CAD source path, such as `fixtures/cad_1d_tolerance/neutral_step_two_part_loop.step`.
4. The app resolves that source path against sensible locations, including the project file directory and the repository/fixture root used by tests.
5. If the STEP/IGES file exists, the app imports it through the CAD geometry adapter and displays the B-Rep-backed model in the OCCT viewer.
6. If the STEP/IGES file is missing, the app leaves the tolerance data loaded and shows a clear status/message such as `CAD source not found: neutral_step_two_part_loop.step`.

This behavior must not be satisfied with a screenshot, mesh-only placeholder, or table-only load. The viewport/model references used for selection, highlighting, snapshots, and reports must remain tied to serializable `ShapeReference` / `FeatureReference` ids.

## Recommended Project Asset Layout

Use a portable default layout like:

```text
caster_study.tolproj
caster_study_assets/
  cad/
    neutral_step_two_part_loop.step
  snapshots/
    snapshot_summary_1.png
  reports/
    report.html
    images/
    css/
```

In this layout, persisted paths should be relative to the `.tolproj` location whenever practical, for example:

```json
{
  "source_path": "caster_study_assets/cad/neutral_step_two_part_loop.step",
  "snapshots": [
    {
      "image_path": "caster_study_assets/snapshots/snapshot_summary_1.png"
    }
  ]
}
```

This keeps a study portable as a folder that can be copied, zipped, or archived. If the user chooses to keep CAD files external, the project should still store the original absolute path plus hash metadata and report a clear missing-source status if that external path is unavailable.

## Packaged Project Format

Use `.tolpack` for the single-file portable project package. The name should mean "tolerance package" to users. Avoid `.tolprojz` unless there is a strong reason to emphasize that it is a zipped `.tolproj`; it is harder to read and easier to mistype.

Recommended behavior:

1. User chooses `Package Project`.
2. The app creates one file such as `caster_study.tolpack`.
3. The package contains the `.tolproj` and the managed asset directory.
4. Paths inside the packaged `.tolproj` remain relative to the package root.
5. Loading a `.tolpack` unpacks or mounts it into a normal project folder, then opens the contained `.tolproj`.

Recommended internal package layout:

```text
project.tolproj
assets/
  cad/
    neutral_step_two_part_loop.step
  snapshots/
    snapshot_summary_1.png
  reports/
    report.html
    images/
    css/
manifest.json
```

`manifest.json` should include package format version, created timestamp, project title, project file name, asset list with hashes, and the original project schema version. Keep the archive format deterministic enough for tests: stable file order, stable metadata where possible, and no machine-specific absolute paths inside the package.

## Integration Test Expectations

- Loading the fixture `.tolproj` must populate the summary table without modal dialogs.
- The same load path must attempt CAD source rehydration and call the viewer/display path when the neutral CAD source exists.
- A missing CAD source fixture must keep the project data visible and report a clear missing-source status.
- The fixture project should use or exercise project-local relative asset paths for CAD and snapshots.
- Package/export tests should prove a project folder can be written to `.tolpack` and loaded back with relative CAD/snapshot/report asset paths intact.
- The fixture flow must support drilldown, tolerance edit/recalculate, snapshot request metadata, and HTML report generation from the same loaded project session.

## Verification

```powershell
$env:PYTHONPATH="src"; python -m unittest discover -s tests
```

Primary viewer/runtime verification:

```powershell
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s -m unittest discover -s tests
```

Manual smoke:

```powershell
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s -m mechanical_design_tool_suite.cad_tolerance_gui
```

## Non-Goals

- No native commercial CAD import.
- No external CAD add-ins.
- No full installer polish if OCCT dependency packaging remains unresolved.

## Stop Condition

Stop when the end-to-end prototype path is launchable or the remaining blocker is documented with exact error output and the next engineering decision.
