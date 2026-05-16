# P25 Report Snapshot HTML Parity Evidence

Date: 2026-05-16

## Scope

P25 tightened the HTML report target only. It did not add PDF export, installer work, native CAD import, native PMI import, or proprietary branding/assets.

## Source Frames

- `047_00-22-18_report_command_context.jpg`: ribbon Snapshot and Generate Report command context.
- `048_00-22-42_report_save_dialog.jpg`: `Save Report` dialog and existing `css`, `images`, `js`, `report.html` output layout.
- `049_00-22-55_browser_report_open.jpg`: browser report opens on a large snapshot with dark fixed left navigation and white canvas.
- `050_00-23-18_report_stackup_section.jpg`: stackup table, result panel, warning, and contribution section structure.
- `051_00-23-38_report_contribution_section.jpg`: stackup snapshot placement and contribution bars with GD&T-style cells.

## Current Artifacts

- `current_report/report.html`
- `current_report/css/report.css`
- `current_report/js/report.js`
- `current_report/report_manifest.json`
- `current_report/images/snapshot-summary-1.png`
- `current_049_report_open.png`
- `current_051_report_tall.png`
- `current_051_report_contribution_tall.png`

## Browser Capture

The in-app Browser plugin connection timed out during setup, so screenshots were captured with installed Chrome headless:

```powershell
$chrome='C:\Program Files\Google\Chrome\Application\chrome.exe'
$root=(Resolve-Path 'docs/cad_1d_tolerance_tool/extracted_specs/2026-05-16_p25_report_snapshot_html_parity').Path
$report=(Resolve-Path 'docs/cad_1d_tolerance_tool/extracted_specs/2026-05-16_p25_report_snapshot_html_parity/current_report/report.html').Path.Replace('\','/')
$url='file:///'+$report
& $chrome '--headless=new' '--disable-gpu' '--hide-scrollbars' '--run-all-compositor-stages-before-draw' '--virtual-time-budget=1000' '--window-size=1365,768' "--screenshot=$root\current_049_report_open.png" $url
& $chrome '--headless=new' '--disable-gpu' '--hide-scrollbars' '--run-all-compositor-stages-before-draw' '--virtual-time-budget=1000' '--window-size=1365,3000' "--screenshot=$root\current_051_report_tall.png" $url
& $chrome '--headless=new' '--disable-gpu' '--hide-scrollbars' '--run-all-compositor-stages-before-draw' '--virtual-time-budget=1000' '--window-size=1365,4000' "--screenshot=$root\current_051_report_contribution_tall.png" $url
```

## Comparison

| Demo evidence | Current evidence | Match | Remaining difference |
| --- | --- | --- | --- |
| Frames 047-048 | GUI test `test_generate_report_uses_save_report_dialog_records_manifest_and_status` | Save Report dialog title, `.html` suffix normalization, generated status message, and persisted report manifest entry are covered. | Native OS save dialog visuals are not screenshot-captured in automation. |
| Frame 049 | `current_049_report_open.png` | Browser report opens on a large bordered snapshot, with dark fixed left nav and white canvas. | MDTS branding replaces EZtol, and fixture geometry is smaller than the caster assembly. |
| Frame 050 | `current_051_report_tall.png` | Summary/dashboard, per-stackup snapshot, table, result panel, and warning treatment are visible in one browser-rendered capture. | Result values and stackup names come from the committed fixture, not the demo caster project. |
| Frame 051 | `current_051_report_contribution_tall.png` | Contribution section uses blue bars and readable report GD&T/table cells where the fixture has GD&T data. | Exact source microspacing and proprietary report glyph styling remain evidence-limited. |

## Verification

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_cad_tolerance_report
$env:PYTHONPATH='src'; python -m unittest tests.test_cad_tolerance_gui
$env:PYTHONPATH='src'; python -m unittest tests.test_cad_tolerance_project_io
```

All three focused commands passed on 2026-05-16.
