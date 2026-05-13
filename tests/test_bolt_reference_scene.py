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


if __name__ == "__main__":
    unittest.main()
