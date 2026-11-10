> Исторические проверки версий до 0.10.2: PDF содержал составные кривые по цветам, но не вложенные группы CorelDRAW. Исправление и новая проверка: [COREL_GROUPS.md](COREL_GROUPS.md).

# Windows 0.10 preview — photographic regions

The new pipeline is enabled for photographs with unlimited colours in the
desktop UI. Fixed palettes retain the existing Potrace pipeline, because the
new shared-grid prototype did not improve their contour smoothness.
WASM is unchanged.

## Geometry and colour

The earlier photographic pipeline merged subtle shades too aggressively.
Fitting every colour independently also left gaps between neighbouring shapes.
The new pipeline filters and assigns pixels, splits connected regions, and
merges adjacent regions by the increase in RGB squared error. Its region budget
depends on spatial boundary density, hue diversity and the selected quality.
Each resulting region keeps its mean colour.

Boundaries form a shared graph. Junctions stay fixed, each shared chain is
smoothed/simplified once, and both neighbouring colours use the same geometry
in opposite directions. Rounded contour endpoints are serialized consistently;
an independently rounded closing midpoint previously created small slivers.
An independent integer intersection audit checks the complete result. A failed
smoothed result falls back to the unsmoothed graph and is audited again.
The tolerance is 0.0001 square source pixels, not a promise of exact arithmetic.

SVG contains one compound path per RGB, inside one colour group. PDF retains
the existing one-Form/one-compound-path-per-RGB export for CorelDRAW.

## Preview

Shared regions are rasterized jointly before reducing sample coverage. Drawing
each colour with independent source-over antialiasing made touching half-covered
pixels only 75% opaque, producing pale seams despite matching geometry. The
new preview/PNG renderer avoids that compositing artifact, bounds temporary
buffers to the visible viewport and caches the latest view. SVG/PDF remain
vector files; third-party viewer antialiasing can still show hairlines.

The processing page now uses original gear illustrations, elapsed time is
formatted to two decimals, and unlimited-colour review hides fixed-palette
swatches to match the original interface.

## Comparison with the installed Vector Magic

Actual SVG references were exported from Vector Magic Desktop Edition 1.15.
Photo / Medium / Unlimited was used in both applications. Rendering was at
three times source resolution, then reduced with Lanczos. Each release uses
its own preview renderer; MAE therefore includes rendering differences as well
as segmentation differences. RGB MAE is measured
on the 0–255 channel scale. It does **not** measure identical vector topology.

| Control image | Background | 0.9 MAE | 0.10 MAE |
|---|---:|---:|---:|
| Green figurine, 568×960 | white | 11.568 | 4.458 |
| Green figurine, 568×960 | RGB 40 | 10.888 | 3.787 |
| Watercolour lion, 800×954 | white | 8.371 | 6.697 |
| Watercolour lion, 800×954 | RGB 40 | 8.653 | 6.670 |

The figurine was additionally checked at Low and High with separately exported
original references: white-background MAE 5.364 and 4.773 respectively.
A nine-colour High reference was also compared with the existing fixed-palette
engine using the exact exported RGB palette; that engine remains in use.

The full-image integer audits measured zero intersection area for all three
figurine qualities and the lion. These are a few control images, not universal
quality certification. Individual colour regions, fine details and curves still
differ from Vector Magic. The original images, original SVGs and comparison
images are kept locally and are not published with this repository.

CorelDRAW 26 was also checked by importing the new 568×960 PDF into a fresh
document. After ungrouping its outer import container, Document Properties
reported **530 objects**, **26,533 nodes**, maximum **329 nodes per curve**.
The PDF contains exactly 530 RGB Forms, and the object panel shows editable
curves. The local evidence and CDR are not included in the public repository.

## GPU and quality-preserving acceleration

OpenCL runs the alpha-aware bilateral filter, integer joint spatial/colour
mode filter, nearest-colour assignment and checkerboard spatial refinement.
Palette discovery, connected components, region merging, shared curves and the
intersection audit remain CPU operations. Selecting GPU does not move those
CPU stages onto the device.

The mode filter has three implementations: NumPy reference, optimized native C
CPU fallback, and OpenCL. Twenty-four alpha/border/random cases are byte-identical
across all three. The entire 568×960 source photo was also checked against the
NumPy reference and native CPU: no differing channels.

On the available GTX 1080, five warmed measurements on the complete source photo
gave median **5.960 ms GPU** and **247.020 ms native CPU** for this filter alone.
The native CPU version uses four row workers. These are not whole-app speedups.
Full compiled CPU/GPU tracing is additionally compared for identical SVG output.

Palette caching keys the actual filtered pixel contents, dimensions and palette
size. It changes neither selected colours nor SVG bytes. A bounded cache keeps
eight palette results. It does not rely on file names or timestamps.

## Reproduction

Use Windows x64 / Python 3.13 and the pinned desktop dependencies. The native
fallback DLL is included; rebuild with Zig 0.15.2 on PATH:

```powershell
python scripts/build_photo_modes.py
python tests/gpu_meanshift.py
python tests/shared_regions.py
python tests/shared_render.py
python tests/region_merge.py
python tests/photo_regions.py
python tests/spatial_ui.py
```

Worker configurations can select `backend: "shared"` explicitly. The UI passes
`photo_regions: true`; a saved preset with `photo_regions: false` retains the
previous unlimited-photo engine. Advanced curve/node settings affect shared
chain fitting. The GUI itself keeps its existing controls and layout.

Aggregate measurements: [photo-regions-comparison.json](photo-regions-comparison.json).
