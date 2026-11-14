"""Long-format validation score export."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pandas as pd

from .io import ROOT, feature_paths, merged_features
from .validation_api import _score_grid, list_target_ids


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
    frames = []
    sigma_tables = {}
    counts = {}
    unscorable = {}
    for alias in active:
        scored = _score_grid(grid_df, alias, preset, sigma=sigma, scale="regional",
                             return_criteria=criteria, target_records=targets)
        sigma_tables[alias] = scored.attrs["sigma_table"]
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
                "sigma_table": sigma_tables, "alias_table": aliases,
                "grid_status": grid_status, "grid_rows": len(grid_df),
                "counts_per_target": counts, "unscorable_targets": unscorable}
    (output / "scores_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest
