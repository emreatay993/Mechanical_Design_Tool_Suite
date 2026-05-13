# UI/UX Design Spec

## Fidelity Target

Target at least 95% fidelity to the visible standalone demo workflow where feasible, using independent branding and assets. If a later agent is uncertain about a UI detail, it must inspect `extracted_specs/2026-05-12_eztol_targeted_visual_review.md`, `output/transcribe/eztol-demo-media-1080p/EZtol-Demo_Media_1080p.viewer.html`, and the visual review key frames before inventing a replacement.

## Primary Workflows

- Import neutral CAD file and inspect the generated assembly tree.
- Create a new stackup through guided endpoint, direction, plane, part, and constraint selections.
- Review auto-generated contributors in a dense table.
- Edit linear tolerances, tolerance type, sensitivity, and nominal values inline.
- Add manual GD&T/GPS contributors and datum references through compact dialogs.
- Switch between summary dashboard, stackup detail, results, and contribution views.
- Capture snapshots and generate a browser-style report.

## App Shell

- Top area uses a compact Windows desktop title/menu/ribbon style.
- Ribbon-like tabs visible in the demo: `Stackup`, `Report`, and `Data`.
- Avoid a web-app hero, cards, or large decorative navigation.
- Default window should open directly into the CAD analysis workspace.

## Main Layout

| Region | Purpose | Required Details |
| --- | --- | --- |
| Left model browser | Imported assembly and part hierarchy | Tree with disclosure arrows, small yellow folder/part icons, home/assembly-view icon row, light-blue selected rows. |
| Center viewport | CAD model interaction and annotations | Primary viewer must be OCCT AIS/V3d embedded in PyQt6 with B-Rep-backed selection. Light-gray background, shaded CAD rendering, axis triad bottom-left, view cube or orientation widget top-right, vertical navigation toolbar on the right edge. |
| Right analysis pane | Summary and stackup detail | Switches between summary dashboard and selected stackup detail; thin gray splitters; compact tables. |
| Bottom/right result area | Result visualization | `Results` and `Contributions` tabs, red/green bars, green bell-curve plots, blue contribution bars. |

## Screen Inventory

| Screen | Purpose | Inputs | Outputs | Notes |
| --- | --- | --- | --- | --- |
| Import/Open | Select neutral CAD file | STEP/IGES path and import options | CAD document and assembly tree | Windows-style file dialog followed by compact import options dialog. |
| Main summary | Manage all stackups | Imported CAD, stackup list | Status dashboard and model annotations | Title `Summary of 1D Tolerance Stackups`; table columns include `OK`, `Name`, `Nominal`, `Objective`, `Target Quality`, `Results`, `Predicted Quality`, `#Dims`. |
| Guided stackup wizard | Define a new 1D requirement | Endpoint, direction, plane, loop parts, constraints | New stackup and generated contributors | Use mini-toolbar prompts and selection filtering rather than a large modal wizard. |
| Stackup detail | Edit contributors | Contributor rows, tolerance values, datums | Updated result and warnings | Back chevron, centered title like `Stackup# details`, export/report icon, gear icon. |
| Add geometric tolerance | Define GD&T/GPS contributor | Feature, control type, tolerance value, datum references | GD&T row in stackup table | Compact Windows-style dialog; manual first. |
| Settings | Set defaults | Default tolerances, analysis type, target quality | Project/application defaults | Must include block/default tolerance behavior from transcript. |
| Contributions | Identify drivers | Current stackup result | Ranked contribution bars and percentages | Blue horizontal bars; table/list with contributor names and percentages. |
| Report viewer | Review/export report | Project results and snapshots | HTML report, later PDF | Browser-style report with dark left navigation rail and white report canvas. |

## Observed Controls To Reproduce

