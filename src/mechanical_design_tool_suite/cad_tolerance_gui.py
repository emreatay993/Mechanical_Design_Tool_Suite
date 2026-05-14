"""Qt Widgets shell for CAD-based 1D tolerance analysis."""

from __future__ import annotations

import math
from pathlib import Path
import re
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
        QStyledItemDelegate,
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

from .cad_geometry_api import (
    CadImportSettings,
    UnsupportedCadFormatError,
    is_supported_neutral_cad,
)
from .cad_geometry_occ import CadKernelUnavailable, OccCadGeometrySession
from .cad_stackup_workflow import GuidedStackupWorkflowController, GuidedToolbarState
from .cad_tolerance_methods import calculate_stackup
from .cad_tolerance_models import (
    CadDocument,
    CadToleranceProject,
    FeatureReference,
    GeometricControlType,
    GeometricTolerance,
    ShapeKind,
    Snapshot,
    StackupContributor,
    StackupRequirement,
    ToleranceType,
    geometric_control_display_label,
)
from .cad_tolerance_project_io import (
    PACKAGE_SUFFIX,
    export_project_package,
    import_project_package,
    load_project,
    project_asset_dir,
    project_relative_path,
    resolve_project_asset_path,
    save_project,
)
from .cad_tolerance_report import ResultDisplayProjection, generate_html_report
from .cad_tolerance_viewmodels import (
    DETAIL_COLUMNS,
    DETAIL_TOLERANCE_TYPE_ROLE,
    FIDELITY_GAP_NOTES,
    GUIDED_STACKUP_STEPS,
    NON_1D_WARNING_TEXT,
    SUMMARY_COLUMNS,
    CadAssemblyTreeModel,
    CadStackupDetailTableModel,
    CadStackupSummaryTableModel,
    CadToleranceWorkspaceViewModel,
    ContributionBarRow,
    DetailEditResult,
    StackupDetailRow,
    StackupSummaryRow,
)
from .cad_viewer_api import CadCameraState, CadViewer, CadViewerSelection, CadViewerUnavailable, HighlightRole, SnapshotRequest, StandardView, ViewerSelectionMode
from .cad_viewer_occ import OccCadViewerWidget


NEUTRAL_CAD_FILTER = (
    "Neutral CAD files (*.step *.stp *.iges *.igs);;"
    "STEP files (*.step *.stp);;"
    "IGES files (*.iges *.igs)"
)
PROJECT_FILTER = "CAD tolerance projects (*.tolproj)"
PACKAGE_FILTER = "CAD tolerance packages (*.tolpack)"


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


class AddGeometricToleranceDialog(QDialog):
    """Manual GD&T/GPS contributor entry dialog for the stackup detail table."""

    CONTROL_OPTIONS = (
        ("Runout", GeometricControlType.RUNOUT),
        ("Position", GeometricControlType.POSITION),
        ("Profile", GeometricControlType.PROFILE),
        ("Manual", GeometricControlType.MANUAL),
    )

    def __init__(
        self,
        feature_names: list[str] | tuple[str, ...] = (),
        parent: QWidget | None = None,
        default_feature: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Geometric Tolerance")
        self.setObjectName("AddGeometricToleranceDialog")
        self.resize(360, 180)

        layout = QGridLayout(self)
        layout.addWidget(QLabel("Feature Controlled:"), 0, 0)
        self.feature_combo = QComboBox()
        self.feature_combo.setObjectName("GdtFeatureControlled")
        self.feature_combo.setEditable(True)
        names = list(dict.fromkeys(name for name in feature_names if name))
        if names:
            self.feature_combo.addItems(names)
        if default_feature:
            self.feature_combo.setCurrentText(default_feature)
        elif not names:
            self.feature_combo.setCurrentText("Manual feature")
        layout.addWidget(self.feature_combo, 0, 1, 1, 2)

        self.control_combo = QComboBox()
        self.control_combo.setObjectName("GdtControlType")
        for label, control_type in self.CONTROL_OPTIONS:
            self.control_combo.addItem(label, control_type.value)
        layout.addWidget(QLabel("Type"), 1, 0)
        layout.addWidget(self.control_combo, 1, 1, 1, 2)

        self.tolerance_edit = QLineEdit()
        self.tolerance_edit.setObjectName("GdtToleranceValue")
        self.tolerance_edit.setPlaceholderText("0.1")
        layout.addWidget(QLabel("Tolerance"), 2, 0)
        layout.addWidget(self.tolerance_edit, 2, 1)

        self.datum_edit = QLineEdit()
        self.datum_edit.setObjectName("GdtDatumReferences")
        self.datum_edit.setPlaceholderText("A")
        layout.addWidget(QLabel("Datum / Reference"), 2, 2)
        layout.addWidget(self.datum_edit, 2, 3)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons, 3, 0, 1, 4)

        self.feature_combo.currentTextChanged.connect(self._update_ok_state)
        self.control_combo.currentTextChanged.connect(self._update_ok_state)
        self.tolerance_edit.textChanged.connect(self._update_ok_state)
        self.datum_edit.textChanged.connect(self._update_ok_state)
        self._update_ok_state()

    def controlled_feature(self) -> str:
        return self.feature_combo.currentText().strip()

    def control_type(self) -> GeometricControlType:
        return GeometricControlType(str(self.control_combo.currentData()))

    def tolerance_value(self) -> float:
        return _parse_positive_float(self.tolerance_edit.text(), "Geometric tolerance")

    def datum_references(self) -> list[str]:
        return _parse_datum_tokens(self.datum_edit.text())

    def geometric_tolerance(self) -> GeometricTolerance:
        return GeometricTolerance(
            control_type=self.control_type(),
            tolerance_value=self.tolerance_value(),
            datum_references=self.datum_references(),
        )

    def _update_ok_state(self) -> None:
        ok = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        try:
            valid = bool(self.controlled_feature()) and self.tolerance_value() > 0.0 and bool(
                self.datum_references()
            )
        except ValueError:
            valid = False
        ok.setEnabled(valid)


