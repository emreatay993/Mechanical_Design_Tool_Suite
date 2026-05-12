"""Calculation methods for CAD-based 1D tolerance stackups."""

from __future__ import annotations

import math

from .cad_tolerance_models import (
    AnalysisMode,
    AnalysisSettings,
    ContributionResult,
    NonOneDWarning,
    NonOneDWarningKind,
    ObjectiveEvaluation,
    QualityMetric,
    QualityResult,
    ResultStatus,
    StackupContributor,
    StackupObjective,
    StackupRequirement,
    StackupResult,
)


def calculate_stackup(
    stackup: StackupRequirement,
    settings: AnalysisSettings | None = None,
) -> StackupResult:
    settings = settings or AnalysisSettings()
    _validate_settings(settings)
    contributors = [item for item in stackup.contributors if item.include_in_stackup]
    for contributor in contributors:
        _validate_contributor(contributor)

    warnings = tuple(stackup.warnings)
    if not contributors:
        objective = _incomplete_objective()
        quality = _empty_quality(stackup)
        return StackupResult(
            stackup_id=stackup.id,
            name=stackup.name,
            analysis_mode=stackup.analysis_mode,
            nominal=0.0,
            worst_case_minus=0.0,
            worst_case_plus=0.0,
            rss_minus=0.0,
            rss_plus=0.0,
            evaluated_minus=0.0,
            evaluated_plus=0.0,
            objective=objective,
            quality=quality,
            contributors=(),
            warnings=warnings,
            status=ResultStatus.INCOMPLETE,
            validation_messages=("Add at least one CAD stackup contributor.",),
        )

    nominal = sum(item.sensitivity * item.nominal for item in contributors)
    worst_case_minus, worst_case_plus = calculate_worst_case(contributors)
    rss_minus, rss_plus = calculate_rss(contributors)
    ranked_contributors = rank_contributions(contributors)

    if stackup.analysis_mode == AnalysisMode.WORST_CASE:
        evaluated_minus = worst_case_minus
        evaluated_plus = worst_case_plus
    else:
        evaluated_minus = rss_minus
        evaluated_plus = rss_plus

    objective = evaluate_objective(
        nominal,
        evaluated_minus,
        evaluated_plus,
        stackup.objective,
    )
    quality = calculate_quality_metrics(
        nominal,
        rss_minus,
        rss_plus,
        stackup.objective,
        stackup.target_quality.metric,
        stackup.target_quality.value,
        stackup.target_quality.sigma_coverage or settings.sigma_coverage,
    )
    status = _combined_result_status(objective, quality, stackup.analysis_mode, warnings)
    return StackupResult(
        stackup_id=stackup.id,
        name=stackup.name,
        analysis_mode=stackup.analysis_mode,
        nominal=nominal,
        worst_case_minus=worst_case_minus,
        worst_case_plus=worst_case_plus,
        rss_minus=rss_minus,
        rss_plus=rss_plus,
        evaluated_minus=evaluated_minus,
        evaluated_plus=evaluated_plus,
        objective=objective,
        quality=quality,
        contributors=ranked_contributors,
        warnings=warnings,
        status=status,
        validation_messages=(),
    )


def calculate_worst_case(
    contributors: list[StackupContributor] | tuple[StackupContributor, ...],
) -> tuple[float, float]:
    minus = sum(abs(item.sensitivity) * float(item.tolerance_minus or 0.0) for item in contributors)
    plus = sum(abs(item.sensitivity) * float(item.tolerance_plus or 0.0) for item in contributors)
    return minus, plus


def calculate_rss(
    contributors: list[StackupContributor] | tuple[StackupContributor, ...],
) -> tuple[float, float]:
    minus = math.sqrt(
        sum(
            (abs(item.sensitivity) * float(item.tolerance_minus or 0.0)) ** 2
            for item in contributors
        )
    )
    plus = math.sqrt(
        sum(
            (abs(item.sensitivity) * float(item.tolerance_plus or 0.0)) ** 2
            for item in contributors
        )
    )
    return minus, plus


