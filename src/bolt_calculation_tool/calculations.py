"""Documented ExampleScenario bolt calculations.

The first prototype intentionally implements the reference-compatible path from
``docs/02_calculation_methodology.md`` and ``docs/09_design_criteria_checks.md``.
Values are kept in the documented internal units: N, N*mm, mm, mm^2, mm^4, MPa.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import inf, pi, sqrt


MARGIN_BASIS_MINOR = "MINOR"
MARGIN_BASIS_STRESS_AREA = "STRESS AREA"
SUPPORTED_MARGIN_BASES = (MARGIN_BASIS_MINOR, MARGIN_BASIS_STRESS_AREA)


@dataclass(frozen=True)
class BoltSpec:
    size: str
    minor_area_mm2: float | None
    stress_area_mm2: float | None
    bolt_hole_countersink_dia_mm: float
    bolt_head_dia_mm: float
    nut_contact_crush_area_min_mm2: float | None
    assembly_force_n: float


BOLT_SPECS: dict[str, BoltSpec] = {
    ".1900-32": BoltSpec(
        size=".1900-32",
        minor_area_mm2=None,
        stress_area_mm2=None,
        bolt_hole_countersink_dia_mm=6.3,
        bolt_head_dia_mm=9.52,
        nut_contact_crush_area_min_mm2=None,
        assembly_force_n=6050.0,
    ),
    ".2500-28": BoltSpec(
        size=".2500-28",
        # Hidden precision inferred in the reference documents.
        minor_area_mm2=11600.0 / 537.12,
        stress_area_mm2=26.06,
        bolt_hole_countersink_dia_mm=7.9,
        bolt_head_dia_mm=11.13,
        nut_contact_crush_area_min_mm2=46.58,
        assembly_force_n=11600.0,
    ),
    ".3125-24": BoltSpec(
        size=".3125-24",
        minor_area_mm2=None,
        stress_area_mm2=None,
        bolt_hole_countersink_dia_mm=9.5,
        bolt_head_dia_mm=12.7,
        nut_contact_crush_area_min_mm2=None,
        assembly_force_n=20000.0,
    ),
    ".3750-24": BoltSpec(
        size=".3750-24",
        minor_area_mm2=None,
        stress_area_mm2=None,
        bolt_hole_countersink_dia_mm=11.0,
        bolt_head_dia_mm=14.27,
        nut_contact_crush_area_min_mm2=None,
        assembly_force_n=30100.0,
    ),
}


@dataclass(frozen=True)
class BoltConstants:
    bolt_size: str
    margin_basis: str
    bolt_thread_area_mm2: float
    bolt_hole_countersink_dia_mm: float
    bolt_head_dia_mm: float
    nut_contact_crush_area_min_mm2: float
    assembly_tensile_stress_mpa: float
    walker_coefficient: float = 0.6384
    yield_002_mpa: float = 708.65

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
    def bolt_contact_crush_area_mm2(self) -> float:
        return (
            pi
            * (self.bolt_head_dia_mm**2 - self.bolt_hole_countersink_dia_mm**2)
            / 4.0
        )

    @property
    def shear_strength_mpa(self) -> float:
        return self.yield_002_mpa / sqrt(3.0)


@dataclass(frozen=True)
class BoltLoad:
    name: str
    fx_n: float
    fy_n: float
    fz_n: float
    mx_nmm: float
    my_nmm: float
    mz_nmm: float
    x_mm: float | None = None
    y_mm: float | None = None
    z_mm: float | None = None


@dataclass(frozen=True)
class StrengthResult:
    tensile_mpa: float
    bending_moment_nmm: float
    bending_stress_mpa: float
    fiber_mpa: float
    lcf_alt_mpa: float
    life: str
    crush_bolt_mpa: float
    crush_nut_mpa: float


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
    interaction_ratio: float
    margin: float

    @property
    def margin_percent_rounded(self) -> int | float:
        if self.margin == inf:
            return inf
        return round(self.margin * 100.0)


@dataclass(frozen=True)
class BoltCalculationResult:
    load: BoltLoad
    strength: StrengthResult
    interaction: InteractionResult

    @property
    def status(self) -> str:
        if self.strength.life == "No Life" or self.interaction.margin < 0.0:
            return "FAIL"
        return "PASS"

    @property
    def governing_check(self) -> str:
        if self.strength.life == "No Life":
            return "LCF life"
        return "Interaction margin"


def available_bolt_sizes() -> list[str]:
    """Return bolt sizes with complete prototype lookup data."""
    return [
        size
        for size, spec in BOLT_SPECS.items()
        if spec.minor_area_mm2 is not None
        and spec.stress_area_mm2 is not None
        and spec.nut_contact_crush_area_min_mm2 is not None
    ]


def resolve_constants(
    bolt_size: str = ".2500-28",
    margin_basis: str = MARGIN_BASIS_MINOR,
) -> BoltConstants:
    """Resolve documented lookup values for the selected bolt configuration."""
    if bolt_size not in BOLT_SPECS:
        supported = ", ".join(BOLT_SPECS)
        raise ValueError(f"Unsupported bolt size {bolt_size!r}. Supported: {supported}")

    if margin_basis not in SUPPORTED_MARGIN_BASES:
        supported = ", ".join(SUPPORTED_MARGIN_BASES)
        raise ValueError(
            f"Unsupported margin basis {margin_basis!r}. Supported: {supported}"
        )

    spec = BOLT_SPECS[bolt_size]
    if margin_basis == MARGIN_BASIS_MINOR:
        thread_area = spec.minor_area_mm2
    else:
        thread_area = spec.stress_area_mm2

    if thread_area is None or spec.nut_contact_crush_area_min_mm2 is None:
        raise ValueError(
            f"{bolt_size} is listed in the source lookup formulas, but the "
            "documents only provide complete prototype constants for .2500-28."
        )

    return BoltConstants(
        bolt_size=spec.size,
        margin_basis=margin_basis,
        bolt_thread_area_mm2=thread_area,
        bolt_hole_countersink_dia_mm=spec.bolt_hole_countersink_dia_mm,
        bolt_head_dia_mm=spec.bolt_head_dia_mm,
        nut_contact_crush_area_min_mm2=spec.nut_contact_crush_area_min_mm2,
        assembly_tensile_stress_mpa=spec.assembly_force_n / thread_area,
    )


def fatigue_life_bucket(lcf_alt_mpa: float) -> str:
    """Return the documented INCO718 573K fatigue-life bucket."""
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
    """Replicate the documented Walker correction branch."""
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


def calculate_strength(load: BoltLoad, constants: BoltConstants) -> StrengthResult:
    tensile_mpa = abs(load.fz_n) / constants.bolt_thread_area_mm2
    bending_moment_nmm = sqrt(load.mx_nmm**2 + load.my_nmm**2)
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

    return StrengthResult(
        tensile_mpa=tensile_mpa,
        bending_moment_nmm=bending_moment_nmm,
        bending_stress_mpa=bending_stress_mpa,
        fiber_mpa=fiber_mpa,
        lcf_alt_mpa=lcf_alt_mpa,
        life=fatigue_life_bucket(lcf_alt_mpa),
        crush_bolt_mpa=load.fz_n / constants.bolt_contact_crush_area_mm2,
        crush_nut_mpa=load.fz_n / constants.nut_contact_crush_area_min_mm2,
    )


def calculate_interaction(
    load: BoltLoad,
    constants: BoltConstants,
) -> InteractionResult:
    plug_n = abs(load.fz_n)
    shear_n = sqrt(load.fx_n**2 + load.fy_n**2)
    bending_nmm = sqrt(load.mx_nmm**2 + load.my_nmm**2)
    torsion_nmm = abs(load.mz_nmm)

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
    margin = inf if interaction_ratio == 0.0 else 1.0 / interaction_ratio - 1.0

    return InteractionResult(
        plug_n=plug_n,
        shear_n=shear_n,
        bending_nmm=bending_nmm,
        torsion_nmm=torsion_nmm,
        rt=rt,
        rb=rb,
        rs=rs,
        rst=rst,
        interaction_ratio=interaction_ratio,
        margin=margin,
    )


def calculate_bolt(
    load: BoltLoad,
    constants: BoltConstants,
) -> BoltCalculationResult:
    return BoltCalculationResult(
        load=load,
        strength=calculate_strength(load, constants),
        interaction=calculate_interaction(load, constants),
    )


def calculate_bolt_group(
    loads: list[BoltLoad],
    constants: BoltConstants,
) -> list[BoltCalculationResult]:
    return [calculate_bolt(load, constants) for load in loads]
