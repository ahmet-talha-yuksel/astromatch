# Module boundaries

Processing provides v2.3 target and Earth feature records. The engine adapts and scores them. The backend initializes one Dataset during FastAPI startup and exposes `/api/v1` endpoints. Validated real target and Earth feature records are available in `processing/out/real/` and `processing/out/mars_measured/`; set `ASTROMATCH_FEATURES` to both paths for the measured Mars targets. The terrain3d component remains separate.

## API

- `GET /api/v1/health`: active mode, data status, engine version, dataset counts, optional ML availability.
- `GET /api/v1/targets`, `GET /api/v1/presets`: target summaries and feature labels/units.
- `GET /api/v1/rank` and `POST /api/v1/rank`: ranked candidates; POST accepts custom weights.
- `GET /api/v1/sites`: all local Earth sites with criterion details for cards, without top-k cut or NMS.
- `GET /api/v1/heat`: precomputed heat points when available, computed otherwise.
- `GET /api/v1/regions/{region_id}`: raw record and scores against matching-scale targets.
- `GET /api/v1/explain`: deterministic explanation for one candidate.
- `GET /api/v1/compare`: one target/candidate comparison card with features, criterion similarities, robust z offsets, score interval, place, and limitations.
- `GET /api/v1/validation`: validation report when available.

New API `score_geo`, `score_arith`, and `score_relative` use **0–100**. `score_geo` is the absolute primary score; relative score means closest available Earth record equals 100. `match_level=relative_only` signals that no close absolute analog was found. Mock responses include `data_status=mock` and a disclaimer at the top level. Legacy `POST /api/rank` and `GET /api/targets` remain available; the former is deprecated and retains its original 0–1 scoring behavior.

## Frontend changes required

The frontend owner should call `/api/v1/targets` and read its `targets` array, use `region_id` (plus scale) as the target key, and call `/api/v1/rank` or `/api/v1/sites`. Display `score_geo` directly as a percentage without multiplying by 100; label `score_relative` as closest available Earth match rather than absolute similarity. Show `match_level`, `floored_criteria`, criterion values/similarities, and the mock disclaimer. Use `/api/v1/heat` for map points. The current placeholder frontend uses legacy `/api/rank` and 0–1 scores and can continue unchanged until its owner migrates it.

For a candidate card, call `GET /api/v1/compare?target_id=T-04&candidate_id=earth_grid_r258_c422&scale=regional&preset=balanced`. Use `per_criterion[*].s_i` and `per_criterion[*].z` to draw the criterion chart, and show `score_ci_low/high`, `place`, `analogy_breaks`, and `not_compared` beside the score. A condensed response looks like:

```json
{
  "target_id": "mars_phoenix_regional",
  "candidate_id": "earth_grid_r258_c422",
  "scale": "regional",
  "preset": "balanced",
  "score_geo": 99.4,
  "score_ci_low": 97.0,
  "score_ci_high": 99.6,
  "score_relative": 100.0,
  "distance_z": 0.057,
  "match_level": "absolute_strong",
  "place": {"name": "Umraniye", "admin1": "Afyonkarahisar", "country_code": "TR", "distance_km": 8.4},
  "per_criterion": {"slope_p90_deg": {"s_i": 0.99, "z": 0.1}},
  "z_by_feature": {"slope_p90_deg": 0.1},
  "target": {"region_id": "mars_phoenix_regional", "features": {}},
  "candidate": {"region_id": "earth_grid_r258_c422", "features": {}},
  "explanation": {"summary": "Score and limitations are supplied here."},
  "analogy_breaks": [],
  "not_compared": [],
  "data_status": "real",
  "disclaimer": null
}
```

The example is abbreviated; `target.features`, `candidate.features`, `per_criterion`, and `explanation` contain the complete objects in a live response. A missing candidate returns 404; invalid scale or preset returns 422. The report index is `engine/report/INDEX.md`.
