from __future__ import annotations

import pytest

from discovery.analog_mapping import cell_id
from discovery.build_turkey_analogs import FEATURES_PATH, load_feature_records
from discovery.global_pool import include_land_cell, land_fraction_5x5, scan_status
from discovery.grid_utils import parse_cell_id


def test_atacama_cell_is_retained_by_land_threshold():
    key = cell_id(-24.1, -70.0)
    lat, lon = parse_cell_id(key)
    assert land_fraction_5x5(lat, lon) >= 0.5
    assert include_land_cell(lat, lon)


@pytest.mark.skipif(not FEATURES_PATH.exists(), reason="requires ignored discovery/data/inputs/features.json")
def test_salda_cell_is_retained_by_land_threshold():
    record = load_feature_records()["earth_salda_regional"]
    key = cell_id(float(record["lat"]), float(record["lon"]))
    lat, lon = parse_cell_id(key)
    assert land_fraction_5x5(lat, lon) >= 0.5
    assert include_land_cell(lat, lon)


def test_mid_pacific_cell_is_not_in_pool():
    lat, lon = parse_cell_id(cell_id(0.25, -150.25))
    assert land_fraction_5x5(lat, lon) < 0.5
    assert not include_land_cell(lat, lon)


def test_scan_status_tracks_validation_source():
    assert scan_status("pilot-key", {"pilot-key": "pilot"}, {}) == ("scanned", "pilot")
    assert scan_status("validation-key", {"validation-key": "validation_sample"}, {}) == ("scanned", "validation_sample")
    assert scan_status("pending", {}, {"pending": {"status": "not_scanned"}}) == ("not_scanned", "none")
    assert scan_status("outside", {}, {}) == ("out_of_coverage", "none")
