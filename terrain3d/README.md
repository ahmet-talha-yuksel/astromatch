# AstroMatch AI — standalone Terrain3D module

## Start (Node.js 20.19+ recommended)

```bash
npm install
npm run dev
```

The initial demo uses **synthetic** elevation data. It is **not NASA terrain**.

## Integrate into the main React/TypeScript app

Copy `src/` to a dedicated `terrain3d/` module directory in the host app.
Install `three`, `@react-three/fiber`, `@react-three/drei` and `@types/three` in the host project.
Import from `terrain3d/src/index.ts`:

```tsx
import { TerrainComparison } from "./terrain3d/src";
<TerrainComparison target={marsTerrain} analog={earthTerrain} />
```

The `TerrainData` contract is in `src/types/terrain.ts`. Data can be fetched as JSON
by the host app. There is no backend dependency.

## Convert real DEM data

```bash
pip install rasterio numpy
python converter/dem_to_json.py path/to/projected_dem.tif public/terrain/mars.json --name "Mars region" --body Mars
```

**Input requirements:** single-band elevations in meters, projected coordinates in meters,
approximately square pixels, valid cells only. Crop/reproject beforehand. This converter
does not harmonize DEM resolution, planetary datums, or physical comparison windows.
Use the same physical window and processing resolution for scientific comparisons.

## Current scope

- Independent Vite demo and reusable exported components
- 3D terrain mesh from elevation matrix
- Orbit/zoom via mouse, side-by-side comparison
- Source, sample spacing and vertical exaggeration labels

## Next steps

- Add validated real MOLA/LOLA/SRTM DEM examples.
- Add terrain metadata: product version, processing date, window size, datum.
- Add automated unit tests and verified offline packaging.
- Check target/analog physical extents and matching cell sizes.
- Optional synchronized cameras.

**Scientific caution:** A 3D topographic resemblance is not evidence of equivalent
gravity, atmosphere, radiation, mineralogy, or mission safety.
