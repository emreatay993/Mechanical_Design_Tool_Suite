# Next-Version Verification And Validation Plan

This document defines how to verify the next-version tolerance tool.

## Verification Objective

The next version shall correctly support:

```text
joint setup
flange setup
sub-joint generation
stackup path creation
standard part selection
bolt length candidate evaluation
thread protrusion checks
summary result propagation
optimization
project save/load
report export
```

## Requirements Traceability

Every implemented feature shall trace to a requirement in
[01_requirements.md](01_requirements.md). Each requirement should have at least
one of:

| Evidence | Example |
| --- | --- |
| Unit test | Stackup method returns expected RSS. |
| Integration test | Opening `JOINT A.1` creates a default path. |
| GUI test | Selecting bolt length updates the live result panel. |
| Manual test | PDF report visually matches the saved project. |
| Review | UX review confirms workflow and terminology. |

## Level 1: Domain And Calculation Unit Tests

Required unit tests:

| Area | Required checks |
| --- | --- |
| Joint model | Default project creates `JOINT A`, three flanges, and `JOINT A.1`. |
| Naming | Added joints and sub-joints receive predictable names and can be renamed. |
| Flange linking | Updating a joint flange updates linked default path items. |
| Path stackup | Path items produce nominal, worst-case, RSS, and 1.5RSS values. |
| Contributor metrics | Top four contributor sum is correct and handles zero variance. |
| Catalog filtering | Bolt lengths filter by size and type. |
| Thread protrusion | Candidate evaluations return pass/warn/fail/incomplete statuses. |
| Optimization | Candidate ranking excludes failures and returns reasons. |
| Units | Values convert or reject incompatible units consistently. |

## Level 2: Project IO Tests

Required save/load tests:

| Case | Expected result |
| --- | --- |
| New default project save/load | Same joints, flanges, sub-joints, paths, and settings are restored. |
| Incomplete project save/load | Incomplete state is preserved and warnings are restored. |
| Catalog-backed item save/load | Catalog IDs and resolved display data are restored. |
| Custom item save/load | User-entered values and notes are restored. |
| Unknown schema version | Load is rejected with a clear message. |
| Migration from older schema | Data migrates and records warnings when needed. |

## Level 3: GUI Workflow Tests

Required GUI workflow tests:

| Workflow | Expected result |
| --- | --- |
| Start new project | `JOINT A`, `JOINT A.1`, and three flanges are visible. |
| Add joint | `JOINT B` appears and receives a default sub-joint. |
| Add flange | A new flange thickness/tolerance column appears and can feed paths. |
| Open sub-joint path | Stackup path builder opens and contains linked default flange items. |
| Add bracket | Bracket appears in the path and affects results when included. |
| Select nut or insert | Standard catalog data is pulled into the path. |
| Select bolt length | Live results and thread protrusion status update on the same page. |
| Save path | Main calculation and thread protrusion summary tables update. |
| Optimize | Recommended candidate and rejection reasons are displayed. |
| Fix invalid input | Error state clears and results recalculate. |

Automated GUI tests are recommended for critical paths. Manual verification is
acceptable for early prototypes but should be recorded with screenshots or test
notes.

## Level 4: Catalog Validation Tests

Catalog tests should verify:

| Case | Expected result |
| --- | --- |
| Valid bolt catalog | Records load and lengths are queryable. |
| Missing required field | Catalog load reports exact record and field. |
| Duplicate ID | Catalog load rejects duplicate or reports conflict. |
| Unit mismatch | Values convert or raise a clear validation error. |
| Incompatible part | Part does not appear for unsupported bolt sizes. |
| Incomplete record | Part can be marked incomplete and blocks final calculation. |

## Level 5: Export And Report Tests

Required export checks:

| Export | Expected result |
| --- | --- |
| PDF report | Contains project title, joint setup, stackup summaries, thread protrusion results, and warnings. |
| PNG export | Captures the selected workspace or path builder view legibly. |
| CSV summary | Contains calculation summary rows for all joints and sub-joints. |
| Reopened project report | Exported values match the reloaded project calculations. |

## Manual UX Review Checklist

Before considering the next-version UI acceptable:

| Check | Acceptance |
| --- | --- |
| Default state | User can see what to do next without reading documentation. |
| Hierarchy | Joint, sub-joint, and path relationships are visually obvious. |
| Same-page decision | Bolt length selection, results, and optimization are visible together. |
| Catalog confidence | Standard parts show source and required calculation data. |
| Error recovery | Users can find and fix invalid fields quickly. |
| Summary propagation | Main summary updates after path save/apply. |
| Terminology | UI consistently uses joint, flange, sub-joint, stackup path, worst case, RSS, 1.5RSS, and thread protrusion. |

## Open Validation Items

| Item | Needed decision |
| --- | --- |
| Thread protrusion formula | Engineering rule and catalog fields must be finalized. |
| Bolt length datum | Catalog convention must be documented. |
| Nut/insert engagement | Engagement formulas must be defined by part type. |
| Unit system | Decide initial supported project units. |
| Packaging | Verify both selector launch and direct `ToleranceAnalysisVNext.exe` launch before handoff. |
