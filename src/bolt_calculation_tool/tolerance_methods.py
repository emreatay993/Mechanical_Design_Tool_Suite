"""Next-version tolerance stackup, protrusion, and validation methods."""

from __future__ import annotations

from dataclasses import dataclass
import math

from .tolerance import SIGMA_COVERAGE, ToleranceDimension, calculate_stackup
from .tolerance_catalog import ToleranceCatalog
from .tolerance_models import Joint, PathItem, SubJoint, sync_path_with_flanges


@dataclass(frozen=True)
class ContributorResult:
    item_id: str
    name: str
    nominal: float
    tolerance: float
    variance: float
    contribution: float


@dataclass(frozen=True)
class StackupPathResult:
    nominal: float
    worst_case_deviation: float
    rss: float
    one_point_five_rss: float
    top_four_contributor_sum: float
    contributors: tuple[ContributorResult, ...]
    validation_messages: tuple[str, ...] = ()


@dataclass(frozen=True)
class CriterionResult:
    name: str
    required: float
    actual: float | None
    margin: float | None
    status: str
    message: str


@dataclass(frozen=True)
class ThreadProtrusionResult:
    status: str
    protrusion: float | None
    engagement: float | None
    criteria: tuple[CriterionResult, ...]
    messages: tuple[str, ...] = ()


@dataclass(frozen=True)
class SubJointResult:
    joint_name: str
    sub_joint_name: str
    stackup: StackupPathResult
    protrusion: ThreadProtrusionResult


def calculate_stackup_path(items: list[PathItem]) -> StackupPathResult:
    active_items = [item for item in items if item.include_in_stackup]
    messages: list[str] = []
    for item in active_items:
        _validate_path_item(item)
    if not active_items:
        return StackupPathResult(
            nominal=0.0,
            worst_case_deviation=0.0,
            rss=0.0,
            one_point_five_rss=0.0,
            top_four_contributor_sum=0.0,
            contributors=(),
            validation_messages=("Add at least one stackup path item.",),
        )

    nominal = sum(item.nominal_thickness for item in active_items)
    dimensions = [
        ToleranceDimension(item.name, item.nominal_thickness, item.tolerance)
        for item in active_items
    ]
    analysis = calculate_stackup(
        dimensions,
        target_min=nominal - 1_000_000.0,
        target_max=nominal + 1_000_000.0,
    )
    total_variance = analysis.rss_variance
    contributors: list[ContributorResult] = []
    for item, dimension_result in zip(active_items, analysis.dimensions, strict=True):
        contribution = (
            dimension_result.variance / total_variance if total_variance > 0.0 else 0.0
        )
        contributors.append(
            ContributorResult(
                item_id=item.id,
                name=item.name,
                nominal=item.nominal_thickness,
                tolerance=item.tolerance,
                variance=dimension_result.variance,
                contribution=contribution,
            )
        )
    top_four = sorted(contributors, key=lambda item: item.contribution, reverse=True)[:4]
    top_four_sum = sum(item.contribution for item in top_four)
    return StackupPathResult(
        nominal=analysis.nominal,
        worst_case_deviation=analysis.worst_case_tolerance,
        rss=analysis.rss_tolerance,
        one_point_five_rss=analysis.rss_tolerance * 1.5,
        top_four_contributor_sum=top_four_sum,
        contributors=tuple(
            sorted(contributors, key=lambda item: item.contribution, reverse=True)
        ),
        validation_messages=tuple(messages),
    )


def calculate_sub_joint_result(
    joint: Joint,
    sub_joint: SubJoint,
    catalog: ToleranceCatalog,
) -> SubJointResult:
    sync_path_with_flanges(joint, sub_joint)
    stackup = calculate_stackup_path(sub_joint.stackup_path.items)
    protrusion = evaluate_thread_protrusion(sub_joint, stackup, catalog)
    return SubJointResult(
        joint_name=joint.name,
        sub_joint_name=sub_joint.name,
        stackup=stackup,
        protrusion=protrusion,
    )


