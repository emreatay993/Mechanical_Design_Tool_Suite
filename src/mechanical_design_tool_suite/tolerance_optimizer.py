"""Bolt length ranking for the next-version tolerance tool."""

from __future__ import annotations

from dataclasses import dataclass

from .tolerance_catalog import ToleranceCatalog
from .tolerance_methods import (
    StackupPathResult,
    ThreadProtrusionResult,
    evaluate_thread_protrusion,
    status_rank,
)
from .tolerance_models import SubJoint


@dataclass(frozen=True)
class OptimizationCandidate:
    length: float
    status: str
    protrusion: float | None
    engagement: float | None
    controlling_message: str
    score: tuple[int, float, float]


@dataclass(frozen=True)
class OptimizationResult:
    recommended_length: float | None
    candidates: tuple[OptimizationCandidate, ...]
    rejected: tuple[OptimizationCandidate, ...]


def rank_bolt_lengths(
    sub_joint: SubJoint,
    stackup: StackupPathResult,
    catalog: ToleranceCatalog,
) -> OptimizationResult:
    bolt = catalog.find_bolt(sub_joint.bolt_size_id, sub_joint.bolt_type_id)
    if bolt is None:
        return OptimizationResult(recommended_length=None, candidates=(), rejected=())

    candidates: list[OptimizationCandidate] = []
    rejected: list[OptimizationCandidate] = []
    original_length = sub_joint.selected_bolt_length
    try:
        for length in bolt.lengths:
            sub_joint.selected_bolt_length = length
            protrusion = evaluate_thread_protrusion(sub_joint, stackup, catalog)
            candidate = _candidate_from_result(length, protrusion)
            if protrusion.status in {"Pass", "Warn"}:
                candidates.append(candidate)
            else:
                rejected.append(candidate)
    finally:
        sub_joint.selected_bolt_length = original_length

    candidates.sort(key=lambda item: item.score)
    rejected.sort(key=lambda item: item.length)
    recommended = candidates[0].length if candidates else None
    return OptimizationResult(
        recommended_length=recommended,
        candidates=tuple(candidates),
        rejected=tuple(rejected),
    )


def _candidate_from_result(
    length: float,
    result: ThreadProtrusionResult,
) -> OptimizationCandidate:
    margins = [
        criterion.margin
        for criterion in result.criteria
        if criterion.margin is not None and criterion.status in {"Pass", "Warn"}
    ]
    usable_margin = min(margins) if margins else -999999.0
    controlling = result.messages[0] if result.messages else ""
    if not controlling and result.criteria:
        controlling = min(
            result.criteria,
            key=lambda criterion: criterion.margin
            if criterion.margin is not None
            else -999999.0,
        ).message
    return OptimizationCandidate(
        length=length,
        status=result.status,
        protrusion=result.protrusion,
        engagement=result.engagement,
        controlling_message=controlling or result.status,
        score=(status_rank(result.status), abs(usable_margin), length),
    )
