from __future__ import annotations

import os
import unittest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from bolt_calculation_tool.gui import BoltCalculationApp, _apply_fusion_light_style


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


if __name__ == "__main__":
    unittest.main()
