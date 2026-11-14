# AstroMatch AI — NASA Space Apps 2026 (starter repository)

**Development scaffold, not a completed scientific implementation.**
Frontend is a temporary minimal API viewer; production frontend is developed separately.
All initial feature values are **synthetic demo fixtures**, not NASA measurements.

## Run with Docker Compose

Prerequisites: Docker Engine/Desktop with Compose v2.

```bash
docker compose up --build
```

- Frontend scaffold: http://localhost:5173
- API documentation: http://localhost:8000/docs
- Health: http://localhost:8000/health

Standalone 3D demo (separate optional Compose profile):

```bash
docker compose --profile terrain3d up --build
```

- 3D demo: http://localhost:5174

Stop: `docker compose down`.

## Without Docker

Python 3.12+ and Node.js 20.19+ recommended.

```bash
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

In another terminal:

```bash
cd frontend && npm install && npm run dev
```

Standalone 3D: `cd terrain3d && npm install && npm run dev`.

## Tests

```bash
python -m pytest validation/test_similarity.py
```

## Project layout

- `backend/`: FastAPI endpoints
- `processing/`: NASA DEM ETL ownership
- `engine/`: Gaussian similarity and weighted geometric scoring
- `discovery/`: global candidate discovery ownership
- `data/`: processed JSON fixtures, raw DEMs excluded from Git
- `terrain3d/`: standalone React Three Fiber terrain viewer + GeoTIFF converter
- `frontend/`: placeholder React app, not the final frontend
- `shared/`: schema contracts
- `validation/`: tests
- `docs/`: limitations and integration notes

## Scientific and engineering caveats

- Real MOLA, LOLA, SRTM/Copernicus datasets are not bundled.
- Global 0.5° scan, validated Earth candidates, calibration and offline map tiles are not implemented.
- DEM converter requires metric projected raster; reproject and harmonize upstream.
- Terrain viewer is a reusable component; import into the main frontend when ready.
- Docker configuration is provided but must be built on a machine with Docker.
