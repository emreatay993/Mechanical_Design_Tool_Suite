# vNext Implementation Plan

Reference file: `docs/tolerance_tool/vnext/06_implementation_plan.md`.

## Summary

Implement the tolerance tool vNext as a parallel subsystem while preserving the
current single-stackup tolerance GUI. The vNext workspace shall use a Qt Quick /
QML interface with Qt Fusion light styling and a React-like engineering
application feel: clear hierarchy, card-like panels, dense but readable tables,
inline validation, and same-page bolt length decisions.

## Implementation Scope

- Keep `tolerance.py` as the low-level worst-case/RSS calculation source.
- Add vNext domain, catalog, calculation, optimizer, project IO, and QML GUI
  modules.
- Ship a sample standard-part catalog so the first version is immediately
  usable without waiting for final engineering data.
- Add a separate source launcher and console entry point:
  `tolerance-analysis-vnext-gui`.
- Keep the legacy `tolerance-analysis-gui` entry point available.
- Default to Qt Quick Fusion light styling and allow modern Qt Quick Controls
  alternatives such as `Material` and `Universal` through `--quick-style`.

## UI/UX Plan

- Build an Integrated Workspace:
  - left panel: joints and sub-joints.
  - center panel: selected joint setup and stackup path builder.
  - right panel: live results, bolt/engagement choices, thread checks, and
    optimization.
  - bottom/center summary area: project-level summary rows.
- Use Qt Quick Controls with Fusion light as the default, plus selectable
  Material/Universal-style options where the local Qt install supports them.
  The custom layout still uses restrained colors, rounded panels, stable
  spacing, and action buttons that read like a professional engineering tool
  rather than a spreadsheet clone.
- Expose the app style choice in the vNext workspace header as an application
  preference. Because Qt Quick Controls styles are selected at startup, changes
  are saved for the next launch rather than stored in `.tolproj` project data.
- Default state shall include `JOINT A`, `JOINT A.1`, three flanges, a linked
  stackup path, sample bolt data, and visible live results.

## Calculation And Data Plan

- Model projects as versioned `.tolproj` JSON files.
- Model joints, flanges, sub-joints, stackup paths, path items, catalog parts,
  and calculation snapshots explicitly.
- Generate default stackup paths from parent joint flanges and keep linked
  flange path items synchronized.
- Calculate nominal stack, worst-case deviation, RSS, 1.5RSS, top-four
  contributor percentage, and thread protrusion/engagement status.
- Implement provisional sample-catalog protrusion rules:
  - units are millimeters.
  - bolt length datum is under-head length.
  - nut protrusion equals `bolt_length - stack_nominal - nut_thickness`.
  - thread criteria are `1.5P`, `2P`, and `2P+Chamfer`.

## Test Plan

- Preserve existing tolerance tests.
- Add vNext tests for default project creation, stackup calculations,
  contributor ranking, flange/path synchronization, catalog-based optimization,
  project save/load, backend state, and CSV export.
- Verify that the QML file loads under an offscreen Qt platform.
