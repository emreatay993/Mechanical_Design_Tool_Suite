from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from bolt_calculation_tool.tolerance_vnext_gui import (
    PREFERENCES_ENV_VAR,
    ToleranceVNextBackend,
    _parse_args,
    _resolve_style_args,
    _save_theme_preferences,
)


class ToleranceVNextBackendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.backend = ToleranceVNextBackend()

    def test_backend_exposes_default_workspace_state(self) -> None:
        self.assertEqual(self.backend.projectTitle, "Bracket Assembly Tolerance Review")
        self.assertEqual(len(self.backend.joints), 1)
        self.assertEqual(self.backend.selectedSubJoint["name"], "JOINT A.1")
        self.assertEqual(self.backend.metrics["status"], "Pass")
        self.assertEqual(self.backend.summaryRows[0]["sub_joint"], "JOINT A.1")

    def test_editing_flange_updates_live_metrics(self) -> None:
        flange = self.backend.flanges[0]
        self.backend.updateFlange(flange["id"], "6", "0.15")

        self.assertEqual(self.backend.metrics["nominal"], "13")
        self.assertTrue(self.backend.dirty)

    def test_save_load_and_csv_export_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_path = Path(directory) / "ui_state.tolproj"
            csv_path = Path(directory) / "summary.csv"
            self.backend.saveProjectTo(str(project_path))
            self.backend.addJoint()
            self.backend.openProjectFrom(str(project_path))
            self.backend.exportCsvTo(str(csv_path))

            self.assertTrue(project_path.exists())
            self.assertTrue(csv_path.exists())
            self.assertIn("JOINT A.1", csv_path.read_text(encoding="utf-8"))

    def test_theme_selection_is_saved_as_app_preference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            preferences_path = Path(directory) / "ui_preferences.json"
            backend = ToleranceVNextBackend(
                quick_style="Fusion",
                material_theme="Light",
                preferences_path=preferences_path,
            )

            backend.setQuickStyle("Material")
            backend.setMaterialTheme("Dark")

            self.assertEqual(backend.quickStyle, "Material")
            self.assertEqual(backend.activeQuickStyle, "Fusion")
            self.assertEqual(backend.materialTheme, "Dark")
            self.assertTrue(backend.themeRestartRequired)
            self.assertFalse(backend.dirty)
            self.assertIn("Restart to apply Material Dark", backend.themeHint)
            saved = json.loads(preferences_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["quick_style"], "Material")
            self.assertEqual(saved["material_theme"], "Dark")

    def test_invalid_theme_selection_is_rejected(self) -> None:
        self.backend.setQuickStyle("Unknown")

        self.assertEqual(self.backend.quickStyle, self.backend.activeQuickStyle)
        self.assertIn("not an available", self.backend.statusText)

    def test_saved_theme_preference_is_used_for_launch_defaults(self) -> None:
        tracked_env = (
            PREFERENCES_ENV_VAR,
            "TOLERANCE_VNEXT_QUICK_STYLE",
            "QT_QUICK_CONTROLS_MATERIAL_THEME",
        )
        previous_env = {name: os.environ.get(name) for name in tracked_env}
        try:
            with tempfile.TemporaryDirectory() as directory:
                preferences_path = Path(directory) / "ui_preferences.json"
                _save_theme_preferences(
                    {"quick_style": "Universal", "material_theme": "Dark"},
                    preferences_path,
                )
                os.environ[PREFERENCES_ENV_VAR] = str(preferences_path)
                os.environ.pop("TOLERANCE_VNEXT_QUICK_STYLE", None)
                os.environ.pop("QT_QUICK_CONTROLS_MATERIAL_THEME", None)

                args = _resolve_style_args(_parse_args([]))

                self.assertEqual(args.quick_style, "Universal")
                self.assertEqual(args.material_theme, "Dark")
        finally:
            for name, value in previous_env.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value


if __name__ == "__main__":
    unittest.main()
