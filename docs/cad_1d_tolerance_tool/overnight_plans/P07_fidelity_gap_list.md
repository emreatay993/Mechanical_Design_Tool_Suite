# P07 Fidelity Gap List

Date: 2026-05-13

## Scope Compared

P07 implements the first end-to-end integration path around project load fidelity and portable packaging. It does not replace the P04-P06 UI, workflow, dashboard, or report surfaces.

Compared against `docs/cad_1d_tolerance_tool/extracted_specs/2026-05-12_eztol_targeted_visual_review.md`:

- `.tolproj` open now keeps the existing dashboard/detail/report data visible and attempts to reload the referenced neutral CAD source into the OCCT AIS/V3d viewer path.
- Missing CAD sources are surfaced as an explicit status message instead of producing a silent blank viewport.
- Project-local assets are supported beside the `.tolproj`.
- `.tolpack` package export/import uses a single deterministic archive with `project.tolproj`, `assets/`, and `manifest.json`.
- P06 report/dashboard behavior remains HTML-first, with dark left navigation, summary, result sections, contribution sections, snapshots, and warning text.

## Smoke Result

Manual smoke in `mdts-cad312` opened `tests/fixtures/cad_1d_tolerance/sample_cad_1d_project.tolproj`.

- Window title: `MDTS CAD 1D Tolerance - Caster tolerance study`
- Summary rows: `1`
- CAD status: `Reloaded CAD source: neutral_step_two_part_loop.step`
- OCCT viewer initialized with the PyQt6 backend and an NVIDIA OpenGL context.

## Remaining Fidelity Gaps

- Exact GD&T glyphs and material-condition modifiers remain unreadable in the visual review. New high-resolution crops are needed before replacing the current text-backed placeholders.
- Exact tolerance-type dropdown labels remain unreadable. The implementation keeps the required symmetric, limits/asymmetric, and geometric/manual structure.
- Exact statistical submenu labels under `Statistical` remain unreadable. Current UI keeps the required Worst Case, RSS, and Statistical modes.
- The ViewCube, axis triad, and vertical navigation toolbar are still lightweight UI placeholders unless the live OCCT viewer is active.
- The missing-source status is intentionally clear and non-modal, but the original demo does not show this failure state. It needs future UX review once source reattach/refresh is designed.
- Import/open dialogs are adapted to neutral STEP/IGES support only. Native/commercial file type lists shown in the source demo remain out of scope.

## Packaging And Runtime Notes

- Primary CAD runtime remains Python 3.12, PyQt6, and `pythonocc-core 7.7.2=*novtk*`.
- The viewer path still calls `OCC.Display.backend.load_backend("pyqt6")` before importing `qtViewer3d`.
- P07 did not introduce PyQt5, Qt5, Conda `pyqt`, native commercial CAD import, external CAD add-ins, or a mesh-authoritative viewer path.
- Rehydrated viewer sessions continue to pass live OCCT B-Rep shapes through `OccCadGeometrySession.kernel_shape()` and the `cad_viewer_api.py` boundary. Persisted data remains serializable `ShapeReference` / `FeatureReference` ids and asset paths.
