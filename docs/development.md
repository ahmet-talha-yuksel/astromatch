# Development

Copy `.env.example` to `.env`, then run `docker compose up --build`. Backend docs are at `/docs`, health at `/health`, frontend at `:5173`, and the optional terrain viewer at `docker compose --profile terrain3d up --build` on `:5174`. Without Docker, install backend requirements and run Uvicorn; install each Node workspace separately and use `npm run dev`.
