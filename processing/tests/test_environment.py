import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import pytest
import zipfile
from pyhdf.SD import SD, SDC

from processing.scripts.modis import CMGFile, calibrated, cmg_window, circular_hour, lst_qa, ndvi_qa, weighted_mean
from processing.scripts.temperature import compare_temperature

ROOT = Path(__file__).resolve().parents[1]


def test_lst_combined_use_bit_is_not_a_data_quality_bit():
    np.testing.assert_equal(lst_qa([0, 8, 1, 2, 3, 4, 64, 128, 192, 48]),
                            [True, True, False, False, False, False, False, False, False, True])


def test_ndvi_061_file_legend_uses_three_land_bits_and_two_geospatial_bits():
    qc = np.array([(land << 11) | (3 << 14) for land in range(8)])
    np.testing.assert_equal(ndvi_qa(qc, np.zeros(8)), [False, True, False, False, False, False, False, False])
    qc = np.array([(1 << 11) | (geo << 14) for geo in range(4)])
    np.testing.assert_equal(ndvi_qa(qc, np.zeros(4)), [False, False, True, True])
    good = (1 << 11) | (3 << 14)
    bad = [good | flag for flag in (1, 2, 3, 15 << 2, 3 << 6, 1 << 8, 1 << 10)]
    assert not ndvi_qa(bad, np.zeros(len(bad))).any()
    assert not ndvi_qa([good], [4])[0]  # Historical time-series estimate is not this month's observation.


def test_modis_products_have_different_calibration_conventions_and_valid_zero_ndvi():
    attrs = {'valid_range': [7500, 65535], '_FillValue': 0, 'scale_factor': .02, 'add_offset': 0, 'units': 'K'}
    values = calibrated([0, 15000, 7000], attrs, 'MOD11C3')
    assert np.isnan(values[0]) and np.isnan(values[2])
    assert values[1] == pytest.approx(26.85)
    attrs = {'valid_range': [-2000, 10000], '_FillValue': -3000, 'scale_factor': 10000, 'add_offset': 0}
    np.testing.assert_allclose(calibrated([-2000, 0, 5000, 10000, -3000], attrs, 'MOD13C2'),
                               [-.2, 0, .5, 1, np.nan], equal_nan=True)
    with pytest.raises(ValueError, match='encoding'):
        calibrated([5000], dict(attrs, scale_factor=.0001), 'MOD13C2')


def test_weighted_sampling_and_utc_midnight_are_handled():
    assert weighted_mean(np.array([2., 10., np.nan]), np.array([3., 1., 8.])) == 4
    assert weighted_mean(np.array([np.nan]), np.array([1.])) is None
    hour = circular_hour(np.array([23.8, .2]), np.ones(2))
    assert min(hour, 24-hour) == pytest.approx(0, abs=1e-8)
    assert circular_hour(np.array([0., 12.]), np.ones(2)) is None
    q = CMGFile.quality(np.ones((2, 2)), np.ones((2, 2)))
    assert q['accepted_area_fraction'] == 1


def test_cmg_windows_use_physical_scale_and_keep_native_centers():
    for lat in (37.55, 75.3775):
        local = {'body': 'earth', 'lat': lat, 'lon': 29.67, 'window_km': 10}
        a, count, weights = cmg_window(local)
        b, regional_count, regional = cmg_window(dict(local, window_km=50))
        assert weights.shape == count and regional.shape == regional_count
        assert (weights > 0).sum() < (regional > 0).sum()
        assert (weights > 0).sum() > 0 and max(count) < 20
    with pytest.raises(ValueError):
        cmg_window(dict(local, body='mars'))


def test_hdf_wrong_product_and_wrong_collection_are_rejected(tmp_path):
    file = tmp_path/'MOD13C2.A2021152.061.2021194035425.hdf'
    with pytest.raises(ValueError, match='named'):
        CMGFile(file, 'MOD11C3', '2026-11-14')
    handle = SD(str(file), SDC.WRITE | SDC.CREATE)
    handle.identifier_product_doi = '10.5067/MODIS/MOD13C2.006'
    handle.end()
    with pytest.raises(ValueError, match='DOI'):
        CMGFile(file, 'MOD13C2', '2026-11-14')


