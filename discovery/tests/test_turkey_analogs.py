from __future__ import annotations

import json
from pathlib import Path

from discovery.build_turkey_analogs import (
    FEATURES_PATH, SCORING_FEATURES, build_records, load_feature_records, source_commit, validate,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "out" / "turkey_analogs.json"


def test_turkey_features_refs_cells_and_qualitative_schema():
    feature_records = load_feature_records()
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    records = payload["records"]
    validate(records, feature_records)

    assert payload["schema_version"] == "0.2-draft"
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


def _assert_no_metric_values(value, metric_names: set[str]):
    if isinstance(value, dict):
        assert not (set(value) & metric_names)
        for nested in value.values():
            _assert_no_metric_values(nested, metric_names)
    elif isinstance(value, list):
        for nested in value:
            _assert_no_metric_values(nested, metric_names)
