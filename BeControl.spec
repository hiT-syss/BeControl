from pathlib import Path
from importlib.metadata import distributions
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

source = Path(SPECPATH)
datas = [
    (str(source / "chevron.svg"), "."),
    (str(source / "BeControl.ico"), "."),
    (str(source / "licenses"), "licenses"),
]
datas += collect_data_files("mediapipe")
for distribution in distributions():
    name = distribution.metadata.get("Name", "dependency")
    for entry in distribution.files or []:
        if any(word in entry.name.lower() for word in ("license", "copying", "notice")):
            if ".dist-info" in str(entry) or ".egg-info" in str(entry):
                path = distribution.locate_file(entry)
                if path.is_file():
                    datas.append((str(path), f"licenses/{name}"))

python_license = Path(sys.base_prefix) / "LICENSE.txt"
if python_license.exists():
    datas.append((str(python_license), "licenses/Python"))

analysis = Analysis(
    [str(source / "app.py")],
    pathex=[str(source)],
    binaries=collect_dynamic_libs("mediapipe"),
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={"matplotlib": {"backends": ["Agg"]}},
    runtime_hooks=[],
    excludes=["tkinter", "jax", "jaxlib", "tensorflow", "scipy", "IPython", "pytest"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="BeControl",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(source / "BeControl.ico"),
    version=str(source / "version_info.txt"),
)
bundle = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="BeControlExe",
)
