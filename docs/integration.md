# Module boundaries

Processing provides v2.3 target and Earth feature records. The engine adapts and scores them. The backend initializes one Dataset during FastAPI startup and exposes `/api/v1` endpoints. Current checked-in records are synthetic; auto mode uses generated mock data until valid real features arrive. The terrain3d component remains separate.

## API

- `GET /api/v1/health`: active mode, data status, engine version, dataset counts, optional ML availability.
- `GET /api/v1/targets`, `GET /api/v1/presets`: target summaries and feature labels/units.
- `GET /api/v1/rank` and `POST /api/v1/rank`: ranked candidates; POST accepts custom weights.
- `GET /api/v1/sites`: all local Earth sites with criterion details for cards, without top-k cut or NMS.
- `GET /api/v1/heat`: precomputed heat points when available, computed otherwise.
- `GET /api/v1/regions/{region_id}`: raw record and scores against matching-scale targets.
- `GET /api/v1/explain`: deterministic explanation for one candidate.
- `GET /api/v1/validation`: validation report when available.

New API `score_geo`, `score_arith`, and `score_relative` use **0–100**. `score_geo` is the absolute primary score; relative score means closest available Earth record equals 100. `match_level=relative_only` signals that no close absolute analog was found. Mock responses include `data_status=mock` and a disclaimer at the top level. Legacy `POST /api/rank` and `GET /api/targets` remain available; the former is deprecated and retains its original 0–1 scoring behavior.

## Frontend changes required

The frontend owner should call `/api/v1/targets` and read its `targets` array, use `region_id` (plus scale) as the target key, and call `/api/v1/rank` or `/api/v1/sites`. Display `score_geo` directly as a percentage without multiplying by 100; label `score_relative` as closest available Earth match rather than absolute similarity. Show `match_level`, `floored_criteria`, criterion values/similarities, and the mock disclaimer. Use `/api/v1/heat` for map points. The current placeholder frontend uses legacy `/api/rank` and 0–1 scores and can continue unchanged until its owner migrates it.
