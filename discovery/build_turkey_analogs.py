"""Build qualitative Turkish analog hypotheses from the supplied field data."""

from __future__ import annotations

import argparse
import json
import warnings
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .analog_mapping import cell_id
from .coverage_check import coverage_center

import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "out" / "turkey_analogs.json"
FEATURES_PATH = ROOT / "data" / "inputs" / "features.json"
GRID_PATH = ROOT / "data" / "inputs" / "earth_grid.parquet"
COVERAGE_PATH = ROOT / "data" / "inputs" / "coverage.geojson"
COVERAGE_REPORT_PATH = ROOT / "out" / "validation" / "coverage_report.json"
SOURCE_PATH = ROOT / "data" / "inputs" / "SOURCE.txt"

FEATURE_SITE_PREFIXES = {
    "E-TR-01": "earth_salda",
    "E-TR-02": "earth_kula",
    "E-TR-03": "earth_meke",
    "E-TR-04": None,
    "E-TR-05": "earth_hassa",
    "E-TR-06": "earth_tuz_golu",
}
SCORING_FEATURES = (
    "slope_median_deg", "slope_p90_deg", "flat_fraction", "tri_median_m",
    "relief_m", "elevation_std_m",
)

COMMON_LIMITATION = "Koordinat yaklaşıktır, DEM'e bakarak merkez teyit edilecek."
MEKE_ACIGOL_LIMITATION = "Global 0.5° ızgarada aynı hücreye düşer (shares_cell_with)."


def candidate(target_id: str, basis: str, rationale: str) -> dict[str, str]:
    return {"target_id": target_id, "rationale": rationale, "basis": basis}


def source_rows() -> list[dict]:
    rows = [
        {
            "region_id": "E-TR-01", "name": "Salda Gölü", "role": "turkey_candidate_and_reference",
            "lat": 37.55, "lon": 29.68, "tags": ["lake", "paleolake", "carbonate"],
            "analog_dimensions": ["karbonat", "paleo-göl"],
            "candidate_targets": [candidate(
                "T-01", "ekip_raporu_v2",
                "Jezero'da paleo-göl ve karbonat var; Salda karbonat ve göl ortamıdır. "
                "Ekip raporunda Jezero ile ilişkisi bilinen referans/doğrulama sahası olarak geçer. "
                "Literatür kaynağı teyit edilecek.",
            )],
        },
        {
            "region_id": "E-TR-02", "name": "Kula Volkanik Alanı", "role": "turkey_candidate",
            "lat": 38.6, "lon": 28.6, "tags": ["volcanic_field", "basaltic_cones", "lava_flows"],
            "analog_dimensions": ["genç bazaltik koniler", "lav akıntıları"],
            "candidate_targets": [
                candidate(
                    "T-03", "hipotez",
                    "Marius Hills volkanik dom alanıdır; Kula'da koni ve lav akıntısı yapıları var. "
                    "Yapı sınıfı düzeyinde nitel benzerlik, nicel doğrulama bekliyor.",
                ),
                candidate(
                    "T-04", "hipotez",
                    "Opsiyonel Tharsis volkanik ovası ile volkanik arazi sınıfı benzerliği; T-04 opsiyonel hedef.",
                ),
            ],
        },
        {
            "region_id": "E-TR-03", "name": "Meke Gölü maarı", "role": "turkey_candidate",
            "lat": 37.68, "lon": 33.64, "tags": ["maar", "explosion_crater", "lake"],
            "analog_dimensions": ["su-magma etkileşimli patlama krateri"],
            "candidate_targets": [candidate(
                "T-03", "hipotez",
                "Volkanik krater morfolojisi düzeyinde zayıf nitel benzerlik; nicel sonuca bırakıldı.",
            )],
        },
        {
            "region_id": "E-TR-04", "name": "Acıgöl maarı (Karapınar)", "role": "turkey_candidate",
            "lat": 37.7, "lon": 33.7, "tags": ["maar", "explosion_crater"],
            "analog_dimensions": ["su-magma etkileşimli patlama krateri"],
            "candidate_targets": [candidate(
                "T-03", "hipotez",
                "Volkanik krater morfolojisi düzeyinde zayıf nitel benzerlik; nicel sonuca bırakıldı.",
            )],
        },
        {
            "region_id": "E-TR-05", "name": "Hassa lav tüpleri (Hatay)", "role": "turkey_candidate",
            "lat": 36.8, "lon": 36.5, "tags": ["lava_tube", "cave"],
            "analog_dimensions": ["mağara ve lav tüpü"],
            "candidate_targets": [candidate(
                "T-03", "hipotez", "Volkanik alan ve lav tüpü morfolojisi düzeyinde nitel benzerlik.",
            )],
            "limitations": [
                "Lav tüpü ve çöküntü boyutu onlarca-yüzlerce metredir; 500 m çözünürlüklü DEM metrikleri bunu çözemez, bu boyut bu veri setiyle ölçülemez.",
                "Türkiye'nin ilk lav tüpü mağarasının 2015'te bulunduğu ve bilimsel olarak az karakterize edildiği bilgisi ekip raporundan alındı, kaynak teyit edilecek.",
                "Koordinat ~36.5 boylamında hücre sınırında; kesinleşince cell_id yeniden hesaplanmalı.",
            ],
        },
        {
            "region_id": "E-TR-06", "name": "Tuz Gölü", "role": "turkey_candidate",
            "lat": 38.75, "lon": 33.37, "tags": ["salt_flat", "evaporite", "wind_processes"],
            "analog_dimensions": ["tuz düzlüğü", "evaporitler", "rüzgar süreçleri"],
            "candidate_targets": [candidate(
                "T-01", "hipotez",
                "Evaporit ve kurumuş göl ortamı düzeyinde nitel benzerlik; nicel sonuca bırakıldı.",
            )],
        },
    ]
    for row in rows:
        extra_limitations = row.get("limitations", [])
        row["limitations"] = [COMMON_LIMITATION]
        if row["region_id"] in {"E-TR-03", "E-TR-04"}:
            row["limitations"].append(MEKE_ACIGOL_LIMITATION)
        row["limitations"].extend(extra_limitations)
    return rows


