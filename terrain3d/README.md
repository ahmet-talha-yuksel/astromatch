# AstroMatch AI — standalone Terrain3D module

Phase 6 documentation: [integration readiness](docs/integration-readiness.md), [scientific validation](docs/scientific-validation.md), and [integration guide](docs/integration-guide.md).

Independent React/TypeScript viewer with no dependency on `frontend/`, backend services,
or NASA APIs. Every bundled terrain is **synthetic**, not NASA measurements.
The original 64×64 Mars/Earth surfaces remain in the demo; three small JSON examples
also exercise URL loading, rectangular spacing and a NoData hole.

## Run and verify

From `terrain3d/`, with Node.js 20.19+:

```bash
npm install
npm run dev -- --host 0.0.0.0 --port 5174
npm test
npm run build
```

Tests compile the validation, loading and geometry modules with the existing TypeScript
compiler and run Node's built-in test runner; no testing framework dependency is added.
Temporary compiled tests are removed afterward. Optional browser checks use Python
Playwright and an installed Chrome:

```bash
pip install playwright
python tests/browser_check.py
```

Start the dev server first. `TERRAIN_URL` (default `http://localhost:5174`) and
`CHROME_PATH` override the browser test defaults. The browser harness is a dev-only
test entry, excluded from the production build. It tests actual mouse drag/wheel
events, loading/errors, and a delayed response after switching URLs.

## TerrainData JSON contract

The canonical delivery type is `TerrainDataJSON` in `src/types/terrain.ts`.
`TerrainData` accepts this type or the deprecated legacy type for compatibility.
`validateTerrainData(input: unknown)` returns normalized `ValidatedTerrainData` or
throws a descriptive `TerrainValidationError`. A TypeScript cast is not validation.

| Field | JSON type | Requirement / meaning |
| --- | --- | --- |
| `id` | non-empty string | Required; unique terrain identifier, assigned upstream |
| `name` | non-empty string | Required; human-readable label |
| `body` | `"Earth"`, `"Mars"`, `"Moon"` | Required; case-sensitive |
| `width`, `height` | integers ≥ 2 | Required; columns and rows; product must be a safe integer |
| `heights` | array of numbers or `null` | Required; exactly `width * height`; elevation in meters |
| `cellSizeMeters` | positive number or `{ "x": number, "y": number }` | Required; output sample spacing; scalar explicitly means equal axes |
| `source` | non-empty string | Required; dataset source, or explicit generator description |
| `resolutionMeters` | positive number or `{ "x": number, "y": number }` | Required; original source DEM resolution, independent of output spacing |
| `verticalExaggeration` | finite number > 0 | Optional; defaults to 1; display-only vertical multiplier |
| `dataType` | `"real"` or `"synthetic"` | Required; never inferred from a body or name |
| `validMask` | array of booleans | Optional; exactly `width * height`; omitted means all valid |
| `horizontalWindowMeters` | `{ "width": number, "height": number }` | Required; physical sample-center span, defined below |
| `verticalDatum` | non-empty string | Required; named elevation reference, including planetary reference surface where applicable |
| `coordinateReferenceSystem` | non-empty string | Required; source/projected CRS identifier or WKT; use an explicit local metric grid for synthetic data |
| `processingMetadata` | object | Optional for synthetic; required with provenance for real data |

`processingMetadata` supports these fields:

| Field | Type | Requirement |
| --- | --- | --- |
| `provenance` | object | Required for real datasets; optional for synthetic |
| `provenance.dataset` | non-empty string | Original dataset name |
| `provenance.productId` | non-empty string | Traceable tile/product identifier |
| `provenance.version` | non-empty string | Product release/version |
| `provenance.url` | absolute HTTP(S) URL | Stable product/catalog record or `https://doi.org/...` |
| `steps` | array of non-empty strings | Optional; crop, reprojection, resampling, NoData treatment, etc. |
| `processedAt` | UTC ISO timestamp string | Optional; e.g. `2026-11-14T10:00:00Z` |
| `software` | non-empty string | Optional; software and version |

