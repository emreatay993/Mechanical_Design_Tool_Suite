# ExampleScenario Bolt Strength Calculation Methodology

This document defines the calculation logic for the `ExampleScenario` load case. The current scope is the `ExampleScenario` block for circumferential flange bolts.

The goal is to preserve the calculation algorithm in implementation-ready form so
a future GUI can reproduce and validate the same results.

## Calculation Scope

The reference `ExampleScenario` output table contains these calculated columns:

| Output column | Meaning | Cell pattern |
| --- | --- | --- |
| `Tensile Stress` | Direct axial tensile stress from `FZ` | `D6:D...` |
| `Fiber Stress` | Direct stress plus bending stress from `MX`/`MY` | `E6:E...` |
| `LCF sigma_alt` | Walker-corrected alternating stress | `F6:F...` |
| `Life` | Fatigue life category from INCO718 table | `G6:G...` |
| `Flange Crush Stress, Bolt` | Bearing/crush stress under bolt head | `I6:I...` |
| `Flange Crush Stress, Nut` | Bearing/crush stress under nut | `J6:J...` |

The `ExampleScenario` loads are read from the `L1` sheet:

| `L1` column | Name in sheet | Used by this calculation |
| --- | --- | --- |
| `E` | `FZ` / plug load | Axial force, N |
| `F` | `MX` | Bending moment about X, treated as N*mm |
| `G` | `MY` | Bending moment about Y, treated as N*mm |

The reference calculation does not use `FX`, `FY`, or `MZ` in the documented `ExampleScenario` stress
columns.

The reference `ExampleScenario` interaction table contains these calculated columns:

| Output column | Meaning |
| --- | --- |
| `PLUG` | Absolute axial/plug force from `FZ` |
| `SHEAR` | Resultant direct shear from `FX` and `FY` |
| `BENDING` | Resultant bending moment from `MX` and `MY` |
| `Torsion` | Absolute torsion from `MZ` |
| `Rt` | Tensile/plug utilization ratio |
| `Rb` | Bending utilization ratio |
| `Rs` | Direct shear utilization ratio |
| `Rst` | Torsional shear utilization ratio |
| `Margin` | Margin to the circular interaction curve |

For the interaction table, all six `L1` load columns are used:

| `L1` load | Use |
| --- | --- |
| `FX`, `FY` | direct shear resultant |
| `FZ` | plug/tensile force |
| `MX`, `MY` | bending moment resultant |
| `MZ` | torsion |

## Units

| Quantity | Unit |
| --- | --- |
| Force `FZ` | N |
| Moments `MX`, `MY` | N*mm as used by the reference calculation |
| Areas | mm^2 |
| Radius / diameters | mm |
| Moment of inertia | mm^4 |
| Polar moment of inertia | mm^4 |
| Stress | MPa, equivalent to N/mm^2 |

If `MX` and `MY` were interpreted as N*m, the bending stress would be 1000
times larger and would not match the reference calculation. Therefore the implementation
must use the moment values as N*mm, or convert them to N*mm before applying the
formula.

## Input And Lookup Logic

### Bolt Size

Cell `N6` is the bolt size input. The benchmark reference data use:

```text
bolt_size = ".2500-28"
```

### Thread Areas

Cell `N7`:

```excel
=VLOOKUP(N6,Ref!F5:I8,4,)
```

This returns the minor thread area. For `.2500-28`, the displayed value is:

```text
minor_thread_area = 21.60 mm^2
```

Cell `N8`:

```excel
=VLOOKUP(N6,Ref!B5:D8,3,)
```

This returns the NAS1348 stress area. For `.2500-28`, the displayed value is:

```text
stress_area_nas1348 = 26.06 mm^2
```

Cell `N10` is a dropdown:

```text
"MINOR" or "STRESS AREA"
```

Cell `O12`, the bolt thread stress area used in calculations:

```excel
=IF(N10="MINOR",N7,IF(N10="STRESS AREA",N8))
```

For the documented benchmark:

```text
margin_basis = "MINOR"
bolt_thread_area = minor_thread_area
```

The displayed value is `21.60 mm^2`. Some reference calculations in this repo
use `11600 / 537.12 = 21.5966636878 mm^2` to reproduce the rounded reference
outputs more closely, because the reference calculation likely carries hidden precision
behind the displayed `21.60`.

### Section Properties

Cell `O13`, equivalent bolt stress-area radius:

```excel
=SQRT(O12/PI())
```

Python:

```python
bolt_radius = sqrt(bolt_thread_area / pi)
```

Cell `O14`, equivalent circular-section moment of inertia:

```excel
=(PI()*O13^4)/4
```

Python:

```python
moment_of_inertia = pi * bolt_radius**4 / 4
```

For the displayed `.2500-28`, `MINOR` case:

