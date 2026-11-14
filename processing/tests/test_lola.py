import numpy as np
import pytest
from pyproj import CRS, Transformer

from processing.scripts.acquire_lola import decode_lola, verify_label


def test_lola_height_is_half_dn_without_radius_offset():
    dn = np.array([[-200, 0], [200, 1000]], dtype='<i2')
    decoded, transform = decode_lola(dn.tobytes(), size=2)
    np.testing.assert_equal(decoded * .5, [[-100, 0], [100, 500]])
    assert transform @ (1, 1) == (0, 0)
    assert transform @ (.5, .5) == (-120, 120)
    assert decoded.dtype == np.dtype('int16')


def test_lola_rejects_wrong_layout_and_special_values():
    with pytest.raises(ValueError, match='Truncated'):
        decode_lola(b'\0', size=2)
    with pytest.raises(ValueError, match='samples'):
        decode_lola(np.full((2, 2), -32768, dtype='<i2').tobytes(), size=2)
    with pytest.raises(ValueError, match='Unexpected'):
        verify_label('NAME = RADIUS')


def test_south_polar_stereographic_orientation_matches_catalog():
    crs = CRS.from_proj4('+proj=stere +lat_0=-90 +lat_ts=-90 +lon_0=0 +R=1737400 +units=m')
    project = Transformer.from_crs(crs.geodetic_crs, crs, always_xy=True)
    x, y = project.transform(0, -89)
    assert x == pytest.approx(0, abs=1e-8) and y > 0
    x, y = project.transform(90, -89)
    assert x > 0 and y == pytest.approx(0, abs=1e-8)
    distance = 2*1737400*np.tan(np.radians(1)/2)
    assert x == pytest.approx(distance)


def test_generic_reader_rejects_radius_band_as_height(tmp_path):
    import rasterio
    from processing.scripts.dem import process_dem
    from processing.tests.test_dem import fixture_dem
    request = fixture_dem(tmp_path, 'moon')
    with rasterio.open(request.path, 'r+') as src:
        src.offsets = (1737400.0,)
    with pytest.raises(ValueError, match='planetary radius'):
        process_dem(request)


def test_real_lola_and_combined_outputs():
    import json
    from pathlib import Path
    from PIL import Image
    import pyarrow.parquet as pq
    root = Path(__file__).resolve().parents[1] / 'out'
    records = json.loads((root / 'real/features.json').read_text())['records']
    assert len(records) == 21
    assert len({r['region_id'] for r in records}) == 21
    assert {r['body'] for r in records} == {'earth', 'mars', 'moon'}
    for r in records:
        assert not r['synthetic'] and r['resolution_validated'] is (r['body'] == 'earth' or 'shackleton' in r['region_id'])
        assert all(f['data_status'] == 'derived' and f['comparable'] is (r['body'] == 'earth' or 'shackleton' in r['region_id']) for f in r['features'].values())
    moons = [r for r in records if 'shackleton' in r['region_id']]
    assert len(moons) == 2
    for r in moons:
        assert (r['lat'], r['lon']) == (-89.67, 129.78)
        assert r['provenance']['band_scale'] == .5
        assert r['provenance']['band_offset'] == 0
        assert r['quality']['nodata_ratio'] == 0
        assert r['provenance']['source_quality_verified']
        assert r['quality']['qa_validation']['status'] == 'passed'
        meta = r['heightmap']
        assert json.loads((root / 'real' / meta['metadata_path']).read_text()) == meta
        with Image.open(root / 'real' / meta['path']) as image:
            pixels = np.asarray(image)
        z = pixels.astype(float)*meta['scale'] + meta['offset']
        assert np.max(np.abs(z)) < 10000  # radius-offset regression protection
        relief = np.percentile(z, 95) - np.percentile(z, 5)
        assert relief == pytest.approx(r['features']['relief_m']['value'], abs=meta['scale'] + 1e-6)
        assert pixels.shape == ((20, 20) if r['scale'] == 'local' else (50, 50))
    assert pq.read_table(root / 'real/earth_grid.parquet').num_rows == 8
    manifests = json.loads((root / 'real/retrieval.json').read_text())['datasets']
    assert len(manifests) == 8
    assert sum(len(m.get('inputs', [])) for m in manifests) > 20
    srtm=next(m for m in manifests if m.get('product','').startswith('SRTMGL30'))
    assert len(srtm['imported'])==4
    assert all(len(item['source_zip_sha256'])==64 for item in srtm['imported'])
    assert any(isinstance(m.get('conversion'),dict) and m['conversion'].get('stored_band_offset_m')==0 for m in manifests)
