# Full Clone Gap Matrix

Date: 2026-05-14

This is the baseline coverage matrix for the requested high-fidelity EZtol-style CAD 1D tolerance clone. It is based on the full local video context pack, the timestamped transcript, the targeted visual review, fresh 10-second full-pass sheets, numbered CAD docs, and the current P07-era implementation state.

Evidence used:

- `output/transcribe/eztol-demo-media-1080p/EZtol-Demo_Media_1080p.viewer.html`
- `output/transcribe/eztol-demo-media-1080p/EZtol-Demo_Media_1080p.timestamped_transcript.md`
- `output/transcribe/eztol-demo-media-1080p/visual_review_2026-05-14_full_pass/full_10sec_sheet_*.jpg`
- `docs/cad_1d_tolerance_tool/extracted_specs/2026-05-12_eztol_targeted_visual_review.md`
- Numbered docs `01` through `09`

Status legend:

- `met`: implemented well enough for the prototype target.
- `partial`: visible implementation exists, but fidelity, workflow depth, tests, or polish are not yet sufficient.
- `missing`: no meaningful implementation yet.
- `out_of_scope`: intentionally excluded from the current neutral-CAD clone.
- `roadmap`: worth considering after the neutral-CAD clone reaches the requested fidelity target.

## Coverage Matrix

