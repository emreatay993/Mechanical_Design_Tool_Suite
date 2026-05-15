"""Automated live-runtime smoke harness for the CAD 1D tolerance GUI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any

from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication

from mechanical_design_tool_suite.cad_tolerance_gui import create_cad_tolerance_window
from mechanical_design_tool_suite.cad_tolerance_project_io import PACKAGE_SUFFIX
from mechanical_design_tool_suite.cad_viewer_api import SnapshotRequest


NEUTRAL_CAD_SUFFIXES = {".step", ".stp", ".iges", ".igs"}
PROJECT_SUFFIX = ".tolproj"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("startup_path", type=Path, help="STEP, IGES, .tolproj, or .tolpack path.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for screenshots and any unpacked .tolpack contents.",
    )
    parser.add_argument(
        "--prefix",
        default="cad_1d_runtime_smoke",
        help="Filename prefix for generated evidence.",
    )
    parser.add_argument(
        "--settle-ms",
        type=int,
        default=1500,
        help="Delay after load before capture, in milliseconds.",
    )
    args = parser.parse_args(argv)

    startup_path = args.startup_path.resolve()
    if not startup_path.exists():
        raise FileNotFoundError(startup_path)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    app = QApplication.instance() or QApplication(sys.argv)
    window = create_cad_tolerance_window(app)
    window.resize(1500, 900)
    window.show()
    _settle(app, 250)

    load_kind = _load_startup_path(window, startup_path)
    _settle(app, max(args.settle_ms, 0))

    viewport_path = output_dir / f"{args.prefix}_viewport.png"
    full_window_path = output_dir / f"{args.prefix}_full_window.png"
    snapshot = window.viewport_host.capture_snapshot(
        SnapshotRequest(viewport_path, annotations=window.viewport_host.annotations)
    )
    _settle(app, 250)
    full_window = _grab_full_window(app, window, full_window_path)

    summary: dict[str, Any] = {
        "startup_path": str(startup_path),
        "load_kind": load_kind,
        "viewer_class": type(window.viewer).__name__,
        "window_title": window.windowTitle(),
        "status": window.statusBar().currentMessage(),
        "project_title": window.project.title,
        "cad_document_count": len(window.project.cad_documents),
        "stackup_count": len(window.project.stackups),
        "displayed_shape_count": len(getattr(window.viewer, "displayed_shape_ids", ())),
        "project_path": str(window.project_path) if window.project_path else "",
        "viewport_snapshot": _image_summary(Path(snapshot.image_path)),
        "full_window_snapshot": full_window,
    }
    summary_path = output_dir / f"{args.prefix}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))

    window.close()
    app.processEvents()
    return 0


def _load_startup_path(window: Any, startup_path: Path) -> str:
    suffix = startup_path.suffix.lower()
    if suffix == PACKAGE_SUFFIX:
        window._open_package_file(startup_path)
        return "tolpack"
    if suffix == PROJECT_SUFFIX:
        window.load_project_file(startup_path)
        return "tolproj"
    if suffix in NEUTRAL_CAD_SUFFIXES:
        document = window.geometry_session.import_file(startup_path)
        if hasattr(window.viewer, "display_document"):
            window.viewer.display_document(window.geometry_session)
        window.set_imported_document(document)
        return suffix.lstrip(".")
    raise ValueError(f"Unsupported startup path for CAD 1D smoke: {startup_path}")


def _grab_full_window(app: QApplication, window: Any, output_path: Path) -> dict[str, Any]:
    screen = window.windowHandle().screen() if window.windowHandle() else app.primaryScreen()
    if screen is None:
        raise RuntimeError("No Qt screen is available for full-window capture.")
    window.raise_()
    window.activateWindow()
    app.processEvents()
    frame = window.frameGeometry()
    pixmap = screen.grabWindow(
        0,
        frame.x(),
        frame.y(),
        frame.width(),
        frame.height(),
    )
    capture_method = "desktop_region"
    if pixmap.isNull():
        pixmap = screen.grabWindow(int(window.winId()))
        capture_method = "window_handle"
    if pixmap.isNull() or not pixmap.save(str(output_path)):
        raise RuntimeError(f"Could not capture full-window screenshot: {output_path}")
    summary = _image_summary(output_path)
    summary["capture_method"] = capture_method
    return summary


def _image_summary(path: Path) -> dict[str, Any]:
    image = QImage(str(path))
    if image.isNull():
        raise RuntimeError(f"Unreadable image: {path}")
    return {
        "path": str(path),
        "width": image.width(),
        "height": image.height(),
        "bytes": path.stat().st_size,
        "sampled_unique_colors": _sampled_unique_color_count(image),
        "sampled_nonblack_ratio": _sampled_nonblack_ratio(image),
    }


def _sampled_unique_color_count(image: QImage) -> int:
    colors: set[int] = set()
    step_x = max(1, image.width() // 64)
    step_y = max(1, image.height() // 64)
    for y in range(0, image.height(), step_y):
        for x in range(0, image.width(), step_x):
            colors.add(image.pixel(x, y) & 0x00FFFFFF)
    return len(colors)


def _sampled_nonblack_ratio(image: QImage) -> float:
    samples = 0
    nonblack = 0
    step_x = max(1, image.width() // 64)
    step_y = max(1, image.height() // 64)
    for y in range(0, image.height(), step_y):
        for x in range(0, image.width(), step_x):
            rgb = image.pixel(x, y) & 0x00FFFFFF
            samples += 1
            if rgb != 0:
                nonblack += 1
    return round(nonblack / samples, 4) if samples else 0.0


def _settle(app: QApplication, milliseconds: int) -> None:
    deadline = time.monotonic() + milliseconds / 1000.0
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.025)
    app.processEvents()


if __name__ == "__main__":
    raise SystemExit(main())
