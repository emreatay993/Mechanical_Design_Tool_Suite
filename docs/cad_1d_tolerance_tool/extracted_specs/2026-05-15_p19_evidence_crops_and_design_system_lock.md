# P19 Evidence Crops And Design System Lock

Date: 2026-05-15

Branch: `codex/p19-evidence-design-lock`

## Scope

This file is the visual/design-system lock for P21-P25 UI, workflow, result, dashboard, and report work. It converts the video evidence into implementation targets so later workers do not rediscover colors, density, pane proportions, or unresolved label boundaries.

The target is pixel-level fidelity to the legible source-frame layout, density, color semantics, and component behavior. Independent branding is still mandatory: do not copy EZtol/Sigmetrix logos, product names, vendor marks, or proprietary art assets. Replace only brand identity while keeping the demonstrated desktop CAD layout, spacing, state colors, workflow structure, and report composition.

## Evidence Reviewed

- `docs/cad_1d_tolerance_tool/overnight_plans/README.md`
- `docs/cad_1d_tolerance_tool/10_full_clone_productization_plan.md`
- `docs/cad_1d_tolerance_tool/overnight_plans/P19_evidence_crops_and_design_system_lock.md`
- Numbered CAD docs `01` through `09`
- `docs/cad_1d_tolerance_tool/extracted_specs/2026-05-12_eztol_demo_extracted_spec.md`
- `docs/cad_1d_tolerance_tool/extracted_specs/2026-05-12_eztol_targeted_visual_review.md`
- `docs/cad_1d_tolerance_tool/extracted_specs/2026-05-14_full_clone_gap_matrix.md`
- `docs/cad_1d_tolerance_tool/extracted_specs/2026-05-15_final_fidelity_audit_and_roadmap.md`
- `docs/cad_1d_tolerance_tool/extracted_specs/2026-05-15_p17_visual_evidence_closeout.md`
- `docs/cad_1d_tolerance_tool/extracted_specs/2026-05-15_p18_adapter_contract_and_viewer_acceptance.md`
- `docs/cad_1d_tolerance_tool/extracted_specs/2026-05-15_p18_live_runtime_packaged_smoke.md`
- `docs/cad_1d_tolerance_tool/source_artifacts/transcripts/2026-05-12_eztol_demo_timestamped_transcript.md`
- `output/transcribe/eztol-demo-media-1080p/EZtol-Demo_Media_1080p.viewer.html`
- `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-12/key_frame_manifest.tsv`
- `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-12/key_frames/*.jpg`
- `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-12/five_second_sheets/ui_5sec_sheet_001.jpg`
- `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-14_full_pass/full_10sec_sheet_*.jpg`

## Visual Lock Policy

| Area | Lock Rule |
| --- | --- |
| 1920x1080 source-frame matching | Treat the 1920x1080 key frames as the primary visual truth. At this size, fixed chrome, tab strips, result panels, row heights, and report nav should aim for `+/-2 px` when Qt/DPI permits and `+/-8 px` when splitter/user-resize constraints apply. |
| Color matching | Use the sampled source-frame tokens below as implementation targets. Keep channel values within roughly `+/-8` RGB for flat UI fills and within the same semantic family for antialiased annotation/plot strokes. |
| Typography and density | Use Segoe UI or the platform equivalent. Preserve compact desktop density: body table/tree text around 10-11 pt logical size, 20-26 px source-frame row heights, and bold pane/table headers. |
| Layout scaling | Preserve source proportions rather than introducing card layouts or web-dashboard spacing. If the window shrinks, protect the right analysis pane and table columns first, then let the viewport compress. |
| Unreadable labels | Do not invent labels, GD&T glyphs, modifiers, or statistical submenu text. Implement the confirmed structure and leave exact wording/glyphs in the unresolved crop list until a crop resolves them. |
| Branding | Clone workflow/layout/styling. Replace vendor logos, marks, and product names with MDTS/independent branding. |

## UI Tokens

The hex values are source-frame samples from the listed evidence frames. Use them as target colors; where antialiasing or transparent CAD overlays affects a sample, the semantic target is noted.

