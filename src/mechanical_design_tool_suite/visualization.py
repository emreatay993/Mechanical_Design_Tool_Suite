"""PyVista visualization for node-based bolt results."""

from __future__ import annotations

from math import isfinite
from typing import Any, Iterable, Sequence

from .calculations import BoltCalculationResult


VISUALIZATION_CMAP = "jet"
HOVER_TEXT_POSITION = 2


SCALAR_CHOICES = {
    "FX": lambda result: result.load.fx_n,
    "FY": lambda result: result.load.fy_n,
    "FZ": lambda result: result.load.fz_n,
    "Shear": lambda result: result.interaction.shear_n,
    "Bending": lambda result: result.interaction.bending_nmm,
    "Fiber Stress": lambda result: result.strength.fiber_mpa,
    "LCF sigma_alt": lambda result: result.strength.lcf_alt_mpa,
    "Interaction Ratio": lambda result: result.interaction.interaction_ratio,
    "Margin": lambda result: result.interaction.margin,
}


def scalar_values_for_results(
    results: list[BoltCalculationResult],
    scalar_name: str,
) -> list[float]:
    """Return plotted scalar values for the current result set."""
    if scalar_name not in SCALAR_CHOICES:
        choices = ", ".join(SCALAR_CHOICES)
        raise ValueError(f"Unknown scalar {scalar_name!r}. Choices: {choices}")
    return [float(SCALAR_CHOICES[scalar_name](result)) for result in results]


def local_scalar_range(values: Iterable[float]) -> tuple[float, float]:
    """Return a scalar range based only on finite values being plotted."""
    finite_values = [value for value in values if isfinite(value)]
    if not finite_values:
        raise ValueError("Cannot visualize a scalar with no finite values.")

    minimum = min(finite_values)
    maximum = max(finite_values)
    if minimum == maximum:
        padding = max(abs(minimum) * 1.0e-6, 1.0e-12)
        return minimum - padding, maximum + padding
    return minimum, maximum


def format_contour_value(value: float) -> str:
    """Format a contour value for compact hover display."""
    return f"{value:.6g}"


def format_hover_text(node_name: str, scalar_name: str, value: float) -> str:
    """Return the upper-left hover overlay text for a picked bolt node."""
    return f"{node_name}\n{scalar_name}: {format_contour_value(value)}"


def hover_prompt_text(scalar_name: str) -> str:
    """Return the idle upper-left hover overlay text."""
    return f"Hover over a bolt node\n{scalar_name}: -"


def results_have_coordinates(results: Iterable[BoltCalculationResult]) -> bool:
    return all(
        result.load.x_mm is not None
        and result.load.y_mm is not None
        and result.load.z_mm is not None
        for result in results
    )


def open_pyvista_plot(
    results: list[BoltCalculationResult],
    scalar_name: str,
) -> None:
    """Open a PyVista point-cloud window for the selected scalar."""
    if not results:
        raise ValueError("Calculate results before opening visualization.")
    if not results_have_coordinates(results):
        raise ValueError("All rows need X, Y, and Z coordinates for visualization.")
    selected_values = scalar_values_for_results(results, scalar_name)
    scalar_range = local_scalar_range(selected_values)

    try:
        import pyvista as pv
    except ImportError as exc:
        raise RuntimeError(
            "PyVista is not installed in this Python environment. Install pyvista "
            "to use the 3D node contour window."
        ) from exc

    points = [
        (result.load.x_mm, result.load.y_mm, result.load.z_mm)
        for result in results
    ]
    cloud = pv.PolyData(points)
    for name, getter in SCALAR_CHOICES.items():
        cloud[name] = [getter(result) for result in results]

    plotter = pv.Plotter(title=f"Bolt nodes - {scalar_name}")
    node_actor = plotter.add_mesh(
        cloud,
        scalars=scalar_name,
        render_points_as_spheres=True,
        point_size=22,
        cmap=VISUALIZATION_CMAP,
        clim=scalar_range,
        scalar_bar_args={
            "title": scalar_name,
            "n_labels": 5,
            "fmt": "%.3g",
        },
    )
    plotter.add_point_labels(points, [result.load.name for result in results], font_size=11)
    _install_hover_overlay(
        plotter=plotter,
        node_actor=node_actor,
        node_names=[result.load.name for result in results],
        scalar_name=scalar_name,
        scalar_values=selected_values,
    )
    plotter.add_axes()
    plotter.show_grid()
    plotter.show()


def _install_hover_overlay(
    plotter: Any,
    node_actor: Any,
    node_names: Sequence[str],
    scalar_name: str,
    scalar_values: Sequence[float],
) -> None:
    """Install mouse hover text for bolt nodes in the upper-left plot corner."""
    from vtkmodules.vtkRenderingCore import vtkPointPicker

    hover_actor = plotter.add_text(
        hover_prompt_text(scalar_name),
        position="upper_left",
        font_size=12,
        color="black",
        name="bolt_hover_info",
    )
    picker = vtkPointPicker()
    picker.SetTolerance(0.025)
    picker.PickFromListOn()
    picker.AddPickList(node_actor)

    def set_hover_text(text: str) -> None:
        if hover_actor.get_text(HOVER_TEXT_POSITION) == text:
            return
        hover_actor.set_text(HOVER_TEXT_POSITION, text)
        plotter.render()

    def on_mouse_move(_interactor: Any, _event: str) -> None:
        event_position = plotter.iren.interactor.GetEventPosition()
        picker.Pick(event_position[0], event_position[1], 0, plotter.renderer)
        point_id = picker.GetPointId()
        if 0 <= point_id < len(node_names):
            set_hover_text(
                format_hover_text(
                    node_names[point_id],
                    scalar_name,
                    scalar_values[point_id],
                )
            )
            return
        set_hover_text(hover_prompt_text(scalar_name))

    plotter.iren.interactor.AddObserver("MouseMoveEvent", on_mouse_move)

    # Keep VTK callback objects alive for the life of the plotter.
    plotter._bolt_hover_actor = hover_actor
    plotter._bolt_hover_picker = picker
    plotter._bolt_hover_callback = on_mouse_move
