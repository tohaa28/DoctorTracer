# Native quality module

`doctortracer_quality.dll` is built from the same Rust sources as web/doctortracer.wasm.
The original source is MIT (rust/src/raster_refit.rs, joint_palette.rs); the combined application remains GPL-3.0-or-later. No proprietary library is used.

Rebuild with scripts/build_quality_native.py using the GNU Rust Windows target. The DLL imports only Windows system APIs / CRT; it does not require a separate Rust or MinGW installation at runtime.
