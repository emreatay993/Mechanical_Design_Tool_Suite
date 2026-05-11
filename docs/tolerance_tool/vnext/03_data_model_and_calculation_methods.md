# Next-Version Data Model And Calculation Methods

This document defines the domain model and calculation behavior for the
next-version tolerance tool.

## Domain Model

```text
ToleranceProject
  id
  title
  unit_system
  joints[]
  catalog_references[]
  method_settings

Joint
  id
  name
  flanges[]
  sub_joints[]

Flange
  id
  name
  nominal_thickness
  tolerance
  material_or_note

SubJoint
  id
  name
  parent_joint_id
  bolt_size_id
  bolt_type_id
  selected_bolt_length_id
  stackup_path_id
  result_snapshot

StackupPath
  id
  sub_joint_id
  items[]
  engagement_type
  selected_engagement_part_id
  method_settings

PathItem
  id
  source_type
  source_id
  name
  nominal_thickness
  tolerance
  role
  include_in_stackup
```

## Object Definitions

| Object | Definition |
| --- | --- |
| Joint | A main assembly connection location where the part interfaces with other parts. |
| Flange | A joint-level thickness contributor that can feed one or more stackup paths. |
| Sub-joint | A configuration under a joint, for example `JOINT A.1`, with its own stackup path and bolt selection. |
| Stackup path | Ordered set of flange references, standard parts, and custom items used for one sub-joint calculation. |
| Standard part | Catalog-backed hardware or path item such as bolt, nut, insert, washer, bracket, or spacer. |
| Custom item | User-entered path item not backed by a catalog record. |

## Standard Part Catalog Model

Catalog records should be data-driven. The UI should not hardcode hardware
dimensions.

| Field | Purpose |
| --- | --- |
| `part_id` | Stable catalog identifier. |
| `part_type` | Bolt, nut, insert, washer, bracket, spacer, custom template, or other supported type. |
| `display_name` | User-facing part name. |
| `compatible_bolt_sizes` | Bolt sizes this part supports. |
| `nominal_thickness` | Thickness or stack contribution when applicable. |
| `tolerance` | Catalog tolerance when applicable. |
| `thread_pitch` | Pitch `P` for thread protrusion checks when applicable. |
| `chamfer_allowance` | Chamfer allowance for `2P+Chamfer` checks when applicable. |
| `lengths` | Standard available lengths for bolts. |
| `engagement_rule` | Rule or parameters for nut, insert, or threaded-hole engagement. |
| `source` | Catalog, standard, or internal data source reference. |

Catalog records with missing required calculation fields shall be selectable only
as incomplete records and shall block final calculation until completed or
replaced.

## Stackup Path Generation

When a sub-joint is opened for the first time:

1. The tool reads the parent joint's flange list.
2. It creates path items that reference the joint flanges.
3. It applies the default engagement placeholder, such as `Select nut/insert`.
4. It leaves optional extra items, such as brackets, washers, or spacers, for the user to add.
5. It calculates live results only after required fields are complete.

Flange path items should remain linked to the parent joint by default. If a
flange value changes in the joint table, linked stackup paths update.

## Stackup Calculation

The existing calculation model extends from generic dimensions to path items.
Each included path item contributes:

```text
nominal_i
tolerance_i
sigma_i = tolerance_i / 3
variance_i = sigma_i^2
```

For one stackup path:

```text
nominal_stack = sum(nominal_i)
worst_case_deviation = sum(tolerance_i)
rss = sqrt(sum(variance_i)) * 3
one_point_five_rss = rss * 1.5
```

The next version should keep the 3-sigma RSS convention unless method settings
explicitly allow a different sigma basis.

## Contributor Metrics

Each included path item has an RSS variance contribution:

```text
contribution_i = variance_i / sum(variance_i)
```

The top four contributor sum is:

```text
top_four_contributor_sum = sum(largest four contribution_i values)
```

The UI should show the percentage and the names of the top contributors. If the
RSS variance is zero, contributor percentages should display as not applicable
instead of dividing by zero.

## Bolt Length Candidate Calculation

Bolt length selection shall be driven by catalog definitions. For each candidate
bolt length:

1. Read the selected bolt size, bolt type, pitch, and candidate length from the catalog.
2. Read the selected stackup path's nominal, worst-case, RSS, and 1.5RSS values.
3. Read the engagement type and engagement part, such as nut, insert, or threaded hole.
4. Compute required engagement and residual thread protrusion using the catalog-defined length convention and engagement rule.
5. Evaluate criteria such as `1.5P`, `2P`, and `2P+Chamfer`.
6. Return pass, warning, fail, or incomplete status with reasons.

The exact mechanical formula for effective grip length, engagement depth, and
thread protrusion shall be parameterized by catalog data and engineering rules.
It shall not be embedded only in UI code.

## Thread Protrusion Summary

The main workspace shall show thread protrusion results by sub-joint.

| Column | Meaning |
| --- | --- |
| `1.5P` | Candidate satisfies or reports value against one and a half pitch criterion. |
| `2P` | Candidate satisfies or reports value against two pitch criterion. |
| `2P+Chamfer` | Candidate satisfies or reports value against two pitch plus chamfer allowance criterion. |

Each cell should carry numeric detail and status. Example status values:

| Status | Meaning |
| --- | --- |
| Pass | Candidate satisfies the criterion. |
| Warn | Candidate is close to the limit or depends on incomplete optional data. |
| Fail | Candidate does not satisfy the criterion. |
| Incomplete | Required catalog or path data is missing. |

## Optimization Method

Optimization should rank candidate bolt lengths. The first baseline ranking can
use deterministic rules:

1. Exclude incomplete candidates.
2. Exclude candidates that fail required thread protrusion or engagement checks.
3. Prefer candidates that pass all required criteria with adequate margin.
4. Prefer standard catalog lengths over custom lengths.
5. Prefer candidates with lower risk status.
6. Break ties with configurable project preference, such as shorter bolt or
   preferred hardware family.

Optimization output shall include:

| Output | Purpose |
| --- | --- |
| Recommended bolt length | Default choice for the engineer to review. |
| Ranked alternatives | Other usable candidates. |
| Rejection reasons | Why a candidate cannot be used. |
| Dominant contributors | Path items driving RSS or worst-case deviation. |
| Suggested actions | Practical next steps such as reviewing a bracket tolerance or choosing another length. |

## Units

The next version shall make units explicit. A project should define a unit
system, and every catalog record and user-entered value should either use that
system or declare its own source unit with conversion.

At minimum, the next version should support consistent length units for:

```text
flange thickness
path item thickness
tolerance
bolt length
thread pitch
chamfer allowance
thread protrusion
```

## Open Engineering Decisions

| Decision | Why it matters |
| --- | --- |
| Exact bolt length datum | Catalogs may define bolt length under-head, overall, or family-specific conventions. |
| Engagement formulas by nut/insert/threaded hole | Each engagement type may need different parameters. |
| Required thread protrusion rule | The tool needs clear pass/fail criteria for `1.5P`, `2P`, and `2P+Chamfer`. |
| Treatment of asymmetric tolerances | Current model is symmetric; hardware catalogs may need plus/minus fields. |
| Treatment of correlation | Current RSS assumes independent contributors. |