def load_feature_records(features_path: Path = FEATURES_PATH) -> dict[str, dict]:
    if not features_path.is_file():
        raise FileNotFoundError(f"Kisi 1 features.json not found: {features_path}")
    data = json.loads(features_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("records"), list):
        raise ValueError("features.json must have {schema_version, records} structure")
    records = {}
    for record in data["records"]:
        region_id = record.get("region_id")
        if region_id:
            if region_id in records:
                raise ValueError(f"Duplicate features.json region_id: {region_id}")
            records[str(region_id)] = record
    return records


def feature_links(region_id: str, feature_records: dict[str, dict]) -> tuple[list[dict], dict[str, dict | None]]:
    prefix = FEATURE_SITE_PREFIXES[region_id]
    refs: list[dict] = []
    availability: dict[str, dict | None] = {"local": None, "regional": None}
    if prefix is None:
        return refs, availability

    expected = {scale: f"{prefix}_{scale}" for scale in ("local", "regional")}
    missing = [key for key in expected.values() if key not in feature_records]
    if missing:
        warnings.warn(
            f"{region_id}: expected features.json records missing: {', '.join(missing)}; leaving features_ref empty",
            RuntimeWarning,
            stacklevel=2,
        )
        return refs, availability

    for scale, actual_id in expected.items():
        source = feature_records[actual_id]
        features = source.get("features") or {}
        comparable_count = sum(
            1 for name in SCORING_FEATURES
            if isinstance(features.get(name), dict) and features[name].get("comparable") is True
        )
        refs.append({"file": "features.json", "region_id": actual_id, "scale": scale})
        availability[scale] = {
            "resolution_validated": source.get("resolution_validated"),
            "comparable_metric_count": comparable_count,
            "data_status": source.get("data_status"),
        }
    return refs, availability


