"""Shared application icon loading for the launcher and each packaged GUI.

Icons are authored as self-contained SVG art (background, shading, and glyph
baked in) under ``qml/assets/icons``. They are rasterised on demand through
Qt's SVG engine so the same vector source drives the launcher cards, the
window/taskbar icons, and the packaged ``.exe`` icons.
"""

from __future__ import annotations

from importlib import resources

from PyQt6.QtCore import QByteArray, QRectF, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

_ICON_FILES = {
    "bolt": "app-bolt.svg",
    "tolerance": "app-tolerance.svg",
    "vnext": "app-tolerance-vnext.svg",
    "cad-1d": "app-cad-1d.svg",
    "suite": "app-launcher.svg",
}

# Accent used only if the SVG asset cannot be loaded (packaging fault).
_FALLBACK_ACCENT = {
    "bolt": "#2f6f9f",
    "tolerance": "#6f55d9",
    "vnext": "#23845f",
    "cad-1d": "#c76a16",
    "suite": "#16314f",
}

_ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)


def _load_svg(kind: str) -> QSvgRenderer | None:
    file_name = _ICON_FILES.get(kind)
    if file_name is None:
        return None
    try:
        svg_text = (
            resources.files("mechanical_design_tool_suite")
            .joinpath("qml", "assets", "icons", file_name)
            .read_text(encoding="utf-8")
        )
    except (FileNotFoundError, ModuleNotFoundError, OSError):
        return None
    renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
    return renderer if renderer.isValid() else None


def app_pixmap(kind: str, size: int) -> QPixmap:
    """Render ``kind`` to a transparent square pixmap of ``size`` pixels."""

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    renderer = _load_svg(kind)
    if renderer is not None:
        renderer.render(painter, QRectF(0, 0, size, size))
    else:
        accent = QColor(_FALLBACK_ACCENT.get(kind, "#2f6f9f"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(accent)
        radius = size * 0.22
        painter.drawRoundedRect(
            int(size * 0.08),
            int(size * 0.08),
            int(size * 0.84),
            int(size * 0.84),
            radius,
            radius,
        )
    painter.end()
    return pixmap


def app_icon(kind: str) -> QIcon:
    """Build a multi-resolution :class:`QIcon` for window and taskbar use."""

    icon = QIcon()
    for size in _ICON_SIZES:
        icon.addPixmap(app_pixmap(kind, size))
    return icon
