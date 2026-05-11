# Next-Version Architecture And Persistence

This document proposes architecture and persistence behavior for the
next-version tolerance tool.

## Architecture Goals

| Goal | Implication |
| --- | --- |
| Keep calculations testable | Domain and calculation logic stay outside PyQt widgets. |
| Support catalogs | Standard part data is loaded through a catalog service. |
| Support project save/load | Editable project state uses a versioned file format. |
| Support live UI results | UI controllers recalculate affected sub-joints after edits. |
| Support extensible methods | Bolt length optimization, asymmetric tolerances, Monte Carlo, and future methods can live in the domain layer without rewriting the UI shell. |

## Proposed Module Boundaries

```text
bolt_calculation_tool/
  tolerance.py                         current baseline stackup calculation
  tolerance_models.py                  vNext dataclasses/domain models
  tolerance_methods.py                 vNext stackup, contributor, protrusion methods
  tolerance_catalog.py                 standard part catalog loading/querying
  tolerance_project_io.py              project save/load and migration
  tolerance_optimizer.py               bolt length candidate ranking
  tolerance_gui.py                     current GUI or transitional launcher
  tolerance_vnext_gui.py               next-version GUI shell and views
```

The exact filenames may change, but the separation should not:

| Layer | Responsibility |
| --- | --- |
| Models | Project, joint, flange, sub-joint, path, item, catalog, and result objects. |
| Methods | Pure calculations and validation. |
| Catalog service | Load, validate, search, and filter standard parts. |
| Project IO | Save/load versioned project files. |
| Optimizer | Rank bolt length and configuration candidates. |
| GUI | User interaction, presentation, dialogs, and export orchestration. |

## Data Flow

```text
User edits joint/flange/sub-joint/path
        |
        v
GUI controller updates project model
        |
        v
Validation service identifies incomplete or invalid fields
        |
        v
Calculation service recomputes affected path results
        |
        v
Optimizer ranks bolt length candidates when enough data exists
        |
        v
GUI updates live results and summary tables
        |
        v
Project IO persists state on save/autosave
```

## Catalog Integration

Standard parts should be loaded from data files rather than hardcoded widgets.
Acceptable initial formats:

| Format | Use |
| --- | --- |
| JSON | Best for structured standard part records and validation. |
| CSV | Good for bolt length tables and simple hardware lists. |
| XLSX import | Useful if engineering source data already lives in spreadsheets, but should be converted to validated internal records. |

Catalog loading shall validate:

| Validation | Example |
| --- | --- |
| Required fields | Bolt records need size, type, pitch, and available lengths. |
| Numeric fields | Thickness, tolerance, pitch, chamfer, and length fields are finite numbers. |
| Compatibility | Nut and insert records declare compatible bolt sizes. |
| Units | Catalog values declare units or inherit a catalog-level unit system. |
| Duplicate IDs | Duplicate part IDs are rejected. |

## Project File Format

The next version shall use a versioned project file. JSON is recommended for the
first implementation because it is human-reviewable and easy to test.

Recommended extension:

```text
.tolproj
```

Minimum top-level shape:

```json
{
  "schema_version": 1,
  "title": "Tolerance Project",
  "unit_system": "mm",
  "method_settings": {
    "sigma_coverage": 3.0
  },
  "joints": [],
  "catalog_references": []
}
```

Saved projects shall preserve enough data to reopen and continue editing
without requiring recalculation from screenshots or exported reports.

## Save And Autosave

| Behavior | Requirement |
| --- | --- |
| Save | Writes the current project to the chosen project file. |
| Save As | Writes the current project to a new file. |
| Unsaved indicator | Shows unsaved changes in the window title or header. |
| Autosave | Optional for baseline, but recommended to protect long editing sessions. |
| Save validation | Allows saving incomplete projects, but marks incomplete calculations clearly. |

Incomplete projects should be savable. Engineering users may build a project in
stages before all catalog choices are available.

## Migration

Because the project file is versioned, loading shall include a migration step:

```text
read file
check schema_version
migrate to current in-memory model
validate migrated model
show migration warnings if needed
```

Unknown future schema versions shall be rejected with a clear message.

## Export Architecture

Reports and exports should read from calculation result objects, not directly
from GUI widgets. PDF/PNG rendering can still capture views, but calculation
tables should be exportable from structured data.

Required exports:

| Export | Source |
| --- | --- |
| PDF report | Project metadata, joint setup, selected paths, summaries, and warnings. |
| PNG view export | Current visual workspace or path builder view. |
| CSV summary | Calculation summary and thread protrusion summary tables. |

## Backward Compatibility With Current Tool

The current `calculate_stackup` function can remain as a low-level method for a
simple path. The next-version model should adapt path items into calculation
inputs rather than rewriting the current baseline behavior inside the GUI.

Suggested adapter:

```text
StackupPath items
  -> included nominal/tolerance rows
  -> stackup calculation
  -> vNext result object
```

This keeps the existing worst-case/RSS behavior testable while allowing the
new workflow to add catalog and bolt-length logic around it.
