# Requirements

## Summary

Build a standalone CAD-based 1D tolerance analysis tool that faithfully reproduces the demonstrated EZtol-style workflow and at least 95% of the visible UI/UX patterns where technically feasible. The first implementation should support neutral CAD formats only and should avoid native commercial CAD dependencies.

## Evidence

Requirements in this file are derived from:

- `extracted_specs/2026-05-12_eztol_demo_extracted_spec.md`
- `extracted_specs/2026-05-12_eztol_targeted_visual_review.md`
- `source_artifacts/transcripts/2026-05-12_eztol_demo_timestamped_transcript.md`
- `output/transcribe/eztol-demo-media-1080p/visual_evidence/sheet_*.jpg`

## Functional Requirements

### CAD Import And Project Management

- FR-CAD-001: Import neutral CAD geometry from STEP AP203/AP214/AP242 files.
- FR-CAD-002: Import IGES files for B-Rep geometry where supported by the chosen kernel.
- FR-CAD-003: Treat STL/OBJ, if added, as visualization-only formats unless a future workflow defines reliable topology mapping.
- FR-CAD-004: Build an assembly/part browser from imported product structure when the file preserves it.
- FR-CAD-005: Persist source CAD path, file hash, import timestamp, units, assembly hierarchy, display names, colors, and selected topology references in the project.
- FR-CAD-006: Provide a reattach/refresh pathway for revised neutral CAD files when the original path or hash changes.
- FR-CAD-007: Save and load analysis as a versioned project file, extending the repo's existing `.tolproj` JSON pattern.
- FR-CAD-008: Provide a Windows-style open/import flow with file name, file type, import options, object filters, units, and OK/Cancel controls. Initial file type choices must show neutral formats only.

### Viewport And Selection

- FR-VIEW-001: Render shaded CAD geometry in a central viewport with orbit, pan, zoom, fit, standard views, axis triad, and view cube or equivalent orientation widget.
- FR-VIEW-001A: Use OCCT AIS/V3d as the primary CAD viewer and keep OCCT B-Rep topology as the authoritative selection and measurement source. Tessellated meshes may be used only as internal display caches or secondary diagnostics.
- FR-VIEW-002: Support selectable bodies, faces, edges, vertices, axes, and inferred surface normals where exposed by the geometry kernel.
- FR-VIEW-002A: Map every live viewer selection back to a serializable `ShapeReference` and, where possible, an inferred `FeatureReference`; do not persist raw AIS/V3d/TopoDS handles.
- FR-VIEW-002B: Support role-based selection filters for stackup start feature, end feature, direction reference, analysis plane, loop members, and warning review.
- FR-VIEW-003: Highlight selected geometry with translucent colors matching the demo style: green, red, blue, magenta, and yellow depending on selection role.
- FR-VIEW-003A: Support cross-highlighting between the assembly browser, viewport picks, contributor table rows, and result/warning displays.
- FR-VIEW-004: Draw dimension arrows, leader lines, and draggable annotation labels directly over the model.
- FR-VIEW-005: Allow snapshots of the current viewport with annotations for reports.
- FR-VIEW-006: The CAD viewer runtime must use PyQt6 for UI integration. PyQt5/Qt5 may not be introduced into the primary UI runtime to satisfy CAD viewer dependencies.

### Stackup Authoring

- FR-STK-001: Provide a `New Stackup` guided workflow with stateful prompts and mini-toolbar style actions.
- FR-STK-001A: The guided mini-toolbar must include the observed step states `Selection 1`, `Width 1`, `Selection 2`, `Width 2`, `Direction`, `Analysis Plane`, and `Dimension Location`.
- FR-STK-002: Let the user select start/end endpoints from faces, edges, or vertices.
- FR-STK-003: Prompt for stackup direction when endpoint geometry is cylindrical or otherwise ambiguous.
- FR-STK-004: Let the user select an annotation plane and reposition the nominal annotation.
- FR-STK-005: Let the user select loop parts and assembly constraint features in guided sequence.
- FR-STK-006: Filter valid selections by current workflow step, expected part, and stackup direction.
- FR-STK-007: Generate an initial dimension contributor table from selected loop geometry.
- FR-STK-008: Allow manual insertion of intermediate/reference features when the drawing dimension scheme differs from the automatically inferred scheme.
- FR-STK-009: Reuse existing dimension/tolerance definitions for repeated parts and shared features.

### Tolerance Definition

- FR-TOL-001: Support symmetric plus/minus tolerances.
- FR-TOL-002: Support limit/asymmetric tolerances with independent minus and plus values.
- FR-TOL-003: Support manual GD&T/GPS-style contributors, including runout, position, and profile-equivalent controls.
- FR-TOL-004: Support datum labels and datum references in geometric tolerance rows.
- FR-TOL-005: Keep all generated contributors editable from a dense table.
- FR-TOL-006: Track sensitivity/sign, nominal contribution, tolerance, datum, source feature, and whether the contributor is shared with other stackups.

### Analysis And Results

- FR-RES-001: Calculate nominal stackup result.
- FR-RES-002: Calculate worst-case variation with directional minus/plus support.
- FR-RES-003: Calculate RSS variation.
- FR-RES-004: Calculate statistical quality metrics including Cp/Cpk or an equivalent sigma/quality summary.
- FR-RES-005: Compare results to user-defined objectives such as `+/-0.750`.
- FR-RES-006: Show pass/fail/warning state for each stackup in a summary dashboard.
- FR-RES-007: Rank contributors by percent contribution to total variation.
- FR-RES-008: Mark shared dimensions and indicate affected stackups.
- FR-RES-009: Show warnings when geometry suggests likely non-1D effects.