class ToleranceCellDelegate(QStyledItemDelegate):
    """Editable combo for tolerance values and tolerance-mode examples."""

    def createEditor(self, parent: QWidget, option, index):  # noqa: N802 - Qt override
        if index.column() != 3:
            return super().createEditor(parent, option, index)
        combo = QComboBox(parent)
        combo.setEditable(True)
        combo.setObjectName("ToleranceTypeEditor")
        current = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        tolerance_type = str(index.data(DETAIL_TOLERANCE_TYPE_ROLE) or "")
        examples = [
            current,
            "symmetric:+/-0.05",
            "limits:+0.075/-0.05",
            "runout 0.1 A",
            "position 0.15 A",
            "profile 0.5 A",
        ]
        if tolerance_type == ToleranceType.GEOMETRIC.value:
            examples.insert(1, "geometric:" + current)
        combo.addItems([item for item in dict.fromkeys(examples) if item])
        return combo

    def setEditorData(self, editor: QWidget, index) -> None:  # noqa: N802 - Qt override
        if isinstance(editor, QComboBox):
            editor.setCurrentText(str(index.data(Qt.ItemDataRole.EditRole) or ""))
            return
        super().setEditorData(editor, index)

    def setModelData(self, editor: QWidget, model, index) -> None:  # noqa: N802 - Qt override
        if isinstance(editor, QComboBox):
            model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)
            return
        super().setModelData(editor, model, index)


