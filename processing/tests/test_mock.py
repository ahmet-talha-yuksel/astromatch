import json
import struct
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import pytest
from PIL import Image

from processing.scripts import generate_mock as generator

@pytest.fixture()
def generated(tmp_path):
    return tmp_path, generator.generate(tmp_path)


def test_v23_contract_and_comparability(generated):
    path, payload = generated
    assert json.loads((path / 'features.json').read_text()) == payload
    assert payload['schema_version'] == '2.3'
    records = payload['records']
    assert len({r['region_id'] for r in records}) == len(records)
    assert {r['body'] for r in records} == {'earth', 'mars', 'moon'}
    assert any(not r['resolution_validated'] for r in records)
    for r in records:
        assert r['schema_version'] == '2.3' and r['data_status'] == 'mock'
        assert r['synthetic'] is True
        assert r['kind'] == ('candidate' if r['body'] == 'earth' else 'target')
        assert (r['window_km'], r['analysis_resolution_m']) == (
            (10, 500) if r['scale'] == 'local' else (50, 1000))
        assert '+proj=laea' in r['crs']
        assert r['dem_source'] == 'synthetic analytic surface'
        for name in generator.TOPOGRAPHIC:
            f = r['features'][name]
            assert set(f) == {'value', 'data_status', 'comparable'}
            assert f['data_status'] == 'mock' and np.isfinite(f['value'])
            assert f['comparable'] is r['resolution_validated']
        if not r['resolution_validated']:
            assert r['quality']['warnings']
        temp = r['features']['surface_temp_diurnal_range_c']
        assert temp['value'] is None and temp['comparable'] is False
        assert temp['comparability_note']
        assert not any('ndvi' in k for k in r['features'])
        if r['body'] == 'earth':
            assert set(r['earth_filters']) == {'ndvi_mean', 'precip_mm_yr', 'land_fraction'}
            for f in r['earth_filters'].values():
                assert f['data_status'] == 'mock' and f['comparable'] is False
        else:
            assert r['earth_filters'] is None
    assert generator.feature(None, validated=True)['comparable'] is False


def test_flattened_parquet_matches_earth_regional(generated):
    path, payload = generated
    table = pq.read_table(path / 'earth_grid.parquet')
    assert table.schema.metadata[b'schema_version'] == b'2.3'
    expected = [generator.flatten(r) for r in payload['records']
                if r['body'] == 'earth' and r['scale'] == 'regional']
    assert table.to_pylist() == expected
    assert 'features' not in table.column_names
    assert 'slope_median_deg__status' in table.column_names
    assert table['surface_temp_diurnal_range_c'].null_count == 4
    assert str(table.schema.field('surface_temp_diurnal_range_c').type) == 'double'


def test_heightmaps_decode_and_metadata(generated):
    path, payload = generated
    for r in payload['records']:
        meta = r['heightmap']
        assert json.loads((path / meta['metadata_path']).read_text()) == meta
        png = path / meta['path']
        header = png.read_bytes()
        size = r['window_km'] * 1000 // r['analysis_resolution_m']
        assert header[:8] == b'\x89PNG\r\n\x1a\n'
        assert struct.unpack('>IIBB', header[16:26]) == (size, size, 16, 0)
        with Image.open(png) as image:
            pixels = np.asarray(image)
        valid = pixels != meta['NoData']
        assert not valid[0, 0] and valid.sum() == size * size - 1
        assert r['quality']['nodata_ratio'] == pytest.approx(1 / (size * size))
        assert meta['pixel_size_x_m'] == meta['pixel_size_y_m'] == r['analysis_resolution_m']
        assert size * meta['pixel_size_x_m'] == r['window_km'] * 1000
        decoded = np.where(valid, pixels.astype(float) * meta['scale'] + meta['offset'], np.nan)
        metrics = generator.terrain_features(decoded, r['analysis_resolution_m'], r['resolution_validated'])
        assert metrics['relief_m']['value'] == pytest.approx(r['features']['relief_m']['value'], abs=0.11)


def test_known_plane_and_nodata():
    y, x = np.mgrid[:10, :10]
    dem = 3.0 * x + 4.0 * y
    features = generator.terrain_features(dem, 100, True)
    angle = np.degrees(np.arctan(0.05))
    assert features['slope_median_deg']['value'] == pytest.approx(angle)
    assert features['slope_p90_deg']['value'] == pytest.approx(angle)
    assert features['flat_fraction']['value'] == 1
    assert features['tri_median_m']['value'] == pytest.approx(np.sqrt(150))
    assert features['relief_m']['value'] == pytest.approx(np.percentile(dem, 95) - np.percentile(dem, 5))
    assert features['elevation_std_m']['value'] == pytest.approx(dem.std())
    dem[0, 0] = np.nan
    assert generator.terrain_features(dem, 100, True)['slope_median_deg']['value'] == pytest.approx(angle)
    missing = generator.terrain_features(np.full((10, 10), np.nan), 100, True)
    assert all(f['value'] is None and not f['comparable'] for f in missing.values())


def test_coverage_statuses_and_links(generated):
    path, payload = generated
    collection = json.loads((path / 'coverage.geojson').read_text())
    assert collection['type'] == 'FeatureCollection'
    assert {f['properties']['status'] for f in collection['features']} == {'scanned', 'not_scanned', 'no_data'}
    ids = {r['region_id'] for r in payload['records']}
    for item in collection['features']:
        props = item['properties']
        assert props['body'] == 'earth' and props['data_status'] == 'mock'
        ring = item['geometry']['coordinates'][0]
        assert ring[0] == ring[-1]
        assert ring[2][0] - ring[0][0] == 0.5
        if props['status'] == 'scanned':
            assert props['region_id'] in ids
        if props['status'] == 'no_data':
            assert props['coverage'] == 'none'


def test_reproducible_and_checked_in(generated, tmp_path):
    path, _ = generated
    second = tmp_path / 'second'
    generator.generate(second)
    for file in path.rglob('*'):
        if not file.is_file() or second in file.parents:
            continue
        relative = file.relative_to(path)
        assert file.read_bytes() == (second / relative).read_bytes()
        assert file.read_bytes() == (generator.DEFAULT_OUT / relative).read_bytes()
