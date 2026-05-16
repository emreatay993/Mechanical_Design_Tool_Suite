"""Standalone PyQt6 tolerance analysis calculator."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

from .tolerance import StackupAnalysis, ToleranceDimension, calculate_stackup
from .app_icons import app_icon

try:
    from PyQt6.QtCore import QLineF, QMarginsF, QRectF, QSize, QSizeF, Qt
    from PyQt6.QtGui import (
        QColor,
        QDoubleValidator,
        QFont,
        QFontDatabase,
        QImage,
        QPageLayout,
        QPageSize,
        QPainter,
        QPalette,
        QPdfWriter,
        QPen,
    )
    from PyQt6.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QStyle,
        QStyleFactory,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover - exercised only without GUI deps.
    raise RuntimeError(
        "The tolerance analysis GUI requires PyQt6. Install the package with "
        "`python -m pip install -e .` before launching the GUI."
    ) from exc


PLUS_MINUS = "\u00b1"
PURPLE = QColor("#281e78")
TEXT = QColor("#303030")
MUTED = QColor("#919191")
WORST_LIGHT = QColor("#7fd7ed")
WORST_DARK = QColor("#338ba1")
RSS_LIGHT = QColor("#fb9c95")
RSS_DARK = QColor("#d56159")


class CircleXButton(QPushButton):
    """Filled circle-x remove button drawn with Qt vector primitives."""

    def __init__(self) -> None:
        super().__init__()
        self.setAccessibleName("Remove dimension")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(24, 24)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFlat(True)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override name.
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.isDown():
            fill = QColor("#111111")
        elif self.underMouse():
            fill = QColor("#1f1f1f")
        else:
            fill = QColor("#303030")

        size = 22.0
        left = (self.width() - size) / 2.0
        top = (self.height() - size) / 2.0
        circle = QRectF(left, top, size, size)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fill)
        painter.drawEllipse(circle)

        inset = 7.0
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(
            QPen(
                QColor("#ffffff"),
                2.4,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )
        painter.drawLine(
            QLineF(
                circle.left() + inset,
                circle.top() + inset,
                circle.right() - inset,
                circle.bottom() - inset,
            )
        )
        painter.drawLine(
            QLineF(
                circle.right() - inset,
                circle.top() + inset,
                circle.left() + inset,
                circle.bottom() - inset,
            )
        )

    def enterEvent(self, event) -> None:  # noqa: N802 - Qt override name.
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802 - Qt override name.
        super().leaveEvent(event)
        self.update()


class StackupPlot(QWidget):
    """Paints the stackup graphic from the Five Flute calculator."""

    def __init__(self) -> None:
        super().__init__()
        self.analysis: StackupAnalysis | None = None
        self.setMinimumWidth(1040)
        self.setMinimumHeight(260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_analysis(self, analysis: StackupAnalysis | None) -> None:
        self.analysis = analysis
        self.setMinimumHeight(self._height_for_analysis())
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(1160, self._height_for_analysis())

    def _height_for_analysis(self) -> int:
        row_count = len(self.analysis.dimensions) if self.analysis else 4
        return max(245, 80 + row_count * 26 + 100)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override name.
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#ffffff"))

        if self.analysis is None:
            painter.setPen(TEXT)
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Add dimensions to calculate the stackup.",
            )
            return

        analysis = self.analysis
        width = self.width()
        label_right = 237
        plot_left = 290
        plot_right = max(plot_left + 320, width - 70)
        top_line_y = 34
        target_top = 18
        first_bar_y = 48
        row_step = 27
        bar_height = 13
        average_y = first_bar_y + len(analysis.dimensions) * row_step + 18
        worst_y = average_y + 31
        rss_y = worst_y + 27
        bottom_y = rss_y + 26

        x_min, x_max = self._scale_range(analysis)

        def map_x(value: float) -> float:
            if x_max == x_min:
                return float(plot_left)
            return plot_left + (value - x_min) / (x_max - x_min) * (
                plot_right - plot_left
            )

        painter.setPen(QPen(MUTED, 1))
        painter.drawLine(0, top_line_y, width, top_line_y)
        painter.drawLine(label_right + 8, top_line_y - 9, label_right + 8, bottom_y)
        self._draw_line(painter, map_x(0.0), top_line_y - 9, map_x(0.0), bottom_y)

        self._draw_target_marker(
            painter,
            map_x(analysis.target_min),
            target_top,
            bottom_y,
            f"{analysis.target_min:.4f}",
            Qt.AlignmentFlag.AlignRight,
        )
        self._draw_target_marker(
            painter,
            map_x(analysis.target_max),
            target_top,
            bottom_y,
            f"{analysis.target_max:.4f}",
            Qt.AlignmentFlag.AlignLeft,
        )

        cumulative = 0.0
        for index, dimension_result in enumerate(analysis.dimensions):
            dimension = dimension_result.dimension
            y = first_bar_y + index * row_step
            start = cumulative
            cumulative += dimension.nominal
            self._draw_left_text(painter, label_right, y + 11, dimension.name, PURPLE)
            self._draw_span(painter, map_x(start), map_x(cumulative), y, bar_height, PURPLE)
            if index < len(analysis.dimensions) - 1:
                painter.setPen(QPen(PURPLE, 1))
                self._draw_line(
                    painter,
                    map_x(cumulative),
                    y + bar_height,
                    map_x(cumulative),
                    y + row_step + bar_height,
                )
            text_x = min(map_x(cumulative) + 8, plot_right - 128)
            painter.fillRect(QRectF(text_x - 2, y - 1, 128, 18), QColor("#ffffff"))
            painter.setPen(TEXT)
            painter.setFont(QFont(painter.font().family(), 8))
            painter.drawText(
                QRectF(text_x, y - 1, 126, 18),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                f"{dimension.nominal:.4f} {PLUS_MINUS} {dimension.tolerance:.4f}",
            )

        self._draw_left_text(
            painter,
            label_right,
            average_y + 12,
            "Average assembly dimension",
            TEXT,
        )
        self._draw_value_at(
            painter,
            map_x(analysis.nominal),
            average_y + 12,
            f"{analysis.nominal:.4f}",
            TEXT,
        )

        self._draw_left_text(
            painter,
            label_right,
            worst_y + 11,
            "Worse case tolerance",
            WORST_DARK,
        )
        self._draw_span(
            painter,
            map_x(0.0),
            map_x(analysis.nominal),
            worst_y,
            bar_height,
            WORST_LIGHT,
        )
        self._draw_span(
            painter,
            map_x(analysis.worst_case_min),
            map_x(analysis.worst_case_max),
            worst_y + 2,
            bar_height - 4,
            WORST_DARK,
        )
        self._draw_range_labels(
            painter,
            map_x(analysis.worst_case_min),
            map_x(analysis.worst_case_max),
            worst_y + 11,
            analysis.worst_case_min,
            analysis.worst_case_max,
        )

        self._draw_left_text(painter, label_right, rss_y + 11, "RSS tolerance", RSS_DARK)
        self._draw_span(
            painter,
            map_x(0.0),
            map_x(analysis.nominal),
            rss_y,
            bar_height,
            RSS_LIGHT,
        )
        self._draw_span(
            painter,
            map_x(analysis.rss_min),
            map_x(analysis.rss_max),
            rss_y + 2,
            bar_height - 4,
            RSS_DARK,
        )
        self._draw_range_labels(
            painter,
            map_x(analysis.rss_min),
            map_x(analysis.rss_max),
            rss_y + 11,
            analysis.rss_min,
            analysis.rss_max,
        )

    def _scale_range(self, analysis: StackupAnalysis) -> tuple[float, float]:
        values = [
            0.0,
            analysis.target_min,
            analysis.target_max,
            analysis.nominal,
            analysis.worst_case_min,
            analysis.worst_case_max,
            analysis.rss_min,
            analysis.rss_max,
        ]
        cumulative = 0.0
        values.append(cumulative)
        for dimension in analysis.dimensions:
            cumulative += dimension.dimension.nominal
            values.append(cumulative)

        low = min(values)
        high = max(values)
        span = high - low
        if span == 0.0:
            span = 1.0
        pad = span * 0.08
        return low - pad, high + pad

    def _draw_span(
        self,
        painter: QPainter,
        x1: float,
        x2: float,
        y: float,
        height: float,
        color: QColor,
    ) -> None:
        left = min(x1, x2)
        width = max(abs(x2 - x1), 1.0)
        painter.fillRect(QRectF(left, y, width, height), color)

    def _draw_line(
        self,
        painter: QPainter,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> None:
        painter.drawLine(QLineF(float(x1), float(y1), float(x2), float(y2)))

    def _draw_left_text(
        self,
        painter: QPainter,
        x: int,
        baseline: int,
        text: str,
        color: QColor,
    ) -> None:
        painter.setPen(color)
        painter.setFont(QFont(painter.font().family(), 9))
        painter.drawText(
            QRectF(12, baseline - 14, x - 16, 18),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            text,
        )

    def _draw_value_at(
        self,
        painter: QPainter,
        x: float,
        baseline: int,
        text: str,
        color: QColor,
    ) -> None:
        painter.fillRect(QRectF(x - 28, baseline - 14, 56, 18), QColor("#ffffff"))
        painter.setPen(color)
        painter.setFont(QFont(painter.font().family(), 9))
        painter.drawText(
            QRectF(x - 36, baseline - 14, 72, 18),
            Qt.AlignmentFlag.AlignCenter,
            text,
        )

    def _draw_target_marker(
        self,
        painter: QPainter,
        x: float,
        y1: int,
        y2: int,
        label: str,
        alignment: Qt.AlignmentFlag,
    ) -> None:
        painter.setPen(QPen(PURPLE, 1))
        self._draw_line(painter, x, y1, x, y2)
        painter.setPen(PURPLE)
        painter.setFont(QFont(painter.font().family(), 8))
        if alignment == Qt.AlignmentFlag.AlignRight:
            rect = QRectF(x - 62, 0, 58, 16)
        else:
            rect = QRectF(x + 4, 0, 58, 16)
        painter.drawText(rect, alignment | Qt.AlignmentFlag.AlignVCenter, label)

    def _draw_range_labels(
        self,
        painter: QPainter,
        left_x: float,
        right_x: float,
        baseline: int,
        left_value: float,
        right_value: float,
    ) -> None:
        painter.setPen(TEXT)
        painter.setFont(QFont(painter.font().family(), 8))
        painter.drawText(
            QRectF(left_x - 66, baseline - 14, 62, 18),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            f"{left_value:.4f}",
        )
        painter.fillRect(QRectF(right_x + 3, baseline - 14, 48, 18), QColor("#ffffff"))
        painter.drawText(
            QRectF(right_x + 6, baseline - 14, 52, 18),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            f"{right_value:.4f}",
        )


class ToleranceAnalysisApp(QMainWindow):
    """Standalone clone of the Five Flute tolerance analysis calculator."""

    def __init__(self) -> None:
        super().__init__()
        self.analysis: StackupAnalysis | None = None
        self._updating = False

        self.setWindowTitle("Tolerance Analysis")
        self.resize(1500, 900)
        self.setMinimumSize(1020, 700)
        self._build_layout()
        self._load_default_dimensions()
        self._recalculate()

    def _build_layout(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.setCentralWidget(scroll)
        self.page_scroll = scroll

        content = QWidget()
        content.setObjectName("AppSurface")
        content.setMinimumWidth(980)
        scroll.setWidget(content)
        self.export_content = content

        root = QVBoxLayout(content)
        root.setContentsMargins(14, 12, 14, 22)
        root.setSpacing(18)

        crumb = QFrame()
        crumb.setObjectName("BreadcrumbBar")
        crumb_layout = QHBoxLayout(crumb)
        crumb_layout.setContentsMargins(0, 0, 0, 0)
        icon = QLabel("\u25a3")
        icon.setObjectName("BreadcrumbIcon")
        crumb_label = QLabel("Tolerance Analysis")
        crumb_label.setObjectName("BreadcrumbLabel")
        crumb_layout.addWidget(icon)
        crumb_layout.addWidget(crumb_label)
        crumb_layout.addStretch(1)
        root.addWidget(crumb)

        title_row = QHBoxLayout()
        title_row.setSpacing(12)
        self.title_edit = QLineEdit("New Tolerance Analysis")
        self.title_edit.setObjectName("PageTitleEdit")
        self.title_edit.setPlaceholderText("Tolerance analysis title")
        self.title_edit.setClearButtonEnabled(False)
        self.title_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        title_row.addWidget(self.title_edit, 1)
        save_button = QPushButton("Save tolerance analysis")
        save_button.setEnabled(False)
        save_button.setObjectName("DisabledToolbarButton")
        title_row.addWidget(save_button)
        share_button = QPushButton("Share")
        share_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        share_button.setToolTip("Export this tolerance analysis as PDF or PNG")
        share_button.clicked.connect(self._export_page)
        title_row.addWidget(share_button)
        root.addLayout(title_row)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("Divider")
        root.addWidget(divider)

        root.addWidget(self._section_label("Inputs:", "Dimensions and bilateral tolerances in stackup"))
        self.dimension_table = self._build_dimension_table()
        root.addWidget(self.dimension_table)

        button_row = QHBoxLayout()
        button_row.setSpacing(4)
        add_button = QPushButton("Add dimension")
        add_button.setObjectName("PrimaryAction")
        add_button.clicked.connect(self._add_default_dimension)
        clear_button = QPushButton("Clear")
        clear_button.setObjectName("PrimaryAction")
        clear_button.clicked.connect(self._clear_dimensions)
        button_row.addWidget(add_button)
        button_row.addWidget(clear_button)
        button_row.addStretch(1)
        root.addLayout(button_row)

        root.addWidget(self._section_label("Inputs:", "Design targets for assembly dimension"))
        target_frame = QFrame()
        target_frame.setObjectName("FlatTableFrame")
        target_layout = QGridLayout(target_frame)
        target_layout.setContentsMargins(0, 0, 0, 0)
        target_layout.setHorizontalSpacing(0)
        target_layout.setVerticalSpacing(0)
        target_layout.addWidget(self._table_header("Target min dimension for stackup"), 0, 0)
        target_layout.addWidget(self._table_header("Target max dimension for stackup"), 0, 1)
        self.target_min_edit = self._number_edit("0.001")
        self.target_max_edit = self._number_edit("0.022")
        target_layout.addWidget(self.target_min_edit, 1, 0)
        target_layout.addWidget(self.target_max_edit, 1, 1)
        self.target_min_edit.textChanged.connect(self._recalculate)
        self.target_max_edit.textChanged.connect(self._recalculate)
        root.addWidget(target_frame)

        root.addWidget(
            self._section_label(
                "Outputs:",
                "Stackup plot with worst case & root sum squared (RSS) tolerances",
            )
        )
        plot_scroll = QScrollArea()
        plot_scroll.setWidgetResizable(True)
        plot_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.plot = StackupPlot()
        plot_scroll.setWidget(self.plot)
        plot_scroll.setMinimumHeight(285)
        root.addWidget(plot_scroll)

        root.addWidget(
            self._section_label(
                "Outputs:",
                "Dimension analysis with worst case and RSS tolerance failure rates",
            )
        )
        self.analysis_table = self._build_analysis_table()
        root.addWidget(self.analysis_table)

        self.status_label = QLabel("")
        self.status_label.setObjectName("StatusLine")
        root.addWidget(self.status_label)

    def _section_label(self, prefix: str, text: str) -> QLabel:
        label = QLabel(f"<span style='color:#919191'>{prefix}</span> {text}")
        label.setObjectName("SectionLabel")
        return label

    def _build_dimension_table(self) -> QTableWidget:
        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(
            ("Name", "Nominal dimension", f"{PLUS_MINUS} tolerance", "")
        )
        for column in range(table.columnCount()):
            header_item = table.horizontalHeaderItem(column)
            if header_item is None:
                continue
            alignment = Qt.AlignmentFlag.AlignLeft if column == 0 else Qt.AlignmentFlag.AlignCenter
            header_item.setTextAlignment(alignment | Qt.AlignmentFlag.AlignVCenter)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(49)
        table.setShowGrid(False)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(1, 170)
        table.setColumnWidth(2, 150)
        table.setColumnWidth(3, 54)
        table.setMinimumHeight(232)
        return table

    def _build_analysis_table(self) -> QTableWidget:
        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(
            ("Dimension", "Nominal", "Tolerance", "Std. Deviation", "Variance")
        )
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(24)
        table.setShowGrid(False)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, 5):
            table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            table.setColumnWidth(column, 150)
        table.setMinimumHeight(195)
        return table

    def _table_header(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("InlineTableHeader")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumHeight(30)
        return label

    def _number_edit(self, value: str) -> QLineEdit:
        edit = QLineEdit(value)
        edit.setObjectName("NumberEdit")
        edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        validator = QDoubleValidator(edit)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        edit.setValidator(validator)
        edit.setMinimumHeight(28)
        return edit

    def _dimension_text_edit(self, value: str, centered: bool = False) -> QLineEdit:
        edit = QLineEdit(value)
        edit.setObjectName("DimensionTextEdit" if not centered else "DimensionNumberEdit")
        alignment = Qt.AlignmentFlag.AlignCenter if centered else Qt.AlignmentFlag.AlignLeft
        edit.setAlignment(alignment | Qt.AlignmentFlag.AlignVCenter)
        edit.setMinimumHeight(34)
        edit.textChanged.connect(self._recalculate)
        return edit

    def _dimension_number_edit(self, value: str, allow_negative: bool) -> QLineEdit:
        edit = self._dimension_text_edit(value, centered=True)
        validator = QDoubleValidator(edit)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        if not allow_negative:
            validator.setBottom(0.0)
        edit.setValidator(validator)
        return edit

    def _load_default_dimensions(self) -> None:
        self._updating = True
        self.dimension_table.setRowCount(0)
        for index in range(4):
            self._insert_dimension_row(f"#{index + 1}", "1", "0.005")
        self._updating = False
        self.dimension_table.setMinimumHeight(self._dimension_table_height())

    def _insert_dimension_row(self, name: str, nominal: str, tolerance: str) -> None:
        row = self.dimension_table.rowCount()
        self.dimension_table.insertRow(row)
        self.dimension_table.setRowHeight(row, 49)
        self.dimension_table.setCellWidget(row, 0, self._dimension_text_edit(name))
        self.dimension_table.setCellWidget(
            row,
            1,
            self._dimension_number_edit(nominal, allow_negative=True),
        )
        self.dimension_table.setCellWidget(
            row,
            2,
            self._dimension_number_edit(tolerance, allow_negative=False),
        )
        remove_button = CircleXButton()
        remove_button.setToolTip("Remove dimension")
        remove_button.clicked.connect(lambda checked=False, button=remove_button: self._remove_row(button))
        remove_cell = QWidget()
        remove_cell.setObjectName("RemoveCell")
        remove_layout = QHBoxLayout(remove_cell)
        remove_layout.setContentsMargins(0, 0, 0, 0)
        remove_layout.addWidget(remove_button, 0, Qt.AlignmentFlag.AlignCenter)
        self.dimension_table.setCellWidget(row, 3, remove_cell)

    def _add_default_dimension(self) -> None:
        self._updating = True
        next_index = self.dimension_table.rowCount() + 1
        self._insert_dimension_row(f"#{next_index}", "1", "0.005")
        self._updating = False
        self.dimension_table.setMinimumHeight(self._dimension_table_height())
        self._recalculate()

    def _clear_dimensions(self) -> None:
        self._updating = True
        self.dimension_table.setRowCount(0)
        self._updating = False
        self.dimension_table.setMinimumHeight(self._dimension_table_height())
        self._recalculate()

    def _remove_row(self, button: QPushButton) -> None:
        for row in range(self.dimension_table.rowCount()):
            widget = self.dimension_table.cellWidget(row, 3)
            row_button = widget.findChild(QPushButton) if widget is not None else None
            if row_button is button:
                self._updating = True
                self.dimension_table.removeRow(row)
                self._updating = False
                self.dimension_table.setMinimumHeight(self._dimension_table_height())
                self._recalculate()
                return

    def _dimension_table_height(self) -> int:
        return max(92, 36 + self.dimension_table.rowCount() * 49)

    def _dimensions_from_table(self) -> list[ToleranceDimension]:
        dimensions: list[ToleranceDimension] = []
        for row in range(self.dimension_table.rowCount()):
            name = self._cell_text(row, 0)
            nominal_text = self._cell_text(row, 1)
            tolerance_text = self._cell_text(row, 2)
            if not any((name, nominal_text, tolerance_text)):
                continue
            if not nominal_text:
                raise ValueError(f"Row {row + 1} nominal dimension is required.")
            if not tolerance_text:
                raise ValueError(f"Row {row + 1} tolerance is required.")
            dimensions.append(
                ToleranceDimension(
                    name=name or f"#{row + 1}",
                    nominal=float(nominal_text),
                    tolerance=float(tolerance_text),
                )
            )
        return dimensions

    def _cell_text(self, row: int, column: int) -> str:
        widget = self.dimension_table.cellWidget(row, column)
        if isinstance(widget, QLineEdit):
            return widget.text().strip()
        item = self.dimension_table.item(row, column)
        return item.text().strip() if item is not None else ""

    def _recalculate(self) -> None:
        if self._updating:
            return
        try:
            analysis = calculate_stackup(
                self._dimensions_from_table(),
                float(self.target_min_edit.text()),
                float(self.target_max_edit.text()),
            )
        except (TypeError, ValueError) as exc:
            self.analysis = None
            self.plot.set_analysis(None)
            self.analysis_table.setRowCount(0)
            self._set_status(f"Input error: {exc}", error=True)
            return

        self.analysis = analysis
        self.plot.set_analysis(analysis)
        self._fill_analysis_table(analysis)
        self._set_status(
            f"{len(analysis.dimensions)} dimensions, nominal stackup {analysis.nominal:.4f}.",
            error=False,
        )

    def _fill_analysis_table(self, analysis: StackupAnalysis) -> None:
        self.analysis_table.setRowCount(len(analysis.dimensions) + 3)
        for row, dimension_result in enumerate(analysis.dimensions):
            dimension = dimension_result.dimension
            self._set_analysis_row(
                row,
                (
                    dimension.name,
                    f"{dimension.nominal:.4f}",
                    f"{PLUS_MINUS} {dimension.tolerance:.4f}",
                    f"{dimension_result.std_deviation:.4f}",
                    f"{dimension_result.variance:.8f}",
                ),
            )

        worst_row = len(analysis.dimensions)
        self._set_analysis_row(
            worst_row,
            (
                "Worst case stackup",
                f"{analysis.nominal:.4f}",
                f"{PLUS_MINUS} {analysis.worst_case_tolerance:.4f}",
                f"{analysis.worst_case_std_deviation:.4f}",
                f"{analysis.worst_case_variance:.8f}",
            ),
            background=WORST_LIGHT,
        )

        rss_row = worst_row + 1
        self._set_analysis_row(
            rss_row,
            (
                "RSS stackup",
                f"{analysis.nominal:.4f}",
                f"{PLUS_MINUS} {analysis.rss_tolerance:.4f}",
                f"{analysis.rss_std_deviation:.4f}",
                f"{analysis.rss_variance:.8f}",
            ),
            background=RSS_LIGHT,
        )

        failure_row = rss_row + 1
        self._set_analysis_row(
            failure_row,
            (
                "",
                f"{analysis.rss_left_tail_failure_rate * 100.0:.2f}% left tail failures",
                "",
                f"{analysis.rss_right_tail_failure_rate * 100.0:.2f}% right tail failures",
                "",
            ),
            background=RSS_LIGHT,
        )
        self.analysis_table.setSpan(failure_row, 1, 1, 2)
        self.analysis_table.setSpan(failure_row, 3, 1, 2)
        self.analysis_table.setMinimumHeight(38 + self.analysis_table.rowCount() * 27)

    def _set_analysis_row(
        self,
        row: int,
        values: tuple[str, str, str, str, str],
        background: QColor | None = None,
    ) -> None:
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if column == 0:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if background is not None:
                item.setBackground(background)
            self.analysis_table.setItem(row, column, item)

    def _set_status(self, text: str, error: bool) -> None:
        self.status_label.setText(text)
        color = "#d56159" if error else "#338ba1"
        self.status_label.setStyleSheet(f"color: {color}; font-size: 11px;")

    def _export_page(self) -> None:
        default_path = self._default_export_path()
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export tolerance analysis",
            str(default_path),
            "PDF document (*.pdf);;PNG image (*.png)",
        )
        if not path:
            return

        export_path = self._export_path_with_suffix(Path(path), selected_filter)
        try:
            if export_path.suffix.lower() == ".png":
                self._export_page_png(export_path)
            else:
                self._export_page_pdf(export_path)
        except Exception as exc:
            QMessageBox.warning(self, "Export failed", str(exc))
            self._set_status("Export failed.", error=True)
            return

        self._set_status(f"Exported {export_path.name}.", error=False)

    def _default_export_path(self) -> Path:
        documents = Path.home() / "Documents"
        base_dir = documents if documents.exists() else Path.home()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        title = self._safe_filename_stem(self._analysis_title())
        return base_dir / f"{title}_{stamp}.pdf"

    def _analysis_title(self) -> str:
        title = self.title_edit.text().strip()
        return title or "Tolerance Analysis"

    def _safe_filename_stem(self, text: str) -> str:
        safe_chars = []
        for char in text.strip().lower():
            if char.isalnum():
                safe_chars.append(char)
            elif char in {" ", "-", "_"}:
                safe_chars.append("_")
        stem = "".join(safe_chars).strip("_")
        while "__" in stem:
            stem = stem.replace("__", "_")
        return stem or "tolerance_analysis"

    def _export_path_with_suffix(self, path: Path, selected_filter: str) -> Path:
        suffix = path.suffix.lower()
        if suffix in {".pdf", ".png"}:
            return path
        if "png" in selected_filter.lower():
            return path.with_suffix(".png")
        return path.with_suffix(".pdf")

    def _export_page_png(self, path: Path) -> None:
        image = self._render_page_image(scale=3.0)
        if not image.save(str(path), "PNG"):
            raise RuntimeError(f"Could not write PNG file: {path}")

    def _export_page_pdf(self, path: Path) -> None:
        widget = self.export_content
        export_size = self._export_page_size()
        old_size = widget.size()
        self._prepare_export_widget(export_size)
        try:
            dpi = 300
            width_mm = export_size.width() / 96.0 * 25.4
            height_mm = export_size.height() / 96.0 * 25.4
            writer = QPdfWriter(str(path))
            writer.setResolution(dpi)
            writer.setPageSize(
                QPageSize(
                    QSizeF(width_mm, height_mm),
                    QPageSize.Unit.Millimeter,
                    "Tolerance Analysis",
                )
            )
            writer.setPageMargins(
                QMarginsF(0.0, 0.0, 0.0, 0.0),
                QPageLayout.Unit.Millimeter,
            )

            painter = QPainter(writer)
            try:
                page_rect = writer.pageLayout().paintRectPixels(dpi)
                painter.scale(
                    page_rect.width() / export_size.width(),
                    page_rect.height() / export_size.height(),
                )
                widget.render(painter)
            finally:
                painter.end()
        finally:
            self._restore_export_widget(old_size)

    def _render_page_image(self, scale: float) -> QImage:
        widget = self.export_content
        export_size = self._export_page_size()
        old_size = widget.size()
        self._prepare_export_widget(export_size)
        try:
            image_size = QSize(
                int(export_size.width() * scale),
                int(export_size.height() * scale),
            )
            image = QImage(image_size, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(QColor("#ffffff"))
            dots_per_meter = int(300 / 25.4 * 1000)
            image.setDotsPerMeterX(dots_per_meter)
            image.setDotsPerMeterY(dots_per_meter)

            painter = QPainter(image)
            try:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
                painter.scale(scale, scale)
                widget.render(painter)
            finally:
                painter.end()
            return image
        finally:
            self._restore_export_widget(old_size)

    def _export_page_size(self) -> QSize:
        widget = self.export_content
        hint = widget.sizeHint()
        current = widget.size()
        width = max(current.width(), hint.width(), widget.minimumWidth())
        height = max(current.height(), hint.height())
        return QSize(width, height)

    def _prepare_export_widget(self, size: QSize) -> None:
        self.export_content.resize(size)
        layout = self.export_content.layout()
        if layout is not None:
            layout.activate()
        QApplication.processEvents()

    def _restore_export_widget(self, old_size: QSize) -> None:
        self.export_content.resize(old_size)
        layout = self.export_content.layout()
        if layout is not None:
            layout.activate()
        QApplication.processEvents()


def _apply_tolerance_style(app: QApplication) -> None:
    fusion_style = QStyleFactory.create("Fusion")
    if fusion_style is not None:
        app.setStyle(fusion_style)
    else:
        app.setStyle("Fusion")

    font_families = set(QFontDatabase.families())
    for family in ("Montserrat", "Segoe UI", "Arial", "Tahoma"):
        if family in font_families:
            app.setFont(QFont(family, 9))
            break

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.WindowText, TEXT)
    palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#f3f3f3"))
    palette.setColor(QPalette.ColorRole.Text, TEXT)
    palette.setColor(QPalette.ColorRole.Button, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.ButtonText, TEXT)
    palette.setColor(QPalette.ColorRole.Highlight, PURPLE)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    app.setStyleSheet(
        """
        QMainWindow, QWidget#AppSurface {
            background: #ffffff;
            color: #303030;
        }
        QLabel {
            background: transparent;
        }
        QFrame#BreadcrumbBar {
            background: #f4f4f4;
            border-bottom: 1px solid #cccccc;
        }
        QLabel#BreadcrumbIcon {
            color: #303030;
            font-size: 16px;
            padding-left: 4px;
        }
        QLabel#BreadcrumbLabel {
            color: #303030;
            font-size: 11px;
            padding: 8px 0;
        }
        QLabel#SectionLabel {
            font-size: 12px;
            color: #303030;
            margin-top: 12px;
        }
        QLabel#SectionLabel span {
            color: #919191;
        }
        QFrame#Divider {
            color: #cfcfcf;
        }
        QTableWidget {
            background: #ffffff;
            alternate-background-color: #f2f2f2;
            border: 0;
            gridline-color: #e5e5e5;
            selection-background-color: #ece8ff;
            selection-color: #303030;
        }
        QHeaderView::section {
            background: #ffffff;
            border: 0;
            border-bottom: 1px solid #bdbdbd;
            color: #303030;
            font-weight: 700;
            padding: 5px 8px;
        }
        QTableWidget::item {
            padding: 4px 8px;
        }
        QPushButton {
            background: #ffffff;
            border: 1px solid #c7c7c7;
            border-radius: 3px;
            padding: 6px 12px;
            min-height: 22px;
        }
        QPushButton:hover {
            border-color: #281e78;
        }
        QPushButton:disabled {
            background: #c7c7c9;
            color: #ffffff;
            border-color: #c7c7c9;
        }
        QPushButton#PrimaryAction {
            background: #281e78;
            border-color: #20175f;
            color: #ffffff;
            font-weight: 500;
        }
        QPushButton#PrimaryAction:hover {
            background: #332596;
        }
        QLineEdit, QTableWidget QLineEdit {
            background: transparent;
            border: 0;
            padding: 4px 8px;
            color: #111111;
        }
        QLineEdit#PageTitleEdit {
            background: transparent;
            border: 1px solid transparent;
            border-radius: 4px;
            color: #202020;
            font-size: 20px;
            font-weight: 500;
            padding: 2px 6px;
            min-height: 34px;
        }
        QLineEdit#PageTitleEdit:hover {
            border-color: #d0d0d0;
        }
        QLineEdit#PageTitleEdit:focus {
            background: #ffffff;
            border: 2px solid #69dbe8;
            padding: 1px 5px;
        }
        QLineEdit#DimensionTextEdit, QLineEdit#DimensionNumberEdit {
            background: transparent;
            border: 1px solid transparent;
            border-radius: 5px;
            color: #111111;
            font-size: 13px;
            padding: 2px 10px;
        }
        QLineEdit#DimensionTextEdit:focus, QLineEdit#DimensionNumberEdit:focus {
            background: #ffffff;
            border: 2px solid #69dbe8;
            padding: 1px 9px;
        }
        QLineEdit#NumberEdit {
            background: #ffffff;
            border: 0;
            border-bottom: 1px solid #bdbdbd;
        }
        QLabel#InlineTableHeader {
            background: #ffffff;
            border-bottom: 1px solid #bdbdbd;
            color: #303030;
            font-weight: 700;
        }
        QFrame#FlatTableFrame {
            border: 0;
            background: #ffffff;
        }
        QLabel#StatusLine {
            color: #338ba1;
            font-size: 11px;
        }
        QLabel#StatusLine[error="true"] {
            color: #d56159;
        }
        QScrollArea {
            background: #ffffff;
            border: 0;
        }
        """
    )


def create_tolerance_window(app: QApplication | None = None) -> ToleranceAnalysisApp:
    app = app or QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    _apply_tolerance_style(app)
    window = ToleranceAnalysisApp()
    return window


def main() -> None:
    app = QApplication(sys.argv)
    app.setWindowIcon(app_icon("tolerance"))
    window = create_tolerance_window(app)
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
