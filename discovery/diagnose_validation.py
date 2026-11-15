"""Numeric multi-target diagnostics for the independent USGS sample."""

from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import rankdata

from .analog_mapping import cell_id
from .analysis_utils import TARGET_ENGINE_IDS, TARGET_IDS

ROOT = Path(__file__).resolve().parent
FEATURES = (
    "slope_median_deg", "slope_p90_deg", "flat_fraction", "tri_median_m",
    "relief_m", "elevation_std_m",
)
REFERENCE_DIRECTIONS = {
    "flat_fraction": 1.0,
    "-relief_m": -1.0,
    "-slope_median_deg": -1.0,
    "-elevation_std_m": -1.0,
}
DEFAULT_GRID = ROOT / "data/inputs/earth_grid_validation.parquet"
DEFAULT_MAP = ROOT / "data/inputs/validation_sample/cell_key_map.csv"
DEFAULT_SCORES = ROOT / "out/runs/c6e4be4_v2/scores_validation.parquet"
DEFAULT_ANALOGS = ROOT / "out/known_analogs.json"
DEFAULT_VALIDATION = ROOT / "out/runs/c6e4be4_v2/usgs_sample/validation_results.json"
DEFAULT_OUT = ROOT / "out/runs/c6e4be4_v2/usgs_sample"


def auc(positive: np.ndarray, background: np.ndarray) -> float | None:
    positive = np.asarray(positive, dtype=float)
    background = np.asarray(background, dtype=float)
    if not len(positive) or not len(background):
        return None
    ranks = rankdata(np.concatenate([positive, background]), method="average")
    u = ranks[:len(positive)].sum() - len(positive) * (len(positive) + 1) / 2
    return float(u / (len(positive) * len(background)))


def latitude_summary(positive_lats: np.ndarray, background_lats: np.ndarray) -> dict:
    edges = [-90, -60, -30, 0, 30, 60, 90.0000001]
    labels = ["[-90,-60)", "[-60,-30)", "[-30,0)", "[0,30)", "[30,60)", "[60,90]"]
    groups = {}
    for name, values in (("positive", positive_lats), ("background", background_lats)):
        values = np.asarray(values, dtype=float)
        bins = np.histogram(values, bins=edges)[0]
        groups[name] = {
            "count": int(len(values)),
            "median_absolute_latitude": float(np.median(np.abs(values))) if len(values) else None,
            "latitude_band_counts": {label: int(n) for label, n in zip(labels, bins, strict=True)},
            "latitude_band_proportions": {label: (float(n / len(values)) if len(values) else None) for label, n in zip(labels, bins, strict=True)},
        }
    return groups


def latitude_stratified_auc(frame: pd.DataFrame, score_col: str) -> dict:
    edges = [-90, -60, -30, 0, 30, 60, 90.0000001]
    labels = ["[-90,-60)", "[-60,-30)", "[-30,0)", "[0,30)", "[30,60)", "[60,90]"]
    values = pd.to_numeric(frame[score_col], errors="coerce")
    work = frame.loc[values.notna()].copy()
    work["_score"] = values.loc[values.notna()]
    work["_band"] = pd.cut(pd.to_numeric(work.lat), bins=edges, labels=labels, right=False, include_lowest=True)
    result = []
    numerator = 0.0
    denominator = 0
    for label in labels:
        band = work.loc[work._band == label]
        pos = band.loc[band.group.eq("analog"), "_score"].to_numpy(dtype=float)
        bg = band.loc[band.group.eq("background"), "_score"].to_numpy(dtype=float)
        if len(pos) == 0 or len(bg) == 0:
            continue
        band_auc = auc(pos, bg)
        weight = len(pos) * len(bg)
        numerator += float(band_auc) * weight
        denominator += weight
        result.append({"band": str(label), "positive_count": int(len(pos)), "background_count": int(len(bg)), "auc": band_auc})
    return {"bands": result, "pooled_auc": numerator / denominator if denominator else None,
            "pooled_weight": int(denominator)}


