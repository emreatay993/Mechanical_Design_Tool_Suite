# P16 Final Fidelity Audit And Roadmap

Date: 2026-05-15

## Summary

P16 audits the current CAD 1D tolerance tool after P08-P15 against the full video-derived EZtol-style requirement set. The product is now a credible standalone neutral-CAD 1D tolerance clone: the core model, STEP/IGES import path, project persistence, editable tolerance table, manual GDT entry, guided workflow, viewer overlay/snapshot contract, dashboard, HTML report, launcher entry point, and CAD runtime packaging rules are implemented and covered by tests.

The remaining gaps are not hidden: the unresolved items are mostly final visual/manual proof, exact small unreadable labels, real launched GUI import smoke coverage, packaged executable smoke coverage, source reattach UX polish, and the native Qt/OCCT test-order caveat called out below. No remaining gap requires native commercial CAD import or full 3D tolerance solving.

Recommendation: keep PyQt6 + OCCT/pythonocc as the primary implementation for now. A small C++ Qt6 + OCCT viewport component is not warranted unless P17/P18 proves that `qtViewer3d` cannot support stable packaged launch, interactive selection, annotation capture, or deterministic test isolation.

## Evidence Reviewed

- `docs/cad_1d_tolerance_tool/overnight_plans/README.md`
- `docs/cad_1d_tolerance_tool/overnight_plans/P16_final_fidelity_audit_and_roadmap.md`
- Numbered CAD docs `01` through `09`
- `docs/cad_1d_tolerance_tool/extracted_specs/2026-05-12_eztol_demo_extracted_spec.md`
- `docs/cad_1d_tolerance_tool/extracted_specs/2026-05-12_eztol_targeted_visual_review.md`
- `docs/cad_1d_tolerance_tool/extracted_specs/2026-05-14_full_clone_gap_matrix.md`
- `docs/cad_1d_tolerance_tool/source_artifacts/transcripts/2026-05-12_eztol_demo_timestamped_transcript.md`
- Full video context pack under `output/transcribe/eztol-demo-media-1080p/`, including transcript, manifest, key-frame manifest, selected key frames, and report frames
- P08-P15 implementation commits:
  - P08 `64d8cf6` evidence reset
  - P09 `52f66c5` editable table and GDT
  - P10 `2d1daab` XDE metadata
  - P11 `6368d5d` viewer annotations
  - P12 `1de47c9` guided workflow
  - P13 `3d7da35` dashboard fidelity
  - P14 `5f7ab84` report assets
  - P15 `5fe95d3` runtime launcher packaging

## Status Legend

- `met`: implemented and covered well enough for the current P0 neutral-CAD clone contract.
- `partial`: implemented in part, but final visual proof, live manual/runtime coverage, exact label fidelity, or workflow polish remains.
- `missing`: no meaningful implementation evidence remains. P16 found no `FCE-*` row that is still wholly missing after P09-P15.
- `out_of_scope`: intentionally excluded from the P0 standalone neutral-CAD clone.
- `roadmap`: legitimate future capability or proof item, but not required to accept the P0 clone.

## Final Coverage Matrix