def load_grid_coverage(
    grid_path: Path = GRID_PATH,
    coverage_path: Path = COVERAGE_PATH,
) -> tuple[set[str], dict[str, dict], dict[str, dict]]:
    if not grid_path.is_file():
        raise FileNotFoundError(f"Processed earth grid not found: {grid_path}")
    if not coverage_path.is_file():
        raise FileNotFoundError(f"Grid coverage file not found: {coverage_path}")
    grid = pq.read_table(grid_path, columns=["lat", "lon"]).to_pylist()
    processed_keys = {cell_id(float(row["lat"]), float(row["lon"])) for row in grid}
    coverage_data = json.loads(coverage_path.read_text(encoding="utf-8"))
    coverage_by_key = {}
    for feature in coverage_data.get("features", []):
        props = feature.get("properties") or {}
        lat, lon = coverage_center(feature)
        key = cell_id(lat, lon)
        if key in coverage_by_key:
            raise ValueError(f"Duplicate cell in coverage.geojson: {key}")
        coverage_by_key[key] = props

    if not COVERAGE_REPORT_PATH.is_file():
        raise FileNotFoundError(f"Coverage validation report not found: {COVERAGE_REPORT_PATH}")
    report = json.loads(COVERAGE_REPORT_PATH.read_text(encoding="utf-8"))
    report_count = report.get("scope", {}).get("processed_cell_count")
    if report_count is not None and report_count != len(processed_keys):
        raise ValueError(
            f"coverage_report processed count ({report_count}) does not match grid ({len(processed_keys)})"
        )
    report_sites = {row.get("region_id"): row for row in report.get("turkey_sites", [])}
    return processed_keys, coverage_by_key, report_sites


def coverage_state(key: str, processed_keys: set[str], coverage_by_key: dict[str, dict]) -> dict:
    if key in processed_keys:
        coverage = coverage_by_key.get(key, {})
        return {
            "cell_key": key,
            "status": "processed",
            "comparable": coverage.get("comparable"),
        }
    coverage = coverage_by_key.get(key)
    if coverage and coverage.get("status") == "not_scanned":
        return {"cell_key": key, "status": "not_scanned", "comparable": False}
    return {"cell_key": key, "status": "out_of_scope", "comparable": False}


def source_commit(source_path: Path = SOURCE_PATH) -> str:
    if not source_path.is_file():
        raise FileNotFoundError(f"Grid source metadata not found: {source_path}")
    for line in source_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("Source commit:"):
            value = line.split(":", 1)[1].strip()
            if value:
                return value
    raise ValueError(f"Source commit is missing from {source_path}")


def build_records(
    features_path: Path = FEATURES_PATH,
    grid_path: Path = GRID_PATH,
    coverage_path: Path = COVERAGE_PATH,
) -> list[dict]:
    rows = source_rows()
    feature_records = load_feature_records(features_path)
    processed_keys, coverage_by_key, report_sites = load_grid_coverage(grid_path, coverage_path)
    source = source_commit()
    grouped: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        grouped[cell_id(row["lat"], row["lon"])].append(row["region_id"])

    records = []
    for row in rows:
        current_cell = cell_id(row["lat"], row["lon"])
        features_ref, feature_availability = feature_links(row["region_id"], feature_records)
        limitations = list(row["limitations"])
        if row["region_id"] == "E-TR-04" and not features_ref:
            limitations.append("features.json'da bu saha için ayrı kayıt yok; Meke ile aynı 0.5° hücreye düşer")
        site_coverage = coverage_state(current_cell, processed_keys, coverage_by_key)
        report_site = report_sites.get(row["region_id"])
        if report_site is None or report_site.get("cell_id") != current_cell:
            raise ValueError(f"Coverage report is missing or has a different cell for {row['region_id']}")
        report_status = "processed" if report_site.get("status") == "valid" else report_site.get("status")
        if report_status != site_coverage["status"]:
            raise ValueError(
                f"Coverage report and input files disagree for {row['region_id']}: "
                f"{report_status!r} != {site_coverage['status']!r}"
            )
        if row["region_id"] == "E-TR-05" and site_coverage["status"] == "not_scanned":
            limitations.append("Bu sahanın cell_key grid coverage dosyasında not_scanned durumundadır.")
        records.append({
            "region_id": row["region_id"],
            "name": row["name"],
            "role": row["role"],
            "lat": row["lat"],
            "lon": row["lon"],
            "coord_status": "approximate_unverified",
            "cell_id": current_cell,
            "shares_cell_with": [rid for rid in grouped[current_cell] if rid != row["region_id"]],
            "tags": row["tags"],
            "analog_dimensions": row["analog_dimensions"],
            "candidate_targets": row["candidate_targets"],
            "usgs_listed": False,
            "limitations": limitations,
            "features_ref": features_ref,
            "feature_availability": feature_availability,
            "grid_coverage": site_coverage,
            "source_commit": source,
            "local_media": [],
            "status": "draft_qualitative",
        })
    return records


