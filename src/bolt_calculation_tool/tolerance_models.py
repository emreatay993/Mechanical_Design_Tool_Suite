"""Domain models for the next-version tolerance workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


SCHEMA_VERSION = 1
DEFAULT_UNIT_SYSTEM = "mm"
DEFAULT_SIGMA_COVERAGE = 3.0


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


@dataclass
class MethodSettings:
    sigma_coverage: float = DEFAULT_SIGMA_COVERAGE

    def to_dict(self) -> dict[str, Any]:
        return {"sigma_coverage": self.sigma_coverage}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "MethodSettings":
        if not data:
            return cls()
        return cls(sigma_coverage=float(data.get("sigma_coverage", DEFAULT_SIGMA_COVERAGE)))


@dataclass
class Flange:
    name: str
    nominal_thickness: float
    tolerance: float
    id: str = field(default_factory=lambda: new_id("flange"))
    material_or_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "nominal_thickness": self.nominal_thickness,
            "tolerance": self.tolerance,
            "material_or_note": self.material_or_note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Flange":
        return cls(
            id=str(data.get("id") or new_id("flange")),
            name=str(data.get("name") or "Flange"),
            nominal_thickness=float(data.get("nominal_thickness", 0.0)),
            tolerance=float(data.get("tolerance", 0.0)),
            material_or_note=str(data.get("material_or_note", "")),
        )


@dataclass
class PathItem:
    name: str
    nominal_thickness: float
    tolerance: float
    source_type: str = "custom"
    source_id: str = ""
    role: str = "custom"
    include_in_stackup: bool = True
    id: str = field(default_factory=lambda: new_id("item"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "name": self.name,
            "nominal_thickness": self.nominal_thickness,
            "tolerance": self.tolerance,
            "role": self.role,
            "include_in_stackup": self.include_in_stackup,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PathItem":
        return cls(
            id=str(data.get("id") or new_id("item")),
            source_type=str(data.get("source_type", "custom")),
            source_id=str(data.get("source_id", "")),
            name=str(data.get("name") or "Path item"),
            nominal_thickness=float(data.get("nominal_thickness", 0.0)),
            tolerance=float(data.get("tolerance", 0.0)),
            role=str(data.get("role", "custom")),
            include_in_stackup=bool(data.get("include_in_stackup", True)),
        )


@dataclass
class StackupPath:
    items: list[PathItem] = field(default_factory=list)
    engagement_type: str = "nut"
    selected_engagement_part_id: str = "nut_0190_standard"
    id: str = field(default_factory=lambda: new_id("path"))
    method_settings: MethodSettings = field(default_factory=MethodSettings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "items": [item.to_dict() for item in self.items],
            "engagement_type": self.engagement_type,
            "selected_engagement_part_id": self.selected_engagement_part_id,
            "method_settings": self.method_settings.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "StackupPath":
        if not data:
            return cls()
        return cls(
            id=str(data.get("id") or new_id("path")),
            items=[PathItem.from_dict(item) for item in data.get("items", [])],
            engagement_type=str(data.get("engagement_type", "nut")),
            selected_engagement_part_id=str(
                data.get("selected_engagement_part_id", "nut_0190_standard")
            ),
            method_settings=MethodSettings.from_dict(data.get("method_settings")),
        )


@dataclass
class SubJoint:
    name: str
    bolt_size_id: str = "0.190"
    bolt_type_id: str = "PD Shank"
    selected_bolt_length: float = 17.5
    stackup_path: StackupPath = field(default_factory=StackupPath)
    id: str = field(default_factory=lambda: new_id("subjoint"))
    result_snapshot: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "bolt_size_id": self.bolt_size_id,
            "bolt_type_id": self.bolt_type_id,
            "selected_bolt_length": self.selected_bolt_length,
            "stackup_path": self.stackup_path.to_dict(),
            "result_snapshot": self.result_snapshot,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SubJoint":
        return cls(
            id=str(data.get("id") or new_id("subjoint")),
            name=str(data.get("name") or "Sub-joint"),
            bolt_size_id=str(data.get("bolt_size_id", "0.190")),
            bolt_type_id=str(data.get("bolt_type_id", "PD Shank")),
            selected_bolt_length=float(data.get("selected_bolt_length", 17.5)),
            stackup_path=StackupPath.from_dict(data.get("stackup_path")),
            result_snapshot=dict(data.get("result_snapshot", {})),
        )


@dataclass
class Joint:
    name: str
    flanges: list[Flange] = field(default_factory=list)
    sub_joints: list[SubJoint] = field(default_factory=list)
    id: str = field(default_factory=lambda: new_id("joint"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "flanges": [flange.to_dict() for flange in self.flanges],
            "sub_joints": [sub_joint.to_dict() for sub_joint in self.sub_joints],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Joint":
        return cls(
            id=str(data.get("id") or new_id("joint")),
            name=str(data.get("name") or "JOINT"),
            flanges=[Flange.from_dict(item) for item in data.get("flanges", [])],
            sub_joints=[
                SubJoint.from_dict(item) for item in data.get("sub_joints", [])
            ],
        )


@dataclass
class ToleranceProject:
    title: str = "Tolerance Project"
    unit_system: str = DEFAULT_UNIT_SYSTEM
    joints: list[Joint] = field(default_factory=list)
    catalog_references: list[str] = field(default_factory=list)
    method_settings: MethodSettings = field(default_factory=MethodSettings)
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "title": self.title,
            "unit_system": self.unit_system,
            "method_settings": self.method_settings.to_dict(),
            "joints": [joint.to_dict() for joint in self.joints],
            "catalog_references": list(self.catalog_references),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToleranceProject":
        version = int(data.get("schema_version", 0))
        if version != SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported tolerance project schema version {version}; "
                f"expected {SCHEMA_VERSION}."
            )
        return cls(
            schema_version=version,
            title=str(data.get("title") or "Tolerance Project"),
            unit_system=str(data.get("unit_system") or DEFAULT_UNIT_SYSTEM),
            method_settings=MethodSettings.from_dict(data.get("method_settings")),
            joints=[Joint.from_dict(item) for item in data.get("joints", [])],
            catalog_references=[str(item) for item in data.get("catalog_references", [])],
        )


def create_flange_path_item(flange: Flange) -> PathItem:
    return PathItem(
        source_type="flange",
        source_id=flange.id,
        name=flange.name,
        nominal_thickness=flange.nominal_thickness,
        tolerance=flange.tolerance,
        role="flange",
    )


def sync_path_with_flanges(joint: Joint, sub_joint: SubJoint) -> None:
    path = sub_joint.stackup_path
    existing_by_source = {
        item.source_id: item
        for item in path.items
        if item.source_type == "flange" and item.source_id
    }
    synced_items: list[PathItem] = []
    for flange in joint.flanges:
        item = existing_by_source.get(flange.id)
        if item is None:
            item = create_flange_path_item(flange)
        else:
            item.name = flange.name
            item.nominal_thickness = flange.nominal_thickness
            item.tolerance = flange.tolerance
        synced_items.append(item)
    synced_items.extend(item for item in path.items if item.source_type != "flange")
    path.items = synced_items


def create_default_joint(name: str = "JOINT A", sample_values: bool = False) -> Joint:
    if sample_values:
        flange_specs = [
            ("Flange 1", 5.0, 0.15),
            ("Flange 2", 4.0, 0.25),
            ("Flange 3", 3.0, 0.20),
        ]
    else:
        flange_specs = [
            ("Flange 1", 0.0, 0.0),
            ("Flange 2", 0.0, 0.0),
            ("Flange 3", 0.0, 0.0),
        ]
    joint = Joint(
        name=name,
        flanges=[
            Flange(name=flange_name, nominal_thickness=nominal, tolerance=tolerance)
            for flange_name, nominal, tolerance in flange_specs
        ],
    )
    sub_joint = SubJoint(name=f"{name}.1")
    joint.sub_joints.append(sub_joint)
    sync_path_with_flanges(joint, sub_joint)
    return joint


def create_default_project() -> ToleranceProject:
    return ToleranceProject(
        title="Bracket Assembly Tolerance Review",
        joints=[create_default_joint("JOINT A", sample_values=True)],
        catalog_references=["builtin:tolerance_sample_catalog"],
    )


def next_joint_name(existing_count: int) -> str:
    index = existing_count
    letters = ""
    while True:
        letters = chr(ord("A") + index % 26) + letters
        index = index // 26 - 1
        if index < 0:
            break
    return f"JOINT {letters}"
