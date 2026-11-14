"""Offline checks on the small committed real-data deliverable; no raw DEM needed."""
import json
from pathlib import Path
import struct

import numpy as np
import pyarrow.parquet as pq
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1] / 'out' / 'salda_jezero'


def test_real_bundle_contract_and_sampling_warnings():
    payload = json.loads((ROOT / 'features.json').read_text())
    assert payload['schema_version'] == '2.3'
    records = payload['records']
    assert len(records) == 4
    assert {(r['body'], r['scale']) for r in records} == {
        ('earth', 'local'), ('earth', 'regional'), ('mars', 'local'), ('mars', 'regional')}
    for r in records:
        assert r['synthetic'] is False and r['data_status'] == 'derived'
        assert r['quality']['nodata_ratio'] == 0
        assert len(r['provenance']['source_file_sha256']) == 64
        # Sampling review has not passed; do not expose these as score-ready.
        assert r['resolution_validated'] is False
        assert r['quality']['warnings']
        for f in r['features'].values():
            assert f['data_status'] == 'derived' and f['comparable'] is False
            assert f['value'] is not None
        if r['body'] == 'mars':
            sampling = r['quality']['sampling']
            assert 0 < sampling['mean_observed_bin_fraction'] < 1
            assert sampling['analysis_cells_without_observed_bins'] > 0
    rows = pq.read_table(ROOT / 'earth_grid.parquet').to_pylist()
    assert len(rows) == 1 and rows[0]['region_id'] == 'earth_salda_regional'
    assert rows[0]['slope_median_deg__status'] == 'derived'
    assert json.loads((ROOT / 'coverage.geojson').read_text())['features'][0]['properties']['status'] == 'scanned'


def test_real_png_round_trip_and_reference_geometry():
    records = json.loads((ROOT / 'features.json').read_text())['records']
    for r in records:
        m = json.loads((ROOT / r['heightmap']['metadata_path']).read_text())
        png = ROOT / m['path']
        assert struct.unpack('>IIBB', png.read_bytes()[16:26]) == (m['width'], m['height'], 16, 0)
        with Image.open(png) as im:
            pixels = np.asarray(im)
        assert (pixels != m['NoData']).all()
        z = pixels.astype(float) * m['scale'] + m['offset']
        relief = np.percentile(z, 95) - np.percentile(z, 5)
        assert relief == pytest.approx(r['features']['relief_m']['value'], abs=m['scale'] + 1e-6)
        assert m['width'] * m['pixel_size_x_m'] == r['window_km'] * 1000
        assert m['height'] * m['pixel_size_y_m'] == r['window_km'] * 1000


def test_retrieval_evidence():
    meta = json.loads((ROOT / 'retrieval.json').read_text())
    assert meta['mola_zero_elevation_is_valid']
    assert 0 < meta['mola_measured_bin_fraction_in_crop'] < 1
    assert len(meta['inputs']) == 6
    for item in meta['inputs']:
        assert item['url'].startswith('https://') and len(item['sha256']) == 64
        assert item['bytes'] > 0
    assert sum(x['content_range'] is not None for x in meta['inputs']) == 2
