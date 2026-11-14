import pytest
from engine.similarity import rank_candidates

def test_exact_match_ranks_first():
    target = {"features": {"slope_deg": 10, "tri_m": 3, "relief_m": 100}}
    candidates = [{"id": "bad", "features": {"slope_deg": 20, "tri_m": 3, "relief_m": 100}},
                  {"id": "exact", "features": target["features"]}]
    ranked = rank_candidates(target, candidates, {"slope_deg": 1})
    assert ranked[0]["id"] == "exact"
    assert ranked[0]["score"] == pytest.approx(1)

def test_missing_data_is_not_perfect_match():
    ranked = rank_candidates({"features": {"slope_deg": 1}}, [{"id": "x", "features": {}}], {"slope_deg": 1})
    assert ranked[0]["score"] is None
