from __future__ import annotations

import numpy as np

from discovery.diagnose_validation import auc, latitude_summary


def test_auc_and_latitude_diagnostics_in_memory():
    assert auc(np.array([3.0, 4.0]), np.array([1.0, 2.0])) == 1.0
    assert auc(np.array([1.0]), np.array([2.0])) == 0.0
    summary = latitude_summary(np.array([-45.0, 15.0]), np.array([-10.0, 65.0]))
    assert summary["positive"]["median_absolute_latitude"] == 30.0
    assert summary["positive"]["latitude_band_counts"]["[-60,-30)"] == 1
    assert summary["positive"]["latitude_band_counts"]["[0,30)"] == 1
    assert summary["background"]["latitude_band_counts"]["[60,90]"] == 1
