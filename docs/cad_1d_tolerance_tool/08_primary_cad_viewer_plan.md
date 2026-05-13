# Primary CAD Viewer Plan

## Decision

The primary CAD viewer must use OCCT/OpenCascade B-Rep presentation through AIS/V3d embedded in PyQt6. PyVista/VTK is not the primary CAD viewer path for the final product.

The approved Python prototype path is:

- Python 3.12 environment from `environment-cad312.yml`.
- `pythonocc-core 7.7.2` with the `novtk` OCCT build.
- `OCC.Display.backend.load_backend("pyqt6")`.
- `OCC.Display.qtDisplay.qtViewer3d` / `OCC.Display.OCCViewer.Viewer3d`.
- Live OCCT shapes supplied by `OccCadGeometrySession.kernel_shape()`.

The `novtk` build removes OCCT's IVtk bridge only. It does not remove STEP/IGES import, B-Rep topology, AIS presentation, V3d views, Graphic3d styles, or SelectMgr selection support.

## Product Requirement

The final CAD workflow must not treat tessellated mesh data as the authoritative model. Tessellation may exist only as an internal render cache or secondary diagnostic/export path. Selection, measurement, stackup endpoint references, and persisted topology references must stay tied to OCCT B-Rep faces, edges, vertices, axes, planes, and cylinders.

## Viewer Ownership Boundary

Add a dedicated viewer layer, separate from the import/geometry adapter:

| Module | Responsibility |
| --- | --- |
| `cad_viewer_api.py` | Kernel-neutral viewer protocol, camera state, highlight roles, selection event payloads, snapshot request/result types. |
| `cad_viewer_occ.py` | PyQt6/pythonocc AIS/V3d viewer widget and OCCT presentation mapping. |
| `cad_tolerance_gui.py` | Main window and docks; hosts the viewer widget but does not own AIS/V3d handles. |
| `cad_tolerance_viewmodels.py` | Assembly tree and table models; reacts to viewer selections through serializable references. |

The viewer layer owns transient presentation state:

- `AIS_InteractiveContext`
- `V3d_Viewer`
- `V3d_View`
- `AIS_Shape` or `AIS_ColoredShape` handles
- selection modes and active selection filters
- transient highlights and annotation display objects
- camera/view state

The persistence/domain layer must never store AIS, V3d, TopoDS, OpenGL, QWidget, or VTK objects.

## Selection And Highlighting

The viewer must maintain bidirectional maps:

- `ShapeReference.id -> TopoDS_Shape`
- `ShapeReference.id -> AIS_InteractiveObject`
- selected AIS owner/object -> `ShapeReference`
- `ShapeReference -> FeatureReference` where a feature can be inferred

Required selection modes:

- Body/solid for assembly browsing and loop-part selection.
- Face for stackup endpoints, datum-like references, planar/cylindrical feature picks.
- Edge for axis/direction references and width picks.
- Vertex for endpoint references where needed.

Required highlight roles:

| Role | Use |
| --- | --- |
| `hover` | Cursor preselection. |
| `selected_start` | First stackup endpoint. |
| `selected_end` | Second stackup endpoint. |
| `direction` | Direction reference. |
| `analysis_plane` | Annotation/analysis plane reference. |
| `loop_member` | Loop component or constraint feature. |
| `warning` | Geometry involved in non-1D warnings. |

Use OCCT presentation color/transparency for geometry highlights. Do not approximate highlight semantics with detached mesh overlays unless AIS highlighting fails and the fallback is explicitly documented.

## Camera And Navigation

The first usable viewer must provide:

- fit all
- orbit
- pan
- zoom
- standard views
- shaded display
- edge overlay if available without destabilizing performance
- light-gray viewport background matching the UI spec

The final viewer should add:

- axis triad
- view cube or equivalent orientation widget
- vertical navigation toolbar
- annotation display objects and draggable labels
- report snapshot capture with annotations

## Environment And Packaging

Use `environment-cad312.yml` for CAD viewer development. The package combination to preserve is:

- Python `3.12`
- `pythonocc-core 7.7.2=*novtk*`
- PyQt6 from project dependencies

Do not install Conda `pyqt`, `pyqt5`, or a non-`novtk` `pythonocc-core` build into the CAD runtime. The non-`novtk` build can pull Conda Qt5 into the environment and break PyQt6.

Run CAD viewer commands with user-site disabled when validating packaging behavior:

```powershell
$env:PYTHONNOUSERSITE="1"
$env:PYTHONPATH="src"
& "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s -m unittest discover -s tests
```

## Implementation Phases

### Phase 1: Viewer Host Spike

Create a minimal PyQt6 widget that:

- calls `load_backend("pyqt6")` before importing `OCC.Display.qtDisplay`
- embeds `qtViewer3d`
- initializes the OCCT display driver
- displays the generated STEP fixture from `OccCadGeometrySession`
- fits the view and renders nonblank geometry
- exposes a `display_document(session)` method that consumes the existing P03 adapter

Acceptance:

- launchable manual smoke script or GUI test harness
- no PyQt5 installed or imported
- no Conda Qt5 installed in `mdts-cad312`
- `qtViewer3d.InitDriver()` succeeds on the development machine

### Phase 2: Reference Mapping And Selection

Add selection plumbing:

- display every selectable `ShapeReference`
- map AIS selections back to `ShapeReference.id`
- emit selection changed events with `FeatureReference` when inferred
- implement body, face, edge, vertex selection filters
- cross-highlight from assembly browser to viewer

Acceptance:

- selecting a planar face returns a `FeatureReference` with point/normal
- selecting a cylindrical face returns a `FeatureReference` with point/axis/radius
- browser selection highlights the same body in the viewport

### Phase 3: Stackup Workflow Integration

Connect the viewer to the guided workflow:

- role-based highlight colors
- workflow prompts drive valid selection modes
- selected endpoints/direction/plane become stackup references
- dimension/annotation overlay objects appear in the viewer

Acceptance:

- fixture workflow can create one stackup from two selected features
- generated contributors retain stable serializable references
- table row selection highlights corresponding geometry

### Phase 4: Snapshot And Report Support

Add viewport capture:

- save report-grade image snapshots
- include camera state and visible annotation positions
- support deterministic snapshot manifest entries in `.tolproj`

Acceptance:

- snapshot file exists and is nonblank
- project snapshot metadata round-trips
- HTML report can reference the captured image

## Fallback Strategy

If `qtViewer3d` proves unstable in PyQt6, do not switch the primary product viewer to mesh-only PyVista. The fallback is a small C++ Qt6 + OCCT viewport component wrapped for Python, while keeping the Python domain, persistence, and `cad_geometry_api.py` boundary stable.

PyVista/VTK remains acceptable only for secondary diagnostics, non-authoritative previews, or future post-processing plots.

## Verification Checklist

- `pythonocc-core` import works in `mdts-cad312`.
- `PyQt6.QtCore` imports and reports Qt 6.x.
- `PyQt5` is absent.
- `OCC.Display.backend.load_backend("pyqt6")` succeeds.
- `qtViewer3d.InitDriver()` succeeds.
- A generated STEP fixture displays as nonblank shaded geometry.
- Selection returns B-Rep-backed `ShapeReference` ids, not mesh-only ids.
- Snapshot capture produces a nonblank image.
