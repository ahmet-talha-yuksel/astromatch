# Module boundaries
- `processing/` (Person 1): real NASA DEM ingest + terrain metrics
- `engine/` (Person 2): metric similarities, weighted ranking
- `discovery/` (Person 3): global grid and Türkiye candidate selection
- `terrain3d/`, `validation/`, `docs/` (Person 4): reusable 3D and verification
- `frontend/`: independent frontend team; starter is only a placeholder

API: GET /health, GET /api/targets, GET /api/candidates, POST /api/rank.
`POST /api/rank`: `{ "target_id": "mars_jezero", "weights": {"slope_deg": 1, "tri_m": 1, "relief_m": 1} }`.

Terrain3D: `TerrainComparison({target, analog})` with `TerrainData` from
`terrain3d/src/types/terrain.ts`. No direct frontend coupling.
