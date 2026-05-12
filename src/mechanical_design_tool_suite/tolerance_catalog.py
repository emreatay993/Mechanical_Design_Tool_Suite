"""Catalog loading and filtering for tolerance-tool standard parts."""

from __future__ import annotations

from dataclasses import dataclass
import json
from importlib import resources
from typing import Any


DEFAULT_CATALOG: dict[str, Any] = {
    "schema_version": 1,
    "bolts": [
        {
            "id": "bolt_0190_pd_shank",
            "size": "0.190",
            "type": "PD Shank",
            "display_name": "0.190 PD Shank",
            "pitch": 0.8,
            "chamfer_allowance": 0.4,
            "lengths": [14.0, 15.0, 16.0, 17.5, 18.0, 20.0, 22.0],
        },
        {
            "id": "bolt_0250_close_tol",
            "size": "0.250",
            "type": "Close Tolerance",
            "display_name": "0.250 Close Tolerance",
            "pitch": 1.0,
            "chamfer_allowance": 0.5,
            "lengths": [18.0, 20.0, 22.0, 24.0, 26.0, 28.0],
        },
    ],
    "hardware": [
        {
            "id": "nut_0190_standard",
            "part_type": "nut",
            "display_name": "0.190 Standard Nut",
            "compatible_bolt_sizes": ["0.190"],
            "nominal_thickness": 2.0,
            "tolerance": 0.05,
        },
        {
            "id": "nut_0250_standard",
            "part_type": "nut",
            "display_name": "0.250 Standard Nut",
            "compatible_bolt_sizes": ["0.250"],
            "nominal_thickness": 2.8,
            "tolerance": 0.06,
        },
        {
            "id": "insert_0190_light",
            "part_type": "insert",
            "display_name": "0.190 Light Insert",
            "compatible_bolt_sizes": ["0.190"],
            "nominal_thickness": 3.4,
            "tolerance": 0.08,
            "min_engagement": 3.2,
            "max_engagement": 6.0,
        },
        {
            "id": "bracket_std_100",
            "part_type": "bracket",
            "display_name": "Standard Bracket 1.00",
            "compatible_bolt_sizes": ["0.190", "0.250"],
            "nominal_thickness": 1.0,
            "tolerance": 0.10,
        },
        {
            "id": "washer_0190_thin",
            "part_type": "washer",
            "display_name": "0.190 Thin Washer",
            "compatible_bolt_sizes": ["0.190"],
            "nominal_thickness": 0.6,
            "tolerance": 0.03,
        },
    ],
}


@dataclass(frozen=True)
class BoltCatalogRecord:
    id: str
    size: str
    type: str
    display_name: str
    pitch: float
    chamfer_allowance: float
    lengths: tuple[float, ...]


@dataclass(frozen=True)
class HardwareCatalogRecord:
    id: str
    part_type: str
    display_name: str
    compatible_bolt_sizes: tuple[str, ...]
    nominal_thickness: float
    tolerance: float
    min_engagement: float | None = None
    max_engagement: float | None = None


class ToleranceCatalog:
    def __init__(
        self,
        bolts: list[BoltCatalogRecord],
        hardware: list[HardwareCatalogRecord],
    ) -> None:
        self.bolts = bolts
        self.hardware = hardware
        self._bolts_by_key = {(bolt.size, bolt.type): bolt for bolt in bolts}
        self._hardware_by_id = {item.id: item for item in hardware}

    @classmethod
    def builtin(cls) -> "ToleranceCatalog":
        try:
            catalog_text = (
                resources.files("mechanical_design_tool_suite")
                .joinpath("data/tolerance_catalog.json")
                .read_text(encoding="utf-8")
            )
            data = json.loads(catalog_text)
        except (FileNotFoundError, ModuleNotFoundError):
            data = DEFAULT_CATALOG
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToleranceCatalog":
        bolts = [_bolt_from_dict(item) for item in data.get("bolts", [])]
        hardware = [_hardware_from_dict(item) for item in data.get("hardware", [])]
        _validate_catalog(bolts, hardware)
        return cls(bolts=bolts, hardware=hardware)

    def bolt_sizes(self) -> list[str]:
        return sorted({bolt.size for bolt in self.bolts})

    def bolt_types_for_size(self, size: str) -> list[str]:
        return sorted({bolt.type for bolt in self.bolts if bolt.size == size})

    def lengths_for(self, size: str, bolt_type: str) -> list[float]:
        bolt = self.find_bolt(size, bolt_type)
        return list(bolt.lengths) if bolt else []

    def find_bolt(self, size: str, bolt_type: str) -> BoltCatalogRecord | None:
        return self._bolts_by_key.get((size, bolt_type))

    def hardware_by_type(
        self, part_type: str, bolt_size: str | None = None
    ) -> list[HardwareCatalogRecord]:
        items = [item for item in self.hardware if item.part_type == part_type]
        if bolt_size:
            items = [
                item for item in items if bolt_size in item.compatible_bolt_sizes
            ]
        return items

    def find_hardware(self, item_id: str) -> HardwareCatalogRecord | None:
        return self._hardware_by_id.get(item_id)

    def default_hardware(self, part_type: str, bolt_size: str) -> HardwareCatalogRecord | None:
        items = self.hardware_by_type(part_type, bolt_size)
        return items[0] if items else None


def _bolt_from_dict(data: dict[str, Any]) -> BoltCatalogRecord:
    return BoltCatalogRecord(
        id=str(data["id"]),
        size=str(data["size"]),
        type=str(data["type"]),
        display_name=str(data.get("display_name") or data["id"]),
        pitch=float(data["pitch"]),
        chamfer_allowance=float(data.get("chamfer_allowance", 0.0)),
        lengths=tuple(float(length) for length in data.get("lengths", [])),
    )


def _hardware_from_dict(data: dict[str, Any]) -> HardwareCatalogRecord:
    return HardwareCatalogRecord(
        id=str(data["id"]),
        part_type=str(data["part_type"]),
        display_name=str(data.get("display_name") or data["id"]),
        compatible_bolt_sizes=tuple(
            str(size) for size in data.get("compatible_bolt_sizes", [])
        ),
        nominal_thickness=float(data.get("nominal_thickness", 0.0)),
        tolerance=float(data.get("tolerance", 0.0)),
        min_engagement=_optional_float(data.get("min_engagement")),
        max_engagement=_optional_float(data.get("max_engagement")),
    )


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _validate_catalog(
    bolts: list[BoltCatalogRecord],
    hardware: list[HardwareCatalogRecord],
) -> None:
    bolt_ids: set[str] = set()
    bolt_keys: set[tuple[str, str]] = set()
    for bolt in bolts:
        if bolt.id in bolt_ids:
            raise ValueError(f"Duplicate bolt catalog id: {bolt.id}")
        bolt_ids.add(bolt.id)
        key = (bolt.size, bolt.type)
        if key in bolt_keys:
            raise ValueError(f"Duplicate bolt catalog key: {bolt.size} / {bolt.type}")
        bolt_keys.add(key)
        if bolt.pitch <= 0.0:
            raise ValueError(f"{bolt.display_name} pitch must be positive.")
        if not bolt.lengths:
            raise ValueError(f"{bolt.display_name} must define standard lengths.")

    hardware_ids: set[str] = set()
    for item in hardware:
        if item.id in hardware_ids:
            raise ValueError(f"Duplicate hardware catalog id: {item.id}")
        hardware_ids.add(item.id)
        if item.tolerance < 0.0:
            raise ValueError(f"{item.display_name} tolerance must be non-negative.")
