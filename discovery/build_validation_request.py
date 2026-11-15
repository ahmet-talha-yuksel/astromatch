"""Build a reproducible request for independent validation samples."""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .analog_mapping import cell_id
from .coverage_check import coverage_center


ROOT = Path(__file__).resolve().parent
ANALOGS_PATH = ROOT / "out" / "known_analogs.json"
COVERAGE_REPORT_PATH = ROOT / "out" / "validation" / "coverage_report.json"
GRID_PATH = ROOT / "data" / "inputs" / "earth_grid.parquet"
COVERAGE_PATH = ROOT / "data" / "inputs" / "coverage.geojson"
OUTPUT_DIR = ROOT / "out" / "validation"
CSV_NAME = "validation_sample_request.csv"
README_NAME = "README_request.md"
SEED = 42
BACKGROUND_COUNT = 1500
CSV_FIELDS = [
    "group", "order", "cell_key", "lat", "lon", "analog_names",
    "in_processed", "in_coverage_not_scanned",
]


def parse_cell_center(key: str) -> tuple[float, float]:
    match = re.fullmatch(r"g_(-?\d{2,3}\.\d{2})_(-?\d{2,3}\.\d{2})", key)
    if not match:
        raise ValueError(f"Unexpected cell_key format: {key!r}")
    return float(match.group(1)), float(match.group(2))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_rows() -> tuple[list[dict[str, Any]], dict[str, int]]:
    import pyarrow.parquet as pq

    analog_data = read_json(ANALOGS_PATH)
    analog_records = analog_data if isinstance(analog_data, list) else analog_data.get("records", [])
    grouped_names: dict[str, list[str]] = {}
    for analog in analog_records:
        key = cell_id(float(analog["lat"]), float(analog["lon"]))
        names = grouped_names.setdefault(key, [])
        name = str(analog["name"])
        if name not in names:
            names.append(name)

    coverage_report = read_json(COVERAGE_REPORT_PATH)
    reported_analog_cells = coverage_report["usgs_analog_coverage"]["analog_cells_by_status"]
    report_processed_analog_keys = set(reported_analog_cells.get("processed", []))
    report_processed_analog_keys.update(reported_analog_cells.get("valid", []))
    report_not_scanned_analog_keys = set(reported_analog_cells.get("not_scanned", []))
    report_analog_keys = set().union(*(set(v) for v in reported_analog_cells.values()))
    if report_analog_keys != set(grouped_names):
        raise ValueError("Coverage report analog cell keys do not match known_analogs.json")

    grid_table = pq.read_table(GRID_PATH)
    grid_rows = grid_table.to_pylist()
    processed_keys = {cell_id(float(row["lat"]), float(row["lon"])) for row in grid_rows}
    report_processed_count = coverage_report["scope"]["processed_cell_count"]
    if len(processed_keys) != report_processed_count:
        raise ValueError(
            f"Grid processed-cell count ({len(processed_keys)}) does not match coverage report "
            f"({report_processed_count})"
        )

    coverage = read_json(COVERAGE_PATH)
    not_scanned_keys: set[str] = set()
    for feature in coverage.get("features", []):
        props = feature.get("properties") or {}
        if props.get("status") == "not_scanned":
            lat, lon = coverage_center(feature)
            not_scanned_keys.add(cell_id(lat, lon))
    if not report_not_scanned_analog_keys.issubset(not_scanned_keys):
        raise ValueError("Coverage report contains analog not_scanned cells missing from coverage.geojson")

    analog_keys = set(grouped_names)
    rows: list[dict[str, Any]] = []
    for key in sorted(grouped_names):
        lat, lon = parse_cell_center(key)
        in_processed = key in processed_keys
        in_not_scanned = key in not_scanned_keys
        if (key in report_processed_analog_keys) != in_processed:
            raise ValueError(f"Coverage report and grid disagree for analog cell {key}")
        if (key in report_not_scanned_analog_keys) != in_not_scanned:
            raise ValueError(f"Coverage report and coverage.geojson disagree for analog cell {key}")
        rows.append({
            "group": "analog",
            "order": "",
            "cell_key": key,
            "lat": lat,
            "lon": lon,
            "analog_names": "; ".join(grouped_names[key]),
            "in_processed": in_processed,
            "in_coverage_not_scanned": in_not_scanned,
        })

    excluded = analog_keys | processed_keys | not_scanned_keys
    eligible_background: list[tuple[str, float, float]] = []
    lat_index = 0
    lat = -59.75
    while lat <= 69.75 + 1e-10:
        lon_index = 0
        lon = -179.75
        while lon <= 179.75 + 1e-10:
            key = cell_id(lat, lon)
            if key not in excluded:
                eligible_background.append((key, lat, lon))
            lon_index += 1
            lon = -179.75 + 0.5 * lon_index
        lat_index += 1
        lat = -59.75 + 0.5 * lat_index

    if len(eligible_background) < BACKGROUND_COUNT:
        raise ValueError(
            f"Not enough eligible background cells: {len(eligible_background)} < {BACKGROUND_COUNT}"
        )
    sampled = random.Random(SEED).sample(eligible_background, BACKGROUND_COUNT)
    for order, (key, lat, lon) in enumerate(sampled, start=1):
        rows.append({
            "group": "background",
            "order": order,
            "cell_key": key,
            "lat": lat,
            "lon": lon,
            "analog_names": "",
            "in_processed": False,
            "in_coverage_not_scanned": False,
        })

    stats = {
        "analog_rows": len(grouped_names),
        "background_rows": BACKGROUND_COUNT,
        "processed_cells": len(processed_keys),
        "coverage_not_scanned_cells": len(not_scanned_keys),
        "eligible_background_cells": len(eligible_background),
    }
    return rows, stats


