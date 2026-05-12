# Tolerance Tool Next-Version Design Specs

This folder defines the next version of the tolerance tool. It converts the
provided spreadsheet mockup and chat workflow notes into English product,
UI/UX, data-model, calculation, architecture, persistence, and validation
specifications.

The next version is not just the current single-stackup calculator with a new
skin. It is a joint-driven stackup workspace where users define assembly joints,
flanges, sub-joints, stackup paths, standard hardware, bolt length candidates,
thread protrusion checks, and live optimization results.

## Document Set

| Document | Purpose |
| --- | --- |
| [01_requirements.md](01_requirements.md) | Product and functional requirements for joints, flanges, sub-joints, stackup paths, bolt length selection, summaries, and optimization. |
| [02_ui_ux_design_spec.md](02_ui_ux_design_spec.md) | User experience model, screen layout, interaction behavior, validation states, and visual design direction. |
| [03_data_model_and_calculation_methods.md](03_data_model_and_calculation_methods.md) | Domain model, standard-part catalog model, stackup path calculations, contributor metrics, and thread protrusion logic. |
| [04_architecture_and_persistence.md](04_architecture_and_persistence.md) | Proposed software architecture, module boundaries, catalog integration, autosave, project files, and migration approach. |
| [05_verification_validation_plan.md](05_verification_validation_plan.md) | Verification plan for requirements, UI workflows, calculations, persistence, catalogs, and exports. |
| [tolerance_stackup_qml_mockups.html](tolerance_stackup_qml_mockups.html) | Eight QML-style GUI mockup directions for the bolted-joint 1D tolerance stackup workflow. |
| [06_implementation_plan.md](06_implementation_plan.md) | Saved implementation plan and reference file for this vNext build. |

## Source Interpretation

The spreadsheet mockup describes:

- A top-level `JOINT` table with default `JOINT A`, editable joint names, add
  joint behavior, default two flange contributors, and add/delete flange behavior.
- A `JOINT BOLT DETAIL` table where each joint gets default sub-joints such as
  `JOINT A.1`, with bolt size, bolt type, and bolt length fields.
- A calculation summary table with worst-case deviation, RSS, 1.5RSS, and top
  four contributor sum.
- A thread protrusion table with criteria such as `1.5P`, `2P`, and
  `2P+Chamfer`.
- A stackup path builder opened from a sub-joint row.

The chat notes add that `JOINT A` and `JOINT A.1` should exist by default,
clicking `JOINT A.1` should open the stackup path page/window, the path should
be created from sensible defaults, the user should add only extra items such as
brackets and choose hardware such as nut or insert, standard parts should be
pulled automatically from data, and bolt length selection, results, and
optimization should happen on the same page.

## Relationship To Current Baseline

The current baseline remains documented in the parent folder. This next-version
spec reuses the existing worst-case and RSS terminology but expands the product
from one generic dimension list into a structured assembly workflow:

```text
Project
  -> Joint
    -> Flanges
    -> Sub-joints
      -> Stackup path
      -> Bolt length selection
      -> Summary and optimization results
```
