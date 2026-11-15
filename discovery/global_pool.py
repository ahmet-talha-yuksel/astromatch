"""Build an approximate, coordinate-only global land-cell pool."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from global_land_mask import globe

from .analog_mapping import cell_id
from .coverage_check import coverage_center
from .grid_utils import parse_cell_id


ROOT = Path(__file__).resolve().parent
GRID_PATH = ROOT / "data" / "inputs" / "earth_grid.parquet"
VALIDATION_GRID_PATH = ROOT / "data" / "inputs" / "earth_grid_validation.parquet"
COVERAGE_PATH = ROOT / "data" / "inputs" / "coverage.geojson"
ANALOGS_PATH = ROOT / "out" / "known_analogs.json"
TURKEY_PATH = ROOT / "out" / "turkey_analogs.json"
OUTPUT_PATH = ROOT / "out" / "global_pool.parquet"
STEP = 0.5
LAND_THRESHOLD = 0.5
SUBCELL_OFFSETS = np.array([-0.2, -0.1, 0.0, 0.1, 0.2], dtype=float)


def land_fraction_5x5(lat: float, lon: float) -> float:
    """Return the approximate land fraction for the containing 0.5-degree cell."""
    center_lat, center_lon = parse_cell_id(cell_id(float(lat), float(lon)))
    lat_samples, lon_samples = np.meshgrid(
        center_lat + SUBCELL_OFFSETS,
        center_lon + SUBCELL_OFFSETS,
        indexing="ij",
    )
    return float(np.asarray(globe.is_land(lat_samples.ravel(), lon_samples.ravel())).mean())


def include_land_cell(lat: float, lon: float) -> bool:
    return land_fraction_5x5(lat, lon) >= LAND_THRESHOLD


def scan_status(key: str, processed_sources: dict[str, str], coverage_by_key: dict[str, dict]) -> tuple[str, str]:
    if key in processed_sources:
        return "scanned", processed_sources[key]
    if coverage_by_key.get(key, {}).get("status") == "not_scanned":
        return "not_scanned", "none"
    return "out_of_coverage", "none"


def _coverage_index(grid_paths: list[Path]) -> tuple[dict[str, str], dict[str, dict]]:
    for path in grid_paths:
        if not path.is_file():
            raise FileNotFoundError(f"Grid not found: {path}")
    if not COVERAGE_PATH.is_file():
        raise FileNotFoundError(f"Coverage GeoJSON not found: {COVERAGE_PATH}")
    processed_sources: dict[str, str] = {}
    for path, source in zip(grid_paths, ("pilot", "validation_sample"), strict=False):
        grid = pq.read_table(path, columns=["lat", "lon"]).to_pylist()
        for row in grid:
            processed_sources.setdefault(cell_id(float(row["lat"]), float(row["lon"])), source)
    coverage_data = json.loads(COVERAGE_PATH.read_text(encoding="utf-8"))
    coverage_by_key = {}
    for feature in coverage_data.get("features", []):
        props = feature.get("properties") or {}
        lat, lon = coverage_center(feature)
        key = cell_id(float(lat), float(lon))
        if key in coverage_by_key:
            raise ValueError(f"Duplicate cell in coverage GeoJSON: {key}")
        coverage_by_key[key] = props
    return processed_sources, coverage_by_key


def _known_analog_index() -> tuple[dict[str, int], set[str]]:
    if not ANALOGS_PATH.is_file():
        raise FileNotFoundError(f"Known analog file not found: {ANALOGS_PATH}")
    records = json.loads(ANALOGS_PATH.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("known_analogs.json must be a JSON list")
    counts: Counter[str] = Counter()
    for record in records:
        key = cell_id(float(record["lat"]), float(record["lon"]))
        counts[key] += 1
    return dict(counts), set(counts)


def _turkey_index() -> dict[str, list[str]]:
    if not TURKEY_PATH.is_file():
        raise FileNotFoundError(f"Turkey analog file not found: {TURKEY_PATH}")
    payload = json.loads(TURKEY_PATH.read_text(encoding="utf-8"))
    result: dict[str, list[str]] = defaultdict(list)
    for record in payload.get("records", []):
        key = cell_id(float(record["lat"]), float(record["lon"]))
        result[key].append(str(record["region_id"]))
    return dict(result)


def build_pool(grid_paths: list[Path] | None = None) -> tuple[pd.DataFrame, dict]:
    grid_paths = grid_paths or [GRID_PATH, VALIDATION_GRID_PATH]
    processed_sources, coverage_by_key = _coverage_index(grid_paths)
    analog_counts, analog_keys = _known_analog_index()
    turkey_by_key = _turkey_index()
    pilot_rows = pq.read_table(GRID_PATH, columns=["lat", "lon", "land_fraction"]).to_pylist()
    pilot_land = {
        cell_id(float(row["lat"]), float(row["lon"])): float(row["land_fraction"])
        for row in pilot_rows if row["land_fraction"] is not None
    }

    latitude_centers = np.arange(-89.75, 90.0, STEP)
    longitude_centers = np.arange(-179.75, 180.0, STEP)
    rows = []
    pilot_estimates: dict[str, float] = {}
    status_counts: Counter[str] = Counter()
    land_cells = 0

    for lat_center in latitude_centers:
        lat_values = np.broadcast_to(
            (lat_center + SUBCELL_OFFSETS)[:, None, None],
            (5, len(longitude_centers), 5),
        )
        lon_values = np.broadcast_to(
            (longitude_centers[None, :, None] + SUBCELL_OFFSETS[None, None, :]),
            (5, len(longitude_centers), 5),
        )
        fractions = np.asarray(globe.is_land(lat_values, lon_values), dtype=bool).mean(axis=(0, 2))
        for lon_center, fraction in zip(longitude_centers, fractions, strict=True):
            key = cell_id(float(lat_center), float(lon_center))
            fraction = float(fraction)
            if key in pilot_land:
                pilot_estimates[key] = fraction
            if fraction < LAND_THRESHOLD:
                continue
            land_cells += 1
            status, scan_source = scan_status(key, processed_sources, coverage_by_key)
            status_counts[status] += 1
            rows.append({
                "cell_key": key,
                "lat": float(lat_center),
                "lon": float(lon_center),
                "land_fraction": fraction,
                "scan_status": status,
                "scan_source": scan_source,
                "usgs_analog_count": int(analog_counts.get(key, 0)),
                "turkey_region_ids": turkey_by_key.get(key, []),
            })

    if len(pilot_estimates) != len(pilot_land):
        missing = sorted(set(pilot_land) - set(pilot_estimates))
        raise ValueError(f"Could not sample all pilot cells for land_fraction comparison: {missing[:5]}")
    differences = [abs(pilot_estimates[key] - real) for key, real in pilot_land.items()]
    frame = pd.DataFrame(rows, columns=[
        "cell_key", "lat", "lon", "land_fraction", "scan_status", "scan_source",
        "usgs_analog_count", "turkey_region_ids",
    ])
    report = {
        "total_cell_centers": int(len(latitude_centers) * len(longitude_centers)),
        "land_cells_retained": land_cells,
        "scan_status_counts": {name: int(status_counts.get(name, 0)) for name in ("scanned", "not_scanned", "out_of_coverage")},
        "scan_source_counts": {name: sum(1 for row in rows if row["scan_source"] == name) for name in ("pilot", "validation_sample", "none")},
        "known_analog_unique_cells": len(analog_keys),
        "known_analog_cells_in_pool": len(analog_keys.intersection({row["cell_key"] for row in rows})),
        "known_analog_cells_scanned": len(analog_keys.intersection({row["cell_key"] for row in rows if row["scan_status"] == "scanned"})),
        "pilot_land_fraction_rows": len(pilot_rows),
        "pilot_land_fraction_available": len(pilot_land),
        "pilot_land_fraction_missing": len(pilot_rows) - len(pilot_land),
        "pilot_land_fraction_comparison_count": len(differences),
        "pilot_land_fraction_mean_absolute_difference": float(np.mean(differences)),
    }
    return frame, report


def write_pool(output_path: Path = OUTPUT_PATH, *, grid_paths: list[Path] | None = None, force: bool = False) -> dict:
    if output_path.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite existing global pool: {output_path}")
    frame, report = build_pool(grid_paths)
    table = pa.Table.from_pandas(frame, preserve_index=False)
    metadata = dict(table.schema.metadata or {})
    metadata.update({
        b"description": b"Coordinate-only global 0.5-degree land-cell pool; contains no terrain features or scores.",
        b"land_fraction_method": b"Approximate 5x5 point sampling using global-land-mask; cells retained at land_fraction >= 0.5.",
        b"generated_at_utc": datetime.now(timezone.utc).isoformat().encode("ascii"),
        b"scope": json.dumps(report, sort_keys=True).encode("utf-8"),
    })
    table = table.replace_schema_metadata(metadata)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, output_path, compression="zstd")
    return report


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", nargs="+", type=Path, default=[GRID_PATH, VALIDATION_GRID_PATH])
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    report = write_pool(grid_paths=args.grid, force=args.force)
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"Wrote {OUTPUT_PATH.relative_to(ROOT)} ({OUTPUT_PATH.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
