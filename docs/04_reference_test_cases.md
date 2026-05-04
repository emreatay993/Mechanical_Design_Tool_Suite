# Reference Test Cases

This document records benchmark cases for validating a future GUI or calculation backend against the documented reference behavior.

## Benchmark Set: ExampleScenario Circumferential Flange

Scope:

```text
load case = ExampleScenario
source load sheet = L1
bolt size = .2500-28
margin basis = MINOR
units = N, N*mm, mm, mm^2, mm^4, MPa
```

Constants used by the executable benchmark:

| Name | Value | Notes |
| --- | ---: | --- |
| `bolt_thread_area_mm2` | `21.5966636878` | Inferred from `11600 / 537.12`; displayed as `21.60` |
| `bolt_radius_mm` | `sqrt(area / pi)` | displayed as `2.62` |
| `moment_of_inertia_mm4` | `pi * radius^4 / 4` | displayed as `37.12` |
| `bolt_hole_countersink_dia_mm` | `7.90` | Cell `O17` |
| `bolt_head_dia_mm` | `11.13` | Cell `O18` |
| `bolt_contact_crush_area_mm2` | `48.2759903697` | displayed as `48.28` |
| `nut_contact_crush_area_min_mm2` | `46.58` | Cell `O21` |
| `assembly_tensile_stress_mpa` | `537.12` | Cell `O22` |
| `walker_coefficient` | `0.6384` | Inferred hidden precision; displayed as `0.64` |

If exact source values are exported later, update these constants and tighten
the tolerances in the executable benchmark.

## Input Cases

The first nine benchmark rows in the `L1` sheet are used as benchmark input.
Only `FZ`, `MX`, and `MY` are used by the documented `ExampleScenario` stress formulas.

| Bolt | `FZ` N | `MX` N*mm | `MY` N*mm |
| --- | ---: | ---: | ---: |
| BOLT01 | 10856 | 182 | -140 |
| BOLT02 | 10859 | 318 | -28 |
| BOLT03 | 10869 | 312 | 1 |
| BOLT04 | 10857 | 250 | 53 |
| BOLT05 | 10827 | 204 | 104 |
| BOLT06 | 10797 | 144 | 134 |
| BOLT07 | 10754 | 129 | 123 |
| BOLT08 | 10708 | 46 | 153 |
| BOLT09 | 10632 | 31 | 148 |

## Expected Outputs

The expected values below are the one-decimal displayed reference values.

| Bolt | Tensile stress MPa | Fiber stress MPa | LCF sigma_alt MPa | Life | Crush bolt MPa | Crush nut MPa |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| BOLT01 | 502.7 | 518.9 | 77.4 | Infinite | 224.9 | 233.1 |
| BOLT02 | 502.8 | 525.3 | 58.6 | Infinite | 224.9 | 233.1 |
| BOLT03 | 503.3 | 525.3 | 58.7 | Infinite | 225.1 | 233.4 |
| BOLT04 | 502.7 | 520.8 | 72.2 | Infinite | 224.9 | 233.1 |
| BOLT05 | 501.3 | 517.5 | 81.1 | Infinite | 224.3 | 232.5 |
| BOLT06 | 499.9 | 513.8 | 90.6 | Infinite | 223.6 | 231.8 |
| BOLT07 | 497.9 | 510.5 | 98.5 | Infinite | 222.8 | 230.9 |
| BOLT08 | 495.8 | 507.1 | 106.5 | Infinite | 221.8 | 229.9 |
| BOLT09 | 492.3 | 503.0 | 115.6 | Infinite | 220.2 | 228.3 |

## Validation Tolerances

Recommended initial tolerances:

| Output | Tolerance |
| --- | ---: |
| Tensile stress | `0.15 MPa` |
| Fiber stress | `0.20 MPa` |
| LCF sigma_alt | `0.20 MPa` |
| Crush stress | `0.15 MPa` |
| Life label | exact string match |

These tolerances are intentionally small but not zero because the reference data
show rounded cells. If exact reference calculation cell values become available, use tighter
tolerances.

## Executable Benchmark

Run:

```powershell
python scripts\benchmark_example_scenario_bolt_strength.py
```

Expected result:

```text
All ExampleScenario benchmark checks passed.
```

The script prints every calculated value and compares it against the expected
reference values.

## Benchmark Set: ExampleScenario Interaction Curve

Scope:

