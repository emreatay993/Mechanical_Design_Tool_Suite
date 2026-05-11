# Next-Version Requirements

This document defines product and functional requirements for the next version
of the tolerance tool.

Requirement status values:

| Status | Meaning |
| --- | --- |
| Proposed | Required or desired for the next-version design baseline |
| Future | Useful extension after the next-version baseline |
| Open | Needs engineering or product decision before implementation |

Priority values:

| Priority | Meaning |
| --- | --- |
| P0 | Required for the next usable version |
| P1 | Important follow-on capability |
| P2 | Future enhancement |

## Product Scope

| ID | Priority | Status | Requirement |
| --- | --- | --- | --- |
| TOL-NV-SCOPE-001 | P0 | Proposed | The next version shall support joint-driven tolerance analysis for bolted assembly interfaces. |
| TOL-NV-SCOPE-002 | P0 | Proposed | The tool shall model joints, flanges, sub-joints, stackup paths, standard hardware, bolt length candidates, and summary results in one project. |
| TOL-NV-SCOPE-003 | P0 | Proposed | The tool shall preserve the current worst-case and RSS calculation concepts while extending them to named stackup paths. |
| TOL-NV-SCOPE-004 | P0 | Proposed | The tool shall allow users to choose a bolt length while viewing live stackup and thread protrusion results on the same page. |
| TOL-NV-SCOPE-005 | P0 | Proposed | The tool shall support optimization from the same page used for stackup path and bolt length selection. |
| TOL-NV-SCOPE-006 | P1 | Open | Product direction shall decide whether the next version remains a standalone tolerance GUI or is launched from the main bolt calculation GUI. |

## Joint Setup

| ID | Priority | Status | Requirement |
| --- | --- | --- | --- |
| TOL-NV-JOINT-001 | P0 | Proposed | A new project shall start with one default joint named `JOINT A`. |
| TOL-NV-JOINT-002 | P0 | Proposed | Joint names shall be editable. |
| TOL-NV-JOINT-003 | P0 | Proposed | The user shall be able to add additional joints such as `JOINT B` and `JOINT C`. |
| TOL-NV-JOINT-004 | P0 | Proposed | A joint shall represent a main assembly connection location where the part interfaces with other parts. |
| TOL-NV-JOINT-005 | P0 | Proposed | Each joint shall include a flange definition table. |
| TOL-NV-JOINT-006 | P0 | Proposed | A new project shall start with three default flange columns: `Flange 1`, `Flange 2`, and `Flange 3`. |
| TOL-NV-JOINT-007 | P0 | Proposed | Each flange shall have a nominal thickness and a plus/minus tolerance. |
| TOL-NV-JOINT-008 | P0 | Proposed | The user shall be able to add more flanges when an assembly has more than three flange contributors. |
| TOL-NV-JOINT-009 | P0 | Proposed | Flange values entered in the joint table shall feed the stackup paths for that joint. |
| TOL-NV-JOINT-010 | P1 | Proposed | The UI shall let the user hide unused flange columns without deleting the underlying data. |

## Sub-Joint And Bolt Detail Setup

| ID | Priority | Status | Requirement |
| --- | --- | --- | --- |
| TOL-NV-SUB-001 | P0 | Proposed | Each joint shall have one default sub-joint configuration such as `JOINT A.1`. |
| TOL-NV-SUB-002 | P0 | Proposed | The bolt detail table shall be generated automatically from the joint list and each joint's sub-joints. |
| TOL-NV-SUB-003 | P0 | Proposed | Each sub-joint shall expose bolt size, bolt type, and bolt length fields. |
| TOL-NV-SUB-004 | P0 | Proposed | The user shall be able to add additional sub-joints when a joint has multiple stackup path configurations. |
| TOL-NV-SUB-005 | P0 | Proposed | Clicking a sub-joint row or its action button shall open the stackup path builder for that sub-joint. |
| TOL-NV-SUB-006 | P0 | Proposed | Sub-joint names shall remain traceable back to the parent joint. |
| TOL-NV-SUB-007 | P1 | Proposed | The user shall be able to duplicate a sub-joint configuration and then edit the copy. |

## Stackup Path Builder

| ID | Priority | Status | Requirement |
| --- | --- | --- | --- |
| TOL-NV-PATH-001 | P0 | Proposed | Opening a sub-joint shall create or load an editable stackup path page or window. |
| TOL-NV-PATH-002 | P0 | Proposed | The initial stackup path shall be generated from the parent joint's flange definitions. |
| TOL-NV-PATH-003 | P0 | Proposed | The user shall be able to add optional path items such as brackets, washers, spacers, nuts, inserts, or custom thickness items. |
| TOL-NV-PATH-004 | P0 | Proposed | Standard hardware and standard path items shall be pulled from a data catalog rather than manually retyped whenever possible. |
| TOL-NV-PATH-005 | P0 | Proposed | The path builder shall distinguish between flange references, catalog parts, and custom user-defined items. |
| TOL-NV-PATH-006 | P0 | Proposed | The path builder shall allow users to decide whether the joint terminates into a nut, insert, threaded hole, or other supported engagement type. |
| TOL-NV-PATH-007 | P0 | Proposed | Saving a stackup path shall update the parent bolt detail table, calculation summary, and thread protrusion summary. |
| TOL-NV-PATH-008 | P1 | Proposed | The path builder should provide a visual ordered stack representation alongside the editable item table. |

