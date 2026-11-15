"""Build the known analogs adapter from the cleaned USGS GeoJSON."""

from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from analog_mapping import cell_id


ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "data" / "processed" / "usgs_analogs_clean.geojson"
OUTPUT = ROOT / "out" / "known_analogs.json"


def output_path(force: bool) -> Path:
    if force or not OUTPUT.exists():
        return OUTPUT
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = OUTPUT.with_name(f"{OUTPUT.stem}_{stamp}{OUTPUT.suffix}")
    suffix = 2
    while candidate.exists():
        candidate = OUTPUT.with_name(f"{OUTPUT.stem}_{stamp}_{suffix}{OUTPUT.suffix}")
        suffix += 1
    return candidate


def is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value)) or value == ""


def theme_slug(value: Any) -> list[str]:
    if is_missing(value):
        return []
    slug = re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")
    return [slug] if slug else []


def body_slugs(value: Any) -> list[str]:
    if is_missing(value):
        return []
    body = str(value).strip().lower()
    return [body] if body in {"mars", "moon"} else []


def build() -> tuple[list[dict[str, Any]], dict[str, int]]:
    source = json.loads(INPUT.read_text(encoding="utf-8"))
    features = source.get("features")
    if not isinstance(features, list):
        raise ValueError("Input GeoJSON does not contain a features array")

    records: list[dict[str, Any]] = []
    mismatches = {"latitude": 0, "longitude": 0}
    for index, feature in enumerate(features, start=1):
        properties = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates")
        if geometry.get("type") != "Point" or not isinstance(coordinates, list) or len(coordinates) < 2:
            raise ValueError(f"Feature {index} is not a valid Point")
        lon, lat = float(coordinates[0]), float(coordinates[1])

        for axis, actual, field in (("latitude", lat, "Lat"), ("longitude", lon, "Lon")):
            attribute = properties.get(field)
            if not is_missing(attribute) and abs(actual - float(attribute)) > 0.001:
                mismatches[axis] += 1

        expected_source_id = f"USGS-ANALOG-{index:05d}"
        source_record_id = properties.get("source_record_id")
        if source_record_id != expected_source_id:
            raise ValueError(
                f"Feature order/source_record_id mismatch at {index}: {source_record_id!r}"
            )

        records.append({
            "analog_id": f"usgs_{index:04d}",
            "name": properties.get("Name"),
            "lat": lat,
            "lon": lon,
            "analog_for": body_slugs(properties.get("AnalogBody")),
            "theme": theme_slug(properties.get("AnalogType")),
            "cell_id": cell_id(lat, lon),
            "source": "USGS P9J72921",
        })

    return records, mismatches


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Overwrite discovery/out/known_analogs.json")
    args = parser.parse_args()

    records, mismatches = build()
    destination = output_path(args.force)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(records)} records to {destination.relative_to(ROOT)}")
    print(
        "Coordinate attribute differences > 0.001 degrees: "
        f"latitude={mismatches['latitude']}, longitude={mismatches['longitude']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
