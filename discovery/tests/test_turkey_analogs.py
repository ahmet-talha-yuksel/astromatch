from __future__ import annotations

import json
from pathlib import Path

from discovery.build_turkey_analogs import (
    FEATURES_PATH, FEATURE_SITE_PREFIXES, SCORING_FEATURES, build_records,
    coordinate_updates, load_feature_records, source_commit, validate,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "out" / "turkey_analogs.json"


def test_turkey_features_refs_cells_and_qualitative_schema():
    feature_records = load_feature_records()
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    records = payload["records"]
    validate(records, feature_records)

    assert payload["schema_version"] == "0.3-draft"
    assert payload["source_commit"] == source_commit()
    assert all(ref["region_id"] in feature_records for row in records for ref in row["features_ref"])

    expected_cells = [
        "g_037.75_029.75",
        "g_038.75_028.75",
        "g_037.75_033.75",
        "g_037.75_033.75",
        "g_036.75_036.75",
        "g_038.75_033.25",
    ]
    assert [row["cell_id"] for row in records] == expected_cells

    by_id = {row["region_id"]: row for row in records}
    assert by_id["E-TR-03"]["shares_cell_with"] == ["E-TR-04"]
    assert by_id["E-TR-04"]["shares_cell_with"] == ["E-TR-03"]
    assert by_id["E-TR-04"]["features_ref"] == []
    assert any("features.json'da bu saha için ayrı kayıt yok" in x for x in by_id["E-TR-04"]["limitations"])
    assert by_id["E-TR-05"]["grid_coverage"]["status"] == "not_scanned"
    assert any("not_scanned" in x for x in by_id["E-TR-05"]["limitations"])
    assert by_id["E-TR-04"]["coord_status"] == "approximate_unverified"
    assert by_id["E-TR-04"]["coord_source"] is None
    assert (by_id["E-TR-04"]["lat"], by_id["E-TR-04"]["lon"]) == (37.7, 33.7)

    for record in records:
        prefix = FEATURE_SITE_PREFIXES[record["region_id"]]
        choices = [f"{prefix}_regional", f"{prefix}_local"] if prefix else []
        source_id = next((rid for rid in choices if rid in feature_records), None)
        if source_id:
            assert record["coord_source"] == source_id
            assert record["coord_status"] == "from_features_json"
            assert record["lat"] == feature_records[source_id]["lat"]
            assert record["lon"] == feature_records[source_id]["lon"]

    t04 = next(c for c in by_id["E-TR-02"]["candidate_targets"] if c["target_id"] == "T-04")
    assert t04["target_available"] is False
    assert "features.json" in t04["note"]

    for row in records:
        assert set(row["feature_availability"]) == {"local", "regional"}
        for scale, availability in row["feature_availability"].items():
            if availability is not None:
                assert set(availability) == {"resolution_validated", "comparable_metric_count", "data_status"}
        _assert_no_metric_values(row, set(SCORING_FEATURES))


def test_feature_refs_are_local_regional_pairs_for_mapped_sites():
    records = build_records()
    by_id = {row["region_id"]: row for row in records}
    for region_id in ("E-TR-01", "E-TR-02", "E-TR-03", "E-TR-05", "E-TR-06"):
        refs = by_id[region_id]["features_ref"]
        assert {ref["scale"] for ref in refs} == {"local", "regional"}
        assert all(ref["region_id"].endswith(f"_{ref['scale']}") for ref in refs)


def test_feature_coordinate_shifts_and_recomputed_cells():
    updates = coordinate_updates(load_feature_records())
    assert [row["region_id"] for row in updates] == [f"E-TR-{i:02d}" for i in range(1, 7)]
    assert all(not row["cell_changed"] for row in updates)
    assert all(row["distance_km"] >= 0 for row in updates)
    assert updates[3]["source_record_id"] is None
    assert updates[3]["distance_km"] == 0


def _assert_no_metric_values(value, metric_names: set[str]):
    if isinstance(value, dict):
        assert not (set(value) & metric_names)
        for nested in value.values():
            _assert_no_metric_values(nested, metric_names)
    elif isinstance(value, list):
        for nested in value:
            _assert_no_metric_values(nested, metric_names)
