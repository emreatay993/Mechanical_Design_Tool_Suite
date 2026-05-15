from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from mechanical_design_tool_suite import cad_tolerance_gui
from mechanical_design_tool_suite.launcher import PROGRAMS, _program_command, _program_icon


REPO_ROOT = Path(__file__).resolve().parents[1]


class LauncherProgramTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_cad_1d_tolerance_program_is_in_launcher(self) -> None:
        programs_by_key = {program.key: program for program in PROGRAMS}

        self.assertIn("cad-1d-tolerance", programs_by_key)
        cad_program = programs_by_key["cad-1d-tolerance"]
        self.assertEqual(
            cad_program.module_name,
            "mechanical_design_tool_suite.cad_tolerance_gui",
        )
        self.assertEqual(cad_program.exe_name, "Cad1DTolerance.exe")

    def test_source_launch_command_uses_cad_module_entrypoint(self) -> None:
        cad_program = next(
            program for program in PROGRAMS if program.key == "cad-1d-tolerance"
        )

        self.assertEqual(
            _program_command(cad_program),
            [sys.executable, "-m", "mechanical_design_tool_suite.cad_tolerance_gui"],
        )

    def test_cad_launcher_icon_renders(self) -> None:
        cad_program = next(
            program for program in PROGRAMS if program.key == "cad-1d-tolerance"
        )

        pixmap = _program_icon(cad_program.icon_kind, cad_program.accent, 48)

        self.assertFalse(pixmap.isNull())
        self.assertEqual(pixmap.width(), 48)
        self.assertEqual(pixmap.height(), 48)


class _FakeCadApp:
    def __init__(self, argv: list[str]) -> None:
        self.argv = list(argv)

    def exec(self) -> int:
        return 0


class _FakeCadWindow:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Path | None]] = []

    def _open_package_file(self, path: Path) -> None:
        self.calls.append(("package", path))

    def load_project_file(self, path: Path) -> None:
        self.calls.append(("project", path))

    def open_cad_file(self, path: Path) -> None:
        self.calls.append(("cad", path))

    def show(self) -> None:
        self.calls.append(("show", None))


class CadGuiEntrypointTest(unittest.TestCase):
    def _run_main(self, *argv: str) -> _FakeCadWindow:
        window = _FakeCadWindow()
        with (
            patch.object(sys, "argv", ["cad-1d-tolerance-gui", *argv]),
            patch.object(cad_tolerance_gui, "QApplication", _FakeCadApp),
            patch.object(
                cad_tolerance_gui,
                "create_cad_tolerance_window",
                return_value=window,
            ),
        ):
            with self.assertRaises(SystemExit) as context:
                cad_tolerance_gui.main()
        self.assertEqual(context.exception.code, 0)
        return window

    def test_direct_entrypoint_opens_supported_startup_paths(self) -> None:
        cases = {
            r"fixtures\caster.step": ("cad", Path(r"fixtures\caster.step")),
            r"fixtures\caster.iges": ("cad", Path(r"fixtures\caster.iges")),
            r"fixtures\sample.tolproj": ("project", Path(r"fixtures\sample.tolproj")),
            r"fixtures\sample.tolpack": ("package", Path(r"fixtures\sample.tolpack")),
        }

        for argument, expected_call in cases.items():
            with self.subTest(argument=argument):
                window = self._run_main(argument)
                self.assertEqual(window.calls[0], expected_call)
                self.assertEqual(window.calls[-1], ("show", None))

    def test_direct_entrypoint_without_argument_opens_empty_workspace(self) -> None:
        window = self._run_main()

        self.assertEqual(window.calls, [("show", None)])


class CadPackagingConfigTest(unittest.TestCase):
    def test_pyinstaller_spec_includes_cad_executable_source_launcher(self) -> None:
        spec_text = (REPO_ROOT / "MechanicalDesignToolSuite.spec").read_text(encoding="utf-8")

        self.assertIn('"Cad1DTolerance"', spec_text)
        self.assertIn('project_root / "scripts" / "run_cad_1d_tolerance.py"', spec_text)
        self.assertIn('collect_conda_dll_dependencies("OCC")', spec_text)

    def test_build_script_has_cad_program_and_runtime_guard(self) -> None:
        script_text = (REPO_ROOT / "scripts" / "build_windows.ps1").read_text(encoding="utf-8")

        self.assertIn('"Cad1D"', script_text)
        self.assertIn('"Cad1DTolerance.exe"', script_text)
        self.assertIn("Test-CadRuntimeDependencies", script_text)
        self.assertIn("pythonocc-core 7.9.3", script_text)
        self.assertIn("novtk", script_text)
        self.assertIn("PyQt5 is present", script_text)
        self.assertIn("Conda Qt5 package is present", script_text)

    def test_cad_environment_keeps_occt_runtime_pinned_without_conda_pyqt(self) -> None:
        environment_text = (REPO_ROOT / "environment-cad312.yml").read_text(encoding="utf-8")
        pyproject_text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertIn("python=3.12", environment_text)
        self.assertIn("numpy=1.26.*", environment_text)
        self.assertIn("pythonocc-core=7.9.3=*novtk*", environment_text)
        self.assertIn("ffmpeg", environment_text)
        self.assertIn('"PyQt6>=6.6"', pyproject_text)
        self.assertNotIn("\n  - pyqt", environment_text.lower())
        self.assertNotIn("\n  - pyqt5", environment_text.lower())
        self.assertNotIn("\n  - qt=5", environment_text.lower())
        self.assertNotIn("\n  - qt-main=5", environment_text.lower())


if __name__ == "__main__":
    unittest.main()
