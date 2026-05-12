# EZtol Demo Targeted Visual Review

This document records the deeper visual review requested before implementation. It supersedes the earlier coarse 10-second contact-sheet pass for UI/UX fidelity work.

## Review Method

- Source video: `output/transcribe/eztol-demo-media-1080p/EZtol-Demo_Media_1080p.mp4`
- Review pack: `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-12/`
- Key frames: `visual_review_2026-05-12/key_frames/*.jpg`
- Dense sheets: `visual_review_2026-05-12/five_second_sheets/ui_5sec_sheet_*.jpg`
- Key frame manifest: `visual_review_2026-05-12/key_frame_manifest.tsv`

The pass extracted 58 high-resolution key frames at workflow/dialog timestamps and 28 five-second contact sheets covering the actual UI/report portion from about `00:02:30` to `00:29:45`.

## Implementation Rule

Any agent implementing UI, workflow, report, table, or result presentation must reread this file and inspect the referenced frames before making design decisions. If a control or label is uncertain, implement the demonstrated structure and leave the exact small label as a documented gap rather than inventing a polished alternative.

## Launch, Open, And Import

### `00:02:35` - Launch State

- Main title reads `EZtol`; canvas is a blank gray gradient.
- Top ribbon shows `File` and `Get Started`; the `File` tab is highlighted orange.
- Large `Open` command uses a folder icon.
- Left dock shows a `No Browser` dropdown, close `X`, and help `?`.
- Status bar shows `Loading ...`; lower counters show `0` and `0/0`.
- Source branding appears at lower-left in the original; clone should use independent branding but preserve the placement pattern.

### `00:02:50` - Open Dialog

- Standard Windows `Open` dialog is centered over the app.
- Dialog fields/buttons include `File name`, `Files of type`, `Project File: Default.ipj`, `Projects...`, `Find...`, disabled `Options...`, `Open`, `Cancel`, and `Preview not available`.
- File list columns include `Name`, `Date modified`, `Type`, and `Size`.
- Original file type list includes many native/commercial CAD formats, but the clone must filter initial support to neutral formats only: STEP and IGES.

### `00:03:20` - Import Options

- Adjacent frame sheets show `Import: caster.sldasm`.
- Dialog has `Options` and `Select` tabs.
- Object filters include `Solids`, `Surfaces`, `Meshes`, `Wires`, `Work Features`, and `Points`.
- Import dialog includes import type, object filters, unit/length handling, assembly/part options, file name/location fields, `OK`, and `Cancel`.
- For the neutral-format clone, preserve the dialog structure but adapt labels/options to STEP/IGES import.

## Main Workspace And Guided Stackup

### `00:04:10` - Main Workspace

- Window title area reads like `EZtol    caster`.
- Ribbon tabs: `File`, `Tolerance Stackup`, `View`.
- Ribbon groups/actions: `Stackup`, `Report`, `Data`, `New Stackup`, disabled `Add Feature`, `Snapshot`, disabled `Generate Report`, `Import`, `Export`.
- Left model browser has `Model`, `Assembly View`, and an assembly tree rooted at `caster.iam`.
- Visible model tree entries include `3rd Party`, `Relationships`, `Representations`, `Origin`, `top_plate:1`, `axle_support:1`, `bushing:1`, `axle:1`, `wheel:1`, `bushing:2`, `axle_support:2`.
- Workspace split is 3D viewport left/center and analysis pane right.
- Summary title: `Summary of 1D Tolerance Stackups`.
- Summary columns: `OK`, `Name`, `Nominal`, `Objective`, `Target Quality`, `Results`, `Predicted Quality`, `#Dims`.
- Lower right tabs: `Results`, `Contributions`.

### `00:04:35` - Snapshot Tooltip

- `Snapshot` tooltip: `Sets the current view orientation and size for the report image.`
- ViewCube/orientation widget and vertical navigation toolbar are visible.

### `00:05:00-00:05:48` - Endpoint, Direction, Plane

