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
    CadRuntimeShapeProvider,
    CadSourceValidationResult,
    GeometryIndex,
    InMemoryCadGeometrySession,
    MeasurementKind,
    UnsupportedCadFormatError,
    cad_format_from_path,
    cad_source_topology_hash,
    feature_from_shape_reference,
    is_supported_neutral_cad,
    measure_feature_pair,
    normalize_vector,
    validate_cad_source_reimport,
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
    CadSourceStatus,
    FeatureKind,
    FeatureReference,
    ShapeKind,
    ShapeReference,
    Vector3D,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "cad_1d_tolerance"
CASTER_WHELL_FIXTURE_DIR = FIXTURE_DIR / "caster_whell_v0"
CASTER_WHELL_STEP_FIXTURE = CASTER_WHELL_FIXTURE_DIR / "caster_wheel.stp"
XDE_NAMED_COLORED_STEP_FIXTURE = FIXTURE_DIR / "xde_named_colored_assembly.step"
PYTHONOCC_PIP_BLOCKER = (
    "Local check: `python -m pip install --dry-run pythonocc-core` returned "
    "`No matching distribution found for pythonocc-core`."
)


def _assembly_names(node: AssemblyNode) -> list[str]:
    names = [node.name]
    for child in node.children:
        names.extend(_assembly_names(child))
    return names


