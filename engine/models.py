from __future__ import annotations
from pydantic import BaseModel, Field

class Feature(BaseModel):
    value: float | None = None
    data_status: str = 'mock'
    comparable: bool = False
    comparability_note: str | None = None

class Region(BaseModel):
    region_id: str
    kind: str
    body: str
    name: str
    lat: float | None = None
    lon: float | None = None
    scale: str = 'local'
    window_km: float | None = None
    analysis_resolution_m: float | None = None
    source_resolution_m: float | None = None
    resolution_validated: bool = False
    dem_source: str | None = None
    dem_version: str | None = None
    features: dict[str, Feature] = Field(default_factory=dict)
    earth_filters: dict[str, float | None] = Field(default_factory=dict)
    quality: dict = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    processing_version: str | None = None
    data_status: str = 'mock'

class Dataset(BaseModel):
    targets: list[Region] = Field(default_factory=list)
    candidates: list[Region] = Field(default_factory=list)
    known_analogs: list[Region] = Field(default_factory=list)
    defaults_applied: list[str] = Field(default_factory=list)
    invalid_records: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    input_hashes: dict[str, str] = Field(default_factory=dict)
    mode: str = 'real'

class DataPaths(BaseModel):
    features: str | None = None
    grid: str | None = None
    known: str | None = None

class TargetSummary(BaseModel):
    region_id: str
    name: str
    body: str
    scales: list[str]

class Explanation(BaseModel):
    strongest: list[dict] = Field(default_factory=list)
    weakest: list[dict] = Field(default_factory=list)
    summary: str = ''
    not_compared: list[dict] = Field(default_factory=list)
    analogy_breaks: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)

class HeatPoint(BaseModel):
    id: str
    lat: float
    lon: float
    score: float
    data_status: str | None = None
    disclaimer: str | None = None

class RankResult(BaseModel):
    target_id: str
    scale: str
    preset: str
    top_k: list[dict]
    full_scores: list[dict]
    excluded: list[dict]
    novel_candidates: list[dict]
    sigma: dict[str, dict[str, float | str]]
    data_status: str
    disclaimer: str | None = None
