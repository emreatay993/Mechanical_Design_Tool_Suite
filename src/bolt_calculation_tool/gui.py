"""Qt Fusion prototype GUI for the ExampleScenario bolt calculation tool."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QColor, QFont, QFontDatabase, QPalette
    from PyQt6.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QComboBox,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QMainWindow,
        QMessageBox,
        QPlainTextEdit,
        QPushButton,
        QSizePolicy,
        QSplitter,
        QStatusBar,
        QStyle,
        QStyleFactory,
        QTabWidget,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover - exercised only without GUI deps.
    raise RuntimeError(
        "The Qt GUI requires PyQt6. Install the package with "
        "`python -m pip install -e .` before launching the GUI."
    ) from exc

from .calculations import (
    MARGIN_BASIS_MINOR,
    SUPPORTED_MARGIN_BASES,
    BoltCalculationResult,
    available_bolt_sizes,
    calculate_bolt_group,
    resolve_constants,
)
from .io import ParsedTable, parse_load_table
from .sample_data import example_scenario_table_text
from .visualization import SCALAR_CHOICES, open_pyvista_plot, results_have_coordinates


CRITERIA_LABEL = "ExampleScenario / INCO718 BAR / 250 C"


class BoltCalculationApp(QMainWindow):
    """Main window for the prototype desktop application."""

    def __init__(self) -> None:
        super().__init__()
        self.results: list[BoltCalculationResult] = []
        self.parsed_table: ParsedTable | None = None
        self._suppress_input_dirty = False

        self.setWindowTitle("Bolt Calculation Tool Prototype")
        self.resize(1360, 840)
        self.setMinimumSize(1060, 680)

        self._build_layout()
        self._load_example()

    def _build_layout(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 14, 14, 10)
        root.setSpacing(10)

        top_bar = QFrame()
        top_bar.setObjectName("TopBar")
        top_layout = QGridLayout(top_bar)
        top_layout.setContentsMargins(14, 12, 14, 12)
        top_layout.setHorizontalSpacing(10)
        top_layout.setVerticalSpacing(8)

        title = QLabel("Bolt Calculation Tool")
        title.setObjectName("AppTitle")
        subtitle = QLabel("ExampleScenario strength, fatigue, crush, and interaction checks")
        subtitle.setObjectName("Subtitle")
        top_layout.addWidget(title, 0, 0, 1, 4)
        top_layout.addWidget(subtitle, 1, 0, 1, 4)

        self.bolt_size_combo = self._combo(available_bolt_sizes())
        self.bolt_size_combo.setCurrentText(available_bolt_sizes()[0])
        self.margin_basis_combo = self._combo(list(SUPPORTED_MARGIN_BASES))
        self.margin_basis_combo.setCurrentText(MARGIN_BASIS_MINOR)
        self.criteria_value = self._readonly_value(CRITERIA_LABEL)
        self.coordinate_value = self._readonly_value("Local bolt coordinates")

        top_layout.addWidget(self._control("Bolt size", self.bolt_size_combo), 2, 0)
        top_layout.addWidget(self._control("Margin basis", self.margin_basis_combo), 2, 1)
        top_layout.addWidget(self._control("Criteria", self.criteria_value), 2, 2)
        top_layout.addWidget(self._control("Coordinate basis", self.coordinate_value), 2, 3)
        top_layout.setColumnStretch(2, 1)

        button_row = QHBoxLayout()
        button_row.setSpacing(6)
        button_row.addWidget(
            self._button(
                "Load Example",
                QStyle.StandardPixmap.SP_FileDialogDetailedView,
                self._load_example,
            )
        )
        button_row.addWidget(
            self._button("Paste", QStyle.StandardPixmap.SP_FileDialogContentsView, self._paste_clipboard)
        )
        button_row.addWidget(
            self._button("Import", QStyle.StandardPixmap.SP_DialogOpenButton, self._import_table)
        )
        self.calculate_button = self._button(
            "Calculate",
            QStyle.StandardPixmap.SP_DialogApplyButton,
            self._calculate,
        )
        self.calculate_button.setObjectName("PrimaryButton")
        button_row.addWidget(
            self.calculate_button
        )
        self.export_button = self._button(
            "Export",
            QStyle.StandardPixmap.SP_DialogSaveButton,
            self._export_results,
        )
        button_row.addWidget(self.export_button)
        button_row.addStretch(1)

        self.scalar_combo = self._combo(list(SCALAR_CHOICES))
        self.scalar_combo.setCurrentText("Margin")
        button_row.addWidget(QLabel("Contour"))
        button_row.addWidget(self.scalar_combo)
        self.visualize_button = self._button(
            "Visualize",
            QStyle.StandardPixmap.SP_DesktopIcon,
            self._visualize,
        )
        button_row.addWidget(self.visualize_button)
        top_layout.addLayout(button_row, 3, 0, 1, 4)
        root.addWidget(top_bar)

        summary = QFrame()
        summary.setObjectName("SummaryBand")
        summary_layout = QHBoxLayout(summary)
        summary_layout.setContentsMargins(12, 8, 12, 8)
        summary_layout.setSpacing(16)
        self.status_label = QLabel("Load the example table or paste your own load table.")
        self.status_label.setObjectName("StatusLabel")
        self.rows_label = QLabel("Rows: -")
        self.fail_label = QLabel("Failures: -")
        self.governing_label = QLabel("Governing: -")
        self.visualization_label = QLabel("Visualization: -")
        for label in (
            self.rows_label,
            self.fail_label,
            self.governing_label,
            self.visualization_label,
        ):
            label.setObjectName("SummaryMetric")
        summary_layout.addWidget(self.status_label, 1)
        summary_layout.addWidget(self.rows_label)
        summary_layout.addWidget(self.fail_label)
        summary_layout.addWidget(self.governing_label)
        summary_layout.addWidget(self.visualization_label)
        root.addWidget(summary)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter, 1)

        self.input_tabs = QTabWidget()
        self.input_tabs.setDocumentMode(True)
        self.input_text = QPlainTextEdit()
        self.input_text.setPlaceholderText(
            "NodeID\tX[mm]\tY[mm]\tZ[mm]\tFX[N]\tFY[N]\tFZ[N]\t"
            "MX[N*mm]\tMY[N*mm]\tMZ[N*mm]"
        )
        self.input_text.setFont(QFont("Consolas", 10))
        self.input_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.input_tabs.addTab(self.input_text, "Input Table")

        self.preview_table = self._table(
            ("Bolt", "X", "Y", "Z", "FX", "FY", "FZ", "MX", "MY", "MZ")
        )
        self.input_tabs.addTab(self.preview_table, "Parsed Loads")

        self.output_tabs = QTabWidget()
        self.output_tabs.setDocumentMode(True)
        self.results_table = self._table(
            (
                "Bolt",
                "Tensile",
                "Fiber",
                "LCF alt",
                "Life",
                "Crush Bolt",
                "Crush Nut",
                "PLUG",
                "SHEAR",
                "BENDING",
                "Torsion",
                "Rt",
                "Rb",
                "Rs",
                "Rst",
                "Margin",
                "Status",
                "Governing",
            )
        )
        self.output_tabs.addTab(self.results_table, "Results")

        self.trace_text = QPlainTextEdit()
        self.trace_text.setReadOnly(True)
        self.trace_text.setFont(QFont("Consolas", 10))
        self.output_tabs.addTab(self.trace_text, "Trace")

        splitter.addWidget(self.input_tabs)
        splitter.addWidget(self.output_tabs)
        splitter.setSizes([300, 470])

        status_bar = QStatusBar()
        status_bar.showMessage("Qt Fusion light style active")
        self.setStatusBar(status_bar)

        self.input_text.textChanged.connect(self._mark_input_dirty)
        self.bolt_size_combo.currentTextChanged.connect(self._mark_input_dirty)
        self.margin_basis_combo.currentTextChanged.connect(self._mark_input_dirty)
        self.results_table.itemSelectionChanged.connect(self._on_result_selection_changed)
        self._set_result_actions_enabled(False)

    def _combo(self, values: list[str]) -> QComboBox:
        combo = QComboBox()
        combo.addItems(values)
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        combo.setMinimumHeight(30)
        return combo

    def _readonly_value(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("ReadOnlyValue")
        label.setMinimumHeight(30)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return label

    def _control(self, label: str, widget: QWidget) -> QFrame:
        frame = QFrame()
        frame.setObjectName("ControlBlock")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        control_label = QLabel(label)
        control_label.setObjectName("ControlLabel")
        layout.addWidget(control_label)
        layout.addWidget(widget)
        return frame

    def _button(
        self,
        text: str,
        icon_id: QStyle.StandardPixmap,
        callback,
    ) -> QPushButton:
        button = QPushButton(text)
        button.setIcon(self.style().standardIcon(icon_id))
        button.setMinimumHeight(32)
        button.clicked.connect(callback)
        return button

    def _table(self, headers: tuple[str, ...]) -> QTableWidget:
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setShowGrid(True)
        table.setSortingEnabled(False)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(24)
        table.horizontalHeader().setStretchLastSection(False)
        table.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        widths = {
            "Bolt": 100,
            "Life": 86,
            "Status": 78,
            "Governing": 150,
            "Margin": 86,
        }
        for index, header in enumerate(headers):
            table.setColumnWidth(index, widths.get(header, 94))
            table.horizontalHeader().setSectionResizeMode(
                index,
                QHeaderView.ResizeMode.Interactive,
            )
        return table

    def _load_example(self) -> None:
        self._replace_input(example_scenario_table_text())
        self._calculate()

    def _paste_clipboard(self) -> None:
        text = QApplication.clipboard().text()
        if not text.strip():
            QMessageBox.warning(self, "Paste failed", "The clipboard does not contain text.")
            return
        self._replace_input(text)
        self._set_status("Clipboard table pasted.")

    def _import_table(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import load table",
            "",
            "Delimited tables (*.csv *.tsv *.txt);;CSV files (*.csv);;TSV files (*.tsv);;Text files (*.txt);;All files (*.*)",
        )
        if not path:
            return
        table_text = Path(path).read_text(encoding="utf-8-sig")
        self._replace_input(table_text)
        self._set_status(f"Imported {Path(path).name}.")

    def _replace_input(self, text: str) -> None:
        self._suppress_input_dirty = True
        self.input_text.setPlainText(text)
        self._suppress_input_dirty = False
        self._clear_outputs()

    def _mark_input_dirty(self) -> None:
        if self._suppress_input_dirty:
            return
        self._clear_outputs()
        self._set_status("Input changed.")

    def _clear_outputs(self) -> None:
        self.results = []
        self.parsed_table = None
        self.preview_table.setRowCount(0)
        self.results_table.setRowCount(0)
        self.trace_text.setPlainText("")
        self.rows_label.setText("Rows: -")
        self.fail_label.setText("Failures: -")
        self.governing_label.setText("Governing: -")
        self.visualization_label.setText("Visualization: -")
        self._set_result_actions_enabled(False)

    def _calculate(self) -> None:
        try:
            parsed = parse_load_table(self.input_text.toPlainText())
            constants = resolve_constants(
                self.bolt_size_combo.currentText(),
                self.margin_basis_combo.currentText(),
            )
            results = calculate_bolt_group(parsed.loads, constants)
        except Exception as exc:
            QMessageBox.critical(self, "Calculation failed", str(exc))
            self._set_status("Calculation failed. Fix the input table and retry.")
            return

        self.parsed_table = parsed
        self.results = results
        self._fill_preview(parsed)
        self._fill_results(results)
        self._fill_trace(parsed, results)
        self._update_summary(results)
        self._set_result_actions_enabled(True)
        self.input_tabs.setCurrentIndex(1)
        self.output_tabs.setCurrentIndex(0)
        self._select_governing_row()

    def _fill_preview(self, parsed: ParsedTable) -> None:
        self.preview_table.setRowCount(len(parsed.loads))
        for row, load in enumerate(parsed.loads):
            values = (
                load.name,
                self._fmt_optional(load.x_mm, 3),
                self._fmt_optional(load.y_mm, 3),
                self._fmt_optional(load.z_mm, 3),
                self._fmt(load.fx_n, 2),
                self._fmt(load.fy_n, 2),
                self._fmt(load.fz_n, 2),
                self._fmt(load.mx_nmm, 2),
                self._fmt(load.my_nmm, 2),
                self._fmt(load.mz_nmm, 2),
            )
            self._set_row(self.preview_table, row, values)
        self._resize_table(self.preview_table)

    def _fill_results(self, results: list[BoltCalculationResult]) -> None:
        self.results_table.setRowCount(len(results))
        governing_row = self._governing_row_index(results)
        for row, result in enumerate(results):
            strength = result.strength
            interaction = result.interaction
            values = (
                result.load.name,
                self._fmt(strength.tensile_mpa, 1),
                self._fmt(strength.fiber_mpa, 1),
                self._fmt(strength.lcf_alt_mpa, 1),
                strength.life,
                self._fmt(strength.crush_bolt_mpa, 1),
                self._fmt(strength.crush_nut_mpa, 1),
                self._fmt(interaction.plug_n, 1),
                self._fmt(interaction.shear_n, 1),
                self._fmt(interaction.bending_nmm, 1),
                self._fmt(interaction.torsion_nmm, 1),
                self._fmt(interaction.rt, 3),
                self._fmt(interaction.rb, 3),
                self._fmt(interaction.rs, 3),
                self._fmt(interaction.rst, 3),
                self._fmt_margin(interaction.margin),
                result.status,
                result.governing_check,
            )
            self._set_row(
                self.results_table,
                row,
                values,
                result.status,
                is_governing=row == governing_row,
                tooltip=self._result_tooltip(result),
            )
        self._resize_table(self.results_table)

    def _set_row(
        self,
        table: QTableWidget,
        row: int,
        values: tuple[str, ...],
        status: str | None = None,
        is_governing: bool = False,
        tooltip: str | None = None,
    ) -> None:
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if tooltip:
                item.setToolTip(tooltip)
            if column == 0:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if status == "FAIL":
                item.setBackground(QColor("#fdeaea"))
                item.setForeground(QColor("#8b1f1f"))
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            elif is_governing:
                item.setBackground(QColor("#eef6fb"))
            elif status == "PASS" and column == len(values) - 2:
                item.setForeground(QColor("#1f6b43"))
            if is_governing and column in (0, len(values) - 3, len(values) - 2, len(values) - 1):
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            table.setItem(row, column, item)

    def _fill_trace(
        self,
        parsed: ParsedTable,
        results: list[BoltCalculationResult],
        selected_index: int | None = None,
    ) -> None:
        constants = resolve_constants(
            self.bolt_size_combo.currentText(),
            self.margin_basis_combo.currentText(),
        )
        notes = "\n".join(f"- {note}" for note in parsed.notes) or "- none"
        field_map = "\n".join(
            f"- {field}: {header}" for field, header in sorted(parsed.field_headers.items())
        )
        selected_text = "Selected bolt: none"
        if selected_index is not None and 0 <= selected_index < len(results):
            selected_text = self._selected_trace(results[selected_index])

        text = f"""{selected_text}

