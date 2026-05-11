# Tolerance Tool Verification And Validation Plan

This document defines the verification plan for the standalone tolerance
analysis GUI and its calculation layer.

## Verification Objective

The tool shall correctly calculate a one-dimensional tolerance stackup with:

```text
nominal stackup
per-dimension standard deviations and variances
worst-case tolerance range
RSS tolerance range
RSS left-tail and right-tail failure rates
```

It shall also present the results consistently in the GUI and export the current
analysis to PDF and PNG without stale or invalid output.

## Level 1: Calculation Unit Tests

Calculation tests should exercise `calculate_stackup` directly.

Required cases:

| Case | Expected check |
| --- | --- |
| Default four-row example | Matches nominal, worst-case, RSS, variance, and tail-risk values in the existing test. |
| Single dimension | Worst-case and RSS tolerance both equal the single input tolerance. |
| Mixed nominal signs | Nominal stackup equals the algebraic sum of nominal values. |
| Zero tolerance | RSS sigma is zero and deterministic tail-risk behavior is used. |
| Negative tolerance | Raises `ValueError`. |
| Non-finite input | Raises `ValueError`. |
| Non-numeric input | Raises `ValueError`. |
| Empty dimension list | Raises `ValueError`. |
| `target_min > target_max` | Raises `ValueError`. |
| Blank dimension name | Normalizes to a row-style name. |

Current executable coverage exists in
[`../../tests/test_tolerance_analysis.py`](../../tests/test_tolerance_analysis.py)
for the default example, negative tolerance rejection, and target ordering.

## Level 2: GUI Integration Tests

GUI tests should verify:

| Behavior | Expected check |
| --- | --- |
| Startup | Four default dimension rows are present and an analysis is displayed. |
| Editing a nominal value | Plot, table, and status line update. |
| Editing target limits | Tail-risk rows and plot target markers update. |
| Add dimension | A new row appears and recalculation runs. |
| Remove dimension | The selected row is removed and recalculation runs. |
| Clear | Outputs clear and a controlled input error is shown. |
| Blank full row | Row is ignored. |
| Partial row | Controlled row-specific input error is shown. |
| Invalid target ordering | Controlled target-ordering input error is shown. |
| Recovered valid input | Plot and table repopulate after fixing the error. |

Automated GUI tests can use Qt test utilities if the project adopts them. Until
then, these behaviors should be checked manually before release.

## Level 3: Export Tests

Export verification should cover:

| Case | Expected check |
| --- | --- |
| PDF export | File is created, non-empty, and contains the current page rendering. |
| PNG export | File is created, non-empty, and visually matches the current page. |
| Title-derived filename | Unsafe filename characters are removed or replaced. |
| Empty title | Default filename stem is used. |
| Export cancellation | No error status is shown. |
| Export failure | Controlled error status is shown. |

PDF/PNG outputs should be visually inspected after major UI changes because the
export path renders live widgets.

## Level 4: Manual Review Checklist

Before a release or handoff:

| Check | Acceptance |
| --- | --- |
| Method labels | UI and docs consistently use worst case, RSS/root sum squared, target min/max, and tail risk. |
| Units | Any absence of unit handling is explicit in docs or UI. |
| Disabled save | Product decision is documented: implement persistence or remove the disabled action. |
| Packaging | Selector and direct executable launch paths are documented and tested. |
| Main GUI relationship | It is clear whether the tolerance GUI is standalone or integrated. |
| Mockup drift | Future UI work based on `tolerance_stackup_mockups.html` does not claim unsupported methods are implemented. |

## Regression Commands

From the repository root:

```powershell
$env:PYTHONPATH="src"; python -m unittest tests.test_tolerance_analysis
```

To run all current backend tests:

```powershell
$env:PYTHONPATH="src"; python -m unittest discover -s tests
```

To launch the GUI for manual verification:

```powershell
python scripts\run_tolerance_analysis.py
```

## Known Gaps

| Gap | Risk |
| --- | --- |
| Limited calculation unit tests | Some edge cases are documented but not yet executable tests. |
| No automated GUI test coverage | Recalculation, validation, and export regressions could be missed. |
| No persistence workflow | Users cannot reopen editable tolerance analyses. |
| No explicit unit support | Users can mix units accidentally. |