| Token | Target | Evidence | Rule |
| --- | --- | --- | --- |
| Shell title/tab charcoal | `#525252` | Frame `005`, title/tab bar | Main app top strip and inactive tab background. |
| Active file/app tab orange | `#EE842B` | Frame `005`, `File` tab | Use only as the compact app/file accent, not as a dominant page color. |
| Ribbon background | `#F6F6F6` | Frame `005`, ribbon area | Ribbon command field background. |
| Pane/model-browser white | `#FFFFFF` | Frame `005`, browser/right pane | Main tree/table/report surfaces. |
| Thin splitter/grid gray | `#D9D9D9` | Frame `005`, splitter sample | Splitters, table grid, dock borders. |
| Viewport neutral gray | `#C4C4C4` | Frame `005`, CAD viewport | Default CAD viewport background. |
| Table selected row | `#E3EFF9` | Frame `019`, selected detail row | Active table/tree row fill. Use a stronger outline for active cell. |
| Table neutral alternate row | `#F3F3F3` | Frame `019`, unselected row band | Alternating dense grid row fill. |
| Failed/objective row pale red | `#FAF2F2` with stronger edge `#ECCDCE` | Frame `019`, objective row | Out-of-spec rows and failed objective bands. |
| Passing dashboard row pale green | `#EFFBF1` | Frame `057`, dashboard table | Pass/OK row tint. Keep subtle, not saturated. |
| Result fail red | `#B82828` | Frame `014`, worst-case bar mask | Result out-of-objective bar, fail icons, failed status emphasis. |
| Result/pass green | `#109020` | Frames `014`, `033`, result bar/bell curve | Pass bar, bell curve, OK icons, eligible/confirmed state. |
| Warning yellow | `#F8D800` | Frame `014`, non-1D warning icon | Warning triangle and caution affordance. Use black text beside it. |
| Annotation/input blue | Saturated blue family, source stroke includes `#1820D8`; contribution bars use `#0070C0` | Frames `014`, `046`, `051` | Blue dimensions, input callouts, and contribution bars. |
| Annotation/result red | Saturated red family around `#A00000` to `#B82828` | Frames `014`, `049`, `051` | Result/stackup dimension callouts and red nominal dimensions. |
| Report nav dark | `#181818` | Frame `049`, browser report nav | Fixed report navigation rail. |
| Report nav text gray | `#B8B8B8` target family | Frame `049`, nav text | Muted large nav links over dark rail. |
| Report canvas | `#FFFFFF` | Frames `049` through `051` | Report page/canvas and model snapshot backing. |
| Report image border | `#D0D0D0` target family | Frames `049` through `051` | Thin borders around snapshots/tables. |

## Typography And Row Heights

| Surface | Source-Frame Target | Implementation Rule |
| --- | --- | --- |
| Title/tab strip | 14-16 px source-frame text, regular weight | Compact Segoe UI, no oversized product title. |
| Ribbon command labels | 14-16 px source-frame labels with 32-42 px icons | Use small desktop icon+text commands. Keep group labels visible below commands. |
| Model browser tree | 20-22 px row height, 14 px source-frame text, 16 px icons | Disclosure arrow, small folder/part icons, and light-blue row selection. |
| Detail/dashboard table body | 24-26 px row height, compact 14 px source-frame text | Preserve dense spreadsheet behavior; no card/table hybrid. |
| Detail table header | 42-44 px source-frame header band, bold column labels | Headers stay compact and fixed above scrollable rows. |
| Result panel text | 14-16 px labels, bold result title | Plot labels can be smaller but must remain legible at 1920x1080. |
| Report nav | 21-24 px visual text over dark nav | Left nav links are large enough for scanning, not tiny app chrome. |
| Report section titles | 34-48 px source-frame scale depending heading level | Browser report can use larger heading scale than the app panes. |

## Layout Targets

### 1920x1080 Source Frames

| Region | Frame 005 Target | Frame 014 Detail Target | Rule |
| --- | ---: | ---: | --- |
| Title/tab strip | `y=0-56` | `y=0-56` | Dark top strip includes quick commands, tabs, and centered document title. |
| Ribbon command area | `y=57-176` | `y=57-176` | Compact ribbon is about 120 px high at 1080p. |
| Work area | `y=177-1048` | `y=177-1048` | Dock/viewport/pane area. |
| Status bar | `y=1049-1079` | `y=1049-1079` | Thin status/counter strip. |
| Left browser width | `x=0-339` | `x=0-270` | Accept 270-340 px depending state; target 14-18 percent of window. |
| Central viewport width | `x=340-1178` | `x=271-1177` | Target 44-47 percent of window. |
| Right analysis pane width | `x=1180-1919` | `x=1178-1919` | Target about 740 px, 38-39 percent of window. |
| Right pane header | `y=188-262` | `y=188-262` | Header/title/icon band. |
| Right top table | `y=270-744` | `y=270-750` | Top table owns about 54-56 percent of right pane work height. |
| Right lower result/contribution panel | `y=756-1017` | `y=756-1018` | Lower panel owns about 29-31 percent of right pane work height. |
| Right bottom tabs | `y=1018-1046` | `y=1019-1046` | `Results` / `Contributions` tab strip. |

