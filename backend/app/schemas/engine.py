from __future__ import annotations
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

class CandidateScore(BaseModel):
    model_config=ConfigDict(extra='allow')
    id: str
    score_geo: float = Field(description='Absolute geometric similarity, 0–100')
    score_arith: float = Field(description='Arithmetic similarity, 0–100')
    score_relative: float = Field(description='Relative score: best eligible Earth record is 100')
    score_percentile: float
    match_level: str
    data_status: str | None = None
    disclaimer: str | None = None

class RankResponse(BaseModel):
    target_id: str
    scale: str
    preset: str
    top_k: list[CandidateScore]
    full_scores: list[CandidateScore]
    excluded: list[dict[str, Any]]
    novel_candidates: list[CandidateScore]
    sigma: dict[str, dict[str, float | str]]
    data_status: str
    disclaimer: str | None = None

class Envelope(BaseModel):
    data_status: str
    disclaimer: str | None = None
    model_config=ConfigDict(extra='allow')
