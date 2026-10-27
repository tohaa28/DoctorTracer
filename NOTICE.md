# Licenses and attribution

DoctorTracer is an independent raster-to-vector application. It is not affiliated with Vector Magic. No Vector Magic executable, library, extracted implementation or graphic resource is included.

* `core/photo_modes.c` and its CPU DLL build script: original MIT-licensed integer mode filter; license text in `desktop/LICENSE`. Its CPU and OpenCL implementations are tested for identical output.
* `desktop/`: original application code under the MIT license in `desktop/LICENSE`.
* The Windows combined distribution, from 0.6 onward, links the Potrace DLL and is distributed under GPL-3.0-or-later (using the later-version option of Potrace's GPL-2.0-or-later license). The original MIT-licensed components retain their MIT notices. The full GPLv3 text is included in `licenses/GPL-3.0.txt`, along with complete corresponding application, adapter and Potrace sources and a reproducible DLL build script.
* `core/tracer.cpp`, legacy browser frontend, `scripts/build_wasm_legacy.py`, and the historical Emscripten WASM distribution: GPL-2.0-or-later. The full license is `core/potrace-1.16/COPYING`; corresponding sources and build script are included. Preserve the GPL license and corresponding source when redistributing this combined WASM application.
* Potrace 1.16: Copyright 2001–2019 Peter Selinger, GPL-2.0-or-later. The complete upstream source distribution is in `core/potrace-1.16/`. The desktop uses the bundled official executable for illustrations and a locally built DLL with `core/native_svg.c` for photo curve fitting. `desktop/vendor/potrace/` contains the original license, source archive and Windows notice.
* VTracer 0.6.15: MIT. PySide6 / Qt: LGPLv3 / GPLv3 / commercial options; Pillow: HPND; NumPy: BSD; OpenCV: Apache-2.0; PyOpenCL: MIT; PyInstaller: GPL with bootloader exception. Windows bundles retain dependency license files.
* Windows 0.8 preview adds skia-pathops 0.9.2 / Skia PathOps (BSD-3-Clause), pyclipper 1.4.0 (MIT), and its embedded Clipper 6.4.2 (Boost Software License 1.0). License texts are included in `licenses/SKIA-PATHOPS.txt`, `licenses/PYCLIPPER.txt`, and `licenses/BOOST-1.0.txt`. Clipper copyright: Angus Johnson, 2010–2017.

Generated SVG files are user output and are not assigned a license by this application.

## Rust browser preview 0.11

The current browser app loads `web/doctortracer.wasm`, built from `rust/`, not the historical Emscripten binary. Original Rust core, Rust loader, integer GPU filter, PDF adapter and original icons retain MIT notices. Frontend portions derived from the earlier GPL frontend retain GPL-2.0-or-later notices; the combined 0.11 browser distribution uses GPL-3.0-or-later under that later-version option, compatible with the Apache-2.0 dependency. Full application source, pinned Cargo dependencies and build scripts are in this repository.

visioncortex 0.8.8 (MIT OR Apache-2.0) provides region clustering and curve fitting. The cutout pipeline is independently integrated using its public API, informed by VTracer's documented cutout architecture. Dependencies include flo_curves (Apache-2.0), roots (BSD-2-Clause), bit-vec, num-traits, log, smallvec, either and itertools (MIT and/or Apache-2.0). Build-time autocfg is MIT OR Apache-2.0. Cargo.lock records exact versions/checksums. `scripts/build_wasm.py` collects upstream notices into `web/LICENSE.txt`; the hosted artifact includes it. Apache-2.0 text is retained in `licenses/APACHE-2.0.txt`.

## Desktop WASM 0.12

Version 0.12 replaces the visioncortex pipeline with independently ported desktop algorithms. The combined browser distribution remains GPL-3.0-or-later. Rust modules retain MIT or Apache-2.0 SPDX notices; Potrace 1.16 is GPL-2.0-or-later, Clipper 6.4.2 is Boost-1.0, and Skia PathKit uses its preserved BSD-style notice. Exact sources and build adapters are in core/, rust/ and scripts/. Qt-derived UI icons are DoctorTracer's own MIT artwork; no proprietary Vector Magic resources are distributed. web/LICENSE.txt contains the distribution notices. The preceding 0.11 dependency description is historical.


The Windows distribution includes doctortracer_quality.dll built from this repository’s rust/src/raster_refit.rs and ABI in rust/src/lib.rs (MIT). Rebuild with scripts/build_quality_native.py. Combined distribution licensing remains as described above.

The Windows doctortracer_clipper.dll is built from core/clipper.cpp (Boost-1.0) and core/wasm_audit.cpp (MIT), also used by web/vendor/audit.wasm. Rebuild with scripts/build_clipper_native.py.
