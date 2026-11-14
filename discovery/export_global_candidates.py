"""Export real grid cells selected by score, Turkey references, and USGS analogs."""

from __future__ import annotations

import argparse
import json
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from .analysis_utils import (
    SCORING_FEATURES, TARGET_IDS, UNSCORABLE_TARGETS, load_grid,
    non_overwriting_path, safe_json_value, scope_block, scores_by_key, timestamp_iso,
)
from .analog_mapping import cell_id
from .grid_utils import cell_polygon
from .score_io import load_scores


ROOT = Path(__file__).resolve().parent
DEFAULT_GRID = ROOT / "data" / "inputs" / "earth_grid.parquet"
DEFAULT_SCORES = ROOT.parent / "engine" / "out" / "scores"
DEFAULT_ANALOGS = ROOT / "out" / "known_analogs.json"
DEFAULT_TURKEY = ROOT / "out" / "turkey_analogs.json"
DEFAULT_OUTPUT = ROOT / "out" / "global_candidates.geojson"
MAX_WARN_BYTES = 15 * 1024 * 1024
MAX_BYTES = 40 * 1024 * 1024


def records_from_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else data.get("records", [])


def analog_groups(path: Path) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for row in records_from_json(path):
        key = cell_id(float(row["lat"]), float(row["lon"]))
        name = str(row.get("name") or "")
        if name and name not in groups[key]:
            groups[key].append(name)
    return dict(groups)


def turkey_groups(path: Path | None) -> dict[str, list[str]]:
    if path is None or not path.is_file():
        warnings.warn("Turkey analog file is absent; no Turkey cells will be added", RuntimeWarning)
        return {}
    groups: dict[str, list[str]] = defaultdict(list)
    for row in records_from_json(path):
        key = cell_id(float(row["lat"]), float(row["lon"]))
        groups[key].append(str(row["region_id"]))
    return dict(groups)


def build_collection(
    grid: pd.DataFrame, score_frame: pd.DataFrame, analogs: dict[str, list[str]],
    turkey: dict[str, list[str]], top_k: int, precision: int,
) -> dict[str, Any]:
    keyed_scores = scores_by_key(score_frame, grid)
    grid_by_key = grid.drop_duplicates("cell_key", keep="first").set_index("cell_key")
    reasons: dict[str, set[str]] = defaultdict(set)
    score_map: dict[str, dict[str, float]] = defaultdict(dict)
    rank_map: dict[str, dict[str, int]] = defaultdict(dict)
    criteria_map: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)

    for target_id in TARGET_IDS:
        if target_id in UNSCORABLE_TARGETS:
            continue
        target = keyed_scores.loc[
            keyed_scores.target_id.astype(str).eq(target_id)
            & keyed_scores.cell_key.notna()
            & keyed_scores.score.notna()
        ].copy()
        target = target.drop_duplicates("cell_key", keep="first")
        target = target.loc[target.cell_key.astype(str).isin(grid_by_key.index)]
        target = target.sort_values(["score", "cell_key"], ascending=[False, True], kind="mergesort")
        selected = target.head(top_k)
        for rank, (_, row) in enumerate(selected.iterrows(), start=1):
            key = str(row.cell_key)
            reasons[key].add(f"top_{target_id}")
            score_map[key][target_id] = float(row.score)
            rank_map[key][target_id] = rank
            criteria = {}
            for feature in SCORING_FEATURES:
                col = f"s_{feature}"
                if col in target.columns and pd.notna(row.get(col)):
                    criteria[col] = float(row[col])
            if criteria:
                criteria_map[key][target_id] = criteria

    for key in turkey:
        if key in grid_by_key.index:
            reasons[key].add("turkey_site")
    for key in analogs:
        if key in grid_by_key.index:
            reasons[key].add("usgs_analog")

    features = []
    for key in sorted(reasons):
        row = grid_by_key.loc[key]
        lat, lon = float(row.lat), float(row.lon)
        props: dict[str, Any] = {
            "cell_id": row.get("cell_id", key),
            "cell_key": key,
            "lat": round(lat, precision),
            "lon": round(lon, precision),
            "features": {
                name: (round(float(row[name]), precision) if pd.notna(row.get(name)) else None)
                for name in SCORING_FEATURES
            },
            "scores": {target_id: score_map[key].get(target_id) for target_id in TARGET_IDS},
            "ranks": {target_id: rank_map[key].get(target_id) for target_id in TARGET_IDS},
            "turkey_region_ids": turkey.get(key, []),
            "usgs_analog_count": len(analogs.get(key, [])),
            "selection_reasons": sorted(reasons[key]),
        }
        if key in criteria_map:
            props["criterion_scores"] = criteria_map[key]
        feature = {
            "type": "Feature",
            "geometry": cell_polygon(key),
            "properties": props,
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "metadata": {
            "scope": scope_block(grid),
            "unscorable_targets": UNSCORABLE_TARGETS,
            "generated_at": timestamp_iso(),
        },
        "features": features,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", nargs="+", type=Path, default=[DEFAULT_GRID])
    parser.add_argument("--scores", type=Path, default=DEFAULT_SCORES)
    parser.add_argument("--analogs", type=Path, default=DEFAULT_ANALOGS)
    parser.add_argument("--turkey", type=Path, default=DEFAULT_TURKEY)
    parser.add_argument("--top-k", type=int, default=500)
    parser.add_argument("--precision", type=int, default=4)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.top_k < 1 or args.precision < 0:
        parser.error("--top-k must be positive and --precision non-negative")
    if not args.scores.exists():
        raise FileNotFoundError(
            f"Person 2 score export not found: {args.scores}; expected scores_all.parquet or scores_all.csv"
        )
    grid = load_grid(args.grid)
    scores = load_scores(args.scores)
    analogs = analog_groups(args.analogs)
    turkey = turkey_groups(args.turkey)
    collection = build_collection(grid, scores, analogs, turkey, args.top_k, args.precision)
    payload = json.dumps(safe_json_value(collection), ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    size = len(payload.encode("utf-8"))
    if size > MAX_BYTES:
        raise ValueError(f"Export size {size} bytes exceeds 40 MB limit")
    if size > MAX_WARN_BYTES:
        warnings.warn(f"Export is {size} bytes, above 15 MB", RuntimeWarning)
    output = non_overwriting_path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8")
    print(f"Wrote {output} ({size} bytes; {len(collection['features'])} features)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