| ID | Final Status | P16 Finding / Remaining Gap |
| --- | --- | --- |
| FCE-001 | partial | Domain and UI/report traceability exists, but final live CAD-to-table-to-report visual proof is still needed. |
| FCE-002 | partial | Linear and manual GDT contributors are represented and editable; exact GDT glyph/material-condition fidelity remains unreadable. |
| FCE-003 | met | Reference nominal zero and worst-case `+/-0.75` behavior is covered by deterministic calculations. |
| FCE-010 | partial | Source launch path and compact workspace exist; packaged live launch smoke is not yet executed. |
| FCE-011 | partial | Neutral open routing exists; exact Windows dialog parity and manual live open/import screenshot evidence remain. |
| FCE-012 | partial | STEP/IGES import behavior and metadata exist; modal import option parity and source-status UX need polish. |
| FCE-013 | met | STEP and IGES B-Rep import is implemented through the OCCT adapter and CAD-runtime tests. |
| FCE-014 | out_of_scope | Native Inventor, CATIA, NX, Creo, SOLIDWORKS, and JT import remain excluded. |
| FCE-015 | partial | Source path/hash/project-local behavior is covered; user-facing refresh/reattach UX is not demo-complete. |
| FCE-016 | met | `.tolproj` and `.tolpack` project/package behavior is implemented with relative assets. |
| FCE-020 | partial | Three-pane shell exists; final pixel-level density, icon, splitter, and screenshot evidence remain. |
| FCE-021 | partial | Ribbon/action set exists; exact icon order, tooltip parity, and enabled-state manual proof remain. |
| FCE-022 | partial | XDE names/colors and deterministic tree data exist; hide/show and full browser row behavior remain partial. |
| FCE-023 | met | OCCT AIS/V3d primary viewer path displays live STEP shapes and snapshots in `mdts-cad312`. |
| FCE-024 | partial | Axis/ViewCube/navigation affordances exist as lightweight/placeholder controls; final interactive parity remains. |
| FCE-025 | partial | Selection modes and highlight roles exist; full live hover/cross-role manual coverage remains. |
| FCE-026 | partial | Cross-highlighting pathways exist, but full browser/viewer/table/result visual proof remains. |
| FCE-030 | met | Guided mini-toolbar states are implemented and tested. |
| FCE-031 | partial | Endpoint selection flow exists; real interactive B-Rep GUI picking is not fully automated end-to-end. |
| FCE-032 | met | Direction selection state, filters, and persistence are implemented. |
| FCE-033 | met | Analysis-plane and annotation-position state is implemented. |
| FCE-034 | met | Loop component selection and counters are implemented. |
| FCE-035 | partial | Mating-feature flow works for selected features; automatic native mate graph import remains excluded. |
| FCE-036 | met | Deterministic contributors are generated from selected workflow features. |
| FCE-037 | met | Add Feature and reused part dimension schemes are implemented. |
| FCE-040 | met | Red/blue/yellow annotation overlay model and snapshot-ready labels/leaders are implemented. |
| FCE-041 | met | Draggable annotation labels are implemented in the Qt overlay host. |
| FCE-050 | met | Dense detail table columns, hierarchy rows, result/objective rows, and row styling are implemented. |
| FCE-051 | met | Inline numeric edits validate, recalculate, and round-trip. |
| FCE-052 | partial | Tolerance mode switching is implemented as Symmetric, Limits, and Geometric; exact demo dropdown labels remain unreadable. |
| FCE-053 | partial | Defaults/settings data exists; exact settings dialog parity remains partial. |
| FCE-054 | partial | Add Geometric Tolerance dialog is implemented; exact symbol glyphs/material modifiers remain unreadable. |
| FCE-055 | met | Datum/reference rows and GDT contributors are represented and persisted. |
| FCE-056 | met | Shared-dimension markers/tooltips and edit warnings are implemented. |
| FCE-060 | met | Worst-case and RSS math are implemented and tested. |
| FCE-061 | met | Cpk, Sigma, and Yield-style statistical summaries are implemented and tested. |
| FCE-062 | partial | Result bars and statistical/bell-curve projections exist; final visual screenshot parity remains. |
| FCE-063 | partial | Non-1D warning UI exists; exact thresholds are engineering constants because the video does not specify them. |
| FCE-064 | met | Multi-stackup dashboard projection and model annotations are implemented. |
| FCE-065 | met | Summary columns and values are implemented, including `#Dims`. |
| FCE-066 | met | Summary-to-detail drilldown and return behavior are implemented. |
| FCE-067 | met | Contribution ranking and blue bar presentation are implemented. |
| FCE-070 | met | Snapshot request/output path and overlay-inclusive snapshot contract are implemented. |
| FCE-071 | partial | Portable report output exists; exact Windows Save Report dialog proof remains partial. |
| FCE-072 | partial | Browser-style HTML report exists; final browser screenshot comparison is not committed. |
| FCE-080 | out_of_scope | CAD add-in ribbons, context menus, sensitivity plots, and animation tools remain reference-only. |
| FCE-081 | out_of_scope | Full 3D CETOL-style solving remains excluded. |
| FCE-082 | out_of_scope | Angular deviation result calculation remains excluded. |
| FCE-083 | roadmap | Thermal expansion remains a future roadmap item, not a demonstrated release capability. |
| FCE-084 | roadmap | Direct native model PMI/dimension import remains future roadmap; manual GDT is P0. |
| FCE-085 | met | Sigma rollup and individual Sigma display are implemented. |
| FCE-086 | roadmap | Hole-pattern fit follow-up remains future example work, not P0 acceptance. |
| FCE-090 | met | This P16 audit closes the final audit row and preserves explicit remaining partial/roadmap gaps. |

## Required Validation Scenario Audit

| P16 Scenario | Final Status | Evidence / Caveat |
| --- | --- | --- |
| Launch/open/import STEP and IGES | partial | STEP/IGES kernel import and live STEP viewer snapshot are covered in `mdts-cad312`; real interactive GUI open/import remains a manual smoke gap. |
| Load `.tolproj` with existing source, missing source, project-local assets, and `.tolpack` | met | GUI and project IO tests cover source states and portable package behavior. |
| Guided stackup creation through the UI | met | Workflow controller and PyQt UI tests cover toolbar, filters, finish, counters, and Add Feature. |
| Inline tolerance edit and GDT dialog | met | Table edits validate, recalculate, warn on shared dimensions, and survive round-trip; manual GDT row is tested. |
| Dashboard pass/fail/warning and multi-stackup drilldown | met | GUI/model tests cover badges, warning banner, result panel, and drilldown. |
| Contributions view and shared-dimension markers | met | Shared markers/tooltips and contribution bars are covered by GUI/workflow tests. |
| Snapshot and report generation | met | HTML report, portable assets, manifest, and viewer/overlay snapshot contracts are covered. |
| Suite launcher and direct CAD GUI launch | partial | Source launcher, entry point routing, env pins, spec/build config are tested; packaged executable run was not executed. |

