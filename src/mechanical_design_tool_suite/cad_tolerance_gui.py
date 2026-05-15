"""Qt Widgets shell for CAD-based 1D tolerance analysis."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import math
from pathlib import Path
import re
import sys
from typing import Any

try:
    from PyQt6.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt, pyqtSignal
    from PyQt6.QtGui import (
        QAction,
        QColor,
        QFont,
        QFontDatabase,
        QIcon,
        QImage,
        QMouseEvent,
        QPainter,
        QPainterPath,
        QPen,
        QPalette,
        QPixmap,
    )
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
    validate_cad_source_reimport,
)
from .cad_geometry_occ import CadKernelUnavailable, OccCadGeometrySession
from .cad_stackup_workflow import GuidedStackupWorkflowController, GuidedToolbarState
from .cad_tolerance_methods import calculate_stackup
from .cad_tolerance_models import (
    CadDocument,
    CadSourceStatus,
    CadToleranceProject,
    FeatureReference,
    GeometricControlType,
    GeometricTolerance,
    ShapeKind,
    Snapshot,
    StackupContributor,
    StackupRequirement,
    ResultStatus,
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
from .cad_tolerance_report import (
    ReportGenerationResult,
    ResultDisplayProjection,
    generate_html_report,
)
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
from .cad_viewer_api import (
    CadCameraState,
    CadViewer,
    CadViewerSelection,
    CadViewerUnavailable,
    HighlightRole,
    SnapshotRequest,
    StandardView,
    ViewerAnnotation,
    ViewerAnnotationAnchor,
    ViewerAnnotationRole,
    ViewerSelectionMode,
)
from .cad_viewer_occ import OccCadViewerWidget


NEUTRAL_CAD_FILTER = (
    "Neutral CAD files (*.step *.stp *.iges *.igs);;"
    "STEP files (*.step *.stp);;"
    "IGES files (*.iges *.igs)"
)
PROJECT_FILTER = "CAD tolerance projects (*.tolproj)"
PACKAGE_FILTER = "CAD tolerance packages (*.tolpack)"
SOURCE_STATUS_LABELS = {
    CadSourceStatus.PRESENT: "Present",
    CadSourceStatus.MISSING: "Missing",
    CadSourceStatus.RELOCATED: "Relocated",
    CadSourceStatus.CHANGED_HASH: "Changed",
    CadSourceStatus.CHANGED_TOPOLOGY: "Topology changed",
    CadSourceStatus.PROJECT_LOCAL_PACKAGE_ASSET: "Project-local asset",
    CadSourceStatus.UNKNOWN: "Unknown",
}


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
        self._annotations: tuple[ViewerAnnotation, ...] = ()

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

    def set_annotations(self, annotations: Any) -> None:
        self._annotations = tuple(annotations)

    @property
    def annotations(self) -> tuple[ViewerAnnotation, ...]:
        return self._annotations

    def camera_state(self) -> CadCameraState:
        return CadCameraState(view_name=str(self.property("standardView") or "placeholder"))

    def capture_snapshot(self, request: SnapshotRequest) -> Snapshot:
        output_path = Path(request.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image = self.grab()
        image.save(str(output_path))
        annotation_positions = dict(request.annotation_positions)
        annotations = request.annotations or self._annotations
        if annotations:
            annotation_positions["_viewer_annotations"] = [
                annotation.to_dict() for annotation in annotations
            ]
        return Snapshot(
            image_path=str(output_path),
            camera=self.camera_state().to_dict(),
            visible_stackup_ids=list(request.visible_stackup_ids),
            annotation_positions=annotation_positions,
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

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.setObjectName("ImportDialogButtons")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button is not None:
            ok_button.setEnabled(is_supported_neutral_cad(self._path))
        layout.addWidget(self.buttons)

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
            "source_mode": self.import_type_combo.currentData(),
            "object_filters": filters,
            "object_filter": ",".join(label.lower().replace(" ", "_") for label in filters),
            "assembly_option": self.assembly_combo.currentText(),
            "part_option": self.part_combo.currentText(),
        }

    def _options_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        import_group = QGroupBox("Import Type")
        import_layout = QGridLayout(import_group)
        self.import_type_combo = QComboBox()
        self.import_type_combo.addItem("Reference neutral CAD source", "reference")
        self.import_type_combo.addItem("Convert neutral CAD geometry", "convert")
        import_layout.addWidget(QLabel("Type"), 0, 0)
        import_layout.addWidget(self.import_type_combo, 0, 1)
        self.units_combo = QComboBox()
        self.units_combo.addItems(["From source", "Millimeters", "Inches", "Centimeters"])
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
        name_edit = QLineEdit(self._path.name)
        name_edit.setReadOnly(True)
        path_edit = QLineEdit(str(self._path))
        path_edit.setReadOnly(True)
        type_edit = QLineEdit("STEP / IGES neutral CAD")
        type_edit.setReadOnly(True)
        file_layout.addWidget(QLabel("File Name"), 0, 0)
        file_layout.addWidget(name_edit, 0, 1)
        file_layout.addWidget(QLabel("File Location"), 1, 0)
        file_layout.addWidget(path_edit, 1, 1)
        file_layout.addWidget(QLabel("Files of Type"), 2, 0)
        file_layout.addWidget(type_edit, 2, 1)
        layout.addWidget(file_group)
        layout.addStretch(1)
        return tab

    def _select_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("Objects selected by the neutral CAD B-Rep import filters:"))
        for label in self.OBJECT_FILTER_LABELS:
            layout.addWidget(QLabel(label))
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


class _ViewerAnnotationCanvas(QWidget):
    """Paints leader lines and arrowheads for viewport annotations."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ViewerAnnotationCanvas")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self._annotations: tuple[ViewerAnnotation, ...] = ()

    def set_annotations(self, annotations: tuple[ViewerAnnotation, ...]) -> None:
        self._annotations = annotations
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        if not self._annotations:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        _paint_annotations(painter, self.size(), self._annotations, draw_labels=False)


