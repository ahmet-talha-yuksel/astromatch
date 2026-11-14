from dataclasses import replace
import copy
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from processing.scripts.dem import process_dem, validate_comparison
from processing.scripts.qa_evidence import POLICY_PATH, evaluate, file_hash
from processing.tests.test_dem import fixture_dem


@pytest.fixture()
def evidence_fixture(tmp_path):
    # Entirely synthetic files exercise the real-product approval code path.
    request = replace(fixture_dem(tmp_path, 'moon'), synthetic=False, georeferencing_verified=True)
    with rasterio.open(request.path) as source:
        profile = source.profile.copy()
    counts = tmp_path/'counts.tif'
    for key in ('blockxsize', 'blockysize'):
        profile.pop(key, None)
    profile.update(dtype='int16', nodata=None)
    with rasterio.open(counts, 'w', **profile) as dst:
        dst.write(np.ones((40, 40), dtype='int16'), 1)
    fine = tmp_path/'fine.tif'
    profile.update(width=80, height=80, dtype='float64', transform=from_origin(-10000, 10000, 250, 250))
    y, x = np.mgrid[:80, :80]
    with rasterio.open(fine, 'w', **profile) as dst:
        dst.write(1.5*x+2*y-1.75, 1)
        dst.scales = (2.0,)
        dst.offsets = (-100.0,)
    request = replace(request, counts_path=str(counts))
    primary, _ = process_dem(request)
    reference, _ = process_dem(replace(request, path=str(fine), counts_path=None, source_resolution_m=250))
    policy = json.loads(POLICY_PATH.read_text())
    decision = evaluate(primary, reference, policy)
    assert decision['passed']
    report = {'policy': policy, 'policy_file_sha256': file_hash(POLICY_PATH),
              'records': [{'primary': primary, 'reference': reference,
                           'counts_file_sha256': file_hash(counts), 'decision': decision}]}
    qa = tmp_path/'report.json'
    qa.write_text(json.dumps(report))
    return replace(request, qa_report_path=str(qa), source_quality_verified=True), report


def test_proven_quality_needs_matching_earth_counterpart(evidence_fixture, tmp_path):
    request, _ = evidence_fixture
    moon, _ = process_dem(request)
    assert moon['quality']['qa_validation']['status'] == 'passed'
    assert moon['quality']['validation_eligible']
    assert not moon['resolution_validated']
    earth, _ = process_dem(replace(fixture_dem(tmp_path, 'earth'), synthetic=False, georeferencing_verified=True, source_quality_verified=True))
    validate_comparison([earth, moon])
    assert earth['resolution_validated'] and moon['resolution_validated']
    assert all(f['comparable'] for f in moon['features'].values())


@pytest.mark.parametrize('changes', [{'analysis_resolution_m': 1000}, {'lat': -89.4}, {'vertical_reference': 'different'}])
def test_evidence_cannot_be_reused_for_other_window_or_reference(evidence_fixture, changes):
    request, _ = evidence_fixture
    record, _ = process_dem(replace(request, **changes))
    assert record['quality']['qa_validation']['status'] == 'failed'
    assert not record['quality']['validation_eligible']
    assert not record['provenance']['source_quality_verified']


def test_source_hash_change_invalidates_evidence(evidence_fixture):
    request, _ = evidence_fixture
    with rasterio.open(request.path, 'r+') as dst:
        a = dst.read(1)
        a[0, 0] += 1  # outside analysis window; feature values may remain identical
        dst.write(a, 1)
    record, _ = process_dem(request)
    assert record['quality']['qa_validation']['status'] == 'failed'
    assert 'hash' in record['quality']['qa_validation']['reason']


def test_counts_hash_change_invalidates_evidence(evidence_fixture):
    request, _ = evidence_fixture
    with rasterio.open(request.counts_path, 'r+') as dst:
        a = dst.read(1)
        a[0, 0] = 2  # still measured; observed fractions remain unchanged
        dst.write(a, 1)
    record, _ = process_dem(request)
    assert record['quality']['qa_validation']['status'] == 'failed'
    assert 'counts file changed' in record['quality']['qa_validation']['reason']


def test_saved_pass_flag_cannot_override_failed_metric_checks(evidence_fixture):
    request, report = evidence_fixture
    report['records'][0]['reference']['features']['slope_median_deg']['value'] = 80
    Path(request.qa_report_path).write_text(json.dumps(report))
    record, _ = process_dem(request)
    assert record['quality']['qa_validation']['status'] == 'failed'


def test_no_qa_file_cannot_be_replaced_by_boolean(evidence_fixture):
    request, _ = evidence_fixture
    record, _ = process_dem(replace(request, qa_report_path=None))
    assert not record['quality']['validation_eligible']
    assert not record['provenance']['source_quality_verified']
    missing, _ = process_dem(replace(request, qa_report_path='/nonexistent/qa.json'))
    assert missing['quality']['qa_validation']['status'] == 'failed'


