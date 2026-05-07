"""PyVista visualization for node-based bolt results."""

from __future__ import annotations

from math import isfinite
from typing import Iterable

from .calculations import BoltCalculationResult


VISUALIZATION_CMAP = "jet"


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
    plotter.add_mesh(
        cloud,
        scalars=scalar_name,
        render_points_as_spheres=True,
        point_size=22,
        cmap=VISUALIZATION_CMAP,
        clim=scalar_range,
        show_scalar_bar=False,
    )
    plotter.add_point_labels(points, [result.load.name for result in results], font_size=11)
    plotter.add_axes()
    plotter.show_grid()
    plotter.add_scalar_bar(title=scalar_name, n_labels=5)
    plotter.show()