If provenance is supplied, all four of its fields are mandatory. Required metadata
must be supplied truthfully; validation checks structure, not the authenticity or
scientific suitability of a claimed product, CRS or datum. Unknown extra keys are
ignored and not retained in the normalized object; malformed supported fields fail.

## Units, ordering and physical window

Elevations are absolute values in **meters relative to `verticalDatum`**.
Negative values and actual zero-meter elevations are valid. Flatten rows in order:

```text
index = row * width + column
horizontalWindowMeters.width  = (width  - 1) * cellSizeMeters.x
horizontalWindowMeters.height = (height - 1) * cellSizeMeters.y
```

A scalar `cellSizeMeters` supplies both axes. Window metadata uses the distance
between the first and last sample centers, **not** the raster's outer pixel-edge
footprint. Tolerance is `max(0.000001 meters, expected span * 0.000001)` per axis.
For a resampled DEM, compute output spacing and the center span from the output
transform; do not copy a source raster's pixel-edge bounds as the window size.
Source `resolutionMeters` must retain original resolution after resampling.

The renderer preserves X/Y horizontal aspect ratio, mapping columns to display X
and rows to display Z. It translates the minimum valid elevation to display Y = 0
and normalizes the longest horizontal span to 10 scene units. Only display height
is multiplied by `verticalExaggeration`; input elevations are not changed.
The viewer does not reproject coordinates, interpret north/east orientation,
convert vertical datums or enforce comparable physical windows between viewers.
Record geographic location/orientation in your upstream product/catalog metadata.

## NoData behavior

- Deliver missing samples as `null` with `validMask[index] = false`.
- A finite numeric sentinel is also accepted only when masked false; it normalizes
  to `null`. It never enters elevation/color extrema or GPU vertices.
- `null` without a false mask is an error. NaN/Infinity are always rejected,
  including masked entries; they are not valid JSON numbers.
- Invalid samples produce no vertices. Each triangle is emitted only if all three
  of its samples are valid, preserving independent valid triangles in adjacent cells.
  Holes are not filled, bridged, converted to zeros or interpolated.
- At least one valid sample and one fully valid triangle are required. Empty or
  completely disconnected valid data yields a readable validation error.
- Extreme elevation/spacing/exaggeration combinations that exceed safe GPU float32
  range are rejected. Display height is limited to `1e30` scene units to leave
  headroom for normals. This is a numeric guard, not a scientifically useful scale.

## Copy-paste synthetic JSON

```json
{
  "id": "small-mars-synthetic",
  "name": "Synthetic Mars slope",
  "body": "Mars",
  "width": 2,
  "height": 2,
  "heights": [100, 110, 120, 130],
  "cellSizeMeters": { "x": 100, "y": 150 },
  "source": "Generated demonstration, NOT NASA measurements",
  "resolutionMeters": { "x": 100, "y": 150 },
  "verticalExaggeration": 1,
  "dataType": "synthetic",
  "horizontalWindowMeters": { "width": 100, "height": 150 },
  "verticalDatum": "Synthetic local elevation reference",
  "coordinateReferenceSystem": "Synthetic local metric grid"
}
```

Small fixtures are in `public/terrain/{mars,moon,earth}_demo.json`. The Moon fixture
has a masked central sample; the Earth fixture uses different X and Y spacing.

## React integration and loading

Reuse `src/` as a module in a React/TypeScript host with `three`, `@react-three/fiber`
and `@react-three/drei` installed (`@types/three` for TypeScript). Import its public
API from `src/index.ts`. Existing object props remain supported:

```tsx
import { TerrainViewer, TerrainComparison, validateTerrainData } from "./terrain3d/src";
import marsJson from "./mars.json";
import earthJson from "./earth.json";

const mars = validateTerrainData(marsJson);
const earth = validateTerrainData(earthJson);

export function TerrainPanel() {
  return <>
    <TerrainViewer terrain={mars} />
    <TerrainViewer terrainUrl="/terrain/moon_demo.json" />
    <TerrainComparison target={mars} analog={earth} />
  </>;
}
```

