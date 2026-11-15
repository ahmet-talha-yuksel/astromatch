import logging

import numpy as np
import pytest

from engine.adapters import adapt
from engine.calibration import calibrate
from engine.io import config
from engine.measurement import target_status
from engine.mock import generate
from engine.models import Dataset
from engine.ranking import rank
from engine.validation_api import _default_reference, _sigma_table
from engine.validation_metrics import grid_feature_correlations
from engine.weights import weight_vector


def test_failed_feature_is_excluded_without_blocking_target(caplog):
    targets, candidates, _ = generate(n_grid=30, n_reference=0)
    raw = next(row for row in targets if row['region_id'] == 'T-01' and row['scale'] == 'regional')
    raw['measurement_support'] = {'sensitivity': {
        'slope_p90_deg': {'pass': False, 'rel_diff': .1544, 'abs_diff': .912}}}
    with caplog.at_level(logging.WARNING):
        target = adapt(raw)
    assert 'input comparable=true' in caplog.text
    assert target.features['slope_p90_deg'].comparable is False
    assert target_status(target) == ('scorable', None)
    ds = Dataset(targets=[target], candidates=[adapt(row) for row in candidates if row['scale'] == 'regional'], mode='mock')
    result = rank(ds, target.region_id, 'regional')
    assert result.full_scores
    assert any('15.44% / 0.912°' in item for item in result.excluded_features)
    assert any('slope_p90_deg excluded' in item for item in result.top_k[0]['explanation']['excluded_features'])
    for key in ('slope_median_deg', 'flat_fraction', 'tri_median_m'):
        target.features[key].comparable = False
    assert target_status(target)[0] == 'unscorable'


def test_group_weights_and_calibration_median50():
    cfg = config('features.yaml')
    keys = list(cfg['features'])
    weights = weight_vector(cfg, {})
    for group in cfg['feature_groups'].values():
        assert sum(weights[keys.index(key)] for key in group) == pytest.approx(1 / 3)
    rng = np.random.default_rng(21)
    values = rng.normal(size=(40, len(keys))) * np.arange(1, len(keys) + 1)
    mask = np.ones_like(values, dtype=bool)
    first = calibrate(values, mask, 'regional', 'balanced', cfg)
    second = calibrate(values, mask, 'regional', 'balanced', cfg)
    assert first == second
    assert first['method'] == 'loo_median50'
    assert .05 <= first['k'] <= 2
    assert first['median_pairwise_score_geo'] == pytest.approx(50, abs=.001)
    fixed = calibrate(values, mask, 'regional', 'balanced', {**cfg, 'sigma_calibration': 'fixed_k'})
    assert fixed['k'] == .5 and fixed['method'] == 'fixed_k'


def test_fixed_k_rank_uses_legacy_rule():
    cfg = config('features.yaml')
    original = cfg['sigma_calibration']
    try:
        cfg['sigma_calibration'] = 'fixed_k'
        targets, candidates, _ = generate(n_grid=30, n_reference=0)
        target = adapt(next(row for row in targets if row['region_id'] == 'T-01' and row['scale'] == 'regional'))
        ds = Dataset(targets=[target], candidates=[adapt(row) for row in candidates if row['scale'] == 'regional'], mode='mock')
        result = rank(ds, target.region_id, 'regional')
        assert result.sigma_calibration['method'] == 'fixed_k'
        assert result.sigma_calibration['k'] == .5
    finally:
        cfg['sigma_calibration'] = original


def test_scanned_percentile_uses_eligible_grid_only():
    targets, candidates, _ = generate(n_grid=40, n_reference=0)
    target = adapt(next(row for row in targets if row['region_id'] == 'T-01' and row['scale'] == 'regional'))
    ds = Dataset(targets=[target], candidates=[adapt(row) for row in candidates if row['scale'] == 'regional'], mode='mock')
    result = rank(ds, target.region_id, 'regional')
    grid_ids = {row.region_id for row in ds.candidates if row.kind == 'earth_grid'}
    scores = np.array([row['score_geo'] for row in result.full_scores if row['id'] in grid_ids])
    assert len(scores) > 0
    for row in result.full_scores:
        expected = 100 * np.mean(scores < row['score_geo'])
        assert row['score_percentile_scanned'] == pytest.approx(expected)
    assert result.sigma_calibration['method'] == 'loo_median50'


def test_local_frozen_sigma_and_feature_correlations():
    cfg = config('features.yaml')
    frame = _default_reference('local')
    table, calibration = _sigma_table(frame, 'local', None, cfg['features'], weight_vector(cfg, {}), 'balanced')
    assert calibration['pool_kind'] == 'earth_site'
    assert calibration['n'] == 8
    assert all(item['n_samples'] == 8 for item in table.values())
    from engine.io import load_dataset
    from engine.models import DataPaths
    ds = load_dataset(DataPaths(features=['processing/out/real/features.json', 'processing/out/mars_measured/features.json'], grid='processing/out/earth_grid.parquet'))
    correlations = grid_feature_correlations(ds)
    assert correlations['n_cells'] == 216
    assert correlations['matrix']['relief_m']['elevation_std_m'] > .9
