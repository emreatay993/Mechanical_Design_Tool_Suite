# Design Criteria And Checks

This document records design criteria and calculation checks for a future Bolt
Calculation Tool implementation.

The current content is intentionally limited to the documented
`ExampleScenario` circumferential flange bolt calculation. It extracts criteria
and checks from the current methodology, reference test cases, and verification
plan so new criteria can be added later without changing the existing source
documents.

## Source Documents

| Source | Use in this document |
| --- | --- |
| `02_calculation_methodology.md` | Formula definitions, input logic, units, and compatibility notes |
| `04_reference_test_cases.md` | Benchmark cases, expected outputs, and tolerances |
| `07_verification_validation_plan.md` | Verification levels, pass criteria, and regression workflow |
| `scripts/benchmark_example_scenario_bolt_strength.py` | Executable strength benchmark |
| `scripts/benchmark_example_scenario_interaction_curve.py` | Executable interaction benchmark |

## Scope

Initial scope:

```text
load case = ExampleScenario
source load sheet = L1
bolt size = .2500-28
margin basis = MINOR
units = N, N*mm, mm, mm^2, mm^4, MPa
```

Geometry values are treated as inputs, lookup results, or derived input
properties. They are not design objectives in this document. Future geometry
optimization, bolt selection objectives, or automated sizing criteria should be
added only when that work is explicitly defined.

## Design Criteria

| ID | Criteria area | Criterion |
| --- | --- | --- |
| DC-001 | Units | Calculations shall use N for force, N*mm for moments, mm for length, mm^2 for area, mm^4 for inertia, and MPa for stress. |
| DC-002 | Reference compatibility | The initial implementation shall reproduce the documented `ExampleScenario` reference behavior before extending to other load cases. |
| DC-003 | Load usage | Bolt strength outputs shall use `FZ`, `MX`, and `MY`; interaction outputs shall use `FX`, `FY`, `FZ`, `MX`, `MY`, and `MZ`. |
| DC-004 | Bolt size input | Bolt size shall drive thread area lookup, contact geometry lookup, and derived section properties. |
| DC-005 | Margin basis input | `MINOR` shall select minor thread area, and `STRESS AREA` shall select NAS1348 stress area. |
| DC-006 | Geometry inputs | Bolt radius, moment of inertia, polar moment of inertia, countersink diameter, bolt head diameter, and nut contact geometry shall be treated as input or derived-input data, not as optimized design variables. |
| DC-007 | Hidden precision | Benchmark agreement shall use the documented hidden-precision values until exact exported source values are available. |
| DC-008 | Result display | Display rounding may differ from calculation precision, but benchmark comparisons shall use the documented tolerances. |
| DC-009 | Fatigue life method | The current life-label check is for reference compatibility only; the future calculation implementation should be ready to replace bucket-only life with interpolated life when the fatigue-life method is defined. |

## Input And Derived-Input Checks

These checks verify input selection, lookup consistency, and derived input
properties. They do not define geometry optimization criteria.

| ID | Check | Required behavior |
| --- | --- | --- |
| CHK-IN-001 | Bolt size | `.2500-28` shall reproduce the documented ExampleScenario constants. |
| CHK-IN-002 | Area selection | `MINOR` selects the minor area; `STRESS AREA` selects the NAS1348 stress area. |
| CHK-IN-003 | Bolt thread area | For the current benchmark, use `11600 / 537.12 = 21.5966636878 mm^2` to reproduce hidden-precision reference behavior. |
| CHK-IN-004 | Bolt radius | `bolt_radius = sqrt(bolt_thread_area / pi)`. |
| CHK-IN-005 | Moment of inertia | `moment_of_inertia = pi * bolt_radius^4 / 4`. |
| CHK-IN-006 | Polar moment of inertia | `polar_moment_of_inertia = 2 * moment_of_inertia`. |
| CHK-IN-007 | Bolt contact crush area | `bolt_contact_crush_area = pi * (bolt_head_dia^2 - bolt_hole_countersink_dia^2) / 4`. |
| CHK-IN-008 | Nut contact crush area | Use the documented minimum nut contact crush area for the selected bolt size. |
| CHK-IN-009 | Assembly tensile stress | For the current benchmark, `assembly_tensile_stress = 537.12 MPa`. |
| CHK-IN-010 | Walker coefficient | For the current benchmark, use `walker_coefficient = 0.6384` until exact source precision is available. |
| CHK-IN-011 | Interaction material strength | For the current benchmark, `yield_002 = 708.65 MPa` and `shear_strength = yield_002 / sqrt(3)`. |

## Strength And Fatigue Checks

