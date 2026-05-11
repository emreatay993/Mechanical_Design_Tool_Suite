"""Next-version tolerance stackup, protrusion, and validation methods."""

from __future__ import annotations

from dataclasses import dataclass
import math
import random

from .tolerance_catalog import ToleranceCatalog
from .tolerance_models import (
    Joint,
    MethodSettings,
    PathItem,
    SubJoint,
    sync_path_with_flanges,
)


@dataclass(frozen=True)
class ContributorResult:
    item_id: str
    name: str
    nominal: float
    tolerance: float
    tolerance_minus: float
    tolerance_plus: float
    variance: float
    contribution: float


@dataclass(frozen=True)
class MonteCarloStackupResult:
    sample_count: int
    seed: int
    mean: float
    std_deviation: float
    minimum: float
    p00135: float
    p50: float
    p99865: float
    maximum: float


@dataclass(frozen=True)
class StackupPathResult:
    nominal: float
    worst_case_deviation: float
    worst_case_minus: float
    worst_case_plus: float
    rss: float
    rss_minus: float
    rss_plus: float
    one_point_five_rss: float
    one_point_five_rss_minus: float
    one_point_five_rss_plus: float
    top_four_contributor_sum: float
    contributors: tuple[ContributorResult, ...]
    monte_carlo: MonteCarloStackupResult | None = None
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


def calculate_stackup_path(
    items: list[PathItem],
    settings: MethodSettings | None = None,
) -> StackupPathResult:
    settings = settings or MethodSettings()
    active_items = [item for item in items if item.include_in_stackup]
    messages: list[str] = []
    for item in active_items:
        _validate_path_item(item, settings)
    if not active_items:
        return StackupPathResult(
            nominal=0.0,
            worst_case_deviation=0.0,
            worst_case_minus=0.0,
            worst_case_plus=0.0,
            rss=0.0,
            rss_minus=0.0,
            rss_plus=0.0,
            one_point_five_rss=0.0,
            one_point_five_rss_minus=0.0,
            one_point_five_rss_plus=0.0,
            top_four_contributor_sum=0.0,
            contributors=(),
            monte_carlo=None,
            validation_messages=("Add at least one stackup path item.",),
        )

    nominal = sum(item.nominal_thickness for item in active_items)
    sigma_coverage = _validated_sigma_coverage(settings.sigma_coverage)
    worst_case_minus = sum(float(item.tolerance_minus or 0.0) for item in active_items)
    worst_case_plus = sum(float(item.tolerance_plus or 0.0) for item in active_items)
    rss_minus = math.sqrt(
        sum(float(item.tolerance_minus or 0.0) ** 2 for item in active_items)
    )
    rss_plus = math.sqrt(
        sum(float(item.tolerance_plus or 0.0) ** 2 for item in active_items)
    )
    worst_case_deviation = max(worst_case_minus, worst_case_plus)
    rss = max(rss_minus, rss_plus)
    total_variance = sum(
        (max(float(item.tolerance_minus or 0.0), float(item.tolerance_plus or 0.0)) / sigma_coverage)
        ** 2
        for item in active_items
    )
    contributors: list[ContributorResult] = []
    for item in active_items:
        tolerance_minus = float(item.tolerance_minus or 0.0)
        tolerance_plus = float(item.tolerance_plus or 0.0)
        envelope_tolerance = max(tolerance_minus, tolerance_plus)
        variance = (envelope_tolerance / sigma_coverage) ** 2
        contribution = variance / total_variance if total_variance > 0.0 else 0.0
        contributors.append(
            ContributorResult(
                item_id=item.id,
                name=item.name,
                nominal=item.nominal_thickness,
                tolerance=envelope_tolerance,
                tolerance_minus=tolerance_minus,
                tolerance_plus=tolerance_plus,
                variance=variance,
                contribution=contribution,
            )
        )
    top_four = sorted(contributors, key=lambda item: item.contribution, reverse=True)[:4]
    top_four_sum = sum(item.contribution for item in top_four)
    monte_carlo = (
        calculate_monte_carlo_stackup(active_items, settings)
        if settings.monte_carlo_enabled
        else None
    )
    return StackupPathResult(
        nominal=nominal,
        worst_case_deviation=worst_case_deviation,
        worst_case_minus=worst_case_minus,
        worst_case_plus=worst_case_plus,
        rss=rss,
        rss_minus=rss_minus,
        rss_plus=rss_plus,
        one_point_five_rss=rss * 1.5,
        one_point_five_rss_minus=rss_minus * 1.5,
        one_point_five_rss_plus=rss_plus * 1.5,
        top_four_contributor_sum=top_four_sum,
        contributors=tuple(
            sorted(contributors, key=lambda item: item.contribution, reverse=True)
        ),
        monte_carlo=monte_carlo,
        validation_messages=tuple(messages),
    )


