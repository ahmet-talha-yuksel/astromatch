"""Compare USGS and Turkish analog cells with the supplied discovery coverage."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from .analog_mapping import cell_id


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "out" / "validation" / "coverage_report.json"
SCORING_FEATURES = (
    "slope_median_deg", "slope_p90_deg", "flat_fraction", "tri_median_m",
    "relief_m", "elevation_std_m",
)


def destination_path() -> Path:
    if not OUTPUT.exists():
        return OUTPUT
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = OUTPUT.with_name(f"{OUTPUT.stem}_{stamp}{OUTPUT.suffix}")
    suffix = 2
    while candidate.exists():
        candidate = OUTPUT.with_name(f"{OUTPUT.stem}_{stamp}_{suffix}{OUTPUT.suffix}")
        suffix += 1
    return candidate


def coverage_center(feature: dict[str, Any]) -> tuple[float, float]:
    geometry = feature.get("geometry") or {}
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates") or []
    rings: list[list[list[float]]] = []
    if kind == "Polygon":
        rings = coordinates[:1]
    elif kind == "MultiPolygon":
        rings = [polygon[0] for polygon in coordinates if polygon]
    else:
        raise ValueError(f"Coverage geometry must be a polygon, got {kind!r}")
    points = [point for ring in rings for point in ring]
    if not points:
        raise ValueError("Coverage polygon has no coordinates")
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    # Coverage cells are axis-aligned 0.5-degree grid polygons; their bbox midpoint
    # is the cell center used for coordinate-key matching.
    return (min(ys) + max(ys)) / 2, (min(xs) + max(xs)) / 2


def classify(key: str, coverage: dict[str, dict[str, Any]]) -> str:
    row = coverage.get(key)
    if row is None:
        return "out_of_scope"
    if row.get("status") == "scanned" and row.get("comparable") is True:
        return "valid"
    if row.get("status") == "scanned":
        return "processed"
    if row.get("status") == "not_scanned":
        return "not_scanned"
    return str(row.get("status") or "unknown")


def point_summary(name: str, lat: float, lon: float, coverage: dict[str, dict[str, Any]]) -> dict[str, Any]:
    key = cell_id(lat, lon)
    return {"name": name, "lat": lat, "lon": lon, "cell_id": key, "status": classify(key, coverage)}


def read_analogs(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else data.get("records", [])


def source_scope(source_path: Path, grid_rows: list[dict[str, Any]], valid: int) -> dict[str, Any]:
    values = {}
    for line in source_path.read_text(encoding="utf-8").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    latitudes = [float(row["lat"]) for row in grid_rows]
    longitudes = [float(row["lon"]) for row in grid_rows]
    bins: Counter[tuple[int, int]] = Counter(
        (math.floor(lat / 5) * 5, math.floor(lon / 5) * 5)
        for lat, lon in zip(latitudes, longitudes)
    )
    top_bins = sorted(bins.items(), key=lambda item: (-item[1], item[0]))[:10]
    return {
        "processed_cell_count": len({cell_id(float(row["lat"]), float(row["lon"])) for row in grid_rows}),
        "valid_cell_count": valid,
        "is_global": False,
        "latitude_range": [min(latitudes), max(latitudes)],
        "longitude_range": [min(longitudes), max(longitudes)],
        "five_degree_bins_top_10": [
            {"lat_min": lat0, "lat_max": lat0 + 5, "lon_min": lon0,
             "lon_max": lon0 + 5, "cell_count": count}
            for (lat0, lon0), count in top_bins
        ],
        "note": "Kapsam küresel değildir; sonuçlar yalnızca işlenmiş hücreler için geçerlidir.",
        "source_branch": values.get("Source branch"),
        "source_commit": values.get("Source commit"),
    }


def build_report(grid_path: Path, coverage_path: Path, analogs_path: Path, turkey_path: Path) -> dict[str, Any]:
    table = pq.read_table(grid_path)
    grid_rows = table.to_pylist()
    grid_by_key: dict[str, dict[str, Any]] = {}
    for row in grid_rows:
        key = cell_id(float(row["lat"]), float(row["lon"]))
        if key in grid_by_key:
            raise ValueError(f"Duplicate coordinate cell_key in grid: {key}")
        grid_by_key[key] = row

    coverage_data = json.loads(coverage_path.read_text(encoding="utf-8"))
    coverage_by_key: dict[str, dict[str, Any]] = {}
    status_counts: Counter[str] = Counter()
    comparable_counts: Counter[str] = Counter()
    for feature in coverage_data.get("features", []):
        lat, lon = coverage_center(feature)
        key = cell_id(lat, lon)
        props = feature.get("properties") or {}
        if key in coverage_by_key:
            raise ValueError(f"Duplicate coordinate cell_key in coverage: {key}")
        coverage_by_key[key] = props
        status_counts[str(props.get("status") or "null")] += 1
        comparable_counts[str(props.get("comparable"))] += 1

    processed_keys = set(grid_by_key)
    valid_keys = {
        key for key, props in coverage_by_key.items()
        if props.get("status") == "scanned" and props.get("comparable") is True
    }
    scanned_keys = {
        key for key, props in coverage_by_key.items()
        if props.get("status") == "scanned"
    }
    not_scanned_keys = {
        key for key, props in coverage_by_key.items()
        if props.get("status") == "not_scanned"
    }
    if processed_keys != scanned_keys:
        raise ValueError(
            "Grid rows and coverage scanned cells do not match by coordinate cell_key "
            f"(grid={len(processed_keys)}, scanned={len(scanned_keys)})"
        )

    analogs = read_analogs(analogs_path)
    analogs_by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for analog in analogs:
        key = cell_id(float(analog["lat"]), float(analog["lon"]))
        analogs_by_key[key].append({"name": analog.get("name"), "cell_id": key})
    analog_cell_status = {key: classify(key, coverage_by_key) for key in analogs_by_key}
    analog_counts = Counter(analog_cell_status.values())
    contained_analogs = [
        item for key, items in analogs_by_key.items()
        if analog_cell_status[key] in {"valid", "processed"}
        for item in items
    ]
    analog_status_report = {
        "distinct_usgs_cells": len(analogs_by_key),
        "distinct_cells_by_status": {
            status: analog_counts.get(status, 0)
            for status in ("processed", "valid", "not_scanned", "out_of_scope")
        },
        "analogs_in_processed_cells": contained_analogs,
        "analog_cells_by_status": {
            status: [key for key, state in sorted(analog_cell_status.items()) if state == status]
            for status in ("processed", "valid", "not_scanned", "out_of_scope")
        },
    }

    turkey_data = json.loads(turkey_path.read_text(encoding="utf-8"))
    turkey_rows = turkey_data if isinstance(turkey_data, list) else turkey_data.get("records", [])
    turkey_status = [
        point_summary(row["name"], float(row["lat"]), float(row["lon"]), coverage_by_key)
        | {"region_id": row.get("region_id")}
        for row in turkey_rows
    ]
    controls = [
        point_summary("Meteor Crater", 35.03, -111.02, coverage_by_key),
        point_summary("Haughton", 75.4, -89.7, coverage_by_key),
        point_summary("Atacama", -24.1, -70.0, coverage_by_key),
    ]

    lats = [float(row["lat"]) for row in grid_rows]
    lons = [float(row["lon"]) for row in grid_rows]
    bins: Counter[tuple[int, int]] = Counter()
    for lat, lon in zip(lats, lons):
        bins[(math.floor(lat / 5) * 5, math.floor(lon / 5) * 5)] += 1
    top_bins = sorted(bins.items(), key=lambda item: (-item[1], item[0]))[:10]

    source_file = grid_path.parent / "SOURCE.txt"
    valid_count = len(valid_keys)
    return {
        "generated_at": datetime.now(timezone(timedelta(hours=3))).isoformat(timespec="seconds"),
        "scope": source_scope(source_file, grid_rows, valid_count),
        "grid_cell_count": len(grid_rows),
        "coverage_feature_count": len(coverage_by_key),
        "coverage_status_counts": dict(status_counts),
        "coverage_comparable_counts": dict(comparable_counts),
        "usgs_analog_coverage": analog_status_report,
        "turkey_sites": turkey_status,
        "control_sites": controls,
        "processed_cell_distribution": {
            "latitude_range": [min(lats), max(lats)],
            "longitude_range": [min(lons), max(lons)],
            "five_degree_bins_top_10": [
                {"lat_min": lat0, "lat_max": lat0 + 5, "lon_min": lon0,
                 "lon_max": lon0 + 5, "cell_count": count}
                for (lat0, lon0), count in top_bins
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", type=Path, required=True)
    parser.add_argument("--coverage", type=Path, required=True)
    parser.add_argument("--analogs", type=Path, required=True)
    parser.add_argument("--turkey", type=Path, required=True)
    args = parser.parse_args()

    report = build_report(args.grid, args.coverage, args.analogs, args.turkey)
    output = destination_path()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output.relative_to(ROOT)}")
    print(json.dumps({
        "scope": report["scope"],
        "usgs_analog_coverage": report["usgs_analog_coverage"]["distinct_cells_by_status"],
        "turkey_sites": report["turkey_sites"],
        "control_sites": report["control_sites"],
        "processed_cell_distribution": report["processed_cell_distribution"],
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
