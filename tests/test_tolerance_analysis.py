from __future__ import annotations

import unittest

from bolt_calculation_tool.tolerance import ToleranceDimension, calculate_stackup


class ToleranceAnalysisTest(unittest.TestCase):
    def test_default_five_flute_example_matches_saved_page(self) -> None:
        result = calculate_stackup(
            [
                ToleranceDimension("#1", 1.0, 0.005),
                ToleranceDimension("#2", 1.0, 0.005),
                ToleranceDimension("#3", 1.0, 0.005),
                ToleranceDimension("#4", 1.0, 0.005),
            ],
            target_min=0.001,
            target_max=0.022,
        )

        self.assertAlmostEqual(result.nominal, 4.0)
        self.assertAlmostEqual(result.worst_case_tolerance, 0.0200)
        self.assertAlmostEqual(result.worst_case_std_deviation, 0.0066666667)
        self.assertAlmostEqual(result.worst_case_variance, 0.0000444444)
        self.assertAlmostEqual(result.rss_tolerance, 0.0100)
        self.assertAlmostEqual(result.rss_std_deviation, 0.0033333333)
        self.assertAlmostEqual(result.rss_variance, 0.0000111111)
        self.assertAlmostEqual(result.rss_left_tail_failure_rate, 0.0)
        self.assertAlmostEqual(result.rss_right_tail_failure_rate, 1.0)

    def test_negative_tolerance_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "tolerance"):
            calculate_stackup(
                [ToleranceDimension("#1", 1.0, -0.1)],
                target_min=0.0,
                target_max=2.0,
            )

    def test_target_min_must_not_exceed_target_max(self) -> None:
        with self.assertRaisesRegex(ValueError, "Target min"):
            calculate_stackup(
                [ToleranceDimension("#1", 1.0, 0.1)],
                target_min=2.0,
                target_max=1.0,
            )


if __name__ == "__main__":
    unittest.main()