def calculate_sub_joint_result(
    joint: Joint,
    sub_joint: SubJoint,
    catalog: ToleranceCatalog,
) -> SubJointResult:
    sync_path_with_flanges(joint, sub_joint)
    stackup = calculate_stackup_path(
        sub_joint.stackup_path.items,
        sub_joint.stackup_path.method_settings,
    )
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


def calculate_monte_carlo_stackup(
    active_items: list[PathItem],
    settings: MethodSettings,
) -> MonteCarloStackupResult:
    sample_count = int(settings.monte_carlo_sample_count)
    if sample_count < 100 or sample_count > 100000:
        raise ValueError("Monte Carlo sample count must be between 100 and 100000.")
    sigma_coverage = _validated_sigma_coverage(settings.sigma_coverage)
    seed = int(settings.monte_carlo_seed)
    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(sample_count):
        total = 0.0
        for item in active_items:
            z_score = rng.gauss(0.0, 1.0)
            tolerance = (
                float(item.tolerance_plus or 0.0)
                if z_score >= 0.0
                else float(item.tolerance_minus or 0.0)
            )
            total += item.nominal_thickness + z_score * tolerance / sigma_coverage
        samples.append(total)
    samples.sort()
    mean = sum(samples) / sample_count
    variance = (
        sum((sample - mean) ** 2 for sample in samples) / (sample_count - 1)
        if sample_count > 1
        else 0.0
    )
    return MonteCarloStackupResult(
        sample_count=sample_count,
        seed=seed,
        mean=mean,
        std_deviation=math.sqrt(variance),
        minimum=samples[0],
        p00135=_percentile(samples, 0.00135),
        p50=_percentile(samples, 0.50),
        p99865=_percentile(samples, 0.99865),
        maximum=samples[-1],
    )


def _validate_path_item(item: PathItem, settings: MethodSettings) -> None:
    try:
        nominal = float(item.nominal_thickness)
        tolerance = float(item.tolerance)
        tolerance_minus = float(item.tolerance_minus or 0.0)
        tolerance_plus = float(item.tolerance_plus or 0.0)
        sigma_coverage = float(settings.sigma_coverage)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{item.name} thickness and tolerance must be numeric.") from exc
    if not math.isfinite(nominal):
        raise ValueError(f"{item.name} thickness must be finite.")
    if not math.isfinite(tolerance) or not math.isfinite(tolerance_minus) or not math.isfinite(tolerance_plus):
        raise ValueError(f"{item.name} tolerance must be finite.")
    if tolerance < 0.0 or tolerance_minus < 0.0 or tolerance_plus < 0.0:
        raise ValueError(f"{item.name} tolerance must be non-negative.")
    if not math.isfinite(sigma_coverage) or sigma_coverage <= 0.0:
        raise ValueError("Sigma coverage must be positive.")


def _validated_sigma_coverage(value: float) -> float:
    try:
        sigma_coverage = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Sigma coverage must be numeric.") from exc
    if not math.isfinite(sigma_coverage) or sigma_coverage <= 0.0:
        raise ValueError("Sigma coverage must be positive.")
    return sigma_coverage


def _percentile(sorted_samples: list[float], fraction: float) -> float:
    if not sorted_samples:
        return 0.0
    position = fraction * (len(sorted_samples) - 1)
    lower_index = int(math.floor(position))
    upper_index = int(math.ceil(position))
    if lower_index == upper_index:
        return sorted_samples[lower_index]
    lower_weight = upper_index - position
    upper_weight = position - lower_index
    return (
        sorted_samples[lower_index] * lower_weight
        + sorted_samples[upper_index] * upper_weight
    )


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
