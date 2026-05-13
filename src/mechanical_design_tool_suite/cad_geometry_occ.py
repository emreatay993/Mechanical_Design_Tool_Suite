"""OCCT-backed neutral CAD geometry adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.util
from pathlib import Path
from collections.abc import Sequence
from typing import Any

from .cad_display_style import display_color_for_part
from .cad_geometry_api import (
    CadGeometryError,
    CadGeometrySession,
    CadImportSettings,
    GeometryIndex,
    Measurement,
    cad_format_from_path,
    feature_from_shape_reference,
    measure_feature_pair,
    shape_reference_label,
)
from .cad_tolerance_models import (
    AssemblyNode,
    AssemblyNodeType,
    CadDocument,
    CadFileFormat,
    FeatureKind,
    FeatureReference,
    ShapeKind,
    ShapeReference,
    Vector3D,
)


OCC_DEPENDENCY_MESSAGE = (
    "OCCT Python bindings are unavailable. P03 keeps OCC usage behind "
    "cad_geometry_occ.py; install a compatible pythonocc-core/OCC binding to "
    "enable STEP/IGES import tests."
)


class CadKernelUnavailable(CadGeometryError):
    """Raised when the optional OCCT Python binding cannot be imported."""


@dataclass(frozen=True)
class _OccModules:
    STEPControl_Reader: Any
    IGESControl_Reader: Any
    IFSelect_RetDone: Any
    TopAbs_SOLID: Any
    TopAbs_FACE: Any
    TopAbs_EDGE: Any
    TopAbs_VERTEX: Any
    TopExp_Explorer: Any
    topods: Any
    BRepAdaptor_Surface: Any
    BRepAdaptor_Curve: Any
    GeomAbs_Plane: Any
    GeomAbs_Cylinder: Any
    GeomAbs_Line: Any
    GeomAbs_Circle: Any
    BRep_Tool: Any
    GProp_GProps: Any
    brepgprop: Any | None = None
    brepgprop_SurfaceProperties: Any | None = None


def is_occ_available() -> bool:
    return importlib.util.find_spec("OCC") is not None


class OccCadGeometrySession(CadGeometrySession):
    """Neutral STEP/IGES import through pythonocc/OCCT."""

    def __init__(self) -> None:
        self._index: GeometryIndex | None = None
        self._shape_cache: dict[str, Any] = {}

    def import_file(
        self,
        path: str | Path,
        settings: CadImportSettings | None = None,
    ) -> CadDocument:
        input_path = Path(path)
        file_format = cad_format_from_path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"CAD file does not exist: {input_path}")

        self._index = None
        self._shape_cache.clear()
        modules = _load_occ_modules()
        active_settings = settings or CadImportSettings()
        root_shape = _read_neutral_shape(input_path, file_format, modules)
        document = CadDocument(
            source_path=str(input_path),
            file_hash=f"sha256:{_sha256_file(input_path)}",
            file_format=file_format,
            imported_at=_utc_timestamp(),
            units=active_settings.units,
            display_name=input_path.name,
            import_settings=active_settings.to_dict(),
        )
        self._index = self._build_index(document, root_shape, modules, active_settings)
        return self._index.document

    def assembly_tree(self) -> list[AssemblyNode]:
        if self._index is None or self._index.document.assembly_root is None:
            return []
        return [self._index.document.assembly_root]

    def shape_references(
        self,
        kinds: set[ShapeKind] | None = None,
    ) -> list[ShapeReference]:
        if self._index is None:
            return []
        return self._index.shapes_by_kind(*(kinds or set()))

    def feature_references(
        self,
        kinds: set[FeatureKind] | None = None,
    ) -> list[FeatureReference]:
        if self._index is None:
            return []
        return self._index.features_by_kind(*(kinds or set()))

    def measure_between(
        self,
        a: FeatureReference,
        b: FeatureReference,
        direction: Vector3D | Sequence[float],
    ) -> Measurement:
        units = self._index.document.units if self._index is not None else "mm"
        return measure_feature_pair(a, b, direction, units=units)

    def kernel_shape(self, shape_ref: ShapeReference) -> Any | None:
        """Return the live OCCT shape for viewport code; never persist this value."""

        return self._shape_cache.get(shape_ref.id)

    def _build_index(
        self,
        document: CadDocument,
        root_shape: Any,
        modules: _OccModules,
        settings: CadImportSettings,
    ) -> GeometryIndex:
        self._shape_cache.clear()
        root_node = AssemblyNode(
            name=document.display_name or Path(document.source_path).name,
            node_type=AssemblyNodeType.ROOT,
            source_label="root",
        )
        document.assembly_root = root_node

        shapes: list[ShapeReference] = []
        features: list[FeatureReference] = []
        bodies = list(_iter_subshapes(modules, root_shape, modules.TopAbs_SOLID))
        if not bodies:
            bodies = [root_shape]

        for body_index, body_shape in enumerate(bodies, start=1):
            body_node = AssemblyNode(
                name=f"Body {body_index}",
                node_type=AssemblyNodeType.BODY,
                parent_id=root_node.id,
                display_color=display_color_for_part(f"Body {body_index}", body_index),
                source_label=f"body:{body_index}",
            )
            root_node.children.append(body_node)
            body_path = [root_node.name, body_node.name]
            body_ref = _make_shape_reference(
                document=document,
                assembly_path=body_path,
                shape_type=ShapeKind.BODY,
                ordinal=body_index,
                signature={"topology": "body"},
                display_name=body_node.name,
            )
            shapes.append(body_ref)
            self._shape_cache[body_ref.id] = body_shape

            faces = list(_iter_subshapes(modules, body_shape, modules.TopAbs_FACE))
            for face_index, face in enumerate(faces, start=1):
                face = modules.topods.Face(face)
                signature = _face_signature(modules, face)
                face_ref = _make_shape_reference(
                    document=document,
                    assembly_path=body_path,
                    shape_type=ShapeKind.FACE,
                    ordinal=face_index,
                    signature=signature,
                    display_name=f"{body_node.name} Face {face_index}",
                )
                shapes.append(face_ref)
                self._shape_cache[face_ref.id] = face
                features.append(
                    feature_from_shape_reference(
                        face_ref,
                        name=face_ref.fallback_display_name,
                        owner_part_id=body_node.id,
                    )
                )

            if settings.include_edges:
                edges = list(_iter_subshapes(modules, body_shape, modules.TopAbs_EDGE))
                for edge_index, edge in enumerate(edges, start=1):
                    edge = modules.topods.Edge(edge)
                    signature = _edge_signature(modules, edge)
                    edge_ref = _make_shape_reference(
                        document=document,
                        assembly_path=body_path,
                        shape_type=ShapeKind.EDGE,
                        ordinal=edge_index,
                        signature=signature,
                        display_name=f"{body_node.name} Edge {edge_index}",
                    )
                    shapes.append(edge_ref)
                    self._shape_cache[edge_ref.id] = edge
                    features.append(
                        feature_from_shape_reference(
                            edge_ref,
                            name=edge_ref.fallback_display_name,
                            owner_part_id=body_node.id,
                        )
                    )

            if settings.include_vertices:
                vertices = list(
                    _iter_subshapes(modules, body_shape, modules.TopAbs_VERTEX)
                )
                for vertex_index, vertex in enumerate(vertices, start=1):
                    vertex = modules.topods.Vertex(vertex)
                    signature = _vertex_signature(modules, vertex)
                    vertex_ref = _make_shape_reference(
                        document=document,
                        assembly_path=body_path,
                        shape_type=ShapeKind.VERTEX,
                        ordinal=vertex_index,
                        signature=signature,
                        display_name=f"{body_node.name} Vertex {vertex_index}",
                    )
                    shapes.append(vertex_ref)
                    self._shape_cache[vertex_ref.id] = vertex
                    features.append(
                        feature_from_shape_reference(
                            vertex_ref,
                            name=vertex_ref.fallback_display_name,
                            owner_part_id=body_node.id,
                        )
                    )

        return GeometryIndex(document=document, shapes=shapes, features=features)


def _load_occ_modules() -> _OccModules:
    try:
        from OCC.Core.BRep import BRep_Tool
        from OCC.Core.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
        from OCC.Core.GProp import GProp_GProps
        from OCC.Core.GeomAbs import (
            GeomAbs_Circle,
            GeomAbs_Cylinder,
            GeomAbs_Line,
            GeomAbs_Plane,
        )
        from OCC.Core.IFSelect import IFSelect_RetDone
        from OCC.Core.IGESControl import IGESControl_Reader
        from OCC.Core.STEPControl import STEPControl_Reader
        from OCC.Core.TopAbs import (
            TopAbs_EDGE,
            TopAbs_FACE,
            TopAbs_SOLID,
            TopAbs_VERTEX,
        )
        from OCC.Core.TopExp import TopExp_Explorer
        from OCC.Core.TopoDS import topods
    except ImportError as exc:
        raise CadKernelUnavailable(OCC_DEPENDENCY_MESSAGE) from exc

    brepgprop = None
    try:
        from OCC.Core.BRepGProp import brepgprop as brepgprop_module

        brepgprop = brepgprop_module
    except ImportError:
        brepgprop = None

    surface_properties = None
    try:
        from OCC.Core.BRepGProp import brepgprop_SurfaceProperties

        surface_properties = brepgprop_SurfaceProperties
    except ImportError:
        surface_properties = None

    return _OccModules(
        STEPControl_Reader=STEPControl_Reader,
        IGESControl_Reader=IGESControl_Reader,
        IFSelect_RetDone=IFSelect_RetDone,
        TopAbs_SOLID=TopAbs_SOLID,
        TopAbs_FACE=TopAbs_FACE,
        TopAbs_EDGE=TopAbs_EDGE,
        TopAbs_VERTEX=TopAbs_VERTEX,
        TopExp_Explorer=TopExp_Explorer,
        topods=topods,
        BRepAdaptor_Surface=BRepAdaptor_Surface,
        BRepAdaptor_Curve=BRepAdaptor_Curve,
        GeomAbs_Plane=GeomAbs_Plane,
        GeomAbs_Cylinder=GeomAbs_Cylinder,
        GeomAbs_Line=GeomAbs_Line,
        GeomAbs_Circle=GeomAbs_Circle,
        BRep_Tool=BRep_Tool,
        GProp_GProps=GProp_GProps,
        brepgprop=brepgprop,
        brepgprop_SurfaceProperties=surface_properties,
    )


def _read_neutral_shape(
    path: Path,
    file_format: CadFileFormat,
    modules: _OccModules,
) -> Any:
    if file_format == CadFileFormat.STEP:
        reader = modules.STEPControl_Reader()
    elif file_format == CadFileFormat.IGES:
        reader = modules.IGESControl_Reader()
    else:
        raise ValueError("OCCT import supports only STEP and IGES neutral files.")

    status = reader.ReadFile(str(path))
    if status != modules.IFSelect_RetDone:
        raise CadGeometryError(f"OCCT failed to read {file_format.value.upper()} file: {path}")
    transferred = reader.TransferRoots()
    if transferred <= 0:
        raise CadGeometryError(f"OCCT did not transfer any roots from: {path}")
    return reader.OneShape()


def _iter_subshapes(
    modules: _OccModules,
    shape: Any,
    topology_kind: Any,
) -> list[Any]:
    explorer = modules.TopExp_Explorer(shape, topology_kind)
    items: list[Any] = []
    while explorer.More():
        items.append(explorer.Current())
        explorer.Next()
    return items


def _make_shape_reference(
    document: CadDocument,
    assembly_path: list[str],
    shape_type: ShapeKind,
    ordinal: int,
    signature: dict[str, Any],
    display_name: str,
) -> ShapeReference:
    label = shape_reference_label(document.id, assembly_path, shape_type, ordinal)
    safe_id = f"shape_{label.replace(':', '_').replace('/', '_')}"
    return ShapeReference(
        id=safe_id,
        document_id=document.id,
        assembly_path=assembly_path,
        shape_type=shape_type,
        kernel_label=label,
        geometric_signature=signature,
        fallback_display_name=display_name,
    )


def _face_signature(modules: _OccModules, face: Any) -> dict[str, Any]:
    signature: dict[str, Any] = {"topology": "face"}
    adaptor = modules.BRepAdaptor_Surface(face)
    surface_type = adaptor.GetType()
    if surface_type == modules.GeomAbs_Plane:
        plane = adaptor.Plane()
        signature.update(
            {
                "surface_type": "plane",
                "point": _gp_point(plane.Location()),
                "normal": _gp_direction(plane.Axis().Direction()),
            }
        )
    elif surface_type == modules.GeomAbs_Cylinder:
        cylinder = adaptor.Cylinder()
        signature.update(
            {
                "surface_type": "cylinder",
                "point": _gp_point(cylinder.Location()),
                "axis": _gp_direction(cylinder.Axis().Direction()),
                "radius": float(cylinder.Radius()),
            }
        )
    else:
        signature["surface_type"] = str(surface_type)

    _add_surface_properties(modules, face, signature)
    return signature


def _edge_signature(modules: _OccModules, edge: Any) -> dict[str, Any]:
    signature: dict[str, Any] = {"topology": "edge"}
    adaptor = modules.BRepAdaptor_Curve(edge)
    curve_type = adaptor.GetType()
    if curve_type == modules.GeomAbs_Line:
        line = adaptor.Line()
        signature.update(
            {
                "curve_type": "line",
                "point": _gp_point(line.Location()),
                "axis": _gp_direction(line.Direction()),
            }
        )
    elif curve_type == modules.GeomAbs_Circle:
        circle = adaptor.Circle()
        signature.update(
            {
                "curve_type": "circle",
                "point": _gp_point(circle.Location()),
                "axis": _gp_direction(circle.Axis().Direction()),
                "radius": float(circle.Radius()),
            }
        )
    else:
        signature["curve_type"] = str(curve_type)
    return signature


def _vertex_signature(modules: _OccModules, vertex: Any) -> dict[str, Any]:
    point = _brep_tool_point(modules, vertex)
    return {
        "topology": "vertex",
        "point": _gp_point(point),
    }


def _add_surface_properties(
    modules: _OccModules,
    face: Any,
    signature: dict[str, Any],
) -> None:
    props = modules.GProp_GProps()
    try:
        if modules.brepgprop is not None and hasattr(
            modules.brepgprop,
            "SurfaceProperties",
        ):
            modules.brepgprop.SurfaceProperties(face, props)
        elif modules.brepgprop_SurfaceProperties is not None:
            modules.brepgprop_SurfaceProperties(face, props)
        else:
            return
        signature["area"] = float(props.Mass())
        signature.setdefault("center", _gp_point(props.CentreOfMass()))
    except Exception:
        signature["property_note"] = "OCCT surface properties were unavailable."


def _brep_tool_point(modules: _OccModules, vertex: Any) -> Any:
    tool = modules.BRep_Tool
    try:
        return tool.Pnt(vertex)
    except TypeError:
        return tool().Pnt(vertex)


def _gp_point(point: Any) -> list[float]:
    return [float(point.X()), float(point.Y()), float(point.Z())]


def _gp_direction(direction: Any) -> list[float]:
    return [float(direction.X()), float(direction.Y()), float(direction.Z())]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00",
        "Z",
    )
