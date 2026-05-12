# Data Model and Calculation Methods

## Design Goals

- Represent CAD-derived 1D stackups without coupling the core model to any specific CAD kernel or Qt class.
- Preserve traceability from each tolerance contributor back to source CAD geometry, manual user edits, and shared requirements.
- Support the demonstrated worst-case, RSS, statistical quality, contribution, and objective comparison workflows.
- Allow manual GD&T/GPS contributor entry before attempting direct PMI interpretation.

## Domain Objects

| Object | Purpose | Key Fields |
| --- | --- | --- |
| `CadToleranceProject` | Root project document | schema version, units, CAD documents, stackups, settings, snapshots, reports |
| `CadDocument` | Imported neutral CAD source | source path, hash, format, import timestamp, units, assembly root, color/name metadata |
| `AssemblyNode` | Assembly browser node | id, name, node type, parent id, children, transform, display color, source label |
| `ShapeReference` | Stable-enough topology reference | document id, assembly path, OCCT/XDE label if available, shape type, geometric signature, fallback display name |
| `FeatureReference` | User-facing picked feature | feature type, shape reference, axis/normal/point data, owner part, datum label |
| `StackupRequirement` | One measured 1D requirement | name, endpoint features, direction vector, annotation plane, objective, target quality, analysis mode, warning state |
| `StackupContributor` | One row in the stackup table | name, sensitivity, nominal, tolerance minus/plus, tolerance type, datum references, source feature, shared flag |
| `GeometricTolerance` | Manual GD&T/GPS contributor | control type, tolerance value, material modifier if later added, datum frame, conversion rule |
| `StackupResult` | Calculated outcome | nominal, worst-case minus/plus, RSS minus/plus, quality metrics, pass/fail/warning, contributors |
| `Snapshot` | Report-ready viewport state | camera, visible stackups, annotation positions, image path/blob reference, timestamp |

## CAD Inputs

P0 supported input formats:

- STEP AP203/AP214/AP242
- IGES

P1/P2 options:

- STL/OBJ only for visualization, not stackup topology.
- STEP AP242 PMI/GD&T metadata as a research spike, not a first clone requirement.
- Native commercial formats are out of scope for the initial clone.

## Tolerance Chain Model

Each stackup is a signed 1D chain:

```text
requirement = sum(sensitivity_i * nominal_i)
worst_minus = sum(abs(sensitivity_i) * tolerance_minus_i)
worst_plus  = sum(abs(sensitivity_i) * tolerance_plus_i)
rss_minus   = sqrt(sum((abs(sensitivity_i) * tolerance_minus_i)^2))
rss_plus    = sqrt(sum((abs(sensitivity_i) * tolerance_plus_i)^2))
```

`sensitivity_i` is usually `+1` or `-1` for a first clone. The model should not assume that forever; GD&T-derived contributors or future lever-arm approximations may use different effective sensitivities.

## Calculation Methods

### Worst Case

- Sum directional tolerances linearly.
- Preserve minus/plus direction independently.
- Compare the resulting envelope against the objective tolerance.

### RSS

- Sum independent contributors by root-sum-square.
- Preserve directional minus/plus RSS for asymmetric contributors.
- Use RSS as a displayed analysis mode and as input to statistical quality views.

### Statistical Quality

- Persist project-level defaults for target quality and sigma coverage.
- Compute an achieved variation at target quality and a predicted quality at objective tolerance.
- Use Cp/Cpk or a sigma-equivalent metric consistently. Exact formulas should be documented in tests once adopted.
- Existing repo code already has deterministic Monte Carlo settings and stackup result types in `src/mechanical_design_tool_suite/tolerance_methods.py`; reuse the pure-domain style.

### Contribution Ranking

- Contributor contribution is based on variance fraction for statistical/RSS views:

```text
contribution_i = variance_i / sum(variance_j)
```

- Display sorted percentages in the `Contributions` tab.
- Preserve zero-variance and no-contributor edge cases without division errors.

### GD&T / GPS 1D Conversion

Manual GD&T rows should store the original control and the derived 1D effect. P0 conversion support:

- Runout to a datum axis: effective radial/diametral variation along the chosen stack direction.
- Position to datum frame: effective translational variation projected onto the stack direction.
- Profile-equivalent control: effective boundary variation projected onto the stack direction.

Every conversion must keep a traceable source note so the user can audit how the geometric control became a 1D contributor.

## Non-1D Warning Heuristics

The tool should warn, not block, when geometry suggests a 1D result may be incomplete:

- Endpoint or constraint features are laterally offset from the selected stack direction.
- Loop includes cylindrical/rotational constraints whose angular variation could affect the measured requirement.
- Selected direction is not aligned with dominant constraint normals/axes.
- The loop spans multiple separated interfaces where rotations can amplify translational variation.
- A contributor's projected effect is highly sensitive to the selected direction or annotation plane.

Threshold values remain an engineering decision and should be implemented as configurable constants with tests.

## Assumptions and Limits

- Units default to millimeters.
- The P0 clone does not solve angular deviation or full 3D tolerance analysis.
- The P0 clone does not import native commercial CAD files.
- The P0 clone does not automatically consume native CAD PMI.
- Topological naming across model revisions is a risk. Store multiple reference hints, not a single brittle id.