Design path: {CRITERIA_LABEL}
Coordinate system: {self.coordinate_value.text()}
GUI style: Qt Fusion light engineering

Resolved constants:
- bolt_size: {constants.bolt_size}
- margin_basis: {constants.margin_basis}
- bolt_thread_area_mm2: {constants.bolt_thread_area_mm2:.10f}
- bolt_radius_mm: {constants.bolt_radius_mm:.10f}
- moment_of_inertia_mm4: {constants.moment_of_inertia_mm4:.10f}
- polar_moment_of_inertia_mm4: {constants.polar_moment_of_inertia_mm4:.10f}
- bolt_contact_crush_area_mm2: {constants.bolt_contact_crush_area_mm2:.10f}
- nut_contact_crush_area_min_mm2: {constants.nut_contact_crush_area_min_mm2:.10f}
- assembly_tensile_stress_mpa: {constants.assembly_tensile_stress_mpa:.10f}
- walker_coefficient: {constants.walker_coefficient:.10f}
- yield_002_mpa: {constants.yield_002_mpa:.10f}
- shear_strength_mpa: {constants.shear_strength_mpa:.10f}

Imported rows: {len(parsed.loads)}
Rows with coordinates: {"yes" if results_have_coordinates(results) else "no"}

Header map:
{field_map}

