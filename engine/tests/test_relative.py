import builtins
import sys
import types
import pytest
from engine import load_dataset,rank
from engine.io import config
from engine.sigma import sigma_metadata


def test_local_sigma_pools_regional_and_fixed_fallback():
    ds=load_dataset(mock=True)
    result=rank(ds,'T-02','local')
    assert all(x['sigma_source']=='earth_reference_robust_std' and x['n_samples']==300 for x in result.sigma.values())
    spec=config('features.yaml')['features']['relief_m']
    fixed=sigma_metadata([1,2],'relief_m','local',spec,[],200)
    assert fixed=={'value':150.0,'sigma_source':'fixed_default','n_samples':0}


def test_relative_score_and_explanation():
    ds=load_dataset(mock=True)
    target=next(t for t in ds.targets if t.region_id=='T-02' and t.scale=='local')
    for f in target.features.values():
        if f.value is not None: f.value+=100000
    result=rank(ds,'T-02','local',detailed=True)
    assert max(r['score_relative'] for r in result.full_scores)==pytest.approx(100)
    assert result.top_k[0]['match_level']=='relative_only'
    assert result.top_k[0]['explanation']['summary'].startswith('No close Earth analog at this scale; ranking shows the closest available by standardized distance.')
    assert 'near ' in result.top_k[0]['explanation']['summary']
    assert 'floored_criteria' in result.top_k[0]


def test_agreement_basis_without_hdbscan(monkeypatch):
    original=builtins.__import__
    def blocked(name,*args,**kwargs):
        if name=='hdbscan': raise ImportError('disabled')
        return original(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',blocked)
    result=rank(load_dataset(mock=True),'T-01','local')
    assert all(r['agreement_basis']=='geo+knn' for r in result.full_scores)


def test_agreement_basis_with_hdbscan(monkeypatch):
    import numpy as np
    class FakeCluster:
        def __init__(self,**kwargs): pass
        def fit(self,z): self.labels_=np.zeros(len(z),dtype=int); return self
    monkeypatch.setitem(sys.modules,'hdbscan',types.SimpleNamespace(HDBSCAN=FakeCluster))
    result=rank(load_dataset(mock=True),'T-01','local')
    assert all(r['agreement_basis']=='geo+knn+cluster' for r in result.full_scores)
