import numpy as np
from pyproj import CRS, Transformer
import pytest
import rasterio
from rasterio.transform import from_origin

from processing.scripts.acquire_earth_sites import tile_name, footprint_bounds, covering_tiles, mosaic
from processing.scripts.metrics import TOPOGRAPHIC


def test_signed_tile_names_and_boundary_coverage():
    assert tile_name(-25, -70) == 'Copernicus_DSM_COG_10_S25_00_W070_00_DEM'
    assert tile_name(38, 28) == 'Copernicus_DSM_COG_10_N38_00_E028_00_DEM'
    assert covering_tiles([-70.1, -24.1, -69.8, -23.8]) == [(-25, -71), (-25, -70), (-24, -71), (-24, -70)]
    assert covering_tiles([28, 38, 29, 39]) == [(38, 28)]


def test_physical_window_bounds_enclose_all_corners():
    lat, lon = -24.063777777777776, -69.8805
    west, south, east, north = footprint_bounds(lat, lon)
    crs = CRS.from_proj4(f'+proj=laea +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m')
    inverse = Transformer.from_crs(crs, 'EPSG:4326', always_xy=True)
    for x in (-25000, 0, 25000):
        for y in (-25000, 0, 25000):
            xx, yy = inverse.transform(x, y)
            assert west < xx < east and south < yy < north
    with pytest.raises(ValueError):
        footprint_bounds(85, 30)


def test_mosaic_preserves_both_sides_and_masks_nodata(tmp_path):
    step = 1/3600
    paths = []
    for index in (0, 1):
        path = tmp_path / f'{index}.tif'
        data = np.full((4, 4), (index + 1)*100, dtype='float32')
        if index == 0:
            data[-1, 0] = -9999
        with rasterio.open(path, 'w', driver='GTiff', width=4, height=4, count=1,
                           dtype='float32', nodata=-9999, crs='EPSG:4326',
                           transform=from_origin(index*4*step, 1, step, step)) as dst:
            dst.write(data, 1)
        paths.append(path)
    dest = tmp_path / 'crop.tif'
    assert mosaic(paths, dest, [0, 1-4*step, 8*step, 1]) == (4, 8)
    with rasterio.open(dest) as src:
        data = src.read(1)
        assert np.isnan(data[-1, 0])
        np.testing.assert_equal(data[:3, :4], 100)
        np.testing.assert_equal(data[:, 4:], 200)
        assert src.units == ('m',)
        assert src.res == pytest.approx((step, step))


def test_config_merge_preserves_relative_paths_and_rejects_duplicates(tmp_path):
    import json
    from processing.scripts.combine_configs import combine
    source = tmp_path / 'source'
    source.mkdir()
    config = source / 'config.json'
    record = {'region_id': 'earth_example', 'path': 'example.tif', 'counts_path': 'counts.tif', 'qa_report_path': 'qa.json'}
    config.write_text(json.dumps({'records': [record], 'retrieval_manifest': 'retrieval.json'}))
    destination = tmp_path / 'nested' / 'combined.json'
    result = combine([config], destination)
    for key in ('path', 'counts_path', 'qa_report_path'):
        assert (destination.parent / result['records'][0][key]).resolve() == (source / record[key]).resolve()
    assert (destination.parent / result['retrieval_manifests'][0]).resolve() == source / 'retrieval.json'
    before = destination.read_bytes()
    with pytest.raises(ValueError, match='Duplicate'):
        combine([config, config], destination)
    assert destination.read_bytes() == before


def test_real_four_site_deliverable_is_readable_and_cautious():
    import json
    from pathlib import Path
    import pyarrow.parquet as pq
    from PIL import Image
    root = Path(__file__).resolve().parents[1] / 'out'
    records = json.loads((root / 'real/features.json').read_text())['records']
    earth = [r for r in records if r['body'] == 'earth']
    assert {r['region_id'] for r in earth} == {
        f'earth_{name}_{scale}' for name in ('salda', 'kula', 'hassa', 'atacama', 'meke', 'tuz_golu', 'haughton', 'meteor_crater')
        for scale in ('local', 'regional')}
    for r in earth:
        assert r['quality']['nodata_ratio'] == 0 and r['quality']['coverage'] == 'full'
        assert r['data_status'] == 'derived' and not r['synthetic']
        assert r['resolution_validated']
        assert all(r['features'][key]['comparable'] and r['features'][key]['value'] is not None for key in TOPOGRAPHIC)
        meta = r['heightmap']
        with Image.open(root / 'real' / meta['path']) as image:
            pixels = np.asarray(image)
        assert (pixels != meta['NoData']).all()
        z = pixels.astype(float)*meta['scale']+meta['offset']
        relief = np.percentile(z, 95)-np.percentile(z, 5)
        assert relief == pytest.approx(r['features']['relief_m']['value'], abs=meta['scale']+1e-6)
        if 'hassa' in r['region_id']:
            assert any('not a verified cave' in w for w in r['quality']['warnings'])
        if 'atacama' in r['region_id']:
            assert any('not a labeled negative' in w for w in r['quality']['warnings'])
    rows = pq.read_table(root / 'real/earth_grid.parquet').to_pylist()
    assert {r['region_id'] for r in rows} == {r['region_id'] for r in earth if r['scale'] == 'regional'}
    coverage = json.loads((root / 'real/coverage.geojson').read_text())['features']
    assert {f['properties']['region_id'] for f in coverage} == {r['region_id'] for r in rows}
    acquisition = json.loads((root / 'earth_sites/retrieval.json').read_text())
    assert len(acquisition['inputs']) == 7 and len(acquisition['windows']) == 3
    assert all(len(item['sha256']) == 64 for item in acquisition['inputs'])