- `New Stackup` activates a floating mini-toolbar near the model.
- Mini-toolbar step labels include `Selection 1`, `Width 1`, `Selection 2`, `Width 2`, `Direction`, `Analysis Plane`, and `Dimension Location`.
- Confirmation controls include green check, red X, and a small dropdown/list button.
- Prompt text includes `Select a face, edge or vertex`, `Select a direction reference`, and `Select a work plane or planar face`.
- Cylindrical bushing features highlight translucent green; active/hovered faces use red outlines or red translucent fills.
- Direction and annotation graphics use red/blue arrows and `0.000` labels.

### `00:06:08-00:06:52` - Loop And Constraint Selection

- Prompt changes to `Select the component that mates with bushing:2`.
- Mini-toolbar counters change through `1 Components`, `Face`, `Width`, `0 of 0 Mating Faces`, `5 Components`, `0 of 8 Mating Faces`, and `6 of 8 Mating Faces`.
- Constraint prompt: `Select a face, edge or vertex from bushing:2 that mates with axle_support:2`.
- Eligible features are green; selected/active areas are red.
- After completion, `Add Feature` and `Generate Report` become enabled.

## Stackup Detail, Editing, And GD&T

### `00:07:05-00:08:35` - Generated Detail Table

- Detail title: `Stackup1 details`.
- Header icons: back arrow, camera/snapshot, gear.
- Detail columns: `Name`, `Sens`, `Nominal`, `Tolerance`, `Datum`.
- Visible rows include `bushing:2`, `Hole1`, `Dimension1`, `Shaft2`, `axle_support:2`, `Hole3`, `Dimension2`, `Face4`, `top_plate:1`, `Face5`, `Dimension3`, `Face6`, `axle_support:1`, `bushing:1`, `Dimension4`, `Hole1`.
- Values include sensitivities `0`, `+1`, `-1`; hole/shaft diameters near `diameter 12.00` and `diameter 22.00`; tolerances such as `+/-0.05`, `+/-0.1`, `+/-0.25`; linear values `0.0`, `58.0`, and `12.0`.
- Left of the detail table, vertical connector graphics show green/red node markers and arrows for the stackup path.
- Result panel title: `Worst Case Results for Stackup1`.
- Worst-case bar is red/green with center label `0.000` and bounds around `-0.400` and `0.400`.
- Warning text appears with yellow triangle: `Calculated results are ignoring potentially significant 3D effects`.

### `00:08:40-00:09:05` - Inline Edits

- Selected rows are light blue and active cells have a visible outline.
- `Dimension1` is edited to about `+/-0.05`; `Dimension2` is edited to `58.000 +/-0.075`.
- Result bounds visibly tighten after edits.
- A tolerance-type dropdown is visible; exact option labels are too small to confirm. Implement a compact dropdown for symmetric, limits/asymmetric, and geometric/manual modes.

### `00:09:00-00:10:55` - Add Feature And Reuse

- `Add Feature` flow uses the same floating in-canvas toolbar with selection controls, checkmark, plus, red X, and dropdown.
- Geometry highlights use red, green, and yellow.
- `Stackup2 details` appears with reused structure: `bushing:2`, `axle_support:2`, `top_plate:1`, `axle_support:1`, `bushing:1`.
- Datum `A` appears in the `Datum` column and as standalone feature rows.
- Reused supports/bushings show repeated tolerance/datum patterns, including `Dimension2 58.000 +/-0.075`.
- Intermediate top-plate features include `Face5`, `Dimension5`, `Face7`, `Dimension6`, `Face6`, with `Dimension5/6` around `12.00 +/-0.25`.

### `00:10:55-00:13:55` - GD&T And Objectives

- `Add Geometric Tolerance` dialog fields include `Feature Controlled`, a geometric-symbol dropdown, numeric tolerance input, datum/reference input, `OK`, and `Cancel`.
- `OK` is disabled until required fields are complete.
- Dialog examples show controlled features like `Face5` and `A`, tolerance values such as `0.2`, and datum/reference values such as `A` or `Hole1`.
- Table values include manual geometric rows with `diameter 0.1`, `diameter 0.15`, and `diameter 0.5`, with datum `A`.
- Stackup title becomes `vertical coax details`; result row/name becomes `vertical coax`.
- Objective/result rows appear at the bottom of the table.
- `vertical coax` row shows approximately `0.00 +/-0.75`; `Objectives` row later shows `0.00 +/-0.60`.

