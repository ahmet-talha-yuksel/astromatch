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
    method: str | None = None
    features_interpolated: dict[str, float | None] = Field(default_factory=dict)
    measurement_support: dict = Field(default_factory=dict)
    method_sensitive: bool = False

class Dataset(BaseModel):
    targets: list[Region] = Field(default_factory=list)
    candidates: list[Region] = Field(default_factory=list)
    known_analogs: list[Region] = Field(default_factory=list)
    defaults_applied: list[str] = Field(default_factory=list)
    invalid_records: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    input_hashes: dict[str, str] = Field(default_factory=dict)
    mode: str = 'real'
    input_source: str | None = None

class DataPaths(BaseModel):
    features: str | list[str] | None = None
    grid: str | None = None
    known: str | None = None

class TargetSummary(BaseModel):
    region_id: str
    name: str
    body: str
    scales: list[str]
    alias: str | None = None
    status: str = 'scorable'
    reason: str | None = None
    target_confidence: str | None = None
    measurement_support: dict | None = None
    method_sensitive: bool | None = None

class Explanation(BaseModel):
    strongest: list[dict] = Field(default_factory=list)
    weakest: list[dict] = Field(default_factory=list)
    summary: str = ''
    not_compared: list[dict] = Field(default_factory=list)
    analogy_breaks: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    target_method: str | None = None
    measurement_support: dict | None = None
    target_confidence: str | None = None
    method_sensitive: bool = False
    methodology_note: str | None = None
    discrimination_label: str | None = None
    comparison_scope: str = 'Topographic similarity only (slope, roughness, relief). Not compared: temperature, ice/volatiles, mineralogy, atmosphere.'

class HeatPoint(BaseModel):
    id: str
    lat: float
    lon: float
    score: float | None
    status: str | None = None
    distance_z: float | None = None
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
    sigma: dict[str, dict[str, int | float | str]]
    data_status: str
    disclaimer: str | None = None
    target_confidence: str | None = None
    method_sensitive: bool = False
    target_status: str = 'scorable'
    target_reason: str | None = None
    discrimination_label: str | None = None
    discrimination_explanation: str | None = None
    comparison_scope: str = 'Topographic similarity only (slope, roughness, relief). Not compared: temperature, ice/volatiles, mineralogy, atmosphere.'
