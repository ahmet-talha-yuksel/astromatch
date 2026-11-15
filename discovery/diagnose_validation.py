"""Write numeric diagnostics for the independent USGS validation sample."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import rankdata

from .analog_mapping import cell_id

ROOT = Path(__file__).resolve().parent
FEATURES = (
    "slope_median_deg", "slope_p90_deg", "flat_fraction", "tri_median_m",
    "relief_m", "elevation_std_m",
)
DEFAULT_GRID = ROOT / "data/inputs/earth_grid_validation.parquet"
DEFAULT_MAP = ROOT / "data/inputs/validation_sample/cell_key_map.csv"
DEFAULT_SCORES = ROOT / "data/inputs/scores_validation.parquet"
DEFAULT_FEATURES = ROOT / "data/inputs/features.json"
DEFAULT_ANALOGS = ROOT / "out/known_analogs.json"
DEFAULT_OUT = ROOT / "out/validation/usgs_sample"


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


def output_paths(out_dir: Path) -> tuple[Path, Path]:
    base_json, base_csv = out_dir / "diagnostics.json", out_dir / "diagnostics.csv"
    if not base_json.exists() and not base_csv.exists():
        return base_json, base_csv
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path, csv_path = out_dir / f"diagnostics_{stamp}.json", out_dir / f"diagnostics_{stamp}.csv"
    n = 2
    while json_path.exists() or csv_path.exists():
        json_path, csv_path = out_dir / f"diagnostics_{stamp}_{n}.json", out_dir / f"diagnostics_{stamp}_{n}.csv"
        n += 1
    return json_path, csv_path


def analyze(grid_path: Path, map_path: Path, scores_path: Path, features_path: Path, analogs_path: Path) -> tuple[dict, list[dict]]:
    grid = pq.read_table(grid_path).to_pandas()
    grid["cell_key"] = [cell_id(float(lat), float(lon)) for lat, lon in zip(grid.lat, grid.lon, strict=True)]
    sample_map = pd.read_csv(map_path).drop_duplicates("cell_key").set_index("cell_key")
    score_frame = pq.read_table(scores_path).to_pandas()
    score_frame = score_frame.loc[score_frame.target_id.astype(str).eq("T-02")].drop_duplicates("cell_id", keep="first")
    score_map = score_frame.set_index("cell_id").score
    grid = grid.set_index("cell_key", drop=False)
    grid["score"] = score_map.reindex(grid.cell_id).to_numpy()
    land = pd.to_numeric(grid.get("land_fraction", pd.Series(1.0, index=grid.index)), errors="coerce")
    valid = grid.score.notna() & land.ge(0.5)
    analog_payload = json.loads(analogs_path.read_text(encoding="utf-8"))
    analog_records = analog_payload if isinstance(analog_payload, list) else analog_payload.get("records", [])
    analog_keys = {cell_id(float(r["lat"]), float(r["lon"])) for r in analog_records}
    positives = set(grid.index[valid]) & analog_keys
    backgrounds = set(grid.index[valid]) - analog_keys
    # The sample manifest labels are checked against the exact validate_usgs cohorts.
    mapped_groups = sample_map.group.astype(str).to_dict()
    if any(mapped_groups.get(k) != "analog" for k in positives):
        raise ValueError("Sample map does not label every valid USGS-positive cell as analog")
    if any(mapped_groups.get(k) != "background" for k in backgrounds):
        raise ValueError("Sample map does not label every valid non-analog cell as background")
    pos, bg = grid.loc[sorted(positives)], grid.loc[sorted(backgrounds)]

    feature_payload = json.loads(features_path.read_text(encoding="utf-8"))
    target = next(r for r in feature_payload["records"] if r.get("region_id") == "moon_shackleton_regional")
    rows = []
    for feature in FEATURES:
        pvals = pd.to_numeric(pos[feature], errors="coerce").dropna().to_numpy(dtype=float)
        bvals = pd.to_numeric(bg[feature], errors="coerce").dropna().to_numpy(dtype=float)
        target_entry = (target.get("features") or {}).get(feature) or {}
        rows.append({
            "feature": feature,
            "positive_n": int(len(pvals)),
            "positive_median": float(np.median(pvals)) if len(pvals) else None,
            "background_n": int(len(bvals)),
            "background_median": float(np.median(bvals)) if len(bvals) else None,
            "univariate_auc_raw_value": auc(pvals, bvals),
            "moon_shackleton_regional_reference_value": target_entry.get("value"),
        })

    criterion_rows = []
    criteria = [c for c in score_frame.columns if str(c).startswith("s_")]
    for column in criteria:
        by_key = score_frame.set_index("cell_id")[column]
        pvals = pd.to_numeric(by_key.reindex(pos.cell_id), errors="coerce").dropna().to_numpy(dtype=float)
        bvals = pd.to_numeric(by_key.reindex(bg.cell_id), errors="coerce").dropna().to_numpy(dtype=float)
        criterion_rows.append({"criterion": column, "positive_n": len(pvals), "positive_median": float(np.median(pvals)) if len(pvals) else None,
                               "background_n": len(bvals), "background_median": float(np.median(bvals)) if len(bvals) else None,
                               "auc": auc(pvals, bvals)})

    payload = {
        "target_id": "T-02",
        "grid_rows": int(len(grid)),
        "valid_cell_count": int(valid.sum()),
        "positive_count": int(len(positives)),
        "background_count": int(len(backgrounds)),
        "feature_diagnostics": rows,
        "criterion_score_diagnostics": criterion_rows,
        "latitude_distribution": latitude_summary(pos.lat.to_numpy(), bg.lat.to_numpy()),
        "caveats": [
            "Univariate AUC is not evidence of causality.",
            "Background cells were selected from those passing WorldCover QA; VALIDATION_SAMPLE.md does not state whether the same QA was applied to analog cells.",
        ],
    }
    return payload, rows + criterion_rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", type=Path, default=DEFAULT_GRID)
    parser.add_argument("--sample-map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--scores", type=Path, default=DEFAULT_SCORES)
    parser.add_argument("--features", type=Path, default=DEFAULT_FEATURES)
    parser.add_argument("--analogs", type=Path, default=DEFAULT_ANALOGS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    payload, rows = analyze(args.grid, args.sample_map, args.scores, args.features, args.analogs)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path, csv_path = output_paths(args.out_dir)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"json": str(json_path), "csv": str(csv_path), "positive_count": payload["positive_count"], "background_count": payload["background_count"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
