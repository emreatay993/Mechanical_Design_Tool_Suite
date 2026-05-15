"""Pure domain models for CAD-based 1D tolerance analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar
from uuid import uuid4


SCHEMA_VERSION = 3
PROJECT_TYPE = "cad_1d_tolerance"
DEFAULT_UNIT_SYSTEM = "mm"
DEFAULT_SIGMA_COVERAGE = 3.0
DEFAULT_TARGET_CPK = 1.33


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class CadFileFormat(_StringEnum):
    STEP = "step"
    IGES = "iges"
    UNKNOWN = "unknown"


class CadSourceStatus(_StringEnum):
    PRESENT = "present"
    MISSING = "missing"
    RELOCATED = "relocated"
    CHANGED_HASH = "changed_hash"
    CHANGED_TOPOLOGY = "changed_topology"
    PROJECT_LOCAL_PACKAGE_ASSET = "project_local_package_asset"
    UNKNOWN = "unknown"


class AssemblyNodeType(_StringEnum):
    ROOT = "root"
    ASSEMBLY = "assembly"
    PART = "part"
    BODY = "body"
    FEATURE = "feature"


class ShapeKind(_StringEnum):
    BODY = "body"
    FACE = "face"
    EDGE = "edge"
    VERTEX = "vertex"
    AXIS = "axis"
    PLANE = "plane"
    UNKNOWN = "unknown"


class FeatureKind(_StringEnum):
    FACE = "face"
    EDGE = "edge"
    VERTEX = "vertex"
    AXIS = "axis"
    PLANE = "plane"
    CYLINDER = "cylinder"
    DATUM = "datum"
    MANUAL = "manual"
    UNKNOWN = "unknown"


class ToleranceType(_StringEnum):
    SYMMETRIC = "symmetric"
    LIMITS = "limits"
    GEOMETRIC = "geometric"


class GeometricControlType(_StringEnum):
    RUNOUT = "runout"
    POSITION = "position"
    PROFILE = "profile"
    MANUAL = "manual"


def geometric_control_display_label(control_type: GeometricControlType | str) -> str:
    control = _coerce_enum(
        GeometricControlType,
        control_type,
        GeometricControlType.MANUAL,
    )
    return {
        GeometricControlType.RUNOUT: "runout",
        GeometricControlType.POSITION: "position",
        GeometricControlType.PROFILE: "profile",
        GeometricControlType.MANUAL: "manual",
    }[control]


def geometric_derived_effect(
    control_type: GeometricControlType | str,
    tolerance_value: float,
) -> tuple[float, float]:
    _coerce_enum(GeometricControlType, control_type, GeometricControlType.MANUAL)
    effect = abs(float(tolerance_value)) * 0.5
    return effect, effect


def geometric_conversion_note(control_type: GeometricControlType | str) -> str:
    label = geometric_control_display_label(control_type)
    return f"{label} tolerance projected as a symmetric 1D contributor."


class AnalysisMode(_StringEnum):
    WORST_CASE = "worst_case"
    RSS = "rss"
    STATISTICAL = "statistical"


class ObjectiveType(_StringEnum):
    BILATERAL = "bilateral"
    UPPER_LIMIT = "upper_limit"
    LOWER_LIMIT = "lower_limit"
    RANGE = "range"


class QualityMetric(_StringEnum):
    CPK = "cpk"
    SIGMA = "sigma"
    YIELD = "yield"
    WORST_CASE = "worst_case"
    RSS = "rss"


class ResultStatus(_StringEnum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    INCOMPLETE = "incomplete"


class NonOneDWarningKind(_StringEnum):
    OFFSET_FEATURES = "offset_features"
    ROTATIONAL_CONSTRAINT = "rotational_constraint"
    DIRECTION_MISALIGNMENT = "direction_misalignment"
    MULTI_INTERFACE_LOOP = "multi_interface_loop"
    SENSITIVE_PROJECTION = "sensitive_projection"
    MANUAL_REVIEW = "manual_review"


EnumT = TypeVar("EnumT", bound=Enum)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


def _coerce_enum(enum_type: type[EnumT], value: Any, default: EnumT) -> EnumT:
    if isinstance(value, enum_type):
        return value
    if value is None:
        return default
    try:
        return enum_type(str(value))
    except ValueError:
        return default


def _enum_value(value: Enum | str) -> str:
    return value.value if isinstance(value, Enum) else str(value)


def _float_or_none(value: Any) -> float | None:
    return None if value is None else float(value)


def _vector_or_none(value: Any) -> "Vector3D | None":
    if value is None:
        return None
    if isinstance(value, Vector3D):
        return value
    return Vector3D.from_iterable(value)


def _string_list(values: Any) -> list[str]:
    if values is None:
        return []
    return [str(value) for value in values]


def _identity_transform() -> list[float]:
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


def _normalize_tolerance_pair(
    tolerance: float,
    tolerance_minus: float | None,
    tolerance_plus: float | None,
) -> tuple[float, float, float]:
    base = float(tolerance)
    minus = base if tolerance_minus is None else float(tolerance_minus)
    plus = base if tolerance_plus is None else float(tolerance_plus)
    return max(base, minus, plus), minus, plus


@dataclass
class Vector3D:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __post_init__(self) -> None:
        self.x = float(self.x)
        self.y = float(self.y)
        self.z = float(self.z)

    @classmethod
    def from_iterable(cls, values: Any) -> "Vector3D":
        x, y, z = values
        return cls(float(x), float(y), float(z))

    def to_list(self) -> list[float]:
        return [self.x, self.y, self.z]


@dataclass
class AnalysisSettings:
    sigma_coverage: float = DEFAULT_SIGMA_COVERAGE
    default_target_cpk: float = DEFAULT_TARGET_CPK
    lateral_offset_warning_threshold: float = 1.0
    min_direction_alignment: float = 0.95
    multi_interface_warning_count: int = 3
    projection_sensitivity_warning_threshold: float = 0.10

    def __post_init__(self) -> None:
        self.sigma_coverage = float(self.sigma_coverage)
        self.default_target_cpk = float(self.default_target_cpk)
        self.lateral_offset_warning_threshold = float(
            self.lateral_offset_warning_threshold
        )
        self.min_direction_alignment = float(self.min_direction_alignment)
        self.multi_interface_warning_count = int(self.multi_interface_warning_count)
        self.projection_sensitivity_warning_threshold = float(
            self.projection_sensitivity_warning_threshold
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "sigma_coverage": self.sigma_coverage,
            "default_target_cpk": self.default_target_cpk,
            "lateral_offset_warning_threshold": self.lateral_offset_warning_threshold,
            "min_direction_alignment": self.min_direction_alignment,
            "multi_interface_warning_count": self.multi_interface_warning_count,
            "projection_sensitivity_warning_threshold": (
                self.projection_sensitivity_warning_threshold
            ),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "AnalysisSettings":
        if not data:
            return cls()
        return cls(
            sigma_coverage=float(data.get("sigma_coverage", DEFAULT_SIGMA_COVERAGE)),
            default_target_cpk=float(data.get("default_target_cpk", DEFAULT_TARGET_CPK)),
            lateral_offset_warning_threshold=float(
                data.get("lateral_offset_warning_threshold", 1.0)
            ),
            min_direction_alignment=float(data.get("min_direction_alignment", 0.95)),
            multi_interface_warning_count=int(
                data.get("multi_interface_warning_count", 3)
            ),
            projection_sensitivity_warning_threshold=float(
                data.get("projection_sensitivity_warning_threshold", 0.10)
            ),
        )


@dataclass
class AssemblyNode:
    name: str
    node_type: AssemblyNodeType = AssemblyNodeType.PART
    parent_id: str = ""
    children: list["AssemblyNode"] = field(default_factory=list)
    transform: list[float] = field(default_factory=_identity_transform)
    display_color: tuple[int, int, int] | None = None
    source_label: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("asm"))

    def __post_init__(self) -> None:
        self.node_type = _coerce_enum(
            AssemblyNodeType, self.node_type, AssemblyNodeType.PART
        )
        self.transform = [float(value) for value in self.transform]
        if self.display_color is not None:
            self.display_color = tuple(int(value) for value in self.display_color[:3])
        self.metadata = dict(self.metadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "node_type": self.node_type.value,
            "parent_id": self.parent_id,
            "children": [child.to_dict() for child in self.children],
            "transform": list(self.transform),
            "display_color": list(self.display_color) if self.display_color else None,
            "source_label": self.source_label,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AssemblyNode":
        return cls(
            id=str(data.get("id") or new_id("asm")),
            name=str(data.get("name") or "Assembly Node"),
            node_type=_coerce_enum(
                AssemblyNodeType, data.get("node_type"), AssemblyNodeType.PART
            ),
            parent_id=str(data.get("parent_id") or ""),
            children=[
                AssemblyNode.from_dict(item) for item in data.get("children", [])
            ],
            transform=list(data.get("transform") or _identity_transform()),
            display_color=(
                tuple(data["display_color"]) if data.get("display_color") else None
            ),
            source_label=str(data.get("source_label") or ""),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class ShapeReference:
    document_id: str = ""
    assembly_path: list[str] = field(default_factory=list)
    shape_type: ShapeKind = ShapeKind.UNKNOWN
    kernel_label: str = ""
    geometric_signature: dict[str, Any] = field(default_factory=dict)
    fallback_display_name: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("shape"))

    def __post_init__(self) -> None:
        self.shape_type = _coerce_enum(ShapeKind, self.shape_type, ShapeKind.UNKNOWN)
        self.assembly_path = _string_list(self.assembly_path)
        self.geometric_signature = dict(self.geometric_signature)
        self.metadata = dict(self.metadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "assembly_path": list(self.assembly_path),
            "shape_type": self.shape_type.value,
            "kernel_label": self.kernel_label,
            "geometric_signature": dict(self.geometric_signature),
            "fallback_display_name": self.fallback_display_name,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ShapeReference | None":
        if not data:
            return None
        return cls(
            id=str(data.get("id") or new_id("shape")),
            document_id=str(data.get("document_id") or ""),
            assembly_path=_string_list(data.get("assembly_path")),
            shape_type=_coerce_enum(ShapeKind, data.get("shape_type"), ShapeKind.UNKNOWN),
            kernel_label=str(data.get("kernel_label") or ""),
            geometric_signature=dict(data.get("geometric_signature") or {}),
            fallback_display_name=str(data.get("fallback_display_name") or ""),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class FeatureReference:
    name: str = ""
    feature_type: FeatureKind = FeatureKind.UNKNOWN
    shape_reference: ShapeReference | None = None
    owner_part_id: str = ""
    datum_label: str = ""
    point: Vector3D | None = None
    axis: Vector3D | None = None
    normal: Vector3D | None = None
    id: str = field(default_factory=lambda: new_id("feature"))

    def __post_init__(self) -> None:
        self.feature_type = _coerce_enum(
            FeatureKind, self.feature_type, FeatureKind.UNKNOWN
        )
        self.point = _vector_or_none(self.point)
        self.axis = _vector_or_none(self.axis)
        self.normal = _vector_or_none(self.normal)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "feature_type": self.feature_type.value,
            "shape_reference": (
                self.shape_reference.to_dict() if self.shape_reference else None
            ),
            "owner_part_id": self.owner_part_id,
            "datum_label": self.datum_label,
            "point": self.point.to_list() if self.point else None,
            "axis": self.axis.to_list() if self.axis else None,
            "normal": self.normal.to_list() if self.normal else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "FeatureReference | None":
        if not data:
            return None
        return cls(
            id=str(data.get("id") or new_id("feature")),
            name=str(data.get("name") or ""),
            feature_type=_coerce_enum(
                FeatureKind, data.get("feature_type"), FeatureKind.UNKNOWN
            ),
            shape_reference=ShapeReference.from_dict(data.get("shape_reference")),
            owner_part_id=str(data.get("owner_part_id") or ""),
            datum_label=str(data.get("datum_label") or ""),
            point=_vector_or_none(data.get("point")),
            axis=_vector_or_none(data.get("axis")),
            normal=_vector_or_none(data.get("normal")),
        )


@dataclass
class AnnotationPlane:
    origin: Vector3D = field(default_factory=Vector3D)
    normal: Vector3D = field(default_factory=lambda: Vector3D(0.0, 0.0, 1.0))
    source_feature_id: str = ""
    display_name: str = ""

    def __post_init__(self) -> None:
        self.origin = _vector_or_none(self.origin) or Vector3D()
        self.normal = _vector_or_none(self.normal) or Vector3D(0.0, 0.0, 1.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "origin": self.origin.to_list(),
            "normal": self.normal.to_list(),
            "source_feature_id": self.source_feature_id,
            "display_name": self.display_name,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "AnnotationPlane":
        if not data:
            return cls()
        return cls(
            origin=Vector3D.from_iterable(data.get("origin", [0.0, 0.0, 0.0])),
            normal=Vector3D.from_iterable(data.get("normal", [0.0, 0.0, 1.0])),
            source_feature_id=str(data.get("source_feature_id") or ""),
            display_name=str(data.get("display_name") or ""),
        )


@dataclass
class GeometricTolerance:
    control_type: GeometricControlType = GeometricControlType.MANUAL
    tolerance_value: float = 0.0
    datum_references: list[str] = field(default_factory=list)
    material_modifier: str = ""
    derived_minus: float | None = None
    derived_plus: float | None = None
    conversion_note: str = ""
    id: str = field(default_factory=lambda: new_id("gdt"))

    def __post_init__(self) -> None:
        self.control_type = _coerce_enum(
            GeometricControlType, self.control_type, GeometricControlType.MANUAL
        )
        self.tolerance_value = float(self.tolerance_value)
        self.datum_references = _string_list(self.datum_references)
        default_minus, default_plus = geometric_derived_effect(
            self.control_type,
            self.tolerance_value,
        )
        self.derived_minus = (
            default_minus if self.derived_minus is None else float(self.derived_minus)
        )
        self.derived_plus = (
            default_plus if self.derived_plus is None else float(self.derived_plus)
        )
        if not self.conversion_note:
            self.conversion_note = geometric_conversion_note(self.control_type)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "control_type": self.control_type.value,
            "tolerance_value": self.tolerance_value,
            "datum_references": list(self.datum_references),
            "material_modifier": self.material_modifier,
            "derived_minus": self.derived_minus,
            "derived_plus": self.derived_plus,
            "conversion_note": self.conversion_note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "GeometricTolerance | None":
        if not data:
            return None
        return cls(
            id=str(data.get("id") or new_id("gdt")),
            control_type=_coerce_enum(
                GeometricControlType,
                data.get("control_type"),
                GeometricControlType.MANUAL,
            ),
            tolerance_value=float(data.get("tolerance_value", 0.0)),
            datum_references=_string_list(data.get("datum_references")),
            material_modifier=str(data.get("material_modifier") or ""),
            derived_minus=_float_or_none(data.get("derived_minus")),
            derived_plus=_float_or_none(data.get("derived_plus")),
            conversion_note=str(data.get("conversion_note") or ""),
        )


@dataclass
class StackupContributor:
    name: str
    nominal: float
    tolerance: float
    sensitivity: float = 1.0
    tolerance_minus: float | None = None
    tolerance_plus: float | None = None
    tolerance_type: ToleranceType = ToleranceType.SYMMETRIC
    datum_references: list[str] = field(default_factory=list)
    source_feature: FeatureReference | None = None
    geometric_tolerance: GeometricTolerance | None = None
    shared_with_stackup_ids: list[str] = field(default_factory=list)
    include_in_stackup: bool = True
    source_note: str = ""
    id: str = field(default_factory=lambda: new_id("contrib"))

    def __post_init__(self) -> None:
        self.sensitivity = float(self.sensitivity)
        self.nominal = float(self.nominal)
        self.tolerance_type = _coerce_enum(
            ToleranceType, self.tolerance_type, ToleranceType.SYMMETRIC
        )
        if (
            self.geometric_tolerance
            and self.tolerance == 0.0
            and self.tolerance_minus is None
            and self.tolerance_plus is None
        ):
            self.tolerance_minus = self.geometric_tolerance.derived_minus
            self.tolerance_plus = self.geometric_tolerance.derived_plus
        self.tolerance, self.tolerance_minus, self.tolerance_plus = (
            _normalize_tolerance_pair(
                self.tolerance, self.tolerance_minus, self.tolerance_plus
            )
        )
        self.datum_references = _string_list(self.datum_references)
        self.shared_with_stackup_ids = _string_list(self.shared_with_stackup_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "nominal": self.nominal,
            "sensitivity": self.sensitivity,
            "tolerance": self.tolerance,
            "tolerance_minus": self.tolerance_minus,
            "tolerance_plus": self.tolerance_plus,
            "tolerance_type": self.tolerance_type.value,
            "datum_references": list(self.datum_references),
            "source_feature": (
                self.source_feature.to_dict() if self.source_feature else None
            ),
            "geometric_tolerance": (
                self.geometric_tolerance.to_dict() if self.geometric_tolerance else None
            ),
            "shared_with_stackup_ids": list(self.shared_with_stackup_ids),
            "include_in_stackup": self.include_in_stackup,
            "source_note": self.source_note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StackupContributor":
        return cls(
            id=str(data.get("id") or new_id("contrib")),
            name=str(data.get("name") or "Contributor"),
            nominal=float(data.get("nominal", 0.0)),
            sensitivity=float(data.get("sensitivity", 1.0)),
            tolerance=float(data.get("tolerance", 0.0)),
            tolerance_minus=_float_or_none(data.get("tolerance_minus")),
            tolerance_plus=_float_or_none(data.get("tolerance_plus")),
            tolerance_type=_coerce_enum(
                ToleranceType, data.get("tolerance_type"), ToleranceType.SYMMETRIC
            ),
            datum_references=_string_list(data.get("datum_references")),
            source_feature=FeatureReference.from_dict(data.get("source_feature")),
            geometric_tolerance=GeometricTolerance.from_dict(
                data.get("geometric_tolerance")
            ),
            shared_with_stackup_ids=_string_list(data.get("shared_with_stackup_ids")),
            include_in_stackup=bool(data.get("include_in_stackup", True)),
            source_note=str(data.get("source_note") or ""),
        )


@dataclass
class StackupObjective:
    objective_type: ObjectiveType = ObjectiveType.BILATERAL
    nominal: float = 0.0
    tolerance_minus: float = 0.0
    tolerance_plus: float = 0.0
    lower_limit: float | None = None
    upper_limit: float | None = None
    description: str = ""

    def __post_init__(self) -> None:
        self.objective_type = _coerce_enum(
            ObjectiveType, self.objective_type, ObjectiveType.BILATERAL
        )
        self.nominal = float(self.nominal)
        self.tolerance_minus = float(self.tolerance_minus)
        self.tolerance_plus = float(self.tolerance_plus)
        self.lower_limit = _float_or_none(self.lower_limit)
        self.upper_limit = _float_or_none(self.upper_limit)

    @classmethod
    def bilateral(
        cls,
        nominal: float = 0.0,
        tolerance: float = 0.0,
        tolerance_minus: float | None = None,
        tolerance_plus: float | None = None,
        description: str = "",
    ) -> "StackupObjective":
        _, minus, plus = _normalize_tolerance_pair(
            tolerance, tolerance_minus, tolerance_plus
        )
        return cls(
            objective_type=ObjectiveType.BILATERAL,
            nominal=nominal,
            tolerance_minus=minus,
            tolerance_plus=plus,
            description=description,
        )

    @classmethod
    def for_upper_limit(cls, value: float, description: str = "") -> "StackupObjective":
        return cls(
            objective_type=ObjectiveType.UPPER_LIMIT,
            upper_limit=float(value),
            description=description,
        )

    @classmethod
    def for_lower_limit(cls, value: float, description: str = "") -> "StackupObjective":
        return cls(
            objective_type=ObjectiveType.LOWER_LIMIT,
            lower_limit=float(value),
            description=description,
        )

    def lower_bound(self) -> float | None:
        if self.objective_type == ObjectiveType.BILATERAL:
            return self.nominal - self.tolerance_minus
        if self.objective_type == ObjectiveType.LOWER_LIMIT:
            return self.lower_limit
        if self.objective_type == ObjectiveType.RANGE:
            return self.lower_limit
        return None

    def upper_bound(self) -> float | None:
        if self.objective_type == ObjectiveType.BILATERAL:
            return self.nominal + self.tolerance_plus
        if self.objective_type == ObjectiveType.UPPER_LIMIT:
            return self.upper_limit
        if self.objective_type == ObjectiveType.RANGE:
            return self.upper_limit
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective_type": self.objective_type.value,
            "nominal": self.nominal,
            "tolerance_minus": self.tolerance_minus,
            "tolerance_plus": self.tolerance_plus,
            "lower_limit": self.lower_limit,
            "upper_limit": self.upper_limit,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "StackupObjective":
        if not data:
            return cls()
        return cls(
            objective_type=_coerce_enum(
                ObjectiveType, data.get("objective_type"), ObjectiveType.BILATERAL
            ),
            nominal=float(data.get("nominal", 0.0)),
            tolerance_minus=float(data.get("tolerance_minus", 0.0)),
            tolerance_plus=float(data.get("tolerance_plus", 0.0)),
            lower_limit=_float_or_none(data.get("lower_limit")),
            upper_limit=_float_or_none(data.get("upper_limit")),
            description=str(data.get("description") or ""),
        )


@dataclass
class QualityTarget:
    metric: QualityMetric = QualityMetric.CPK
    value: float | None = DEFAULT_TARGET_CPK
    sigma_coverage: float = DEFAULT_SIGMA_COVERAGE

    def __post_init__(self) -> None:
        self.metric = _coerce_enum(QualityMetric, self.metric, QualityMetric.CPK)
        self.value = _float_or_none(self.value)
        self.sigma_coverage = float(self.sigma_coverage)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric.value,
            "value": self.value,
            "sigma_coverage": self.sigma_coverage,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "QualityTarget":
        if not data:
            return cls()
        return cls(
            metric=_coerce_enum(QualityMetric, data.get("metric"), QualityMetric.CPK),
            value=_float_or_none(data.get("value")),
            sigma_coverage=float(data.get("sigma_coverage", DEFAULT_SIGMA_COVERAGE)),
        )


@dataclass
class NonOneDWarning:
    warning_kind: NonOneDWarningKind
    message: str
    severity: ResultStatus = ResultStatus.WARN
    feature_ids: list[str] = field(default_factory=list)
    observed_value: float | None = None
    threshold: float | None = None
    id: str = field(default_factory=lambda: new_id("warn"))

    def __post_init__(self) -> None:
        self.warning_kind = _coerce_enum(
            NonOneDWarningKind, self.warning_kind, NonOneDWarningKind.MANUAL_REVIEW
        )
        self.severity = _coerce_enum(ResultStatus, self.severity, ResultStatus.WARN)
        self.feature_ids = _string_list(self.feature_ids)
        self.observed_value = _float_or_none(self.observed_value)
        self.threshold = _float_or_none(self.threshold)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "warning_kind": self.warning_kind.value,
            "message": self.message,
            "severity": self.severity.value,
            "feature_ids": list(self.feature_ids),
            "observed_value": self.observed_value,
            "threshold": self.threshold,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NonOneDWarning":
        return cls(
            id=str(data.get("id") or new_id("warn")),
            warning_kind=_coerce_enum(
                NonOneDWarningKind,
                data.get("warning_kind"),
                NonOneDWarningKind.MANUAL_REVIEW,
            ),
            message=str(data.get("message") or ""),
            severity=_coerce_enum(ResultStatus, data.get("severity"), ResultStatus.WARN),
            feature_ids=_string_list(data.get("feature_ids")),
            observed_value=_float_or_none(data.get("observed_value")),
            threshold=_float_or_none(data.get("threshold")),
        )


@dataclass
class StackupRequirement:
    name: str
    contributors: list[StackupContributor] = field(default_factory=list)
    objective: StackupObjective = field(default_factory=StackupObjective)
    target_quality: QualityTarget = field(default_factory=QualityTarget)
    analysis_mode: AnalysisMode = AnalysisMode.WORST_CASE
    start_feature: FeatureReference | None = None
    end_feature: FeatureReference | None = None
    direction: Vector3D = field(default_factory=lambda: Vector3D(1.0, 0.0, 0.0))
    annotation_plane: AnnotationPlane = field(default_factory=AnnotationPlane)
    loop_features: list[FeatureReference] = field(default_factory=list)
    constraint_features: list[FeatureReference] = field(default_factory=list)
    annotation_position: dict[str, Any] = field(default_factory=dict)
    warnings: list[NonOneDWarning] = field(default_factory=list)
    id: str = field(default_factory=lambda: new_id("stackup"))

    def __post_init__(self) -> None:
        self.analysis_mode = _coerce_enum(
            AnalysisMode, self.analysis_mode, AnalysisMode.WORST_CASE
        )
        self.direction = _vector_or_none(self.direction) or Vector3D(1.0, 0.0, 0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "contributors": [item.to_dict() for item in self.contributors],
            "objective": self.objective.to_dict(),
            "target_quality": self.target_quality.to_dict(),
            "analysis_mode": self.analysis_mode.value,
            "start_feature": self.start_feature.to_dict() if self.start_feature else None,
            "end_feature": self.end_feature.to_dict() if self.end_feature else None,
            "direction": self.direction.to_list(),
            "annotation_plane": self.annotation_plane.to_dict(),
            "loop_features": [feature.to_dict() for feature in self.loop_features],
            "constraint_features": [
                feature.to_dict() for feature in self.constraint_features
            ],
            "annotation_position": dict(self.annotation_position),
            "warnings": [warning.to_dict() for warning in self.warnings],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StackupRequirement":
        return cls(
            id=str(data.get("id") or new_id("stackup")),
            name=str(data.get("name") or "Stackup"),
            contributors=[
                StackupContributor.from_dict(item)
                for item in data.get("contributors", [])
            ],
            objective=StackupObjective.from_dict(data.get("objective")),
            target_quality=QualityTarget.from_dict(data.get("target_quality")),
            analysis_mode=_coerce_enum(
                AnalysisMode, data.get("analysis_mode"), AnalysisMode.WORST_CASE
            ),
            start_feature=FeatureReference.from_dict(data.get("start_feature")),
            end_feature=FeatureReference.from_dict(data.get("end_feature")),
            direction=Vector3D.from_iterable(data.get("direction", [1.0, 0.0, 0.0])),
            annotation_plane=AnnotationPlane.from_dict(data.get("annotation_plane")),
            loop_features=[
                feature
                for feature in (
                    FeatureReference.from_dict(item)
                    for item in data.get("loop_features", [])
                )
                if feature is not None
            ],
            constraint_features=[
                feature
                for feature in (
                    FeatureReference.from_dict(item)
                    for item in data.get("constraint_features", [])
                )
                if feature is not None
            ],
            annotation_position=dict(data.get("annotation_position") or {}),
            warnings=[
                NonOneDWarning.from_dict(item) for item in data.get("warnings", [])
            ],
        )


@dataclass
class CadDocument:
    source_path: str
    file_hash: str = ""
    source_topology_hash: str = ""
    source_status: CadSourceStatus = CadSourceStatus.UNKNOWN
    source_status_message: str = ""
    source_last_checked_at: str = ""
    file_format: CadFileFormat = CadFileFormat.UNKNOWN
    imported_at: str = ""
    units: str = DEFAULT_UNIT_SYSTEM
    assembly_root: AssemblyNode | None = None
    display_name: str = ""
    import_settings: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("cad"))

    def __post_init__(self) -> None:
        self.file_format = _coerce_enum(
            CadFileFormat, self.file_format, CadFileFormat.UNKNOWN
        )
        self.source_status = _coerce_enum(
            CadSourceStatus, self.source_status, CadSourceStatus.UNKNOWN
        )
        self.import_settings = dict(self.import_settings)
        self.metadata = dict(self.metadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_path": self.source_path,
            "file_hash": self.file_hash,
            "source_topology_hash": self.source_topology_hash,
            "source_status": self.source_status.value,
            "source_status_message": self.source_status_message,
            "source_last_checked_at": self.source_last_checked_at,
            "file_format": self.file_format.value,
            "imported_at": self.imported_at,
            "units": self.units,
            "assembly_root": self.assembly_root.to_dict() if self.assembly_root else None,
            "display_name": self.display_name,
            "import_settings": dict(self.import_settings),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CadDocument":
        return cls(
            id=str(data.get("id") or new_id("cad")),
            source_path=str(data.get("source_path") or ""),
            file_hash=str(data.get("file_hash") or ""),
            source_topology_hash=str(data.get("source_topology_hash") or ""),
            source_status=_coerce_enum(
                CadSourceStatus,
                data.get("source_status"),
                CadSourceStatus.UNKNOWN,
            ),
            source_status_message=str(data.get("source_status_message") or ""),
            source_last_checked_at=str(data.get("source_last_checked_at") or ""),
            file_format=_coerce_enum(
                CadFileFormat, data.get("file_format"), CadFileFormat.UNKNOWN
            ),
            imported_at=str(data.get("imported_at") or ""),
            units=str(data.get("units") or DEFAULT_UNIT_SYSTEM),
            assembly_root=(
                AssemblyNode.from_dict(data["assembly_root"])
                if data.get("assembly_root")
                else None
            ),
            display_name=str(data.get("display_name") or ""),
            import_settings=dict(data.get("import_settings") or {}),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class Snapshot:
    image_path: str = ""
    camera: dict[str, Any] = field(default_factory=dict)
    visible_stackup_ids: list[str] = field(default_factory=list)
    annotation_positions: dict[str, Any] = field(default_factory=dict)
    captured_at: str = ""
    id: str = field(default_factory=lambda: new_id("snapshot"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "image_path": self.image_path,
            "camera": dict(self.camera),
            "visible_stackup_ids": list(self.visible_stackup_ids),
            "annotation_positions": dict(self.annotation_positions),
            "captured_at": self.captured_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Snapshot":
        return cls(
            id=str(data.get("id") or new_id("snapshot")),
            image_path=str(data.get("image_path") or ""),
            camera=dict(data.get("camera") or {}),
            visible_stackup_ids=_string_list(data.get("visible_stackup_ids")),
            annotation_positions=dict(data.get("annotation_positions") or {}),
            captured_at=str(data.get("captured_at") or ""),
        )


@dataclass
class CadToleranceProject:
    title: str = "CAD 1D Tolerance Project"
    unit_system: str = DEFAULT_UNIT_SYSTEM
    cad_documents: list[CadDocument] = field(default_factory=list)
    stackups: list[StackupRequirement] = field(default_factory=list)
    settings: AnalysisSettings = field(default_factory=AnalysisSettings)
    snapshots: list[Snapshot] = field(default_factory=list)
    reports: list[dict[str, Any]] = field(default_factory=list)
    schema_version: int = SCHEMA_VERSION
    project_type: str = PROJECT_TYPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_type": self.project_type,
            "title": self.title,
            "unit_system": self.unit_system,
            "cad_documents": [document.to_dict() for document in self.cad_documents],
            "stackups": [stackup.to_dict() for stackup in self.stackups],
            "settings": self.settings.to_dict(),
            "snapshots": [snapshot.to_dict() for snapshot in self.snapshots],
            "reports": [dict(report) for report in self.reports],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CadToleranceProject":
        return cls(
            schema_version=int(data.get("schema_version", SCHEMA_VERSION)),
            project_type=str(data.get("project_type") or PROJECT_TYPE),
            title=str(data.get("title") or "CAD 1D Tolerance Project"),
            unit_system=str(data.get("unit_system") or DEFAULT_UNIT_SYSTEM),
            cad_documents=[
                CadDocument.from_dict(item) for item in data.get("cad_documents", [])
            ],
            stackups=[
                StackupRequirement.from_dict(item) for item in data.get("stackups", [])
            ],
            settings=AnalysisSettings.from_dict(data.get("settings")),
            snapshots=[Snapshot.from_dict(item) for item in data.get("snapshots", [])],
            reports=[dict(item) for item in data.get("reports", [])],
        )


@dataclass(frozen=True)
class ContributionResult:
    contributor_id: str
    name: str
    sensitivity: float
    nominal: float
    tolerance_minus: float
    tolerance_plus: float
    variance: float
    contribution: float

    @property
    def percent(self) -> float:
        return self.contribution * 100.0


@dataclass(frozen=True)
class QualityResult:
    mean: float
    standard_deviation: float
    cp: float | None
    cpk: float | None
    sigma: float | None
    yield_probability: float | None
    target_metric: QualityMetric
    target_value: float | None
    status: ResultStatus


@dataclass(frozen=True)
class ObjectiveEvaluation:
    status: ResultStatus
    lower_bound: float | None
    upper_bound: float | None
    result_lower: float
    result_upper: float
    lower_margin: float | None
    upper_margin: float | None
    message: str


@dataclass(frozen=True)
class StackupResult:
    stackup_id: str
    name: str
    analysis_mode: AnalysisMode
    nominal: float
    worst_case_minus: float
    worst_case_plus: float
    rss_minus: float
    rss_plus: float
    evaluated_minus: float
    evaluated_plus: float
    objective: ObjectiveEvaluation
    quality: QualityResult
    contributors: tuple[ContributionResult, ...]
    warnings: tuple[NonOneDWarning, ...]
    status: ResultStatus
    validation_messages: tuple[str, ...] = ()