def output_paths() -> tuple[Path, Path]:
    csv_path = OUTPUT_DIR / CSV_NAME
    readme_path = OUTPUT_DIR / README_NAME
    if not csv_path.exists() and not readme_path.exists():
        return csv_path, readme_path
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = OUTPUT_DIR / f"validation_sample_request_{stamp}.csv"
    readme_path = OUTPUT_DIR / f"README_request_{stamp}.md"
    suffix = 2
    while csv_path.exists() or readme_path.exists():
        csv_path = OUTPUT_DIR / f"validation_sample_request_{stamp}_{suffix}.csv"
        readme_path = OUTPUT_DIR / f"README_request_{stamp}_{suffix}.md"
        suffix += 1
    return csv_path, readme_path


def validate_rows(rows: list[dict[str, Any]]) -> dict[str, int]:
    analogs = [row for row in rows if row["group"] == "analog"]
    background = [row for row in rows if row["group"] == "background"]
    keys = [row["cell_key"] for row in rows]
    assert len(analogs) == 187
    assert len(background) == 1500
    assert len(keys) == len(set(keys))
    assert [row["order"] for row in background] == list(range(1, 1501))
    assert all(not row["in_processed"] for row in background)
    assert all(not row["in_coverage_not_scanned"] for row in background)
    return {"analog_rows": len(analogs), "background_rows": len(background), "unique_cell_keys": len(set(keys))}


def readme_text() -> str:
    return """# Validation sample request

## Why this request is needed

The analog group identifies known analog cells for the independent validation sample. The background group provides a reproducible random set of other cells for the same validation request.

## Selection

- Analog cells are grouped by `cell_key` recomputed from the supplied analog coordinates with `discovery.analog_mapping.cell_id`; names sharing a cell are joined with `; `.
- Background cells are 0.5-degree cell centers between latitudes -60 and 70, sampled without replacement with seed 42.
- Analog cells, the 408 processed cells, and cells marked `not_scanned` in `coverage.geojson` are excluded from background sampling.
- No land/ocean filter is applied. Person 1's `land_fraction` filter is expected to handle ocean cells.
- `order` is 1 through 1500 for the randomized background permutation; analog rows have an empty `order`.

## Expected output from Person 1

For the requested cells, return `earth_grid.parquet` with the same schema, the same 50x50 km window, and the same processing version as the source grid. Preserve `cell_key` so the returned records can be joined to this request.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    rows, stats = build_rows()
    checked = validate_rows(rows)
    repeated_rows, repeated_stats = build_rows()
    assert rows == repeated_rows and stats == repeated_stats

    csv_path, readme_path = output_paths()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in (csv_path, readme_path):
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite existing file: {path}")
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    readme_path.write_text(readme_text(), encoding="utf-8")
    print(f"CSV: {csv_path.relative_to(ROOT)}")
    print(f"README: {readme_path.relative_to(ROOT)}")
    print(f"Counts: {checked}; unique cell_key values: {checked['unique_cell_keys']}")
    print("Reproducibility check: identical output rows on second seeded build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
