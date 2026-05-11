# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules


project_root = Path(SPECPATH).resolve()
src_root = project_root / "src"
sys.path.insert(0, str(src_root))

entry_scripts = [
    ("BoltCalculationTool", project_root / "scripts" / "run_launcher.py"),
    ("BoltCalculationGui", project_root / "scripts" / "run_gui.py"),
    ("ToleranceAnalysis", project_root / "scripts" / "run_tolerance_analysis.py"),
    ("ToleranceAnalysisVNext", project_root / "scripts" / "run_tolerance_vnext_analysis.py"),
]


datas = []
binaries = []
hiddenimports = []

for package_name in (
    "bolt_calculation_tool",
    "PyQt6",
    "pyvista",
    "vtk",
    "vtkmodules",
    "numpy",
    "openpyxl",
):
    package_datas, package_binaries, package_hiddenimports = collect_all(package_name)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

hiddenimports += collect_submodules("bolt_calculation_tool")
hiddenimports += collect_submodules("openpyxl")
hiddenimports += [
    "PyQt6.QtQml",
    "PyQt6.QtQuick",
    "PyQt6.QtQuickWidgets",
    "vtkmodules.all",
    "vtkmodules.qt.QVTKRenderWindowInteractor",
]

for data_path in (
    src_root / "bolt_calculation_tool" / "data" / "tolerance_catalog.json",
    src_root / "bolt_calculation_tool" / "qml" / "tolerance_vnext.qml",
):
    if data_path.exists():
        datas.append((str(data_path), str(data_path.parent.relative_to(src_root))))


a = Analysis(
    [str(script_path) for _, script_path in entry_scripts],
    pathex=[str(src_root), str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=sorted(set(hiddenimports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exes = []
for index, (name, _) in enumerate(entry_scripts):
    exes.append(
        EXE(
            pyz,
            a.scripts[index : index + 1],
            [],
            exclude_binaries=True,
            name=name,
            debug=False,
            bootloader_ignore_signals=False,
            strip=False,
            upx=False,
            console=False,
            disable_windowed_traceback=False,
            argv_emulation=False,
            target_arch=None,
            codesign_identity=None,
            entitlements_file=None,
        )
    )

coll = COLLECT(
    *exes,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="BoltCalculationTool",
)
