import json
from pathlib import Path

from processing.scripts.review_sampling import review
from processing.tests.test_dem import fixture_dem


def test_review_preserves_input_and_does_not_grant_comparability(tmp_path):
    from dataclasses import asdict
    request = fixture_dem(tmp_path)
    config = tmp_path / 'config.json'
    config.write_text(json.dumps({'records': [asdict(request)]}))
    before = config.read_bytes()
    report = review(config, tmp_path / 'report.json')
    assert config.read_bytes() == before
    assert not report['decision']['promote_to_comparable']
    candidates = report['results'][0]['candidates']
    assert candidates[0]['grid_shape'] == [20, 20]
    assert candidates[3]['grid_shape'] == [5, 5]
    assert candidates[3]['interior_tri_cells_max'] == 9
    assert not any(c['all_cells_have_observed_support'] for c in candidates)
    assert all(v is None for v in candidates[0]['difference_from_previous_resolution'].values())
    assert any(v != 0 for v in candidates[1]['difference_from_previous_resolution'].values())


def test_real_sampling_report_is_honest_and_complete():
    root = Path(__file__).resolve().parents[1]
    report = json.loads((root / 'out/salda_jezero/sampling_review.json').read_text())
    assert not report['decision']['promote_to_comparable']
    mars = {r['scale']: r for r in report['results'] if r['body'] == 'mars'}
    assert mars['local']['first_tested_resolution_with_all_cells_supported_m'] == 2000
    assert mars['regional']['first_tested_resolution_with_all_cells_supported_m'] == 5000
    assert len(report['results']) == 4
    for result in mars.values():
        assert len(result['candidates']) == 5
        assert result['candidates'][0]['sampling']['analysis_cells_without_observed_bins'] > 0
