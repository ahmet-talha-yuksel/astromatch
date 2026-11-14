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
    sigma: dict[str, dict[str, int | float | str]]
    data_status: str
    disclaimer: str | None = None
    target_confidence: str | None = None
    target_status: str = 'scorable'
    target_reason: str | None = None
    method_sensitive: bool = False
    discrimination_label: str | None = None
    discrimination_explanation: str | None = None
    terrain_commonality: dict[str, Any] | None = None

class Envelope(BaseModel):
    data_status: str
    disclaimer: str | None = None
    model_config=ConfigDict(extra='allow')

class HealthResponse(Envelope):
    status: str
    data_mode: str
    engine_version: str
    dataset_counts: dict[str,int]
    sklearn_available: bool
    hdbscan_available: bool

class TargetsResponse(Envelope):
    targets: list[dict[str,Any]]

class PresetsResponse(Envelope):
    presets: dict[str,dict[str,float]]
    features: dict[str,dict[str,str]]

class SitesResponse(Envelope):
    target_id: str
    scale: str
    preset: str
    sites: list[CandidateScore]
    excluded: list[dict[str,Any]]
    target_confidence: str | None = None
    target_status: str = 'scorable'
    target_reason: str | None = None
    discrimination_label: str | None = None
    discrimination_explanation: str | None = None
    terrain_commonality: dict[str, Any] | None = None

class HeatResponse(Envelope):
    target_id: str
    scale: str
    preset: str
    source: str
    points: list[dict[str,Any]]

class RegionResponse(Envelope):
    region: dict[str,Any]
    records: list[dict[str,Any]]
    scores: list[dict[str,Any]]

class ExplainResponse(Envelope):
    target_id: str
    candidate_id: str
    scale: str
    preset: str
    explanation: dict[str,Any]

class ValidationResponse(Envelope):
    report: dict[str,Any]