def evaluate_thread_protrusion(
    sub_joint: SubJoint,
    stackup: StackupPathResult,
    catalog: ToleranceCatalog,
) -> ThreadProtrusionResult:
    bolt = catalog.find_bolt(sub_joint.bolt_size_id, sub_joint.bolt_type_id)
    if bolt is None:
        return _incomplete_protrusion(
            f"Select a valid bolt size/type for {sub_joint.name}."
        )
    if sub_joint.selected_bolt_length <= 0.0:
        return _incomplete_protrusion(f"Select a bolt length for {sub_joint.name}.")

    engagement_type = sub_joint.stackup_path.engagement_type
    engagement_part = catalog.find_hardware(
        sub_joint.stackup_path.selected_engagement_part_id
    )
    if engagement_part is None:
        engagement_part = catalog.default_hardware(engagement_type, sub_joint.bolt_size_id)
    if engagement_part is None:
        return _incomplete_protrusion(
            f"Select a {engagement_type} compatible with {sub_joint.bolt_size_id}."
        )

    if engagement_type == "nut":
        protrusion = (
            sub_joint.selected_bolt_length
            - stackup.nominal
            - engagement_part.nominal_thickness
        )
        criteria = (
            _criterion("1.5P", bolt.pitch * 1.5, protrusion),
            _criterion("2P", bolt.pitch * 2.0, protrusion),
            _criterion("2P+Chamfer", bolt.pitch * 2.0 + bolt.chamfer_allowance, protrusion),
        )
        return ThreadProtrusionResult(
            status=_combined_status(criteria),
            protrusion=protrusion,
            engagement=None,
            criteria=criteria,
        )

    engagement = sub_joint.selected_bolt_length - stackup.nominal
    min_engagement = engagement_part.min_engagement or bolt.pitch * 2.0
    max_engagement = engagement_part.max_engagement
    criteria: list[CriterionResult] = [
        _criterion("Min engagement", min_engagement, engagement)
    ]
    if max_engagement is not None:
        margin = max_engagement - engagement
        criteria.append(
            CriterionResult(
                name="Max engagement",
                required=max_engagement,
                actual=engagement,
                margin=margin,
                status="Pass" if margin >= 0.0 else "Fail",
                message=(
                    "Engagement is within max limit."
                    if margin >= 0.0
                    else "Engagement exceeds max limit."
                ),
            )
        )
    return ThreadProtrusionResult(
        status=_combined_status(tuple(criteria)),
        protrusion=None,
        engagement=engagement,
        criteria=tuple(criteria),
    )


def status_rank(status: str) -> int:
    return {"Pass": 0, "Warn": 1, "Fail": 2, "Incomplete": 3}.get(status, 3)


def _validate_path_item(item: PathItem) -> None:
    try:
        nominal = float(item.nominal_thickness)
        tolerance = float(item.tolerance)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{item.name} thickness and tolerance must be numeric.") from exc
    if not math.isfinite(nominal):
        raise ValueError(f"{item.name} thickness must be finite.")
    if not math.isfinite(tolerance):
        raise ValueError(f"{item.name} tolerance must be finite.")
    if tolerance < 0.0:
        raise ValueError(f"{item.name} tolerance must be non-negative.")


def _criterion(name: str, required: float, actual: float) -> CriterionResult:
    margin = actual - required
    if margin < 0.0:
        status = "Fail"
        message = f"{name} fails by {abs(margin):.3f}."
    elif margin < max(required * 0.10, 0.05):
        status = "Warn"
        message = f"{name} has low margin ({margin:.3f})."
    else:
        status = "Pass"
        message = f"{name} passes with {margin:.3f} margin."
    return CriterionResult(
        name=name,
        required=required,
        actual=actual,
        margin=margin,
        status=status,
        message=message,
    )


def _combined_status(criteria: tuple[CriterionResult, ...]) -> str:
    statuses = {criterion.status for criterion in criteria}
    if "Fail" in statuses:
        return "Fail"
    if "Incomplete" in statuses:
        return "Incomplete"
    if "Warn" in statuses:
        return "Warn"
    return "Pass"


def _incomplete_protrusion(message: str) -> ThreadProtrusionResult:
    return ThreadProtrusionResult(
        status="Incomplete",
        protrusion=None,
        engagement=None,
        criteria=(),
        messages=(message,),
    )
