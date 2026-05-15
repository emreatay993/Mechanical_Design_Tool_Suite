# P18 Adapter Contract And Viewer Acceptance

Date: 2026-05-15

Branch: `codex/p18-adapter-contract`

## Summary

P18 now makes the CAD geometry to viewer runtime contract explicit without changing the product authority path. `CadRuntimeShapeProvider` is the viewer-facing provider contract for serializable `ShapeReference` / `FeatureReference` metadata plus transient live CAD-kernel shapes. `OccCadGeometrySession.runtime_shape()` is the OCCT implementation, and `kernel_shape()` remains only as a backward-compatible alias.

`OccCadViewerWidget` now consumes the explicit provider contract instead of calling an undocumented method on the generic geometry session. The primary viewer remains PyQt6 + pythonocc/OCCT AIS/V3d. No C++ viewport was implemented, and no mesh, STL, OBJ, VTK, or PyVista authority path was introduced.

## Contract Evidence

- `cad_geometry_api.py` defines `CadRuntimeShapeProvider` as a runtime-only protocol.
- `cad_geometry_occ.py` implements the provider through `runtime_shape()` backed by the existing live OCCT shape cache.
- `cad_viewer_api.py` and `cad_viewer_occ.py` type `display_document()` against `CadRuntimeShapeProvider`.
- `tests.test_cad_geometry_api` verifies `OccCadGeometrySession` advertises the runtime provider contract and that the in-memory test session does not claim live runtime shapes.

## Persistence Conformance

The project/package boundary now has artifact-level guards in `tests.test_cad_tolerance_project_io`:

- Saved `.tolproj` JSON is recursively checked for JSON-only values and runtime handle tokens.
- Packaged `.tolpack` `manifest.json` and embedded `project.tolproj` are checked the same way.
- Guarded runtime tokens include PyQt/Qt widget types, OCC/OCP module handles, AIS/V3d/TopoDS/Graphic3d/SelectMgr names, and OCCT handle markers.

The conformance check is intentionally at the artifact boundary because open metadata dictionaries are the realistic path where stringified runtime handles could otherwise leak into persistence.

## Viewer Runtime Gates

Focused P18 gates now cover:

- PyQt6/pythonocc backend load with no PyQt5 visible in the primary runtime test.
- STEP and IGES OCCT import through `tests.test_cad_geometry_api`.
- XDE names, colors, and labels where available through the XDE STEP fixture test.
- `qtViewer3d.InitDriver()` through `OccCadViewerWidget.initialize_viewer()`.
- Body/face selection mode activation.
- Selection-to-`ShapeReference` mapping via live OCCT shape lookup and the OCC selection callback probe.
- Native annotation rendering through nonzero native annotation count.
- Nonblank snapshot export using sampled unique-color and nonblack-ratio checks.
- Runtime smoke scripts now fail when the primary viewer is not `OccCadViewerWidget`, no live B-Rep-backed shapes are displayed, or the exported viewport snapshot is effectively blank.

The older packaged/runtime smoke evidence remains in `2026-05-15_p18_live_runtime_packaged_smoke.md`; this note records the new adapter-contract and gate hardening work.

## C++ Fallback Decision

No C++ Qt6 + OCCT fallback spec was added in this pass because the P18 gates did not justify escalation. The current PyQt6/pythonocc path initializes, displays B-Rep-backed shapes, maps selections to serializable references, renders native annotations, exports nonblank snapshots, and passes the focused runtime tests.

The known native full-window capture/composition caveat from P17/P18 remains tracked in the existing live-runtime smoke note. It is not currently a blocker for source import, selection mapping, annotation state, report snapshot export, project/package persistence, or packaged startup.

Escalate only the viewport adapter behind `cad_viewer_api.py` if a future gate proves one of these blockers:

- Packaged `qtViewer3d` launch cannot be made reliable.
- Live B-Rep selection or highlight callbacks cannot support guided stackups.
- Overlay-inclusive report snapshots cannot be made deterministic.
- CAD runtime tests cannot be isolated from native crashes after practical cleanup.

## Verification

Standard Python:

```powershell
$env:PYTHONPATH="src"; python -m unittest tests.test_cad_geometry_api tests.test_cad_viewer_api tests.test_cad_tolerance_project_io
```

Result: passed, 35 tests run, 6 skipped.

CAD runtime:

```powershell
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s -m unittest tests.test_cad_geometry_api tests.test_cad_viewer_api
```

Result: passed, 24 tests run, 1 skipped.

Runtime smoke gate sanity check:

```powershell
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s tests\scripts\cad_1d_runtime_smoke.py tests\fixtures\cad_1d_tolerance\neutral_step_two_part_loop.step --output-dir $env:TEMP\mdts_p18_runtime_gate --prefix p18_gate_step --settle-ms 1000
```

Result: passed. `viewer_class=OccCadViewerWidget`, `displayed_shape_count=2`, `runtime_gate_failures=[]`, viewport snapshot `sampled_unique_colors=60`, viewport snapshot `sampled_nonblack_ratio=1.0`.

Viewer smoke gate sanity check:

```powershell
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s tests\scripts\cad_viewer_smoke.py --snapshot $env:TEMP\mdts_p18_cad_viewer_smoke.png --exit-after-ms 1000
```

Result: passed. Snapshot size `1246x1556`, `unique_colors=56`, `nonblack_ratio=1.0000`.

