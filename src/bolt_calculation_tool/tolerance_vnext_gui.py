"""Qt Quick / QML next-version tolerance analysis workspace."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path
import sys
from typing import Any

from .tolerance_catalog import HardwareCatalogRecord, ToleranceCatalog
from .tolerance_methods import (
    StackupPathResult,
    SubJointResult,
    calculate_sub_joint_result,
)
from .tolerance_models import (
    Flange,
    Joint,
    MethodSettings,
    PathItem,
    SubJoint,
    ToleranceProject,
    create_default_joint,
    create_default_project,
    next_joint_name,
    sync_path_with_flanges,
)
from .tolerance_optimizer import rank_bolt_lengths
from .tolerance_project_io import load_project, save_project
from .tolerance_spreadsheet_io import load_spreadsheet_project

try:
    from PyQt6.QtCore import QObject, Qt, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
    from PyQt6.QtGui import QGuiApplication, QImage, QPainter, QPageLayout, QPageSize, QPdfWriter
    from PyQt6.QtQml import QQmlApplicationEngine
    from PyQt6.QtQuick import QQuickWindow
    from PyQt6.QtWidgets import QApplication, QFileDialog
except ImportError as exc:  # pragma: no cover - exercised only without GUI deps.
    raise RuntimeError(
        "The tolerance vNext GUI requires PyQt6 with Qt Quick/QML support."
    ) from exc


QUICK_STYLE_OPTIONS = ("Fusion", "Material", "Universal", "Basic", "Imagine")
MATERIAL_THEME_OPTIONS = ("Light", "Dark")
DEFAULT_QUICK_STYLE = "Fusion"
DEFAULT_MATERIAL_THEME = "Light"
PREFERENCES_ENV_VAR = "TOLERANCE_VNEXT_PREFERENCES"


class ToleranceVNextBackend(QObject):
    projectChanged = pyqtSignal()
    selectedChanged = pyqtSignal()
    statusChanged = pyqtSignal()
    themeChanged = pyqtSignal()

    def __init__(
        self,
        catalog: ToleranceCatalog | None = None,
        *,
        quick_style: str | None = None,
        material_theme: str | None = None,
        preferences_path: Path | str | None = None,
    ) -> None:
        super().__init__()
        QQuickWindow.setTextRenderType(QQuickWindow.TextRenderType.NativeTextRendering)
        self.catalog = catalog or ToleranceCatalog.builtin()
        self.project = create_default_project()
        self.project_path: Path | None = None
        self.dirty = False
        self.status_text = "Ready."
        self.window = None
        self.preferences_path = (
            Path(preferences_path) if preferences_path is not None else _theme_preferences_path()
        )
        self.active_quick_style = (
            _match_choice(quick_style, QUICK_STYLE_OPTIONS)
            or _match_choice(os.environ.get("QT_QUICK_CONTROLS_STYLE"), QUICK_STYLE_OPTIONS)
            or DEFAULT_QUICK_STYLE
        )
        self.active_material_theme = (
            _match_choice(material_theme, MATERIAL_THEME_OPTIONS)
            or _match_choice(
                os.environ.get("QT_QUICK_CONTROLS_MATERIAL_THEME"),
                MATERIAL_THEME_OPTIONS,
            )
            or DEFAULT_MATERIAL_THEME
        )
        self.preferred_quick_style = self.active_quick_style
        self.preferred_material_theme = self.active_material_theme
        first_joint = self.project.joints[0]
        self.selected_joint_id = first_joint.id
        self.selected_sub_joint_id = first_joint.sub_joints[0].id
        self._ensure_selection_valid()

    @pyqtProperty(str, notify=projectChanged)
    def projectTitle(self) -> str:
        return self.project.title

    @pyqtProperty(str, notify=projectChanged)
    def unitSystem(self) -> str:
        return self.project.unit_system

    @pyqtProperty(str, notify=statusChanged)
    def statusText(self) -> str:
        return self.status_text

    @pyqtProperty(str, notify=projectChanged)
    def saveState(self) -> str:
        path = str(self.project_path) if self.project_path else "Unsaved project"
        return f"{'*' if self.dirty else ''}{path}"

    @pyqtProperty("QVariant", notify=themeChanged)
    def availableQuickStyles(self) -> list[str]:
        return list(QUICK_STYLE_OPTIONS)

    @pyqtProperty("QVariant", notify=themeChanged)
    def availableMaterialThemes(self) -> list[str]:
        return list(MATERIAL_THEME_OPTIONS)

    @pyqtProperty(str, notify=themeChanged)
    def quickStyle(self) -> str:
        return self.preferred_quick_style

    @pyqtProperty(str, notify=themeChanged)
    def activeQuickStyle(self) -> str:
        return self.active_quick_style

    @pyqtProperty(str, notify=themeChanged)
    def materialTheme(self) -> str:
        return self.preferred_material_theme

    @pyqtProperty(str, notify=themeChanged)
    def activeMaterialTheme(self) -> str:
        return self.active_material_theme

    @pyqtProperty(bool, notify=themeChanged)
    def themeRestartRequired(self) -> bool:
        material_changed = (
            self.preferred_quick_style == "Material"
            and self.preferred_material_theme != self.active_material_theme
        )
        return self.preferred_quick_style != self.active_quick_style or material_changed

    @pyqtProperty(str, notify=themeChanged)
    def themeHint(self) -> str:
        if self.themeRestartRequired:
            return (
                f"Restart to apply {self.preferred_quick_style} "
                f"{self.preferred_material_theme}."
            )
        if self.active_quick_style == "Material":
            return f"Active style: {self.active_quick_style} {self.active_material_theme}."
        return f"Active style: {self.active_quick_style}."

    @pyqtProperty("QVariant", notify=projectChanged)
    def joints(self) -> list[dict[str, Any]]:
        return [self._joint_to_ui(joint) for joint in self.project.joints]

    @pyqtProperty("QVariant", notify=selectedChanged)
    def selectedJoint(self) -> dict[str, Any]:
        joint = self._selected_joint()
        return self._joint_to_ui(joint) if joint else {}

    @pyqtProperty("QVariant", notify=selectedChanged)
    def selectedSubJoint(self) -> dict[str, Any]:
        selected = self._selected_pair()
        if selected is None:
            return {}
        _, sub_joint = selected
        return self._sub_joint_to_ui(sub_joint)

    @pyqtProperty("QVariant", notify=projectChanged)
    def flanges(self) -> list[dict[str, Any]]:
        joint = self._selected_joint()
        if joint is None:
            return []
        return [self._flange_to_ui(flange) for flange in joint.flanges]

    @pyqtProperty("QVariant", notify=projectChanged)
    def pathItems(self) -> list[dict[str, Any]]:
        selected = self._selected_pair()
        if selected is None:
            return []
        joint, sub_joint = selected
        sync_path_with_flanges(joint, sub_joint)
        return [self._path_item_to_ui(item) for item in sub_joint.stackup_path.items]

    @pyqtProperty("QVariant", notify=projectChanged)
    def boltSizes(self) -> list[str]:
        return self.catalog.bolt_sizes()

    @pyqtProperty("QVariant", notify=projectChanged)
    def boltTypes(self) -> list[str]:
        selected = self._selected_pair()
        if selected is None:
            return []
        _, sub_joint = selected
        return self.catalog.bolt_types_for_size(sub_joint.bolt_size_id)

    @pyqtProperty("QVariant", notify=projectChanged)
    def boltLengths(self) -> list[str]:
        selected = self._selected_pair()
        if selected is None:
            return []
        _, sub_joint = selected
        return [
            _format_number(length)
            for length in self.catalog.lengths_for(
                sub_joint.bolt_size_id, sub_joint.bolt_type_id
            )
        ]

    @pyqtProperty("QVariant", notify=projectChanged)
    def hardwareOptions(self) -> list[dict[str, Any]]:
        selected = self._selected_pair()
        if selected is None:
            return []
        _, sub_joint = selected
        options: list[dict[str, Any]] = []
        for part_type in ("nut", "insert", "bracket", "washer"):
            for item in self.catalog.hardware_by_type(part_type, sub_joint.bolt_size_id):
                options.append(self._hardware_to_ui(item))
        return options

    @pyqtProperty("QVariant", notify=projectChanged)
    def engagementOptions(self) -> list[dict[str, Any]]:
        selected = self._selected_pair()
        if selected is None:
            return []
        _, sub_joint = selected
        part_type = sub_joint.stackup_path.engagement_type
        return [
            self._hardware_to_ui(item)
            for item in self.catalog.hardware_by_type(part_type, sub_joint.bolt_size_id)
        ]

    @pyqtProperty("QVariant", notify=projectChanged)
    def metrics(self) -> dict[str, Any]:
        result = self._selected_result()
        if result is None:
            return {}
        stackup = result.stackup
        protrusion = result.protrusion
        contributors = stackup.contributors[:4]
        monte_carlo = _monte_carlo_to_ui(stackup.monte_carlo)
        return {
            "status": protrusion.status,
            "nominal": _format_number(stackup.nominal),
            "worst_case": _format_number(stackup.worst_case_deviation),
            "worst_case_minus": _format_number(stackup.worst_case_minus),
            "worst_case_plus": _format_number(stackup.worst_case_plus),
            "rss": _format_number(stackup.rss),
            "rss_minus": _format_number(stackup.rss_minus),
            "rss_plus": _format_number(stackup.rss_plus),
            "one_point_five_rss": _format_number(stackup.one_point_five_rss),
            "one_point_five_rss_minus": _format_number(
                stackup.one_point_five_rss_minus
            ),
            "one_point_five_rss_plus": _format_number(
                stackup.one_point_five_rss_plus
            ),
            "top_four": f"{stackup.top_four_contributor_sum * 100.0:.0f}%",
            "top_contributors": ", ".join(item.name for item in contributors) or "-",
            "protrusion": _format_optional(protrusion.protrusion),
            "engagement": _format_optional(protrusion.engagement),
            "monte_carlo": monte_carlo,
            "criteria": [
                {
                    "name": item.name,
                    "required": _format_number(item.required),
                    "actual": _format_optional(item.actual),
                    "margin": _format_optional(item.margin),
                    "status": item.status,
                    "message": item.message,
                }
                for item in protrusion.criteria
            ],
            "messages": list(protrusion.messages),
        }

    @pyqtProperty("QVariant", notify=projectChanged)
    def candidateRows(self) -> list[dict[str, Any]]:
        selected = self._selected_pair()
        result = self._selected_result()
        if selected is None or result is None:
            return []
        _, sub_joint = selected
        ranked = rank_bolt_lengths(sub_joint, result.stackup, self.catalog)
        rows = [
            self._candidate_to_ui(item, item.length == ranked.recommended_length)
            for item in ranked.candidates
        ]
        rows.extend(self._candidate_to_ui(item, False) for item in ranked.rejected)
        return rows

    @pyqtProperty("QVariant", notify=projectChanged)
    def summaryRows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for joint in self.project.joints:
            for sub_joint in joint.sub_joints:
                try:
                    result = calculate_sub_joint_result(joint, sub_joint, self.catalog)
                    rows.append(
                        {
                            "joint": joint.name,
                            "sub_joint": sub_joint.name,
                            "bolt": f"{sub_joint.bolt_size_id} {sub_joint.bolt_type_id}",
                            "length": _format_number(sub_joint.selected_bolt_length),
                            "worst_case": _format_number(
                                result.stackup.worst_case_deviation
                            ),
                            "worst_case_minus": _format_number(
                                result.stackup.worst_case_minus
                            ),
                            "worst_case_plus": _format_number(
                                result.stackup.worst_case_plus
                            ),
                            "rss": _format_number(result.stackup.rss),
                            "rss_minus": _format_number(result.stackup.rss_minus),
                            "rss_plus": _format_number(result.stackup.rss_plus),
                            "one_point_five_rss": _format_number(
                                result.stackup.one_point_five_rss
                            ),
                            "mc_mean": _format_optional(
                                result.stackup.monte_carlo.mean
                                if result.stackup.monte_carlo
                                else None
                            ),
                            "mc_p00135": _format_optional(
                                result.stackup.monte_carlo.p00135
                                if result.stackup.monte_carlo
                                else None
                            ),
                            "mc_p99865": _format_optional(
                                result.stackup.monte_carlo.p99865
                                if result.stackup.monte_carlo
                                else None
                            ),
                            "top_four": (
                                f"{result.stackup.top_four_contributor_sum * 100.0:.0f}%"
                            ),
                            "status": result.protrusion.status,
                        }
                    )
                except ValueError as exc:
                    rows.append(
                        {
                            "joint": joint.name,
                            "sub_joint": sub_joint.name,
                            "bolt": "-",
                            "length": "-",
                            "worst_case": "-",
                            "worst_case_minus": "-",
                            "worst_case_plus": "-",
                            "rss": "-",
                            "rss_minus": "-",
                            "rss_plus": "-",
                            "one_point_five_rss": "-",
                            "mc_mean": "-",
                            "mc_p00135": "-",
                            "mc_p99865": "-",
                            "top_four": "-",
                            "status": f"Input error: {exc}",
                        }
                    )
        return rows

    @pyqtProperty("QVariant", notify=projectChanged)
    def threadRows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for joint in self.project.joints:
            for sub_joint in joint.sub_joints:
                result = calculate_sub_joint_result(joint, sub_joint, self.catalog)
                criteria = {item.name: item for item in result.protrusion.criteria}
                rows.append(
                    {
                        "joint": joint.name,
                        "sub_joint": sub_joint.name,
                        "one_five_p": _criterion_cell(criteria.get("1.5P")),
                        "two_p": _criterion_cell(criteria.get("2P")),
                        "two_p_chamfer": _criterion_cell(
                            criteria.get("2P+Chamfer")
                        ),
                        "status": result.protrusion.status,
                    }
                )
        return rows

    @pyqtSlot()
    def refresh(self) -> None:
        self._emit_all()

    @pyqtSlot(str)
    def setQuickStyle(self, style: str) -> None:
        matched = _match_choice(style, QUICK_STYLE_OPTIONS)
        if matched is None:
            self._set_status(f"{style} is not an available Qt Quick Controls style.")
            return
        self.preferred_quick_style = matched
        self._persist_theme_preferences()

    @pyqtSlot(str)
    def setMaterialTheme(self, theme: str) -> None:
        matched = _match_choice(theme, MATERIAL_THEME_OPTIONS)
        if matched is None:
            self._set_status(f"{theme} is not an available Material theme.")
            return
        self.preferred_material_theme = matched
        self._persist_theme_preferences()

    @pyqtSlot(str)
    def setProjectTitle(self, title: str) -> None:
        self.project.title = title.strip() or "Tolerance Project"
        self._mark_dirty("Project title updated.")

    @pyqtSlot(str, str)
    def selectSubJoint(self, joint_id: str, sub_joint_id: str) -> None:
        self.selected_joint_id = joint_id
        self.selected_sub_joint_id = sub_joint_id
        self._ensure_selection_valid()
        self.status_text = "Selected stackup path."
        self.selectedChanged.emit()
        self.statusChanged.emit()

    @pyqtSlot()
    def addJoint(self) -> None:
        joint = create_default_joint(next_joint_name(len(self.project.joints)))
        self.project.joints.append(joint)
        self.selected_joint_id = joint.id
        self.selected_sub_joint_id = joint.sub_joints[0].id
        self._mark_dirty(f"Added {joint.name}.")

    @pyqtSlot()
    def addFlange(self) -> None:
        joint = self._selected_joint()
        if joint is None:
            return
        flange = Flange(
            name=f"Flange {len(joint.flanges) + 1}",
            nominal_thickness=0.0,
            tolerance=0.0,
        )
        joint.flanges.append(flange)
        for sub_joint in joint.sub_joints:
            sync_path_with_flanges(joint, sub_joint)
        self._mark_dirty(f"Added {flange.name}.")

    @pyqtSlot()
    def addSubJoint(self) -> None:
        joint = self._selected_joint()
        if joint is None:
            return
        sub_joint = SubJoint(name=f"{joint.name}.{len(joint.sub_joints) + 1}")
        joint.sub_joints.append(sub_joint)
        sync_path_with_flanges(joint, sub_joint)
        self.selected_sub_joint_id = sub_joint.id
        self._mark_dirty(f"Added {sub_joint.name}.")

    @pyqtSlot()
    def duplicateSelectedSubJoint(self) -> None:
        selected = self._selected_pair()
        if selected is None:
            return
        joint, source = selected
        sub_joint = SubJoint(
            name=f"{joint.name}.{len(joint.sub_joints) + 1}",
            bolt_size_id=source.bolt_size_id,
            bolt_type_id=source.bolt_type_id,
            selected_bolt_length=source.selected_bolt_length,
        )
        sub_joint.stackup_path.engagement_type = source.stackup_path.engagement_type
        sub_joint.stackup_path.selected_engagement_part_id = (
            source.stackup_path.selected_engagement_part_id
        )
        source_settings = source.stackup_path.method_settings
        sub_joint.stackup_path.method_settings = MethodSettings(
            sigma_coverage=source_settings.sigma_coverage,
            monte_carlo_enabled=source_settings.monte_carlo_enabled,
            monte_carlo_sample_count=source_settings.monte_carlo_sample_count,
            monte_carlo_seed=source_settings.monte_carlo_seed,
        )
        sub_joint.stackup_path.items = [
            PathItem(
                source_type=item.source_type,
                source_id=item.source_id,
                name=item.name,
                nominal_thickness=item.nominal_thickness,
                tolerance=item.tolerance,
                tolerance_minus=item.tolerance_minus,
                tolerance_plus=item.tolerance_plus,
                role=item.role,
                include_in_stackup=item.include_in_stackup,
            )
            for item in source.stackup_path.items
        ]
        joint.sub_joints.append(sub_joint)
        self.selected_sub_joint_id = sub_joint.id
        self._mark_dirty(f"Duplicated as {sub_joint.name}.")

    @pyqtSlot(str, str)
    def renameSelectedJoint(self, name: str, sub_name: str) -> None:
        selected = self._selected_pair()
        if selected is None:
            return
        joint, sub_joint = selected
        if name.strip():
            joint.name = name.strip()
        if sub_name.strip():
            sub_joint.name = sub_name.strip()
        self._mark_dirty("Names updated.")

    @pyqtSlot(str, str, str)
    @pyqtSlot(str, str, str, str)
    def updateFlange(
        self,
        flange_id: str,
        nominal: str,
        tolerance_minus: str,
        tolerance_plus: str | None = None,
    ) -> None:
        joint = self._selected_joint()
        if joint is None:
            return
        flange = next((item for item in joint.flanges if item.id == flange_id), None)
        if flange is None:
            return
        try:
            nominal_value, minus_value, plus_value = _parse_tolerance_inputs(
                flange.name,
                nominal,
                tolerance_minus,
                tolerance_plus,
            )
        except ValueError:
            self._set_status(f"{flange.name}: thickness and tolerance must be numeric.")
            return
        if minus_value < 0.0 or plus_value < 0.0:
            self._set_status(f"{flange.name}: tolerance must be non-negative.")
            return
        flange.nominal_thickness = nominal_value
        flange.tolerance_minus = minus_value
        flange.tolerance_plus = plus_value
        flange.tolerance = max(minus_value, plus_value)
        for sub_joint in joint.sub_joints:
            sync_path_with_flanges(joint, sub_joint)
        self._mark_dirty(f"{flange.name} updated.")

    @pyqtSlot(str)
    def setBoltSize(self, size: str) -> None:
        selected = self._selected_pair()
        if selected is None or not size:
            return
        _, sub_joint = selected
        sub_joint.bolt_size_id = size
        types = self.catalog.bolt_types_for_size(size)
        sub_joint.bolt_type_id = types[0] if types else ""
        lengths = self.catalog.lengths_for(size, sub_joint.bolt_type_id)
        sub_joint.selected_bolt_length = lengths[0] if lengths else 0.0
        self._ensure_default_engagement(sub_joint)
        self._mark_dirty("Bolt size updated.")

    @pyqtSlot(str)
    def setBoltType(self, bolt_type: str) -> None:
        selected = self._selected_pair()
        if selected is None or not bolt_type:
            return
        _, sub_joint = selected
        sub_joint.bolt_type_id = bolt_type
        lengths = self.catalog.lengths_for(sub_joint.bolt_size_id, bolt_type)
        if lengths and sub_joint.selected_bolt_length not in lengths:
            sub_joint.selected_bolt_length = lengths[0]
        self._mark_dirty("Bolt type updated.")

    @pyqtSlot(str)
    def setBoltLength(self, length: str) -> None:
        selected = self._selected_pair()
        if selected is None or not length:
            return
        try:
            value = float(length)
        except ValueError:
            self._set_status("Bolt length must be numeric.")
            return
        _, sub_joint = selected
        sub_joint.selected_bolt_length = value
        self._mark_dirty("Bolt length updated.")

    @pyqtSlot(str)
    def setEngagementType(self, part_type: str) -> None:
        selected = self._selected_pair()
        if selected is None or not part_type:
            return
        _, sub_joint = selected
        sub_joint.stackup_path.engagement_type = part_type
        self._ensure_default_engagement(sub_joint)
        self._mark_dirty("Engagement type updated.")

    @pyqtSlot(str)
    def setEngagementPart(self, item_id: str) -> None:
        selected = self._selected_pair()
        if selected is None or not item_id:
            return
        _, sub_joint = selected
        sub_joint.stackup_path.selected_engagement_part_id = item_id
        self._mark_dirty("Engagement part updated.")

    @pyqtSlot(str)
    def addCatalogPathItem(self, item_id: str) -> None:
        selected = self._selected_pair()
        if selected is None or not item_id:
            return
        _, sub_joint = selected
        record = self.catalog.find_hardware(item_id)
        if record is None:
            self._set_status("Catalog item was not found.")
            return
        sub_joint.stackup_path.items.append(
            PathItem(
                source_type="catalog",
                source_id=record.id,
                name=record.display_name,
                nominal_thickness=record.nominal_thickness,
                tolerance=record.tolerance,
                tolerance_minus=record.tolerance,
                tolerance_plus=record.tolerance,
                role=record.part_type,
            )
        )
        self._mark_dirty(f"Added {record.display_name}.")

    @pyqtSlot()
    def addCustomPathItem(self) -> None:
        selected = self._selected_pair()
        if selected is None:
            return
        _, sub_joint = selected
        sub_joint.stackup_path.items.append(
            PathItem(
                name="Custom item",
                nominal_thickness=0.0,
                tolerance=0.0,
                role="custom",
            )
        )
        self._mark_dirty("Added custom path item.")

    @pyqtSlot(str, str, str, bool)
    @pyqtSlot(str, str, str, str, bool)
    def updatePathItem(
        self,
        item_id: str,
        nominal: str,
        tolerance_minus: str,
        tolerance_plus_or_include: str | bool,
        include_in_stackup: bool | None = None,
    ) -> None:
        selected = self._selected_pair()
        if selected is None:
            return
        _, sub_joint = selected
        item = next(
            (candidate for candidate in sub_joint.stackup_path.items if candidate.id == item_id),
            None,
        )
        if item is None:
            return
        if item.source_type == "flange":
            self._set_status("Edit linked flange values in the joint setup table.")
            return
        tolerance_plus = (
            None if include_in_stackup is None else str(tolerance_plus_or_include)
        )
        include = (
            bool(tolerance_plus_or_include)
            if include_in_stackup is None
            else include_in_stackup
        )
        try:
            nominal_value, minus_value, plus_value = _parse_tolerance_inputs(
                item.name,
                nominal,
                tolerance_minus,
                tolerance_plus,
            )
        except ValueError:
            self._set_status(f"{item.name}: thickness and tolerance must be numeric.")
            return
        if minus_value < 0.0 or plus_value < 0.0:
            self._set_status(f"{item.name}: tolerance must be non-negative.")
            return
        item.nominal_thickness = nominal_value
        item.tolerance_minus = minus_value
        item.tolerance_plus = plus_value
        item.tolerance = max(minus_value, plus_value)
        item.include_in_stackup = include
        self._mark_dirty(f"{item.name} updated.")

    @pyqtSlot(bool, str, str)
    def updateMonteCarloSettings(self, enabled: bool, samples: str, seed: str) -> None:
        selected = self._selected_pair()
        if selected is None:
            return
        _, sub_joint = selected
        try:
            sample_count = int(samples)
            seed_value = int(seed)
        except ValueError:
            self._set_status("Monte Carlo samples and seed must be integers.")
            return
        if sample_count < 100 or sample_count > 100000:
            self._set_status("Monte Carlo sample count must be between 100 and 100000.")
            return
        settings = sub_joint.stackup_path.method_settings
        settings.monte_carlo_enabled = bool(enabled)
        settings.monte_carlo_sample_count = sample_count
        settings.monte_carlo_seed = seed_value
        self._mark_dirty("Monte Carlo settings updated.")

    @pyqtSlot(str)
    def removePathItem(self, item_id: str) -> None:
        selected = self._selected_pair()
        if selected is None:
            return
        _, sub_joint = selected
        before = len(sub_joint.stackup_path.items)
        sub_joint.stackup_path.items = [
            item
            for item in sub_joint.stackup_path.items
            if item.id != item_id or item.source_type == "flange"
        ]
        if len(sub_joint.stackup_path.items) == before:
            self._set_status("Linked flange items cannot be removed from the path.")
            return
        self._mark_dirty("Removed path item.")

    @pyqtSlot()
    def applyRecommendedLength(self) -> None:
        selected = self._selected_pair()
        result = self._selected_result()
        if selected is None or result is None:
            return
        _, sub_joint = selected
        ranked = rank_bolt_lengths(sub_joint, result.stackup, self.catalog)
        if ranked.recommended_length is None:
            self._set_status("No passing bolt length candidate is available.")
            return
        sub_joint.selected_bolt_length = ranked.recommended_length
        self._mark_dirty(f"Applied recommended length {ranked.recommended_length:g}.")

    @pyqtSlot()
    def newProject(self) -> None:
        self.project = create_default_project()
        self.project_path = None
        self.dirty = False
        first_joint = self.project.joints[0]
        self.selected_joint_id = first_joint.id
        self.selected_sub_joint_id = first_joint.sub_joints[0].id
        self.status_text = "Started a new tolerance project."
        self._emit_all()

    @pyqtSlot()
    def saveProject(self) -> None:
        if self.project_path is None:
            self.saveProjectAs()
            return
        self.saveProjectTo(str(self.project_path))

    @pyqtSlot()
    def saveProjectAs(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            None,
            "Save tolerance project",
            str(Path.home() / "tolerance_project.tolproj"),
            "Tolerance project (*.tolproj)",
        )
        if path:
            self.saveProjectTo(path)

    @pyqtSlot(str)
    def saveProjectTo(self, path: str) -> None:
        self.project_path = save_project(self.project, path)
        self.dirty = False
        self.status_text = f"Saved {self.project_path.name}."
        self._emit_all()

    @pyqtSlot()
    def openProject(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            None,
            "Open tolerance project",
            str(Path.home()),
            "Tolerance project (*.tolproj)",
        )
        if path:
            self.openProjectFrom(path)

    @pyqtSlot(str)
    def openProjectFrom(self, path: str) -> None:
        self.project = load_project(path)
        self.project_path = Path(path)
        self.dirty = False
        self._ensure_selection_valid()
        self.status_text = f"Opened {self.project_path.name}."
        self._emit_all()

    @pyqtSlot()
    def importSpreadsheet(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            None,
            "Import tolerance stackup table",
            str(Path.home()),
            "Stackup table (*.csv *.xlsx)",
        )
        if path:
            self.importSpreadsheetFrom(path)

    @pyqtSlot(str)
    def importSpreadsheetFrom(self, path: str) -> None:
        try:
            self.project = load_spreadsheet_project(path, self.catalog)
        except (OSError, ValueError) as exc:
            self._set_status(f"Could not import stackup table: {exc}")
            return
        self.project_path = None
        self.dirty = True
        first_joint = self.project.joints[0]
        self.selected_joint_id = first_joint.id
        self.selected_sub_joint_id = first_joint.sub_joints[0].id
        self._ensure_selection_valid()
        self.status_text = f"Imported {Path(path).name}."
        self._emit_all()

    @pyqtSlot()
    def exportCsv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            None,
            "Export tolerance summary",
            str(Path.home() / "tolerance_summary.csv"),
            "CSV table (*.csv)",
        )
        if path:
            self.exportCsvTo(path)

    @pyqtSlot(str)
    def exportCsvTo(self, path: str) -> None:
        output_path = Path(path)
        if output_path.suffix.lower() != ".csv":
            output_path = output_path.with_suffix(".csv")
        with output_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=[
                    "joint",
                    "sub_joint",
                    "bolt",
                    "length",
                    "worst_case",
                    "worst_case_minus",
                    "worst_case_plus",
                    "rss",
                    "rss_minus",
                    "rss_plus",
                    "one_point_five_rss",
                    "mc_mean",
                    "mc_p00135",
                    "mc_p99865",
                    "top_four",
                    "status",
                ],
            )
            writer.writeheader()
            writer.writerows(self.summaryRows)
        self.status_text = f"Exported {output_path.name}."
        self.statusChanged.emit()

    @pyqtSlot()
    def exportPng(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            None,
            "Export workspace image",
            str(Path.home() / "tolerance_workspace.png"),
            "PNG image (*.png)",
        )
        if path:
            self.exportPngTo(path)

    @pyqtSlot(str)
    def exportPngTo(self, path: str) -> None:
        if self.window is None:
            self._set_status("Workspace window is not available for PNG export.")
            return
        output_path = Path(path)
        if output_path.suffix.lower() != ".png":
            output_path = output_path.with_suffix(".png")
        image = self._grab_window_image()
        if image.isNull() or not image.save(str(output_path), "PNG"):
            self._set_status("Could not export PNG image.")
            return
        self.status_text = f"Exported {output_path.name}."
        self.statusChanged.emit()

    @pyqtSlot()
    def exportPdf(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            None,
            "Export workspace PDF",
            str(Path.home() / "tolerance_workspace.pdf"),
            "PDF document (*.pdf)",
        )
        if path:
            self.exportPdfTo(path)

    @pyqtSlot(str)
    def exportPdfTo(self, path: str) -> None:
        if self.window is None:
            self._set_status("Workspace window is not available for PDF export.")
            return
        output_path = Path(path)
        if output_path.suffix.lower() != ".pdf":
            output_path = output_path.with_suffix(".pdf")
        image = self._grab_window_image()
        if image.isNull():
            self._set_status("Could not capture workspace for PDF export.")
            return
        writer = QPdfWriter(str(output_path))
        writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        writer.setPageOrientation(QPageLayout.Orientation.Landscape)
        painter = QPainter(writer)
        page = writer.pageLayout().paintRectPixels(writer.resolution())
        scaled = image.scaled(
            page.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = page.x() + (page.width() - scaled.width()) // 2
        y = page.y() + (page.height() - scaled.height()) // 2
        painter.drawImage(x, y, scaled)
        painter.end()
        self.status_text = f"Exported {output_path.name}."
        self.statusChanged.emit()

    def _grab_window_image(self) -> QImage:
        if self.window is None:
            return QImage()
        screen = self.window.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            return QImage()
        pixmap = screen.grabWindow(int(self.window.winId()))
        return pixmap.toImage()

    def _selected_joint(self) -> Joint | None:
        return next(
            (joint for joint in self.project.joints if joint.id == self.selected_joint_id),
            None,
        )

    def _selected_pair(self) -> tuple[Joint, SubJoint] | None:
        joint = self._selected_joint()
        if joint is None:
            return None
        sub_joint = next(
            (
                item
                for item in joint.sub_joints
                if item.id == self.selected_sub_joint_id
            ),
            None,
        )
        if sub_joint is None:
            return None
        return joint, sub_joint

    def _selected_result(self) -> SubJointResult | None:
        selected = self._selected_pair()
        if selected is None:
            return None
        joint, sub_joint = selected
        return calculate_sub_joint_result(joint, sub_joint, self.catalog)

    def _ensure_selection_valid(self) -> None:
        if not self.project.joints:
            self.project.joints.append(create_default_joint("JOINT A", sample_values=True))
        joint = self._selected_joint() or self.project.joints[0]
        self.selected_joint_id = joint.id
        if not joint.sub_joints:
            sub_joint = SubJoint(name=f"{joint.name}.1")
            joint.sub_joints.append(sub_joint)
            sync_path_with_flanges(joint, sub_joint)
        if not any(item.id == self.selected_sub_joint_id for item in joint.sub_joints):
            self.selected_sub_joint_id = joint.sub_joints[0].id
        for sub_joint in joint.sub_joints:
            sync_path_with_flanges(joint, sub_joint)
            self._ensure_default_engagement(sub_joint)

    def _ensure_default_engagement(self, sub_joint: SubJoint) -> None:
        part_type = sub_joint.stackup_path.engagement_type or "nut"
        current = self.catalog.find_hardware(
            sub_joint.stackup_path.selected_engagement_part_id
        )
        if current and sub_joint.bolt_size_id in current.compatible_bolt_sizes:
            return
        default = self.catalog.default_hardware(part_type, sub_joint.bolt_size_id)
        sub_joint.stackup_path.selected_engagement_part_id = default.id if default else ""

    def _joint_to_ui(self, joint: Joint) -> dict[str, Any]:
        return {
            "id": joint.id,
            "name": joint.name,
            "selected": joint.id == self.selected_joint_id,
            "sub_joints": [self._sub_joint_to_ui(item) for item in joint.sub_joints],
        }

    def _sub_joint_to_ui(self, sub_joint: SubJoint) -> dict[str, Any]:
        settings = sub_joint.stackup_path.method_settings
        return {
            "id": sub_joint.id,
            "name": sub_joint.name,
            "bolt_size": sub_joint.bolt_size_id,
            "bolt_type": sub_joint.bolt_type_id,
            "bolt_length": _format_number(sub_joint.selected_bolt_length),
            "engagement_type": sub_joint.stackup_path.engagement_type,
            "engagement_part_id": sub_joint.stackup_path.selected_engagement_part_id,
            "monte_carlo_enabled": settings.monte_carlo_enabled,
            "monte_carlo_sample_count": str(settings.monte_carlo_sample_count),
            "monte_carlo_seed": str(settings.monte_carlo_seed),
            "selected": sub_joint.id == self.selected_sub_joint_id,
        }

    def _flange_to_ui(self, flange: Flange) -> dict[str, Any]:
        return {
            "id": flange.id,
            "name": flange.name,
            "nominal": _format_number(flange.nominal_thickness),
            "tolerance": _format_number(flange.tolerance),
            "tolerance_minus": _format_number(float(flange.tolerance_minus or 0.0)),
            "tolerance_plus": _format_number(float(flange.tolerance_plus or 0.0)),
        }

    def _path_item_to_ui(self, item: PathItem) -> dict[str, Any]:
        return {
            "id": item.id,
            "name": item.name,
            "role": item.role,
            "source_type": item.source_type,
            "source_label": item.source_type.title(),
            "nominal": _format_number(item.nominal_thickness),
            "tolerance": _format_number(item.tolerance),
            "tolerance_minus": _format_number(float(item.tolerance_minus or 0.0)),
            "tolerance_plus": _format_number(float(item.tolerance_plus or 0.0)),
            "include": item.include_in_stackup,
            "locked": item.source_type == "flange",
        }

    def _hardware_to_ui(self, item: HardwareCatalogRecord) -> dict[str, Any]:
        return {
            "id": item.id,
            "display_name": item.display_name,
            "part_type": item.part_type,
            "nominal": _format_number(item.nominal_thickness),
            "tolerance": _format_number(item.tolerance),
        }

    def _candidate_to_ui(self, item, recommended: bool) -> dict[str, Any]:
        return {
            "length": _format_number(item.length),
            "status": item.status,
            "protrusion": _format_optional(item.protrusion),
            "engagement": _format_optional(item.engagement),
            "message": item.controlling_message,
            "recommended": recommended,
        }

    def _mark_dirty(self, message: str) -> None:
        self.dirty = True
        self.status_text = message
        self._emit_all()

    def _set_status(self, message: str) -> None:
        self.status_text = message
        self.statusChanged.emit()

    def _persist_theme_preferences(self) -> None:
        try:
            _save_theme_preferences(
                {
                    "quick_style": self.preferred_quick_style,
                    "material_theme": self.preferred_material_theme,
                },
                self.preferences_path,
            )
        except OSError as exc:
            self.themeChanged.emit()
            self._set_status(f"Could not save UI style preference: {exc}")
            return
        self.themeChanged.emit()
        self._set_status(self.themeHint)

    def _emit_all(self) -> None:
        self.projectChanged.emit()
        self.selectedChanged.emit()
        self.statusChanged.emit()
        self.themeChanged.emit()


def _criterion_cell(criterion) -> str:
    if criterion is None:
        return "-"
    return f"{criterion.status} ({_format_optional(criterion.margin)})"


def _format_number(value: float) -> str:
    return f"{float(value):.4f}".rstrip("0").rstrip(".")


def _format_optional(value: float | None) -> str:
    return "-" if value is None else _format_number(value)


def _parse_tolerance_inputs(
    label: str,
    nominal: str,
    tolerance_minus: str,
    tolerance_plus: str | None,
) -> tuple[float, float, float]:
    try:
        nominal_value = float(nominal)
        minus_value = float(tolerance_minus)
        plus_value = minus_value if tolerance_plus is None else float(tolerance_plus)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}: thickness and tolerance must be numeric.") from exc
    if (
        not math.isfinite(nominal_value)
        or not math.isfinite(minus_value)
        or not math.isfinite(plus_value)
    ):
        raise ValueError(f"{label}: thickness and tolerance must be finite.")
    return nominal_value, minus_value, plus_value


def _monte_carlo_to_ui(result) -> dict[str, Any]:
    if result is None:
        return {
            "enabled": False,
            "sample_count": "",
            "seed": "",
            "mean": "-",
            "std_deviation": "-",
            "minimum": "-",
            "p00135": "-",
            "p50": "-",
            "p99865": "-",
            "maximum": "-",
        }
    return {
        "enabled": True,
        "sample_count": str(result.sample_count),
        "seed": str(result.seed),
        "mean": _format_number(result.mean),
        "std_deviation": _format_number(result.std_deviation),
        "minimum": _format_number(result.minimum),
        "p00135": _format_number(result.p00135),
        "p50": _format_number(result.p50),
        "p99865": _format_number(result.p99865),
        "maximum": _format_number(result.maximum),
    }


def _match_choice(value: str | None, choices: tuple[str, ...]) -> str | None:
    if value is None:
        return None
    value_text = str(value).strip()
    for choice in choices:
        if value_text.lower() == choice.lower():
            return choice
    return None


def _theme_preferences_path() -> Path:
    override = os.environ.get(PREFERENCES_ENV_VAR)
    if override:
        return Path(override)
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "BoltCalculationTool" / "tolerance_vnext_ui.json"
    return Path.home() / ".bolt_calculation_tool" / "tolerance_vnext_ui.json"


def _load_theme_preferences(path: Path | str | None = None) -> dict[str, str]:
    preferences_path = Path(path) if path is not None else _theme_preferences_path()
    try:
        raw = json.loads(preferences_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    preferences: dict[str, str] = {}
    quick_style = _match_choice(raw.get("quick_style"), QUICK_STYLE_OPTIONS)
    material_theme = _match_choice(raw.get("material_theme"), MATERIAL_THEME_OPTIONS)
    if quick_style is not None:
        preferences["quick_style"] = quick_style
    if material_theme is not None:
        preferences["material_theme"] = material_theme
    return preferences


def _save_theme_preferences(preferences: dict[str, str], path: Path | str | None = None) -> None:
    output_path = Path(path) if path is not None else _theme_preferences_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(preferences, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch the tolerance vNext GUI.")
    parser.add_argument(
        "--quick-style",
        choices=QUICK_STYLE_OPTIONS,
        default=None,
        help=(
            "Qt Quick Controls style. Fusion is the default; Material and "
            "Universal provide more modern looks when available. If omitted, "
            "the saved UI preference is used."
        ),
    )
    parser.add_argument(
        "--material-theme",
        choices=MATERIAL_THEME_OPTIONS,
        default=None,
        help="Theme used by the Material style. If omitted, the saved UI preference is used.",
    )
    return parser.parse_args(argv)


def _resolve_style_args(args: argparse.Namespace) -> argparse.Namespace:
    preferences = _load_theme_preferences()
    args.quick_style = (
        args.quick_style
        or _match_choice(os.environ.get("TOLERANCE_VNEXT_QUICK_STYLE"), QUICK_STYLE_OPTIONS)
        or preferences.get("quick_style")
        or DEFAULT_QUICK_STYLE
    )
    args.material_theme = (
        args.material_theme
        or _match_choice(
            os.environ.get("QT_QUICK_CONTROLS_MATERIAL_THEME"),
            MATERIAL_THEME_OPTIONS,
        )
        or preferences.get("material_theme")
        or DEFAULT_MATERIAL_THEME
    )
    return args


def _configure_quick_style(args: argparse.Namespace) -> None:
    os.environ["QT_QUICK_CONTROLS_STYLE"] = args.quick_style
    os.environ["QT_QUICK_CONTROLS_MATERIAL_THEME"] = args.material_theme
    os.environ.setdefault("QT_QUICK_CONTROLS_MATERIAL_ACCENT", "Blue")
    os.environ.setdefault("QT_QUICK_CONTROLS_UNIVERSAL_THEME", "Light")
    os.environ.setdefault("QT_QUICK_CONTROLS_UNIVERSAL_ACCENT", "Cobalt")


def main() -> None:
    args = _resolve_style_args(_parse_args(sys.argv[1:]))
    _configure_quick_style(args)
    app = QApplication([sys.argv[0]])
    app.setApplicationName("Tolerance Tool vNext")
    backend = ToleranceVNextBackend(
        quick_style=args.quick_style,
        material_theme=args.material_theme,
    )
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)
    qml_path = Path(__file__).resolve().parent / "qml" / "tolerance_vnext.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        raise SystemExit(1)
    backend.window = engine.rootObjects()[0]
    backend.refresh()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
