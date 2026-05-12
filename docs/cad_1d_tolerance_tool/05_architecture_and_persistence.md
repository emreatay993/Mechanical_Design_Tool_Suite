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
- Absolute temp paths as the only artifact reference.
- Generated report images without a manifest entry.

## Technology Risks

- OCCT neutral import is appropriate, but direct native CAD import is out of scope unless a commercial SDK is later selected.
- `pythonocc-core` may create packaging and version constraints on Windows. Validate before deep UI coupling.
- Topology references can break when a revised STEP file changes entity order or shape decomposition.
- GD&T interpretation is engineering logic, not a simple metadata read.
- QML is present in the repo, but this CAD clone should use Qt Widgets/model-view first because the UI is table-heavy and dock-heavy.