def test_temperature_difference_requires_paired_valid_pixels(monkeypatch):
    from processing.scripts import modis
    monkeypatch.setattr(modis, 'cmg_window', lambda r: ((0, 0), (1, 3), np.ones((1, 3))))
    reader = object.__new__(CMGFile)
    reader.product, reader.period = 'MOD11C3', {'start': '2021-06-01', 'end': '2021-06-30'}
    attrs = {'valid_range': [7500, 65535], '_FillValue': 0, 'scale_factor': .02, 'units': 'K'}
    def read(name, start, count):
        if name.startswith('LST_'):
            return (np.array([[15000, 16000, 17000]]) if 'Day' in name else np.array([[14000, 15000, 16000]])), attrs
        if name == 'QC_Day':return np.array([[0, 0, 2]]), {}
        if name == 'QC_Night':return np.array([[2, 0, 0]]), {}
        return np.array([[10, 10, 10]]), {'valid_range':[0,120], '_FillValue':255, 'scale_factor':.2}
    reader.read = read
    result = reader.extract({})
    difference = result['features']['surface_temp_monthly_overpass_difference_c']
    assert difference['value'] == pytest.approx(20)
    assert not difference['comparable']
    assert result['quality']['paired_day_night']['accepted_pixels'] == 1
    assert result['quality']['paired_day_night']['accepted_area_fraction'] == pytest.approx(1/3)


def valid_temperature():
    return {'value': 40., 'quantity': 'surface_temperature', 'statistic': 'diurnal_range',
            'time_definition': {'cycle': 'full_diurnal', 'phase': 'all_local_hours', 'season_coverage': 'all_seasons'},
            'measurement_method': 'documented retrieval', 'uncertainty_k': 2.,
            'comparability_note': 'Synthetic protocol unit fixture; no real pair is approved.'}


@pytest.mark.parametrize('change', [
    {'quantity': 'air_temperature'}, {'statistic': 'monthly_overpass_difference'},
    {'time_definition': {'cycle': 'UTC_month'}}, {'measurement_method': ''},
    {'uncertainty_k': None}, {'uncertainty_k': float('nan')}, {'comparability_note': ' '}, {'value': None}])
def test_temperature_gate_fails_each_missing_condition(change):
    left = valid_temperature()
    right = dict(left, **change)
    assert not compare_temperature(left, right)['comparable']


def test_temperature_gate_rejects_absolute_values_even_if_metadata_matches():
    left = valid_temperature()
    assert compare_temperature(left, left)['comparable']
    absolute = dict(left, statistic='monthly_mean')
    assert not compare_temperature(absolute, absolute)['comparable']
    no_time = dict(left, time_definition={})
    assert not compare_temperature(no_time, no_time)['comparable']


def test_environmental_release_is_offline_readable_and_cannot_inherit_topographic_approval():
    records = json.loads((ROOT/'out/real/features.json').read_text())['records']
    earth = [r for r in records if r['body']=='earth']
    assert len(earth)==16 and all(r['resolution_validated'] for r in earth)
    for record in records:
        assert not any('ndvi' in name for name in record['features'])
        if record['body']!='earth':
            assert record['earth_filters'] is None
            continue
        assert not record['earth_filters']['ndvi_mean']['comparable']
        ndvi = record['earth_filters']['ndvi_mean']['value']
        assert ndvi is None or -.2<=ndvi<=1
        for name, item in record['features'].items():
            if name.startswith('surface_temp'):
                assert item['data_status']=='derived' and not item['comparable']
        assert 'surface_temp_diurnal_range_c' not in record['features']
        for quality in record['quality']['environment'].values():
            for sub in ('day', 'night', 'paired_day_night', 'ndvi'):
                if sub in quality:assert 0<=quality[sub]['accepted_area_fraction']<=1
    report = json.loads((ROOT/'out/real/environment.json').read_text())
    assert report['records_processed']==16 and report['scoring_temperature_pairs']==0
    assert report['missing_products']==[]
    assert {r['product'] for r in report['inputs']}=={'MOD11C3.061','MOD13C2.061'}
    assert all(len(r['file_sha256'])==64 for r in report['inputs'])
    table = pq.read_table(ROOT/'out/real/earth_grid.parquet')
    assert table.num_rows==8 and str(table.schema.field('ndvi_mean').type)=='double'
    assert not any(table['ndvi_mean__comparable'].to_pylist())
    assert all(r['ndvi_mean__status']=='derived' for r in table.to_pylist())


