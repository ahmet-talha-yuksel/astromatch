from engine import load_dataset, rank
from engine.io import config
from engine.measurement import eligible_target_feature, excluded_features
from engine.readiness import check_real_data
from engine.models import DataPaths
import pandas as pd


SHAPE = ('hypsometric_integral', 'roughness_ratio', 'curvature_std_per_km')


def test_feature_set_switch_and_mars_gate(monkeypatch):
    monkeypatch.setenv('ASTROMATCH_FEATURE_SET', 'v9')
    ds = load_dataset()
    moon = next(t for t in ds.targets if t.region_id == 'moon_shackleton_regional')
    mars = next(t for t in ds.targets if t.region_id == 'mars_phoenix_regional')
    assert all(eligible_target_feature(moon, key) for key in SHAPE)
    assert all(eligible_target_feature(mars, key) for key in SHAPE)
    assert not excluded_features(mars, SHAPE)
    assert len(rank(ds, moon.region_id, 'regional', k=1).top_k[0]['per_criterion']) == 9
    assert len(rank(ds, mars.region_id, 'regional', k=1).top_k[0]['per_criterion']) == 9
    monkeypatch.setenv('ASTROMATCH_FEATURE_SET', 'v6')
    assert len(config('features.yaml')['features']) == 6
    assert len(rank(ds, moon.region_id, 'regional', k=1).top_k[0]['per_criterion']) == 6


def test_delivered_shape_sensitivity_enables_mars(monkeypatch):
    monkeypatch.setenv('ASTROMATCH_FEATURE_SET', 'v9')
    mars = next(t for t in load_dataset().targets if t.region_id == 'mars_phoenix_regional')
    for key in SHAPE:
        mars.measurement_support['sensitivity'].pop(key, None)
        assert not eligible_target_feature(mars, key)
        mars.measurement_support.setdefault('sensitivity', {})[key] = {'pass': True}
        mars.features_interpolated[key] = mars.features[key].value
        assert eligible_target_feature(mars, key)
    assert not any('shape feature sensitivity not delivered' in item for item in excluded_features(mars, SHAPE))


def test_top_tier_and_flattened_flag(monkeypatch):
    monkeypatch.setenv('ASTROMATCH_FEATURE_SET', 'v9')
    ds = load_dataset()
    cell = next(c for c in ds.candidates if c.kind == 'earth_grid' and c.resolution_validated)
    cell.features['roughness_ratio'].value = 0.0
    result = rank(ds, 'moon_shackleton_regional', 'regional', k=2, include_uncertainty=True)
    row = next(r for r in result.full_scores if r['id'] == cell.region_id)
    assert 'possible_flattened_surface' in row['flags']
    assert result.full_scores[0]['top_tier']
    assert result.full_scores[0]['top_tier_size'] >= 1
    assert all(isinstance(r['top_tier'], bool) for r in result.full_scores)


def test_v9_check_requires_shape_on_validated_grid_but_allows_zero(monkeypatch, tmp_path):
    monkeypatch.setenv('ASTROMATCH_FEATURE_SET', 'v9')
    grid = pd.read_parquet('processing/out/earth_grid.parquet')
    validated = grid.index[grid.resolution_validated][0]
    grid.loc[validated, 'roughness_ratio'] = 0.0
    path = tmp_path / 'grid.parquet'
    grid.to_parquet(path)
    paths = DataPaths(features=['processing/out/real/features.json', 'processing/out/mars_measured/features.json'], grid=str(path))
    ready = check_real_data(paths)
    assert ready['ready']
    assert ready['feature_coverage']['earth_grid']['roughness_ratio']['present'] == len(grid)
    grid.loc[validated, 'hypsometric_integral'] = None
    grid.to_parquet(path)
    failed = check_real_data(paths)
    assert not failed['ready']
    assert any('v9 requires hypsometric_integral' in error for error in failed['errors'])