```text
bolt_radius = 2.62 mm
moment_of_inertia = 37.12 mm^4
```

Cell `O15`, `Bending Distance, c`, is displayed as `2.62 mm`. The documented row
formula for fiber stress uses `O13` directly, not `O15`. For the benchmark they
are numerically the same.

For the interaction table, the polar moment of inertia is:

```python
polar_moment_of_inertia = 2 * moment_of_inertia
```

For `.2500-28`, `MINOR`:

```text
polar_moment_of_inertia = 74.23 mm^4
```

### Contact Geometry

Cell `O17`, bolt hole countersink diameter:

```excel
=IF(N6=".1900-32",6.3,IF(N6=".2500-28",7.9,IF(N6=".3125-24",9.5,IF(N6=".3750-24",11))))
```

For `.2500-28`:

```text
bolt_hole_countersink_dia = 7.90 mm
```

Cell `O18`, bolt head diameter:

```excel
=IF(N6=".1900-32",9.52,IF(N6=".2500-28",11.13,IF(N6=".3125-24",12.7,IF(N6=".3750-24",14.27))))
```

For `.2500-28`:

```text
bolt_head_dia = 11.13 mm
```

Cell `O19`, nut contact minimum diameter:

```excel
=VLOOKUP(N6,Ref!O5:Q8,3,)
```

For `.2500-28`:

```text
nut_contact_min_dia = 10.414 mm
```

Cell `O20`, bolt contact crush area:

```excel
=PI()*(O18^2-O17^2)/4
```

Python:

```python
bolt_contact_crush_area = pi * (bolt_head_dia**2 - bolt_hole_countersink_dia**2) / 4
```

For `.2500-28`:

```text
bolt_contact_crush_area = 48.28 mm^2
```

Cell `O21`, nut contact crush area minimum:

```excel
=VLOOKUP(N6,Ref!O15:S18,5,)
```

The reference table is the AS27820 minimum-area table. For `.2500-28`:

```text
nut_contact_crush_area_min = 46.58 mm^2
```

### Assembly Tensile Stress

Cell `O22`:

```excel
=IF(N6=".1900-32",6050/O12,
 IF(N6=".2500-28",11600/O12,
 IF(N6=".3125-24",20000/O12,
 IF(N6=".3750-24",30100/O12))))
```

Python:

```python
assembly_force_by_bolt_size = {
    ".1900-32": 6050,
    ".2500-28": 11600,
    ".3125-24": 20000,
    ".3750-24": 30100,
}

assembly_tensile_stress = assembly_force_by_bolt_size[bolt_size] / bolt_thread_area
```

For `.2500-28`, `MINOR`:

```text
assembly_tensile_stress = 537.12 MPa
```

### Walker Coefficient

Cell `N44`:

```excel
=VLOOKUP(M37,LCF!L54:M56,2,)
```

The displayed value is:

```text
walker_coefficient = 0.64
```

The benchmark script uses `0.6384` as an inferred hidden-precision value because
it reproduces the reference `LCF sigma_alt` values more closely. If the
exact source values are available later, replace this inferred value with the exact
cell value from `LCF!L54:M56`.

### Material Strengths For Interaction

The interaction table uses the INCO718 BAR `ExampleScenario` material properties at `250 C`.

The reference material-property lookup for the 0.02% yield strength is:

```excel
=VLOOKUP(T23,'Material Properties'!P5:R6,3,)
```

From the `Material Properties` sheet:

| Load case | Temperature K | 0.02% yield strength MPa |
| --- | ---: | ---: |
| `ExampleScenario` | 523 | 708.65 |
| `CDP` | 340 | 773.39 |

The reference `Crc1_N_BJ` table displays this as:

```text
0.02% Yield Strength = 708.7 MPa
```

The shear strength is calculated from the 0.02% yield strength:

```excel
=T24/SQRT(3)
```

Python:

```python
shear_strength = yield_002 / sqrt(3)
```

For the benchmark:

```text
yield_002 = 708.65 MPa
shear_strength = 409.14 MPa
```

The interaction ratio formulas also display 0.2% yield strength and minimum
tensile strength in the material table, but those values are not used in the
documented `Rt`, `Rb`, `Rs`, `Rst`, or `Margin` formulas.

## Row-Level Formulas

For the first bolt row, the reference calculation uses row `19` from the `L1` sheet:

```text
FZ = 'L1'!E19
MX = 'L1'!F19
MY = 'L1'!G19
```

The same pattern is copied downward for later bolt rows.

### Tensile Stress

Cell `D6`:

```excel
=ABS('L1'!E19)/$O$12
```

Python:

```python
tensile_stress = abs(fz_n) / bolt_thread_area
```

### Fiber Stress

Cell `E6`:

