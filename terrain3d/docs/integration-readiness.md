# Phase 6 integration readiness

Status is based on repository contents inspected on 2026-11-14. No external datasets were downloaded and no files outside `terrain3d/` were modified.

| Producer | Status | Evidence / blocker |
|---|---|---|
| Ahmetson / DEM processing | **BLOCKED** | No GeoTIFF or processed DEM exists under `data/processed/`; bundled terrain JSON is explicitly synthetic. |
| David / similarity engine | **PARTIALLY READY** | `shared/examples/similarity.synthetic.json` exists and matches the optional adapter; no production result set was found. |
| Yenge / candidate discovery | **PARTIALLY READY** | `data/processed/candidates.json` contains synthetic metadata, but no candidate-to-terrain dataset links. |
| Terrain3D viewer | **READY** | Runtime validation, NoData-safe geometry, comparison controls, shared scale/legend and metadata display are implemented. |

## Contracts found

The canonical contract is `terrain3d/src/types/terrain.ts` plus its runtime validator.
`shared/terrain.schema.json` is an older legacy schema and does not describe the current
`heights`, datum, CRS and provenance fields. Synthetic fixtures are in
`terrain3d/public/terrain/`. Backend schemas exist but Terrain3D remains independent.

## Required handoff

Ahmetson: regular metric grid, row-major meter elevations, X/Y output spacing and
sample-center window, source resolution, CRS, vertical datum, NoData mask and truthful
real-data provenance. David: target/candidate IDs, documented score direction, finite
scores in `[0,1]`, and explanations. Yenge: stable candidate IDs, coordinate assumptions,
and an explicit `terrainId` only where a processed Earth terrain exists.

## Verification run (2026-11-14)

The existing Docker container `terrain3d-debug` supplied Node.js v22.23.5, npm 10.9.9,
and the installed dependency tree. `npm test` passed all 19 TypeScript/Node tests. The
production `npm run build` passed (`tsc -b` and Vite production bundle; Vite emitted only
the existing large-chunk warning). The host has Python 3.14.5 and the isolated
`terrain3d/.phase6-venv` has pytest 9.2.0; converter tests passed 4 tests.

Playwright 1.65.2 was installed into the isolated venv and used with the existing Chrome.
Browser verification was split into fresh, single-purpose sessions and a test-only
two-canvas comparison route. A development-only camera-state inspection hook is active
only under `/tests/`. The isolated viewer case passed WebGL context/mesh rendering,
rotation, panning, zoom distance, metadata, NoData coverage, synthetic warnings and
exaggeration. The comparison case passed bidirectional camera synchronization,
independence with synchronization disabled, relative/absolute elevation modes, shared
exaggeration and synthetic warnings. The generated GeoTIFF JSON loaded successfully in
the viewer route with its physical spacing, window and valid-data percentage. A separate
fresh session also passed Reset Camera, Top View, Perspective View, Fit Terrain, the
vertical-exaggeration endpoints, Earth fixture dimensions, and missing/malformed JSON
handling. The final browser sessions had no page errors or WebGL errors.

The generated synthetic GeoTIFF → converter → JSON → TypeScript validator pipeline passed:
the 3×3 output preserved row-major heights, central NoData, `{x:10,y:20}` spacing, and a
20×40 m physical window. Loading that JSON into the browser passed.

No Ahmetson DEM, David production similarity result, or Yenge candidate-to-terrain link
was present. Adapter tests explicitly reject absent, malformed, and unresolved outputs;
no values or provenance are synthesized.

