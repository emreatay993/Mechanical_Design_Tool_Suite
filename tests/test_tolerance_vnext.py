from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from bolt_calculation_tool.tolerance_catalog import ToleranceCatalog
from bolt_calculation_tool.tolerance_methods import (
    calculate_stackup_path,
    calculate_sub_joint_result,
)
from bolt_calculation_tool.tolerance_models import (
    Flange,
    MethodSettings,
    PathItem,
    create_default_project,
    sync_path_with_flanges,
)
from bolt_calculation_tool.tolerance_optimizer import rank_bolt_lengths
from bolt_calculation_tool.tolerance_project_io import load_project, save_project


class ToleranceVNextDomainTest(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = ToleranceCatalog.builtin()

    def test_default_project_creates_joint_sub_joint_and_stackup(self) -> None:
        project = create_default_project()
        self.assertEqual(project.joints[0].name, "JOINT A")
        self.assertEqual(len(project.joints[0].flanges), 2)
        self.assertEqual(project.joints[0].sub_joints[0].name, "JOINT A.1")

        joint = project.joints[0]
        sub_joint = joint.sub_joints[0]
        result = calculate_sub_joint_result(joint, sub_joint, self.catalog)

        self.assertAlmostEqual(result.stackup.nominal, 9.0)
        self.assertAlmostEqual(result.stackup.worst_case_deviation, 0.40)
        self.assertAlmostEqual(result.stackup.rss, 0.2915475947)
        self.assertAlmostEqual(result.stackup.one_point_five_rss, 0.4373213921)
        self.assertEqual(result.protrusion.status, "Pass")

    def test_top_four_contributor_sum_uses_largest_variances(self) -> None:
        project = create_default_project()
        joint = project.joints[0]
        sub_joint = joint.sub_joints[0]
        sub_joint.stackup_path.items.append(
            PathItem("Bracket", nominal_thickness=1.0, tolerance=0.10)
        )
        result = calculate_sub_joint_result(joint, sub_joint, self.catalog)

        self.assertEqual(len(result.stackup.contributors), 3)
        self.assertAlmostEqual(result.stackup.top_four_contributor_sum, 1.0)
        self.assertEqual(result.stackup.contributors[0].name, "Flange 2")

    def test_bolt_length_optimizer_recommends_passing_standard_length(self) -> None:
        project = create_default_project()
        joint = project.joints[0]
        sub_joint = joint.sub_joints[0]
        result = calculate_sub_joint_result(joint, sub_joint, self.catalog)
        ranked = rank_bolt_lengths(sub_joint, result.stackup, self.catalog)

        self.assertEqual(ranked.recommended_length, 14.0)
        self.assertTrue(any(candidate.status == "Pass" for candidate in ranked.candidates))

    def test_flange_changes_sync_to_linked_path_items(self) -> None:
        project = create_default_project()
        joint = project.joints[0]
        sub_joint = joint.sub_joints[0]
        joint.flanges[0].nominal_thickness = 6.0
        sync_path_with_flanges(joint, sub_joint)

        self.assertEqual(sub_joint.stackup_path.items[0].name, "Flange 1")
        self.assertAlmostEqual(sub_joint.stackup_path.items[0].nominal_thickness, 6.0)

    def test_flange_delete_sync_removes_stale_linked_path_items(self) -> None:
        project = create_default_project()
        joint = project.joints[0]
        sub_joint = joint.sub_joints[0]
        removed_flange = joint.flanges[0]
        sub_joint.stackup_path.items.append(
            PathItem("Shim", nominal_thickness=1.0, tolerance=0.05)
        )

        joint.flanges = [flange for flange in joint.flanges if flange.id != removed_flange.id]
        sync_path_with_flanges(joint, sub_joint)

        self.assertEqual(len(joint.flanges), 1)
        self.assertFalse(
            any(item.source_id == removed_flange.id for item in sub_joint.stackup_path.items)
        )
        self.assertEqual(sub_joint.stackup_path.items[-1].name, "Shim")

    def test_project_round_trip_preserves_non_default_flange_counts(self) -> None:
        project = create_default_project()
        joint = project.joints[0]
        joint.flanges = [
            Flange("Only flange", nominal_thickness=3.0, tolerance=0.1),
            Flange("Second flange", nominal_thickness=2.0, tolerance=0.2),
            Flange("Third flange", nominal_thickness=1.0, tolerance=0.3),
        ]
        sync_path_with_flanges(joint, joint.sub_joints[0])

        with tempfile.TemporaryDirectory() as directory:
            path = save_project(project, Path(directory) / "custom_flanges.tolproj")
            loaded = load_project(path)

        self.assertEqual(len(loaded.joints[0].flanges), 3)
        self.assertEqual(loaded.joints[0].flanges[0].name, "Only flange")

    def test_project_round_trips_to_versioned_file(self) -> None:
        project = create_default_project()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.tolproj"
            saved_path = save_project(project, path)
            loaded = load_project(saved_path)

        self.assertEqual(loaded.schema_version, project.schema_version)
        self.assertEqual(loaded.joints[0].name, "JOINT A")
        self.assertEqual(loaded.joints[0].sub_joints[0].name, "JOINT A.1")

    def test_asymmetric_tolerances_produce_directional_results(self) -> None:
        result = calculate_stackup_path(
            [
                PathItem(
                    "A",
                    nominal_thickness=1.0,
                    tolerance=0.30,
                    tolerance_minus=0.10,
                    tolerance_plus=0.30,
                ),
                PathItem(
                    "B",
                    nominal_thickness=1.0,
                    tolerance=0.20,
                    tolerance_minus=0.20,
                    tolerance_plus=0.05,
                ),
            ]
        )

        self.assertAlmostEqual(result.nominal, 2.0)
        self.assertAlmostEqual(result.worst_case_minus, 0.30)
        self.assertAlmostEqual(result.worst_case_plus, 0.35)
        self.assertAlmostEqual(result.worst_case_deviation, 0.35)
        self.assertAlmostEqual(result.rss_minus, (0.10**2 + 0.20**2) ** 0.5)
        self.assertAlmostEqual(result.rss_plus, (0.30**2 + 0.05**2) ** 0.5)
        self.assertEqual(result.contributors[0].name, "A")

    def test_monte_carlo_is_deterministic_when_enabled(self) -> None:
        project = create_default_project()
        joint = project.joints[0]
        sub_joint = joint.sub_joints[0]
        settings = sub_joint.stackup_path.method_settings
        settings.monte_carlo_enabled = True
        settings.monte_carlo_sample_count = 5000
        settings.monte_carlo_seed = 42

        first = calculate_sub_joint_result(joint, sub_joint, self.catalog).stackup
        second = calculate_sub_joint_result(joint, sub_joint, self.catalog).stackup

        self.assertIsNotNone(first.monte_carlo)
        self.assertEqual(first.monte_carlo, second.monte_carlo)
        self.assertAlmostEqual(first.monte_carlo.mean, first.nominal, delta=0.02)
        self.assertAlmostEqual(
            first.monte_carlo.std_deviation,
            first.rss / MethodSettings().sigma_coverage,
            delta=0.02,
        )

    def test_monte_carlo_settings_round_trip_with_project(self) -> None:
        project = create_default_project()
        settings = project.joints[0].sub_joints[0].stackup_path.method_settings
        settings.monte_carlo_enabled = True
        settings.monte_carlo_sample_count = 2500
        settings.monte_carlo_seed = 99

        with tempfile.TemporaryDirectory() as directory:
            path = save_project(project, Path(directory) / "monte_carlo.tolproj")
            loaded = load_project(path)

        loaded_settings = loaded.joints[0].sub_joints[0].stackup_path.method_settings
        self.assertTrue(loaded_settings.monte_carlo_enabled)
        self.assertEqual(loaded_settings.monte_carlo_sample_count, 2500)
        self.assertEqual(loaded_settings.monte_carlo_seed, 99)


if __name__ == "__main__":
    unittest.main()