```excel
=D6+(SQRT('L1'!F19^2+'L1'!G19^2))*$O$13/$O$14
```

Python:

```python
bending_moment = sqrt(mx_nmm**2 + my_nmm**2)
bending_stress = bending_moment * bolt_radius / moment_of_inertia
fiber_stress = tensile_stress + bending_stress
```

### LCF Alternating Stress

Cell `F6`:

```excel
=IF(E6<$O$22,
    $O$22*(1-(E6/$O$22))^($N$44)*2.5/2,
    E6*(1-($O$22/E6))^($N$44)*2.5/2
)
```

Python:

```python
scale_factor = 2.5 / 2

if fiber_stress < assembly_tensile_stress:
    lcf_alt = (
        assembly_tensile_stress
        * (1 - fiber_stress / assembly_tensile_stress) ** walker_coefficient
        * scale_factor
    )
else:
    lcf_alt = (
        fiber_stress
        * (1 - assembly_tensile_stress / fiber_stress) ** walker_coefficient
        * scale_factor
    )
```

### Fatigue Life Bucket

The reference INCO718 bar alternating pseudo-life table at `573K` is:

| Stress limit, MPa | Life label |
| ---: | --- |
| 167 | `infinite` |
| 206.2 | `10^7` |
| 300 | `10^6` |
| 412.2 | `10^5` |
| 484.88 | `40000` |

Cell `G6`:

```excel
=IF(F6<=$M$38,"Infinite",
 IF(AND(F6>$M$38,F6<=$M$39),">10^7",
 IF(AND(F6>$M$39,F6<=$M$40),">10^6",
 IF(AND(F6>$M$40,F6<=$M$41),">10^5",
 IF(AND(F6>$M$41,F6<=$M$42),">40K","No Life")))))
```

Python:

```python
def fatigue_life_bucket(lcf_alt):
    if lcf_alt <= 167:
        return "Infinite"
    if lcf_alt <= 206.2:
        return ">10^7"
    if lcf_alt <= 300:
        return ">10^6"
    if lcf_alt <= 412.2:
        return ">10^5"
    if lcf_alt <= 484.88:
        return ">40K"
    return "No Life"
```

### Flange Crush Stress, Bolt Side

Cell `I6`:

```excel
='L1'!E19/Crc1_N!$O$20
```

Python:

```python
flange_crush_stress_bolt = fz_n / bolt_contact_crush_area
```

The reference calculation formula does not use `ABS()` here, so a negative `FZ` would produce
a negative crush stress.

### Flange Crush Stress, Nut Side

Cell `J6`:

```excel
='L1'!E19/Crc1_N!$O$21
```

Python:

```python
flange_crush_stress_nut = fz_n / nut_contact_crush_area_min
```

## ExampleScenario Interaction Curve Formulas

The interaction table first reduces the six load components into four scalar
components.

### Plug

```python
plug = abs(fz_n)
```

### Direct Shear

```python
shear = sqrt(fx_n**2 + fy_n**2)
```

### Bending

```python
bending = sqrt(mx_nmm**2 + my_nmm**2)
```

### Torsion

```python
torsion = abs(mz_nmm)
```

### Tensile / Plug Ratio, Rt

reference formula:

```excel
=(I6/$U$10)/$T$24
```

Python:

```python
rt = (plug / bolt_thread_area) / yield_002
```

### Bending Ratio, Rb

reference formula:

```excel
=(K6*$U$11/$U$12)/$T$24
```

Python:

```python
rb = (bending * bolt_radius / moment_of_inertia) / yield_002
```

### Direct Shear Ratio, Rs

reference formula:

```excel
=(J6/$U$10)/$T$26
```

Python:

```python
rs = (shear / bolt_thread_area) / shear_strength
```

### Torsional Shear Ratio, Rst

reference formula:

```excel
=(L6*$U$11/$U$14)/$T$26
```

Python:

```python
rst = (torsion * bolt_radius / polar_moment_of_inertia) / shear_strength
```

### Interaction Margin

reference formula:

```excel
=-1+1/SQRT((M6+N6)^2+(O6+P6)^2)
```

Python:

```python
interaction_ratio = sqrt((rt + rb) ** 2 + (rs + rst) ** 2)
margin = 1 / interaction_ratio - 1
```

The zero-margin interaction curve is therefore:

```text
(Rt + Rb)^2 + (Rs + Rst)^2 = 1
```

Positive margin means the point is inside the interaction curve. A displayed
margin of `37%` means the current combined interaction ratio is roughly
`1 / 1.37`.

## Full Calculation Flow

