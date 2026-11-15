from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from discovery.analysis_utils import SCORING_FEATURES, load_grid
from discovery.analog_mapping import cell_id
from discovery.export_global_candidates import build_collection
from discovery.grid_utils import cell_bounds, cell_polygon, neighbor_keys, parse_cell_id
from discovery.stability_test import jaccard, noisy_grid
from discovery.validate_usgs import analyze, auc_value, enrichment
from discovery.score_io import load_scores


def test_cell_id_round_trip_and_polar_edge():
    for lat, lon in ((-24.25, -69.75), (37.75, 29.75), (89.75, 179.75)):
        key = cell_id(lat, lon)
        assert parse_cell_id(key) == (lat, lon)
    assert cell_id(90, 180) == "g_089.75_179.75"


def test_cell_bounds_polygon_and_neighbors():
    key = "g_-24.25_-69.75"
    assert cell_bounds(key) == (-70.0, -24.5, -69.5, -24.0)
    ring = cell_polygon(key)["coordinates"][0]
    assert ring[0] == ring[-1]
    assert min(p[0] for p in ring) == -70.0
    assert max(p[0] for p in ring) == -69.5
    assert len(neighbor_keys(key)) == 8


@pytest.mark.parametrize(
    ("positive", "negative", "expected"),
    [([3, 4], [1, 2], 1.0), ([1, 2], [3, 4], 0.0), ([1, 1], [1, 1], 0.5)],
)
def test_auc_ties(positive, negative, expected):
    assert auc_value(np.array(positive), np.array(negative)) == pytest.approx(expected)


def test_percentile_and_enrichment_arithmetic():
    scores = pd.Series([0.1, 0.2, 0.3, 0.4], index=["a", "b", "c", "d"])
    assert enrichment(scores, {"d"}, 0.25) == {
        "top_cell_count": 1, "positive_count_in_top": 1, "enrichment": 4.0
    }


def test_zero_and_insufficient_positive_states():
    grid = _grid(["g_000.25_000.25", "g_000.25_000.75"])
    scores = pd.DataFrame({
        "cell_id": grid.cell_key.tolist(), "target_id": ["T-02", "T-02"], "score": [0.7, 0.2]
    })
    zero = analyze(grid, scores, {"g_030.25_030.25": ["outside"]}, set(), min_positives=2,
                   n_perm=2, n_boot=2, seed=42)
    assert zero["targets"]["T-02"]["status"] == "not_evaluable"
    assert zero["targets"]["T-02"].get("cohorts", {}) == {}
    sparse = analyze(grid, scores, {"g_000.25_000.25": ["one"]}, set(), min_positives=2,
                     n_perm=2, n_boot=2, seed=42)
    assert sparse["targets"]["T-02"]["status"] == "insufficient_positives"
    assert len(sparse["targets"]["T-02"]["positive_cells"]) == 1
    assert sparse["targets"]["T-02"]["positive_cells"][0]["score"] == 0.7
    assert sparse["targets"]["T-01"]["status"] == "unscorable"
    assert sparse["targets"]["T-01"]["score"] is None


def test_neighbor_exclusion_and_jaccard():
    grid = _grid(["g_000.25_000.25", "g_000.25_000.75", "g_002.25_002.25"])
    scores = pd.DataFrame({
        "cell_id": grid.cell_key.tolist(), "target_id": ["T-02"] * 3, "score": [0.9, 0.5, 0.1]
    })
    result = analyze(grid, scores, {"g_000.25_000.25": ["positive"]}, set(), min_positives=1,
                     n_perm=3, n_boot=3, seed=42)
    cohorts = result["targets"]["T-02"]["cohorts"]
    assert cohorts["primary_unlabeled_background"]["background_count"] == 2
    assert cohorts["sensitivity_without_positive_neighbors"]["background_count"] == 1
    assert jaccard({"a", "b"}, {"b", "c"}) == pytest.approx(1 / 3)


def test_noise_clips_physical_bounds():
    grid = _grid(["g_000.25_000.25"] * 2)
    grid["flat_fraction"] = [0.0, 1.0]
    grid["land_fraction"] = [0.4, 0.8]
    noisy = noisy_grid(grid, 10, 42)
    assert noisy.flat_fraction.between(0, 1).all()
    assert noisy.lat.tolist() == grid.lat.tolist()
    assert noisy.land_fraction.tolist() == grid.land_fraction.tolist()
    for feature in SCORING_FEATURES:
        if feature != "flat_fraction":
            assert (noisy[feature].dropna() >= 0).all()


def test_grid_merge_uses_coordinate_cell_key_and_deduplicates(tmp_path):
    first = _grid(["g_037.75_029.75"])
    first["region_id"] = ["earth_grid_r254_c418"]
    second = first.copy()
    paths = [tmp_path / "a.parquet", tmp_path / "b.parquet"]
    first.to_parquet(paths[0], index=False)
    second.to_parquet(paths[1], index=False)
    with pytest.warns(RuntimeWarning, match="duplicate coordinate cell_key"):
        merged = load_grid(paths)
    assert len(merged) == 1
    assert merged.iloc[0].cell_key == "g_037.75_029.75"


def test_load_scores_parquet_and_csv(tmp_path):
    frame = pd.DataFrame({"cell_id": ["earth_grid_r254_c418"], "target_id": ["T-02"], "score": [0.75]})
    parquet = tmp_path / "scores_all.parquet"
    csv = tmp_path / "scores_all.csv"
    frame.to_parquet(parquet, index=False)
    frame.to_csv(csv, index=False)
    assert load_scores(parquet).iloc[0].score == pytest.approx(0.75)
    assert load_scores(csv).iloc[0].score == pytest.approx(0.75)
    assert load_scores(tmp_path).iloc[0].target_id == "T-02"


def test_export_converts_nan_to_null():
    grid = _grid(["g_000.25_000.25"])
    grid.loc[0, "elevation_std_m"] = np.nan
    scores = pd.DataFrame({"cell_id": [grid.cell_key.iloc[0]], "target_id": ["T-02"], "score": [0.8]})
    collection = build_collection(grid, scores, {}, {}, top_k=1, precision=4)
    feature = collection["features"][0]
    assert feature["properties"]["scores"]["T-01"] is None
    assert feature["properties"]["scores"]["T-02"] == 0.8
    assert feature["properties"]["features"]["elevation_std_m"] is None
    encoded = json.dumps(collection, allow_nan=False)
    assert '"T-01": null' in encoded
    assert "metadata" in collection and "scope" in collection["metadata"]


def _grid(keys: list[str]) -> pd.DataFrame:
    from discovery.grid_utils import parse_cell_id

    rows = []
    for i, key in enumerate(keys):
        lat, lon = parse_cell_id(key)
        row = {"cell_key": key, "cell_id": f"earth_grid_r{i:03d}_c{i:03d}", "lat": lat, "lon": lon,
               "land_fraction": 1.0}
        for feature in SCORING_FEATURES:
            row[feature] = float(i + 1)
            row[f"{feature}__comparable"] = True
        rows.append(row)
    return pd.DataFrame(rows)
