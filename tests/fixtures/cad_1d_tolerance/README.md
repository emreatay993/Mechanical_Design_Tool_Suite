# CAD 1D Tolerance Fixtures

This directory is reserved for small, trackable fixtures for the CAD 1D tolerance tool.

## Required Fixture Set

| Fixture ID | File | Purpose | Expected Use |
| --- | --- | --- | --- |
| CAD1D-STEP-ASM-001 | `neutral_step_two_part_loop.step` | Minimal STEP AP203/AP214/AP242 assembly with two or more parts, planar faces, and one cylindrical feature. | Geometry adapter import, assembly tree traversal, endpoint/loop selection smoke tests. |
| CAD1D-IGES-BREP-001 | `neutral_iges_single_part.igs` | Minimal IGES B-Rep part with planar and cylindrical faces. | IGES import support and shape reference serialization smoke tests. |
| CAD1D-NON1D-001 | `offset_rotational_warning.step` | Neutral fixture with laterally offset or rotationally sensitive features. | Non-1D warning heuristic tests. |
| CAD1D-PROJECT-001 | `sample_cad_1d_project.tolproj` | Deterministic project JSON using CAD references and several contributors. | Persistence, report, and UI model tests after P02/P04/P06. |

## Constraints

- Keep fixtures small enough for source control review.
- Prefer ASCII filenames and stable units in millimeters.
- Do not commit commercial or proprietary CAD files.
- STEP/IGES fixtures must be neutral-format only for P0.
- If a binary CAD fixture is too large or licensing is unclear, document the generator script or external storage location instead of committing the file.
