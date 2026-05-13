"""Qt Widgets shell for CAD-based 1D tolerance analysis."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QAction, QColor, QFont, QFontDatabase, QPalette
    from PyQt6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QFrame,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSizePolicy,
        QSplitter,
        QStackedLayout,
        QStackedWidget,
        QStyle,
        QStyleFactory,
        QTabWidget,
        QTableView,
        QToolBar,
        QToolButton,
        QTreeView,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover - exercised only without GUI deps.
    raise RuntimeError(
        "The CAD 1D tolerance shell requires PyQt6. Use the mdts-cad312 "
        "environment or install PyQt6 before launching it."
    ) from exc

from .cad_geometry_occ import CadKernelUnavailable, OccCadGeometrySession
from .cad_tolerance_models import CadDocument, ShapeKind, Snapshot
from .cad_tolerance_project_io import load_project
from .cad_tolerance_viewmodels import (
    DETAIL_COLUMNS,
    FIDELITY_GAP_NOTES,
    GUIDED_STACKUP_STEPS,
    NON_1D_WARNING_TEXT,
    SUMMARY_COLUMNS,
    CadAssemblyTreeModel,
    CadStackupDetailTableModel,
    CadStackupSummaryTableModel,
    CadToleranceWorkspaceViewModel,
    ContributionBarRow,
    StackupSummaryRow,
)
from .cad_viewer_api import CadCameraState, CadViewer, CadViewerUnavailable, HighlightRole, SnapshotRequest, StandardView, ViewerSelectionMode
from .cad_viewer_occ import OccCadViewerWidget


NEUTRAL_CAD_FILTER = (
    "Neutral CAD files (*.step *.stp *.iges *.igs);;"
    "STEP files (*.step *.stp);;"
    "IGES files (*.iges *.igs)"
)
PROJECT_FILTER = "CAD tolerance projects (*.tolproj)"


class PlaceholderCadViewerWidget(QFrame):
    """Viewer API fallback used when OCCT/PyQt6 AIS is unavailable."""

    def __init__(self, parent: QWidget | None = None, reason: str = "") -> None:
        super().__init__(parent)
        self.setObjectName("PlaceholderCadViewer")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._last_session: Any | None = None
        self._selection_modes: set[ViewerSelectionMode] = {ViewerSelectionMode.BODY}
        self._highlight_roles: dict[str, HighlightRole] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addStretch(1)
        title = QLabel("OCCT AIS/V3d viewport host")
        title.setObjectName("PlaceholderViewerTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail = QLabel(reason or "The primary viewer adapter is isolated behind cad_viewer_api.py.")
        detail.setObjectName("PlaceholderViewerDetail")
        detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(detail)
        layout.addStretch(1)

    def display_document(self, session: Any, display_kinds: set[ShapeKind] | None = None) -> None:
        self._last_session = session

    def clear(self) -> None:
        self._last_session = None
        self._highlight_roles.clear()

    def fit_all(self) -> None:
        return

    def pan(self, dx: int, dy: int) -> None:
        return

    def zoom(self, factor: float) -> None:
        if factor <= 0.0:
            raise ValueError("Zoom factor must be positive.")

    def set_standard_view(self, view: StandardView) -> None:
        self.setProperty("standardView", str(view))

    def set_selection_modes(self, modes: set[ViewerSelectionMode]) -> None:
        self._selection_modes = set(modes) or {ViewerSelectionMode.BODY}

    def highlight(self, shape_ref: Any, role: HighlightRole) -> None:
        self._highlight_roles[getattr(shape_ref, "id", str(shape_ref))] = HighlightRole(role)

    def clear_highlights(self, roles: Any = None) -> None:
        if roles is None:
            self._highlight_roles.clear()
            return
        wanted = {HighlightRole(role) for role in roles}
        for shape_id, role in list(self._highlight_roles.items()):
            if role in wanted:
                del self._highlight_roles[shape_id]

    def camera_state(self) -> CadCameraState:
        return CadCameraState(view_name=str(self.property("standardView") or "placeholder"))

    def capture_snapshot(self, request: SnapshotRequest) -> Snapshot:
        output_path = Path(request.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image = self.grab()
        image.save(str(output_path))
        return Snapshot(
            image_path=str(output_path),
            camera=self.camera_state().to_dict(),
            visible_stackup_ids=list(request.visible_stackup_ids),
            annotation_positions=dict(request.annotation_positions),
        )


class NeutralCadImportOptionsDialog(QDialog):
    """Compact neutral import options dialog matching the observed structure."""

    OBJECT_FILTER_LABELS = (
        "Solids",
        "Surfaces",
        "Meshes",
        "Wires",
        "Work Features",
        "Points",
    )

    def __init__(self, path: str | Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Import: {Path(path).name}")
        self.setObjectName("NeutralCadImportOptionsDialog")
        self.resize(420, 430)
        self._path = Path(path)

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.setObjectName("ImportOptionsTabs")
        self.tabs.addTab(self._options_tab(), "Options")
        self.tabs.addTab(self._select_tab(), "Select")
        layout.addWidget(self.tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def import_settings(self) -> dict[str, Any]:
        filters = [
            checkbox.text()
            for checkbox in self.findChildren(QCheckBox)
            if checkbox.objectName().startswith("ImportFilter") and checkbox.isChecked()
        ]
        return {
            "path": str(self._path),
            "units": self.units_combo.currentText(),
            "import_type": self.import_type_combo.currentText(),
            "object_filters": filters,
            "assembly_option": self.assembly_combo.currentText(),
            "part_option": self.part_combo.currentText(),
        }

    def _options_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        import_group = QGroupBox("Import Type")
        import_layout = QGridLayout(import_group)
        self.import_type_combo = QComboBox()
        self.import_type_combo.addItems(["Reference Model", "Convert Model"])
        import_layout.addWidget(QLabel("Type"), 0, 0)
        import_layout.addWidget(self.import_type_combo, 0, 1)
        self.units_combo = QComboBox()
        self.units_combo.addItems(["From source", "Millimeters", "Inches"])
        import_layout.addWidget(QLabel("Length Units"), 1, 0)
        import_layout.addWidget(self.units_combo, 1, 1)
        layout.addWidget(import_group)

        filters_group = QGroupBox("Object Filters")
        filters_layout = QGridLayout(filters_group)
        for index, label in enumerate(self.OBJECT_FILTER_LABELS):
            checkbox = QCheckBox(label)
            checkbox.setObjectName(f"ImportFilter{label.replace(' ', '')}")
            checkbox.setChecked(label in {"Solids", "Surfaces", "Work Features"})
            filters_layout.addWidget(checkbox, index // 2, index % 2)
        layout.addWidget(filters_group)

        options_group = QGroupBox("Assembly Options")
        options_layout = QGridLayout(options_group)
        self.assembly_combo = QComboBox()
        self.assembly_combo.addItems(["Structure", "Flatten"])
        self.part_combo = QComboBox()
        self.part_combo.addItems(["Composite", "Separate bodies"])
        options_layout.addWidget(QLabel("Assembly"), 0, 0)
        options_layout.addWidget(self.assembly_combo, 0, 1)
        options_layout.addWidget(QLabel("Part Options"), 1, 0)
        options_layout.addWidget(self.part_combo, 1, 1)
        layout.addWidget(options_group)

        file_group = QGroupBox("File Name")
        file_layout = QGridLayout(file_group)
        path_edit = QLineEdit(str(self._path))
        path_edit.setReadOnly(True)
        file_layout.addWidget(QLabel("File Location"), 0, 0)
        file_layout.addWidget(path_edit, 0, 1)
        layout.addWidget(file_group)
        layout.addStretch(1)
        return tab

    def _select_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("Select imported objects after the neutral CAD adapter builds the B-Rep index."))
        layout.addStretch(1)
        return tab


class CadViewportHost(QFrame):
    """Hosts the CAD viewer widget plus observed orientation and workflow overlays."""

    def __init__(self, viewer: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("CadViewportHost")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.viewer = viewer

        stack = QStackedLayout(self)
        stack.setStackingMode(QStackedLayout.StackingMode.StackAll)
        stack.addWidget(viewer)

        overlay = QWidget()
        overlay.setObjectName("CadViewportOverlay")
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        overlay_layout = QGridLayout(overlay)
        overlay_layout.setContentsMargins(10, 10, 10, 10)
        overlay_layout.setColumnStretch(0, 1)
        overlay_layout.setRowStretch(1, 1)

        self.view_cube = QLabel("FRONT\nRIGHT")
        self.view_cube.setObjectName("ViewCubePlaceholder")
        self.view_cube.setAlignment(Qt.AlignmentFlag.AlignCenter)
        overlay_layout.addWidget(self.view_cube, 0, 1, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        self.navigation_toolbar = QToolBar("Viewport Navigation")
        self.navigation_toolbar.setObjectName("ViewportNavigationToolbar")
        self.navigation_toolbar.setOrientation(Qt.Orientation.Vertical)
        for label in ("Orbit", "Pan", "Zoom", "Fit", "Home"):
            self.navigation_toolbar.addAction(label)
        overlay_layout.addWidget(self.navigation_toolbar, 1, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.axis_triad = QLabel("Y\n|\nZ--X")
        self.axis_triad.setObjectName("AxisTriadPlaceholder")
        overlay_layout.addWidget(self.axis_triad, 2, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)

        self.guided_toolbar = self._create_guided_toolbar()
        overlay_layout.addWidget(self.guided_toolbar, 2, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        stack.addWidget(overlay)

    def _create_guided_toolbar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("GuidedStackupToolbar")
        layout = QGridLayout(frame)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setHorizontalSpacing(4)
        layout.setVerticalSpacing(3)
        for index, step in enumerate(GUIDED_STACKUP_STEPS):
            button = QPushButton(step)
            button.setObjectName(f"GuidedStep{index}")
            button.setCheckable(True)
            button.setChecked(index == 0)
            layout.addWidget(button, index // 2, index % 2)
        for index, label in enumerate(("OK", "X", "+", "List")):
            button = QPushButton(label)
            button.setObjectName(f"GuidedControl{label}")
            layout.addWidget(button, 4, index)
        return frame


class DashboardBadgesWidget(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("DashboardBadgesWidget")
        layout = QVBoxLayout(self)
        label = QLabel("Results Summary")
        label.setObjectName("ResultsSummaryTitle")
        layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)
        row = QHBoxLayout()
        self.met_badge = _badge_label("0", "BadgeGreen")
        self.not_met_badge = _badge_label("0", "BadgeRedRound")
        self.sigma_badge = _badge_label("", "BadgeRedPill")
        row.addStretch(1)
        row.addWidget(_badge_stack(self.met_badge, "Objectives met"))
        row.addWidget(_badge_stack(self.not_met_badge, "Objectives not met"))
        row.addWidget(_badge_stack(self.sigma_badge, "Predicted Sigma rollup / Target Sigma rollup"))
        row.addStretch(1)
        layout.addLayout(row)

    def set_values(self, met: int, not_met: int, sigma: str) -> None:
        self.met_badge.setText(str(met))
        self.not_met_badge.setText(str(not_met))
        self.sigma_badge.setText(sigma)


class ResultPanelWidget(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ResultPanelWidget")
        layout = QVBoxLayout(self)
        self.title = QLabel("Worst Case Results")
        self.title.setObjectName("ResultPanelTitle")
        layout.addWidget(self.title)
        bar_row = QHBoxLayout()
        self.left_bar = QFrame()
        self.left_bar.setObjectName("ResultBarFail")
        self.center_marker = QFrame()
        self.center_marker.setObjectName("ResultCenterMarker")
        self.right_bar = QFrame()
        self.right_bar.setObjectName("ResultBarPass")
        bar_row.addWidget(self.left_bar, 1)
        bar_row.addWidget(self.center_marker)
        bar_row.addWidget(self.right_bar, 1)
        layout.addLayout(bar_row)
        self.warning = QLabel(NON_1D_WARNING_TEXT)
        self.warning.setObjectName("NonOneDWarningLabel")
        self.warning.setWordWrap(True)
        layout.addWidget(self.warning)

    def set_stackup_name(self, name: str) -> None:
        self.title.setText(f"Worst Case Results for {name}")


class ContributionBarsWidget(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ContributionBarsWidget")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 14, 14, 14)
        self.title = QLabel("Statistical Contributions")
        self.title.setObjectName("ContributionTitle")
        self._layout.addWidget(self.title)
        self._bars: list[QWidget] = []
        self._layout.addStretch(1)

    def set_rows(self, rows: list[ContributionBarRow], title: str) -> None:
        self.title.setText(title)
        for widget in self._bars:
            widget.setParent(None)
        self._bars.clear()
        insert_at = 1
        for row in rows:
            widget = self._bar_row(row)
            self._layout.insertWidget(insert_at, widget)
            self._bars.append(widget)
            insert_at += 1

    def _bar_row(self, row: ContributionBarRow) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel(row.label)
        label.setMinimumWidth(250)
        layout.addWidget(label)
        if row.tolerance_box:
            box = QLabel("  ".join(part for part in (row.tolerance_box, row.datum) if part))
            box.setObjectName("GdtBoxPlaceholder")
            layout.addWidget(box)
        bar = QFrame()
        bar.setObjectName("ContributionBlueBar")
        bar.setMinimumWidth(max(2, int(row.percent * 4)))
        bar.setMaximumWidth(max(2, int(row.percent * 4)))
        layout.addWidget(bar)
        percent = QLabel(f"{row.percent:.1f}%")
        layout.addWidget(percent)
        layout.addStretch(1)
        return widget


class CadToleranceMainWindow(QMainWindow):
    """Dense EZtol-style CAD 1D tolerance shell."""

    def __init__(
        self,
        geometry_session: OccCadGeometrySession | None = None,
        viewer: QWidget | CadViewer | None = None,
        workspace: CadToleranceWorkspaceViewModel | None = None,
    ) -> None:
        super().__init__()
        self.geometry_session = geometry_session or OccCadGeometrySession()
        self.viewer = viewer if viewer is not None else self._create_viewer()
        self.workspace = workspace or CadToleranceWorkspaceViewModel.demo()

        self.summary_model = CadStackupSummaryTableModel(self.workspace.summary_rows)
        self.detail_model = CadStackupDetailTableModel(self.workspace.detail_rows())
        self.assembly_model = CadAssemblyTreeModel(self.workspace.assembly_roots)

        self.setWindowTitle(f"MDTS CAD 1D Tolerance - {self.workspace.project_title}")
        self.resize(1500, 900)
        self.setMinimumSize(1000, 640)
        self._build_actions()
        self._build_shell()
        self._connect_signals()
        self._refresh_dashboard()
        self.statusBar().showMessage("Ready")

    def open_cad_file(self, path: str | Path) -> None:
        input_path = Path(path)
        dialog = NeutralCadImportOptionsDialog(input_path, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            document = self.geometry_session.import_file(input_path)
            if hasattr(self.viewer, "display_document"):
                self.viewer.display_document(self.geometry_session)  # type: ignore[attr-defined]
        except (CadKernelUnavailable, Exception) as exc:
            QMessageBox.warning(self, "CAD import failed", str(exc))
            self.statusBar().showMessage("CAD import failed")
            return
        document.import_settings.update(dialog.import_settings())
        self.set_imported_document(document)

    def set_imported_document(self, document: CadDocument) -> None:
        self.workspace = CadToleranceWorkspaceViewModel.from_document(document)
        self.assembly_model.set_roots(self.workspace.assembly_roots)
        self.summary_model.set_rows(self.workspace.summary_rows)
        self.detail_model.set_rows([])
        self.dashboard_badges.set_values(0, 0, "")
        self.setWindowTitle(f"MDTS CAD 1D Tolerance - {self.workspace.project_title}")
        self.statusBar().showMessage(f"Imported {document.display_name or Path(document.source_path).name}")

    def load_project_file(self, path: str | Path) -> None:
        project = load_project(Path(path))
        self.workspace = CadToleranceWorkspaceViewModel.from_project(project)
        self.assembly_model.set_roots(self.workspace.assembly_roots)
        self.summary_model.set_rows(self.workspace.summary_rows)
        self._set_detail_stackup(self.workspace.selected_stackup_id)
        self._refresh_dashboard()
        self.setWindowTitle(f"MDTS CAD 1D Tolerance - {self.workspace.project_title}")
        self.statusBar().showMessage(f"Loaded {Path(path).name}")

    def _create_viewer(self) -> QWidget:
        try:
            return OccCadViewerWidget(self)
        except CadViewerUnavailable as exc:
            return PlaceholderCadViewerWidget(self, str(exc))

    def _build_actions(self) -> None:
        style = self.style()
        self.open_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon), "Open", self)
        self.open_action.triggered.connect(self._open_dialog)
        self.import_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_ArrowDown), "Import", self)
        self.import_action.triggered.connect(self._open_dialog)
        self.export_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_ArrowUp), "Export", self)
        self.new_stackup_action = QAction("New Stackup", self)
        self.new_stackup_action.triggered.connect(lambda: self.statusBar().showMessage("Select a face, edge or vertex"))
        self.add_feature_action = QAction("Add Feature", self)
        self.add_feature_action.triggered.connect(lambda: self.statusBar().showMessage("Select a face, edge or vertex from the mating component"))
        self.snapshot_action = QAction("Snapshot", self)
        self.snapshot_action.setToolTip("Sets the current view orientation and size for the report image.")
        self.snapshot_action.triggered.connect(self._save_snapshot)
        self.generate_report_action = QAction("Generate Report", self)
        self.settings_action = QAction("Settings", self)
        self.back_action = QAction("Back", self)
        self.back_action.triggered.connect(self.show_summary)

    def _build_shell(self) -> None:
        central = QWidget()
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self._create_ribbon())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("MainWorkspaceSplitter")
        splitter.addWidget(self._create_left_browser())
        splitter.addWidget(CadViewportHost(self.viewer))
        splitter.addWidget(self._create_analysis_pane())
        splitter.setSizes([250, 720, 620])
        root_layout.addWidget(splitter, 1)
        self.setCentralWidget(central)

    def _create_ribbon(self) -> QTabWidget:
        ribbon = QTabWidget()
        ribbon.setObjectName("RibbonTabs")
        ribbon.setMaximumHeight(122)
        ribbon.addTab(self._ribbon_page([self.new_stackup_action, self.add_feature_action], "Stackup"), "Stackup")
        ribbon.addTab(self._ribbon_page([self.snapshot_action, self.generate_report_action], "Report"), "Report")
        ribbon.addTab(self._ribbon_page([self.open_action, self.import_action, self.export_action], "Data"), "Data")
        return ribbon

    def _ribbon_page(self, actions: list[QAction], group_label: str) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(8, 6, 8, 3)
        layout.setSpacing(12)
        for action in actions:
            button = QToolButton()
            button.setDefaultAction(action)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setObjectName(f"RibbonButton{action.text().replace(' ', '')}")
            if action.icon().isNull():
                button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
            layout.addWidget(button)
        group = QLabel(group_label)
        group.setObjectName("RibbonGroupLabel")
        layout.addWidget(group, alignment=Qt.AlignmentFlag.AlignBottom)
        layout.addStretch(1)
        return page

    def _create_left_browser(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("ModelBrowserPanel")
        panel.setMinimumWidth(220)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        header = QHBoxLayout()
        title = QLabel("Model")
        title.setObjectName("DockHeaderTitle")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(QLabel("?"))
        header.addWidget(QLabel("X"))
        layout.addLayout(header)

        toolbar = QToolBar("Assembly Browser")
        toolbar.setObjectName("AssemblyBrowserToolbar")
        toolbar.addAction("Filter")
        toolbar.addAction("Assembly View")
        toolbar.addAction("Find")
        layout.addWidget(toolbar)

        self.assembly_tree = QTreeView()
        self.assembly_tree.setObjectName("AssemblyTreeView")
        self.assembly_tree.setModel(self.assembly_model)
        self.assembly_tree.expandToDepth(1)
        self.assembly_tree.header().hide()
        layout.addWidget(self.assembly_tree, 1)
        return panel

    def _create_analysis_pane(self) -> QWidget:
        self.analysis_stack = QStackedWidget()
        self.analysis_stack.setObjectName("AnalysisPaneStack")
        self.summary_page = self._create_summary_page()
        self.detail_page = self._create_detail_page()
        self.analysis_stack.addWidget(self.summary_page)
        self.analysis_stack.addWidget(self.detail_page)
        return self.analysis_stack

    def _create_summary_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QHBoxLayout()
        header.setContentsMargins(8, 8, 8, 6)
        header.addWidget(QLabel("MDTS"))
        title = QLabel("Summary of 1D Tolerance Stackups")
        title.setObjectName("AnalysisPaneTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(title, 1)
        gear = QToolButton()
        gear.setDefaultAction(self.settings_action)
        gear.setText("Gear")
        header.addWidget(gear)
        layout.addLayout(header)

        self.summary_table = QTableView()
        self.summary_table.setObjectName("SummaryTableView")
        self.summary_table.setModel(self.summary_model)
        self._configure_table(self.summary_table)
        self.summary_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.summary_table, 2)

        self.summary_tabs = QTabWidget()
        self.summary_tabs.setObjectName("SummaryResultTabs")
        self.dashboard_badges = DashboardBadgesWidget()
        self.summary_tabs.addTab(self.dashboard_badges, "Results")
        self.summary_contributions = ContributionBarsWidget()
        self.summary_contributions.set_rows(self.workspace.contribution_rows(), "Contributions Rollup")
        self.summary_tabs.addTab(self.summary_contributions, "Contributions")
        layout.addWidget(self.summary_tabs, 1)
        return page

    def _create_detail_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(8, 8, 8, 6)
        back_button = QToolButton()
        back_button.setDefaultAction(self.back_action)
        back_button.setText("<")
        header.addWidget(back_button)
        self.detail_title = QLabel("Stackup details")
        self.detail_title.setObjectName("AnalysisPaneTitle")
        self.detail_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self.detail_title, 1)
        for action in (self.snapshot_action, self.settings_action):
            button = QToolButton()
            button.setDefaultAction(action)
            header.addWidget(button)
        layout.addLayout(header)

        self.detail_table = QTableView()
        self.detail_table.setObjectName("DetailTableView")
        self.detail_table.setModel(self.detail_model)
        self._configure_table(self.detail_table)
        self.detail_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.detail_table, 2)

        self.detail_tabs = QTabWidget()
        self.detail_tabs.setObjectName("DetailResultTabs")
        self.result_panel = ResultPanelWidget()
        self.detail_tabs.addTab(self.result_panel, "Results")
        self.detail_contributions = ContributionBarsWidget()
        self.detail_tabs.addTab(self.detail_contributions, "Contributions")
        layout.addWidget(self.detail_tabs, 1)
        return page

    def _configure_table(self, table: QTableView) -> None:
        table.setAlternatingRowColors(False)
        table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        table.verticalHeader().setDefaultSectionSize(22)
        table.verticalHeader().hide()
        table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        table.setShowGrid(True)

    def _connect_signals(self) -> None:
        self.summary_table.doubleClicked.connect(lambda index: self._open_summary_index(index.row()))
        self.summary_table.activated.connect(lambda index: self._open_summary_index(index.row()))

    def _open_summary_index(self, row: int) -> None:
        if row < 0 or row >= self.summary_model.rowCount():
            return
        summary = self.summary_model.row_at(row)
        self._set_detail_stackup(summary.stackup_id)
        self.analysis_stack.setCurrentWidget(self.detail_page)

    def _set_detail_stackup(self, stackup_id: str) -> None:
        if not stackup_id:
            self.detail_model.set_rows([])
            return
        self.workspace.select_stackup(stackup_id)
        selected = _summary_by_id(self.workspace.summary_rows, stackup_id)
        title = selected.name if selected else "Stackup"
        self.detail_title.setText(f"{title} details")
        self.detail_model.set_rows(self.workspace.detail_rows(stackup_id))
        self.result_panel.set_stackup_name(title)
        self.detail_contributions.set_rows(
            self.workspace.contribution_rows(stackup_id),
            f"Statistical Contributions for {title}",
        )

    def _refresh_dashboard(self) -> None:
        badges = self.workspace.dashboard_badges
        self.dashboard_badges.set_values(
            badges.objectives_met,
            badges.objectives_not_met,
            badges.sigma_rollup,
        )

    def show_summary(self) -> None:
        self.analysis_stack.setCurrentWidget(self.summary_page)

    def _open_dialog(self) -> None:
        path, selected_filter = QFileDialog.getOpenFileName(
            self,
            "Open neutral CAD file or CAD tolerance project",
            "",
            f"{PROJECT_FILTER};;{NEUTRAL_CAD_FILTER}",
        )
        if not path:
            return
        if selected_filter == PROJECT_FILTER or Path(path).suffix.lower() == ".tolproj":
            try:
                self.load_project_file(path)
            except Exception as exc:
                QMessageBox.warning(self, "Project load failed", str(exc))
            return
        self.open_cad_file(path)

    def _save_snapshot(self) -> None:
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save CAD viewer snapshot",
            "",
            "PNG image (*.png);;JPEG image (*.jpg *.jpeg)",
        )
        if not path:
            return
        output_path = Path(path)
        if output_path.suffix == "":
            output_path = output_path.with_suffix(".png")
        try:
            snapshot = self.viewer.capture_snapshot(SnapshotRequest(output_path))  # type: ignore[attr-defined]
        except Exception as exc:
            QMessageBox.warning(self, "Snapshot failed", str(exc))
            self.statusBar().showMessage("Snapshot failed")
            return
        self.statusBar().showMessage(f"Saved snapshot {Path(snapshot.image_path).name}")


def _summary_by_id(rows: list[StackupSummaryRow], stackup_id: str) -> StackupSummaryRow | None:
    for row in rows:
        if row.stackup_id == stackup_id:
            return row
    return None


def _badge_label(text: str, object_name: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName(object_name)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


def _badge_stack(badge: QLabel, caption: str) -> QWidget:
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignCenter)
    text = QLabel(caption)
    text.setObjectName("BadgeCaption")
    text.setAlignment(Qt.AlignmentFlag.AlignCenter)
    text.setWordWrap(True)
    layout.addWidget(text)
    return widget


def _apply_cad_tolerance_style(app: QApplication) -> None:
    fusion_style = QStyleFactory.create("Fusion")
    if fusion_style is not None:
        app.setStyle(fusion_style)
    else:
        app.setStyle("Fusion")

    font_families = set(QFontDatabase.families())
    for family in ("Segoe UI", "Arial", "Tahoma"):
        if family in font_families:
            app.setFont(QFont(family, 10))
            break

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#f2f2f2"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#202020"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#f7f7f7"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#202020"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#f4f4f4"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#202020"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#d7eaff"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#111111"))
    app.setPalette(palette)

    app.setStyleSheet(
        """
        QMainWindow {
            background: #f2f2f2;
        }
        QTabWidget#RibbonTabs::pane {
            border-bottom: 1px solid #c8c8c8;
            background: #f4f4f4;
        }
        QTabWidget#RibbonTabs QTabBar::tab {
            padding: 7px 14px;
            background: #efefef;
            border-right: 1px solid #d2d2d2;
        }
        QTabWidget#RibbonTabs QTabBar::tab:selected {
            background: #ffffff;
            border-top: 3px solid #e87522;
        }
        QToolButton {
            border: 1px solid transparent;
            padding: 4px;
        }
        QToolButton:hover, QPushButton:hover {
            background: #e4f0fb;
            border: 1px solid #7aa7d9;
        }
        QLabel#RibbonGroupLabel {
            color: #555555;
            padding-left: 10px;
            padding-bottom: 3px;
        }
        QFrame#ModelBrowserPanel {
            background: #ffffff;
            border-right: 1px solid #b8b8b8;
        }
        QLabel#DockHeaderTitle {
            font-weight: 700;
            padding: 6px 8px;
        }
        QToolBar#AssemblyBrowserToolbar {
            border-top: 1px solid #d0d0d0;
            border-bottom: 1px solid #d0d0d0;
            background: #f7f7f7;
            spacing: 4px;
        }
        QTreeView#AssemblyTreeView {
            selection-background-color: #d7eaff;
            border: 0;
        }
        QFrame#CadViewportHost, QFrame#PlaceholderCadViewer {
            background: #bfbfbf;
            border: 1px solid #9c9c9c;
        }
        QLabel#PlaceholderViewerTitle {
            font-size: 18px;
            font-weight: 700;
            color: #303030;
        }
        QLabel#PlaceholderViewerDetail {
            color: #4a4a4a;
        }
        QLabel#ViewCubePlaceholder {
            min-width: 58px;
            min-height: 48px;
            background: rgba(240, 240, 240, 180);
            border: 1px solid #9c9c9c;
            color: #666666;
            font-size: 10px;
        }
        QToolBar#ViewportNavigationToolbar {
            background: rgba(235, 235, 235, 170);
            border: 1px solid #a5a5a5;
        }
        QLabel#AxisTriadPlaceholder {
            color: #1d4ed8;
            font-weight: 700;
        }
        QFrame#GuidedStackupToolbar {
            background: rgba(238, 238, 238, 210);
            border: 1px solid #9b9b9b;
            border-radius: 3px;
        }
        QFrame#GuidedStackupToolbar QPushButton {
            min-height: 20px;
            padding: 1px 7px;
            background: #f5f5f5;
            border: 1px solid #c4c4c4;
            border-radius: 8px;
        }
        QFrame#GuidedStackupToolbar QPushButton:checked {
            background: #aecdff;
            border-color: #5f93d5;
        }
        QLabel#AnalysisPaneTitle {
            font-size: 15px;
            font-weight: 700;
        }
        QTableView {
            gridline-color: #d0d0d0;
            selection-background-color: #d7eaff;
            selection-color: #111111;
            border: 1px solid #bcbcbc;
            background: #ffffff;
            font-size: 10px;
        }
        QHeaderView::section {
            background: #ffffff;
            border: 1px solid #d6d6d6;
            padding: 3px;
            font-weight: 700;
        }
        QTabWidget#SummaryResultTabs::pane, QTabWidget#DetailResultTabs::pane {
            border: 1px solid #bcbcbc;
            background: #ffffff;
        }
        QLabel#ResultsSummaryTitle, QLabel#ResultPanelTitle, QLabel#ContributionTitle {
            font-weight: 700;
            color: #111111;
        }
        QLabel#BadgeGreen {
            min-width: 70px;
            min-height: 56px;
            color: #ffffff;
            background: #15922a;
            border-radius: 10px;
            font-size: 32px;
            font-weight: 800;
        }
        QLabel#BadgeRedRound {
            min-width: 58px;
            min-height: 56px;
            color: #ffffff;
            background: #c92020;
            border-radius: 28px;
            font-size: 28px;
            font-weight: 800;
        }
        QLabel#BadgeRedPill {
            min-width: 210px;
            min-height: 56px;
            color: #ffffff;
            background: #c92020;
            border-radius: 8px;
            font-size: 26px;
            font-weight: 800;
        }
        QLabel#BadgeCaption {
            font-size: 10px;
        }
        QFrame#ResultBarFail {
            min-height: 22px;
            background: #c32b2b;
        }
        QFrame#ResultBarPass {
            min-height: 22px;
            background: #168a24;
        }
        QFrame#ResultCenterMarker {
            min-width: 4px;
            max-width: 4px;
            background: #111111;
        }
        QLabel#NonOneDWarningLabel {
            color: #111111;
            font-weight: 700;
            padding: 10px;
        }
        QFrame#ContributionBlueBar {
            min-height: 22px;
            background: #0d83c9;
        }
        QLabel#GdtBoxPlaceholder {
            border: 1px solid #111111;
            padding: 3px 8px;
            background: #ffffff;
        }
        QStatusBar {
            background: #eeeeee;
            border-top: 1px solid #c8c8c8;
        }
        """
    )


def create_cad_tolerance_window(
    app: QApplication | None = None,
    geometry_session: OccCadGeometrySession | None = None,
    viewer: QWidget | CadViewer | None = None,
    workspace: CadToleranceWorkspaceViewModel | None = None,
) -> CadToleranceMainWindow:
    app = app or QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    _apply_cad_tolerance_style(app)
    return CadToleranceMainWindow(
        geometry_session=geometry_session,
        viewer=viewer,
        workspace=workspace,
    )


CadToleranceViewerWindow = CadToleranceMainWindow


def main() -> None:
    app = QApplication(sys.argv)
    window = create_cad_tolerance_window(app)
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        if path.suffix.lower() == ".tolproj":
            window.load_project_file(path)
        else:
            window.open_cad_file(path)
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
