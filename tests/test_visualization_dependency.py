from __future__ import annotations

import sys
import unittest
from types import SimpleNamespace
from unittest import mock

import pyvista as pv

from bolt_calculation_tool.calculations import calculate_bolt_group, resolve_constants
from bolt_calculation_tool.sample_data import example_scenario_loads
from bolt_calculation_tool.visualization import (
    SCALAR_CHOICES,
    VISUALIZATION_CMAP,
    format_hover_text,
    hover_prompt_text,
    local_scalar_range,
    open_pyvista_plot,
    results_have_coordinates,
    scalar_values_for_results,
)


class VisualizationDependencyTest(unittest.TestCase):
    def test_pyvista_import_and_node_cloud_data(self) -> None:
        results = calculate_bolt_group(
            example_scenario_loads(),
            resolve_constants(".2500-28", "MINOR"),
        )
        points = [
            (result.load.x_mm, result.load.y_mm, result.load.z_mm)
            for result in results
        ]
        cloud = pv.PolyData(points)
        cloud["Margin"] = [SCALAR_CHOICES["Margin"](result) for result in results]

        self.assertTrue(results_have_coordinates(results))
        self.assertEqual(cloud.n_points, 9)
        self.assertIn("Margin", cloud.point_data)

    def test_margin_visualization_uses_local_range_and_jet(self) -> None:
        results = calculate_bolt_group(
            example_scenario_loads(),
            resolve_constants(".2500-28", "MINOR"),
        )

        margin_values = scalar_values_for_results(results, "Margin")
        local_range = local_scalar_range(margin_values)

        self.assertEqual(VISUALIZATION_CMAP, "jet")
        self.assertAlmostEqual(local_range[0], min(margin_values))
        self.assertAlmostEqual(local_range[1], max(margin_values))
        self.assertNotEqual(local_range, (0.0, 1.0))

    def test_hover_text_format(self) -> None:
        self.assertEqual(
            format_hover_text("BOLT01", "LCF sigma_alt", 77.44321),
            "BOLT01\nLCF sigma_alt: 77.4432",
        )
        self.assertEqual(
            hover_prompt_text("Margin"),
            "Hover over a bolt node\nMargin: -",
        )

    def test_plot_call_uses_local_clim_jet_and_hover_overlay(self) -> None:
        results = calculate_bolt_group(
            example_scenario_loads(),
            resolve_constants(".2500-28", "MINOR"),
        )
        captured: dict[str, object] = {}

        class FakeInteractor:
            def __init__(self) -> None:
                self.observers: list[tuple[str, object]] = []

            def AddObserver(self, event_name: str, callback: object) -> None:
                self.observers.append((event_name, callback))
                captured["observers"] = self.observers

            def GetEventPosition(self) -> tuple[int, int]:
                return (0, 0)

        class FakeIren:
            def __init__(self) -> None:
                self.interactor = FakeInteractor()

        class FakePolyData:
            def __init__(self, points: list[tuple[float, float, float]]) -> None:
                self.points = points
                self.point_data: dict[str, list[float]] = {}

            def __setitem__(self, key: str, values: list[float]) -> None:
                self.point_data[key] = values

        class FakeHoverActor:
            def __init__(self, text: str) -> None:
                self.text = {2: text}

            def get_text(self, position: int) -> str:
                return self.text[position]

            def set_text(self, position: int, text: str) -> None:
                self.text[position] = text
                captured["hover_text"] = text

        class FakePlotter:
            def __init__(self, title: str) -> None:
                captured["title"] = title
                self.iren = FakeIren()
                self.renderer = object()

            def add_mesh(self, cloud: FakePolyData, **kwargs: object) -> None:
                captured["cloud"] = cloud
                captured["mesh_kwargs"] = kwargs
                return "node_actor"

            def add_text(self, text: str, **kwargs: object) -> FakeHoverActor:
                captured["hover_initial_text"] = text
                captured["hover_kwargs"] = kwargs
                return FakeHoverActor(text)

            def add_point_labels(self, *_args: object, **_kwargs: object) -> None:
                pass

            def render(self) -> None:
                captured["rendered"] = True

            def add_axes(self) -> None:
                pass

            def show_grid(self) -> None:
                pass

            def show(self) -> None:
                captured["shown"] = True

        fake_pyvista = SimpleNamespace(PolyData=FakePolyData, Plotter=FakePlotter)
        fake_picker = mock.Mock()
        fake_picker.GetPointId.return_value = 0
        fake_picker_class = mock.Mock(return_value=fake_picker)
        with (
            mock.patch.dict(sys.modules, {"pyvista": fake_pyvista}),
            mock.patch(
                "vtkmodules.vtkRenderingCore.vtkPointPicker",
                fake_picker_class,
            ),
        ):
            open_pyvista_plot(results, "Margin")

        margin_values = scalar_values_for_results(results, "Margin")
        mesh_kwargs = captured["mesh_kwargs"]
        observer_event, observer_callback = captured["observers"][0]

        self.assertEqual(mesh_kwargs["cmap"], VISUALIZATION_CMAP)
        self.assertEqual(mesh_kwargs["clim"], local_scalar_range(margin_values))
        self.assertEqual(mesh_kwargs["scalar_bar_args"]["title"], "Margin")
        self.assertEqual(mesh_kwargs["scalar_bar_args"]["n_labels"], 5)
        self.assertEqual(mesh_kwargs["scalar_bar_args"]["fmt"], "%.3g")
        self.assertEqual(captured["hover_initial_text"], hover_prompt_text("Margin"))
        self.assertEqual(captured["hover_kwargs"]["position"], "upper_left")
        self.assertEqual(observer_event, "MouseMoveEvent")

        observer_callback(None, "MouseMoveEvent")
        self.assertEqual(captured["hover_text"], format_hover_text("BOLT01", "Margin", margin_values[0]))
        fake_picker.Pick.assert_called_once()
        fake_picker.AddPickList.assert_called_once_with("node_actor")
        self.assertTrue(captured["shown"])


if __name__ == "__main__":
    unittest.main()
