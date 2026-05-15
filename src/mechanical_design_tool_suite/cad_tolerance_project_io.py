"""Save/load helpers for CAD 1D tolerance project files."""

from __future__ import annotations

from collections.abc import Mapping
import copy
import hashlib
import json
import posixpath
from pathlib import Path
from typing import Any
import zipfile

from .cad_tolerance_models import CadToleranceProject, PROJECT_TYPE, SCHEMA_VERSION


PROJECT_SUFFIX = ".tolproj"
PACKAGE_SUFFIX = ".tolpack"
PACKAGE_FORMAT_VERSION = 1
PACKAGE_PROJECT_NAME = "project.tolproj"
PACKAGE_MANIFEST_NAME = "manifest.json"
PACKAGE_ASSET_ROOT = "assets"
PACKAGE_CREATED_AT = "1980-01-01T00:00:00Z"
CURRENT_SCHEMA_VERSION = SCHEMA_VERSION
MIN_SCHEMA_VERSION = 1
_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


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


def project_asset_dir(project_path: str | Path) -> Path:
    """Return the default managed asset directory beside a `.tolproj` file."""

    path = Path(project_path)
    return path.with_name(f"{path.stem}_assets")


def resolve_project_asset_path(
    reference: str | Path,
    project_path: str | Path,
    extra_roots: list[str | Path] | tuple[str | Path, ...] = (),
) -> Path | None:
    """Resolve a persisted project asset path against portable project locations."""

    if not str(reference):
        return None

    raw_path = Path(reference)
    if raw_path.is_absolute():
        return raw_path.resolve() if raw_path.exists() else None

    project_file = Path(project_path).resolve()
    project_dir = project_file.parent
    asset_dir = project_asset_dir(project_file)
    candidates: list[Path] = [
        project_dir / raw_path,
        asset_dir / raw_path,
        project_dir / PACKAGE_ASSET_ROOT / raw_path,
    ]

    if len(raw_path.parts) == 1:
        candidates.extend(
            [
                asset_dir / "cad" / raw_path.name,
                asset_dir / "snapshots" / raw_path.name,
                asset_dir / "reports" / raw_path.name,
                project_dir / PACKAGE_ASSET_ROOT / "cad" / raw_path.name,
                project_dir / PACKAGE_ASSET_ROOT / "snapshots" / raw_path.name,
                project_dir / PACKAGE_ASSET_ROOT / "reports" / raw_path.name,
            ]
        )

    for root in extra_roots:
        candidates.append(Path(root) / raw_path)
    for root in (project_dir, *project_dir.parents):
        candidates.append(root / raw_path)

    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.exists():
            return resolved
    return None


def project_relative_path(path: str | Path, project_path: str | Path) -> str:
    """Return a POSIX project-relative path when the asset is beside the project."""

    resolved = Path(path).resolve()
    project_dir = Path(project_path).resolve().parent
    try:
        return resolved.relative_to(project_dir).as_posix()
    except ValueError:
        return str(Path(path))


def export_project_package(
    project_path: str | Path,
    package_path: str | Path,
) -> Path:
    """Export a `.tolproj` plus managed assets as a deterministic `.tolpack`."""

    source_project_path = Path(project_path).resolve()
    package_file = Path(package_path)
    if package_file.suffix.lower() != PACKAGE_SUFFIX:
        package_file = package_file.with_suffix(PACKAGE_SUFFIX)
    package_file.parent.mkdir(parents=True, exist_ok=True)

    project = copy.deepcopy(load_project(source_project_path))
    asset_records: list[dict[str, Any]] = []
    archive_paths_by_source: dict[Path, str] = {}
    used_archive_paths: set[str] = set()

    def package_asset(
        kind: str,
        reference: str,
        subdir: str,
        *,
        preserve_report_layout: bool = False,
    ) -> str:
        resolved = resolve_project_asset_path(reference, source_project_path)
        if resolved is None or not resolved.is_file():
            raise FileNotFoundError(f"Project asset not found: {reference}")
        archive_path = archive_paths_by_source.get(resolved)
        if archive_path is None:
            if preserve_report_layout:
                archive_path = _report_asset_archive_path(
                    reference,
                    resolved,
                    source_project_path,
                    used_archive_paths,
                )
            else:
                archive_path = _unique_asset_archive_path(
                    resolved,
                    subdir,
                    used_archive_paths,
                )
            archive_paths_by_source[resolved] = archive_path
            used_archive_paths.add(archive_path)
            asset_records.append(
                {
                    "path": archive_path,
                    "kind": kind,
                    "sha256": f"sha256:{_sha256_file(resolved)}",
                    "size": resolved.stat().st_size,
                    "original_path": _portable_original_path(
                        reference,
                        resolved,
                        source_project_path,
                    ),
                }
            )
        return archive_path

    for document in project.cad_documents:
        if document.source_path:
            document.source_path = package_asset("cad", document.source_path, "cad")
    for snapshot in project.snapshots:
        if snapshot.image_path:
            snapshot.image_path = package_asset(
                "snapshot",
                snapshot.image_path,
                "snapshots",
            )
    for report in project.reports:
        for key in (
            "path",
            "output_path",
            "html_path",
            "image_path",
            "manifest_path",
            "css_path",
            "js_path",
        ):
            value = report.get(key)
            if isinstance(value, str) and value:
                report[key] = package_asset(
                    "report",
                    value,
                    "reports",
                    preserve_report_layout=True,
                )
        for key in ("asset_paths", "assets"):
            values = report.get(key)
            if isinstance(values, list):
                packaged_values: list[Any] = []
                for value in values:
                    if isinstance(value, str) and value:
                        packaged_values.append(
                            package_asset(
                                "report",
                                value,
                                "reports",
                                preserve_report_layout=True,
                            )
                        )
                    else:
                        packaged_values.append(value)
                report[key] = packaged_values

    project_payload = _json_payload(project.to_dict())
    manifest = {
        "package_format": "mdts-cad-1d-tolerance",
        "package_format_version": PACKAGE_FORMAT_VERSION,
        "created_at": PACKAGE_CREATED_AT,
        "project_title": project.title,
        "project_file": PACKAGE_PROJECT_NAME,
        "project_schema_version": project.schema_version,
        "assets": sorted(asset_records, key=lambda item: item["path"]),
    }
    manifest_payload = _json_payload(manifest)

    with zipfile.ZipFile(package_file, "w") as archive:
        _write_zip_bytes(archive, PACKAGE_MANIFEST_NAME, manifest_payload)
        _write_zip_bytes(archive, PACKAGE_PROJECT_NAME, project_payload)
        for resolved, archive_path in sorted(
            archive_paths_by_source.items(),
            key=lambda item: item[1],
        ):
            _write_zip_bytes(archive, archive_path, resolved.read_bytes())
    return package_file


