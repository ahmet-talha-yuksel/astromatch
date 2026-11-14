# Known issues

## HIGH

- Docker CLI/Compose and Docker Desktop daemon are unavailable in the current environment. Compose startup, container health, logs, and HTTP checks are not tested.
- Node.js/npm are unavailable. Frontend and Terrain3D dependency installation, TypeScript compilation, and production builds are not tested.
- FastAPI, pydantic-settings, and pytest are not installed in the active Python environment. Backend route execution and automated tests are not tested.

## MEDIUM

- Scientific datasets, reprojection, calibration, global candidate search, and production map UX are not implemented.
- License selection remains a team decision; no license file is invented.

## LOW

- Frontend remains a small integration scaffold and terrain3d is an independent demo.

## Verification commands for Windows

From the repository root, after installing Docker Desktop and Node.js:

```powershell
docker compose config
docker compose up --build -d
docker compose ps
docker compose logs --tail=100
curl.exe -f http://localhost:8000/health
curl.exe -f http://localhost:8000/openapi.json
curl.exe -f http://localhost:5173/
docker compose --profile terrain3d up --build -d
curl.exe -f http://localhost:5174/
```

For Python checks in a virtual environment:

```powershell
python -m pip install -r backend/requirements.txt
python -m pytest validation
python -c "from backend.app.main import app; print([r.path for r in app.routes])"
```
