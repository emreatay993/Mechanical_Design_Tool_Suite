"""Program selection launcher for the packaged mechanical design tool suite."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from PyQt6.QtCore import QByteArray, QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


_DEBUG_LOG_ENV = "MDTS_PACKAGED_ERROR_LOGS"
_DEBUG_FLAG_FILE = "mdts_debug_build.flag"


@dataclass(frozen=True)
class ProgramDescriptor:
    key: str
    title: str
    subtitle: str
    description: str
    accent: str
    exe_name: str
    module_name: str
    icon_kind: str


PROGRAMS = (
    ProgramDescriptor(
        key="bolt",
        title="Bolt Calculation Tool",
        subtitle="Fastener loads, interaction checks, and visualization",
        description="Run the main bolted-joint calculation workflow.",
        accent="#2f6f9f",
        exe_name="BoltCalculationGui.exe",
        module_name="mechanical_design_tool_suite.gui",
        icon_kind="bolt",
    ),
    ProgramDescriptor(
        key="tolerance",
        title="Legacy Tolerance Tool",
        subtitle="Single stackup worksheet-style tolerance analysis",
        description="Open the current released tolerance analysis interface.",
        accent="#6f55d9",
        exe_name="ToleranceAnalysis.exe",
        module_name="mechanical_design_tool_suite.tolerance_gui",
        icon_kind="tolerance",
    ),
    ProgramDescriptor(
        key="tolerance-vnext",
        title="Tolerance Tool vNext",
        subtitle="Joint-driven stackups, catalog parts, and Monte Carlo",
        description="Open the new engineering workspace with a modern UI.",
        accent="#23845f",
        exe_name="ToleranceAnalysisVNext.exe",
        module_name="mechanical_design_tool_suite.tolerance_vnext_gui",
        icon_kind="vnext",
    ),
    ProgramDescriptor(
        key="cad-1d-tolerance",
        title="CAD 1D Tolerance Tool",
        subtitle="STEP/IGES stackups with OCCT CAD viewing",
        description="Open the CAD-based 1D tolerance analysis prototype.",
        accent="#c76a16",
        exe_name="Cad1DTolerance.exe",
        module_name="mechanical_design_tool_suite.cad_tolerance_gui",
        icon_kind="cad-1d",
    ),
)


class LauncherWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Mechanical Design Tool Suite")
        self.setMinimumSize(980, 580)
        self.setWindowIcon(QIcon(_program_icon("bolt", "#2f6f9f", 48)))
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(34, 28, 34, 28)
        root.setSpacing(22)

        header = QVBoxLayout()
        title = QLabel("Mechanical Design Tool Suite")
        title.setObjectName("LauncherTitle")
        subtitle = QLabel("Select the engineering program you want to run.")
        subtitle.setObjectName("LauncherSubtitle")
        header.addWidget(title)
        header.addWidget(subtitle)
        root.addLayout(header)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(18)
        column_count = 2 if len(PROGRAMS) > 3 else len(PROGRAMS)
        for index, program in enumerate(PROGRAMS):
            row, column = divmod(index, column_count)
            grid.addWidget(ProgramCard(program, self._launch_program), row, column)
        root.addLayout(grid, stretch=1)

        footer = QLabel(
            "The packaged folder also includes direct executables for each GUI."
        )
        footer.setObjectName("LauncherFooter")
        root.addWidget(footer)

    def _launch_program(self, program: ProgramDescriptor) -> None:
        command = _program_command(program)
        if getattr(sys, "frozen", False) and not Path(command[0]).exists():
            QMessageBox.critical(
                self,
                "Program executable is missing",
                (
                    f"{program.title} was not found next to the launcher.\n\n"
                    f"Expected:\n{command[0]}\n\n"
                    "Rebuild the PyInstaller package and keep the dist folder intact."
                ),
            )
            return
        try:
            subprocess.Popen(command, cwd=str(_launch_cwd()), env=_program_environment())
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Could not launch program",
                f"{program.title} could not be started.\n\n{exc}",
            )


class ProgramCard(QFrame):
    def __init__(self, program: ProgramDescriptor, launcher) -> None:
        super().__init__()
        self.program = program
        self.launcher = launcher
        self.setObjectName("ProgramCard")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)

        top_row = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(_program_icon(self.program.icon_kind, self.program.accent, 76))
        icon.setFixedSize(82, 82)
        top_row.addWidget(icon, alignment=Qt.AlignmentFlag.AlignLeft)
        top_row.addStretch(1)
        layout.addLayout(top_row)

        title = QLabel(self.program.title)
        title.setObjectName("ProgramTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        subtitle = QLabel(self.program.subtitle)
        subtitle.setObjectName("ProgramSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        description = QLabel(self.program.description)
        description.setObjectName("ProgramDescription")
        description.setWordWrap(True)
        layout.addWidget(description)
        layout.addStretch(1)

        button = QPushButton("Open")
        button.setObjectName("ProgramOpenButton")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(lambda: self.launcher(self.program))
        layout.addWidget(button)


def _program_command(program: ProgramDescriptor) -> list[str]:
    if getattr(sys, "frozen", False):
        return [str(Path(sys.executable).resolve().parent / program.exe_name)]
    return [sys.executable, "-m", program.module_name]


def _launch_cwd() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def _program_environment() -> dict[str, str] | None:
    if not getattr(sys, "frozen", False):
        return None
    if not _packaged_error_logging_enabled():
        return None

    environment = os.environ.copy()
    environment[_DEBUG_LOG_ENV] = "1"
    return environment


def _packaged_error_logging_enabled() -> bool:
    if os.environ.get(_DEBUG_LOG_ENV, "").strip().lower() in {"1", "true", "yes", "on"}:
        return True

    internal_dir = getattr(sys, "_MEIPASS", None)
    if internal_dir:
        return (Path(internal_dir) / _DEBUG_FLAG_FILE).exists()
    return (Path(sys.executable).resolve().parent / "_internal" / _DEBUG_FLAG_FILE).exists()


def _program_icon(kind: str, accent: str, size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    accent_color = QColor(accent)
    painter.setBrush(QColor("#f7fbff"))
    painter.setPen(QPen(QColor("#d7e1ec"), max(1, size // 48)))
    painter.drawRoundedRect(2, 2, size - 4, size - 4, size // 7, size // 7)

    painter.setPen(
        QPen(
            accent_color,
            max(3, size // 13),
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
        )
    )
    if kind == "bolt":
        points = [
            (0.50, 0.16),
            (0.74, 0.30),
            (0.74, 0.58),
            (0.50, 0.72),
            (0.26, 0.58),
            (0.26, 0.30),
        ]
        painter.setBrush(QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 36))
        painter.drawPolygon(QPolygonF([QPointF(size * x, size * y) for x, y in points]))
        painter.drawLine(int(size * 0.50), int(size * 0.25), int(size * 0.50), int(size * 0.78))
        painter.drawLine(int(size * 0.36), int(size * 0.40), int(size * 0.64), int(size * 0.40))
        painter.drawLine(int(size * 0.36), int(size * 0.55), int(size * 0.64), int(size * 0.55))
    elif kind == "tolerance":
        painter.drawLine(int(size * 0.23), int(size * 0.34), int(size * 0.77), int(size * 0.34))
        painter.drawLine(int(size * 0.23), int(size * 0.60), int(size * 0.77), int(size * 0.60))
        painter.drawLine(int(size * 0.34), int(size * 0.24), int(size * 0.34), int(size * 0.70))
        painter.drawLine(int(size * 0.66), int(size * 0.24), int(size * 0.66), int(size * 0.70))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "+/-")
    elif kind == "vnext":
        painter.drawRoundedRect(
            int(size * 0.23),
            int(size * 0.24),
            int(size * 0.54),
            int(size * 0.44),
            int(size * 0.08),
            int(size * 0.08),
        )
        painter.drawLine(int(size * 0.35), int(size * 0.78), int(size * 0.65), int(size * 0.78))
        painter.drawLine(int(size * 0.50), int(size * 0.68), int(size * 0.50), int(size * 0.78))
        painter.drawLine(int(size * 0.33), int(size * 0.42), int(size * 0.45), int(size * 0.52))
        painter.drawLine(int(size * 0.45), int(size * 0.52), int(size * 0.68), int(size * 0.34))
    else:
        _draw_cad_icon(painter, accent_color, size)

    painter.end()
    return pixmap


def _draw_cad_icon(painter: QPainter, accent_color: QColor, size: int) -> None:
    if _render_svg_icon(painter, "file-axis-3d.svg", accent_color.name(), size):
        return

    painter.drawRect(
        int(size * 0.28),
        int(size * 0.20),
        int(size * 0.44),
        int(size * 0.58),
    )
    painter.drawLine(int(size * 0.60), int(size * 0.20), int(size * 0.72), int(size * 0.32))
    painter.drawLine(int(size * 0.60), int(size * 0.20), int(size * 0.60), int(size * 0.32))
    painter.drawLine(int(size * 0.33), int(size * 0.66), int(size * 0.56), int(size * 0.43))
    painter.drawLine(int(size * 0.33), int(size * 0.44), int(size * 0.33), int(size * 0.66))
    painter.drawLine(int(size * 0.33), int(size * 0.66), int(size * 0.67), int(size * 0.66))


def _render_svg_icon(painter: QPainter, icon_name: str, accent: str, size: int) -> bool:
    try:
        icon_path = resources.files("mechanical_design_tool_suite").joinpath(
            "qml",
            "assets",
            "icons",
            icon_name,
        )
        svg_text = icon_path.read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError, OSError):
        return False

    svg_text = svg_text.replace('stroke="currentColor"', f'stroke="{accent}"')
    renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
    if not renderer.isValid():
        return False

    margin = size * 0.22
    renderer.render(painter, QRectF(margin, margin, size - (2 * margin), size - (2 * margin)))
    return True


def _apply_launcher_style(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(
        """
        QWidget {
            background: #f3f6fb;
            color: #0f172a;
            font-family: Segoe UI, Arial, sans-serif;
            font-size: 12px;
        }
        QLabel {
            background: transparent;
        }
        QLabel#LauncherTitle {
            font-size: 28px;
            font-weight: 700;
            color: #0b1526;
        }
        QLabel#LauncherSubtitle {
            font-size: 14px;
            color: #526173;
        }
        QLabel#LauncherFooter {
            color: #64748b;
        }
        QFrame#ProgramCard {
            background: #ffffff;
            border: 1px solid #d6dfeb;
            border-radius: 8px;
        }
        QFrame#ProgramCard:hover {
            border-color: #9db7d9;
        }
        QLabel#ProgramTitle {
            font-size: 18px;
            font-weight: 700;
            color: #0f172a;
        }
        QLabel#ProgramSubtitle {
            font-size: 12px;
            font-weight: 600;
            color: #334155;
        }
        QLabel#ProgramDescription {
            color: #64748b;
            line-height: 135%;
        }
        QPushButton#ProgramOpenButton {
            background: #10233d;
            border: 1px solid #10233d;
            border-radius: 7px;
            color: #ffffff;
            min-height: 34px;
            font-weight: 600;
        }
        QPushButton#ProgramOpenButton:hover {
            background: #1d3c64;
            border-color: #1d3c64;
        }
        QPushButton#ProgramOpenButton:pressed {
            background: #0b182a;
        }
        """
    )


def main() -> None:
    app = QApplication.instance() or QApplication([sys.argv[0]])
    app.setApplicationName("Mechanical Design Tool Suite")
    _apply_launcher_style(app)
    window = LauncherWindow()
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
