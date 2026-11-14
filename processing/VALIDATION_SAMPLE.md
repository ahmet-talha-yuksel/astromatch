# USGS validation sample

Input snapshots are copied without modification from `origin/feature/discovery` (commit `8d3045a97ed3bfef3593b99db6bfe23aff58f390`) at `discovery/out/validation/validation_sample_request.csv` and `README_request.md` into `processing/requests/usgs_validation/`.

Run/resume:

```sh
processing/.venv/bin/python -m processing.scripts.validation_sample --accessed-on YYYY-MM-DD
```

All 187 analog cells are attempted first. Background rows are visited strictly by the supplied unique `order`. Selection requires ESA WorldCover sampling QA and `land_fraction >= 0.5`. The stopping rule is **220 land-qualified attempts**, independently of DEM outcome. DEM failures are logged and are not replaced by cells chosen for better DEM quality. Unknown masks are failures, never ocean labels. Parallel mask prefetch does not change recorded selection order. The script saves a checkpoint after every delivered result.

Output `processing/out/earth_grid_validation.parquet` has exactly the same Arrow schema, column order, types and schema metadata as the original 408-cell `processing/out/earth_grid.parquet`. The original file is never modified. Processing uses the same `0.3.0` implementation, `metric-gradient-riley8-p95p5-v1`, 50×50 km LAEA windows and 1000 m spacing. Existing verified local NASA SRTMGL30.002 tiles are used within native latitude bounds when they contain the complete physical window; elsewhere public Copernicus GLO-90 COG crops are used. Copernicus is a DSM. EGM96 and EGM2008 references remain explicit, as in the pilot.

To preserve the existing schema, `cell_key` is stored in each row's `provenance_json` and in `out/validation_sample/cell_key_map.csv`, joining on `region_id`. The CSV also contains group, original order, outcome and skip/failure reason. `ledger.json` includes every attempted/skipped request row, mask status, land fraction and processing timings. `summary.json` contains delivered counts, original-grid hash, elapsed time and the background prefix boundary. `features.json` preserves full per-cell metadata and mask/source evidence; heightmap paths resolve relative to `out/validation_sample/`.

Records with computable terrain but failed land/terrain QA are retained with comparison flags closed. Processing failures without a terrain record occur only in the ledger/mapping CSV. This permits explicit missingness accounting rather than silently selecting only high-quality examples. Independent validation must report these exclusions. Engine comparisons additionally need a validated target using matching method/scale; this sample does not change Mars method policy.

The 408 pilot cells are 400 cells in a 20×20 center grid covering the 10°×10° [25,30,35,40] pilot area, plus four Atacama and four Iceland cells. Hassa is east of its 35°E limit and hence not selected in the discovery grid; separately processed curated Hassa local/regional records exist. Later multi-continent expansion is separate and does not alter this request's fixed input population.

## Delivered result (2026-11-15)

All 187 analog requests were attempted: 185 terrain records returned, 2 unavailable DEM failures (`g_042.75_-64.25`, `g_073.75_029.75`). Nine returned analog records have comparison flags closed by land-mask QA / land fraction <0.5. Background orders 1 through 753 were visited without gaps; the first 220 mask-qualified land cells all produced terrain records. The final Parquet contains 405 records, 396 operationally eligible. Original-grid SHA-256 is `eaf434a1fe1b9de3ae81f3762826c8b63154fce53696a7c37c5c1552bf20297e` and is unchanged. Processing took about 9 minutes in this run; this is an observation with shared caches, not a universal runtime guarantee. All 128 processing tests passed.

Deliver on `feature/data`. `out/validation_sample/skipped_cells.json` explicitly lists every skipped or failed visited request. Unvisited background orders 754–1500 are outside the delivered sample; they were not evaluated for selection. Use `cell_key_map.csv` to join delivered records to the original request without altering the pilot Parquet schema.
