from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import tempfile
import unittest


if "QT_QPA_PLATFORM" not in os.environ and importlib.util.find_spec("OCC") is None:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QCheckBox, QLabel, QTabWidget, QWidget

from mechanical_design_tool_suite.cad_tolerance_gui import (
    NeutralCadImportOptionsDialog,
    PlaceholderCadViewerWidget,
    create_cad_tolerance_window,
)
from mechanical_design_tool_suite.cad_tolerance_project_io import load_project, save_project
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
from mechanical_design_tool_suite.cad_tolerance_models import (
    CadDocument,
    CadFileFormat,
    Snapshot,
)


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "cad_1d_tolerance"
    / "sample_cad_1d_project.tolproj"
)


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


class FakeGeometrySession:
    def __init__(self) -> None:
        self.imported_paths: list[Path] = []
        self.imported_settings = []
        self.selection_filters = []

    def import_file(self, path, settings=None) -> CadDocument:
        resolved = Path(path)
        if not resolved.exists():
            raise FileNotFoundError(path)
        self.imported_paths.append(resolved)
        self.imported_settings.append(settings)
        return CadDocument(
            source_path=str(resolved),
            file_format=CadFileFormat.STEP,
            display_name=resolved.name,
        )

    def set_selection_filter(self, kinds) -> None:
        self.selection_filters.append(kinds)


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

    def test_project_load_rehydrates_existing_fixture_cad_source(self) -> None:
        geometry = FakeGeometrySession()
        self.window.geometry_session = geometry

        self.window.load_project_file(FIXTURE_PATH)
        self.app.processEvents()

        self.assertEqual(self.window.summary_model.rowCount(), 1)
        self.assertEqual(
            geometry.imported_paths,
            [(FIXTURE_PATH.parent / "neutral_step_two_part_loop.step").resolve()],
        )
        self.assertIs(self.viewer.displayed_session, geometry)
        self.assertIn("Reloaded CAD source", self.window.statusBar().currentMessage())

    def test_project_load_keeps_data_visible_when_cad_source_is_missing(self) -> None:
        project = load_project(FIXTURE_PATH)
        project.cad_documents[0].source_path = "missing_assets/cad/missing.step"
        geometry = FakeGeometrySession()
        self.window.geometry_session = geometry

        with tempfile.TemporaryDirectory() as directory:
            project_path = save_project(project, Path(directory) / "missing_source.tolproj")
            self.window.load_project_file(project_path)

        self.assertEqual(self.window.summary_model.rowCount(), 1)
        self.assertEqual(geometry.imported_paths, [])
        self.assertIsNone(self.viewer.displayed_session)
        self.assertIn(
            "CAD source not found: missing.step",
            self.window.statusBar().currentMessage(),
        )

    def test_project_load_resolves_project_local_cad_assets(self) -> None:
        project = load_project(FIXTURE_PATH)
        geometry = FakeGeometrySession()
        self.window.geometry_session = geometry

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cad_asset = root / "caster_study_assets" / "cad" / "local.step"
            cad_asset.parent.mkdir(parents=True)
            cad_asset.write_bytes((FIXTURE_PATH.parent / "neutral_step_two_part_loop.step").read_bytes())
            project.cad_documents[0].source_path = "cad/local.step"
            project_path = save_project(project, root / "caster_study.tolproj")
            self.window.load_project_file(project_path)

        self.assertEqual(geometry.imported_paths, [cad_asset.resolve()])
        self.assertIn("Reloaded CAD source: local.step", self.window.cad_source_status_messages)

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
