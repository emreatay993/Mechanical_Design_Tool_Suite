"""PyQt6/pythonocc AIS/V3d CAD viewer adapter."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
from typing import Any

from .cad_geometry_api import CadGeometrySession, feature_from_shape_reference
from .cad_tolerance_models import FeatureReference, ShapeKind, ShapeReference, Snapshot
from .cad_viewer_api import (
    CadCameraState,
    CadViewerError,
    CadViewerSelection,
    CadViewerUnavailable,
    HighlightRole,
    SnapshotRequest,
    StandardView,
    ViewerSelectionMode,
)


OCC_VIEWER_DEPENDENCY_MESSAGE = (
    "The primary CAD viewer requires PyQt6 and pythonocc-core with the PyQt6 "
    "backend. Use the mdts-cad312 environment and call "
    'OCC.Display.backend.load_backend("pyqt6") before importing qtViewer3d.'
)

_IMPORT_ERROR: Exception | None = None

try:
    from PyQt6.QtCore import pyqtSignal
    from PyQt6.QtWidgets import QVBoxLayout, QWidget

    from OCC.Display.backend import load_backend

    load_backend("pyqt6")
    from OCC.Core.AIS import AIS_Shape
    from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
    from OCC.Core.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_VERTEX
    from OCC.Display.qtDisplay import qtViewer3d
except Exception as exc:  # pragma: no cover - exercised without CAD deps.
    _IMPORT_ERROR = exc
    pyqtSignal = None  # type: ignore[assignment]
    QVBoxLayout = None  # type: ignore[assignment]
    QWidget = object  # type: ignore[assignment,misc]
    AIS_Shape = None  # type: ignore[assignment]
    Quantity_Color = None  # type: ignore[assignment]
    Quantity_TOC_RGB = None  # type: ignore[assignment]
    TopAbs_EDGE = None  # type: ignore[assignment]
    TopAbs_FACE = None  # type: ignore[assignment]
    TopAbs_VERTEX = None  # type: ignore[assignment]
    qtViewer3d = None  # type: ignore[assignment]


def is_occ_viewer_available() -> bool:
    """Return whether the PyQt6 OCC viewer stack can be imported."""

    return _IMPORT_ERROR is None


def occ_viewer_import_error() -> Exception | None:
    """Return the optional viewer import error, if the stack is unavailable."""

    return _IMPORT_ERROR


def is_pyqt5_available() -> bool:
    """Return whether PyQt5 is visible to the current interpreter."""

    return importlib.util.find_spec("PyQt5") is not None


if _IMPORT_ERROR is None:

    class OccCadViewerWidget(QWidget):  # type: ignore[misc]
        """OCCT AIS/V3d viewer widget embedded in PyQt6."""

        selection_changed = pyqtSignal(object)

        def __init__(self, parent: QWidget | None = None) -> None:
            super().__init__(parent)
            self._viewer = qtViewer3d(self)
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            layout.addWidget(self._viewer)

            self._display: Any | None = None
            self._context: Any | None = None
            self._session: CadGeometrySession | None = None
            self._initialized = False
            self._selection_modes: set[ViewerSelectionMode] = {ViewerSelectionMode.BODY}
            self._displayed_ais_by_shape_id: dict[str, Any] = {}
            self._displayed_shape_refs: dict[str, ShapeReference] = {}
            self._selectable_shape_refs: dict[str, ShapeReference] = {}
            self._feature_refs_by_shape_id: dict[str, FeatureReference] = {}
            self._kernel_shapes_by_shape_id: dict[str, Any] = {}
            self._highlight_ais: dict[tuple[str, HighlightRole], Any] = {}
            self._last_selection: list[CadViewerSelection] = []

        @property
        def raw_qt_viewer(self) -> Any:
            """Return the wrapped pythonocc qtViewer3d widget."""

            return self._viewer

        @property
        def displayed_shape_ids(self) -> tuple[str, ...]:
            return tuple(self._displayed_ais_by_shape_id)

        @property
        def selected_shapes(self) -> tuple[CadViewerSelection, ...]:
            return tuple(self._last_selection)

        def initialize_viewer(self) -> None:
            """Initialize the OCCT display driver if needed."""

            if self._initialized:
                return
            try:
                if not getattr(self._viewer, "_inited", False):
                    self._viewer.InitDriver()
                self._display = self._viewer._display
                self._context = self._display.Context
                self._display.SetModeShaded()
                self._display.register_select_callback(self._on_occ_selection)
                self._initialized = True
                self._apply_selection_modes()
            except Exception as exc:
                raise CadViewerUnavailable(
                    f"{OCC_VIEWER_DEPENDENCY_MESSAGE} Exact error: {exc}"
                ) from exc

        def display_document(
            self,
            session: CadGeometrySession,
            display_kinds: set[ShapeKind] | None = None,
        ) -> None:
            """Display live OCCT shapes exposed by a P03 geometry session."""

            self.initialize_viewer()
            self.clear()
            self._session = session
            display_kinds = display_kinds or {ShapeKind.BODY}
            self._index_session_shapes(session)
            shape_refs = session.shape_references(display_kinds)
            if not shape_refs and ShapeKind.BODY in display_kinds:
                shape_refs = session.shape_references()

            for shape_ref in shape_refs:
                occ_shape = self._kernel_shapes_by_shape_id.get(shape_ref.id)
                if occ_shape is None:
                    continue
                ais_shapes = self._display.DisplayShape(  # type: ignore[union-attr]
                    occ_shape,
                    color=_quantity_color((0.74, 0.78, 0.82)),
                    transparency=0.0,
                    update=False,
                )
                if not ais_shapes:
                    continue
                self._displayed_ais_by_shape_id[shape_ref.id] = ais_shapes[0]
                self._displayed_shape_refs[shape_ref.id] = shape_ref

            if not self._displayed_ais_by_shape_id:
                raise CadViewerError(
                    "No live OCCT shapes were available from the geometry session."
                )
            self.fit_all()

        def clear(self) -> None:
            self._displayed_ais_by_shape_id.clear()
            self._displayed_shape_refs.clear()
            self._selectable_shape_refs.clear()
            self._feature_refs_by_shape_id.clear()
            self._kernel_shapes_by_shape_id.clear()
            self._highlight_ais.clear()
            self._last_selection = []
            if self._context is not None:
                self._context.RemoveAll(False)
                self._context.UpdateCurrentViewer()

        def fit_all(self) -> None:
            self.initialize_viewer()
            self._display.FitAll()  # type: ignore[union-attr]
            self._display.Repaint()  # type: ignore[union-attr]

        def pan(self, dx: int, dy: int) -> None:
            self.initialize_viewer()
            self._display.Pan(int(dx), int(dy))  # type: ignore[union-attr]

        def zoom(self, factor: float) -> None:
            if factor <= 0.0:
                raise ValueError("Zoom factor must be positive.")
            self.initialize_viewer()
            self._display.ZoomFactor(float(factor))  # type: ignore[union-attr]

        def set_standard_view(self, view: StandardView) -> None:
            self.initialize_viewer()
            view_methods = {
                StandardView.ISO: self._display.View_Iso,
                StandardView.FRONT: self._display.View_Front,
                StandardView.REAR: self._display.View_Rear,
                StandardView.LEFT: self._display.View_Left,
                StandardView.RIGHT: self._display.View_Right,
                StandardView.TOP: self._display.View_Top,
                StandardView.BOTTOM: self._display.View_Bottom,
            }
            view_methods[StandardView(view)]()
            self.fit_all()

        def set_selection_modes(self, modes: set[ViewerSelectionMode]) -> None:
            self._selection_modes = set(modes) or {ViewerSelectionMode.BODY}
            if self._initialized:
                self._apply_selection_modes()

        def highlight(
            self,
            shape_ref: ShapeReference,
            role: HighlightRole,
        ) -> None:
            self.initialize_viewer()
            if self._session is None:
                raise CadViewerError("Display a geometry session before highlighting.")
            role = HighlightRole(role)
            self.clear_highlights([role])
            occ_shape = self._kernel_shapes_by_shape_id.get(shape_ref.id)
            if occ_shape is None:
                occ_shape = self._session.kernel_shape(shape_ref)  # type: ignore[attr-defined]
            if occ_shape is None:
                raise CadViewerError(f"No live OCCT shape for {shape_ref.id!r}.")

            ais = AIS_Shape(occ_shape)
            color_rgb, transparency = _highlight_style(role)
            ais.SetColor(_quantity_color(color_rgb))
            if transparency > 0.0:
                ais.SetTransparency(transparency)
            self._context.Display(ais, False)  # type: ignore[union-attr]
            self._highlight_ais[(shape_ref.id, role)] = ais
            self._context.UpdateCurrentViewer()  # type: ignore[union-attr]

        def clear_highlights(
            self,
            roles: Iterable[HighlightRole] | None = None,
        ) -> None:
            if self._context is None:
                self._highlight_ais.clear()
                return
            wanted = {HighlightRole(role) for role in roles} if roles else None
            for key, ais in list(self._highlight_ais.items()):
                _shape_id, role = key
                if wanted is not None and role not in wanted:
                    continue
                self._context.Remove(ais, False)
                del self._highlight_ais[key]
            self._context.UpdateCurrentViewer()

        def camera_state(self) -> CadCameraState:
            if not self._initialized or self._display is None:
                return CadCameraState()
            view = self._display.View
            return CadCameraState(
                eye=_vector_from_view_method(view, "Eye"),
                target=_vector_from_view_method(view, "At"),
                up=_vector_from_view_method(view, "Up"),
                projection=_vector_from_view_method(view, "Proj"),
                scale=_float_from_view_method(view, "Scale"),
                twist=_float_from_view_method(view, "Twist"),
            )

        def capture_snapshot(self, request: SnapshotRequest) -> Snapshot:
            self.initialize_viewer()
            output_path = Path(request.output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            self._display.ExportToImage(str(output_path))  # type: ignore[union-attr]
            return Snapshot(
                image_path=str(output_path),
                camera=self.camera_state().to_dict(),
                visible_stackup_ids=list(request.visible_stackup_ids),
                annotation_positions=dict(request.annotation_positions),
                captured_at=_utc_timestamp(),
            )

        def shape_reference_for_kernel_shape(self, selected_shape: Any) -> ShapeReference | None:
            for shape_id, candidate in self._kernel_shapes_by_shape_id.items():
                if _topods_same(selected_shape, candidate):
                    return self._selectable_shape_refs.get(shape_id)
            return None

        def _index_session_shapes(self, session: CadGeometrySession) -> None:
            self._selectable_shape_refs.clear()
            self._feature_refs_by_shape_id.clear()
            self._kernel_shapes_by_shape_id.clear()
            for shape_ref in session.shape_references():
                occ_shape = session.kernel_shape(shape_ref)  # type: ignore[attr-defined]
                if occ_shape is None:
                    continue
                self._selectable_shape_refs[shape_ref.id] = shape_ref
                self._kernel_shapes_by_shape_id[shape_ref.id] = occ_shape
            for feature_ref in session.feature_references():
                if feature_ref.shape_reference is not None:
                    self._feature_refs_by_shape_id[
                        feature_ref.shape_reference.id
                    ] = feature_ref

        def _apply_selection_modes(self) -> None:
            if self._context is None:
                return
            modes = self._selection_modes or {ViewerSelectionMode.BODY}
            self._context.Deactivate()
            if modes == {ViewerSelectionMode.BODY}:
                self._context.UpdateSelected(True)
                return
            for mode in modes:
                topology_mode = _topology_mode(mode)
                if topology_mode is not None:
                    self._context.Activate(AIS_Shape.SelectionMode(topology_mode), True)
            self._context.UpdateSelected(True)

        def _on_occ_selection(self, selected_shapes: list[Any], *screen_args: Any) -> None:
            selections: list[CadViewerSelection] = []
            screen_position = _screen_position(screen_args)
            mode = _selection_event_mode(self._selection_modes)
            for selected_shape in selected_shapes:
                shape_ref = self.shape_reference_for_kernel_shape(selected_shape)
                if shape_ref is None:
                    continue
                feature_ref = self._feature_refs_by_shape_id.get(shape_ref.id)
                if feature_ref is None and shape_ref.shape_type != ShapeKind.BODY:
                    feature_ref = feature_from_shape_reference(shape_ref)
                selections.append(
                    CadViewerSelection(
                        shape_reference=shape_ref,
                        feature_reference=feature_ref,
                        mode=mode,
                        screen_position=screen_position,
                    )
                )
            self._last_selection = selections
            self.selection_changed.emit(selections)

else:

    class OccCadViewerWidget:  # pragma: no cover - exercised without CAD deps.
        """Unavailable placeholder that reports the exact optional dependency issue."""

        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise CadViewerUnavailable(
                f"{OCC_VIEWER_DEPENDENCY_MESSAGE} Exact error: {_IMPORT_ERROR}"
            )


def _topology_mode(mode: ViewerSelectionMode) -> Any | None:
    if mode == ViewerSelectionMode.FACE:
        return TopAbs_FACE
    if mode == ViewerSelectionMode.EDGE:
        return TopAbs_EDGE
    if mode == ViewerSelectionMode.VERTEX:
        return TopAbs_VERTEX
    return None


def _selection_event_mode(
    modes: set[ViewerSelectionMode],
) -> ViewerSelectionMode | None:
    if len(modes) == 1:
        return next(iter(modes))
    return None


def _screen_position(args: tuple[Any, ...]) -> tuple[int, int] | None:
    if len(args) >= 2 and all(isinstance(value, int) for value in args[:2]):
        return int(args[0]), int(args[1])
    return None


def _highlight_style(role: HighlightRole) -> tuple[tuple[float, float, float], float]:
    styles = {
        HighlightRole.HOVER: ((1.0, 0.83, 0.16), 0.65),
        HighlightRole.SELECTED_START: ((0.1, 0.78, 0.28), 0.45),
        HighlightRole.SELECTED_END: ((0.9, 0.12, 0.12), 0.45),
        HighlightRole.DIRECTION: ((0.1, 0.35, 0.95), 0.45),
        HighlightRole.ANALYSIS_PLANE: ((0.8, 0.12, 0.8), 0.55),
        HighlightRole.LOOP_MEMBER: ((0.95, 0.84, 0.1), 0.55),
        HighlightRole.WARNING: ((1.0, 0.62, 0.0), 0.35),
    }
    return styles[role]


def _quantity_color(rgb: tuple[float, float, float]) -> Any:
    return Quantity_Color(float(rgb[0]), float(rgb[1]), float(rgb[2]), Quantity_TOC_RGB)


def _topods_same(a: Any, b: Any) -> bool:
    try:
        return bool(a.IsSame(b))
    except Exception:
        return a is b


def _vector_from_view_method(view: Any, method_name: str) -> tuple[float, float, float] | None:
    try:
        values = getattr(view, method_name)()
    except Exception:
        return None
    if not isinstance(values, tuple) or len(values) < 3:
        return None
    try:
        return (float(values[0]), float(values[1]), float(values[2]))
    except (TypeError, ValueError):
        return None


def _float_from_view_method(view: Any, method_name: str) -> float | None:
    try:
        return float(getattr(view, method_name)())
    except Exception:
        return None


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00",
        "Z",
    )
