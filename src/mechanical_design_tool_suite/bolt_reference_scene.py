"""Embedded bolt result and reference geometry scene widget."""

from __future__ import annotations

from typing import Any, Iterable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .calculations import BoltCalculationResult
from .reference_geometry import (
    ReferenceMeshAsset,
    ReferencePart,
    clamp_opacity,
)
from .visualization import (
    SCALAR_CHOICES,
    VISUALIZATION_CMAP,
    local_scalar_range,
    results_have_coordinates,
    scalar_values_for_results,
)


REFERENCE_COLOR = "#9fb4c8"
SELECTED_EDGE_COLOR = "#f0b429"


class BoltReferenceSceneWidget(QWidget):
    """Unified bolt result and visual reference geometry scene."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._plotter: Any | None = None
        self._plotter_error: Exception | None = None
        self._bolt_actor: Any | None = None
        self._label_actor: Any | None = None
        self._reference_actors_by_part_id: dict[str, list[Any]] = {}
        self._reference_parts: dict[str, ReferencePart] = {}
        self._reference_mesh_assets: dict[str, list[ReferenceMeshAsset]] = {}
        self._selected_reference_part_ids: set[str] = set()
        self._results: list[BoltCalculationResult] = []
        self._scalar_name = "Margin"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        try:
            from pyvistaqt import QtInteractor

            self._plotter = QtInteractor(self)
            layout.addWidget(self._plotter)
            self._plotter.add_axes()
            self._plotter.show_grid()
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

    def set_results(
        self,
        results: list[BoltCalculationResult],
        scalar_name: str,
    ) -> None:
        """Display bolt result nodes with the selected scalar contour."""

        self._results = list(results)
        self._scalar_name = scalar_name
        self._clear_bolt_actors()
        if (
            self._plotter is None
            or not self._results
            or not results_have_coordinates(self._results)
        ):
            self._render()
            return

        pv = _import_pyvista()
        scalar_values = scalar_values_for_results(self._results, scalar_name)
        points = [
            (result.load.x_mm, result.load.y_mm, result.load.z_mm)
            for result in self._results
        ]
        cloud = pv.PolyData(points)
        for name, getter in SCALAR_CHOICES.items():
            cloud[name] = [getter(result) for result in self._results]
        self._bolt_actor = self._plotter.add_mesh(
            cloud,
            name="bolt_result_nodes",
            scalars=scalar_name,
            render_points_as_spheres=True,
            point_size=22,
            cmap=VISUALIZATION_CMAP,
            clim=local_scalar_range(scalar_values),
            scalar_bar_args={
                "title": scalar_name,
                "n_labels": 5,
                "fmt": "%.3g",
            },
        )
        self._label_actor = self._plotter.add_point_labels(
            points,
            [result.load.name for result in self._results],
            name="bolt_result_labels",
            font_size=11,
        )
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
            return
        for actor in (self._bolt_actor, self._label_actor):
            if actor is not None:
                try:
                    self._plotter.remove_actor(actor, render=False)
                except Exception:
                    pass
        self._bolt_actor = None
        self._label_actor = None

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


def _import_pyvista() -> Any:
    try:
        import pyvista as pv
    except ImportError as exc:
        raise RuntimeError("PyVista is required for the bolt reference scene.") from exc
    return pv


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
