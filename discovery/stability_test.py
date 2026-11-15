"""Measure ranking stability under noise on the six scoring features."""

from __future__ import annotations

import argparse
import importlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .analysis_utils import (
    SCORING_FEATURES, load_grid, non_overwriting_path, safe_json_value,
    scope_block, timestamp_iso,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_GRID = ROOT / "data" / "inputs" / "earth_grid.parquet"
DEFAULT_OUT = ROOT / "out" / "stability"
NOISE_LEVELS = (0.01, 0.05, 0.10)
NONNEGATIVE_FEATURES = {
    "slope_median_deg", "slope_p90_deg", "tri_median_m", "relief_m", "elevation_std_m"
}


def load_ranker(spec: str, engine_path: Path | None):
    if engine_path is not None:
        resolved = engine_path.resolve()
        if not resolved.is_dir():
            raise FileNotFoundError(f"--engine-path is not a directory: {resolved}")
        sys.path.insert(0, str(resolved))
    try:
        module_name, function_name = spec.split(":", 1)
        function = getattr(importlib.import_module(module_name), function_name)
    except (ValueError, ImportError, AttributeError) as exc:
        raise RuntimeError(
            f"Cannot load ranker {spec!r}. Provide --engine-path pointing to the external engine directory."
        ) from exc
    if not callable(function):
        raise TypeError(f"Ranker is not callable: {spec}")
    return function


def call_ranker(ranker, grid_df: pd.DataFrame, target_id: str, weights: dict | None, sigma: Any):
    result = ranker(
        grid_df, target_id, weights=weights, sigma=sigma, return_criteria=False
    )
    if not isinstance(result, pd.DataFrame):
        raise TypeError("score_grid must return a pandas DataFrame")
    missing = {"cell_id", "score"}.difference(result.columns)
    if missing:
        raise ValueError(f"score_grid output is missing columns: {sorted(missing)}")
    output = result[["cell_id", "score"]].copy()
    output["cell_id"] = output.cell_id.astype(str)
    output["score"] = pd.to_numeric(output.score, errors="coerce")
    output = output.dropna(subset=["score"]).drop_duplicates("cell_id", keep="first")
    sigma_used = result.attrs.get("sigma")
    return output.set_index("cell_id").score, sigma_used


def top_keys(scores: pd.Series, count: int = 5) -> list[str]:
    valid = scores.dropna().sort_values(ascending=False, kind="mergesort")
    return [str(k) for k in valid.index[:count]]


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def noisy_grid(grid: pd.DataFrame, level: float, seed: int) -> pd.DataFrame:
    result = grid.copy(deep=True)
    comparable = pd.Series(True, index=result.index)
    for feature in SCORING_FEATURES:
        flag = f"{feature}__comparable"
        if flag in result:
            comparable &= result[flag].fillna(False).astype(bool)
        comparable &= pd.to_numeric(result[feature], errors="coerce").notna()
    rng = np.random.default_rng(seed)
    for feature in SCORING_FEATURES:
        values = pd.to_numeric(result[feature], errors="coerce")
        valid_values = values.loc[comparable]
        std = float(valid_values.std(ddof=0)) if len(valid_values) else 0.0
        noise = rng.normal(0.0, std * level, size=len(result))
        perturbed = values.to_numpy(dtype=float, na_value=np.nan) + noise
        if feature == "flat_fraction":
            perturbed = np.clip(perturbed, 0.0, 1.0)
        elif feature in NONNEGATIVE_FEATURES:
            finite = np.isfinite(perturbed)
            perturbed[finite] = np.maximum(perturbed[finite], 0.0)
        result[feature] = perturbed
    return result


def summarize_mode(
    grid: pd.DataFrame, ranker, target_id: str, weights: dict | None,
    sigma_mode: str, n_runs: int, seed: int,
) -> dict[str, Any]:
    sigma_arg = "frozen" if sigma_mode == "frozen" else None
    baseline, baseline_sigma = call_ranker(ranker, grid.copy(deep=True), target_id, weights, sigma_arg)
    if baseline.empty:
        raise ValueError(f"Ranker returned no finite scores for target {target_id}")
    baseline_top = set(top_keys(baseline))
    baseline_winner = top_keys(baseline, 1)[0]
    levels: dict[str, Any] = {}
    for level in NOISE_LEVELS:
        jaccards: list[float] = []
        winner_retained = 0
        correlations: list[float] = []
        sigma_values: list[Any] = []
        for run_index in range(n_runs):
            perturbed = noisy_grid(grid, level, seed + run_index)
            scores, sigma_used = call_ranker(ranker, perturbed, target_id, weights, sigma_arg)
            sigma_values.append(safe_json_value(sigma_used))
            jaccards.append(jaccard(baseline_top, set(top_keys(scores))))
            if top_keys(scores, 1) and top_keys(scores, 1)[0] == baseline_winner:
                winner_retained += 1
            common = baseline.index.intersection(scores.index)
            if len(common) >= 2:
                rho = spearmanr(baseline.loc[common], scores.loc[common]).statistic
                if math.isfinite(float(rho)):
                    correlations.append(float(rho))
        levels[f"{level:.0%}"] = {
            "noise_fraction_of_feature_std": level,
            "top5_jaccard_mean": float(np.mean(jaccards)),
            "top5_jaccard_min": float(np.min(jaccards)),
            "first_place_retention_rate": winner_retained / n_runs,
            "spearman_mean": float(np.mean(correlations)) if correlations else None,
            "spearman_min": float(np.min(correlations)) if correlations else None,
            "spearman_runs": len(correlations),
            "runs": n_runs,
            "sigma_values_observed": sigma_values,
        }
    return {
        "target_id": target_id,
        "sigma_mode": sigma_mode,
        "sigma_baseline": safe_json_value(baseline_sigma),
        "baseline_cell_count": len(baseline),
        "baseline_top5_cell_ids": sorted(baseline_top),
        "baseline_first_cell_id": baseline_winner,
        "levels": levels,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", nargs="+", type=Path, default=[DEFAULT_GRID])
    parser.add_argument("--ranker", default="engine.validation_api:score_grid")
    parser.add_argument("--engine-path", type=Path)
    parser.add_argument("--target-id", default="T-02")
    parser.add_argument("--weights-json", type=Path)
    parser.add_argument("--sigma-mode", choices=("end_to_end", "frozen"), required=True)
    parser.add_argument("--n-runs", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    if args.n_runs < 1:
        parser.error("--n-runs must be positive")
    weights = json.loads(args.weights_json.read_text(encoding="utf-8")) if args.weights_json else None
    try:
        ranker = load_ranker(args.ranker, args.engine_path)
    except (RuntimeError, FileNotFoundError, TypeError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")
    grid = load_grid(args.grid)
    report = {
        "generated_at": timestamp_iso(),
        "scope": scope_block(grid),
        "scoring_features": list(SCORING_FEATURES),
        "noise_levels": [0.01, 0.05, 0.10],
        "seed": args.seed,
        "runs_per_level": args.n_runs,
        "sigma_modes": {
            args.sigma_mode: summarize_mode(
                grid, ranker, args.target_id, weights, args.sigma_mode, args.n_runs, args.seed
            )
        },
    }
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    output = non_overwriting_path(out_dir / "stability_results.json")
    output.write_text(json.dumps(safe_json_value(report), ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
