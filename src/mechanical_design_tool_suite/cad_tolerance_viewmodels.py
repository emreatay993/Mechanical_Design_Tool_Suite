"""Qt view models for the CAD 1D tolerance desktop shell."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QIcon, QPainter, QPen, QPixmap, QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QApplication, QStyle

from .cad_tolerance_methods import calculate_stackup
from .cad_tolerance_report import (
    ResultDisplayProjection,
    build_contribution_projection,
    build_dashboard_projection,
    build_result_display,
)
from .cad_stackup_workflow import GUIDED_STACKUP_STEP_LABELS
from .cad_tolerance_models import (
    AnalysisMode,
    AssemblyNode,
    AssemblyNodeType,
    CadDocument,
    CadToleranceProject,
    FeatureReference,
    NonOneDWarning,
    ObjectiveType,
    QualityMetric,
    ResultStatus,
    StackupContributor,
    StackupObjective,
    StackupRequirement,
    ToleranceType,
    geometric_tolerance_frame_text,
)


SUMMARY_COLUMNS = (
    "OK",
    "Name",
    "Nominal",
    "Objective",
    "Target Quality",
    "Results",
    "Predicted Quality",
    "#Dims",
)

DETAIL_COLUMNS = ("Name", "Sens", "Nominal", "Tolerance", "Datum")
DETAIL_TOLERANCE_TYPE_ROLE = int(Qt.ItemDataRole.UserRole) + 1
DETAIL_CONTRIBUTOR_ID_ROLE = int(Qt.ItemDataRole.UserRole) + 2
ASSEMBLY_VISIBILITY_ROLE = int(Qt.ItemDataRole.UserRole) + 3

GUIDED_STACKUP_STEPS = GUIDED_STACKUP_STEP_LABELS

NON_1D_WARNING_TEXT = "Calculated results are ignoring potentially significant 3D effects"

FIDELITY_GAP_NOTES = (
    "Readable GD&T rows use standard Unicode symbols with text labels; material-condition modifiers remain unresolved in the source frames.",
    "Tolerance-type dropdown labels are represented as Symmetric, Limits, and Geometric until higher-resolution crops confirm exact wording.",
    "Statistical submenu labels beyond Worst Case, RSS, and Statistical are unresolved in the targeted visual review.",
)

SUMMARY_FRAME_REFERENCES = (
    "005_00-04-10_main_workspace_after_import.jpg",
    "024_00-11-20_summary_badges_state.jpg",
    "042_00-20-24_dashboard_columns_visible.jpg",
)

DETAIL_FRAME_REFERENCES = (
    "014_00-07-05_generated_stackup_detail_table.jpg",
    "045_00-21-34_shared_dimension_markers.jpg",
    "046_00-21-54_contributions_tab.jpg",
)


@dataclass(frozen=True)
class StackupSummaryRow:
    stackup_id: str
    status: ResultStatus
    name: str
    nominal: str
    objective: str
    target_quality: str
    results: str
    predicted_quality: str
    dimension_count: int
    has_warning: bool = False


@dataclass(frozen=True)
class StackupDetailRow:
    name: str
    sensitivity: str = ""
    nominal: str = ""
    tolerance: str = ""
    datum: str = ""
    row_type: str = "dimension"
    status: ResultStatus | None = None
    shared_with: tuple[str, ...] = ()
    warning: bool = False
    contributor_id: str = ""
    source_feature_id: str = ""
    generated: bool = False
    source_note: str = ""
    tolerance_type: str = ""
    geometric_control: str = ""


@dataclass(frozen=True)
class DetailEditResult:
    accepted: bool
    message: str = ""
    rows: list[StackupDetailRow] | None = None


DetailEditHandler = Callable[[StackupDetailRow, int, str], DetailEditResult]


@dataclass(frozen=True)
class ContributionBarRow:
    label: str
    percent: float
    tolerance_box: str = ""
    datum: str = ""
    contributor_id: str = ""


@dataclass(frozen=True)
class DashboardBadges:
    objectives_met: int = 0
    objectives_not_met: int = 0
    sigma_rollup: str = ""


@dataclass
class CadToleranceWorkspaceViewModel:
    project_title: str = "caster.iam"
    assembly_roots: list[AssemblyNode] = field(default_factory=list)
    summary_rows: list[StackupSummaryRow] = field(default_factory=list)
    detail_rows_by_stackup_id: dict[str, list[StackupDetailRow]] = field(default_factory=dict)
    contribution_rows_by_stackup_id: dict[str, list[ContributionBarRow]] = field(default_factory=dict)
    result_projections_by_stackup_id: dict[str, ResultDisplayProjection] = field(default_factory=dict)
    warnings_by_stackup_id: dict[str, list[NonOneDWarning]] = field(default_factory=dict)
    annotation_positions_by_stackup_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    dashboard_badges: DashboardBadges = field(default_factory=DashboardBadges)
    selected_stackup_id: str = ""
    fidelity_gap_notes: tuple[str, ...] = FIDELITY_GAP_NOTES

    @classmethod
    def demo(cls) -> "CadToleranceWorkspaceViewModel":
        summary_rows = [
            StackupSummaryRow("flush_left", ResultStatus.FAIL, "flush left", "0.00", "+/-0.50", "RSS", "+/-0.56", "Cpk = 0.89", 6),
            StackupSummaryRow("flush_right", ResultStatus.FAIL, "flush right", "0.00", "+/-0.50", "RSS", "+/-0.62", "Cpk = 0.80", 9),
            StackupSummaryRow("overall_height", ResultStatus.PASS, "overall height", "(110.00)", "<= 110.50", "Cpk = 1.10", "<= 110.37", "Cpk = 1.48", 9),
            StackupSummaryRow("clearance_above_wheel", ResultStatus.PASS, "clearance above wheel", "(14.000)", ">= 0.000", "Yield = 99.90%", ">= 13.426", "Yield = 100%", 14),
            StackupSummaryRow("axial_clearance", ResultStatus.PASS, "axial clearance around wheel", "(1.000)", ">= 0.000", "Sigma = 4.50", ">= 0.032", "Sigma = 7.00", 13),
            StackupSummaryRow("width_at_bushings", ResultStatus.PASS, "width at bushings", "(80.0)", "<= 81.0", "Cpk = 1.00", "<= 80.9", "Cpk = 1.10", 13),
            StackupSummaryRow("thread_engagement", ResultStatus.PASS, "thread engagement", "(10.00)", ">= 9.80", "Worst Case", ">= 9.80", "", 2),
            StackupSummaryRow("thread_beneath_top", ResultStatus.PASS, "thread beneath top surface", "(2.000)", ">= 0.000", "Worst Case", ">= 1.700", "", 3),
            StackupSummaryRow("width_top_supports", ResultStatus.PASS, "width at top of supports", "130.000", "+/-1.560", "Cpk = 1.50", "+/-1.352", "Cpk = 1.73", 11, has_warning=True),
        ]
        detail_rows = [
            StackupDetailRow("A", "0", "(dia 22.00)", "+/-0.05", "", "feature"),
            StackupDetailRow("coaxiality of ID to A", "+1", "0.0", "dia 0.1", "A", "dimension", shared_with=("overall height", "clearance above wheel")),
            StackupDetailRow("ID", "0", "(dia 12.00)", "+/-0.05", "", "feature"),
            StackupDetailRow("Axle", "", "", "", "", "part"),
            StackupDetailRow("A", "0", "(dia 12.00)", "+/-0.05", "", "feature"),
            StackupDetailRow("coaxiality of OD to A", "+1", "0.0", "dia 0.2", "A", "dimension", shared_with=("overall height", "clearance above wheel")),
            StackupDetailRow("OD", "+1/2", "(dia 16.00)", "15.90 / 16.15", "", "dimension", shared_with=("overall height",)),
            StackupDetailRow("Asm shift OD-A", "+1", "0", "+/-0.08", "", "dimension", status=ResultStatus.PASS),
            StackupDetailRow("Wheel", "", "", "", "", "part"),
            StackupDetailRow("overall height", "", "(110.00)", "<= 110.37", "", "result", status=ResultStatus.PASS),
            StackupDetailRow("Objectives", "", "", "<= 110.50", "", "objective", status=ResultStatus.PASS),
        ]
        contributions = [
            ContributionBarRow("top_plate | bottom face for support arm", 54.9, "profile 0.5", "A"),
            ContributionBarRow("Asm shift OD-A", 14.8),
            ContributionBarRow("axle | OD", 8.8, "dia 0.2", "A"),
            ContributionBarRow("axle_support | hole for bushing", 8.8, "position 0.2", "A"),
            ContributionBarRow("wheel | OD", 8.8, "runout 0.2", "A"),
            ContributionBarRow("bushing | ID", 2.2, "runout 0.1", "A"),
            ContributionBarRow("Wheel | A", 0.5),
            ContributionBarRow("Wheel | OD", 0.5),
        ]
        stackup1_rows = [
            StackupDetailRow("bushing:2", "", "", "", "", "part"),
            StackupDetailRow("Hole1", "0", "(dia 12.00)", "+/-0.05", "", "feature"),
            StackupDetailRow("Dimension1", "+1", "0.0", "+/-0.10", "", "dimension"),
            StackupDetailRow("Shaft2", "0", "(dia 22.00)", "+/-0.05", "", "feature"),
            StackupDetailRow("axle_support:2", "", "", "", "", "part"),
            StackupDetailRow("Hole3", "0", "(dia 22.00)", "+/-0.05", "", "feature"),
            StackupDetailRow("Dimension2", "-1", "58.0", "+/-0.10", "", "dimension"),
            StackupDetailRow("Face4", "", "", "", "", "feature"),
            StackupDetailRow("top_plate:1", "", "", "", "", "part"),
            StackupDetailRow("Face5", "", "", "", "", "feature"),
            StackupDetailRow("Dimension3", "+1", "0.0", "+/-0.10", "", "dimension"),
            StackupDetailRow("Stackup1", "", "0.000", "+/-0.400", "", "result", status=ResultStatus.WARN, warning=True),
        ]
        root = _demo_assembly_root()
        return cls(
            project_title="caster.iam",
            assembly_roots=[root],
            summary_rows=summary_rows,
            detail_rows_by_stackup_id={
                "overall_height": detail_rows,
                "flush_left": stackup1_rows,
            },
            contribution_rows_by_stackup_id={
                "overall_height": contributions,
                "flush_left": contributions[:5],
            },
            dashboard_badges=DashboardBadges(7, 2, "2.83 / 3.36"),
            selected_stackup_id="overall_height",
        )

    @classmethod
    def from_project(cls, project: CadToleranceProject) -> "CadToleranceWorkspaceViewModel":
        projected_rows, projected_badges = build_dashboard_projection(project)
        summary_rows = [
            StackupSummaryRow(
                row.stackup_id,
                row.status,
                row.name,
                row.nominal,
                row.objective,
                row.target_quality,
                row.results,
                row.predicted_quality,
                row.dimension_count,
                row.has_warning,
            )
            for row in projected_rows
        ]
        detail_rows = {stackup.id: _detail_rows_from_stackup(stackup, project) for stackup in project.stackups}
        contributions = {stackup.id: _contribution_rows_from_stackup(stackup, project) for stackup in project.stackups}
        result_projections = {
            stackup.id: build_result_display(stackup, project=project)
            for stackup in project.stackups
        }
        warnings = {stackup.id: list(stackup.warnings) for stackup in project.stackups}
        annotation_positions = {
            stackup.id: dict(stackup.annotation_position)
            for stackup in project.stackups
            if stackup.annotation_position
        }
        selected = summary_rows[0].stackup_id if summary_rows else ""
        return cls(
            project_title=project.title,
            assembly_roots=[document.assembly_root for document in project.cad_documents if document.assembly_root],
            summary_rows=summary_rows,
            detail_rows_by_stackup_id=detail_rows,
            contribution_rows_by_stackup_id=contributions,
            result_projections_by_stackup_id=result_projections,
            warnings_by_stackup_id=warnings,
            annotation_positions_by_stackup_id=annotation_positions,
            dashboard_badges=DashboardBadges(
                projected_badges.objectives_met,
                projected_badges.objectives_not_met,
                projected_badges.sigma_rollup,
            ),
            selected_stackup_id=selected,
        )

    @classmethod
    def from_document(cls, document: CadDocument) -> "CadToleranceWorkspaceViewModel":
        root = document.assembly_root
        return cls(
            project_title=document.display_name or document.source_path or "Imported CAD",
            assembly_roots=[root] if root else [],
            summary_rows=[],
            dashboard_badges=DashboardBadges(),
        )

    def detail_rows(self, stackup_id: str | None = None) -> list[StackupDetailRow]:
        active_id = stackup_id or self.selected_stackup_id
        return list(self.detail_rows_by_stackup_id.get(active_id, []))

    def contribution_rows(self, stackup_id: str | None = None) -> list[ContributionBarRow]:
        active_id = stackup_id or self.selected_stackup_id
        return list(self.contribution_rows_by_stackup_id.get(active_id, []))

    def result_projection(self, stackup_id: str | None = None) -> ResultDisplayProjection | None:
        active_id = stackup_id or self.selected_stackup_id
        return self.result_projections_by_stackup_id.get(active_id)

    def warnings(self, stackup_id: str | None = None) -> list[NonOneDWarning]:
        active_id = stackup_id or self.selected_stackup_id
        return list(self.warnings_by_stackup_id.get(active_id, []))

    def annotation_position(self, stackup_id: str | None = None) -> dict[str, Any]:
        active_id = stackup_id or self.selected_stackup_id
        return dict(self.annotation_positions_by_stackup_id.get(active_id, {}))

    def select_stackup(self, stackup_id: str) -> None:
        self.selected_stackup_id = stackup_id


class CadStackupSummaryTableModel(QAbstractTableModel):
    def __init__(self, rows: list[StackupSummaryRow] | None = None) -> None:
        super().__init__()
        self._rows = list(rows or [])

    @property
    def rows(self) -> tuple[StackupSummaryRow, ...]:
        return tuple(self._rows)

    def set_rows(self, rows: list[StackupSummaryRow]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def row_at(self, row: int) -> StackupSummaryRow:
        return self._rows[row]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(SUMMARY_COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return SUMMARY_COLUMNS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        column = index.column()
        if role == Qt.ItemDataRole.DisplayRole:
            return _summary_display(row, column)
        if role == Qt.ItemDataRole.DecorationRole and column == 0:
            return _status_icon(row.status, row.has_warning)
        if role == Qt.ItemDataRole.BackgroundRole:
            return _summary_background(row)
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if column in (0, 2, 3, 4, 5, 6, 7):
                return Qt.AlignmentFlag.AlignCenter
            return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        if role == Qt.ItemDataRole.FontRole and row.status == ResultStatus.FAIL:
            font = QFont()
            font.setBold(True)
            return font
        if role == Qt.ItemDataRole.UserRole:
            return row
        if role == Qt.ItemDataRole.ToolTipRole and row.has_warning:
            return NON_1D_WARNING_TEXT
        return None


class CadStackupDetailTableModel(QAbstractTableModel):
    editAccepted = pyqtSignal(str)
    editRejected = pyqtSignal(str)

    def __init__(
        self,
        rows: list[StackupDetailRow] | None = None,
        edit_handler: DetailEditHandler | None = None,
    ) -> None:
        super().__init__()
        self._rows = list(rows or [])
        self._edit_handler = edit_handler
        self._last_error = ""

    @property
    def rows(self) -> tuple[StackupDetailRow, ...]:
        return tuple(self._rows)

    @property
    def last_error(self) -> str:
        return self._last_error

    def set_edit_handler(self, edit_handler: DetailEditHandler | None) -> None:
        self._edit_handler = edit_handler

    def set_rows(self, rows: list[StackupDetailRow]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(DETAIL_COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return DETAIL_COLUMNS[section]
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        flags = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        row = self._rows[index.row()]
        if _detail_cell_is_editable(row, index.column()):
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        column = index.column()
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return _detail_display(row, column)
        if role == Qt.ItemDataRole.DecorationRole and column == 1 and row.shared_with:
            return _stacked_page_icon()
        if role == Qt.ItemDataRole.BackgroundRole:
            return _detail_background(row)
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if column == 0:
                return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
            return Qt.AlignmentFlag.AlignCenter
        if role == Qt.ItemDataRole.FontRole and row.row_type in {"part", "result", "objective"}:
            font = QFont()
            font.setBold(row.row_type in {"result", "objective"})
            return font
        if role == Qt.ItemDataRole.UserRole:
            return row
        if role == DETAIL_TOLERANCE_TYPE_ROLE:
            return row.tolerance_type
        if role == DETAIL_CONTRIBUTOR_ID_ROLE:
            return row.contributor_id
        if role == Qt.ItemDataRole.ToolTipRole:
            notes = []
            if row.shared_with:
                notes.append(
                    "Shared dimension affects: "
                    + ", ".join(_shared_stackup_label(value) for value in row.shared_with)
                )
            if column == 3 and row.geometric_control:
                notes.append(f"Readable feature-control frame: {row.tolerance}")
            if _detail_cell_is_editable(row, column):
                notes.append(_detail_edit_tooltip(row, column))
            if notes:
                return "\n".join(notes)
        return None

    def setData(
        self,
        index: QModelIndex,
        value: Any,
        role: int = Qt.ItemDataRole.EditRole,
    ) -> bool:
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        row = self._rows[index.row()]
        column = index.column()
        if not _detail_cell_is_editable(row, column):
            return self._reject_edit("Only contributor rows can be edited.")
        if self._edit_handler is None:
            return self._reject_edit("No editable CAD tolerance project is loaded.")

        result = self._edit_handler(row, column, "" if value is None else str(value))
        if not result.accepted:
            return self._reject_edit(result.message or "Detail edit was rejected.")

        self._last_error = ""
        if result.rows is not None:
            self.set_rows(result.rows)
        else:
            self.dataChanged.emit(
                index,
                index,
                [
                    int(Qt.ItemDataRole.DisplayRole),
                    int(Qt.ItemDataRole.EditRole),
                    int(Qt.ItemDataRole.ToolTipRole),
                ],
            )
        if result.message:
            self.editAccepted.emit(result.message)
        return True

    def _reject_edit(self, message: str) -> bool:
        self._last_error = message
        self.editRejected.emit(message)
        return False


class CadAssemblyTreeModel(QStandardItemModel):
    def __init__(self, roots: list[AssemblyNode] | None = None) -> None:
        super().__init__()
        self.setHorizontalHeaderLabels(["Model"])
        self.set_roots(roots or [])

    def set_roots(self, roots: list[AssemblyNode]) -> None:
        self.removeRows(0, self.rowCount())
        if not roots:
            self.appendRow(_tree_item("No Browser", "empty", AssemblyNodeType.ROOT))
            return
        for root in roots:
            self.appendRow(_item_from_node(root))


def _demo_assembly_root() -> AssemblyNode:
    root = AssemblyNode("caster.iam", AssemblyNodeType.ROOT, id="demo_root")
    folders = [
        AssemblyNode("3rd Party", AssemblyNodeType.ASSEMBLY, parent_id=root.id, id="demo_3rd_party"),
        AssemblyNode("Relationships", AssemblyNodeType.ASSEMBLY, parent_id=root.id, id="demo_relationships"),
        AssemblyNode("Representations", AssemblyNodeType.ASSEMBLY, parent_id=root.id, id="demo_representations"),
        AssemblyNode("Origin", AssemblyNodeType.ASSEMBLY, parent_id=root.id, id="demo_origin"),
    ]
    parts = [
        "top_plate:1",
        "axle_support:1",
        "bushing:1",
        "axle:1",
        "wheel:1",
        "bushing:2",
        "axle_support:2",
        "hex flange screw:2",
        "hex flange screw:3",
        "hex flange screw:4",
        "hex flange screw:5",
    ]
    root.children.extend(folders)
    root.children.extend(
        AssemblyNode(name, AssemblyNodeType.PART, parent_id=root.id, id=f"demo_{index}")
        for index, name in enumerate(parts, start=1)
    )
    return root


def _summary_row_from_stackup(stackup: StackupRequirement, project: CadToleranceProject) -> StackupSummaryRow:
    result = calculate_stackup(stackup, project.settings)
    return StackupSummaryRow(
        stackup_id=stackup.id,
        status=result.status,
        name=stackup.name,
        nominal=_format_nominal(result.nominal),
        objective=_format_objective(stackup.objective),
        target_quality=_format_quality_target(stackup),
        results=_format_result_envelope(stackup.objective, result.evaluated_minus, result.evaluated_plus, result.nominal),
        predicted_quality=_format_predicted_quality(result.quality.target_metric, result.quality.cpk, result.quality.sigma, result.quality.yield_probability),
        dimension_count=len(stackup.contributors),
        has_warning=bool(result.warnings),
    )


def _detail_rows_from_stackup(
    stackup: StackupRequirement,
    project: CadToleranceProject | None = None,
) -> list[StackupDetailRow]:
    rows: list[StackupDetailRow] = []
    last_part = ""
    for contributor in stackup.contributors:
        part_name = _part_name(contributor)
        if part_name and part_name != last_part:
            rows.append(StackupDetailRow(part_name, row_type="part"))
            last_part = part_name
        feature_name = _feature_name(contributor.source_feature)
        if feature_name:
            rows.append(
                StackupDetailRow(
                    feature_name,
                    "0",
                    _feature_nominal(contributor.source_feature),
                    _format_tolerance(contributor),
                    _datum_text(contributor),
                    "feature",
                    shared_with=tuple(contributor.shared_with_stackup_ids),
                    contributor_id=contributor.id,
                    source_feature_id=contributor.source_feature.id if contributor.source_feature else "",
                    source_note=contributor.source_note,
                    tolerance_type=contributor.tolerance_type.value,
                    geometric_control=_geometric_control_value(contributor),
                )
            )
        rows.append(
            StackupDetailRow(
                contributor.name,
                _format_sensitivity(contributor.sensitivity),
                _format_nominal(contributor.nominal),
                _format_tolerance(contributor),
                _datum_text(contributor),
                "dimension",
                shared_with=tuple(contributor.shared_with_stackup_ids),
                contributor_id=contributor.id,
                source_feature_id=contributor.source_feature.id if contributor.source_feature else "",
                generated=contributor.source_note.startswith("Generated from guided stackup"),
                source_note=contributor.source_note,
                tolerance_type=contributor.tolerance_type.value,
                geometric_control=_geometric_control_value(contributor),
            )
        )
    result = calculate_stackup(stackup, project.settings if project else None)
    rows.append(
        StackupDetailRow(
            stackup.name,
            nominal=_format_nominal(result.nominal),
            tolerance=_format_result_envelope(stackup.objective, result.evaluated_minus, result.evaluated_plus, result.nominal),
            row_type="result",
            status=result.status,
            warning=bool(result.warnings),
        )
    )
    rows.append(
        StackupDetailRow(
            "Objectives",
            tolerance=_format_objective(stackup.objective),
            row_type="objective",
            status=result.objective.status,
        )
    )
    return rows


def _shared_stackup_label(value: str) -> str:
    label = value.removeprefix("stackup_").strip()
    return label.replace("_", " ") if label else value


def _contribution_rows_from_stackup(stackup: StackupRequirement, project: CadToleranceProject) -> list[ContributionBarRow]:
    return [
        ContributionBarRow(
            item.label,
            item.percent,
            item.tolerance_box,
            item.datum,
            item.contributor_id,
        )
        for item in build_contribution_projection(stackup, project=project)
    ]


def _summary_display(row: StackupSummaryRow, column: int) -> Any:
    values = (
        "",
        row.name,
        row.nominal,
        row.objective,
        row.target_quality,
        row.results,
        row.predicted_quality,
        str(row.dimension_count),
    )
    return values[column]


def _detail_display(row: StackupDetailRow, column: int) -> str:
    values = (row.name, row.sensitivity, row.nominal, row.tolerance, row.datum)
    return values[column]


def _detail_cell_is_editable(row: StackupDetailRow, column: int) -> bool:
    if not row.contributor_id:
        return False
    if row.row_type == "dimension":
        return column in {0, 1, 2, 3, 4}
    if row.row_type == "feature":
        return column in {0, 3, 4}
    return False


def _detail_edit_tooltip(row: StackupDetailRow, column: int) -> str:
    labels = {
        0: "Edit contributor or controlled-feature name.",
        1: "Edit stack sensitivity.",
        2: "Edit nominal contribution.",
        3: "Edit tolerance as symmetric +/-0.05, limits +0.02/-0.01, runout 0.1 A, position 0.15 A, or profile 0.5 A.",
        4: "Edit datum/reference labels, separated by commas or spaces.",
    }
    text = labels.get(column, "Edit value.")
    if row.tolerance_type:
        text += f" Current tolerance mode: {row.tolerance_type}."
    return text


def _summary_background(row: StackupSummaryRow) -> QBrush | None:
    if row.status == ResultStatus.FAIL:
        return QBrush(QColor("#faf2f2"))
    if row.status in {ResultStatus.PASS, ResultStatus.WARN}:
        return QBrush(QColor("#effbf1"))
    return None


def _detail_background(row: StackupDetailRow) -> QBrush | None:
    if row.status == ResultStatus.FAIL:
        return QBrush(QColor("#faf2f2"))
    if row.warning or row.status == ResultStatus.WARN:
        return QBrush(QColor("#fff7d6"))
    if row.row_type == "part":
        return QBrush(QColor("#ffffff"))
    if row.row_type == "feature":
        return QBrush(QColor("#f3f3f3"))
    if row.row_type in {"result", "objective"}:
        return QBrush(QColor("#f2f2f2"))
    return None


def _status_icon(status: ResultStatus, warning: bool = False) -> QIcon:
    if status == ResultStatus.FAIL:
        return _circle_icon(QColor("#c91f1f"), "X")
    if warning or status == ResultStatus.WARN:
        return _pass_warning_icon()
    if status == ResultStatus.PASS:
        return _circle_icon(QColor("#168a29"), "")
    return _circle_icon(QColor("#888888"), "")


def _pass_warning_icon() -> QIcon:
    pixmap = QPixmap(22, 18)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    green = QColor("#168a29")
    painter.setBrush(QBrush(green))
    painter.setPen(QPen(green.darker(125), 1))
    painter.drawEllipse(1, 2, 14, 14)
    painter.setPen(QPen(QColor("#ffffff"), 2))
    painter.drawLine(4, 9, 7, 12)
    painter.drawLine(7, 12, 12, 6)
    yellow = QColor("#f2c200")
    painter.setBrush(QBrush(yellow))
    painter.setPen(QPen(yellow.darker(140), 1))
    points = [
        pixmap.rect().center() + _point_delta(5, -5),
        pixmap.rect().center() + _point_delta(-2, 7),
        pixmap.rect().center() + _point_delta(12, 7),
    ]
    painter.drawPolygon(*points)
    painter.setPen(QPen(QColor("#333333"), 1))
    painter.drawLine(16, 9, 16, 12)
    painter.drawPoint(16, 14)
    painter.end()
    return QIcon(pixmap)


def _stacked_page_icon() -> QIcon:
    pixmap = QPixmap(18, 18)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor("#555555"), 1))
    painter.setBrush(QBrush(QColor("#f4f4f4")))
    painter.drawRect(6, 3, 8, 11)
    painter.drawRect(3, 6, 8, 11)
    painter.end()
    return QIcon(pixmap)


def _circle_icon(color: QColor, label: str) -> QIcon:
    pixmap = QPixmap(18, 18)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QBrush(color))
    painter.setPen(QPen(color.darker(125), 1))
    painter.drawEllipse(2, 2, 14, 14)
    if label:
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.drawLine(6, 6, 12, 12)
        painter.drawLine(12, 6, 6, 12)
    else:
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.drawLine(5, 9, 8, 12)
        painter.drawLine(8, 12, 13, 6)
    painter.end()
    return QIcon(pixmap)


def _triangle_icon(color: QColor) -> QIcon:
    pixmap = QPixmap(18, 18)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QBrush(color))
    painter.setPen(QPen(color.darker(140), 1))
    points = [
        pixmap.rect().center() + _point_delta(0, -7),
        pixmap.rect().center() + _point_delta(-7, 6),
        pixmap.rect().center() + _point_delta(7, 6),
    ]
    painter.drawPolygon(*points)
    painter.setPen(QPen(QColor("#333333"), 1))
    painter.drawLine(9, 7, 9, 11)
    painter.drawPoint(9, 13)
    painter.end()
    return QIcon(pixmap)


def _point_delta(x: int, y: int):
    from PyQt6.QtCore import QPoint

    return QPoint(x, y)


def _tree_item(text: str, item_id: str, node_type: AssemblyNodeType) -> QStandardItem:
    item = QStandardItem(text)
    item.setEditable(False)
    item.setData(item_id, Qt.ItemDataRole.UserRole)
    item.setData(True, ASSEMBLY_VISIBILITY_ROLE)
    item.setToolTip("Visible in the CAD viewport")
    item.setIcon(_tree_icon(node_type))
    return item


def _item_from_node(node: AssemblyNode) -> QStandardItem:
    item = _tree_item(node.name, node.id, node.node_type)
    for child in node.children:
        item.appendRow(_item_from_node(child))
    return item


def _tree_icon(node_type: AssemblyNodeType) -> QIcon:
    app = QApplication.instance()
    if app is None:
        return QIcon()
    style = app.style()
    if node_type in {AssemblyNodeType.ROOT, AssemblyNodeType.ASSEMBLY}:
        return style.standardIcon(QStyle.StandardPixmap.SP_DirIcon)
    if node_type in {AssemblyNodeType.PART, AssemblyNodeType.BODY}:
        return style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)
    return style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)


def _format_nominal(value: float) -> str:
    number = float(value)
    if abs(number) >= 100:
        return f"{number:.2f}"
    if abs(number) >= 10:
        return f"{number:.3f}".rstrip("0").rstrip(".")
    return f"{number:.3f}".rstrip("0").rstrip(".") or "0"


def _format_objective(objective: StackupObjective) -> str:
    if objective.objective_type == ObjectiveType.BILATERAL:
        if abs(objective.tolerance_minus - objective.tolerance_plus) < 1.0e-9:
            return f"+/-{objective.tolerance_plus:.3f}".rstrip("0").rstrip(".")
        return f"+{objective.tolerance_plus:.3f}/-{objective.tolerance_minus:.3f}"
    if objective.objective_type == ObjectiveType.UPPER_LIMIT:
        return f"<= {objective.upper_limit:.3f}" if objective.upper_limit is not None else "<= --"
    if objective.objective_type == ObjectiveType.LOWER_LIMIT:
        return f">= {objective.lower_limit:.3f}" if objective.lower_limit is not None else ">= --"
    lower = "--" if objective.lower_limit is None else f"{objective.lower_limit:.3f}"
    upper = "--" if objective.upper_limit is None else f"{objective.upper_limit:.3f}"
    return f"{lower} to {upper}"


def _format_quality_target(stackup: StackupRequirement) -> str:
    target = stackup.target_quality
    if stackup.analysis_mode == AnalysisMode.RSS or target.metric == QualityMetric.RSS:
        return "RSS"
    if stackup.analysis_mode == AnalysisMode.WORST_CASE or target.metric == QualityMetric.WORST_CASE:
        return "Worst Case"
    if target.value is None:
        return _metric_label(target.metric)
    if target.metric == QualityMetric.YIELD:
        return f"Yield = {target.value:.2f}%"
    return f"{_metric_label(target.metric)} = {target.value:.2f}"


def _format_predicted_quality(metric: QualityMetric, cpk: float | None, sigma: float | None, yield_probability: float | None) -> str:
    if metric == QualityMetric.CPK and cpk is not None:
        return f"Cpk = {cpk:.2f}"
    if metric == QualityMetric.SIGMA and sigma is not None:
        return f"Sigma = {sigma:.2f}"
    if metric == QualityMetric.YIELD and yield_probability is not None:
        return f"Yield = {yield_probability * 100.0:.0f}%"
    return ""


def _format_result_envelope(objective: StackupObjective, minus: float, plus: float, nominal: float) -> str:
    if objective.objective_type == ObjectiveType.UPPER_LIMIT:
        return f"<= {nominal + plus:.3f}"
    if objective.objective_type == ObjectiveType.LOWER_LIMIT:
        return f">= {nominal - minus:.3f}"
    if abs(minus - plus) < 1.0e-9:
        return f"+/-{plus:.3f}".rstrip("0").rstrip(".")
    return f"+{plus:.3f}/-{minus:.3f}"


def _format_tolerance(contributor: StackupContributor) -> str:
    if contributor.tolerance_type == ToleranceType.GEOMETRIC and contributor.geometric_tolerance:
        datums = (
            contributor.geometric_tolerance.datum_references
            or contributor.datum_references
        )
        return geometric_tolerance_frame_text(
            contributor.geometric_tolerance.control_type,
            contributor.geometric_tolerance.tolerance_value,
            datums,
        )
    minus = float(contributor.tolerance_minus or 0.0)
    plus = float(contributor.tolerance_plus or 0.0)
    if abs(minus - plus) < 1.0e-9:
        return f"+/-{plus:.3f}".rstrip("0").rstrip(".")
    return f"+{plus:.3f}/-{minus:.3f}"


def _format_sensitivity(value: float) -> str:
    if abs(value - 1.0) < 1.0e-9:
        return "+1"
    if abs(value + 1.0) < 1.0e-9:
        return "-1"
    return f"{value:g}"


def _metric_label(metric: QualityMetric) -> str:
    labels = {
        QualityMetric.CPK: "Cpk",
        QualityMetric.SIGMA: "Sigma",
        QualityMetric.YIELD: "Yield",
        QualityMetric.WORST_CASE: "Worst Case",
        QualityMetric.RSS: "RSS",
    }
    return labels[metric]


def _part_name(contributor: StackupContributor) -> str:
    feature = contributor.source_feature
    if feature and feature.shape_reference and feature.shape_reference.assembly_path:
        return feature.shape_reference.assembly_path[-1]
    if feature and feature.owner_part_id:
        return feature.owner_part_id
    return ""


def _feature_name(feature: FeatureReference | None) -> str:
    if feature is None:
        return ""
    return feature.name or (
        feature.shape_reference.fallback_display_name if feature.shape_reference else ""
    )


def _feature_nominal(feature: FeatureReference | None) -> str:
    if feature is None or feature.shape_reference is None:
        return ""
    signature = feature.shape_reference.geometric_signature
    radius = signature.get("radius")
    if radius is not None:
        return f"(dia {float(radius) * 2.0:.2f})"
    return ""


def _datum_text(contributor: StackupContributor) -> str:
    if contributor.datum_references:
        return ", ".join(contributor.datum_references)
    if contributor.geometric_tolerance and contributor.geometric_tolerance.datum_references:
        return ", ".join(contributor.geometric_tolerance.datum_references)
    if contributor.source_feature and contributor.source_feature.datum_label:
        return contributor.source_feature.datum_label
    return ""


def _geometric_control_value(contributor: StackupContributor) -> str:
    if contributor.geometric_tolerance is None:
        return ""
    return contributor.geometric_tolerance.control_type.value


def _sigma_rollup_from_rows(rows: list[StackupSummaryRow]) -> str:
    sigma_rows = [row for row in rows if "Sigma" in row.predicted_quality or "Sigma" in row.target_quality]
    return "" if not sigma_rows else f"{len(sigma_rows)} sigma rows"