def import_project_package(
    package_path: str | Path,
    output_dir: str | Path,
) -> Path:
    """Unpack a `.tolpack` into a normal project folder and return its project file."""

    package_file = Path(package_path)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(package_file, "r") as archive:
        names = sorted(archive.namelist())
        if PACKAGE_MANIFEST_NAME not in names:
            raise ValueError("Tolerance package is missing manifest.json.")
        manifest = json.loads(archive.read(PACKAGE_MANIFEST_NAME).decode("utf-8"))
        project_name = str(manifest.get("project_file") or PACKAGE_PROJECT_NAME)
        _validate_archive_member(project_name)

        for name in names:
            _validate_archive_member(name)
            destination = target_dir / Path(*Path(name).parts)
            if name.endswith("/"):
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(name))

    project_file = target_dir / Path(*Path(project_name).parts)
    if not project_file.exists():
        raise ValueError(f"Tolerance package project file is missing: {project_name}")
    return project_file


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


def _json_payload(data: Mapping[str, Any]) -> bytes:
    return (json.dumps(data, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _write_zip_bytes(
    archive: zipfile.ZipFile,
    name: str,
    payload: bytes,
) -> None:
    info = zipfile.ZipInfo(name, date_time=_ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    archive.writestr(info, payload)


def _unique_asset_archive_path(
    source_path: Path,
    subdir: str,
    used_archive_paths: set[str],
) -> str:
    candidate = posixpath.join(PACKAGE_ASSET_ROOT, subdir, source_path.name)
    if candidate not in used_archive_paths:
        return candidate
    digest = _sha256_file(source_path)[:8]
    stem = source_path.stem
    suffix = source_path.suffix
    return posixpath.join(
        PACKAGE_ASSET_ROOT,
        subdir,
        f"{stem}-{digest}{suffix}",
    )


def _report_asset_archive_path(
    reference: str,
    resolved: Path,
    project_path: Path,
    used_archive_paths: set[str],
) -> str:
    report_relative = _report_asset_relative_path(reference, resolved, project_path)
    candidate = posixpath.join(PACKAGE_ASSET_ROOT, "reports", report_relative)
    _validate_archive_member(candidate)
    if candidate not in used_archive_paths:
        return candidate
    return _deduplicated_archive_path(candidate, resolved, used_archive_paths)


def _report_asset_relative_path(
    reference: str,
    resolved: Path,
    project_path: Path,
) -> str:
    reference_text = str(reference).replace("\\", "/")
    if not Path(reference).is_absolute():
        parts = [part for part in reference_text.split("/") if part]
        for index, part in enumerate(parts):
            if part == "reports" and index + 1 < len(parts):
                candidate = posixpath.join(*parts[index + 1 :])
                if _safe_relative_archive_path(candidate):
                    return candidate

    try:
        candidate = resolved.relative_to(project_asset_dir(project_path) / "reports").as_posix()
        if _safe_relative_archive_path(candidate):
            return candidate
    except ValueError:
        pass
    return resolved.name


def _safe_relative_archive_path(value: str) -> bool:
    if not value:
        return False
    if "\\" in value:
        return False
    parts = [part for part in value.split("/") if part]
    return bool(parts) and all(part not in {"..", "."} for part in parts)


def _deduplicated_archive_path(
    candidate: str,
    source_path: Path,
    used_archive_paths: set[str],
) -> str:
    directory, filename = posixpath.split(candidate)
    suffix = Path(filename).suffix
    stem = filename[: -len(suffix)] if suffix else filename
    digest = _sha256_file(source_path)[:8]
    deduped = posixpath.join(directory, f"{stem}-{digest}{suffix}")
    if deduped not in used_archive_paths:
        return deduped
    index = 2
    while True:
        deduped = posixpath.join(directory, f"{stem}-{digest}-{index}{suffix}")
        if deduped not in used_archive_paths:
            return deduped
        index += 1


def _portable_original_path(
    reference: str,
    resolved: Path,
    project_path: Path,
) -> str:
    if Path(reference).is_absolute():
        return resolved.name
    return project_relative_path(reference, project_path).replace("\\", "/")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_archive_member(name: str) -> None:
    path = Path(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Unsafe path in tolerance package: {name!r}")
    if "\\" in name:
        raise ValueError(f"Tolerance package paths must use POSIX separators: {name!r}")
