import numpy as np
import pytest

from engine.io import config, load_dataset
from engine.models import DataPaths
from engine.measurement import eligible_target_feature, target_status
from engine.ranking import rank
from engine.transform import transform


def test_configured_transforms_and_multiplicative_slope():
    features = config('features.yaml')['features']
    slope = features['slope_median_deg']
    assert transform(.8, slope) - transform(.3, slope) == pytest.approx(np.log(.85/.35))
    assert transform(0, slope) == pytest.approx(np.log(.05))
    flat = features['flat_fraction']
    assert transform(0, flat) == transform(.01, flat)
    assert transform(1, flat) == transform(.99, flat)


def test_jezero_uses_only_passing_feature_verdicts():
    ds = load_dataset(DataPaths(features=['processing/out/real/features.json', 'processing/out/mars_measured/features.json'], grid='processing/out/earth_grid.parquet'))
    target = next(t for t in ds.targets if t.region_id == 'mars_jezero_regional')
    assert not target.resolution_validated
    assert target_status(target) == ('scorable', None)
    assert sum(eligible_target_feature(target, key) for key in config('features.yaml')['features']) == 7
    assert not eligible_target_feature(target, 'slope_p90_deg')
    assert not eligible_target_feature(target, 'curvature_std_per_km')
    result = rank(ds, target.region_id, 'regional', k=1, include_uncertainty=True)
    assert result.top_k and result.top_k[0]['score_ci_low'] <= result.top_k[0]['score_geo'] <= result.top_k[0]['score_ci_high']
    assert 'slope_p90_deg excluded' in result.excluded_features[0]
