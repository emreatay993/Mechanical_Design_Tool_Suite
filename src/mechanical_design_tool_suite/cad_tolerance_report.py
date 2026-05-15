"""Deterministic dashboard projections and HTML reports for CAD stackups."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from html import escape
import json
from pathlib import Path
import shutil
from typing import Any

from .cad_tolerance_methods import calculate_stackup
from .cad_tolerance_models import (
    AnalysisMode,
    CadToleranceProject,
    NonOneDWarning,
    ObjectiveType,
    QualityMetric,
    ResultStatus,
    Snapshot,
    StackupContributor,
    StackupObjective,
    StackupRequirement,
    StackupResult,
    ToleranceType,
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

NON_1D_WARNING_TEXT = "Calculated results are ignoring potentially significant 3D effects"


@dataclass(frozen=True)
class DashboardProjectionRow:
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
class DashboardBadgesProjection:
    objectives_met: int = 0
    objectives_not_met: int = 0
    sigma_rollup: str = ""


@dataclass(frozen=True)
class WarningProjectionRow:
    warning_id: str
    message: str
    severity: ResultStatus
    feature_ids: tuple[str, ...] = ()
    observed_value: float | None = None
    threshold: float | None = None


@dataclass(frozen=True)
class DetailProjectionRow:
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


@dataclass(frozen=True)
class ContributionProjectionRow:
    label: str
    percent: float
    tolerance_box: str = ""
    datum: str = ""
    contributor_id: str = ""


@dataclass(frozen=True)
class ResultMarker:
    label: str
    value: float
    role: str


@dataclass(frozen=True)
class ResultDisplayProjection:
    stackup_id: str
    name: str
    mode_label: str
    title: str
    status: ResultStatus
    nominal_label: str
    objective_label: str
    result_label: str
    predicted_quality_label: str
    mean_label: str
    standard_deviation_label: str
    markers: tuple[ResultMarker, ...] = ()
    warnings: tuple[WarningProjectionRow, ...] = ()
    objective_lower: float | None = None
    objective_upper: float | None = None
    result_lower: float = 0.0
    result_upper: float = 0.0


@dataclass(frozen=True)
class SnapshotProjectionRow:
    snapshot_id: str
    image_path: str
    camera: dict[str, Any] = field(default_factory=dict)
    visible_stackup_ids: tuple[str, ...] = ()
    annotation_positions: dict[str, Any] = field(default_factory=dict)
    captured_at: str = ""
    artifact_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StackupReportSection:
    summary: DashboardProjectionRow
    detail_rows: tuple[DetailProjectionRow, ...]
    result: ResultDisplayProjection
    contributors: tuple[ContributionProjectionRow, ...]
    warnings: tuple[WarningProjectionRow, ...]
    snapshots: tuple[SnapshotProjectionRow, ...]


@dataclass(frozen=True)
class ReportProjection:
    title: str
    project_title: str
    generated_at: str
    unit_system: str
    summary_rows: tuple[DashboardProjectionRow, ...]
    badges: DashboardBadgesProjection
    snapshots: tuple[SnapshotProjectionRow, ...]
    stackups: tuple[StackupReportSection, ...]


@dataclass(frozen=True)
class ReportGenerationResult:
    output_path: Path
    html: str
    projection: ReportProjection
    asset_paths: tuple[Path, ...] = ()
    manifest_path: Path | None = None
    manifest: dict[str, Any] = field(default_factory=dict)


def build_dashboard_projection(
    project: CadToleranceProject,
) -> tuple[tuple[DashboardProjectionRow, ...], DashboardBadgesProjection]:
    rows: list[DashboardProjectionRow] = []
    predicted_sigma: list[float] = []
    target_sigma: list[float] = []
    for stackup in project.stackups:
        result = calculate_stackup(stackup, project.settings)
        rows.append(_dashboard_row_from_stackup(stackup, project, result))
        predicted = _predicted_sigma_from_result(result)
        target = _target_sigma_from_stackup(stackup)
        if predicted is not None and target is not None:
            predicted_sigma.append(predicted)
            target_sigma.append(target)
    projected_rows = tuple(rows)
    failed = sum(1 for row in rows if row.status == ResultStatus.FAIL)
    met = sum(1 for row in rows if row.status != ResultStatus.FAIL)
    return projected_rows, DashboardBadgesProjection(
        met,
        failed,
        _sigma_rollup(predicted_sigma, target_sigma),
    )


def build_result_display(
    stackup: StackupRequirement,
    result: StackupResult | None = None,
    project: CadToleranceProject | None = None,
) -> ResultDisplayProjection:
    result = result or calculate_stackup(stackup, project.settings if project else None)
    mode_label = _analysis_mode_label(result.analysis_mode)
    warnings = tuple(_warning_projection(warning) for warning in result.warnings)
    markers = _result_markers(result)
    predicted_quality = _format_predicted_quality(
        result.quality.target_metric,
        result.quality.cpk,
        result.quality.sigma,
        result.quality.yield_probability,
    )
    return ResultDisplayProjection(
        stackup_id=stackup.id,
        name=stackup.name,
        mode_label=mode_label,
        title=f"{mode_label} Results for {stackup.name}",
        status=result.status,
        nominal_label=f"Nominal: {_format_nominal(result.nominal)}",
        objective_label=f"Objective: {_format_objective(stackup.objective)}",
        result_label=(
            "Results: "
            + _format_result_envelope(
                stackup.objective,
                result.evaluated_minus,
                result.evaluated_plus,
                result.nominal,
            )
        ),
        predicted_quality_label=predicted_quality,
        mean_label=f"Mean: {result.quality.mean:.2f}",
        standard_deviation_label=f"Standard Deviation: {result.quality.standard_deviation:.2f}",
        markers=markers,
        warnings=warnings,
        objective_lower=result.objective.lower_bound,
        objective_upper=result.objective.upper_bound,
        result_lower=result.objective.result_lower,
        result_upper=result.objective.result_upper,
    )


def build_contribution_projection(
    stackup: StackupRequirement,
    result: StackupResult | None = None,
    project: CadToleranceProject | None = None,
) -> tuple[ContributionProjectionRow, ...]:
    result = result or calculate_stackup(stackup, project.settings if project else None)
    by_id = {contributor.id: contributor for contributor in stackup.contributors}
    rows: list[ContributionProjectionRow] = []
    for item in result.contributors:
        contributor = by_id.get(item.contributor_id)
        rows.append(
            ContributionProjectionRow(
                label=item.name,
                percent=round(item.percent, 1),
                tolerance_box=_format_tolerance(contributor) if contributor else "",
                datum=_datum_text(contributor) if contributor else "",
                contributor_id=item.contributor_id,
            )
        )
    return tuple(rows)


def build_report_projection(
    project: CadToleranceProject,
    *,
    title: str = "Tolerance Stackup Report",
    generated_at: str | None = None,
) -> ReportProjection:
    summary_rows, badges = build_dashboard_projection(project)
    snapshots = tuple(_snapshot_projection(snapshot) for snapshot in project.snapshots)
    sections: list[StackupReportSection] = []
    summary_by_id = {row.stackup_id: row for row in summary_rows}
    for stackup in project.stackups:
        result = calculate_stackup(stackup, project.settings)
        warnings = tuple(_warning_projection(warning) for warning in result.warnings)
        sections.append(
            StackupReportSection(
                summary=summary_by_id[stackup.id],
                detail_rows=_detail_projection_rows(stackup, result),
                result=build_result_display(stackup, result, project),
                contributors=build_contribution_projection(stackup, result, project),
                warnings=warnings,
                snapshots=tuple(
                    snapshot
                    for snapshot in snapshots
                    if stackup.id in snapshot.visible_stackup_ids
                ),
            )
        )
    return ReportProjection(
        title=title,
        project_title=project.title,
        generated_at=generated_at if generated_at is not None else _project_report_timestamp(project),
        unit_system=project.unit_system,
        summary_rows=summary_rows,
        badges=badges,
        snapshots=snapshots,
        stackups=tuple(sections),
    )


def render_report_html(
    projection: ReportProjection,
    *,
    stylesheet_href: str | None = None,
    script_href: str | None = None,
) -> str:
    head_assets = (
        [f'<link rel="stylesheet" href="{_e(stylesheet_href)}">']
        if stylesheet_href
        else ["<style>", _REPORT_CSS, "</style>"]
    )
    if script_href:
        head_assets.append(f'<script src="{_e(script_href)}" defer></script>')
    parts = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{_e(projection.title)} - {_e(projection.project_title)}</title>",
        *head_assets,
        "</head>",
        "<body>",
        _render_nav(projection),
        '<main class="report-canvas">',
        _render_title_page(projection),
        _render_summary(projection),
    ]
    for section in projection.stackups:
        parts.append(_render_stackup_section(section))
    parts.extend(["</main>", "</body>", "</html>"])
    return "\n".join(parts) + "\n"


def generate_html_report(
    project: CadToleranceProject,
    output_path: str | Path,
    *,
    title: str = "Tolerance Stackup Report",
    generated_at: str | None = None,
    project_path: str | Path | None = None,
) -> ReportGenerationResult:
    path = Path(output_path)
    if path.suffix == "":
        path = path / "report.html"
    report_dir = path.parent
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "css").mkdir(parents=True, exist_ok=True)
    (report_dir / "images").mkdir(parents=True, exist_ok=True)
    (report_dir / "js").mkdir(parents=True, exist_ok=True)

    projection = build_report_projection(project, title=title, generated_at=generated_at)
    projection, image_assets, manifest_images = _prepare_snapshot_assets(
        projection,
        report_dir,
        project_path=project_path,
    )
    css_path = report_dir / "css" / "report.css"
    js_path = report_dir / "js" / "report.js"
    manifest_path = report_dir / "report_manifest.json"

    css_path.write_text(_REPORT_CSS + "\n", encoding="utf-8", newline="\n")
    js_path.write_text(_REPORT_JS + "\n", encoding="utf-8", newline="\n")
    html = render_report_html(
        projection,
        stylesheet_href="css/report.css",
        script_href="js/report.js",
    )
    path.write_text(html, encoding="utf-8", newline="\n")
    manifest = _report_manifest(
        projection,
        html_path=path.name,
        images=manifest_images,
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    asset_paths = (css_path, js_path, manifest_path, *image_assets)
    return ReportGenerationResult(path, html, projection, asset_paths, manifest_path, manifest)


def _dashboard_row_from_stackup(
    stackup: StackupRequirement,
    project: CadToleranceProject,
    result: StackupResult | None = None,
) -> DashboardProjectionRow:
    result = result or calculate_stackup(stackup, project.settings)
    return DashboardProjectionRow(
        stackup_id=stackup.id,
        status=result.status,
        name=stackup.name,
        nominal=_format_nominal(result.nominal),
        objective=_format_objective(stackup.objective),
        target_quality=_format_quality_target(stackup),
        results=_format_result_envelope(
            stackup.objective,
            result.evaluated_minus,
            result.evaluated_plus,
            result.nominal,
        ),
        predicted_quality=_format_predicted_quality(
            result.quality.target_metric,
            result.quality.cpk,
            result.quality.sigma,
            result.quality.yield_probability,
        ),
        dimension_count=len([item for item in stackup.contributors if item.include_in_stackup]),
        has_warning=bool(result.warnings),
    )


def _detail_projection_rows(
    stackup: StackupRequirement,
    result: StackupResult,
) -> tuple[DetailProjectionRow, ...]:
    rows: list[DetailProjectionRow] = []
    last_part = ""
    for contributor in stackup.contributors:
        part_name = _part_name(contributor)
        if part_name and part_name != last_part:
            rows.append(DetailProjectionRow(part_name, row_type="part"))
            last_part = part_name
        feature_name = _feature_name(contributor)
        if feature_name:
            rows.append(
                DetailProjectionRow(
                    feature_name,
                    "0",
                    _feature_nominal(contributor),
                    _format_tolerance(contributor),
                    _datum_text(contributor),
                    "feature",
                    shared_with=tuple(contributor.shared_with_stackup_ids),
                    source_feature_id=(
                        contributor.source_feature.id if contributor.source_feature else ""
                    ),
                )
            )
        rows.append(
            DetailProjectionRow(
                contributor.name,
                _format_sensitivity(contributor.sensitivity),
                _format_nominal(contributor.nominal),
                _format_tolerance(contributor),
                _datum_text(contributor),
                "dimension",
                shared_with=tuple(contributor.shared_with_stackup_ids),
                contributor_id=contributor.id,
                source_feature_id=(
                    contributor.source_feature.id if contributor.source_feature else ""
                ),
            )
        )
    rows.append(
        DetailProjectionRow(
            stackup.name,
            nominal=_format_nominal(result.nominal),
            tolerance=_format_result_envelope(
                stackup.objective,
                result.evaluated_minus,
                result.evaluated_plus,
                result.nominal,
            ),
            row_type="result",
            status=result.status,
            warning=bool(result.warnings),
        )
    )
    rows.append(
        DetailProjectionRow(
            "Objectives",
            tolerance=_format_objective(stackup.objective),
            row_type="objective",
            status=result.objective.status,
        )
    )
    return tuple(rows)


def _warning_projection(warning: NonOneDWarning) -> WarningProjectionRow:
    return WarningProjectionRow(
        warning_id=warning.id,
        message=warning.message,
        severity=warning.severity,
        feature_ids=tuple(warning.feature_ids),
        observed_value=warning.observed_value,
        threshold=warning.threshold,
    )


def _snapshot_projection(snapshot: Snapshot) -> SnapshotProjectionRow:
    metadata = {
        "id": snapshot.id,
        "image_path": snapshot.image_path,
        "camera": dict(snapshot.camera),
        "visible_stackup_ids": list(snapshot.visible_stackup_ids),
        "annotation_positions": dict(snapshot.annotation_positions),
        "captured_at": snapshot.captured_at,
    }
    return SnapshotProjectionRow(
        snapshot_id=snapshot.id,
        image_path=snapshot.image_path,
        camera=dict(snapshot.camera),
        visible_stackup_ids=tuple(snapshot.visible_stackup_ids),
        annotation_positions=dict(snapshot.annotation_positions),
        captured_at=snapshot.captured_at,
        artifact_metadata=metadata,
    )


def _prepare_snapshot_assets(
    projection: ReportProjection,
    report_dir: Path,
    *,
    project_path: str | Path | None,
) -> tuple[ReportProjection, tuple[Path, ...], list[dict[str, Any]]]:
    images_dir = report_dir / "images"
    used_names: set[str] = set()
    image_assets: list[Path] = []
    manifest_images: list[dict[str, Any]] = []
    prepared_by_id: dict[str, SnapshotProjectionRow] = {}
    prepared_snapshots: list[SnapshotProjectionRow] = []

    for snapshot in projection.snapshots:
        source = _resolve_snapshot_source(snapshot.image_path, project_path)
        suffix = source.suffix.lower() if source is not None and source.suffix else ".svg"
        if suffix not in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}:
            suffix = ".png"
        if source is None:
            suffix = ".svg"
        filename = _unique_asset_name(
            _safe_filename(snapshot.snapshot_id or "snapshot"),
            suffix,
            used_names,
        )
        relative_image_path = f"images/{filename}"
        output_image = images_dir / filename
        if source is None:
            _write_snapshot_placeholder(output_image, snapshot)
            source_reference = _portable_reference(snapshot.image_path)
            source_state = "placeholder"
        else:
            if source.resolve() != output_image.resolve():
                shutil.copyfile(source, output_image)
            source_reference = _portable_reference(snapshot.image_path)
            source_state = "copied"
        image_assets.append(output_image)
        updated_metadata = dict(snapshot.artifact_metadata)
        updated_metadata["report_image_path"] = relative_image_path
        prepared = replace(
            snapshot,
            image_path=relative_image_path,
            artifact_metadata=updated_metadata,
        )
        prepared_snapshots.append(prepared)
        prepared_by_id[snapshot.snapshot_id] = prepared
        manifest_images.append(
            {
                "snapshot_id": snapshot.snapshot_id,
                "path": relative_image_path,
                "source_reference": source_reference,
                "source_state": source_state,
                "visible_stackup_ids": list(snapshot.visible_stackup_ids),
            }
        )

    prepared_sections = []
    for section in projection.stackups:
        prepared_sections.append(
            replace(
                section,
                snapshots=tuple(
                    prepared_by_id.get(snapshot.snapshot_id, snapshot)
                    for snapshot in section.snapshots
                ),
            )
        )
    return (
        replace(
            projection,
            snapshots=tuple(prepared_snapshots),
            stackups=tuple(prepared_sections),
        ),
        tuple(image_assets),
        manifest_images,
    )


def _resolve_snapshot_source(
    image_path: str,
    project_path: str | Path | None,
) -> Path | None:
    if not image_path:
        return None
    raw_path = Path(image_path)
    if raw_path.is_absolute():
        return raw_path.resolve() if raw_path.is_file() else None
    if project_path is not None:
        from .cad_tolerance_project_io import resolve_project_asset_path

        resolved = resolve_project_asset_path(image_path, project_path)
        if resolved is not None and resolved.is_file():
            return resolved
    if raw_path.is_file():
        return raw_path.resolve()
    return None


def _unique_asset_name(base: str, suffix: str, used_names: set[str]) -> str:
    candidate = f"{base}{suffix}"
    if candidate not in used_names:
        used_names.add(candidate)
        return candidate
    index = 2
    while True:
        candidate = f"{base}-{index}{suffix}"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        index += 1


def _safe_filename(value: str) -> str:
    cleaned = "".join(
        char.lower() if char.isalnum() else "-"
        for char in str(value)
    ).strip("-")
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned or "item"


def _portable_reference(reference: str) -> str:
    if not reference:
        return ""
    path = Path(reference)
    if path.is_absolute():
        return path.name
    return str(reference).replace("\\", "/")


def _write_snapshot_placeholder(path: Path, snapshot: SnapshotProjectionRow) -> None:
    stackups = ", ".join(snapshot.visible_stackup_ids) or "No stackup selection"
    camera = ", ".join(sorted(snapshot.camera)) or "No camera metadata"
    path.write_text(
        "\n".join(
            [
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 720" role="img">',
                "<title>Portable CAD snapshot placeholder</title>",
                '<rect width="1200" height="720" fill="#ffffff"/>',
                '<rect x="32" y="32" width="1136" height="656" fill="#fbfbfb" stroke="#c9c9c9" stroke-width="2"/>',
                '<path d="M270 190 L760 120 L930 255 L435 335 Z" fill="#7186b8" stroke="#53648d" stroke-width="3"/>',
                '<path d="M435 335 L930 255 L930 430 L435 520 Z" fill="#a77b57" stroke="#805d41" stroke-width="3"/>',
                '<path d="M270 190 L435 335 L435 520 L270 385 Z" fill="#8b674b" stroke="#70513a" stroke-width="3"/>',
                '<line x1="190" y1="560" x2="760" y2="560" stroke="#233fa8" stroke-width="5"/>',
                '<line x1="190" y1="560" x2="190" y2="380" stroke="#233fa8" stroke-width="3"/>',
                '<line x1="760" y1="560" x2="760" y2="250" stroke="#233fa8" stroke-width="3"/>',
                '<line x1="655" y1="425" x2="790" y2="425" stroke="#8a1f1f" stroke-width="5"/>',
                '<text x="475" y="596" fill="#233fa8" font-family="Segoe UI, Arial" font-size="34">snapshot view</text>',
                '<text x="700" y="405" fill="#8a1f1f" font-family="Segoe UI, Arial" font-size="30">result</text>',
                f'<text x="80" y="96" fill="#555555" font-family="Segoe UI, Arial" font-size="30">{_e(snapshot.snapshot_id)}</text>',
                f'<text x="80" y="140" fill="#666666" font-family="Segoe UI, Arial" font-size="22">Visible stackups: {_e(stackups)}</text>',
                f'<text x="80" y="172" fill="#777777" font-family="Segoe UI, Arial" font-size="20">Camera metadata: {_e(camera)}</text>',
                "</svg>",
            ]
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _report_manifest(
    projection: ReportProjection,
    *,
    html_path: str,
    images: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "report_format": "mdts-cad-1d-tolerance-report",
        "report_format_version": 1,
        "title": projection.title,
        "project_title": projection.project_title,
        "generated_at": projection.generated_at,
        "unit_system": projection.unit_system,
        "html_path": html_path,
        "css_path": "css/report.css",
        "js_path": "js/report.js",
        "summary_row_count": len(projection.summary_rows),
        "stackup_ids": [section.summary.stackup_id for section in projection.stackups],
        "snapshot_ids": [snapshot.snapshot_id for snapshot in projection.snapshots],
        "images": images,
    }


def _result_markers(result: StackupResult) -> tuple[ResultMarker, ...]:
    markers: list[ResultMarker] = [
        ResultMarker("Result lower", result.objective.result_lower, "result"),
        ResultMarker("Result upper", result.objective.result_upper, "result"),
    ]
    if result.objective.lower_bound is not None:
        markers.append(ResultMarker("Lower objective", result.objective.lower_bound, "objective"))
    if result.objective.upper_bound is not None:
        markers.append(ResultMarker("Upper objective", result.objective.upper_bound, "objective"))
    markers.append(ResultMarker("Mean", result.nominal, "mean"))
    return tuple(markers)


def _render_nav(projection: ReportProjection) -> str:
    links = ['<a href="#summary">Summary</a>']
    for section in projection.stackups:
        links.append(
            f'<a href="#{_anchor("stackup", section.summary.stackup_id)}">{_e(section.summary.name)}</a>'
        )
    return "\n".join(
        [
            '<nav class="left-nav">',
            '<div class="nav-logo">MDTS</div>',
            '<div class="nav-title">Tolerance Report</div>',
            *links,
            "</nav>",
        ]
    )


def _render_title_page(projection: ReportProjection) -> str:
    generated = projection.generated_at or "Not recorded"
    document_name = projection.project_title
    return "\n".join(
        [
            '<section class="title-page">',
            f"<h1>{_e(projection.title)}</h1>",
            f'<div class="project-name">{_e(document_name)}</div>',
            f'<div class="meta-line">Units: {_e(projection.unit_system)}</div>',
            f'<div class="meta-line">Generated: {_e(generated)}</div>',
            "</section>",
        ]
    )


def _render_summary(projection: ReportProjection) -> str:
    rows = "\n".join(_render_summary_row(row) for row in projection.summary_rows)
    snapshots = "\n".join(_render_snapshot(snapshot) for snapshot in projection.snapshots)
    return "\n".join(
        [
            '<section id="summary" class="report-section">',
            "<h2>Summary of 1D Tolerance Stackups</h2>",
            '<div class="badges">',
            f'<div class="badge badge-green"><strong>{projection.badges.objectives_met}</strong><span>Objectives met</span></div>',
            f'<div class="badge badge-red"><strong>{projection.badges.objectives_not_met}</strong><span>Objectives not met</span></div>',
            f'<div class="badge badge-pill"><strong>{_e(projection.badges.sigma_rollup)}</strong><span>Predicted / Target Sigma rollup</span></div>',
            "</div>",
            '<table class="summary-table">',
            _render_header_row(SUMMARY_COLUMNS),
            "<tbody>",
            rows,
            "</tbody>",
            "</table>",
            "<h3>Snapshots</h3>",
            '<div class="snapshots">',
            snapshots or '<div class="empty">No report snapshots captured.</div>',
            "</div>",
            "</section>",
        ]
    )


def _render_stackup_section(section: StackupReportSection) -> str:
    detail_rows = "\n".join(_render_detail_row(row) for row in section.detail_rows)
    contribution_rows = "\n".join(_render_contribution(row) for row in section.contributors)
    warnings = _render_warnings(section.warnings)
    snapshots = "\n".join(_render_snapshot(snapshot) for snapshot in section.snapshots)
    return "\n".join(
        [
            f'<section id="{_anchor("stackup", section.summary.stackup_id)}" class="report-section">',
            f"<h2>{_e(section.summary.name)}</h2>",
            '<div class="stackup-status-row">',
            f'<span class="status status-{_status_class(section.summary.status)}">{_status_text(section.summary)}</span>',
            f"<span>{_e(section.summary.objective)}</span>",
            f"<span>{_e(section.summary.target_quality)}</span>",
            "</div>",
            '<div class="snapshots stackup-snapshots">',
            snapshots or '<div class="empty">No stackup snapshot captured.</div>',
            "</div>",
            "<h3>Stackup Table</h3>",
            '<table class="detail-table">',
            _render_header_row(DETAIL_COLUMNS),
            "<tbody>",
            detail_rows,
            "</tbody>",
            "</table>",
            f"<h3>{_e(section.summary.name)} Analysis Results</h3>",
            _render_result_panel(section.result),
            warnings,
            f"<h3>{_e(section.summary.name)} Analysis Contributions</h3>",
            '<div class="contributions">',
            contribution_rows or '<div class="empty">No contributors are included in this stackup.</div>',
            "</div>",
            "</section>",
        ]
    )


def _render_header_row(columns: tuple[str, ...]) -> str:
    headers = "".join(f"<th>{_e(column)}</th>" for column in columns)
    return f"<thead><tr>{headers}</tr></thead>"


def _render_summary_row(row: DashboardProjectionRow) -> str:
    values = (
        _status_text(row),
        row.name,
        row.nominal,
        row.objective,
        row.target_quality,
        row.results,
        row.predicted_quality,
        str(row.dimension_count),
    )
    cells = "".join(f"<td>{_e(value)}</td>" for value in values)
    return f'<tr class="{_status_class(row.status)}">{cells}</tr>'


def _render_detail_row(row: DetailProjectionRow) -> str:
    classes = [row.row_type]
    if row.status:
        classes.append(_status_class(row.status))
    if row.warning:
        classes.append("warn")
    shared = ""
    if row.shared_with:
        shared = f'<span class="shared-marker" title="Shared with: {_e(", ".join(row.shared_with))}">shared</span>'
    first_cell = f"<td>{_e(row.name)}{shared}</td>"
    values = (row.sensitivity, row.nominal, row.tolerance, row.datum)
    cells = first_cell + "".join(f"<td>{_e(value)}</td>" for value in values)
    return f'<tr class="{" ".join(classes)}">{cells}</tr>'


def _render_result_panel(result: ResultDisplayProjection) -> str:
    markers = "\n".join(
        f'<li><span>{_e(marker.label)}</span><strong>{marker.value:.3f}</strong></li>'
        for marker in result.markers
    )
    plot_markers = "\n".join(_render_result_plot_marker(result, marker) for marker in result.markers)
    predicted = (
        f'<div class="metric">{_e(result.predicted_quality_label)}</div>'
        if result.predicted_quality_label
        else ""
    )
    return "\n".join(
        [
            '<div class="result-panel">',
            f"<h4>{_e(result.title)}</h4>",
            '<div class="result-metrics">',
            f'<div class="metric">{_e(result.mean_label)}</div>',
            f'<div class="metric">{_e(result.standard_deviation_label)}</div>',
            f'<div class="metric">{_e(result.result_label)}</div>',
            f'<div class="metric">{_e(result.objective_label)}</div>',
            predicted,
            "</div>",
            '<div class="range-bar result-plot">',
            '<div class="range-fail"></div><div class="range-pass"></div><div class="range-fail"></div>',
            plot_markers,
            "</div>",
            '<ul class="markers">',
            markers,
            "</ul>",
            "</div>",
        ]
    )


def _render_result_plot_marker(
    result: ResultDisplayProjection,
    marker: ResultMarker,
) -> str:
    left = _result_marker_position(result, marker.value)
    return (
        f'<span class="result-marker marker-{_e(marker.role)}" '
        f'style="left:{left:.2f}%"><span>{marker.value:.3f}</span></span>'
    )


def _result_marker_position(result: ResultDisplayProjection, value: float) -> float:
    values = [result.result_lower, result.result_upper, value]
    values.extend(marker.value for marker in result.markers)
    if result.objective_lower is not None:
        values.append(result.objective_lower)
    if result.objective_upper is not None:
        values.append(result.objective_upper)
    lower = min(values)
    upper = max(values)
    if abs(upper - lower) < 1.0e-9:
        return 50.0
    padding = (upper - lower) * 0.12
    domain_lower = lower - padding
    domain_upper = upper + padding
    return max(0.0, min(100.0, ((value - domain_lower) / (domain_upper - domain_lower)) * 100.0))


def _render_contribution(row: ContributionProjectionRow) -> str:
    width = max(1.0, min(100.0, row.percent))
    tolerance = " ".join(part for part in (row.tolerance_box, row.datum) if part)
    tolerance_html = (
        f'<span class="tolerance-box">{_e(tolerance)}</span>'
        if tolerance
        else '<span class="tolerance-box tolerance-box-empty"></span>'
    )
    return "\n".join(
        [
            '<div class="contribution-row">',
            f'<span class="contribution-label">{_e(row.label)}</span>',
            tolerance_html,
            '<span class="contribution-track">',
            f'<span class="contribution-bar" style="width:{width:.1f}%"></span>',
            "</span>",
            f'<strong>{row.percent:.1f}%</strong>',
            "</div>",
        ]
    )


def _render_warnings(warnings: tuple[WarningProjectionRow, ...]) -> str:
    if not warnings:
        return ""
    items = "\n".join(f"<li>{_e(warning.message)}</li>" for warning in warnings)
    return "\n".join(
        [
            '<div class="warning-box">',
            f"<strong>{_e(NON_1D_WARNING_TEXT)}</strong>",
            "<ul>",
            items,
            "</ul>",
            "</div>",
        ]
    )


def _render_snapshot(snapshot: SnapshotProjectionRow) -> str:
    captured = f"Captured: {snapshot.captured_at}" if snapshot.captured_at else "Captured snapshot"
    metadata = [
        f"Snapshot: {snapshot.snapshot_id}",
        f"Visible stackups: {', '.join(snapshot.visible_stackup_ids) or 'none'}",
        f"Camera keys: {', '.join(sorted(snapshot.camera)) or 'none'}",
    ]
    metadata_html = "".join(f"<li>{_e(item)}</li>" for item in metadata)
    return "\n".join(
        [
            '<figure class="snapshot">',
            f'<img src="{_e(snapshot.image_path)}" alt="CAD snapshot {_e(snapshot.snapshot_id)}">',
            f"<figcaption>{_e(captured)}</figcaption>",
            f'<ul class="snapshot-meta">{metadata_html}</ul>',
            "</figure>",
        ]
    )


def _status_text(row: DashboardProjectionRow) -> str:
    if row.status == ResultStatus.FAIL:
        return "FAIL"
    if row.status == ResultStatus.WARN or row.has_warning:
        return "WARN"
    if row.status == ResultStatus.PASS:
        return "OK"
    return "INCOMPLETE"


def _status_class(status: ResultStatus | None) -> str:
    if status == ResultStatus.FAIL:
        return "fail"
    if status == ResultStatus.WARN:
        return "warn"
    if status == ResultStatus.PASS:
        return "pass"
    return "incomplete"


def _project_report_timestamp(project: CadToleranceProject) -> str:
    for report in project.reports:
        generated_at = report.get("generated_at")
        if generated_at:
            return str(generated_at)
    return ""


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


def _format_predicted_quality(
    metric: QualityMetric,
    cpk: float | None,
    sigma: float | None,
    yield_probability: float | None,
) -> str:
    if metric == QualityMetric.CPK and cpk is not None:
        return f"Cpk = {cpk:.2f}"
    if metric == QualityMetric.SIGMA and sigma is not None:
        return f"Sigma = {sigma:.2f}"
    if metric == QualityMetric.YIELD and yield_probability is not None:
        return f"Yield = {yield_probability * 100.0:.0f}%"
    return ""


def _format_result_envelope(
    objective: StackupObjective,
    minus: float,
    plus: float,
    nominal: float,
) -> str:
    if objective.objective_type == ObjectiveType.UPPER_LIMIT:
        return f"<= {nominal + plus:.3f}"
    if objective.objective_type == ObjectiveType.LOWER_LIMIT:
        return f">= {nominal - minus:.3f}"
    if abs(minus - plus) < 1.0e-9:
        return f"+/-{plus:.3f}".rstrip("0").rstrip(".")
    return f"+{plus:.3f}/-{minus:.3f}"


def _format_tolerance(contributor: StackupContributor | None) -> str:
    if contributor is None:
        return ""
    if contributor.tolerance_type == ToleranceType.GEOMETRIC and contributor.geometric_tolerance:
        return f"dia {contributor.geometric_tolerance.tolerance_value:.3f}".rstrip("0").rstrip(".")
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
    return {
        QualityMetric.CPK: "Cpk",
        QualityMetric.SIGMA: "Sigma",
        QualityMetric.YIELD: "Yield",
        QualityMetric.WORST_CASE: "Worst Case",
        QualityMetric.RSS: "RSS",
    }[metric]


def _analysis_mode_label(mode: AnalysisMode) -> str:
    return {
        AnalysisMode.WORST_CASE: "Worst Case",
        AnalysisMode.RSS: "RSS",
        AnalysisMode.STATISTICAL: "Statistical",
    }[mode]


def _part_name(contributor: StackupContributor) -> str:
    feature = contributor.source_feature
    if feature and feature.shape_reference and feature.shape_reference.assembly_path:
        return feature.shape_reference.assembly_path[-1]
    if feature and feature.owner_part_id:
        return feature.owner_part_id
    return ""


def _feature_name(contributor: StackupContributor) -> str:
    feature = contributor.source_feature
    if feature is None:
        return ""
    return feature.name or (
        feature.shape_reference.fallback_display_name if feature.shape_reference else ""
    )


def _feature_nominal(contributor: StackupContributor) -> str:
    feature = contributor.source_feature
    if feature is None or feature.shape_reference is None:
        return ""
    radius = feature.shape_reference.geometric_signature.get("radius")
    if radius is not None:
        return f"(dia {float(radius) * 2.0:.2f})"
    return ""


def _datum_text(contributor: StackupContributor | None) -> str:
    if contributor is None:
        return ""
    if contributor.datum_references:
        return ", ".join(contributor.datum_references)
    if contributor.geometric_tolerance and contributor.geometric_tolerance.datum_references:
        return ", ".join(contributor.geometric_tolerance.datum_references)
    if contributor.source_feature and contributor.source_feature.datum_label:
        return contributor.source_feature.datum_label
    return ""


def _sigma_rollup(predicted: list[float], targets: list[float]) -> str:
    if not predicted or not targets:
        return ""
    return f"{min(predicted):.2f} / {min(targets):.2f}"


def _predicted_sigma_from_result(result: StackupResult) -> float | None:
    if result.quality.sigma is not None:
        return result.quality.sigma
    if result.quality.cpk is not None:
        return result.quality.cpk * 3.0
    return None


def _target_sigma_from_stackup(stackup: StackupRequirement) -> float | None:
    target = stackup.target_quality
    if target.value is None:
        return None
    if target.metric == QualityMetric.SIGMA:
        return target.value
    if target.metric == QualityMetric.CPK:
        return target.value * 3.0
    return None


def _anchor(prefix: str, value: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-")
    return f"{prefix}-{cleaned or 'item'}"


def _e(value: Any) -> str:
    return escape(str(value), quote=True)


_REPORT_CSS = """
:root {
  color-scheme: light;
  font-family: "Segoe UI", Arial, sans-serif;
}
body {
  margin: 0;
  background: #ffffff;
  color: #4f4f4f;
}
.left-nav {
  position: fixed;
  inset: 0 auto 0 0;
  width: 210px;
  overflow-y: auto;
  background: #111111;
  color: #d6d6d6;
  padding: 0 0 18px;
  box-sizing: border-box;
}
.nav-logo {
  height: 112px;
  display: grid;
  place-items: center;
  border: 0;
  background: #e2e2e2;
  color: #101010;
  font-size: 32px;
  font-weight: 800;
  margin-bottom: 0;
  letter-spacing: 0;
}
.nav-title {
  color: #9e9e9e;
  font-size: 12px;
  text-transform: uppercase;
  padding: 18px 14px 8px;
}
.left-nav a {
  display: block;
  color: #bdbdbd;
  text-decoration: none;
  padding: 9px 14px;
  border-bottom: 1px solid #1f1f1f;
  font-size: 16px;
  line-height: 1.25;
}
.left-nav a:hover {
  color: #ffffff;
  background: #1f1f1f;
}
.left-nav a.active {
  color: #ffffff;
  background: #242424;
}
.report-canvas {
  margin-left: 210px;
  padding: 34px 54px 54px;
  background: #ffffff;
  min-height: 100vh;
}
.title-page,
.report-section {
  max-width: 980px;
  margin: 0 auto 46px;
  padding: 0;
  background: #ffffff;
  border: 0;
}
.title-page h1 {
  margin: 0 0 8px;
  font-size: 34px;
  font-weight: 600;
  color: #4d4d4d;
}
.project-name {
  font-size: 20px;
  color: #555555;
  margin-bottom: 18px;
}
.meta-line {
  color: #666666;
  line-height: 1.7;
}
h2 {
  margin: 0 0 18px;
  font-size: 29px;
  font-weight: 400;
  color: #777777;
}
h3 {
  margin: 34px 0 18px;
  font-size: 22px;
  font-weight: 400;
  color: #777777;
}
h4 {
  margin: 0 0 12px;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  table-layout: fixed;
}
th,
td {
  border: 1px solid #d7d7d7;
  padding: 8px 10px;
  text-align: left;
  overflow-wrap: anywhere;
}
th {
  background: #f7f7f7;
  font-weight: 700;
  color: #222222;
}
.summary-table {
  table-layout: auto;
}
.summary-table th,
.summary-table td {
  white-space: nowrap;
}
.summary-table th:nth-child(2),
.summary-table td:nth-child(2) {
  min-width: 170px;
}
.detail-table {
  table-layout: fixed;
}
tr.pass td {
  background: #eef8ee;
}
tr.warn td {
  background: #fff7d6;
}
tr.fail td {
  background: #f9e2e2;
}
tr.part td {
  background: #ffffff;
  font-weight: 700;
}
tr.feature td {
  background: #f7f7f7;
}
tr.result td,
tr.objective td {
  background: #f2f2f2;
  font-weight: 700;
}
.badges,
.stackup-status-row {
  display: flex;
  gap: 14px;
  align-items: center;
  margin: 12px 0 18px;
}
.badge {
  min-width: 130px;
  padding: 12px 16px;
  color: #ffffff;
  text-align: center;
  background: #c92020;
}
.badge strong {
  display: block;
  font-size: 28px;
}
.badge span {
  display: block;
  font-size: 12px;
}
.badge-green {
  background: #168a29;
}
.badge-pill {
  min-width: 230px;
  border-radius: 8px;
}
.status {
  display: inline-block;
  min-width: 68px;
  padding: 6px 10px;
  color: #ffffff;
  font-weight: 700;
  text-align: center;
}
.status-pass {
  background: #168a29;
}
.status-warn {
  background: #be8f00;
}
.status-fail {
  background: #c92020;
}
.status-incomplete {
  background: #777777;
}
.snapshots {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 18px;
}
.snapshot {
  margin: 0;
  border: 1px solid #cccccc;
  padding: 0;
  background: #ffffff;
}
.snapshot img {
  display: block;
  width: 100%;
  min-height: 360px;
  aspect-ratio: 5 / 3;
  object-fit: contain;
  border: 0;
  background: #ffffff;
}
.snapshot figcaption,
.snapshot-meta {
  font-size: 12px;
  color: #666666;
}
.snapshot-meta {
  margin: 8px 0 0 16px;
  padding: 0;
}
.result-panel {
  border: 1px solid #d0d0d0;
  padding: 14px 26px 10px;
  background: #ffffff;
}
.result-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 8px 14px;
  margin-bottom: 12px;
}
.metric {
  color: #444444;
}
.range-bar {
  display: grid;
  grid-template-columns: 1fr 2fr 1fr;
  height: 24px;
  border: 0;
  border-bottom: 3px solid #111111;
  margin: 34px 18px 26px;
  position: relative;
}
.range-fail {
  background: #c32b2b;
}
.range-pass {
  background: #168a24;
}
.result-marker {
  position: absolute;
  bottom: -13px;
  width: 4px;
  height: 42px;
  margin-left: -2px;
  background: #111111;
}
.result-marker span {
  position: absolute;
  bottom: 44px;
  left: 50%;
  transform: translateX(-50%);
  min-width: 52px;
  color: #111111;
  text-align: center;
  font-size: 12px;
  font-weight: 700;
}
.marker-result {
  background: #c32b2b;
}
.marker-mean {
  background: #111111;
}
.marker-objective {
  background: #111111;
}
.markers {
  columns: 2;
  margin: 8px 0 0 18px;
  padding: 0;
}
.markers li {
  margin-bottom: 3px;
}
.markers span {
  display: inline-block;
  min-width: 120px;
}
.warning-box {
  margin-top: 12px;
  padding: 12px;
  border: 0;
  background: #ffffff;
  color: #111111;
}
.contribution-row {
  display: grid;
  grid-template-columns: minmax(190px, 260px) minmax(90px, 150px) minmax(180px, 1fr) 56px;
  align-items: center;
  column-gap: 12px;
  min-height: 42px;
  margin: 0 0 7px;
}
.contribution-label {
  min-width: 0;
  overflow-wrap: anywhere;
}
.contribution-track {
  display: block;
  position: relative;
  width: 100%;
  min-width: 0;
  height: 31px;
}
.contribution-bar {
  display: block;
  height: 31px;
  max-width: 100%;
  background: #0b82c6;
}
.tolerance-box {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #222222;
  padding: 3px 7px;
  min-width: 0;
  max-width: 100%;
  min-height: 30px;
  box-sizing: border-box;
  text-align: center;
  white-space: normal;
  overflow-wrap: anywhere;
  line-height: 1.15;
  background: #ffffff;
}
.tolerance-box-empty {
  visibility: hidden;
}
.shared-marker {
  display: inline-block;
  margin-left: 8px;
  color: #555555;
  font-size: 11px;
}
.empty {
  color: #777777;
  font-style: italic;
}
""".strip()


_REPORT_JS = """
document.addEventListener("DOMContentLoaded", () => {
  const links = Array.from(document.querySelectorAll(".left-nav a"));
  const byId = new Map(links.map((link) => [link.getAttribute("href"), link]));
  const setActive = () => {
    const hash = window.location.hash || "#summary";
    links.forEach((link) => link.classList.remove("active"));
    const active = byId.get(hash);
    if (active) active.classList.add("active");
  };
  window.addEventListener("hashchange", setActive);
  setActive();
});
""".strip()
