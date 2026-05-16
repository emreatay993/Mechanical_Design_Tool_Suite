# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules


project_root = Path(SPECPATH).resolve()
src_root = project_root / "src"
sys.path.insert(0, str(src_root))

debug_build = os.environ.get("MDTS_PYI_DEBUG", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
runtime_hooks = [str(project_root / "scripts" / "pyinstaller_error_logging_hook.py")]
debug_flag_path = project_root / "build" / "mdts_debug_build.flag"

entry_scripts = [
    ("MechanicalDesignToolSuite", project_root / "scripts" / "run_launcher.py"),
    ("BoltCalculationGui", project_root / "scripts" / "run_gui.py"),
    ("ToleranceAnalysis", project_root / "scripts" / "run_tolerance_analysis.py"),
    ("ToleranceAnalysisVNext", project_root / "scripts" / "run_tolerance_vnext_analysis.py"),
    ("Cad1DTolerance", project_root / "scripts" / "run_cad_1d_tolerance.py"),
]
required_entry_names = {
    "MechanicalDesignToolSuite",
    "BoltCalculationGui",
    "ToleranceAnalysis",
    "ToleranceAnalysisVNext",
    "Cad1DTolerance",
}
missing_entry_names = required_entry_names - {name for name, _ in entry_scripts}
if missing_entry_names:
    raise RuntimeError(
        "PyInstaller entry script(s) are missing: "
        + ", ".join(sorted(missing_entry_names))
    )


datas = []
binaries = []
hiddenimports = []


def collect_conda_dll_dependencies(package_name):
    """Collect DLL dependencies that conda keeps in Library/bin."""

    try:
        import importlib
        import pefile
    except Exception:
        return []

    try:
        package = importlib.import_module(package_name)
    except Exception:
        return []

    package_file = getattr(package, "__file__", None)
    if not package_file:
        return []

    package_root = Path(package_file).resolve().parent
    library_bin = Path(sys.prefix) / "Library" / "bin"
    if not library_bin.exists():
        return []

    dlls_by_name = {path.name.lower(): path for path in library_bin.glob("*.dll")}
    queue = list(package_root.rglob("*.pyd"))
    seen_files = set()
    collected = {}

    while queue:
        file_path = queue.pop()
        file_key = str(file_path).lower()
        if file_key in seen_files:
            continue
        seen_files.add(file_key)

        try:
            pe = pefile.PE(str(file_path), fast_load=True)
            pe.parse_data_directories(
                directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]]
            )
        except Exception:
            continue

        for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
            dll_name = entry.dll.decode(errors="ignore").lower()
            dll_path = dlls_by_name.get(dll_name)
            if dll_path is None or dll_name in collected:
                continue
            collected[dll_name] = dll_path
            queue.append(dll_path)

    return [(str(path), ".") for path in sorted(collected.values())]


for package_name in (
    "mechanical_design_tool_suite",
    "OCC",
    "PyQt6",
    # PyVista/VTK are packaged for existing mesh diagnostics and bolt/vNext
    # views only; CAD 1D tolerance remains OCCT B-Rep authoritative.
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

hiddenimports += collect_submodules("mechanical_design_tool_suite")
hiddenimports += collect_submodules("openpyxl")
# pythonocc keeps many OCCT DLL dependencies in Conda's Library/bin. Collect
# the DLL closure from OCC extension modules so Cad1DTolerance.exe can start
# without requiring the build environment on PATH.
binaries += collect_conda_dll_dependencies("OCC")
hiddenimports += [
    "PyQt6.QtQml",
    "PyQt6.QtQuick",
    "PyQt6.QtQuickWidgets",
    "vtkmodules.all",
    "vtkmodules.qt.QVTKRenderWindowInteractor",
]

for data_path in (
    src_root / "mechanical_design_tool_suite" / "data" / "tolerance_catalog.json",
    src_root / "mechanical_design_tool_suite" / "qml" / "tolerance_vnext.qml",
):
    if data_path.exists():
        datas.append((str(data_path), str(data_path.parent.relative_to(src_root))))

if debug_build:
    debug_flag_path.parent.mkdir(parents=True, exist_ok=True)
    debug_flag_path.write_text(
        "This file enables packaged error logging for debug PyInstaller builds.\n",
        encoding="utf-8",
    )
    datas.append((str(debug_flag_path), "."))


a = Analysis(
    [str(script_path) for _, script_path in entry_scripts],
    pathex=[str(src_root), str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=sorted(set(hiddenimports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=runtime_hooks,
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

entry_script_paths = {script_path.resolve() for _, script_path in entry_scripts}
runtime_script_entries = [
    script_entry
    for script_entry in a.scripts
    if Path(script_entry[1]).resolve() not in entry_script_paths
]
entry_script_entries = {
    Path(script_entry[1]).resolve(): script_entry
    for script_entry in a.scripts
    if Path(script_entry[1]).resolve() in entry_script_paths
}

icon_dir = project_root / "build_assets" / "icons"

exes = []
for name, script_path in entry_scripts:
    script_entry = entry_script_entries.get(script_path.resolve())
    if script_entry is None:
        raise RuntimeError(f"PyInstaller did not collect entry script: {script_path}")

    icon_file = icon_dir / f"{name}.ico"
    exe_icon = str(icon_file) if icon_file.exists() else None

    exes.append(
        EXE(
            pyz,
            [*runtime_script_entries, script_entry],
            [],
            exclude_binaries=True,
            name=name,
            icon=exe_icon,
            debug=debug_build,
            bootloader_ignore_signals=False,
            strip=False,
            upx=False,
            console=debug_build,
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
    name="MechanicalDesignToolSuite",
)
