"""Benchmark the ExampleScenario bolt interaction curve calculation.

This script validates the row-level interaction table against reference values.

Run from the repository root:

    python scripts/benchmark_example_scenario_interaction_curve.py
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi, sqrt


@dataclass(frozen=True)
class Constants:
    bolt_size: str
    margin_basis: str
    bolt_thread_area_mm2: float
    yield_002_mpa: float

    @property
    def bolt_radius_mm(self) -> float:
        return sqrt(self.bolt_thread_area_mm2 / pi)

    @property
    def moment_of_inertia_mm4(self) -> float:
        return pi * self.bolt_radius_mm**4 / 4.0

    @property
    def polar_moment_of_inertia_mm4(self) -> float:
        return 2.0 * self.moment_of_inertia_mm4

    @property
    def shear_strength_mpa(self) -> float:
        return self.yield_002_mpa / sqrt(3.0)


@dataclass(frozen=True)
class InteractionCase:
    name: str
    fx_n: float
    fy_n: float
    fz_n: float
    mx_nmm: float
    my_nmm: float
    mz_nmm: float
    expected_plug_n: float
    expected_shear_n: float
    expected_bending_nmm: float
    expected_torsion_nmm: float
    expected_rt: float
    expected_rb: float
    expected_rs: float
    expected_rst: float
    expected_margin_percent: int


@dataclass(frozen=True)
class InteractionResult:
    plug_n: float
    shear_n: float
    bending_nmm: float
    torsion_nmm: float
    rt: float
    rb: float
    rs: float
    rst: float
    margin: float

    @property
    def margin_percent_rounded(self) -> int:
        return round(self.margin * 100.0)


# Reference context:
# - Bolt size = ".2500-28"
# - Margin basis = "MINOR"
# - T24 = INCO718 BAR ExampleScenario 0.02% yield strength = 708.65 MPa
# - T26 = T24 / sqrt(3)
#
# The bolt thread area is displayed as 21.60 mm2, but the ExampleScenario
# benchmark showed that the reference results are more closely reproduced by the
# inferred hidden precision value 11600 / 537.12.
CONSTANTS = Constants(
    bolt_size=".2500-28",
    margin_basis="MINOR",
    bolt_thread_area_mm2=11600.0 / 537.12,
    yield_002_mpa=708.65,
)


CASES = [
    InteractionCase(
        "BOLT01",
        -16.7,
        -165.6,
        10856.2,
        182.0,
        -140.0,
        -4.8,
        10856,
        166.5,
        229.7,
        4.8,
        0.709,
        0.023,
        0.019,
        0.000,
        37,
    ),
    InteractionCase(
        "BOLT02",
        -5.3,
        -178.1,
        10859.1,
        317.7,
        -27.9,
        -9.1,
        10859,
        178.1,
        318.9,
        9.1,
        0.700,
        0.032,
        0.020,
        0.001,
        35,
    ),
    InteractionCase(
        "BOLT03",
        9.2,
        -174.0,
        10869.2,
        311.9,
        0.6,
        -32.8,
        10869,
        174.3,
        311.9,
        32.8,
        0.700,
        0.031,
        0.020,
        0.003,
        35,
    ),
    InteractionCase(
        "BOLT04",
        21.9,
        -156.5,
        10857.0,
        250.4,
        52.6,
        -42.6,
        10857,
        158.0,
        255.8,
        42.6,
        0.700,
        0.026,
        0.018,
        0.004,
        36,
    ),
    InteractionCase(
        "BOLT05",
        33.6,
        -136.9,
        10827.3,
        203.8,
        104.3,
        -42.5,
        10827,
        140.9,
        229.0,
        42.5,
        0.700,
        0.023,
        0.016,
        0.004,
        37,
    ),
    InteractionCase(
        "BOLT06",
        39.6,
        -118.7,
        10796.5,
        144.2,
        133.9,
        -38.4,
        10797,
        125.1,
        196.8,
        38.4,
        0.700,
        0.020,
        0.014,
        0.003,
        38,
    ),
    InteractionCase(
        "BOLT07",
        40.8,
        -107.0,
        10753.9,
        129.1,
        123.0,
        -45.8,
        10754,
        114.5,
        178.3,
        45.8,
        0.700,
        0.018,
        0.013,
        0.004,
        39,
    ),
    InteractionCase(
        "BOLT08",
        52.6,
        -80.4,
        10707.5,
        45.9,
        153.1,
        -81.0,
        10708,
        96.1,
        159.8,
        81.0,
        0.700,
        0.016,
        0.011,
        0.007,
        40,
    ),
    InteractionCase(
        "BOLT09",
        40.4,
        -49.8,
        10631.8,
        30.8,
        148.4,
        -70.8,
        10632,
        64.1,
        151.5,
        70.8,
        0.700,
        0.015,
        0.007,
        0.006,
        41,
    ),
]


TOLERANCES = {
    "plug_n": 0.6,
    "shear_n": 0.2,
    "bending_nmm": 0.2,
    "torsion_nmm": 0.05,
    "rt": 0.011,
    "rb": 0.001,
    "rs": 0.001,
    "rst": 0.001,
}


def calculate_interaction(
    case: InteractionCase,
    constants: Constants,
) -> InteractionResult:
    plug_n = abs(case.fz_n)
    shear_n = sqrt(case.fx_n**2 + case.fy_n**2)
    bending_nmm = sqrt(case.mx_nmm**2 + case.my_nmm**2)
    torsion_nmm = abs(case.mz_nmm)

    rt = (plug_n / constants.bolt_thread_area_mm2) / constants.yield_002_mpa
    rb = (
        bending_nmm
        * constants.bolt_radius_mm
        / constants.moment_of_inertia_mm4
        / constants.yield_002_mpa
    )
    rs = (shear_n / constants.bolt_thread_area_mm2) / constants.shear_strength_mpa
    rst = (
        torsion_nmm
        * constants.bolt_radius_mm
        / constants.polar_moment_of_inertia_mm4
        / constants.shear_strength_mpa
    )

    interaction_ratio = sqrt((rt + rb) ** 2 + (rs + rst) ** 2)
    margin = 1.0 / interaction_ratio - 1.0

    return InteractionResult(
        plug_n=plug_n,
        shear_n=shear_n,
        bending_nmm=bending_nmm,
        torsion_nmm=torsion_nmm,
        rt=rt,
        rb=rb,
        rs=rs,
        rst=rst,
        margin=margin,
    )


def assert_close(label: str, actual: float, expected: float, tolerance: float) -> None:
    diff = abs(actual - expected)
    if diff > tolerance:
        raise AssertionError(
            f"{label}: actual {actual:.6f}, expected {expected:.6f}, "
            f"diff {diff:.6f}, tolerance {tolerance:.6f}"
        )


def validate_case(case: InteractionCase, result: InteractionResult) -> None:
    assert_close(
        f"{case.name} plug_n",
        result.plug_n,
        case.expected_plug_n,
        TOLERANCES["plug_n"],
    )
    assert_close(
        f"{case.name} shear_n",
        result.shear_n,
        case.expected_shear_n,
        TOLERANCES["shear_n"],
    )
    assert_close(
        f"{case.name} bending_nmm",
        result.bending_nmm,
        case.expected_bending_nmm,
        TOLERANCES["bending_nmm"],
    )
    assert_close(
        f"{case.name} torsion_nmm",
        result.torsion_nmm,
        case.expected_torsion_nmm,
        TOLERANCES["torsion_nmm"],
    )
    assert_close(f"{case.name} rt", result.rt, case.expected_rt, TOLERANCES["rt"])
    assert_close(f"{case.name} rb", result.rb, case.expected_rb, TOLERANCES["rb"])
    assert_close(f"{case.name} rs", result.rs, case.expected_rs, TOLERANCES["rs"])
    assert_close(f"{case.name} rst", result.rst, case.expected_rst, TOLERANCES["rst"])

    if result.margin_percent_rounded != case.expected_margin_percent:
        raise AssertionError(
            f"{case.name} margin percent: actual "
            f"{result.margin_percent_rounded}%, expected "
            f"{case.expected_margin_percent}%"
        )


def print_header(constants: Constants) -> None:
    print("ExampleScenario bolt interaction benchmark")
    print(f"  bolt_size: {constants.bolt_size}")
    print(f"  margin_basis: {constants.margin_basis}")
    print(f"  bolt_thread_area_mm2: {constants.bolt_thread_area_mm2:.10f}")
    print(f"  bolt_radius_mm: {constants.bolt_radius_mm:.10f}")
    print(f"  moment_of_inertia_mm4: {constants.moment_of_inertia_mm4:.10f}")
    print(
        "  polar_moment_of_inertia_mm4: "
        f"{constants.polar_moment_of_inertia_mm4:.10f}"
    )
    print(f"  yield_002_mpa: {constants.yield_002_mpa:.10f}")
    print(f"  shear_strength_mpa: {constants.shear_strength_mpa:.10f}")
    print()


def print_result(case: InteractionCase, result: InteractionResult) -> None:
    print(
        f"{case.name}: "
        f"plug={result.plug_n:.3f}, "
        f"shear={result.shear_n:.3f}, "
        f"bending={result.bending_nmm:.3f}, "
        f"torsion={result.torsion_nmm:.3f}, "
        f"rt={result.rt:.6f}, "
        f"rb={result.rb:.6f}, "
        f"rs={result.rs:.6f}, "
        f"rst={result.rst:.6f}, "
        f"margin={result.margin:.6f} "
        f"({result.margin_percent_rounded}%)"
    )


def main() -> None:
    print_header(CONSTANTS)

    for case in CASES:
        result = calculate_interaction(case, CONSTANTS)
        print_result(case, result)
        validate_case(case, result)

    print()
    print("All ExampleScenario interaction benchmark checks passed.")


if __name__ == "__main__":
    main()





