# Tolerance Tool Software Architecture

This document describes the implementation architecture for the standalone
tolerance analysis GUI.

## Module Responsibilities

| Module | Responsibility |
| --- | --- |
| [`../../src/bolt_calculation_tool/tolerance.py`](../../src/bolt_calculation_tool/tolerance.py) | Pure calculation/domain layer for tolerance stackup analysis. |
| [`../../src/bolt_calculation_tool/tolerance_gui.py`](../../src/bolt_calculation_tool/tolerance_gui.py) | PyQt6 GUI, input collection, plotting, output table, status messages, and PDF/PNG export. |
| [`../../scripts/run_tolerance_analysis.py`](../../scripts/run_tolerance_analysis.py) | Source checkout launcher that prepends `src` to `sys.path` and starts the GUI. |
| [`../../pyproject.toml`](../../pyproject.toml) | Package metadata and `tolerance-analysis-gui` console entry point. |
| [`../../tests/test_tolerance_analysis.py`](../../tests/test_tolerance_analysis.py) | Unit regression tests for the calculation layer. |

## Domain Data Model

The calculation layer exposes immutable dataclasses:

| Type | Purpose |
| --- | --- |
| `ToleranceDimension` | One input row: `name`, `nominal`, and bilateral `tolerance`. |
| `DimensionAnalysis` | Per-dimension calculated standard deviation and variance. |
| `StackupAnalysis` | Full calculation output: dimensions, target limits, nominal, worst-case, RSS, and tail-risk values. |

`StackupAnalysis` also provides convenience properties:

```text
worst_case_min = nominal - worst_case_tolerance
worst_case_max = nominal + worst_case_tolerance
rss_min = nominal - rss_tolerance
rss_max = nominal + rss_tolerance
```

## Data Flow

```text
User edits GUI fields
        |
        v
ToleranceAnalysisApp._dimensions_from_table()
        |
        v
calculate_stackup(dimensions, target_min, target_max)
        |
        v
StackupAnalysis
        |
        +--> StackupPlot.set_analysis()
        |
        +--> ToleranceAnalysisApp._fill_analysis_table()
        |
        +--> PDF/PNG export rendering
```

The GUI owns user interaction and presentation. The calculation module owns
numeric validation, normalization, and mathematical results.

## Error Handling

The calculation layer raises `ValueError` for invalid numeric input or invalid
target ordering. The GUI catches exceptions during recalculation, clears stale
outputs, and shows a controlled status-line error message.

Export errors are caught in the GUI and reported as `Export failed.` with the
exception detail printed to standard output.

## Dependencies

| Dependency | Use |
| --- | --- |
| Python `dataclasses` | Immutable calculation input/output objects. |
| Python `math` | Square root, finiteness checks. |
| Python `statistics.NormalDist` | RSS normal-tail failure-rate calculation. |
| PyQt6 | Standalone GUI, custom plot painting, table widgets, PDF/PNG rendering. |

The calculation layer does not depend on PyQt6.

## Launch And Packaging

Implemented launch paths:

| Path | Command |
| --- | --- |
| Source checkout | `python scripts\run_tolerance_analysis.py` |
| Editable install | `tolerance-analysis-gui` |
| Packaged selector | `dist\BoltCalculationTool\BoltCalculationTool.exe` |
| Packaged direct executable | `dist\BoltCalculationTool\ToleranceAnalysis.exe` |

Packaging note:

The PyInstaller spec builds a GUI suite folder. `BoltCalculationTool.exe` is the
end-user selector, while `ToleranceAnalysis.exe`, `ToleranceAnalysisVNext.exe`,
and `BoltCalculationGui.exe` remain available as direct launchers.

## Extension Points

| Future capability | Recommended architectural direction |
| --- | --- |
| Units | Add explicit unit metadata to inputs and outputs before calculation. |
| Asymmetric tolerances | Replace single `tolerance` with plus/minus fields or a tolerance object. |
| Signed stack directions | Add a contribution sign/direction field instead of overloading nominal values. |
| Correlation/covariance | Extend RSS calculation to include covariance terms while preserving the current independent default. |
| Monte Carlo | Add a separate calculation function and output object rather than mixing simulation state into `calculate_stackup`. |
| Sensitivity ranking | Compute contribution percentages from per-dimension variance and expose them through `StackupAnalysis` or a companion result. |
| Persistence | Define a versioned file schema containing title, rows, targets, units, and method settings. |
| Main GUI integration | Keep the calculation layer shared and embed only the PyQt view/controller pieces in the main application shell. |

## Current Boundaries

The tolerance tool should not depend on the bolt calculation formulas, bolt
benchmark documents, or ExampleScenario validation tolerances. It may share the
same package and distribution, but the calculation semantics are separate.
