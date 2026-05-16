"""Program selection launcher for the packaged mechanical design tool suite."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import Qt
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

from mechanical_design_tool_suite.app_icons import app_icon, app_pixmap


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
        self.setWindowIcon(app_icon("suite"))
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
        icon.setPixmap(app_pixmap(self.program.icon_kind, 76))
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