def rank_contributions(
    contributors: list[StackupContributor] | tuple[StackupContributor, ...],
) -> tuple[ContributionResult, ...]:
    variances: list[tuple[StackupContributor, float]] = []
    for contributor in contributors:
        envelope = max(
            abs(contributor.sensitivity) * float(contributor.tolerance_minus or 0.0),
            abs(contributor.sensitivity) * float(contributor.tolerance_plus or 0.0),
        )
        variances.append((contributor, envelope**2))
    total_variance = sum(variance for _, variance in variances)
    results = [
        ContributionResult(
            contributor_id=contributor.id,
            name=contributor.name,
            sensitivity=contributor.sensitivity,
            nominal=contributor.nominal,
            tolerance_minus=float(contributor.tolerance_minus or 0.0),
            tolerance_plus=float(contributor.tolerance_plus or 0.0),
            variance=variance,
            contribution=variance / total_variance if total_variance > 0.0 else 0.0,
        )
        for contributor, variance in variances
    ]
    return tuple(sorted(results, key=lambda item: item.contribution, reverse=True))


def evaluate_objective(
    nominal: float,
    variation_minus: float,
    variation_plus: float,
    objective: StackupObjective,
) -> ObjectiveEvaluation:
    lower_bound = objective.lower_bound()
    upper_bound = objective.upper_bound()
    result_lower = nominal - variation_minus
    result_upper = nominal + variation_plus
    lower_margin = (
        result_lower - lower_bound if lower_bound is not None else None
    )
    upper_margin = (
        upper_bound - result_upper if upper_bound is not None else None
    )
    failed_lower = lower_margin is not None and lower_margin < 0.0
    failed_upper = upper_margin is not None and upper_margin < 0.0
    status = ResultStatus.FAIL if failed_lower or failed_upper else ResultStatus.PASS
    if status == ResultStatus.PASS:
        message = "Result envelope is inside the objective."
    elif failed_lower and failed_upper:
        message = "Result envelope exceeds both objective limits."
    elif failed_lower:
        message = "Result envelope exceeds the lower objective limit."
    else:
        message = "Result envelope exceeds the upper objective limit."
    return ObjectiveEvaluation(
        status=status,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        result_lower=result_lower,
        result_upper=result_upper,
        lower_margin=lower_margin,
        upper_margin=upper_margin,
        message=message,
    )


def calculate_quality_metrics(
    nominal: float,
    rss_minus: float,
    rss_plus: float,
    objective: StackupObjective,
    target_metric: QualityMetric = QualityMetric.CPK,
    target_value: float | None = None,
    sigma_coverage: float = 3.0,
) -> QualityResult:
    sigma_coverage = _validated_positive(sigma_coverage, "Sigma coverage")
    target_metric = QualityMetric(str(target_metric))
    standard_deviation = max(rss_minus, rss_plus) / sigma_coverage
    lower_bound = objective.lower_bound()
    upper_bound = objective.upper_bound()

    if standard_deviation == 0.0:
        cp = _infinite_if_bounded(lower_bound, upper_bound)
        sigma = _zero_variation_sigma(nominal, lower_bound, upper_bound)
        cpk = None if sigma is None else sigma / 3.0
        yield_probability = 1.0 if sigma is None or sigma >= 0.0 else 0.0
    else:
        lower_distance = (
            nominal - lower_bound if lower_bound is not None else None
        )
        upper_distance = (
            upper_bound - nominal if upper_bound is not None else None
        )
        distances = [
            distance
            for distance in (lower_distance, upper_distance)
            if distance is not None
        ]
        sigma = min(distances) / standard_deviation if distances else None
        cpk = sigma / 3.0 if sigma is not None else None
        cp = (
            (upper_bound - lower_bound) / (6.0 * standard_deviation)
            if lower_bound is not None and upper_bound is not None
            else None
        )
        yield_probability = _normal_probability_between(
            nominal,
            standard_deviation,
            lower_bound,
            upper_bound,
        )

    status = _quality_status(
        target_metric,
        target_value,
        cpk,
        sigma,
        yield_probability,
    )
    return QualityResult(
        mean=nominal,
        standard_deviation=standard_deviation,
        cp=cp,
        cpk=cpk,
        sigma=sigma,
        yield_probability=yield_probability,
        target_metric=target_metric,
        target_value=target_value,
        status=status,
    )