def paired_bootstrap(
    frame: pd.DataFrame, target_col: str, reference_col: str,
    *, n_boot: int, seed: int,
) -> dict:
    subset = frame[["group", target_col, reference_col]].dropna()
    positive = subset.loc[subset.group.eq("analog")]
    background = subset.loc[subset.group.eq("background")]
    target_pos = positive[target_col].to_numpy(dtype=float)
    target_bg = background[target_col].to_numpy(dtype=float)
    ref_pos = positive[reference_col].to_numpy(dtype=float)
    ref_bg = background[reference_col].to_numpy(dtype=float)
    target_auc, ref_auc = auc(target_pos, target_bg), auc(ref_pos, ref_bg)
    if target_auc is None or ref_auc is None:
        return {"positive_count": len(target_pos), "background_count": len(target_bg),
                "target_auc": target_auc, "reference_auc": ref_auc,
                "difference_target_minus_reference": None,
                "reference_auc_bootstrap_95_ci": None, "difference_paired_bootstrap_95_ci": None}
    rng = np.random.default_rng(seed)
    target_samples = np.empty(n_boot)
    reference_samples = np.empty(n_boot)
    for i in range(n_boot):
        ip = rng.integers(0, len(target_pos), len(target_pos))
        ib = rng.integers(0, len(target_bg), len(target_bg))
        target_samples[i] = auc(target_pos[ip], target_bg[ib])
        reference_samples[i] = auc(ref_pos[ip], ref_bg[ib])
    difference = target_samples - reference_samples
    return {
        "positive_count": int(len(target_pos)), "background_count": int(len(target_bg)),
        "target_auc": target_auc, "reference_auc": ref_auc,
        "difference_target_minus_reference": target_auc - ref_auc,
        "reference_auc_bootstrap_95_ci": [float(x) for x in np.quantile(reference_samples, [.025, .975])],
        "difference_paired_bootstrap_95_ci": [float(x) for x in np.quantile(difference, [.025, .975])],
        "bootstrap_iterations": n_boot,
    }


