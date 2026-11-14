# Docker deployment

`docker compose up --build` starts the backend and frontend. The backend selects `ASTROMATCH_DATA_MODE=auto` by default: it loads validated real v2.3 records from `processing/out/features.json` when available, otherwise generated mock data. `/api/v1/health` reports the active mode and record counts. All mock API responses carry `MOCK DATA — NOT A SCIENTIFIC RESULT`.

Set `ASTROMATCH_DATA_MODE=mock` to force a demo, or `ASTROMATCH_DATA_MODE=real` to require real validated records and fail startup if they are unavailable. Set `ASTROMATCH_PRECOMPUTE=1` to populate an empty results volume before starting Uvicorn. `docker compose --profile precompute run --rm precompute` runs all presets and validation once. Results live in the named `engine_results` volume.

Environment variables: `ASTROMATCH_FEATURES`, `ASTROMATCH_GRID`, `ASTROMATCH_KNOWN` select inputs; `ASTROMATCH_RESULTS_DIR` selects output; `ASTROMATCH_WORKERS` defaults to 1; `CORS_ORIGINS` defaults to `http://localhost:5173,http://localhost:5174`. Compose mounts `processing/out` and `discovery/out` read-only. Optional `.env` is loaded when present. `docker compose --profile terrain3d up --build` still starts the separate 3D demo.

The image builds Python 3.11 wheels in a builder stage, then installs them into a slim runtime. It runs as a non-root user, excludes generated data and raw rasters from the build context, and probes `/api/v1/health` without curl. The frontend waits for backend health before starting.
