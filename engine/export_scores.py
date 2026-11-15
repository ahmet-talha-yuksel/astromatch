"""Long-format validation score export."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pandas as pd
import numpy as np

from .io import ROOT, feature_paths, merged_features
from .validation_api import _score_grid, list_target_ids


def _grid_extent(frame):
    if not {'lat','lon'} <= set(frame.columns): return None
    cells=frame
    if 'kind' in frame:
        cells=frame.loc[frame['kind'].eq('earth_grid')]
    coords=cells[['lat','lon']].apply(pd.to_numeric,errors='coerce').dropna()
    if coords.empty: return None
    return {'lat_min':float(coords.lat.min()),'lat_max':float(coords.lat.max()),
            'lon_min':float(coords.lon.min()),'lon_max':float(coords.lon.max())}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export_scores(*, mock=False, features=None, grid=None, preset="balanced",
                  sigma=None, criteria=False, out="engine/out/scores/") -> dict:
    from .cli import ENGINE_VERSION

    hashes = {}
    if mock:
        from .mock import generate
        targets, candidates, _ = generate(n_grid=5000)
        rows = []
        for candidate in candidates:
            if candidate["kind"] != "earth_grid":
                continue
            row = {k: v for k, v in candidate.items() if k != "features"}
            row["cell_id"] = candidate["region_id"]
            for key, item in candidate["features"].items():
                row[key] = item["value"]
                row[key + "__status"] = item["data_status"]
                row[key + "__comparable"] = item["comparable"]
            rows.append(row)
        grid_df = pd.DataFrame(rows)
        hashes["mock_seed_42"] = hashlib.sha256(json.dumps([targets, rows], sort_keys=True).encode()).hexdigest()
        data_status = "mock"
        grid_status = "synthetic_global"
    else:
        feature_files=feature_paths(features)
        grid_path = Path(grid or ROOT / "processing/out/earth_grid.parquet")
        if not grid_path.is_absolute():
            grid_path = ROOT / grid_path
        if not grid_path.exists() and grid is None:
            grid_path = ROOT / "processing/out/real/earth_grid.parquet"
        for feature_path in feature_files:
            if not feature_path.exists():
                raise FileNotFoundError(f"Missing features: {feature_path}")
        if not grid_path.exists():
            raise FileNotFoundError(f"Missing grid: {grid_path}")
        merged,overrides=merged_features(feature_files)
        targets = [r for r in merged if r.get("kind") == "target"]
        grid_df = pd.read_parquet(grid_path)
        for feature_path in feature_files: hashes[str(feature_path)] = _digest(feature_path)
        hashes[str(grid_path)] = _digest(grid_path)
        data_status = "real"
        kinds = set(grid_df["kind"].dropna()) if "kind" in grid_df else set()
        grid_status = "sites_only" if kinds == {"candidate"} else "regional_subset" if len(grid_df)<1000 else "global"

    if "cell_id" not in grid_df:
        if "region_id" not in grid_df:
            raise ValueError("Grid requires cell_id or region_id")
        grid_df = grid_df.assign(cell_id=grid_df["region_id"])
    aliases = list_target_ids()
    active = aliases
    from .io import load_dataset
    from .models import DataPaths
    from .ranking import rank
    dataset=load_dataset(mock=True,mock_n_grid=5000) if mock else load_dataset(DataPaths(features=[str(p) for p in feature_files],grid=str(grid_path)))
    places={c.region_id:c.place for c in dataset.candidates if c.body=='earth'}
    frames = []
    sigma_tables = {}
    calibration_tables = {}
    contextual_factors = {}
    counts = {}
    unscorable = {}
    for alias in active:
        scored = _score_grid(grid_df, alias, preset, sigma=sigma, scale="regional",
                             return_criteria=criteria, target_records=targets)
        place_values=scored['cell_id'].map(places)
        scored['place']=place_values.map(lambda place:json.dumps(place,ensure_ascii=False) if place else None)
        for column,key in (('place_name','name'),('place_admin1','admin1'),('place_country_code','country_code'),('place_distance_km','distance_km')):
            scored[column]=place_values.map(lambda place:place.get(key) if place else None)
        base=aliases.get(alias)
        target_id=alias if mock else f'{base}_regional' if base else None
        matching=next((t for t in dataset.targets if t.region_id==target_id and t.scale=='regional'),None)
        intervals={}
        if matching is not None:
            ranked=rank(dataset,target_id,'regional',preset,include_uncertainty=True)
            intervals={row['id']:row for row in ranked.full_scores}
        for column in ('score_ci_low','score_ci_high','rank_p5','rank_p95','top10_stability'):
            scored[column]=scored['cell_id'].map({rid:row.get(column) for rid,row in intervals.items()})
        for column in ('score_ci_low','score_ci_high'):
            scored[column]=scored[column]/100
        scored['score_ci_low']=np.minimum(scored['score_ci_low'],scored['score'])
        scored['score_ci_high']=np.maximum(scored['score_ci_high'],scored['score'])
        factor=scored.attrs['contextual_factor']
        scored['score_contextual_ci_low']=scored['score_ci_low']*factor
        scored['score_contextual_ci_high']=scored['score_ci_high']*factor
        sigma_tables[alias] = scored.attrs["sigma_table"]
        calibration_tables[alias] = scored.attrs.get("sigma_calibration")
        contextual_factors[alias] = factor
        counts[alias] = {"scored": int(scored.score.notna().sum()),
                         "nan": int(scored.score.isna().sum())}
        if not counts[alias]["scored"]:
            unscorable[alias] = str(scored.excluded_reason.iloc[0]) if len(scored) else "empty grid"
        scored.insert(1, "target_id", alias)
        frames.append(scored)
    combined = pd.concat(frames, ignore_index=True)
    output = Path(out)
    output.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(output / "scores_all.parquet", index=False)
    combined.to_csv(output / "scores_all.csv", index=False, na_rep="")
    manifest = {"data_status": data_status, "inputs_sha256": hashes,
                "input_source": os.getenv('ASTROMATCH_INPUT_SOURCE'),
                "overrides": overrides if not mock else [],
                "engine_version": ENGINE_VERSION, "scale": "regional",
                "preset": preset, "sigma_mode": sigma or "recompute",
                "sigma_table": sigma_tables, "sigma_calibration": calibration_tables, "contextual_factors": contextual_factors, "alias_table": aliases,
                "grid_status": grid_status, "grid_rows": len(grid_df),
                "grid_extent": _grid_extent(grid_df), "grid_label": "regional subset",
                "counts_per_target": counts, "unscorable_targets": unscorable}
    (output / "scores_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest
