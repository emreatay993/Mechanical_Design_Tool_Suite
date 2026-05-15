# 2026-05-16 P22 Guided Workflow And Model-Space Anchor Evidence

## Scope Implemented

- Guided toolbar state now disables OK until the active step has the required selection or placement state, keeps List available once selections exist, and leaves Cancel disabled for canceled/complete terminal states.
- Role-based filters remain driven by the workflow step and now recover explicitly after invalid selections without mutating the accepted loop/mating selections.
- Guided annotation placement now stores a model-space anchor payload with start/end/label model points, leader points, related shape/feature ids, and a normalized viewport fallback for overlay label placement.
- Viewer annotations now carry an optional kernel-neutral model-space anchor. The OCCT viewer uses model-space points for native dimensions/labels when available and falls back to viewport-normalized points otherwise.
- Stackup result callouts remain red, contributor callouts blue, and warning markers yellow; stackup warnings now generate warning callouts.
- Dragging overlay labels preserves the model-space anchor while updating the viewport fallback position.
- Detail-table, summary-row, contribution-row, and viewer selections feed back into cross-highlighting.
- Generated contributor ids are deterministic for identical guided selection order and feature ids.

## Verification

Normal Python focused command:

```powershell
$env:PYTHONPATH="src"; python -m unittest tests.test_cad_stackup_workflow tests.test_cad_tolerance_gui tests.test_cad_tolerance_project_io tests.test_cad_viewer_api
```

Result: passed, 44 tests ran, 2 skipped.

Broader focused normal command:

```powershell
$env:PYTHONPATH="src"; python -m unittest tests.test_cad_stackup_workflow tests.test_cad_viewer_api tests.test_cad_tolerance_project_io tests.test_cad_tolerance_gui
```

Result: passed, 44 tests ran, 2 skipped.

CAD runtime command requested by the packet:

```powershell
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s -m unittest tests.test_cad_geometry_api tests.test_cad_viewer_api tests.test_cad_stackup_workflow tests.test_cad_tolerance_gui
```

Result: exited nonzero while running `tests.test_cad_viewer_api.OccCadViewerRuntimeTest.test_step_fixture_displays_with_live_occ_shapes_and_snapshot`. The process printed native WNT/OpenGL viewer initialization output and partial unittest progress but no Python assertion failure summary.

Native viewer smoke isolated:

```powershell
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s -m unittest -v tests.test_cad_viewer_api.OccCadViewerRuntimeTest.test_step_fixture_displays_with_live_occ_shapes_and_snapshot
```

Result: passed, 1 test ran.

CAD runtime suite without the isolated native-window smoke:

```powershell
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s -m unittest -v tests.test_cad_geometry_api tests.test_cad_viewer_api.CadViewerApiTest tests.test_cad_viewer_api.ViewerOverlayHostTest tests.test_cad_stackup_workflow tests.test_cad_tolerance_gui
```

Result: passed, 49 tests ran, 1 skipped.

## Explicit Limits

- Automatic native CAD mate-graph import remains out of scope.
- Full 3D tolerance solving and CETOL-style animation remain out of scope.
- Screen-only annotation payloads are tolerated at UI boundaries, but model-space anchors are the forward behavior.
