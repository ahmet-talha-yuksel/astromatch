# AstroMatch AI — standalone Terrain3D module

Phase 6 documentation: [integration readiness](docs/integration-readiness.md), [scientific validation](docs/scientific-validation.md), and [integration guide](docs/integration-guide.md).

Independent React/TypeScript viewer with no dependency on `frontend/`, backend services,
or NASA APIs. Every bundled terrain is **synthetic**, not NASA measurements.
The demo includes 144×144 Mars/Earth/Moon surfaces; three small JSON examples
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
  to `null`. It never enters elevation/color extrema or measured-terrain GPU vertices.
- `null` without a false mask is an error. NaN/Infinity are always rejected,
  including masked entries; they are not valid JSON numbers.
- Invalid samples produce no vertices. Each triangle is emitted only if all three
  of its samples are valid, preserving independent valid triangles in adjacent cells.
  The measured DEM holes are not filled, bridged, converted to zeros or interpolated.
- With visual filling disabled, a separate, unlit hatched diagnostic layer marks the omitted triangle footprints
  below the minimum displayed valid elevation. This reference plane is **not** an
  estimated elevation or a terrain surface. It cannot be inspected or walked on.
  The overview legend reports the missing sample percentage, not the larger missing
  triangle percentage. POV also labels unavailable elevation data.
- Visual interpolation is enabled by default in the viewers. It produces a separate,
  explicitly synthetic display product, keeps measured samples fixed, and labels the
  estimated fraction. Show gaps / Fill gaps switches between that product and the
  measured mesh with the diagnostic plane. Source data and scoring never use the fill.
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
in meters. NoData samples are excluded from the range and remain holes in the measured mesh;
the display-only interpolation can cover them, or a labelled hatch can mark
their footprint on a reference plane.

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

### Camera framing improvements

Camera actions can be repeated after orbiting or panning. Reset and perspective
restore the default angle; Fit preserves the current angle and recenters the terrain.
Framing includes displayed relief and viewport aspect ratio, with clipping and zoom
limits adjusted to the terrain bounds. Separate comparison instances use independent
camera synchronization channels. Elevation summaries use a single pass so large DEMs
do not exceed JavaScript function argument limits.

For visual QA on macOS/Linux, set `CHROME_PATH` to your Chrome executable and run
`python qa_visual.py`. `TERRAIN_URL` optionally selects a different dev server.

## Planet surfaces and first person exploration

The default `surface` appearance uses the terrain body's artistic material: ochre
regolith for Mars, cratered gray regolith for the Moon, or layered grass, soil and
rock for Earth. Earth blends rocky areas using geometric slope, with broad color
variation, dry-grass patches and separate fine ground detail. These are artistic
material choices, not inferred vegetation or land-cover classifications.
The Surface menu can override that material without changing the terrain's body or
elevation data. Elevation gradient and neutral shading remain available. Materials
are generated locally with seamless color/bump textures and a second detail scale;
there are no texture downloads or external imagery licenses. These are illustrative
materials, not geographically registered satellite imagery. NoData holes remain
excluded from the measured terrain. They can be shown with a diagnostic hatch
or a clearly labelled display-only estimated fill.
Texture spacing preserves the terrain's horizontal aspect ratio.

Each viewer has a **POV · Explore surface** button. It opens a full-screen explorer
with a third person astronaut and a following camera by default:

- Drag the mouse or swipe the canvas to look around.
- Move with WASD, arrow keys, or the on-screen arrow buttons. Hold Shift for speed.
- Press Space or tap Jump to jump with the current world's gravity.
- Choose Third person or First person, and Slow, Explore, or Fast travel speed.
- The mint boundary and four corner beacons identify the selected source parcel.
- A live parcel map shows your location; Return to parcel restores a valid landing.
- Use the Earth/Mars/Moon buttons to change loaded terrain, material, lighting and sky.
- Press Escape or Exit POV to return to the comparison; keyboard focus is restored.

Ground height follows the rendered DEM triangles and displayed exaggeration.
Movement stays inside the selected source parcel, both on foot and in the air.
An inset keeps the astronaut inside its boundary. Segment checks reject every crossed
NoData triangle, even when both movement endpoints are valid. The surrounding 5×5
area remains decorative and can still be viewed by the camera.
The 24 surrounding parcels are deterministic decorative terrain with a gentle
curvature toward the horizon, not geographic measurements. They never cover the
source parcel or fill its NoData holes. A starfield and artistic horizon supply a
space setting. This is a local planet-like surface, not a globe reconstruction.
Third person uses an illustrative astronaut scale and a smoothed camera that stays
above intervening terrain. First person eye height is 1.7 source meters
with a 0.003 scene-unit minimum for display readability. Travel speed is a visual
navigation setting, not a measured walking speed. Decorative
rocks, sky and fog are artistic; rocks do not participate in collision or change
measured elevations. Switching worlds retains the normalized horizontal position and
look direction inside the selected parcel where valid, otherwise landing on a valid source triangle. This does not
imply geographic correspondence. Separate POV terrain is normalized to its own span.

Provide additional destinations through the optional `explorationTerrains` prop:

```tsx
<TerrainComparison target={mars} analog={earth} explorationTerrains={[moon]} />
<TerrainViewer terrain={earth} explorationTerrains={[mars, moon]} />
```

