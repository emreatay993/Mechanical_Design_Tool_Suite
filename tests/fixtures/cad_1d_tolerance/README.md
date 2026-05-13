# CAD 1D Tolerance Fixtures

This directory is reserved for small, trackable fixtures for the CAD 1D tolerance tool.

## Required Fixture Set

| Fixture ID | File | Purpose | Expected Use |
| --- | --- | --- | --- |
| CAD1D-STEP-ASM-001 | `neutral_step_two_part_loop.step` | Minimal STEP AP203/AP214/AP242 assembly with two or more parts, planar faces, and one cylindrical feature. | Geometry adapter import, assembly tree traversal, endpoint/loop selection smoke tests. |
| CAD1D-IGES-BREP-001 | `neutral_iges_single_part.igs` | Minimal IGES B-Rep part with planar and cylindrical faces. | IGES import support and shape reference serialization smoke tests. |
| CAD1D-NON1D-001 | `offset_rotational_warning.step` | Neutral fixture with laterally offset or rotationally sensitive features. | Non-1D warning heuristic tests. |
| CAD1D-PROJECT-001 | `sample_cad_1d_project.tolproj` | Deterministic project JSON using CAD references and several contributors. | Persistence, report, and UI model tests after P02/P04/P06. |
| CAD1D-CASTER-WHELL-STEP-001 | `caster_whell_v0/caster_wheel.stp` | User-provided caster wheel assembly converted from CATIA native files to STEP. | Real caster geometry import smoke tests in the OCCT `mdts-cad312` runtime. |
| BOLT-REF-STL-001 | `simple_reference.stl` | Minimal ASCII STL mesh in millimeters for bolt visual reference overlays. | Reference geometry import, mesh metadata, and bolt GUI reference-tree tests. |

## Constraints

- Keep fixtures small enough for source control review.
- Prefer ASCII filenames and stable units in millimeters.
- Do not commit commercial or proprietary CAD files.
- STEP/IGES fixtures are the only accepted B-Rep import fixtures for P0.
- If a binary CAD fixture is too large or licensing is unclear, document the generator script or external storage location instead of committing the file.

## P03 Neutral CAD Adapter Status

- The adapter boundary is implemented in `cad_geometry_api.py`, with OCCT-specific imports confined to `cad_geometry_occ.py`.
- Local default-Python dependency check on 2026-05-13: `OCC` and `OCP` imports were unavailable under Python 3.14.
- Local pip install dry run on 2026-05-13: `python -m pip install --dry-run pythonocc-core` failed with `No matching distribution found for pythonocc-core` from the configured PyPI/NVIDIA indexes.
- The local Conda environment `mdts-cad312` fixes the CAD runtime with Python 3.12, `pythonocc-core 7.9.3` using the `novtk` OCCT build, NumPy 1.26 for PyVista/VTK compatibility, and PyQt6 from the project dependencies. It deliberately avoids Conda PyQt5/Qt5.
- Use `C:\ProgramData\miniforge3\envs\mdts-cad312\python.exe` to run real OCCT import smoke tests and PyQt6 UI work.
- Real STEP/IGES adapter smoke tests import the generated neutral fixtures in `mdts-cad312` and skip cleanly under environments without a compatible OCCT binding.
