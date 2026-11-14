import hashlib
import json
from pathlib import Path
from urllib.error import HTTPError

import numpy as np
import pyarrow.parquet as pq
import pytest
import rasterio
from rasterio.transform import from_origin

from processing.scripts import acquire_pilot
from processing.scripts.acquire_pilot import cached_tile, mosaic90
from processing.scripts.pilot_grid import cells, cell_id, window_bounds
from processing.scripts.run_pilot import run, scope_for_time_range


def small_config():
    return {'grid_step_deg': .5, 'window_km': 50, 'analysis_resolution_m': 1000,
            'areas': [{'id': 'test', 'bbox': [29, 37, 30, 38],
                       'selected_centers': [[29.25, 37.25]]}]}


def test_grid_alignment_ids_and_default_reference_extent():
    assert cell_id(-179.75, -89.75) == 'earth_grid_r000_c000'
    assert cell_id(179.75, 89.75) == 'earth_grid_r359_c719'
    for lon, lat in ((29.5, 37.25), (180, 0), (0, float('nan'))):
        with pytest.raises(ValueError):
            cell_id(lon, lat)
    default = Path(__file__).resolve().parents[1] / 'configs/pilot.json'
    grid = cells(json.loads(default.read_text()))
    assert len(grid) == 408 and sum(c['selected'] for c in grid) == 8
    assert len({c['region_id'] for c in grid}) == len(grid)
    config = small_config()
    config['areas'][0]['selected_centers'] = [[29.5, 37.5]]
    with pytest.raises(ValueError):
        cells(config)


def test_high_latitude_window_is_physical_not_half_degree_cell():
    west, south, east, north = window_bounds(-19.75, 64.25)
    assert east-west > 1 and north-south < .5
    with pytest.raises(ValueError):
        window_bounds(179.9, 70)


def test_cache_snapshot_integrity(monkeypatch, tmp_path):
    data = b'verified bytes'
    evidence = {'url': 'https://example.invalid/tile', 'sha256': hashlib.sha256(data).hexdigest()}
    calls = []
    def fake_fetch(*args, **kwargs):
        calls.append(args)
        return data, dict(evidence)
    monkeypatch.setattr(acquire_pilot, 'fetch', fake_fetch)
    path = tmp_path / 'tile.tif'
    first, timing = cached_tile(evidence['url'], path, '2026-11-14')
    assert not timing['cache_hit']
    second, timing = cached_tile(evidence['url'], path, '2026-11-15')
    assert timing['cache_hit'] and timing['download_s'] == 0
    assert first == second and second['retrieved_on'] == '2026-11-14'
    assert len(calls) == 1
    path.write_bytes(b'corrupt')
    with pytest.raises(ValueError, match='integrity'):
        cached_tile(evidence['url'], path, '2026-11-15')


def test_srtm_auth_failure_recorded_without_mislabeling(monkeypatch):
    payload = {'feed': {'entry': [{'links': [{'rel': 'http://esipfed.org/ns/fedsearch/1.1/data#',
                                            'href': 'https://data.lpdaac.earthdatacloud.nasa.gov/protected.zip'}]}]}}
    def fake_fetch(url, **kwargs):
        if 'cmr.earthdata' in url:
            return json.dumps(payload).encode(), {'sha256': 'a'*64}
        raise HTTPError(url, 401, 'Unauthorized', None, None)
    monkeypatch.setattr(acquire_pilot, 'fetch', fake_fetch)
    probe = acquire_pilot.probe_srtm(29.25, 37.25)
    assert probe['http_status'] == 401 and probe['status'] == 'http_access_failed'


def test_glo90_anisotropic_high_latitude_grid_is_preserved(tmp_path):
    source, target = tmp_path/'source.tif', tmp_path/'crop.tif'
    dx, dy = 6/3600, 3/3600
    with rasterio.open(source, 'w', driver='GTiff', width=8, height=8, count=1,
                       dtype='float32', crs='EPSG:4326', transform=from_origin(-20, 65, dx, dy)) as dst:
        dst.write(np.full((8, 8), 200, dtype='float32'), 1)
    mosaic90([source], target, [-20, 65-8*dy, -20+8*dx, 65])
    with rasterio.open(target) as dst:
        assert dst.res == pytest.approx((dx, dy))
        np.testing.assert_equal(dst.read(1), 200)


@pytest.mark.parametrize('low,high,scope', [
    (1, 3, 'all_available_land'), (2, 3.1, 'priority_land_and_usgs'),
    (7, 8, 'priority_land_and_usgs'), (8, 9, 'turkey_surroundings_usgs_and_sample_arid_belts')])