Parser notes:
{notes}

Implementation note:
This prototype uses the documented ExampleScenario reference behavior in N,
N*mm, mm, mm^2, mm^4, and MPa. Other bolt sizes are listed in the source lookup
formulas, but complete prototype constants are currently documented for .2500-28.
"""
        self.trace_text.setPlainText(text)

    def _update_summary(self, results: list[BoltCalculationResult]) -> None:
        fail_count = sum(1 for result in results if result.status == "FAIL")
        finite_results = [
            result
            for result in results
            if result.interaction.margin != float("inf")
        ]
        governing = min(
            finite_results,
            key=lambda result: result.interaction.margin,
            default=None,
        )
        if governing is None:
            governing_text = "all margins infinite"
        else:
            governing_text = (
                f"{governing.load.name} {governing.interaction.margin * 100.0:.0f}%"
            )

        self.rows_label.setText(f"Rows: {len(results)}")
        self.fail_label.setText(f"Failures: {fail_count}")
        self.governing_label.setText(f"Governing: {governing_text}")
        visualization_text = (
            "Visualization: ready"
            if results_have_coordinates(results)
            else "Visualization: no coordinates"
        )
        self.visualization_label.setText(visualization_text)
        self._set_status(f"{len(results)} bolts calculated with {fail_count} failures.")

    def _set_result_actions_enabled(self, has_results: bool) -> None:
        self.export_button.setEnabled(has_results)
        self.visualize_button.setEnabled(
            has_results and results_have_coordinates(self.results)
        )

    def _set_status(self, text: str) -> None:
        self.status_label.setText(text)
        self.statusBar().showMessage(text)

    def _visualize(self) -> None:
        try:
            open_pyvista_plot(self.results, self.scalar_combo.currentText())
        except Exception as exc:
            QMessageBox.warning(self, "Visualization unavailable", str(exc))

    def _on_result_selection_changed(self) -> None:
        if self.parsed_table is None or not self.results:
            return
        selected = self.results_table.selectedIndexes()
        if not selected:
            return
        row = selected[0].row()
        self._fill_trace(self.parsed_table, self.results, selected_index=row)

    def _select_governing_row(self) -> None:
        if not self.results:
            return
        row = self._governing_row_index(self.results)
        if row is None:
            row = 0
        self.results_table.selectRow(row)
        self.results_table.scrollToItem(self.results_table.item(row, 0))
        if self.parsed_table is not None:
            self._fill_trace(self.parsed_table, self.results, selected_index=row)

    def _governing_row_index(
        self,
        results: list[BoltCalculationResult],
    ) -> int | None:
        if not results:
            return None
        for index, result in enumerate(results):
            if result.status == "FAIL":
                return index
        finite_indexes = [
            index
            for index, result in enumerate(results)
            if result.interaction.margin != float("inf")
        ]
        if not finite_indexes:
            return 0
        return min(
            finite_indexes,
            key=lambda index: results[index].interaction.margin,
        )

    def _resize_table(self, table: QTableWidget) -> None:
        table.resizeColumnsToContents()
        minimums = {
            "Bolt": 100,
            "Life": 86,
            "Status": 78,
            "Governing": 150,
            "Margin": 86,
        }
        for column in range(table.columnCount()):
            header = table.horizontalHeaderItem(column).text()
            table.setColumnWidth(
                column,
                max(table.columnWidth(column) + 10, minimums.get(header, 92)),
            )

    def _result_tooltip(self, result: BoltCalculationResult) -> str:
        return (
            f"{result.load.name}\n"
            f"Margin: {self._fmt_margin(result.interaction.margin)}\n"
            f"Fiber stress: {result.strength.fiber_mpa:.1f} MPa\n"
            f"LCF sigma_alt: {result.strength.lcf_alt_mpa:.1f} MPa\n"
            f"Life: {result.strength.life}"
        )

    def _selected_trace(self, result: BoltCalculationResult) -> str:
        load = result.load
        strength = result.strength
        interaction = result.interaction
        return f"""Selected bolt: {load.name}
