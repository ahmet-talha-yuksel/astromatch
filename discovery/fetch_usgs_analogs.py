#!/usr/bin/env python3
"""
Download and normalize the USGS Known Terrestrial Analog Sites dataset.

Source DOI: https://doi.org/10.5066/P9J72921
ScienceBase item: 5f88940b82cebb8c13d912ee

Outputs:
  data/raw/usgs_analogs_source.zip
  data/raw/                  extracted source files
  data/processed/usgs_analogs_clean.geojson
  data/processed/usgs_analogs_clean.csv
  data/processed/cleaning_report.json

The source payload is downloaded from ScienceBase's documented item-file endpoint.
No analog labels or planetary target assignments are invented. Original attributes
are retained; normalized fields are added only when a source field can be mapped.
"""

from __future__ import annotations

import json
import argparse
import hashlib
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import geopandas as gpd
import pandas as pd
import requests

DOI = "10.5066/P9J72921"
ITEM_ID = "5f88940b82cebb8c13d912ee"
ITEM_API = f"https://www.sciencebase.gov/catalog/item/{ITEM_ID}?format=json"
DOWNLOAD_ALL = f"https://www.sciencebase.gov/catalog/file/get/{ITEM_ID}"

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
EXTRACTED = RAW / "extracted"
PROCESSED = ROOT / "data" / "processed"
ZIP_PATH = RAW / "usgs_analogs_source.zip"

# Candidate source-field names; mappings are conservative and case-insensitive.
ALIASES = {
    "name": ["name", "site_name", "sitename", "analog_name", "location", "locality"],
    "description": ["description", "comments", "notes", "summary", "site_desc"],
    "analog_type": ["analog_type", "type", "feature", "landform", "geology", "process"],
    "target_body": ["target_body", "planet", "planetary_body", "body", "target"],
    "country": ["country", "nation", "admin", "country_name"],
    "latitude": ["latitude", "lat", "ycoord", "y_coord"],
    "longitude": ["longitude", "lon", "long", "xcoord", "x_coord"],
}

def log(message: str) -> None:
    print(f"[AstroMatch USGS] {message}")

def safe_extract(zip_file: Path, destination: Path) -> None:
    """Extract without allowing paths to escape destination."""
    destination_resolved = destination.resolve()
    with zipfile.ZipFile(zip_file) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if destination_resolved not in target.parents and target != destination_resolved:
                raise RuntimeError(f"Unsafe path in source archive: {member.filename}")
        archive.extractall(destination)

def get_source() -> dict[str, Any]:
    RAW.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "AstroMatchAI/1.0 (research data preparation)"}

    log("Reading ScienceBase item metadata...")
    response = requests.get(ITEM_API, headers=headers, timeout=60)
    response.raise_for_status()
    metadata = response.json()

    log("Downloading all files attached to the USGS item...")
    data = requests.get(DOWNLOAD_ALL, headers=headers, timeout=180, stream=True)
    data.raise_for_status()
    content_type = data.headers.get("Content-Type", "").lower()
    first = next(data.iter_content(chunk_size=8192), b"")
    if not first:
        raise RuntimeError("ScienceBase returned an empty download.")
    with ZIP_PATH.open("wb") as output:
        output.write(first)
        for chunk in data.iter_content(chunk_size=1024 * 1024):
            if chunk:
                output.write(chunk)

    if not zipfile.is_zipfile(ZIP_PATH):
        preview = ZIP_PATH.read_bytes()[:500].decode("utf-8", errors="replace")
        ZIP_PATH.unlink(missing_ok=True)
        raise RuntimeError(
            "ScienceBase response was not a ZIP archive. "
            f"Content-Type={content_type!r}; response preview={preview!r}"
        )

    EXTRACTED.mkdir(parents=True, exist_ok=True)
    safe_extract(ZIP_PATH, EXTRACTED)
    return metadata

def normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")

def map_source_fields(frame: gpd.GeoDataFrame) -> dict[str, str]:
    by_normalized = {normalize_key(col): col for col in frame.columns}
    mapping = {}
    for standard, candidates in ALIASES.items():
        for candidate in candidates:
            if normalize_key(candidate) in by_normalized:
                mapping[standard] = by_normalized[normalize_key(candidate)]
                break
    return mapping

def read_vector_candidates() -> list[Path]:
    allowed = {".shp", ".geojson", ".json", ".gpkg", ".kml", ".gml"}
    return sorted(p for p in EXTRACTED.rglob("*") if p.is_file() and p.suffix.lower() in allowed)

def read_tabular_candidates() -> list[Path]:
    return sorted(p for p in EXTRACTED.rglob("*") if p.is_file() and p.suffix.lower() in {".csv", ".tsv"})