## Screenshot And Report Comparison Notes

- Key frame `005_00-04-10_main_workspace_after_import.jpg`: the target layout is a dense ribbon, model tree, light-gray OCCT viewport, right summary pane, result tabs, axis triad, ViewCube, and vertical navigation toolbar. Current implementation has the same structural layout and independent MDTS branding, but final screenshot proof should still compare density, icon order, splitter sizing, and placeholder orientation controls.
- Key frame `019_00-09-05_tolerance_type_dropdown.jpg`: the target has a tolerance-type dropdown in the detail table. Current implementation supports Symmetric, Limits, and Geometric mode switching. The exact demo option labels remain unreadable and should not be invented.
- Key frames `025` through `029`: the target shows manual GDT/GPS entry and feature-control-frame-like cells. Current implementation supports Runout, Position, Profile, Manual, tolerance value, and datum/reference input. Exact symbol glyphs and material-condition modifiers remain unresolved.
- Key frames `032_00-14-52_worst_case_rss_modes.jpg` and `033_00-15-18_statistical_quality_bell_curve.jpg`: current implementation covers Worst Case, RSS, Statistical, range bars, Cpk/Sigma/Yield projections, and the non-1D warning text. The Statistical submenu's exact small labels remain unreadable.
- Key frames `049` through `051`: current report output matches the required broad structure: dark left nav, white report canvas, summary table, per-stackup sections, snapshots, result areas, and contribution bars. A committed browser screenshot comparison is still absent, so P17 should produce the final visual evidence pack rather than assuming full pixel fidelity.
- Key frame `051_00-23-38_report_contribution_section.jpg`: the target report image uses blue dimension callouts, red result callouts, and labels including `27.5`, `diameter 10.50`, `diameter 9.866`, `12.5`, `117.5`, `39.0`, `5.0`, and red `1.000`. Current overlay/report machinery can carry annotated snapshots, but exact label placement needs live snapshot comparison.

## Unresolved Unreadable Labels And Glyphs

| Item | Evidence | Required Follow-Up |
| --- | --- | --- |
| Exact tolerance-type dropdown labels | `019_00-09-05_tolerance_type_dropdown.jpg`, transcript `00:09:07-00:09:16` | Fresh close crop of tolerance cell/dropdown. Keep current Symmetric/Limits/Geometric structure until proven otherwise. |
| Exact GDT symbols and material-condition modifiers | Key frames `025` through `029`, report GDT cells | Fresh crops of GDT symbol dropdown and table/report feature-control frames. |
| Exact Statistical submenu labels | `032_00-14-52_worst_case_rss_modes.jpg`, `033_00-15-18_statistical_quality_bell_curve.jpg` | Fresh crop with Statistical submenu open. Preserve Worst Case/RSS/Statistical behavior meanwhile. |
| Exact report table small GDT/glyph cells | `050_00-23-18_report_stackup_section.jpg` | Close crop of report table and contribution GDT frames. |
| Exact left-nav clipping/spacing in report | `049_00-22-55_browser_report_open.jpg` | Optional crop only if styling parity work needs exact clipping; current requirement is the dark fixed nav structure. |
| Late-demo final-state sheets after `00:27:10` | Five-second sheets go black after about `00:27:10` | Use high-resolution key frames `057` and `058`, transcript, and source viewer instead of contact sheets. |

## Intentionally Unimplemented Demo Capabilities

- Native commercial CAD import for Inventor, CATIA, NX, Creo, SOLIDWORKS, JT, and related file types.
- External CAD add-ins and SOLIDWORKS/CETOL ribbon integration.
- Direct native model PMI or model-based dimension import.
- Full 3D tolerance solving, angular deviation calculation, worst-case 3D animation, and CETOL sensitivity/response visualization.
- Thermal expansion.
- Hole-pattern fit follow-up examples.
- Proprietary logos, branding, and vendor assets.
- Production installer/MSI polish and PDF export. The accepted report target remains browser-style HTML first.
- Full automatic native CAD mate-graph import. P0 remains a guided neutral-CAD workflow from selected features.

## P17+ Roadmap

### P17 Visual Evidence Closeout