### Smaller Desktop Target

For a 1366x768 class desktop window:

| Region | Target |
| --- | ---: |
| Title/tab strip | 44-50 px |
| Ribbon command area | 96-110 px |
| Status bar | 24 px |
| Left browser | 220-240 px |
| Right analysis pane | 500-520 px |
| Central viewport | Remaining 606-646 px |
| Detail/dashboard row height | 22-24 px |
| Model browser row height | 19-21 px |

Do not replace the right pane with stacked mobile cards at this size. Keep the three-pane desktop structure and allow horizontal table scrollbars like the source.

## Component Rules

### Shell And Ribbon

- First screen is the usable CAD analysis workspace, not a landing page.
- Top structure: dark title/tab strip, active tab in orange, compact ribbon below.
- Visible ribbon tabs/groups must preserve the demonstrated structure: `File`, `Tolerance Stackup`, `View`, with grouped commands for `Stackup`, `Report`, and `Data`.
- Command set: `New Stackup`, `Add Feature`, `Snapshot`, `Generate Report`, `Import`, and `Export`.
- Disabled commands stay visible and gray, as in frames `005` and `006`.
- Use independent app branding. Do not reproduce source logo art.

### Model Browser

- Left dock title row uses `Model`, dropdown indicator, close `X`, help `?`, and a row of compact browser controls.
- Tree root and rows preserve the caster-style hierarchy pattern: assembly root, category nodes, part instances, disclosure arrows, and yellow folder/part icons.
- Selection state is light blue; visibility/part icons remain small and table-dense.
- Browser should not expand into a card or inspector panel.

### Viewport Chrome

- Viewport background target is `#C4C4C4`.
- CAD model stays large and central with enough whitespace for annotations.
- Axis triad stays bottom-left, roughly 42-55 px square in the 1920 source frame.
- ViewCube/orientation widget stays top-right, roughly 58-70 px square.
- Vertical navigation toolbar stays on the right edge of the viewport, about 34 px wide and 190-210 px tall.
- P18 keeps OCCT AIS/V3d as the authoritative B-Rep viewer. The known full-window black native capture caveat does not justify a mesh-authoritative rewrite.

### Guided Mini-Toolbar

- Toolbar appears only while a guided stackup/add-feature workflow is active.
- Required step labels: `Selection 1`, `Width 1`, `Selection 2`, `Width 2`, `Direction`, `Analysis Plane`, `Dimension Location`.
- Required counters/states: `1 Components`, `5 Components`, `0 of 0 Mating Faces`, `0 of 8 Mating Faces`, `6 of 8 Mating Faces`.
- Required controls: green check, red X, plus/add, and dropdown/list.
- Prompt text must match confirmed transcript/review wording where legible: `Select a face, edge or vertex`, `Select a direction reference`, `Select a work plane or planar face`, and mating-feature prompts.
- Selection colors: eligible geometry green, active/selected/problem geometry red or yellow, input/reference annotations blue.

### Detail And Dashboard Tables

- Tables are spreadsheet-dense with vertical and horizontal scrollbars.
- Detail columns lock to `Name`, `Sens`, `Nominal`, `Tolerance`, `Datum`.
- Summary columns lock to `OK`, `Name`, `Nominal`, `Objective`, `Target Quality`, `Results`, `Predicted Quality`, `#Dims`.
- Use tree-like row hierarchy for parts/features/dimensions and vertical connector graphics in detail views.
- Active row fill is `#E3EFF9`; active cell gets a thin dark outline.
- Failed/objective rows use pale red; pass rows use pale green; warning rows use yellow triangle icon plus bold warning text.
- Shared dimensions use a stacked-page icon with tooltip/list of affected stackups.

### Result Bars And Statistical Plots

