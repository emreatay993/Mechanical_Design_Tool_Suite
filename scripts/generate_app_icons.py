"""Rasterise the SVG application icons into multi-resolution Windows ``.ico``.

The launcher and each GUI render the SVG sources directly at runtime; this
script bakes the same vectors into ``.ico`` files so the packaged executables
carry a proper Explorer/taskbar icon. ``.ico`` files are committed under
``build_assets/icons`` so PyInstaller does not need a display at build time.

Run after editing any ``app-*.svg``::

    python scripts/generate_app_icons.py
"""

from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, QRectF  # noqa: E402
from PyQt6.QtGui import QGuiApplication, QImage, QPainter  # noqa: E402
from PyQt6.QtSvg import QSvgRenderer  # noqa: E402

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_ICON_DIR = (
    _PROJECT_ROOT
    / "src"
    / "mechanical_design_tool_suite"
    / "qml"
    / "assets"
    / "icons"
)
_OUT_DIR = _PROJECT_ROOT / "build_assets" / "icons"

# PyInstaller entry name -> source SVG.
_EXE_ICONS = {
    "MechanicalDesignToolSuite": "app-launcher.svg",
    "BoltCalculationGui": "app-bolt.svg",
    "ToleranceAnalysis": "app-tolerance.svg",
    "ToleranceAnalysisVNext": "app-tolerance-vnext.svg",
    "Cad1DTolerance": "app-cad-1d.svg",
}
_SIZES = (16, 24, 32, 48, 64, 128, 256)


def _render_png(svg_text: str, size: int) -> bytes:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
    if not renderer.isValid():
        raise RuntimeError("invalid SVG content")
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()

    buffer_bytes = QByteArray()
    buffer = QBuffer(buffer_bytes)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, "PNG"):
        raise RuntimeError("failed to encode PNG")
    buffer.close()
    return bytes(buffer_bytes)


def _build_ico(frames: list[tuple[int, bytes]]) -> bytes:
    header = struct.pack("<HHH", 0, 1, len(frames))
    entries = b""
    blobs = b""
    offset = 6 + 16 * len(frames)
    for size, png in frames:
        dimension = 0 if size >= 256 else size
        entries += struct.pack(
            "<BBBBHHII", dimension, dimension, 0, 0, 1, 32, len(png), offset
        )
        offset += len(png)
        blobs += png
    return header + entries + blobs


def main() -> None:
    QGuiApplication(sys.argv)
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    for exe_name, svg_name in _EXE_ICONS.items():
        svg_text = (_ICON_DIR / svg_name).read_text(encoding="utf-8")
        frames = [(size, _render_png(svg_text, size)) for size in _SIZES]
        ico_bytes = _build_ico(frames)
        out_path = _OUT_DIR / f"{exe_name}.ico"
        out_path.write_bytes(ico_bytes)
        print(f"wrote {out_path.relative_to(_PROJECT_ROOT)} ({len(ico_bytes)} bytes)")


if __name__ == "__main__":
    main()
