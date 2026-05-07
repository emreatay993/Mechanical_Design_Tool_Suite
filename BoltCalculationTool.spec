# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules


project_root = Path(SPECPATH).resolve()
src_root = project_root / "src"
entry_script = project_root / "scripts" / "run_gui.py"


datas = []
binaries = []
hiddenimports = []

for package_name in (
    "bolt_calculation_tool",
    "PyQt6",
    "pyvista",
    "vtk",
    "vtkmodules",
    "matplotlib",
    "numpy",
):
    package_datas, package_binaries, package_hiddenimports = collect_all(package_name)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

hiddenimports += collect_submodules("bolt_calculation_tool")
hiddenimports += [
    "vtkmodules.all",
    "vtkmodules.qt.QVTKRenderWindowInteractor",
]


a = Analysis(
    [str(entry_script)],
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

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BoltCalculationTool",
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

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="BoltCalculationTool",
)
