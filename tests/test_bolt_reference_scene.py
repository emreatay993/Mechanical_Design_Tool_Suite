from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pyvista as pv
from PyQt6.QtWidgets import QApplication

from mechanical_design_tool_suite.bolt_reference_scene import BoltReferenceSceneWidget
from mechanical_design_tool_suite.calculations import calculate_bolt_group, resolve_constants
from mechanical_design_tool_suite.reference_geometry import (
    ReferenceMeshAsset,
    ReferencePart,
    ReferenceGeometryFormat,
)
from mechanical_design_tool_suite.sample_data import example_scenario_loads


class BoltReferenceSceneWidgetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.widget = BoltReferenceSceneWidget()

    def tearDown(self) -> None:
        self.widget.close()
        self.app.processEvents()

    def test_reference_part_api_updates_state_without_plotter_requirement(self) -> None:
        part = ReferencePart(
            id="ref_1",
            name="Bracket",
            source_path="bracket.stl",
            file_format=ReferenceGeometryFormat.STL,
            mesh_count=1,
        )
        asset = ReferenceMeshAsset(
            part_id=part.id,
            name="Bracket",
            mesh=pv.Plane(i_size=10.0, j_size=5.0),
        )

        self.widget.add_reference_part(part, [asset])
        self.widget.select_reference_parts([part.id])
        self.widget.set_reference_visibility(part.id, False)
        self.widget.set_reference_opacity(part.id, 1.4)
        self.widget.rename_reference_part(part.id, "Renamed bracket")

        self.assertEqual(self.widget.reference_part_ids, ("ref_1",))
        self.assertEqual(self.widget.selected_reference_part_ids, ("ref_1",))
        self.assertFalse(part.display_state.visible)
        self.assertEqual(part.display_state.opacity, 1.0)
        self.assertEqual(part.name, "Renamed bracket")

        self.widget.remove_reference_part(part.id)
        self.assertEqual(self.widget.reference_part_ids, ())

    def test_set_results_accepts_bolt_coordinates_and_scalar_changes(self) -> None:
        results = calculate_bolt_group(
            example_scenario_loads(),
            resolve_constants(".2500-28", "MINOR"),
        )

        self.widget.set_results(results, "Margin")
        self.widget.set_results(results, "Fiber Stress")
        self.widget.clear_results()

        self.assertEqual(self.widget.reference_part_ids, ())

    def test_scalar_legend_is_left_vertical_and_scales_with_window_size(self) -> None:
        self.widget.resize(420, 300)
        small_args = self.widget._scalar_bar_args("Margin")
        small_label_size = self.widget._point_label_font_size()

        self.widget.resize(1400, 950)
        large_args = self.widget._scalar_bar_args("Margin")
        large_label_size = self.widget._point_label_font_size()

        self.assertTrue(small_args["vertical"])
        self.assertEqual(small_args["position_x"], 0.02)
        self.assertLess(small_args["position_x"], 0.1)
        self.assertEqual(small_args["height"], 0.72)
        self.assertGreater(large_args["title_font_size"], small_args["title_font_size"])
        self.assertGreaterEqual(
            large_args["label_font_size"],
            small_args["label_font_size"],
        )
        self.assertGreaterEqual(large_label_size, small_label_size)

    def test_axis_visibility_state_can_be_toggled_per_axis(self) -> None:
        self.widget.set_axis_visibility("x", False)
        self.widget.set_axis_visibility("z", False)

        self.assertFalse(self.widget.axis_visibility["x"])
        self.assertTrue(self.widget.axis_visibility["y"])
        self.assertFalse(self.widget.axis_visibility["z"])
        with self.assertRaises(ValueError):
            self.widget.set_axis_visibility("roll", True)

    def test_axis_label_fonts_scale_with_window_size(self) -> None:
        self.widget.resize(360, 260)
        small_sizes = self.widget.axis_font_sizes

        self.widget.resize(1500, 980)
        large_sizes = self.widget.axis_font_sizes

        self.assertGreater(large_sizes["title"], small_sizes["title"])
        self.assertGreater(large_sizes["label"], small_sizes["label"])


if __name__ == "__main__":
    unittest.main()
