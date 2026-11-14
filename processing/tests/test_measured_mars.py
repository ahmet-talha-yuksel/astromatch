import numpy as np
import pytest
from processing.scripts.measured_mars import metrics, sensitivity, TOPOGRAPHIC


def test_plane_with_missing_center_has_exact_slope_and_effective_support():
    yy,xx=np.mgrid[:7,:7]
    z=(xx*10+yy*20).astype(float)
    z[3,3]=np.nan
    values,ratio=metrics(z)
    assert values['slope_median_deg']==pytest.approx(np.degrees(np.arctan(np.hypot(.01,.02))))
    assert ratio==pytest.approx(4/49)  # four corners only: clipped 2x2 <6
    assert values['elevation_std_m']==pytest.approx(np.nanstd(z))


def test_six_samples_required_and_empty_metrics_fail():
    z=np.full((3,3),np.nan);z.ravel()[:5]=0
    values,ratio=metrics(z)
    assert ratio==1 and values['slope_median_deg'] is None
    z[1,2]=0
    values,ratio=metrics(z)
    assert ratio<1 and values['slope_median_deg']==0
    assert not all(c['pass'] for c in sensitivity(dict.fromkeys(TOPOGRAPHIC),dict.fromkeys(TOPOGRAPHIC,0)).values())


def test_sensitivity_absolute_or_relative_and_zero_baseline():
    baseline=dict.fromkeys(TOPOGRAPHIC,100.)
    assert all(c['pass'] for c in sensitivity(dict.fromkeys(TOPOGRAPHIC,114.),baseline).values())
    assert not any(c['pass'] for c in sensitivity(dict.fromkeys(TOPOGRAPHIC,120.),baseline).values())
    baseline=dict.fromkeys(TOPOGRAPHIC,0.)
    assert all(c['pass'] for c in sensitivity(baseline,baseline).values())
    assert sensitivity(dict(baseline,slope_median_deg=.2),baseline)['slope_median_deg']['pass']


def test_delivered_records_match_engineering_gate():
    import json
    from pathlib import Path
    path=Path(__file__).resolve().parents[1]/'out/mars_measured/features.json'
    records=json.loads(path.read_text())['records']
    assert {r['region_id'] for r in records}=={'mars_phoenix_regional','mars_jezero_regional','mars_arcadia_regional'}
    for record in records:
        support=record['measurement_support']
        primary={k:record['features'][k]['value'] for k in TOPOGRAPHIC}
        assert support['sensitivity']==sensitivity(primary,record['features_interpolated'])
        expected=all(c['pass'] for c in support['sensitivity'].values()) and support['effective_nodata_ratio']<=.30
        assert record['resolution_validated']==expected
        assert record['quality']['nodata_ratio']==support['effective_nodata_ratio']
        assert all(f['comparable']==expected for f in record['features'].values())
        assert record['provenance']['source_radius_m']==3396000
        assert record['analysis_resolution_m']==1000 and record['window_km']==50
        if not expected: assert support['unscorable_reasons']