def analyze_v2(
    grid_path: Path, map_path: Path, scores_path: Path, analogs_path: Path,
    validation_path: Path, *, n_boot: int = 1000, seed: int = 42,
) -> tuple[dict, list[dict]]:
    grid = pq.read_table(grid_path).to_pandas()
    grid["cell_key"] = [cell_id(float(lat), float(lon)) for lat, lon in zip(grid.lat, grid.lon, strict=True)]
    sample_map = pd.read_csv(map_path).drop_duplicates("cell_key").set_index("cell_key")
    groups = sample_map.group.astype(str).to_dict()
    score_frame = pq.read_table(scores_path).to_pandas()
    analog_payload = json.loads(analogs_path.read_text(encoding="utf-8"))
    analog_records = analog_payload if isinstance(analog_payload, list) else analog_payload.get("records", [])
    analog_keys = {cell_id(float(row["lat"]), float(row["lon"])) for row in analog_records}
    grid["group"] = grid.cell_key.map(groups)
    grid["group"] = grid.group.where(grid.group.isin(("analog", "background")), "excluded")
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    p_values = {}
    for tid, result in validation.get("targets", {}).items():
        p_values[tid] = result.get("cohorts", {}).get("primary_unlabeled_background", {}).get("permutation_p_value")

    target_results = {}
    csv_rows: list[dict] = []
    scored_target_ids = []
    for index, target_id in enumerate(TARGET_IDS):
        target_scores = score_frame.loc[score_frame.target_id.astype(str).eq(target_id)].drop_duplicates("cell_id", keep="first")
        used_features = [c[2:] for c in target_scores.columns if str(c).startswith("s_")
                         and pd.to_numeric(target_scores[c], errors="coerce").notna().any()]
        excluded_features = [feature for feature in FEATURES if feature not in used_features]
        score_map = target_scores.set_index(target_scores.cell_id.astype(str))
        frame = grid.copy()
        frame["score"] = frame.cell_id.astype(str).map(score_map.score)
        valid = frame.score.notna() & frame.group.isin(("analog", "background"))
        cohort = frame.loc[valid].copy()
        if "land_fraction" in cohort.columns:
            cohort = cohort.loc[pd.to_numeric(cohort.land_fraction, errors="coerce").ge(.5)]
        positive = cohort.loc[cohort.group.eq("analog")]
        background = cohort.loc[cohort.group.eq("background")]
        if len(positive) and len(background):
            scored_target_ids.append(target_id)
        criterion_results = {}
        criterion_columns = [c for c in target_scores.columns if str(c).startswith("s_")]
        for column in criterion_columns:
            criterion_map = target_scores.set_index(target_scores.cell_id.astype(str))[column]
            cohort[column] = cohort.cell_id.astype(str).map(criterion_map)
            pos_vals = pd.to_numeric(cohort.loc[cohort.group.eq("analog"), column], errors="coerce").dropna().to_numpy(dtype=float)
            bg_vals = pd.to_numeric(cohort.loc[cohort.group.eq("background"), column], errors="coerce").dropna().to_numpy(dtype=float)
            criterion_auc = auc(pos_vals, bg_vals)
            criterion_results[column] = {"positive_count": len(pos_vals), "background_count": len(bg_vals), "auc": criterion_auc}
            csv_rows.append({"target_id": target_id, "engine_region_id": TARGET_ENGINE_IDS[target_id], "metric_type": "criterion", "metric": column,
                             "auc": criterion_auc, "positive_count": len(pos_vals), "background_count": len(bg_vals)})

        references = {}
        reference_cols = []
        for name, sign in REFERENCE_DIRECTIONS.items():
            feature = name.lstrip("-")
            column = "reference_" + name.replace("-", "minus_")
            cohort[column] = pd.to_numeric(cohort[feature], errors="coerce") * sign
            reference_cols.append((name, column))
        for ref_index, (name, column) in enumerate(reference_cols):
            refs = paired_bootstrap(cohort, "score", column, n_boot=n_boot, seed=seed + index * 100 + ref_index)
            references[name] = refs
            csv_rows.append({"target_id": target_id, "engine_region_id": TARGET_ENGINE_IDS[target_id], "metric_type": "reference", "metric": name,
                             "auc": refs["reference_auc"], "auc_ci_low": (refs.get("reference_auc_bootstrap_95_ci") or [None, None])[0],
                             "auc_ci_high": (refs.get("reference_auc_bootstrap_95_ci") or [None, None])[1],
                             "target_auc": refs.get("target_auc"),
                             "difference_target_minus_reference": refs.get("difference_target_minus_reference"),
                             "difference_ci_low": (refs.get("difference_paired_bootstrap_95_ci") or [None, None])[0],
                             "difference_ci_high": (refs.get("difference_paired_bootstrap_95_ci") or [None, None])[1],
                             "positive_count": refs["positive_count"], "background_count": refs["background_count"]})
        best_reference = max(
            (name for name, _ in reference_cols),
            key=lambda name: references[name]["reference_auc"] if references[name]["reference_auc"] is not None else -math.inf,
            default=None,
        )
        score_lat = latitude_stratified_auc(cohort, "score")
        ref_lat = latitude_stratified_auc(cohort, dict(reference_cols)[best_reference]) if best_reference else {"bands": [], "pooled_auc": None, "pooled_weight": 0}
        for score_type, lat_result in (("target_score", score_lat), ("best_reference:" + str(best_reference), ref_lat)):
            for band in lat_result["bands"]:
                csv_rows.append({"target_id": target_id, "engine_region_id": TARGET_ENGINE_IDS[target_id], "metric_type": "latitude_band", "metric": score_type,
                                 "band": band["band"], "auc": band["auc"],
                                 "positive_count": band["positive_count"], "background_count": band["background_count"]})
            csv_rows.append({"target_id": target_id, "engine_region_id": TARGET_ENGINE_IDS[target_id], "metric_type": "latitude_pooled", "metric": score_type,
                             "auc": lat_result["pooled_auc"], "pooled_weight": lat_result["pooled_weight"]})

        summary = validation.get("targets", {}).get(target_id, {})
        primary = summary.get("cohorts", {}).get("primary_unlabeled_background", {})
        csv_rows.append({"target_id": target_id, "engine_region_id": TARGET_ENGINE_IDS[target_id],
                         "metric_type": "target_summary", "metric": "scoring_features",
                         "used_feature_count": len(used_features), "used_features": ";".join(used_features),
                         "excluded_features": ";".join(excluded_features)})
        target_results[target_id] = {
            "engine_region_id": TARGET_ENGINE_IDS[target_id],
            "status": summary.get("status"),
            "used_feature_count": len(used_features), "used_features": used_features,
            "excluded_features": excluded_features,
            "positive_count": int(len(positive)), "background_count": int(len(background)),
            "target_score_auc": primary.get("auc"), "target_score_auc_ci": primary.get("auc_bootstrap_95_ci"),
            "permutation_p_value": p_values.get(target_id),
            "criterion_score_aucs": criterion_results,
            "reference_scores": references,
            "best_reference_by_auc": best_reference,
            "latitude_stratified_target_score": score_lat,
            "latitude_stratified_best_reference": ref_lat,
        }

    tested_count = len(scored_target_ids)
    threshold = 0.05 / tested_count if tested_count else None
    p_summary = {tid: {"permutation_p_value": p_values.get(tid),
                       "passes_bonferroni": bool(p_values.get(tid) is not None and threshold is not None and p_values[tid] <= threshold)}
                 for tid in scored_target_ids}
    for tid, item in p_summary.items():
        csv_rows.append({"target_id": tid, "engine_region_id": TARGET_ENGINE_IDS[tid], "metric_type": "bonferroni", "metric": "permutation_p_value",
                         "auc": None, "p_value": item["permutation_p_value"], "threshold": threshold,
                         "passes": item["passes_bonferroni"]})
    payload = {
        "grid_rows": int(len(grid)), "tested_target_count": tested_count,
        "bonferroni_alpha": 0.05, "bonferroni_threshold": threshold,
        "bonferroni_results": p_summary,
        "targets": target_results,
        "caveats": [
            "All targets use the same positive USGS cells because analog_for is empty for 191/192 records.",
            "The background sample was selected from cells passing WorldCover QA.",
        ],
        "bootstrap_iterations": n_boot, "bootstrap_seed": seed,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    return payload, csv_rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", type=Path, default=DEFAULT_GRID)
    parser.add_argument("--sample-map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--scores", type=Path, default=DEFAULT_SCORES)
    parser.add_argument("--analogs", type=Path, default=DEFAULT_ANALOGS)
    parser.add_argument("--validation-results", type=Path, default=DEFAULT_VALIDATION)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--n-boot", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.n_boot < 1:
        parser.error("--n-boot must be positive")
    payload, rows = analyze_v2(args.grid, args.sample_map, args.scores, args.analogs,
                               args.validation_results, n_boot=args.n_boot, seed=args.seed)
    json_path, csv_path = args.out_dir / "diagnostics_v2.json", args.out_dir / "diagnostics_v2.csv"
    args.out_dir.mkdir(parents=True, exist_ok=True)
    if json_path.exists() or csv_path.exists():
        raise FileExistsError("Refusing to overwrite diagnostics_v2 outputs")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"json": str(json_path), "csv": str(csv_path), "tested_target_count": payload["tested_target_count"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
