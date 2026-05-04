# Verification And Validation Plan

This plan defines how to verify a future implementation of the decoded
`BOLT_STRENGTH.xlsx` `Steady-State Condition` calculation.

## Validation Objective

The implementation shall reproduce the workbook's `Steady-State Condition` circumferential flange
bolt results for:

```text
bolt size = .2500-28
margin basis = MINOR
load case = Steady-State Condition
source load sheet = L1
```

The first validation target is numeric agreement with the screen-visible
workbook values documented in `04_reference_test_cases.md`.

## Verification Levels

### Level 1: Formula Unit Tests

Verify individual formula functions:

| Function | Required checks |
| --- | --- |
| Area selection | `MINOR` selects minor area, `STRESS AREA` selects NAS1348 stress area |
| Radius | `sqrt(area / pi)` |
| Inertia | `pi * radius^4 / 4` |
| Bolt contact crush area | `pi * (head_dia^2 - countersink_dia^2) / 4` |
| Tensile stress | `abs(FZ) / bolt_thread_area` |
| Fiber stress | `tensile + sqrt(MX^2 + MY^2) * radius / inertia` |
| Walker correction | both below-assembly and above-assembly branches |
| Life bucket | inclusive upper-bound thresholds |
| Crush stress | `FZ / contact_area`, preserving sign |
| Interaction resultants | plug, shear, bending, and torsion scalar reductions |
| Interaction ratios | `Rt`, `Rb`, `Rs`, and `Rst` |
| Interaction margin | `1 / sqrt((Rt + Rb)^2 + (Rs + Rst)^2) - 1` |

### Level 2: Reference Case Tests

Run the benchmark cases in `04_reference_test_cases.md`.

Required outputs:

```text
Tensile Stress
Fiber Stress
LCF sigma_alt
Life
Flange Crush Stress, Bolt
Flange Crush Stress, Nut
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

Pass criteria:

- Numeric outputs are within the tolerances documented in
  `04_reference_test_cases.md`.
- Life labels match exactly.
- The implementation uses `N*mm` moments, not `N*m`, unless it explicitly
  converts from `N*m` to `N*mm`.
- Interaction margin percentages match the rounded workbook percentages.

### Level 3: GUI Integration Tests

When the GUI exists, test that:

- Bolt size selection changes all dependent geometry and lookup values.
- Margin basis dropdown changes the selected bolt thread stress area.
- The displayed table updates when `FZ`, `MX`, or `MY` change.
- Display rounding matches the selected GUI formatting.
- Invalid or missing inputs produce a controlled error message.

## Known Compatibility Notes

### Hidden Precision

Screenshots show rounded values. For example, the workbook displays:

```text
bolt_thread_area = 21.60 mm^2
walker_coefficient = 0.64
```

However, the executable benchmark uses:

```text
bolt_thread_area = 11600 / 537.12 = 21.5966636878 mm^2
walker_coefficient = 0.6384
```

Those inferred values reproduce the screen-visible output more closely. If the
original workbook is available later, export exact cell values and update the
benchmark constants.

### Excel VLOOKUP Behavior

The decoded workbook formulas use `VLOOKUP` without the fourth argument:

```excel
=VLOOKUP(..., ..., column,)
```

Excel treats this as approximate match. For a future GUI, exact dictionary
lookups by bolt size are recommended unless exact workbook compatibility is
required.

### Moment Units

The workbook treats `MX` and `MY` as values compatible with `mm` geometry. The
benchmark therefore uses N*mm. If user input is N*m, multiply by `1000` before
calculating bending stress.

## Regression Workflow

Before accepting a future calculation change:

1. Run the executable benchmark.
2. Confirm all benchmark checks pass.
3. Manually inspect any tolerance changes.
4. Add new reference cases before extending the calculation to other load cases
   such as `CDP`, `L2`, or `L3`.

Command:

```powershell
python scripts\benchmark_steady_state_bolt_strength.py
python scripts\benchmark_steady_state_interaction_curve.py
```

Expected result:

```text
All Steady-State Condition benchmark checks passed.
All Steady-State Condition interaction benchmark checks passed.
```

