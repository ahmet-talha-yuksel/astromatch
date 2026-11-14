from dataclasses import replace
import json

import numpy as np
import pyarrow.parquet as pq
import pytest
from PIL import Image
import rasterio
from rasterio.transform import from_origin

from processing.scripts.dem import DemRequest, process_dem, validate_comparison, RADII
from processing.scripts.metrics import terrain_features
from processing.scripts.process_dem import run, export_heightmap


def fixture_dem(tmp_path, body='earth', **overrides):
    lat, lon = (37.5, 29.7) if body == 'earth' else ((18.38, 77.58) if body == 'mars' else (-89.5, 0))
    crs = f'+proj=laea +lat_0={lat} +lon_0={lon} +R={RADII[body]} +units=m'
    path = tmp_path / f'{body}.tif'
    y, x = np.mgrid[:40, :40]
    profile = dict(driver='GTiff', width=40, height=40, count=1, dtype='float64',
                   crs=crs, transform=from_origin(-10000, 10000, 500, 500), nodata=-9999)
    profile.update(overrides)
    with rasterio.open(path, 'w', **profile) as dst:
        dst.write((3.0*x + 4.0*y)[None])
        dst.scales = (2.0,)
        dst.offsets = (-100.0,)
    return DemRequest(str(path), f'{body}_fixture', 'synthetic fixture', body,
                      {'earth': 'copernicus', 'mars': 'mola', 'moon': 'lola'}[body],
                      lat, lon, 'local', 500, 'm', 'synthetic local datum',
                      'https://example.invalid/synthetic', 'synthetic-1', '2026-11-14', synthetic=True)


@pytest.mark.parametrize('body', ['earth', 'mars', 'moon'])
def test_metric_window_body_scale_offset(tmp_path, body):
    request = fixture_dem(tmp_path, body)
    record, array = process_dem(request)
    assert array.shape == (20, 20)
    assert record['window_km'] == 10
    assert record['quality']['coverage'] == 'full'
    assert not record['resolution_validated']  # no paired Earth/target yet
    y, x = np.mgrid[10:30, 10:30]
    np.testing.assert_allclose(array, (3*x + 4*y)*2 - 100, atol=1e-6)
    assert record['features']['slope_median_deg']['value'] == pytest.approx(np.degrees(np.arctan(10/500)))
    assert all(f['data_status'] == 'mock' for f in record['features'].values())


def test_geographic_source_is_reprojected_before_metrics(tmp_path):
    request = fixture_dem(tmp_path, crs='EPSG:4326',
                          transform=from_origin(29.62, 37.58, .004, .004))
    record, array = process_dem(replace(request, source_resolution_m=450))
    assert record['quality']['coverage'] == 'full'
    assert array.shape == (20, 20)
    assert 'Lambert Azimuthal Equal Area' in record['crs']
    assert np.isfinite(record['features']['slope_median_deg']['value'])


@pytest.mark.parametrize('change,match', [
    ({'body': 'mars'}, 'Product/body'),
    ({'vertical_unit': 'feet'}, 'vertical unit'),
    ({'quantity': 'radius'}, 'not elevation'),
    ({'source_resolution_m': 1001}, 'Upsampling'),
    ({'analysis_resolution_m': 0}, 'positive'),
    ({'analysis_resolution_m': 300}, 'divide'),
    ({'region_id': '../unsafe'}, 'safe filename'),
])
def test_invalid_requests_fail(tmp_path, change, match):
    request = fixture_dem(tmp_path)
    with pytest.raises(ValueError, match=match):
        process_dem(replace(request, **change))


def test_missing_and_wrong_crs(tmp_path):
    request = fixture_dem(tmp_path, crs=None)
    with pytest.raises(ValueError, match='CRS is missing'):
        process_dem(request)
    request = fixture_dem(tmp_path, 'mars', crs='EPSG:4326')
    with pytest.raises(ValueError, match='radius'):
        process_dem(request)


def test_nodata_never_becomes_offset_elevation(tmp_path):
    request = fixture_dem(tmp_path)
    with rasterio.open(request.path, 'r+') as dst:
        a = dst.read(1)
        a[10:20, 10:20] = -9999
        dst.write(a, 1)
    record, array = process_dem(request)
    assert np.isnan(array[:10, :10]).all()
    assert record['quality']['nodata_ratio'] == pytest.approx(.25)
    assert not record['quality']['validation_eligible']
    assert record['quality']['warnings']
    assert record['features']['relief_m']['value'] is not None


def test_internal_hole_and_sparse_metrics():
    dem = np.full((5, 7), np.nan)
    dem[2, 2], dem[2, 3] = 10, 20
    features = terrain_features(dem, 500, True, 'derived')
    assert features['slope_median_deg']['value'] is None
    assert features['tri_median_m']['value'] is None
    assert features['relief_m']['value'] == pytest.approx(9)
    assert features['elevation_std_m']['value'] == 5
    dem = np.zeros((5, 7))
    dem[2, 3] = np.nan
    assert terrain_features(dem, 500, True)['flat_fraction']['value'] == 1


