from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import tempfile
import unittest


if "QT_QPA_PLATFORM" not in os.environ and importlib.util.find_spec("OCC") is None:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QCheckBox, QDialogButtonBox, QLabel, QSplitter, QTabWidget, QWidget

from mechanical_design_tool_suite.cad_tolerance_gui import (
    AddGeometricToleranceDialog,
    ContributionBarMeter,
    NeutralCadImportOptionsDialog,
    PlaceholderCadViewerWidget,
    ResultPlotWidget,
    create_cad_tolerance_window,
)
from mechanical_design_tool_suite.cad_geometry_api import cad_source_topology_hash
from mechanical_design_tool_suite.cad_tolerance_project_io import (
    load_project,
    project_asset_dir,
    save_project,
)
from mechanical_design_tool_suite.cad_tolerance_viewmodels import (
    DETAIL_COLUMNS,
    DETAIL_TOLERANCE_TYPE_ROLE,
    FIDELITY_GAP_NOTES,
    GUIDED_STACKUP_STEPS,
    NON_1D_WARNING_TEXT,
    SUMMARY_COLUMNS,
    CadStackupDetailTableModel,
    CadStackupSummaryTableModel,
    CadToleranceWorkspaceViewModel,
)
from mechanical_design_tool_suite.cad_viewer_api import (
    CadCameraState,
    SnapshotRequest,
    ViewerAnnotation,
    ViewerAnnotationRole,
)
from mechanical_design_tool_suite.cad_tolerance_models import (
    CadDocument,
    CadFileFormat,
    CadSourceStatus,
    GeometricControlType,
    ShapeKind,
    ShapeReference,
    Snapshot,
    ToleranceType,
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


class NativeAnnotationFakeViewer(FakeViewer):
    uses_native_annotations = True


class FakeGeometrySession:
    def __init__(
        self,
        *,
        file_hash: str = "sha256:0123456789abcdef",
        shape_area: float = 42.0,
    ) -> None:
        self.imported_paths: list[Path] = []
        self.imported_settings = []
        self.selection_filters = []
        self.file_hash = file_hash
        self.shapes = [
            ShapeReference(
                id="shape_fake_face",
                assembly_path=["Caster Assembly", "Bracket"],
                shape_type=ShapeKind.FACE,
                kernel_label="cad_doc_1:Caster Assembly/Bracket:face:1",
                geometric_signature={"area": shape_area},
                fallback_display_name="Bracket face",
            )
        ]

    def import_file(self, path, settings=None) -> CadDocument:
        resolved = Path(path)
        if not resolved.exists():
            raise FileNotFoundError(path)
        self.imported_paths.append(resolved)
        self.imported_settings.append(settings)
        return CadDocument(
            source_path=str(resolved),
            file_hash=self.file_hash,
            source_topology_hash=cad_source_topology_hash(self.shapes),
            file_format=CadFileFormat.STEP,
            display_name=resolved.name,
        )

    def shape_references(self, kinds=None):
        return list(self.shapes)

    def feature_references(self, kinds=None):
        return []

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
        self.assertEqual(model.data(model.index(0, 0)), "")
        self.assertEqual(model.data(model.index(8, 0)), "")
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

    def test_project_detail_model_marks_contributor_cells_editable(self) -> None:
        workspace = CadToleranceWorkspaceViewModel.from_project(load_project(FIXTURE_PATH))
        model = CadStackupDetailTableModel(workspace.detail_rows())
        dimension_row = _find_model_row(model, "Bracket to bushing face")

        self.assertTrue(
            model.flags(model.index(dimension_row, 3)) & Qt.ItemFlag.ItemIsEditable
        )
        self.assertEqual(
            model.data(model.index(dimension_row, 3), DETAIL_TOLERANCE_TYPE_ROLE),
            ToleranceType.LIMITS.value,
        )
        self.assertIn(
            "Shared dimension affects",
            model.data(model.index(dimension_row, 1), Qt.ItemDataRole.ToolTipRole),
        )


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
        self.assertEqual(
            [ribbon.tabText(index) for index in range(ribbon.count())],
            ["File", "Tolerance Stackup", "View"],
        )
        self.assertEqual(ribbon.currentIndex(), 1)
        for group_name in ("RibbonGroupStackup", "RibbonGroupReport", "RibbonGroupData"):
            self.assertIsNotNone(self.window.findChild(QWidget, group_name))

        self.assertIsNotNone(self.window.findChild(QWidget, "ModelBrowserPanel"))
        self.assertIsNotNone(self.window.findChild(QWidget, "BrowserFilterButton"))
        self.assertIsNotNone(self.window.findChild(QWidget, "BrowserAssemblyViewButton"))
        self.assertIsNotNone(self.window.findChild(QWidget, "BrowserFindButton"))
        splitter = self.window.findChild(QSplitter, "MainWorkspaceSplitter")
        self.assertIsNotNone(splitter)
        self.assertEqual(splitter.count(), 3)
        self.assertIsNotNone(self.window.findChild(QWidget, "CadViewportHost"))
        self.assertIsNotNone(self.window.findChild(QWidget, "ViewCubeWidget"))
        self.assertIsNotNone(self.window.findChild(QWidget, "AxisTriadWidget"))
        self.assertIsNotNone(self.window.findChild(QWidget, "ViewportNavigationToolbar"))
        guided_toolbar = self.window.findChild(QWidget, "GuidedStackupToolbar")
        self.assertIsNotNone(guided_toolbar)
        self.assertTrue(guided_toolbar.isHidden())
        self.assertIsNotNone(self.window.findChild(QWidget, "SummaryTableView"))
        self.assertIsNotNone(self.window.findChild(QWidget, "DetailTableView"))
        self.assertIsNotNone(self.window.findChild(QLabel, "StatusStackupCountLabel"))
        self.assertIsNotNone(self.window.findChild(QLabel, "StatusSelectionCountLabel"))
        self.assertEqual(self.window.summary_model.rowCount(), 9)
        self.assertEqual(self.window.detail_model.columnCount(), len(DETAIL_COLUMNS))

    def test_guided_stackup_toolbar_is_only_visible_during_guided_workflow(self) -> None:
        guided_toolbar = self.window.findChild(QWidget, "GuidedStackupToolbar")
        self.assertIsNotNone(guided_toolbar)
        self.assertTrue(guided_toolbar.isHidden())

        self.window._start_new_stackup_workflow()
        self.app.processEvents()

        self.assertFalse(guided_toolbar.isHidden())

    def test_viewport_annotation_canvas_stays_transparent_over_native_viewer(self) -> None:
        canvas = self.window.viewport_host.annotation_canvas

        self.assertTrue(canvas.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents))
        self.assertTrue(canvas.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
        self.assertTrue(canvas.testAttribute(Qt.WidgetAttribute.WA_NoSystemBackground))
        self.assertFalse(canvas.autoFillBackground())

    def test_native_annotation_viewer_does_not_use_qt_annotation_labels(self) -> None:
        window = create_cad_tolerance_window(
            self.app,
            viewer=NativeAnnotationFakeViewer(),
        )
        self.addCleanup(window.close)

        window.viewport_host.set_annotations(
            (
                ViewerAnnotation(
                    id="native_annotation",
                    label="0.000",
                    role=ViewerAnnotationRole.STACKUP,
                ),
            )
        )
        self.app.processEvents()

        self.assertTrue(window.viewport_host.annotation_canvas.isHidden())
        self.assertEqual(
            window.viewport_host.findChildren(QLabel, "ViewerAnnotationLabel"),
            [],
        )

    def test_drilldown_updates_detail_title_and_contributions(self) -> None:
        self.window._open_summary_index(2)
        self.app.processEvents()

        self.assertEqual(self.window.detail_title.text(), "overall height details")
        self.assertGreater(self.window.detail_model.rowCount(), 0)
        self.assertIn("overall height", self.window.detail_contributions.title.text())
        self.assertGreaterEqual(len(self.window.detail_contributions.findChildren(ContributionBarMeter)), 8)

    def test_loaded_project_result_panel_shows_plot_and_warning_banner(self) -> None:
        self.window.load_project_file(FIXTURE_PATH)
        self.window._open_summary_index(0)
        self.app.processEvents()

        plot = self.window.result_panel.findChild(ResultPlotWidget, "ResultPlotWidget")
        warning = self.window.result_panel.findChild(QLabel, "NonOneDWarningLabel")

        self.assertIsNotNone(plot)
        self.assertIsNotNone(plot._projection)
        self.assertEqual(plot._projection.mode_label, "Statistical")
        self.assertIn("Actual: Cpk = 3.16", self.window.result_panel.metrics.text())
        self.assertFalse(self.window.result_panel.warning_row.isHidden())
        self.assertIn(NON_1D_WARNING_TEXT, warning.text())

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
        self.assertEqual(
            self.window.project.cad_documents[0].source_status,
            CadSourceStatus.PRESENT,
        )
        self.assertIn("Source: Present", self.window.cad_source_status_label.text())

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
        self.assertEqual(
            self.window.project.cad_documents[0].source_status,
            CadSourceStatus.MISSING,
        )
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
        self.assertEqual(
            self.window.project.cad_documents[0].source_status,
            CadSourceStatus.PROJECT_LOCAL_PACKAGE_ASSET,
        )
        self.assertIn("Using project-local CAD asset: local.step", self.window.cad_source_status_messages)

    def test_project_load_reports_relocated_cad_source_by_name(self) -> None:
        project = load_project(FIXTURE_PATH)
        geometry = FakeGeometrySession()
        self.window.geometry_session = geometry

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            relocated = root / "neutral_step_two_part_loop.step"
            relocated.write_bytes((FIXTURE_PATH.parent / "neutral_step_two_part_loop.step").read_bytes())
            project.cad_documents[0].source_path = "old_folder/neutral_step_two_part_loop.step"
            project_path = save_project(project, root / "caster_study.tolproj")
            self.window.load_project_file(project_path)

        self.assertEqual(geometry.imported_paths, [relocated.resolve()])
        self.assertEqual(
            self.window.project.cad_documents[0].source_status,
            CadSourceStatus.RELOCATED,
        )
        self.assertIn("CAD source relocated", self.window.statusBar().currentMessage())

    def test_project_load_reports_changed_hash_and_changed_topology(self) -> None:
        project = load_project(FIXTURE_PATH)
        baseline_shape = ShapeReference(
            id="shape_baseline",
            assembly_path=["Caster Assembly", "Bracket"],
            shape_type=ShapeKind.FACE,
            kernel_label="cad_doc_1:Caster Assembly/Bracket:face:1",
            geometric_signature={"area": 42.0},
            fallback_display_name="Bracket face",
        )
        project.cad_documents[0].source_topology_hash = cad_source_topology_hash([baseline_shape])

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cad_asset = project_asset_dir(root / "caster_study.tolproj") / "cad" / "local.step"
            cad_asset.parent.mkdir(parents=True)
            cad_asset.write_bytes((FIXTURE_PATH.parent / "neutral_step_two_part_loop.step").read_bytes())
            project.cad_documents[0].source_path = "caster_study_assets/cad/local.step"
            project_path = save_project(project, root / "caster_study.tolproj")

            self.window.geometry_session = FakeGeometrySession(file_hash="sha256:changed", shape_area=42.0)
            self.window.load_project_file(project_path)
            self.assertEqual(
                self.window.project.cad_documents[0].source_status,
                CadSourceStatus.CHANGED_HASH,
            )

            self.window.geometry_session = FakeGeometrySession(file_hash="sha256:changed", shape_area=84.0)
            self.window.load_project_file(project_path)

        self.assertEqual(
            self.window.project.cad_documents[0].source_status,
            CadSourceStatus.CHANGED_TOPOLOGY,
        )

    def test_reattach_cad_source_updates_document_and_status(self) -> None:
        project = load_project(FIXTURE_PATH)
        geometry = FakeGeometrySession(file_hash="sha256:reattached", shape_area=84.0)
        self.window.geometry_session = geometry

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_path = save_project(project, root / "caster_study.tolproj")
            source = root / "replacement.step"
            source.write_bytes((FIXTURE_PATH.parent / "neutral_step_two_part_loop.step").read_bytes())
            self.window.load_project_file(project_path)
            document = self.window.reattach_cad_source(source)

        self.assertEqual(document.source_path, "replacement.step")
        self.assertEqual(document.file_hash, "sha256:reattached")
        self.assertIn(document.source_status, {CadSourceStatus.PRESENT, CadSourceStatus.CHANGED_HASH})
        self.assertIs(self.viewer.displayed_session, geometry)

    def test_loaded_project_detail_table_edits_validate_recalculate_and_warn_on_shared(self) -> None:
        self.window.load_project_file(FIXTURE_PATH)
        self.window._open_summary_index(0)
        self.app.processEvents()
        row = _find_model_row(self.window.detail_model, "Bracket to bushing face")
        old_results = self.window.summary_model.data(self.window.summary_model.index(0, 5))

        accepted = self.window.detail_model.setData(
            self.window.detail_model.index(row, 3),
            "+/-0.05",
            Qt.ItemDataRole.EditRole,
        )
        self.app.processEvents()

        contributor = self.window.project.stackups[0].contributors[0]
        self.assertTrue(accepted)
        self.assertEqual(contributor.tolerance_type, ToleranceType.SYMMETRIC)
        self.assertAlmostEqual(contributor.tolerance_minus, 0.05)
        self.assertAlmostEqual(contributor.tolerance_plus, 0.05)
        self.assertNotEqual(
            self.window.summary_model.data(self.window.summary_model.index(0, 5)),
            old_results,
        )
        self.assertIn("Shared dimension affects", self.window.statusBar().currentMessage())

        rejected = self.window.detail_model.setData(
            self.window.detail_model.index(row, 2),
            "not numeric",
            Qt.ItemDataRole.EditRole,
        )
        self.app.processEvents()

        self.assertFalse(rejected)
        self.assertIn("Nominal must be numeric", self.window.detail_model.last_error)
        self.assertIn("Nominal must be numeric", self.window.statusBar().currentMessage())

    def test_add_geometric_tolerance_dialog_validates_and_adds_position_row(self) -> None:
        dialog = AddGeometricToleranceDialog(["Bushing ID axis"])
        self.addCleanup(dialog.close)
        ok_button = dialog.buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.assertFalse(ok_button.isEnabled())

        dialog.tolerance_edit.setText("0.15")
        dialog.datum_edit.setText("A")
        self.assertTrue(ok_button.isEnabled())
        self.assertAlmostEqual(dialog.geometric_tolerance().derived_plus, 0.075)

        self.window.load_project_file(FIXTURE_PATH)
        self.window._open_summary_index(0)
        original_count = len(self.window.project.stackups[0].contributors)

        contributor = self.window.add_geometric_tolerance(
            "Bushing ID axis",
            GeometricControlType.POSITION,
            0.15,
            ["A"],
        )
        self.app.processEvents()

        self.assertEqual(len(self.window.project.stackups[0].contributors), original_count + 1)
        self.assertEqual(contributor.tolerance_type, ToleranceType.GEOMETRIC)
        self.assertEqual(contributor.geometric_tolerance.control_type, GeometricControlType.POSITION)
        self.assertAlmostEqual(contributor.tolerance_plus, 0.075)
        detail_text = [
            self.window.detail_model.data(self.window.detail_model.index(row_index, 3))
            for row_index in range(self.window.detail_model.rowCount())
        ]
        self.assertTrue(any("position dia 0.15" in str(text) for text in detail_text))

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
        self.assertEqual(dialog.import_settings()["source_mode"], "reference")
        self.assertIn("solids", dialog.import_settings()["object_filter"])
        ok_button = dialog.buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.assertTrue(ok_button.isEnabled())

        unsupported = NeutralCadImportOptionsDialog(Path("native.sldprt"))
        self.addCleanup(unsupported.close)
        unsupported_ok = unsupported.buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.assertFalse(unsupported_ok.isEnabled())


def _find_model_row(model: CadStackupDetailTableModel, name: str) -> int:
    for row in range(model.rowCount()):
        if model.data(model.index(row, 0)) == name:
            return row
    raise AssertionError(f"Detail row not found: {name}")


if __name__ == "__main__":
    unittest.main()
