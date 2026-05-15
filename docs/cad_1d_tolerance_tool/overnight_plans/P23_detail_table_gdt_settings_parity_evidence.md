# P23 Detail Table GDT Settings Parity Evidence

Date: 2026-05-16

## Evidence Sources

- Packet: `docs/cad_1d_tolerance_tool/overnight_plans/P23_detail_table_gdt_settings_parity.md`
- Productization plan task T07: `docs/cad_1d_tolerance_tool/10_full_clone_productization_plan.md`
- Targeted visual review sections `00:07:05-00:13:55`
- Transcript cues `00:07:01-00:13:49` and shared-dimension cue `00:21:26-00:21:42`
- Key frames inspected: `014`, `016`, `019`, `025`, `026`, `028`, and `045`
- Unicode symbol references:
  - Tech Soft 3D HOOPS GD&T appendix maps circular runout to `U+2197`, profile of surface to `U+2313`, and position to `U+2316`: <https://docs.techsoft3d.com/hps/latest/prog_guide/appendix_gdt.html>
  - CAx-IF recommended Unicode strings list position `⌖` / `2316`, profile of a surface `⌓` / `2313`, and total runout `⌰` / `2330`: <https://www.mbx-if.org/home/wp-content/uploads/2024/05/rec_prac_unicode_strings_v1_20230425.pdf>

## Implemented Evidence

- Dense detail table continues to use the observed columns `Name`, `Sens`, `Nominal`, `Tolerance`, and `Datum` with compact editable rows.
- Inline tolerance editing supports symmetric, limits/asymmetric, and geometric/manual text entries through the tolerance-cell delegate.
- Project settings now persist block tolerance, default result mode, and default quality metric alongside existing sigma/Cpk defaults. No schema migration was required because the new settings fields have loader defaults.
- The settings dialog exposes block tolerance, default result mode, default quality metric, target quality value, sigma coverage, and an optional apply-to-existing-stackups path.
- Manual GD&T/GPS entry validates controlled feature, positive tolerance value, and known datum/reference tokens before enabling OK.
- GD&T rows render a readable Unicode-and-text feature-control-frame form such as `[⌖ Position | ⌀0.15 | A]` instead of relying on unreadable source glyphs.
- Datum/reference validation accepts known datum labels and known feature references, while rejecting unknown references such as `Z`.
- Shared-dimension warnings now include affected stackup labels in both tooltip/status feedback, for example `overall height`.

## Fidelity Gaps Preserved

- Exact GD&T symbol glyphs and material-condition modifiers remain unreadable in the available crops, so P23 uses text labels rather than invented symbols.
- Native CAD PMI import remains out of scope.

## Verification

```powershell
$env:PYTHONPATH="src"; python -m unittest tests.test_cad_tolerance_domain tests.test_cad_tolerance_editing tests.test_cad_tolerance_gui tests.test_cad_tolerance_project_io
```

Result: passed, 47 tests.
