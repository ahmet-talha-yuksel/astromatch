"""Validate score ordering against USGS known analog cells."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from .analysis_utils import (
    TARGET_ENGINE_IDS, TARGET_IDS, UNSCORABLE_TARGETS, load_grid, non_overwriting_path,
    rank_percentiles, safe_json_value, scope_block, scores_by_key, timestamp_iso,
)
from .analog_mapping import cell_id
from .coverage_check import coverage_center
from .grid_utils import neighbor_keys
from .score_io import load_scores


ROOT = Path(__file__).resolve().parent
DEFAULT_GRID = ROOT / "data" / "inputs" / "earth_grid.parquet"
DEFAULT_ANALOGS = ROOT / "out" / "known_analogs.json"
DEFAULT_COVERAGE = ROOT / "data" / "inputs" / "coverage.geojson"
DEFAULT_OUT = ROOT / "out" / "validation"
SCORING_FEATURES = (
    "slope_median_deg", "slope_p90_deg", "flat_fraction", "tri_median_m",
    "relief_m", "elevation_std_m",
)

CAVEATS = [
    "190/192 USGS records are impact crater records.",
    "Most positive cells correspond to crater records; their 50x50 km windows are crater-centered, so relief and roughness partly measure crater morphology and AUC can confound analog quality with crater-like terrain discrimination.",
    "Results for target T-02 (Shackleton, Moon) do not apply to Mars targets.",
    "analog_for is empty for 191 records, so all scored targets use the same positive cell set.",
    "The negative set is unlabeled background, not confirmed non-analogs; AUC measures ranking of known analogs against background, not classification accuracy.",
    "Atacama and the supplied Turkish sites are absent from the USGS known-analogs list.",
    "This validation is not evidence for volcanic or carbonate analogs.",
]


def auc_value(positive: np.ndarray, negative: np.ndarray) -> float:
    """Mann-Whitney AUC with average ranks for tied scores."""
    positive = np.asarray(positive, dtype=float)
    negative = np.asarray(negative, dtype=float)
    if len(positive) == 0 or len(negative) == 0:
        return math.nan
    all_scores = np.concatenate([positive, negative])
    ranks = rankdata(all_scores, method="average")
    u = ranks[:len(positive)].sum() - len(positive) * (len(positive) + 1) / 2
    return float(u / (len(positive) * len(negative)))


def enrichment(scores: pd.Series, positive_keys: set[str], fraction: float) -> dict[str, float | int | None]:
    ordered = pd.DataFrame({"cell_key": scores.index.astype(str), "score": scores.to_numpy()})
    ordered = ordered.sort_values(["score", "cell_key"], ascending=[False, True], kind="mergesort")
    top_count = max(1, int(math.ceil(len(ordered) * fraction)))
    hits = int(ordered.head(top_count).cell_key.isin(positive_keys).sum())
    prevalence = len(positive_keys) / len(ordered) if len(ordered) else math.nan
    rate = hits / top_count if top_count else math.nan
    return {
        "top_cell_count": top_count,
        "positive_count_in_top": hits,
        "enrichment": float(rate / prevalence) if prevalence and math.isfinite(prevalence) else None,
    }


def descriptive_positives(scores: pd.Series, positive_keys: set[str], names: dict[str, list[str]]) -> list[dict[str, Any]]:
    percentiles = rank_percentiles(scores)
    return [
        {
            "cell_key": key,
            "analog_names": "; ".join(names.get(key, [])),
            "score": float(scores.loc[key]),
            "percentile": float(percentiles.loc[key]),
        }
        for key in sorted(positive_keys)
    ]


def evaluate_cohort(
    scores: pd.Series,
    positive_keys: set[str],
    background_keys: set[str],
    *, n_perm: int, n_boot: int, seed: int,
) -> dict[str, Any]:
    positive = scores.loc[sorted(positive_keys)].to_numpy(dtype=float)
    negative = scores.loc[sorted(background_keys)].to_numpy(dtype=float)
    observed = auc_value(positive, negative)
    rng = np.random.default_rng(seed)
    boot_auc = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        pos_sample = rng.choice(positive, size=len(positive), replace=True)
        neg_sample = rng.choice(negative, size=len(negative), replace=True)
        boot_auc[i] = auc_value(pos_sample, neg_sample)
    low, high = np.quantile(boot_auc, [0.025, 0.975])

    all_scores = np.concatenate([positive, negative])
    positive_n = len(positive)
    exceed = 0
    for _ in range(n_perm):
        permuted = rng.permutation(all_scores)
        if auc_value(permuted[:positive_n], permuted[positive_n:]) >= observed:
            exceed += 1

    percentiles = rank_percentiles(scores)
    prevalence = len(positive_keys) / len(scores)
    return {
        "positive_count": len(positive),
        "background_count": len(negative),
        "auc": observed,
        "auc_bootstrap_95_ci": [float(low), float(high)],
        "bootstrap_iterations": n_boot,
        "mean_positive_percentile": float(percentiles.loc[sorted(positive_keys)].mean()),
        "top_1_percent": enrichment(scores, positive_keys, 0.01),
        "top_5_percent": enrichment(scores, positive_keys, 0.05),
        "permutation_p_value": float((exceed + 1) / (n_perm + 1)),
        "permutation_iterations": n_perm,
        "positive_prevalence": float(prevalence),
    }


def load_analog_cells(path: Path) -> dict[str, list[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    records = data if isinstance(data, list) else data.get("records", [])
    grouped: dict[str, list[str]] = defaultdict(list)
    for record in records:
        key = cell_id(float(record["lat"]), float(record["lon"]))
        name = str(record.get("name") or "")
        if name and name not in grouped[key]:
            grouped[key].append(name)
    return dict(grouped)


def not_scanned_keys(path: Path) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    keys = set()
    for feature in data.get("features", []):
        props = feature.get("properties") or {}
        if props.get("status") == "not_scanned":
            lat, lon = coverage_center(feature)
            keys.add(cell_id(lat, lon))
    return keys


def analyze(
    grid: pd.DataFrame,
    score_frame: pd.DataFrame,
    analog_names: dict[str, list[str]],
    not_scanned: set[str],
    *, min_positives: int, n_perm: int, n_boot: int, seed: int,
) -> dict[str, Any]:
    keyed_scores = scores_by_key(score_frame, grid)
    grid_keys = set(grid.cell_key.astype(str))
    analog_keys = set(analog_names)
    excluded_analogs: dict[str, list[dict[str, str]]] = {
        "not_in_grid": [], "not_scanned": [], "score_nan": [], "land_fraction_below_0_5": []
    }
    target_results: dict[str, Any] = {}
    positive_summary = []

    for target_index, target_id in enumerate(TARGET_IDS):
        target_scores = keyed_scores.loc[keyed_scores.target_id.astype(str) == target_id]
        target_scores = target_scores.dropna(subset=["cell_key"])
        criterion_columns = [c for c in target_scores.columns if str(c).startswith("s_")]
        used_features = [c[2:] for c in criterion_columns if pd.to_numeric(target_scores[c], errors="coerce").notna().any()]
        excluded_features = [c for c in SCORING_FEATURES if c not in used_features]
        score_map = target_scores.drop_duplicates("cell_key", keep="first").set_index("cell_key")["score"]
        joined = grid.set_index("cell_key").join(score_map.rename("score"), how="left")
        score_valid = joined.score.notna()
        if "land_fraction" in joined:
            land = pd.to_numeric(joined.land_fraction, errors="coerce")
            land_valid = land.ge(0.5)
        else:
            land_valid = pd.Series(True, index=joined.index)
        valid_scores = joined.loc[score_valid & land_valid, "score"].astype(float)
        valid_keys = set(valid_scores.index.astype(str))
        positives = analog_keys & valid_keys
        background = valid_keys - analog_keys
        base_rate = len(positives) / len(valid_keys) if valid_keys else None
        positive_summary.append({
            "target_id": target_id,
            "engine_region_id": TARGET_ENGINE_IDS[target_id],
            "used_feature_count": len(used_features),
            "used_features": used_features,
            "excluded_features": excluded_features,
            "valid_positive_cell_count": len(positives),
            "valid_cell_count": len(valid_keys),
            "base_rate": base_rate,
        })

        if target_id == "T-02":
            for key in sorted(analog_keys):
                names = "; ".join(analog_names[key])
                if key not in grid_keys:
                    reason = "not_scanned" if key in not_scanned else "not_in_grid"
                elif key in score_map.index and pd.isna(score_map.loc[key]):
                    reason = "score_nan"
                elif key in joined.index and "land_fraction" in joined and not bool(land_valid.loc[key]):
                    reason = "land_fraction_below_0_5"
                elif key not in valid_keys:
                    reason = "score_nan"
                else:
                    continue
                excluded_analogs[reason].append({"cell_key": key, "analog_names": names})

        # The engine's evidence gates can make a formerly unscorable target
        # scoreable when current scores are supplied. Keep the static reason
        # only when this score file contains no finite cells for that target.
        if target_id in UNSCORABLE_TARGETS and not len(valid_keys):
            target_results[target_id] = {
                "status": "unscorable",
                "reason": UNSCORABLE_TARGETS[target_id],
                "engine_region_id": TARGET_ENGINE_IDS[target_id],
                "used_feature_count": len(used_features),
                "used_features": used_features,
                "excluded_features": excluded_features,
                "score": None,
                "metrics": None,
            }
            continue

        result: dict[str, Any] = {
            "status": None,
            "engine_region_id": TARGET_ENGINE_IDS[target_id],
            "used_feature_count": len(used_features),
            "used_features": used_features,
            "excluded_features": excluded_features,
            "valid_cell_count": len(valid_keys),
            "valid_positive_cell_count": len(positives),
            "base_rate": base_rate,
            "positive_cells": [],
            "cohorts": {},
        }
        if len(positives) == 0:
            result.update(status="not_evaluable", reason="zero valid positive cells; no metrics calculated")
        elif len(positives) < min_positives:
            result.update(
                status="insufficient_positives",
                reason=f"{len(positives)} valid positives is below --min-positives={min_positives}",
                positive_cells=descriptive_positives(valid_scores, positives, analog_names),
            )
        else:
            neighbor_exclusions = set().union(*(set(neighbor_keys(key)) for key in positives))
            sensitivity_background = background - neighbor_exclusions
            if not len(background):
                result.update(status="not_evaluable", reason="no valid unlabeled background cells")
            else:
                result.update(status="evaluated")
                result["positive_cells"] = descriptive_positives(valid_scores, positives, analog_names)
                result["cohorts"] = {
                    "primary_unlabeled_background": evaluate_cohort(
                        valid_scores, positives, background,
                        n_perm=n_perm, n_boot=n_boot, seed=seed + target_index,
                    ),
                    "sensitivity_without_positive_neighbors": evaluate_cohort(
                        valid_scores, positives, sensitivity_background,
                        n_perm=n_perm, n_boot=n_boot, seed=seed + 100 + target_index,
                    ) if sensitivity_background else {
                        "status": "not_evaluable", "reason": "no background cells remain after removing positive neighbors",
                    },
                }
        target_results[target_id] = result

    controls = []
    control_points = [
        ("Meteor Crater", 35.03, -111.02),
        ("Haughton", 75.4, -89.7),
    ]
    t02 = target_results.get("T-02", {})
    t02_scores = keyed_scores.loc[keyed_scores.target_id.astype(str) == "T-02"].dropna(subset=["cell_key"])
    t02_map = t02_scores.drop_duplicates("cell_key", keep="first").set_index("cell_key")["score"]
    joined_t02 = grid.set_index("cell_key").join(t02_map.rename("score"), how="left")
    valid_t02 = joined_t02.score.notna()
    if "land_fraction" in joined_t02:
        valid_t02 &= pd.to_numeric(joined_t02.land_fraction, errors="coerce").ge(0.5)
    valid_t02_scores = joined_t02.loc[valid_t02, "score"]
    t02_percentiles = rank_percentiles(valid_t02_scores) if len(valid_t02_scores) else pd.Series(dtype=float)
    for name, lat, lon in control_points:
        key = cell_id(lat, lon)
        row = {"name": name, "cell_key": key, "status": "not_in_grid", "percentile": None}
        if key in grid_keys:
            if key in t02_map.index and pd.notna(t02_map.loc[key]):
                row["status"] = "scored"
                if key in t02_percentiles.index:
                    row["percentile"] = float(t02_percentiles.loc[key])
            else:
                row["status"] = "score_nan"
                row["reason"] = "cell is present in grid but has no finite T-02 score"
        else:
            row["reason"] = "cell_key is absent from the supplied processed grid"
        controls.append(row)

    excluded_report = {
        reason: {"count": len(cells), "cells": cells}
        for reason, cells in excluded_analogs.items()
    }
    return {
        "positive_counts_at_start": positive_summary,
        "scope": None,
        "targets": target_results,
        "analog_cells_excluded_from_valid_positive_set": excluded_report,
        "control_sites": controls,
        "caveats": CAVEATS,
    }


def output_bundle(out_dir: Path) -> tuple[Path, Path]:
    csv_path = out_dir / "validation_summary.csv"
    json_path = out_dir / "validation_results.json"
    if not csv_path.exists() and not json_path.exists():
        return json_path, csv_path
    stamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"validation_results_{stamp}.json"
    csv_path = out_dir / f"validation_summary_{stamp}.csv"
    suffix = 2
    while json_path.exists() or csv_path.exists():
        json_path = out_dir / f"validation_results_{stamp}_{suffix}.json"
        csv_path = out_dir / f"validation_summary_{stamp}_{suffix}.csv"
        suffix += 1
    return json_path, csv_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", nargs="+", type=Path, default=[DEFAULT_GRID])
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--analogs", type=Path, default=DEFAULT_ANALOGS)
    parser.add_argument("--coverage", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-perm", type=int, default=1000)
    parser.add_argument("--n-boot", type=int, default=1000)
    parser.add_argument("--min-positives", type=int, default=20)
    args = parser.parse_args()
    if args.n_perm < 1 or args.n_boot < 1 or args.min_positives < 1:
        parser.error("--n-perm, --n-boot, and --min-positives must be positive")

    grid = load_grid(args.grid)
    scores = load_scores(args.scores)
    analog_names = load_analog_cells(args.analogs)
    result = analyze(
        grid, scores, analog_names, not_scanned_keys(args.coverage),
        min_positives=args.min_positives, n_perm=args.n_perm, n_boot=args.n_boot, seed=args.seed,
    )
    result["scope"] = scope_block(grid)
    result["generated_at"] = timestamp_iso()
    result["parameters"] = {
        "seed": args.seed, "n_perm": args.n_perm, "n_boot": args.n_boot,
        "min_positives": args.min_positives,
    }

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path, csv_path = output_bundle(out_dir)
    if json_path.exists() or csv_path.exists():
        raise FileExistsError("Refusing to overwrite validation output files")
    json_path.write_text(json.dumps(safe_json_value(result), ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "target_id", "engine_region_id", "status", "used_feature_count", "used_features", "excluded_features",
            "valid_positive_cell_count", "valid_cell_count", "base_rate",
            "primary_auc", "primary_auc_ci_low", "primary_auc_ci_high",
            "sensitivity_auc", "sensitivity_auc_ci_low", "sensitivity_auc_ci_high", "reason", "scope",
        ])
        writer.writeheader()
        for target_id in TARGET_IDS:
            item = result["targets"][target_id]
            primary = item.get("cohorts", {}).get("primary_unlabeled_background", {})
            sensitivity = item.get("cohorts", {}).get("sensitivity_without_positive_neighbors", {})
            pci = primary.get("auc_bootstrap_95_ci", [None, None])
            sci = sensitivity.get("auc_bootstrap_95_ci", [None, None])
            writer.writerow({
                "target_id": target_id, "engine_region_id": TARGET_ENGINE_IDS[target_id], "status": item["status"],
                "used_feature_count": item.get("used_feature_count", 0),
                "used_features": ";".join(item.get("used_features", [])),
                "excluded_features": ";".join(item.get("excluded_features", [])),
                "valid_positive_cell_count": item.get("valid_positive_cell_count", 0),
                "valid_cell_count": item.get("valid_cell_count", 0), "base_rate": item.get("base_rate"),
                "primary_auc": primary.get("auc"), "primary_auc_ci_low": pci[0], "primary_auc_ci_high": pci[1],
                "sensitivity_auc": sensitivity.get("auc"), "sensitivity_auc_ci_low": sci[0],
                "sensitivity_auc_ci_high": sci[1], "reason": item.get("reason"),
                "scope": json.dumps(result["scope"], ensure_ascii=True, separators=(",", ":")),
            })
    print("Valid positive counts (first):")
    print(json.dumps(result["positive_counts_at_start"], ensure_ascii=True))
    print(f"JSON: {json_path}\nCSV: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
