from copy import deepcopy
import json
from pathlib import Path
import pytest
from processing.scripts.target_profiles import profiles, validate_profiles


def test_profiles_have_five_targets_and_all_sites_both_scales():
    root = Path(__file__).resolve().parents[1]/'out/real'
    doc = json.loads((root/'target_profiles.json').read_text(encoding='utf-8'))
    validate_profiles(doc)
    assert [r['target_id'] for r in doc['targets']] == [f'T-0{i}' for i in range(1,6)]
    assert len(doc['earth_sites']) == 16
    assert all(r['dimensions']['thermal']['values']['surface_temp_min_c'] is None for r in doc['targets'])
    phoenix = doc['targets'][3]['dimensions']['water_ice']
    assert phoenix['category']=='direct_observation' and phoenix['spatial_scope']=='site'
    assert doc['targets'][4]['dimensions']['water_ice']['category']=='orbital_indicator'


@pytest.mark.parametrize('bad', ['category','evidence','source','verified_by'])
def test_reject_invalid_evidence_unsourced_claim_or_unreviewed_verification(bad):
    doc = profiles([])
    item=doc['targets'][3]['dimensions']['water_ice']
    item[bad] = {'category':'confirmed','evidence':'guess','source':{},'verified_by':'auto'}[bad]
    with pytest.raises(ValueError): validate_profiles(doc)


def test_unknown_and_not_applicable_do_not_assert_a_source():
    doc=profiles(['earth_kula_local'])
    assert all(v['category']=='unknown' and v['source'] is None for v in doc['earth_sites'][0]['dimensions'].values())
    assert doc['targets'][1]['dimensions']['dust_wind']['category']=='not_applicable'
