from __future__ import annotations

from pathlib import Path
import unittest

from mechanical_design_tool_suite.cad_geometry_api import (
    UnsupportedCadFormatError,
    cad_format_from_path,
    is_supported_neutral_cad,
)
from mechanical_design_tool_suite.cad_geometry_occ import is_occ_available
from mechanical_design_tool_suite.reference_geometry import (
    REFERENCE_DEFAULT_OPACITY,
    ReferenceDisplayState,
    ReferenceGeometryFormat,
    ReferenceGeometryService,
    ReferencePart,
    UnsupportedReferenceGeometryFormatError,
    clamp_opacity,
    is_supported_reference_geometry,
    reference_format_from_path,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "cad_1d_tolerance"
STL_FIXTURE = FIXTURE_DIR / "simple_reference.stl"
STEP_FIXTURE = FIXTURE_DIR / "neutral_step_two_part_loop.step"


class ReferenceGeometryModelTest(unittest.TestCase):
    def test_reference_format_detection_includes_stl_without_changing_cad_api(self) -> None:
        self.assertEqual(
            reference_format_from_path("fixture.step"),
            ReferenceGeometryFormat.STEP,
        )
        self.assertEqual(
            reference_format_from_path("fixture.IGS"),
            ReferenceGeometryFormat.IGES,
        )
        self.assertEqual(
            reference_format_from_path("fixture.stl"),
            ReferenceGeometryFormat.STL,
        )
        self.assertTrue(is_supported_reference_geometry("fixture.stl"))

        self.assertFalse(is_supported_neutral_cad("fixture.stl"))
        with self.assertRaises(UnsupportedCadFormatError):
            cad_format_from_path("fixture.stl")
        with self.assertRaises(UnsupportedReferenceGeometryFormatError):
            reference_format_from_path("fixture.obj")

    def test_display_state_clamps_opacity_and_round_trips(self) -> None:
        self.assertEqual(clamp_opacity(-1.0), 0.0)
        self.assertEqual(clamp_opacity(2.0), 1.0)

        state = ReferenceDisplayState(visible=False, opacity=1.5, selected=True)
        self.assertFalse(state.visible)
        self.assertEqual(state.opacity, 1.0)
        self.assertTrue(state.selected)
        self.assertEqual(
            ReferenceDisplayState.from_dict(state.to_dict()).to_dict(),
            state.to_dict(),
        )

    def test_reference_part_serializes_and_renames(self) -> None:
        part = ReferencePart(
            id="ref_part",
            name="Bracket",
            source_path="bracket.stl",
            file_format=ReferenceGeometryFormat.STL,
            mesh_count=1,
        )

        part.rename("Support bracket")
        round_tripped = ReferencePart.from_dict(part.to_dict())

        self.assertEqual(round_tripped.id, "ref_part")
        self.assertEqual(round_tripped.name, "Support bracket")
        self.assertEqual(round_tripped.file_format, ReferenceGeometryFormat.STL)
        self.assertEqual(round_tripped.display_state.opacity, REFERENCE_DEFAULT_OPACITY)
        with self.assertRaises(ValueError):
            part.rename("   ")


class ReferenceGeometryServiceTest(unittest.TestCase):
    def test_stl_import_returns_visual_mesh_asset(self) -> None:
        result = ReferenceGeometryService().import_part(STL_FIXTURE)

        self.assertEqual(result.part.file_format, ReferenceGeometryFormat.STL)
        self.assertEqual(result.part.mesh_count, 1)
        self.assertEqual(result.part.name, "simple_reference")
        self.assertTrue(result.part.metadata["mesh_only"])
        self.assertEqual(len(result.mesh_assets), 1)
        self.assertGreater(result.mesh_assets[0].n_points, 0)
        self.assertGreater(result.mesh_assets[0].n_cells, 0)
        self.assertEqual(result.mesh_assets[0].part_id, result.part.id)

    def test_step_import_to_mesh_is_guarded_by_occ_availability(self) -> None:
        if not is_occ_available():
            self.skipTest("OCCT Python bindings are unavailable.")
        if not STEP_FIXTURE.exists():
            self.skipTest(f"STEP CAD fixture is not present: {STEP_FIXTURE}")

        result = ReferenceGeometryService().import_part(STEP_FIXTURE)

        self.assertEqual(result.part.file_format, ReferenceGeometryFormat.STEP)
        self.assertGreaterEqual(len(result.mesh_assets), 1)
        self.assertEqual(result.part.mesh_count, len(result.mesh_assets))
        self.assertTrue(all(asset.n_points > 0 for asset in result.mesh_assets))


if __name__ == "__main__":
    unittest.main()