def test_partial_measurement_support_fails_policy(evidence_fixture):
    _, report = evidence_fixture
    entry = copy.deepcopy(report['records'][0])
    entry['primary']['quality']['sampling']['min_observed_bin_fraction'] = .5
    assert not evaluate(entry['primary'], entry['reference'], report['policy'])['passed']


def test_real_reviewed_package_unlocks_only_qualified_pairs():
    import pyarrow.parquet as pq
    root = Path(__file__).resolve().parents[1]/'out'
    report = json.loads((root/'quality_review/lola_report.json').read_text())
    assert all(e['decision']['passed'] for e in report['records'])
    for e in report['records']:
        assert e['primary']['quality']['sampling']['min_observed_bin_fraction'] == 1
        assert e['reference']['source_resolution_m'] == 120
    records = json.loads((root/'real/features.json').read_text())['records']
    assert len(records) == 12
    assert sum(r['resolution_validated'] for r in records) == 10
    for r in records:
        expected = r['body'] != 'mars'
        assert r['resolution_validated'] is expected
        assert all(f['comparable'] is expected for f in r['features'].values())
        if r['body'] == 'moon':
            assert r['quality']['qa_validation']['status'] == 'passed'
            evidence = r['quality']['qa_validation']
            assert len(evidence['report_sha256']) == 64
            assert file_hash(root/'real'/evidence['report_file']) == evidence['report_sha256']
    rows = pq.read_table(root/'real/earth_grid.parquet').to_pylist()
    assert len(rows) == 4 and all(r['slope_median_deg__comparable'] for r in rows)
    # Original preliminary deliverable remains available as an audit snapshot.
    original = json.loads((root/'quality_review/preliminary_features.json').read_text())['records']
    assert not any(r['resolution_validated'] for r in original)


def test_policy_revision_invalidates_old_report(evidence_fixture, monkeypatch, tmp_path):
    from processing.scripts import qa_evidence
    request, report = evidence_fixture
    changed = copy.deepcopy(report['policy'])
    changed['scope'] += ' Revised.'
    policy = tmp_path/'policy.json'
    policy.write_text(json.dumps(changed))
    monkeypatch.setattr(qa_evidence, 'POLICY_PATH', policy)
    record, _ = process_dem(request)
    assert record['quality']['qa_validation']['status'] == 'failed'
    assert 'policy changed' in record['quality']['qa_validation']['reason']


def test_reference_vertical_mismatch_fails(evidence_fixture):
    _, report = evidence_fixture
    entry = copy.deepcopy(report['records'][0])
    entry['reference']['provenance']['vertical_reference'] = 'different datum'
    assert not evaluate(entry['primary'], entry['reference'], report['policy'])['passed']


def test_qa_crop_contains_physical_analysis_corners():
    from pyproj import CRS, Transformer
    from processing.scripts.acquire_lola_qa import POLAR, crop_indices
    laea = CRS.from_proj4('+proj=laea +lat_0=-89.67 +lon_0=129.78 +R=1737400 +units=m')
    transform = Transformer.from_crs(laea, POLAR, always_xy=True)
    for spacing, size in ((240, 3812), (120, 7624)):
        r0, r1, c0, c1 = crop_indices(spacing, size)
        half = size*spacing/2
        for x in (-25000, 0, 25000):
            for y in (-25000, 0, 25000):
                xx, yy = transform.transform(x, y)
                assert -half+c0*spacing < xx < -half+c1*spacing
                assert half-r1*spacing < yy < half-r0*spacing


def test_qa_label_must_match_acquisition_period():
    from processing.scripts.acquire_lola_qa import verify_qa_label
    fields = {'LINES': 3812, 'LINE_SAMPLES': 3812, 'SAMPLE_BITS': 16, 'MAP_SCALE': 240,
              'A_AXIS_RADIUS': 1737.4, 'CENTER_LATITUDE': -90, 'CENTER_LONGITUDE': 0,
              'RECORD_BYTES': 7624, 'SCALING_FACTOR': 1, 'OFFSET': 0}
    metadata = '\n'.join(f'{k} = {v}' for k, v in fields.items())
    original = 'START_TIME = 2009-07-13\nSTOP_TIME = 2017-02-02\nPRODUCT_CREATION_TIME = 2017-06-15'
    label = ('LRO-L-LOLA-4-GDR-V1.0\nPOLAR STEREOGRAPHIC\nLSB_INTEGER\n'
             'MEAN EARTH/POLAR AXIS OF DE421\nNAME = COUNT\n' + metadata + '\n' + original)
    verify_qa_label(label, 240, 3812, 'counts', original)
    with pytest.raises(ValueError, match='time mismatch'):
        verify_qa_label(label.replace('2017-02-02', '2018-02-02'), 240, 3812, 'counts', original)