```text
Read bolt size and margin basis
        |
        v
Look up minor area and NAS1348 stress area
        |
        v
Select bolt_thread_area from margin basis
        |
        v
Calculate radius and moment of inertia
        |
        v
Look up/contact geometry and crush areas
        |
        v
Calculate assembly tensile stress and Walker coefficient
        |
        v
For each ExampleScenario bolt row:
    read FZ, MX, MY from L1
    calculate tensile stress
    calculate bending stress
    calculate fiber stress
    calculate Walker-corrected LCF alternating stress
    assign fatigue life bucket
    calculate bolt-side and nut-side crush stresses

For each ExampleScenario interaction row:
    read FX, FY, FZ, MX, MY, MZ from L1
    calculate PLUG, SHEAR, BENDING, and Torsion resultants
    calculate Rt, Rb, Rs, and Rst
    combine ratios with the circular interaction formula
    calculate margin
```

## Reference Calculation: BOLT01

reference `L1` inputs for `BOLT01`:

```text
FZ = 10856 N
MX = 182 N*mm
MY = -140 N*mm
```

Benchmark constants:

```text
bolt_thread_area = 21.5966636878 mm^2
bolt_radius = 2.6219137210 mm
moment_of_inertia = 37.1161966138 mm^4
bolt_contact_crush_area = 48.2759903697 mm^2
nut_contact_crush_area_min = 46.58 mm^2
assembly_tensile_stress = 537.12 MPa
walker_coefficient = 0.6384
```

Step-by-step:

```text
tensile_stress = abs(10856) / 21.5966636878
               = 502.67 MPa
               -> displayed as 502.7 MPa

bending_moment = sqrt(182^2 + (-140)^2)
               = 229.62 N*mm

bending_stress = 229.62 * 2.6219137210 / 37.1161966138
               = 16.22 MPa

fiber_stress = 502.67 + 16.22
             = 518.89 MPa
             -> displayed as 518.9 MPa

lcf_alt = 537.12 * (1 - 518.89 / 537.12)^0.6384 * 1.25
        = 77.44 MPa
        -> displayed as 77.4 MPa

life = "Infinite" because 77.44 <= 167

flange_crush_stress_bolt = 10856 / 48.2759903697
                          = 224.87 MPa
                          -> displayed as 224.9 MPa

flange_crush_stress_nut = 10856 / 46.58
                         = 233.06 MPa
                         -> displayed as 233.1 MPa
```

## Reference Interaction Calculation: BOLT01

Reference interaction inputs for `BOLT01`:

```text
FX = -16.7 N
FY = -165.6 N
FZ = 10856.2 N
MX = 182.0 N*mm
MY = -140.0 N*mm
MZ = -4.8 N*mm
```

Benchmark constants:

```text
bolt_thread_area = 21.5966636878 mm^2
bolt_radius = 2.6219137210 mm
moment_of_inertia = 37.1161966138 mm^4
polar_moment_of_inertia = 74.2323932276 mm^4
yield_002 = 708.65 MPa
shear_strength = 708.65 / sqrt(3) = 409.14 MPa
```

Step-by-step:

```text
plug = abs(10856.2)
     = 10856.2 N
     -> displayed as 10,856

shear = sqrt((-16.7)^2 + (-165.6)^2)
      = 166.44 N
      -> displayed as 166.5

bending = sqrt(182.0^2 + (-140.0)^2)
        = 229.62 N*mm
        -> displayed as 229.7

torsion = abs(-4.8)
        = 4.8 N*mm

Rt = (10856.2 / 21.5966636878) / 708.65
   = 0.709

Rb = (229.62 * 2.6219137210 / 37.1161966138) / 708.65
   = 0.023

Rs = (166.44 / 21.5966636878) / 409.14
   = 0.019

Rst = (4.8 * 2.6219137210 / 74.2323932276) / 409.14
    = 0.0004
    -> displayed as 0.000

interaction_ratio = sqrt((0.709 + 0.023)^2 + (0.019 + 0.0004)^2)
                  = 0.7325

margin = 1 / 0.7325 - 1
       = 0.365
       -> displayed as 37%
```

## Implementation Notes

- Use `N*mm` moments in the formula. Convert from `N*m` to `N*mm` before
  calculating bending stress if needed.
- Preserve the branch logic in the Walker correction. The formula changes
  depending on whether `fiber_stress` is below or above
  `assembly_tensile_stress`.
- Preserve the life-bucket boundaries exactly. The reference calculation uses inclusive
  upper bounds.
- The source `VLOOKUP` formulas omit the fourth argument, so Excel performs
  approximate matching. A future implementation should use exact dictionary
  lookups by bolt size unless approximate lookup behavior is deliberately needed
  for compatibility testing.
- Several reference values are rounded. Validation should compare
  displayed values to a tolerance unless exact source cell values are
  available.
- The reference lower-right `Normal / Limit / Ultimate` table is not used by the
  documented row-level interaction margin formulas. It may be chart/reference data
  for plotted curves and should be documented separately if chart reproduction is
  required.




