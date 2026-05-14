"""Manual smoke harness for the P04A PyQt6 OCCT CAD viewer."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import tempfile

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication

from mechanical_design_tool_suite.cad_tolerance_gui import create_cad_tolerance_window
from mechanical_design_tool_suite.cad_viewer_api import SnapshotRequest


DEFAULT_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "cad_1d_tolerance"
    / "neutral_step_two_part_loop.step"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        type=Path,
        default=DEFAULT_FIXTURE,
        help="STEP/IGES fixture to display.",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        help="Optional output image path. Defaults to a temporary PNG for automated smoke.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Keep the viewer open for manual inspection instead of auto-capturing.",
    )
    parser.add_argument(
        "--exit-after-ms",
        type=int,
        default=1000,
        help="Delay before snapshot capture and exit when --snapshot is set.",
    )
    args = parser.parse_args(argv)
    if args.snapshot is None and not args.interactive:
        args.snapshot = Path(tempfile.gettempdir()) / "mdts_cad_viewer_smoke.png"

    app = QApplication.instance() or QApplication(sys.argv)
    window = create_cad_tolerance_window(app)
    _load_fixture_without_dialog(window, args.fixture)
    window.show()

    if args.snapshot is None:
        return int(app.exec())

    def capture_and_exit() -> None:
        try:
            snapshot = window.viewport_host.capture_snapshot(
                SnapshotRequest(
                    args.snapshot,
                    annotations=window.viewport_host.annotations,
                )
            )
            image = QImage(snapshot.image_path)
            if image.isNull() or image.width() <= 0 or image.height() <= 0:
                raise RuntimeError(f"Snapshot is blank or unreadable: {snapshot.image_path}")
            print(
                f"Displayed {args.fixture} and captured {snapshot.image_path} "
                f"({image.width()}x{image.height()})."
            )
            app.quit()
        except Exception as exc:
            print(f"CAD viewer smoke failed: {exc}", file=sys.stderr)
            app.exit(1)

    QTimer.singleShot(max(args.exit_after_ms, 0), capture_and_exit)
    return int(app.exec())


def _load_fixture_without_dialog(window, fixture: Path) -> None:
    document = window.geometry_session.import_file(fixture)
    if hasattr(window.viewer, "display_document"):
        window.viewer.display_document(window.geometry_session)
    window.set_imported_document(document)


if __name__ == "__main__":
    raise SystemExit(main())