- Worst-case/RSS bar: white panel, thin black baseline, red out-of-objective segment, green in-objective segment, black center marker, endpoint labels above.
- Statistical plot: white plot box, thin black border, green bell-curve fill, red/black vertical limit lines, metric text above or left.
- Warning strip text stays exactly confirmed: `Calculated results are ignoring potentially significant 3D effects`.
- Do not hide warning state when a row is otherwise green.

### Contribution Bars

- Contribution view uses horizontal blue bars, target `#0070C0`.
- Left labels remain table-like and can include feature-control-frame-style cells where evidence is readable.
- Percent labels appear right of bars.
- Preserve ranking order and compact vertical spacing from frame `046`.

### Dialogs

- Open and Save Report flows use Windows-style dialogs with file name/type fields and `Open`/`Save`/`Cancel`.
- Import options preserve the `Options` and `Select` tab structure, object filters, unit/length handling, assembly/part options, file name/location fields, `OK`, and `Cancel`.
- Initial clone file filters remain STEP/IGES only even though the source dialog lists native/commercial formats.
- Add Geometric Tolerance dialog includes controlled feature, symbol/control dropdown, tolerance input, datum/reference input, `OK`, and `Cancel`; disabled `OK` until required fields are complete.
- Exact tiny option labels and glyphs remain unresolved unless a crop clearly proves them.

### Browser Report

- Report layout is a browser-style HTML report with a fixed dark left nav and white main canvas.
- Source frame `049`: browser nav rail is about 188-190 px wide inside the browser window, target `#181818`.
- Nav links include the summary and stackup names; text is muted gray over dark rail.
- Main canvas is white with thin bordered model images, large section headings, dashboard summary tables, result sections, contribution sections, and annotated CAD snapshots.
- Report snapshots must show actual CAD state and red/blue dimension callouts. Do not use atmospheric or placeholder images.
- Report branding must be independent while preserving the left-nav/logo placement pattern.

## Key-Frame Mapping

| Evidence Area | Key Frames / Sheets | Transcript Anchor | Locked Decisions |
| --- | --- | --- | --- |
| Open/import | `003`, `004`, `ui_5sec_sheet_001.jpg` | `00:02:35-00:04:03` | Windows open dialog, neutral-format file filter, import options modal structure, source reference behavior. |
| Shell/layout/ribbon | `005`, `006` | `00:04:07-00:04:45` | Three-pane desktop workspace, ribbon groups, browser, viewport chrome, right summary pane, report/snapshot commands. |
| Guided workflow | `007` through `013` | `00:04:55-00:07:01` | Floating toolbar, endpoint/direction/plane flow, component/mating counters, filtered selections. |
| Generated detail table | `014`, `015`, `016`, `017`, `018`, `019` | `00:07:01-00:09:19` | Detail title/header icons, dense table columns, row hierarchy, inline edits, tolerance dropdown structure. |
| Add feature/reuse | `020` through `024` | `00:09:19-00:11:20` | Add Feature reuse, repeated part scheme propagation, result bar/badge behavior. |
| GD&T/GPS | `025` through `029` | `00:12:05-00:13:49` | Manual GDT/GPS contributor entry, datum labels, feature-control-like cells; exact glyphs unresolved. |
| Objectives/results/warnings | `030` through `036` | `00:13:49-00:16:48` | Stackup naming/objective, Worst Case/RSS/Statistical modes, bell curve, non-1D warning treatment. |
| Dashboard/detail/contributions | `040` through `046` | `00:19:40-00:21:54` | Multi-stackup dashboard rows, pass/fail/warning styling, shared markers, drilldown, contribution bars. |
| Report | `047` through `051` | `00:22:18-00:23:38` | Save Report flow, fixed dark nav, white canvas, annotated snapshots, summary/table/result/contribution sections. |
| Sigma rollup/final state | `057`, `058`, `full_10sec_sheet_009.jpg` | `00:28:30-00:29:12` | Rollup sigma badge/state, late summary display. Use key frames because later five-second sheets go black. |
| Full-pass safety net | `full_10sec_sheet_001.jpg` through `full_10sec_sheet_011.jpg` | Whole video | Sequence check only; do not use the thumbnail sheets for primary token sampling. |

## Transcript Mapping