Status: {result.status}
Governing check: {result.governing_check}

Loads:
- FX/FY/FZ N: {load.fx_n:.3f}, {load.fy_n:.3f}, {load.fz_n:.3f}
- MX/MY/MZ N*mm: {load.mx_nmm:.3f}, {load.my_nmm:.3f}, {load.mz_nmm:.3f}
- X/Y/Z mm: {self._fmt_optional(load.x_mm, 3)}, {self._fmt_optional(load.y_mm, 3)}, {self._fmt_optional(load.z_mm, 3)}

Strength:
- tensile_mpa: {strength.tensile_mpa:.6f}
- bending_moment_nmm: {strength.bending_moment_nmm:.6f}
- bending_stress_mpa: {strength.bending_stress_mpa:.6f}
- fiber_mpa: {strength.fiber_mpa:.6f}
- lcf_alt_mpa: {strength.lcf_alt_mpa:.6f}
- life: {strength.life}
- crush_bolt_mpa: {strength.crush_bolt_mpa:.6f}
- crush_nut_mpa: {strength.crush_nut_mpa:.6f}

Interaction:
- plug_n: {interaction.plug_n:.6f}
- shear_n: {interaction.shear_n:.6f}
- bending_nmm: {interaction.bending_nmm:.6f}
- torsion_nmm: {interaction.torsion_nmm:.6f}
- Rt/Rb/Rs/Rst: {interaction.rt:.6f}, {interaction.rb:.6f}, {interaction.rs:.6f}, {interaction.rst:.6f}
- interaction_ratio: {interaction.interaction_ratio:.6f}
- margin: {interaction.margin:.6f} ({self._fmt_margin(interaction.margin)})
"""

    def _export_results(self) -> None:
        if not self.results:
            QMessageBox.information(self, "No results", "Calculate results before exporting.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export results",
            "",
            "CSV files (*.csv);;All files (*.*)",
        )
        if not path:
            return
        export_path = Path(path)
        if export_path.suffix == "":
            export_path = export_path.with_suffix(".csv")
        with export_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "Bolt",
                    "Tensile Stress MPa",
                    "Fiber Stress MPa",
                    "LCF sigma_alt MPa",
                    "Life",
                    "Flange Crush Stress Bolt MPa",
                    "Flange Crush Stress Nut MPa",
                    "PLUG N",
                    "SHEAR N",
                    "BENDING N*mm",
                    "Torsion N*mm",
                    "Rt",
                    "Rb",
                    "Rs",
                    "Rst",
                    "Margin",
                    "Status",
                    "Governing",
                ]
            )
            for result in self.results:
                strength = result.strength
                interaction = result.interaction
                writer.writerow(
                    [
                        result.load.name,
                        strength.tensile_mpa,
                        strength.fiber_mpa,
                        strength.lcf_alt_mpa,
                        strength.life,
                        strength.crush_bolt_mpa,
                        strength.crush_nut_mpa,
                        interaction.plug_n,
                        interaction.shear_n,
                        interaction.bending_nmm,
                        interaction.torsion_nmm,
                        interaction.rt,
                        interaction.rb,
                        interaction.rs,
                        interaction.rst,
                        interaction.margin,
                        result.status,
                        result.governing_check,
                    ]
                )
        self._set_status(f"Exported results to {export_path.name}.")

    def _fmt(self, value: float, decimals: int) -> str:
        return f"{value:.{decimals}f}"

    def _fmt_optional(self, value: float | None, decimals: int) -> str:
        if value is None:
            return ""
        return self._fmt(value, decimals)

    def _fmt_margin(self, margin: float) -> str:
        if margin == float("inf"):
            return "inf"
        return f"{margin * 100.0:.0f}%"


def _apply_fusion_light_style(app: QApplication) -> None:
    fusion_style = QStyleFactory.create("Fusion")
    if fusion_style is not None:
        app.setStyle(fusion_style)
    else:
        app.setStyle("Fusion")
    app.setProperty("boltToolVisualStyle", "Qt Fusion Light Engineering")
    font_families = set(QFontDatabase.families())
    for family in ("Segoe UI", "Arial", "Calibri", "Tahoma"):
        if family in font_families:
            app.setFont(QFont(family, 10))
            break

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#f4f6f8"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#1f2933"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#f7f9fb"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#1f2933"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#1f2933"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#eef2f5"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#1f2933"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#2f6f9f"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    app.setStyleSheet(
        """
        QMainWindow, QWidget {
            background: #f4f6f8;
            color: #1f2933;
        }
        QLabel {
            background: transparent;
        }
        QFrame#TopBar {
            background: #edf3f7;
            border: 1px solid #d2dbe5;
            border-radius: 6px;
        }
        QLabel#AppTitle {
            color: #162330;
            font-size: 18px;
            font-weight: 700;
        }
        QLabel#Subtitle {
            color: #52616f;
            font-size: 11px;
        }
        QLabel#ControlLabel {
            color: #52616f;
            font-size: 10px;
            font-weight: 700;
        }
        QFrame#SummaryBand {
            background: #ffffff;
            border: 1px solid #d2dbe5;
            border-left: 4px solid #2f6f9f;
            border-radius: 4px;
        }
        QLabel#StatusLabel {
            color: #16324f;
            font-weight: 700;
        }
        QLabel#SummaryMetric {
            color: #2d3c4a;
            background: #f5f8fb;
            border: 1px solid #d7e0e8;
            border-radius: 4px;
            padding: 5px 8px;
            font-weight: 600;
        }
        QLabel#ReadOnlyValue {
            background: #f8fafc;
            border: 1px solid #cbd5df;
            border-radius: 4px;
            padding: 5px 8px;
            color: #263442;
        }
        QComboBox, QPushButton {
            background: #ffffff;
            border: 1px solid #b8c4cf;
            border-radius: 4px;
            padding: 5px 8px;
            min-height: 22px;
        }
        QPushButton {
            font-weight: 600;
        }
        QPushButton:disabled {
            background: #edf1f5;
            border-color: #d2dbe5;
            color: #8c9aa7;
        }
        QComboBox:hover, QPushButton:hover {
            border-color: #2f6f9f;
            background: #f8fbfd;
        }
        QPushButton:pressed {
            background: #e3edf5;
        }
        QPushButton#PrimaryButton {
            background: #2f6f9f;
            border-color: #285d86;
            color: #ffffff;
        }
        QPushButton#PrimaryButton:hover {
            background: #367eaf;
            border-color: #285d86;
            color: #ffffff;
        }
        QPushButton#PrimaryButton:pressed {
            background: #285d86;
            color: #ffffff;
        }
        QTabWidget::pane {
            background: #ffffff;
            border: 1px solid #d2dbe5;
            top: -1px;
        }
        QTabBar::tab {
            background: #e7edf3;
            border: 1px solid #cbd5df;
            padding: 7px 12px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected {
            background: #ffffff;
            border-bottom-color: #ffffff;
            color: #16324f;
            font-weight: 700;
        }
        QPlainTextEdit {
            background: #ffffff;
            border: 1px solid #cbd5df;
            border-radius: 4px;
            selection-background-color: #cfe4f4;
            selection-color: #162330;
        }
        QTableWidget {
            background: #ffffff;
            alternate-background-color: #f7f9fb;
            border: 1px solid #cbd5df;
            gridline-color: #d8e0e8;
            selection-background-color: #d8eaf7;
            selection-color: #14212b;
        }
        QHeaderView::section {
            background: #e7edf3;
            border: 0;
            border-right: 1px solid #cbd5df;
            border-bottom: 1px solid #cbd5df;
            color: #263442;
            font-weight: 700;
            padding: 6px;
        }
        QSplitter::handle {
            background: #dce3ea;
        }
        QStatusBar {
            background: #eef2f5;
            border-top: 1px solid #d2dbe5;
            color: #52616f;
        }
        """
    )


def create_bolt_window(app: QApplication | None = None) -> BoltCalculationApp:
    app = app or QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    _apply_fusion_light_style(app)
    window = BoltCalculationApp()
    return window


def main() -> None:
    app = QApplication(sys.argv)
    window = create_bolt_window(app)
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