## Results And Statistical Displays

### `00:12:00-00:16:48` - Mode Menus And Plots

- Result mode dropdowns include `Worst Case`, `RSS`, and `Statistical`.
- Statistical result title: `Statistical Results for vertical coax`.
- Statistical plot shows `Actual: Cpk = 1.60`, `Mean: 0.00`, `Standard Deviation: 0.13`.
- Green bell curve is centered at `0.00`; red/black vertical limits are labeled around `-0.75`, `+0.75`, `-0.60`, and `+0.60`.
- Worst-case display shows a green center band with red out-of-objective regions, with markers around `-0.8`, `-0.6`, `0.0`, `+0.6`, and `+0.8`.
- Detail rows can tint pale red/pink when the objective is not met, such as `vertical coax` with `Cpk = 1.60` versus objective `Cpk = 2.00`.

### `00:20:04-00:20:52` And `00:24:00-00:24:25` - Multi-Stackup Dashboard

- Summary rows observed:
  - `flush left`: nominal `0.00`, objective `+/-0.50`, target `RSS`, result `+/-0.56`, predicted `Cpk = 0.89`, `#Dims = 6`.
  - `flush right`: nominal `0.00`, objective `+/-0.50`, target `RSS`, result `+/-0.62`, predicted `Cpk = 0.80`, `#Dims = 9`.
  - `overall height`: nominal `(110.00)`, objective `<= 110.50`, target `Cpk = 1.10`, result `<= 110.37`, predicted `Cpk = 1.48`, `#Dims = 9`.
  - `clearance above wheel`: nominal `(14.000)`, objective `>= 0.000`, target `Yield = 99.90...`, result `>= 13.426`, predicted `Yield = 100%`, `#Dims = 14`.
  - `axial clearance around wheel`: nominal `(1.000)`, objective `>= 0.000`, target `Sigma = 4.50`, result `>= 0.032`, predicted `Sigma = 7.00`, `#Dims = 13`.
  - `width at bushings`: nominal `(80.0)`, objective `<= 81.0`, target `Cpk = 1.00`, result `<= 80.9`, predicted `Cpk = 1.10`, `#Dims = 13`.
  - `thread engagement`: nominal `(10.00)`, objective `>= 9.80`, target `Worst Case`, result `>= 9.80`, `#Dims = 2`.
  - `thread beneath top surface`: nominal `(2.000)`, objective `>= 0.000`, target `Worst Case`, result `>= 1.700`, `#Dims = 3`.
  - `width at top of supports`: nominal `130.000`, objective `+/-1.560`, target `Cpk = 1.50`, result `+/-1.352`, predicted `Cpk = 1.73`, `#Dims = 11`.
- Result summary panel uses large badges: green `7` objectives met, red `2` objectives not met, red pill `2.83 / 3.36` for predicted/target sigma rollup.
- Failed rows are pale red/pink with red icons; passing rows use green check icons; selected rows use pale blue.

### `00:21:10-00:21:54` - Drilldown, Shared Markers, Contributions

- Selecting a dashboard row opens `overall height details`.
- Visible detail rows include `ID`, `Axle`, `A`, `coaxiality of OD to A`, `OD`, `Asm shift OD-A`, and `Wheel`.
- Shared-dimension marker appears as a small stacked-page icon.
- Shared marker tooltip lists affected stackups such as `overall height` and `clearance above wheel`.
- `Contributions` tab title: `Statistical Contributions for overall height`.
- Blue horizontal bar chart examples:
  - `top_plate | bottom face for support arm`: `54.9%`.
  - `Asm shift OD-A`: `14.8%`.
  - `axle | OD`: `8.8%`.
  - `axle_support | hole for bushing`: `8.8%`.
  - `wheel | OD`: `8.8%`.
  - `bushing | ID`: `2.2%`.
  - `Wheel | A`: `0.5%`.
  - `Wheel | OD`: `0.5%`.

## Report Output

