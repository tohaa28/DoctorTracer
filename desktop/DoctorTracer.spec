from pathlib import Path
from PyInstaller.utils.hooks import collect_delvewheel_libs_directory
cl_data,cl_binaries=collect_delvewheel_libs_directory('pyopencl')
src=Path(SPECPATH)
a=Analysis([str(src/'app.py')],pathex=[str(src)],
    binaries=cl_binaries,datas=cl_data+[(str(src/'vendor'),'vendor'),(str(src/'icon.ico'),'.')],hiddenimports=[],
    excludes=['PySide6.QtWebEngineCore','PySide6.QtWebEngineWidgets','PySide6.QtQml','PySide6.QtQuick'],
    noarchive=False,optimize=0)
# Qt expects the operating system's unversioned ICU API. Ignore unrelated ICU DLLs on PATH.
a.binaries=[entry for entry in a.binaries if Path(entry[0]).name.lower() not in ('icuuc.dll','icudt78.dll')]
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='DoctorTracer',debug=False,
    bootloader_ignore_signals=False,strip=False,upx=False,console=False,
    disable_windowed_traceback=False,icon=[str(src/'icon.ico')])
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='DoctorTracer')
