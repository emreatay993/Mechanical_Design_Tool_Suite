"""Reference geometry models and loaders for bolt visualization."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
from pathlib import Path
from typing import Any
from uuid import uuid4

from .cad_tolerance_models import CadFileFormat, ShapeKind


REFERENCE_DEFAULT_OPACITY = 0.35


class ReferenceGeometryFormat(str, Enum):
    """Visual reference geometry formats accepted by the bolt scene."""

    STEP = "step"
    IGES = "iges"
    STL = "stl"

    def __str__(self) -> str:
        return self.value


SUPPORTED_REFERENCE_GEOMETRY_SUFFIXES = {
    ".step": ReferenceGeometryFormat.STEP,
    ".stp": ReferenceGeometryFormat.STEP,
    ".iges": ReferenceGeometryFormat.IGES,
    ".igs": ReferenceGeometryFormat.IGES,
    ".stl": ReferenceGeometryFormat.STL,
}


class UnsupportedReferenceGeometryFormatError(ValueError):
    """Raised when a file is not usable as bolt reference geometry."""


class ReferenceGeometryImportError(RuntimeError):
    """Raised when a supported reference geometry file cannot be meshed."""


def new_reference_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


def clamp_opacity(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass
class ReferenceDisplayState:
    """Serializable display controls for one reference part."""

    visible: bool = True
    opacity: float = REFERENCE_DEFAULT_OPACITY
    selected: bool = False

    def __post_init__(self) -> None:
        self.visible = bool(self.visible)
        self.opacity = clamp_opacity(self.opacity)
        self.selected = bool(self.selected)

    def to_dict(self) -> dict[str, Any]:
        return {
            "visible": self.visible,
            "opacity": self.opacity,
            "selected": self.selected,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ReferenceDisplayState":
        if not data:
            return cls()
        return cls(
            visible=bool(data.get("visible", True)),
            opacity=float(data.get("opacity", REFERENCE_DEFAULT_OPACITY)),
            selected=bool(data.get("selected", False)),
        )


@dataclass
class ReferencePart:
    """Serializable part entry shown in the bolt reference tree."""

    name: str
    source_path: str
    file_format: ReferenceGeometryFormat
    display_state: ReferenceDisplayState = field(default_factory=ReferenceDisplayState)
    file_hash: str = ""
    imported_at: str = ""
    units: str = "mm"
    mesh_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_reference_id("ref"))

    def __post_init__(self) -> None:
        self.file_format = _coerce_reference_format(self.file_format)
        self.display_state = (
            self.display_state
            if isinstance(self.display_state, ReferenceDisplayState)
            else ReferenceDisplayState.from_dict(self.display_state)
        )
        self.metadata = dict(self.metadata)
        self.mesh_count = int(self.mesh_count)

    def rename(self, name: str) -> None:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("Reference part name cannot be empty.")
        self.name = cleaned

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "source_path": self.source_path,
            "file_format": self.file_format.value,
            "display_state": self.display_state.to_dict(),
            "file_hash": self.file_hash,
            "imported_at": self.imported_at,
            "units": self.units,
            "mesh_count": self.mesh_count,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReferencePart":
        return cls(
            id=str(data.get("id") or new_reference_id("ref")),
            name=str(data.get("name") or "Reference Part"),
            source_path=str(data.get("source_path") or ""),
            file_format=_coerce_reference_format(data.get("file_format")),
            display_state=ReferenceDisplayState.from_dict(data.get("display_state")),
            file_hash=str(data.get("file_hash") or ""),
            imported_at=str(data.get("imported_at") or ""),
            units=str(data.get("units") or "mm"),
            mesh_count=int(data.get("mesh_count", 0)),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class ReferenceMeshAsset:
    """Runtime mesh data for one displayed reference body or mesh block."""

    part_id: str
    name: str
    mesh: Any
    source_shape_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_reference_id("mesh"))

    @property
    def n_points(self) -> int:
        return int(getattr(self.mesh, "n_points", 0))

    @property
    def n_cells(self) -> int:
        return int(getattr(self.mesh, "n_cells", 0))

    def summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "part_id": self.part_id,
            "name": self.name,
            "source_shape_id": self.source_shape_id,
            "n_points": self.n_points,
            "n_cells": self.n_cells,
            "metadata": dict(self.metadata),
        }


@dataclass
class ReferencePartImportResult:
    """Imported reference part plus runtime display meshes."""

    part: ReferencePart
    mesh_assets: list[ReferenceMeshAsset]
    document: Any | None = None


class ReferenceGeometryService:
    """Load visual reference geometry without changing bolt calculations."""

    def import_part(self, path: str | Path) -> ReferencePartImportResult:
        input_path = Path(path)
        file_format = reference_format_from_path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Reference geometry file does not exist: {input_path}")
        if file_format == ReferenceGeometryFormat.STL:
            return self._import_stl(input_path)
        return self._import_neutral_cad(input_path, file_format)

    def _import_stl(self, path: Path) -> ReferencePartImportResult:
        pv = _import_pyvista()
        mesh = _coerce_pyvista_mesh(pv.read(str(path)))
        part = _make_reference_part(
            path=path,
            file_format=ReferenceGeometryFormat.STL,
            mesh_count=1,
            metadata={"loader": "pyvista", "mesh_only": True},
        )
        asset = ReferenceMeshAsset(
            part_id=part.id,
            name=part.name,
            mesh=mesh,
            metadata=_mesh_metadata(mesh),
        )
        return ReferencePartImportResult(part=part, mesh_assets=[asset])

    def _import_neutral_cad(
        self,
        path: Path,
        file_format: ReferenceGeometryFormat,
    ) -> ReferencePartImportResult:
        from .cad_geometry_occ import OccCadGeometrySession

        session = OccCadGeometrySession()
        document = session.import_file(path)
        body_refs = session.shape_references({ShapeKind.BODY})
        if not body_refs:
            body_refs = session.shape_references()

        mesh_assets: list[ReferenceMeshAsset] = []
        part = _make_reference_part(
            path=path,
            file_format=file_format,
            mesh_count=0,
            metadata={
                "loader": "occ",
                "cad_document_id": document.id,
                "mesh_only": False,
            },
            units=document.units,
        )

        for index, shape_ref in enumerate(body_refs, start=1):
            occ_shape = session.kernel_shape(shape_ref)
            if occ_shape is None:
                continue
            mesh = _mesh_from_occ_shape(occ_shape)
            mesh_assets.append(
                ReferenceMeshAsset(
                    part_id=part.id,
                    name=shape_ref.fallback_display_name or f"{part.name} Body {index}",
                    mesh=mesh,
                    source_shape_id=shape_ref.id,
                    metadata={
                        **_mesh_metadata(mesh),
                        "shape_type": shape_ref.shape_type.value,
                    },
                )
            )

        if not mesh_assets:
            raise ReferenceGeometryImportError(
                f"No meshable body geometry was found in {path.name}."
            )
        part.mesh_count = len(mesh_assets)
        return ReferencePartImportResult(
            part=part,
            mesh_assets=mesh_assets,
            document=document,
        )


def reference_format_from_path(path: str | Path) -> ReferenceGeometryFormat:
    suffix = Path(path).suffix.lower()
    try:
        return SUPPORTED_REFERENCE_GEOMETRY_SUFFIXES[suffix]
    except KeyError as exc:
        supported = ", ".join(sorted(SUPPORTED_REFERENCE_GEOMETRY_SUFFIXES))
        raise UnsupportedReferenceGeometryFormatError(
            f"Unsupported reference geometry format {suffix or '<none>'!r}. "
            f"Supported formats: {supported}."
        ) from exc


def is_supported_reference_geometry(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_REFERENCE_GEOMETRY_SUFFIXES


def _make_reference_part(
    path: Path,
    file_format: ReferenceGeometryFormat,
    mesh_count: int,
    metadata: dict[str, Any],
    units: str = "mm",
) -> ReferencePart:
    return ReferencePart(
        name=path.stem,
        source_path=str(path),
        file_format=file_format,
        file_hash=f"sha256:{_sha256_file(path)}",
        imported_at=_utc_timestamp(),
        units=units,
        mesh_count=mesh_count,
        metadata=metadata,
    )


def _coerce_reference_format(value: Any) -> ReferenceGeometryFormat:
    if isinstance(value, ReferenceGeometryFormat):
        return value
    if isinstance(value, CadFileFormat):
        if value == CadFileFormat.STEP:
            return ReferenceGeometryFormat.STEP
        if value == CadFileFormat.IGES:
            return ReferenceGeometryFormat.IGES
    return ReferenceGeometryFormat(str(value))


def _import_pyvista() -> Any:
    try:
        import pyvista as pv
    except ImportError as exc:
        raise ReferenceGeometryImportError(
            "PyVista is required to load visual reference geometry."
        ) from exc
    return pv


def _coerce_pyvista_mesh(mesh: Any) -> Any:
    if hasattr(mesh, "combine"):
        mesh = mesh.combine()
    if hasattr(mesh, "extract_surface"):
        try:
            mesh = mesh.extract_surface(algorithm="dataset_surface")
        except TypeError:
            mesh = mesh.extract_surface()
    n_points = int(getattr(mesh, "n_points", 0))
    n_cells = int(getattr(mesh, "n_cells", 0))
    if n_points <= 0 or n_cells <= 0:
        raise ReferenceGeometryImportError("Reference geometry mesh is empty.")
    return mesh


def _mesh_metadata(mesh: Any) -> dict[str, Any]:
    bounds = getattr(mesh, "bounds", None)
    return {
        "n_points": int(getattr(mesh, "n_points", 0)),
        "n_cells": int(getattr(mesh, "n_cells", 0)),
        "bounds": [float(value) for value in bounds] if bounds else [],
    }


def _mesh_from_occ_shape(shape: Any) -> Any:
    pv = _import_pyvista()
    try:
        from OCC.Core.BRep import BRep_Tool
        from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
        from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_REVERSED
        from OCC.Core.TopExp import TopExp_Explorer
        from OCC.Core.TopLoc import TopLoc_Location
        from OCC.Core.TopoDS import topods
    except ImportError as exc:
        raise ReferenceGeometryImportError(
            "OCCT meshing modules are unavailable for STEP/IGES reference geometry."
        ) from exc

    BRepMesh_IncrementalMesh(shape, 0.1, False, 0.5, True)
    points: list[tuple[float, float, float]] = []
    faces: list[int] = []
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        face = topods.Face(explorer.Current())
        location = TopLoc_Location()
        triangulation = _brep_tool_triangulation(BRep_Tool, face, location)
        if triangulation is not None:
            face_offset = len(points)
            transform = location.Transformation()
            for node_index in range(1, int(triangulation.NbNodes()) + 1):
                point = triangulation.Node(node_index).Transformed(transform)
                points.append((float(point.X()), float(point.Y()), float(point.Z())))
            for triangle_index in range(1, int(triangulation.NbTriangles()) + 1):
                n1, n2, n3 = triangulation.Triangle(triangle_index).Get()
                if face.Orientation() == TopAbs_REVERSED:
                    n2, n3 = n3, n2
                faces.extend(
                    [
                        3,
                        face_offset + int(n1) - 1,
                        face_offset + int(n2) - 1,
                        face_offset + int(n3) - 1,
                    ]
                )
        explorer.Next()

    if not points or not faces:
        raise ReferenceGeometryImportError("OCCT produced an empty display mesh.")
    return _coerce_pyvista_mesh(pv.PolyData(points, faces))


def _brep_tool_triangulation(tool: Any, face: Any, location: Any) -> Any | None:
    try:
        return tool.Triangulation(face, location)
    except TypeError:
        return tool().Triangulation(face, location)


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
