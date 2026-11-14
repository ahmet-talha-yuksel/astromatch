# Validation sample request

## Why this request is needed

The analog group identifies known analog cells for the independent validation sample. The background group provides a reproducible random set of other cells for the same validation request.

## Selection

- Analog cells are grouped by `cell_key` recomputed from the supplied analog coordinates with `discovery.analog_mapping.cell_id`; names sharing a cell are joined with `; `.
- Background cells are 0.5-degree cell centers between latitudes -60 and 70, sampled without replacement with seed 42.
- Analog cells, the 408 processed cells, and cells marked `not_scanned` in `coverage.geojson` are excluded from background sampling.
- No land/ocean filter is applied. Person 1's `land_fraction` filter is expected to handle ocean cells.
- `order` is 1 through 1500 for the randomized background permutation; analog rows have an empty `order`.

## Expected output from Person 1

For the requested cells, return `earth_grid.parquet` with the same schema, the same 50x50 km window, and the same processing version as the source grid. Preserve `cell_key` so the returned records can be joined to this request.
