from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

if "QT_QPA_PLATFORM" not in os.environ and importlib.util.find_spec("OCC") is None:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

from mechanical_design_tool_suite.cad_geometry_occ import OccCadGeometrySession
from mechanical_design_tool_suite.cad_tolerance_models import ShapeKind, ShapeReference
from mechanical_design_tool_suite.cad_viewer_api import (
    CadViewerSelection,
    HighlightRole,
    SnapshotRequest,
    ViewerAnnotation,
    ViewerAnnotationRole,
    ViewerSelectionMode,
)
from mechanical_design_tool_suite.cad_viewer_occ import (
    OCC_VIEWER_DEPENDENCY_MESSAGE,
    OccCadViewerWidget,
    is_occ_viewer_available,
    is_pyqt5_available,
    occ_viewer_import_error,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "cad_1d_tolerance"
STEP_FIXTURE = FIXTURE_DIR / "neutral_step_two_part_loop.step"


class CadViewerApiTest(unittest.TestCase):
    def test_selection_payload_is_serializable_and_kernel_neutral(self) -> None:
        shape = ShapeReference(
            id="shape_body_1",
            document_id="cad_doc_1",
            assembly_path=["Fixture", "Body 1"],
            shape_type=ShapeKind.BODY,
            fallback_display_name="Body 1",
        )
        selection = CadViewerSelection(
            shape_reference=shape,
            mode=ViewerSelectionMode.BODY,
            role=HighlightRole.SELECTED_START,
            screen_position=(12, 34),
        )

        self.assertEqual(selection.shape_id, "shape_body_1")
        self.assertEqual(
            selection.to_dict(),
            {
                "shape_id": "shape_body_1",
                "shape_type": "body",
                "feature_id": "",
                "feature_type": None,
                "mode": "body",
                "role": "selected_start",
                "screen_position": [12, 34],
            },
        )
        self.assertEqual(ViewerSelectionMode.from_shape_kind(ShapeKind.FACE), ViewerSelectionMode.FACE)
        self.assertIsNone(ViewerSelectionMode.from_shape_kind(ShapeKind.PLANE))

    def test_snapshot_request_keeps_output_path_as_path(self) -> None:
        request = SnapshotRequest(Path("viewer.png"))

        self.assertEqual(request.output_path, Path("viewer.png"))
        self.assertEqual(request.visible_stackup_ids, ())
        self.assertEqual(request.annotation_positions, {})
        self.assertEqual(request.annotations, ())

    def test_viewer_annotation_is_serializable_snapshot_overlay(self) -> None:
        annotation = ViewerAnnotation(
            id="stackup_1:main",
            label="0.000",
            role=ViewerAnnotationRole.STACKUP,
            start=(0.4, 0.25),
            end=(0.4, 0.75),
            label_position=(0.48, 0.55),
            shape_ids=("shape_face_1",),
            feature_ids=("feature_face_1",),
        )
        request = SnapshotRequest(Path("viewer.png"), annotations=(annotation,))

        self.assertEqual(request.annotations, (annotation,))
        self.assertEqual(
            annotation.to_dict(),
            {
                "id": "stackup_1:main",
                "label": "0.000",
                "role": "stackup",
                "start": [0.4, 0.25],
                "end": [0.4, 0.75],
                "label_position": [0.48, 0.55],
                "leader_points": [],
                "shape_ids": ["shape_face_1"],
                "feature_ids": ["feature_face_1"],
                "draggable": True,
            },
        )
        self.assertEqual(str(HighlightRole.ELIGIBLE), "eligible")
        self.assertEqual(str(HighlightRole.CROSS_HIGHLIGHT), "cross_highlight")


class OccCadViewerRuntimeTest(unittest.TestCase):
    def setUp(self) -> None:
        if not is_occ_viewer_available():
            self.skipTest(
                f"{OCC_VIEWER_DEPENDENCY_MESSAGE} Exact error: {occ_viewer_import_error()}"
            )
        if not STEP_FIXTURE.exists():
            self.skipTest(f"STEP CAD fixture is not present: {STEP_FIXTURE}")

    def test_runtime_uses_pyqt6_backend_without_pyqt5(self) -> None:
        from OCC.Display.backend import get_loaded_backend

        self.assertEqual(get_loaded_backend(), "pyqt6")
        self.assertFalse(is_pyqt5_available())

    def test_step_fixture_displays_with_live_occ_shapes_and_snapshot(self) -> None:
        from PyQt6.QtGui import QImage
        from PyQt6.QtWidgets import QApplication

        if QApplication.instance() is not None:
            self.skipTest(
                "Run the OCCT qtViewer3d native-window smoke test in isolation; "
                "it can crash after another QApplication is created in discovery."
            )
        app = QApplication([])
        session = OccCadGeometrySession()
        session.import_file(STEP_FIXTURE)
        body_refs = session.shape_references({ShapeKind.BODY})
        face_refs = session.shape_references({ShapeKind.FACE})
        self.assertTrue(body_refs)
        self.assertTrue(face_refs)

        widget = OccCadViewerWidget()
        self.addCleanup(widget.close)
        widget.resize(640, 480)
        widget.show()
        app.processEvents()

        widget.display_document(session)
        app.processEvents()

        self.assertTrue(widget.displayed_shape_ids)
        self.assertEqual(set(widget.displayed_shape_ids), {shape.id for shape in body_refs})

        first_body = body_refs[0]
        self.assertIs(
            widget.shape_reference_for_kernel_shape(session.kernel_shape(first_body)),
            first_body,
        )

        widget.set_selection_modes({ViewerSelectionMode.BODY, ViewerSelectionMode.FACE})
        self.assertEqual(
            set(widget.active_selection_modes),
            {ViewerSelectionMode.BODY, ViewerSelectionMode.FACE},
        )
        widget.highlight(face_refs[0], HighlightRole.SELECTED_START)
        widget.clear_highlights()
        widget.set_annotations(
            (
                ViewerAnnotation(
                    id="runtime_stackup_annotation",
                    label="0.000",
                    role=ViewerAnnotationRole.STACKUP,
                ),
            )
        )
        widget.fit_all()
        widget.zoom(1.05)
        widget.pan(1, -1)
        camera = widget.camera_state().to_dict()
        self.assertIn("eye", camera)
        self.assertIn("scale", camera)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "cad_viewer_snapshot.png"
            snapshot = widget.capture_snapshot(
                SnapshotRequest(output_path, annotations=widget.annotations)
            )
            app.processEvents()

            self.assertEqual(Path(snapshot.image_path), output_path)
            self.assertTrue(output_path.exists())
            self.assertGreater(output_path.stat().st_size, 0)
            image = QImage(str(output_path))
            self.assertFalse(image.isNull())
            self.assertGreater(image.width(), 0)
            self.assertGreater(image.height(), 0)
            self.assertIn("_viewer_annotations", snapshot.annotation_positions)


@unittest.skipUnless(importlib.util.find_spec("PyQt6"), "PyQt6 is not installed.")
class ViewerOverlayHostTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from PyQt6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def test_viewport_host_captures_annotation_overlays(self) -> None:
        from PyQt6.QtGui import QImage
        from PyQt6.QtWidgets import QFrame, QLabel

        from mechanical_design_tool_suite.cad_tolerance_gui import CadViewportHost

        host = CadViewportHost(QFrame())
        self.addCleanup(host.close)
        host.resize(640, 480)
        annotation = ViewerAnnotation(
            id="stackup_1:main",
            label="0.000",
            role=ViewerAnnotationRole.STACKUP,
            start=(0.35, 0.25),
            end=(0.35, 0.76),
            label_position=(0.44, 0.54),
        )
        host.set_annotations((annotation,))
        host.show()
        self.app.processEvents()

        labels = host.findChildren(QLabel, "ViewerAnnotationLabel")
        self.assertEqual(len(labels), 1)
        self.assertEqual(labels[0].text(), "0.000")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "overlay_snapshot.png"
            snapshot = host.capture_snapshot(
                SnapshotRequest(output_path, annotations=host.annotations)
            )
            image = QImage(str(output_path))

        self.assertEqual(Path(snapshot.image_path), output_path)
        self.assertFalse(image.isNull())
        self.assertGreater(image.width(), 0)
        self.assertIn("_viewer_annotations", snapshot.annotation_positions)
        self.assertEqual(
            snapshot.annotation_positions["_viewer_annotations"][0]["role"],
            "stackup",
        )


if __name__ == "__main__":
    unittest.main()
