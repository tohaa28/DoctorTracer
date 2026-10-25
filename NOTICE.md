# Licenses and attribution

DoctorTracer is an independent raster-to-vector application. It is not affiliated with Vector Magic. No Vector Magic executable, library, extracted implementation or graphic resource is included.

* `core/photo_modes.c` and its CPU DLL build script: original MIT-licensed integer mode filter; license text in `desktop/LICENSE`. Its CPU and OpenCL implementations are tested for identical output.
* `desktop/`: original application code under the MIT license in `desktop/LICENSE`.
* The Windows combined distribution, from 0.6 onward, links the Potrace DLL and is distributed under GPL-3.0-or-later (using the later-version option of Potrace's GPL-2.0-or-later license). The original MIT-licensed components retain their MIT notices. The full GPLv3 text is included in `licenses/GPL-3.0.txt`, along with complete corresponding application, adapter and Potrace sources and a reproducible DLL build script.
* `core/tracer.cpp`, `web/`, `scripts/build_wasm.py`, and the linked WASM distribution: GPL-2.0-or-later. The full license is `core/potrace-1.16/COPYING`; corresponding sources and build script are included. Preserve the GPL license and corresponding source when redistributing this combined WASM application.
* Potrace 1.16: Copyright 2001–2019 Peter Selinger, GPL-2.0-or-later. The complete upstream source distribution is in `core/potrace-1.16/`. The desktop uses the bundled official executable for illustrations and a locally built DLL with `core/native_svg.c` for photo curve fitting. `desktop/vendor/potrace/` contains the original license, source archive and Windows notice.
* VTracer 0.6.15: MIT. PySide6 / Qt: LGPLv3 / GPLv3 / commercial options; Pillow: HPND; NumPy: BSD; OpenCV: Apache-2.0; PyOpenCL: MIT; PyInstaller: GPL with bootloader exception. Windows bundles retain dependency license files.
* Windows 0.8 preview adds skia-pathops 0.9.2 / Skia PathOps (BSD-3-Clause), pyclipper 1.4.0 (MIT), and its embedded Clipper 6.4.2 (Boost Software License 1.0). License texts are included in `licenses/SKIA-PATHOPS.txt`, `licenses/PYCLIPPER.txt`, and `licenses/BOOST-1.0.txt`. Clipper copyright: Angus Johnson, 2010–2017.

Generated SVG files are user output and are not assigned a license by this application.
