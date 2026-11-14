from __future__ import annotations
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from engine.similarity import rank_candidates
from backend.app.api.router import router
from backend.app.core.config import settings
from backend.app.services.data import load_json

app = FastAPI(title="AstroMatch AI API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)

class RankRequest(BaseModel):
    target_id: str = "mars_jezero"
    weights: dict[str, float] = Field(default_factory=lambda: {"slope_deg": 1, "tri_m": 1, "relief_m": 1})

@app.post("/api/rank")
def rank(request: RankRequest):
    target = next((x for x in load_json("targets.json") if x["id"] == request.target_id), None)
    if target is None:
        raise HTTPException(404, "Target not found")
    try:
        return {"target": target, "ranked": rank_candidates(target, load_json("candidates.json"), request.weights)}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
