"""Kernel-neutral CAD viewer API for CAD 1D tolerance workflows."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from .cad_geometry_api import CadGeometrySession
from .cad_tolerance_models import FeatureReference, ShapeKind, ShapeReference, Snapshot


class CadViewerError(RuntimeError):
    """Base exception for CAD viewer adapter failures."""


class CadViewerUnavailable(CadViewerError):
    """Raised when the optional viewer runtime cannot initialize."""


class HighlightRole(str, Enum):
    HOVER = "hover"
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
class CadViewerSelection:
    """Domain-level selection event payload emitted by viewer adapters."""

    shape_reference: ShapeReference
    feature_reference: FeatureReference | None = None
    mode: ViewerSelectionMode | None = None
    role: HighlightRole | None = None
    screen_position: tuple[int, int] | None = None

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
        }


@dataclass(frozen=True)
class SnapshotRequest:
    """Viewer snapshot request with serializable output metadata."""

    output_path: Path
    visible_stackup_ids: tuple[str, ...] = ()
    annotation_positions: dict[str, Any] = field(default_factory=dict)
    highlight_shape_ids: tuple[str, ...] = ()
    highlight_feature_ids: tuple[str, ...] = ()
    warning_ids: tuple[str, ...] = ()
    artifact_metadata: dict[str, Any] = field(default_factory=dict)


class CadViewer(Protocol):
    """Protocol implemented by replaceable CAD viewer adapters."""

    def display_document(
        self,
        session: CadGeometrySession,
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

    def camera_state(self) -> CadCameraState:
        """Return current serializable camera state."""

    def capture_snapshot(self, request: SnapshotRequest) -> Snapshot:
        """Capture a report-ready image snapshot."""
