import json
import time
import numpy as np
import pandas as pd
import pytest
from engine import load_dataset,rank,explain,heat
from engine.models import Dataset,DataPaths
from engine.adapters import adapt
from engine.similarity import criterion_similarity,rank_candidates
from engine.aggregate import aggregate_matrix
from engine.ranking import haversine
from engine.io import _read


def test_gaussian_and_other_criteria():
    cfg={'method':'gaussian'}
    assert criterion_similarity(3,3,cfg,2)==1
    assert criterion_similarity(2,3,cfg,2)==criterion_similarity(4,3,cfg,2)
    assert criterion_similarity(5,3,cfg,2)<criterion_similarity(4,3,cfg,2)
    assert criterion_similarity(2,0,{'method':'trapezoid','a':0,'b':1,'c':3,'d':4})==1
    assert criterion_similarity(10,0,{'method':'one_sided_below','limit':5,'width':5})==0


def test_aggregate_floor_and_coverage():
    geo,arith,cov,valid,norm=aggregate_matrix([[1,0,.5],[1,np.nan,.5]],[[1,1,1],[1,0,1]],[1,1,1],min_features=2)
    assert valid.all() and geo[0]<=arith[0] and geo[0]>0
    assert cov[1]==pytest.approx(2/3) and norm[1,0]==pytest.approx(.5)


def test_mock_safety_and_explanations():
    ds=load_dataset(mock=True)
    result=rank(ds,'T-01','local',k=3)
    assert result.data_status=='mock' and result.disclaimer
    assert all(r['data_status']=='mock' and r['disclaimer'] for r in result.full_scores)
    assert result.top_k[0]['explanation']['analogy_breaks']
    assert explain(ds,'T-01',result.top_k[0]['id'],'local').summary
    assert heat(ds,'T-01','local')
    ds.mode='real'
    with pytest.raises(ValueError,match='mock'): rank(ds,'T-01','local')


def test_eligibility_and_scale():
    ds=load_dataset(mock=True)
    target=next(t for t in ds.targets if t.region_id=='T-01' and t.scale=='local')
    c=next(c for c in ds.candidates if c.scale=='local')
    ds.candidates=[c]
    assert rank(ds,'T-01','regional').full_scores==[]
    c.features['slope_median_deg'].value=None
    c.features['slope_p90_deg'].comparable=False
    c.resolution_validated=False
    assert rank(ds,'T-01','local').excluded
    c.resolution_validated=True
    result=rank(ds,'T-01','local')
    assert result.full_scores and result.full_scores[0]['criteria_coverage']<1


def test_nms_and_determinism():
    ds=load_dataset(mock=True)
    one=rank(ds,'T-01','local',k=8).model_dump_json()
    two=rank(ds,'T-01','local',k=8).model_dump_json()
    assert one==two
    top=json.loads(one)['top_k']
    for i,a in enumerate(top):
        for b in top[i+1:]: assert haversine(a['lat'],a['lon'],b['lat'],b['lon'])>=20


def test_adapters_and_parquet(tmp_path):
    legacy={'id':'x','planet':'Earth','features':{'slope_deg':2,'tri_m':4,'relief_m':8},'isSynthetic':True}
    v23={'region_id':'x','kind':'earth_site','body':'earth','name':'x','scale':'local','resolution_validated':True,'data_status':'mock','features':{'slope_median_deg':{'value':2,'data_status':'mock','comparable':True},'tri_median_m':{'value':4,'data_status':'mock','comparable':True},'relief_m':{'value':8,'data_status':'mock','comparable':True}}}
    flat={'region_id':'x','kind':'earth_site','body':'earth','name':'x','scale':'local','resolution_validated':True,'data_status':'mock','slope_median_deg':2,'slope_median_deg__status':'mock','slope_median_deg__comparable':True,'tri_median_m':4,'tri_median_m__status':'mock','tri_median_m__comparable':True,'relief_m':8,'relief_m__status':'mock','relief_m__comparable':True}
    path=tmp_path/'records.parquet'; pd.DataFrame([flat]).to_parquet(path)
    a,b,c=adapt(legacy),adapt(v23),adapt(_read(path)[0])
    assert {k:f.value for k,f in a.features.items()}=={k:f.value for k,f in b.features.items()}=={k:f.value for k,f in c.features.items()}


def test_legacy_api():
    result=rank_candidates({'features':{'slope_deg':3}},[{'id':'x','features':{'slope_deg':3}}],{'slope_deg':1})
    assert result[0]['score']==1


def test_vectorized_100k():
    x=np.random.default_rng(42).uniform(0,1,(100000,6))
    start=time.perf_counter(); geo,*_=aggregate_matrix(x,np.ones_like(x,bool),np.ones(6))
    assert time.perf_counter()-start<1 and len(geo)==100000

def test_optional_ml_missing(monkeypatch):
    import builtins
    from engine.ml import analyze,pca_export
    original=builtins.__import__
    def blocked(name,*args,**kwargs):
        if name.startswith('sklearn'): raise ImportError('disabled in test')
        return original(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',blocked)
    ds=load_dataset(mock=True)
    target=next(t for t in ds.targets if t.scale=='local')
    assert analyze(target,[],[],[],set()) is None
    assert pca_export(ds)['status']=='unavailable'
    assert all(r['agreement']=='unavailable' for r in rank(ds,'T-01','local').full_scores)


def test_cli_deterministic_bytes(tmp_path,monkeypatch):
    import engine.cli as cli
    from engine import mock
    from engine.models import Dataset
    from engine.adapters import adapt
    t,c,k=mock.generate(n_grid=10)
    ds=Dataset(targets=[adapt(t[0])],candidates=[adapt(x) for x in c],known_analogs=[adapt(x) for x in k],mode='mock')
    monkeypatch.setattr(cli,'load_dataset',lambda *args,**kwargs:ds)
    a=tmp_path/'a'; b=tmp_path/'b'
    cli.main(['run','--mock','--out',str(a),'--timestamp','2026-01-01T00:00:00Z'])
    cli.main(['run','--mock','--out',str(b),'--timestamp','2026-01-01T00:00:00Z'])
    assert {p.name:p.read_bytes() for p in a.iterdir()}=={p.name:p.read_bytes() for p in b.iterdir()}

def test_external_features_and_flat_grid_replace_legacy(tmp_path):
    from engine.mock import generate
    from engine.io import load_dataset
    from engine.models import DataPaths
    targets,sites,_=generate(n_grid=0)
    target=targets[0];target['data_status']='derived'
    for feature in target['features'].values(): feature['data_status']='derived'
    site=sites[0];site['data_status']='derived'
    for feature in site['features'].values(): feature['data_status']='derived'
    path=tmp_path/'features.json';path.write_text(json.dumps([target,site]))
    grid=tmp_path/'grid.parquet'
    row={'region_id':'G-real','kind':'earth_grid','body':'earth','name':'Real grid','scale':'local','resolution_validated':True,'data_status':'derived'}
    for key,feature in site['features'].items():
        row[key]=feature['value'];row[key+'__status']='derived';row[key+'__comparable']=feature['comparable']
    pd.DataFrame([row]).to_parquet(grid)
    ds=load_dataset(DataPaths(features=str(path),grid=str(grid)))
    assert [t.region_id for t in ds.targets]==[target['region_id']]
    assert {c.region_id for c in ds.candidates}=={site['region_id'],'G-real'}
    assert all(c.data_status=='derived' for c in ds.candidates)
