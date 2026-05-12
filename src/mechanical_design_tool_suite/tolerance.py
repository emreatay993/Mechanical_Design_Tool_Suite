"""Tolerance stackup calculation utilities."""

from __future__ import annotations

from dataclasses import dataclass
import math
from statistics import NormalDist


SIGMA_COVERAGE = 3.0


@dataclass(frozen=True)
class ToleranceDimension:
    """One nominal dimension with a bilateral tolerance."""

    name: str
    nominal: float
    tolerance: float


@dataclass(frozen=True)
class DimensionAnalysis:
    """Calculated tolerance terms for one stackup dimension."""

    dimension: ToleranceDimension
    std_deviation: float
    variance: float


@dataclass(frozen=True)
class StackupAnalysis:
    """Worst-case and RSS tolerance analysis for an assembly stackup."""

    dimensions: tuple[DimensionAnalysis, ...]
    target_min: float
    target_max: float
    nominal: float
    worst_case_tolerance: float
    worst_case_std_deviation: float
    worst_case_variance: float
    rss_tolerance: float
    rss_std_deviation: float
    rss_variance: float
    rss_left_tail_failure_rate: float
    rss_right_tail_failure_rate: float

    @property
    def worst_case_min(self) -> float:
        return self.nominal - self.worst_case_tolerance

    @property
    def worst_case_max(self) -> float:
        return self.nominal + self.worst_case_tolerance

    @property
    def rss_min(self) -> float:
        return self.nominal - self.rss_tolerance

    @property
    def rss_max(self) -> float:
        return self.nominal + self.rss_tolerance


def calculate_stackup(
    dimensions: list[ToleranceDimension] | tuple[ToleranceDimension, ...],
    target_min: float,
    target_max: float,
) -> StackupAnalysis:
    """Calculate worst-case and RSS stackup terms.

    The calculator follows the Five Flute convention visible in the saved
    page: each bilateral tolerance is treated as a +/- 3 sigma interval.
    """

    clean_dimensions = _validate_dimensions(dimensions)
    target_min = _validated_number("Target min", target_min)
    target_max = _validated_number("Target max", target_max)
    if target_min > target_max:
        raise ValueError("Target min must be less than or equal to target max.")

    dimension_results = tuple(
        DimensionAnalysis(
            dimension=dimension,
            std_deviation=dimension.tolerance / SIGMA_COVERAGE,
            variance=(dimension.tolerance / SIGMA_COVERAGE) ** 2,
        )
        for dimension in clean_dimensions
    )
    nominal = sum(result.dimension.nominal for result in dimension_results)
    worst_case_tolerance = sum(
        result.dimension.tolerance for result in dimension_results
    )
    worst_case_std_deviation = worst_case_tolerance / SIGMA_COVERAGE
    worst_case_variance = worst_case_std_deviation**2
    rss_variance = sum(result.variance for result in dimension_results)
    rss_std_deviation = math.sqrt(rss_variance)
    rss_tolerance = rss_std_deviation * SIGMA_COVERAGE
    left_rate, right_rate = _rss_failure_rates(
        nominal,
        rss_std_deviation,
        target_min,
        target_max,
    )

    return StackupAnalysis(
        dimensions=dimension_results,
        target_min=target_min,
        target_max=target_max,
        nominal=nominal,
        worst_case_tolerance=worst_case_tolerance,
        worst_case_std_deviation=worst_case_std_deviation,
        worst_case_variance=worst_case_variance,
        rss_tolerance=rss_tolerance,
        rss_std_deviation=rss_std_deviation,
        rss_variance=rss_variance,
        rss_left_tail_failure_rate=left_rate,
        rss_right_tail_failure_rate=right_rate,
    )


def _validate_dimensions(
    dimensions: list[ToleranceDimension] | tuple[ToleranceDimension, ...],
) -> tuple[ToleranceDimension, ...]:
    if not dimensions:
        raise ValueError("Add at least one dimension.")

    clean_dimensions: list[ToleranceDimension] = []
    for index, dimension in enumerate(dimensions, start=1):
        name = dimension.name.strip() or f"#{index}"
        nominal = _validated_number(f"{name} nominal", dimension.nominal)
        tolerance = _validated_number(f"{name} tolerance", dimension.tolerance)
        if tolerance < 0.0:
            raise ValueError(f"{name} tolerance must be greater than or equal to 0.")
        clean_dimensions.append(
            ToleranceDimension(name=name, nominal=nominal, tolerance=tolerance)
        )
    return tuple(clean_dimensions)


def _validated_number(label: str, value: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a number.") from exc
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite.")
    return number


def _rss_failure_rates(
    nominal: float,
    std_deviation: float,
    target_min: float,
    target_max: float,
) -> tuple[float, float]:
    if std_deviation == 0.0:
        left = 1.0 if nominal < target_min else 0.0
        right = 1.0 if nominal > target_max else 0.0
        return left, right

    distribution = NormalDist(mu=nominal, sigma=std_deviation)
    left_rate = distribution.cdf(target_min)
    right_rate = 1.0 - distribution.cdf(target_max)
    return _clamp_rate(left_rate), _clamp_rate(right_rate)


def _clamp_rate(value: float) -> float:
    return min(max(value, 0.0), 1.0)
