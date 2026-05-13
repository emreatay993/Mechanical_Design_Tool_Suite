"""Kernel-neutral CAD geometry adapter API."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from math import sqrt
from pathlib import Path
from typing import Any

from .cad_tolerance_models import (
    AssemblyNode,
    CadDocument,
    CadFileFormat,
    FeatureKind,
    FeatureReference,
    ShapeKind,
    ShapeReference,
    Snapshot,
    Vector3D,
)


SUPPORTED_NEUTRAL_CAD_SUFFIXES = {
    ".step": CadFileFormat.STEP,
    ".stp": CadFileFormat.STEP,
    ".iges": CadFileFormat.IGES,
    ".igs": CadFileFormat.IGES,
}


class MeasurementKind(str, Enum):
    POINT_TO_POINT = "point_to_point"
    PLANE_TO_PLANE = "plane_to_plane"
    PLANE_TO_AXIS = "plane_to_axis"
    AXIS_TO_AXIS = "axis_to_axis"
    FEATURE_TO_FEATURE = "feature_to_feature"

    def __str__(self) -> str:
        return self.value


class CadGeometryError(RuntimeError):
    """Base exception for CAD geometry adapter failures."""


class UnsupportedCadFormatError(ValueError):
    """Raised when a file is not a supported neutral CAD format."""


@dataclass(frozen=True)
class CadImportSettings:
    """Import options that can be serialized without kernel-specific types."""

    units: str = "mm"
    heal_shapes: bool = True
    object_filter: str = "solids"
    include_edges: bool = True
    include_vertices: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "units": self.units,
            "heal_shapes": self.heal_shapes,
            "object_filter": self.object_filter,
            "include_edges": self.include_edges,
            "include_vertices": self.include_vertices,
        }


@dataclass(frozen=True)
class Measurement:
    """Directional measurement between two selection-ready features."""

    value: float
    units: str
    direction: Vector3D
    measurement_kind: MeasurementKind = MeasurementKind.FEATURE_TO_FEATURE
    source_feature_ids: tuple[str, str] = ("", "")
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class GeometryIndex:
    """Imported geometry metadata exposed without leaking kernel objects."""

    document: CadDocument
    shapes: list[ShapeReference] = field(default_factory=list)
    features: list[FeatureReference] = field(default_factory=list)

    def shapes_by_kind(self, *kinds: ShapeKind) -> list[ShapeReference]:
        wanted = set(kinds)
        if not wanted:
            return list(self.shapes)
        return [shape for shape in self.shapes if shape.shape_type in wanted]

    def features_by_kind(self, *kinds: FeatureKind) -> list[FeatureReference]:
        wanted = set(kinds)
        if not wanted:
            return list(self.features)
        return [feature for feature in self.features if feature.feature_type in wanted]


class CadGeometrySession(ABC):
    """Replaceable geometry session boundary used by GUI and workflow code."""

    @abstractmethod
    def import_file(
        self,
        path: str | Path,
        settings: CadImportSettings | None = None,
    ) -> CadDocument:
        """Import a neutral CAD file and return serializable document metadata."""

    @abstractmethod
    def assembly_tree(self) -> list[AssemblyNode]:
        """Return the current document roots for the assembly browser."""

    @abstractmethod
    def shape_references(
        self,
        kinds: set[ShapeKind] | None = None,
    ) -> list[ShapeReference]:
        """Return available selectable shape references."""

    @abstractmethod
    def feature_references(
        self,
        kinds: set[FeatureKind] | None = None,
    ) -> list[FeatureReference]:
        """Return available selection-ready feature references."""

    @abstractmethod
    def measure_between(
        self,
        a: FeatureReference,
        b: FeatureReference,
        direction: Vector3D | Sequence[float],
    ) -> Measurement:
        """Measure two features along the requested stackup direction."""

    def selected_feature(self) -> FeatureReference | None:
        return None

    def set_selection_filter(self, _kinds: set[ShapeKind]) -> None:
        return None

    def capture_snapshot(
        self,
        _annotations: list[Any] | None = None,
    ) -> Snapshot:
        raise NotImplementedError("Snapshot capture is provided by the viewport adapter.")


class InMemoryCadGeometrySession(CadGeometrySession):
    """Small test/mock session for UI code before a live CAD viewport exists."""

    def __init__(self, index: GeometryIndex | None = None) -> None:
        self._index = index

    def import_file(
        self,
        path: str | Path,
        settings: CadImportSettings | None = None,
    ) -> CadDocument:
        if self._index is None:
            cad_format = cad_format_from_path(path)
            document = CadDocument(
                source_path=str(Path(path)),
                file_format=cad_format,
                units=(settings or CadImportSettings()).units,
                display_name=Path(path).name,
                import_settings=(settings or CadImportSettings()).to_dict(),
            )
            self._index = GeometryIndex(document=document)
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
        return measure_feature_pair(a, b, direction)


def cad_format_from_path(path: str | Path) -> CadFileFormat:
    suffix = Path(path).suffix.lower()
    try:
        return SUPPORTED_NEUTRAL_CAD_SUFFIXES[suffix]
    except KeyError as exc:
        supported = ", ".join(sorted(SUPPORTED_NEUTRAL_CAD_SUFFIXES))
        raise UnsupportedCadFormatError(
            f"Unsupported CAD format {suffix or '<none>'!r}. "
            f"P0 neutral import supports only: {supported}."
        ) from exc


def is_supported_neutral_cad(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_NEUTRAL_CAD_SUFFIXES


def feature_from_shape_reference(
    shape: ShapeReference,
    name: str = "",
    owner_part_id: str = "",
) -> FeatureReference:
    """Create a best-effort feature reference from a serializable shape signature."""

    signature = shape.geometric_signature
    feature_kind = _feature_kind_from_shape(shape)
    return FeatureReference(
        name=name or shape.fallback_display_name,
        feature_type=feature_kind,
        shape_reference=shape,
        owner_part_id=owner_part_id,
        point=_vector_from_signature(signature, "point", "center", "origin", "location"),
        axis=_vector_from_signature(signature, "axis", "direction"),
        normal=_vector_from_signature(signature, "normal"),
    )


def measure_feature_pair(
    a: FeatureReference,
    b: FeatureReference,
    direction: Vector3D | Sequence[float],
    units: str = "mm",
) -> Measurement:
    """Measure two planar/cylindrical/point features along a 1D direction."""

    normalized_direction = normalize_vector(direction)
    point_a = feature_point(a)
    point_b = feature_point(b)
    if point_a is None or point_b is None:
        raise ValueError(
            "Both feature references need a point, center, origin, or location "
            "to compute a directional 1D measurement."
        )

    delta = subtract_vectors(point_b, point_a)
    projected = dot_vectors(delta, normalized_direction)
    kind = _measurement_kind(a, b)
    details: dict[str, Any] = {
        "delta": delta.to_list(),
        "absolute_value": abs(projected),
    }

    radius_a = feature_radius(a)
    radius_b = feature_radius(b)
    if radius_a is not None:
        details["feature_a_radius"] = radius_a
    if radius_b is not None:
        details["feature_b_radius"] = radius_b
    if radius_a is not None and radius_b is not None:
        details["radius_delta"] = radius_b - radius_a

    return Measurement(
        value=projected,
        units=units,
        direction=normalized_direction,
        measurement_kind=kind,
        source_feature_ids=(a.id, b.id),
        details=details,
    )


def feature_point(feature: FeatureReference) -> Vector3D | None:
    if feature.point is not None:
        return feature.point
    signature = _feature_signature(feature)
    return _vector_from_signature(signature, "point", "center", "origin", "location")


def feature_radius(feature: FeatureReference) -> float | None:
    signature = _feature_signature(feature)
    for key in ("radius", "diameter"):
        if key not in signature:
            continue
        value = float(signature[key])
        return value / 2.0 if key == "diameter" else value
    return None


def normalize_vector(vector: Vector3D | Sequence[float]) -> Vector3D:
    value = vector if isinstance(vector, Vector3D) else Vector3D.from_iterable(vector)
    magnitude = sqrt(value.x * value.x + value.y * value.y + value.z * value.z)
    if magnitude <= 0.0:
        raise ValueError("Measurement direction must have non-zero length.")
    return Vector3D(value.x / magnitude, value.y / magnitude, value.z / magnitude)


def subtract_vectors(a: Vector3D, b: Vector3D) -> Vector3D:
    return Vector3D(a.x - b.x, a.y - b.y, a.z - b.z)


def dot_vectors(a: Vector3D, b: Vector3D) -> float:
    return a.x * b.x + a.y * b.y + a.z * b.z


def shape_reference_label(
    document_id: str,
    owner_path: Iterable[str],
    kind: ShapeKind,
    ordinal: int,
) -> str:
    path = "/".join(str(item) for item in owner_path if item)
    return f"{document_id}:{path}:{kind.value}:{ordinal}"


def _feature_signature(feature: FeatureReference) -> dict[str, Any]:
    if feature.shape_reference is None:
        return {}
    return feature.shape_reference.geometric_signature


def _feature_kind_from_shape(shape: ShapeReference) -> FeatureKind:
    signature = shape.geometric_signature
    surface_type = str(signature.get("surface_type") or "").lower()
    curve_type = str(signature.get("curve_type") or "").lower()
    if "cylinder" in surface_type or "radius" in signature:
        return FeatureKind.CYLINDER
    if "plane" in surface_type:
        return FeatureKind.PLANE
    if shape.shape_type == ShapeKind.FACE:
        return FeatureKind.FACE
    if shape.shape_type == ShapeKind.EDGE:
        return FeatureKind.AXIS if "line" in curve_type else FeatureKind.EDGE
    if shape.shape_type == ShapeKind.VERTEX:
        return FeatureKind.VERTEX
    if shape.shape_type == ShapeKind.AXIS:
        return FeatureKind.AXIS
    if shape.shape_type == ShapeKind.PLANE:
        return FeatureKind.PLANE
    return FeatureKind.UNKNOWN


def _measurement_kind(
    a: FeatureReference,
    b: FeatureReference,
) -> MeasurementKind:
    planar = {FeatureKind.FACE, FeatureKind.PLANE}
    axial = {FeatureKind.AXIS, FeatureKind.CYLINDER}
    if a.feature_type in planar and b.feature_type in planar:
        return MeasurementKind.PLANE_TO_PLANE
    if (
        a.feature_type in planar
        and b.feature_type in axial
        or a.feature_type in axial
        and b.feature_type in planar
    ):
        return MeasurementKind.PLANE_TO_AXIS
    if a.feature_type in axial and b.feature_type in axial:
        return MeasurementKind.AXIS_TO_AXIS
    if a.feature_type == FeatureKind.VERTEX or b.feature_type == FeatureKind.VERTEX:
        return MeasurementKind.POINT_TO_POINT
    return MeasurementKind.FEATURE_TO_FEATURE


def _vector_from_signature(
    signature: dict[str, Any],
    *keys: str,
) -> Vector3D | None:
    for key in keys:
        value = signature.get(key)
        if value is None:
            continue
        try:
            return Vector3D.from_iterable(value)
        except (TypeError, ValueError):
            continue
    return None
