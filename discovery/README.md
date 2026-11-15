# AstroMatch Discovery: USGS and Earth Analog Data

## Data sources and preparation

The USGS release **Known Terrestrial Analog Sites for Planetary Science** by Marc A. Hunter (2020) was downloaded from the official release. DOI: https://doi.org/10.5066/P9J72921; ScienceBase item: `5f88940b82cebb8c13d912ee`.

The source Shapefile has 192 point records in EPSG:3857. The cleaned outputs retain all 192 records, convert geometry to EPSG:4326, and report zero null, empty, invalid, duplicate, or out-of-range geometries removed. See `data/processed/cleaning_report.json` for source and output SHA256 values and the full cleaning report. The USGS list is a known-site validation set, not a global inventory of Earth analog terrain.

## Known analogs

`out/known_analogs.json` keeps its existing schema and field names. `analog_for` describes which planetary target a record is associated with; it does not describe the celestial body where the site is located. All 192 sites are on Earth, and `analog_for` is empty for 191 records.

These records are **not target-validated analogs**: 190/192 are impact craters, and 191 records have an empty `analog_for`. A candidate's proximity to a USGS-listed site does not mean that it is a validated analog for that target; it indicates geographic proximity only.

The current engine adapter accepts these records: `analog_id` becomes `region_id`, `theme` becomes `tags`, the body is normalized to `earth`, and `analog_for` is preserved. USGS `g_...` cell keys still differ from engine grid IDs (`earth_grid_rNNN_cNNN`), so location-based validation is performed separately with `discovery/validate_usgs`.

## Turkey analog records

`out/turkey_analogs.json` uses schema `0.3-draft`. Five sites use latitude and longitude from their regional `features.json` record, falling back to local only if regional is absent. Acigol has no separate feature record and retains its approximate supplied coordinates. The file keeps qualitative hypotheses separate from numeric metrics, which remain in `features.json`. T-04 is explicitly marked unavailable because no T-04 target record exists in the supplied `features.json`.

## Grid scope and global coordinate pool

`data/inputs/earth_grid.parquet` is a regional pilot: 408 processed cells, 216 valid/comparable cells. It is centered on Turkey with small Atacama and Iceland samples; it is **not a global grid**. The separate `out/global_pool.parquet` contains coordinates only, not terrain features or scores. It uses 25 `global-land-mask` point samples per 0.5-degree cell and retains estimated land fraction >= 0.5. The current pool has 579 scanned cells (179 pilot, 400 validation sample), 1,639 `not_scanned`, and 83,694 `out_of_coverage`; the latter is a coverage label, not a measurement of all global terrain.

## Current scored results (engine c6e4be4)

The current run is `out/runs/c6e4be4_v2/`, produced with engine commit `c6e4be499ebfac7e7d5fbcb544c027b74475eaf5`. Its complete inputs, package versions, commands, and source commits are recorded in `out/runs/c6e4be4_v2/RUN_INFO_v2.json`. The earlier engine `4ca89bc` results are retained for traceability under `out/archive/engine_4ca89bc/`; they predate calibration and are not current results.

### Target identities and feature availability

`T-01`, `T-02`, and `T-03` retain their specification aliases for Jezero, Shackleton, and Marius Hills. Phoenix and Arcadia use their engine region IDs, `mars_phoenix_regional` and `mars_arcadia_regional`; they are not T-04/T-05 aliases. Optional T-04 Tharsis is not scored in this run. `T-04` in `out/turkey_analogs.json` names the optional Tharsis hypothesis.

Jezero is evaluated with five of six scoring features; `slope_p90_deg` is excluded. Its target record has `resolution_validated=false`; all six feature `comparable` flags in that source record are false. Marius Hills has no valid score (`resolution_not_validated`) and all six scoring features are excluded. The score and validation outputs retain both the requested target ID and `engine_region_id`.

The engine loads `processing/out/real/features.json`, followed by `processing/out/mars_measured/features.json`; for equal or unknown processing versions the later file wins. The `engine_refresh` copy at commit `c6e4be4` was used. Neither source file differs between `c6e4be4` and `origin/main`. The discovered regional target values are:

