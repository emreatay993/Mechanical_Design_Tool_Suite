from __future__ import annotations

import unittest

from bolt_calculation_tool.calculations import calculate_bolt_group, resolve_constants
from bolt_calculation_tool.sample_data import example_scenario_loads
from bolt_calculation_tool.visualization import SCALAR_CHOICES, results_have_coordinates


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


if __name__ == "__main__":
    unittest.main()
