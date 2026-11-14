import json
import pytest
from engine.mock import generate
import backend.app.services.data as service


def test_auto_selects_valid_real_features(tmp_path,monkeypatch):
    targets,candidates,_=generate(n_grid=0)
    rows=[targets[0],candidates[0]]
    for row in rows:
        row['data_status']='derived'
        for feature in row['features'].values(): feature['data_status']='derived'
    path=tmp_path/'features.json';path.write_text(json.dumps(rows))
    monkeypatch.setenv('ASTROMATCH_DATA_MODE','auto')
    monkeypatch.setenv('ASTROMATCH_FEATURES',str(path))
    old_ds,old_mode=service._dataset,service._active_mode
    try:
        ds=service.initialize_dataset()
        assert ds.mode=='real' and service.active_mode()=='real'
        assert len(ds.targets)==1 and len(ds.candidates)==1
    finally:
        service._dataset,service._active_mode=old_ds,old_mode


def test_real_mode_rejects_demo_fixtures(monkeypatch,tmp_path):
    monkeypatch.setenv('ASTROMATCH_DATA_MODE','real')
    monkeypatch.setenv('ASTROMATCH_FEATURES',str(tmp_path/'missing.json'))
    with pytest.raises(ValueError,match='requires valid, non-mock'):
        service.initialize_dataset()
