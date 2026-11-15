"""Analytic and masked-window checks for data-only morphology descriptors."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import rasterio
from rasterio.transform import from_origin

from processing.scripts.dem import process_dem
from processing.scripts.enrich_morphology import JSON_FILES, PARQUET_FILES, bind_unchanged_review, enrich, legacy_record
from processing.scripts.measured_window import measured_window
from processing.scripts.metrics import TOPOGRAPHIC, terrain_features
from processing.scripts.morphology import MORPHOLOGY, morphology_features
from processing.scripts.process_dem import write_earth_grid
from processing.tests.test_dem import fixture_dem


def values(array, spacing=1000):
    features, support = morphology_features(array, spacing)
    return {key: f['value'] for key, f in features.items()}, support


def test_plane_exact_hi_and_paired_roughness():
    y, x = np.mgrid[:50, :50]
    z = 100 + x * 10 + y * 20
    f, support = values(z)
    assert f['hypsometric_integral'] == pytest.approx(.5)
    assert f['roughness_ratio'] == pytest.approx(np.sqrt(8/224))
    assert f['curvature_std_per_km'] == pytest.approx(0, abs=1e-12)
    assert support['measured_samples'] == 2500
    assert support['curvature_centers'] == 48 * 48
    assert support['minimum_support'] == {'3x3': 6, '15x15': 150}
    assert support['interpolation'] == 'none'


def test_curvature_units_analytic_quartic_and_translation_scaling():
    _, cols = np.mgrid[:25, :25]
    x = (cols - 12) * 1000
    z = x.astype(float)**4 * 1e-12
    f, _ = values(z)
    expected = np.std(12e-12 * x[1:-1, 1:-1]**2) * 1000
    assert f['curvature_std_per_km'] == pytest.approx(expected, rel=1e-10)
    shifted, _ = values(z + 1e9)
    scaled, _ = values(z * 3)
    spaced, _ = values(z, 2000)
    for key in MORPHOLOGY: assert shifted[key] == pytest.approx(f[key], rel=1e-7, abs=1e-10)
    for key in ('hypsometric_integral', 'roughness_ratio'): assert scaled[key] == pytest.approx(f[key])
    assert scaled['curvature_std_per_km'] == pytest.approx(3 * f['curvature_std_per_km'])
    assert spaced['curvature_std_per_km'] == pytest.approx(f['curvature_std_per_km'] / 4)


def test_measured_support_missing_centers_and_undefined_flat_ratios():
    sparse = np.full((21, 21), np.nan)
    sparse[9:12, 9:12] = np.arange(9).reshape(3, 3)
    before = sparse.copy()
    features, support = morphology_features(sparse, 1000)
    np.testing.assert_array_equal(sparse, before)
    assert features['hypsometric_integral']['value'] == pytest.approx(.5)
    assert features['roughness_ratio'] == {'value': None, 'data_status': 'derived', 'comparable': False}
    assert support['roughness_paired_centers'] == 0
    flat, support = morphology_features(np.zeros((20, 20)), 1000)
    assert flat['hypsometric_integral']['value'] is None
    assert flat['roughness_ratio']['value'] is None
    assert not flat['roughness_ratio']['comparable']
    assert flat['curvature_std_per_km']['value'] == 0
    assert flat['curvature_std_per_km']['comparable']
    assert set(support['null_reasons']) == {'hypsometric_integral', 'roughness_ratio'}
    empty, _ = morphology_features(np.full((20, 20), np.nan), 500)
    assert all(f['value'] is None and not f['comparable'] for f in empty.values())


def test_quadratic_fits_require_measured_center_and_full_rank():
    y, x = np.mgrid[:25, :25]
    z = (x*x + y*y).astype(float)
    z[12, 12] = np.nan
    f, support = values(z)
    assert support['measured_samples'] == 624
    assert support['curvature_centers'] <= 23*23 - 1
    assert f['curvature_std_per_km'] == pytest.approx(0, abs=1e-12)
    # Six samples on just two rows cannot identify all six quadratic coefficients.
    z = np.full((3, 3), np.nan); z[:2] = 1
    f, support = values(z)
    assert f['curvature_std_per_km'] is None
    assert support['curvature_centers'] == 0


@pytest.mark.parametrize('array,spacing', [(np.ones((2, 4)), 10), (np.ones(10), 10), (np.ones((4, 4)), 0), (np.ones((4, 4)), np.nan)])
def test_invalid_metric_inputs(array, spacing):
    with pytest.raises(ValueError): morphology_features(array, spacing)


def test_counts_crop_preserves_exact_native_pixels_and_rejects_half_pixel_shift(tmp_path):
    request = fixture_dem(tmp_path)
    counts = tmp_path/'counts.tif'
    with rasterio.open(request.path) as src:
        profile = src.profile.copy()
        for key in ('blockxsize', 'blockysize'): profile.pop(key, None)
    profile.update(width=20, height=20, dtype='int16', nodata=None, transform=from_origin(-5000, 5000, 500, 500))
    support = np.ones((20, 20), dtype='int16'); support[5, 6] = 0
    with rasterio.open(counts, 'w', **profile) as dst: dst.write(support, 1)
    result = measured_window(request.path, counts, crs=profile['crs'], transform=profile['transform'], shape=(20, 20), vertical_unit='m')
    yy, xx = np.mgrid[10:30, 10:30]
    expected = (3*xx + 4*yy)*2 - 100.0; expected[5, 6] = np.nan
    np.testing.assert_allclose(result, expected, equal_nan=True)
    with rasterio.open(counts, 'r+') as dst: dst.transform = from_origin(-4750, 5000, 500, 500)
    with pytest.raises(ValueError, match='align exactly'):
        measured_window(request.path, counts, crs=profile['crs'], transform=profile['transform'], shape=(20, 20), vertical_unit='m')


def test_process_dem_adds_features_without_recomputing_original_criteria(tmp_path):
    request = replace(fixture_dem(tmp_path), synthetic=False)
    record, array = process_dem(request)
    old = terrain_features(array, record['analysis_resolution_m'], False, 'derived')
    assert {key: record['features'][key] for key in TOPOGRAPHIC} == old
    assert set(MORPHOLOGY).issubset(record['features'])
    assert all(record['features'][key]['data_status'] == 'derived' and record['features'][key]['comparable'] for key in MORPHOLOGY)
    assert record['quality']['morphology']['source_support'] == 'finite source DEM samples; no added infill'
    assert record['resolution_validated'] is False
    path = tmp_path/'grid.parquet'
    regional = {**record, 'scale': 'regional', 'heightmap': {'path':'x.png', 'metadata_path':'x.json'}}
    write_earth_grid([regional], path)
    table = pq.read_table(path)
    assert set(MORPHOLOGY).issubset(table.column_names)
    assert all(table.schema.field(key).type == pa.float64() for key in MORPHOLOGY)
    assert 'morphology_metadata_json' in table.column_names


@pytest.mark.parametrize('body', ['mars', 'moon'])
def test_real_planet_without_counts_does_not_publish_interpolated_morphology(tmp_path, body):
    request = replace(fixture_dem(tmp_path, body), synthetic=False)
    record, array = process_dem(request)
    assert np.isfinite(array).all()  # The display/legacy DEM is still present.
    for key in MORPHOLOGY:
        assert record['features'][key] == {'value': None, 'data_status': 'derived', 'comparable': False}
    assert 'counts raster required' in record['quality']['morphology']['source_support']


def test_offline_backfill_is_idempotent_and_preserves_legacy_data(tmp_path):
    root = tmp_path/'processing'; raw = root/'raw'; raw.mkdir(parents=True)
    request = replace(fixture_dem(raw), synthetic=False)
    record, _ = process_dem(request)
    old = legacy_record(record)
    old['measurement_support'] = {'sensitivity': {'curvature_std_per_km': {'pass': False}}}
    output = root/'out'; output.mkdir()
    path = output/'features.json'; path.write_text(json.dumps({'records':[old]}))
    review_path = output/'target_quality.json'
    original_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    review_path.write_text(json.dumps({'features_file_sha256': original_hash, 'decisions': [{'resolution_validated': False}]}))
    args = dict(json_files=('out/features.json',), parquet_files=(), write=True)
    report = enrich(root, **args)
    delivered = json.loads(path.read_text())['records'][0]
    assert legacy_record(delivered) == old
    assert delivered['features']['curvature_std_per_km']['value'] is not None
    assert delivered['features']['curvature_std_per_km']['comparable'] is False
    assert report['artifacts'][0]['legacy_fields_preserved']
    first = path.read_bytes()
    review = json.loads(review_path.read_text())
    assert review['features_file_sha256'] == hashlib.sha256(first).hexdigest()
    assert review['morphology_enrichment']['prior_features_file_sha256'] == original_hash
    assert review['decisions'] == [{'resolution_validated': False}]
    first_review = review_path.read_bytes()
    enrich(root, **args)
    assert path.read_bytes() == first
    assert review_path.read_bytes() == first_review
    with pytest.raises(ValueError, match='does not bind'):
        bind_unchanged_review(json.loads(path.read_text()), {**review, 'features_file_sha256': '0'*64}, '1'*64)
    # Do not overwrite a single artifact if any raw input has changed.
    with rasterio.open(request.path, 'r+') as dst:
        array = dst.read(1); array[0, 0] += 1; dst.write(array, 1)
    with pytest.raises(FileNotFoundError, match='hash-matching'): enrich(root, **args)
    assert path.read_bytes() == first


def test_delivered_descriptors_have_consistent_contract_and_measured_jezero_window():
    root = Path(__file__).resolve().parents[1]
    for name in JSON_FILES:
        for record in json.loads((root/name).read_text())['records']:
            support = record['quality']['morphology']
            assert support['interpolation'] == 'none'
            assert support['spacing_m'] == record['analysis_resolution_m']
            assert support['window_shape'] == [round(record['window_km']*1000/record['analysis_resolution_m'])]*2
            if record['body'] in ('mars', 'moon'):
                assert support['source_support'] == 'counts > 0 before reprojection'
            for field in MORPHOLOGY:
                item = record['features'][field]
                assert item['data_status'] == 'derived'
                check = record.get('measurement_support', {}).get('sensitivity', {}).get(field, {'pass': True})
                assert item['comparable'] == (item['value'] is not None and check['pass'])
                if item['value'] is None:
                    assert field in support['null_reasons']
                else:
                    assert np.isfinite(item['value']) and item['value'] >= 0
    for name in PARQUET_FILES:
        table = pq.read_table(root/name)
        for field in MORPHOLOGY:
            assert table.schema.field(field).type == pa.float64()
            for value, status, comparable in zip(table[field].to_pylist(), table[field+'__status'].to_pylist(), table[field+'__comparable'].to_pylist()):
                assert status == 'derived' and comparable == (value is not None)
    def jezero(name):
        return next(r for r in json.loads((root/name).read_text())['records'] if r['region_id'] == 'mars_jezero_regional')
    curated, measured = jezero('out/real/features.json'), jezero('out/mars_measured/features.json')
    # Both routes use the same measured-only window, although their legacy metrics differ.
    assert {k: curated['features'][k]['value'] for k in MORPHOLOGY} == {k: measured['features'][k]['value'] for k in MORPHOLOGY}
