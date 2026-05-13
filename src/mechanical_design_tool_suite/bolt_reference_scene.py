"""Embedded bolt result and reference geometry scene widget."""

from __future__ import annotations

import os
from typing import Any, Iterable

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .calculations import BoltCalculationResult
from .reference_geometry import (
    ReferenceMeshAsset,
    ReferencePart,
    clamp_opacity,
)
from .visualization import (
    HOVER_TEXT_POSITION,
    SCALAR_CHOICES,
    VISUALIZATION_CMAP,
    format_hover_text,
    hover_prompt_text,
    local_scalar_range,
    results_have_coordinates,
    scalar_values_for_results,
)


REFERENCE_COLOR = "#9fb4c8"
SELECTED_EDGE_COLOR = "#f0b429"
BOLT_NODE_SIZE_DEFAULT = 22
BOLT_NODE_SIZE_MIN = 8
BOLT_NODE_SIZE_MAX = 56
BOLT_NODE_SIZE_STEP = 2


class BoltReferenceSceneWidget(QWidget):
    """Unified bolt result and visual reference geometry scene."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._plotter: Any | None = None
        self._plotter_error: Exception | None = None
        self._bolt_actor: Any | None = None
        self._label_actor: Any | None = None
        self._grid_actor: Any | None = None
        self._hover_actor: Any | None = None
        self._hover_picker: Any | None = None
        self._hover_callback: Any | None = None
        self._hover_observer_id: Any | None = None
        self._reference_actors_by_part_id: dict[str, list[Any]] = {}
        self._reference_parts: dict[str, ReferencePart] = {}
        self._reference_mesh_assets: dict[str, list[ReferenceMeshAsset]] = {}
        self._selected_reference_part_ids: set[str] = set()
        self._axis_visibility = {"x": True, "y": True, "z": True}
        self._bolt_node_size = BOLT_NODE_SIZE_DEFAULT
        self._results: list[BoltCalculationResult] = []
        self._scalar_name = "Margin"
        self._last_result_geometry_key: tuple[tuple[str, float | None, float | None, float | None], ...] = ()
        self._last_draw_reset_camera: bool | None = None
        self._active_scalar_bar_title: str | None = None
        self._last_scalar_bar_args: dict[str, Any] = {}
        self._resize_refresh_timer = QTimer(self)
        self._resize_refresh_timer.setSingleShot(True)
        self._resize_refresh_timer.setInterval(120)
        self._resize_refresh_timer.timeout.connect(self._refresh_results_after_resize)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        try:
            if _qt_platform_is_offscreen():
                raise RuntimeError("PyVistaQt scene disabled under QT_QPA_PLATFORM=offscreen.")
            from pyvistaqt import QtInteractor

            self._plotter = QtInteractor(self)
            layout.addWidget(self._plotter)
            self._plotter.add_axes()
            self._grid_actor = self._plotter.show_grid()
            self._apply_axis_visibility()
        except Exception as exc:  # pragma: no cover - depends on optional runtime.
            self._plotter_error = exc
            placeholder = QLabel(
                "Embedded 3D scene unavailable.\n"
                "Install pyvistaqt to view bolt nodes and reference geometry here."
            )
            placeholder.setObjectName("ScenePlaceholder")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(placeholder)

    @property
    def is_available(self) -> bool:
        return self._plotter is not None

    @property
    def plotter_error(self) -> Exception | None:
        return self._plotter_error

    @property
    def reference_part_ids(self) -> tuple[str, ...]:
        return tuple(self._reference_parts)

    @property
    def selected_reference_part_ids(self) -> tuple[str, ...]:
        return tuple(self._selected_reference_part_ids)

    @property
    def reference_parts(self) -> tuple[ReferencePart, ...]:
        return tuple(self._reference_parts.values())

    @property
    def axis_visibility(self) -> dict[str, bool]:
        return dict(self._axis_visibility)

    @property
    def axis_font_sizes(self) -> dict[str, int]:
        title_size, label_size = self._axis_font_sizes()
        return {"title": title_size, "label": label_size}

    @property
    def last_scalar_bar_args(self) -> dict[str, Any]:
        return dict(self._last_scalar_bar_args)

    @property
    def last_draw_reset_camera(self) -> bool | None:
        return self._last_draw_reset_camera

    @property
    def bolt_node_size(self) -> int:
        return self._bolt_node_size

    def set_results(
        self,
        results: list[BoltCalculationResult],
        scalar_name: str,
        reset_camera: bool | None = None,
    ) -> None:
        """Display bolt result nodes with the selected scalar contour."""

        next_results = list(results)
        geometry_key = _result_geometry_key(next_results)
        should_reset_camera = (
            bool(geometry_key and geometry_key != self._last_result_geometry_key)
            if reset_camera is None
            else bool(reset_camera)
        )
        self._results = next_results
        self._scalar_name = scalar_name
        self._last_result_geometry_key = geometry_key
        self._draw_results(reset_camera=should_reset_camera)

    def _draw_results(self, reset_camera: bool) -> None:
        self._last_draw_reset_camera = bool(reset_camera)
        self._clear_bolt_actors()
        if (
            self._plotter is None
            or not self._results
            or not results_have_coordinates(self._results)
        ):
            self._render()
            return

        pv = _import_pyvista()
        scalar_values = scalar_values_for_results(self._results, self._scalar_name)
        points = [
            (result.load.x_mm, result.load.y_mm, result.load.z_mm)
            for result in self._results
        ]
        cloud = pv.PolyData(points)
        for name, getter in SCALAR_CHOICES.items():
            cloud[name] = [getter(result) for result in self._results]
        scalar_bar_args = self._scalar_bar_args(self._scalar_name)
        self._bolt_actor = self._plotter.add_mesh(
            cloud,
            name="bolt_result_nodes",
            scalars=self._scalar_name,
            render_points_as_spheres=True,
            point_size=self._bolt_node_size,
            cmap=VISUALIZATION_CMAP,
            clim=local_scalar_range(scalar_values),
            scalar_bar_args=scalar_bar_args,
        )
        self._active_scalar_bar_title = self._scalar_name
        self._last_scalar_bar_args = scalar_bar_args
        self._label_actor = self._plotter.add_point_labels(
            points,
            [result.load.name for result in self._results],
            name="bolt_result_labels",
            font_size=self._point_label_font_size(),
        )
        self._install_hover_overlay(
            node_actor=self._bolt_actor,
            node_names=[result.load.name for result in self._results],
            scalar_values=scalar_values,
        )
        if reset_camera:
            self._plotter.reset_camera()
        self._render()

    def add_reference_part(
        self,
        part: ReferencePart,
        mesh_assets: list[ReferenceMeshAsset],
    ) -> None:
        self._reference_parts[part.id] = part
        self._reference_mesh_assets[part.id] = list(mesh_assets)
        self._remove_reference_actors(part.id)
        if self._plotter is not None:
            self._display_reference_part(part, mesh_assets)
        self._render()

    def remove_reference_part(self, part_id: str) -> None:
        self._remove_reference_actors(part_id)
        self._reference_parts.pop(part_id, None)
        self._reference_mesh_assets.pop(part_id, None)
        self._selected_reference_part_ids.discard(part_id)
        self._render()

    def rename_reference_part(self, part_id: str, name: str) -> None:
        part = self._reference_parts[part_id]
        part.rename(name)

    def set_reference_visibility(self, part_id: str, visible: bool) -> None:
        part = self._reference_parts[part_id]
        part.display_state.visible = bool(visible)
        for actor in self._reference_actors_by_part_id.get(part_id, []):
            _set_actor_visibility(actor, part.display_state.visible)
        self._render()

    def set_reference_opacity(self, part_id: str, opacity_0_to_1: float) -> None:
        part = self._reference_parts[part_id]
        part.display_state.opacity = clamp_opacity(opacity_0_to_1)
        for actor in self._reference_actors_by_part_id.get(part_id, []):
            _set_actor_opacity(actor, part.display_state.opacity)
        self._render()

    def select_reference_parts(self, part_ids: Iterable[str]) -> None:
        selected = {part_id for part_id in part_ids if part_id in self._reference_parts}
        self._selected_reference_part_ids = selected
        for part_id, part in self._reference_parts.items():
            part.display_state.selected = part_id in selected
            for actor in self._reference_actors_by_part_id.get(part_id, []):
                _set_actor_selected(actor, part.display_state.selected)
        self._render()

    def set_axis_visibility(self, axis: str, visible: bool) -> None:
        key = str(axis).lower()
        if key not in self._axis_visibility:
            raise ValueError("Axis must be one of: x, y, z.")
        self._axis_visibility[key] = bool(visible)
        self._apply_axis_visibility()
        self._render()

    def set_bolt_node_size(self, point_size: int) -> None:
        self._bolt_node_size = _clamp_bolt_node_size(point_size)
        if self._results and results_have_coordinates(self._results):
            self._draw_results(reset_camera=False)

    def adjust_bolt_node_size(self, delta: int) -> int:
        self.set_bolt_node_size(self._bolt_node_size + int(delta))
        return self._bolt_node_size

    def clear_results(self) -> None:
        self.set_results([], self._scalar_name)

    def clear_references(self) -> None:
        for part_id in list(self._reference_parts):
            self.remove_reference_part(part_id)

    def _display_reference_part(
        self,
        part: ReferencePart,
        mesh_assets: list[ReferenceMeshAsset],
    ) -> None:
        if self._plotter is None:
            return
        actors: list[Any] = []
        for index, asset in enumerate(mesh_assets, start=1):
            actor = self._plotter.add_mesh(
                asset.mesh,
                name=f"reference_{part.id}_{index}",
                color=REFERENCE_COLOR,
                opacity=part.display_state.opacity,
                show_edges=part.display_state.selected,
                edge_color=SELECTED_EDGE_COLOR,
                smooth_shading=True,
            )
            _set_actor_visibility(actor, part.display_state.visible)
            _set_actor_selected(actor, part.display_state.selected)
            actors.append(actor)
        self._reference_actors_by_part_id[part.id] = actors

    def _clear_bolt_actors(self) -> None:
        if self._plotter is None:
            self._bolt_actor = None
            self._label_actor = None
            self._hover_actor = None
            self._hover_picker = None
            self._hover_callback = None
            self._hover_observer_id = None
            return
        self._clear_hover_overlay()
        if self._active_scalar_bar_title:
            try:
                self._plotter.remove_scalar_bar(self._active_scalar_bar_title)
            except Exception:
                pass
            self._active_scalar_bar_title = None
        for actor in (self._bolt_actor, self._label_actor):
            if actor is not None:
                try:
                    self._plotter.remove_actor(actor, render=False)
                except Exception:
                    pass
        self._bolt_actor = None
        self._label_actor = None

    def _install_hover_overlay(
        self,
        node_actor: Any,
        node_names: list[str],
        scalar_values: list[float],
    ) -> None:
        if self._plotter is None:
            return
        try:
            from vtkmodules.vtkRenderingCore import vtkPointPicker
        except ImportError:
            return

        hover_actor = self._plotter.add_text(
            hover_prompt_text(self._scalar_name),
            position="upper_left",
            font_size=self._hover_font_size(),
            color="black",
            name="bolt_hover_info",
        )
        picker = vtkPointPicker()
        picker.SetTolerance(0.025)
        picker.PickFromListOn()
        picker.AddPickList(node_actor)

        def set_hover_text(text: str) -> None:
            if hover_actor.get_text(HOVER_TEXT_POSITION) == text:
                return
            hover_actor.set_text(HOVER_TEXT_POSITION, text)
            self._render()

        def on_mouse_move(_interactor: Any, _event: str) -> None:
            event_position = self._plotter.iren.interactor.GetEventPosition()
            picker.Pick(event_position[0], event_position[1], 0, self._plotter.renderer)
            point_id = picker.GetPointId()
            if 0 <= point_id < len(node_names):
                set_hover_text(
                    format_hover_text(
                        node_names[point_id],
                        self._scalar_name,
                        scalar_values[point_id],
                    )
                )
                return
            set_hover_text(hover_prompt_text(self._scalar_name))

        self._hover_actor = hover_actor
        self._hover_picker = picker
        self._hover_callback = on_mouse_move
        self._hover_observer_id = self._plotter.iren.interactor.AddObserver(
            "MouseMoveEvent",
            on_mouse_move,
        )

    def _clear_hover_overlay(self) -> None:
        if self._plotter is not None and self._hover_observer_id is not None:
            try:
                self._plotter.iren.interactor.RemoveObserver(self._hover_observer_id)
            except Exception:
                pass
        if self._plotter is not None and self._hover_actor is not None:
            try:
                self._plotter.remove_actor(self._hover_actor, render=False)
            except Exception:
                pass
        self._hover_actor = None
        self._hover_picker = None
        self._hover_callback = None
        self._hover_observer_id = None

    def _remove_reference_actors(self, part_id: str) -> None:
        if self._plotter is not None:
            for actor in self._reference_actors_by_part_id.get(part_id, []):
                try:
                    self._plotter.remove_actor(actor, render=False)
                except Exception:
                    pass
        self._reference_actors_by_part_id.pop(part_id, None)

    def _render(self) -> None:
        if self._plotter is None:
            return
        try:
            self._plotter.render()
        except Exception:
            pass

    def _apply_axis_visibility(self) -> None:
        if self._grid_actor is None:
            return
        setters = {
            "x": "SetXAxisVisibility",
            "y": "SetYAxisVisibility",
            "z": "SetZAxisVisibility",
        }
        for axis, setter_name in setters.items():
            setter = getattr(self._grid_actor, setter_name, None)
            if setter is not None:
                setter(bool(self._axis_visibility[axis]))
        if hasattr(self._grid_actor, "SetVisibility"):
            self._grid_actor.SetVisibility(any(self._axis_visibility.values()))
        self._apply_axis_font_sizes()

    def _axis_font_sizes(self) -> tuple[int, int]:
        short_edge = max(1, min(self.width(), self.height()))
        title_size = max(10, min(24, int(short_edge / 32)))
        label_size = max(8, min(20, int(short_edge / 42)))
        return title_size, label_size

    def _apply_axis_font_sizes(self) -> None:
        if self._grid_actor is None:
            return
        title_size, label_size = self._axis_font_sizes()
        for axis_index in range(3):
            title_property_getter = getattr(
                self._grid_actor,
                "GetTitleTextProperty",
                None,
            )
            label_property_getter = getattr(
                self._grid_actor,
                "GetLabelTextProperty",
                None,
            )
            _set_text_property_font_size(
                title_property_getter,
                axis_index,
                title_size,
            )
            _set_text_property_font_size(
                label_property_getter,
                axis_index,
                label_size,
            )

    def _scalar_bar_args(self, title: str) -> dict[str, Any]:
        short_edge = max(1, min(self.width(), self.height()))
        title_font_size = max(8, min(22, int(short_edge / 34)))
        label_font_size = max(7, min(18, int(short_edge / 44)))
        return {
            "title": title,
            "n_labels": 5,
            "fmt": "%.3g",
            "vertical": True,
            "position_x": 0.02,
            "position_y": 0.14,
            "width": 0.08,
            "height": 0.72,
            "title_font_size": title_font_size,
            "label_font_size": label_font_size,
            "shadow": False,
        }

    def _point_label_font_size(self) -> int:
        short_edge = max(1, min(self.width(), self.height()))
        return max(8, min(16, int(short_edge / 52)))

    def _hover_font_size(self) -> int:
        short_edge = max(1, min(self.width(), self.height()))
        return max(9, min(18, int(short_edge / 46)))

    def _refresh_results_after_resize(self) -> None:
        if self._results and results_have_coordinates(self._results):
            self._draw_results(reset_camera=False)

    def resizeEvent(self, event: Any) -> None:  # noqa: N802 - Qt override.
        super().resizeEvent(event)
        self._apply_axis_font_sizes()
        if self._plotter is not None and self._results:
            self._resize_refresh_timer.start()


def _qt_platform_is_offscreen() -> bool:
    return os.environ.get("QT_QPA_PLATFORM", "").casefold() == "offscreen"


def _import_pyvista() -> Any:
    try:
        import pyvista as pv
    except ImportError as exc:
        raise RuntimeError("PyVista is required for the bolt reference scene.") from exc
    return pv


def _result_geometry_key(
    results: list[BoltCalculationResult],
) -> tuple[tuple[str, float | None, float | None, float | None], ...]:
    return tuple(
        (
            result.load.name,
            result.load.x_mm,
            result.load.y_mm,
            result.load.z_mm,
        )
        for result in results
    )


def _clamp_bolt_node_size(point_size: int) -> int:
    return max(BOLT_NODE_SIZE_MIN, min(BOLT_NODE_SIZE_MAX, int(point_size)))


def _set_actor_visibility(actor: Any, visible: bool) -> None:
    try:
        actor.SetVisibility(bool(visible))
    except Exception:
        try:
            actor.visibility = bool(visible)
        except Exception:
            pass


def _set_actor_opacity(actor: Any, opacity: float) -> None:
    try:
        actor.GetProperty().SetOpacity(clamp_opacity(opacity))
    except Exception:
        try:
            actor.prop.opacity = clamp_opacity(opacity)
        except Exception:
            pass


def _set_actor_selected(actor: Any, selected: bool) -> None:
    try:
        prop = actor.GetProperty()
        if selected:
            prop.EdgeVisibilityOn()
            prop.SetEdgeColor(0.94, 0.71, 0.16)
            prop.SetLineWidth(2.0)
        else:
            prop.EdgeVisibilityOff()
    except Exception:
        pass


def _set_text_property_font_size(
    property_getter: Any,
    axis_index: int,
    font_size: int,
) -> None:
    if property_getter is None:
        return
    try:
        text_property = property_getter(axis_index)
        text_property.SetFontSize(int(font_size))
    except Exception:
        pass
