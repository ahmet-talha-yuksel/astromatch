# Validation score interface

```python
from engine.validation_api import score_grid, list_target_ids

score_grid(grid_df, target_id, weights=None, *, sigma=None,
           scale="regional", return_criteria=False) -> pandas.DataFrame
```

`grid_df` accepts flattened v2.3 grid columns: `cell_id` (or `region_id`), `scale`, `resolution_validated`, and configured feature values. Optional `<feature>__comparable` defaults to the row's resolution validation for topography. The result preserves every input row and its order. Its columns are `cell_id`, `score`, `n_features`, and `excluded_reason`. `score` is the geometric score divided by 100, hence 0–1; ineligible rows get `NaN`, never zero. `return_criteria=True` adds `s_<feature>` columns (raw similarity, 0–1, `NaN` when not eligible). `df.attrs["sigma"]` and `df.attrs["sigma_source"]` contain the values and provenance used; `sigma_table` also includes sample counts. Calls are deterministic and do not mutate `grid_df`.

The configured aliases are returned by `list_target_ids()`: T-01 is Jezero, T-02 Shackleton, T-03 Marius Hills; T-04 is currently unassigned. A regional grid uses the target's `*_regional` record. By default target records come from `processing/out/real/features.json` when present, otherwise mock records. The current real Jezero and Marius regional targets have `resolution_validated=false`, so they yield all `NaN`. Shackleton is eligible. The current `processing/out/real/earth_grid.parquet` has only eight regional site rows (`grid_status=sites_only`); it is not a global grid.

## Sigma and noise tests

- `sigma=None` (default): recompute sigma from the supplied grid on every call. This measures **end-to-end** sensitivity: noise changes both values and possibly calibration.
- `sigma="frozen"`: compute sigma once from the default reference grid for that scale and cache it. This isolates score sensitivity to the changed cell values. It is stable across calls with different supplied grids.
- `sigma={feature: positive_value, ...}`: use a complete explicit table. All configured features are required.

```python
from engine.validation_api import score_grid
base = score_grid(grid_df, "T-02", sigma="frozen")
noisy = grid_df.copy()
noisy["slope_median_deg"] *= 1 + rng.normal(0, .05, len(noisy))
changed = score_grid(noisy, "T-02", sigma="frozen")
# Compare base.score and changed.score on rows where both are finite.
```

## Features and eligibility

The score uses the six features in `config/features.yaml`: `slope_median_deg`, `slope_p90_deg`, `flat_fraction`, `tri_median_m`, `relief_m`, and `elevation_std_m`. The base weight of each is 1. `config/presets.yaml` multiplies selected weights: `landing_ops` gives flat fraction 3, p90 slope 3, median slope 2; `rover_mobility` gives TRI 3, p90 slope 2, relief 2; `geomorphology` gives relief 3, elevation standard deviation 2, TRI 2. `balanced` keeps all at 1. `weights` accepts a preset name or a custom modifier dictionary.

Both target and cell require matching scale and validated resolution. Each feature needs finite values and comparability on both sides. At least three positively weighted features must qualify; eligible weights are renormalized. The geometric score uses a 0.01 floor on individual similarities. A target failing these requirements yields all `NaN` with a `target_unscorable` reason. Missing cells do not become zero scores.

## CLI export

```bash
python -m engine.cli export-scores --mock --criteria --out engine/out/scores/
python -m engine.cli export-scores --features processing/out/real/features.json --grid processing/out/real/earth_grid.parquet --out engine/out/scores/
```

The CLI writes `scores_all.parquet`, `scores_all.csv`, and `scores_manifest.json`. It exports one row per input cell and available regional target, including NaNs (empty fields in CSV). The manifest records data status, input SHA-256 values, engine version, sigma table and mode, aliases, counts, and unscorable reasons. The CLI defaults to `processing/out/earth_grid.parquet`; when that path is absent it uses `processing/out/real/earth_grid.parquet` and marks its eight rows as `sites_only`.
