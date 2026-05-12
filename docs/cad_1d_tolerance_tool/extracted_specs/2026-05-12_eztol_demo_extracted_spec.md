# EZtol Demo Extracted Specification

This document captures observed behavior and visual design details from the local EZtol demo video context pack. It is an evidence layer, not the final implementation plan. Promote stable requirements into the numbered product documents in `docs/cad_1d_tolerance_tool/`.

## Evidence Sources

- Video context pack: `output/transcribe/eztol-demo-media-1080p/README.md`
- Timestamped transcript: `docs/cad_1d_tolerance_tool/source_artifacts/transcripts/2026-05-12_eztol_demo_timestamped_transcript.md`
- Captions: `docs/cad_1d_tolerance_tool/source_artifacts/captions/2026-05-12_eztol_demo_captions.vtt`
- Visual evidence sheets: `output/transcribe/eztol-demo-media-1080p/visual_evidence/sheet_*.jpg`

## Product Intent

Build a standalone CAD-based 1D tolerance analysis tool inspired by the demo workflow. The target is high UI/UX fidelity to the demonstrated prototype while using independent branding, independent implementation, and neutral CAD formats first.

The clone target is not a general 3D tolerance solver. The core value is guided 1D stackup creation from imported CAD geometry, editable dimension/tolerance schemes, GD&T/GPS-style contributor entry, dashboard results, contribution ranking, snapshots, and report output.

## Transcript-Derived Functional Requirements

### Stackup Semantics

- `00:00:00-00:02:12`: Support assembly-level tolerance studies with part-level control details.
- `00:00:27-00:02:12`: Represent a loop from one side of the assembly to the other, including parts, features, dimension contributors, tolerance type, nominal contribution, sensitivity, and variation contribution.
- `00:00:40-00:01:45`: Support linear tolerances plus 1D effects from runout, position, profile/ISO position equivalents, and datum references.

### CAD Import And File Management

- `00:02:35-00:04:55`: Provide a standalone desktop app that imports CAD geometry.
- `00:03:14-00:04:03`: Preserve enough link/reference metadata to refresh or reattach analysis to a revised source model when feasible.
- Local constraint from user: initial supported CAD formats should be limited to non-commercial neutral formats. P0 formats are STEP AP203/AP214/AP242 and IGES. STL/OBJ may be allowed later for visualization only because they do not preserve reliable B-Rep topology for stackups.
- `00:04:27-00:04:55`: Provide commands for defining stackups, taking snapshots, regenerating reports, importing/exporting analysis data, and saving analysis as a standalone project file.

### Guided Stackup Definition

- `00:04:55-00:06:02`: New stackup creation launches a guided selection flow with mini-toolbar/tooltips.
- `00:05:04-00:05:24`: User selects face, edge, or vertex endpoints that define the measurement being studied.
- `00:05:25-00:05:45`: If an endpoint is cylindrical or otherwise ambiguous, prompt for stackup direction from an edge, axis, or surface normal.
- `00:05:45-00:06:02`: User selects an annotation plane and can drag/place the nominal value annotation in the viewport.
- `00:06:02-00:07:01`: User selects parts in the loop and assembly constraints between parts. Selection should be filtered by expected part, feature type, and stackup direction.

### Dimension Scheme Generation And Editing

- `00:07:01-00:08:03`: After loop creation, display involved parts and automatically derive stackup dimensions between selected constraint surfaces.
- `00:07:18-00:07:50`: Propose an effective dimensioning scheme but allow manual adjustment for drawing-specific schemes.
- `00:07:50-00:08:14`: Default tolerances, default analysis type, and quality metrics come from application settings.
- `00:08:14-00:10:14`: Allow inline editing of linear tolerances such as `+/-0.05`, `+/-0.075`, and `+/-0.25`.
- `00:09:07-00:09:19`: Traditional tolerance types include symmetric plus/minus and limits; geometric tolerances are a distinct mode.
- `00:09:19-00:10:01`: User can add an intermediate/reference feature into the loop when the drawing dimension scheme uses a feature not initially selected.
- `00:10:14-00:10:36`: Reused parts inherit previously defined dimensioning/tolerance schemes.

### GD&T / GPS Contributor Entry

- `00:12:05-00:13:49`: Support direct GD&T/GPS-style controls in the stackup.
- `00:12:11-00:12:26`: User can assign datum labels and define runout, such as bushing ID runout `0.1` to OD datum `A`.
- `00:12:26-00:12:42`: User can define position tolerance, such as hole position `0.15` to datum `A`.
- `00:12:42-00:13:14`: User can add/rename features as datums and define ISO/GPS-equivalent position controls.
- `00:13:33-00:13:49`: Tolerance values remain editable after definition.

### Results, Quality, And Warnings

- `00:13:49-00:15:45`: Stackups are nameable, have objective limits such as `+/-0.750`, and calculate against those objectives.
- `00:14:08-00:14:49`: Results compare calculated variation against requirements with green/red status indicators and a summary table.
- `00:14:51-00:15:03`: Analysis modes include worst case and RSS.
- `00:15:03-00:15:45`: Statistical analysis supports quality metrics such as Cp/Cpk, achieved variation at a target quality level, and achieved quality at a target tolerance.
- `00:15:55-00:19:07`: Because the tool is 1D, it should warn when geometry suggests rotation, offsets, or other 3D effects may invalidate a pure translational result.
- `00:24:18-00:25:56`: Angular deviation is explicitly out of scope for the 1D tool.

### Multiple Requirements, Drilldown, And Contributions