def validate(records: list[dict], feature_records: dict[str, dict] | None = None) -> None:
    expected_cells = {
        "E-TR-01": "g_037.75_029.75",
        "E-TR-02": "g_038.75_028.75",
        "E-TR-03": "g_037.75_033.75",
        "E-TR-04": "g_037.75_033.75",
        "E-TR-05": "g_036.75_036.75",
        "E-TR-06": "g_038.75_033.25",
    }
    assert len(records) == 6
    ids = [record["region_id"] for record in records]
    assert ids == [f"E-TR-{i:02d}" for i in range(1, 7)]
    assert len(set(ids)) == 6
    for record in records:
        assert record["cell_id"] == expected_cells[record["region_id"]]
        assert record["usgs_listed"] is False
        assert set(record) == {
            "region_id", "name", "role", "lat", "lon", "coord_status", "cell_id",
            "shares_cell_with", "tags", "analog_dimensions", "candidate_targets",
            "usgs_listed", "limitations", "features_ref", "feature_availability",
            "grid_coverage", "local_media", "status", "source_commit",
        }
        assert isinstance(record["features_ref"], list)
        if feature_records is not None:
            assert all(ref["region_id"] in feature_records for ref in record["features_ref"])
    meke = next(r for r in records if r["region_id"] == "E-TR-03")
    acigol = next(r for r in records if r["region_id"] == "E-TR-04")
    assert meke["shares_cell_with"] == ["E-TR-04"]
    assert acigol["shares_cell_with"] == ["E-TR-03"]


def destination_path(force: bool) -> Path:
    if force or not OUTPUT.exists():
        return OUTPUT
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate_path = OUTPUT.with_name(f"{OUTPUT.stem}_{stamp}{OUTPUT.suffix}")
    counter = 2
    while candidate_path.exists():
        candidate_path = OUTPUT.with_name(f"{OUTPUT.stem}_{stamp}_{counter}{OUTPUT.suffix}")
        counter += 1
    return candidate_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Overwrite turkey_analogs.json")
    args = parser.parse_args()

    records = build_records()
    feature_records = load_feature_records()
    source = source_commit()
    validate(records, feature_records)
    payload = {
        "schema_version": "0.2-draft",
        "generated_at": datetime.now(timezone(timedelta(hours=3))).isoformat(timespec="seconds"),
        "owner": "Kisi 3 - discovery",
        "status": "draft_qualitative",
        "note": "Eslesmeler niteliksel hipotezdir; siralama sonucu Kisi 2 benzerlik motorundan gelir. Sayisal ozellikler features.json'da, region_id ile bagli.",
        "source_commit": source,
        "records": records,
    }
    output = destination_path(args.force)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    reparsed = json.loads(output.read_text(encoding="utf-8"))
    validate(reparsed["records"])
    assert reparsed["schema_version"] == "0.2-draft"
    assert reparsed["generated_at"].endswith("+03:00")
    print(f"Wrote {output.relative_to(ROOT)}")
    print("Validation passed: six unique IDs, expected cells, reciprocal shared cell, JSON round-trip, qualitative fields only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
