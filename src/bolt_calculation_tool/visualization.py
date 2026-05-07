"""Optional PyVista visualization for node-based bolt results."""

from __future__ import annotations

from typing import Iterable

from .calculations import BoltCalculationResult


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
    if scalar_name not in SCALAR_CHOICES:
        choices = ", ".join(SCALAR_CHOICES)
        raise ValueError(f"Unknown scalar {scalar_name!r}. Choices: {choices}")

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
        cmap="viridis",
    )
    plotter.add_point_labels(points, [result.load.name for result in results], font_size=11)
    plotter.add_axes()
    plotter.show_grid()
    plotter.add_scalar_bar(title=scalar_name)
    plotter.show()