def detect_non_1d_warnings(
    *,
    offset_distance: float | None = None,
    direction_alignment_cosine: float | None = None,
    has_rotational_constraints: bool = False,
    interface_count: int | None = None,
    projection_sensitivity: float | None = None,
    settings: AnalysisSettings | None = None,
) -> tuple[NonOneDWarning, ...]:
    settings = settings or AnalysisSettings()
    warnings: list[NonOneDWarning] = []
    if (
        offset_distance is not None
        and abs(offset_distance) > settings.lateral_offset_warning_threshold
    ):
        warnings.append(
            NonOneDWarning(
                NonOneDWarningKind.OFFSET_FEATURES,
                "Endpoint or constraint features are laterally offset from the stack direction.",
                observed_value=abs(offset_distance),
                threshold=settings.lateral_offset_warning_threshold,
            )
        )
    if (
        direction_alignment_cosine is not None
        and abs(direction_alignment_cosine) < settings.min_direction_alignment
    ):
        warnings.append(
            NonOneDWarning(
                NonOneDWarningKind.DIRECTION_MISALIGNMENT,
                "Selected stack direction is not aligned with a dominant feature axis or normal.",
                observed_value=abs(direction_alignment_cosine),
                threshold=settings.min_direction_alignment,
            )
        )
    if has_rotational_constraints:
        warnings.append(
            NonOneDWarning(
                NonOneDWarningKind.ROTATIONAL_CONSTRAINT,
                "Loop includes cylindrical or rotational constraints that may amplify variation.",
            )
        )
    if (
        interface_count is not None
        and interface_count > settings.multi_interface_warning_count
    ):
        warnings.append(
            NonOneDWarning(
                NonOneDWarningKind.MULTI_INTERFACE_LOOP,
                "Loop spans enough interfaces that rotations may affect the 1D result.",
                observed_value=float(interface_count),
                threshold=float(settings.multi_interface_warning_count),
            )
        )
    if (
        projection_sensitivity is not None
        and abs(projection_sensitivity)
        > settings.projection_sensitivity_warning_threshold
    ):
        warnings.append(
            NonOneDWarning(
                NonOneDWarningKind.SENSITIVE_PROJECTION,
                "Projected contributor effect is sensitive to direction or annotation plane choice.",
                observed_value=abs(projection_sensitivity),
                threshold=settings.projection_sensitivity_warning_threshold,
            )
        )
    return tuple(warnings)


def status_rank(status: ResultStatus | str) -> int:
    status_value = str(status.value if isinstance(status, ResultStatus) else status)
    return {
        ResultStatus.PASS.value: 0,
        ResultStatus.WARN.value: 1,
        ResultStatus.FAIL.value: 2,
        ResultStatus.INCOMPLETE.value: 3,
    }.get(status_value, 3)


def _combined_result_status(
    objective: ObjectiveEvaluation,
    quality: QualityResult,
    analysis_mode: AnalysisMode,
    warnings: tuple[NonOneDWarning, ...],
) -> ResultStatus:
    if objective.status == ResultStatus.FAIL:
        return ResultStatus.FAIL
    if analysis_mode == AnalysisMode.STATISTICAL and quality.status == ResultStatus.FAIL:
        return ResultStatus.FAIL
    if warnings:
        return ResultStatus.WARN
    return ResultStatus.PASS