Pass exactly one of `terrain` or `terrainUrl`. Objects are validated before a
canvas is mounted. URLs use native fetch, show a loading state, check HTTP status,
parse and validate JSON, and show errors with the URL and relevant field/status.
Changing a URL immediately removes old content, aborts the old request and ignores
late results. Unmount and React StrictMode effect cleanup are handled. Cross-origin
URLs require normal browser CORS access; there is no external API dependency.
`loadTerrain(url, optionalAbortSignal)` is also exported for host-managed loading.

Left-drag rotates, right-drag pans and the wheel zooms. Damping remains enabled;
distance limits are 4–30 scene units. These are display distances, not meters.

## Compatibility

Deprecated `elevationsMeters` is accepted as an alias for `heights`; if both are
supplied they must agree. Deprecated `isSynthetic` maps to `dataType` only if no
explicit `dataType` is supplied, and conflicting labels are rejected.

Old **explicitly synthetic** `elevationsMeters` objects can omit new metadata. Only
for that legacy format, resolution is the generator's sample spacing, the window
is computed and datum/CRS are marked as synthetic local references. There is no
such fallback for real data or for new `heights` objects. Unlabeled old objects
are rejected; they must explicitly declare real/synthetic status.

The existing `converter/dem_to_json.py` is an unchanged Phase 1 utility, not the
Phase 2 delivery producer. Its output lacks labeling and scientific metadata and
will be rejected until enriched. It has not been run or extended in this phase.
Do not infer a real product's original resolution, datum or provenance from its
local filename or from resampled grid spacing.

## Ahmetson's delivery checklist

1. Crop/reproject/resample upstream into a regular metric grid; provide separate
   X/Y spacing when needed. Resolve units, orientation and datum upstream.
2. Emit the canonical fields listed above, with row-major `heights` in meters.
   Keep original `resolutionMeters` distinct from output `cellSizeMeters`.
3. Supply the center-to-center physical window, named vertical datum and source
   CRS. Record processing steps, software and time when available.
4. Set `dataType: "real"` only for real measurements and include
   `processingMetadata.provenance` with dataset, productId, version and URL.
   Supply `source` as well. Never label generated surfaces as real/NASA data.
5. Use `null` plus a false validity mask for NoData; never silently replace it with zero.
6. Validate the complete JSON using `validateTerrainData`, then deliver the object
   or serve the JSON at a URL accessible to the host. No renderer changes are needed.

Real product retrieval, DEM processing, datum reconciliation, scientific matching,
synchronized cameras and backend integration are outside this phase. A topographic
resemblance alone does not establish equivalent planetary conditions.

## TerrainViewer scientific controls

Each viewer provides Reset Camera, Top View, Perspective View and Fit Terrain actions.
They preserve OrbitControls and adapt their distance limits to the physical terrain
span, including rectangular grids. Mouse interaction remains left-drag rotate,
right-drag pan and wheel zoom.

The vertical exaggeration slider ranges from 0.5× to 5×. It changes only display
height; source elevations and metadata are never mutated. Elevation gradient and
neutral shaded modes are available, with a legend showing the valid elevation range
in meters. NoData samples are excluded from the range and remain holes in the mesh.

Moving over a valid mesh location shows the original (unexaggerated) elevation and
local X/Y coordinates in meters, plus terrain name and body. These are local grid
coordinates, not latitude/longitude. NoData locations produce no inspection value.

The Scientific metadata panel shows data type, source, source resolution, display
spacing, physical window, datum, CRS, valid-data percentage, exaggeration and real
dataset provenance when available. Synthetic surfaces are labeled prominently as
“SYNTHETIC DEMO — NOT NASA DATA”. Metadata is descriptive and does not establish
measurement authenticity or scientific equivalence between planetary bodies.

The public component API remains compatible:

```tsx
<TerrainViewer terrain={terrainData} />
<TerrainViewer terrainUrl="/terrain/mars_demo.json" />
```

