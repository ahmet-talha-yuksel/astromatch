import json

import pytest

from engine.adapters import adapt
from engine.io import merged_features, load_dataset
from engine.measurement import target_status, target_confidence
from engine.mock import generate
from engine.models import DataPaths, Dataset
from engine.ranking import rank


def test_merge_newer_version_then_later_file(tmp_path,caplog):
    targets,candidates,_=generate(n_grid=0,n_reference=0)
    target=next(row for row in targets if row['scale']=='regional')
    site=next(row for row in candidates if row['kind']=='earth_site' and row['scale']=='regional')
    for row in (target,site):
        row['data_status']='derived'
        for feature in row['features'].values(): feature['data_status']='derived'
    target['region_id']='mars_jezero_regional'
    target['processing_version']='0.3.0'
    first=tmp_path/'first.json';first.write_text(json.dumps({'records':[target,site]}))
    later=json.loads(json.dumps(target));later['method']='measured_only_planefit_v1'
    later['features']['relief_m']['value']=999
    second=tmp_path/'second.json';second.write_text(json.dumps({'records':[later]}))
    rows,overrides=merged_features([first,second])
    assert next(r for r in rows if r['kind']=='target')['features']['relief_m']['value']==999
    assert len(overrides)==1 and 'later file' in overrides[0]
    with caplog.at_level('WARNING'):
        ds=load_dataset(DataPaths(features=[str(first),str(second)],grid=str(tmp_path/'missing.parquet')))
    assert ds.targets[0].method=='measured_only_planefit_v1'
    assert 'mars_jezero_regional' in caplog.text
    later['processing_version']='0.2.0';second.write_text(json.dumps({'records':[later]}))
    rows,overrides=merged_features([first,second])
    assert next(r for r in rows if r['kind']=='target')['features']['relief_m']['value']!=999
    assert 'kept' in overrides[0]


def test_saturated_absolute_scores_still_have_strict_relative_order(monkeypatch):
    import engine.ml as ml
    monkeypatch.setattr(ml,'analyze',lambda *args,**kwargs:None)
    targets,candidates,_=generate(n_grid=0,n_reference=0)
    target=next(row for row in targets if row['region_id']=='T-01' and row['scale']=='regional')
    template=next(row for row in candidates if row['kind']=='earth_site' and row['scale']=='regional')
    rows=[]
    for offset,label in ((1000,'A'),(1100,'B'),(1200,'C')):
        row=json.loads(json.dumps(template));row['region_id']='G-'+label;row['kind']='earth_grid'
        for key in target['features']:
            if key in row['features'] and row['features'][key]['comparable']:
                row['features'][key]['value']=target['features'][key]['value']+offset
        rows.append(row)
    ds=Dataset(targets=[adapt(target)],candidates=[adapt(row) for row in rows],mode='mock')
    result=rank(ds,'T-01','regional')
    assert [r['id'] for r in result.full_scores]==['G-A','G-B','G-C']
    assert len({round(r['score_geo'],6) for r in result.full_scores})==1
    assert result.full_scores[0]['score_relative']==100
    assert result.full_scores[0]['distance_z']<result.full_scores[1]['distance_z']<result.full_scores[2]['distance_z']
    assert result.full_scores[0]['score_relative']>result.full_scores[1]['score_relative']>result.full_scores[2]['score_relative']
    assert result.discrimination_label=='uniformly_dissimilar'
    assert 'No close Earth analog at this scale' in result.top_k[0]['explanation']['summary']


def test_mars_measured_fixtures_without_overriding_flags():
    targets,_,_=generate(n_grid=0,n_reference=0)
    template=next(row for row in targets if row['scale']=='regional' and row['body']=='mars')
    rows=[]
    for rid,ratio,valid,failed in [('mars_phoenix_regional',.0492,True,False),
                                   ('mars_arcadia_regional',.1948,True,False),
                                   ('mars_jezero_regional',.2248,False,True)]:
        row=json.loads(json.dumps(template));row['region_id']=rid;row['resolution_validated']=valid
        for feature in row['features'].values():feature['comparable']=valid
        row['method']='measured_only_planefit_v1'
        row['measurement_support']={'effective_nodata_ratio':ratio,'thresholds':{'rel':.15,'abs':{'slope_p90_deg':.2}},
                                    'sensitivity':{'slope_p90_deg':{'pass':not failed,'rel_diff':.1544 if failed else .05,'abs_diff':.912 if failed else .1}}}
        rows.append(adapt(row))
    assert [target_status(row)[0] for row in rows]==['scorable','scorable','unscorable']
    assert [target_confidence(row) for row in rows]==['high','medium','low']
    assert target_status(rows[2])[1]=='resolution_not_validated'
    from engine.measurement import excluded_features
    assert any('slope_p90_deg excluded' in item for item in excluded_features(rows[2]))