| Target / loaded record | resolution_validated | slope median (deg) | slope p90 (deg) | flat fraction | TRI median (m) | relief (m) | elevation std (m) | comparable flags (same feature order) |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Jezero / `mars_jezero_regional` (`mars_measured`) | false | 1.4405 | 6.8147 | 0.8421 | 75.3586 | 805.8346 | 275.6281 | F, F, F, F, F, F |
| Shackleton / `moon_shackleton_regional` (`real`) | true | 8.3934 | 22.7676 | 0.2596 | 413.3622 | 2783.0303 | 918.2550 | T, T, T, T, T, T |
| Phoenix / `mars_phoenix_regional` (`mars_measured`) | true | 0.5178 | 1.8192 | 0.9794 | 26.6621 | 243.3709 | 88.3802 | T, T, T, T, T, T |
| Arcadia / `mars_arcadia_regional` (`mars_measured`) | true | 1.5613 | 5.5627 | 0.8828 | 72.7447 | 555.9476 | 194.3952 | T, T, T, T, T, T |

All four source records have `processing_version=0.3.0`. Their `quality.sampling.note` says that nonzero counts indicate measured source bins, while other DEM bins are interpolated, and that this diagnostic does not automatically validate effective resolution. No separate probe explanation was present. In these four rows, target AUC decreases monotonically as `relief_m` and `slope_p90_deg` increase; this is a descriptive ordering of these records only (n=4 targets; descriptive, not a statistical test).

### Independent USGS sample validation

The primary validation uses only `earth_grid_validation.parquet`, not the 408-cell pilot. Each scoreable target uses 176 positive USGS cells and 220 background cells. Bootstrap and permutation tests use 1,000 iterations. Bonferroni threshold is `0.05/4 = 0.0125`.

| Target | AUC [95% bootstrap CI] | Permutation p | Mean positive percentile | Bonferroni |
|---|---:|---:|---:|---|
| T-01 / Jezero | 0.5044 [0.4496, 0.5652] | 0.4246 | 50.37 | not passed |
| T-02 / Shackleton | 0.4684 [0.4111, 0.5279] | 0.8601 | 48.37 | not passed |
| T-03 / Marius Hills | null (unscorable) | null | null | not tested |
| `mars_phoenix_regional` | 0.6433 [0.5910, 0.6948] | 0.0010 | 58.09 | passed |
| `mars_arcadia_regional` | 0.5187 [0.4601, 0.5736] | 0.2408 | 51.16 | not passed |

Phoenix is the only result passing the Bonferroni threshold (p=0.0010, alpha=0.0125). Its AUC (0.643) is statistically indistinguishable from the raw flat_fraction baseline (AUC 0.606; paired bootstrap difference 95% CI [-0.034, 0.117]) while exceeding the -relief_m, -slope_median_deg and -elevation_std_m baselines, so the result does not show information beyond terrain flatness. The flat-fraction reference AUC is 0.6063; its latitude-stratified pooled AUC is 0.6284. The target-score latitude-stratified pooled AUCs are Jezero 0.4868, Shackleton 0.4482, Phoenix 0.6373, and Arcadia 0.4976. Per-band counts and AUCs are in `usgs_sample/diagnostics_v2.json`.

The paired bootstrap intervals below are for `target AUC ? reference AUC`. If an interval includes zero, the target AUC is ?referanstan ay?rt edilemez?; if wholly positive, ?referanstan y?ksek?; if wholly negative, ?referanstan d???k?.

| Target | flat_fraction | -relief_m | -slope_median_deg | -elevation_std_m |
|---|---|---|---|---|
| T-01 | [-0.2071, -0.0004] ? referanstan d???k | [-0.1323, 0.0961] ? referanstan ay?rt edilemez | [-0.1156, 0.1058] ? referanstan ay?rt edilemez | [-0.1407, 0.0827] ? referanstan ay?rt edilemez |
| T-02 | [-0.2370, -0.0296] ? referanstan d???k | [-0.1642, 0.0615] ? referanstan ay?rt edilemez | [-0.1549, 0.0718] ? referanstan ay?rt edilemez | [-0.1665, 0.0468] ? referanstan ay?rt edilemez |
| Phoenix | [-0.0339, 0.1172] ? referanstan ay?rt edilemez | [0.0294, 0.2087] ? referanstan y?ksek | [0.0505, 0.2140] ? referanstan y?ksek | [0.0322, 0.1989] ? referanstan y?ksek |
| Arcadia | [-0.1886, 0.0244] ? referanstan ay?rt edilemez | [-0.1152, 0.1030] ? referanstan ay?rt edilemez | [-0.0935, 0.1218] ? referanstan ay?rt edilemez | [-0.1213, 0.0922] ? referanstan ay?rt edilemez |

