from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from mechanical_design_tool_suite.cad_tolerance_models import (
    AnalysisMode,
    AnalysisSettings,
    AnnotationPlane,
    AssemblyNode,
    AssemblyNodeType,
    CadDocument,
    CadFileFormat,
    CadToleranceProject,
    FeatureKind,
    FeatureReference,
    GeometricControlType,
    GeometricTolerance,
    NonOneDWarning,
    NonOneDWarningKind,
    PROJECT_TYPE,
    QualityMetric,
    QualityTarget,
    ResultStatus,
    ShapeKind,
    ShapeReference,
    Snapshot,
    StackupContributor,
    StackupObjective,
    StackupRequirement,
    ToleranceType,
    Vector3D,
)
from mechanical_design_tool_suite.cad_tolerance_project_io import (
    CURRENT_SCHEMA_VERSION,
    PROJECT_SUFFIX,
    load_project,
    migrate_project_data,
    save_project,
)


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "cad_1d_tolerance"
    / "sample_cad_1d_project.tolproj"
)


def _sample_project() -> CadToleranceProject:
    assembly_root = AssemblyNode(
        id="asm_root",
        name="Caster Assembly",
        node_type=AssemblyNodeType.ROOT,
        children=[
            AssemblyNode(
                id="asm_bracket",
                name="Bracket",
                node_type=AssemblyNodeType.PART,
                parent_id="asm_root",
                display_color=(180, 190, 205),
                source_label="0:1",
            ),
            AssemblyNode(
                id="asm_bushing",
                name="Bushing",
                node_type=AssemblyNodeType.PART,
                parent_id="asm_root",
                display_color=(80, 140, 180),
                source_label="0:2",
            ),
        ],
        source_label="0",
    )
    cad_document = CadDocument(
        id="cad_doc_1",
        source_path="fixtures/cad_1d_tolerance/neutral_step_two_part_loop.step",
        file_hash="sha256:0123456789abcdef",
        file_format=CadFileFormat.STEP,
        imported_at="2026-05-12T20:10:00Z",
        units="mm",
        assembly_root=assembly_root,
        display_name="neutral_step_two_part_loop.step",
        import_settings={"heal_shapes": True, "object_filter": "solids"},
    )

    start_shape = ShapeReference(
        id="shape_start_face",
        document_id="cad_doc_1",
        assembly_path=["Caster Assembly", "Bracket"],
        shape_type=ShapeKind.FACE,
        kernel_label="0:1:face:12",
        geometric_signature={"area": 420.0, "normal": [1.0, 0.0, 0.0]},
        fallback_display_name="Bracket inside face",
    )
    end_shape = ShapeReference(
        id="shape_end_cylinder",
        document_id="cad_doc_1",
        assembly_path=["Caster Assembly", "Bushing"],
        shape_type=ShapeKind.FACE,
        kernel_label="0:2:face:7",
        geometric_signature={"radius": 12.5, "axis": [1.0, 0.0, 0.0]},
        fallback_display_name="Bushing ID",
    )
    start_feature = FeatureReference(
        id="feature_start",
        name="Bracket datum face",
        feature_type=FeatureKind.FACE,
        shape_reference=start_shape,
        owner_part_id="asm_bracket",
        datum_label="A",
        point=Vector3D(0.0, 0.0, 0.0),
        normal=Vector3D(1.0, 0.0, 0.0),
    )
    end_feature = FeatureReference(
        id="feature_end",
        name="Bushing ID axis",
        feature_type=FeatureKind.CYLINDER,
        shape_reference=end_shape,
        owner_part_id="asm_bushing",
        datum_label="B",
        point=Vector3D(24.0, 0.0, 0.0),
        axis=Vector3D(1.0, 0.0, 0.0),
    )
    generated_contributor = StackupContributor(
        id="contrib_generated_1",
        name="Bracket to bushing face",
        nominal=24.0,
        tolerance=0.0,
        tolerance_minus=0.10,
        tolerance_plus=0.15,
        sensitivity=1.0,
        tolerance_type=ToleranceType.LIMITS,
        source_feature=start_feature,
        shared_with_stackup_ids=["stackup_overall_height"],
        source_note="Generated from STEP loop selection.",
    )
    geometric = GeometricTolerance(
        id="gdt_runout_1",
        control_type=GeometricControlType.RUNOUT,
        tolerance_value=0.10,
        datum_references=["A"],
        derived_minus=0.05,
        derived_plus=0.05,
        conversion_note="Runout projected onto the selected stack direction.",
    )
    manual_contributor = StackupContributor(
        id="contrib_gdt_1",
        name="Manual runout to datum A",
        nominal=0.0,
        tolerance=0.0,
        tolerance_type=ToleranceType.GEOMETRIC,
        datum_references=["A"],
        source_feature=end_feature,
        geometric_tolerance=geometric,
        source_note="Manual GD&T row.",
    )
    stackup = StackupRequirement(
        id="stackup_bushing_alignment",
        name="Bushing ID alignment",
        contributors=[generated_contributor, manual_contributor],
        objective=StackupObjective.bilateral(
            nominal=24.0,
            tolerance_minus=0.50,
            tolerance_plus=0.75,
            description="+0.75/-0.50 bushing objective",
        ),
        target_quality=QualityTarget(QualityMetric.CPK, 1.67, sigma_coverage=3.0),
        analysis_mode=AnalysisMode.STATISTICAL,
        start_feature=start_feature,
        end_feature=end_feature,
        direction=Vector3D(1.0, 0.0, 0.0),
        annotation_plane=AnnotationPlane(
            origin=Vector3D(12.0, 20.0, 0.0),
            normal=Vector3D(0.0, 0.0, 1.0),
            source_feature_id="feature_start",
            display_name="Front annotation plane",
        ),
        warnings=[
            NonOneDWarning(
                id="warn_offset_1",
                warning_kind=NonOneDWarningKind.OFFSET_FEATURES,
                message="Endpoint features are laterally offset from the stack direction.",
                severity=ResultStatus.WARN,
                feature_ids=["feature_start", "feature_end"],
                observed_value=1.8,
                threshold=1.0,
            )
        ],
    )
    snapshot = Snapshot(
        id="snapshot_summary_1",
        image_path="snapshots/bushing_alignment.png",
        camera={"eye": [120.0, 80.0, 60.0], "target": [12.0, 0.0, 0.0]},
        visible_stackup_ids=["stackup_bushing_alignment"],
        annotation_positions={"stackup_bushing_alignment": [0.42, 0.58]},
        captured_at="2026-05-12T20:20:00Z",
    )
    return CadToleranceProject(
        title="Caster tolerance study",
        unit_system="mm",
        cad_documents=[cad_document],
        stackups=[stackup],
        settings=AnalysisSettings(
            sigma_coverage=3.0,
            default_target_cpk=1.67,
            lateral_offset_warning_threshold=1.0,
            min_direction_alignment=0.96,
            multi_interface_warning_count=4,
            projection_sensitivity_warning_threshold=0.12,
        ),
        snapshots=[snapshot],
        reports=[
            {
                "id": "report_summary_1",
                "title": "Caster tolerance report",
                "snapshot_ids": ["snapshot_summary_1"],
                "generated_at": "2026-05-12T20:30:00Z",
            }
        ],
    )


