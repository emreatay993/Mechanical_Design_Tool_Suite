from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QWidget

from mechanical_design_tool_suite.cad_geometry_api import GeometryIndex, InMemoryCadGeometrySession
from mechanical_design_tool_suite.cad_stackup_workflow import (
    DEFAULT_GENERATED_TOLERANCE,
    GUIDED_STACKUP_STEP_LABELS,
    GuidedStackupStep,
    GuidedStackupWorkflowController,
)
from mechanical_design_tool_suite.cad_tolerance_gui import create_cad_tolerance_window
from mechanical_design_tool_suite.cad_tolerance_models import (
    AssemblyNode,
    AssemblyNodeType,
    CadDocument,
    CadFileFormat,
    CadToleranceProject,
    FeatureKind,
    FeatureReference,
    ShapeKind,
    ShapeReference,
    Snapshot,
    StackupContributor,
    StackupRequirement,
    Vector3D,
)
from mechanical_design_tool_suite.cad_tolerance_viewmodels import CadToleranceWorkspaceViewModel
from mechanical_design_tool_suite.cad_viewer_api import (
    CadCameraState,
    CadViewerSelection,
    HighlightRole,
    SnapshotRequest,
    ViewerSelectionMode,
)


class FakeViewer(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.selection_modes_history: list[set[ViewerSelectionMode]] = []
        self.highlights: list[tuple[str, HighlightRole]] = []
        self.snapshot_requests: list[SnapshotRequest] = []

    def display_document(self, session, display_kinds=None) -> None:
        return

    def clear(self) -> None:
        return

    def fit_all(self) -> None:
        return

    def pan(self, dx: int, dy: int) -> None:
        return

    def zoom(self, factor: float) -> None:
        return

    def set_standard_view(self, view) -> None:
        return

    def set_selection_modes(self, modes) -> None:
        self.selection_modes_history.append(set(modes))

    def highlight(self, shape_ref, role) -> None:
        self.highlights.append((shape_ref.id, HighlightRole(role)))

    def clear_highlights(self, roles=None) -> None:
        return

    def camera_state(self) -> CadCameraState:
        return CadCameraState(view_name="fake")

    def capture_snapshot(self, request: SnapshotRequest) -> Snapshot:
        self.snapshot_requests.append(request)
        Path(request.output_path).write_bytes(b"fake")
        return Snapshot(
            image_path=str(request.output_path),
            camera=self.camera_state().to_dict(),
            visible_stackup_ids=list(request.visible_stackup_ids),
            annotation_positions=dict(request.annotation_positions),
        )


class GuidedStackupWorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        fixture = _workflow_fixture()
        self.session = fixture["session"]
        self.project = fixture["project"]
        self.features = fixture["features"]

    def test_controller_guides_endpoint_direction_plane_loop_and_constraints(self) -> None:
        controller = GuidedStackupWorkflowController(self.session, self.project)

        update = controller.start_new_stackup("Stackup1")

        self.assertEqual(update.toolbar.step_labels, GUIDED_STACKUP_STEP_LABELS)
        self.assertEqual(update.toolbar.active_label, "Selection 1")
        self.assertEqual(update.selection_filter.prompt, "Select a face, edge or vertex")
        self.assertEqual(
            update.selection_filter.viewer_mode_set,
            {ViewerSelectionMode.FACE, ViewerSelectionMode.EDGE, ViewerSelectionMode.VERTEX},
        )

        update = controller.apply_selection(_selection(self.features["start"]))
        self.assertEqual(update.toolbar.active_label, "Width 1")
        self.assertEqual(update.highlights[0].role, HighlightRole.SELECTED_START)

        update = controller.confirm_current_step()
        self.assertEqual(update.toolbar.active_label, "Selection 2")

        update = controller.apply_selection(_selection(self.features["end"]))
        self.assertEqual(update.toolbar.active_label, "Width 2")
        self.assertEqual(update.highlights[0].role, HighlightRole.SELECTED_END)

        update = controller.confirm_current_step()
        self.assertEqual(update.toolbar.active_label, "Direction")
        self.assertEqual(update.selection_filter.prompt, "Select a direction reference")

        update = controller.apply_selection(_selection(self.features["direction"]))
        self.assertEqual(update.toolbar.active_label, "Analysis Plane")
        self.assertEqual(controller.state.direction.to_list(), [0.0, 0.0, 1.0])
        self.assertEqual(update.highlights[0].role, HighlightRole.DIRECTION)

        update = controller.apply_selection(_selection(self.features["analysis_plane"]))
        self.assertEqual(update.toolbar.active_label, "Dimension Location")
        self.assertEqual(update.highlights[0].role, HighlightRole.ANALYSIS_PLANE)

        update = controller.set_annotation_position(
            {"screen": [420, 580], "model": [1.0, 2.0, 3.0]}
        )
        self.assertEqual(controller.state.active_step, GuidedStackupStep.LOOP_COMPONENTS)
        self.assertIn("Select the component", update.selection_filter.prompt)

        controller.set_mating_face_goal(2)
        update = controller.apply_selection(_selection(self.features["loop_component"]))
        self.assertEqual(update.toolbar.component_count_text, "1 Component")
        self.assertEqual(update.highlights[0].role, HighlightRole.LOOP_MEMBER)

        update = controller.confirm_current_step()
        self.assertEqual(controller.state.active_step, GuidedStackupStep.MATING_FACES)
        self.assertIn("axle_support:2", update.selection_filter.prompt)

        controller.apply_selection(_selection(self.features["mating_1"]))
        update = controller.apply_selection(_selection(self.features["mating_2"]))
        self.assertEqual(update.toolbar.mating_face_count_text, "2 of 2 Mating Faces")

        update = controller.finish()
        stackup = update.stackup

        self.assertIsNotNone(stackup)
        self.assertEqual(self.project.stackups[-1], stackup)
        self.assertEqual(stackup.start_feature.id, "feature_start")
        self.assertEqual(stackup.end_feature.id, "feature_end")
        self.assertEqual([feature.id for feature in stackup.loop_features], ["feature_loop_component"])
        self.assertEqual(
            [feature.id for feature in stackup.constraint_features],
            ["feature_mating_1", "feature_mating_2"],
        )
        self.assertEqual(stackup.annotation_position["screen"], [420, 580])
        self.assertEqual(stackup.annotation_plane.source_feature_id, "feature_analysis_plane")
        self.assertEqual(stackup.direction.to_list(), [0.0, 0.0, 1.0])
        self.assertEqual([row.name for row in stackup.contributors], ["Dimension1", "Dimension2", "Dimension3"])
        self.assertTrue(
            all(row.tolerance == DEFAULT_GENERATED_TOLERANCE for row in stackup.contributors)
        )
        self.assertTrue(
            all(row.source_feature and row.source_feature.shape_reference for row in stackup.contributors)
        )

    def test_manual_insert_marks_shared_dimension_in_generated_rows(self) -> None:
        shared_feature = self.features["shared_top_face"]
        existing = StackupRequirement(
            id="stackup_overall_height",
            name="overall height",
            contributors=[
                StackupContributor(
                    id="contrib_existing_shared",
                    name="Dimension2",
                    nominal=12.0,
                    tolerance=0.25,
                    source_feature=shared_feature,
                    source_note="Generated from guided stackup selection.",
                )
            ],
        )
        self.project.stackups.append(existing)
        controller = GuidedStackupWorkflowController(self.session, self.project)
        _advance_to_loop(controller, self.features)

        update = controller.insert_intermediate_feature(
            _selection(shared_feature),
            name="Top surface reference",
        )
        self.assertEqual(update.highlights[0].role, HighlightRole.LOOP_MEMBER)

        stackup = controller.finish().stackup
        inserted = stackup.contributors[0]
        self.assertEqual(inserted.source_feature.name, "Top surface reference")
        self.assertEqual(inserted.source_note, "Manually inserted intermediate feature.")
        self.assertEqual(inserted.shared_with_stackup_ids, ["stackup_overall_height"])

        workspace = CadToleranceWorkspaceViewModel.from_project(self.project)
        rows = workspace.detail_rows(stackup.id)
        inserted_rows = [row for row in rows if row.contributor_id == inserted.id]
        self.assertEqual(inserted_rows[0].shared_with, ("stackup_overall_height",))
        self.assertEqual(
            workspace.annotation_position(stackup.id),
            {"screen": [420, 580], "model": [1.0, 2.0, 3.0]},
        )

    def test_reused_part_dimension_scheme_is_preserved_for_added_feature(self) -> None:
        existing = StackupRequirement(
            id="stackup_vertical_coax",
            name="vertical coax",
            contributors=[
                StackupContributor(
                    id="contrib_bushing_scheme",
                    name="Dimension2",
                    nominal=58.0,
                    tolerance=0.075,
                    datum_references=["A"],
                    source_feature=self.features["start"],
                    source_note="Generated from guided stackup selection.",
                )
            ],
        )
        self.project.stackups.append(existing)
        controller = GuidedStackupWorkflowController(self.session, self.project)
        _advance_to_loop(controller, self.features)

        controller.begin_add_feature()
        update = controller.apply_selection(_selection(self.features["end"]))

        self.assertEqual(update.toolbar.active_label, "Dimension Location")
        stackup = controller.finish().stackup
        reused = stackup.contributors[-1]
        self.assertAlmostEqual(reused.tolerance, 0.075)
        self.assertEqual(reused.datum_references, ["A"])
        self.assertEqual(reused.source_note, "Manually inserted intermediate feature.")
        self.assertTrue(
            stackup.warnings[0].message.startswith("Automatic native CAD mate inference")
        )

    def test_direction_filter_rejects_perpendicular_mating_face(self) -> None:
        controller = GuidedStackupWorkflowController(self.session, self.project)
        _advance_to_loop(controller, self.features)
        controller.apply_selection(_selection(self.features["loop_component"]))
        controller.confirm_current_step()

        with self.assertRaisesRegex(ValueError, "aligned with the stackup direction"):
            controller.apply_selection(_selection(self.features["perpendicular_mating"]))

    def test_gui_starts_workflow_updates_toolbar_and_uses_viewer_filters(self) -> None:
        viewer = FakeViewer()
        workspace = CadToleranceWorkspaceViewModel.from_project(self.project)
        window = create_cad_tolerance_window(
            self.app,
            geometry_session=self.session,
            viewer=viewer,
            workspace=workspace,
        )
        self.addCleanup(window.close)
        window.project = self.project

        window.new_stackup_action.trigger()
        self.app.processEvents()

        prompt = window.findChild(QLabel, "GuidedPromptLabel")
        first_step = window.findChild(QPushButton, "GuidedStep0")
        second_step = window.findChild(QPushButton, "GuidedStep1")

        self.assertEqual(prompt.text(), "Select a face, edge or vertex")
        self.assertTrue(first_step.isChecked())
        self.assertEqual(
            viewer.selection_modes_history[-1],
            {ViewerSelectionMode.FACE, ViewerSelectionMode.EDGE, ViewerSelectionMode.VERTEX},
        )

        window.handle_viewer_selections([_selection(self.features["start"])])
        self.app.processEvents()

        self.assertTrue(second_step.isChecked())
        self.assertEqual(viewer.highlights[-1], ("shape_start", HighlightRole.SELECTED_START))

        stackup_id = "stackup_annotation"
        window.workspace.selected_stackup_id = stackup_id
        window.workspace.annotation_positions_by_stackup_id[stackup_id] = {"screen": [0.25, 0.75]}
        with tempfile.TemporaryDirectory() as directory:
            snapshot_path = Path(directory) / "snapshot.png"
            snapshot = viewer.capture_snapshot(
                SnapshotRequest(
                    snapshot_path,
                    visible_stackup_ids=(stackup_id,),
                    annotation_positions={
                        stackup_id: window.workspace.annotation_position(stackup_id)
                    },
                )
            )

        self.assertEqual(snapshot.visible_stackup_ids, [stackup_id])
        self.assertEqual(snapshot.annotation_positions[stackup_id], {"screen": [0.25, 0.75]})

    def test_gui_toolbar_controls_drive_full_workflow_and_add_feature(self) -> None:
        viewer = FakeViewer()
        workspace = CadToleranceWorkspaceViewModel.from_project(self.project)
        window = create_cad_tolerance_window(
            self.app,
            geometry_session=self.session,
            viewer=viewer,
            workspace=workspace,
        )
        self.addCleanup(window.close)
        window.project = self.project

        window.new_stackup_action.trigger()
        self.app.processEvents()
        ok_button = window.findChild(QPushButton, "GuidedControlOK")
        list_button = window.findChild(QPushButton, "GuidedControlList")

        window.handle_viewer_selections([_selection(self.features["start"])])
        ok_button.click()
        window.handle_viewer_selections([_selection(self.features["end"])])
        ok_button.click()
        window.handle_viewer_selections([_selection(self.features["direction"])])
        window.handle_viewer_selections([_selection(self.features["analysis_plane"])])
        window.viewport_host.annotationMoved.emit(
            "workflow_stackup_dimension",
            {"screen": [0.36, 0.64]},
        )
        window.handle_viewer_selections([_selection(self.features["loop_component"])])
        ok_button.click()
        window.handle_viewer_selections([_selection(self.features["mating_1"])])
        window.handle_viewer_selections([_selection(self.features["mating_2"])])
        ok_button.click()
        self.app.processEvents()

        stackup = self.project.stackups[-1]
        self.assertEqual(stackup.annotation_position, {"screen": [0.36, 0.64]})
        self.assertEqual([row.name for row in stackup.contributors], ["Dimension1", "Dimension2", "Dimension3"])
        self.assertTrue(window.add_feature_action.isEnabled())
        self.assertTrue(window.generate_report_action.isEnabled())

        list_button.click()
        self.assertIn("1 Components", window.statusBar().currentMessage())
        self.assertIn("2 of 2 Mating Faces", window.statusBar().currentMessage())

        window.add_feature_action.trigger()
        self.assertIn("Select a face, edge or vertex to add", window.statusBar().currentMessage())
        window.handle_viewer_selections([_selection(self.features["shared_top_face"])])
        self.app.processEvents()

        self.assertEqual(stackup.contributors[-1].source_feature.id, "feature_shared_top_face")
        self.assertEqual(window.detail_model.rowCount(), len(window.workspace.detail_rows(stackup.id)))


def _advance_to_loop(
    controller: GuidedStackupWorkflowController,
    features: dict[str, FeatureReference],
) -> None:
    controller.start_new_stackup("Stackup2")
    controller.apply_selection(_selection(features["start"]))
    controller.confirm_current_step()
    controller.apply_selection(_selection(features["end"]))
    controller.confirm_current_step()
    controller.apply_selection(_selection(features["direction"]))
    controller.apply_selection(_selection(features["analysis_plane"]))
    controller.set_annotation_position({"screen": [420, 580], "model": [1.0, 2.0, 3.0]})


def _workflow_fixture() -> dict[str, object]:
    root = AssemblyNode(
        id="asm_root",
        name="Caster Assembly",
        node_type=AssemblyNodeType.ROOT,
    )
    document = CadDocument(
        id="cad_doc_1",
        source_path="fixture.step",
        file_format=CadFileFormat.STEP,
        display_name="fixture.step",
        assembly_root=root,
    )
    features = {
        "start": _feature(
            "feature_start",
            "bushing:2 ID",
            FeatureKind.CYLINDER,
            _shape(
                "shape_start",
                ShapeKind.FACE,
                "bushing:2 ID",
                ["Caster Assembly", "bushing:2"],
                {"surface_type": "cylinder", "point": [0.0, 0.0, 0.0], "axis": [0.0, 0.0, 1.0], "radius": 6.0},
            ),
            "bushing:2",
            point=(0.0, 0.0, 0.0),
            axis=(0.0, 0.0, 1.0),
        ),
        "end": _feature(
            "feature_end",
            "bushing:1 ID",
            FeatureKind.CYLINDER,
            _shape(
                "shape_end",
                ShapeKind.FACE,
                "bushing:1 ID",
                ["Caster Assembly", "bushing:1"],
                {"surface_type": "cylinder", "point": [0.0, 0.0, 10.0], "axis": [0.0, 0.0, 1.0], "radius": 6.0},
            ),
            "bushing:1",
            point=(0.0, 0.0, 10.0),
            axis=(0.0, 0.0, 1.0),
        ),
        "direction": _feature(
            "feature_direction",
            "top plate top surface",
            FeatureKind.PLANE,
            _shape(
                "shape_direction",
                ShapeKind.FACE,
                "top plate top surface",
                ["Caster Assembly", "top_plate:1"],
                {"surface_type": "plane", "point": [0.0, 0.0, 0.0], "normal": [0.0, 0.0, 1.0]},
            ),
            "top_plate:1",
            point=(0.0, 0.0, 0.0),
            normal=(0.0, 0.0, 1.0),
        ),
        "analysis_plane": _feature(
            "feature_analysis_plane",
            "front annotation plane",
            FeatureKind.PLANE,
            _shape(
                "shape_analysis_plane",
                ShapeKind.FACE,
                "front annotation plane",
                ["Caster Assembly", "top_plate:1"],
                {"surface_type": "plane", "point": [0.0, 20.0, 0.0], "normal": [0.0, 1.0, 0.0]},
            ),
            "top_plate:1",
            point=(0.0, 20.0, 0.0),
            normal=(0.0, 1.0, 0.0),
        ),
        "loop_component": _feature(
            "feature_loop_component",
            "axle support component",
            FeatureKind.FACE,
            _shape(
                "shape_loop_component",
                ShapeKind.FACE,
                "axle support component",
                ["Caster Assembly", "axle_support:2"],
                {"surface_type": "plane", "point": [0.0, 0.0, 4.0], "normal": [0.0, 0.0, 1.0]},
            ),
            "axle_support:2",
            point=(0.0, 0.0, 4.0),
            normal=(0.0, 0.0, 1.0),
        ),
        "mating_1": _feature(
            "feature_mating_1",
            "axle support mating face",
            FeatureKind.FACE,
            _shape(
                "shape_mating_1",
                ShapeKind.FACE,
                "axle support mating face",
                ["Caster Assembly", "axle_support:2"],
                {"surface_type": "plane", "point": [0.0, 0.0, 5.0], "normal": [0.0, 0.0, 1.0]},
            ),
            "axle_support:2",
            point=(0.0, 0.0, 5.0),
            normal=(0.0, 0.0, 1.0),
        ),
        "mating_2": _feature(
            "feature_mating_2",
            "axle support second mating face",
            FeatureKind.FACE,
            _shape(
                "shape_mating_2",
                ShapeKind.FACE,
                "axle support second mating face",
                ["Caster Assembly", "axle_support:2"],
                {"surface_type": "plane", "point": [0.0, 0.0, 8.0], "normal": [0.0, 0.0, 1.0]},
            ),
            "axle_support:2",
            point=(0.0, 0.0, 8.0),
            normal=(0.0, 0.0, 1.0),
        ),
        "perpendicular_mating": _feature(
            "feature_perpendicular_mating",
            "axle support side face",
            FeatureKind.FACE,
            _shape(
                "shape_perpendicular_mating",
                ShapeKind.FACE,
                "axle support side face",
                ["Caster Assembly", "axle_support:2"],
                {"surface_type": "plane", "point": [0.0, 0.0, 6.0], "normal": [1.0, 0.0, 0.0]},
            ),
            "axle_support:2",
            point=(0.0, 0.0, 6.0),
            normal=(1.0, 0.0, 0.0),
        ),
        "shared_top_face": _feature(
            "feature_shared_top_face",
            "top plate reference face",
            FeatureKind.FACE,
            _shape(
                "shape_shared_top_face",
                ShapeKind.FACE,
                "top plate reference face",
                ["Caster Assembly", "top_plate:1"],
                {"surface_type": "plane", "point": [0.0, 0.0, 12.0], "normal": [0.0, 0.0, 1.0]},
            ),
            "top_plate:1",
            point=(0.0, 0.0, 12.0),
            normal=(0.0, 0.0, 1.0),
        ),
    }
    index = GeometryIndex(
        document=document,
        shapes=[feature.shape_reference for feature in features.values()],
        features=list(features.values()),
    )
    session = InMemoryCadGeometrySession(index)
    project = CadToleranceProject(
        title="Caster workflow fixture",
        cad_documents=[document],
    )
    return {"session": session, "project": project, "features": features}


def _shape(
    shape_id: str,
    kind: ShapeKind,
    name: str,
    assembly_path: list[str],
    signature: dict[str, object],
) -> ShapeReference:
    return ShapeReference(
        id=shape_id,
        document_id="cad_doc_1",
        assembly_path=assembly_path,
        shape_type=kind,
        geometric_signature=signature,
        fallback_display_name=name,
    )


def _feature(
    feature_id: str,
    name: str,
    kind: FeatureKind,
    shape: ShapeReference,
    owner: str,
    point: tuple[float, float, float],
    normal: tuple[float, float, float] | None = None,
    axis: tuple[float, float, float] | None = None,
) -> FeatureReference:
    return FeatureReference(
        id=feature_id,
        name=name,
        feature_type=kind,
        shape_reference=shape,
        owner_part_id=owner,
        point=Vector3D(*point),
        normal=Vector3D(*normal) if normal else None,
        axis=Vector3D(*axis) if axis else None,
    )


def _selection(feature: FeatureReference) -> CadViewerSelection:
    return CadViewerSelection(
        shape_reference=feature.shape_reference,
        feature_reference=feature,
        mode=ViewerSelectionMode.FACE,
    )


if __name__ == "__main__":
    unittest.main()