- `00:19:07-00:21:08`: Manage multiple assembly requirements that can share one dimensioning scheme.
- `00:19:41-00:20:22`: Show multiple stackups on the model and summarize them in a dashboard, including examples like surface flushness, overall height, wheel clearance, and axial wheel clearance.
- `00:20:22-00:21:08`: Dashboard rows show pass/fail, possible non-1D effects, objective, target quality, analysis type, statistical metrics, results, and contributor count.
- `00:21:08-00:22:09`: Drill into each stackup to a spreadsheet-like tolerance table.
- `00:21:21-00:21:42`: Shared dimensions are marked so the user sees which other requirements are affected by tolerance changes.
- `00:21:42-00:22:09`: Contributions view ranks tolerances by percent contribution to variation.

### Snapshots And Reports

- `00:04:32-00:04:45` and `00:15:45-00:15:55`: Users can reposition annotations for report clarity and capture snapshots.
- `00:22:09-00:23:36`: Reports include snapshots, dashboard summary, loop diagrams, tolerance tables, results, and contribution plots.

## Visual UI Inventory

- App shell: compact desktop application with dark Windows title bar, small top-left app/file icons, ribbon-like tabs named `Stackup`, `Report`, and `Data`.
- Main layout: three-pane work area with left assembly browser, center 3D CAD viewport, and right analysis pane. Splitters are thin gray dividers.
- Left browser: assembly hierarchy with disclosure arrows, yellow part/folder icons, home/assembly-view icon row, and light-blue selected rows.
- Viewport: light gray background, shaded CAD model, axis triad at bottom left, view cube/navigation widget at top right, vertical navigation toolbar on right edge.
- Viewport annotations: red stackup/result dimension arrows, blue input dimension arrows, leader lines, draggable labels, and colored selected faces/parts.
- Right summary pane: title `Summary of 1D Tolerance Stackups`, gear icon, table columns including `OK`, `Name`, `Nominal`, `Objective`, `Target Quality`, `Results`, `Predicted Quality`, and `#Dims`.
- Summary status: green check for pass, red/yellow fail or caution icons, pale green/red row backgrounds, and light-blue active-row selection.
- Detail pane: back chevron, centered title like `Stackup# details`, export/report icon, gear icon, and dense editable grid.
- Detail grid: columns include `Name`, `Sens`, `Nominal`, `Tolerance`, and `Datum`; hierarchical rows use bracket/glyph indentation and inline editors/dropdowns.
- Results area: tabs `Results` and `Contributions`; shows red/green worst-case bars, green bell-curve statistical plots, large summary badges, or blue contribution bars.
- Dialogs: Open, Import Options, Settings, Add Geometric Tolerance, feature/constraint dialogs, report save, variation/sensitivity dialogs.
- Report surface: browser-like report with black left navigation rail, large white report canvas, summary table, embedded model/dimension screenshots, tolerance tables, and plots.

## Visual Style System

- Overall style: dense engineering desktop UI, not a marketing app.
- Colors: Windows neutrals, white panes, light-gray dividers, medium-gray viewport, dark charcoal title bars, orange app/file accent.
- Engineering annotations: saturated blue for input dimensions and saturated red for stackup/result dimensions.
- Status colors: green pass/acceptable, red fail/out of spec, yellow caution/non-1D warning.
- Typography: compact Segoe UI-like tables and trees around 10-12 px, bolder panel titles around 13-16 px.
- Tables: thin borders, alternating very light rows, inline text boxes/dropdowns, scrollbars, high information density.
- Icon style: small Windows-style toolbar icons, gear/settings, back chevron, export/report, home, check/X status badges, warning triangle, folder/part tree icons, and GD&T/tolerance symbols.

## Visual Evidence Map

- `sheet_001.jpg`: `00:00-03:10`, slide intro, launch, and file-open flow.
- `sheet_002.jpg`: `03:20-06:50`, import options, main app, viewport selection, and red/blue annotations.
- `sheet_003.jpg`: `07:00-09:10`, detail table, worst-case result bar, settings, and inline edits.
- `sheet_004.jpg`: `10:00-12:50`, pass/fail bars, summary badges, and geometric tolerance dialogs.
- `sheet_005.jpg`: `13:20-16:50`, vertical case details, tolerance edits, and bell-curve result panel.
- `sheet_006.jpg`: `17:10-19:40`, CAD add-in screens and multi-stackup summary.
- `sheet_007.jpg`: `20:00-23:40`, summary/detail/contribution transitions and report output.
- `sheet_008.jpg`: `23:50-26:30`, CAD add-in transitions, context menu, variation/sensitivity dialogs, and plots.
- `sheet_009.jpg`: `26:40-29:40`, final analysis state and outro transition.
- `sheet_010.jpg` and `sheet_011.jpg`: `30:00-33:20`, outro slides only.

## Explicit Non-Goals For Initial Clone

- Native commercial CAD file import is not P0. Limit P0 to neutral formats.
- Direct CAD PMI import is not P0. Manual GD&T/GPS contributor entry is P0; STEP AP242 PMI reading is an optional spike.
- Thermal expansion is not supported in the demonstrated release and is not P0.
- Angular deviation and full 3D tolerance analysis are not P0. The tool should detect/warn on likely non-1D effects instead.
- External CAD add-ins, such as SOLIDWORKS integration, are not P0 for the standalone neutral-format clone.

## Open Questions

- Exact threshold rules for non-1D geometry warnings are not stated in the video.
- Exact report output format is not stated; HTML is a practical first target because the demo report is browser-like.
- Exact project file schema is not visible; this repo already has `.tolproj` JSON, so the CAD tool should extend that pattern.
- Exact dialog field labels are sometimes fuzzy in the visual sheets. Agents must revisit the local video viewer before implementing any uncertain dialog.
