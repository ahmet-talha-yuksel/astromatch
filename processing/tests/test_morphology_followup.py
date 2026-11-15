import json
from pathlib import Path
import zipfile

import numpy as np
import pyarrow.parquet as pq
import pytest

from processing.scripts.enrich_morphology import PARQUET_FILES
from processing.scripts.measured_mars import MEASURED_FEATURES, metrics, sensitivity
from processing.scripts.measured_window import measured_window
from processing.scripts.morphology import morphology_features
from processing.scripts.morphology_quality import ZERO_PREFIX, annotate_zero_roughness, zero_roughness_warning
from processing.scripts.measured_mars import request_for
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]


def test_zero_note_is_contextual_idempotent_and_does_not_change_value_or_qa():
    record = {'features': {'roughness_ratio': {'value': 0, 'comparable': True}},
              'resolution_validated': True, 'earth_filters': {'land_fraction': {'value': .1}},
              'quality': {'landmask': {'qa_passed': True}, 'warnings': ['existing']}}
    annotate_zero_roughness(record)
    assert 'water-dominated' in record['quality']['warnings'][-1]
    annotate_zero_roughness(record)
    assert len(record['quality']['warnings']) == 2
    assert record['features']['roughness_ratio'] == {'value': 0, 'comparable': True}
    assert record['resolution_validated']
    record['quality']['landmask']['qa_passed'] = False
    annotate_zero_roughness(record)
    assert 'not established' in record['quality']['warnings'][-1]
    assert 'water-dominated' not in record['quality']['warnings'][-1]
    assert len(record['quality']['warnings']) == 2
    for value in (None, 1e-12, .1): assert zero_roughness_warning(value) is None


def test_delivered_zero_notes_match_json_and_parquet_without_null_warnings():
    records = json.loads((ROOT/'out/pilot_expanded/features.json').read_text())['records']
    zero = [r for r in records if r['features']['roughness_ratio']['value'] == 0]
    assert len(zero) == 44 and sum(r['resolution_validated'] for r in zero) == 12
    assert all(any(w.startswith(ZERO_PREFIX) for w in r['quality']['warnings']) for r in zero)
    assert all('water-dominated' in r['quality']['warnings'][-1] for r in zero if r['resolution_validated'])
    for name in PARQUET_FILES:
        rows = pq.read_table(ROOT/name).to_pylist()
        for row in rows:
            notes = [w for w in json.loads(row['quality_warnings_json']) if w.startswith(ZERO_PREFIX)]
            assert len(notes) == int(row['roughness_ratio'] == 0)


def test_marius_delivered_contract_and_nine_sensitivity_checks():
    record = json.loads((ROOT/'out/moon_measured/features.json').read_text())['records'][0]
    assert record['target_id'] == 'T-03'
    assert record['method'] == 'measured_only_planefit_v1'
    assert record['provenance']['band_scale'] == .5
    assert record['provenance']['source_radius_m'] == 1737400
    assert not record['resolution_validated']
    assert set(record['features_interpolated']) == set(record['measurement_support']['sensitivity']) == set(MEASURED_FEATURES)
    primary = {k: record['features'][k]['value'] for k in MEASURED_FEATURES}
    assert record['measurement_support']['sensitivity'] == sensitivity(primary, record['features_interpolated'])
    assert record['measurement_support']['all_nine_sensitivity_passed']
    assert not record['measurement_support']['nine_feature_validation_passed']


def test_cached_marius_measured_values_preserve_half_meter_calibration_and_absent_bins():
    record = json.loads((ROOT/'out/moon_measured/features.json').read_text())['records'][0]
    request = request_for('marius', ROOT)
    if not all(Path(p).is_file() for p in (request.path, request.counts_path)):
        pytest.skip('Optional reproduction from locally cached raw rasters; exported contract is tested separately')
    # Cache-independent reconstruction from calibrated native counts-masked pixels.
    array = measured_window(request.path, request.counts_path, crs=record['crs'],
                            transform=from_origin(-25000,25000,1000,1000), shape=(50,50), vertical_unit='m')
    six, effective = metrics(array)
    extra, _ = morphology_features(array, 1000)
    expected = {**six, **{k: v['value'] for k,v in extra.items()}}
    for key, value in expected.items():
        assert record['features'][key]['value'] == pytest.approx(value, abs=1e-12)
    assert record['measurement_support']['effective_nodata_ratio'] == pytest.approx(effective)
    assert record['measurement_support']['sensitivity'] == sensitivity(expected, record['features_interpolated'])
    assert record['quality']['morphology']['measured_samples'] == np.isfinite(array).sum()
    assert record['measurement_support']['raw_unmeasured_ratio'] == pytest.approx(np.isnan(array).mean())


def test_handoff_contains_separate_measured_exports_and_current_controls():
    with zipfile.ZipFile(ROOT/'out/handoff/kisi2_v2_3.zip') as archive:
        for folder in ('mars_measured', 'moon_measured'):
            assert archive.read(folder+'/features.json') == (ROOT/'out'/folder/'features.json').read_bytes()
        assert 'curvature 0.01 km^-1' in archive.read('HANDOFF.md').decode()