### `00:22:18-00:22:42` - Save Report

- `Generate Report` command is available on the ribbon.
- Save dialog title: `Save Report`.
- File list includes `css`, `images`, `js`, and `report.html`.
- Fields/buttons include `File name`, `Save as type: All Files (*.*)`, `Save`, `Cancel`, `New folder`, and search box.

### `00:22:55-00:23:38` - Browser Report

- Browser URL resembles `file:///C:/data/Demos/Caster - EZtol completed/test5/report.html`.
- Report has a fixed dark left navigation rail with source logo and links: `Summary`, `flush left`, `flush right`, `overall height`, `clearance above wheel`, `axial clearance around wheel`, `width at bushings`, `thread engagement`, `thread beneath top surface`, `width at top of supports`.
- Main canvas is white with gray typography, bordered model images, dashboard summary tables, result sections, and contribution sections.
- Title page shows `Tolerance Stackup Report`, `caster.iam`, date, and time.
- Report summary table mirrors the in-app dashboard.
- `flush left Analysis Results` shows `RSS Results for flush left`, `Mean: 0.00`, `Standard Deviation: 0.19`, green central tolerance band, red out-of-limit side bands, and warning text.
- `flush left Analysis Contributions` uses blue bars, including `Asm shift clr hole-major DIA` around `62.2%` and `axle_support | clr hole` around `17.1%`.
- `axial clearance around wheel` report section shows a large annotated caster image with blue dimension callouts and red `1.000`; visible labels include `27.5`, `diameter 10.50`, `diameter 9.866`, `12.5`, `117.5`, `39.0`, and `5.0`.

## CAD Add-In And Late-Demo Context

Native CAD add-ins are out of scope for the neutral-format clone, but the late demo provides useful interaction references.

- SolidWorks context shows a `CETOL 6 Sigma` ribbon with modes `1 Assemble Mode`, `2 Dimension Mode`, `3 Analyze Mode`.
- Commands include `Read From CAD`, `Read from CXM`, `Save to CXM As`, `Options`, `Solve`, `View Results`, `Show Locations`, `Visualize Worst Case`, `Visualize Sensitivities`, and `Visualize Response`.
- `CETOL Properties` panel includes `Measurement Type: Linear`, `CAD Nominal: 0 mm`, `Solved Nominal: 0 mm`, `Reverse Sign`, `References`, `Requirements`, `Notes`, `Start Feature`, `End Feature`, and `Direction Feature`.
- `View Results` dialog includes tabs `Details`, `Requirements`, `Sensitivities`, `Contributions`, `Notes`, a range bar, normal distribution details, standard deviation, and min/max.
- Context menu includes `Make Nominal`, `Visualize Sensitivities`, `Visualize Response`, `View Result >`, `Color Image in Document`, and `Save Image to File...`.
- `Visualize Sensitivities` dialog includes variable selector, red line plot, range limits, `Scale From Tolerance`, `Scale Factor`, `Intervals`, measurements table with `Name`, `Value`, `Sensitivity`, `Context`, and buttons `Recalculate`, `Stop Animation`, `Close`.

## Remaining Visual Uncertainties

- Some GD&T symbols and material-condition modifiers are too small to read reliably from the review artifacts.
- Tolerance-type dropdown labels are visible but not fully legible.
- Statistical submenu labels under `Statistical` are not fully legible.
- Some key-frame labels and five-second-sheet timestamps do not perfectly align; use the key frame filenames and source video viewer when exact sequence matters.
- Five-second sheets go black after about `27:10`; final sigma/final-state observations rely on high-resolution key frames and earlier visual evidence sheets.

## Required Implementation Follow-Up

- UI shell workers must implement the observed ribbon/action names, three-pane split, summary/detail columns, mini-toolbar labels, row colors, status badges, and warning presentation.
- Workflow workers must implement the exact guided selection states before adding new workflow abstractions.
- Report workers must implement the browser-like report layout with dark left nav, white report canvas, summary table, result sections, contribution sections, and annotated snapshot images.
- Any exact symbol/dropdown that remains unreadable must be documented as a fidelity gap and revisited with a new crop from the source MP4.
