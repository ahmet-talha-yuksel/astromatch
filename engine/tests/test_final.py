import json
import logging
from pathlib import Path
import pytest
from engine import load_dataset, rank
from engine.cli import main, write_results
from engine.io import ROOT, config
from engine.ml import pca_export
from engine.mock import generate
from engine.readiness import check_real_data
from engine.models import DataPaths


def test_references_only_affect_sigma():
    ds=load_dataset(mock=True,mock_n_grid=10)
    refs=[r for r in ds.candidates if r.kind=='earth_reference']
    assert len(refs)==300 and all(r.scale=='local' for r in refs)
    result=rank(ds,'T-01','local')
    assert result.sigma['relief_m']['sigma_source']=='earth_robust_std'
    assert result.sigma['relief_m']['n_samples']==300
    assert len(result.full_scores)==8
    assert not any(r['id'].startswith('R-') for r in result.full_scores)
    assert not any(p['id'].startswith('R-') for p in pca_export(ds)['points'])
    regional=rank(ds,'T-01','regional')
    assert regional.sigma['relief_m']['sigma_source']=='pooled_from_regional'
    assert regional.sigma['relief_m']['n_samples']==10


def test_local_relative_threshold_and_regional_top_five():
    ds=load_dataset(mock=True,mock_n_grid=240)
    local=rank(ds,'T-02','local')
    assert all(r['match_level']=='relative_only' for r in local.full_scores if r['score_geo']<60 and r['score_relative']>=90)
    assert all(r['match_level']=='weak' for r in local.full_scores if r['score_geo']<60 and r['score_relative']<90)
    regional=rank(ds,'T-02','regional')
    for position,row in enumerate(regional.full_scores):
        if row['score_geo']<60:
            assert (row['match_level']=='relative_only')==(position<max(1,__import__('math').ceil(len(regional.full_scores)*.05)))


def test_spread_warning_and_reference_exclusion(tmp_path,caplog):
    ds=load_dataset(mock=True,mock_n_grid=10)
    ds.targets=[next(t for t in ds.targets if t.region_id=='T-01' and t.scale=='local')]
    sites=[r for r in ds.candidates if r.kind=='earth_site' and r.scale=='local']
    for site in sites[1:]: site.features={k:v.model_copy(deep=True) for k,v in sites[0].features.items()}
    with caplog.at_level(logging.WARNING): index=write_results(ds,tmp_path,['balanced'],20,'2026-01-01T00:00:00Z')
    spread=index['score_spread']['T-01__local__balanced']
    assert spread['count']==8 and spread['std']<5
    assert any('sites poorly discriminated — check sigma' in w for w in index['warnings'])
    assert 'sites poorly discriminated — check sigma' in caplog.text
    assert len(json.loads((tmp_path/'sites__T-01__local__balanced.json').read_text())['sites'])==8
    assert not any(p['id'].startswith('R-') for p in json.loads((tmp_path/'T-01__local__balanced__heat.json').read_text()))


def _real_rows():
    targets,candidates,_=generate(n_grid=0,n_reference=0)
    rows=[targets[0],candidates[0]]
    for row in rows:
        row['data_status']='derived'
        for feature in row['features'].values():feature['data_status']='derived'
    return rows


def test_check_valid_mock_and_legacy(tmp_path,capsys):
    real=tmp_path/'real.json';real.write_text(json.dumps(_real_rows()))
    good=check_real_data(DataPaths(features=str(real)))
    assert good['ready'] and good['counts_by_kind_body_scale']['target/mars/local']==1
    assert good['features_by_record'] and good['null_ratios']
    mock_rows=_real_rows();mock_rows[0]['data_status']='mock'
    mock=tmp_path/'mock.json';mock.write_text(json.dumps(mock_rows))
    bad=check_real_data(DataPaths(features=str(mock)))
    assert not bad['ready'] and bad['mock_records']
    legacy=check_real_data(DataPaths(features=str(ROOT/'data/processed/targets.json'),grid=str(ROOT/'data/processed/candidates.json')))
    assert not legacy['ready'] and any('schema_version must be 2.3' in e for e in legacy['errors'])
    with pytest.raises(SystemExit) as check_exit:main(['check','--features',str(mock)])
    check_output=json.loads(capsys.readouterr().out)
    with pytest.raises(SystemExit) as run_exit:main(['run','--features',str(mock)])
    run_output=json.loads(capsys.readouterr().err)
    assert check_exit.value.code==run_exit.value.code==2
    assert check_output['errors']==run_output['errors']
    main(['check','--features',str(real)])
    assert json.loads(capsys.readouterr().out)['ready']
    output=tmp_path/'real_out'
    main(['run','--features',str(real),'--out',str(output),'--timestamp','2026-11-14T00:00:00Z'])
    assert json.loads((output/'index.json').read_text())['data_status']=='real'


def test_export_demo_freeze(tmp_path):
    out=tmp_path/'demo_results'
    main(['export-demo','--mock','--out',str(out),'--timestamp','2026-11-14T00:00:00Z'])
    manifest=json.loads((out/'MANIFEST.json').read_text())
    index=json.loads((out/'index.json').read_text())
    assert manifest['data_status']=='mock' and manifest['input_sha256']['mock_dataset']
    assert json.loads((out/'validation_report.json').read_text())['input_sha256']==manifest['input_sha256']
    assert manifest['generated_at']==index['generated_at']
    second=tmp_path/'second_demo'
    main(['export-demo','--mock','--out',str(second),'--timestamp','2026-11-14T00:00:00Z'])
    assert json.loads((second/'MANIFEST.json').read_text())==manifest
    assert len(manifest['input_sha256']['mock_dataset'])==64
    assert len(index['score_spread'])==20
    assert len(list(out.glob('T-*__*.json')))==40
    assert (out/'validation_report.json').exists() and (out/'validation_report.md').exists()
    # Seeded uncertainty summaries add five values to each scored candidate.
    assert sum(p.stat().st_size for p in out.iterdir() if p.is_file())<7_000_000


def test_check_flattened_parquet_with_nulls(tmp_path):
    import pandas as pd
    rows=_real_rows()
    target=rows[0]
    features=tmp_path/'features.json';features.write_text(json.dumps([target]))
    site=rows[1]
    flat={key:site[key] for key in ('region_id','kind','body','name','scale','resolution_validated','data_status')}
    for key,feature in site['features'].items():
        if key=='surface_temp_diurnal_range_c':continue
        flat[key]=feature['value'];flat[key+'__status']='derived';flat[key+'__comparable']=True
    flat['elevation_std_m']=None
    grid=tmp_path/'grid.parquet';pd.DataFrame([flat]).to_parquet(grid)
    report=check_real_data(DataPaths(features=str(features),grid=str(grid)))
    assert report['ready'],report['errors']
    assert report['null_ratios']['elevation_std_m']>.0


def test_backend_reference_is_hidden():
    from fastapi.testclient import TestClient
    from backend.app.main import app
    with TestClient(app) as client:
        assert client.get('/api/v1/regions/R-0000').status_code==404
