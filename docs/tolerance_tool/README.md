# Tolerance Tool Design Documents

This folder contains the design specification set for the standalone tolerance
analysis GUI. The tool is the Five Flute-style tolerance stackup calculator
implemented separately from the main bolt calculation GUI.

## Document Set

| Document | Purpose |
| --- | --- |
| [01_requirements.md](01_requirements.md) | Product, functional, input, output, validation, export, and packaging requirements. |
| [02_calculation_methods.md](02_calculation_methods.md) | Worst-case, RSS, tail-risk, validation, and current calculation assumptions. |
| [03_user_interface_workflow.md](03_user_interface_workflow.md) | User-facing workflow, screen behavior, validation states, plotting, and export behavior. |
| [04_software_architecture.md](04_software_architecture.md) | Module responsibilities, data flow, dependencies, launch paths, and extension points. |
| [05_verification_validation_plan.md](05_verification_validation_plan.md) | Unit, integration, export, and manual verification plan for the tolerance tool. |
| [vnext/README.md](vnext/README.md) | Next-version requirements, UI/UX, data model, calculation, architecture, persistence, and validation specs. |

## Implementation References

| Area | Reference |
| --- | --- |
| Domain calculation | [`../../src/bolt_calculation_tool/tolerance.py`](../../src/bolt_calculation_tool/tolerance.py) |
| Standalone PyQt6 GUI | [`../../src/bolt_calculation_tool/tolerance_gui.py`](../../src/bolt_calculation_tool/tolerance_gui.py) |
| Source checkout launcher | [`../../scripts/run_tolerance_analysis.py`](../../scripts/run_tolerance_analysis.py) |
| Package entry point | [`../../pyproject.toml`](../../pyproject.toml) |
| Regression tests | [`../../tests/test_tolerance_analysis.py`](../../tests/test_tolerance_analysis.py) |
| Visual mockups | [`../tolerance_stackup_mockups.html`](../tolerance_stackup_mockups.html) |

## Terminology Note

In this document set, "tolerance" means a dimensional stackup tolerance entered
by the user. This is separate from the main bolt-tool validation tolerances used
to compare benchmark outputs in the existing bolt calculation documents.
