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
    SCORING_FEATURES, TARGET_ENGINE_IDS, TARGET_IDS, UNSCORABLE_TARGETS, load_grid,
    non_overwriting_path, safe_json_value, scope_block, scores_by_key, timestamp_iso,
)
from .analog_mapping import cell_id
from .grid_utils import cell_polygon, parse_cell_id
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


def load_grid_sources(paths: list[Path]) -> pd.DataFrame:
    frames = []
    for path in paths:
        frame = pd.read_parquet(path).copy()
        if "lat" not in frame or "lon" not in frame:
            raise ValueError(f"Grid is missing coordinates: {path}")
        frame["cell_key"] = [cell_id(float(lat), float(lon)) for lat, lon in zip(frame.lat, frame.lon)]
        frame["grid_source"] = "validation_sample" if "validation" in path.stem.lower() else "pilot"
        frames.append(frame)
    if not frames:
        raise ValueError("At least one grid is required")
    return pd.concat(frames, ignore_index=True, sort=False)


def build_collection(
    grid: pd.DataFrame, score_frame: pd.DataFrame, analogs: dict[str, list[str]],
    turkey: dict[str, list[str]], top_k: int, precision: int,
    engine_commit: str | None = None,
) -> dict[str, Any]:
    keyed_scores = scores_by_key(score_frame, grid)
    if "grid_source" not in grid:
        grid = grid.copy()
        grid["grid_source"] = "pilot"
    grid = grid.reset_index(drop=True)
    reasons: dict[tuple[str, str], set[str]] = defaultdict(set)
    score_map: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    rank_map: dict[tuple[str, str], dict[str, int]] = defaultdict(dict)
    criteria_map: dict[tuple[str, str], dict[str, dict[str, float]]] = defaultdict(dict)
    grid_lookup = {}
    for idx, row in grid.iterrows():
        source, key = str(row.grid_source), str(row.cell_key)
        grid_lookup[(source, key)] = idx
    if "grid_source" in score_frame.columns:
        score_lookup = {
            (str(row.grid_source), str(row.cell_id), str(row.target_id)): row
            for row in keyed_scores.itertuples(index=False)
        }
    else:
        score_lookup = {}
        for row in keyed_scores.itertuples(index=False):
            score_lookup[("*", str(row.cell_key), str(row.target_id))] = row

    target_states = {}

    for target_id in TARGET_IDS:
        selected_rows = []
        feature_columns = [f"s_{feature}" for feature in SCORING_FEATURES if f"s_{feature}" in keyed_scores.columns]
        valid_target = keyed_scores.loc[keyed_scores.target_id.astype(str).eq(target_id)]
        used_features = [col[2:] for col in feature_columns if pd.to_numeric(valid_target[col], errors="coerce").notna().any()]
        target_states[target_id] = {
            "engine_region_id": TARGET_ENGINE_IDS[target_id],
            "status": "scorable" if valid_target.score.notna().any() else "unscorable",
            "used_feature_count": len(used_features),
            "used_features": used_features,
            "excluded_features": [feature for feature in SCORING_FEATURES if feature not in used_features],
        }
        if target_states[target_id]["status"] == "unscorable":
            continue
        for (source, key), idx in grid_lookup.items():
            row = grid.iloc[idx]
            cell_id_value = str(row.get("cell_id", key))
            match = score_lookup.get((source, cell_id_value, target_id))
            if match is None and "grid_source" not in score_frame.columns:
                match = score_lookup.get(("*", key, target_id))
            if match is None or pd.isna(match.score):
                continue
            selected_rows.append({"source": source, "key": key, "idx": idx, "score": float(match.score), "match": match})
        selected_rows.sort(key=lambda item: (-item["score"], item["key"], item["source"]))
        for rank, item in enumerate(selected_rows[:top_k], start=1):
            pair, row, match = (item["source"], item["key"]), grid.iloc[item["idx"]], item["match"]
            reasons[pair].add(f"top_{target_id}")
            score_map[pair][target_id] = item["score"]
            rank_map[pair][target_id] = rank
            criteria = {}
            for feature in SCORING_FEATURES:
                col = f"s_{feature}"
                value = getattr(match, col, None)
                if value is not None and pd.notna(value):
                    criteria[col] = float(value)
            if criteria:
                criteria_map[pair][target_id] = criteria

    for pair in reasons:
        _, key = pair
        if key in turkey:
            reasons[pair].add("turkey_site")
        if key in analogs:
            reasons[pair].add("usgs_analog")
    for source, key in grid_lookup:
        pair = (source, key)
        if key in turkey:
            reasons[pair].add("turkey_site")
        if key in analogs:
            reasons[pair].add("usgs_analog")
    processed_keys = {key for _, key in grid_lookup}
    for key in (set(turkey) | set(analogs)) - processed_keys:
        pair = ("reference_only", key)
        if key in turkey:
            reasons[pair].add("turkey_site")
        if key in analogs:
            reasons[pair].add("usgs_analog")

    features = []
    for source, key in sorted(reasons):
        row = grid.iloc[grid_lookup[(source, key)]] if source != "reference_only" else None
        pair = (source, key)
        lat, lon = (float(row.lat), float(row.lon)) if row is not None else parse_cell_id(key)
        props: dict[str, Any] = {
            "cell_id": row.get("cell_id", key) if row is not None else key,
            "cell_key": key,
            "grid_source": source,
            "lat": round(lat, precision),
            "lon": round(lon, precision),
            "features": {
                name: (round(float(row[name]), precision) if row is not None and pd.notna(row.get(name)) else None)
                for name in SCORING_FEATURES
            },
            "scores": {target_id: score_map[pair].get(target_id) for target_id in TARGET_IDS},
            "ranks": {target_id: rank_map[pair].get(target_id) for target_id in TARGET_IDS},
            "engine_region_ids": {target_id: TARGET_ENGINE_IDS[target_id] for target_id in TARGET_IDS},
            "turkey_region_ids": turkey.get(key, []),
            "usgs_analog_count": len(analogs.get(key, [])),
            "selection_reasons": sorted(reasons[pair]),
        }
        if pair in criteria_map:
            props["criterion_scores"] = criteria_map[pair]
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
            "targets": target_states,
            "engine_commit": engine_commit,
            "generated_at": timestamp_iso(),
        },
        "features": features,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", nargs="+", type=Path, default=[DEFAULT_GRID])
    parser.add_argument("--scores", nargs="+", type=Path, default=[DEFAULT_SCORES])
    parser.add_argument("--analogs", type=Path, default=DEFAULT_ANALOGS)
    parser.add_argument("--turkey", type=Path, default=DEFAULT_TURKEY)
    parser.add_argument("--top-k", type=int, default=500)
    parser.add_argument("--precision", type=int, default=4)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--engine-commit", default=None)
    args = parser.parse_args()
    if args.top_k < 1 or args.precision < 0:
        parser.error("--top-k must be positive and --precision non-negative")
    missing_scores = [path for path in args.scores if not path.exists()]
    if missing_scores:
        raise FileNotFoundError(f"Score file(s) not found: {missing_scores}")
    grid = load_grid_sources(args.grid)
    scores = pd.concat([load_scores(path) for path in args.scores], ignore_index=True, sort=False)
    analogs = analog_groups(args.analogs)
    turkey = turkey_groups(args.turkey)
    collection = build_collection(grid, scores, analogs, turkey, args.top_k, args.precision, args.engine_commit)
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
