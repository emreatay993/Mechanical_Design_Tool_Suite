from __future__ import annotations

import os
from pathlib import Path
import unittest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from mechanical_design_tool_suite.gui import BoltCalculationApp, _apply_fusion_light_style


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "cad_1d_tolerance"
STL_FIXTURE = FIXTURE_DIR / "simple_reference.stl"


class GuiStateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        _apply_fusion_light_style(cls.app)

    def setUp(self) -> None:
        self.window = BoltCalculationApp()

    def tearDown(self) -> None:
        self.window.close()
        self.app.processEvents()

    def test_example_opens_with_results_and_valid_actions(self) -> None:
        self.assertEqual(len(self.window.results), 9)
        self.assertEqual(self.window.results_table.rowCount(), 9)
        self.assertTrue(self.window.export_button.isEnabled())
        self.assertTrue(self.window.visualize_button.isEnabled())
        self.assertEqual(self.window.rows_label.text(), "Rows: 9")

    def test_editing_input_clears_stale_results(self) -> None:
        self.window.input_text.insertPlainText(" ")
        self.app.processEvents()

        self.assertEqual(self.window.results, [])
        self.assertEqual(self.window.results_table.rowCount(), 0)
        self.assertFalse(self.window.export_button.isEnabled())
        self.assertFalse(self.window.visualize_button.isEnabled())
        self.assertEqual(self.window.rows_label.text(), "Rows: -")

    def test_visualization_disabled_without_coordinates(self) -> None:
        self.window._replace_input(
            "\n".join(
                [
                    "NodeID,FX[N],FY[N],FZ[N],MX[N*mm],MY[N*mm],MZ[N*mm]",
                    "B1,1,2,10856,182,-140,4",
                ]
            )
        )
        self.window._calculate()

        self.assertEqual(len(self.window.results), 1)
        self.assertTrue(self.window.export_button.isEnabled())
        self.assertFalse(self.window.visualize_button.isEnabled())
        self.assertEqual(self.window.visualization_label.text(), "Visualization: no coordinates")

    def test_reference_part_tree_controls_update_scene_state(self) -> None:
        part = self.window._import_reference_part(STL_FIXTURE)
        self.app.processEvents()

        self.assertEqual(self.window.reference_tree.topLevelItemCount(), 1)
        self.assertEqual(self.window.scene_widget.reference_part_ids, (part.id,))
        self.assertTrue(self.window.delete_reference_button.isEnabled())
        self.assertTrue(self.window.rename_reference_button.isEnabled())

        self.window.reference_opacity_slider.setValue(62)
        self.app.processEvents()
        self.assertAlmostEqual(part.display_state.opacity, 0.62)

        item = self.window.reference_tree.topLevelItem(0)
        item.setCheckState(0, Qt.CheckState.Unchecked)
        self.app.processEvents()
        self.assertFalse(part.display_state.visible)

        self.window._rename_reference_part(part.id, "Renamed reference")
        self.assertEqual(part.name, "Renamed reference")
        self.assertEqual(item.text(0), "Renamed reference")

        self.window._delete_selected_reference_parts()
        self.assertEqual(self.window.reference_tree.topLevelItemCount(), 0)
        self.assertEqual(self.window.scene_widget.reference_part_ids, ())

    def test_scene_can_be_windowed_fullscreened_and_restored(self) -> None:
        self.assertIsNone(self.window.scene_window)

        self.window._open_scene_windowed()
        self.app.processEvents()
        self.assertIsNotNone(self.window.scene_window)
        self.assertIs(self.window.scene_widget.parent(), self.window.scene_window)

        self.window._open_scene_fullscreen()
        self.app.processEvents()
        self.assertTrue(self.window.scene_window.isFullScreen())

        self.window._restore_scene_to_tab()
        self.app.processEvents()
        self.assertIsNone(self.window.scene_window)
        self.assertIs(self.window.scene_widget.parent(), self.window.scene_host)


if __name__ == "__main__":
    unittest.main()