| Transcript Range | Implementation Meaning |
| --- | --- |
| `00:02:35-00:04:55` | Standalone app, open/import, source reference, ribbon commands, snapshot/report/import/export/save. |
| `00:04:55-00:07:01` | New Stackup guided flow, endpoint/direction/plane selection, component and mating-feature filtering, OK completion. |
| `00:07:01-00:10:14` | Generated dimensions, default tolerances/settings, inline tolerance edits, tolerance type structure, Add Feature. |
| `00:10:14-00:10:36` | Reused part dimensioning/tolerance scheme behavior. |
| `00:12:05-00:13:49` | Manual GDT/GPS entry, datum labels, runout/position/profile-equivalent examples, editable values. |
| `00:13:49-00:15:45` | Stackup naming, objective `+/-0.750`, pass/fail result bars, Worst Case/RSS/Statistical interpretation. |
| `00:15:55-00:19:07` | Non-1D warning semantics and out-of-scope full 3D rotational solve. |
| `00:19:07-00:22:09` | Multi-stackup dashboard, target/result/quality columns, shared dimension marker, contributions tab. |
| `00:22:09-00:23:36` | Snapshot preparation, Generate Report, browser report navigation, snapshots/tables/results/contributors. |
| `00:24:18-00:28:08` | Angular deviation, thermal expansion, native PMI/import are out of scope or roadmap for the neutral clone. |
| `00:28:30-00:29:12` | Rollup sigma and individual stackup sigma display. |

## Unresolved Crop List

| Item | Evidence To Crop | Current Lock Until Resolved | Required Follow-Up |
| --- | --- | --- | --- |
| Exact tolerance-type dropdown labels | Frame `019_00-09-05_tolerance_type_dropdown.jpg`; source MP4 around `00:09:07-00:09:19` | Implement confirmed structure: symmetric plus/minus, limits/asymmetric, and geometric/manual modes. | Fresh close crop or frame extraction with the dropdown open and text legible. |
| Exact GD&T symbols and material-condition modifiers | Frames `025` through `029`; source MP4 around `00:12:05-00:13:49` | Support Runout, Position, Profile, Manual/Geometric rows, tolerance value, datum/reference input. | Close crops of symbol dropdown, table cells, and feature-control-frame cells. |
| Exact Statistical submenu labels | Frames `032`, `033`; source MP4 around `00:14:49-00:15:45` | Preserve `Worst Case`, `RSS`, and `Statistical` modes plus Cp/Cpk/Sigma/Yield projections. | Crop the result mode dropdown/menu with submenu labels visible. |
| Report GDT/table glyph cells | Frames `050`, `051`; source MP4 around `00:23:15-00:23:38` | Preserve report table/result/contribution structure and leave exact glyph cells generic where unreadable. | Crop report table cells and contribution labels at browser zoom/source resolution. |
| Import-option micro labels | Frame `004_00-03-20_import_options_dialog.jpg`; `ui_5sec_sheet_001.jpg` | Preserve tabs, object filters, unit handling, source/reference options, OK/Cancel; filter to STEP/IGES. | Crop import dialog labels only if P20 needs exact wording. |
| Report left-nav clipping and microspacing | Frames `049` through `051` | Preserve fixed dark nav, white canvas, section links, and large report headings. | Optional crop if report styling needs exact nav clipping/spacing. |
| Late five-second sheet black cells | `ui_5sec_sheet_028.jpg` after about `00:27:10` | Use key frames `057` and `058` plus full-pass sheet `009` for sigma/final-state evidence. | Do not rely on black contact-sheet cells for late-demo decisions. |

## Acceptance Checklist For Later UI Workers

- Main shell at 1920x1080 keeps title/tab strip, 120 px ribbon, three-pane split, viewport chrome, right pane, lower result tabs, and status bar within the visual tolerances above.
- Ribbon action order and enabled/disabled states match frames `005` and `006` before feature-specific polish is claimed.
- Model browser preserves dense tree rows, icons, selection state, and width target. It does not become a wide inspector card.
- Guided mini-toolbar is hidden outside active workflow and shows the locked step labels/counters/controls during workflow.
- Detail and dashboard tables use locked columns, row heights, selection/fail/pass/warning colors, and scroll behavior.
- Result bars, bell curve, warning strip, and contribution bars use the locked color semantics and panel composition.
- Report output uses fixed dark left nav, white canvas, large annotated snapshots, summary table, per-stackup sections, result plots, and blue contribution bars.
- Any unreadable label/glyph remains listed above until a new crop resolves it. No worker should silently replace an unresolved source detail with an invented polished label.
- Visual comparisons should cite the exact key frame(s), transcript range, and this lock before claiming P21-P25 UI/report fidelity.
