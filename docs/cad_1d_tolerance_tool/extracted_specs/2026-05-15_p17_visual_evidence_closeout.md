# P17 Visual Evidence Closeout

Date: 2026-05-15

## Scope

P17 compared the current CAD 1D tolerance UI and generated HTML report against the five demo frames named by P16. This is an evidence closeout only: it does not expand scope into native commercial CAD import, CAD add-ins, native PMI import, full 3D solving, angular deviation, thermal expansion, proprietary branding/assets, or a broad UI rewrite.

## Evidence Captured

Current evidence folder: `docs/cad_1d_tolerance_tool/extracted_specs/2026-05-15_p17_visual_evidence/`

| Current capture | Size | Purpose |
| --- | ---: | --- |
| `current_005_main_workspace.png` | 3000 x 1858 | Current loaded main workspace from `sample_cad_1d_project.tolproj`. |
| `current_019_tolerance_dropdown_detail_table.png` | 3000 x 1858 | Current detail table with tolerance editor choices open. |
| `current_033_statistical_result_bell_curve.png` | 3000 x 1858 | Current statistical result view with bell curve and non-1D warning. |
| `current_049_browser_report_open.png` | 1365 x 768 | Generated report opened in headless Chrome at normal browser height. |
| `current_051_report_contribution_section.png` | 1365 x 3000 | Generated report with the contribution section visible near the bottom. |
| `current_report_annotated_viewport_snapshot.png` | 1022 x 1556 | Report-ready OCCT snapshot exported from the current viewport. |
| `current_report/report.html` | n/a | Generated HTML report used for the browser captures. |

Capture notes:
- UI captures were produced with `mdts-cad312` and the checked-in fixture `tests/fixtures/cad_1d_tolerance/sample_cad_1d_project.tolproj`.
- Report captures were produced from `current_report/report.html` using Chrome headless.
- Chrome headless returned a blank image when launched directly at a `#fragment` URL on this machine, so the contribution evidence uses a tall normal-load screenshot instead.
- The full-window GUI captures show the native OCCT viewport surface as black, while `current_report_annotated_viewport_snapshot.png` proves the OCCT export path renders the model, colors, triad, and annotations. Treat the black full-window viewport as live screenshot/compositor evidence still needing P18-level runtime smoke hardening, not as a report snapshot failure.

## Demo Sources

| Frame | Source image | Transcript cue |
| --- | --- | --- |
| 005 | `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-12/key_frames/005_00-04-10_main_workspace_after_import.jpg` | `00:04:07-00:04:15` |
| 019 | `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-12/key_frames/019_00-09-05_tolerance_type_dropdown.jpg` | `00:09:02-00:09:19` |
| 033 | `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-12/key_frames/033_00-15-18_statistical_quality_bell_curve.jpg` | `00:15:09-00:15:24` |
| 049 | `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-12/key_frames/049_00-22-55_browser_report_open.jpg` | `00:22:50-00:23:00` |
| 051 | `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-12/key_frames/051_00-23-38_report_contribution_section.jpg` | `00:23:26-00:23:40` |

## Frame Comparison

