"""Minimal PyQt6 host for the P04A primary CAD viewer spike."""

from __future__ import annotations

from pathlib import Path
import sys

try:
    from PyQt6.QtGui import QAction, QColor, QFont, QFontDatabase, QPalette
    from PyQt6.QtWidgets import (
        QApplication,
        QFileDialog,
        QMainWindow,
        QMessageBox,
        QStyleFactory,
        QToolBar,
    )
except ImportError as exc:  # pragma: no cover - exercised only without GUI deps.
    raise RuntimeError(
        "The CAD tolerance viewer host requires PyQt6. Use the mdts-cad312 "
        "environment or install PyQt6 before launching it."
    ) from exc

from .cad_geometry_occ import OccCadGeometrySession
from .cad_viewer_api import SnapshotRequest, StandardView
from .cad_viewer_occ import OccCadViewerWidget


NEUTRAL_CAD_FILTER = (
    "Neutral CAD files (*.step *.stp *.iges *.igs);;"
    "STEP files (*.step *.stp);;"
    "IGES files (*.iges *.igs)"
)


class CadToleranceViewerWindow(QMainWindow):
    """Small viewer smoke window kept separate from the full P04 UI shell."""

    def __init__(
        self,
        geometry_session: OccCadGeometrySession | None = None,
        viewer: OccCadViewerWidget | None = None,
    ) -> None:
        super().__init__()
        self.geometry_session = geometry_session or OccCadGeometrySession()
        self.viewer = viewer or OccCadViewerWidget(self)

        self.setWindowTitle("CAD 1D Tolerance Viewer Spike")
        self.resize(1200, 800)
        self.setMinimumSize(800, 520)
        self.setCentralWidget(self.viewer)
        self._build_toolbar()
        self.statusBar().showMessage("Ready")

    def open_cad_file(self, path: str | Path) -> None:
        input_path = Path(path)
        document = self.geometry_session.import_file(input_path)
        self.viewer.display_document(self.geometry_session)
        self.statusBar().showMessage(
            f"Displayed {document.display_name or input_path.name}"
        )

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("CAD Viewer")
        toolbar.setMovable(False)
        toolbar.setObjectName("CadViewerToolbar")
        self.addToolBar(toolbar)

        open_action = QAction("Open", self)
        open_action.triggered.connect(self._open_dialog)
        toolbar.addAction(open_action)

        fit_action = QAction("Fit", self)
        fit_action.triggered.connect(self.viewer.fit_all)
        toolbar.addAction(fit_action)

        iso_action = QAction("Iso", self)
        iso_action.triggered.connect(lambda: self.viewer.set_standard_view(StandardView.ISO))
        toolbar.addAction(iso_action)

        snapshot_action = QAction("Snapshot", self)
        snapshot_action.triggered.connect(self._save_snapshot)
        toolbar.addAction(snapshot_action)

    def _open_dialog(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Open neutral CAD file",
            "",
            NEUTRAL_CAD_FILTER,
        )
        if not path:
            return
        try:
            self.open_cad_file(path)
        except Exception as exc:
            QMessageBox.warning(self, "CAD import failed", str(exc))
            self.statusBar().showMessage("CAD import failed")

    def _save_snapshot(self) -> None:
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save CAD viewer snapshot",
            "",
            "PNG image (*.png);;JPEG image (*.jpg *.jpeg)",
        )
        if not path:
            return
        output_path = Path(path)
        if output_path.suffix == "":
            output_path = output_path.with_suffix(".png")
        try:
            snapshot = self.viewer.capture_snapshot(SnapshotRequest(output_path))
        except Exception as exc:
            QMessageBox.warning(self, "Snapshot failed", str(exc))
            self.statusBar().showMessage("Snapshot failed")
            return
        self.statusBar().showMessage(f"Saved snapshot {Path(snapshot.image_path).name}")


def _apply_cad_tolerance_style(app: QApplication) -> None:
    fusion_style = QStyleFactory.create("Fusion")
    if fusion_style is not None:
        app.setStyle(fusion_style)
    else:
        app.setStyle("Fusion")

    font_families = set(QFontDatabase.families())
    for family in ("Segoe UI", "Arial", "Tahoma"):
        if family in font_families:
            app.setFont(QFont(family, 10))
            break

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#f2f2f2"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#202020"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#f7f7f7"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#202020"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#f4f4f4"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#202020"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#2f6f9f"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    app.setStyleSheet(
        """
        QMainWindow {
            background: #f2f2f2;
        }
        QToolBar#CadViewerToolbar {
            background: #eeeeee;
            border-bottom: 1px solid #c8c8c8;
            spacing: 4px;
        }
        QToolButton {
            background: #ffffff;
            border: 1px solid #bdbdbd;
            border-radius: 3px;
            padding: 4px 8px;
        }
        QToolButton:hover {
            background: #eaf3fb;
            border-color: #2f6f9f;
        }
        QStatusBar {
            background: #eeeeee;
            border-top: 1px solid #c8c8c8;
        }
        """
    )


def create_cad_tolerance_window(
    app: QApplication | None = None,
    geometry_session: OccCadGeometrySession | None = None,
) -> CadToleranceViewerWindow:
    app = app or QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    _apply_cad_tolerance_style(app)
    return CadToleranceViewerWindow(geometry_session=geometry_session)


def main() -> None:
    app = QApplication(sys.argv)
    window = create_cad_tolerance_window(app)
    if len(sys.argv) > 1:
        window.open_cad_file(sys.argv[1])
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