def clean_geometry(frame: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, dict[str, Any]]:
    report: dict[str, Any] = {
        "input_features": int(len(frame)),
        "input_crs": str(frame.crs) if frame.crs else None,
        "null_geometry_removed": 0,
        "empty_geometry_removed": 0,
        "invalid_geometry_repaired": 0,
        "invalid_geometry_removed": 0,
        "duplicate_geometry_removed": 0,
        "coordinate_outliers_removed": 0,
    }

    frame = frame.copy()
    null_mask = frame.geometry.isna()
    report["null_geometry_removed"] = int(null_mask.sum())
    frame = frame.loc[~null_mask].copy()

    empty_mask = frame.geometry.is_empty
    report["empty_geometry_removed"] = int(empty_mask.sum())
    frame = frame.loc[~empty_mask].copy()

    invalid_mask = ~frame.geometry.is_valid
    if invalid_mask.any():
        # buffer(0) is a common repair for simple invalid polygon geometries.
        # For point layers it is effectively a no-op; unrepaired invalids are dropped.
        before_wkb = frame.loc[invalid_mask].geometry.to_wkb()
        try:
            repaired = frame.loc[invalid_mask].geometry.make_valid()
            frame.loc[invalid_mask, "geometry"] = repaired
            after_wkb = frame.loc[invalid_mask].geometry.to_wkb()
            report["invalid_geometry_repaired"] = int(
                (before_wkb.to_numpy() != after_wkb.to_numpy()).sum()
            )
        except Exception:
            pass
        still_invalid = ~frame.geometry.is_valid
        report["invalid_geometry_removed"] = int(still_invalid.sum())
        frame = frame.loc[~still_invalid].copy()

    if frame.crs is None:
        raise RuntimeError(
            "The source vector has no CRS. Refusing to guess coordinates; "
            "inspect the original metadata and assign the documented CRS."
        )

    frame = frame.to_crs("EPSG:4326")

    # This release is described as a point layer. Preserve geometry types and
    # remove only geometries whose WGS84 bounds are impossible.
    bounds = frame.geometry.bounds
    valid_bounds = (
        bounds["minx"].between(-180, 180)
        & bounds["maxx"].between(-180, 180)
        & bounds["miny"].between(-90, 90)
        & bounds["maxy"].between(-90, 90)
    )
    report["coordinate_outliers_removed"] = int((~valid_bounds).sum())
    frame = frame.loc[valid_bounds].copy()

    before = len(frame)
    frame = frame.loc[~frame.geometry.to_wkb().duplicated()].copy()
    report["duplicate_geometry_removed"] = int(before - len(frame))

    return frame, report

def add_normalized_fields(frame: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, dict[str, str]]:
    mapping = map_source_fields(frame)
    out = frame.copy()

    for standard in ("name", "description", "analog_type", "target_body", "country"):
        source_col = mapping.get(standard)
        if source_col and standard not in out.columns:
            out[standard] = out[source_col]

    if "latitude" in mapping and "latitude" not in out.columns:
        out["latitude"] = pd.to_numeric(out[mapping["latitude"]], errors="coerce")
    if "longitude" in mapping and "longitude" not in out.columns:
        out["longitude"] = pd.to_numeric(out[mapping["longitude"]], errors="coerce")

    # Geometry is authoritative for coordinates. This avoids silently trusting
    # stale or incorrectly named attribute columns.
    if out.geometry.geom_type.eq("Point").all():
        out["longitude"] = out.geometry.x
        out["latitude"] = out.geometry.y

    if "name" not in out.columns:
        out["name"] = pd.NA
    if "analog_type" not in out.columns:
        out["analog_type"] = pd.NA
    if "target_body" not in out.columns:
        out["target_body"] = pd.NA

    def unique_column(base: str) -> str:
        candidate = base
        suffix = 2
        while candidate in out.columns:
            candidate = f"{base}_{suffix}"
            suffix += 1
        return candidate

    additions = [
        ("astromatch_source", "USGS Known Terrestrial Analog Sites"),
        ("source_doi", DOI),
        ("source_item_id", ITEM_ID),
        ("source_record_id", [f"USGS-ANALOG-{i:05d}" for i in range(1, len(out) + 1)]),
    ]
    for base, values in additions:
        out.insert(0, unique_column(base), values)
    return out, mapping

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Read an existing source file instead of downloading")
    parser.add_argument("--force", action="store_true", help="Overwrite the standard output files")
    return parser.parse_args()

def unused_output_path(path: Path, force: bool) -> Path:
    if force or not path.exists() or path.stat().st_size == 0:
        return path
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = path.with_name(f"{path.stem}_{stamp}{path.suffix}")
    counter = 2
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}_{stamp}_{counter}{path.suffix}")
        counter += 1
    return candidate

