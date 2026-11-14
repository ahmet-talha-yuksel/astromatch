import json

import numpy as np
import pandas as pd
import pytest

from engine.export_scores import export_scores
from engine.mock import generate
from engine.validation_api import _score_grid, list_target_ids, score_grid


@pytest.fixture
def sample():
    targets, candidates, _ = generate(n_grid=240)
    rows = []
    for record in candidates:
        if record["kind"] != "earth_grid":
            continue
        row = {k: v for k, v in record.items() if k != "features"}
        row["cell_id"] = record["region_id"]
        for key, item in record["features"].items():
            row[key] = item["value"]
            row[key + "__status"] = item["data_status"]
            row[key + "__comparable"] = item["comparable"]
        rows.append(row)
    return pd.DataFrame(rows), targets


def run_mock(frame, targets, alias="T-02", **kwargs):
    return _score_grid(frame, alias, target_records=targets, **kwargs)


def test_order_nan_criteria_determinism_and_purity(sample):
    frame, targets = sample
    original = frame.copy(deep=True)
    first = run_mock(frame, targets, return_criteria=True)
    second = run_mock(frame, targets, return_criteria=True)
    pd.testing.assert_frame_equal(first, second, check_exact=True)
    pd.testing.assert_frame_equal(frame, original, check_exact=True)
    assert first.cell_id.tolist() == frame.cell_id.tolist()
    assert len(first) == len(frame)
    assert list(first.columns[:5]) == ["cell_id", "score", "distance_z", "n_features", "excluded_reason"]
    assert "s_slope_median_deg" in first
    assert first.score.isna().sum() == 2
    assert not (first.score.dropna() == 0).any()
    assert first.loc[0, "n_features"] == 0
    assert first.loc[0, "excluded_reason"] == "fewer than min_features eligible"
    assert np.isnan(first.loc[0, "s_slope_median_deg"])


def test_aliases_and_unscorable_target(sample):
    frame, targets = sample
    assert list_target_ids()["T-01"] == "mars_jezero"
    for alias in ("T-01", "T-02", "T-03"):
        assert run_mock(frame, targets, alias).score.notna().any()
    assert list_target_ids()["T-04"] == "mars_phoenix"
    with pytest.warns(UserWarning, match="target_unscorable"):
        result = run_mock(frame, targets, "T-04")
    assert result.score.isna().all()
    assert result.excluded_reason.str.startswith("target_unscorable:").all()
    with pytest.warns(UserWarning, match="target_unscorable"):
        real = score_grid(frame, "T-01")
    assert real.score.isna().all()
    assert real.excluded_reason.eq("target_unscorable: resolution_not_validated").all()


def test_sigma_modes(sample):
    frame, targets = sample
    baseline = run_mock(frame, targets)
    noisy = frame.copy(deep=True)
    noisy["slope_median_deg"] *= 1.05
    changed = run_mock(noisy, targets)
    assert changed.attrs["sigma"]["slope_median_deg"] != baseline.attrs["sigma"]["slope_median_deg"]
    frozen_a = run_mock(frame, targets, sigma="frozen")
    frozen_b = run_mock(noisy, targets, sigma="frozen")
    assert frozen_a.attrs["sigma"] == frozen_b.attrs["sigma"]
    assert frozen_a.attrs["sigma_source"] == frozen_b.attrs["sigma_source"]
    explicit = {key: 10.0 for key in baseline.attrs["sigma"]}
    direct = run_mock(frame, targets, sigma=explicit)
    assert direct.attrs["sigma"] == explicit
    assert set(direct.attrs["sigma_source"].values()) == {"explicit"}


def test_scale_and_missing_values(sample):
    frame, targets = sample
    altered = frame.copy(deep=True)
    altered.loc[1, "scale"] = "local"
    for key in ("slope_median_deg", "slope_p90_deg", "flat_fraction", "tri_median_m"):
        altered.loc[2, key] = np.nan
    result = run_mock(altered, targets)
    assert np.isnan(result.loc[1, "score"])
    assert result.loc[1, "excluded_reason"] == "scale mismatch"
    assert np.isnan(result.loc[2, "score"])
    assert result.loc[2, "n_features"] == 2


def test_export_long_format(tmp_path):
    manifest = export_scores(mock=True, criteria=True, out=tmp_path)
    frame = pd.read_parquet(tmp_path / "scores_all.parquet")
    csv = pd.read_csv(tmp_path / "scores_all.csv")
    assert manifest["grid_rows"] == 5000
    assert len(frame) == len(csv) == 5000 * 5
    assert frame.groupby("target_id").size().to_dict() == {alias: 5000 for alias in ("T-01","T-02","T-03","T-04","T-05")}
    assert frame.score.isna().sum() == csv.score.isna().sum() == 32 * 3 + 5000 * 2
    assert "s_slope_median_deg" in frame
    assert {'score_ci_low','score_ci_high','rank_p5','rank_p95','top10_stability'} <= set(frame.columns)
    scored=frame.loc[frame.score.notna()]
    assert (scored.score_ci_low <= scored.score).all()
    assert (scored.score <= scored.score_ci_high).all()
    assert json.loads((tmp_path / "scores_manifest.json").read_text())["data_status"] == "mock"
