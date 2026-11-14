# Multi-continent Earth expansion

The original `out/earth_grid.parquet` remains unchanged. The extension reuses the same stable 0.5-degree global cell IDs and adds 604 distinct real regional DEM windows. Four existing Atacama cells are skipped rather than replaced. Each window is 50×50 km in local LAEA at 1000 m resolution.

| Region | New windows | Source |
| --- | ---: | --- |
| Southwestern USA | 100 | NASA SRTMGL30.002 |
| Andes / Atacama | 96 | NASA SRTMGL30.002 |
| Sahara | 100 | NASA SRTMGL30.002 |
| East Africa | 100 | NASA SRTMGL30.002 |
| Arabia | 100 | NASA SRTMGL30.002 |
| Iran | 100 | NASA SRTMGL30.002 |
| Central Australia | 4 | Copernicus GLO-90 |
| East Asia | 4 | Copernicus GLO-90 |

Together with the original 408 cells, the combined dataset contains 1,012 cells. The original Turkey pilot area contributes 400 (39.5%). That pilot area's rectangular bounds also include locations outside Turkey; `pilot_area=turkey` is an operational area label, not a country boundary classification. The selection covers five continents, with intentionally unequal sample counts. It is a bounded sample of multiple regions, not an exhaustive or statistically representative global survey. The map must keep unscanned regions unknown.

Quality follows the established regional processing contract. Native SRTM latitude limits are enforced and source tiles must contain the complete physical window. Source URLs, archive hashes, crop hashes and vertical references are preserved. Every new window gets ESA WorldCover 2021 v200 permanent-water sampling at 100 m and 50 m spacing; unknown area must be <=5% and land-fraction sampling difference <=0.01. Failed/unavailable masks and terrain with excess NoData stay in the dataset with comparable flags closed. Snow/ice is land; height zero is never treated as water. Existing terrain definitions and target-matching validation are retained.

Reproduce/resume from the repository root:

```sh
processing/.venv/bin/python -m processing.scripts.expand_global --accessed-on YYYY-MM-DD
```

This reads the existing cached NASA SRTM inputs and downloads public Copernicus and ESA data where required. Per-cell masks are checkpointed; rerunning reuses matching completed mask requests. Raw TIFFs are ignored by Git. `out/global_expansion/summary.json` reports actual eligible counts, mask errors, area counts and the unchanged base-grid hash.

Use the combined dataset with the engine:

```sh
export ASTROMATCH_GRID=processing/out/global_expansion/earth_grid_combined.parquet
export ASTROMATCH_COVERAGE=processing/out/global_expansion/coverage_combined.geojson
```

Compose defaults point to those combined outputs. Existing environment overrides remain supported. New heightmaps are also published under `processing/out/heightmaps/` so existing map and terrain path resolution works. Full records, source evidence and mask QA live in `out/global_expansion/`; the original regional delivery and Earth grid remain available for regression comparison.

The expansion retains `metric-gradient-riley8-p95p5-v1` for Earth as in the existing regional grid. Mars measured-only estimator differences remain an explicit engine sensitivity concern; this expansion does not validate equality of those methods or establish landing suitability. No new local-scale reference population, monthly temperature or NDVI measurements are supplied.
