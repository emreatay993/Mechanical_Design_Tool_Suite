from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from openpyxl import Workbook

from bolt_calculation_tool.tolerance_catalog import ToleranceCatalog
from bolt_calculation_tool.tolerance_methods import calculate_sub_joint_result
from bolt_calculation_tool.tolerance_spreadsheet_io import load_spreadsheet_project


class ToleranceSpreadsheetImportTest(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = ToleranceCatalog.builtin()

    def test_csv_import_creates_project_with_asymmetric_tolerances(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stackups.csv"
            path.write_text(
                "\n".join(
                    [
                        "project_title,unit_system,joint,sub_joint,item_type,item_name,nominal_thickness,tolerance_minus,tolerance_plus,bolt_size,bolt_type,bolt_length,engagement_type",
                        "Imported Assembly,mm,JOINT A,JOINT A.1,flange,Flange 1,5,0.10,0.20,0.190,PD Shank,17.5,nut",
                        "Imported Assembly,mm,JOINT A,JOINT A.1,flange,Flange 2,4,0.25,0.25,0.190,PD Shank,17.5,nut",
                        "Imported Assembly,mm,JOINT A,JOINT A.1,custom,Shim,1,0.05,0.10,0.190,PD Shank,17.5,nut",
                    ]
                ),
                encoding="utf-8",
            )

            project = load_spreadsheet_project(path, self.catalog)

        joint = project.joints[0]
        sub_joint = joint.sub_joints[0]
        result = calculate_sub_joint_result(joint, sub_joint, self.catalog)
        self.assertEqual(project.title, "Imported Assembly")
        self.assertEqual(len(joint.flanges), 2)
        self.assertEqual(len(sub_joint.stackup_path.items), 3)
        self.assertAlmostEqual(result.stackup.nominal, 10.0)
        self.assertAlmostEqual(result.stackup.worst_case_minus, 0.40)
        self.assertAlmostEqual(result.stackup.worst_case_plus, 0.55)

    def test_xlsx_import_reads_stackups_sheet(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stackups.xlsx"
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "stackups"
            sheet.append(
                [
                    "project_title",
                    "unit_system",
                    "joint",
                    "sub_joint",
                    "item_type",
                    "item_name",
                    "nominal_thickness",
                    "tolerance",
                ]
            )
            sheet.append(["XLSX Import", "mm", "JOINT X", "JOINT X.1", "flange", "Flange 1", 2.0, 0.1])
            workbook.save(path)

            project = load_spreadsheet_project(path, self.catalog)

        self.assertEqual(project.title, "XLSX Import")
        self.assertEqual(project.joints[0].name, "JOINT X")
        self.assertEqual(project.joints[0].flanges[0].tolerance_plus, 0.1)

    def test_duplicate_flange_conflict_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "conflict.csv"
            path.write_text(
                "\n".join(
                    [
                        "joint,sub_joint,item_type,item_name,nominal_thickness,tolerance",
                        "JOINT A,JOINT A.1,flange,Flange 1,5,0.1",
                        "JOINT A,JOINT A.2,flange,Flange 1,6,0.1",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "conflicting values"):
                load_spreadsheet_project(path, self.catalog)


if __name__ == "__main__":
    unittest.main()
