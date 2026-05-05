# Bolt Calculation Tool Requirements

This document defines high-level requirements for the future Bolt Calculation
Tool. Detailed formulas, validation cases, GUI behavior, and implementation
architecture are defined in the other design specification documents.

Requirement status values:

| Status | Meaning |
| --- | --- |
| Proposed | Initial requirement, not yet fully reviewed |
| Accepted | Reviewed and approved for implementation planning |
| Deferred | Intentionally postponed |
| Rejected | Not planned |

Priority values:

| Priority | Meaning |
| --- | --- |
| P0 | Required for the first usable version |
| P1 | Important, but may follow the first usable version |
| P2 | Nice to have or future extension |

## Product Scope

| ID | Priority | Status | Requirement |
| --- | --- | --- | --- |
| REQ-SCOPE-001 | P0 | Proposed | The tool shall calculate and check a single bolt. |
| REQ-SCOPE-002 | P0 | Proposed | The tool shall calculate and check a joint design containing multiple bolts. |
| REQ-SCOPE-003 | P0 | Proposed | The first version shall primarily target mechanical engineers working on aerospace applications. |
| REQ-SCOPE-004 | P0 | Proposed | The calculation scope shall be driven by the failure checks defined in `02_calculation_methodology.md` and `09_design_criteria_checks.md`. |
| REQ-SCOPE-005 | P1 | Proposed | The tool shall allow additional failure checks to be added after the first version without redesigning the full application. |

## Standards And Design Criteria

| ID | Priority | Status | Requirement |
| --- | --- | --- | --- |
| REQ-STD-001 | P0 | Proposed | The tool shall support multiple selectable design code paths. |
| REQ-STD-002 | P0 | Proposed | The tool shall support in-house design criteria as selectable design code paths. |
| REQ-STD-003 | P0 | Proposed | The first-version standards priority shall be ASTM, ASME, ISO, then Eurocode. |
| REQ-STD-004 | P0 | Proposed | The selected design code path shall determine which checks, material allowables, derating rules, and acceptance criteria are applied. |
| REQ-STD-005 | P1 | Proposed | The tool shall keep design-code-specific logic separated so additional criteria can be added without changing unrelated code paths. |

## Units

| ID | Priority | Status | Requirement |
| --- | --- | --- | --- |
| REQ-UNIT-001 | P0 | Proposed | The tool shall support SI units. |
| REQ-UNIT-002 | P0 | Proposed | The tool shall support Imperial units. |
| REQ-UNIT-003 | P0 | Proposed | The tool shall explicitly track units for all user inputs, imported data, intermediate calculations, and reported outputs. |
| REQ-UNIT-004 | P0 | Proposed | The tool shall convert user-provided loads, moments, geometry, temperature, and material properties into the internal unit system required by the selected calculation methodology. |
| REQ-UNIT-005 | P0 | Proposed | The tool shall prevent mixing incompatible units without explicit conversion. |

## Load Input Requirements

| ID | Priority | Status | Requirement |
| --- | --- | --- | --- |
| REQ-LOAD-001 | P0 | Proposed | For each bolt node, the user shall be able to supply force components `FX`, `FY`, `FZ`. |
| REQ-LOAD-002 | P0 | Proposed | For each bolt node, the user shall be able to supply moment components `MX`, `MY`, `MZ`. |
| REQ-LOAD-003 | P0 | Proposed | Bolt forces and moments shall be interpreted at a single node point under the bolt head for a beam-style bolt representation. |
| REQ-LOAD-004 | P0 | Proposed | The tool shall support load components supplied in global coordinates. |
| REQ-LOAD-005 | P0 | Proposed | The tool shall support load components supplied in local bolt coordinates. |
| REQ-LOAD-006 | P0 | Proposed | In local bolt coordinates, the local `Z` axis shall be the bolt axial direction. |
| REQ-LOAD-007 | P0 | Proposed | In local bolt coordinates, positive local `Z` shall point toward the nut side of the bolt. |
| REQ-LOAD-008 | P0 | Proposed | The coordinate system used for each load set shall be explicitly specified by the user or by the imported data. |
| REQ-LOAD-009 | P1 | Proposed | The tool shall preserve original imported load values and report any converted values used for calculation traceability. |

## Tabular Data Import And Paste

| ID | Priority | Status | Requirement |
| --- | --- | --- | --- |
| REQ-IMPORT-001 | P0 | Proposed | The user shall be able to paste tabular bolt load data directly into the tool. |
| REQ-IMPORT-002 | P0 | Proposed | The user shall be able to import bolt load data from CSV files. |
| REQ-IMPORT-003 | P0 | Proposed | The user shall be able to import bolt load data from TSV files. |
| REQ-IMPORT-004 | P0 | Proposed | The user shall be able to import bolt load data from TXT files containing delimited tables. |
| REQ-IMPORT-005 | P0 | Proposed | The user shall be able to import bolt load data from Excel tables. |
| REQ-IMPORT-006 | P0 | Proposed | CSV, TSV, and TXT imports shall support different delimiter types. |
| REQ-IMPORT-007 | P0 | Proposed | The import parser shall support tables containing load columns, moment columns, and optional coordinate columns. |
| REQ-IMPORT-008 | P0 | Proposed | The import parser shall not require columns to appear in a fixed order. |
| REQ-IMPORT-009 | P0 | Proposed | The import parser shall map recognized headers to the required internal fields before calculation. |