def test_pair_validation_and_revalidation(tmp_path):
    earth, _ = process_dem(fixture_dem(tmp_path))
    mars, _ = process_dem(fixture_dem(tmp_path, 'mars'))
    validate_comparison([earth, mars])
    assert earth['resolution_validated'] and mars['resolution_validated']
    assert all(f['comparable'] for f in earth['features'].values())
    mars['analysis_resolution_m'] = 1000
    validate_comparison([earth, mars])
    assert not earth['resolution_validated'] and not mars['resolution_validated']
    assert all(not f['comparable'] for f in earth['features'].values())


def test_empty_window_has_null_values(tmp_path):
    request = fixture_dem(tmp_path)
    record, array = process_dem(replace(request, lat=-30, lon=-70))
    assert np.isnan(array).all()
    assert record['quality']['coverage'] == 'none'
    assert all(f['value'] is None and not f['comparable'] for f in record['features'].values())


def test_heightmap_quantization(tmp_path):
    request = fixture_dem(tmp_path)
    record, array = process_dem(request)
    array[0, 0] = np.nan
    array[-1, -1] = 20000  # forces adaptive scale
    export_heightmap(tmp_path, record, array)
    meta = record['heightmap']
    with Image.open(tmp_path / meta['path']) as image:
        pixels = np.asarray(image)
    assert pixels[0, 0] == meta['NoData']
    valid = np.isfinite(array)
    assert np.all(pixels[valid] != meta['NoData'])
    np.testing.assert_allclose(pixels[valid] * meta['scale'] + meta['offset'],
                               array[valid], atol=meta['scale']/2 + 1e-8, rtol=0)


def test_batch_outputs_readable_and_repeatable(tmp_path):
    from dataclasses import asdict
    earth = replace(fixture_dem(tmp_path), scale='regional', analysis_resolution_m=1000)
    mars = replace(fixture_dem(tmp_path, 'mars'), scale='regional', analysis_resolution_m=1000)
    config = tmp_path / 'config.json'
    config.write_text(json.dumps({'records': [asdict(earth), asdict(mars)]}))
    out = tmp_path / 'out'
    records = run(config, out)
    assert json.loads((out / 'features.json').read_text())['records'] == records
    rows = pq.read_table(out / 'earth_grid.parquet').to_pylist()
    assert len(rows) == 1 and rows[0]['body'] == 'earth'
    assert rows[0]['slope_median_deg__status'] == 'mock'
    assert json.loads((out / 'coverage.geojson').read_text())['features'][0]['properties']['data_status'] == 'mock'
    assert 'synthetic' in (out / 'DATA_SOURCES.md').read_text().lower()
    before = {p.relative_to(out): p.read_bytes() for p in out.rglob('*') if p.is_file()}
    run(config, out)
    assert before == {p.relative_to(out): p.read_bytes() for p in out.rglob('*') if p.is_file()}


def test_pds3_label_and_binary_image(tmp_path):
    # Small synthetic PDS3 fixture: tests GDAL PDS driver, not NASA observations.
    image = tmp_path / 'dem.img'
    np.arange(1600, dtype='>i2').tofile(image)
    label = tmp_path / 'dem.lbl'
    label.write_text('''PDS_VERSION_ID = PDS3
RECORD_TYPE = FIXED_LENGTH
RECORD_BYTES = 80
FILE_RECORDS = 40
^IMAGE = "dem.img"
OBJECT = IMAGE
 LINES = 40
 LINE_SAMPLES = 40
 SAMPLE_TYPE = MSB_INTEGER
 SAMPLE_BITS = 16
 SCALING_FACTOR = 0.5
 OFFSET = -100.0
END_OBJECT = IMAGE
OBJECT = IMAGE_MAP_PROJECTION
 MAP_PROJECTION_TYPE = "EQUIRECTANGULAR"
 A_AXIS_RADIUS = 3396.19 <KM>
 B_AXIS_RADIUS = 3396.19 <KM>
 C_AXIS_RADIUS = 3396.19 <KM>
 CENTER_LATITUDE = 0.0
 CENTER_LONGITUDE = 0.0
 LINE_PROJECTION_OFFSET = 19.5
 SAMPLE_PROJECTION_OFFSET = 19.5
 MAP_SCALE = 0.5 <KM/PIXEL>
 COORDINATE_SYSTEM_TYPE = "BODY-FIXED ROTATING"
 POSITIVE_LONGITUDE_DIRECTION = "EAST"
END_OBJECT = IMAGE_MAP_PROJECTION
END
''')
    request = DemRequest(str(label), 'pds_fixture', 'Synthetic PDS', 'mars', 'mola',
                         0, 0, 'local', 500, 'm', 'synthetic areoid',
                         'https://example.invalid/pds', 'test', '2026-11-14', synthetic=True)
    record, array = process_dem(request)
    assert array.shape == (20, 20) and np.isfinite(array).all()
    assert record['provenance']['band_scale'] == .5
    assert record['provenance']['band_offset'] == -100
    assert array.min() > 0 and array.max() < 700


def test_real_products_require_explicit_quality_review(tmp_path):
    request = replace(fixture_dem(tmp_path), synthetic=False)
    record, _ = process_dem(request)
    assert all(f['data_status'] == 'derived' for f in record['features'].values())
    assert not record['quality']['validation_eligible']
    assert not record['resolution_validated']
    assert any('review' in w for w in record['quality']['warnings'])