def _iter_assembly_nodes(node: AssemblyNode) -> list[AssemblyNode]:
    nodes = [node]
    for child in node.children:
        nodes.extend(_iter_assembly_nodes(child))
    return nodes


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
            metadata={"metadata_source": "test"},
        )
        document = CadDocument(
            id="cad_doc_1",
            source_path="fixture.step",
            file_format=CadFileFormat.STEP,
            assembly_root=root,
            display_name="fixture.step",
            metadata={"cad_metadata_source": "in_memory"},
        )
        shape = ShapeReference(
            id="shape_body_1",
            document_id="cad_doc_1",
            assembly_path=["Fixture Assembly", "Body 1"],
            shape_type=ShapeKind.BODY,
            metadata={"xde_label": "0:1:1"},
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

    def test_source_topology_hash_ignores_runtime_ids_and_file_hash_labels(self) -> None:
        first = ShapeReference(
            id="shape_old",
            document_id="cad_old",
            assembly_path=["Caster", "Bracket"],
            shape_type=ShapeKind.FACE,
            kernel_label="sha256:old:xde:0:1:face:7",
            geometric_signature={"area": 42.1234567, "normal": [1.0, 0.0, 0.0]},
            fallback_display_name="Datum face",
            metadata={"xde_label": "0:1"},
        )
        second = ShapeReference(
            id="shape_new",
            document_id="cad_new",
            assembly_path=["Caster", "Bracket"],
            shape_type=ShapeKind.FACE,
            kernel_label="sha256:new:xde:0:1:face:7",
            geometric_signature={"area": 42.12345671, "normal": [1.0, 0.0, 0.0]},
            fallback_display_name="Datum face",
            metadata={"xde_label": "0:1"},
        )

        self.assertEqual(
            cad_source_topology_hash([first]),
            cad_source_topology_hash([second]),
        )

    def test_source_validation_separates_hash_and_topology_changes(self) -> None:
        baseline_shape = ShapeReference(
            id="shape_a",
            assembly_path=["Caster", "Bracket"],
            shape_type=ShapeKind.FACE,
            kernel_label="cad_old:Caster/Bracket:face:1",
            geometric_signature={"area": 42.0},
            fallback_display_name="Datum face",
        )
        changed_shape = ShapeReference(
            id="shape_b",
            assembly_path=["Caster", "Bracket"],
            shape_type=ShapeKind.FACE,
            kernel_label="cad_new:Caster/Bracket:face:1",
            geometric_signature={"area": 84.0},
            fallback_display_name="Datum face",
        )
        original = CadDocument(
            source_path="old.step",
            file_hash="sha256:old",
            source_topology_hash=cad_source_topology_hash([baseline_shape]),
        )
        reexported = CadDocument(source_path="new.step", file_hash="sha256:new")

        hash_only = validate_cad_source_reimport(original, reexported, [baseline_shape])
        topology_changed = validate_cad_source_reimport(
            original,
            reexported,
            [changed_shape],
        )

        self.assertIsInstance(hash_only, CadSourceValidationResult)
        self.assertEqual(hash_only.status, CadSourceStatus.CHANGED_HASH)
        self.assertTrue(hash_only.hash_changed)
        self.assertFalse(hash_only.topology_changed)
        self.assertEqual(topology_changed.status, CadSourceStatus.CHANGED_TOPOLOGY)
        self.assertTrue(topology_changed.topology_changed)

    def test_occ_session_advertises_explicit_runtime_shape_provider_contract(self) -> None:
        session = OccCadGeometrySession()
        missing_shape = ShapeReference(
            id="shape_not_imported",
            shape_type=ShapeKind.BODY,
            fallback_display_name="Not imported",
        )

        self.assertIsInstance(session, CadRuntimeShapeProvider)
        self.assertIsNone(session.runtime_shape(missing_shape))
        self.assertIsNone(session.kernel_shape(missing_shape))

    def test_in_memory_session_does_not_claim_live_runtime_shapes(self) -> None:
        session = InMemoryCadGeometrySession()

        self.assertNotIsInstance(session, CadRuntimeShapeProvider)

    def test_cad_metadata_fields_are_additive_and_serializable(self) -> None:
        root = AssemblyNode(
            id="asm_xde_root",
            name="xde_fixture",
            source_label="0:1:1:1",
            metadata={"metadata_source": "occt_xde", "xde_label": "0:1:1:1"},
        )
        shape = ShapeReference(
            id="shape_xde_face",
            document_id="cad_xde",
            assembly_path=["xde_fixture", "top_plate:1"],
            shape_type=ShapeKind.FACE,
            metadata={"metadata_source": "occt_xde", "display_color": [51, 102, 204]},
        )
        document = CadDocument(
            id="cad_xde",
            source_path="xde_named_colored_assembly.step",
            file_format=CadFileFormat.STEP,
            assembly_root=root,
            display_name="xde_named_colored_assembly.step",
            metadata={"cad_metadata_source": "occt_xde"},
        )

        loaded_document = CadDocument.from_dict(document.to_dict())
        loaded_shape = ShapeReference.from_dict(shape.to_dict())

        self.assertEqual(loaded_document.metadata["cad_metadata_source"], "occt_xde")
        self.assertEqual(
            loaded_document.assembly_root.metadata["xde_label"],
            "0:1:1:1",
        )
        self.assertEqual(loaded_shape.metadata["display_color"], [51, 102, 204])


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
        assembly_names = _assembly_names(session.assembly_tree()[0])
        self.assertFalse(
            any("Open CASCADE STEP translator" in name for name in assembly_names)
        )
        display_colors = [
            child.display_color
            for root in session.assembly_tree()
            for child in _iter_assembly_nodes(root)
            if child.node_type in {AssemblyNodeType.PART, AssemblyNodeType.BODY}
        ]
        self.assertTrue(display_colors)
        self.assertTrue(all(color is not None for color in display_colors))
        if len(display_colors) > 1:
            self.assertGreater(len(set(display_colors)), 1)

    def test_xde_step_fixture_preserves_names_colors_and_labels(self) -> None:
        if not is_occ_available():
            self.skipTest(f"{OCC_DEPENDENCY_MESSAGE} {PYTHONOCC_PIP_BLOCKER}")
        if not XDE_NAMED_COLORED_STEP_FIXTURE.exists():
            self.skipTest(
                f"XDE STEP CAD fixture is not present: {XDE_NAMED_COLORED_STEP_FIXTURE}"
            )

        session = OccCadGeometrySession()
        document = session.import_file(XDE_NAMED_COLORED_STEP_FIXTURE)
        root = session.assembly_tree()[0]
        part_nodes = {
            node.name: node
            for node in _iter_assembly_nodes(root)
            if node.node_type == AssemblyNodeType.PART
        }
        body_refs = session.shape_references({ShapeKind.BODY})

        self.assertEqual(document.file_format, CadFileFormat.STEP)
        self.assertEqual(document.metadata["cad_metadata_source"], "occt_xde")
        self.assertEqual(root.name, "xde_fixture")
        self.assertEqual(part_nodes["top_plate:1"].display_color, (51, 102, 204))
        self.assertEqual(part_nodes["bushing:1"].display_color, (204, 76, 26))
        self.assertTrue(
            any(shape.assembly_path[-1] == "top_plate:1" for shape in body_refs)
        )
        self.assertTrue(
            any(shape.assembly_path[-1] == "bushing:1" for shape in body_refs)
        )
        self.assertTrue(all(shape.metadata.get("xde_label") for shape in body_refs))
        self.assertEqual(len({shape.id for shape in body_refs}), len(body_refs))

    def test_caster_whell_step_fixture_imports_when_occ_is_available(self) -> None:
        if not is_occ_available():
            self.skipTest(f"{OCC_DEPENDENCY_MESSAGE} {PYTHONOCC_PIP_BLOCKER}")
        if not CASTER_WHELL_STEP_FIXTURE.exists():
            self.skipTest(
                f"Caster STEP fixture is not present: {CASTER_WHELL_STEP_FIXTURE}"
            )

        session = OccCadGeometrySession()
        document = session.import_file(CASTER_WHELL_STEP_FIXTURE)

        self.assertEqual(document.file_format, CadFileFormat.STEP)
        self.assertEqual(document.display_name, "caster_wheel.stp")
        self.assertTrue(session.assembly_tree())
        self.assertTrue(session.shape_references())
        self.assertTrue(session.feature_references())
        from mechanical_design_tool_suite.cad_viewer_occ import (
            _shape_display_rgb,
            _should_use_palette_colors,
        )

        body_refs = session.shape_references({ShapeKind.BODY})
        self.assertTrue(_should_use_palette_colors(session, body_refs))
        viewer_colors = [
            _shape_display_rgb(
                session,
                body_ref,
                display_index,
                use_palette_colors=True,
            )
            for display_index, body_ref in enumerate(body_refs, start=1)
        ]
        self.assertGreater(len(set(viewer_colors)), 1)
        if document.metadata.get("cad_metadata_source") == "occt_xde":
            assembly_names = _assembly_names(session.assembly_tree()[0])
            self.assertIn("caster_wheel", assembly_names)
            self.assertIn("Assemblage", assembly_names)
            self.assertFalse(
                all(name.startswith("Body ") for name in assembly_names[1:])
            )

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
