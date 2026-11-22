# Native quality module

`doctortracer_quality.dll` is built from the same Rust sources as web/doctortracer.wasm.
The original source is MIT (rust/src/raster_refit.rs, joint_palette.rs); the combined application remains GPL-3.0-or-later. No proprietary library is used.

Rebuild with scripts/build_quality_native.py using the GNU Rust Windows target. The DLL imports only Windows system APIs / CRT; it does not require a separate Rust or MinGW installation at runtime.

`doctortracer_clipper.dll` compiles core/clipper.cpp (Boost-1.0) and core/wasm_audit.cpp (MIT), the same source as the WASM integer backend. Rebuild with scripts/build_clipper_native.py --zig <official Zig 0.15.2>. Only Windows system CRT dependencies are required. Used for highly fragmented geometry and worker recovery.
