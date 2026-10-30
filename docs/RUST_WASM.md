> Исторический отчёт версии 0.11. В 0.12 ядро заменено переносом десктопного алгоритма: [новый отчёт](DESKTOP_WASM_PARITY.md).

# Rust WASM 0.11 preview

Published browser target: https://tohaa28.github.io/DoctorTracer/ . Windows 0.10.2 is unchanged.

## Architecture

RGBA decode/EXIF handling and previews use browser APIs. An ES module Worker hosts a 156 KB Rust WASM module: integer edge-preserving filter, bounded 5-bit histogram palette fitting, visioncortex clustering, cutout region extraction, spline/polygon paths, grouping by exact RGB. Quantized output is remapped to the final palette after region merging, so requested N colours never grow beyond N. Automatic colours retain regional means. Empty alpha images return empty SVG; original transparent pixels are restored before the cutout pass. One-pixel interior holes that the spline fitter drops are restored as reverse-wound unit rectangles within the same curve.

Optional WebGPU computes the same integer filter. CPU fallback is automatic. GPU is NOT used for all tracing calculations, and no claim of overall speedup is made. Devices that do not provide WebGPU use Rust CPU. No server receives image pixels. The worker is terminated on cancel; another image invalidates outstanding decode operations. Input dimensions are bounded to 8 million pixels and 4096 per side at the ABI; the UI resizes to at most 2400 per side.

SVG contains one outer image group and nested RGB groups. PDF uses explicit isolated DeviceRGB transparency Form groups, one per RGB, directly referenced by the page. Each connected curve is a separate fill within its colour Form. Corel supplies the imported-file parent group. There are no raster XObjects or invisible placeholders. Native CorelDRAW 26 import of the Rust nine-colour figurine PDF produced nine immediate colour subgroups, including one singleton.

## Quality boundaries

This is a functional Rust browser rewrite, not a port of the accepted Windows shared-boundary graph. Region masks are cut out, but independent spline fitting can introduce local geometric gaps/intersections. Exact Windows/Vector Magic geometry is not established. The browser does not yet have Windows region editing, batch processing, custom RGB palette editing or EPS export. Binary transparency threshold is 128/255.

On the same local Vector Magic medium/unlimited references, white-background RGB MAE (0–255) was 8.212 on the figurine and 8.603 on the watercolour lion. Accepted Windows values were 4.458 and 6.697. Thus Rust preview is currently WORSE than Windows on these controls. Alpha IoU was 0.99910 and 0.98797. These are raster comparisons of two examples, not proof of vector equivalence. User files and reference exports remain private.

Local Rust WASM CPU timings (one warm process, medium quality, includes Rust filtering; illustrative, not browser-wide benchmarks): figurine 568×960 automatic 2.25 s, nine colours 0.38 s; lion 800×954 automatic 11.61 s, nine colours 8.46 s. The legacy C++ nine-colour engine took 0.14 s and 0.42 s respectively; Rust preview is NOT currently an across-the-board speed improvement. It adds automatic regional colours, editable colour hierarchy, WebGPU filtering and pure-Rust deployment. Further optimization must preserve output.

## Verification, 2026-10-25

- `node tests/rust_wasm.mjs`: real compiled WASM, repeat determinism, palette count, curves/polygons, empty alpha, invalid input, monotonic processing stages, PDF Forms/xref.
- `tests/browser.html`, served locally from repository root: 12 dimensions/detail combinations, WebGPU readback vs Rust filter byte equality, CPU/GPU final SVG equality, CPU-prefilter equivalence, browser raster check of a one-pixel alpha hole, vector PDF grouping. Actual WebGPU ran in all 12 cases on the test machine.
- Native UI basic wizard through result and save, WebGPU backend visible, PDF download invoked. Automated browser layout flows passed at 390×844, 640×640, 820×640 and 1280×720 with no horizontal panel overflow.
- Native CorelDRAW import of an actual Rust-generated PDF, expanded outer colour groups.
- Three qualities on both private control images; nine-colour palettes stay at nine colour groups.

## Reproduce

Rust 1.99.1, `rustup target add wasm32-unknown-unknown`, then `python scripts/build_wasm.py` and `node tests/rust_wasm.mjs`. Cargo.lock pins dependencies. No Emscripten or wasm-bindgen CLI is needed. `build/site` contains only static runtime files, the original demo and license notices, never test photos. `python scripts/serve.py` serves web runtime locally. For browser verification, serve the repository root (`python -m http.server 8767 --bind 127.0.0.1`) and open `/tests/browser.html`.

## Publication

The current GitHub OAuth token lacks workflow-write scope. The checked static artifact is published through the gh-pages branch using GitHub Pages branch publishing. A future Rust build/test/deploy workflow is retained as docs/pages-workflow.example.yml; it is not currently active. No account token scopes were expanded.