def _validate_settings(settings: AnalysisSettings) -> None:
    _validated_positive(settings.sigma_coverage, "Sigma coverage")
    _validated_positive(settings.default_target_cpk, "Default target Cpk")


def _validate_contributor(contributor: StackupContributor) -> None:
    values = {
        "nominal": contributor.nominal,
        "sensitivity": contributor.sensitivity,
        "tolerance_minus": contributor.tolerance_minus or 0.0,
        "tolerance_plus": contributor.tolerance_plus or 0.0,
    }
    for label, value in values.items():
        if not math.isfinite(float(value)):
            raise ValueError(f"{contributor.name} {label} must be finite.")
    if float(contributor.tolerance_minus or 0.0) < 0.0:
        raise ValueError(f"{contributor.name} tolerance_minus must be non-negative.")
    if float(contributor.tolerance_plus or 0.0) < 0.0:
        raise ValueError(f"{contributor.name} tolerance_plus must be non-negative.")


def _validated_positive(value: float, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric.") from exc
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError(f"{label} must be positive.")
    return number


def _normal_probability_between(
    mean: float,
    standard_deviation: float,
    lower_bound: float | None,
    upper_bound: float | None,
) -> float:
    lower_probability = (
        0.0
        if lower_bound is None
        else _normal_cdf((lower_bound - mean) / standard_deviation)
    )
    upper_probability = (
        1.0
        if upper_bound is None
        else _normal_cdf((upper_bound - mean) / standard_deviation)
    )
    return max(0.0, min(1.0, upper_probability - lower_probability))


def _normal_cdf(z_score: float) -> float:
    return 0.5 * (1.0 + math.erf(z_score / math.sqrt(2.0)))


def _quality_status(
    target_metric: QualityMetric,
    target_value: float | None,
    cpk: float | None,
    sigma: float | None,
    yield_probability: float | None,
) -> ResultStatus:
    if target_value is None:
        return ResultStatus.PASS
    target = float(target_value)
    if target_metric == QualityMetric.CPK:
        return ResultStatus.PASS if cpk is not None and cpk >= target else ResultStatus.FAIL
    if target_metric == QualityMetric.SIGMA:
        return ResultStatus.PASS if sigma is not None and sigma >= target else ResultStatus.FAIL
    if target_metric == QualityMetric.YIELD:
        target_probability = target / 100.0 if target > 1.0 else target
        return (
            ResultStatus.PASS
            if yield_probability is not None and yield_probability >= target_probability
            else ResultStatus.FAIL
        )
    return ResultStatus.PASS


def _infinite_if_bounded(
    lower_bound: float | None,
    upper_bound: float | None,
) -> float | None:
    return math.inf if lower_bound is not None and upper_bound is not None else None


def _zero_variation_sigma(
    nominal: float,
    lower_bound: float | None,
    upper_bound: float | None,
) -> float | None:
    if lower_bound is not None and nominal < lower_bound:
        return -math.inf
    if upper_bound is not None and nominal > upper_bound:
        return -math.inf
    if lower_bound is None and upper_bound is None:
        return None
    return math.inf


def _empty_quality(stackup: StackupRequirement) -> QualityResult:
    return QualityResult(
        mean=0.0,
        standard_deviation=0.0,
        cp=None,
        cpk=None,
        sigma=None,
        yield_probability=None,
        target_metric=stackup.target_quality.metric,
        target_value=stackup.target_quality.value,
        status=ResultStatus.INCOMPLETE,
    )


def _incomplete_objective() -> ObjectiveEvaluation:
    return ObjectiveEvaluation(
        status=ResultStatus.INCOMPLETE,
        lower_bound=None,
        upper_bound=None,
        result_lower=0.0,
        result_upper=0.0,
        lower_margin=None,
        upper_margin=None,
        message="No active contributors are available for objective comparison.",
    )
