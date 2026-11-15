from __future__ import annotations
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

class CandidateScore(BaseModel):
    model_config=ConfigDict(extra='allow')
    id: str
    score_geo: float = Field(description='Absolute geometric similarity, 0–100')
    score_contextual: float | None = Field(default=None, description='Terrain score discounted by commonality in the scanned grid, 0–100')
    score_contextual_ci_low: float | None = None
    score_contextual_ci_high: float | None = None
    score_arith: float = Field(description='Arithmetic similarity, 0–100')
    score_relative: float = Field(description='Relative score: best eligible Earth record is 100')
    score_percentile: float
    score_percentile_scanned: float | None = None
    top_tier: bool | None = None
    top_tier_size: int | None = None
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
    excluded_features: list[str] = Field(default_factory=list)
    sigma_calibration: dict[str, Any] | None = None
    top_tier_size: int = 0

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
    excluded_features: list[str] = Field(default_factory=list)
    sigma_calibration: dict[str, Any] | None = None
    top_tier_size: int = 0

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

class CompareResponse(Envelope):
    target_id: str
    candidate_id: str
    scale: str
    preset: str
    target: dict[str,Any]
    candidate: dict[str,Any]
    per_criterion: dict[str,Any]
    z_by_feature: dict[str,float]
    distance_z: float
    score_geo: float
    score_contextual: float | None = None
    score_contextual_ci_low: float | None = None
    score_contextual_ci_high: float | None = None
    score_ci_low: float | None = None
    score_ci_high: float | None = None
    score_relative: float
    match_level: str
    score_percentile_scanned: float | None = None
    top_tier: bool | None = None
    top_tier_size: int | None = None
    place: dict[str,Any] | None = None
    explanation: dict[str,Any]
    analogy_breaks: list[str]
    not_compared: list[dict[str,Any]]

class ValidationResponse(Envelope):
    report: dict[str,Any]