Goal: Produce a committed visual evidence pack comparing the current UI and generated report to the key frames used by P16.

Preconditions: Current P16 audit, P08 matrix, targeted visual review, and `mdts-cad312` runtime.

Conservative write scope: `docs/cad_1d_tolerance_tool/`, generated comparison screenshots under a dated evidence folder, and focused screenshot scripts only if needed.

Deliverables: Current main workspace screenshot, detail/table screenshot, result/dashboard screenshot, generated report browser screenshot, side-by-side notes against key frames `005`, `019`, `033`, `049`, and `051`.

Verification: Re-run standard and CAD-runtime tests, plus open the generated report in a browser and confirm images render.

Non-goals: No new CAD formats, no full 3D solving, no native CAD add-in work.

Packetization notes: P17 should be documentation/evidence-first and only change code if a screenshot reveals a small obvious fidelity bug.

### P18 Live Runtime And Packaged Smoke Hardening

Goal: Close the live runtime proof gaps for real GUI STEP/IGES import and packaged `Cad1DTolerance.exe` launch.

Preconditions: P15 packaging config and `mdts-cad312`.

Conservative write scope: `scripts/`, launcher/build docs, focused runtime smoke tests, and minimal GUI startup fixes.

Deliverables: Live source GUI smoke for STEP, IGES, `.tolproj`, and `.tolpack`; packaged build/run result or a documented blocker; investigation of the focused CAD command's module-order/native Qt/OCCT exit.

Verification: P16 full discovery commands plus split viewer/focused CAD commands when needed; packaged build smoke when feasible.

Non-goals: MSI installer polish, dependency changes that make PyVista/VTK authoritative.

Packetization notes: P18 is the point where a C++ viewport spike should be considered if pythonocc `qtViewer3d` blocks packaged launch or test isolation.

### P19 Crop Resolution And Exact Label Pass

Goal: Resolve the remaining unreadable UI labels and symbols from the source MP4 without guessing.

Preconditions: Source MP4 and ffmpeg available in `mdts-cad312`.

Conservative write scope: extracted specs, small UI label/glyph updates if the new crop provides clear evidence, and targeted tests for changed labels.

Deliverables: Close crops for tolerance dropdown, GDT symbol dropdown/table cells, Statistical submenu, and report GDT cells; updated unresolved-label list; UI updates only where evidence is legible.

Verification: `git diff --check`, focused GUI tests, and visual notes with crop paths.

Non-goals: New GDT interpretation families or native PMI import.

Packetization notes: P19 can run after P17 or in parallel with P18 if it only touches docs and narrow label mappings.

### P20 Source Reattach And Import UX Polish

Goal: Improve source-reference UX and import-option parity without expanding format scope.

Preconditions: P10 source metadata and P15 launch paths.

Conservative write scope: CAD import dialog/UI wiring, project source-status viewmodel, docs, and focused tests.

Deliverables: Clear existing/missing/project-local source status in the UI, reattach/refresh action for changed neutral CAD, import options dialog with neutral-format filters, object filters, unit handling, and OK/Cancel behavior.

Verification: GUI tests for source states and reattach routing, CAD-runtime import tests for STEP/IGES, standard suite.

Non-goals: Native CAD import, topology naming guarantees across arbitrary revisions, commercial CAD constraints.

Packetization notes: P20 should stay neutral-CAD only and preserve the adapter boundary.

## Viewport Stack Recommendation

PyQt6 + OCCT/pythonocc remains sufficient for the next phase. P11 and P15 produced enough evidence that the current path can display live OCCT shapes, preserve B-Rep-backed references, apply highlights, carry serializable annotations, and capture snapshots. The known caveat is native Qt/OCCT sensitivity in focused test ordering, not a proved product blocker.

Do not start a C++ Qt6 + OCCT viewport component now. Keep `cad_viewer_api.py` stable and revisit the fallback only if P18 shows one of these concrete blockers:

- `qtViewer3d` cannot launch reliably from the packaged executable.
- Live selection/highlight callbacks cannot be made stable enough for guided stackups.
- Overlay-inclusive snapshots cannot be made deterministic enough for reports.
- CAD-runtime tests cannot be isolated without native crashes after practical cleanup.

## Verification Run

Executed on 2026-05-15:

```powershell
$env:PYTHONPATH="src"; python -m unittest discover -s tests
```

Result: passed, 134 tests run, 7 skipped.

```powershell
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s -m unittest discover -s tests
```

Result: passed, 134 tests run, 2 skipped.

The full CAD-runtime discovery did not crash, so the focused CAD fallback command was not required for P16 closeout. Explorer coverage did identify a separate native Qt/OCCT module-order caveat for the exact focused command ordering; that is routed to P18 rather than treated as a current full-discovery failure.
