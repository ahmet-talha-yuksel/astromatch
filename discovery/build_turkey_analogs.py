"""Build qualitative Turkish analog hypotheses from the supplied field data."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .analog_mapping import cell_id


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "out" / "turkey_analogs.json"

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


def build_records() -> list[dict]:
    rows = source_rows()
    grouped: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        grouped[cell_id(row["lat"], row["lon"])].append(row["region_id"])

    records = []
    for row in rows:
        current_cell = cell_id(row["lat"], row["lon"])
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
            "limitations": row["limitations"],
            "features_ref": {"file": "features.json", "region_id": row["region_id"]},
            "local_media": [],
            "status": "draft_qualitative",
        })
    return records


def validate(records: list[dict]) -> None:
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
            "usgs_listed", "limitations", "features_ref", "local_media", "status",
        }
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
    validate(records)
    payload = {
        "schema_version": "0.1-draft",
        "generated_at": datetime.now(timezone(timedelta(hours=3))).isoformat(timespec="seconds"),
        "owner": "Kisi 3 - discovery",
        "status": "draft_qualitative",
        "note": "Eslesmeler niteliksel hipotezdir; siralama sonucu Kisi 2 benzerlik motorundan gelir. Sayisal ozellikler features.json'da, region_id ile bagli.",
        "records": records,
    }
    output = destination_path(args.force)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    reparsed = json.loads(output.read_text(encoding="utf-8"))
    validate(reparsed["records"])
    assert reparsed["schema_version"] == "0.1-draft"
    assert reparsed["generated_at"].endswith("+03:00")
    print(f"Wrote {output.relative_to(ROOT)}")
    print("Validation passed: six unique IDs, expected cells, reciprocal shared cell, JSON round-trip, qualitative fields only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