class CadViewportHost(QFrame):
    """Hosts the CAD viewer widget plus observed orientation and workflow overlays."""

    def __init__(self, viewer: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("CadViewportHost")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.viewer = viewer
        self._step_buttons: dict[str, QPushButton] = {}
        self._control_buttons: dict[str, QPushButton] = {}

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
            self._step_buttons[step] = button
            layout.addWidget(button, index // 2, index % 2)
        self.guided_prompt = QLabel("Select a face, edge or vertex")
        self.guided_prompt.setObjectName("GuidedPromptLabel")
        self.guided_prompt.setWordWrap(True)
        layout.addWidget(self.guided_prompt, 3, 0, 1, 2)
        self.component_counter = QLabel("0 Components")
        self.component_counter.setObjectName("GuidedComponentCounter")
        self.mating_face_counter = QLabel("0 of 0 Mating Faces")
        self.mating_face_counter.setObjectName("GuidedMatingFaceCounter")
        layout.addWidget(self.component_counter, 3, 2)
        layout.addWidget(self.mating_face_counter, 3, 3)
        for index, label in enumerate(("OK", "X", "+", "List")):
            button = QPushButton(label)
            button.setObjectName(f"GuidedControl{label}")
            self._control_buttons[label] = button
            layout.addWidget(button, 4, index)
        return frame

    def set_workflow_toolbar_state(self, state: GuidedToolbarState) -> None:
        for label, button in self._step_buttons.items():
            button.setChecked(label == state.active_label)
        self.guided_prompt.setText(state.prompt)
        self.component_counter.setText(state.component_count_text)
        self.mating_face_counter.setText(state.mating_face_count_text)
        enabled_by_label = {
            "OK": state.check_enabled,
            "X": state.cancel_enabled,
            "+": state.add_enabled,
            "List": state.list_enabled,
        }
        for label, enabled in enabled_by_label.items():
            if label in self._control_buttons:
                self._control_buttons[label].setEnabled(enabled)


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
        self.metrics = QLabel("")
        self.metrics.setObjectName("ResultPanelMetrics")
        self.metrics.setWordWrap(True)
        layout.addWidget(self.metrics)
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
        self.warning.setVisible(False)
        layout.addWidget(self.warning)

    def set_stackup_name(self, name: str) -> None:
        self.title.setText(f"Worst Case Results for {name}")
        self.metrics.setText("")
        self.warning.setVisible(False)

    def set_projection(self, projection: ResultDisplayProjection) -> None:
        self.title.setText(projection.title)
        metrics = [
            projection.mean_label,
            projection.standard_deviation_label,
            projection.result_label,
            projection.objective_label,
        ]
        if projection.predicted_quality_label:
            metrics.append(projection.predicted_quality_label)
        self.metrics.setText("    ".join(metrics))
        if projection.warnings:
            warning_lines = [NON_1D_WARNING_TEXT]
            warning_lines.extend(warning.message for warning in projection.warnings)
            self.warning.setText("! " + "\n".join(warning_lines))
            self.warning.setVisible(True)
        else:
            self.warning.setText("")
            self.warning.setVisible(False)


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
        self.project = CadToleranceProject(title=self.workspace.project_title)
        self.project_path: Path | None = None
        self.cad_source_status_messages: list[str] = []
        self.workflow_controller: GuidedStackupWorkflowController | None = None
        self.geometric_dialog_factory = AddGeometricToleranceDialog

        self.summary_model = CadStackupSummaryTableModel(self.workspace.summary_rows)
        self.detail_model = CadStackupDetailTableModel(
            self.workspace.detail_rows(),
            edit_handler=self._handle_detail_edit,
        )
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
        self.project = CadToleranceProject(
            title=document.display_name or document.source_path or "Imported CAD",
            cad_documents=[document],
        )
        self.project_path = None
        self.cad_source_status_messages = []
        self.workspace = CadToleranceWorkspaceViewModel.from_document(document)
        self.assembly_model.set_roots(self.workspace.assembly_roots)
        self.summary_model.set_rows(self.workspace.summary_rows)
        self.detail_model.set_rows([])
        self.dashboard_badges.set_values(0, 0, "")
        self.summary_contributions.set_rows([], "Contributions Rollup")
        self.result_panel.set_stackup_name("Stackup")
        self.setWindowTitle(f"MDTS CAD 1D Tolerance - {self.workspace.project_title}")
        self.statusBar().showMessage(f"Imported {document.display_name or Path(document.source_path).name}")

    def load_project_file(self, path: str | Path) -> None:
        project_path = Path(path)
        project = load_project(project_path)
        self.project = project
        self.project_path = project_path
        self.workspace = CadToleranceWorkspaceViewModel.from_project(project)
        self.assembly_model.set_roots(self.workspace.assembly_roots)
        self.summary_model.set_rows(self.workspace.summary_rows)
        self._set_detail_stackup(self.workspace.selected_stackup_id)
        self._refresh_dashboard()
        self.setWindowTitle(f"MDTS CAD 1D Tolerance - {self.workspace.project_title}")
        self._rehydrate_project_cad_sources(project_path)
        if self.cad_source_status_messages:
            self.statusBar().showMessage("; ".join(self.cad_source_status_messages))
        else:
            self.statusBar().showMessage(f"Loaded {project_path.name}")

    def _rehydrate_project_cad_sources(self, project_path: Path) -> None:
        self.cad_source_status_messages = []
        if not self.project.cad_documents:
            return

        displayed = False
        for document in self.project.cad_documents:
            source_path = document.source_path
            source_name = Path(source_path).name if source_path else "CAD source"
            if not source_path:
                self.cad_source_status_messages.append("CAD source not recorded")
                continue
            resolved_path = resolve_project_asset_path(source_path, project_path)
            if resolved_path is None:
                self.cad_source_status_messages.append(
                    f"CAD source not found: {source_name}"
                )
                continue
            if not is_supported_neutral_cad(resolved_path):
                self.cad_source_status_messages.append(
                    f"Unsupported CAD source: {source_name}"
                )
                continue
            try:
                self.geometry_session.import_file(
                    resolved_path,
                    _cad_import_settings_from_document(document, self.project),
                )
                if hasattr(self.viewer, "display_document"):
                    self.viewer.display_document(self.geometry_session)  # type: ignore[attr-defined]
                displayed = True
                self.cad_source_status_messages.append(
                    f"Reloaded CAD source: {resolved_path.name}"
                )
            except UnsupportedCadFormatError:
                self.cad_source_status_messages.append(
                    f"Unsupported CAD source: {source_name}"
                )
            except FileNotFoundError:
                self.cad_source_status_messages.append(
                    f"CAD source not found: {source_name}"
                )
            except (CadKernelUnavailable, Exception) as exc:
                self.cad_source_status_messages.append(
                    f"CAD source unavailable: {source_name} ({exc})"
                )

        if not displayed and hasattr(self.viewer, "clear"):
            self.viewer.clear()  # type: ignore[attr-defined]

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
        self.export_action.setToolTip("Package Project (.tolpack)")
        self.export_action.triggered.connect(self._package_project)
        self.save_project_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), "Save Project", self)
        self.save_project_action.triggered.connect(self._save_project)
        self.new_stackup_action = QAction("New Stackup", self)
        self.new_stackup_action.triggered.connect(self._start_new_stackup_workflow)
        self.add_feature_action = QAction("Add Feature", self)
        self.add_feature_action.triggered.connect(lambda: self.statusBar().showMessage("Select a face, edge or vertex from the mating component"))
        self.add_geometric_tolerance_action = QAction("Add Geometric Tolerance", self)
        self.add_geometric_tolerance_action.triggered.connect(self._open_add_geometric_tolerance_dialog)
        self.snapshot_action = QAction("Snapshot", self)
        self.snapshot_action.setToolTip("Sets the current view orientation and size for the report image.")
        self.snapshot_action.triggered.connect(self._save_snapshot)
        self.generate_report_action = QAction("Generate Report", self)
        self.generate_report_action.triggered.connect(self._generate_report)
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
        self.viewport_host = CadViewportHost(self.viewer)
        splitter.addWidget(self.viewport_host)
        splitter.addWidget(self._create_analysis_pane())
        splitter.setSizes([250, 720, 620])
        root_layout.addWidget(splitter, 1)
        self.setCentralWidget(central)

    def _create_ribbon(self) -> QTabWidget:
        ribbon = QTabWidget()
        ribbon.setObjectName("RibbonTabs")
        ribbon.setMaximumHeight(122)
        ribbon.addTab(self._ribbon_page([self.new_stackup_action, self.add_feature_action, self.add_geometric_tolerance_action], "Stackup"), "Stackup")
        ribbon.addTab(self._ribbon_page([self.snapshot_action, self.generate_report_action], "Report"), "Report")
        ribbon.addTab(self._ribbon_page([self.open_action, self.import_action, self.save_project_action, self.export_action], "Data"), "Data")
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
        for action in (self.add_geometric_tolerance_action, self.snapshot_action, self.settings_action):
            button = QToolButton()
            button.setDefaultAction(action)
            header.addWidget(button)
        layout.addLayout(header)

        self.detail_table = QTableView()
        self.detail_table.setObjectName("DetailTableView")
        self.detail_table.setModel(self.detail_model)
        self._configure_table(self.detail_table)
        self.detail_table.setItemDelegateForColumn(3, ToleranceCellDelegate(self.detail_table))
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
        self.detail_model.editAccepted.connect(self.statusBar().showMessage)
        self.detail_model.editRejected.connect(self.statusBar().showMessage)
        selection_signal = getattr(self.viewer, "selection_changed", None)
        if selection_signal is not None and hasattr(selection_signal, "connect"):
            selection_signal.connect(self.handle_viewer_selections)

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
        self._update_detail_outputs(stackup_id, title)

    def _update_detail_outputs(self, stackup_id: str, title: str | None = None) -> None:
        selected = _summary_by_id(self.workspace.summary_rows, stackup_id)
        resolved_title = title or (selected.name if selected else "Stackup")
        projection = self.workspace.result_projection(stackup_id)
        if projection is not None:
            self.result_panel.set_projection(projection)
        else:
            self.result_panel.set_stackup_name(resolved_title)
        self.detail_contributions.set_rows(
            self.workspace.contribution_rows(stackup_id),
            f"{projection.mode_label if projection else 'Statistical'} Contributions for {resolved_title}",
        )

    def _handle_detail_edit(
        self,
        row: StackupDetailRow,
        column: int,
        value: str,
    ) -> DetailEditResult:
        stackup_id = self.workspace.selected_stackup_id
        stackup = _stackup_by_id(self.project, stackup_id)
        if stackup is None:
            return DetailEditResult(False, "Load or create a stackup before editing the detail table.")
        try:
            message = _apply_detail_edit(stackup, row, column, value)
            calculate_stackup(stackup, self.project.settings)
        except ValueError as exc:
            return DetailEditResult(False, str(exc))

        self.workspace = CadToleranceWorkspaceViewModel.from_project(self.project)
        self.workspace.select_stackup(stackup_id)
        self.summary_model.set_rows(self.workspace.summary_rows)
        self._refresh_dashboard()
        self._update_detail_outputs(stackup_id)
        rows = self.workspace.detail_rows(stackup_id)
        return DetailEditResult(True, message, rows)

    def _refresh_dashboard(self) -> None:
        badges = self.workspace.dashboard_badges
        self.dashboard_badges.set_values(
            badges.objectives_met,
            badges.objectives_not_met,
            badges.sigma_rollup,
        )
        self.summary_contributions.set_rows(
            self.workspace.contribution_rows(self.workspace.selected_stackup_id),
            "Contributions Rollup",
        )

    def _start_new_stackup_workflow(self) -> None:
        self.workflow_controller = GuidedStackupWorkflowController(
            self.geometry_session,
            self.project,
        )
        update = self.workflow_controller.start_new_stackup()
        self._apply_workflow_update(update)

    def handle_viewer_selections(self, selections: list[CadViewerSelection] | tuple[CadViewerSelection, ...]) -> None:
        if self.workflow_controller is None or not selections:
            return
        try:
            update = self.workflow_controller.apply_selection(selections[0])
        except ValueError as exc:
            self.statusBar().showMessage(str(exc))
            return
        self._apply_workflow_update(update)

    def _apply_workflow_update(self, update) -> None:
        self.viewport_host.set_workflow_toolbar_state(update.toolbar)
        if hasattr(self.viewer, "set_selection_modes"):
            self.viewer.set_selection_modes(update.selection_filter.viewer_mode_set)  # type: ignore[attr-defined]
        if hasattr(self.geometry_session, "set_selection_filter"):
            self.geometry_session.set_selection_filter(update.selection_filter.shape_kind_set)
        for highlight in update.highlights:
            if hasattr(self.viewer, "highlight"):
                self.viewer.highlight(highlight.shape_reference, highlight.role)  # type: ignore[attr-defined]
        self.statusBar().showMessage(update.selection_filter.prompt)
        if update.stackup is not None:
            self.workspace = CadToleranceWorkspaceViewModel.from_project(self.project)
            self.summary_model.set_rows(self.workspace.summary_rows)
            self._set_detail_stackup(update.stackup.id)
            self._refresh_dashboard()
            self.add_feature_action.setEnabled(True)
            self.generate_report_action.setEnabled(True)

    def show_summary(self) -> None:
        self.analysis_stack.setCurrentWidget(self.summary_page)

    def _open_dialog(self) -> None:
        path, selected_filter = QFileDialog.getOpenFileName(
            self,
            "Open neutral CAD file or CAD tolerance project",
            "",
            f"{PROJECT_FILTER};;{PACKAGE_FILTER};;{NEUTRAL_CAD_FILTER}",
        )
        if not path:
            return
        suffix = Path(path).suffix.lower()
        if selected_filter == PACKAGE_FILTER or suffix == PACKAGE_SUFFIX:
            try:
                self._open_package_file(path)
            except Exception as exc:
                QMessageBox.warning(self, "Project package import failed", str(exc))
            return
        if selected_filter == PROJECT_FILTER or suffix == ".tolproj":
            try:
                self.load_project_file(path)
            except Exception as exc:
                QMessageBox.warning(self, "Project load failed", str(exc))
            return
        self.open_cad_file(path)

    def _open_package_file(self, path: str | Path) -> None:
        package_path = Path(path)
        output_dir = package_path.with_suffix("")
        project_path = import_project_package(package_path, output_dir)
        self.load_project_file(project_path)

    def _save_project(self) -> None:
        if self.project_path is None:
            path, _selected_filter = QFileDialog.getSaveFileName(
                self,
                "Save CAD tolerance project",
                "",
                PROJECT_FILTER,
            )
            if not path:
                return
            self.project_path = save_project(self.project, path)
        else:
            save_project(self.project, self.project_path)
        self.statusBar().showMessage(f"Saved project {self.project_path.name}")

    def _open_add_geometric_tolerance_dialog(self) -> None:
        stackup = _stackup_by_id(self.project, self.workspace.selected_stackup_id)
        if stackup is None:
            self.statusBar().showMessage("Load or create a stackup before adding GD&T.")
            return
        default_feature = self._selected_detail_feature_name()
        dialog = self.geometric_dialog_factory(
            _controlled_feature_names(stackup),
            self,
            default_feature=default_feature,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.add_geometric_tolerance(
                dialog.controlled_feature(),
                dialog.control_type(),
                dialog.tolerance_value(),
                dialog.datum_references(),
            )
        except ValueError as exc:
            self.statusBar().showMessage(str(exc))

    def add_geometric_tolerance(
        self,
        controlled_feature: str,
        control_type: GeometricControlType | str,
        tolerance_value: float,
        datum_references: list[str] | tuple[str, ...],
    ) -> StackupContributor:
        stackup_id = self.workspace.selected_stackup_id
        stackup = _stackup_by_id(self.project, stackup_id)
        if stackup is None:
            raise ValueError("Load or create a stackup before adding GD&T.")
        datums = list(datum_references)
        if not controlled_feature.strip():
            raise ValueError("Controlled feature is required.")
        if not datums:
            raise ValueError("At least one datum/reference is required.")

        control = GeometricControlType(str(control_type))
        geometric = GeometricTolerance(
            control_type=control,
            tolerance_value=_parse_positive_float(tolerance_value, "Geometric tolerance"),
            datum_references=datums,
        )
        source_feature = _feature_by_display_name(stackup, controlled_feature)
        contributor = StackupContributor(
            _manual_gdt_contributor_name(control, controlled_feature, datums),
            nominal=0.0,
            tolerance=0.0,
            tolerance_type=ToleranceType.GEOMETRIC,
            datum_references=datums,
            source_feature=source_feature,
            geometric_tolerance=geometric,
            source_note="Manual GD&T row.",
        )
        stackup.contributors.append(contributor)
        calculate_stackup(stackup, self.project.settings)
        message = (
            f"Added {geometric_control_display_label(control)} {geometric.tolerance_value:g} "
            f"to {controlled_feature}."
        )
        self._rebuild_workspace_after_project_edit(stackup.id, message)
        return contributor

    def _selected_detail_feature_name(self) -> str:
        index = self.detail_table.currentIndex()
        if not index.isValid():
            return ""
        row = index.data(Qt.ItemDataRole.UserRole)
        if isinstance(row, StackupDetailRow):
            return row.name
        return ""

    def _rebuild_workspace_after_project_edit(self, stackup_id: str, message: str) -> None:
        self.workspace = CadToleranceWorkspaceViewModel.from_project(self.project)
        self.summary_model.set_rows(self.workspace.summary_rows)
        self._set_detail_stackup(stackup_id)
        self._refresh_dashboard()
        self.statusBar().showMessage(message)

    def _package_project(self) -> None:
        if self.project_path is None:
            project_path, _selected_filter = QFileDialog.getSaveFileName(
                self,
                "Save CAD tolerance project",
                "",
                PROJECT_FILTER,
            )
            if not project_path:
                return
            self.project_path = save_project(self.project, project_path)
        else:
            save_project(self.project, self.project_path)

        default_package = self.project_path.with_suffix(PACKAGE_SUFFIX)
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Package Project",
            str(default_package),
            PACKAGE_FILTER,
        )
        if not path:
            return
        try:
            package_path = export_project_package(self.project_path, path)
        except Exception as exc:
            QMessageBox.warning(self, "Project package export failed", str(exc))
            self.statusBar().showMessage("Project package export failed")
            return
        self.statusBar().showMessage(f"Packaged project {package_path.name}")

    def _save_snapshot(self) -> None:
        default_path = ""
        if self.project_path is not None:
            default_path = str(
                project_asset_dir(self.project_path)
                / "snapshots"
                / "snapshot_summary_1.png"
            )
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save CAD viewer snapshot",
            default_path,
            "PNG image (*.png);;JPEG image (*.jpg *.jpeg)",
        )
        if not path:
            return
        output_path = Path(path)
        if output_path.suffix == "":
            output_path = output_path.with_suffix(".png")
        try:
            stackup_id = self.workspace.selected_stackup_id
            annotation_positions = {}
            if stackup_id:
                annotation_positions[stackup_id] = self.workspace.annotation_position(stackup_id)
            stackup = _stackup_by_id(self.project, stackup_id)
            shape_ids, feature_ids = _snapshot_reference_ids(stackup)
            warning_ids = tuple(warning.id for warning in self.workspace.warnings(stackup_id))
            snapshot = self.viewer.capture_snapshot(
                SnapshotRequest(
                    output_path,
                    visible_stackup_ids=(stackup_id,) if stackup_id else (),
                    annotation_positions=annotation_positions,
                    highlight_shape_ids=shape_ids,
                    highlight_feature_ids=feature_ids,
                    warning_ids=warning_ids,
                    artifact_metadata={
                        "purpose": "cad_1d_tolerance_report",
                        "stackup_id": stackup_id,
                        "image_role": "annotated_model_snapshot",
                    },
                )
            )  # type: ignore[attr-defined]
        except Exception as exc:
            QMessageBox.warning(self, "Snapshot failed", str(exc))
            self.statusBar().showMessage("Snapshot failed")
            return
        if self.project_path is not None and snapshot.image_path:
            snapshot.image_path = project_relative_path(
                snapshot.image_path,
                self.project_path,
            )
        self.project.snapshots.append(snapshot)
        if self.project.stackups:
            self.workspace = CadToleranceWorkspaceViewModel.from_project(self.project)
        self.statusBar().showMessage(f"Saved snapshot {Path(snapshot.image_path).name}")

    def _generate_report(self) -> None:
        default_path = ""
        if self.project_path is not None:
            default_path = str(
                project_asset_dir(self.project_path) / "reports" / "report.html"
            )
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save Report",
            default_path,
            "HTML report (*.html);;All Files (*.*)",
        )
        if not path:
            return
        output_path = Path(path)
        if output_path.suffix == "":
            output_path = output_path.with_suffix(".html")
        try:
            result = generate_html_report(self.project, output_path)
        except Exception as exc:
            QMessageBox.warning(self, "Report generation failed", str(exc))
            self.statusBar().showMessage("Report generation failed")
            return
        self.statusBar().showMessage(f"Generated report {result.output_path.name}")


