from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QCheckBox, QLabel, QTabWidget, QWidget

from mechanical_design_tool_suite.cad_tolerance_gui import (
    NeutralCadImportOptionsDialog,
    PlaceholderCadViewerWidget,
    create_cad_tolerance_window,
)
from mechanical_design_tool_suite.cad_tolerance_viewmodels import (
    DETAIL_COLUMNS,
    FIDELITY_GAP_NOTES,
    GUIDED_STACKUP_STEPS,
    NON_1D_WARNING_TEXT,
    SUMMARY_COLUMNS,
    CadStackupDetailTableModel,
    CadStackupSummaryTableModel,
    CadToleranceWorkspaceViewModel,
)
from mechanical_design_tool_suite.cad_viewer_api import CadCameraState, SnapshotRequest
from mechanical_design_tool_suite.cad_tolerance_models import Snapshot


class FakeViewer(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.displayed_session = None
        self.snapshot_requests: list[SnapshotRequest] = []

    def display_document(self, session, display_kinds=None) -> None:
        self.displayed_session = session

    def clear(self) -> None:
        self.displayed_session = None

    def fit_all(self) -> None:
        return

    def pan(self, dx: int, dy: int) -> None:
        return

    def zoom(self, factor: float) -> None:
        return

    def set_standard_view(self, view) -> None:
        return

    def set_selection_modes(self, modes) -> None:
        return

    def highlight(self, shape_ref, role) -> None:
        return

    def clear_highlights(self, roles=None) -> None:
        return

    def camera_state(self) -> CadCameraState:
        return CadCameraState(view_name="fake")

    def capture_snapshot(self, request: SnapshotRequest) -> Snapshot:
        self.snapshot_requests.append(request)
        Path(request.output_path).write_bytes(b"fake")
        return Snapshot(image_path=str(request.output_path), camera=self.camera_state().to_dict())


class CadToleranceViewModelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_summary_model_exposes_required_columns_and_visual_rows(self) -> None:
        workspace = CadToleranceWorkspaceViewModel.demo()
        model = CadStackupSummaryTableModel(workspace.summary_rows)

        columns = [
            model.headerData(index, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
            for index in range(model.columnCount())
        ]

        self.assertEqual(tuple(columns), SUMMARY_COLUMNS)
        self.assertEqual(model.rowCount(), 9)
        self.assertEqual(model.data(model.index(0, 1)), "flush left")
        self.assertEqual(model.data(model.index(0, 0)), "X")
        self.assertEqual(model.data(model.index(8, 0)), "!")
        self.assertIsNotNone(model.data(model.index(0, 0), Qt.ItemDataRole.DecorationRole))
        self.assertIsNotNone(model.data(model.index(0, 0), Qt.ItemDataRole.BackgroundRole))
        self.assertIn(NON_1D_WARNING_TEXT, model.data(model.index(8, 0), Qt.ItemDataRole.ToolTipRole))

    def test_detail_model_exposes_required_columns_shared_marker_and_gap_notes(self) -> None:
        workspace = CadToleranceWorkspaceViewModel.demo()
        model = CadStackupDetailTableModel(workspace.detail_rows("overall_height"))

        columns = [
            model.headerData(index, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
            for index in range(model.columnCount())
        ]

        self.assertEqual(tuple(columns), DETAIL_COLUMNS)
        self.assertGreater(model.rowCount(), 8)
        shared_row = model.index(1, 1)
        self.assertIsNotNone(model.data(shared_row, Qt.ItemDataRole.DecorationRole))
        self.assertIn("overall height", model.data(shared_row, Qt.ItemDataRole.ToolTipRole))
        self.assertTrue(any("GD&T" in note for note in FIDELITY_GAP_NOTES))


class CadToleranceGuiShellTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.viewer = FakeViewer()
        self.window = create_cad_tolerance_window(self.app, viewer=self.viewer)

    def tearDown(self) -> None:
        self.window.close()
        self.app.processEvents()

    def test_shell_has_dense_three_pane_layout_ribbon_tabs_and_tables(self) -> None:
        ribbon = self.window.findChild(QTabWidget, "RibbonTabs")
        self.assertIsNotNone(ribbon)
        self.assertEqual([ribbon.tabText(index) for index in range(ribbon.count())], ["Stackup", "Report", "Data"])

        self.assertIsNotNone(self.window.findChild(QWidget, "ModelBrowserPanel"))
        self.assertIsNotNone(self.window.findChild(QWidget, "CadViewportHost"))
        self.assertIsNotNone(self.window.findChild(QWidget, "SummaryTableView"))
        self.assertIsNotNone(self.window.findChild(QWidget, "DetailTableView"))
        self.assertEqual(self.window.summary_model.rowCount(), 9)
        self.assertEqual(self.window.detail_model.columnCount(), len(DETAIL_COLUMNS))

    def test_drilldown_updates_detail_title_and_contributions(self) -> None:
        self.window._open_summary_index(2)
        self.app.processEvents()

        self.assertEqual(self.window.detail_title.text(), "overall height details")
        self.assertGreater(self.window.detail_model.rowCount(), 0)
        self.assertIn("overall height", self.window.detail_contributions.title.text())

    def test_placeholder_viewer_isolated_behind_viewer_api(self) -> None:
        placeholder = PlaceholderCadViewerWidget(reason="test runtime")
        self.addCleanup(placeholder.close)
        placeholder.set_standard_view("front")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.png"
            snapshot = placeholder.capture_snapshot(SnapshotRequest(path))

        self.assertEqual(Path(snapshot.image_path).name, "snapshot.png")
        self.assertIn("view_name", snapshot.camera)

    def test_import_dialog_preserves_observed_options_and_select_structure(self) -> None:
        dialog = NeutralCadImportOptionsDialog(Path("fixture.step"))
        self.addCleanup(dialog.close)

        tabs = dialog.findChild(QTabWidget, "ImportOptionsTabs")
        labels = [box.text() for box in dialog.findChildren(QCheckBox)]

        self.assertEqual([tabs.tabText(index) for index in range(tabs.count())], ["Options", "Select"])
        for label in ("Solids", "Surfaces", "Meshes", "Wires", "Work Features", "Points"):
            self.assertIn(label, labels)
        self.assertEqual(dialog.import_settings()["units"], "From source")


if __name__ == "__main__":
    unittest.main()
