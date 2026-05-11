# Tolerance Tool User Interface And Workflow

This document specifies the user-facing behavior for the standalone tolerance
analysis GUI implemented in
[`../../src/bolt_calculation_tool/tolerance_gui.py`](../../src/bolt_calculation_tool/tolerance_gui.py).

## Launch Paths

From a source checkout:

```powershell
python scripts\run_tolerance_analysis.py
```

From an editable package install:

```powershell
tolerance-analysis-gui
```

The current tolerance GUI is standalone. It is not launched from the main
`bolt-calc-gui` window.

## Screen Structure

The screen is organized as:

| Area | Behavior |
| --- | --- |
| Header | Shows "Tolerance Analysis", an editable analysis title, a disabled save button, and a Share export button. |
| Dimension input table | Lets the user edit name, nominal dimension, and plus/minus tolerance rows. |
| Dimension actions | Adds a default row, clears all rows, or removes an individual row. |
| Target inputs | Lets the user edit target minimum and target maximum dimensions. |
| Stackup plot | Draws target markers, cumulative dimension spans, nominal stackup, worst-case range, and RSS range. |
| Analysis table | Shows per-dimension terms plus worst-case, RSS, and tail-failure summary rows. |
| Status line | Reports successful recalculation, input errors, and export results. |

## Default Startup State

The GUI opens with:

| Field | Default |
| --- | --- |
| Title | `New Tolerance Analysis` |
| Dimension rows | Four rows named `#1` through `#4` |
| Nominal per row | `1` |
| Tolerance per row | `0.005` |
| Target min | `0.001` |
| Target max | `0.022` |

The app recalculates immediately after loading the defaults.

## Primary Workflow

1. The user edits the analysis title if needed.
2. The user enters or edits dimension rows.
3. The user enters target minimum and target maximum values.
4. The app recalculates automatically after input changes.
5. The user reviews the stackup plot, dimension analysis table, and tail-risk rows.
6. The user exports the analysis as PDF or PNG with the Share action.

## Dimension Table Behavior

| Action | Expected behavior |
| --- | --- |
| Add dimension | Appends a default dimension row and recalculates. |
| Remove row | Removes that row and recalculates. |
| Clear | Removes all dimension rows and recalculates, which produces a controlled input error until at least one row is present. |
| Fully blank row | Ignored by the GUI adapter. |
| Partial row with blank nominal | Rejected with a row-specific input error. |
| Partial row with blank tolerance | Rejected with a row-specific input error. |
| Blank name | Passed to the calculation layer and normalized to a row-style name. |

Nominal cells accept negative values. Tolerance cells are intended for
non-negative values and are also validated in the calculation layer.

## Recalculation And Error States

Every dimension and target edit triggers recalculation.

On success:

| Output | Behavior |
| --- | --- |
| Internal analysis state | Updated with the new `StackupAnalysis`. |
| Plot | Updated to the new stackup. |
| Analysis table | Repopulated with current dimension and summary rows. |
| Status line | Displays dimension count and nominal stackup. |

On input error:

| Output | Behavior |
| --- | --- |
| Internal analysis state | Cleared. |
| Plot | Cleared to empty-state behavior. |
| Analysis table | Cleared. |
| Status line | Displays `Input error: ...` in error styling. |

## Plot Behavior

The stackup plot scales to include:

| Plotted value |
| --- |
| Target minimum |
| Target maximum |
| Nominal stackup |
| Worst-case minimum and maximum |
| RSS minimum and maximum |
| Cumulative dimension endpoints |

The plot shows dimension spans, the average assembly dimension, worst-case
tolerance, RSS tolerance, and numeric range labels. If there is no valid
analysis, it shows an empty-state message asking the user to add dimensions.

## Analysis Table Behavior

The table reports:

| Row type | Values |
| --- | --- |
| Dimension rows | Dimension name, nominal, plus/minus tolerance, standard deviation, variance. |
| Worst-case summary | Nominal, plus/minus worst-case tolerance, worst-case standard deviation, worst-case variance. |
| RSS summary | Nominal, plus/minus RSS tolerance, RSS standard deviation, RSS variance. |
| RSS tail-risk summary | Left-tail and right-tail failure percentages. |

Display precision is four decimal places for nominal/tolerance-style values and
ten decimal places for standard deviation/variance-style values.

## Export Workflow

The Share action:

1. Opens a save dialog titled `Export tolerance analysis`.
2. Offers PDF and PNG formats.
3. Builds a default filename from a safe version of the analysis title plus a timestamp.
4. Renders the current page content to the selected format.
5. Reports success or failure through the status line.

The default export directory is the user's `Documents` directory when available;
otherwise it falls back to the user's home directory.

## Persistence Gap

The header includes a disabled `Save tolerance analysis` button. There is no
live persistence workflow for editable analysis files. The design baseline should
either implement a project file format or remove the disabled save action from
the production UI.
