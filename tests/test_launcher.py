from __future__ import annotations

import os
import sys
import unittest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from mechanical_design_tool_suite.launcher import PROGRAMS, _program_command, _program_icon


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


if __name__ == "__main__":
    unittest.main()