```text
load case = ExampleScenario
source load sheet = L1
bolt size = .2500-28
margin basis = MINOR
units = N, N*mm, mm, mm^2, mm^4, MPa
```

Constants used by the executable interaction benchmark:

| Name | Value | Notes |
| --- | ---: | --- |
| `bolt_thread_area_mm2` | `21.5966636878` | Inferred from `11600 / 537.12`; displayed as `21.60` |
| `bolt_radius_mm` | `sqrt(area / pi)` | displayed as `2.62` |
| `moment_of_inertia_mm4` | `pi * radius^4 / 4` | displayed as `37.12` |
| `polar_moment_of_inertia_mm4` | `2 * moment_of_inertia` | displayed as `74.23` |
| `yield_002_mpa` | `708.65` | Material Properties ExampleScenario value, displayed as `708.7` |
| `shear_strength_mpa` | `yield_002 / sqrt(3)` | displayed as `409.1` |

## Interaction Input Cases

The first nine benchmark interaction rows are used as benchmark input.

| Bolt | `FX` N | `FY` N | `FZ` N | `MX` N*mm | `MY` N*mm | `MZ` N*mm |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BOLT01 | -16.7 | -165.6 | 10856.2 | 182.0 | -140.0 | -4.8 |
| BOLT02 | -5.3 | -178.1 | 10859.1 | 317.7 | -27.9 | -9.1 |
| BOLT03 | 9.2 | -174.0 | 10869.2 | 311.9 | 0.6 | -32.8 |
| BOLT04 | 21.9 | -156.5 | 10857.0 | 250.4 | 52.6 | -42.6 |
| BOLT05 | 33.6 | -136.9 | 10827.3 | 203.8 | 104.3 | -42.5 |
| BOLT06 | 39.6 | -118.7 | 10796.5 | 144.2 | 133.9 | -38.4 |
| BOLT07 | 40.8 | -107.0 | 10753.9 | 129.1 | 123.0 | -45.8 |
| BOLT08 | 52.6 | -80.4 | 10707.5 | 45.9 | 153.1 | -81.0 |
| BOLT09 | 40.4 | -49.8 | 10631.8 | 30.8 | 148.4 | -70.8 |

## Expected Interaction Outputs

The expected values below are the displayed reference values.

| Bolt | PLUG N | SHEAR N | BENDING N*mm | Torsion N*mm | Rt | Rb | Rs | Rst | Margin |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BOLT01 | 10856 | 166.5 | 229.7 | 4.8 | 0.709 | 0.023 | 0.019 | 0.000 | 37% |
| BOLT02 | 10859 | 178.1 | 318.9 | 9.1 | 0.700 | 0.032 | 0.020 | 0.001 | 35% |
| BOLT03 | 10869 | 174.3 | 311.9 | 32.8 | 0.700 | 0.031 | 0.020 | 0.003 | 35% |
| BOLT04 | 10857 | 158.0 | 255.8 | 42.6 | 0.700 | 0.026 | 0.018 | 0.004 | 36% |
| BOLT05 | 10827 | 140.9 | 229.0 | 42.5 | 0.700 | 0.023 | 0.016 | 0.004 | 37% |
| BOLT06 | 10797 | 125.1 | 196.8 | 38.4 | 0.700 | 0.020 | 0.014 | 0.003 | 38% |
| BOLT07 | 10754 | 114.5 | 178.3 | 45.8 | 0.700 | 0.018 | 0.013 | 0.004 | 39% |
| BOLT08 | 10708 | 96.1 | 159.8 | 81.0 | 0.700 | 0.016 | 0.011 | 0.007 | 40% |
| BOLT09 | 10632 | 64.1 | 151.5 | 70.8 | 0.700 | 0.015 | 0.007 | 0.006 | 41% |

The reference calculation display rounds most `Rt` values to one decimal, so values shown as
`0.700` in this table are validated with a wider tolerance than the `BOLT01`
`0.709` value.

Recommended interaction tolerances:

| Output | Tolerance |
| --- | ---: |
| PLUG | `0.6 N` |
| SHEAR | `0.2 N` |
| BENDING | `0.2 N*mm` |
| Torsion | `0.05 N*mm` |
| Rt | `0.011` |
| Rb | `0.001` |
| Rs | `0.001` |
| Rst | `0.001` |
| Margin | exact rounded percent match |

Executable benchmark:

```powershell
python scripts\benchmark_example_scenario_interaction_curve.py
```

Expected result:

```text
All ExampleScenario interaction benchmark checks passed.
```