## Bolt Length Selection

| ID | Priority | Status | Requirement |
| --- | --- | --- | --- |
| TOL-NV-BOLT-001 | P0 | Proposed | Bolt length candidates shall be filtered by selected bolt size and bolt type. |
| TOL-NV-BOLT-002 | P0 | Proposed | The user shall be able to choose bolt length from standard catalog values. |
| TOL-NV-BOLT-003 | P0 | Proposed | The selected bolt length shall update stackup and thread protrusion results immediately. |
| TOL-NV-BOLT-004 | P0 | Proposed | The bolt length selection UI shall show pass/fail or warning states for each relevant criterion. |
| TOL-NV-BOLT-005 | P0 | Proposed | The tool shall support comparing candidate bolt lengths without leaving the stackup path page. |
| TOL-NV-BOLT-006 | P1 | Proposed | The UI should explain why a candidate bolt length is rejected or ranked lower. |

## Summaries And Results

| ID | Priority | Status | Requirement |
| --- | --- | --- | --- |
| TOL-NV-RES-001 | P0 | Proposed | The main page shall show a calculation summary per joint and sub-joint. |
| TOL-NV-RES-002 | P0 | Proposed | The calculation summary shall include worst-case deviation, RSS, 1.5RSS, and top four contributor sum. |
| TOL-NV-RES-003 | P0 | Proposed | The main page shall show thread protrusion results per joint and sub-joint. |
| TOL-NV-RES-004 | P0 | Proposed | Thread protrusion results shall include criteria such as `1.5P`, `2P`, and `2P+Chamfer` when supported by the selected bolt catalog record. |
| TOL-NV-RES-005 | P0 | Proposed | Results from the stackup path page shall flow back to the summary tables automatically after save or apply. |
| TOL-NV-RES-006 | P1 | Proposed | Summary tables should support row status indicators for complete, incomplete, warning, and failing configurations. |

## Optimization

| ID | Priority | Status | Requirement |
| --- | --- | --- | --- |
| TOL-NV-OPT-001 | P0 | Proposed | The stackup path page shall provide an optimization action for bolt length and stackup configuration review. |
| TOL-NV-OPT-002 | P0 | Proposed | Optimization shall operate on standard catalog bolt lengths first. |
| TOL-NV-OPT-003 | P0 | Proposed | Optimization shall rank candidates using calculation summary and thread protrusion constraints. |
| TOL-NV-OPT-004 | P1 | Proposed | Optimization should identify dominant tolerance contributors. |
| TOL-NV-OPT-005 | P1 | Proposed | Optimization should suggest practical actions such as selecting a different bolt length or reviewing the highest-contributing stack item. |
| TOL-NV-OPT-006 | P2 | Future | Optimization may consider cost, availability, preferred hardware families, and manufacturing capability. |

## Persistence, Import, And Export

| ID | Priority | Status | Requirement |
| --- | --- | --- | --- |
| TOL-NV-DATA-001 | P0 | Proposed | The next version shall implement a real save workflow for editable tolerance projects. |
| TOL-NV-DATA-002 | P0 | Proposed | Saved projects shall preserve joints, flanges, sub-joints, stackup paths, selected catalog parts, selected bolt lengths, units, and method settings. |
| TOL-NV-DATA-003 | P0 | Proposed | The project file format shall be versioned. |
| TOL-NV-DATA-004 | P0 | Proposed | Reports shall preserve the current PDF/PNG export capability and add next-version summary content. |
| TOL-NV-DATA-005 | P1 | Implemented | The tool should support importing the joint/flange setup from CSV or spreadsheet-style tables. |
| TOL-NV-DATA-006 | P1 | Implemented | The tool should support exporting calculation summaries to CSV. |

## UI/UX Quality Requirements

| ID | Priority | Status | Requirement |
| --- | --- | --- | --- |
| TOL-NV-UX-001 | P0 | Proposed | The next UI shall be structured for engineering workflow, not as a raw spreadsheet clone. |
| TOL-NV-UX-002 | P0 | Proposed | The UI shall keep input setup, live results, and actions visible enough that users do not need to switch pages repeatedly for the common workflow. |
| TOL-NV-UX-003 | P0 | Proposed | The stackup path page shall show bolt length choices and result tables side by side. |
| TOL-NV-UX-004 | P0 | Proposed | Required next actions shall be obvious for incomplete joints, incomplete sub-joints, and invalid paths. |
| TOL-NV-UX-005 | P0 | Proposed | Validation messages shall identify the exact joint, sub-joint, flange, path item, or catalog field causing the issue. |
| TOL-NV-UX-006 | P1 | Proposed | The UI should support keyboard-friendly table editing for engineering users entering many rows. |
