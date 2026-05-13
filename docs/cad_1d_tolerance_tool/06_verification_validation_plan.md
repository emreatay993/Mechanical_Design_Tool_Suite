# Verification and Validation Plan

## Verification Strategy

- Keep domain and calculation tests independent from GUI and CAD kernel dependencies.
- Add geometry adapter tests around small neutral CAD fixtures.
- Add persistence round-trip tests for `.tolproj` projects with CAD references and stackups.
- Add GUI model/view tests for table columns, selection state, summary/detail transitions, and edited tolerance propagation.
- Add visual regression screenshots for the main shell once the UI stabilizes.
- Validate UI fidelity against the local video context pack and frame sheets.

## Test Commands

Existing baseline:

```powershell
$env:PYTHONPATH="src"; python -m unittest discover -s tests
```

Future CAD-specific tests should remain runnable without a live GUI where possible:

```powershell
$env:PYTHONPATH="src"; python -m unittest discover -s tests -p "test_cad_tolerance*.py"
```

Primary CAD viewer tests must run in the Python 3.12 OCCT/PyQt6 environment so the real AIS/V3d viewer stack is validated:

```powershell
$env:PYTHONNOUSERSITE="1"; $env:PYTHONPATH="src"; & "C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe" -s -m unittest discover -s tests -p "test_cad_viewer*.py"
```

## Validation Scenarios

| Case | Purpose | Inputs | Expected Result | Source |
| --- | --- | --- | --- | --- |
| V01 | Import neutral CAD | STEP assembly with at least two parts and planar/cylindrical faces | Assembly tree, shaded viewport, selectable faces/edges/vertices | Requirements FR-CAD and FR-VIEW |
| V02 | Guided stackup creation | Two endpoint features, direction, plane, loop parts | New stackup with generated contributors and annotations | Transcript `00:04:55-00:07:01` |
| V03 | Linear tolerance editing | Generated contributors with symmetric/asymmetric tolerances | Worst-case and RSS update immediately | Transcript `00:08:14-00:10:14` |
| V04 | Manual GD&T entry | Runout or position row with datum reference | GD&T row appears in detail table and result updates | Transcript `00:12:05-00:13:49` |
| V05 | Summary dashboard | Multiple stackups with mixed pass/fail states | Summary rows show OK/status, objective, results, predicted quality, and #Dims | Transcript `00:19:07-00:21:08` |
| V06 | Contributions | Stackup with multiple contributors | Contributions sorted by percent variation contribution | Transcript `00:21:42-00:22:09` |
| V07 | Non-1D warning | Offset or rotationally sensitive loop fixture | Dashboard and detail show warning state | Transcript `00:15:55-00:19:07` |
| V08 | Report generation | Stackups, snapshots, and results | HTML report with summary, snapshots, tables, and plots | Transcript `00:22:09-00:23:36` |
| V09 | UI fidelity | Main shell and detail views | Layout, density, colors, table columns, and transitions match visual evidence | Visual sheets 002-007 |
| V10 | Targeted visual fidelity | Main shell, guided toolbar, result plots, dashboard badges, report pages | UI matches `extracted_specs/2026-05-12_eztol_targeted_visual_review.md` or records explicit fidelity gaps | Targeted visual review |
| V11 | Primary OCCT viewer | STEP fixture in `mdts-cad312` with PyQt6 and `pythonocc-core` `novtk` | AIS/V3d widget initializes, renders nonblank shaded geometry, supports fit/orbit/pan/zoom, maps at least one face selection to `ShapeReference` | Requirements FR-VIEW-001A through FR-VIEW-006 |

## Neutral CAD Fixture Requirements

Trackable fixture placeholders are documented under `tests/fixtures/cad_1d_tolerance/`.

| Fixture ID | Required Format | Minimum Geometry | Verification Target |
| --- | --- | --- | --- |
| CAD1D-STEP-ASM-001 | STEP AP203/AP214/AP242 | Two or more assembly parts, planar faces, one cylindrical feature, millimeter units | V01 import, assembly tree, endpoint selection, shape references |
| CAD1D-IGES-BREP-001 | IGES | One B-Rep part with planar and cylindrical faces, millimeter units | V01 IGES import and basic feature metadata |
| CAD1D-NON1D-001 | STEP AP203/AP214/AP242 | Offset or rotationally sensitive loop geometry | V07 non-1D warning heuristic tests |
| CAD1D-PROJECT-001 | `.tolproj` JSON | CAD source metadata, one passing stackup, one failing or warning stackup, asymmetric contributor examples | Persistence, report, and UI model tests after the relevant packets land |

Fixture acceptance rules:

- Use neutral formats only for P0; native CAD, JT, STL, and OBJ are not acceptance fixtures for this clone.
- Keep units explicit and default to millimeters.
- Include at least one planar endpoint and one cylindrical/axis-like feature across the fixture set.
- Include stable display names that can drive deterministic tree and table tests.
- If a binary fixture cannot be committed, record the generator script or local artifact path in this directory before relying on it in tests.

## Reference Cases

- Manual loop from transcript opening: bushing ID alignment, nominal misalignment `0`, objective/worst-case variation near `+/-0.75`.
- Linear tolerance examples from transcript: `+/-0.05`, `+/-0.075`, `+/-0.25`.
- GD&T examples from transcript: runout `0.1` to datum `A`, position `0.15` to datum `A`.
- Multi-stackup examples from transcript: vertical coaxiality, surface flushness, overall height, wheel clearance, axial wheel clearance.

## Acceptance Criteria

- P0 domain tests cover worst-case, RSS, asymmetric tolerances, contribution ranking, and project round-trip.
- P0 CAD tests import at least one STEP and one IGES fixture.
- Primary viewer smoke tests prove the PyQt6 AIS/V3d widget renders nonblank geometry and selection remains B-Rep-backed, not mesh-only.
- P0 UI tests verify the summary table and detail table column sets.
- P0 report tests generate deterministic HTML from a fixture project.
- Before any overnight agent claims completion, it must state which canonical docs it reread and which evidence timestamps, visual review key frames, or sheets resolved UI uncertainty.
- Before P04, P05, P06, or P07 claims completion, the agent must inspect `extracted_specs/2026-05-12_eztol_targeted_visual_review.md`.

## Residual Risks

- Neutral CAD fixtures may not cover all STEP/IGES topology variants.
- Visual fidelity cannot be fully verified until the CAD viewport and annotation layer exist.
- Non-1D warnings need engineering thresholds that are not specified in the demo.
