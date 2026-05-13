from __future__ import annotations

import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pyvista as pv
from PyQt6.QtWidgets import QApplication

from mechanical_design_tool_suite.bolt_reference_scene import (
    BOLT_NODE_SIZE_DEFAULT,
    BOLT_NODE_SIZE_MAX,
    BOLT_NODE_SIZE_MIN,
    BOLT_NODE_SIZE_STEP,
    BoltReferenceSceneWidget,
)
from mechanical_design_tool_suite.calculations import calculate_bolt_group, resolve_constants
from mechanical_design_tool_suite.reference_geometry import (
    ReferenceMeshAsset,
    ReferencePart,
    ReferenceGeometryFormat,
)
from mechanical_design_tool_suite.sample_data import example_scenario_loads
from mechanical_design_tool_suite.visualization import format_hover_text, hover_prompt_text


class BoltReferenceSceneWidgetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.widget = BoltReferenceSceneWidget()

    def tearDown(self) -> None:
        self.widget.close()
        self.app.processEvents()

    def test_reference_part_api_updates_state_without_plotter_requirement(self) -> None:
        part = ReferencePart(
            id="ref_1",
            name="Bracket",
            source_path="bracket.stl",
            file_format=ReferenceGeometryFormat.STL,
            mesh_count=1,
        )
        asset = ReferenceMeshAsset(
            part_id=part.id,
            name="Bracket",
            mesh=pv.Plane(i_size=10.0, j_size=5.0),
        )

        self.widget.add_reference_part(part, [asset])
        self.widget.select_reference_parts([part.id])
        self.widget.set_reference_visibility(part.id, False)
        self.widget.set_reference_opacity(part.id, 1.4)
        self.widget.rename_reference_part(part.id, "Renamed bracket")

        self.assertEqual(self.widget.reference_part_ids, ("ref_1",))
        self.assertEqual(self.widget.selected_reference_part_ids, ("ref_1",))
        self.assertFalse(part.display_state.visible)
        self.assertEqual(part.display_state.opacity, 1.0)
        self.assertEqual(part.name, "Renamed bracket")

        self.widget.remove_reference_part(part.id)
        self.assertEqual(self.widget.reference_part_ids, ())

    def test_set_results_accepts_bolt_coordinates_and_scalar_changes(self) -> None:
        results = calculate_bolt_group(
            example_scenario_loads(),
            resolve_constants(".2500-28", "MINOR"),
        )

        self.widget.set_results(results, "Margin")
        self.assertTrue(self.widget.last_draw_reset_camera)
        self.widget.set_results(results, "Fiber Stress")
        self.assertFalse(self.widget.last_draw_reset_camera)
        self.widget.clear_results()

        self.assertEqual(self.widget.reference_part_ids, ())

    def test_explicit_camera_reset_override_is_available(self) -> None:
        results = calculate_bolt_group(
            example_scenario_loads(),
            resolve_constants(".2500-28", "MINOR"),
        )

        self.widget.set_results(results, "Margin", reset_camera=False)
        self.assertFalse(self.widget.last_draw_reset_camera)

        self.widget.set_results(results, "Fiber Stress", reset_camera=True)
        self.assertTrue(self.widget.last_draw_reset_camera)

    def test_bolt_node_size_is_adjustable_and_clamped_without_camera_reset(self) -> None:
        results = calculate_bolt_group(
            example_scenario_loads(),
            resolve_constants(".2500-28", "MINOR"),
        )
        self.widget.set_results(results, "Margin")

        self.widget.set_bolt_node_size(BOLT_NODE_SIZE_DEFAULT + BOLT_NODE_SIZE_STEP)
        self.assertEqual(
            self.widget.bolt_node_size,
            BOLT_NODE_SIZE_DEFAULT + BOLT_NODE_SIZE_STEP,
        )
        self.assertFalse(self.widget.last_draw_reset_camera)

        self.widget.adjust_bolt_node_size(10_000)
        self.assertEqual(self.widget.bolt_node_size, BOLT_NODE_SIZE_MAX)
        self.widget.adjust_bolt_node_size(-10_000)
        self.assertEqual(self.widget.bolt_node_size, BOLT_NODE_SIZE_MIN)

    def test_embedded_hover_overlay_shows_current_bolt_scalar_and_cleans_up(self) -> None:
        captured: dict[str, object] = {}

        class FakeInteractor:
            def __init__(self) -> None:
                self.observers: dict[int, object] = {}
                self.removed: list[int] = []

            def AddObserver(self, event_name: str, callback: object) -> int:
                captured["observer_event"] = event_name
                self.observers[42] = callback
                return 42

            def RemoveObserver(self, observer_id: int) -> None:
                self.removed.append(observer_id)
                captured["removed_observer"] = observer_id

            def GetEventPosition(self) -> tuple[int, int]:
                return (12, 34)

        class FakeIren:
            def __init__(self) -> None:
                self.interactor = FakeInteractor()

        class FakeHoverActor:
            def __init__(self, text: str) -> None:
                self.text = {2: text}

            def get_text(self, position: int) -> str:
                return self.text[position]

            def set_text(self, position: int, text: str) -> None:
                self.text[position] = text
                captured["hover_text"] = text

        class FakePlotter:
            def __init__(self) -> None:
                self.iren = FakeIren()
                self.renderer = object()
                self.removed_actors: list[object] = []

            def add_text(self, text: str, **kwargs: object) -> FakeHoverActor:
                captured["initial_text"] = text
                captured["text_kwargs"] = kwargs
                return FakeHoverActor(text)

            def remove_actor(self, actor: object, render: bool = False) -> None:
                self.removed_actors.append(actor)
                captured["removed_actor"] = actor
                captured["removed_render"] = render

            def render(self) -> None:
                captured["rendered"] = True

        fake_picker = mock.Mock()
        fake_picker.GetPointId.return_value = 0
        fake_picker_class = mock.Mock(return_value=fake_picker)
        fake_plotter = FakePlotter()
        self.widget._plotter = fake_plotter
        self.widget._scalar_name = "Margin"

        with mock.patch(
            "vtkmodules.vtkRenderingCore.vtkPointPicker",
            fake_picker_class,
        ):
            self.widget._install_hover_overlay(
                node_actor="node_actor",
                node_names=["BOLT01"],
                scalar_values=[0.123456],
            )

        self.assertEqual(captured["initial_text"], hover_prompt_text("Margin"))
        self.assertEqual(captured["text_kwargs"]["position"], "upper_left")
        self.assertEqual(captured["observer_event"], "MouseMoveEvent")
        fake_picker.AddPickList.assert_called_once_with("node_actor")

        callback = fake_plotter.iren.interactor.observers[42]
        callback(None, "MouseMoveEvent")
        self.assertEqual(
            captured["hover_text"],
            format_hover_text("BOLT01", "Margin", 0.123456),
        )
        fake_picker.Pick.assert_called_once_with(12, 34, 0, fake_plotter.renderer)

        hover_actor = self.widget._hover_actor
        self.widget._clear_hover_overlay()
        self.assertEqual(captured["removed_observer"], 42)
        self.assertIs(captured["removed_actor"], hover_actor)
        self.assertFalse(captured["removed_render"])
        self.assertIsNone(self.widget._hover_actor)

    def test_scalar_legend_is_left_vertical_and_scales_with_window_size(self) -> None:
        self.widget.resize(420, 300)
        small_args = self.widget._scalar_bar_args("Margin")
        small_label_size = self.widget._point_label_font_size()

        self.widget.resize(1400, 950)
        large_args = self.widget._scalar_bar_args("Margin")
        large_label_size = self.widget._point_label_font_size()

        self.assertTrue(small_args["vertical"])
        self.assertEqual(small_args["position_x"], 0.02)
        self.assertLess(small_args["position_x"], 0.1)
        self.assertEqual(small_args["height"], 0.72)
        self.assertGreater(large_args["title_font_size"], small_args["title_font_size"])
        self.assertGreaterEqual(
            large_args["label_font_size"],
            small_args["label_font_size"],
        )
        self.assertGreaterEqual(large_label_size, small_label_size)

    def test_axis_visibility_state_can_be_toggled_per_axis(self) -> None:
        self.widget.set_axis_visibility("x", False)
        self.widget.set_axis_visibility("z", False)

        self.assertFalse(self.widget.axis_visibility["x"])
        self.assertTrue(self.widget.axis_visibility["y"])
        self.assertFalse(self.widget.axis_visibility["z"])
        with self.assertRaises(ValueError):
            self.widget.set_axis_visibility("roll", True)

    def test_axis_label_fonts_scale_with_window_size(self) -> None:
        self.widget.resize(360, 260)
        small_sizes = self.widget.axis_font_sizes

        self.widget.resize(1500, 980)
        large_sizes = self.widget.axis_font_sizes

        self.assertGreater(large_sizes["title"], small_sizes["title"])
        self.assertGreater(large_sizes["label"], small_sizes["label"])


if __name__ == "__main__":
    unittest.main()
