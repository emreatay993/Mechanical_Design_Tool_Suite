"""Generate small neutral CAD fixtures for the CAD 1D tolerance adapter tests."""

from __future__ import annotations

from pathlib import Path

from OCC.Core.BRep import BRep_Builder
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.IGESControl import IGESControl_Writer
from OCC.Core.Interface import Interface_Static
from OCC.Core.STEPControl import STEPControl_AsIs, STEPControl_Writer
from OCC.Core.TopoDS import TopoDS_Compound
from OCC.Core.gp import gp_Ax2, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec


FIXTURE_DIR = Path(__file__).resolve().parent


def main() -> None:
    write_step(FIXTURE_DIR / "neutral_step_two_part_loop.step", two_body_loop())
    write_iges(FIXTURE_DIR / "neutral_iges_single_part.igs", cylinder_part())
    write_step(FIXTURE_DIR / "offset_rotational_warning.step", offset_loop())


def two_body_loop() -> TopoDS_Compound:
    bracket = BRepPrimAPI_MakeBox(20.0, 30.0, 10.0).Shape()
    bushing = BRepPrimAPI_MakeCylinder(
        gp_Ax2(gp_Pnt(35.0, 15.0, 0.0), gp_Dir(0.0, 0.0, 1.0)),
        5.0,
        10.0,
    ).Shape()
    return compound([bracket, bushing])


def cylinder_part() -> object:
    return BRepPrimAPI_MakeCylinder(
        gp_Ax2(gp_Pnt(0.0, 0.0, 0.0), gp_Dir(0.0, 0.0, 1.0)),
        8.0,
        25.0,
    ).Shape()


def offset_loop() -> TopoDS_Compound:
    base = BRepPrimAPI_MakeBox(20.0, 20.0, 8.0).Shape()
    moved = translate(
        BRepPrimAPI_MakeCylinder(
            gp_Ax2(gp_Pnt(0.0, 0.0, 0.0), gp_Dir(0.0, 0.0, 1.0)),
            4.0,
            8.0,
        ).Shape(),
        30.0,
        12.0,
        0.0,
    )
    return compound([base, moved])


def translate(shape: object, x: float, y: float, z: float) -> object:
    transform = gp_Trsf()
    transform.SetTranslation(gp_Vec(x, y, z))
    return BRepBuilderAPI_Transform(shape, transform, True).Shape()


def compound(shapes: list[object]) -> TopoDS_Compound:
    builder = BRep_Builder()
    result = TopoDS_Compound()
    builder.MakeCompound(result)
    for shape in shapes:
        builder.Add(result, shape)
    return result


def write_step(path: Path, shape: object) -> None:
    Interface_Static.SetCVal("write.step.schema", "AP214")
    Interface_Static.SetCVal("write.step.unit", "MM")
    writer = STEPControl_Writer()
    transfer_status = writer.Transfer(shape, STEPControl_AsIs)
    if transfer_status != IFSelect_RetDone:
        raise RuntimeError(f"STEP transfer failed for {path}.")
    write_status = writer.Write(str(path))
    if write_status != IFSelect_RetDone:
        raise RuntimeError(f"STEP write failed for {path}.")


def write_iges(path: Path, shape: object) -> None:
    writer = IGESControl_Writer("MM", 0)
    writer.AddShape(shape)
    if not writer.Write(str(path)):
        raise RuntimeError(f"IGES write failed for {path}.")


if __name__ == "__main__":
    main()
