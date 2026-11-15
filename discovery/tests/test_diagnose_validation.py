from __future__ import annotations

import numpy as np

import pandas as pd

from discovery.diagnose_validation import auc, latitude_summary, latitude_stratified_auc, paired_bootstrap


def test_auc_and_latitude_diagnostics_in_memory():
    assert auc(np.array([3.0, 4.0]), np.array([1.0, 2.0])) == 1.0
    assert auc(np.array([1.0]), np.array([2.0])) == 0.0
    summary = latitude_summary(np.array([-45.0, 15.0]), np.array([-10.0, 65.0]))
    assert summary["positive"]["median_absolute_latitude"] == 30.0
    assert summary["positive"]["latitude_band_counts"]["[-60,-30)"] == 1
    assert summary["positive"]["latitude_band_counts"]["[0,30)"] == 1
    assert summary["background"]["latitude_band_counts"]["[60,90]"] == 1


def test_paired_reference_bootstrap_and_latitude_strata_in_memory():
    frame = pd.DataFrame({
        "group": ["analog", "analog", "background", "background"],
        "lat": [10.0, 40.0, 15.0, 45.0],
        "score": [0.9, 0.8, 0.2, 0.1],
        "reference": [0.8, 0.7, 0.3, 0.2],
    })
    result = paired_bootstrap(frame, "score", "reference", n_boot=50, seed=17)
    assert result["target_auc"] == 1.0
    assert result["reference_auc"] == 1.0
    assert result["difference_paired_bootstrap_95_ci"] == [0.0, 0.0]
    lat = latitude_stratified_auc(frame, "score")
    assert lat["pooled_auc"] == 1.0
    assert [row["band"] for row in lat["bands"]] == ["[0,30)", "[30,60)"]
