from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from bolt_calculation_tool.tolerance_catalog import ToleranceCatalog
from bolt_calculation_tool.tolerance_methods import calculate_sub_joint_result
from bolt_calculation_tool.tolerance_models import (
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
        self.assertEqual(len(project.joints[0].flanges), 3)
        self.assertEqual(project.joints[0].sub_joints[0].name, "JOINT A.1")

        joint = project.joints[0]
        sub_joint = joint.sub_joints[0]
        result = calculate_sub_joint_result(joint, sub_joint, self.catalog)

        self.assertAlmostEqual(result.stackup.nominal, 12.0)
        self.assertAlmostEqual(result.stackup.worst_case_deviation, 0.60)
        self.assertAlmostEqual(result.stackup.rss, 0.3535533906)
        self.assertAlmostEqual(result.stackup.one_point_five_rss, 0.5303300859)
        self.assertEqual(result.protrusion.status, "Pass")

    def test_top_four_contributor_sum_uses_largest_variances(self) -> None:
        project = create_default_project()
        joint = project.joints[0]
        sub_joint = joint.sub_joints[0]
        sub_joint.stackup_path.items.append(
            PathItem("Bracket", nominal_thickness=1.0, tolerance=0.10)
        )
        result = calculate_sub_joint_result(joint, sub_joint, self.catalog)

        self.assertEqual(len(result.stackup.contributors), 4)
        self.assertAlmostEqual(result.stackup.top_four_contributor_sum, 1.0)
        self.assertEqual(result.stackup.contributors[0].name, "Flange 2")

    def test_bolt_length_optimizer_recommends_passing_standard_length(self) -> None:
        project = create_default_project()
        joint = project.joints[0]
        sub_joint = joint.sub_joints[0]
        result = calculate_sub_joint_result(joint, sub_joint, self.catalog)
        ranked = rank_bolt_lengths(sub_joint, result.stackup, self.catalog)

        self.assertEqual(ranked.recommended_length, 17.5)
        self.assertTrue(any(candidate.status == "Fail" for candidate in ranked.rejected))

    def test_flange_changes_sync_to_linked_path_items(self) -> None:
        project = create_default_project()
        joint = project.joints[0]
        sub_joint = joint.sub_joints[0]
        joint.flanges[0].nominal_thickness = 6.0
        sync_path_with_flanges(joint, sub_joint)

        self.assertEqual(sub_joint.stackup_path.items[0].name, "Flange 1")
        self.assertAlmostEqual(sub_joint.stackup_path.items[0].nominal_thickness, 6.0)

    def test_project_round_trips_to_versioned_file(self) -> None:
        project = create_default_project()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.tolproj"
            saved_path = save_project(project, path)
            loaded = load_project(saved_path)

        self.assertEqual(loaded.schema_version, project.schema_version)
        self.assertEqual(loaded.joints[0].name, "JOINT A")
        self.assertEqual(loaded.joints[0].sub_joints[0].name, "JOINT A.1")


if __name__ == "__main__":
    unittest.main()