def main() -> int:
    args = parse_args()
    PROCESSED.mkdir(parents=True, exist_ok=True)
    metadata: dict[str, Any] = {}
    if args.input:
        input_path = args.input.resolve()
        raw_root = RAW.resolve()
        if raw_root not in input_path.parents or not input_path.is_file():
            raise RuntimeError(f"--input must be an existing file inside {RAW}")
        source_candidates = [input_path]
        if input_path.suffix.lower() == ".zip":
            EXTRACTED.mkdir(parents=True, exist_ok=True)
            safe_extract(input_path, EXTRACTED)
            source_candidates = list(EXTRACTED.rglob("*"))
    else:
        metadata = get_source()
        source_candidates = list(EXTRACTED.rglob("*"))

    if not metadata.get("title"):
        for metadata_file in sorted(RAW.rglob("*.xml")):
            try:
                xml_root = ET.parse(metadata_file).getroot()
                title = next((node.text.strip() for node in xml_root.iter()
                              if node.tag.rsplit("}", 1)[-1].lower() == "title" and node.text and node.text.strip()), None)
                if title:
                    metadata["title"] = title
                    break
            except (ET.ParseError, OSError):
                continue

    vector_ext = {".shp", ".geojson", ".json", ".gpkg", ".kml", ".gml"}
    tabular_ext = {".csv", ".tsv"}
    vector_files = sorted(p for p in source_candidates if p.is_file() and p.suffix.lower() in vector_ext)
    tabular_files = sorted(p for p in source_candidates if p.is_file() and p.suffix.lower() in tabular_ext)
    if not vector_files:
        raise RuntimeError(f"No vector GIS file found. Tabular files: {[p.name for p in tabular_files]}")

    # Prefer GeoPackage/GeoJSON/Shapefile, then other supported vector formats.
    priority = {".gpkg": 0, ".geojson": 1, ".json": 2, ".shp": 3, ".kml": 4, ".gml": 5}
    vector_files.sort(key=lambda p: (priority.get(p.suffix.lower(), 99), str(p)))
    source_vector = vector_files[0]
    log(f"Reading vector source: {source_vector.relative_to(ROOT)}")

    source = gpd.read_file(source_vector)
    cleaned, geometry_report = clean_geometry(source)
    cleaned, field_mapping = add_normalized_fields(cleaned)

    if cleaned.empty:
        raise RuntimeError("No records remain after geometry validation.")

    geojson_path = unused_output_path(PROCESSED / "usgs_analogs_clean.geojson", args.force)
    csv_path = unused_output_path(PROCESSED / "usgs_analogs_clean.csv", args.force)
    cleaned.to_file(geojson_path, driver="GeoJSON", encoding="UTF-8")

    table = pd.DataFrame(cleaned.drop(columns="geometry"))
    table.to_csv(csv_path, index=False, encoding="utf-8-sig")

    source_hashes = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(RAW.rglob("*")) if path.is_file()
    }
    output_hashes = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (geojson_path, csv_path)
    }
    report = {
        "dataset": "Known Terrestrial Analog Sites for Planetary Science",
        "publisher": "U.S. Geological Survey, Astrogeology Science Center",
        "author": "Marc A. Hunter",
        "doi": DOI,
        "source_url": f"https://doi.org/{DOI}",
        "sciencebase_item_id": ITEM_ID,
        "license": "CC0 1.0 Universal (as marked on the USGS data release page)",
        "accessed_utc": datetime.now(timezone.utc).isoformat(),
        "source_vector_file": str(source_vector.relative_to(ROOT)),
        "source_vector_files_found": [str(p.relative_to(ROOT)) for p in vector_files],
        "tabular_files_found": [str(p.relative_to(ROOT)) for p in tabular_files],
        "source_crs": geometry_report["input_crs"],
        "output_crs": "EPSG:4326",
        "source_fields": [str(c) for c in source.columns],
        "normalized_field_mapping": field_mapping,
        "geometry_validation": geometry_report,
        "record_counts": {
            "before": geometry_report["input_features"],
            "after": int(len(cleaned)),
        },
        "output_features": int(len(cleaned)),
        "geometry_types": {str(k): int(v) for k, v in cleaned.geometry.geom_type.value_counts().items()},
        "output_files": [str(geojson_path.relative_to(ROOT)), str(csv_path.relative_to(ROOT))],
        "sha256": {"source_files": source_hashes, "output_files": output_hashes},
        "limitations": [
            "No missing analog type, planetary target, or site name has been inferred.",
            "Original source attributes are retained.",
            "Coordinates are taken from the geometry after reprojection to EPSG:4326.",
            "The source is a known-sites reference layer, not a complete global candidate grid.",
            "This script does not assign Salda, Kula, Meke/Acıgöl, Hassa, or Tuz Gölü to USGS records."
        ],
        "sciencebase_item_title": metadata.get("title"),
    }
    report_path = unused_output_path(PROCESSED / "cleaning_report.json", args.force)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    log(f"Finished: {len(cleaned)} features")
    log(f"GeoJSON: {geojson_path}")
    log(f"CSV: {csv_path}")
    log(f"Report: {report_path}")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except requests.HTTPError as exc:
        log(f"HTTP error while accessing USGS ScienceBase: {exc}")
        log("Try again later or download the source ZIP manually from the DOI landing page.")
        raise SystemExit(2)
    except Exception as exc:
        log(f"FAILED: {exc}")
        raise SystemExit(1)
