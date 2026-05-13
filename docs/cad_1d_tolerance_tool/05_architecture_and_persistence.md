# Architecture and Persistence

## Architecture Goals

- Faithfully reproduce the EZtol-style desktop workflow while keeping the implementation maintainable.
- Make CAD kernel access replaceable so `pythonocc` is not a permanent architectural trap.
- Keep calculations, project models, and report generation independent from Qt and OCCT.
- Support neutral CAD formats first.
- Keep future commercial/native CAD import possible through a new adapter without rewriting UI or domain models.

## Recommended Stack

### Long-Run Direction

Use OCCT/OpenCascade as the CAD kernel foundation for neutral CAD import, B-Rep topology, assembly structure, and viewport selection. OCCT officially supports STEP AP203/AP214/AP242 and IGES through its data exchange modules, with XDE support for attributes such as names, colors, layers, materials, assembly data, and PMI-related metadata.

`pythonocc` is acceptable for a first prototype because it wraps OCCT for Python and provides Qt/PySide widgets, but the product architecture should treat it as one binding option. If Python binding, packaging, or OCCT API coverage becomes the bottleneck, move the geometry/viewport adapter to a C++ Qt + OCCT component while preserving the Python domain and persistence model.

### Practical First Implementation

- UI: Qt Widgets/PyQt6 to match the existing repo and support dense `QTreeView`/`QTableView` model-view surfaces.
- CAD kernel spike: OCCT through `pythonocc-core` or an equivalent OCCT Python binding.
- Primary CAD viewer: OCCT AIS/V3d embedded in PyQt6 through a dedicated viewer adapter. Do not use PyVista/VTK as the authoritative CAD viewer path.
- Domain/calculation/persistence/reporting: pure Python modules under `src/mechanical_design_tool_suite/`.
- Persistence: versioned JSON `.tolproj`, extending the existing repo pattern.
- Reports: HTML first, PDF later.

### External References

- OCCT data exchange: `https://dev.opencascade.org/about/data_exchange`
- OCCT XDE: `https://dev.opencascade.org/doc/occt-6.7.0/overview/html/user_guides__xde.html`
- pythonOCC: `https://dev.opencascade.org/project/pythonocc`
- Qt model/view: `https://doc.qt.io/qt-6/model-view-programming.html`

## Application Modules

| Module | Responsibility |
| --- | --- |
| `cad_tolerance_models.py` | Pure dataclasses/enums for CAD documents, assembly nodes, feature references, stackups, contributors, results, snapshots. |
| `cad_tolerance_methods.py` | Pure calculation methods for worst case, RSS, quality metrics, contribution ranking, non-1D warnings. |
| `cad_tolerance_project_io.py` | Versioned `.tolproj` save/load and migration. |
| `cad_geometry_api.py` | Kernel-neutral interface for import, assembly traversal, shape references, selection, measurements, snapshots. |
| `cad_geometry_occ.py` | OCCT/pythonocc implementation of `cad_geometry_api.py`. |
| `cad_viewer_api.py` | Kernel-neutral viewer protocol for camera state, selection events, highlight roles, and snapshot requests. |
| `cad_viewer_occ.py` | PyQt6/pythonocc AIS/V3d viewer widget and OCCT presentation mapping. |
| `cad_tolerance_report.py` | HTML report generation from project, results, snapshots, and plots. |
| `cad_tolerance_gui.py` | Qt main window, docks, ribbon tabs, menu/actions, model/view binding. |
| `cad_tolerance_viewmodels.py` | Qt table/tree models and selection bridge. |

## CAD Integration Boundary

The GUI and domain code should talk to the geometry layer through an interface shaped like:

