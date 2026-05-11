# Next-Version UI/UX Design Spec

This document defines the target user experience for the next-version tolerance
tool.

## UX Direction

The next version should feel like a structured engineering workspace rather
than a spreadsheet. The spreadsheet mockup is useful for data shape, but the
implemented UI should reduce empty-cell scanning, make hierarchy clear, and keep
decisions tied to live results.

Primary UX goals:

| Goal | Design implication |
| --- | --- |
| Fast setup | Default `JOINT A`, `JOINT A.1`, and three flanges are created automatically. |
| Clear hierarchy | Joints, sub-joints, and stackup paths are visually nested. |
| Low manual entry | Standard nuts, inserts, bolts, washers, and brackets come from catalogs. |
| Decision visibility | Bolt length candidates, stackup results, thread protrusion, and warnings are visible on the same page. |
| Safe editing | Invalid or incomplete inputs are flagged inline and in summary status. |
| Engineering traceability | Every result links back to the path items and catalog records that created it. |

## Information Architecture

```text
Tolerance Project
  Main Workspace
    Joint Setup
    Joint Bolt Detail
    Calculation Summary
    Thread Protrusion Summary
  Stackup Path Builder
    Path Items
    Standard Part Picker
    Bolt Length Candidates
    Live Results
    Optimization
  Reports
    PDF/PNG summary
    CSV calculation export
```

## Main Workspace Layout

The main workspace should use a dense but readable engineering layout:

```text
+--------------------------------------------------------------------------+
| Project name / units / save / export                                     |
+----------------------------------------+---------------------------------+
| Joint setup                            | Guidance and validation          |
| - JOINT A                              | - Missing fields                 |
| - Add joint                            | - Catalog status                 |
| - Flange 1/2/3 + Add flange            | - Project-level warnings         |
+----------------------------------------+---------------------------------+
| Joint bolt detail                      | Thread protrusion summary         |
| - JOINT A                              | - 1.5P / 2P / 2P+Chamfer          |
|   - JOINT A.1  [Open path]             | - pass/warn/fail by sub-joint     |
| - JOINT B                              |                                  |
|   - JOINT B.1 ...                      |                                  |
+----------------------------------------+---------------------------------+
| Calculation summary: Worst Case Dev. / RSS / 1.5RSS / Top 4 Contributor  |
+--------------------------------------------------------------------------+
```

## Main Workspace Behavior

| Area | Behavior |
| --- | --- |
| Project header | Shows project title, unit system, save state, and export actions. |
| Joint setup table | Allows editing joint names and flange thickness/tolerance values. |
| Add joint | Adds the next joint name by sequence, for example `JOINT B`. |
| Add flange | Adds a new flange column with thickness and tolerance fields. |
| Joint bolt detail | Shows each joint with generated sub-joints and bolt fields. |
| Open path action | Opens the stackup path builder for the selected sub-joint. |
| Calculation summary | Shows numeric results pulled from each saved or applied path. |
| Thread protrusion summary | Shows bolt-length-related result status by sub-joint. |
| Validation area | Aggregates project-level issues and links users to the source field. |

The default state should not be blank. It should show `JOINT A`, `JOINT A.1`,
three flange columns, and a clear prompt to open the first stackup path.

## Stackup Path Builder Layout

The stackup path builder may be a modal, docked page, or separate window, but it
must behave as one focused workspace for the selected sub-joint.

```text
+----------------------------------------------------------------------------+
| Breadcrumb: JOINT A > JOINT A.1     Save Path   Apply   Close               |
+--------------------------+--------------------------+----------------------+
| Ordered stackup path     | Selected item properties | Live results         |
| - Flange 1 ref           | - Source: flange/catalog | Worst case           |
| - Flange 2 ref           | - Nominal thickness      | RSS                  |
| - Flange 3 ref           | - Tolerance              | 1.5RSS               |
| - Add bracket            | - Include in stack       | Top contributors     |
| - Nut/Insert selection   |                          | Thread protrusion    |
+--------------------------+--------------------------+----------------------+
| Standard part picker     | Bolt size/type/length candidates + Optimize      |
+----------------------------------------------------------------------------+
```

## Stackup Path Builder Behavior

| Action | Expected behavior |
| --- | --- |
| Open sub-joint | Loads the saved path or creates a default path from the parent joint flanges. |
| Add path item | Lets the user add catalog parts or custom items. |
| Select nut/insert | Pulls standard dimensions, compatible sizes, and engagement fields from catalog data. |
| Select bolt size/type | Filters available bolt length candidates. |
| Select bolt length | Recalculates results immediately. |
| Save path | Persists the path and updates the main summary tables. |
| Optimize | Ranks available bolt length candidates and highlights recommended choices. |

The user should not need to return to the main workspace to see whether a bolt
length choice works.

## Component Picker UX

The component picker should support:

| Capability | Detail |
| --- | --- |
| Search | Find standard parts by name, family, size, or type. |
| Filter | Filter by bolt size compatibility, part type, and catalog source. |
| Part preview | Show nominal thickness, tolerance, engagement data, and source. |
| Add as catalog item | Inserts a locked catalog-backed item. |
| Add as custom item | Inserts an editable custom item with required trace notes. |
| Missing data state | Clearly marks catalog records that cannot be used for calculation. |

## Visual Design Direction

| Area | Direction |
| --- | --- |
| Overall style | Quiet engineering application, compact tables, clear hierarchy, restrained color. |
| Status colors | Use color plus text/icon status; never rely on color alone. |
| Tables | Sticky headers, row grouping, inline validation, and stable column widths. |
| Path visual | Ordered vertical stack or compact bolt-axis diagram that reflects path order. |
| Results panel | Always visible in the path builder, with summary first and details below. |
| Optimization | Show recommended candidate, rejected candidates, and reasons. |

Avoid a decorative landing page. The first screen should be the project
workspace.

## Validation And Error UX

Validation should be layered:

| Level | Example |
| --- | --- |
| Inline field | `Flange 2 tolerance must be non-negative.` |
| Row status | `JOINT A.1 path incomplete: select nut or insert.` |
| Panel summary | `3 issues block bolt length optimization.` |
| Result status | `Selected bolt length fails 2P+Chamfer protrusion.` |

Validation messages should include the exact object name when possible:

```text
JOINT B > JOINT B.3 > Bracket: thickness is required.
```

## Result Presentation

The path builder live results panel should show:

| Result | Presentation |
| --- | --- |
| Worst-case deviation | Numeric value with pass/warn/fail status if limits exist. |
| RSS | Numeric value and range. |
| 1.5RSS | Numeric value for conservative screening. |
| Top four contributor sum | Percentage and contributor names. |
| Thread protrusion | Values against `1.5P`, `2P`, and `2P+Chamfer` criteria. |
| Candidate ranking | Recommended bolt length and alternatives with reasons. |

The main workspace should show the same summary at row level so the user can
compare sub-joints without reopening each path.

## Accessibility And Productivity

| Requirement | Detail |
| --- | --- |
| Keyboard editing | Users can move through tables with Tab/Enter and add rows without mouse-only workflows. |
| Undo-friendly edits | Destructive actions such as deleting a joint or path item require confirmation or undo. |
| Resize behavior | Tables and result panels remain usable on laptop screens. |
| Searchable catalogs | Large standard part lists must not require scrolling-only selection. |
| Clear save state | The UI shows unsaved changes and last saved time. |
