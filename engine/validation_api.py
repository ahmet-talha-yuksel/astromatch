"""Row-preserving validation scores using the engine's configured criteria."""
from __future__ import annotations

import json
import math
import warnings
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from .adapters import adapt
from .aggregate import aggregate_matrix
from .io import ROOT, config
from .sigma import sigma_metadata
from .similarity import criterion_similarity


def list_target_ids() -> dict[str, str | None]:
    """Return the configured aliases, including an unassigned T-04."""
    return dict(config("target_aliases.yaml"))


def _records(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return data
    for key in ("records", "regions"):
        if key in data and isinstance(data[key], list):
            return data[key]
    raise ValueError(f"{path}: expected a list or records/regions wrapper")


@lru_cache(maxsize=1)
def _default_targets() -> tuple[list[dict], str]:
    path = ROOT / "processing/out/real/features.json"
    if path.exists():
        return [r for r in _records(path) if r.get("kind") == "target"], "real"
    from .mock import generate
    return generate(n_grid=0)[0], "mock"


@lru_cache(maxsize=2)
def _default_reference(scale: str) -> pd.DataFrame:
    path = ROOT / "processing/out/earth_grid.parquet"
    if not path.exists():
        path = ROOT / "processing/out/real/earth_grid.parquet"
    if path.exists():
        return pd.read_parquet(path)
    from .mock import generate
    _, candidates, _ = generate(n_grid=5000)
    return pd.DataFrame({key: [r["features"][key]["value"] for r in candidates
                               if r["kind"] == "earth_grid"]
                         for key in config("features.yaml")["features"]})


def _target(rows: list[dict], target_id: str, scale: str):
    aliases = list_target_ids()
    base = aliases.get(target_id, target_id)
    if base is None:
        return None
    accepted = {base, f"{base}_{scale}", target_id}
    return next((adapt(r, configured=set(config("features.yaml")["features"]))
                 for r in rows if r.get("scale") == scale and
                 r.get("region_id") in accepted), None)


def _weights(weights, features):
    presets = config("presets.yaml")
    if weights is None:
        modifiers = presets["balanced"]
    elif isinstance(weights, str):
        if weights not in presets:
            raise ValueError(f"Unknown preset: {weights}")
        modifiers = presets[weights]
    elif isinstance(weights, dict):
        unknown = set(weights) - set(features)
        if unknown:
            raise ValueError(f"Unknown weight keys: {sorted(unknown)}")
        modifiers = weights
    else:
        raise TypeError("weights must be a preset, dict, or None")
    result = np.array([float(features[k].get("weight", 1)) *
                       float(modifiers.get(k, 1)) for k in features])
    if not np.isfinite(result).all() or (result < 0).any() or result.sum() <= 0:
        raise ValueError("Weights must be finite, nonnegative, and have a positive sum")
    return result


def _sigma_table(grid: pd.DataFrame, scale: str, sigma, features):
    if isinstance(sigma, dict):
        if set(sigma) != set(features):
            raise ValueError("Explicit sigma must contain every configured feature")
        table = {}
        for key, value in sigma.items():
            value = float(value)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"Invalid sigma for {key}")
            table[key] = {"value": value, "sigma_source": "explicit", "n_samples": 0}
        return table
    if sigma not in (None, "frozen"):
        raise ValueError("sigma must be None, 'frozen', or a complete dict")
    if sigma == "frozen":
        return {key: dict(value) for key, value in _frozen_sigma(scale).items()}
    source = grid
    same_mask = source["scale"].eq(scale).to_numpy() if "scale" in source else np.ones(len(source), bool)
    regional_mask = source["scale"].eq("regional").to_numpy() if "scale" in source else same_mask
    table = {}
    for key, cfg in features.items():
        column = pd.to_numeric(source[key], errors="coerce").to_numpy(dtype=float) if key in source else np.full(len(source), np.nan)
        table[key] = sigma_metadata(column[same_mask], key, scale, cfg,
                                    column[regional_mask],
                                    config("features.yaml").get("min_sigma_samples", 200))
    return table


