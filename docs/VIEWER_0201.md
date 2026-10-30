# Viewer patch 0.20.1 / Windows 0.18.1

Only viewing code changes. No tracing, palette, geometry, export, GPU, or Rust binaries changed.

Browser: exponential cursor-anchored wheel zoom including deltaMode normalization; fractional slider steps; requestAnimationFrame-coalesced vector rendering directly to a canvas with the same joint-coverage renderer and supersampling; obsolete asynchronous frames discarded; no per-frame PNG encoding, URL allocation or raster/vector source switching. Pointer cancellation and native image drag handled. Tools and checkerboard remain visible with the canvas preview.

Windows: continuous fractional wheel deltas, cursor anchoring, same slider and wheel limits.

Validation: desktop/viewer cursor invariance and inverse wheel regression; browser demo vector, bitmap/outline switches, wheel and drag; syntax and diff checks. Native/WASM tracing binaries remain the previous tested versions.
