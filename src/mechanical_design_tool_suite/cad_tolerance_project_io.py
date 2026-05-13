"""Save/load helpers for CAD 1D tolerance project files."""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
from typing import Any

from .cad_tolerance_models import CadToleranceProject, PROJECT_TYPE, SCHEMA_VERSION


PROJECT_SUFFIX = ".tolproj"
CURRENT_SCHEMA_VERSION = SCHEMA_VERSION
MIN_SCHEMA_VERSION = 1


def save_project(project: CadToleranceProject, path: str | Path) -> Path:
    data = project.to_dict()
    if data.get("project_type") != PROJECT_TYPE:
        raise ValueError(
            f"CAD tolerance project type must be {PROJECT_TYPE!r}; "
            f"got {data.get('project_type')!r}."
        )
    data["schema_version"] = CURRENT_SCHEMA_VERSION

    output_path = Path(path)
    if output_path.suffix.lower() != PROJECT_SUFFIX:
        output_path = output_path.with_suffix(PROJECT_SUFFIX)
    output_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return output_path


def load_project(path: str | Path) -> CadToleranceProject:
    input_path = Path(path)
    data = json.loads(input_path.read_text(encoding="utf-8"))
    migrated = migrate_project_data(data)
    return CadToleranceProject.from_dict(migrated)


def migrate_project_data(data: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(data, Mapping):
        raise ValueError("CAD tolerance project file must contain a JSON object.")

    migrated = dict(data)
    _validate_project_type(migrated)
    schema_version = _schema_version(migrated)
    if schema_version > CURRENT_SCHEMA_VERSION:
        raise ValueError(
            "Unsupported CAD tolerance project schema_version "
            f"{schema_version}; latest supported is {CURRENT_SCHEMA_VERSION}."
        )
    if schema_version < MIN_SCHEMA_VERSION:
        raise ValueError(
            "Unsupported CAD tolerance project schema_version "
            f"{schema_version}; minimum supported is {MIN_SCHEMA_VERSION}."
        )

    while schema_version < CURRENT_SCHEMA_VERSION:
        if schema_version == 1:
            migrated = _migrate_v1_to_v2(migrated)
            schema_version = 2
            continue
        raise ValueError(
            "Unsupported CAD tolerance project schema_version "
            f"{schema_version}; latest supported is {CURRENT_SCHEMA_VERSION}."
        )

    return migrated


def _validate_project_type(data: Mapping[str, Any]) -> None:
    project_type = data.get("project_type")
    if project_type != PROJECT_TYPE:
        raise ValueError(
            f"CAD tolerance project_type must be {PROJECT_TYPE!r}; "
            f"got {project_type!r}."
        )


def _schema_version(data: Mapping[str, Any]) -> int:
    if "schema_version" not in data:
        raise ValueError("CAD tolerance project file is missing schema_version.")
    try:
        return int(data["schema_version"])
    except (TypeError, ValueError) as exc:
        raise ValueError("CAD tolerance project schema_version must be an integer.") from exc


def _migrate_v1_to_v2(data: Mapping[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    if "unit_system" not in migrated and "units" in migrated:
        migrated["unit_system"] = migrated["units"]
    migrated.setdefault("cad_documents", [])
    migrated.setdefault("stackups", [])
    migrated.setdefault("settings", {})
    migrated.setdefault("snapshots", [])
    migrated.setdefault("reports", [])
    migrated["schema_version"] = 2
    return migrated