@lru_cache(maxsize=2)
def _frozen_sigma(scale: str):
    return _sigma_table(_default_reference(scale), scale, None,
                        config("features.yaml")["features"])


def _score_grid(grid_df: pd.DataFrame, target_id: str, weights=None, *, sigma=None,
                scale="regional", return_criteria=False, target_records=None) -> pd.DataFrame:
    if not isinstance(grid_df, pd.DataFrame):
        raise TypeError("grid_df must be a pandas DataFrame")
    features = config("features.yaml")["features"]
    keys = list(features)
    weights_array = _weights(weights, features)
    n = len(grid_df)
    ids = grid_df["cell_id"].to_numpy(copy=True) if "cell_id" in grid_df else grid_df["region_id"].to_numpy(copy=True)
    target = _target(target_records if target_records is not None else _default_targets()[0], target_id, scale)
    table = _sigma_table(grid_df, scale, sigma, features)
    scores = np.full((n, len(keys)), np.nan)
    eligible = np.zeros((n, len(keys)), dtype=bool)
    resolution = grid_df["resolution_validated"].fillna(False).astype(bool).to_numpy() if "resolution_validated" in grid_df else np.zeros(n, bool)
    matching = grid_df["scale"].eq(scale).to_numpy() if "scale" in grid_df else np.ones(n, bool)
    reason = None
    if target is None:
        reason = "target_unscorable: target or scale not found"
    elif not target.resolution_validated:
        reason = "target_unscorable: resolution not validated"
    elif sum(f.value is not None and f.comparable and weights_array[j] > 0
             for j, key in enumerate(keys) if (f := target.features.get(key)) is not None) < config("features.yaml").get("min_features", 3):
        reason = "target_unscorable: fewer than min_features eligible"
    if reason:
        warnings.warn(f"{target_id}: {reason}", stacklevel=2)
    if reason is None:
        for j, key in enumerate(keys):
            tf = target.features.get(key)
            if tf is None or tf.value is None or not tf.comparable or key not in grid_df:
                continue
            value = pd.to_numeric(grid_df[key], errors="coerce").to_numpy(dtype=float)
            comparable_col = key + "__comparable"
            comparable = grid_df[comparable_col].fillna(False).astype(bool).to_numpy() if comparable_col in grid_df else resolution
            mask = np.isfinite(value) & comparable & resolution & matching
            eligible[:, j] = mask
            if features[key]["method"] == "gaussian":
                scores[mask, j] = np.exp(-.5 * ((value[mask] - tf.value) / table[key]["value"]) ** 2)
            else:
                scores[mask, j] = [criterion_similarity(v, tf.value, features[key], table[key]["value"]) for v in value[mask]]
    geo, _, _, valid, _ = aggregate_matrix(scores, eligible, weights_array,
                                            config("features.yaml").get("min_features", 3))
    count = (eligible & (weights_array > 0)).sum(axis=1)
    excluded = np.where(valid, None, "fewer than min_features eligible").astype(object)
    excluded[~matching] = "scale mismatch"
    if reason:
        excluded[:] = reason
    out = pd.DataFrame({"cell_id": ids, "score": geo / 100,
                        "n_features": count, "excluded_reason": excluded})
    if return_criteria:
        for j, key in enumerate(keys):
            out["s_" + key] = scores[:, j]
    out.attrs["sigma"] = {key: value["value"] for key, value in table.items()}
    out.attrs["sigma_source"] = {key: value["sigma_source"] for key, value in table.items()}
    out.attrs["sigma_table"] = table
    return out


def score_grid(grid_df: pd.DataFrame, target_id: str, weights=None, *, sigma=None,
               scale="regional", return_criteria=False) -> pd.DataFrame:
    """Score every input row, returning NaN for ineligible cells."""
    return _score_grid(grid_df, target_id, weights, sigma=sigma, scale=scale,
                       return_criteria=return_criteria)