def _cad_import_settings_from_document(
    document: CadDocument,
    project: CadToleranceProject,
) -> CadImportSettings:
    settings = dict(document.import_settings)
    return CadImportSettings(
        units=str(settings.get("units") or document.units or project.unit_system),
        heal_shapes=bool(settings.get("heal_shapes", True)),
        object_filter=str(settings.get("object_filter") or "solids"),
        include_edges=bool(settings.get("include_edges", True)),
        include_vertices=bool(settings.get("include_vertices", True)),
    )


def _stackup_by_id(project: CadToleranceProject, stackup_id: str) -> StackupRequirement | None:
    for stackup in project.stackups:
        if stackup.id == stackup_id:
            return stackup
    return None


def _snapshot_reference_ids(stackup: StackupRequirement | None) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if stackup is None:
        return (), ()
    feature_ids: list[str] = []
    shape_ids: list[str] = []

    def collect(feature) -> None:
        if feature is None:
            return
        if feature.id and feature.id not in feature_ids:
            feature_ids.append(feature.id)
        shape = feature.shape_reference
        if shape is not None and shape.id and shape.id not in shape_ids:
            shape_ids.append(shape.id)

    collect(stackup.start_feature)
    collect(stackup.end_feature)
    for feature in stackup.loop_features:
        collect(feature)
    for feature in stackup.constraint_features:
        collect(feature)
    for contributor in stackup.contributors:
        collect(contributor.source_feature)
    return tuple(shape_ids), tuple(feature_ids)


