from __future__ import annotations

import sys
import unittest
from types import SimpleNamespace
from unittest import mock

from bolt_calculation_tool.calculations import calculate_bolt_group, resolve_constants
from bolt_calculation_tool.sample_data import example_scenario_loads
from bolt_calculation_tool.visualization import (
    SCALAR_CHOICES,
    VISUALIZATION_CMAP,
    local_scalar_range,
    open_pyvista_plot,
    results_have_coordinates,
    scalar_values_for_results,
)


class VisualizationDependencyTest(unittest.TestCase):
    def test_pyvista_import_and_node_cloud_data(self) -> None:
        import pyvista as pv

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

    def test_plot_call_uses_local_clim_and_jet_colormap(self) -> None:
        results = calculate_bolt_group(
            example_scenario_loads(),
            resolve_constants(".2500-28", "MINOR"),
        )
        captured: dict[str, object] = {}

        class FakePolyData:
            def __init__(self, points: list[tuple[float, float, float]]) -> None:
                self.points = points
                self.point_data: dict[str, list[float]] = {}

            def __setitem__(self, key: str, values: list[float]) -> None:
                self.point_data[key] = values

        class FakePlotter:
            def __init__(self, title: str) -> None:
                captured["title"] = title

            def add_mesh(self, cloud: FakePolyData, **kwargs: object) -> None:
                captured["cloud"] = cloud
                captured["mesh_kwargs"] = kwargs

            def add_point_labels(self, *_args: object, **_kwargs: object) -> None:
                pass

            def add_axes(self) -> None:
                pass

            def show_grid(self) -> None:
                pass

            def add_scalar_bar(self, **kwargs: object) -> None:
                captured["scalar_bar_kwargs"] = kwargs

            def show(self) -> None:
                captured["shown"] = True

        fake_pyvista = SimpleNamespace(PolyData=FakePolyData, Plotter=FakePlotter)
        with mock.patch.dict(sys.modules, {"pyvista": fake_pyvista}):
            open_pyvista_plot(results, "Margin")

        margin_values = scalar_values_for_results(results, "Margin")
        mesh_kwargs = captured["mesh_kwargs"]

        self.assertEqual(mesh_kwargs["cmap"], VISUALIZATION_CMAP)
        self.assertEqual(mesh_kwargs["clim"], local_scalar_range(margin_values))
        self.assertFalse(mesh_kwargs["show_scalar_bar"])
        self.assertEqual(captured["scalar_bar_kwargs"]["title"], "Margin")
        self.assertTrue(captured["shown"])


if __name__ == "__main__":
    unittest.main()