def test_conservative_gate_boundaries(low, high, scope):
    assert scope_for_time_range(low, high) == scope


def test_pilot_unknown_and_no_data_are_distinct(tmp_path):
    config = small_config()
    cell = next(c for c in cells(config) if c['selected'])
    manifest = {'config': config, 'accessed_on': '2026-11-14', 'inputs': [], 'srtm_probes': {},
                'landmask': {'status': 'not_run', 'duration_s': None},
                'attempts': [dict(cell, status='no_data', path=None, timing={},
                                  source_selection='srtm_access_unavailable')]}
    acquisition = tmp_path/'acquisition.json'
    acquisition.write_text(json.dumps(manifest))
    report = run(acquisition, tmp_path, tmp_path/'out')
    coverage = json.loads((tmp_path/'out/coverage.geojson').read_text())['features']
    statuses = [f['properties']['status'] for f in coverage]
    assert statuses.count('no_data') == 1 and statuses.count('not_scanned') == 3
    assert report['records_written'] == 0
    assert report['global_decision']['status'] == 'deferred'
    assert report['global_decision']['estimated_hours_range'] is None
    assert pq.read_table(tmp_path/'out/earth_grid.parquet').num_rows == 0


def test_pilot_real_window_has_stage_timing_and_null_landmask(tmp_path):
    from processing.tests.test_dem import fixture_dem
    from dataclasses import replace
    from processing.scripts.dem import process_dem
    request = fixture_dem(tmp_path)
    timer = {}
    record, _ = process_dem(replace(request, scale='regional', analysis_resolution_m=1000), timings=timer)
    assert timer['processing_wall_s'] >= timer['reprojection_s'] + timer['feature_extraction_s']
    assert all(v >= 0 for v in timer.values())
    assert 'processing_wall_s' not in record


@pytest.mark.parametrize('low,high', [(-1, 2), (3, 2), (1, float('inf')), (float('nan'), 3)])
def test_gate_rejects_invalid_estimates(low, high):
    with pytest.raises(ValueError):
        scope_for_time_range(low, high)


def test_shared_real_pilot_outputs_are_offline_readable():
    from PIL import Image
    root = Path(__file__).resolve().parents[1] / 'out/pilot'
    records = json.loads((root/'features.json').read_text())['records']
    assert len(records) == 8
    assert {r['grid']['pilot_area'] for r in records} == {'turkey', 'atacama', 'iceland'}
    for r in records:
        assert r['region_id'] == cell_id(r['lon'], r['lat'])
        assert r['window_km'] == 50 and r['analysis_resolution_m'] == 1000
        assert not r['synthetic'] and r['data_status'] == 'derived'
        assert r['dem_source'] == 'copernicus_glo90'
        assert not r['resolution_validated']
        assert all(f['value'] is not None and not f['comparable'] for f in r['features'].values())
        assert r['earth_filters']['land_fraction']['value'] is None
        meta = r['heightmap']
        with Image.open(root/meta['path']) as image:
            pixels = np.asarray(image)
        assert pixels.shape == (50, 50) and (pixels != meta['NoData']).all()
        z = pixels.astype(float)*meta['scale']+meta['offset']
        assert np.percentile(z, 95)-np.percentile(z, 5) == pytest.approx(
            r['features']['relief_m']['value'], abs=meta['scale']+1e-6)
    table = pq.read_table(root/'earth_grid.parquet')
    assert table.num_rows == 8
    assert str(table.schema.field('land_fraction').type) == 'double'
    assert table['land_fraction'].null_count == 8
    coverage = json.loads((root/'coverage.geojson').read_text())['features']
    assert len(coverage) == 408
    assert sum(f['properties']['status'] == 'scanned' for f in coverage) == 8
    assert sum(f['properties']['status'] == 'not_scanned' for f in coverage) == 400
    for f in coverage:
        ring = f['geometry']['coordinates'][0]
        assert ring[0] == ring[-1]
        assert ring[2][0]-ring[0][0] == .5
        assert ring[2][1]-ring[0][1] == .5
    timing = json.loads((root/'pilot_timing.json').read_text())
    assert timing['global_decision']['status'] == 'deferred'
    assert timing['global_decision']['estimated_hours_range'] is None
    assert timing['landmask']['duration_s'] is None
    assert timing['dem_sources_measured'] == ['copernicus_glo90']
    for item in timing['measurements']:
        assert all(v >= 0 for v in item['processing'].values())
        assert item['processing']['processing_wall_s'] >= item['processing']['feature_extraction_s']
        assert all(v >= 0 for v in item['acquisition'].values())
