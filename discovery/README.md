# AstroMatch Discovery: USGS and Earth Analog Data

## Data sources and preparation

The USGS release **Known Terrestrial Analog Sites for Planetary Science** by Marc A. Hunter (2020) was downloaded from the official release. DOI: https://doi.org/10.5066/P9J72921; ScienceBase item: `5f88940b82cebb8c13d912ee`.

The source Shapefile has 192 point records in EPSG:3857. The cleaned outputs retain all 192 records, convert geometry to EPSG:4326, and report zero null, empty, invalid, duplicate, or out-of-range geometries removed. See `data/processed/cleaning_report.json` for source and output SHA256 values and the full cleaning report. The USGS list is a known-site validation set, not a global inventory of Earth analog terrain.

## Known analogs

`out/known_analogs.json` keeps its existing schema and field names. `analog_for` describes which planetary target a record is associated with; it does not describe the celestial body where the site is located. All 192 sites are on Earth, and `analog_for` is empty for 191 records.

These records are **not target-validated analogs**: 190/192 are impact craters, and 191 records have an empty `analog_for`. A candidate's proximity to a USGS-listed site does not mean that it is a validated analog for that target; it indicates geographic proximity only.

For engine integration, Kişi 2 will align the adapter using `analog_id` → `region_id`, `theme` → `tags`, and `body="earth"` (option A). Do not merge the integration into main before that alignment is complete. USGS `g_...` cell keys do not match engine candidate IDs (`earth_grid_rNNN_cNNN`), so known-analog ranking and top-k recall do not work automatically in the engine. USGS validation is run separately with `discovery/validate_usgs`.

## Turkey analog records

`out/turkey_analogs.json` uses schema `0.3-draft`. Five sites use latitude and longitude from their regional `features.json` record, falling back to local only if regional is absent. Acigol has no separate feature record and retains its approximate supplied coordinates. The file keeps qualitative hypotheses separate from numeric metrics, which remain in `features.json`. T-04 is explicitly marked unavailable because no T-04 target record exists in the supplied `features.json`.

## Grid scope and global coordinate pool

The processed pilot grid contains 408 cells: a Turkey-centered 20 by 20 pilot plus four Atacama and four Iceland cells. It is a regional sample, not a global grid. Of the 408 cells, 216 pass the resolution and six-feature comparability checks. The `global_grid.py` module remains a placeholder; it does not scan the globe.

`out/global_pool.parquet` is a separate coordinate-only pool generated over all 0.5-degree cell centers. Land fraction is approximate: 25 `global-land-mask` point samples per cell, retaining cells with estimated land fraction at least 0.5. It contains no terrain features or scores. It currently has 579 scanned cells (179 pilot, 400 validation sample), 1,639 `not_scanned`, and 83,694 `out_of_coverage`. `out_of_coverage` does not mean unscanned global terrain was measured.

`out/global_candidates.geojson` is a scored export from the supplied regional grid. Its 216 features are not global coverage; its metadata records that scope.

## Scoring, validation, and stability

The scoring features are `slope_median_deg`, `slope_p90_deg`, `flat_fraction`, `tri_median_m`, `relief_m`, and `elevation_std_m`.

The pilot USGS validation (`out/validation/validation_results.json`) is `not_evaluable` for T-02 because none of the known analog cells overlap its valid scored cells. The independent sample results are under `out/validation/usgs_sample/`: 176 valid positive cells and 220 valid background cells for T-02. T-01 and T-03 are unscorable. AUC is 0.4621 with bootstrap 95% interval [0.4432, 0.4802], permutation p=1.0, mean positive percentile 48.02, and top 1% / 5% enrichment 0.5625 / 0.1125. The result is negative: **the score did not distinguish known analogs from background**. Sensitivity excluding positive neighbors gives AUC 0.4604 [0.4408, 0.4798]. The background is unlabeled, not confirmed negative examples. Diagnostics are in `out/validation/usgs_sample/diagnostics.json` and `.csv` (or timestamped equivalents if those names already existed).

Stability outputs are under `out/stability/`. They use T-02, 50 runs per noise level (1%, 5%, 10%), seed 42, and separate `end_to_end` and `frozen` sigma modes. At 1% noise, mean top-5 Jaccard is 0.860 / 0.867 and mean Spearman is 0.99964 / 0.99967 for end-to-end / frozen. At 5%, the values are 0.636 / 0.625 and 0.99542 / 0.99558. At 10%, they are 0.414 / 0.417 and 0.98466 / 0.98508. These are regional-grid results for T-02; they do not establish stability for Mars targets.

Most USGS records are impact craters (190 of 192). Crater-centered 50 by 50 km windows can make relief and roughness reflect crater morphology, so AUC can confound analog quality with crater-like terrain discrimination. T-02 is Shackleton on the Moon; these results do not apply to Mars. Univariate AUC is not evidence of causality. Background cells were selected from those passing WorldCover QA; `VALIDATION_SAMPLE.md` does not state whether the same QA was applied to analog cells.

## Integration

The adapter mapping described above remains an integration requirement. The engine does not load `turkey_analogs.json` or `global_candidates.geojson`.

## File map

- `data/raw/`: downloaded USGS ZIP and metadata; `data/raw/extracted/` contains the source Shapefile components.
- `data/processed/usgs_analogs_clean.geojson`, `usgs_analogs_clean.csv`, `cleaning_report.json`: source preserving cleaned release and audit report.
- `data/inputs/`: pilot grid, coverage, real `features.json`, scores, validation sample snapshot, and source manifests. These inputs are ignored by Git.
- `out/known_analogs.json`: 192 USGS records mapped to cell keys.
- `out/turkey_analogs.json`: six qualitative Turkish site records.
- `out/global_pool.parquet`: coordinate-only global land-cell pool; no features or scores.
- `out/global_candidates.geojson`: scored cells from the regional pilot grid.
- `out/validation/`: pilot and independent-sample validation reports and request artifacts.
- `out/stability/`: T-02 noise stability reports for both sigma modes.
- `out/scores/`: traceable copies of pilot and validation score tables.

## Commands

Run from the repository root with the discovery environment activated:

```powershell
python -m pip install -r discovery/requirements.txt
```

Build the Turkish records and coordinate pool:

```powershell
python -m discovery.build_turkey_analogs
python -m discovery.global_pool
```

Validate the independent sample after its score table is available:

```powershell
python -m discovery.validate_usgs --grid discovery/data/inputs/earth_grid_validation.parquet --scores discovery/data/inputs/scores_validation.parquet --out-dir discovery/out/validation/usgs_sample
```

Run stability separately for each sigma mode, supplying the external engine directory:

```powershell
python -m discovery.stability_test --grid discovery/data/inputs/earth_grid.parquet --engine-path C:\Users\eraym\astromatch_ext\engine_main --target-id T-02 --sigma-mode end_to_end
python -m discovery.stability_test --grid discovery/data/inputs/earth_grid.parquet --engine-path C:\Users\eraym\astromatch_ext\engine_main --target-id T-02 --sigma-mode frozen
```

Export the scored regional candidates:

```powershell
python -m discovery.export_global_candidates --grid discovery/data/inputs/earth_grid.parquet --scores discovery/data/inputs/scores_all.parquet --analogs discovery/out/known_analogs.json --turkey discovery/out/turkey_analogs.json
```
