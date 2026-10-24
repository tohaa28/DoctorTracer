# Licenses and attribution

DoctorTracer is an independent raster-to-vector application. It is not affiliated with Vector Magic. No Vector Magic executable, library, extracted implementation or graphic resource is included.

* `desktop/`: original application code under the MIT license in `desktop/LICENSE`.
* `core/tracer.cpp`, `web/`, `scripts/build_wasm.py`, and the linked WASM distribution: GPL-2.0-or-later. The full license is `core/potrace-1.16/COPYING`; corresponding sources and build script are included. Preserve the GPL license and corresponding source when redistributing this combined WASM application.
* Potrace 1.16: Copyright 2001–2019 Peter Selinger, GPL-2.0-or-later. The complete unmodified upstream source distribution is in `core/potrace-1.16/`; the desktop invokes the separately bundled official Windows executable. `desktop/vendor/potrace/` contains its license, source archive and Windows notice.
* VTracer 0.6.15: MIT. PySide6 / Qt: LGPLv3 / GPLv3 / commercial options; Pillow: HPND; NumPy: BSD; OpenCV: Apache-2.0; PyOpenCL: MIT; PyInstaller: GPL with bootloader exception. Windows bundles retain dependency license files.

Generated SVG files are user output and are not assigned a license by this application.