| ID | Check | Required behavior |
| --- | --- | --- |
| CHK-ST-001 | Tensile stress | `tensile_stress = abs(FZ) / bolt_thread_area`. |
| CHK-ST-002 | Bending moment resultant | `bending_moment = sqrt(MX^2 + MY^2)`. |
| CHK-ST-003 | Bending stress | `bending_stress = bending_moment * bolt_radius / moment_of_inertia`. |
| CHK-ST-004 | Fiber stress | `fiber_stress = tensile_stress + bending_stress`. |
| CHK-ST-005 | Walker branch below assembly stress | If `fiber_stress < assembly_tensile_stress`, use the documented below-assembly Walker correction branch. |
| CHK-ST-006 | Walker branch above assembly stress | If `fiber_stress >= assembly_tensile_stress`, use the documented above-assembly Walker correction branch. |
| CHK-ST-007 | LCF scale factor | Walker-corrected alternating stress shall use `scale_factor = 2.5 / 2`. |
| CHK-ST-008 | Reference fatigue life label | For current reference compatibility, life labels shall use the documented INCO718 thresholds with inclusive upper bounds. |
| CHK-ST-009 | Interpolated life readiness | Bucket labels shall not be treated as the final fatigue-life method; the implementation should allow replacing or augmenting the label with interpolated life later. |
| CHK-ST-010 | Reference life label output | Current benchmark life label comparison shall be an exact string match. |

## Crush Checks

| ID | Check | Required behavior |
| --- | --- | --- |
| CHK-CR-001 | Bolt-side crush stress | `flange_crush_stress_bolt = FZ / bolt_contact_crush_area`. |
| CHK-CR-002 | Nut-side crush stress | `flange_crush_stress_nut = FZ / nut_contact_crush_area_min`. |
| CHK-CR-003 | Crush stress sign | Crush stress shall preserve the sign of `FZ`; negative `FZ` produces negative crush stress. |

## Interaction Checks

| ID | Check | Required behavior |
| --- | --- | --- |
| CHK-INT-001 | Plug load | `plug = abs(FZ)`. |
| CHK-INT-002 | Direct shear resultant | `shear = sqrt(FX^2 + FY^2)`. |
| CHK-INT-003 | Bending resultant | `bending = sqrt(MX^2 + MY^2)`. |
| CHK-INT-004 | Torsion | `torsion = abs(MZ)`. |
| CHK-INT-005 | Tensile ratio `Rt` | `Rt = (plug / bolt_thread_area) / yield_002`. |
| CHK-INT-006 | Bending ratio `Rb` | `Rb = (bending * bolt_radius / moment_of_inertia) / yield_002`. |
| CHK-INT-007 | Direct shear ratio `Rs` | `Rs = (shear / bolt_thread_area) / shear_strength`. |
| CHK-INT-008 | Torsional shear ratio `Rst` | `Rst = (torsion * bolt_radius / polar_moment_of_inertia) / shear_strength`. |
| CHK-INT-009 | Interaction ratio | `interaction_ratio = sqrt((Rt + Rb)^2 + (Rs + Rst)^2)`. |
| CHK-INT-010 | Margin | `margin = 1 / interaction_ratio - 1`. |
| CHK-INT-011 | Margin interpretation | Positive margin means the point is inside the interaction curve. |
| CHK-INT-012 | Margin display | Displayed margin percentages shall match the rounded reference percentages. |

## Benchmark Acceptance Criteria

The future implementation shall pass the existing ExampleScenario benchmark
checks before the calculation scope is expanded.

Required strength outputs:

```text
Tensile Stress
Fiber Stress
LCF sigma_alt
Life
Flange Crush Stress, Bolt
Flange Crush Stress, Nut
```

Recommended strength tolerances:

| Output | Tolerance |
| --- | ---: |
| Tensile stress | `0.15 MPa` |
| Fiber stress | `0.20 MPa` |
| LCF sigma_alt | `0.20 MPa` |
| Crush stress | `0.15 MPa` |
| Life label | exact string match for current reference compatibility |

Required interaction outputs:

```text
PLUG
SHEAR
BENDING
Torsion
Rt
Rb
Rs
Rst
Margin
```

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

Executable benchmark commands:

```powershell
python scripts\benchmark_example_scenario_bolt_strength.py
python scripts\benchmark_example_scenario_interaction_curve.py
```

Expected result:

```text
All ExampleScenario benchmark checks passed.
All ExampleScenario interaction benchmark checks passed.
```

## Compatibility Notes

### Hidden Precision

Some displayed source values are rounded. The current benchmarks use inferred
hidden-precision values where needed to reproduce the reference rows:

```text
bolt_thread_area = 11600 / 537.12 = 21.5966636878 mm^2
walker_coefficient = 0.6384
```

If exact exported source values become available, update the reference constants
and then tighten tolerances where appropriate.

### Excel VLOOKUP Behavior

The source methodology documents Excel `VLOOKUP` formulas without an explicit
fourth argument, which Excel treats as approximate match. Exact dictionary
lookups by bolt size are recommended for the future tool unless exact Excel
lookup compatibility is explicitly required.

### Moment Units

The reference calculation treats `MX`, `MY`, and `MZ` as values compatible with
mm geometry. Benchmarks therefore use N*mm. If user input is N*m, convert to
N*mm before applying stress or interaction formulas.

## Future Additions

Add new criteria here when the tool scope expands to additional load cases,
bolt sizes, materials, GUI workflows, or optimization/selection behavior. New
entries should identify the source document or engineering basis, required
formula or behavior, acceptance tolerance, and whether the check is executable.