def test_bad_environmental_input_preserves_existing_release(tmp_path):
    from processing.scripts.enrich_environment import enrich
    source=tmp_path/'release';source.mkdir()
    for name in ('features.json','earth_grid.parquet','DATA_SOURCES.md'):
        (source/name).write_bytes((ROOT/'out/real'/name).read_bytes())
    before={p.name:p.read_bytes() for p in source.iterdir()}
    with pytest.raises(ValueError, match='named'):
        enrich(source, ndvi_path=tmp_path/'wrong.hdf', accessed_on='2026-11-14')
    assert before=={p.name:p.read_bytes() for p in source.iterdir()}


def test_root_release_and_handoff_bundle_match_current_outputs():
    root = ROOT/'out'
    # Analog-profile context is a separate augmentation of real/features.json;
    # historical handoff/root snapshots retain identical non-context attributes.
    def without_context(data):
        doc = json.loads(data)
        for record in doc['records']:
            record.pop('context', None)
        return doc
    assert without_context((root/'features.json').read_bytes()) == without_context((root/'real/features.json').read_bytes())
    for name in ('environment.json', 'retrieval.json', 'target_quality.json'):
        assert (root/name).read_bytes() == (root/'real'/name).read_bytes()
    a, b = pq.read_table(root/'earth_grid.parquet'), pq.read_table(root/'pilot_expanded/earth_grid.parquet')
    assert a.select(b.column_names).equals(b)
    for name in ('coverage.geojson','pilot_timing.json'):
        assert (root/name).read_bytes()==(root/'pilot_expanded'/name).read_bytes()
    records = json.loads((root/'features.json').read_text())['records']
    with zipfile.ZipFile(root/'handoff/kisi2_v2_3.zip') as archive:
        assert archive.testzip() is None
        assert without_context(archive.read('features.json')) == without_context((root/'real/features.json').read_bytes())
        for name in ('earth_grid.parquet','coverage.geojson','environment.json'):
            if name.endswith(('.json', '.geojson')):
                assert json.loads(archive.read(name)) == json.loads((root/'real'/name).read_bytes())
            else:
                assert archive.read(name)==(root/'real'/name).read_bytes()
        for record in records:
            for key in ('path','metadata_path'):
                path=record['heightmap'][key]
                if path.endswith('.json'):
                    assert json.loads(archive.read(path)) == json.loads((root/path).read_bytes())
                else:
                    assert archive.read(path)==(root/path).read_bytes()
            evidence=record['quality'].get('qa_validation',{})
            if evidence.get('report_file'):
                path=evidence['report_file']
                assert json.loads(archive.read(path)) == json.loads((root/path).read_bytes())
        assert not any(name.endswith(('.hdf','.tif','.zip')) for name in archive.namelist())


def test_publisher_rejects_unsafe_references_before_writing(tmp_path):
    from processing.scripts.publish_release import publish
    source=tmp_path/'source';source.mkdir()
    payload={'schema_version':'2.3','records':[{
        'heightmap':{'path':'../outside.png','metadata_path':'../outside.json'},'quality':{}}]}
    (source/'features.json').write_text(json.dumps(payload))
    for name in ('earth_grid.parquet','coverage.geojson'):(source/name).write_bytes(b'fixture')
    target=tmp_path/'target'
    with pytest.raises(ValueError, match='Unsafe'):
        publish(source,target)
    assert not target.exists()
