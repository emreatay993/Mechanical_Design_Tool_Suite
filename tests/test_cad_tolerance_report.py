from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from mechanical_design_tool_suite.cad_tolerance_project_io import load_project
from mechanical_design_tool_suite.cad_tolerance_report import (
    NON_1D_WARNING_TEXT,
    build_report_projection,
    generate_html_report,
    render_report_html,
)
from mechanical_design_tool_suite.cad_tolerance_models import ResultStatus
from mechanical_design_tool_suite.cad_viewer_api import SnapshotRequest


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "cad_1d_tolerance"
    / "sample_cad_1d_project.tolproj"
)


class CadToleranceReportTest(unittest.TestCase):
    def test_projection_builds_dashboard_result_contribution_and_warning_views(self) -> None:
        project = load_project(FIXTURE_PATH)

        projection = build_report_projection(project)

        self.assertEqual(projection.project_title, "Caster tolerance study")
        self.assertEqual(projection.badges.objectives_met, 1)
        self.assertEqual(projection.badges.objectives_not_met, 0)
        self.assertEqual(projection.badges.sigma_rollup, "9.49 / 5.01")

        row = projection.summary_rows[0]
        self.assertEqual(row.name, "Bushing ID alignment")
        self.assertEqual(row.status, ResultStatus.WARN)
        self.assertTrue(row.has_warning)
        self.assertEqual(row.objective, "+0.750/-0.500")
        self.assertEqual(row.results, "+0.158/-0.112")
        self.assertEqual(row.predicted_quality, "Cpk = 3.16")
        self.assertEqual(row.dimension_count, 2)

        section = projection.stackups[0]
        self.assertEqual(section.result.title, "Statistical Results for Bushing ID alignment")
        self.assertEqual(section.result.mean_label, "Mean: 24.00")
        self.assertEqual(section.result.standard_deviation_label, "Standard Deviation: 0.05")
        self.assertEqual(section.warnings[0].warning_id, "warn_offset_1")
        self.assertEqual(section.warnings[0].feature_ids, ("feature_start", "feature_end"))
        self.assertIn("laterally offset", section.warnings[0].message)

        self.assertEqual([row.percent for row in section.contributors], [90.0, 10.0])
        self.assertEqual(section.contributors[0].tolerance_box, "+0.150/-0.100")
        self.assertEqual(section.contributors[1].tolerance_box, "dia 0.1")
        self.assertEqual(section.contributors[1].datum, "A")

        snapshot = projection.snapshots[0]
        self.assertEqual(snapshot.snapshot_id, "snapshot_summary_1")
        self.assertEqual(snapshot.image_path, "snapshots/bushing_alignment.png")
        self.assertEqual(snapshot.visible_stackup_ids, ("stackup_bushing_alignment",))
        self.assertEqual(snapshot.camera["target"], [12.0, 0.0, 0.0])
        self.assertEqual(snapshot.artifact_metadata["image_path"], snapshot.image_path)

    def test_html_report_generation_is_deterministic_and_matches_browser_layout(self) -> None:
        project = load_project(FIXTURE_PATH)

        with tempfile.TemporaryDirectory() as directory:
            first = generate_html_report(project, Path(directory) / "report.html")
            second = generate_html_report(project, Path(directory) / "report.html")

        self.assertEqual(first.html, second.html)
        self.assertEqual(first.output_path.name, "report.html")
        self.assertIn('<nav class="left-nav">', first.html)
        self.assertIn('<main class="report-canvas">', first.html)
        self.assertIn("Tolerance Stackup Report", first.html)
        self.assertIn("Summary of 1D Tolerance Stackups", first.html)
        self.assertIn("Bushing ID alignment Analysis Results", first.html)
        self.assertIn("Statistical Results for Bushing ID alignment", first.html)
        self.assertIn("Bushing ID alignment Analysis Contributions", first.html)
        self.assertIn('class="contribution-track"', first.html)
        self.assertIn('<link rel="stylesheet" href="css/report.css">', first.html)
        self.assertIn('<script src="js/report.js" defer></script>', first.html)
        self.assertIn("images/snapshot-summary-1.svg", first.html)
        self.assertIn(NON_1D_WARNING_TEXT, first.html)
        self.assertIn("Endpoint features are laterally offset from the stack direction.", first.html)
        self.assertNotIn(".pdf", first.html.lower())

    def test_html_report_writes_portable_deterministic_assets_and_manifest(self) -> None:
        project = load_project(FIXTURE_PATH)

        with tempfile.TemporaryDirectory() as directory:
            result = generate_html_report(project, Path(directory) / "report.html")
            root = Path(directory)
            manifest_text = (root / "report_manifest.json").read_text(encoding="utf-8")

            self.assertTrue((root / "css" / "report.css").is_file())
            self.assertTrue((root / "js" / "report.js").is_file())
            self.assertTrue((root / "images" / "snapshot-summary-1.svg").is_file())
            self.assertTrue((root / "report_manifest.json").is_file())
            self.assertEqual(
                [path.relative_to(root).as_posix() for path in result.asset_paths],
                [
                    "css/report.css",
                    "js/report.js",
                    "report_manifest.json",
                    "images/snapshot-summary-1.svg",
                ],
            )
            self.assertEqual(result.manifest["html_path"], "report.html")
            self.assertEqual(result.manifest["css_path"], "css/report.css")
            self.assertEqual(result.manifest["js_path"], "js/report.js")
            self.assertEqual(result.manifest["images"][0]["path"], "images/snapshot-summary-1.svg")
            self.assertEqual(result.manifest["images"][0]["source_reference"], "snapshots/bushing_alignment.png")
            self.assertNotIn(str(root), result.html)
            self.assertNotIn(str(root), manifest_text)

    def test_html_report_escapes_project_and_stackup_text(self) -> None:
        project = load_project(FIXTURE_PATH)
        project.title = 'Caster <script>alert("x")</script> & study'
        project.stackups[0].name = "Bushing <unsafe> & alignment"

        html = render_report_html(build_report_projection(project))

        self.assertIn("Caster &lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; &amp; study", html)
        self.assertIn("Bushing &lt;unsafe&gt; &amp; alignment", html)
        self.assertNotIn("<script>alert", html)

    def test_snapshot_request_contract_carries_serializable_report_metadata(self) -> None:
        request = SnapshotRequest(
            Path("viewer.png"),
            visible_stackup_ids=("stackup_bushing_alignment",),
            annotation_positions={"stackup_bushing_alignment": [0.42, 0.58]},
            highlight_shape_ids=("shape_start_face", "shape_end_cylinder"),
            highlight_feature_ids=("feature_start", "feature_end"),
            warning_ids=("warn_offset_1",),
            artifact_metadata={"image_role": "annotated_model_snapshot"},
        )

        self.assertEqual(request.output_path, Path("viewer.png"))
        self.assertEqual(request.visible_stackup_ids, ("stackup_bushing_alignment",))
        self.assertEqual(request.highlight_shape_ids, ("shape_start_face", "shape_end_cylinder"))
        self.assertEqual(request.highlight_feature_ids, ("feature_start", "feature_end"))
        self.assertEqual(request.warning_ids, ("warn_offset_1",))
        self.assertEqual(request.artifact_metadata["image_role"], "annotated_model_snapshot")


if __name__ == "__main__":
    unittest.main()
