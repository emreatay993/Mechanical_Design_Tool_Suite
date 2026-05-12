"""Sample ExampleScenario rows used by the prototype GUI and tests."""

from __future__ import annotations

from math import cos, pi, sin

from .calculations import BoltLoad


def example_scenario_loads() -> list[BoltLoad]:
    raw_rows = [
        ("BOLT01", -16.7, -165.6, 10856.2, 182.0, -140.0, -4.8),
        ("BOLT02", -5.3, -178.1, 10859.1, 317.7, -27.9, -9.1),
        ("BOLT03", 9.2, -174.0, 10869.2, 311.9, 0.6, -32.8),
        ("BOLT04", 21.9, -156.5, 10857.0, 250.4, 52.6, -42.6),
        ("BOLT05", 33.6, -136.9, 10827.3, 203.8, 104.3, -42.5),
        ("BOLT06", 39.6, -118.7, 10796.5, 144.2, 133.9, -38.4),
        ("BOLT07", 40.8, -107.0, 10753.9, 129.1, 123.0, -45.8),
        ("BOLT08", 52.6, -80.4, 10707.5, 45.9, 153.1, -81.0),
        ("BOLT09", 40.4, -49.8, 10631.8, 30.8, 148.4, -70.8),
    ]

    loads: list[BoltLoad] = []
    radius = 120.0
    for index, row in enumerate(raw_rows):
        angle = 2.0 * pi * index / len(raw_rows)
        loads.append(
            BoltLoad(
                name=row[0],
                fx_n=row[1],
                fy_n=row[2],
                fz_n=row[3],
                mx_nmm=row[4],
                my_nmm=row[5],
                mz_nmm=row[6],
                x_mm=radius * cos(angle),
                y_mm=radius * sin(angle),
                z_mm=0.0,
            )
        )
    return loads


def example_scenario_table_text() -> str:
    header = "NodeID\tX[mm]\tY[mm]\tZ[mm]\tFX[N]\tFY[N]\tFZ[N]\tMX[N*mm]\tMY[N*mm]\tMZ[N*mm]"
    rows = []
    for load in example_scenario_loads():
        rows.append(
            "\t".join(
                [
                    load.name,
                    f"{load.x_mm:.3f}",
                    f"{load.y_mm:.3f}",
                    f"{load.z_mm:.3f}",
                    f"{load.fx_n:.1f}",
                    f"{load.fy_n:.1f}",
                    f"{load.fz_n:.1f}",
                    f"{load.mx_nmm:.1f}",
                    f"{load.my_nmm:.1f}",
                    f"{load.mz_nmm:.1f}",
                ]
            )
        )
    return "\n".join([header, *rows])
