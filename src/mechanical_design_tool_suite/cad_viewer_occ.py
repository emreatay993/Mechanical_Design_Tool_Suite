"""PyQt6/pythonocc AIS/V3d CAD viewer adapter."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
from typing import Any

from .cad_geometry_api import CadRuntimeShapeProvider, feature_from_shape_reference
from .cad_display_style import display_color_for_part, rgb_bytes_to_unit
from .cad_tolerance_models import (
    AssemblyNode,
    FeatureReference,
    ShapeKind,
    ShapeReference,
    Snapshot,
)
from .cad_viewer_api import (
    CadCameraState,
    CadViewerError,
    CadViewerSelection,
    CadViewerUnavailable,
    HighlightRole,
    SnapshotRequest,
    StandardView,
    ViewerAnnotation,
    ViewerAnnotationRole,
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

    from OCC.Core.Aspect import Aspect_GFM_VER, Aspect_TOL_SOLID
    from OCC.Display.backend import load_backend

    load_backend("pyqt6")
    from OCC.Core.AIS import AIS_Shape, AIS_TextLabel
    from OCC.Core.gp import gp_Dir, gp_Pln, gp_Pnt
    from OCC.Core.Graphic3d import (
        Graphic3d_MaterialAspect,
        Graphic3d_NOM_SATIN,
        Graphic3d_TypeOfShadingModel_Phong,
    )
    from OCC.Core.Prs3d import Prs3d_LineAspect
    from OCC.Core.PrsDim import PrsDim_LengthDimension
    from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
    from OCC.Core.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_SOLID, TopAbs_VERTEX
    from OCC.Display.qtDisplay import qtViewer3d
except Exception as exc:  # pragma: no cover - exercised without CAD deps.
    _IMPORT_ERROR = exc
    pyqtSignal = None  # type: ignore[assignment]
    QVBoxLayout = None  # type: ignore[assignment]
    QWidget = object  # type: ignore[assignment,misc]
    AIS_Shape = None  # type: ignore[assignment]
    AIS_TextLabel = None  # type: ignore[assignment]
    gp_Dir = None  # type: ignore[assignment]
    gp_Pln = None  # type: ignore[assignment]
    gp_Pnt = None  # type: ignore[assignment]
    Aspect_GFM_VER = None  # type: ignore[assignment]
    Aspect_TOL_SOLID = None  # type: ignore[assignment]
    Graphic3d_MaterialAspect = None  # type: ignore[assignment]
    Graphic3d_NOM_SATIN = None  # type: ignore[assignment]
    Graphic3d_TypeOfShadingModel_Phong = None  # type: ignore[assignment]
    Prs3d_LineAspect = None  # type: ignore[assignment]
    PrsDim_LengthDimension = None  # type: ignore[assignment]
    Quantity_Color = None  # type: ignore[assignment]
    Quantity_TOC_RGB = None  # type: ignore[assignment]
    TopAbs_EDGE = None  # type: ignore[assignment]
    TopAbs_FACE = None  # type: ignore[assignment]
    TopAbs_SOLID = None  # type: ignore[assignment]
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
            self.uses_native_annotations = True
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            layout.addWidget(self._viewer)

            self._display: Any | None = None
            self._context: Any | None = None
            self._session: CadRuntimeShapeProvider | None = None
            self._initialized = False
            self._selection_modes: set[ViewerSelectionMode] = {ViewerSelectionMode.BODY}
            self._displayed_ais_by_shape_id: dict[str, Any] = {}
            self._displayed_shape_refs: dict[str, ShapeReference] = {}
            self._selectable_shape_refs: dict[str, ShapeReference] = {}
            self._feature_refs_by_shape_id: dict[str, FeatureReference] = {}
            self._kernel_shapes_by_shape_id: dict[str, Any] = {}
            self._highlight_ais: dict[tuple[str, HighlightRole], Any] = {}
            self._annotation_ais: list[Any] = []
            self._last_selection: list[CadViewerSelection] = []
            self._annotations: tuple[ViewerAnnotation, ...] = ()

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

        @property
        def active_selection_modes(self) -> tuple[ViewerSelectionMode, ...]:
            return tuple(sorted(self._selection_modes, key=lambda mode: mode.value))

        @property
        def annotations(self) -> tuple[ViewerAnnotation, ...]:
            return self._annotations

        @property
        def native_annotation_count(self) -> int:
            return len(self._annotation_ais)

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
                self._apply_view_style()
                self._display.register_select_callback(self._on_occ_selection)
                self._initialized = True
                self._apply_selection_modes()
            except Exception as exc:
                raise CadViewerUnavailable(
                    f"{OCC_VIEWER_DEPENDENCY_MESSAGE} Exact error: {exc}"
                ) from exc

        def display_document(
            self,
            session: CadRuntimeShapeProvider,
            display_kinds: set[ShapeKind] | None = None,
        ) -> None:
            """Display live OCCT shapes exposed by a P03 geometry session."""

            self.initialize_viewer()
            current_annotations = self._annotations
            self.clear()
            self._annotations = current_annotations
            self._session = session
            display_kinds = display_kinds or {ShapeKind.BODY}
            self._index_session_shapes(session)
            shape_refs = session.shape_references(display_kinds)
            if not shape_refs and ShapeKind.BODY in display_kinds:
                shape_refs = session.shape_references()
            use_palette_colors = _should_use_palette_colors(session, shape_refs)

            for display_index, shape_ref in enumerate(shape_refs, start=1):
                occ_shape = self._kernel_shapes_by_shape_id.get(shape_ref.id)
                if occ_shape is None:
                    continue
                color_rgb = _shape_display_rgb(
                    session,
                    shape_ref,
                    display_index,
                    use_palette_colors=use_palette_colors,
                )
                ais_shapes = self._display.DisplayShape(  # type: ignore[union-attr]
                    occ_shape,
                    material=Graphic3d_MaterialAspect(Graphic3d_NOM_SATIN),
                    color=_quantity_color(color_rgb),
                    transparency=0.0,
                    update=False,
                )
                if not ais_shapes:
                    continue
                for ais_shape in ais_shapes:
                    _apply_object_style(ais_shape, color_rgb)
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
            self._annotation_ais.clear()
            self._last_selection = []
            self._annotations = ()
            if self._context is not None:
                self._context.RemoveAll(False)
                self._context.UpdateCurrentViewer()

        def fit_all(self) -> None:
            self.initialize_viewer()
            self._display.FitAll()  # type: ignore[union-attr]
            self._display.Repaint()  # type: ignore[union-attr]
            self._sync_native_annotations()

        def pan(self, dx: int, dy: int) -> None:
            self.initialize_viewer()
            self._display.Pan(int(dx), int(dy))  # type: ignore[union-attr]
            self._sync_native_annotations()

        def zoom(self, factor: float) -> None:
            if factor <= 0.0:
                raise ValueError("Zoom factor must be positive.")
            self.initialize_viewer()
            self._display.ZoomFactor(float(factor))  # type: ignore[union-attr]
            self._sync_native_annotations()

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
                occ_shape = self._session.runtime_shape(shape_ref)
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

        def set_annotations(self, annotations: Iterable[ViewerAnnotation]) -> None:
            self._annotations = tuple(annotations)
            if self._initialized:
                self._sync_native_annotations()

        def _sync_native_annotations(self) -> None:
            if self._context is None or self._display is None:
                return
            self._clear_native_annotations(update=False)
            for annotation in self._annotations:
                for ais in self._annotation_presentations(annotation):
                    self._context.Display(ais, False)
                    self._annotation_ais.append(ais)
            self._context.UpdateCurrentViewer()

        def _clear_native_annotations(self, *, update: bool = True) -> None:
            if self._context is None:
                self._annotation_ais.clear()
                return
            for ais in self._annotation_ais:
                self._context.Remove(ais, False)
            self._annotation_ais.clear()
            if update:
                self._context.UpdateCurrentViewer()

        def _annotation_presentations(
            self,
            annotation: ViewerAnnotation,
        ) -> tuple[Any, ...]:
            try:
                start = self._annotation_start_point(annotation)
                end = self._annotation_end_point(annotation)
                label = self._annotation_label_point(annotation)
                color = _quantity_color(_annotation_rgb(annotation.role))
                if start.Distance(end) <= 1.0e-7:
                    return (self._text_label(annotation.label, label, color),)

                plane = gp_Pln(start, self._view_plane_normal())  # type: ignore[misc]
                dimension = PrsDim_LengthDimension(start, end, plane)
                dimension.SetCustomValue(str(annotation.label))
                dimension.SetTextPosition(label)
                dimension.SetColor(color)
                aspect = dimension.DimensionAspect()
                _try_call(aspect.SetCommonColor, color)
                _try_call(aspect.MakeArrows3d, False)
                _try_call(aspect.MakeText3d, False)
                _try_call(aspect.MakeTextShaded, False)
                text_aspect = aspect.TextAspect()
                _try_call(text_aspect.SetHeight, self._annotation_text_height())
                _try_call(aspect.SetTextAspect, text_aspect)
                _try_call(dimension.SetDimensionAspect, aspect)
                return (dimension,)
            except Exception:
                try:
                    label = self._point_from_normalized(
                        annotation.label_position or _annotation_midpoint(annotation)
                    )
                    return (
                        self._text_label(
                            annotation.label,
                            label,
                            _quantity_color(_annotation_rgb(annotation.role)),
                        ),
                    )
                except Exception:
                    return ()

        def _annotation_start_point(self, annotation: ViewerAnnotation) -> Any:
            anchor = annotation.anchor
            if anchor is not None and anchor.start_model is not None:
                return _gp_point(anchor.start_model)
            if anchor is not None and anchor.leader_model_points:
                return _gp_point(anchor.leader_model_points[0])
            return self._point_from_normalized(annotation.start)

        def _annotation_end_point(self, annotation: ViewerAnnotation) -> Any:
            anchor = annotation.anchor
            if anchor is not None and anchor.end_model is not None:
                return _gp_point(anchor.end_model)
            if anchor is not None and len(anchor.leader_model_points) >= 2:
                return _gp_point(anchor.leader_model_points[-1])
            return self._point_from_normalized(annotation.end)

        def _annotation_label_point(self, annotation: ViewerAnnotation) -> Any:
            anchor = annotation.anchor
            if anchor is not None and anchor.label_model is not None:
                return _gp_point(anchor.label_model)
            if anchor is not None and anchor.end_model is not None:
                return _gp_point(anchor.end_model)
            return self._point_from_normalized(
                annotation.label_position or _annotation_midpoint(annotation)
            )

        def _point_from_normalized(self, point: tuple[float, float]) -> Any:
            view = self._display.View  # type: ignore[union-attr]
            x = int(round(_clamp01(point[0]) * max(1, self._viewer.width() - 1)))
            y = int(round(_clamp01(point[1]) * max(1, self._viewer.height() - 1)))
            converted = view.ConvertWithProj(x, y)
            return gp_Pnt(  # type: ignore[misc]
                float(converted[0]),
                float(converted[1]),
                float(converted[2]),
            )

        def _view_plane_normal(self) -> Any:
            view = self._display.View  # type: ignore[union-attr]
            try:
                projection = view.Proj()
                return gp_Dir(  # type: ignore[misc]
                    float(projection[0]),
                    float(projection[1]),
                    float(projection[2]),
                )
            except Exception:
                return gp_Dir(0.0, 0.0, 1.0)  # type: ignore[misc]

        def _annotation_text_height(self) -> float:
            try:
                _width, height = self._display.View.Size()  # type: ignore[union-attr]
                return max(1.0, float(height) * 0.028)
            except Exception:
                return 4.0

        def _text_label(self, text: str, position: Any, color: Any) -> Any:
            label = AIS_TextLabel()
            label.SetText(str(text))
            label.SetPosition(position)
            label.SetColor(color)
            label.SetHeight(self._annotation_text_height())
            _try_call(label.SetZoomable, False)
            return label

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
            annotation_positions = dict(request.annotation_positions)
            annotations = request.annotations or self._annotations
            if annotations:
                annotation_positions["_viewer_annotations"] = [
                    annotation.to_dict() for annotation in annotations
                ]
            return Snapshot(
                image_path=str(output_path),
                camera=self.camera_state().to_dict(),
                visible_stackup_ids=list(request.visible_stackup_ids),
                annotation_positions=annotation_positions,
                captured_at=_utc_timestamp(),
            )

        def shape_reference_for_kernel_shape(self, selected_shape: Any) -> ShapeReference | None:
            for shape_id, candidate in self._kernel_shapes_by_shape_id.items():
                if _topods_same(selected_shape, candidate):
                    return self._selectable_shape_refs.get(shape_id)
            return None

        def _index_session_shapes(self, session: CadRuntimeShapeProvider) -> None:
            self._selectable_shape_refs.clear()
            self._feature_refs_by_shape_id.clear()
            self._kernel_shapes_by_shape_id.clear()
            for shape_ref in session.shape_references():
                occ_shape = session.runtime_shape(shape_ref)
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
            for mode in modes:
                selection_mode = _selection_mode(mode)
                if selection_mode is not None:
                    self._context.Activate(selection_mode, True)
            self._context.UpdateSelected(True)

        def _apply_view_style(self) -> None:
            """Apply viewport styling without making OCC version-specific calls fatal."""

            _try_call(
                self._display.set_bg_gradient_color,
                [196, 198, 200],
                [232, 233, 235],
                Aspect_GFM_VER,
            )
            _try_call(self._display.display_triedron)

            viewer = getattr(self._display, "Viewer", None)
            if viewer is not None:
                _try_call(viewer.SetDefaultLights)
                _try_call(viewer.SetLightOn)
                _try_call(
                    viewer.SetDefaultShadingModel,
                    Graphic3d_TypeOfShadingModel_Phong,
                )

            view = getattr(self._display, "View", None)
            if view is not None:
                _try_call(view.SetLightOn)
                _try_call(view.SetShadingModel, Graphic3d_TypeOfShadingModel_Phong)
                try:
                    params = view.ChangeRenderingParams()
                    params.IsAntialiasingEnabled = True
                    params.NbMsaaSamples = 4
                    params.ShadingModel = Graphic3d_TypeOfShadingModel_Phong
                except Exception:
                    pass

            if self._context is not None:
                drawer = self._context.DefaultDrawer()
                boundary = Prs3d_LineAspect(
                    _quantity_color((0.17, 0.19, 0.21)),
                    Aspect_TOL_SOLID,
                    1.0,
                )
                _try_call(drawer.SetFaceBoundaryDraw, True)
                _try_call(drawer.SetFaceBoundaryAspect, boundary)

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
                        model_position=_selection_model_position(feature_ref),
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


def _selection_mode(mode: ViewerSelectionMode) -> Any | None:
    if mode == ViewerSelectionMode.BODY:
        return AIS_Shape.SelectionMode(TopAbs_SOLID)
    if mode == ViewerSelectionMode.FACE:
        return AIS_Shape.SelectionMode(TopAbs_FACE)
    if mode == ViewerSelectionMode.EDGE:
        return AIS_Shape.SelectionMode(TopAbs_EDGE)
    if mode == ViewerSelectionMode.VERTEX:
        return AIS_Shape.SelectionMode(TopAbs_VERTEX)
    return None


def _selection_event_mode(
    modes: set[ViewerSelectionMode],
) -> ViewerSelectionMode | None:
    if len(modes) == 1:
        return next(iter(modes))
    return None


def _annotation_midpoint(annotation: ViewerAnnotation) -> tuple[float, float]:
    return (
        (float(annotation.start[0]) + float(annotation.end[0])) / 2.0,
        (float(annotation.start[1]) + float(annotation.end[1])) / 2.0,
    )


def _gp_point(point: tuple[float, float, float]) -> Any:
    return gp_Pnt(float(point[0]), float(point[1]), float(point[2]))  # type: ignore[misc]


def _annotation_rgb(role: ViewerAnnotationRole) -> tuple[float, float, float]:
    role = ViewerAnnotationRole(role)
    if role == ViewerAnnotationRole.STACKUP:
        return (0.92, 0.04, 0.03)
    if role == ViewerAnnotationRole.CONTRIBUTOR:
        return (0.04, 0.32, 0.88)
    if role == ViewerAnnotationRole.WARNING:
        return (0.94, 0.64, 0.05)
    return (0.06, 0.06, 0.06)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _screen_position(args: tuple[Any, ...]) -> tuple[int, int] | None:
    if len(args) >= 2 and all(isinstance(value, int) for value in args[:2]):
        return int(args[0]), int(args[1])
    return None


def _selection_model_position(
    feature_ref: FeatureReference | None,
) -> tuple[float, float, float] | None:
    if feature_ref is None or feature_ref.point is None:
        return None
    return (
        float(feature_ref.point.x),
        float(feature_ref.point.y),
        float(feature_ref.point.z),
    )


def _highlight_style(role: HighlightRole) -> tuple[tuple[float, float, float], float]:
    styles = {
        HighlightRole.HOVER: ((0.12, 0.86, 0.25), 0.58),
        HighlightRole.ELIGIBLE: ((0.12, 0.86, 0.25), 0.58),
        HighlightRole.CROSS_HIGHLIGHT: ((0.9, 0.12, 0.12), 0.42),
        HighlightRole.SELECTED_START: ((0.9, 0.12, 0.12), 0.42),
        HighlightRole.SELECTED_END: ((0.9, 0.12, 0.12), 0.42),
        HighlightRole.DIRECTION: ((0.9, 0.12, 0.12), 0.50),
        HighlightRole.ANALYSIS_PLANE: ((0.9, 0.12, 0.12), 0.55),
        HighlightRole.LOOP_MEMBER: ((0.12, 0.86, 0.25), 0.52),
        HighlightRole.WARNING: ((1.0, 0.86, 0.05), 0.38),
    }
    return styles[role]


def _shape_display_rgb(
    session: CadRuntimeShapeProvider,
    shape_ref: ShapeReference,
    display_index: int,
    *,
    use_palette_colors: bool = False,
) -> tuple[float, float, float]:
    part_name = (
        shape_ref.assembly_path[-1]
        if shape_ref.assembly_path
        else shape_ref.fallback_display_name
    )
    display_color = None
    if not use_palette_colors:
        display_color = _assembly_display_color(session, shape_ref.assembly_path)
    if display_color is None:
        display_color = display_color_for_part(part_name, display_index)
    return rgb_bytes_to_unit(display_color)


def _should_use_palette_colors(
    session: CadRuntimeShapeProvider,
    shape_refs: Iterable[ShapeReference],
) -> bool:
    body_colors: list[tuple[int, int, int]] = []
    for index, shape_ref in enumerate(shape_refs, start=1):
        if shape_ref.shape_type != ShapeKind.BODY:
            continue
        color = _assembly_display_color(session, shape_ref.assembly_path)
        if color is None:
            return False
        body_colors.append(tuple(int(channel) for channel in color[:3]))
    if len(body_colors) < 2:
        return False
    return len(set(body_colors)) == 1 and _is_neutral_display_color(body_colors[0])


def _is_neutral_display_color(color: tuple[int, int, int]) -> bool:
    red, green, blue = color
    spread = max(color) - min(color)
    return spread <= 40 or (abs(red - green) <= 10 and abs(green - blue) <= 50)


def _assembly_display_color(
    session: CadRuntimeShapeProvider,
    assembly_path: list[str],
) -> tuple[int, int, int] | None:
    if not assembly_path:
        return None
    for root in session.assembly_tree():
        match = _find_assembly_node_by_path(root, assembly_path)
        if match is not None and match.display_color is not None:
            return match.display_color
    return None


def _find_assembly_node_by_path(
    node: AssemblyNode,
    path: list[str],
) -> AssemblyNode | None:
    if not path or node.name != path[0]:
        return None
    if len(path) == 1:
        return node
    for child in node.children:
        match = _find_assembly_node_by_path(child, path[1:])
        if match is not None:
            return match
    return None


def _apply_object_style(ais_shape: Any, color_rgb: tuple[float, float, float]) -> None:
    _try_call(ais_shape.SetColor, _quantity_color(color_rgb))
    _try_call(ais_shape.SetMaterial, Graphic3d_MaterialAspect(Graphic3d_NOM_SATIN))


def _quantity_color(rgb: tuple[float, float, float]) -> Any:
    return Quantity_Color(float(rgb[0]), float(rgb[1]), float(rgb[2]), Quantity_TOC_RGB)


def _try_call(callable_obj: Any, *args: Any) -> None:
    try:
        callable_obj(*args)
    except Exception:
        pass


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
