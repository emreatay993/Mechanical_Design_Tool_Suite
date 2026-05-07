from __future__ import annotations

import unittest

from bolt_calculation_tool.calculations import calculate_bolt_group, resolve_constants
from bolt_calculation_tool.io import parse_load_table
from bolt_calculation_tool.sample_data import example_scenario_table_text


class ExampleScenarioBackendTest(unittest.TestCase):
    def setUp(self) -> None:
        parsed = parse_load_table(example_scenario_table_text())
        constants = resolve_constants(".2500-28", "MINOR")
        self.results = calculate_bolt_group(parsed.loads, constants)

    def test_strength_reference_rows(self) -> None:
        expected = {
            "BOLT01": (502.7, 518.9, 77.4, "Infinite", 224.9, 233.1),
            "BOLT02": (502.8, 525.3, 58.6, "Infinite", 224.9, 233.1),
            "BOLT03": (503.3, 525.3, 58.7, "Infinite", 225.1, 233.4),
            "BOLT04": (502.7, 520.8, 72.2, "Infinite", 224.9, 233.1),
            "BOLT05": (501.3, 517.5, 81.1, "Infinite", 224.3, 232.5),
            "BOLT06": (499.9, 513.8, 90.6, "Infinite", 223.6, 231.8),
            "BOLT07": (497.9, 510.5, 98.5, "Infinite", 222.8, 230.9),
            "BOLT08": (495.8, 507.1, 106.5, "Infinite", 221.8, 229.9),
            "BOLT09": (492.3, 503.0, 115.6, "Infinite", 220.2, 228.3),
        }
        for result in self.results:
            with self.subTest(result.load.name):
                tensile, fiber, lcf, life, crush_bolt, crush_nut = expected[
                    result.load.name
                ]
                self.assertAlmostEqual(result.strength.tensile_mpa, tensile, delta=0.15)
                self.assertAlmostEqual(result.strength.fiber_mpa, fiber, delta=0.20)
                self.assertAlmostEqual(result.strength.lcf_alt_mpa, lcf, delta=0.20)
                self.assertEqual(result.strength.life, life)
                self.assertAlmostEqual(
                    result.strength.crush_bolt_mpa, crush_bolt, delta=0.15
                )
                self.assertAlmostEqual(
                    result.strength.crush_nut_mpa, crush_nut, delta=0.15
                )

    def test_interaction_reference_rows(self) -> None:
        expected_margin = {
            "BOLT01": 37,
            "BOLT02": 35,
            "BOLT03": 35,
            "BOLT04": 36,
            "BOLT05": 37,
            "BOLT06": 38,
            "BOLT07": 39,
            "BOLT08": 40,
            "BOLT09": 41,
        }
        expected_bolt01 = {
            "plug_n": 10856,
            "shear_n": 166.5,
            "bending_nmm": 229.7,
            "torsion_nmm": 4.8,
            "rt": 0.709,
            "rb": 0.023,
            "rs": 0.019,
            "rst": 0.000,
        }
        for result in self.results:
            with self.subTest(result.load.name):
                self.assertEqual(
                    result.interaction.margin_percent_rounded,
                    expected_margin[result.load.name],
                )
                if result.load.name == "BOLT01":
                    interaction = result.interaction
                    self.assertAlmostEqual(
                        interaction.plug_n, expected_bolt01["plug_n"], delta=0.6
                    )
                    self.assertAlmostEqual(
                        interaction.shear_n, expected_bolt01["shear_n"], delta=0.2
                    )
                    self.assertAlmostEqual(
                        interaction.bending_nmm,
                        expected_bolt01["bending_nmm"],
                        delta=0.2,
                    )
                    self.assertAlmostEqual(
                        interaction.torsion_nmm,
                        expected_bolt01["torsion_nmm"],
                        delta=0.05,
                    )
                    self.assertAlmostEqual(interaction.rt, expected_bolt01["rt"], delta=0.011)
                    self.assertAlmostEqual(interaction.rb, expected_bolt01["rb"], delta=0.001)
                    self.assertAlmostEqual(interaction.rs, expected_bolt01["rs"], delta=0.001)
                    self.assertAlmostEqual(interaction.rst, expected_bolt01["rst"], delta=0.001)

    def test_unit_header_conversions(self) -> None:
        table = "\n".join(
            [
                "NodeID,FX[kN],FY[N],FZ[N],MX[N.m],MY[N*mm],MZ[N.mm]",
                "B1,1.5,2,3,4,5,6",
            ]
        )
        parsed = parse_load_table(table)
        load = parsed.loads[0]
        self.assertEqual(load.fx_n, 1500.0)
        self.assertEqual(load.mx_nmm, 4000.0)
        self.assertEqual(load.my_nmm, 5.0)


if __name__ == "__main__":
    unittest.main()
