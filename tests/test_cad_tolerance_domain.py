from __future__ import annotations

import math
import unittest

from mechanical_design_tool_suite.cad_tolerance_methods import (
    calculate_stackup,
    detect_non_1d_warnings,
    rank_contributions,
)
from mechanical_design_tool_suite.cad_tolerance_models import (
    AnalysisMode,
    CadToleranceProject,
    FeatureKind,
    FeatureReference,
    GeometricControlType,
    GeometricTolerance,
    NonOneDWarningKind,
    QualityMetric,
    QualityTarget,
    ResultStatus,
    ShapeKind,
    ShapeReference,
    StackupContributor,
    StackupObjective,
    StackupRequirement,
    ToleranceType,
)


class CadToleranceDomainTest(unittest.TestCase):
    def test_symmetric_stackup_uses_signed_nominal_and_absolute_variation(self) -> None:
        stackup = StackupRequirement(
            "bushing alignment",
            objective=StackupObjective.bilateral(nominal=3.0, tolerance=0.50),
            contributors=[
                StackupContributor("left face", nominal=10.0, tolerance=0.10),
                StackupContributor(
                    "right face",
                    nominal=7.0,
                    tolerance=0.20,
                    sensitivity=-1.0,
                ),
            ],
        )

        result = calculate_stackup(stackup)

        self.assertAlmostEqual(result.nominal, 3.0)
        self.assertAlmostEqual(result.worst_case_minus, 0.30)
        self.assertAlmostEqual(result.worst_case_plus, 0.30)
        self.assertAlmostEqual(result.rss_minus, math.sqrt(0.10**2 + 0.20**2))
        self.assertEqual(result.status, ResultStatus.PASS)
        self.assertEqual(result.contributors[0].name, "right face")
        self.assertAlmostEqual(result.contributors[0].contribution, 0.80)

    def test_asymmetric_tolerances_preserve_directional_minus_plus(self) -> None:
        stackup = StackupRequirement(
            "asymmetric limits",
            objective=StackupObjective.bilateral(nominal=-3.0, tolerance=0.90),
            contributors=[
                StackupContributor(
                    "slot",
                    nominal=5.0,
                    tolerance=0.0,
                    tolerance_minus=0.10,
                    tolerance_plus=0.30,
                    tolerance_type=ToleranceType.LIMITS,
                ),
                StackupContributor(
                    "pin",
                    nominal=4.0,
                    tolerance=0.0,
                    tolerance_minus=0.20,
                    tolerance_plus=0.05,
                    sensitivity=-2.0,
                    tolerance_type=ToleranceType.LIMITS,
                ),
            ],
        )

        result = calculate_stackup(stackup)

        self.assertAlmostEqual(result.nominal, -3.0)
        self.assertAlmostEqual(result.worst_case_minus, 0.10 + 2.0 * 0.20)
        self.assertAlmostEqual(result.worst_case_plus, 0.30 + 2.0 * 0.05)
        self.assertAlmostEqual(
            result.rss_minus,
            math.sqrt(0.10**2 + (2.0 * 0.20) ** 2),
        )
        self.assertAlmostEqual(
            result.rss_plus,
            math.sqrt(0.30**2 + (2.0 * 0.05) ** 2),
        )
        self.assertEqual(result.status, ResultStatus.PASS)

    def test_empty_stackup_returns_incomplete_without_division_errors(self) -> None:
        result = calculate_stackup(StackupRequirement("empty"))

        self.assertEqual(result.status, ResultStatus.INCOMPLETE)
        self.assertEqual(result.contributors, ())
        self.assertIn("Add at least one", result.validation_messages[0])

    def test_objective_failure_sets_fail_status(self) -> None:
        stackup = StackupRequirement(
            "too wide",
            objective=StackupObjective.bilateral(nominal=0.0, tolerance=0.25),
            contributors=[
                StackupContributor("A", nominal=0.0, tolerance=0.20),
                StackupContributor("B", nominal=0.0, tolerance=0.20),
            ],
        )

        result = calculate_stackup(stackup)

        self.assertEqual(result.objective.status, ResultStatus.FAIL)
        self.assertEqual(result.status, ResultStatus.FAIL)
        self.assertLess(result.objective.lower_margin, 0.0)
        self.assertLess(result.objective.upper_margin, 0.0)

    def test_rss_mode_evaluates_objective_against_rss_envelope(self) -> None:
        stackup = StackupRequirement(
            "rss pass",
            analysis_mode=AnalysisMode.RSS,
            objective=StackupObjective.bilateral(nominal=0.0, tolerance=0.30),
            contributors=[
                StackupContributor("A", nominal=0.0, tolerance=0.20),
                StackupContributor("B", nominal=0.0, tolerance=0.20),
            ],
        )

        result = calculate_stackup(stackup)

        self.assertAlmostEqual(result.evaluated_plus, math.sqrt(0.20**2 + 0.20**2))
        self.assertEqual(result.objective.status, ResultStatus.PASS)
        self.assertEqual(result.status, ResultStatus.PASS)

    def test_quality_metrics_are_deterministic_for_cpk_target(self) -> None:
        stackup = StackupRequirement(
            "statistical coax",
            analysis_mode=AnalysisMode.STATISTICAL,
            objective=StackupObjective.bilateral(nominal=0.0, tolerance=0.60),
            target_quality=QualityTarget(QualityMetric.CPK, 2.0),
            contributors=[StackupContributor("A", nominal=0.0, tolerance=0.30)],
        )

        result = calculate_stackup(stackup)

        self.assertAlmostEqual(result.quality.standard_deviation, 0.10)
        self.assertAlmostEqual(result.quality.cpk, 2.0)
        self.assertAlmostEqual(result.quality.sigma, 6.0)
        self.assertEqual(result.quality.status, ResultStatus.PASS)
        self.assertEqual(result.status, ResultStatus.PASS)

    def test_contribution_ranking_handles_zero_variance(self) -> None:
        contributors = (
            StackupContributor("A", nominal=1.0, tolerance=0.0),
            StackupContributor("B", nominal=2.0, tolerance=0.0),
        )

        ranked = rank_contributions(contributors)

        self.assertEqual(len(ranked), 2)
        self.assertTrue(all(item.contribution == 0.0 for item in ranked))

    def test_geometric_tolerance_contributor_uses_derived_1d_effect(self) -> None:
        geometric = GeometricTolerance(
            GeometricControlType.RUNOUT,
            tolerance_value=0.10,
            datum_references=["A"],
            derived_minus=0.05,
            derived_plus=0.05,
            conversion_note="Runout projected onto stack direction.",
        )
        contributor = StackupContributor(
            "runout of ID to A",
            nominal=0.0,
            tolerance=0.0,
            tolerance_type=ToleranceType.GEOMETRIC,
            geometric_tolerance=geometric,
        )

        self.assertAlmostEqual(contributor.tolerance_minus, 0.05)
        self.assertAlmostEqual(contributor.tolerance_plus, 0.05)
        self.assertEqual(contributor.geometric_tolerance.datum_references, ["A"])

    def test_manual_gdt_defaults_match_demo_half_value_effects(self) -> None:
        cases = (
            (GeometricControlType.RUNOUT, 0.10, 0.05),
            (GeometricControlType.POSITION, 0.15, 0.075),
            (GeometricControlType.PROFILE, 0.50, 0.25),
        )

        for control_type, tolerance_value, expected_effect in cases:
            with self.subTest(control_type=control_type):
                geometric = GeometricTolerance(
                    control_type=control_type,
                    tolerance_value=tolerance_value,
                    datum_references=["A"],
                )
                contributor = StackupContributor(
                    f"{control_type.value} to A",
                    nominal=0.0,
                    tolerance=0.0,
                    tolerance_type=ToleranceType.GEOMETRIC,
                    geometric_tolerance=geometric,
                )

                self.assertAlmostEqual(contributor.tolerance_minus, expected_effect)
                self.assertAlmostEqual(contributor.tolerance_plus, expected_effect)
                self.assertIn("1D contributor", geometric.conversion_note)

    def test_non_1d_warning_detection_uses_configurable_scalar_inputs(self) -> None:
        warnings = detect_non_1d_warnings(
            offset_distance=2.0,
            direction_alignment_cosine=0.80,
            has_rotational_constraints=True,
            interface_count=5,
            projection_sensitivity=0.20,
        )

        self.assertEqual(len(warnings), 5)
        self.assertEqual(warnings[0].warning_kind, NonOneDWarningKind.OFFSET_FEATURES)
        self.assertTrue(all(warning.severity == ResultStatus.WARN for warning in warnings))

    def test_stackup_with_warning_returns_warn_when_objective_passes(self) -> None:
        warnings = list(detect_non_1d_warnings(has_rotational_constraints=True))
        stackup = StackupRequirement(
            "warning pass",
            objective=StackupObjective.bilateral(nominal=0.0, tolerance=1.0),
            warnings=warnings,
            contributors=[StackupContributor("A", nominal=0.0, tolerance=0.1)],
        )

        result = calculate_stackup(stackup)

        self.assertEqual(result.objective.status, ResultStatus.PASS)
        self.assertEqual(result.status, ResultStatus.WARN)
        self.assertEqual(len(result.warnings), 1)

    def test_domain_models_round_trip_nested_serializable_references(self) -> None:
        shape = ShapeReference(
            document_id="cad_1",
            assembly_path=["caster", "bushing:1"],
            shape_type=ShapeKind.FACE,
            kernel_label="0:1:2:3",
            fallback_display_name="bushing face",
        )
        feature = FeatureReference(
            name="Hole1",
            feature_type=FeatureKind.CYLINDER,
            shape_reference=shape,
            datum_label="A",
        )
        stackup = StackupRequirement(
            "round trip",
            contributors=[
                StackupContributor(
                    "Dimension1",
                    nominal=12.0,
                    tolerance=0.05,
                    source_feature=feature,
                    shared_with_stackup_ids=["overall height"],
                )
            ],
        )
        project = CadToleranceProject(stackups=[stackup])

        loaded = CadToleranceProject.from_dict(project.to_dict())

        self.assertEqual(loaded.project_type, "cad_1d_tolerance")
        self.assertEqual(loaded.stackups[0].contributors[0].source_feature.datum_label, "A")
        self.assertEqual(
            loaded.stackups[0].contributors[0].source_feature.shape_reference.shape_type,
            ShapeKind.FACE,
        )


if __name__ == "__main__":
    unittest.main()