## Header Recognition And Units

| ID | Priority | Status | Requirement |
| --- | --- | --- | --- |
| REQ-HEADER-001 | P0 | Proposed | The import parser shall recognize `NodeID` as an optional node identifier column. |
| REQ-HEADER-002 | P0 | Proposed | The import parser shall recognize `Node Number` as an optional node identifier column. |
| REQ-HEADER-003 | P0 | Proposed | The import parser shall recognize common force component headers including `FX`, `FY`, `FZ`, `Fx`, `Fy`, and `Fz`. |
| REQ-HEADER-004 | P0 | Proposed | The import parser shall recognize common moment component headers including `MX`, `MY`, `MZ`, `Mx`, `My`, and `Mz`. |
| REQ-HEADER-005 | P0 | Proposed | The import parser shall recognize coordinate headers `X`, `Y`, and `Z`. |
| REQ-HEADER-006 | P0 | Proposed | The import parser shall support similar practical header variations for node identifiers, force components, moment components, and coordinates. |
| REQ-HEADER-007 | P0 | Proposed | Force, moment, and coordinate headers may include unit labels. |
| REQ-HEADER-008 | P0 | Proposed | Unit labels may be attached directly to the header name, such as `FX[N]`. |
| REQ-HEADER-009 | P0 | Proposed | Unit labels may be separated from the header name by whitespace, such as `FX [N]`. |
| REQ-HEADER-010 | P0 | Proposed | Coordinate columns shall support unit labels `[m]`, `[cm]`, and `[mm]`. |
| REQ-HEADER-011 | P0 | Proposed | Force columns shall support unit labels `[N]` and `[kN]`. |
| REQ-HEADER-012 | P0 | Proposed | Moment columns shall support unit labels `[N.m]`, `[N*m]`, `[kN.m]`, `[kN*m]`, `[N.mm]`, and `[N*mm]`. |
| REQ-HEADER-013 | P0 | Proposed | The import parser shall convert recognized column units into the active internal unit system before calculation. |
| REQ-HEADER-014 | P0 | Proposed | Optional node identifier columns shall be retained for later use when supplied. |
| REQ-HEADER-015 | P0 | Proposed | The import workflow shall report unrecognized, missing, duplicate, or ambiguous headers before calculation. |

## Bolt Group Requirements

| ID | Priority | Status | Requirement |
| --- | --- | --- | --- |
| REQ-GROUP-001 | P0 | Proposed | The tool shall support single-bolt evaluations. |
| REQ-GROUP-002 | P0 | Proposed | The tool shall support multi-bolt group evaluations. |
| REQ-GROUP-003 | P0 | Proposed | The tool shall support circular planar bolt patterns. |
| REQ-GROUP-004 | P0 | Proposed | The tool shall support translational planar bolt patterns. |
| REQ-GROUP-005 | P1 | Proposed | The tool shall support custom bolt patterns. |
| REQ-GROUP-006 | P1 | Proposed | The tool shall support spatial three-dimensional bolt patterns. |
| REQ-GROUP-007 | P0 | Proposed | The tool shall not impose an artificial maximum number of bolts to evaluate. |
| REQ-GROUP-008 | P1 | Proposed | The tool shall handle large bolt counts using implementation choices that keep calculation performance and GUI responsiveness acceptable. |

## Node Coordinates And Visualization Data

| ID | Priority | Status | Requirement |
| --- | --- | --- | --- |
| REQ-NODE-001 | P0 | Proposed | `NodeID` and `Node Number` columns shall be optional in imported or pasted tables. |
| REQ-NODE-002 | P0 | Proposed | `X`, `Y`, and `Z` coordinate columns shall be optional in imported or pasted tables. |
| REQ-NODE-003 | P0 | Proposed | When `X`, `Y`, and `Z` coordinates are supplied, the tool shall use them for node visualization. |
| REQ-NODE-004 | P0 | Proposed | Coordinate units supplied in headers shall be applied before plotting node positions. |
| REQ-NODE-005 | P1 | Proposed | The tool shall preserve optional node identifiers so they can be used in later workflows, reports, and visualization labels. |

## PyVista Visualization

