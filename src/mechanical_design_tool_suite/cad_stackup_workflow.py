"""Guided stackup workflow controller for CAD 1D tolerance authoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .cad_geometry_api import (
    CadGeometrySession,
    Measurement,
    feature_from_shape_reference,
    feature_point,
    normalize_vector,
    subtract_vectors,
)
from .cad_tolerance_models import (
    AnalysisMode,
    AnnotationPlane,
    CadToleranceProject,
    FeatureKind,
    FeatureReference,
    ShapeKind,
    ShapeReference,
    StackupContributor,
    StackupObjective,
    StackupRequirement,
    ToleranceType,
    Vector3D,
    new_id,
)
from .cad_viewer_api import CadViewerSelection, HighlightRole, ViewerSelectionMode


GUIDED_STACKUP_STEP_LABELS = (
    "Selection 1",
    "Width 1",
    "Selection 2",
    "Width 2",
    "Direction",
    "Analysis Plane",
    "Dimension Location",
)

GUIDED_TOOLBAR_CONTROL_LABELS = ("OK", "X", "+", "List")
DEFAULT_GENERATED_TOLERANCE = 0.10
DEFAULT_STACKUP_OBJECTIVE_TOLERANCE = 0.75


class GuidedStackupStep(str, Enum):
    SELECTION_1 = "selection_1"
    WIDTH_1 = "width_1"
    SELECTION_2 = "selection_2"
    WIDTH_2 = "width_2"
    DIRECTION = "direction"
    ANALYSIS_PLANE = "analysis_plane"
    DIMENSION_LOCATION = "dimension_location"
    LOOP_COMPONENTS = "loop_components"
    MATING_FACES = "mating_faces"
    COMPLETE = "complete"
    CANCELED = "canceled"

    @property
    def label(self) -> str:
        labels = {
            self.SELECTION_1: "Selection 1",
            self.WIDTH_1: "Width 1",
            self.SELECTION_2: "Selection 2",
            self.WIDTH_2: "Width 2",
            self.DIRECTION: "Direction",
            self.ANALYSIS_PLANE: "Analysis Plane",
            self.DIMENSION_LOCATION: "Dimension Location",
            self.LOOP_COMPONENTS: "Dimension Location",
            self.MATING_FACES: "Dimension Location",
            self.COMPLETE: "Dimension Location",
            self.CANCELED: "Selection 1",
        }
        return labels[self]


@dataclass(frozen=True)
class StackupSelectionFilter:
    """Current B-Rep-backed pick request for the viewer and geometry adapter."""

    prompt: str
    shape_kinds: tuple[ShapeKind, ...] = ()
    feature_kinds: tuple[FeatureKind, ...] = ()
    viewer_modes: tuple[ViewerSelectionMode, ...] = ()
    role: HighlightRole | None = None
    expected_owner_part_id: str = ""
    requires_direction_alignment: bool = False

    @property
    def shape_kind_set(self) -> set[ShapeKind]:
        return set(self.shape_kinds)

    @property
    def viewer_mode_set(self) -> set[ViewerSelectionMode]:
        return set(self.viewer_modes)


@dataclass(frozen=True)
class GuidedToolbarState:
    step_labels: tuple[str, ...] = GUIDED_STACKUP_STEP_LABELS
    active_label: str = "Selection 1"
    prompt: str = "Select a face, edge or vertex"
    component_count_text: str = "0 Components"
    mating_face_count_text: str = "0 of 0 Mating Faces"
    control_labels: tuple[str, ...] = GUIDED_TOOLBAR_CONTROL_LABELS
    check_enabled: bool = True
    cancel_enabled: bool = True
    add_enabled: bool = False
    list_enabled: bool = True


@dataclass(frozen=True)
class WorkflowHighlightRequest:
    shape_reference: ShapeReference
    role: HighlightRole


@dataclass(frozen=True)
class StackupWorkflowUpdate:
    toolbar: GuidedToolbarState
    selection_filter: StackupSelectionFilter
    highlights: tuple[WorkflowHighlightRequest, ...] = ()
    generated_contributors: tuple[StackupContributor, ...] = ()
    stackup: StackupRequirement | None = None


@dataclass
class StackupWorkflowState:
    name: str = "Stackup1"
    active_step: GuidedStackupStep = GuidedStackupStep.SELECTION_1
    start_feature: FeatureReference | None = None
    end_feature: FeatureReference | None = None
    first_width_feature: FeatureReference | None = None
    second_width_feature: FeatureReference | None = None
    direction_feature: FeatureReference | None = None
    direction: Vector3D | None = None
    analysis_plane_feature: FeatureReference | None = None
    annotation_plane: AnnotationPlane | None = None
    annotation_position: dict[str, Any] = field(default_factory=dict)
    loop_features: list[FeatureReference] = field(default_factory=list)
    constraint_features: list[FeatureReference] = field(default_factory=list)
    inserted_features: list[FeatureReference] = field(default_factory=list)
    generated_contributors: list[StackupContributor] = field(default_factory=list)
    mating_face_goal: int = 0


class GuidedStackupWorkflowController:
    """State machine for EZtol-style guided stackup creation.

    The controller intentionally consumes and returns only serializable domain
    references. It does not discover a production loop; contributors are created
    deterministically from the features selected by the user or tests.
    """

    def __init__(
        self,
        geometry_session: CadGeometrySession,
        project: CadToleranceProject | None = None,
    ) -> None:
        self.geometry_session = geometry_session
        self.project = project
        self.state = StackupWorkflowState()

    def start_new_stackup(self, name: str | None = None) -> StackupWorkflowUpdate:
        self.state = StackupWorkflowState(name=name or self._next_stackup_name())
        return self.current_update()

    def current_update(
        self,
        highlights: tuple[WorkflowHighlightRequest, ...] = (),
        stackup: StackupRequirement | None = None,
    ) -> StackupWorkflowUpdate:
        return StackupWorkflowUpdate(
            toolbar=self._toolbar_state(),
            selection_filter=self._selection_filter(),
            highlights=highlights,
            generated_contributors=tuple(self.state.generated_contributors),
            stackup=stackup,
        )

    def apply_selection(self, selection: CadViewerSelection) -> StackupWorkflowUpdate:
        feature = self._feature_from_selection(selection)
        self._validate_selection(feature)
        step = self.state.active_step

        if step == GuidedStackupStep.SELECTION_1:
            self.state.start_feature = feature
            self.state.first_width_feature = feature
            self.state.active_step = GuidedStackupStep.WIDTH_1
            return self.current_update((_highlight(feature, HighlightRole.SELECTED_START),))

        if step == GuidedStackupStep.WIDTH_1:
            self.state.first_width_feature = feature
            return self.current_update((_highlight(feature, HighlightRole.SELECTED_START),))

        if step == GuidedStackupStep.SELECTION_2:
            self.state.end_feature = feature
            self.state.second_width_feature = feature
            self.state.active_step = GuidedStackupStep.WIDTH_2
            return self.current_update((_highlight(feature, HighlightRole.SELECTED_END),))

        if step == GuidedStackupStep.WIDTH_2:
            self.state.second_width_feature = feature
            return self.current_update((_highlight(feature, HighlightRole.SELECTED_END),))

        if step == GuidedStackupStep.DIRECTION:
            self.state.direction_feature = feature
            self.state.direction = self._direction_from_feature(feature)
            self.state.active_step = GuidedStackupStep.ANALYSIS_PLANE
            return self.current_update((_highlight(feature, HighlightRole.DIRECTION),))

        if step == GuidedStackupStep.ANALYSIS_PLANE:
            self.state.analysis_plane_feature = feature
            self.state.annotation_plane = self._annotation_plane_from_feature(feature)
            self.state.active_step = GuidedStackupStep.DIMENSION_LOCATION
            return self.current_update((_highlight(feature, HighlightRole.ANALYSIS_PLANE),))

        if step == GuidedStackupStep.LOOP_COMPONENTS:
            self.state.loop_features.append(feature)
            return self.current_update((_highlight(feature, HighlightRole.LOOP_MEMBER),))

        if step == GuidedStackupStep.MATING_FACES:
            self.state.constraint_features.append(feature)
            return self.current_update((_highlight(feature, HighlightRole.LOOP_MEMBER),))

        raise ValueError(f"Workflow step {step.value!r} does not accept geometry selections.")

    def confirm_current_step(self) -> StackupWorkflowUpdate:
        step = self.state.active_step
        if step == GuidedStackupStep.WIDTH_1:
            self.state.active_step = GuidedStackupStep.SELECTION_2
        elif step == GuidedStackupStep.WIDTH_2:
            self.state.active_step = (
                GuidedStackupStep.DIRECTION
                if self._requires_direction_pick()
                else GuidedStackupStep.ANALYSIS_PLANE
            )
            if self.state.active_step == GuidedStackupStep.ANALYSIS_PLANE:
                self.state.direction = self._direction_from_endpoints()
        elif step == GuidedStackupStep.DIMENSION_LOCATION:
            self.state.active_step = GuidedStackupStep.LOOP_COMPONENTS
        elif step == GuidedStackupStep.LOOP_COMPONENTS:
            self.state.active_step = GuidedStackupStep.MATING_FACES
        elif step == GuidedStackupStep.MATING_FACES:
            return self.finish()
        return self.current_update()

    def cancel(self) -> StackupWorkflowUpdate:
        self.state.active_step = GuidedStackupStep.CANCELED
        return self.current_update()

    def set_annotation_position(self, position: dict[str, Any]) -> StackupWorkflowUpdate:
        if self.state.active_step != GuidedStackupStep.DIMENSION_LOCATION:
            raise ValueError("Annotation position can only be set during Dimension Location.")
        self.state.annotation_position = dict(position)
        self.state.active_step = GuidedStackupStep.LOOP_COMPONENTS
        return self.current_update()

    def set_mating_face_goal(self, total: int) -> StackupWorkflowUpdate:
        self.state.mating_face_goal = max(0, int(total))
        return self.current_update()

    def insert_intermediate_feature(
        self,
        selection: CadViewerSelection,
        name: str | None = None,
    ) -> StackupWorkflowUpdate:
        feature = self._feature_from_selection(selection)
        if name:
            feature.name = name
        self.state.inserted_features.append(feature)
        self.state.generated_contributors = self._build_contributors()
        return self.current_update((_highlight(feature, HighlightRole.LOOP_MEMBER),))

    def finish(self) -> StackupWorkflowUpdate:
        self._require_ready_to_finish()
        self.state.generated_contributors = self._build_contributors()
        stackup = StackupRequirement(
            id=new_id("stackup"),
            name=self.state.name,
            contributors=list(self.state.generated_contributors),
            objective=StackupObjective.bilateral(
                nominal=0.0,
                tolerance=DEFAULT_STACKUP_OBJECTIVE_TOLERANCE,
            ),
            analysis_mode=AnalysisMode.WORST_CASE,
            start_feature=self.state.start_feature,
            end_feature=self.state.end_feature,
            direction=self._workflow_direction(),
            annotation_plane=self.state.annotation_plane or AnnotationPlane(),
            loop_features=list(self.state.loop_features),
            constraint_features=list(self.state.constraint_features),
            annotation_position=dict(self.state.annotation_position),
        )
        self.state.active_step = GuidedStackupStep.COMPLETE
        if self.project is not None:
            self.project.stackups.append(stackup)
        return self.current_update(stackup=stackup)

    def _next_stackup_name(self) -> str:
        existing = len(self.project.stackups) if self.project is not None else 0
        return f"Stackup{existing + 1}"

    def _selection_filter(self) -> StackupSelectionFilter:
        step = self.state.active_step
        endpoint_shapes = (ShapeKind.FACE, ShapeKind.EDGE, ShapeKind.VERTEX)
        endpoint_features = (
            FeatureKind.FACE,
            FeatureKind.EDGE,
            FeatureKind.VERTEX,
            FeatureKind.AXIS,
            FeatureKind.PLANE,
            FeatureKind.CYLINDER,
        )
        endpoint_modes = _viewer_modes_for(endpoint_shapes)
        if step in {GuidedStackupStep.SELECTION_1, GuidedStackupStep.WIDTH_1}:
            return StackupSelectionFilter(
                "Select a face, edge or vertex",
                endpoint_shapes,
                endpoint_features,
                endpoint_modes,
                HighlightRole.SELECTED_START,
            )
        if step in {GuidedStackupStep.SELECTION_2, GuidedStackupStep.WIDTH_2}:
            return StackupSelectionFilter(
                "Select a face, edge or vertex",
                endpoint_shapes,
                endpoint_features,
                endpoint_modes,
                HighlightRole.SELECTED_END,
            )
        if step == GuidedStackupStep.DIRECTION:
            return StackupSelectionFilter(
                "Select a direction reference",
                endpoint_shapes,
                endpoint_features,
                endpoint_modes,
                HighlightRole.DIRECTION,
            )
        if step == GuidedStackupStep.ANALYSIS_PLANE:
            return StackupSelectionFilter(
                "Select a work plane or planar face",
                (ShapeKind.FACE, ShapeKind.PLANE),
                (FeatureKind.FACE, FeatureKind.PLANE),
                _viewer_modes_for((ShapeKind.FACE,)),
                HighlightRole.ANALYSIS_PLANE,
            )
        if step == GuidedStackupStep.DIMENSION_LOCATION:
            return StackupSelectionFilter(
                "Drag the nominal dimension label to the desired location",
                (),
                (),
                (),
                None,
            )
        if step == GuidedStackupStep.LOOP_COMPONENTS:
            return StackupSelectionFilter(
                "Select the component that mates with the active part",
                (ShapeKind.BODY, ShapeKind.FACE, ShapeKind.EDGE, ShapeKind.VERTEX),
                (*endpoint_features, FeatureKind.UNKNOWN),
                _viewer_modes_for((ShapeKind.BODY, ShapeKind.FACE, ShapeKind.EDGE, ShapeKind.VERTEX)),
                HighlightRole.LOOP_MEMBER,
                requires_direction_alignment=True,
            )
        if step == GuidedStackupStep.MATING_FACES:
            expected_owner = self.state.loop_features[-1].owner_part_id if self.state.loop_features else ""
            expected_name = expected_owner or "the mating component"
            return StackupSelectionFilter(
                f"Select a face, edge or vertex from {expected_name} that mates with the next component",
                endpoint_shapes,
                endpoint_features,
                endpoint_modes,
                HighlightRole.LOOP_MEMBER,
                expected_owner_part_id=expected_owner,
                requires_direction_alignment=True,
            )
        return StackupSelectionFilter("Workflow complete")

    def _toolbar_state(self) -> GuidedToolbarState:
        components = len(self.state.loop_features)
        mating_faces = len(self.state.constraint_features)
        mating_goal = self.state.mating_face_goal
        return GuidedToolbarState(
            active_label=self.state.active_step.label,
            prompt=self._selection_filter().prompt,
            component_count_text=f"{components} Component" + ("" if components == 1 else "s"),
            mating_face_count_text=f"{mating_faces} of {mating_goal} Mating Faces",
            add_enabled=self.state.active_step
            in {
                GuidedStackupStep.LOOP_COMPONENTS,
                GuidedStackupStep.MATING_FACES,
                GuidedStackupStep.COMPLETE,
            },
        )

    def _feature_from_selection(self, selection: CadViewerSelection) -> FeatureReference:
        feature = selection.feature_reference
        if feature is None:
            feature = feature_from_shape_reference(selection.shape_reference)
        if feature.shape_reference is None:
            feature.shape_reference = selection.shape_reference
        return feature

    def _validate_selection(self, feature: FeatureReference) -> None:
        selection_filter = self._selection_filter()
        shape = feature.shape_reference
        if shape is not None and selection_filter.shape_kinds and shape.shape_type not in selection_filter.shape_kinds:
            raise ValueError(f"Current step does not accept {shape.shape_type.value} selections.")
        if selection_filter.feature_kinds and feature.feature_type not in selection_filter.feature_kinds:
            raise ValueError(f"Current step does not accept {feature.feature_type.value} features.")
        expected_owner = selection_filter.expected_owner_part_id
        if expected_owner and feature.owner_part_id and feature.owner_part_id != expected_owner:
            raise ValueError(f"Expected a selection from {expected_owner}.")

    def _requires_direction_pick(self) -> bool:
        start = self.state.start_feature
        end = self.state.end_feature
        if start is None or end is None:
            return True
        ambiguous = {FeatureKind.CYLINDER, FeatureKind.AXIS, FeatureKind.EDGE}
        return start.feature_type in ambiguous or end.feature_type in ambiguous

    def _direction_from_feature(self, feature: FeatureReference) -> Vector3D:
        if feature.normal is not None:
            return normalize_vector(feature.normal)
        if feature.axis is not None:
            return normalize_vector(feature.axis)
        return self._direction_from_endpoints()

    def _direction_from_endpoints(self) -> Vector3D:
        start = self.state.start_feature
        end = self.state.end_feature
        if start is None or end is None:
            return Vector3D(1.0, 0.0, 0.0)
        start_point = feature_point(start)
        end_point = feature_point(end)
        if start_point is not None and end_point is not None:
            try:
                return normalize_vector(subtract_vectors(end_point, start_point))
            except ValueError:
                pass
        try:
            return normalize_vector(self.geometry_session.measure_between(start, end, (1.0, 0.0, 0.0)).direction)
        except Exception:
            return Vector3D(1.0, 0.0, 0.0)

    def _workflow_direction(self) -> Vector3D:
        return self.state.direction or self._direction_from_endpoints()

    def _annotation_plane_from_feature(self, feature: FeatureReference) -> AnnotationPlane:
        origin = feature.point or Vector3D()
        normal = feature.normal or feature.axis or Vector3D(0.0, 0.0, 1.0)
        return AnnotationPlane(
            origin=origin,
            normal=normalize_vector(normal),
            source_feature_id=feature.id,
            display_name=feature.name or _shape_name(feature.shape_reference) or "Analysis Plane",
        )

    def _build_contributors(self) -> list[StackupContributor]:
        selected = [
            *self.state.loop_features,
            *self.state.constraint_features,
            *self.state.inserted_features,
        ]
        if not selected and self.state.end_feature is not None:
            selected = [self.state.end_feature]

        contributors: list[StackupContributor] = []
        previous = self.state.start_feature
        inserted_feature_ids = {feature.id for feature in self.state.inserted_features}
        for index, feature in enumerate(selected, start=1):
            measurement = self._measure(previous, feature)
            nominal = measurement.value if measurement is not None else 0.0
            sensitivity = 1.0 if nominal >= 0.0 else -1.0
            source_note = (
                "Manually inserted intermediate feature."
                if feature.id in inserted_feature_ids
                else "Generated from guided stackup selection."
            )
            contributors.append(
                StackupContributor(
                    id=new_id("contrib"),
                    name=f"Dimension{index}",
                    nominal=abs(nominal),
                    tolerance=DEFAULT_GENERATED_TOLERANCE,
                    sensitivity=sensitivity,
                    tolerance_type=ToleranceType.SYMMETRIC,
                    source_feature=feature,
                    shared_with_stackup_ids=self._shared_stackup_ids_for(feature),
                    source_note=source_note,
                )
            )
            previous = feature
        return contributors

    def _measure(
        self,
        previous: FeatureReference | None,
        feature: FeatureReference,
    ) -> Measurement | None:
        if previous is None:
            return None
        try:
            return self.geometry_session.measure_between(previous, feature, self._workflow_direction())
        except Exception:
            return None

    def _shared_stackup_ids_for(self, feature: FeatureReference) -> list[str]:
        if self.project is None:
            return []
        feature_ids = {feature.id}
        if feature.shape_reference is not None:
            feature_ids.add(feature.shape_reference.id)
        shared: list[str] = []
        for stackup in self.project.stackups:
            for contributor in stackup.contributors:
                source = contributor.source_feature
                if source is None:
                    continue
                source_ids = {source.id}
                if source.shape_reference is not None:
                    source_ids.add(source.shape_reference.id)
                if feature_ids & source_ids:
                    shared.append(stackup.id)
                    break
        return shared

    def _require_ready_to_finish(self) -> None:
        if self.state.start_feature is None:
            raise ValueError("Start feature has not been selected.")
        if self.state.end_feature is None:
            raise ValueError("End feature has not been selected.")


def _viewer_modes_for(shape_kinds: tuple[ShapeKind, ...]) -> tuple[ViewerSelectionMode, ...]:
    modes = []
    for kind in shape_kinds:
        mode = ViewerSelectionMode.from_shape_kind(kind)
        if mode is not None and mode not in modes:
            modes.append(mode)
    return tuple(modes)


def _highlight(feature: FeatureReference, role: HighlightRole) -> WorkflowHighlightRequest:
    if feature.shape_reference is None:
        raise ValueError("Selected feature does not carry a ShapeReference for highlighting.")
    return WorkflowHighlightRequest(feature.shape_reference, role)


def _shape_name(shape: ShapeReference | None) -> str:
    return shape.fallback_display_name if shape is not None else ""
