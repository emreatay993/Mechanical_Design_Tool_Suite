"""Tkinter prototype GUI for the ExampleScenario bolt calculation tool."""

from __future__ import annotations

import csv
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .calculations import (
    MARGIN_BASIS_MINOR,
    SUPPORTED_MARGIN_BASES,
    BoltCalculationResult,
    available_bolt_sizes,
    calculate_bolt_group,
    resolve_constants,
)
from .io import ParsedTable, parse_load_table
from .sample_data import example_scenario_table_text
from .visualization import SCALAR_CHOICES, open_pyvista_plot, results_have_coordinates


class BoltCalculationApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Bolt Calculation Tool Prototype")
        self.geometry("1320x820")
        self.minsize(980, 640)

        self.results: list[BoltCalculationResult] = []
        self.parsed_table: ParsedTable | None = None

        self.bolt_size = tk.StringVar(value=available_bolt_sizes()[0])
        self.margin_basis = tk.StringVar(value=MARGIN_BASIS_MINOR)
        self.design_path = tk.StringVar(value="ExampleScenario / INCO718 BAR / 250 C")
        self.coordinate_system = tk.StringVar(value="Local bolt coordinates")
        self.scalar_choice = tk.StringVar(value="Margin")
        self.status_text = tk.StringVar(value="Load the example table or paste your own load table.")

        self._configure_style()
        self._build_layout()
        self._load_example()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        if sys.platform == "win32":
            style.theme_use("vista")
        style.configure("Status.TLabel", font=("Segoe UI", 10, "bold"))
        style.configure("Small.TLabel", font=("Segoe UI", 9))
        style.configure("Treeview", rowheight=24)

    def _build_layout(self) -> None:
        root = ttk.Frame(self, padding=10)
        root.pack(fill=tk.BOTH, expand=True)

        toolbar = ttk.Frame(root)
        toolbar.pack(fill=tk.X)

        self._labeled_combo(
            toolbar,
            "Bolt size",
            self.bolt_size,
            available_bolt_sizes(),
            width=12,
        ).pack(side=tk.LEFT, padx=(0, 10))
        self._labeled_combo(
            toolbar,
            "Margin basis",
            self.margin_basis,
            list(SUPPORTED_MARGIN_BASES),
            width=14,
        ).pack(side=tk.LEFT, padx=(0, 10))
        self._labeled_combo(
            toolbar,
            "Criteria",
            self.design_path,
            ["ExampleScenario / INCO718 BAR / 250 C"],
            width=34,
        ).pack(side=tk.LEFT, padx=(0, 10))
        self._labeled_combo(
            toolbar,
            "Coordinates",
            self.coordinate_system,
            ["Local bolt coordinates", "Global coordinates"],
            width=22,
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(toolbar, text="Load Example", command=self._load_example).pack(
            side=tk.LEFT, padx=(4, 0)
        )
        ttk.Button(toolbar, text="Paste", command=self._paste_clipboard).pack(
            side=tk.LEFT, padx=(4, 0)
        )
        ttk.Button(toolbar, text="Import", command=self._import_table).pack(
            side=tk.LEFT, padx=(4, 0)
        )
        ttk.Button(toolbar, text="Calculate", command=self._calculate).pack(
            side=tk.LEFT, padx=(4, 0)
        )
        ttk.Button(toolbar, text="Export", command=self._export_results).pack(
            side=tk.LEFT, padx=(4, 0)
        )

        viz_frame = ttk.Frame(toolbar)
        viz_frame.pack(side=tk.RIGHT)
        ttk.Label(viz_frame, text="Contour").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Combobox(
            viz_frame,
            textvariable=self.scalar_choice,
            values=list(SCALAR_CHOICES),
            state="readonly",
            width=18,
        ).pack(side=tk.LEFT)
        ttk.Button(viz_frame, text="Visualize", command=self._visualize).pack(
            side=tk.LEFT, padx=(4, 0)
        )

        ttk.Label(root, textvariable=self.status_text, style="Status.TLabel").pack(
            fill=tk.X, pady=(10, 8)
        )

        paned = ttk.PanedWindow(root, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)

        input_frame = ttk.Frame(paned)
        output_frame = ttk.Frame(paned)
        paned.add(input_frame, weight=2)
        paned.add(output_frame, weight=3)

        input_tabs = ttk.Notebook(input_frame)
        input_tabs.pack(fill=tk.BOTH, expand=True)

        paste_frame = ttk.Frame(input_tabs, padding=4)
        preview_frame = ttk.Frame(input_tabs, padding=4)
        input_tabs.add(paste_frame, text="Input Table")
        input_tabs.add(preview_frame, text="Parsed Loads")

        self.input_text = tk.Text(
            paste_frame,
            height=12,
            wrap="none",
            undo=True,
            font=("Consolas", 10),
        )
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        input_y = ttk.Scrollbar(paste_frame, orient=tk.VERTICAL, command=self.input_text.yview)
        input_x = ttk.Scrollbar(paste_frame, orient=tk.HORIZONTAL, command=self.input_text.xview)
        self.input_text.configure(yscrollcommand=input_y.set, xscrollcommand=input_x.set)
        input_y.pack(side=tk.RIGHT, fill=tk.Y)
        input_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.preview_tree = self._tree(
            preview_frame,
            ("Bolt", "X", "Y", "Z", "FX", "FY", "FZ", "MX", "MY", "MZ"),
        )

        output_tabs = ttk.Notebook(output_frame)
        output_tabs.pack(fill=tk.BOTH, expand=True)

        results_frame = ttk.Frame(output_tabs, padding=4)
        trace_frame = ttk.Frame(output_tabs, padding=4)
        output_tabs.add(results_frame, text="Results")
        output_tabs.add(trace_frame, text="Trace")

        self.results_tree = self._tree(
            results_frame,
            (
                "Bolt",
                "Tensile",
                "Fiber",
                "LCF alt",
                "Life",
                "Crush Bolt",
                "Crush Nut",
                "PLUG",
                "SHEAR",
                "BENDING",
                "Torsion",
                "Rt",
                "Rb",
                "Rs",
                "Rst",
                "Margin",
                "Status",
                "Governing",
            ),
        )

        self.trace_text = tk.Text(
            trace_frame,
            wrap="word",
            state="disabled",
            font=("Consolas", 10),
        )
        self.trace_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        trace_scroll = ttk.Scrollbar(trace_frame, orient=tk.VERTICAL, command=self.trace_text.yview)
        self.trace_text.configure(yscrollcommand=trace_scroll.set)
        trace_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _labeled_combo(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.StringVar,
        values: list[str],
        width: int,
    ) -> ttk.Frame:
        frame = ttk.Frame(parent)
        ttk.Label(frame, text=label, style="Small.TLabel").pack(anchor=tk.W)
        ttk.Combobox(
            frame,
            textvariable=variable,
            values=values,
            state="readonly",
            width=width,
        ).pack(fill=tk.X)
        return frame

    def _tree(self, parent: ttk.Frame, columns: tuple[str, ...]) -> ttk.Treeview:
        wrapper = ttk.Frame(parent)
        wrapper.pack(fill=tk.BOTH, expand=True)
        tree = ttk.Treeview(wrapper, columns=columns, show="headings")
        for column in columns:
            tree.heading(column, text=column)
            tree.column(column, width=self._column_width(column), anchor=tk.E)
        tree.column(columns[0], anchor=tk.W)
        y_scroll = ttk.Scrollbar(wrapper, orient=tk.VERTICAL, command=tree.yview)
        x_scroll = ttk.Scrollbar(wrapper, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        x_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        return tree

    def _column_width(self, column: str) -> int:
        widths = {
            "Bolt": 90,
            "Life": 80,
            "Status": 70,
            "Governing": 130,
            "Margin": 90,
        }
        return widths.get(column, 92)

    def _load_example(self) -> None:
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", example_scenario_table_text())
        self.status_text.set("ExampleScenario rows loaded. Click Calculate to refresh results.")

    def _paste_clipboard(self) -> None:
        try:
            text = self.clipboard_get()
        except tk.TclError:
            messagebox.showerror("Paste failed", "The clipboard does not contain text.")
            return
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", text)
        self.status_text.set("Clipboard table pasted. Click Calculate to validate headers and run.")

    def _import_table(self) -> None:
        path = filedialog.askopenfilename(
            title="Import load table",
            filetypes=[
                ("Delimited tables", "*.csv *.tsv *.txt"),
                ("CSV files", "*.csv"),
                ("TSV files", "*.tsv"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        table_text = Path(path).read_text(encoding="utf-8-sig")
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", table_text)
        self.status_text.set(f"Imported {Path(path).name}. Click Calculate to run.")

    def _calculate(self) -> None:
        try:
            parsed = parse_load_table(self.input_text.get("1.0", tk.END))
            constants = resolve_constants(self.bolt_size.get(), self.margin_basis.get())
            results = calculate_bolt_group(parsed.loads, constants)
        except Exception as exc:
            messagebox.showerror("Calculation failed", str(exc))
            self.status_text.set("Calculation failed. Fix the input table and retry.")
            return

        self.parsed_table = parsed
        self.results = results
        self._fill_preview(parsed)
        self._fill_results(results)
        self._fill_trace(parsed, results)
        self._update_status(results)

    def _fill_preview(self, parsed: ParsedTable) -> None:
        self.preview_tree.delete(*self.preview_tree.get_children())
        for load in parsed.loads:
            self.preview_tree.insert(
                "",
                tk.END,
                values=(
                    load.name,
                    self._fmt_optional(load.x_mm, 3),
                    self._fmt_optional(load.y_mm, 3),
                    self._fmt_optional(load.z_mm, 3),
                    self._fmt(load.fx_n, 2),
                    self._fmt(load.fy_n, 2),
                    self._fmt(load.fz_n, 2),
                    self._fmt(load.mx_nmm, 2),
                    self._fmt(load.my_nmm, 2),
                    self._fmt(load.mz_nmm, 2),
                ),
            )

    def _fill_results(self, results: list[BoltCalculationResult]) -> None:
        self.results_tree.delete(*self.results_tree.get_children())
        for result in results:
            strength = result.strength
            interaction = result.interaction
            self.results_tree.insert(
                "",
                tk.END,
                values=(
                    result.load.name,
                    self._fmt(strength.tensile_mpa, 1),
                    self._fmt(strength.fiber_mpa, 1),
                    self._fmt(strength.lcf_alt_mpa, 1),
                    strength.life,
                    self._fmt(strength.crush_bolt_mpa, 1),
                    self._fmt(strength.crush_nut_mpa, 1),
                    self._fmt(interaction.plug_n, 1),
                    self._fmt(interaction.shear_n, 1),
                    self._fmt(interaction.bending_nmm, 1),
                    self._fmt(interaction.torsion_nmm, 1),
                    self._fmt(interaction.rt, 3),
                    self._fmt(interaction.rb, 3),
                    self._fmt(interaction.rs, 3),
                    self._fmt(interaction.rst, 3),
                    self._fmt_margin(interaction.margin),
                    result.status,
                    result.governing_check,
                ),
            )

    def _fill_trace(
        self,
        parsed: ParsedTable,
        results: list[BoltCalculationResult],
    ) -> None:
        constants = resolve_constants(self.bolt_size.get(), self.margin_basis.get())
        notes = "\n".join(f"- {note}" for note in parsed.notes) or "- none"
        field_map = "\n".join(
            f"- {field}: {header}" for field, header in sorted(parsed.field_headers.items())
        )
        text = f"""Design path: {self.design_path.get()}
Coordinate system: {self.coordinate_system.get()}

Resolved constants:
- bolt_size: {constants.bolt_size}
- margin_basis: {constants.margin_basis}
- bolt_thread_area_mm2: {constants.bolt_thread_area_mm2:.10f}
- bolt_radius_mm: {constants.bolt_radius_mm:.10f}
- moment_of_inertia_mm4: {constants.moment_of_inertia_mm4:.10f}
- polar_moment_of_inertia_mm4: {constants.polar_moment_of_inertia_mm4:.10f}
- bolt_contact_crush_area_mm2: {constants.bolt_contact_crush_area_mm2:.10f}
- nut_contact_crush_area_min_mm2: {constants.nut_contact_crush_area_min_mm2:.10f}
- assembly_tensile_stress_mpa: {constants.assembly_tensile_stress_mpa:.10f}
- walker_coefficient: {constants.walker_coefficient:.10f}
- yield_002_mpa: {constants.yield_002_mpa:.10f}
- shear_strength_mpa: {constants.shear_strength_mpa:.10f}

Imported rows: {len(parsed.loads)}
Rows with coordinates: {"yes" if results_have_coordinates(results) else "no"}

Header map:
{field_map}

Parser notes:
{notes}

Implementation note:
This prototype uses the documented ExampleScenario reference behavior in N,
N*mm, mm, mm^2, mm^4, and MPa. Other bolt sizes are listed in the source lookup
formulas, but complete prototype constants are currently documented for .2500-28.
"""
        self.trace_text.configure(state="normal")
        self.trace_text.delete("1.0", tk.END)
        self.trace_text.insert("1.0", text)
        self.trace_text.configure(state="disabled")

    def _update_status(self, results: list[BoltCalculationResult]) -> None:
        fail_count = sum(1 for result in results if result.status == "FAIL")
        finite_results = [
            result
            for result in results
            if result.interaction.margin != float("inf")
        ]
        governing = min(
            finite_results,
            key=lambda result: result.interaction.margin,
            default=None,
        )
        if governing is None:
            margin_text = "all margins infinite"
        else:
            margin_text = (
                f"governing {governing.load.name}: "
                f"{governing.interaction.margin * 100.0:.0f}%"
            )
        self.status_text.set(
            f"{len(results)} bolts calculated, {fail_count} failures, {margin_text}."
        )

    def _visualize(self) -> None:
        try:
            open_pyvista_plot(self.results, self.scalar_choice.get())
        except Exception as exc:
            messagebox.showerror("Visualization unavailable", str(exc))

    def _export_results(self) -> None:
        if not self.results:
            messagebox.showinfo("No results", "Calculate results before exporting.")
            return
        path = filedialog.asksaveasfilename(
            title="Export results",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        with Path(path).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "Bolt",
                    "Tensile Stress MPa",
                    "Fiber Stress MPa",
                    "LCF sigma_alt MPa",
                    "Life",
                    "Flange Crush Stress Bolt MPa",
                    "Flange Crush Stress Nut MPa",
                    "PLUG N",
                    "SHEAR N",
                    "BENDING N*mm",
                    "Torsion N*mm",
                    "Rt",
                    "Rb",
                    "Rs",
                    "Rst",
                    "Margin",
                    "Status",
                    "Governing",
                ]
            )
            for result in self.results:
                strength = result.strength
                interaction = result.interaction
                writer.writerow(
                    [
                        result.load.name,
                        strength.tensile_mpa,
                        strength.fiber_mpa,
                        strength.lcf_alt_mpa,
                        strength.life,
                        strength.crush_bolt_mpa,
                        strength.crush_nut_mpa,
                        interaction.plug_n,
                        interaction.shear_n,
                        interaction.bending_nmm,
                        interaction.torsion_nmm,
                        interaction.rt,
                        interaction.rb,
                        interaction.rs,
                        interaction.rst,
                        interaction.margin,
                        result.status,
                        result.governing_check,
                    ]
                )
        self.status_text.set(f"Exported results to {Path(path).name}.")

    def _fmt(self, value: float, decimals: int) -> str:
        return f"{value:.{decimals}f}"

    def _fmt_optional(self, value: float | None, decimals: int) -> str:
        if value is None:
            return ""
        return self._fmt(value, decimals)

    def _fmt_margin(self, margin: float) -> str:
        if margin == float("inf"):
            return "inf"
        return f"{margin * 100.0:.0f}%"


def main() -> None:
    app = BoltCalculationApp()
    app.mainloop()


if __name__ == "__main__":
    main()