| ID | Priority | Status | Requirement |
| --- | --- | --- | --- |
| REQ-VIZ-001 | P0 | Proposed | The GUI shall provide a PyVista-based window for visualizing nodes when node coordinates are available. |
| REQ-VIZ-002 | P0 | Proposed | The PyVista visualization shall allow the user to display contour values of input force components `FX`, `FY`, and `FZ` on nodes. |
| REQ-VIZ-003 | P0 | Proposed | The PyVista visualization shall allow the user to display contour values of input moment components `MX`, `MY`, and `MZ` on nodes. |
| REQ-VIZ-004 | P0 | Proposed | The PyVista visualization shall allow the user to display contour values of derived input quantities, including applicable force and moment resultants. |
| REQ-VIZ-005 | P0 | Proposed | The PyVista visualization shall allow the user to display contour values of calculated outputs generated by the tool. |
| REQ-VIZ-006 | P0 | Proposed | The PyVista visualization shall allow the user to display contour values of calculated criteria values generated by the active design code path. |
| REQ-VIZ-007 | P0 | Proposed | The PyVista visualization shall allow the user to display contour values of calculated margins generated by the tool. |
| REQ-VIZ-008 | P1 | Proposed | The visualization shall support choosing which scalar value is currently displayed as a node contour. |

## Preload And Clamping Force

| ID | Priority | Status | Requirement |
| --- | --- | --- | --- |
| REQ-PRELOAD-001 | P0 | Proposed | The first version shall not require the user to provide preload as a separate input field. |
| REQ-PRELOAD-002 | P0 | Proposed | The first version shall not require the user to provide clamping force as a separate input field. |
| REQ-PRELOAD-003 | P0 | Proposed | The first version shall assume supplied FEA bolt loads already include preload effects where preload is relevant. |
| REQ-PRELOAD-004 | P1 | Proposed | Future versions may add explicit preload and clamping-force inputs if a calculation method requires them. |

## Temperature And Material Behavior

| ID | Priority | Status | Requirement |
| --- | --- | --- | --- |
| REQ-TEMP-001 | P0 | Proposed | The tool shall support temperature effects where required by the selected calculation methodology. |
| REQ-TEMP-002 | P0 | Proposed | The tool shall support temperature-dependent yield strength from material property tables. |
| REQ-TEMP-003 | P0 | Proposed | The tool shall support temperature-dependent yield strength from piecewise formulas. |
| REQ-TEMP-004 | P0 | Proposed | The tool shall support temperature-dependent yield strength using a constant derating factor. |
| REQ-TEMP-005 | P0 | Proposed | The active temperature method shall be visible in the calculation trace and result report. |
| REQ-TEMP-006 | P1 | Proposed | The tool shall allow additional temperature-dependent material properties to be added when future checks require them. |

## Calculation Behavior

| ID | Priority | Status | Requirement |
| --- | --- | --- | --- |
| REQ-CALC-001 | P0 | Proposed | The tool shall evaluate all active failure checks specified by the selected calculation methodology. |
| REQ-CALC-002 | P0 | Proposed | The tool shall allow the user to select which supported design code path or in-house criteria set is active for a calculation. |
| REQ-CALC-003 | P0 | Proposed | The tool shall identify pass/fail status for each active check. |
| REQ-CALC-004 | P0 | Proposed | The tool shall report governing checks for each bolt and for the overall bolt group where applicable. |
| REQ-CALC-005 | P1 | Proposed | The tool shall keep enough calculation traceability for engineering review of inputs, derived values, allowables, utilization values, and margins. |

## Open Requirement Questions

The following questions must be resolved before implementation starts:

| ID | Question |
| --- | --- |
| OQ-001 | What internal base unit system should be used: SI only internally, or selectable internal unit systems? |
| OQ-002 | Which exact ASTM, ASME, ISO, and Eurocode documents or clauses are in scope for the first version? |
| OQ-003 | Which in-house criteria are known today, and should they be treated as proprietary named methods or generic configurable methods? |
| OQ-004 | Which material properties besides yield strength are required in the first version? |
| OQ-005 | How should the tool handle missing or out-of-range temperature material data? |
| OQ-006 | Should coordinate transformations from global to local bolt axes be performed by the tool, or should the user provide already-transformed local loads when needed? |
| OQ-007 | For spatial bolt patterns, what geometry definition is required: coordinates only, local axes per bolt, joint plane definitions, or full connector metadata? |
| OQ-008 | What result quantities must appear in the first-version report for each bolt and for the complete joint? |
| OQ-009 | Which delimiter types must be supported explicitly for TXT and CSV imports beyond comma and tab? |
| OQ-010 | Should Excel import support a selected range, a named table, a selected sheet, or all sheets? |
| OQ-011 | Should ambiguous duplicate headers be rejected, or should the GUI provide a manual column-mapping step? |
| OQ-012 | Which derived resultants are required first for visualization: force resultant, shear resultant, bending resultant, moment resultant, torsion, or all of these? |
| OQ-013 | Which calculated outputs, criteria, and margins should be available as PyVista contours in the first version? |
