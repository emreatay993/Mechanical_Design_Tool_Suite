from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import tempfile
import unittest


if "QT_QPA_PLATFORM" not in os.environ and importlib.util.find_spec("OCC") is None:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from mechanical_design_tool_suite.cad_tolerance_gui import (
    PlaceholderCadViewerWidget,
    create_cad_tolerance_window,
)
from mechanical_design_tool_suite.cad_tolerance_models import (
    GeometricControlType,
    ToleranceType,
)
from mechanical_design_tool_suite.cad_tolerance_project_io import load_project, save_project


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "cad_1d_tolerance"
    / "sample_cad_1d_project.tolproj"
)


class CadToleranceEditingPersistenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.viewer = PlaceholderCadViewerWidget(reason="editing test")
        self.window = create_cad_tolerance_window(self.app, viewer=self.viewer)
        self.window.load_project_file(FIXTURE_PATH)
        self.window._open_summary_index(0)

    def tearDown(self) -> None:
        self.window.close()
        self.viewer.close()
        self.app.processEvents()

    def test_table_and_manual_gdt_edits_survive_tolproj_round_trip(self) -> None:
        row = _find_model_row(self.window.detail_model, "Bracket to bushing face")

        self.assertTrue(
            self.window.detail_model.setData(
                self.window.detail_model.index(row, 0),
                "Dimension2",
                Qt.ItemDataRole.EditRole,
            )
        )
        row = _find_model_row(self.window.detail_model, "Dimension2")
        self.assertTrue(
            self.window.detail_model.setData(
                self.window.detail_model.index(row, 2),
                "58.000",
                Qt.ItemDataRole.EditRole,
            )
        )
        self.assertTrue(
            self.window.detail_model.setData(
                self.window.detail_model.index(row, 3),
                "position 0.15 A",
                Qt.ItemDataRole.EditRole,
            )
        )
        self.assertTrue(
            self.window.detail_model.setData(
                self.window.detail_model.index(row, 4),
                "A",
                Qt.ItemDataRole.EditRole,
            )
        )
        self.window.add_geometric_tolerance(
            "Bushing ID axis",
            GeometricControlType.PROFILE,
            0.5,
            ["A"],
        )

        with tempfile.TemporaryDirectory() as directory:
            saved_path = save_project(self.window.project, Path(directory) / "edited.tolproj")
            loaded = load_project(saved_path)

        edited = loaded.stackups[0].contributors[0]
        self.assertEqual(edited.name, "Dimension2")
        self.assertAlmostEqual(edited.nominal, 58.0)
        self.assertEqual(edited.tolerance_type, ToleranceType.GEOMETRIC)
        self.assertEqual(edited.geometric_tolerance.control_type, GeometricControlType.POSITION)
        self.assertEqual(edited.geometric_tolerance.datum_references, ["A"])
        self.assertAlmostEqual(edited.tolerance_plus, 0.075)

        profile = loaded.stackups[0].contributors[-1]
        self.assertEqual(profile.tolerance_type, ToleranceType.GEOMETRIC)
        self.assertEqual(profile.geometric_tolerance.control_type, GeometricControlType.PROFILE)
        self.assertEqual(profile.datum_references, ["A"])
        self.assertAlmostEqual(profile.tolerance_plus, 0.25)


def _find_model_row(model, name: str) -> int:
    for row in range(model.rowCount()):
        if model.data(model.index(row, 0)) == name:
            return row
    raise AssertionError(f"Detail row not found: {name}")


if __name__ == "__main__":
    unittest.main()
