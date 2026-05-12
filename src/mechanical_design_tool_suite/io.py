"""Delimited table parsing for prototype bolt-load input."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from io import StringIO
from typing import Iterable

from .calculations import BoltLoad


REQUIRED_FIELDS = ("fx_n", "fy_n", "fz_n", "mx_nmm", "my_nmm", "mz_nmm")
OPTIONAL_FIELDS = ("name", "x_mm", "y_mm", "z_mm")
ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS


@dataclass(frozen=True)
class ParsedTable:
    loads: list[BoltLoad]
    field_headers: dict[str, str]
    notes: list[str]


@dataclass(frozen=True)
class HeaderInfo:
    canonical: str | None
    unit: str | None
    label: str


def parse_load_table(text: str) -> ParsedTable:
    """Parse a pasted/imported table into internal-unit bolt loads."""
    clean_text = text.strip()
    if not clean_text:
        raise ValueError("Paste or import a table before calculating.")

    rows = _read_delimited_rows(clean_text)
    if len(rows) < 2:
        raise ValueError("The table must contain a header row and at least one data row.")

    raw_headers = [cell.strip() for cell in rows[0]]
    headers = [_parse_header(header) for header in raw_headers]
    field_indexes: dict[str, int] = {}
    field_headers: dict[str, str] = {}
    notes: list[str] = []

    for index, header in enumerate(headers):
        if header.canonical is None:
            if header.label:
                notes.append(f"Ignored unrecognized header: {header.label}")
            continue
        if header.canonical in field_indexes:
            previous = raw_headers[field_indexes[header.canonical]]
            raise ValueError(
                "Duplicate or ambiguous header for "
                f"{header.canonical}: {previous!r} and {raw_headers[index]!r}"
            )
        field_indexes[header.canonical] = index
        field_headers[header.canonical] = raw_headers[index]

    missing = [field for field in REQUIRED_FIELDS if field not in field_indexes]
    if missing:
        names = ", ".join(_display_field_name(field) for field in missing)
        raise ValueError(f"Missing required load columns: {names}")

    loads: list[BoltLoad] = []
    for row_number, row in enumerate(rows[1:], start=2):
        if not any(cell.strip() for cell in row):
            continue
        values: dict[str, str] = {}
        for field, index in field_indexes.items():
            values[field] = row[index].strip() if index < len(row) else ""

        try:
            load = BoltLoad(
                name=values.get("name") or f"ROW{row_number - 1:03d}",
                fx_n=_number(values["fx_n"], row_number, "FX")
                * _unit_factor(headers[field_indexes["fx_n"]], "force"),
                fy_n=_number(values["fy_n"], row_number, "FY")
                * _unit_factor(headers[field_indexes["fy_n"]], "force"),
                fz_n=_number(values["fz_n"], row_number, "FZ")
                * _unit_factor(headers[field_indexes["fz_n"]], "force"),
                mx_nmm=_number(values["mx_nmm"], row_number, "MX")
                * _unit_factor(headers[field_indexes["mx_nmm"]], "moment"),
                my_nmm=_number(values["my_nmm"], row_number, "MY")
                * _unit_factor(headers[field_indexes["my_nmm"]], "moment"),
                mz_nmm=_number(values["mz_nmm"], row_number, "MZ")
                * _unit_factor(headers[field_indexes["mz_nmm"]], "moment"),
                x_mm=_optional_number(values.get("x_mm"), row_number, "X")
                * _unit_factor(headers[field_indexes["x_mm"]], "length")
                if "x_mm" in field_indexes
                else None,
                y_mm=_optional_number(values.get("y_mm"), row_number, "Y")
                * _unit_factor(headers[field_indexes["y_mm"]], "length")
                if "y_mm" in field_indexes
                else None,
                z_mm=_optional_number(values.get("z_mm"), row_number, "Z")
                * _unit_factor(headers[field_indexes["z_mm"]], "length")
                if "z_mm" in field_indexes
                else None,
            )
        except KeyError as exc:
            raise ValueError(f"Missing value for {exc.args[0]!r} on row {row_number}.")
        loads.append(load)

    if not loads:
        raise ValueError("No data rows were found after the header.")

    return ParsedTable(loads=loads, field_headers=field_headers, notes=notes)


def _read_delimited_rows(text: str) -> list[list[str]]:
    sample = text[:2048]
    delimiters = "\t,;|"
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=delimiters)
    except csv.Error:
        dialect = csv.excel_tab if "\t" in text.splitlines()[0] else csv.excel

    rows = list(csv.reader(StringIO(text), dialect))
    if len(rows) == 1 and len(rows[0]) == 1:
        rows = [re.split(r"\s+", line.strip()) for line in text.splitlines()]

    width = max(len(row) for row in rows)
    return [row + [""] * (width - len(row)) for row in rows]


def _parse_header(header: str) -> HeaderInfo:
    label = header.strip()
    unit = None
    match = re.search(r"\s*[\[(]\s*([^)\]]+?)\s*[\])]\s*$", label)
    if match:
        unit = match.group(1)
        label = label[: match.start()].strip()

    normalized = re.sub(r"[^a-z0-9]+", "", label.lower())
    canonical = _canonical_header(normalized)
    return HeaderInfo(canonical=canonical, unit=unit, label=header.strip())


def _canonical_header(normalized: str) -> str | None:
    node_headers = {
        "nodeid",
        "node",
        "nodenumber",
        "bolt",
        "boltid",
        "boltname",
        "name",
        "id",
    }
    if normalized in node_headers:
        return "name"

    force_headers = {
        "fx": "fx_n",
        "forcex": "fx_n",
        "fy": "fy_n",
        "forcey": "fy_n",
        "fz": "fz_n",
        "forcez": "fz_n",
    }
    if normalized in force_headers:
        return force_headers[normalized]

    moment_headers = {
        "mx": "mx_nmm",
        "momentx": "mx_nmm",
        "my": "my_nmm",
        "momenty": "my_nmm",
        "mz": "mz_nmm",
        "momentz": "mz_nmm",
    }
    if normalized in moment_headers:
        return moment_headers[normalized]

    coord_headers = {
        "x": "x_mm",
        "xcoord": "x_mm",
        "xcoordinate": "x_mm",
        "y": "y_mm",
        "ycoord": "y_mm",
        "ycoordinate": "y_mm",
        "z": "z_mm",
        "zcoord": "z_mm",
        "zcoordinate": "z_mm",
    }
    return coord_headers.get(normalized)


def _unit_factor(header: HeaderInfo, category: str) -> float:
    if not header.unit:
        return 1.0

    unit = re.sub(r"[\s_\-]+", "", header.unit.lower())
    unit = unit.replace(".", "*")

    factors = {
        "force": {
            "n": 1.0,
            "kn": 1000.0,
        },
        "moment": {
            "n*mm": 1.0,
            "nmm": 1.0,
            "n*m": 1000.0,
            "nm": 1000.0,
            "kn*mm": 1000.0,
            "knmm": 1000.0,
            "kn*m": 1_000_000.0,
            "knm": 1_000_000.0,
        },
        "length": {
            "mm": 1.0,
            "cm": 10.0,
            "m": 1000.0,
        },
    }

    try:
        return factors[category][unit]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported {category} unit {header.unit!r} in header {header.label!r}."
        ) from exc


def _number(raw_value: str, row_number: int, field_label: str) -> float:
    value = _clean_numeric(raw_value)
    if value == "":
        raise ValueError(f"Missing numeric value for {field_label} on row {row_number}.")
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(
            f"Invalid numeric value for {field_label} on row {row_number}: {raw_value!r}"
        ) from exc


def _optional_number(
    raw_value: str | None,
    row_number: int,
    field_label: str,
) -> float | None:
    if raw_value is None:
        return None
    value = _clean_numeric(raw_value)
    if value == "":
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(
            f"Invalid numeric value for {field_label} on row {row_number}: {raw_value!r}"
        ) from exc


def _clean_numeric(raw_value: str) -> str:
    value = raw_value.strip()
    if "," in value and "." in value:
        value = value.replace(",", "")
    return value


def _display_field_name(field: str) -> str:
    return {
        "fx_n": "FX",
        "fy_n": "FY",
        "fz_n": "FZ",
        "mx_nmm": "MX",
        "my_nmm": "MY",
        "mz_nmm": "MZ",
    }.get(field, field)
