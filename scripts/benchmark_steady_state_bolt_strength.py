"""Benchmark the decoded Steady-State Condition bolt strength calculation.

This script is intentionally standalone. It documents the formulas decoded from
the Excel workbook screenshots and validates them against screen-visible
reference values for the first nine Steady-State Condition bolt rows.

Run from the repository root:

    python scripts/benchmark_steady_state_bolt_strength.py
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi, sqrt


@dataclass(frozen=True)
class Constants:
    bolt_size: str
    margin_basis: str
    bolt_thread_area_mm2: float
    bolt_hole_countersink_dia_mm: float
    bolt_head_dia_mm: float
    nut_contact_crush_area_min_mm2: float
    assembly_tensile_stress_mpa: float
    walker_coefficient: float

    @property
    def bolt_radius_mm(self) -> float:
        return sqrt(self.bolt_thread_area_mm2 / pi)

    @property
    def moment_of_inertia_mm4(self) -> float:
        return pi * self.bolt_radius_mm**4 / 4.0

    @property
    def bolt_contact_crush_area_mm2(self) -> float:
        return (
            pi
            * (
                self.bolt_head_dia_mm**2
                - self.bolt_hole_countersink_dia_mm**2
            )
            / 4.0
        )


@dataclass(frozen=True)
class BoltCase:
    name: str
    fz_n: float
    mx_nmm: float
    my_nmm: float
    expected_tensile_mpa: float
    expected_fiber_mpa: float
    expected_lcf_alt_mpa: float
    expected_life: str
    expected_crush_bolt_mpa: float
    expected_crush_nut_mpa: float


@dataclass(frozen=True)
class BoltResult:
    tensile_mpa: float
    fiber_mpa: float
    lcf_alt_mpa: float
    life: str
    crush_bolt_mpa: float
    crush_nut_mpa: float


# Spreadsheet context:
# - N6 = ".2500-28"
# - N10 = "MINOR"
# - O22 displays 537.12 MPa.
#
# The workbook displays O12 as 21.60 mm2, but 11600 / 537.12 gives
# 21.5966636878 mm2. Using that inferred hidden-precision area reproduces the
# visible workbook rows better than using rounded 21.60.
#
# N44 displays 0.64. The exact LCF lookup value is not visible in the screenshots;
# 0.6384 is inferred from the visible LCF outputs. Replace it with the exported
# workbook value when the original spreadsheet is available.
CONSTANTS = Constants(
    bolt_size=".2500-28",
    margin_basis="MINOR",
    bolt_thread_area_mm2=11600.0 / 537.12,
    bolt_hole_countersink_dia_mm=7.90,
    bolt_head_dia_mm=11.13,
    nut_contact_crush_area_min_mm2=46.58,
    assembly_tensile_stress_mpa=537.12,
    walker_coefficient=0.6384,
)


CASES = [
    BoltCase("BOLT01", 10856, 182, -140, 502.7, 518.9, 77.4, "Infinite", 224.9, 233.1),
    BoltCase("BOLT02", 10859, 318, -28, 502.8, 525.3, 58.6, "Infinite", 224.9, 233.1),
    BoltCase("BOLT03", 10869, 312, 1, 503.3, 525.3, 58.7, "Infinite", 225.1, 233.4),
    BoltCase("BOLT04", 10857, 250, 53, 502.7, 520.8, 72.2, "Infinite", 224.9, 233.1),
    BoltCase("BOLT05", 10827, 204, 104, 501.3, 517.5, 81.1, "Infinite", 224.3, 232.5),
    BoltCase("BOLT06", 10797, 144, 134, 499.9, 513.8, 90.6, "Infinite", 223.6, 231.8),
    BoltCase("BOLT07", 10754, 129, 123, 497.9, 510.5, 98.5, "Infinite", 222.8, 230.9),
    BoltCase("BOLT08", 10708, 46, 153, 495.8, 507.1, 106.5, "Infinite", 221.8, 229.9),
    BoltCase("BOLT09", 10632, 31, 148, 492.3, 503.0, 115.6, "Infinite", 220.2, 228.3),
]


TOLERANCES = {
    "tensile_mpa": 0.15,
    "fiber_mpa": 0.20,
    "lcf_alt_mpa": 0.20,
    "crush_bolt_mpa": 0.15,
    "crush_nut_mpa": 0.15,
}


def fatigue_life_bucket(lcf_alt_mpa: float) -> str:
    """Return the workbook life bucket for the INCO718 573K table."""
    if lcf_alt_mpa <= 167.0:
        return "Infinite"
    if lcf_alt_mpa <= 206.2:
        return ">10^7"
    if lcf_alt_mpa <= 300.0:
        return ">10^6"
    if lcf_alt_mpa <= 412.2:
        return ">10^5"
    if lcf_alt_mpa <= 484.88:
        return ">40K"
    return "No Life"


def walker_corrected_alt_stress(
    fiber_stress_mpa: float,
    assembly_tensile_stress_mpa: float,
    walker_coefficient: float,
) -> float:
    """Replicate the Excel IF branch used for the LCF alternating stress."""
    scale_factor = 2.5 / 2.0

    if fiber_stress_mpa < assembly_tensile_stress_mpa:
        return (
            assembly_tensile_stress_mpa
            * (1.0 - fiber_stress_mpa / assembly_tensile_stress_mpa)
            ** walker_coefficient
            * scale_factor
        )

    return (
        fiber_stress_mpa
        * (1.0 - assembly_tensile_stress_mpa / fiber_stress_mpa)
        ** walker_coefficient
        * scale_factor
    )


def calculate_bolt(case: BoltCase, constants: Constants) -> BoltResult:
    tensile_mpa = abs(case.fz_n) / constants.bolt_thread_area_mm2

    bending_moment_nmm = sqrt(case.mx_nmm**2 + case.my_nmm**2)
    bending_stress_mpa = (
        bending_moment_nmm
        * constants.bolt_radius_mm
        / constants.moment_of_inertia_mm4
    )
    fiber_mpa = tensile_mpa + bending_stress_mpa

    lcf_alt_mpa = walker_corrected_alt_stress(
        fiber_stress_mpa=fiber_mpa,
        assembly_tensile_stress_mpa=constants.assembly_tensile_stress_mpa,
        walker_coefficient=constants.walker_coefficient,
    )

    return BoltResult(
        tensile_mpa=tensile_mpa,
        fiber_mpa=fiber_mpa,
        lcf_alt_mpa=lcf_alt_mpa,
        life=fatigue_life_bucket(lcf_alt_mpa),
        crush_bolt_mpa=case.fz_n / constants.bolt_contact_crush_area_mm2,
        crush_nut_mpa=case.fz_n / constants.nut_contact_crush_area_min_mm2,
    )


def assert_close(label: str, actual: float, expected: float, tolerance: float) -> None:
    diff = abs(actual - expected)
    if diff > tolerance:
        raise AssertionError(
            f"{label}: actual {actual:.6f}, expected {expected:.6f}, "
            f"diff {diff:.6f}, tolerance {tolerance:.6f}"
        )


def validate_case(case: BoltCase, result: BoltResult) -> None:
    assert_close(
        f"{case.name} tensile_mpa",
        result.tensile_mpa,
        case.expected_tensile_mpa,
        TOLERANCES["tensile_mpa"],
    )
    assert_close(
        f"{case.name} fiber_mpa",
        result.fiber_mpa,
        case.expected_fiber_mpa,
        TOLERANCES["fiber_mpa"],
    )
    assert_close(
        f"{case.name} lcf_alt_mpa",
        result.lcf_alt_mpa,
        case.expected_lcf_alt_mpa,
        TOLERANCES["lcf_alt_mpa"],
    )
    assert_close(
        f"{case.name} crush_bolt_mpa",
        result.crush_bolt_mpa,
        case.expected_crush_bolt_mpa,
        TOLERANCES["crush_bolt_mpa"],
    )
    assert_close(
        f"{case.name} crush_nut_mpa",
        result.crush_nut_mpa,
        case.expected_crush_nut_mpa,
        TOLERANCES["crush_nut_mpa"],
    )

    if result.life != case.expected_life:
        raise AssertionError(
            f"{case.name} life: actual {result.life!r}, "
            f"expected {case.expected_life!r}"
        )


def print_header(constants: Constants) -> None:
    print("Steady-State Condition bolt strength benchmark")
    print(f"  bolt_size: {constants.bolt_size}")
    print(f"  margin_basis: {constants.margin_basis}")
    print(f"  bolt_thread_area_mm2: {constants.bolt_thread_area_mm2:.10f}")
    print(f"  bolt_radius_mm: {constants.bolt_radius_mm:.10f}")
    print(f"  moment_of_inertia_mm4: {constants.moment_of_inertia_mm4:.10f}")
    print(
        "  bolt_contact_crush_area_mm2: "
        f"{constants.bolt_contact_crush_area_mm2:.10f}"
    )
    print(
        "  nut_contact_crush_area_min_mm2: "
        f"{constants.nut_contact_crush_area_min_mm2:.10f}"
    )
    print(
        "  assembly_tensile_stress_mpa: "
        f"{constants.assembly_tensile_stress_mpa:.10f}"
    )
    print(f"  walker_coefficient: {constants.walker_coefficient:.10f}")
    print()


def print_result(case: BoltCase, result: BoltResult) -> None:
    print(
        f"{case.name}: "
        f"tensile={result.tensile_mpa:.3f}, "
        f"fiber={result.fiber_mpa:.3f}, "
        f"lcf_alt={result.lcf_alt_mpa:.3f}, "
        f"life={result.life}, "
        f"crush_bolt={result.crush_bolt_mpa:.3f}, "
        f"crush_nut={result.crush_nut_mpa:.3f}"
    )


def main() -> None:
    print_header(CONSTANTS)

    for case in CASES:
        result = calculate_bolt(case, CONSTANTS)
        print_result(case, result)
        validate_case(case, result)

    print()
    print("All Steady-State Condition benchmark checks passed.")


if __name__ == "__main__":
    main()

