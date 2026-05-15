"""OCCT-backed neutral CAD geometry adapter."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.util
from pathlib import Path
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

_GENERIC_XDE_NAME_PREFIXES = (
    "Open CASCADE STEP translator",
    "Open CASCADE IGES translator",
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
    STEPCAFControl_Reader: Any | None = None
    IGESCAFControl_Reader: Any | None = None
    XCAFApp_Application: Any | None = None
    XCAFDoc_DocumentTool: Any | None = None
    XCAFDoc_ColorGen: Any | None = None
    XCAFDoc_ColorSurf: Any | None = None
    XCAFDoc_ColorCurv: Any | None = None
    TDocStd_Document: Any | None = None
    TDF_Label: Any | None = None
    TDF_LabelSequence: Any | None = None
    Quantity_Color: Any | None = None


@dataclass(frozen=True)
class _XdeImportResult:
    caf_document: Any
    shape_tool: Any
    color_tool: Any
    free_labels: list[Any]
    root_shape: Any
    reader_name: str
    label_sequences: list[Any]


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
        xde_model = _read_xde_neutral_model(input_path, file_format, modules)
        root_shape = (
            xde_model.root_shape
            if xde_model is not None
            else _read_neutral_shape(input_path, file_format, modules)
        )
        document = CadDocument(
            source_path=str(input_path),
            file_hash=f"sha256:{_sha256_file(input_path)}",
            file_format=file_format,
            imported_at=_utc_timestamp(),
            units=active_settings.units,
            display_name=input_path.name,
            import_settings=active_settings.to_dict(),
        )
        if xde_model is not None:
            self._index = self._build_xde_index(
                document,
                xde_model,
                modules,
                active_settings,
            )
            if self._index.shapes:
                return self._index.document
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

    def runtime_shape(self, shape_ref: ShapeReference) -> Any | None:
        """Return the live OCCT shape for viewport code; never persist this value."""

        return self._shape_cache.get(shape_ref.id)

    def kernel_shape(self, shape_ref: ShapeReference) -> Any | None:
        """Backward-compatible alias for the explicit runtime shape contract."""

        return self.runtime_shape(shape_ref)

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

    def _build_xde_index(
        self,
        document: CadDocument,
        xde_model: _XdeImportResult,
        modules: _OccModules,
        settings: CadImportSettings,
    ) -> GeometryIndex:
        self._shape_cache.clear()
        document.metadata = {
            **document.metadata,
            "cad_metadata_source": "occt_xde",
            "xde_reader": xde_model.reader_name,
            "xde_free_shape_count": len(xde_model.free_labels),
        }

        shapes: list[ShapeReference] = []
        features: list[FeatureReference] = []
        part_counter = [0]

        free_labels = list(xde_model.free_labels)
        if len(free_labels) == 1:
            free_label = free_labels[0]
            root_target = _xde_target_label(xde_model.shape_tool, modules, free_label)
            root_children = _xde_components(
                xde_model.shape_tool,
                modules,
                root_target,
                keepalive=xde_model.label_sequences,
            )
            if root_children:
                root_name = _xde_display_name(
                    xde_model.shape_tool,
                    modules,
                    free_label,
                    fallback=document.display_name or Path(document.source_path).name,
                )
                root_node = AssemblyNode(
                    id=_stable_xde_id("asm", document, _xde_label_entry(free_label)),
                    name=root_name,
                    node_type=AssemblyNodeType.ROOT,
                    transform=_xde_transform(xde_model.shape_tool, modules, free_label),
                    source_label=_xde_label_entry(free_label),
                    metadata=_xde_label_metadata(
                        xde_model.shape_tool,
                        modules,
                        free_label,
                        role="root",
                    ),
                )
                document.assembly_root = root_node
                self._append_xde_children(
                    parent_node=root_node,
                    labels=root_children,
                    document=document,
                    xde_model=xde_model,
                    modules=modules,
                    settings=settings,
                    shapes=shapes,
                    features=features,
                    assembly_path=[root_node.name],
                    part_counter=part_counter,
                )
                return GeometryIndex(document=document, shapes=shapes, features=features)

        root_node = AssemblyNode(
            id=_stable_xde_id("asm", document, "root"),
            name=document.display_name or Path(document.source_path).name,
            node_type=AssemblyNodeType.ROOT,
            source_label="root",
            metadata={
                "metadata_source": "occt_xde",
                "xde_root": True,
                "xde_free_shape_count": len(free_labels),
            },
        )
        document.assembly_root = root_node
        self._append_xde_children(
            parent_node=root_node,
            labels=free_labels,
            document=document,
            xde_model=xde_model,
            modules=modules,
            settings=settings,
            shapes=shapes,
            features=features,
            assembly_path=[root_node.name],
            part_counter=part_counter,
        )
        return GeometryIndex(document=document, shapes=shapes, features=features)

    def _append_xde_children(
        self,
        parent_node: AssemblyNode,
        labels: list[Any],
        document: CadDocument,
        xde_model: _XdeImportResult,
        modules: _OccModules,
        settings: CadImportSettings,
        shapes: list[ShapeReference],
        features: list[FeatureReference],
        assembly_path: list[str],
        part_counter: list[int],
    ) -> None:
        base_names = [
            _xde_display_name(
                xde_model.shape_tool,
                modules,
                label,
                fallback=f"Part {index}",
            )
            for index, label in enumerate(labels, start=1)
        ]
        name_counts = Counter(base_names)
        seen_names: dict[str, int] = {}
        for sibling_index, label in enumerate(labels, start=1):
            base_name = base_names[sibling_index - 1]
            seen_names[base_name] = seen_names.get(base_name, 0) + 1
            display_name = _xde_occurrence_name(
                base_name,
                occurrence_count=name_counts[base_name],
                occurrence_index=seen_names[base_name],
            )
            self._append_xde_label_node(
                parent_node=parent_node,
                label=label,
                display_name=display_name,
                document=document,
                xde_model=xde_model,
                modules=modules,
                settings=settings,
                shapes=shapes,
                features=features,
                assembly_path=assembly_path,
                part_counter=part_counter,
            )

    def _append_xde_label_node(
        self,
        parent_node: AssemblyNode,
        label: Any,
        display_name: str,
        document: CadDocument,
        xde_model: _XdeImportResult,
        modules: _OccModules,
        settings: CadImportSettings,
        shapes: list[ShapeReference],
        features: list[FeatureReference],
        assembly_path: list[str],
        part_counter: list[int],
    ) -> None:
        target_label = _xde_target_label(xde_model.shape_tool, modules, label)
        child_labels = _xde_components(
            xde_model.shape_tool,
            modules,
            target_label,
            keepalive=xde_model.label_sequences,
        )
        node_type = AssemblyNodeType.ASSEMBLY if child_labels else AssemblyNodeType.PART
        node_path = [*assembly_path, display_name]
        color = _xde_color(xde_model, modules, label, target_label)
        if node_type == AssemblyNodeType.PART:
            part_counter[0] += 1
            if color is None:
                color = display_color_for_part(display_name, part_counter[0])

        node = AssemblyNode(
            id=_stable_xde_id("asm", document, _xde_label_entry(label)),
            name=display_name,
            node_type=node_type,
            parent_id=parent_node.id,
            transform=_xde_transform(xde_model.shape_tool, modules, label),
            display_color=color,
            source_label=_xde_label_entry(label),
            metadata=_xde_label_metadata(
                xde_model.shape_tool,
                modules,
                label,
                role=node_type.value,
                color=color,
            ),
        )
        parent_node.children.append(node)

        if child_labels:
            self._append_xde_children(
                parent_node=node,
                labels=child_labels,
                document=document,
                xde_model=xde_model,
                modules=modules,
                settings=settings,
                shapes=shapes,
                features=features,
                assembly_path=node_path,
                part_counter=part_counter,
            )
            return

        body_shape = _xde_shape(xde_model.shape_tool, label)
        if body_shape is None:
            body_shape = _xde_shape(xde_model.shape_tool, target_label)
        if body_shape is None:
            return

        body_ref = _make_xde_shape_reference(
            document=document,
            label=label,
            referred_label=target_label,
            assembly_path=node_path,
            shape_type=ShapeKind.BODY,
            ordinal=0,
            signature={"topology": "body"},
            display_name=display_name,
            color=color,
        )
        shapes.append(body_ref)
        self._shape_cache[body_ref.id] = body_shape

        faces = list(_iter_subshapes(modules, body_shape, modules.TopAbs_FACE))
        for face_index, face in enumerate(faces, start=1):
            face = modules.topods.Face(face)
            face_ref = _make_xde_shape_reference(
                document=document,
                label=label,
                referred_label=target_label,
                assembly_path=node_path,
                shape_type=ShapeKind.FACE,
                ordinal=face_index,
                signature=_face_signature(modules, face),
                display_name=f"{display_name} Face {face_index}",
                color=color,
            )
            shapes.append(face_ref)
            self._shape_cache[face_ref.id] = face
            features.append(
                feature_from_shape_reference(
                    face_ref,
                    name=face_ref.fallback_display_name,
                    owner_part_id=node.id,
                )
            )

        if settings.include_edges:
            edges = list(_iter_subshapes(modules, body_shape, modules.TopAbs_EDGE))
            for edge_index, edge in enumerate(edges, start=1):
                edge = modules.topods.Edge(edge)
                edge_ref = _make_xde_shape_reference(
                    document=document,
                    label=label,
                    referred_label=target_label,
                    assembly_path=node_path,
                    shape_type=ShapeKind.EDGE,
                    ordinal=edge_index,
                    signature=_edge_signature(modules, edge),
                    display_name=f"{display_name} Edge {edge_index}",
                    color=color,
                )
                shapes.append(edge_ref)
                self._shape_cache[edge_ref.id] = edge
                features.append(
                    feature_from_shape_reference(
                        edge_ref,
                        name=edge_ref.fallback_display_name,
                        owner_part_id=node.id,
                    )
                )

        if settings.include_vertices:
            vertices = list(_iter_subshapes(modules, body_shape, modules.TopAbs_VERTEX))
            for vertex_index, vertex in enumerate(vertices, start=1):
                vertex = modules.topods.Vertex(vertex)
                vertex_ref = _make_xde_shape_reference(
                    document=document,
                    label=label,
                    referred_label=target_label,
                    assembly_path=node_path,
                    shape_type=ShapeKind.VERTEX,
                    ordinal=vertex_index,
                    signature=_vertex_signature(modules, vertex),
                    display_name=f"{display_name} Vertex {vertex_index}",
                    color=color,
                )
                shapes.append(vertex_ref)
                self._shape_cache[vertex_ref.id] = vertex
                features.append(
                    feature_from_shape_reference(
                        vertex_ref,
                        name=vertex_ref.fallback_display_name,
                        owner_part_id=node.id,
                    )
                )


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

    STEPCAFControl_Reader = None
    IGESCAFControl_Reader = None
    XCAFApp_Application = None
    XCAFDoc_DocumentTool = None
    XCAFDoc_ColorGen = None
    XCAFDoc_ColorSurf = None
    XCAFDoc_ColorCurv = None
    TDocStd_Document = None
    TDF_Label = None
    TDF_LabelSequence = None
    Quantity_Color = None
    try:
        from OCC.Core.IGESCAFControl import IGESCAFControl_Reader as iges_caf_reader
        from OCC.Core.Quantity import Quantity_Color as quantity_color
        from OCC.Core.STEPCAFControl import STEPCAFControl_Reader as step_caf_reader
        from OCC.Core.TDF import TDF_Label as tdf_label
        from OCC.Core.TDF import TDF_LabelSequence as tdf_label_sequence
        from OCC.Core.TDocStd import TDocStd_Document as tdocstd_document
        from OCC.Core.XCAFApp import XCAFApp_Application as xcaf_application
        from OCC.Core.XCAFDoc import (
            XCAFDoc_ColorCurv as xcaf_color_curv,
            XCAFDoc_ColorGen as xcaf_color_gen,
            XCAFDoc_ColorSurf as xcaf_color_surf,
            XCAFDoc_DocumentTool as xcaf_document_tool,
        )

        STEPCAFControl_Reader = step_caf_reader
        IGESCAFControl_Reader = iges_caf_reader
        XCAFApp_Application = xcaf_application
        XCAFDoc_DocumentTool = xcaf_document_tool
        XCAFDoc_ColorGen = xcaf_color_gen
        XCAFDoc_ColorSurf = xcaf_color_surf
        XCAFDoc_ColorCurv = xcaf_color_curv
        TDocStd_Document = tdocstd_document
        TDF_Label = tdf_label
        TDF_LabelSequence = tdf_label_sequence
        Quantity_Color = quantity_color
    except ImportError:
        pass

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
        STEPCAFControl_Reader=STEPCAFControl_Reader,
        IGESCAFControl_Reader=IGESCAFControl_Reader,
        XCAFApp_Application=XCAFApp_Application,
        XCAFDoc_DocumentTool=XCAFDoc_DocumentTool,
        XCAFDoc_ColorGen=XCAFDoc_ColorGen,
        XCAFDoc_ColorSurf=XCAFDoc_ColorSurf,
        XCAFDoc_ColorCurv=XCAFDoc_ColorCurv,
        TDocStd_Document=TDocStd_Document,
        TDF_Label=TDF_Label,
        TDF_LabelSequence=TDF_LabelSequence,
        Quantity_Color=Quantity_Color,
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


def _read_xde_neutral_model(
    path: Path,
    file_format: CadFileFormat,
    modules: _OccModules,
) -> _XdeImportResult | None:
    if not _xde_modules_available(modules):
        return None
    if file_format == CadFileFormat.STEP:
        if modules.STEPCAFControl_Reader is None:
            return None
        reader = modules.STEPCAFControl_Reader()
        reader_name = "STEPCAFControl_Reader"
    elif file_format == CadFileFormat.IGES:
        if modules.IGESCAFControl_Reader is None:
            return None
        reader = modules.IGESCAFControl_Reader()
        reader_name = "IGESCAFControl_Reader"
    else:
        return None

    for method_name in (
        "SetNameMode",
        "SetColorMode",
        "SetLayerMode",
        "SetPropsMode",
        "SetProductMetaMode",
        "SetMetaMode",
    ):
        method = getattr(reader, method_name, None)
        if method is not None:
            try:
                method(True)
            except Exception:
                pass

    status = reader.ReadFile(str(path))
    if status != modules.IFSelect_RetDone:
        return None

    application = modules.XCAFApp_Application.GetApplication()
    caf_document = modules.TDocStd_Document("MDTV-XCAF")
    application.NewDocument("MDTV-XCAF", caf_document)
    try:
        transferred = reader.Transfer(caf_document)
    except Exception:
        return None
    if not transferred:
        return None

    shape_tool = modules.XCAFDoc_DocumentTool.ShapeTool(caf_document.Main())
    color_tool = modules.XCAFDoc_DocumentTool.ColorTool(caf_document.Main())
    label_sequence = modules.TDF_LabelSequence()
    shape_tool.GetFreeShapes(label_sequence)
    free_labels = _label_sequence_items(label_sequence)
    if not free_labels:
        return None
    try:
        root_shape = shape_tool.GetOneShape()
    except Exception:
        root_shape = None
    if root_shape is None:
        return None
    return _XdeImportResult(
        caf_document=caf_document,
        shape_tool=shape_tool,
        color_tool=color_tool,
        free_labels=free_labels,
        root_shape=root_shape,
        reader_name=reader_name,
        label_sequences=[label_sequence],
    )


def _xde_modules_available(modules: _OccModules) -> bool:
    required = (
        modules.XCAFApp_Application,
        modules.XCAFDoc_DocumentTool,
        modules.TDocStd_Document,
        modules.TDF_Label,
        modules.TDF_LabelSequence,
        modules.Quantity_Color,
    )
    readers = (modules.STEPCAFControl_Reader, modules.IGESCAFControl_Reader)
    return all(item is not None for item in required) and any(
        reader is not None for reader in readers
    )


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


def _make_xde_shape_reference(
    document: CadDocument,
    label: Any,
    referred_label: Any,
    assembly_path: list[str],
    shape_type: ShapeKind,
    ordinal: int,
    signature: dict[str, Any],
    display_name: str,
    color: tuple[int, int, int] | None,
) -> ShapeReference:
    label_entry = _xde_label_entry(label)
    referred_entry = _xde_label_entry(referred_label)
    kernel_label = (
        f"{document.file_hash or document.id}:xde:{label_entry}:"
        f"{shape_type.value}:{ordinal}"
    )
    safe_id = _stable_xde_id(
        "shape",
        document,
        f"{label_entry}:{shape_type.value}:{ordinal}",
    )
    metadata: dict[str, Any] = {
        "metadata_source": "occt_xde",
        "xde_label": label_entry,
        "xde_referred_label": referred_entry,
    }
    if color is not None:
        metadata["display_color"] = list(color)
    return ShapeReference(
        id=safe_id,
        document_id=document.id,
        assembly_path=assembly_path,
        shape_type=shape_type,
        kernel_label=kernel_label,
        geometric_signature=signature,
        fallback_display_name=display_name,
        metadata=metadata,
    )


def _label_sequence_items(sequence: Any) -> list[Any]:
    return [sequence.Value(index) for index in range(1, sequence.Length() + 1)]


def _xde_components(
    shape_tool: Any,
    modules: _OccModules,
    label: Any,
    keepalive: list[Any] | None = None,
) -> list[Any]:
    sequence = modules.TDF_LabelSequence()
    try:
        shape_tool.GetComponents(label, sequence)
    except Exception:
        return []
    if keepalive is not None:
        keepalive.append(sequence)
    return _label_sequence_items(sequence)


def _xde_target_label(shape_tool: Any, modules: _OccModules, label: Any) -> Any:
    try:
        if not shape_tool.IsReference(label):
            return label
        referred = modules.TDF_Label()
        if shape_tool.GetReferredShape(label, referred) and not referred.IsNull():
            return referred
    except Exception:
        pass
    return label


def _xde_display_name(
    shape_tool: Any,
    modules: _OccModules,
    label: Any,
    fallback: str,
) -> str:
    label_name = _clean_xde_name(_xde_label_name(label))
    if label_name:
        return label_name
    target = _xde_target_label(shape_tool, modules, label)
    target_name = _clean_xde_name(_xde_label_name(target))
    return target_name or fallback


def _xde_occurrence_name(
    name: str,
    occurrence_count: int,
    occurrence_index: int,
) -> str:
    if occurrence_count <= 1:
        return name
    if ":" in name:
        return f"{name} ({occurrence_index})"
    return f"{name}:{occurrence_index}"


def _xde_label_metadata(
    shape_tool: Any,
    modules: _OccModules,
    label: Any,
    role: str,
    color: tuple[int, int, int] | None = None,
) -> dict[str, Any]:
    target = _xde_target_label(shape_tool, modules, label)
    metadata: dict[str, Any] = {
        "metadata_source": "occt_xde",
        "role": role,
        "xde_label": _xde_label_entry(label),
        "xde_name": _xde_label_name(label),
        "xde_referred_label": _xde_label_entry(target),
        "xde_referred_name": _xde_label_name(target),
        "xde_is_component": _xde_bool(shape_tool, "IsComponent", label),
        "xde_is_reference": _xde_bool(shape_tool, "IsReference", label),
        "xde_is_assembly": _xde_bool(shape_tool, "IsAssembly", target),
        "xde_is_simple_shape": _xde_bool(shape_tool, "IsSimpleShape", target),
    }
    if color is not None:
        metadata["display_color"] = list(color)
    return metadata


def _xde_bool(shape_tool: Any, method_name: str, label: Any) -> bool:
    try:
        return bool(getattr(shape_tool, method_name)(label))
    except Exception:
        return False


def _xde_label_name(label: Any) -> str:
    try:
        return str(label.GetLabelName() or "").strip()
    except Exception:
        return ""


def _clean_xde_name(name: str) -> str:
    value = str(name or "").strip()
    if not value or value.isdigit():
        return ""
    for prefix in _GENERIC_XDE_NAME_PREFIXES:
        if value.startswith(prefix):
            return ""
    return value


def _xde_label_entry(label: Any) -> str:
    try:
        return str(label.EntryDump())
    except Exception:
        try:
            return f"tag:{label.Tag()}"
        except Exception:
            return ""


def _xde_shape(shape_tool: Any, label: Any) -> Any | None:
    try:
        return shape_tool.GetShape(label)
    except Exception:
        return None


def _xde_color(
    xde_model: _XdeImportResult,
    modules: _OccModules,
    label: Any,
    target_label: Any,
) -> tuple[int, int, int] | None:
    color_types = tuple(
        color_type
        for color_type in (
            modules.XCAFDoc_ColorSurf,
            modules.XCAFDoc_ColorGen,
            modules.XCAFDoc_ColorCurv,
        )
        if color_type is not None
    )
    shapes = [
        _xde_shape(xde_model.shape_tool, label),
        _xde_shape(xde_model.shape_tool, target_label),
    ]
    for shape in shapes:
        if shape is None:
            continue
        for color_type in color_types:
            color = _xde_color_from_tool(
                xde_model.color_tool,
                modules,
                shape,
                color_type,
                instance=True,
            )
            if color is not None:
                return color
        for color_type in color_types:
            color = _xde_color_from_tool(
                xde_model.color_tool,
                modules,
                shape,
                color_type,
                instance=False,
            )
            if color is not None:
                return color
    return None


def _xde_color_from_tool(
    color_tool: Any,
    modules: _OccModules,
    shape: Any,
    color_type: Any,
    instance: bool,
) -> tuple[int, int, int] | None:
    quantity = modules.Quantity_Color()
    try:
        if instance:
            found = color_tool.GetInstanceColor(shape, color_type, quantity)
        else:
            found = color_tool.GetColor(shape, color_type, quantity)
    except Exception:
        return None
    if not found:
        return None
    return (
        _unit_color_to_byte(quantity.Red()),
        _unit_color_to_byte(quantity.Green()),
        _unit_color_to_byte(quantity.Blue()),
    )


def _unit_color_to_byte(value: float) -> int:
    return max(0, min(255, int(round(float(value) * 255.0))))


def _xde_transform(shape_tool: Any, modules: _OccModules, label: Any) -> list[float]:
    try:
        location = shape_tool.GetLocation(label)
        transform = location.Transformation()
        return [
            float(transform.Value(1, 1)),
            float(transform.Value(1, 2)),
            float(transform.Value(1, 3)),
            float(transform.Value(1, 4)),
            float(transform.Value(2, 1)),
            float(transform.Value(2, 2)),
            float(transform.Value(2, 3)),
            float(transform.Value(2, 4)),
            float(transform.Value(3, 1)),
            float(transform.Value(3, 2)),
            float(transform.Value(3, 3)),
            float(transform.Value(3, 4)),
            0.0,
            0.0,
            0.0,
            1.0,
        ]
    except Exception:
        return [
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
        ]


def _stable_xde_id(prefix: str, document: CadDocument, key: str) -> str:
    document_key = document.file_hash
    if ":" in document_key:
        document_key = document_key.split(":", 1)[1]
    document_key = document_key[:16] or document.id
    return f"{prefix}_{_safe_identifier(document_key)}_{_safe_identifier(key)}"


def _safe_identifier(value: str) -> str:
    pieces = [
        character.lower() if character.isascii() and character.isalnum() else "_"
        for character in str(value)
    ]
    identifier = "".join(pieces).strip("_")
    while "__" in identifier:
        identifier = identifier.replace("__", "_")
    return identifier or "item"


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
