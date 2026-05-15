"""Kernel-neutral CAD viewer API for CAD 1D tolerance workflows."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from .cad_geometry_api import CadRuntimeShapeProvider
from .cad_tolerance_models import FeatureReference, ShapeKind, ShapeReference, Snapshot


class CadViewerError(RuntimeError):
    """Base exception for CAD viewer adapter failures."""


class CadViewerUnavailable(CadViewerError):
    """Raised when the optional viewer runtime cannot initialize."""


class HighlightRole(str, Enum):
    HOVER = "hover"
    ELIGIBLE = "eligible"
    CROSS_HIGHLIGHT = "cross_highlight"
    SELECTED_START = "selected_start"
    SELECTED_END = "selected_end"
    DIRECTION = "direction"
    ANALYSIS_PLANE = "analysis_plane"
    LOOP_MEMBER = "loop_member"
    WARNING = "warning"

    def __str__(self) -> str:
        return self.value


class ViewerSelectionMode(str, Enum):
    BODY = "body"
    FACE = "face"
    EDGE = "edge"
    VERTEX = "vertex"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_shape_kind(cls, shape_kind: ShapeKind) -> "ViewerSelectionMode | None":
        if shape_kind == ShapeKind.BODY:
            return cls.BODY
        if shape_kind == ShapeKind.FACE:
            return cls.FACE
        if shape_kind == ShapeKind.EDGE:
            return cls.EDGE
        if shape_kind == ShapeKind.VERTEX:
            return cls.VERTEX
        return None


class StandardView(str, Enum):
    ISO = "iso"
    FRONT = "front"
    REAR = "rear"
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"

    def __str__(self) -> str:
        return self.value


class ViewerAnnotationRole(str, Enum):
    STACKUP = "stackup"
    CONTRIBUTOR = "contributor"
    WARNING = "warning"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class CadCameraState:
    """Serializable camera state captured from a viewer adapter."""

    eye: tuple[float, float, float] | None = None
    target: tuple[float, float, float] | None = None
    up: tuple[float, float, float] | None = None
    projection: tuple[float, float, float] | None = None
    scale: float | None = None
    twist: float | None = None
    view_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "eye": list(self.eye) if self.eye else None,
            "target": list(self.target) if self.target else None,
            "up": list(self.up) if self.up else None,
            "projection": list(self.projection) if self.projection else None,
            "scale": self.scale,
            "twist": self.twist,
            "view_name": self.view_name,
        }


@dataclass(frozen=True)
class ViewerAnnotation:
    """Snapshot-ready annotation overlay with optional model-space anchors.

    ``start``/``end``/``label_position`` are normalized viewport fallbacks for
    the lightweight Qt overlay. ``anchor`` carries the model-space points used
    by native CAD viewers and persisted snapshot metadata.
    """

    id: str
    label: str = "0.000"
    role: ViewerAnnotationRole = ViewerAnnotationRole.STACKUP
    start: tuple[float, float] = (0.42, 0.34)
    end: tuple[float, float] = (0.42, 0.70)
    label_position: tuple[float, float] | None = None
    leader_points: tuple[tuple[float, float], ...] = ()
    shape_ids: tuple[str, ...] = ()
    feature_ids: tuple[str, ...] = ()
    anchor: "ViewerAnnotationAnchor | None" = None
    draggable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "role": self.role.value,
            "start": [float(self.start[0]), float(self.start[1])],
            "end": [float(self.end[0]), float(self.end[1])],
            "label_position": (
                [float(self.label_position[0]), float(self.label_position[1])]
                if self.label_position
                else None
            ),
            "leader_points": [
                [float(point[0]), float(point[1])] for point in self.leader_points
            ],
            "shape_ids": list(self.shape_ids),
            "feature_ids": list(self.feature_ids),
            "anchor": self.anchor.to_dict() if self.anchor else None,
            "draggable": self.draggable,
        }


@dataclass(frozen=True)
class ViewerAnnotationAnchor:
    """Serializable model-space anchor for CAD callouts.

    The anchor is intentionally kernel-neutral: it stores only coordinates,
    serializable ids, and small metadata. The screen coordinate is a normalized
    fallback for the Qt overlay and for preserving a user's dragged label
    placement when no reverse screen-to-model projection is available.
    """

    start_model: tuple[float, float, float] | None = None
    end_model: tuple[float, float, float] | None = None
    label_model: tuple[float, float, float] | None = None
    leader_model_points: tuple[tuple[float, float, float], ...] = ()
    screen: tuple[float, float] | None = None
    source_feature_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> "ViewerAnnotationAnchor | None":
        if not isinstance(data, Mapping):
            return None
        payload = data.get("anchor")
        if isinstance(payload, Mapping):
            data = payload
        model = _tuple3(data.get("model"))
        start = _tuple3(data.get("start_model")) or model
        end = _tuple3(data.get("end_model")) or model
        label = _tuple3(data.get("label_model")) or model
        leader_points = tuple(
            point
            for point in (_tuple3(item) for item in data.get("leader_model_points", ()))
            if point is not None
        )
        screen = _tuple2(data.get("screen"))
        if not any((start, end, label, leader_points, screen)):
            return None
        return cls(
            start_model=start,
            end_model=end,
            label_model=label,
            leader_model_points=leader_points,
            screen=screen,
            source_feature_id=str(data.get("source_feature_id") or ""),
            metadata=dict(data.get("metadata") or {}),
        )

    def with_screen(self, screen: tuple[float, float]) -> "ViewerAnnotationAnchor":
        return ViewerAnnotationAnchor(
            start_model=self.start_model,
            end_model=self.end_model,
            label_model=self.label_model,
            leader_model_points=self.leader_model_points,
            screen=(_clamp01(screen[0]), _clamp01(screen[1])),
            source_feature_id=self.source_feature_id,
            metadata=dict(self.metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        has_model = any((self.start_model, self.end_model, self.label_model, self.leader_model_points))
        return {
            "kind": "model_space" if has_model else "viewport",
            "version": 1,
            "start_model": _list3(self.start_model),
            "end_model": _list3(self.end_model),
            "label_model": _list3(self.label_model),
            "leader_model_points": [
                [float(value) for value in point] for point in self.leader_model_points
            ],
            "screen": (
                [_clamp01(self.screen[0]), _clamp01(self.screen[1])]
                if self.screen
                else None
            ),
            "source_feature_id": self.source_feature_id,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class CadViewerSelection:
    """Domain-level selection event payload emitted by viewer adapters."""

    shape_reference: ShapeReference
    feature_reference: FeatureReference | None = None
    mode: ViewerSelectionMode | None = None
    role: HighlightRole | None = None
    screen_position: tuple[int, int] | None = None
    model_position: tuple[float, float, float] | None = None

    @property
    def shape_id(self) -> str:
        return self.shape_reference.id

    @property
    def feature_id(self) -> str:
        return self.feature_reference.id if self.feature_reference else ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "shape_id": self.shape_id,
            "shape_type": self.shape_reference.shape_type.value,
            "feature_id": self.feature_id,
            "feature_type": (
                self.feature_reference.feature_type.value
                if self.feature_reference
                else None
            ),
            "mode": self.mode.value if self.mode else None,
            "role": self.role.value if self.role else None,
            "screen_position": list(self.screen_position)
            if self.screen_position
            else None,
            "model_position": list(self.model_position)
            if self.model_position
            else None,
        }


def _tuple2(value: Any) -> tuple[float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    if not all(isinstance(item, (int, float)) for item in value):
        return None
    return _clamp01(value[0]), _clamp01(value[1])


def _tuple3(value: Any) -> tuple[float, float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    if not all(isinstance(item, (int, float)) for item in value):
        return None
    return float(value[0]), float(value[1]), float(value[2])


def _list3(value: tuple[float, float, float] | None) -> list[float] | None:
    return [float(item) for item in value] if value else None


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass(frozen=True)
class SnapshotRequest:
    """Viewer snapshot request with serializable output metadata."""

    output_path: Path
    visible_stackup_ids: tuple[str, ...] = ()
    annotations: tuple[ViewerAnnotation, ...] = ()
    annotation_positions: dict[str, Any] = field(default_factory=dict)
    highlight_shape_ids: tuple[str, ...] = ()
    highlight_feature_ids: tuple[str, ...] = ()
    warning_ids: tuple[str, ...] = ()
    artifact_metadata: dict[str, Any] = field(default_factory=dict)


class CadViewer(Protocol):
    """Protocol implemented by replaceable CAD viewer adapters."""

    def display_document(
        self,
        session: CadRuntimeShapeProvider,
        display_kinds: set[ShapeKind] | None = None,
    ) -> None:
        """Display live kernel shapes from an imported geometry session."""

    def clear(self) -> None:
        """Clear transient presentation state."""

    def fit_all(self) -> None:
        """Fit all displayed geometry in the active view."""

    def pan(self, dx: int, dy: int) -> None:
        """Pan the active view by screen-space pixels."""

    def zoom(self, factor: float) -> None:
        """Zoom the active view by a positive factor."""

    def set_standard_view(self, view: StandardView) -> None:
        """Set one of the standard CAD orientations."""

    def set_selection_modes(self, modes: set[ViewerSelectionMode]) -> None:
        """Set active B-Rep-backed selection modes."""

    def highlight(
        self,
        shape_ref: ShapeReference,
        role: HighlightRole,
    ) -> None:
        """Apply a transient role highlight to a serializable shape reference."""

    def clear_highlights(self, roles: Iterable[HighlightRole] | None = None) -> None:
        """Clear transient highlights."""

    def set_annotations(self, annotations: Iterable[ViewerAnnotation]) -> None:
        """Set snapshot-ready viewport annotations."""

    def camera_state(self) -> CadCameraState:
        """Return current serializable camera state."""

    def capture_snapshot(self, request: SnapshotRequest) -> Snapshot:
        """Capture a report-ready image snapshot."""
