# Tolerance Tool Calculation Methods

This document defines the calculation methodology for the standalone tolerance
analysis GUI. The implemented source of truth is
[`../../src/bolt_calculation_tool/tolerance.py`](../../src/bolt_calculation_tool/tolerance.py).

## Calculation Scope

The implemented calculator handles a one-dimensional additive tolerance stackup.
Each input dimension has:

| Input | Meaning |
| --- | --- |
| `name` | User-facing row label. Blank names are replaced with `#<row>`. |
| `nominal` | Nominal contribution to the stackup. |
| `tolerance` | Symmetric bilateral tolerance around the nominal value. |

The stackup also has:

| Input | Meaning |
| --- | --- |
| `target_min` | Lower acceptable assembly dimension. |
| `target_max` | Upper acceptable assembly dimension. |

All values are plain floats in the current implementation. No unit conversion is
performed, so the user must enter all dimensions, tolerances, and target limits
in a consistent unit system.

## Validation Rules

| Rule | Behavior |
| --- | --- |
| Empty dimension list | Rejected with `Add at least one dimension.` |
| Blank full UI row | Ignored by the GUI adapter before calculation. |
| Blank name | Replaced by `#<row>`. |
| Missing nominal in a partial UI row | Rejected by the GUI before calculation. |
| Missing tolerance in a partial UI row | Rejected by the GUI before calculation. |
| Non-numeric value | Rejected. |
| Infinite or NaN value | Rejected. |
| Negative tolerance | Rejected. |
| `target_min > target_max` | Rejected. |

## Dimension Terms

The current Five Flute-style convention treats each bilateral tolerance as a
plus/minus 3-sigma interval:

```text
sigma_i = tolerance_i / 3
variance_i = sigma_i^2
```

Each dimension row displayed by the GUI reports:

```text
nominal_i
tolerance_i
sigma_i
variance_i
```

## Nominal Stackup

The nominal stackup is the sum of all nominal dimension contributions:

```text
nominal_stackup = sum(nominal_i)
```

The current model assumes every entered dimension contributes additively. If
subtractive dimensions are required later, the data model should add an explicit
sign or direction instead of relying on users to enter negative nominal values.

## Worst-Case Stackup

Worst-case tolerance is the linear sum of all bilateral tolerances:

```text
worst_case_tolerance = sum(tolerance_i)
worst_case_min = nominal_stackup - worst_case_tolerance
worst_case_max = nominal_stackup + worst_case_tolerance
```

The implementation also reports display terms for worst-case standard deviation
and variance:

```text
worst_case_std_deviation = worst_case_tolerance / 3
worst_case_variance = worst_case_std_deviation^2
```

These display terms preserve the same 3-sigma convention as the per-dimension
rows. They are not used for RSS tail-risk calculation.

## RSS Stackup

RSS assumes dimension contributors are independent and normally distributed.
The stackup variance is the sum of per-dimension variances:

```text
rss_variance = sum(variance_i)
rss_std_deviation = sqrt(rss_variance)
rss_tolerance = rss_std_deviation * 3
rss_min = nominal_stackup - rss_tolerance
rss_max = nominal_stackup + rss_tolerance
```

## RSS Tail-Risk Estimate

The RSS risk model uses a normal distribution:

```text
X ~ Normal(nominal_stackup, rss_std_deviation)
```

Tail failure rates are:

```text
left_tail_failure_rate = P(X < target_min)
right_tail_failure_rate = P(X > target_max)
```

In implementation terms:

```text
left_tail_failure_rate = NormalDist(mu=nominal, sigma=rss_sigma).cdf(target_min)
right_tail_failure_rate = 1 - NormalDist(mu=nominal, sigma=rss_sigma).cdf(target_max)
```

Rates are clamped to the inclusive range `[0, 1]`.

When `rss_std_deviation` is zero, the distribution is deterministic:

| Condition | Left rate | Right rate |
| --- | --- | --- |
| `nominal_stackup < target_min` | `1.0` | `0.0` unless also above max, which cannot happen with ordered targets |
| `nominal_stackup > target_max` | `0.0` | `1.0` |
| Inside target range | `0.0` | `0.0` |

## Current Default Example

The default regression example uses four dimensions:

| Name | Nominal | Tolerance |
| --- | --- | --- |
| `#1` | `1.0` | `0.005` |
| `#2` | `1.0` | `0.005` |
| `#3` | `1.0` | `0.005` |
| `#4` | `1.0` | `0.005` |

With `target_min = 0.001` and `target_max = 0.022`, the executable tests expect:

| Output | Expected value |
| --- | --- |
| Nominal stackup | `4.0` |
| Worst-case tolerance | `0.0200` |
| Worst-case standard deviation | `0.0066666667` |
| Worst-case variance | `0.0000444444` |
| RSS tolerance | `0.0100` |
| RSS standard deviation | `0.0033333333` |
| RSS variance | `0.0000111111` |
| RSS left-tail failure rate | `0.0` |
| RSS right-tail failure rate | `1.0` |

The target limits in this saved example are intentionally retained because they
match the current regression test, even though the nominal stackup is far above
the target maximum.

## Assumptions And Limitations

| Area | Current assumption |
| --- | --- |
| Tolerance form | Symmetric bilateral tolerance only. |
| Distribution | Normal per dimension under the plus/minus 3-sigma convention. |
| Dependency | Independent dimension contributors for RSS. |
| Correlation | No covariance or correlation terms. |
| Units | No explicit unit metadata or conversion. |
| Direction | Additive nominal stackup. |
| Process shift | No mean shift, Cpk, or capability model. |
| Simulation | No Monte Carlo path in live code. |
| Optimization | No cost/yield or tolerance recommendation logic in live code. |