class CadToleranceProjectIoTest(unittest.TestCase):
    def test_project_round_trips_all_persisted_cad_fields(self) -> None:
        project = _sample_project()

        with tempfile.TemporaryDirectory() as directory:
            saved_path = save_project(project, Path(directory) / "caster_study")
            loaded = load_project(saved_path)

        self.assertEqual(saved_path.suffix, PROJECT_SUFFIX)
        self.assertEqual(loaded.schema_version, CURRENT_SCHEMA_VERSION)
        self.assertEqual(loaded.project_type, PROJECT_TYPE)
        self.assertEqual(loaded.title, "Caster tolerance study")
        self.assertEqual(loaded.settings.default_target_cpk, 1.67)

        document = loaded.cad_documents[0]
        self.assertEqual(document.file_format, CadFileFormat.STEP)
        self.assertEqual(document.file_hash, "sha256:0123456789abcdef")
        self.assertEqual(document.import_settings["object_filter"], "solids")
        self.assertEqual(document.assembly_root.children[1].display_color, (80, 140, 180))

        stackup = loaded.stackups[0]
        self.assertEqual(stackup.analysis_mode, AnalysisMode.STATISTICAL)
        self.assertAlmostEqual(stackup.objective.tolerance_plus, 0.75)
        self.assertEqual(stackup.target_quality.metric, QualityMetric.CPK)
        self.assertEqual(stackup.start_feature.datum_label, "A")
        self.assertEqual(stackup.end_feature.shape_reference.shape_type, ShapeKind.FACE)
        self.assertEqual(stackup.annotation_plane.display_name, "Front annotation plane")

        generated = stackup.contributors[0]
        self.assertEqual(generated.tolerance_type, ToleranceType.LIMITS)
        self.assertAlmostEqual(generated.tolerance_minus, 0.10)
        self.assertEqual(generated.shared_with_stackup_ids, ["stackup_overall_height"])

        manual = stackup.contributors[1]
        self.assertEqual(manual.tolerance_type, ToleranceType.GEOMETRIC)
        self.assertEqual(manual.geometric_tolerance.control_type, GeometricControlType.RUNOUT)
        self.assertEqual(manual.geometric_tolerance.datum_references, ["A"])
        self.assertAlmostEqual(manual.geometric_tolerance.derived_plus, 0.05)
        self.assertEqual(stackup.warnings[0].warning_kind, NonOneDWarningKind.OFFSET_FEATURES)

        self.assertEqual(loaded.snapshots[0].camera["target"], [12.0, 0.0, 0.0])
        self.assertEqual(loaded.reports[0]["snapshot_ids"], ["snapshot_summary_1"])

    def test_fixture_project_round_trips_through_disk(self) -> None:
        project = load_project(FIXTURE_PATH)

        with tempfile.TemporaryDirectory() as directory:
            saved_path = save_project(project, Path(directory) / "fixture_copy.tolproj")
            loaded = load_project(saved_path)

        self.assertEqual(loaded.title, project.title)
        self.assertEqual(loaded.cad_documents[0].display_name, "neutral_step_two_part_loop.step")
        self.assertEqual(loaded.stackups[0].contributors[1].name, "Manual runout to datum A")

    def test_missing_optional_fields_load_with_domain_defaults(self) -> None:
        data = {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "project_type": PROJECT_TYPE,
            "title": "minimal CAD project",
        }

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "minimal.tolproj"
            path.write_text(json.dumps(data), encoding="utf-8")
            loaded = load_project(path)

        self.assertEqual(loaded.title, "minimal CAD project")
        self.assertEqual(loaded.unit_system, "mm")
        self.assertEqual(loaded.cad_documents, [])
        self.assertEqual(loaded.stackups, [])
        self.assertAlmostEqual(loaded.settings.sigma_coverage, 3.0)

    def test_invalid_project_envelopes_raise_value_error(self) -> None:
        cases = [
            [1, 2, 3],
            {"schema_version": CURRENT_SCHEMA_VERSION, "project_type": "legacy_tolerance"},
            {"schema_version": CURRENT_SCHEMA_VERSION + 1, "project_type": PROJECT_TYPE},
            {"project_type": PROJECT_TYPE},
            {"schema_version": "not-an-integer", "project_type": PROJECT_TYPE},
        ]

        with tempfile.TemporaryDirectory() as directory:
            for index, data in enumerate(cases):
                with self.subTest(data=data):
                    path = Path(directory) / f"invalid_{index}.tolproj"
                    path.write_text(json.dumps(data), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_project(path)

    def test_unknown_forward_fields_are_ignored_when_known_schema_is_valid(self) -> None:
        data = _sample_project().to_dict()
        data["future_top_level"] = {"ignored": True}
        data["cad_documents"][0]["future_document_field"] = "ignored"
        data["stackups"][0]["future_stackup_field"] = "ignored"
        data["stackups"][0]["contributors"][0]["future_contributor_field"] = "ignored"

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "future_fields.tolproj"
            path.write_text(json.dumps(data), encoding="utf-8")
            loaded = load_project(path)

        self.assertEqual(loaded.title, "Caster tolerance study")
        self.assertEqual(loaded.cad_documents[0].id, "cad_doc_1")
        self.assertEqual(loaded.stackups[0].contributors[0].id, "contrib_generated_1")

    def test_schema_v1_migration_hook_normalizes_to_current_schema(self) -> None:
        legacy = {
            "schema_version": 1,
            "project_type": PROJECT_TYPE,
            "title": "legacy CAD project",
            "units": "inch",
        }

        migrated = migrate_project_data(legacy)

        self.assertEqual(migrated["schema_version"], CURRENT_SCHEMA_VERSION)
        self.assertEqual(migrated["unit_system"], "inch")
        self.assertEqual(migrated["cad_documents"], [])
        self.assertEqual(migrated["stackups"], [])
        self.assertEqual(migrated["snapshots"], [])
        self.assertEqual(migrated["reports"], [])
        self.assertNotIn("unit_system", legacy)

    def test_save_rejects_wrong_project_type(self) -> None:
        project = _sample_project()
        project.project_type = "legacy_tolerance"

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                save_project(project, Path(directory) / "wrong_type.tolproj")


if __name__ == "__main__":
    unittest.main()