| Demo frame | Current evidence | Visible match | Visible difference |
| --- | --- | --- | --- |
| 005 main workspace | `current_005_main_workspace.png` | Three-pane desktop shell, model browser, central viewport host, right summary table, result tabs, ViewCube/orientation overlay, vertical navigation controls, status bar. | Demo has one dense EZtol ribbon tab with Stackup/Report/Data groups visible together; current UI separates Stackup, Report, and Data into top tabs. Demo browser shows native caster assembly hierarchy and colored CAD model; current fixture tree is simplified and the full-window capture does not composite the OCCT model. Current summary uses MDTS branding and rollup badges not visible in this demo frame. |
| 019 tolerance dropdown/detail table | `current_019_tolerance_dropdown_detail_table.png` | Detail view, selected table row/cell, editable tolerance combo, visible symmetric/limits/geometric-style options, statistical result area below. | Demo table is denser and uses native caster rows, feature icons, vertical scrollbar, and inline tolerance text such as `58.000 +/-0.075`. Current labels are evidence-backed but not exact demo labels; current editor options are readable but not proven to match the source. |
| 033 statistical bell curve | `current_033_statistical_result_bell_curve.png` | Statistical result title, Cpk/mean/std-dev metrics, green bell curve, red/black objective/result markers, non-1D warning banner. | Demo bell curve is more compact inside the result panel and is paired with a caster viewport view and demo-specific stackup name. Current calculation values, fixture geometry, and warning wording are prototype fixture evidence rather than demo caster values. |
| 049 browser report open | `current_049_browser_report_open.png` | Dark fixed left nav, white report canvas, report title, summary table, stackup nav link, embedded annotated CAD snapshot. | Demo browser opens/scrolled to a large stackup snapshot page with EZtol logo and caster assembly image. Current report opens at the title/summary section, uses MDTS branding, and places the first snapshot below the summary. |
| 051 report contribution section | `current_051_report_contribution_section.png` | Report contains annotated snapshot, stackup table, result section, warning text, and blue contribution bars. | Demo frame shows a large annotated caster snapshot for the selected stackup and contribution/table content around it. Current report repeats the snapshot in summary and stackup sections, uses a simple block/cylinder fixture, and only the first contribution row is visible at the bottom of the tall evidence capture. |

## Fixed In P17

- The guided stackup floating toolbar is now hidden by default and only appears while a guided stackup workflow is active. The first capture pass showed it in normal loaded/detail states, where the demo frames do not show that toolbar. This was a small unambiguous viewport polish fix in `src/mechanical_design_tool_suite/cad_tolerance_gui.py`, covered by `tests/test_cad_tolerance_gui.py`.

## Still Partial

- Full-window screenshots do not yet provide clean live OCCT model compositing, even though the report snapshot export does. P18 should treat this as a runtime visual smoke gap.
- Ribbon density/order remains partial: the actions exist, but the current tab structure does not match the demo's single visible Tolerance Stackup ribbon grouping.
- Model browser fidelity remains partial: current fixture hierarchy is simplified and does not show the demo caster assembly tree, visibility states, or native names.
- Detail-table visual density remains partial: row grouping and editable tolerance behavior exist, but exact iconography, row spacing, and table density differ.
- Report layout remains partial: the report has the required dark nav/white canvas/snapshot/table/result/contribution structure, but it does not open or compose like the demo stackup snapshot page.
- The current fixture is intentionally smaller than the demo caster assembly, so viewport and report geometry cannot be visually identical to the source frames.

## Unreadable-Source Gaps

- Exact tolerance dropdown labels from frame 019 remain unreadable. Current labels preserve symmetric, limits, runout, position, and profile structures without guessing the source wording.
- Exact GD&T glyphs, material-condition modifiers, and feature-control-frame cells remain unresolved from the available frames.
- Exact statistical submenu labels remain unresolved; current behavior preserves Worst Case, RSS, and Statistical modes.
- Exact report GDT cells and some contribution/report microspacing remain unresolved without fresh close crops.

## Intentionally Different

- Branding stays independent: MDTS names/logos replace EZtol/Sigmetrix marks.
- P0 remains neutral STEP/IGES CAD; native Inventor/CATIA/NX/Creo/SOLIDWORKS/JT import and CAD add-ins are out of scope.
- Automatic native PMI import, full 3D tolerance solving, angular deviation, thermal expansion, CETOL animation/sensitivity views, and proprietary assets are out of scope.
- The HTML browser report remains the accepted report target; PDF/export polish is not added in P17.

## Status Updates

No existing P08/P16 status rows were upgraded or downgraded. The P17 evidence supports the new closeout note and one small UI polish fix only.