### Multi-Requirement Dashboard

- FR-DASH-001: Manage multiple stackups in one project.
- FR-DASH-002: Show all stackups in a summary table with columns for status, name, nominal, objective, target quality, results, predicted quality, and number of dimensions.
- FR-DASH-003: Allow row selection to highlight corresponding model annotations.
- FR-DASH-004: Provide drilldown from each summary row into stackup detail.
- FR-DASH-005: Provide large rollup badges for objectives met, objectives not met, and predicted/target sigma rollup.
- FR-DASH-006: Support dashboard objective/result expressions with `+/-`, `<=`, `>=`, `RSS`, `Worst Case`, `Cpk`, `Yield`, and `Sigma` display modes.

### Reporting

- FR-RPT-001: Generate a browser-style report containing dashboard summary, viewport snapshots, loop diagrams, tolerance tables, results plots, and contribution plots.
- FR-RPT-002: Allow report regeneration after model/table changes.
- FR-RPT-003: Export reports to HTML first, then PDF once rendering is stable.
- FR-RPT-004: The HTML report must use a dark fixed left navigation rail, white report canvas, summary section, per-stackup result sections, contribution sections, and annotated CAD snapshot images.

## UI Fidelity Requirements

- UI-FID-001: Match the demonstrated desktop CAD layout: ribbon tabs at top, left assembly browser, center viewport, right analysis pane.
- UI-FID-002: Use compact desktop table density, not a spacious dashboard layout.
- UI-FID-003: Match the visible color semantics for status, selections, and annotations.
- UI-FID-004: Reproduce summary/detail/contribution/report transitions visible in the demo.
- UI-FID-005: Avoid copying proprietary logos or branding. Clone workflow, layout, and interaction patterns with independent naming and assets.
- UI-FID-006: Implement observed table details from the targeted visual review: summary columns, detail columns, pale red failed rows, pale blue selected rows, green check icons, red failure icons, yellow non-1D warning triangle, and stacked-page shared-dimension marker.
- UI-FID-007: UI workers must inspect `extracted_specs/2026-05-12_eztol_targeted_visual_review.md` before implementing ribbon actions, dialogs, tables, result plots, or report pages.

## Non-Functional Requirements

- NFR-001: Keep domain models and calculation methods independent of Qt and the CAD kernel.
- NFR-002: Keep CAD geometry access behind a replaceable adapter API.
- NFR-003: Preserve deterministic tests for calculations, persistence, and report generation.
- NFR-004: Support Windows as the primary development and packaging target.
- NFR-005: Keep first-run workflows usable without internet access once dependencies and CAD fixtures are installed.
- NFR-006: Store user-facing numeric values in millimeters by default, with unit metadata persisted per project.
- NFR-007: Use a versioned schema for future migration.

## Non-Goals For Initial Clone

- Native commercial CAD import for Inventor, CATIA, NX, Creo, SOLIDWORKS, or JT.
- External CAD add-ins.
- Automatic native CAD PMI import.
- Full 3D tolerance analysis or angular deviation calculation.
- Thermal expansion.
- Production installer polish before the OCCT packaging spike is complete.

## Traceability

| Requirement Area | Primary Evidence | Priority | Status |
| --- | --- | --- | --- |
| CAD import and standalone app | Transcript `00:02:35-00:04:55`; user neutral-format constraint | P0 | Derived |
| Guided stackup workflow | Transcript `00:04:55-00:07:01`; visual sheet 002 | P0 | Derived |
| Tolerance table editing | Transcript `00:08:14-00:10:14`; visual sheets 003-005 | P0 | Derived |
| GD&T/GPS manual entry | Transcript `00:12:05-00:13:49`; visual sheet 004 | P0 | Derived |
| Results dashboard | Transcript `00:13:49-00:21:08`; visual sheets 005-007 | P0 | Derived |
| Reports | Transcript `00:22:09-00:23:36`; visual sheet 007 | P1 | Derived |
| Targeted UI fidelity details | `extracted_specs/2026-05-12_eztol_targeted_visual_review.md` | P0 | Derived |

## P0 Evidence Checklist

P00 locks the following evidence sources as required rereads for later implementation packets:

| Evidence Area | Required Source | P0 Requirement Coverage |
| --- | --- | --- |
| Neutral import and project workflow | `source_artifacts/transcripts/2026-05-12_eztol_demo_timestamped_transcript.md`, cues around `00:02:35-00:04:55` | FR-CAD-001 through FR-CAD-008 |
| Guided stackup authoring | Targeted visual review sections `00:05:00-00:06:52` plus key frames `007` through `013` | FR-STK-001 through FR-STK-009 |
| Dense tolerance editing and GD&T entry | Targeted visual review sections `00:07:05-00:13:55` plus key frames `014` through `028` | FR-TOL-001 through FR-TOL-006 |
| Results, dashboard, and non-1D warnings | Transcript cues around `00:15:55-00:21:54`; targeted review dashboard and contribution sections | FR-RES-001 through FR-RES-009, FR-DASH-001 through FR-DASH-006 |
| Browser-style report output | Targeted visual review report section `00:22:18-00:23:38` | FR-RPT-001 through FR-RPT-004 |
| UI fidelity details | `extracted_specs/2026-05-12_eztol_targeted_visual_review.md`, then local key frames and five-second sheets | UI-FID-001 through UI-FID-007 |

No P0 requirement area is currently missing a primary evidence source. Exact GD&T glyphs, tolerance-type dropdown labels, statistical submenu labels, and non-1D thresholds remain documented implementation uncertainties rather than missing requirements.
