# Tolerance Tool Requirements

This document defines requirements for the standalone tolerance analysis GUI.
The current implementation is a tolerance stackup calculator with bilateral
dimension tolerances, worst-case results, RSS results, RSS tail-risk estimates,
and PDF/PNG export.

Requirement status values:

| Status | Meaning |
| --- | --- |
| Implemented | Present in the current source tree |
| Proposed | Desired behavior for the design baseline |
| Deferred | Useful future behavior, not required for the current baseline |

Priority values:

| Priority | Meaning |
| --- | --- |
| P0 | Required for the first documented baseline |
| P1 | Important follow-on capability |
| P2 | Future extension |

## Product Scope

| ID | Priority | Status | Requirement |
| --- | --- | --- | --- |
| TOL-REQ-SCOPE-001 | P0 | Implemented | The tool shall run as a standalone PyQt6 tolerance analysis GUI. |
| TOL-REQ-SCOPE-002 | P0 | Implemented | The tool shall calculate dimensional tolerance stackups from a list of dimensions and bilateral tolerances. |
| TOL-REQ-SCOPE-003 | P0 | Implemented | The tool shall provide both worst-case and root sum squared (RSS) stackup results. |
| TOL-REQ-SCOPE-004 | P0 | Implemented | The tool shall allow the user to compare stackup results against minimum and maximum target dimensions. |
| TOL-REQ-SCOPE-005 | P0 | Proposed | The documentation shall distinguish dimensional tolerance analysis from bolt benchmark validation tolerances. |
| TOL-REQ-SCOPE-006 | P1 | Deferred | The tolerance tool should be launchable from the main bolt calculation GUI if the product direction requires a single application shell. |

## Inputs

| ID | Priority | Status | Requirement |
| --- | --- | --- | --- |
| TOL-REQ-IN-001 | P0 | Implemented | The user shall be able to enter a human-readable analysis title. |
| TOL-REQ-IN-002 | P0 | Implemented | The user shall be able to enter any number of stackup dimensions. |
| TOL-REQ-IN-003 | P0 | Implemented | Each dimension row shall include a name, nominal dimension, and symmetric bilateral tolerance. |
| TOL-REQ-IN-004 | P0 | Implemented | Blank dimension names shall be accepted and replaced with row-style names such as `#1`. |
| TOL-REQ-IN-005 | P0 | Implemented | Nominal dimensions may be positive, zero, or negative. |
| TOL-REQ-IN-006 | P0 | Implemented | Bilateral tolerances shall be finite, numeric, and greater than or equal to zero. |
| TOL-REQ-IN-007 | P0 | Implemented | The user shall be able to enter target minimum and target maximum dimensions. |
| TOL-REQ-IN-008 | P0 | Implemented | Target minimum shall be less than or equal to target maximum. |
| TOL-REQ-IN-009 | P1 | Proposed | The tool should make units explicit for all dimension, tolerance, target, and report values. |
| TOL-REQ-IN-010 | P1 | Deferred | The tool should support asymmetric plus/minus tolerances. |
| TOL-REQ-IN-011 | P2 | Deferred | The tool should support signed contribution direction for subtractive dimensions. |

## Calculation Outputs

| ID | Priority | Status | Requirement |
| --- | --- | --- | --- |
| TOL-REQ-OUT-001 | P0 | Implemented | The tool shall report nominal stackup as the sum of nominal dimension values. |
| TOL-REQ-OUT-002 | P0 | Implemented | The tool shall report each dimension's standard deviation and variance. |
| TOL-REQ-OUT-003 | P0 | Implemented | The tool shall report worst-case stackup tolerance, minimum, and maximum. |
| TOL-REQ-OUT-004 | P0 | Implemented | The tool shall report RSS stackup tolerance, minimum, and maximum. |
| TOL-REQ-OUT-005 | P0 | Implemented | The tool shall report RSS left-tail and right-tail failure rates relative to target limits. |
| TOL-REQ-OUT-006 | P0 | Implemented | The tool shall update displayed outputs automatically after valid input changes. |
| TOL-REQ-OUT-007 | P1 | Deferred | The tool should report yield as one minus combined tail risk when that metric is added to the UI. |
| TOL-REQ-OUT-008 | P1 | Deferred | The tool should report sensitivity or contribution ranking for each dimension. |
| TOL-REQ-OUT-009 | P2 | Deferred | The tool should support Monte Carlo simulation, Cpk, and scenario comparison if required by future risk-review workflows. |

## User Interface

| ID | Priority | Status | Requirement |
| --- | --- | --- | --- |
| TOL-REQ-UI-001 | P0 | Implemented | The UI shall provide a dimension table with add, remove, and clear actions. |
| TOL-REQ-UI-002 | P0 | Implemented | The UI shall initialize with a usable four-dimension example. |
| TOL-REQ-UI-003 | P0 | Implemented | The UI shall show a stackup plot containing target markers, cumulative dimensions, nominal stackup, worst-case range, and RSS range. |
| TOL-REQ-UI-004 | P0 | Implemented | The UI shall show an analysis table containing dimension rows and summary rows. |
| TOL-REQ-UI-005 | P0 | Implemented | The UI shall display controlled status messages for successful calculation and input errors. |
| TOL-REQ-UI-006 | P0 | Implemented | Invalid input shall clear stale analysis output rather than continuing to display outdated results. |
| TOL-REQ-UI-007 | P1 | Proposed | The UI should explain units and assumptions in labels or report metadata once unit support exists. |
| TOL-REQ-UI-008 | P1 | Deferred | The currently disabled save action should either be implemented or removed from the baseline UI. |

## Export And Persistence

| ID | Priority | Status | Requirement |
| --- | --- | --- | --- |
| TOL-REQ-EXP-001 | P0 | Implemented | The user shall be able to export the current tolerance analysis page to PDF. |
| TOL-REQ-EXP-002 | P0 | Implemented | The user shall be able to export the current tolerance analysis page to PNG. |
| TOL-REQ-EXP-003 | P0 | Implemented | Export filenames shall be derived from the analysis title and a timestamp. |
| TOL-REQ-EXP-004 | P0 | Implemented | Export errors shall be reported through the UI status line. |
| TOL-REQ-EXP-005 | P1 | Deferred | The tool should persist editable tolerance analyses to a project file format. |
| TOL-REQ-EXP-006 | P1 | Deferred | Persisted files should preserve title, dimension rows, targets, units, and method settings. |

## Packaging And Launch

| ID | Priority | Status | Requirement |
| --- | --- | --- | --- |
| TOL-REQ-PKG-001 | P0 | Implemented | Developers shall be able to launch the tool from a source checkout with `python scripts\run_tolerance_analysis.py`. |
| TOL-REQ-PKG-002 | P0 | Implemented | Editable installs shall expose the `tolerance-analysis-gui` console entry point. |
| TOL-REQ-PKG-003 | P1 | Implemented | Windows packaging shall include dedicated tolerance GUI executables and a top-level program selector. |
| TOL-REQ-PKG-004 | P1 | Implemented | Packaging documentation shall list the launch path for the tolerance tool separately from the main bolt calculation GUI. |
