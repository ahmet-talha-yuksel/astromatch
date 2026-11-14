# Docker verification

Compose defines backend, frontend, and an optional terrain3d profile. Development mounts preserve container `node_modules`; Vite and Uvicorn bind to `0.0.0.0`. The backend uses only checked-in synthetic fixtures at startup and does not download NASA data. Docker verification is pending when Docker Desktop is available in the execution environment.