def _summary_by_id(rows: list[StackupSummaryRow], stackup_id: str) -> StackupSummaryRow | None:
    for row in rows:
        if row.stackup_id == stackup_id:
            return row
    return None


def _apply_detail_edit(
    stackup: StackupRequirement,
    row: StackupDetailRow,
    column: int,
    value: str,
) -> str:
    contributor = _contributor_by_id(stackup, row.contributor_id)
    if contributor is None:
        raise ValueError("The edited detail row no longer exists.")
    text = value.strip()

    if column == 0:
        if not text:
            raise ValueError("Name cannot be empty.")
        if row.row_type == "feature" and contributor.source_feature is not None:
            contributor.source_feature.name = text
            return f"Updated controlled feature name to {text}."
        contributor.name = text
        return _edit_status_message(contributor, "name")

    if column == 1:
        contributor.sensitivity = _parse_finite_float(text, "Sensitivity")
        return _edit_status_message(contributor, "sensitivity")

    if column == 2:
        contributor.nominal = _parse_finite_float(text, "Nominal")
        return _edit_status_message(contributor, "nominal")

    if column == 3:
        _apply_tolerance_text(contributor, text)
        return _edit_status_message(contributor, "tolerance")

    if column == 4:
        datums = _parse_datum_tokens(text)
        contributor.datum_references = datums
        if contributor.geometric_tolerance is not None:
            contributor.geometric_tolerance.datum_references = datums
        if row.row_type == "feature" and contributor.source_feature is not None:
            contributor.source_feature.datum_label = datums[0] if datums else ""
        return _edit_status_message(contributor, "datum")

    raise ValueError("This detail column is not editable.")