| Area | Demo-Derived Expectation | Current Status | Gap / Next Packet |
| --- | --- | --- | --- |
| Traditional stack-up intro | Demo opens with PowerPoint/manual stack-up context and caster drawing. | out_of_scope | Use as domain context only; do not clone slides or vendor branding. |
| Blank product launch | EZtol-like splash/main window opens from Windows. | partial | Launcher and entry point exist, but final icon/packaged CAD runtime needs P15 validation. |
| File open flow | Windows file dialog opens CAD assembly and hands it to import options. | partial | Basic neutral open exists; import options need exact behavior and source-status integration. P08/P15. |
| Import options dialog | Modal import settings include units/tolerance defaults and selectable import behavior. | partial | Current dialog does not fully mirror demo options or consistently drive import behavior. P09/P12/P15. |
| CAD source references | Loaded projects preserve source references and can show missing-source state. | met | P07 path exists; P08/P15 should verify visual status and package behavior. |
| Project-local assets | Assets near `.tolproj` reload without absolute paths. | met | Keep covered by P07 tests; P14/P15 extend report/package assets. |
| `.tolpack` package | Portable package export/import with deterministic, relative contents. | met | Preserve while adding report/snapshot assets. P14/P15. |
| Main workspace layout | Left model browser, center CAD viewport, right summary/detail analysis pane, ribbon actions. | partial | Layout exists but density, control states, icons, resizing, and visual parity need P13/P15. |
| Ribbon/toolbar actions | Compact actions for new stackup, add feature, snapshot, generate report, import/export. | partial | Buttons exist in prototype form; iconography/state wiring/final ordering need P12-P15. |
| Model browser | Assembly tree shows real part hierarchy, body names, visibility/selection states. | partial | Current tree is too synthetic; needs XDE names, colors, stable ids, hide/show. P10/P11. |
| CAD viewport rendering | Shaded CAD assembly with colors, gray background, triad/ViewCube/navigation. | partial | OCCT viewer path exists; color/name fidelity, selection, overlays, and navigation polish need P10/P11. |
| STEP/IGES import | Neutral CAD formats load as supported P0 inputs. | met | Continue supporting only STEP/IGES for current scope. |
| SAT/native import | Native/commercial formats or ACIS SAT. | out_of_scope | Removed from current code path; keep roadmap note only. |
| Native CAD add-in | Late demo shows SOLIDWORKS/CETOL-style add-in reference. | out_of_scope | Roadmap comparator, not P0 implementation. |
| XDE assembly metadata | Product names, colors, labels, hierarchy, and reusable shape ids survive import. | partial | Needs STEPCAF/XCAF traversal and tests with caster fixture. P10. |
| Selection filters | Body/face/edge/vertex picking and highlighted selected items. | partial | Prototype selection is not demo-grade; needs filter states, hover, mapping, cross-highlighting. P11. |
| Guided endpoint flow | Pick first/second endpoint, confirm/cancel/list controls, visible counters. | partial | State machine exists but lacks full UI fidelity and production selection loop. P12. |
| Direction selection | Select stack direction with persistent axis/direction annotation. | partial | Needs exact guided prompt/control behavior and robust persistence. P12. |
| Annotation plane | Select plane and position dimension labels in viewport. | missing | Needs draggable overlay/leader layer. P11/P12. |
| Loop parts | Select/include loop parts and show counters/check state. | partial | Needs usable loop authoring, selected part state, and generated contributors. P12. |
| Mating features | Identify mating faces/features between loop parts. | missing | Full native mate solving is out of scope, but selected mating-feature workflow is needed. P12. |
| Automatic contributors | Generate dimensional contributors from selected loop geometry. | partial | Prototype contributor creation exists but not production-quality from real selected geometry. P12. |
| Add feature workflow | Add intermediate/reference/GD&T features after initial stackup. | partial | Add Feature behavior and row integration need table/viewer coupling. P09/P12. |
| Red/blue annotations | Viewport dimensions use red/blue vertical/horizontal callouts and leader lines. | missing | Core visual fidelity item for P11. |
| Draggable labels | Demo moves labels/callouts to reduce overlap. | missing | Needs annotation model and viewer overlay hit-testing. P11. |
| Summary dashboard | Multi-stackup table with OK icons, nominal/objective/target/result/predicted quality/#dims. | partial | Basic dashboard exists; exact columns, badges, color rules, and drilldown need P13. |
| Pass/fail rollup | Round green/red counters and large red quality/objective score. | partial | Needs exact visual treatment and projection tests. P13. |
| Detail table | Spreadsheet-like contributor grid with names, sensitivity, nominal, tolerance, datum fields. | partial | Needs full edit delegates, validation, recalculation, and persistence. P09. |
| Inline tolerance edits | Numeric edits update worst-case/RSS/statistical result immediately. | partial | Calculation exists; editable Qt model/delegates need completion. P09. |
| Tolerance-type dropdown | Rows can switch dimensional/tolerance behavior through dropdowns. | missing | Needed for demo parity. P09. |
| GD&T dialog | Manual GD&T/GPS feature dialog supports runout/position-like entries and datums. | partial | Domain has partial representation; dialog UX and table integration need P09. |
| Datum/reference handling | Datum letters/feature references appear in rows and affect contributors. | partial | Needs model fields, validation, and display parity. P09. |
| Shared dimensions | Shared contributor markers/tooltips and consistent updates across stackups. | missing | Needed for dashboard/detail fidelity. P09/P13. |
| Worst-case mode | Result range bar and values for worst-case analysis. | partial | Calculation exists; visual mode parity needs P13. |
| RSS/statistical modes | Toggle between RSS/statistical displays and quality metrics. | partial | Calculations exist but UI controls/plots are incomplete. P13. |
| Bell curve plot | Statistical result area shows green normal curve and spec lines. | partial | Prototype plot exists; layout and deterministic rendering need P13/P14. |
| Contribution bars | Contributor contribution view with blue bars and sorted percentages. | partial | Needs demo-grade widget and report reuse. P13/P14. |
| Non-1D warning | Warning banner/status for loops likely requiring 3D analysis. | partial | Heuristic data exists; automatic geometry-driven warnings and UX need P13. |
| Settings dialogs | Demo shows settings/result-related dialogs and modal option panes. | partial | Need inventory in P08 and implement only product-critical settings in P09/P13/P15. |
| Snapshots | Capture annotated CAD viewport for project/report use. | partial | Needs overlay-inclusive deterministic snapshot pipeline. P11/P14. |
| Report save dialog | User chooses report destination and assets are written. | partial | HTML output exists; save flow and portable asset folder need P14. |
| Browser report | Dark left nav, white content, summary, per-stackup snapshots/tables/plots. | partial | Existing report is useful but not visually close enough. P14. |
| Report assets | Images/CSS/scripts are deterministic and relative. | partial | Needs no absolute paths and package compatibility. P14/P15. |
| Packaged executable | CAD GUI launches from packaged Windows build. | partial | Build/runtime dependency collection needs verification. P15. |
| CAD runtime dependencies | Correct Conda env includes PyQt6, pythonocc novtk, NumPy, ffmpeg. | met | `ffmpeg` is now included in `environment-cad312.yml`; P15 validates build. |
| Full test discovery | CAD and non-CAD tests run with clear blocked/skipped reporting. | partial | Existing unrelated discovery crash must be reported separately; P16 defines focused fallback. |
| Visual fidelity audit | Final screenshots/reports compared to full video evidence. | missing | P16 final audit after P08-P15. |

## Architecture Assessment

PyQt6 plus OCCT/pythonocc remains the practical default for the product shell and first high-fidelity clone. The missing pieces are mostly product workflow, model/view editing, metadata traversal, and overlay/report fidelity rather than a fundamental language mismatch.

Escalate only the viewport component to a small C++ Qt6 + OCCT module if P11/P15 prove that pythonocc's PyQt6 `qtViewer3d` path cannot reliably support selection mapping, HiDPI focus, overlay snapshots, or packaging. Keep the Python domain, project persistence, report generation, and launcher unless a concrete blocker appears.

## Immediate Packet Mapping

- P08: turn this baseline into a stricter evidence-by-evidence traceability matrix.
- P09: close detail-table, tolerance editing, GD&T, datum, and shared-dimension gaps.
- P10: close assembly/name/color/shape-id fidelity gaps.
- P11: close viewer interaction, selection, annotation, and snapshot-overlay gaps.
- P12: close guided stackup workflow gaps.
- P13: close dashboard, plot, warning, and contribution visual gaps.
- P14: close report and snapshot output gaps.
- P15: close launcher/runtime/package gaps.
- P16: perform the final audit against this matrix and the full video evidence.