The comparison automatically supplies target and analog as destinations. Missing
planetary terrain leaves the corresponding button disabled. The demo includes three
144×144 synthetic landscapes, with hills/ridges and separate lunar crater terrain;
none represents real NASA measurements. The converter and real DEM inputs are unchanged.

### Comparison overview scenery

The overview canvases also show the 24 decorative context parcels, a starfield and a
small orbiting survey spacecraft. Context terrain is dimmed so the selected source
parcel remains prominent. Its mint boundary and corner beacons follow the source
surface; hovering the source mesh or focusing the Selected parcel button increases
its highlight. Clicking that button fits the source parcel. Context and spacecraft
are excluded from scientific inspection and camera-fit bounds.

Overview context uses the comparison's shared world span and display elevation offset,
so changing absolute/relative modes does not detach the source boundary. The central
DEM and its NoData holes remain unchanged. Surroundings are labeled generated scenery;
the orbital spacecraft is illustrative and stops when reduced motion is requested.

### Explorer character, camera guard and hidden encounter

The astronaut has a gold visor, helmet hardware, collar, suit joints, chest controls,
life-support pack, gloves and boots, with separate arm/leg swing and softened gait.
Overview orbit controls stop short of the horizon and pan horizontally. A height
guard keeps the camera above source DEM triangles and the actual tessellated context
surface, including relative display offsets and vertical exaggeration.

Click/tap the orbiting satellite (or focus its Inspect orbiting satellite button and
press Enter) for a hidden alien visitor near the selected parcel. The satellite pauses
on hover/focus for easier picking, and while the encounter is open. A second click or
the dismiss button sends the visitor away. The encounter does not change source data;
it skips the entrance/waving animation when reduced motion is requested.


### Planet-specific jumping

Space (from the terrain view) and the on-screen Jump button use the same impulse.
A single press produces one jump; holding Space or clicking again in the air does
not trigger another. Both first and third person views follow the jump. The astronaut
uses a suspended pose in the air and resumes walking on landing.

Approximate surface gravity comes from the NASA NSSDC fact sheets:
[Earth: 9.80 m/s²](https://nssdc.gsfc.nasa.gov/planetary/factsheet/earthfact.html),
[Mars: 3.73 m/s²](https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html), and
[Moon: 1.62 m/s²](https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html).
The same 3.6 m/s launch impulse is displayed at the astronaut's illustrative
0.14 scene-unit character scale, independently of DEM scale, travel speed and
vertical exaggeration. Thus lower gravity produces higher jumps and longer airtime,
without claiming DEM-meter-accurate human motion or local gravity measurements.

Vertical integration follows elapsed time and lands on the current DEM triangle.
Horizontal movement still respects parcel boundaries and NoData while airborne;
the player cannot jump into terrain above their feet. Return to parcel, terrain
replacement and planet changes safely reset the jump. A camera-view change preserves
it. Background-tab frame intervals are capped to avoid a large return-time leap.


### Measured Mars coverage and the NoData overlay

For the delivered 50×50 regional heightmaps, the API's actual missing samples are
583/2500 for Jezero (T-01, 23.32%), 198/2500 for Phoenix (T-04, 7.92%), and
514/2500 for Arcadia (T-05, 20.56%). These are raw heightmap mask fractions, distinct
from downstream feature-neighborhood support percentages. A triangle needs three
valid samples; consequently the omitted triangle fractions are larger: 39.30%,
16.62%, and 38.17%, respectively. The old black patches showed the background through
these missing triangles, rather than shadows or real depressions.

The diagnostic hatch makes the gaps explicit without changing elevations, masks,
provenance, feature extraction, scoring, inspection, or navigation. A continuous
measured model requires better source coverage. The optional display interpolation described below is a separate
estimated product and does not improve source coverage, validate a target, or
change ranking eligibility.

With the integrated frontend and real-data API running, verify against the delivered
records with `CHROME_PATH="/path/to/chrome" python tests/measured_nodata_check.py`.
`APP_URL` and `API_URL` override localhost ports 5173 and 8000. The check covers all
three targets, source-data preservation, POV labels, shaders and the mobile legend,
and writes both `qa-screens/nodata-t-*.png` and `qa-screens/filled-t-*.png` screenshots.


### Display-only gap filling

The viewer starts with **Estimated fill** enabled for missing height samples. **Show
gaps** restores the untouched measured mesh and its NoData hatching; **Fill gaps**
restores the continuous display. The same toggle is available in POV. Estimates have
a subtle warm tint, and the badge always reports the original missing sample fraction.

`visualInterpolation.ts` initializes missing samples from observed neighbors, then
relaxes only those samples with spacing-aware harmonic neighbor weights. Known
samples stay exactly fixed. Estimates remain within the valid source elevation range;
edge gaps are handled, and iteration work is capped for large rasters. This is an
artistic approximation, not a validated reconstruction or a replacement DEM. A private
copy is labelled synthetic and is used only by display geometry and camera clearance.

Heights, validMask, provenance, measured-data percentages, elevation extrema and all
backend features/scores remain unchanged. Inspection checks the original triangle,
so an estimated face cannot be reported as a measured elevation. Walking and jumping
still use the original mask and cannot enter estimated-only triangles or leave the
selected parcel. The camera can look across the filled surface and stays above it.