```python
class CadGeometrySession:
    def import_file(self, path: Path) -> CadDocument: ...
    def assembly_tree(self) -> list[AssemblyNode]: ...
    def display_shape(self, shape_ref: ShapeReference) -> None: ...
    def set_selection_filter(self, kinds: set[ShapeKind]) -> None: ...
    def selected_feature(self) -> FeatureReference | None: ...
    def measure_between(self, a: FeatureReference, b: FeatureReference, direction: Vector3) -> Measurement: ...
    def capture_snapshot(self, annotations: list[Annotation]) -> Snapshot: ...
```

The real interface can differ, but the boundary must preserve these properties:

- No Qt widgets in domain/calculation modules.
- No OCCT classes in project JSON.
- No direct table editing logic inside the CAD adapter.
- Geometry references persist as serializable ids plus geometric fallback signatures.

## Primary CAD Viewer Boundary

The final product viewer should use OCCT AIS/V3d as the primary CAD display and selection layer. Tessellated meshes may exist inside OCCT or as secondary diagnostic exports, but the application must not use mesh data as the authoritative CAD model for selection, measurement, or persistence.

The Python prototype viewer path is:

```python
from OCC.Display.backend import load_backend

load_backend("pyqt6")
from OCC.Display.qtDisplay import qtViewer3d
```

The `mdts-cad312` environment uses `pythonocc-core 7.7.2` with the `novtk` OCCT build. That build intentionally removes the OCCT/VTK bridge while preserving STEP/IGES import, B-Rep topology, AIS presentation, V3d views, Graphic3d styling, and SelectMgr selection support. It avoids the Conda Qt5 dependency chain that conflicts with PyQt6.

The viewer layer owns transient runtime objects:

- `AIS_InteractiveContext`, `AIS_Shape`, and presentation attributes.
- `V3d_Viewer` and `V3d_View`.
- Selection modes and highlight state.
- Camera state and snapshot capture mechanics.
- Maps between AIS owners/objects and serializable `ShapeReference` ids.

The viewer layer must expose only serializable or domain-level objects to the rest of the application: `ShapeReference`, `FeatureReference`, camera dictionaries, highlight role names, and `Snapshot` metadata.

The first fallback, if pythonocc's PyQt6 viewer helper is not stable enough, is a small C++ Qt6 + OCCT viewport component wrapped for Python. The fallback is not a mesh-only PyVista primary viewer.

## Persistence Model

Extend the existing `.tolproj` JSON style:

```json
{
  "schema_version": 2,
  "project_type": "cad_1d_tolerance",
  "unit_system": "mm",
  "cad_documents": [],
  "stackups": [],
  "settings": {},
  "snapshots": [],
  "reports": []
}
```

Persist:

- Original CAD path and content hash.
- Import settings and units.
- Assembly tree labels and display names.
- Shape references as serializable ids and fallback geometry signatures.
- Stackup endpoints, direction, annotation plane, and contributors.
- User overrides and manual GD&T rows.
- Result snapshots and report snapshot references.

Do not persist:

- Raw OCCT pointer handles.
- Raw AIS/V3d viewer handles.
- VTK actor/polydata handles.
- Absolute temp paths as the only artifact reference.
- Generated report images without a manifest entry.

## Technology Risks

- OCCT neutral import is appropriate, but direct native CAD import is out of scope unless a commercial SDK is later selected.
- `pythonocc-core` may create packaging and version constraints on Windows. Validate before deep UI coupling.
- pythonocc's `qtViewer3d` is a native-window Qt widget, not a modern `QOpenGLWidget`; resize, focus, HiDPI, snapshot, and lifecycle behavior need a dedicated spike before final UI coupling.
- The `novtk` runtime does not provide OCCT IVtk bridge modules. This is acceptable for an AIS/V3d primary viewer, but it rules out relying on OCCT-VTK bridge examples as the main product viewer.
- Topology references can break when a revised STEP file changes entity order or shape decomposition.
- GD&T interpretation is engineering logic, not a simple metadata read.
- QML is present in the repo, but this CAD clone should use Qt Widgets/model-view first because the UI is table-heavy and dock-heavy.