def _apply_tolerance_text(contributor: StackupContributor, text: str) -> None:
    if not text:
        raise ValueError("Tolerance cannot be empty.")
    mode_text, body = _split_tolerance_mode(text)
    mode = mode_text or _infer_tolerance_mode(body, contributor)
    if mode == ToleranceType.SYMMETRIC.value:
        tolerance = _parse_symmetric_tolerance(body)
        contributor.tolerance_type = ToleranceType.SYMMETRIC
        contributor.tolerance = tolerance
        contributor.tolerance_minus = tolerance
        contributor.tolerance_plus = tolerance
        contributor.geometric_tolerance = None
        return
    if mode == ToleranceType.LIMITS.value:
        minus, plus = _parse_limits_tolerance(body)
        contributor.tolerance_type = ToleranceType.LIMITS
        contributor.tolerance = max(minus, plus)
        contributor.tolerance_minus = minus
        contributor.tolerance_plus = plus
        contributor.geometric_tolerance = None
        return
    if mode == ToleranceType.GEOMETRIC.value:
        control, tolerance, datums = _parse_geometric_tolerance(body, contributor)
        geometric = GeometricTolerance(
            control_type=control,
            tolerance_value=tolerance,
            datum_references=datums,
        )
        contributor.tolerance_type = ToleranceType.GEOMETRIC
        contributor.tolerance = max(
            float(geometric.derived_minus or 0.0),
            float(geometric.derived_plus or 0.0),
        )
        contributor.tolerance_minus = geometric.derived_minus
        contributor.tolerance_plus = geometric.derived_plus
        contributor.datum_references = datums
        contributor.geometric_tolerance = geometric
        return
    raise ValueError(f"Unsupported tolerance mode: {mode}")