Viewer state is local to each instance, so two comparison panels can be inspected and
controlled independently. Geometry is memoized by terrain, exaggeration and color mode;
invalid triangles retain the existing NoData masking behavior.

## TerrainComparison

`TerrainComparison` accepts the existing `{ target, analog }` API:

```tsx
<TerrainComparison target={marsTarget} analog={earthAnalog} />
```

It provides side-by-side target/analog panels, a shared 0.5×–5× exaggeration control,
absolute and relative elevation modes, a shared relative legend, valid-data and relief
summary, synthetic-data warnings, physical-window mismatch warnings, and vertical-datum
warnings. Relative mode subtracts each terrain's median valid elevation; it does not
normalize either terrain independently or change source values. Absolute mode retains
each source datum and warns when the datum labels differ.

The Sync Cameras toggle synchronizes camera position and target between the two panels
using a scoped comparison key with guarded event propagation to avoid feedback loops.
When disabled, each OrbitControls instance remains independent. Horizontal geometry is
kept in the same viewer world scale and rectangular X/Y spacing is preserved. Camera
orientation is synchronized only as a view operation; geographic alignment is never
assumed.

## Production DEM converter

`converter/dem_to_json.py` converts an already prepared single-band GeoTIFF (or any
Rasterio-readable raster) into the same canonical JSON. Install its isolated Python
dependencies with `python -m pip install rasterio numpy`. Rasterio must be able to
read the selected format; GeoTIFF is the tested format.

Windows PowerShell:

```powershell
python -m pip install rasterio numpy
python converter/dem_to_json.py --input data\processed\mars_jezero.tif --output public\terrain\mars_jezero.json --id mars_jezero --name "Mars Jezero Crater" --body Mars --data-type real --dataset "NASA MOLA" --product-id "EXACT_PRODUCT_ID" --version "EXACT_VERSION" --source-url "https://example.org/actual-dataset" --vertical-datum "EXACT_VERTICAL_REFERENCE" --target-size 128 --resampling bilinear
```

CMD uses the same command with `%CD%` or absolute paths if desired:

```cmd
python converter\dem_to_json.py --input data\processed\earth.tif --output public\terrain\earth.json --id earth --name "Prepared Earth DEM" --body Earth --data-type real --dataset "Dataset name" --product-id "PRODUCT" --version "VERSION" --source-url "https://example.org/product" --vertical-datum "Named vertical datum" --target-size 256
```

The CLI also accepts legacy positional input/output paths, `--target-width` plus
`--target-height`, `--window COL ROW WIDTH HEIGHT`, `--window-meters X Y WIDTH HEIGHT`,
`--resampling nearest`, `--resampling bilinear`, `--resampling cubic`,
`--resampling average` or `--resampling mode`, repeated
`--processing-note`, and `--vertical-exaggeration`. Use `--allow-upsampling` explicitly
when output samples are finer than the source; interpolation creates no new measurements.

The converter currently accepts north-up, unrotated, projected CRS rasters whose
horizontal CRS units are meters. It rejects geographic degree rasters, rotated/skewed
or south-up transforms, missing CRS, non-meter horizontal units, and planetary CRS
definitions that cannot be verified as metric. Mars and Moon geographic products must
be prepared upstream with a body-appropriate projection; the converter never applies
Earth transformations or fabricates a planetary radius. Vertical units must be meters,
and `--vertical-datum` is always explicit.

NoData is read from the raster mask/nodata metadata and is emitted as `null` with a
false `validMask` entry. Resampling uses Rasterio masked arrays so invalid values do
not become zero or contaminate valid extrema. The output reports valid percentage in
the CLI and records source dimensions, output dimensions and resampling in
`processingMetadata.steps`. `resolutionMeters` is source pixel spacing; output
`cellSizeMeters` and `horizontalWindowMeters` describe the generated sample grid.
Real conversion refuses missing dataset, product ID, version or HTTP(S) provenance.
Synthetic conversion still requires an explicit synthetic label and never claims NASA
measurements. Run `pytest converter/tests` after installing pytest to exercise offline
small-raster fixtures; no external dataset is downloaded.
