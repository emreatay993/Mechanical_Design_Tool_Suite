from __future__ import annotations

from pathlib import Path
import unittest

from mechanical_design_tool_suite.cad_display_style import (
    display_color_for_part,
    normalize_rgb_triplet,
    rgb_bytes_to_unit,
)
from mechanical_design_tool_suite.cad_geometry_api import (
    CadImportSettings,
    GeometryIndex,
    InMemoryCadGeometrySession,
    MeasurementKind,
    UnsupportedCadFormatError,
    cad_format_from_path,
    feature_from_shape_reference,
    is_supported_neutral_cad,
    measure_feature_pair,
    normalize_vector,
)
from mechanical_design_tool_suite.cad_geometry_occ import (
    OCC_DEPENDENCY_MESSAGE,
    CadKernelUnavailable,
    OccCadGeometrySession,
    is_occ_available,
)
from mechanical_design_tool_suite.cad_tolerance_models import (
    AssemblyNode,
    AssemblyNodeType,
    CadDocument,
    CadFileFormat,
    FeatureKind,
    FeatureReference,
    ShapeKind,
    ShapeReference,
    Vector3D,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "cad_1d_tolerance"
CASTER_WHELL_FIXTURE_DIR = FIXTURE_DIR / "caster_whell_v0"
CASTER_WHELL_STEP_FIXTURE = CASTER_WHELL_FIXTURE_DIR / "caster_wheel.stp"
PYTHONOCC_PIP_BLOCKER = (
    "Local check: `python -m pip install --dry-run pythonocc-core` returned "
    "`No matching distribution found for pythonocc-core`."
)


class CadGeometryApiTest(unittest.TestCase):
    def test_display_style_palette_is_stable_and_normalized(self) -> None:
        self.assertEqual(display_color_for_part("top_plate:1", 1), (66, 84, 150))
        self.assertEqual(display_color_for_part("axle_support:1", 2), (165, 109, 61))
        self.assertEqual(display_color_for_part("wheel:1", 3), (217, 196, 116))
        self.assertEqual(normalize_rgb_triplet((-10, 127.6, 300)), (0, 128, 255))
        self.assertEqual(rgb_bytes_to_unit((255, 128, 0)), (1.0, 128 / 255.0, 0.0))

    def test_neutral_format_detection_is_limited_to_step_and_iges(self) -> None:
        cases = {
            "part.step": CadFileFormat.STEP,
            "part.STP": CadFileFormat.STEP,
            "part.iges": CadFileFormat.IGES,
            "part.IGS": CadFileFormat.IGES,
        }

        for filename, expected in cases.items():
            with self.subTest(filename=filename):
                self.assertEqual(cad_format_from_path(filename), expected)
                self.assertTrue(is_supported_neutral_cad(filename))

        for filename in ("native.sldprt", "mesh.stl", "viewer.obj"):
            with self.subTest(filename=filename):
                self.assertFalse(is_supported_neutral_cad(filename))
                with self.assertRaises(UnsupportedCadFormatError):
                    cad_format_from_path(filename)

    def test_caster_whell_step_fixture_tracks_real_caster_geometry(self) -> None:
        self.assertTrue(CASTER_WHELL_STEP_FIXTURE.exists())
        self.assertEqual(
            cad_format_from_path(CASTER_WHELL_STEP_FIXTURE),
            CadFileFormat.STEP,
        )
        self.assertTrue(is_supported_neutral_cad(CASTER_WHELL_STEP_FIXTURE))

        for filename in ("Assemblage.CATProduct", "P1 0,357kg.CATPart"):
            with self.subTest(filename=filename):
                self.assertFalse(is_supported_neutral_cad(filename))
                with self.assertRaises(UnsupportedCadFormatError):
                    cad_format_from_path(filename)

    def test_feature_reference_is_extracted_from_planar_shape_signature(self) -> None:
        shape = ShapeReference(
            id="shape_plane_1",
            document_id="cad_doc_1",
            assembly_path=["Fixture", "Body 1"],
            shape_type=ShapeKind.FACE,
            kernel_label="cad_doc_1:Fixture/Body 1:face:1",
            geometric_signature={
                "surface_type": "plane",
                "point": [10.0, 0.0, 0.0],
                "normal": [1.0, 0.0, 0.0],
                "area": 420.0,
            },
            fallback_display_name="Datum face",
        )

        feature = feature_from_shape_reference(shape, owner_part_id="body_1")

        self.assertEqual(feature.feature_type, FeatureKind.PLANE)
        self.assertEqual(feature.owner_part_id, "body_1")
        self.assertEqual(feature.name, "Datum face")
        self.assertEqual(feature.point.to_list(), [10.0, 0.0, 0.0])
        self.assertEqual(feature.normal.to_list(), [1.0, 0.0, 0.0])

    def test_feature_reference_is_extracted_from_cylindrical_shape_signature(self) -> None:
        shape = ShapeReference(
            id="shape_cylinder_1",
            document_id="cad_doc_1",
            assembly_path=["Fixture", "Body 1"],
            shape_type=ShapeKind.FACE,
            kernel_label="cad_doc_1:Fixture/Body 1:face:2",
            geometric_signature={
                "surface_type": "cylinder",
                "point": [24.0, 2.0, 0.0],
                "axis": [1.0, 0.0, 0.0],
                "radius": 12.5,
            },
            fallback_display_name="Bushing ID",
        )

        feature = feature_from_shape_reference(shape)

        self.assertEqual(feature.feature_type, FeatureKind.CYLINDER)
        self.assertEqual(feature.point.to_list(), [24.0, 2.0, 0.0])
        self.assertEqual(feature.axis.to_list(), [1.0, 0.0, 0.0])

    def test_directional_measurement_supports_planar_and_cylindrical_features(self) -> None:
        plane = FeatureReference(
            id="feature_start",
            name="Datum face",
            feature_type=FeatureKind.PLANE,
            point=Vector3D(10.0, 0.0, 0.0),
            normal=Vector3D(1.0, 0.0, 0.0),
        )
        cylinder_shape = ShapeReference(
            id="shape_cylinder_1",
            shape_type=ShapeKind.FACE,
            geometric_signature={"radius": 12.5},
        )
        cylinder = FeatureReference(
            id="feature_end",
            name="Bushing ID",
            feature_type=FeatureKind.CYLINDER,
            shape_reference=cylinder_shape,
            point=Vector3D(34.0, 2.0, 0.0),
            axis=Vector3D(1.0, 0.0, 0.0),
        )

        measurement = measure_feature_pair(plane, cylinder, [2.0, 0.0, 0.0])

        self.assertEqual(measurement.measurement_kind, MeasurementKind.PLANE_TO_AXIS)
        self.assertEqual(measurement.source_feature_ids, ("feature_start", "feature_end"))
        self.assertAlmostEqual(measurement.value, 24.0)
        self.assertEqual(measurement.direction.to_list(), [1.0, 0.0, 0.0])
        self.assertEqual(measurement.details["feature_b_radius"], 12.5)
        self.assertEqual(measurement.details["delta"], [24.0, 2.0, 0.0])

    def test_normalize_vector_rejects_zero_direction(self) -> None:
        with self.assertRaises(ValueError):
            normalize_vector([0.0, 0.0, 0.0])

    def test_in_memory_session_exposes_document_tree_shapes_and_measurements(self) -> None:
        root = AssemblyNode(
            id="asm_root",
            name="Fixture Assembly",
            node_type=AssemblyNodeType.ROOT,
        )
        document = CadDocument(
            id="cad_doc_1",
            source_path="fixture.step",
            file_format=CadFileFormat.STEP,
            assembly_root=root,
            display_name="fixture.step",
        )
        shape = ShapeReference(
            id="shape_body_1",
            document_id="cad_doc_1",
            assembly_path=["Fixture Assembly", "Body 1"],
            shape_type=ShapeKind.BODY,
        )
        start = FeatureReference(
            id="feature_start",
            feature_type=FeatureKind.PLANE,
            point=Vector3D(0.0, 0.0, 0.0),
        )
        end = FeatureReference(
            id="feature_end",
            feature_type=FeatureKind.PLANE,
            point=Vector3D(5.0, 0.0, 0.0),
        )
        session = InMemoryCadGeometrySession(
            GeometryIndex(document=document, shapes=[shape], features=[start, end])
        )

        self.assertEqual(session.import_file("fixture.step"), document)
        self.assertEqual(session.assembly_tree(), [root])
        self.assertEqual(session.shape_references({ShapeKind.BODY}), [shape])
        self.assertEqual(session.feature_references({FeatureKind.PLANE}), [start, end])
        self.assertAlmostEqual(
            session.measure_between(start, end, Vector3D(1.0, 0.0, 0.0)).value,
            5.0,
        )

    def test_import_settings_are_serializable(self) -> None:
        settings = CadImportSettings(
            units="mm",
            heal_shapes=False,
            object_filter="brep",
            include_edges=False,
            include_vertices=False,
        )

        self.assertEqual(
            settings.to_dict(),
            {
                "units": "mm",
                "heal_shapes": False,
                "object_filter": "brep",
                "include_edges": False,
                "include_vertices": False,
            },
        )


class OccCadGeometryAdapterTest(unittest.TestCase):
    def test_missing_occ_dependency_reports_adapter_boundary(self) -> None:
        if is_occ_available():
            self.skipTest("OCCT binding is installed; missing-dependency path not active.")

        with self.assertRaises(CadKernelUnavailable) as context:
            OccCadGeometrySession().import_file(FIXTURE_DIR / "neutral_step_two_part_loop.step")

        self.assertIn("cad_geometry_occ.py", str(context.exception))
        self.assertIn("pythonocc-core", str(context.exception))

    def test_missing_file_is_reported_before_optional_kernel_import(self) -> None:
        session = OccCadGeometrySession()
        session._index = GeometryIndex(
            document=CadDocument(source_path="old.step", file_format=CadFileFormat.STEP)
        )

        with self.assertRaises(FileNotFoundError):
            session.import_file(FIXTURE_DIR / "missing_fixture.step")

        self.assertEqual(session.assembly_tree(), [])
        self.assertEqual(session.shape_references(), [])
        self.assertEqual(session.feature_references(), [])

    def test_step_fixture_imports_when_occ_and_fixture_are_available(self) -> None:
        if not is_occ_available():
            self.skipTest(f"{OCC_DEPENDENCY_MESSAGE} {PYTHONOCC_PIP_BLOCKER}")
        fixture = FIXTURE_DIR / "neutral_step_two_part_loop.step"
        if not fixture.exists():
            self.skipTest(f"STEP CAD fixture is not present: {fixture}")

        session = OccCadGeometrySession()
        document = session.import_file(fixture)

        self.assertEqual(document.file_format, CadFileFormat.STEP)
        self.assertTrue(session.assembly_tree())
        self.assertTrue(session.shape_references())
        self.assertTrue(session.feature_references())
        body_colors = [
            child.display_color
            for root in session.assembly_tree()
            for child in root.children
            if child.node_type == AssemblyNodeType.BODY
        ]
        self.assertTrue(body_colors)
        self.assertTrue(all(color is not None for color in body_colors))
        if len(body_colors) > 1:
            self.assertGreater(len(set(body_colors)), 1)

    def test_caster_whell_step_fixture_imports_when_occ_is_available(self) -> None:
        if not is_occ_available():
            self.skipTest(f"{OCC_DEPENDENCY_MESSAGE} {PYTHONOCC_PIP_BLOCKER}")
        if not CASTER_WHELL_STEP_FIXTURE.exists():
            self.skipTest(f"Caster STEP fixture is not present: {CASTER_WHELL_STEP_FIXTURE}")

        session = OccCadGeometrySession()
        document = session.import_file(CASTER_WHELL_STEP_FIXTURE)

        self.assertEqual(document.file_format, CadFileFormat.STEP)
        self.assertEqual(document.display_name, "caster_wheel.stp")
        self.assertTrue(session.assembly_tree())
        self.assertTrue(session.shape_references())
        self.assertTrue(session.feature_references())

    def test_iges_fixture_imports_when_occ_and_fixture_are_available(self) -> None:
        if not is_occ_available():
            self.skipTest(f"{OCC_DEPENDENCY_MESSAGE} {PYTHONOCC_PIP_BLOCKER}")
        fixture = FIXTURE_DIR / "neutral_iges_single_part.igs"
        if not fixture.exists():
            self.skipTest(f"IGES CAD fixture is not present: {fixture}")

        session = OccCadGeometrySession()
        document = session.import_file(fixture)

        self.assertEqual(document.file_format, CadFileFormat.IGES)
        self.assertTrue(session.assembly_tree())
        self.assertTrue(session.shape_references())
        self.assertTrue(session.feature_references())


if __name__ == "__main__":
    unittest.main()