All target validations use the same positive set; `analog_for` is empty for 191/192 USGS records. Therefore, these results are **not evidence of target-specific analog quality**. The background was selected from cells that passed WorldCover QA; the sample documentation does not say whether identical QA was applied to analog cells. A univariate AUC is not causal evidence.

### Stability

The T-02/Shackleton stability run uses the 408-cell pilot, 50 repetitions per noise level, seed 42, and noise levels 1%, 5%, and 10%. Jaccard is mean top-5 Jaccard; Spearman is mean rank correlation.

| Sigma mode | Noise | Top-5 Jaccard | Spearman |
|---|---:|---:|---:|
| end_to_end | 1% | 1.0000 | 0.999562 |
| end_to_end | 5% | 1.0000 | 0.996346 |
| end_to_end | 10% | 0.9933 | 0.992225 |
| frozen | 1% | 1.0000 | 0.999618 |
| frozen | 5% | 1.0000 | 0.996668 |
| frozen | 10% | 0.9933 | 0.992630 |

These are regional pilot results for Shackleton, not global stability results.

### Candidate export and archive map

`out/global_candidates.geojson` is the canonical copy of `out/runs/c6e4be4_v2/global_candidates.geojson`: 589 features, comprising 216 pilot, 370 validation-sample, and 3 `reference_only` features. The grid scope is regional, not global; the file contains scored candidates only where valid grid scores exist plus reference locations. It is not a global 0.5-degree terrain-feature grid.

- `out/runs/c6e4be4_v2/`: current scores, validation, diagnostics, stability, export, and `RUN_INFO_v2.json`.
- `out/archive/engine_4ca89bc/`: prior calibration-era score, validation, stability, and GeoJSON outputs, retained only for traceability.
- `out/validation/`: motor-independent coverage reports and validation-sample request artifacts.
- `C:\Users\eraym\astromatch_ext\discarded\runs_c6e4be4\`: old alias-label run directory moved outside the repository.

### Reproduction

Run from the repository root with the discovery environment and the external engine archive available. The ignored source inputs are restored as bytes from their recorded source commits; do not use PowerShell text redirection for Parquet files. For example:

```powershell
python -c "import pathlib,subprocess; src='processing/out/earth_grid.parquet'; dst=pathlib.Path('discovery/data/inputs/earth_grid.parquet'); dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(subprocess.run(['git','show',f'origin/main:{src}'],check=True,stdout=subprocess.PIPE).stdout)"
```

Restore `earth_grid_validation.parquet`, `features.json`, and coverage files from the commits recorded in `data/inputs/SOURCE*.txt` using the same byte-writing pattern and their recorded Git paths. Recreate the external engine archive with:

```powershell
git archive c6e4be4 engine processing/out/real/features.json processing/out/mars_measured/features.json | tar -x -C C:\Users\eraym\astromatch_ext\engine_refresh
```

The v2 score tables were generated by calling `engine.validation_api.score_grid` for each target with `weights=None`, `sigma=None`, and `return_criteria=True`; target IDs, feature mapping, output paths, input commits, and package versions are recorded in `out/runs/c6e4be4_v2/RUN_INFO_v2.json`. Re-run validation with:

```powershell
python -m discovery.validate_usgs --grid discovery/data/inputs/earth_grid_validation.parquet --scores discovery/out/runs/c6e4be4_v2/scores_validation.parquet --out-dir discovery/out/runs/c6e4be4_v2/usgs_sample
```

Re-run the two stability modes and export with:

```powershell
python -m discovery.stability_test --grid discovery/data/inputs/earth_grid.parquet --engine-path C:\Users\eraym\astromatch_ext\engine_refresh --target-id T-02 --sigma-mode end_to_end --out-dir discovery/out/runs/c6e4be4_v2/stability
python -m discovery.stability_test --grid discovery/data/inputs/earth_grid.parquet --engine-path C:\Users\eraym\astromatch_ext\engine_refresh --target-id T-02 --sigma-mode frozen --out-dir discovery/out/runs/c6e4be4_v2/stability
python -m discovery.export_global_candidates --grid discovery/data/inputs/earth_grid.parquet discovery/data/inputs/earth_grid_validation.parquet --scores discovery/out/runs/c6e4be4_v2/scores_pilot_408.parquet discovery/out/runs/c6e4be4_v2/scores_validation.parquet --analogs discovery/out/known_analogs.json --turkey discovery/out/turkey_analogs.json --top-k 500 --out discovery/out/global_candidates.geojson --engine-commit c6e4be499ebfac7e7d5fbcb544c027b74475eaf5
```

The validation and stability commands write results; preserve existing run artifacts before executing them again.
