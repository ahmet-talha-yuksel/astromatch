import json, os
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.config import settings
from engine.ranking import DISCLAIMER

@pytest.fixture(scope='module')
def client(tmp_path_factory):
    previous=os.environ.get('ASTROMATCH_DATA_MODE')
    os.environ['ASTROMATCH_DATA_MODE']='mock'
    prior_results=settings.results_dir
    path=tmp_path_factory.mktemp('results')
    settings.results_dir=str(path)
    (path/'validation_report.json').write_text(json.dumps({'data_status':'mock','disclaimer':DISCLAIMER,'targets':{}}))
    try:
        with TestClient(app) as c: yield c,path
    finally:
        settings.results_dir=prior_results
        if previous is None: os.environ.pop('ASTROMATCH_DATA_MODE',None)
        else: os.environ['ASTROMATCH_DATA_MODE']=previous


def check_mock(response):
    assert response.status_code==200,response.text
    body=response.json()
    assert body['data_status']=='mock' and body['disclaimer']==DISCLAIMER
    return body


def test_health_targets_presets(client):
    c,_=client
    health=check_mock(c.get('/api/v1/health'))
    assert health['data_mode']=='mock' and health['dataset_counts']['candidates']>=5000
    assert isinstance(health['sklearn_available'],bool) and isinstance(health['hdbscan_available'],bool)
    targets=check_mock(c.get('/api/v1/targets'))['targets']
    assert {t['region_id'] for t in targets}=={'T-01','T-02','T-03'}
    presets=check_mock(c.get('/api/v1/presets'))
    assert 'balanced' in presets['presets'] and presets['features']['relief_m']['unit']=='m'


def test_get_post_rank_and_sites(client):
    c,_=client
    get=check_mock(c.get('/api/v1/rank',params={'target_id':'T-01','scale':'local'}))
    assert get['top_k'][0]['score_geo']<=100 and get['top_k'][0]['score_relative']==100
    assert get['sigma']['relief_m']['sigma_source']=='earth_robust_std' and get['sigma']['relief_m']['n_samples']>=200
    post=check_mock(c.post('/api/v1/rank',json={'target_id':'T-01','scale':'local','weights':{'relief_m':2}}))
    assert post['top_k'] and post['preset']=='balanced'
    sites=check_mock(c.get('/api/v1/sites',params={'target_id':'T-01'}))
    assert len(sites['sites'])==8 and all('per_criterion' in s and 'floored_criteria' in s for s in sites['sites'])


def test_heat_computed_and_precomputed(client):
    c,path=client
    params={'target_id':'T-01','scale':'local'}
    computed=check_mock(c.get('/api/v1/heat',params=params))
    assert computed['source']=='computed' and len(computed['points'])==8
    (path/'T-01__local__balanced__heat.json').write_text(json.dumps([{'id':'X','lat':1,'lon':2,'score':3,'data_status':'mock','disclaimer':DISCLAIMER}]))
    pre=check_mock(c.get('/api/v1/heat',params=params))
    assert pre['source']=='precomputed' and pre['points'][0]['id']=='X'


def test_region_explain_validation_legacy(client):
    c,_=client
    region=check_mock(c.get('/api/v1/regions/S-01'))
    assert region['region']['name']=='Salda' and len(region['records'])==2 and len(region['scores'])==5
    explanation=check_mock(c.get('/api/v1/explain',params={'target_id':'T-02','candidate_id':'S-01','scale':'local'}))
    assert explanation['explanation']['summary']
    assert check_mock(c.get('/api/v1/validation'))['report']['data_status']=='mock'
    legacy=c.post('/api/rank',json={'target_id':'mars_jezero'})
    assert legacy.status_code==200 and legacy.json()['ranked'][0]['score']<=1
    assert app.openapi()['paths']['/api/rank']['post']['deprecated'] is True


def test_errors(client):
    c,_=client
    assert c.get('/api/v1/rank',params={'target_id':'missing'}).status_code==404
    assert c.get('/api/v1/rank',params={'target_id':'T-03','scale':'local'}).status_code==404
    assert c.get('/api/v1/rank',params={'target_id':'T-01','preset':'bad'}).status_code==422
    assert c.post('/api/v1/rank',json={'target_id':'T-01','weights':{'unknown':2}}).status_code==422
    assert c.post('/api/v1/rank',json={'target_id':'T-01','weights':{'relief_m':-1}}).status_code==422
    assert c.post('/api/v1/rank',json={'target_id':'T-01','weights':{'relief_m':0}}).status_code==422
    assert c.get('/api/v1/regions/nope').status_code==404
    assert c.get('/api/v1/explain',params={'target_id':'T-01','candidate_id':'nope'}).status_code==404


def test_compare_card_and_errors(client):
    c,_=client
    params={'target_id':'T-01','candidate_id':'S-01','scale':'local','preset':'balanced'}
    card=check_mock(c.get('/api/v1/compare',params=params))
    assert card['target']['region_id']=='T-01' and card['candidate']['region_id']=='S-01'
    assert card['place']['country_code']=='TR'
    assert card['score_ci_low'] <= card['score_geo'] <= card['score_ci_high']
    assert 's_i' in card['per_criterion']['relief_m'] and 'z' in card['per_criterion']['relief_m']
    assert card['explanation']['analogy_breaks']==card['analogy_breaks']
    assert c.get('/api/v1/compare',params={**params,'candidate_id':'missing'}).status_code==404
    assert c.get('/api/v1/compare',params={**params,'target_id':'missing'}).status_code==404
    assert c.get('/api/v1/compare',params={**params,'preset':'missing'}).status_code==422
    assert c.get('/api/v1/compare',params={**params,'scale':'invalid'}).status_code==422


def test_mock_demo_precomputed_without_ranking(client,monkeypatch,tmp_path):
    from pathlib import Path
    import backend.app.api.v1 as v1
    from engine.cli import main
    c,_=client
    demo=tmp_path/'demo_results'
    main(['export-demo','--mock','--out',str(demo),'--timestamp','2026-11-14T00:00:00Z'])
    monkeypatch.setattr(settings,'results_dir',str(demo))
    monkeypatch.setattr(v1,'engine_rank',lambda *args,**kwargs: (_ for _ in ()).throw(AssertionError('rank recomputed')))
    ranked=check_mock(c.get('/api/v1/rank',params={'target_id':'T-01','scale':'local'}))
    assert ranked['top_k']
    sites=check_mock(c.get('/api/v1/sites',params={'target_id':'T-01'}))
    assert len(sites['sites'])==8
    heat=check_mock(c.get('/api/v1/heat',params={'target_id':'T-01','scale':'local'}))
    assert heat['source']=='precomputed'