- Ribbon tabs/actions: `File`, `Tolerance Stackup`, `View`, `New Stackup`, `Add Feature`, `Snapshot`, `Generate Report`, `Import`, `Export`.
- Launch/open state: a neutral clone should keep the observed `Open` command, left `No Browser` dock pattern, status bar, and Windows open dialog structure while limiting file types to STEP/IGES.
- Import dialog: use `Options` and `Select` tabs, object filters for `Solids`, `Surfaces`, `Meshes`, `Wires`, `Work Features`, and `Points`, unit handling, assembly/part options, file path fields, `OK`, and `Cancel`.
- Guided mini-toolbar labels: `Selection 1`, `Width 1`, `Selection 2`, `Width 2`, `Direction`, `Analysis Plane`, `Dimension Location`, component/mating-face counters, green check, red X, plus/add, and dropdown/list button.
- Guided prompts: `Select a face, edge or vertex`, `Select a direction reference`, `Select a work plane or planar face`, and component/constraint prompts matching the current workflow step.
- Detail table rows should support nested part/feature/dimension entries such as part names, `Hole`, `Shaft`, `Face`, `Dimension`, result row, and `Objectives` row.
- Shared-dimension marker: use a small stacked-page icon with tooltip listing affected stackups.
- Non-1D warning: yellow triangle icon plus bold text `Calculated results are ignoring potentially significant 3D effects`.
- Dashboard rollup badges: green objectives-met count, red objectives-not-met count, and red predicted/target sigma rollup pill.
- Report save: Windows `Save Report` dialog followed by browser report output.

## Detailed Visual Style

- Palette: Windows neutral grays and whites, medium-gray viewport, dark charcoal title bar, small orange file/app accent.
- Status: green for pass, red for fail, yellow for caution or possible non-1D effects.
- Annotations: saturated blue for input dimensions; saturated red for stackup/result dimensions.
- Selection: light-blue rows in trees/tables; translucent colored geometry highlights in viewport.
- Typography: Segoe UI-like desktop font, 10-12 px for trees/tables, 13-16 px for pane titles.
- Tables: dense grids, thin borders, inline text editors, dropdowns, horizontal and vertical scrollbars.
- Iconography: small desktop toolbar icons; gear/settings, back chevron, report/export, home, check/X, warning triangle, part/folder tree icons, GD&T/tolerance symbols.

## Interaction Patterns

- Selection-driven prompts: the current workflow step determines valid geometry picks and visible instructions.
- Direct manipulation: annotation labels can be placed and moved in the viewport.
- Table-first editing: generated stackup contributors are edited in a spreadsheet-like grid.
- Summary-detail navigation: selecting a dashboard row opens a detail view; back chevron returns to summary.
- Immediate recalculation: editing tolerance values updates result indicators and contribution charts.
- Shared-dimension warning: editing a shared dimension must reveal affected stackups before or during the edit.
- Report snapshots: user should be able to arrange annotations for readability before capture.
- Result mode switching: provide compact menu or selector for `Worst Case`, `RSS`, and `Statistical`; exact statistical submenu labels remain a visual uncertainty.
- Table editing: active row is light blue, active cell is outlined, failed result/objective rows tint pale red/pink.

## Visual Evidence Reference

- `output/transcribe/eztol-demo-media-1080p/visual_evidence/sheet_002.jpg`: import options, main app, viewport selections.
- `output/transcribe/eztol-demo-media-1080p/visual_evidence/sheet_003.jpg`: detail table, result bar, settings, inline edits.
- `output/transcribe/eztol-demo-media-1080p/visual_evidence/sheet_004.jpg`: pass/fail bars and geometric tolerance dialogs.
- `output/transcribe/eztol-demo-media-1080p/visual_evidence/sheet_005.jpg`: vertical detail case and bell-curve panel.
- `output/transcribe/eztol-demo-media-1080p/visual_evidence/sheet_007.jpg`: summary/detail/contribution transitions and report output.
- `docs/cad_1d_tolerance_tool/extracted_specs/2026-05-12_eztol_targeted_visual_review.md`: detailed frame-by-frame UI review from 58 key frames and 28 five-second sheets.
- `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-12/key_frames/`: high-resolution workflow frames to inspect before UI implementation.

## Visual Fidelity Gaps To Resolve During UI Work

- Exact GD&T symbol glyphs and material-condition modifiers are not reliably readable from the review frames.
- Exact tolerance-type dropdown labels are not fully legible.
- Exact statistical submenu labels under `Statistical` are not fully legible.
- Some key-frame timestamps and five-second contact-sheet timestamps do not perfectly align. Use the source video viewer and key-frame filenames when sequence matters.

## Mockups

Tracked mockups should be added under `mockups/`. Any mockup that claims EZtol-style fidelity must cite the visual evidence sheet and timestamp range it reproduces.