def _split_tolerance_mode(text: str) -> tuple[str, str]:
    raw = text.strip()
    lowered = raw.lower()
    aliases = {
        "sym": ToleranceType.SYMMETRIC.value,
        "symmetric": ToleranceType.SYMMETRIC.value,
        "pm": ToleranceType.SYMMETRIC.value,
        "limits": ToleranceType.LIMITS.value,
        "limit": ToleranceType.LIMITS.value,
        "asymmetric": ToleranceType.LIMITS.value,
        "geometric": ToleranceType.GEOMETRIC.value,
        "gdt": ToleranceType.GEOMETRIC.value,
        "gd&t": ToleranceType.GEOMETRIC.value,
    }
    for prefix, mode in aliases.items():
        if lowered == prefix:
            return mode, ""
        if lowered.startswith(prefix + ":"):
            return mode, raw[len(prefix) + 1 :].strip()
        if lowered.startswith(prefix + " "):
            return mode, raw[len(prefix) + 1 :].strip()
    return "", raw


def _infer_tolerance_mode(text: str, contributor: StackupContributor) -> str:
    lowered = text.lower().strip()
    if lowered.startswith(("runout", "position", "profile", "manual", "dia ")):
        return ToleranceType.GEOMETRIC.value
    if "+/-" in lowered or "+-" in lowered:
        return ToleranceType.SYMMETRIC.value
    if "/" in lowered and "+" in lowered and "-" in lowered:
        return ToleranceType.LIMITS.value
    if contributor.tolerance_type == ToleranceType.GEOMETRIC:
        return ToleranceType.GEOMETRIC.value
    return ToleranceType.SYMMETRIC.value


def _parse_symmetric_tolerance(text: str) -> float:
    body = text.strip()
    if not body:
        raise ValueError("Symmetric tolerance value is required.")
    body = (
        body.replace("+/-", " ")
        .replace("+-", " ")
        .replace("dia", " ")
        .replace("diameter", " ")
    )
    numbers = _extract_numbers(body)
    if not numbers:
        raise ValueError("Symmetric tolerance value is required.")
    value = abs(numbers[-1])
    if value < 0.0:
        raise ValueError("Tolerance must be non-negative.")
    return value