class _DraggableAnnotationLabel(QLabel):
    moved = pyqtSignal(str, object)

    def __init__(self, annotation: ViewerAnnotation, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ViewerAnnotationLabel")
        self._annotation_id = annotation.id
        self._draggable = annotation.draggable
        self._press_offset = QPoint()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_annotation(annotation)

    def set_annotation(self, annotation: ViewerAnnotation) -> None:
        self._annotation_id = annotation.id
        self._draggable = annotation.draggable
        self.setText(annotation.label)
        color = _annotation_color(annotation.role)
        self.setStyleSheet(
            "QLabel#ViewerAnnotationLabel {"
            f"color: {color.name()};"
            "background: rgba(238, 238, 238, 185);"
            f"border: 1px solid {color.name()};"
            "padding: 1px 4px;"
            "font-weight: 700;"
            "}"
        )
        self.adjustSize()
        self.setCursor(Qt.CursorShape.OpenHandCursor if annotation.draggable else Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        if not self._draggable or event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        self._press_offset = event.position().toPoint()
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        if not self._draggable or not event.buttons() & Qt.MouseButton.LeftButton:
            super().mouseMoveEvent(event)
            return
        parent = self.parentWidget()
        if parent is None:
            return
        proposed = self.mapToParent(event.position().toPoint() - self._press_offset)
        x = max(0, min(proposed.x(), parent.width() - self.width()))
        y = max(0, min(proposed.y(), parent.height() - self.height()))
        self.move(x, y)
        self.moved.emit(self._annotation_id, _normalized_label_position(self))
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        if self._draggable and event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.moved.emit(self._annotation_id, _normalized_label_position(self))
            event.accept()
            return
        super().mouseReleaseEvent(event)


class _ViewCubeWidget(QFrame):
    viewRequested = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ViewCubeWidget")
        self.setToolTip("Set isometric view")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(68, 60)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.LeftButton:
            self.viewRequested.emit(StandardView.ISO)
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        top = [QPoint(16, 14), QPoint(38, 6), QPoint(58, 16), QPoint(34, 25)]
        front = [QPoint(16, 14), QPoint(34, 25), QPoint(34, 50), QPoint(16, 39)]
        right = [QPoint(34, 25), QPoint(58, 16), QPoint(58, 40), QPoint(34, 50)]
        painter.setPen(QPen(QColor("#8f8f8f"), 1))
        painter.setBrush(QColor("#efefef"))
        painter.drawPolygon(*top)
        painter.setBrush(QColor("#d8d8d8"))
        painter.drawPolygon(*front)
        painter.setBrush(QColor("#c9c9c9"))
        painter.drawPolygon(*right)
        painter.setPen(QPen(QColor("#555555"), 1))
        font = painter.font()
        font.setPointSize(6)
        painter.setFont(font)
        painter.drawText(QRect(14, 24, 23, 14), Qt.AlignmentFlag.AlignCenter, "FRONT")
        painter.drawText(QRect(36, 23, 22, 14), Qt.AlignmentFlag.AlignCenter, "RIGHT")
        painter.end()


class _AxisTriadWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("AxisTriadWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFixedSize(64, 56)

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        origin = QPoint(19, 39)
        axes = (
            ("X", QPoint(52, 41), QColor("#c00000")),
            ("Y", QPoint(19, 9), QColor("#18a51d")),
            ("Z", QPoint(8, 48), QColor("#192fd6")),
        )
        for label, end, color in axes:
            painter.setPen(QPen(color, 2))
            painter.drawLine(origin, end)
            _draw_small_arrow_head(painter, origin, end, color)
            painter.drawText(QRect(end.x() - 7, end.y() - 9, 16, 14), Qt.AlignmentFlag.AlignCenter, label)
        painter.setPen(QPen(QColor("#333333"), 1))
        painter.setBrush(QColor("#333333"))
        painter.drawEllipse(origin, 2, 2)
        painter.end()


def _draw_small_arrow_head(painter: QPainter, tail: QPoint, tip: QPoint, color: QColor) -> None:
    dx = tip.x() - tail.x()
    dy = tip.y() - tail.y()
    length = math.hypot(dx, dy)
    if length <= 0.1:
        return
    ux = dx / length
    uy = dy / length
    px = -uy
    py = ux
    head = 6.0
    spread = 3.0
    left = QPointF(tip.x() - ux * head + px * spread, tip.y() - uy * head + py * spread)
    right = QPointF(tip.x() - ux * head - px * spread, tip.y() - uy * head - py * spread)
    painter.setBrush(color)
    painter.drawPolygon(tip, left.toPoint(), right.toPoint())


def _chrome_icon(kind: str, size: int = 24) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    rect = pixmap.rect().adjusted(3, 3, -3, -3)
    dark = QColor("#202020")
    gray = QColor("#707070")
    blue = QColor("#0070c0")
    green = QColor("#109020")
    red = QColor("#b82828")

    if kind == "new_stackup":
        painter.setPen(QPen(dark, 2))
        painter.drawLine(rect.left(), rect.center().y(), rect.right(), rect.center().y())
        painter.drawLine(rect.right() - 5, rect.center().y() - 4, rect.right(), rect.center().y())
        painter.drawLine(rect.right() - 5, rect.center().y() + 4, rect.right(), rect.center().y())
        painter.setBrush(green)
        painter.setPen(QPen(green.darker(130), 1))
        painter.drawEllipse(rect.left(), rect.top(), 9, 9)
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        painter.drawLine(rect.left() + 4, rect.top() + 2, rect.left() + 4, rect.top() + 7)
        painter.drawLine(rect.left() + 2, rect.top() + 4, rect.left() + 7, rect.top() + 4)
    elif kind == "add_feature":
        painter.setPen(QPen(gray, 2))
        painter.drawLine(rect.left(), rect.center().y(), rect.right(), rect.center().y())
        painter.drawLine(rect.right() - 5, rect.center().y() - 4, rect.right(), rect.center().y())
        painter.drawLine(rect.right() - 5, rect.center().y() + 4, rect.right(), rect.center().y())
        painter.setBrush(QColor("#d6d6d6"))
        painter.setPen(QPen(QColor("#b5b5b5"), 1))
        painter.drawEllipse(rect.left(), rect.top(), 9, 9)
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        painter.drawLine(rect.left() + 4, rect.top() + 2, rect.left() + 4, rect.top() + 7)
        painter.drawLine(rect.left() + 2, rect.top() + 4, rect.left() + 7, rect.top() + 4)
    elif kind == "snapshot":
        painter.setBrush(dark)
        painter.setPen(QPen(dark, 1))
        painter.drawRoundedRect(rect.adjusted(1, 4, -1, -2), 2, 2)
        painter.drawRect(rect.left() + 5, rect.top() + 2, 8, 4)
        painter.setBrush(QColor("#f6f6f6"))
        painter.drawEllipse(rect.center(), 4, 4)
    elif kind == "report":
        painter.setBrush(QColor("#e9e9e9"))
        painter.setPen(QPen(QColor("#b8b8b8"), 1))
        painter.drawRect(rect.adjusted(3, 0, -2, 0))
        painter.setPen(QPen(gray, 1))
        for y in (8, 12, 16):
            painter.drawLine(rect.left() + 8, rect.top() + y, rect.right() - 5, rect.top() + y)
        painter.setBrush(QColor("#d6d6d6"))
        painter.setPen(QPen(QColor("#b5b5b5"), 1))
        painter.drawEllipse(rect.left(), rect.top(), 8, 8)
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        painter.drawLine(rect.left() + 4, rect.top() + 2, rect.left() + 4, rect.top() + 6)
        painter.drawLine(rect.left() + 2, rect.top() + 4, rect.left() + 6, rect.top() + 4)
    elif kind == "import":
        painter.setPen(QPen(green, 2))
        painter.drawLine(rect.left(), rect.center().y(), rect.right() - 3, rect.center().y())
        painter.drawLine(rect.left(), rect.center().y(), rect.left() + 5, rect.center().y() - 5)
        painter.drawLine(rect.left(), rect.center().y(), rect.left() + 5, rect.center().y() + 5)
        painter.setPen(QPen(gray, 1))
        painter.drawRect(rect.adjusted(6, 3, -2, -3))
    elif kind == "export":
        painter.setPen(QPen(red, 2))
        painter.drawLine(rect.left() + 3, rect.center().y(), rect.right(), rect.center().y())
        painter.drawLine(rect.right(), rect.center().y(), rect.right() - 5, rect.center().y() - 5)
        painter.drawLine(rect.right(), rect.center().y(), rect.right() - 5, rect.center().y() + 5)
        painter.setPen(QPen(gray, 1))
        painter.drawRect(rect.adjusted(2, 3, -6, -3))
    elif kind == "open":
        painter.setBrush(QColor("#f4cf64"))
        painter.setPen(QPen(QColor("#a5831c"), 1))
        painter.drawRect(rect.adjusted(0, 5, 0, -1))
        painter.drawRect(rect.left() + 2, rect.top() + 2, 9, 5)
    elif kind == "save":
        painter.setBrush(QColor("#e8e8e8"))
        painter.setPen(QPen(gray, 1))
        painter.drawRect(rect)
        painter.fillRect(rect.adjusted(4, 3, -4, -11), QColor("#637d9a"))
        painter.fillRect(rect.adjusted(5, 14, -5, -3), QColor("#ffffff"))
    elif kind == "settings":
        painter.setPen(QPen(dark, 2))
        painter.drawEllipse(rect.center(), 5, 5)
        for angle in range(0, 360, 45):
            radians = math.radians(angle)
            start = QPointF(rect.center().x() + math.cos(radians) * 7, rect.center().y() + math.sin(radians) * 7)
            end = QPointF(rect.center().x() + math.cos(radians) * 10, rect.center().y() + math.sin(radians) * 10)
            painter.drawLine(start, end)
    elif kind == "refresh":
        painter.setPen(QPen(blue, 2))
        painter.drawArc(rect, 35 * 16, 270 * 16)
        painter.drawLine(rect.right() - 4, rect.top() + 5, rect.right(), rect.top() + 5)
        painter.drawLine(rect.right(), rect.top() + 5, rect.right() - 1, rect.top() + 10)
    elif kind == "reattach":
        painter.setBrush(QColor("#f4cf64"))
        painter.setPen(QPen(QColor("#a5831c"), 1))
        painter.drawRect(rect.adjusted(0, 5, 0, -1))
        painter.setPen(QPen(blue, 2))
        painter.drawLine(rect.left() + 5, rect.center().y(), rect.right() - 4, rect.center().y())
    elif kind in {"iso", "front", "top", "right"}:
        painter.setBrush(QColor("#ededed"))
        painter.setPen(QPen(gray, 1))
        if kind == "iso":
            painter.drawPolygon(
                QPoint(rect.center().x(), rect.top()),
                QPoint(rect.right(), rect.center().y()),
                QPoint(rect.center().x(), rect.bottom()),
                QPoint(rect.left(), rect.center().y()),
            )
        elif kind == "front":
            painter.drawRect(rect.adjusted(2, 4, -2, -4))
        elif kind == "top":
            painter.drawRect(rect.adjusted(1, 2, -1, -8))
        else:
            painter.drawRect(rect.adjusted(6, 2, -6, -2))
    elif kind == "pan":
        painter.setPen(QPen(dark, 2))
        painter.drawLine(rect.center().x(), rect.top(), rect.center().x(), rect.bottom())
        painter.drawLine(rect.left(), rect.center().y(), rect.right(), rect.center().y())
        painter.drawLine(rect.center().x(), rect.top(), rect.center().x() - 4, rect.top() + 4)
        painter.drawLine(rect.center().x(), rect.top(), rect.center().x() + 4, rect.top() + 4)
    elif kind == "zoom":
        painter.setPen(QPen(dark, 2))
        painter.drawEllipse(rect.left() + 2, rect.top() + 2, 10, 10)
        painter.drawLine(rect.left() + 11, rect.top() + 11, rect.right(), rect.bottom())
        painter.drawLine(rect.left() + 5, rect.top() + 7, rect.left() + 10, rect.top() + 7)
        painter.drawLine(rect.left() + 7, rect.top() + 5, rect.left() + 7, rect.top() + 10)
    elif kind == "fit":
        painter.setPen(QPen(dark, 2))
        painter.drawRect(rect.adjusted(2, 2, -2, -2))
        painter.drawLine(rect.left() + 2, rect.top() + 7, rect.left() + 7, rect.top() + 2)
        painter.drawLine(rect.right() - 2, rect.bottom() - 7, rect.right() - 7, rect.bottom() - 2)
    elif kind == "filter":
        painter.setPen(QPen(blue, 2))
        painter.drawLine(rect.left(), rect.top() + 1, rect.right(), rect.top() + 1)
        painter.drawLine(rect.left(), rect.top() + 1, rect.center().x(), rect.center().y())
        painter.drawLine(rect.right(), rect.top() + 1, rect.center().x(), rect.center().y())
        painter.drawLine(rect.center().x(), rect.center().y(), rect.center().x(), rect.bottom())
    elif kind == "find":
        painter.setPen(QPen(dark, 2))
        painter.drawEllipse(rect.left() + 2, rect.top() + 2, 9, 9)
        painter.drawEllipse(rect.left() + 10, rect.top() + 2, 9, 9)
        painter.drawLine(rect.left() + 7, rect.top() + 11, rect.left() + 5, rect.bottom())
        painter.drawLine(rect.left() + 15, rect.top() + 11, rect.left() + 17, rect.bottom())
    elif kind == "view":
        painter.setBrush(QColor("#f4cf64"))
        painter.setPen(QPen(QColor("#a5831c"), 1))
        painter.drawRect(rect.adjusted(1, 4, -7, -2))
        painter.setBrush(QColor("#f8dc72"))
        painter.drawRect(rect.adjusted(7, 1, -1, -5))
    else:
        painter.setPen(QPen(QColor("#ee842b"), 2))
        painter.drawEllipse(rect)

    painter.end()
    return QIcon(pixmap)


class CadViewportHost(QFrame):
    """Hosts the CAD viewer widget plus observed orientation and workflow overlays."""

    annotationMoved = pyqtSignal(str, object)
    workflowConfirmRequested = pyqtSignal()
    workflowCancelRequested = pyqtSignal()
    workflowAddFeatureRequested = pyqtSignal()
    workflowListRequested = pyqtSignal()

    def __init__(self, viewer: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("CadViewportHost")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.viewer = viewer
        self._step_buttons: dict[str, QPushButton] = {}
        self._control_buttons: dict[str, QPushButton] = {}
        self._annotations: tuple[ViewerAnnotation, ...] = ()
        self._annotation_labels: dict[str, _DraggableAnnotationLabel] = {}

        stack = QStackedLayout(self)
        stack.setContentsMargins(0, 0, 0, 0)
        stack.addWidget(viewer)

        self.annotation_canvas = _ViewerAnnotationCanvas(self)

        self.view_cube = _ViewCubeWidget(self)
        self.view_cube.viewRequested.connect(self._set_standard_view)

        self.navigation_toolbar = QToolBar("Viewport Navigation", self)
        self.navigation_toolbar.setObjectName("ViewportNavigationToolbar")
        self.navigation_toolbar.setOrientation(Qt.Orientation.Vertical)
        self.navigation_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.navigation_toolbar.setIconSize(QSize(18, 18))
        self.navigation_toolbar.setMovable(False)
        self.navigation_toolbar.setFloatable(False)
        self._build_navigation_toolbar()

        self.axis_triad = _AxisTriadWidget(self)

        self.guided_toolbar = self._create_guided_toolbar()
        self.guided_toolbar.setParent(self)
        self.guided_toolbar.hide()
        self.set_annotations(())

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
        self.guided_prompt.setMinimumWidth(260)
        layout.addWidget(self.guided_prompt, 3, 0, 1, 4)
        self.component_counter = QLabel("0 Components")
        self.component_counter.setObjectName("GuidedComponentCounter")
        self.mating_face_counter = QLabel("0 of 0 Mating Faces")
        self.mating_face_counter.setObjectName("GuidedMatingFaceCounter")
        layout.addWidget(self.component_counter, 4, 0, 1, 2)
        layout.addWidget(self.mating_face_counter, 4, 2, 1, 2)
        control_signals = {
            "OK": (self.workflowConfirmRequested, "Accept the current guided step"),
            "X": (self.workflowCancelRequested, "Cancel the guided workflow"),
            "+": (self.workflowAddFeatureRequested, "Add an intermediate feature"),
            "List": (self.workflowListRequested, "Show selected workflow items"),
        }
        control_roles = {"OK": "ok", "X": "cancel", "+": "add", "List": "list"}
        for index, label in enumerate(("OK", "X", "+", "List")):
            button = QPushButton(label)
            button.setObjectName(f"GuidedControl{label}")
            button.setToolTip(control_signals[label][1])
            button.setProperty("controlRole", control_roles[label])
            button.clicked.connect(control_signals[label][0].emit)
            self._control_buttons[label] = button
            layout.addWidget(button, 5, index)
        return frame

    def set_workflow_toolbar_state(self, state: GuidedToolbarState) -> None:
        self.guided_toolbar.show()
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
        self._layout_overlay()

    def hide_workflow_toolbar(self) -> None:
        self.guided_toolbar.hide()

    @property
    def annotations(self) -> tuple[ViewerAnnotation, ...]:
        return self._annotations

    def set_annotations(self, annotations: tuple[ViewerAnnotation, ...]) -> None:
        self._annotations = tuple(annotations)
        if hasattr(self.viewer, "set_annotations"):
            self.viewer.set_annotations(self._annotations)  # type: ignore[attr-defined]
        if self._viewer_uses_native_annotations():
            self.annotation_canvas.set_annotations(())
            self.annotation_canvas.hide()
            self._clear_annotation_labels()
        else:
            self.annotation_canvas.set_annotations(self._annotations)
            self.annotation_canvas.show()
            self._sync_annotation_labels()
        self._layout_overlay()

    def capture_snapshot(self, request: SnapshotRequest) -> Snapshot:
        output_path = Path(request.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        annotations = request.annotations or self._annotations
        annotation_positions = dict(request.annotation_positions)
        if annotations:
            annotation_positions["_viewer_annotations"] = [
                annotation.to_dict() for annotation in annotations
            ]
        if hasattr(self.viewer, "capture_snapshot"):
            base_snapshot = self.viewer.capture_snapshot(request)  # type: ignore[attr-defined]
            image = QImage(str(output_path))
            if not image.isNull():
                _paint_annotations_on_image(image, annotations)
                image.save(str(output_path))
                return Snapshot(
                    image_path=str(output_path),
                    camera=dict(base_snapshot.camera),
                    visible_stackup_ids=list(request.visible_stackup_ids),
                    annotation_positions=annotation_positions,
                    captured_at=base_snapshot.captured_at,
                )

        pixmap = self.grab()
        if pixmap.isNull() or not pixmap.save(str(output_path)):
            raise RuntimeError(f"Could not capture CAD viewport snapshot: {output_path}")
        camera = self.viewer.camera_state().to_dict() if hasattr(self.viewer, "camera_state") else CadCameraState().to_dict()
        return Snapshot(
            image_path=str(output_path),
            camera=camera,
            visible_stackup_ids=list(request.visible_stackup_ids),
            annotation_positions=annotation_positions,
        )

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        self._layout_overlay()

    def _build_navigation_toolbar(self) -> None:
        self._add_navigation_action("Isometric", "iso", lambda: self._set_standard_view(StandardView.ISO))
        self._add_navigation_action("Front", "front", lambda: self._set_standard_view(StandardView.FRONT))
        self._add_navigation_action("Top", "top", lambda: self._set_standard_view(StandardView.TOP))
        self._add_navigation_action("Right", "right", lambda: self._set_standard_view(StandardView.RIGHT))
        self.navigation_toolbar.addSeparator()
        self._add_navigation_action("Pan", "pan", lambda: self._pan(32, 0))
        self._add_navigation_action("Zoom", "zoom", lambda: self._zoom(1.15))
        self._add_navigation_action("Fit", "fit", self._fit_all)

    def _add_navigation_action(self, label: str, icon_name: str, callback) -> None:
        action = self.navigation_toolbar.addAction(_chrome_icon(icon_name, 20), label)
        action.setToolTip(label)
        action.triggered.connect(callback)

    def _fit_all(self) -> None:
        if hasattr(self.viewer, "fit_all"):
            self.viewer.fit_all()  # type: ignore[attr-defined]

    def _pan(self, dx: int, dy: int) -> None:
        if hasattr(self.viewer, "pan"):
            self.viewer.pan(dx, dy)  # type: ignore[attr-defined]

    def _zoom(self, factor: float) -> None:
        if hasattr(self.viewer, "zoom"):
            self.viewer.zoom(factor)  # type: ignore[attr-defined]

    def _set_standard_view(self, view: StandardView) -> None:
        if hasattr(self.viewer, "set_standard_view"):
            self.viewer.set_standard_view(view)  # type: ignore[attr-defined]

    def _sync_annotation_labels(self) -> None:
        annotation_ids = {annotation.id for annotation in self._annotations}
        for annotation_id, label in list(self._annotation_labels.items()):
            if annotation_id not in annotation_ids:
                label.deleteLater()
                del self._annotation_labels[annotation_id]
        for annotation in self._annotations:
            label = self._annotation_labels.get(annotation.id)
            if label is None:
                label = _DraggableAnnotationLabel(annotation, self)
                label.moved.connect(self._handle_annotation_label_moved)
                self._annotation_labels[annotation.id] = label
            else:
                label.set_annotation(annotation)
            label.show()

    def _handle_annotation_label_moved(self, annotation_id: str, position: object) -> None:
        if not isinstance(position, dict):
            return
        screen = position.get("screen")
        if (
            not isinstance(screen, list)
            or len(screen) != 2
            or not all(isinstance(value, (int, float)) for value in screen)
        ):
            return
        normalized = (float(screen[0]), float(screen[1]))
        updated = []
        moved_payload: dict[str, Any] = {"screen": [normalized[0], normalized[1]]}
        for annotation in self._annotations:
            if annotation.id == annotation_id:
                anchor = annotation.anchor
                if anchor is not None:
                    anchor = anchor.with_screen(normalized)
                    moved_payload = anchor.to_dict()
                updated.append(
                    replace(annotation, label_position=normalized, anchor=anchor)
                )
            else:
                updated.append(annotation)
        self._annotations = tuple(updated)
        if hasattr(self.viewer, "set_annotations"):
            self.viewer.set_annotations(self._annotations)  # type: ignore[attr-defined]
        self.annotation_canvas.set_annotations(self._annotations)
        self.annotationMoved.emit(annotation_id, moved_payload)

    def _viewer_uses_native_annotations(self) -> bool:
        return bool(getattr(self.viewer, "uses_native_annotations", False))

    def _clear_annotation_labels(self) -> None:
        for label in self._annotation_labels.values():
            label.deleteLater()
        self._annotation_labels.clear()

    def _layout_overlay(self) -> None:
        rect = self.rect()
        margin = 12
        self.annotation_canvas.setGeometry(rect)
        self.annotation_canvas.raise_()

        cube_size = self.view_cube.size()
        self.view_cube.setGeometry(
            max(margin, rect.width() - cube_size.width() - margin),
            margin,
            cube_size.width(),
            cube_size.height(),
        )

        nav_hint = self.navigation_toolbar.sizeHint()
        nav_width = max(34, nav_hint.width())
        nav_height = min(max(190, nav_hint.height()), max(120, rect.height() - 190))
        self.navigation_toolbar.setGeometry(
            max(margin, rect.width() - nav_width - margin),
            max(margin + cube_size.height() + 12, (rect.height() - nav_height) // 2),
            nav_width,
            nav_height,
        )

        axis_size = self.axis_triad.size()
        self.axis_triad.setGeometry(
            margin,
            max(margin, rect.height() - axis_size.height() - margin),
            axis_size.width(),
            axis_size.height(),
        )

        guided_hint = self.guided_toolbar.sizeHint()
        guided_width = min(max(380, guided_hint.width()), max(320, rect.width() - 2 * margin))
        guided_height = guided_hint.height()
        self.guided_toolbar.setGeometry(
            max(margin, rect.width() - guided_width - margin),
            max(margin, rect.height() - guided_height - margin),
            guided_width,
            guided_height,
        )

        self._layout_annotation_labels()
        for widget in (
            self.view_cube,
            self.navigation_toolbar,
            self.axis_triad,
            self.guided_toolbar,
        ):
            widget.raise_()

    def _layout_annotation_labels(self) -> None:
        for annotation in self._annotations:
            label = self._annotation_labels.get(annotation.id)
            if label is None:
                continue
            label.adjustSize()
            point = _annotation_label_point(self.size(), annotation)
            x = max(0, min(int(point.x() - label.width() / 2), self.width() - label.width()))
            y = max(0, min(int(point.y() - label.height() / 2), self.height() - label.height()))
            label.move(x, y)
            label.raise_()


def _annotation_color(role: ViewerAnnotationRole) -> QColor:
    colors = {
        ViewerAnnotationRole.STACKUP: QColor("#c40000"),
        ViewerAnnotationRole.CONTRIBUTOR: QColor("#2459d6"),
        ViewerAnnotationRole.WARNING: QColor("#d6a300"),
    }
    return colors[ViewerAnnotationRole(role)]


def _point_from_normalized(size: QSize, point: tuple[float, float]) -> QPointF:
    x = max(0.0, min(1.0, float(point[0])))
    y = max(0.0, min(1.0, float(point[1])))
    return QPointF(x * max(size.width(), 1), y * max(size.height(), 1))


def _annotation_label_point(size: QSize, annotation: ViewerAnnotation) -> QPointF:
    if annotation.label_position is not None:
        return _point_from_normalized(size, annotation.label_position)
    if annotation.anchor is not None and annotation.anchor.screen is not None:
        return _point_from_normalized(size, annotation.anchor.screen)
    start = _point_from_normalized(size, annotation.start)
    end = _point_from_normalized(size, annotation.end)
    side = 0.055 if annotation.role == ViewerAnnotationRole.STACKUP else 0.04
    return QPointF(
        min(max(size.width() * 0.04, end.x() + size.width() * side), size.width() * 0.96),
        (start.y() + end.y()) / 2.0,
    )


def _paint_annotations_on_image(
    image: QImage,
    annotations: tuple[ViewerAnnotation, ...],
) -> None:
    if not annotations:
        return
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    _paint_annotations(painter, image.size(), annotations, draw_labels=True)
    painter.end()


def _paint_annotations(
    painter: QPainter,
    size: QSize,
    annotations: tuple[ViewerAnnotation, ...],
    *,
    draw_labels: bool,
) -> None:
    for annotation in annotations:
        color = _annotation_color(annotation.role)
        pen = QPen(color, 3 if annotation.role == ViewerAnnotationRole.STACKUP else 2)
        painter.setPen(pen)
        start = _point_from_normalized(size, annotation.start)
        end = _point_from_normalized(size, annotation.end)
        label_pos = _annotation_label_point(size, annotation)
        painter.drawLine(start, end)
        _draw_arrow_head(painter, start, end)
        _draw_arrow_head(painter, end, start)
        leader_start = QPointF(end.x(), (start.y() + end.y()) / 2.0)
        painter.drawLine(leader_start, label_pos)
        for first, second in zip(annotation.leader_points, annotation.leader_points[1:]):
            painter.drawLine(
                _point_from_normalized(size, first),
                _point_from_normalized(size, second),
            )
        if draw_labels:
            _paint_annotation_label(painter, label_pos, annotation, color)


def _paint_annotation_label(
    painter: QPainter,
    point: QPointF,
    annotation: ViewerAnnotation,
    color: QColor,
) -> None:
    font = painter.font()
    font.setBold(True)
    painter.setFont(font)
    metrics = painter.fontMetrics()
    width = max(46, metrics.horizontalAdvance(annotation.label) + 12)
    height = metrics.height() + 8
    rect = QRect(
        int(point.x() - width / 2),
        int(point.y() - height / 2),
        width,
        height,
    )
    painter.fillRect(rect, QColor(238, 238, 238, 210))
    painter.setPen(QPen(color, 1))
    painter.drawRect(rect)
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, annotation.label)


def _draw_arrow_head(painter: QPainter, tail: QPointF, tip: QPointF) -> None:
    dx = tip.x() - tail.x()
    dy = tip.y() - tail.y()
    length = math.hypot(dx, dy)
    if length <= 0.1:
        return
    ux = dx / length
    uy = dy / length
    px = -uy
    py = ux
    head = 10.0
    spread = 5.0
    left = QPointF(tip.x() - ux * head + px * spread, tip.y() - uy * head + py * spread)
    right = QPointF(tip.x() - ux * head - px * spread, tip.y() - uy * head - py * spread)
    painter.drawLine(tip, left)
    painter.drawLine(tip, right)


def _normalized_label_position(label: QLabel) -> dict[str, list[float]]:
    parent = label.parentWidget()
    if parent is None or parent.width() <= 0 or parent.height() <= 0:
        return {"screen": [0.5, 0.5]}
    center = label.geometry().center()
    return {
        "screen": [
            round(center.x() / parent.width(), 4),
            round(center.y() / parent.height(), 4),
        ]
    }


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
        layout.setContentsMargins(18, 16, 18, 12)
        layout.setSpacing(8)
        self.title = QLabel("Worst Case Results")
        self.title.setObjectName("ResultPanelTitle")
        layout.addWidget(self.title)
        self.metrics = QLabel("")
        self.metrics.setObjectName("ResultPanelMetrics")
        self.metrics.setWordWrap(True)
        layout.addWidget(self.metrics)
        self.plot = ResultPlotWidget()
        layout.addWidget(self.plot, 1)
        self.warning_row = QWidget()
        warning_layout = QHBoxLayout(self.warning_row)
        warning_layout.setContentsMargins(0, 0, 0, 0)
        warning_layout.setSpacing(8)
        self.warning_icon = QLabel()
        self.warning_icon.setPixmap(_warning_pixmap(24))
        warning_layout.addWidget(self.warning_icon, alignment=Qt.AlignmentFlag.AlignTop)
        self.warning = QLabel(NON_1D_WARNING_TEXT)
        self.warning.setObjectName("NonOneDWarningLabel")
        self.warning.setWordWrap(True)
        warning_layout.addWidget(self.warning, 1)
        self.warning_row.setVisible(False)
        layout.addWidget(self.warning_row)

    def set_stackup_name(self, name: str) -> None:
        self.title.setText(f"Worst Case Results for {name}")
        self.metrics.setText("")
        self.plot.clear()
        self.warning_row.setVisible(False)

    def set_projection(self, projection: ResultDisplayProjection) -> None:
        self.title.setText(projection.title)
        metrics = []
        if projection.mode_label == "Statistical":
            if projection.predicted_quality_label:
                metrics.append("Actual: " + projection.predicted_quality_label)
            metrics.extend([projection.mean_label, projection.standard_deviation_label])
        else:
            metrics.extend([projection.result_label, projection.objective_label])
        if projection.mode_label != "Statistical" and projection.predicted_quality_label:
            metrics.append(projection.predicted_quality_label)
        self.metrics.setText("\n".join(item for item in metrics if item))
        self.plot.set_projection(projection)
        if projection.warnings:
            warning_lines = [NON_1D_WARNING_TEXT]
            warning_lines.extend(warning.message for warning in projection.warnings)
            self.warning.setText("\n".join(warning_lines))
            self.warning_row.setVisible(True)
        else:
            self.warning.setText("")
            self.warning_row.setVisible(False)


class ResultPlotWidget(QWidget):
    """Compact result plot matching the demo range-bar and bell-curve density."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ResultPlotWidget")
        self._projection: ResultDisplayProjection | None = None
        self.setMinimumHeight(154)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def clear(self) -> None:
        self._projection = None
        self.update()

    def set_projection(self, projection: ResultDisplayProjection) -> None:
        self._projection = projection
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        painter.setPen(QPen(QColor("#111111"), 1))
        plot_rect = self.rect().adjusted(18, 26, -18, -28)
        if plot_rect.width() <= 20 or plot_rect.height() <= 20:
            painter.end()
            return
        projection = self._projection
        if projection is None:
            painter.drawRect(plot_rect)
            painter.end()
            return
        if projection.mode_label == "Statistical":
            self._draw_statistical(painter, plot_rect, projection)
        else:
            self._draw_range_bar(painter, plot_rect, projection)
        painter.end()

    def _draw_range_bar(self, painter: QPainter, rect: QRect, projection: ResultDisplayProjection) -> None:
        value_range = _plot_value_range(projection)
        x_for = lambda value: _plot_x(rect, value_range, value)
        center_y = rect.center().y()
        painter.setPen(QPen(QColor("#111111"), 1))
        painter.drawLine(rect.left(), center_y, rect.right(), center_y)
        _draw_axis_arrow(painter, QPointF(rect.left(), center_y), left=True)
        _draw_axis_arrow(painter, QPointF(rect.right(), center_y), left=False)

        objective_lower = projection.objective_lower if projection.objective_lower is not None else value_range[0]
        objective_upper = projection.objective_upper if projection.objective_upper is not None else value_range[1]
        result_lower = projection.result_lower
        result_upper = projection.result_upper
        band_top = center_y - 12
        band_height = 24
        left_red = QRectF(x_for(min(result_lower, objective_lower)), band_top, max(0.0, x_for(objective_lower) - x_for(min(result_lower, objective_lower))), band_height)
        green = QRectF(x_for(objective_lower), band_top, max(2.0, x_for(objective_upper) - x_for(objective_lower)), band_height)
        right_red = QRectF(x_for(objective_upper), band_top, max(0.0, x_for(max(result_upper, objective_upper)) - x_for(objective_upper)), band_height)
        painter.fillRect(left_red, QColor("#c93434"))
        painter.fillRect(green, QColor("#148c27"))
        painter.fillRect(right_red, QColor("#c93434"))

        for marker in projection.markers:
            color = QColor("#111111")
            if marker.role == "result":
                color = QColor("#b51f1f") if projection.status == ResultStatus.FAIL else QColor("#137c24")
            elif marker.role == "mean":
                color = QColor("#111111")
            x = x_for(marker.value)
            painter.setPen(QPen(color, 2 if marker.role != "mean" else 1))
            painter.drawLine(QPointF(x, band_top - 6), QPointF(x, band_top + band_height + 12))
            _draw_plot_label(painter, rect, x, marker.value, marker.role)

    def _draw_statistical(self, painter: QPainter, rect: QRect, projection: ResultDisplayProjection) -> None:
        value_range = _plot_value_range(projection)
        x_for = lambda value: _plot_x(rect, value_range, value)
        painter.setPen(QPen(QColor("#111111"), 1))
        painter.drawRect(rect)
        mean = next((marker.value for marker in projection.markers if marker.role == "mean"), (value_range[0] + value_range[1]) / 2.0)
        sigma = max((value_range[1] - value_range[0]) / 9.0, 0.001)
        base_y = rect.bottom() - 1
        peak_height = rect.height() * 0.78
        path = QPainterPath()
        path.moveTo(rect.left(), base_y)
        steps = 90
        for index in range(steps + 1):
            x = rect.left() + rect.width() * index / steps
            value = value_range[0] + (value_range[1] - value_range[0]) * index / steps
            bell = math.exp(-0.5 * ((value - mean) / sigma) ** 2)
            y = base_y - peak_height * bell
            path.lineTo(x, y)
        path.lineTo(rect.right(), base_y)
        path.closeSubpath()
        painter.fillPath(path, QColor("#139027"))

        for marker in projection.markers:
            color = QColor("#111111")
            width = 2
            if marker.role == "result":
                color = QColor("#157f2a") if projection.status != ResultStatus.FAIL else QColor("#b51f1f")
            if marker.role == "objective":
                color = QColor("#111111")
            x = x_for(marker.value)
            painter.setPen(QPen(color, width))
            painter.drawLine(QPointF(x, rect.top() - 8), QPointF(x, rect.bottom() + 1))
            _draw_plot_label(painter, rect, x, marker.value, marker.role)


class _ContributionRowWidget(QWidget):
    selected = pyqtSignal(str)

    def __init__(self, contributor_id: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.contributor_id = contributor_id
        if contributor_id:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setProperty("contributorId", contributor_id)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        if self.contributor_id and event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.contributor_id)
            event.accept()
            return
        super().mousePressEvent(event)


class ContributionBarsWidget(QFrame):
    contributorSelected = pyqtSignal(str)

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
        widget = _ContributionRowWidget(row.contributor_id)
        widget.setObjectName("ContributionRow")
        widget.selected.connect(self.contributorSelected.emit)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)
        label = QLabel(row.label)
        label.setMinimumWidth(250)
        label.setMaximumWidth(330)
        label.setWordWrap(False)
        layout.addWidget(label)
        if row.tolerance_box:
            box = QLabel("  ".join(part for part in (row.tolerance_box, row.datum) if part))
            box.setObjectName("GdtBoxPlaceholder")
            layout.addWidget(box)
        bar = ContributionBarMeter(row.percent)
        layout.addWidget(bar)
        percent = QLabel(f"{row.percent:.1f}%")
        percent.setMinimumWidth(52)
        layout.addWidget(percent)
        layout.addStretch(1)
        return widget


class ContributionBarMeter(QWidget):
    def __init__(self, percent: float, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ContributionBarMeter")
        self._percent = max(0.0, min(100.0, float(percent)))
        self.setMinimumSize(280, 24)
        self.setMaximumHeight(24)

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        rect = self.rect().adjusted(0, 4, -1, -4)
        painter.fillRect(rect, QColor("#ffffff"))
        painter.setPen(QPen(QColor("#d0d0d0"), 1))
        painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())
        width = max(2, int(rect.width() * self._percent / 100.0))
        painter.fillRect(QRect(rect.left(), rect.top(), width, rect.height()), QColor("#0d83c9"))
        painter.end()


def _warning_pixmap(size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    center = pixmap.rect().center()
    points = [
        center + QPoint(0, int(-0.38 * size)),
        center + QPoint(int(-0.40 * size), int(0.34 * size)),
        center + QPoint(int(0.40 * size), int(0.34 * size)),
    ]
    painter.setBrush(QColor("#f2c200"))
    painter.setPen(QPen(QColor("#a77900"), 1))
    painter.drawPolygon(*points)
    painter.setPen(QPen(QColor("#222222"), 2))
    painter.drawLine(center.x(), center.y() - int(0.15 * size), center.x(), center.y() + int(0.13 * size))
    painter.drawPoint(center.x(), center.y() + int(0.27 * size))
    painter.end()
    return pixmap


def _plot_value_range(projection: ResultDisplayProjection) -> tuple[float, float]:
    values = [marker.value for marker in projection.markers]
    values.extend([projection.result_lower, projection.result_upper])
    if projection.objective_lower is not None:
        values.append(projection.objective_lower)
    if projection.objective_upper is not None:
        values.append(projection.objective_upper)
    lower = min(values) if values else -1.0
    upper = max(values) if values else 1.0
    if math.isclose(lower, upper):
        lower -= 1.0
        upper += 1.0
    padding = (upper - lower) * 0.14
    return lower - padding, upper + padding


def _plot_x(rect: QRect, value_range: tuple[float, float], value: float) -> float:
    lower, upper = value_range
    ratio = (value - lower) / (upper - lower)
    ratio = max(0.0, min(1.0, ratio))
    return rect.left() + ratio * rect.width()


def _draw_axis_arrow(painter: QPainter, point: QPointF, *, left: bool) -> None:
    direction = -1 if left else 1
    painter.drawLine(point, QPointF(point.x() - direction * 12, point.y() - 5))
    painter.drawLine(point, QPointF(point.x() - direction * 12, point.y() + 5))


def _draw_plot_label(
    painter: QPainter,
    rect: QRect,
    x: float,
    value: float,
    role: str,
) -> None:
    label = _format_plot_number(value)
    metrics = painter.fontMetrics()
    label_width = metrics.horizontalAdvance(label)
    x_left = int(max(rect.left(), min(rect.right() - label_width, x - label_width / 2)))
    if role == "result":
        y = rect.top() - 18
    elif role == "mean":
        y = rect.bottom() + metrics.height() + 2
    else:
        y = rect.bottom() + metrics.height() + 2
    painter.setPen(QPen(QColor("#111111"), 1))
    painter.drawText(x_left, y, label)


def _format_plot_number(value: float) -> str:
    number = float(value)
    if abs(number) >= 100:
        return f"{number:.2f}"
    if abs(number) >= 10:
        return f"{number:.2f}"
    return f"{number:.3f}".rstrip("0").rstrip(".")


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

        self.setWindowTitle(f"MDTS CAD 1D Tolerance    {self.workspace.project_title}")
        self.resize(1500, 900)
        self.setMinimumSize(1000, 640)
        self._build_actions()
        self._build_shell()
        self._connect_signals()
        self._refresh_dashboard()
        self._update_cad_source_status_ui()
        self.statusBar().showMessage("Ready")

    def open_cad_file(self, path: str | Path) -> None:
        input_path = Path(path)
        dialog = NeutralCadImportOptionsDialog(input_path, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        import_settings = dialog.import_settings()
        try:
            document = self.geometry_session.import_file(
                input_path,
                _cad_import_settings_from_dialog(import_settings),
            )
            if hasattr(self.viewer, "display_document"):
                self.viewer.display_document(self.geometry_session)  # type: ignore[attr-defined]
        except (CadKernelUnavailable, Exception) as exc:
            QMessageBox.warning(self, "CAD import failed", str(exc))
            self.statusBar().showMessage("CAD import failed")
            return
        document.import_settings.update(import_settings)
        document.source_status = CadSourceStatus.PRESENT
        document.source_status_message = (
            f"CAD source present: {document.display_name or input_path.name}"
        )
        document.source_last_checked_at = _utc_timestamp()
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
        self._sync_stackup_action_state()
        self._update_cad_source_status_ui()
        self.setWindowTitle(f"MDTS CAD 1D Tolerance    {self.workspace.project_title}")
        self._update_status_counters()
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
        self._sync_stackup_action_state()
        self.setWindowTitle(f"MDTS CAD 1D Tolerance    {self.workspace.project_title}")
        self._rehydrate_project_cad_sources(project_path)
        self._update_cad_source_status_ui()
        self._update_status_counters()
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
                _set_document_source_status(
                    document,
                    CadSourceStatus.UNKNOWN,
                    "CAD source not recorded",
                )
                self.cad_source_status_messages.append("CAD source not recorded")
                continue
            resolved_path = resolve_project_asset_path(source_path, project_path)
            relocated = False
            if resolved_path is None:
                resolved_path = _find_relocated_cad_source(document, project_path)
                relocated = resolved_path is not None
                if resolved_path is None:
                    message = f"CAD source not found: {source_name}"
                    _set_document_source_status(
                        document,
                        CadSourceStatus.MISSING,
                        message,
                    )
                    self.cad_source_status_messages.append(message)
                    continue
            if not is_supported_neutral_cad(resolved_path):
                message = f"Unsupported CAD source: {source_name}"
                _set_document_source_status(
                    document,
                    CadSourceStatus.UNKNOWN,
                    message,
                )
                self.cad_source_status_messages.append(message)
                continue
            try:
                imported_document = self.geometry_session.import_file(
                    resolved_path,
                    _cad_import_settings_from_document(document, self.project),
                )
                if hasattr(self.viewer, "display_document"):
                    self.viewer.display_document(self.geometry_session)  # type: ignore[attr-defined]
                displayed = True
                validation = validate_cad_source_reimport(
                    document,
                    imported_document,
                    _session_shape_references(self.geometry_session),
                    _session_feature_references(self.geometry_session),
                )
                status = validation.status
                message = validation.message
                if relocated and status == CadSourceStatus.PRESENT:
                    status = CadSourceStatus.RELOCATED
                    message = f"CAD source relocated: {resolved_path.name}"
                elif (
                    status == CadSourceStatus.PRESENT
                    and _is_project_local_cad_asset(resolved_path, project_path)
                ):
                    status = CadSourceStatus.PROJECT_LOCAL_PACKAGE_ASSET
                    message = f"Using project-local CAD asset: {resolved_path.name}"
                elif status == CadSourceStatus.PRESENT:
                    message = f"Reloaded CAD source: {resolved_path.name}"
                _set_document_source_status(
                    document,
                    status,
                    message,
                    topology_hash=validation.topology_hash,
                )
                self.cad_source_status_messages.append(message)
            except UnsupportedCadFormatError:
                message = f"Unsupported CAD source: {source_name}"
                _set_document_source_status(
                    document,
                    CadSourceStatus.UNKNOWN,
                    message,
                )
                self.cad_source_status_messages.append(message)
            except FileNotFoundError:
                message = f"CAD source not found: {source_name}"
                _set_document_source_status(
                    document,
                    CadSourceStatus.MISSING,
                    message,
                )
                self.cad_source_status_messages.append(message)
            except (CadKernelUnavailable, Exception) as exc:
                message = f"CAD source unavailable: {source_name} ({exc})"
                _set_document_source_status(
                    document,
                    CadSourceStatus.UNKNOWN,
                    message,
                )
                self.cad_source_status_messages.append(message)

        if not displayed and hasattr(self.viewer, "clear"):
            self.viewer.clear()  # type: ignore[attr-defined]

    def _create_viewer(self) -> QWidget:
        try:
            return OccCadViewerWidget(self)
        except CadViewerUnavailable as exc:
            return PlaceholderCadViewerWidget(self, str(exc))

    def _build_actions(self) -> None:
        self.open_action = QAction(_chrome_icon("open", 32), "Open", self)
        self.open_action.setToolTip("Open a STEP, IGES, .tolproj, or .tolpack file.")
        self.open_action.triggered.connect(self._open_dialog)
        self.import_action = QAction(_chrome_icon("import", 24), "Import", self)
        self.import_action.setToolTip("Import a neutral STEP or IGES CAD file.")
        self.import_action.triggered.connect(self._open_dialog)
        self.export_action = QAction(_chrome_icon("export", 24), "Export", self)
        self.export_action.setToolTip("Package Project (.tolpack)")
        self.export_action.triggered.connect(self._package_project)
        self.save_project_action = QAction(_chrome_icon("save", 24), "Save Project", self)
        self.save_project_action.setToolTip("Save the current CAD tolerance project.")
        self.save_project_action.triggered.connect(self._save_project)
        self.refresh_source_action = QAction(_chrome_icon("refresh", 24), "Refresh Source", self)
        self.refresh_source_action.setToolTip("Refresh the saved STEP/IGES source reference.")
        self.refresh_source_action.triggered.connect(self.refresh_cad_source)
        self.reattach_source_action = QAction(_chrome_icon("reattach", 24), "Reattach Source", self)
        self.reattach_source_action.setToolTip("Choose a replacement STEP/IGES source file.")
        self.reattach_source_action.triggered.connect(self._reattach_cad_source_dialog)
        self.new_stackup_action = QAction(_chrome_icon("new_stackup", 36), "New Stackup", self)
        self.new_stackup_action.setToolTip("Create a guided 1D tolerance stackup.")
        self.new_stackup_action.triggered.connect(self._start_new_stackup_workflow)
        self.add_feature_action = QAction(_chrome_icon("add_feature", 36), "Add Feature", self)
        self.add_feature_action.setToolTip("Add an intermediate feature to the selected stackup.")
        self.add_feature_action.setEnabled(False)
        self.add_feature_action.triggered.connect(self._start_add_feature_flow)
        self.add_geometric_tolerance_action = QAction(_chrome_icon("report", 30), "Add Geometric Tolerance", self)
        self.add_geometric_tolerance_action.setToolTip("Add a manual GD&T/GPS contributor.")
        self.add_geometric_tolerance_action.triggered.connect(self._open_add_geometric_tolerance_dialog)
        self.snapshot_action = QAction(_chrome_icon("snapshot", 36), "Snapshot", self)
        self.snapshot_action.setToolTip("Sets the current view orientation and size for the report image.")
        self.snapshot_action.triggered.connect(self._save_snapshot)
        self.generate_report_action = QAction(_chrome_icon("report", 36), "Generate Report", self)
        self.generate_report_action.setToolTip("Generate a browser-style tolerance stackup report.")
        self.generate_report_action.setEnabled(False)
        self.generate_report_action.triggered.connect(self._generate_report)
        self.settings_action = QAction(_chrome_icon("settings", 24), "Settings", self)
        self.settings_action.setToolTip("Open project tolerance defaults and display settings.")
        self.back_action = QAction("Back", self)
        self.back_action.triggered.connect(self.show_summary)
        self.view_iso_action = QAction(_chrome_icon("iso", 24), "Isometric", self)
        self.view_iso_action.triggered.connect(lambda: self.viewport_host._set_standard_view(StandardView.ISO))
        self.view_front_action = QAction(_chrome_icon("front", 24), "Front", self)
        self.view_front_action.triggered.connect(lambda: self.viewport_host._set_standard_view(StandardView.FRONT))
        self.view_top_action = QAction(_chrome_icon("top", 24), "Top", self)
        self.view_top_action.triggered.connect(lambda: self.viewport_host._set_standard_view(StandardView.TOP))
        self.view_right_action = QAction(_chrome_icon("right", 24), "Right", self)
        self.view_right_action.triggered.connect(lambda: self.viewport_host._set_standard_view(StandardView.RIGHT))
        self.view_fit_action = QAction(_chrome_icon("fit", 24), "Fit", self)
        self.view_fit_action.triggered.connect(lambda: self.viewport_host._fit_all())
        self.view_zoom_action = QAction(_chrome_icon("zoom", 24), "Zoom", self)
        self.view_zoom_action.triggered.connect(lambda: self.viewport_host._zoom(1.15))
        self.view_pan_action = QAction(_chrome_icon("pan", 24), "Pan", self)
        self.view_pan_action.triggered.connect(lambda: self.viewport_host._pan(32, 0))

    def _build_shell(self) -> None:
        central = QWidget()
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self._create_ribbon())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("MainWorkspaceSplitter")
        self.main_splitter = splitter
        splitter.addWidget(self._create_left_browser())
        self.viewport_host = CadViewportHost(self.viewer)
        splitter.addWidget(self.viewport_host)
        splitter.addWidget(self._create_analysis_pane())
        splitter.setSizes([270, 660, 570])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        root_layout.addWidget(splitter, 1)
        self.setCentralWidget(central)
        self._configure_status_bar()

    def _create_ribbon(self) -> QTabWidget:
        ribbon = QTabWidget()
        ribbon.setObjectName("RibbonTabs")
        ribbon.setMaximumHeight(120)
        ribbon.addTab(
            self._ribbon_page(
                [
                    ("Project", [self.open_action, self.save_project_action]),
                    ("Source", [self.import_action, self.refresh_source_action, self.reattach_source_action]),
                    ("Package", [self.export_action]),
                ],
            ),
            "File",
        )
        ribbon.addTab(
            self._ribbon_page(
                [
                    ("Stackup", [self.new_stackup_action, self.add_feature_action]),
                    ("Report", [self.snapshot_action, self.generate_report_action]),
                    ("Data", [self.import_action, self.export_action]),
                ],
            ),
            "Tolerance Stackup",
        )
        ribbon.addTab(
            self._ribbon_page(
                [
                    ("Standard Views", [self.view_iso_action, self.view_front_action, self.view_top_action, self.view_right_action]),
                    ("Navigate", [self.view_pan_action, self.view_zoom_action, self.view_fit_action]),
                    ("Display", [self.settings_action]),
                ],
            ),
            "View",
        )
        ribbon.setCurrentIndex(1)
        return ribbon

    def _ribbon_page(self, groups: list[tuple[str, list[QAction]]]) -> QWidget:
        page = QWidget()
        page.setObjectName("RibbonPage")
        layout = QHBoxLayout(page)
        layout.setContentsMargins(4, 4, 8, 2)
        layout.setSpacing(0)
        for group_label, actions in groups:
            layout.addWidget(self._ribbon_group(group_label, actions))
        layout.addStretch(1)
        return page

    def _ribbon_group(self, group_label: str, actions: list[QAction]) -> QWidget:
        frame = QFrame()
        frame.setObjectName(f"RibbonGroup{group_label.replace(' ', '')}")
        frame.setProperty("ribbonGroup", True)
        group_layout = QVBoxLayout(frame)
        group_layout.setContentsMargins(5, 2, 5, 1)
        group_layout.setSpacing(1)
        command_row = QHBoxLayout()
        command_row.setSpacing(3)
        for action in actions:
            button = QToolButton()
            button.setDefaultAction(action)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setIconSize(QSize(30, 30))
            button.setProperty("ribbonCommand", True)
            button.setObjectName(f"RibbonButton{action.text().replace(' ', '')}")
            command_row.addWidget(button)
        group_layout.addLayout(command_row)
        group = QLabel(group_label)
        group.setObjectName("RibbonGroupLabel")
        group.setAlignment(Qt.AlignmentFlag.AlignCenter)
        group_layout.addWidget(group)
        return frame

    def _create_left_browser(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("ModelBrowserPanel")
        panel.setMinimumWidth(220)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        header = QHBoxLayout()
        header.setContentsMargins(8, 5, 5, 4)
        title = QLabel("Model")
        title.setObjectName("DockHeaderTitle")
        header.addWidget(title)
        header.addWidget(QLabel("v"))
        header.addStretch(1)
        help_button = QToolButton()
        help_button.setObjectName("ModelBrowserHelpButton")
        help_button.setText("?")
        help_button.setToolTip("Model browser help")
        header.addWidget(help_button)
        close_button = QToolButton()
        close_button.setObjectName("ModelBrowserCloseButton")
        close_button.setText("X")
        close_button.setToolTip("Close model browser")
        header.addWidget(close_button)
        layout.addLayout(header)

        browser_controls = QFrame()
        browser_controls.setObjectName("AssemblyBrowserToolbar")
        control_layout = QHBoxLayout(browser_controls)
        control_layout.setContentsMargins(4, 2, 4, 2)
        control_layout.setSpacing(3)
        filter_button = QToolButton()
        filter_button.setObjectName("BrowserFilterButton")
        filter_button.setIcon(_chrome_icon("filter", 18))
        filter_button.setToolTip("Filter model browser")
        control_layout.addWidget(filter_button)
        view_button = QToolButton()
        view_button.setObjectName("BrowserAssemblyViewButton")
        view_button.setIcon(_chrome_icon("view", 18))
        view_button.setText("Assembly View")
        view_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        view_button.setToolTip("Assembly View")
        control_layout.addWidget(view_button, 1)
        find_button = QToolButton()
        find_button.setObjectName("BrowserFindButton")
        find_button.setIcon(_chrome_icon("find", 18))
        find_button.setToolTip("Find in model browser")
        control_layout.addWidget(find_button)
        layout.addWidget(browser_controls)

        self.cad_source_status_label = QLabel()
        self.cad_source_status_label.setObjectName("CadSourceStatusLabel")
        self.cad_source_status_label.setWordWrap(True)
        layout.addWidget(self.cad_source_status_label)

        self.assembly_tree = QTreeView()
        self.assembly_tree.setObjectName("AssemblyTreeView")
        self.assembly_tree.setModel(self.assembly_model)
        self.assembly_tree.expandToDepth(1)
        self.assembly_tree.header().hide()
        self.assembly_tree.setUniformRowHeights(True)
        self.assembly_tree.setIndentation(14)
        layout.addWidget(self.assembly_tree, 1)
        return panel

    def _configure_status_bar(self) -> None:
        self.status_stackup_count_label = QLabel()
        self.status_stackup_count_label.setObjectName("StatusStackupCountLabel")
        self.status_selection_count_label = QLabel()
        self.status_selection_count_label.setObjectName("StatusSelectionCountLabel")
        self.statusBar().addPermanentWidget(self.status_stackup_count_label)
        self.statusBar().addPermanentWidget(self.status_selection_count_label)
        self._update_status_counters()

    def _update_status_counters(self) -> None:
        if not hasattr(self, "status_stackup_count_label"):
            return
        stackup_count = len(self.project.stackups) or len(self.workspace.summary_rows)
        self.status_stackup_count_label.setText(str(stackup_count))
        selected_count = "0/0"
        if self.project.stackups:
            selected = _stackup_by_id(self.project, self.workspace.selected_stackup_id)
            if selected is not None:
                selected_count = f"{len(selected.contributors)}/{len(selected.contributors)}"
        self.status_selection_count_label.setText(selected_count)

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
        brand = QLabel("MDTS")
        brand.setObjectName("AnalysisPaneBrand")
        header.addWidget(brand)
        title = QLabel("Summary of 1D Tolerance Stackups")
        title.setObjectName("AnalysisPaneTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(title, 1)
        gear = QToolButton()
        gear.setDefaultAction(self.settings_action)
        gear.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        gear.setObjectName("AnalysisPaneGearButton")
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
        self.summary_table.selectionModel().currentRowChanged.connect(
            self._handle_summary_row_changed
        )
        self.detail_model.editAccepted.connect(self.statusBar().showMessage)
        self.detail_model.editRejected.connect(self.statusBar().showMessage)
        self.detail_table.selectionModel().currentRowChanged.connect(
            self._handle_detail_row_changed
        )
        self.assembly_tree.selectionModel().currentChanged.connect(
            self._handle_assembly_tree_changed
        )
        self.viewport_host.annotationMoved.connect(self._handle_annotation_moved)
        self.viewport_host.workflowConfirmRequested.connect(self._confirm_workflow_step)
        self.viewport_host.workflowCancelRequested.connect(self._cancel_workflow)
        self.viewport_host.workflowAddFeatureRequested.connect(self._start_add_feature_flow)
        self.viewport_host.workflowListRequested.connect(self._show_workflow_selection_list)
        self.detail_contributions.contributorSelected.connect(
            self._handle_contributor_selected
        )
        self.summary_contributions.contributorSelected.connect(
            self._handle_contributor_selected
        )
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
            self.viewport_host.set_annotations(())
            return
        self.workspace.select_stackup(stackup_id)
        selected = _summary_by_id(self.workspace.summary_rows, stackup_id)
        title = selected.name if selected else "Stackup"
        self.detail_title.setText(f"{title} details")
        self.detail_model.set_rows(self.workspace.detail_rows(stackup_id))
        self._update_detail_outputs(stackup_id, title)
        self._sync_viewer_annotations(stackup_id)

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

    def _handle_detail_row_changed(self, current, _previous) -> None:
        if not current.isValid():
            return
        row = current.data(Qt.ItemDataRole.UserRole)
        if not isinstance(row, StackupDetailRow):
            return
        shape_ref = self._shape_reference_for_detail_row(row)
        if shape_ref is not None:
            self._cross_highlight_shape(shape_ref)

    def _handle_assembly_tree_changed(self, current, _previous) -> None:
        if not current.isValid():
            return
        shape_ref = self._shape_reference_for_assembly_item(
            str(current.data(Qt.ItemDataRole.UserRole) or ""),
            str(current.data(Qt.ItemDataRole.DisplayRole) or ""),
        )
        if shape_ref is not None:
            self._cross_highlight_shape(shape_ref)

    def _handle_summary_row_changed(self, current, _previous) -> None:
        if not current.isValid():
            return
        if current.row() < 0 or current.row() >= self.summary_model.rowCount():
            return
        summary = self.summary_model.row_at(current.row())
        stackup = _stackup_by_id(self.project, summary.stackup_id)
        if stackup is None:
            return
        self.workspace.select_stackup(stackup.id)
        self._sync_viewer_annotations(stackup.id)
        shape_ref = _first_stackup_shape_reference(stackup)
        if shape_ref is not None:
            self._cross_highlight_shape(shape_ref)

    def _handle_contributor_selected(self, contributor_id: str) -> None:
        stackup = _stackup_by_id(self.project, self.workspace.selected_stackup_id)
        if stackup is None:
            return
        contributor = _contributor_by_id(stackup, contributor_id)
        if contributor is None or contributor.source_feature is None:
            return
        shape_ref = contributor.source_feature.shape_reference
        if shape_ref is not None:
            self._cross_highlight_shape(shape_ref)
        for row_index, row in enumerate(self.detail_model.rows):
            if row.contributor_id == contributor_id:
                self.detail_table.selectRow(row_index)
                break

    def _handle_annotation_moved(self, _annotation_id: str, position: object) -> None:
        if not isinstance(position, dict):
            return
        stored_position = _clean_annotation_payload(position)
        if not stored_position:
            return
        if self.workflow_controller is not None:
            try:
                update = self.workflow_controller.set_annotation_position(stored_position)
            except ValueError:
                pass
            else:
                self._apply_workflow_update(update)
                return
        stackup = _stackup_by_id(self.project, self.workspace.selected_stackup_id)
        if stackup is None:
            return
        stackup.annotation_position = stored_position
        self.workspace.annotation_positions_by_stackup_id[stackup.id] = dict(stored_position)
        self._sync_viewer_annotations(stackup.id)
        self.statusBar().showMessage("Moved stackup annotation label")

    def _select_detail_row_for_selection(self, selection: CadViewerSelection) -> None:
        for row_index, row in enumerate(self.detail_model.rows):
            if not _detail_row_matches_selection(row, selection, self._feature_reference_by_id):
                continue
            self.detail_table.selectRow(row_index)
            return

    def _shape_reference_for_detail_row(self, row: StackupDetailRow):
        if not row.source_feature_id:
            return None
        feature = self._feature_reference_by_id(row.source_feature_id)
        if feature is not None:
            return feature.shape_reference
        return None

    def _feature_reference_by_id(self, feature_id: str) -> FeatureReference | None:
        if not feature_id:
            return None
        for feature in _project_feature_references(self.project):
            shape = feature.shape_reference
            if feature.id == feature_id or (shape is not None and shape.id == feature_id):
                return feature
        return None

    def _shape_reference_for_assembly_item(self, item_id: str, display_name: str):
        if not hasattr(self.geometry_session, "shape_references"):
            return None
        try:
            body_refs = self.geometry_session.shape_references({ShapeKind.BODY})
        except Exception:
            return None
        for shape_ref in body_refs:
            if shape_ref.id == item_id:
                return shape_ref
            if display_name and (
                display_name == shape_ref.fallback_display_name
                or display_name in shape_ref.assembly_path
            ):
                return shape_ref
        return None

    def _cross_highlight_shape(self, shape_ref) -> None:
        if not hasattr(self.viewer, "highlight"):
            return
        try:
            if hasattr(self.viewer, "clear_highlights"):
                self.viewer.clear_highlights([HighlightRole.CROSS_HIGHLIGHT])  # type: ignore[attr-defined]
            self.viewer.highlight(shape_ref, HighlightRole.CROSS_HIGHLIGHT)  # type: ignore[attr-defined]
        except Exception as exc:
            self.statusBar().showMessage(f"Viewer highlight unavailable: {exc}")

    def _sync_viewer_annotations(self, stackup_id: str) -> None:
        stackup = _stackup_by_id(self.project, stackup_id)
        annotations = _viewer_annotations_for_stackup(stackup) if stackup else ()
        self.viewport_host.set_annotations(annotations)

    def _workflow_annotations(self) -> tuple[ViewerAnnotation, ...]:
        if self.workflow_controller is None:
            return ()
        state = self.workflow_controller.state
        if state.start_feature is None and state.end_feature is None:
            return ()
        anchor = _viewer_anchor_from_position(state.annotation_position)
        position = (
            _screen_position_tuple(state.annotation_position)
            or (anchor.screen if anchor else None)
            or (0.58, 0.62)
        )
        shape_ids, feature_ids = _feature_reference_ids(
            [state.start_feature, state.end_feature, state.direction_feature]
        )
        return (
            ViewerAnnotation(
                id="workflow_stackup_dimension",
                label="0.000",
                role=ViewerAnnotationRole.STACKUP,
                start=(0.55, 0.34),
                end=(0.55, 0.72),
                label_position=position,
                shape_ids=shape_ids,
                feature_ids=feature_ids,
                anchor=anchor,
            ),
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
        self._update_status_counters()

    def _start_new_stackup_workflow(self) -> None:
        self.workflow_controller = GuidedStackupWorkflowController(
            self.geometry_session,
            self.project,
        )
        update = self.workflow_controller.start_new_stackup()
        self._apply_workflow_update(update)

    def _confirm_workflow_step(self) -> None:
        if self.workflow_controller is None:
            self.statusBar().showMessage("Start a new stackup before confirming a workflow step.")
            return
        try:
            update = self.workflow_controller.confirm_current_step()
        except ValueError as exc:
            self.statusBar().showMessage(str(exc))
            return
        self._apply_workflow_update(update)

    def _cancel_workflow(self) -> None:
        if self.workflow_controller is None:
            return
        update = self.workflow_controller.cancel()
        self._apply_workflow_update(update)
        self.workflow_controller = None
        self.viewport_host.set_annotations(())
        self.viewport_host.hide_workflow_toolbar()
        self.statusBar().showMessage("Canceled guided stackup workflow")

    def _start_add_feature_flow(self) -> None:
        stackup = _stackup_by_id(self.project, self.workspace.selected_stackup_id)
        if self.workflow_controller is None:
            if stackup is None:
                self.statusBar().showMessage("Create or select a stackup before adding a feature.")
                return
            self.workflow_controller = GuidedStackupWorkflowController(
                self.geometry_session,
                self.project,
            )
        try:
            update = self.workflow_controller.begin_add_feature(stackup)
        except ValueError as exc:
            self.statusBar().showMessage(str(exc))
            return
        self._apply_workflow_update(update)

    def _show_workflow_selection_list(self) -> None:
        if self.workflow_controller is None:
            self.statusBar().showMessage("No guided workflow is active.")
            return
        self.statusBar().showMessage(self.workflow_controller.selection_summary())

    def handle_viewer_selections(self, selections: list[CadViewerSelection] | tuple[CadViewerSelection, ...]) -> None:
        if not selections:
            return
        self._select_detail_row_for_selection(selections[0])
        if self.workflow_controller is None:
            return
        try:
            update = self.workflow_controller.apply_selection(selections[0])
        except ValueError as exc:
            recovery = self.workflow_controller.recover_from_invalid_selection(str(exc))
            self._apply_workflow_update(recovery)
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
        message = update.recovery_message or update.selection_filter.prompt
        self.statusBar().showMessage(message)
        if update.stackup is None:
            self.viewport_host.set_annotations(self._workflow_annotations())
        if update.stackup is not None:
            self.viewport_host.hide_workflow_toolbar()
            self.workspace = CadToleranceWorkspaceViewModel.from_project(self.project)
            self.summary_model.set_rows(self.workspace.summary_rows)
            self._set_detail_stackup(update.stackup.id)
            self._refresh_dashboard()
            self._sync_stackup_action_state()

    def _sync_stackup_action_state(self) -> None:
        has_stackups = bool(self.project.stackups)
        self.add_feature_action.setEnabled(has_stackups)
        self.generate_report_action.setEnabled(has_stackups)

    def _update_cad_source_status_ui(self) -> None:
        has_documents = bool(self.project.cad_documents)
        if hasattr(self, "refresh_source_action"):
            self.refresh_source_action.setEnabled(has_documents and self.project_path is not None)
        if hasattr(self, "reattach_source_action"):
            self.reattach_source_action.setEnabled(has_documents)
        if not hasattr(self, "cad_source_status_label"):
            return
        if not has_documents:
            self.cad_source_status_label.setText("Source: No CAD source")
            self.cad_source_status_label.setToolTip("")
            return
        document = self.project.cad_documents[0]
        label = SOURCE_STATUS_LABELS.get(document.source_status, "Unknown")
        source_name = (
            Path(document.source_path).name
            or document.display_name
            or "CAD source"
        )
        message = document.source_status_message or f"CAD source status: {label}"
        self.cad_source_status_label.setText(f"Source: {label} - {source_name}")
        self.cad_source_status_label.setToolTip(message)

    def show_summary(self) -> None:
        self.analysis_stack.setCurrentWidget(self.summary_page)

    def refresh_cad_source(self) -> None:
        if self.project_path is None:
            self.statusBar().showMessage("Save or load a project before refreshing CAD sources.")
            return
        self._rehydrate_project_cad_sources(self.project_path)
        self._update_cad_source_status_ui()
        if self.cad_source_status_messages:
            self.statusBar().showMessage("; ".join(self.cad_source_status_messages))
        else:
            self.statusBar().showMessage("No CAD source references to refresh.")

    def reattach_cad_source(
        self,
        path: str | Path,
        document_id: str = "",
    ) -> CadDocument:
        if not self.project.cad_documents:
            raise ValueError("Load or import a CAD document before reattaching a source.")
        document = _document_by_id(self.project, document_id) or self.project.cad_documents[0]
        input_path = Path(path)
        if not is_supported_neutral_cad(input_path):
            raise UnsupportedCadFormatError(
                f"Unsupported CAD source: {input_path.name}. "
                "Use STEP or IGES for P20 source reattach."
            )
        imported_document = self.geometry_session.import_file(
            input_path,
            _cad_import_settings_from_document(document, self.project),
        )
        validation = validate_cad_source_reimport(
            document,
            imported_document,
            _session_shape_references(self.geometry_session),
            _session_feature_references(self.geometry_session),
        )
        if hasattr(self.viewer, "display_document"):
            self.viewer.display_document(self.geometry_session)  # type: ignore[attr-defined]

        document.source_path = _source_path_for_project(input_path, self.project_path)
        document.file_hash = imported_document.file_hash
        document.source_topology_hash = validation.topology_hash
        document.file_format = imported_document.file_format
        document.imported_at = imported_document.imported_at
        document.units = imported_document.units
        document.assembly_root = imported_document.assembly_root
        document.display_name = imported_document.display_name or input_path.name
        document.import_settings = {
            **document.import_settings,
            **imported_document.import_settings,
        }

        status = validation.status
        message = validation.message
        if (
            status == CadSourceStatus.PRESENT
            and _is_project_local_cad_asset(input_path.resolve(), self.project_path)
        ):
            status = CadSourceStatus.PROJECT_LOCAL_PACKAGE_ASSET
            message = f"Reattached project-local CAD asset: {input_path.name}"
        elif status == CadSourceStatus.PRESENT:
            message = f"Reattached CAD source: {input_path.name}"
        else:
            message = f"Reattached CAD source: {input_path.name}; {message}"
        _set_document_source_status(
            document,
            status,
            message,
            topology_hash=validation.topology_hash,
            update_topology_hash=True,
        )

        self.workspace = CadToleranceWorkspaceViewModel.from_project(self.project)
        self.assembly_model.set_roots(self.workspace.assembly_roots)
        self.summary_model.set_rows(self.workspace.summary_rows)
        self._set_detail_stackup(self.workspace.selected_stackup_id)
        self._refresh_dashboard()
        self._sync_stackup_action_state()
        self._update_cad_source_status_ui()
        self.statusBar().showMessage(message)
        return document

    def _reattach_cad_source_dialog(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Reattach neutral CAD source",
            "",
            NEUTRAL_CAD_FILTER,
        )
        if not path:
            return
        try:
            self.reattach_cad_source(path)
        except Exception as exc:
            QMessageBox.warning(self, "CAD source reattach failed", str(exc))
            self.statusBar().showMessage("CAD source reattach failed")

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
        self._update_cad_source_status_ui()
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
            snapshot = self.viewport_host.capture_snapshot(
                SnapshotRequest(
                    output_path,
                    visible_stackup_ids=(stackup_id,) if stackup_id else (),
                    annotations=self.viewport_host.annotations,
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
        if self.project_path is not None:
            save_project(self.project, self.project_path)
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
            result = generate_html_report(
                self.project,
                output_path,
                generated_at=_utc_timestamp(),
                project_path=self.project_path,
            )
        except Exception as exc:
            QMessageBox.warning(self, "Report generation failed", str(exc))
            self.statusBar().showMessage("Report generation failed")
            return
        if self.project_path is not None:
            _upsert_report_manifest_entry(self.project, self.project_path, result)
            save_project(self.project, self.project_path)
        self.statusBar().showMessage(f"Generated report {result.output_path.name}")


def _cad_import_settings_from_document(
    document: CadDocument,
    project: CadToleranceProject,
) -> CadImportSettings:
    settings = dict(document.import_settings)
    return CadImportSettings(
        units=_unit_setting(str(settings.get("units") or document.units or project.unit_system)),
        heal_shapes=bool(settings.get("heal_shapes", True)),
        object_filter=str(
            settings.get("object_filter")
            or _object_filter_from_labels(settings.get("object_filters"))
            or "solids"
        ),
        include_edges=bool(settings.get("include_edges", True)),
        include_vertices=bool(settings.get("include_vertices", True)),
    )


def _cad_import_settings_from_dialog(settings: dict[str, Any]) -> CadImportSettings:
    filters = settings.get("object_filters")
    return CadImportSettings(
        units=_unit_setting(str(settings.get("units") or "mm")),
        heal_shapes=True,
        object_filter=_object_filter_from_labels(filters) or "solids",
        include_edges=_filter_enabled(filters, "Wires"),
        include_vertices=_filter_enabled(filters, "Points"),
    )


def _unit_setting(value: str) -> str:
    normalized = value.strip().lower()
    return {
        "from source": "mm",
        "millimeters": "mm",
        "millimetres": "mm",
        "mm": "mm",
        "inches": "in",
        "inch": "in",
        "in": "in",
        "centimeters": "cm",
        "centimetres": "cm",
        "cm": "cm",
    }.get(normalized, value or "mm")


def _object_filter_from_labels(value: Any) -> str:
    if isinstance(value, str):
        return value
    if not isinstance(value, (list, tuple)):
        return ""
    return ",".join(str(item).lower().replace(" ", "_") for item in value if item)


def _filter_enabled(filters: Any, label: str) -> bool:
    if not isinstance(filters, (list, tuple)):
        return True
    return label in filters


def _session_shape_references(session: Any) -> list[Any]:
    try:
        return list(session.shape_references())
    except Exception:
        return []


def _session_feature_references(session: Any) -> list[Any]:
    try:
        return list(session.feature_references())
    except Exception:
        return []


def _set_document_source_status(
    document: CadDocument,
    status: CadSourceStatus,
    message: str,
    *,
    topology_hash: str = "",
    update_topology_hash: bool = False,
) -> None:
    document.source_status = status
    document.source_status_message = message
    document.source_last_checked_at = _utc_timestamp()
    if topology_hash and (update_topology_hash or not document.source_topology_hash):
        document.source_topology_hash = topology_hash


def _document_by_id(
    project: CadToleranceProject,
    document_id: str,
) -> CadDocument | None:
    if not document_id:
        return None
    for document in project.cad_documents:
        if document.id == document_id:
            return document
    return None


def _source_path_for_project(path: Path, project_path: Path | None) -> str:
    if project_path is None:
        return str(path)
    return project_relative_path(path, project_path)


def _find_relocated_cad_source(
    document: CadDocument,
    project_path: Path,
) -> Path | None:
    name = Path(document.source_path).name
    if not name:
        return None
    roots = [
        project_asset_dir(project_path) / "cad",
        project_path.parent / "assets" / "cad",
        project_path.parent,
    ]
    candidates: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        try:
            candidates.extend(
                path
                for path in root.rglob(name)
                if path.is_file() and is_supported_neutral_cad(path)
            )
        except OSError:
            continue
    if not candidates:
        return None
    wanted_hash = document.file_hash
    if wanted_hash:
        for candidate in candidates:
            try:
                if f"sha256:{_sha256_file(candidate)}" == wanted_hash:
                    return candidate.resolve()
            except OSError:
                continue
    return candidates[0].resolve()


def _is_project_local_cad_asset(
    path: Path,
    project_path: Path | None,
) -> bool:
    if project_path is None:
        return False
    resolved = path.resolve()
    roots = [
        project_asset_dir(project_path).resolve(),
        (project_path.parent / "assets").resolve(),
    ]
    for root in roots:
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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


def _first_stackup_shape_reference(stackup: StackupRequirement):
    for feature in _stackup_features(stackup):
        if feature.shape_reference is not None:
            return feature.shape_reference
    return None


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _upsert_report_manifest_entry(
    project: CadToleranceProject,
    project_path: Path,
    result: ReportGenerationResult,
) -> None:
    report_dir = result.output_path.parent

    def rel(path: Path) -> str:
        return project_relative_path(path, project_path).replace("\\", "/")

    html_path = rel(result.output_path)
    manifest_path = rel(result.manifest_path) if result.manifest_path is not None else ""
    entry = {
        "id": _report_entry_id(html_path),
        "title": result.manifest.get("title", "Tolerance Stackup Report"),
        "generated_at": result.manifest.get("generated_at", ""),
        "path": html_path,
        "html_path": html_path,
        "manifest_path": manifest_path,
        "css_path": rel(report_dir / "css" / "report.css"),
        "js_path": rel(report_dir / "js" / "report.js"),
        "asset_paths": [rel(path) for path in result.asset_paths],
        "snapshot_ids": list(result.manifest.get("snapshot_ids", [])),
        "stackup_ids": list(result.manifest.get("stackup_ids", [])),
        "report_format": result.manifest.get("report_format", ""),
        "report_format_version": result.manifest.get("report_format_version", 1),
    }
    for index, existing in enumerate(project.reports):
        if existing.get("html_path") == html_path or existing.get("path") == html_path:
            project.reports[index] = entry
            return
    project.reports.append(entry)


def _report_entry_id(html_path: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "_" for char in html_path)
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return f"report_{cleaned.strip('_') or 'html'}"


def _project_feature_references(project: CadToleranceProject) -> list[FeatureReference]:
    features: list[FeatureReference] = []

    def collect(feature: FeatureReference | None) -> None:
        if feature is None:
            return
        if all(existing.id != feature.id for existing in features):
            features.append(feature)

    for stackup in project.stackups:
        collect(stackup.start_feature)
        collect(stackup.end_feature)
        for feature in stackup.loop_features:
            collect(feature)
        for feature in stackup.constraint_features:
            collect(feature)
        for contributor in stackup.contributors:
            collect(contributor.source_feature)
    return features


def _detail_row_matches_selection(
    row: StackupDetailRow,
    selection: CadViewerSelection,
    feature_lookup,
) -> bool:
    if not row.source_feature_id:
        return False
    selected_ids = {selection.shape_id, selection.feature_id}
    feature = feature_lookup(row.source_feature_id)
    if feature is not None:
        selected_ids.add(feature.id)
        if feature.shape_reference is not None:
            selected_ids.add(feature.shape_reference.id)
    return row.source_feature_id in selected_ids


def _viewer_annotations_for_stackup(
    stackup: StackupRequirement | None,
) -> tuple[ViewerAnnotation, ...]:
    if stackup is None:
        return ()
    shape_ids, feature_ids = _snapshot_reference_ids(stackup)
    stackup_anchor = _stackup_viewer_anchor(stackup)
    position = (
        _screen_position_tuple(stackup.annotation_position)
        or (stackup_anchor.screen if stackup_anchor else None)
        or (0.58, 0.56)
    )
    annotations = [
        ViewerAnnotation(
            id=f"{stackup.id}:stackup",
            label=f"{stackup.objective.nominal:.3f}",
            role=ViewerAnnotationRole.STACKUP,
            start=(0.54, 0.34),
            end=(0.54, 0.72),
            label_position=position,
            shape_ids=shape_ids,
            feature_ids=feature_ids,
            anchor=stackup_anchor,
        )
    ]
    for index, contributor in enumerate(stackup.contributors[:4], start=1):
        x = min(0.86, 0.64 + index * 0.055)
        contributor_anchor = _contributor_viewer_anchor(
            contributor,
            screen=(min(0.94, x + 0.045), 0.44 + index * 0.065),
        )
        annotations.append(
            ViewerAnnotation(
                id=f"{stackup.id}:{contributor.id}",
                label=f"{contributor.nominal:.3f}",
                role=ViewerAnnotationRole.CONTRIBUTOR,
                start=(x, 0.30 + index * 0.025),
                end=(x, 0.70 - index * 0.025),
                label_position=(min(0.94, x + 0.045), 0.44 + index * 0.065),
                shape_ids=(
                    (contributor.source_feature.shape_reference.id,)
                    if contributor.source_feature
                    and contributor.source_feature.shape_reference is not None
                    else ()
                ),
                feature_ids=(
                    (contributor.source_feature.id,)
                    if contributor.source_feature is not None
                    else ()
                ),
                anchor=contributor_anchor,
            )
        )
    for index, warning in enumerate(stackup.warnings[:3], start=1):
        warning_anchor = _warning_viewer_anchor(stackup, warning, index)
        annotations.append(
            ViewerAnnotation(
                id=f"{stackup.id}:{warning.id}",
                label="!",
                role=ViewerAnnotationRole.WARNING,
                start=(0.36 + index * 0.035, 0.22),
                end=(0.36 + index * 0.035, 0.28),
                label_position=warning_anchor.screen
                if warning_anchor and warning_anchor.screen
                else (0.34 + index * 0.04, 0.18),
                shape_ids=tuple(_shape_ids_for_warning(stackup, warning.feature_ids)),
                feature_ids=tuple(warning.feature_ids),
                anchor=warning_anchor,
                draggable=False,
            )
        )
    return tuple(annotations)


def _feature_reference_ids(
    features: list[FeatureReference | None],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    shape_ids: list[str] = []
    feature_ids: list[str] = []
    for feature in features:
        if feature is None:
            continue
        if feature.id and feature.id not in feature_ids:
            feature_ids.append(feature.id)
        shape = feature.shape_reference
        if shape is not None and shape.id and shape.id not in shape_ids:
            shape_ids.append(shape.id)
    return tuple(shape_ids), tuple(feature_ids)


def _screen_position_tuple(position: dict[str, Any]) -> tuple[float, float] | None:
    screen = position.get("screen") if isinstance(position, dict) else None
    if (
        isinstance(screen, (list, tuple))
        and len(screen) == 2
        and all(isinstance(value, (int, float)) for value in screen)
    ):
        return (max(0.0, min(1.0, float(screen[0]))), max(0.0, min(1.0, float(screen[1]))))
    return None


def _clean_annotation_payload(position: dict[str, Any]) -> dict[str, Any]:
    anchor = ViewerAnnotationAnchor.from_dict(position)
    if anchor is not None:
        return anchor.to_dict()
    screen = _screen_position_tuple(position)
    if screen is None:
        return {}
    return {"kind": "viewport", "version": 1, "screen": [screen[0], screen[1]]}


def _viewer_anchor_from_position(position: dict[str, Any]) -> ViewerAnnotationAnchor | None:
    if not isinstance(position, dict):
        return None
    return ViewerAnnotationAnchor.from_dict(position)


def _stackup_viewer_anchor(stackup: StackupRequirement) -> ViewerAnnotationAnchor:
    persisted = _viewer_anchor_from_position(stackup.annotation_position)
    start_model = (persisted.start_model if persisted else None) or _feature_model_point(stackup.start_feature)
    end_model = (persisted.end_model if persisted else None) or _feature_model_point(stackup.end_feature)
    label_model = (
        (persisted.label_model if persisted else None)
        or _midpoint3(start_model, end_model)
        or _feature_model_point(stackup.start_feature)
    )
    leader_points = persisted.leader_model_points if persisted else ()
    if not leader_points:
        leader_points = tuple(point for point in (start_model, end_model) if point is not None)
    return ViewerAnnotationAnchor(
        start_model=start_model,
        end_model=end_model,
        label_model=label_model,
        leader_model_points=leader_points,
        screen=(persisted.screen if persisted else _screen_position_tuple(stackup.annotation_position)),
        source_feature_id=stackup.annotation_plane.source_feature_id,
        metadata={"source": "stackup_requirement", "stackup_id": stackup.id},
    )


def _contributor_viewer_anchor(
    contributor: StackupContributor,
    *,
    screen: tuple[float, float],
) -> ViewerAnnotationAnchor | None:
    point = _feature_model_point(contributor.source_feature)
    return ViewerAnnotationAnchor(
        start_model=point,
        end_model=point,
        label_model=point,
        screen=screen,
        source_feature_id=contributor.source_feature.id
        if contributor.source_feature is not None
        else "",
        metadata={"source": "stackup_contributor", "contributor_id": contributor.id},
    )


def _warning_viewer_anchor(
    stackup: StackupRequirement,
    warning,
    index: int,
) -> ViewerAnnotationAnchor:
    feature = _first_warning_feature(stackup, warning.feature_ids)
    point = _feature_model_point(feature) or _feature_model_point(stackup.start_feature)
    screen = (min(0.92, 0.34 + index * 0.04), 0.18)
    return ViewerAnnotationAnchor(
        start_model=point,
        end_model=point,
        label_model=point,
        screen=screen,
        source_feature_id=feature.id if feature is not None else "",
        metadata={"source": "stackup_warning", "warning_id": warning.id},
    )


def _first_warning_feature(
    stackup: StackupRequirement,
    feature_ids: list[str],
) -> FeatureReference | None:
    wanted = set(feature_ids)
    for feature in _stackup_features(stackup):
        shape = feature.shape_reference
        if feature.id in wanted or (shape is not None and shape.id in wanted):
            return feature
    return None


def _shape_ids_for_warning(
    stackup: StackupRequirement,
    feature_ids: list[str],
) -> list[str]:
    wanted = set(feature_ids)
    shape_ids: list[str] = []
    for feature in _stackup_features(stackup):
        shape = feature.shape_reference
        if feature.id in wanted and shape is not None and shape.id not in shape_ids:
            shape_ids.append(shape.id)
    return shape_ids


def _stackup_features(stackup: StackupRequirement) -> list[FeatureReference]:
    features: list[FeatureReference] = []

    def collect(feature: FeatureReference | None) -> None:
        if feature is not None and all(existing.id != feature.id for existing in features):
            features.append(feature)

    collect(stackup.start_feature)
    collect(stackup.end_feature)
    for feature in stackup.loop_features:
        collect(feature)
    for feature in stackup.constraint_features:
        collect(feature)
    for contributor in stackup.contributors:
        collect(contributor.source_feature)
    return features


def _feature_model_point(
    feature: FeatureReference | None,
) -> tuple[float, float, float] | None:
    if feature is None:
        return None
    if feature.point is not None:
        return (feature.point.x, feature.point.y, feature.point.z)
    shape = feature.shape_reference
    if shape is None:
        return None
    signature = shape.geometric_signature
    return (
        _tuple3(signature.get("point"))
        or _tuple3(signature.get("center"))
        or _tuple3(signature.get("origin"))
    )


def _tuple3(value: Any) -> tuple[float, float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    if not all(isinstance(item, (int, float)) for item in value):
        return None
    return float(value[0]), float(value[1]), float(value[2])


def _midpoint3(
    a: tuple[float, float, float] | None,
    b: tuple[float, float, float] | None,
) -> tuple[float, float, float] | None:
    if a is None or b is None:
        return a or b
    return (
        (a[0] + b[0]) / 2.0,
        (a[1] + b[1]) / 2.0,
        (a[2] + b[2]) / 2.0,
    )


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
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#e3eff9"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#111111"))
    app.setPalette(palette)

    app.setStyleSheet(
        """
        QMainWindow {
            background: #f2f2f2;
        }
        QTabWidget#RibbonTabs::pane {
            border: 0;
            border-bottom: 1px solid #c8c8c8;
            background: #f6f6f6;
        }
        QTabWidget#RibbonTabs QTabBar::tab {
            min-height: 24px;
            padding: 3px 12px;
            background: #525252;
            color: #f0f0f0;
            border-right: 1px solid #656565;
        }
        QTabWidget#RibbonTabs QTabBar::tab:selected {
            background: #f6f6f6;
            color: #202020;
            border-right: 1px solid #d9d9d9;
        }
        QTabWidget#RibbonTabs QTabBar::tab:first {
            background: #ee842b;
            color: #ffffff;
            border-right: 1px solid #c86a1f;
        }
        QTabWidget#RibbonTabs QTabBar::tab:first:selected {
            background: #ee842b;
            color: #ffffff;
        }
        QToolButton {
            border: 1px solid transparent;
            padding: 4px;
        }
        QToolButton[ribbonCommand="true"] {
            min-width: 76px;
            max-width: 116px;
            min-height: 54px;
            padding: 2px 4px;
            color: #202020;
            font-size: 10px;
        }
        QToolButton[ribbonCommand="true"]:disabled {
            color: #9a9a9a;
        }
        QToolButton:hover, QPushButton:hover {
            background: #e4f0fb;
            border: 1px solid #7aa7d9;
        }
        QFrame[ribbonGroup="true"] {
            border-right: 1px solid #d9d9d9;
            background: #f6f6f6;
        }
        QLabel#RibbonGroupLabel {
            color: #555555;
            font-size: 10px;
            padding-top: 1px;
        }
        QFrame#ModelBrowserPanel {
            background: #ffffff;
            border-right: 1px solid #d9d9d9;
        }
        QLabel#DockHeaderTitle {
            font-weight: 700;
            padding: 0;
        }
        QToolButton#ModelBrowserHelpButton, QToolButton#ModelBrowserCloseButton {
            min-width: 18px;
            max-width: 18px;
            min-height: 18px;
            padding: 0;
        }
        QFrame#AssemblyBrowserToolbar {
            border-top: 1px solid #d0d0d0;
            border-bottom: 1px solid #d0d0d0;
            background: #f7f7f7;
        }
        QFrame#AssemblyBrowserToolbar QToolButton {
            min-height: 20px;
            padding: 1px 3px;
        }
        QLabel#CadSourceStatusLabel {
            color: #555555;
            font-size: 9px;
            padding: 2px 6px;
            border-bottom: 1px solid #eeeeee;
        }
        QTreeView#AssemblyTreeView {
            selection-background-color: #e3eff9;
            border: 0;
            alternate-background-color: #f3f3f3;
            font-size: 10px;
        }
        QFrame#CadViewportHost, QFrame#PlaceholderCadViewer {
            background: #c4c4c4;
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
        QFrame#ViewCubeWidget {
            background: rgba(240, 240, 240, 165);
            border: 1px solid #9c9c9c;
        }
        QToolBar#ViewportNavigationToolbar {
            background: rgba(235, 235, 235, 185);
            border: 1px solid #a5a5a5;
        }
        QToolBar#ViewportNavigationToolbar QToolButton {
            min-width: 26px;
            max-width: 28px;
            min-height: 25px;
            padding: 1px;
        }
        QWidget#AxisTriadWidget {
            background: transparent;
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
        QFrame#GuidedStackupToolbar QPushButton[controlRole="ok"] {
            background: #dff2e3;
            border-color: #5aa36b;
        }
        QFrame#GuidedStackupToolbar QPushButton[controlRole="cancel"] {
            background: #f9dedc;
            border-color: #c65f58;
        }
        QFrame#GuidedStackupToolbar QPushButton[controlRole="add"] {
            background: #fff0cf;
            border-color: #c99125;
        }
        QFrame#GuidedStackupToolbar QPushButton[controlRole="list"] {
            background: #e8edf4;
            border-color: #7e91ad;
        }
        QLabel#AnalysisPaneTitle {
            font-size: 15px;
            font-weight: 700;
        }
        QLabel#AnalysisPaneBrand {
            color: #333333;
            padding-left: 2px;
        }
        QTableView {
            gridline-color: #d0d0d0;
            selection-background-color: #e3eff9;
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
        QWidget#ResultPlotWidget {
            background: #ffffff;
            min-height: 150px;
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
            padding: 2px 0;
        }
        QWidget#ContributionRow {
            min-height: 26px;
        }
        QWidget#ContributionBarMeter {
            background: #ffffff;
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
        QLabel#StatusStackupCountLabel, QLabel#StatusSelectionCountLabel {
            min-width: 44px;
            padding: 0 8px;
            border-left: 1px solid #d0d0d0;
            color: #333333;
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
