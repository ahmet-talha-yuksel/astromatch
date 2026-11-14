import json
from pathlib import Path
import pytest
from engine.adapters import adapt
from engine.mock import generate
from engine.models import Dataset
from engine.ranking import DISCLAIMER,haversine
import engine.cli as cli


def test_all_mock_outputs_and_local_sites(tmp_path,monkeypatch):
    targets,candidates,known=generate(n_grid=200)
    ds=Dataset(targets=[adapt(x) for x in targets],candidates=[adapt(x) for x in candidates],known_analogs=[adapt(x) for x in known],mode='mock')
    monkeypatch.setattr(cli,'load_dataset',lambda *args,**kwargs:ds)
    cli.main(['run','--mock','--preset','all','--out',str(tmp_path),'--timestamp','2026-01-01T00:00:00Z'])
    site_names={'Salda','Kula','Meke','Hassa','Tuz Gölü','Atacama','Haughton','Meteor Crater'}
    assert json.loads((tmp_path/'index.json').read_text())['disclaimer']==DISCLAIMER
    assert json.loads((tmp_path/'pca.json').read_text())['disclaimer']==DISCLAIMER
    ranked=list(tmp_path.glob('T-*__*.json'))
    ranked=[p for p in ranked if not p.name.endswith('__heat.json')]
    assert len(ranked)==20
    for path in ranked:
        data=json.loads(path.read_text())
        assert data['data_status']=='mock' and data['disclaimer']==DISCLAIMER
        assert all(r['score_geo']<=r['score_arith']+1e-9 for r in data['full_scores'])
        assert all(r['data_status']=='mock' and r['disclaimer']==DISCLAIMER for r in data['full_scores']+data['excluded']+data['top_k']+data['novel_candidates'])
        separation=20 if data['scale']=='local' else 150
        assert all(haversine(a['lat'],a['lon'],b['lat'],b['lon'])>=separation for i,a in enumerate(data['top_k']) for b in data['top_k'][i+1:])
        heat=json.loads((tmp_path/(path.stem+'__heat.json')).read_text())
        assert all(r['data_status']=='mock' and r['disclaimer']==DISCLAIMER for r in heat)
        if data['scale']=='local':
            sites=json.loads((tmp_path/('sites__'+path.name)).read_text())
            assert sites['data_status']=='mock' and sites['disclaimer']==DISCLAIMER
            assert {r['name'] for r in sites['sites']}==site_names
            assert all(r['per_criterion'] and r['data_status']=='mock' and r['disclaimer']==DISCLAIMER for r in sites['sites'])