def _parse_limits_tolerance(text: str) -> tuple[float, float]:
    signed = re.findall(r"([+-]\s*\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)", text)
    minus = None
    plus = None
    for token in signed:
        compact = token.replace(" ", "")
        number = float(compact)
        if compact.startswith("+"):
            plus = abs(number)
        else:
            minus = abs(number)
    if minus is not None and plus is not None:
        return minus, plus
    numbers = [abs(number) for number in _extract_numbers(text)]
    if len(numbers) >= 2:
        return numbers[0], numbers[1]
    raise ValueError("Limits tolerance must include minus and plus values.")


def _parse_geometric_tolerance(
    text: str,
    contributor: StackupContributor,
) -> tuple[GeometricControlType, float, list[str]]:
    raw = text.strip()
    lowered = raw.lower()
    control = (
        contributor.geometric_tolerance.control_type
        if contributor.geometric_tolerance is not None
        else GeometricControlType.MANUAL
    )
    for candidate in GeometricControlType:
        label = candidate.value
        if lowered == label or lowered.startswith(label + " "):
            control = candidate
            raw = raw[len(label) :].strip()
            lowered = raw.lower()
            break
    if lowered.startswith("dia "):
        raw = raw[4:].strip()
    numbers = _extract_numbers(raw)
    if not numbers:
        raise ValueError("Geometric tolerance value is required.")
    tolerance = abs(numbers[0])
    if tolerance <= 0.0:
        raise ValueError("Geometric tolerance must be positive.")
    match = _NUMBER_RE.search(raw)
    remainder = raw[match.end() :] if match else ""
    datums = _parse_datum_tokens(remainder)
    if not datums:
        datums = list(contributor.datum_references)
    if not datums and contributor.geometric_tolerance is not None:
        datums = list(contributor.geometric_tolerance.datum_references)
    if not datums:
        raise ValueError("Geometric tolerance requires at least one datum/reference.")
    return control, tolerance, datums


def _parse_datum_tokens(text: str) -> list[str]:
    blocked = {
        "dia",
        "diameter",
        "runout",
        "position",
        "profile",
        "manual",
        "to",
        "datum",
        "reference",
    }
    tokens: list[str] = []
    for raw in re.split(r"[\s,;/]+", str(text).strip()):
        token = raw.strip().strip("[]()")
        if not token or token.lower() in blocked:
            continue
        if _NUMBER_RE.fullmatch(token):
            continue
        normalized = token.upper()
        if normalized not in tokens:
            tokens.append(normalized)
    return tokens


def _parse_finite_float(value: Any, label: str) -> float:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric.") from exc
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite.")
    return number


def _parse_positive_float(value: Any, label: str) -> float:
    number = _parse_finite_float(value, label)
    if number <= 0.0:
        raise ValueError(f"{label} must be positive.")
    return number


_NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")


def _extract_numbers(text: str) -> list[float]:
    return [float(match.group(0)) for match in _NUMBER_RE.finditer(text)]


def _contributor_by_id(
    stackup: StackupRequirement,
    contributor_id: str,
) -> StackupContributor | None:
    for contributor in stackup.contributors:
        if contributor.id == contributor_id:
            return contributor
    return None


def _controlled_feature_names(stackup: StackupRequirement) -> list[str]:
    names: list[str] = []
    for contributor in stackup.contributors:
        feature = contributor.source_feature
        for name in (
            feature.name if feature is not None else "",
            contributor.name,
        ):
            if name and name not in names:
                names.append(name)
    return names


def _feature_by_display_name(
    stackup: StackupRequirement,
    feature_name: str,
) -> FeatureReference | None:
    wanted = feature_name.strip()
    if not wanted:
        return None
    for contributor in stackup.contributors:
        feature = contributor.source_feature
        if feature is None:
            continue
        names = [
            feature.name,
            feature.shape_reference.fallback_display_name if feature.shape_reference else "",
            contributor.name,
        ]
        if any(name == wanted for name in names):
            return feature
    return None


def _manual_gdt_contributor_name(
    control_type: GeometricControlType,
    feature_name: str,
    datum_references: list[str],
) -> str:
    datum_text = ", ".join(datum_references)
    label = geometric_control_display_label(control_type).title()
    return f"{label} {feature_name} to {datum_text}"


def _edit_status_message(contributor: StackupContributor, field: str) -> str:
    message = f"Updated {contributor.name} {field}; results recalculated."
    if contributor.shared_with_stackup_ids:
        message += " Shared dimension affects: " + ", ".join(
            contributor.shared_with_stackup_ids
        )
    return message


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
        QLabel#ResultPanelMetrics {
            color: #333333;
            font-size: 10px;
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
        if path.suffix.lower() == PACKAGE_SUFFIX:
            window._open_package_file(path)
        elif path.suffix.lower() == ".tolproj":
            window.load_project_file(path)
        else:
            window.open_cad_file(path)
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
