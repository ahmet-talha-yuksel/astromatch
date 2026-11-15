import json
import logging

import pandas as pd
import pytest

from engine.adapters import adapt
from engine.cli import write_results
from engine.grid_status import grid_inventory, not_scanned_points
from engine.io import load_dataset
from engine.measurement import gate_reason, target_confidence, target_status
from engine.method_sensitivity import compare
from engine.mock import generate
from engine.models import DataPaths, Dataset
from engine.ranking import heat, list_targets, rank
from engine.readiness import check_real_data
from engine.validation_api import list_target_ids, score_grid


def phoenix_fixture():
    """Measured-only Phoenix-like mock fixture; no claims about real Phoenix data."""
    targets, candidates, _ = generate(n_grid=60, n_reference=0)
    target=next(r for r in targets if r['region_id']=='T-01' and r['scale']=='regional')
    target['region_id']='mars_phoenix_regional'
    target['name']='Phoenix-like mock target'
    target['method']='measured_only_planefit_v1'
    target['measurement_support']={
        'raw_unmeasured_ratio':.24,'effective_nodata_ratio':.15,
        'min_measured_neighbors':6,
        'thresholds':{'rel':.15,'abs':{},'max_effective_nodata':.30},
        'sensitivity':{key:{'abs_diff':.01,'rel_diff':.01,'pass':True}
                       for key in ('slope_median_deg','slope_p90_deg','flat_fraction',
                                   'tri_median_m','relief_m','elevation_std_m')}}
    alternate=next(r for r in candidates if r['kind']=='earth_grid')
    target['features_interpolated']={key:alternate['features'][key]['value']
                                     for key in target['measurement_support']['sensitivity']}
    ds=Dataset(targets=[adapt(target)],
               candidates=[adapt(r) for r in candidates if r['scale']=='regional'],mode='mock')
    return ds


def test_wrapper_candidate_dedupe_and_real_grid(tmp_path):
    target,site=generate(n_grid=0,n_reference=0)[:2]
    target=target[1]
    site=site[8]
    for row in (target,site):
        row['data_status']='derived'
        for value in row['features'].values(): value['data_status']='derived'
    site['kind']='candidate'
    path=tmp_path/'features.json'
    path.write_text(json.dumps({'schema_version':'2.3','records':[target,site]}))
    flat={k:v for k,v in site.items() if k!='features'}
    flat['kind']='earth_grid'
    for key,value in site['features'].items():
        flat[key]=value['value'];flat[key+'__status']='derived';flat[key+'__comparable']=value['comparable']
    grid=tmp_path/'grid.parquet';pd.DataFrame([flat]).to_parquet(grid)
    ds=load_dataset(DataPaths(features=str(path),grid=str(grid)))
    assert len(ds.targets)==1 and len(ds.candidates)==1
    assert ds.candidates[0].kind=='earth_site'
    assert any('Deduplicated' in item for item in ds.defaults_applied)
    assert any('kind candidate -> earth_site' in item for item in ds.defaults_applied)
    report=check_real_data(DataPaths(features=str(path),grid=str(grid)))
    assert report['ready'] and report['grid_status']=='regional_subset'
    real=check_real_data(DataPaths(features='processing/out/real/features.json',grid='processing/out/earth_grid.parquet'))
    assert real['ready'] and real['grid_counts']['scanned']==408 and real['grid_counts']['eligible']==216
    site_only=check_real_data(DataPaths(features='processing/out/real/features.json',grid='processing/out/real/earth_grid.parquet'))
    assert site_only['ready'] and site_only['grid_status']=='sites_only'


def test_measurement_gate_confidence_and_warning(caplog):
    ds=phoenix_fixture();target=ds.targets[0]
    assert target_confidence(target)=='medium'
    target.measurement_support['effective_nodata_ratio']=.08
    assert target_confidence(target)=='high'
    target.measurement_support['effective_nodata_ratio']=.25
    assert target_confidence(target)=='low'
    target.measurement_support['effective_nodata_ratio']=.31
    with caplog.at_level(logging.WARNING):
        assert gate_reason(target)=='effective_nodata_exceeds_threshold'
        result=rank(ds,target.region_id,'regional')
    assert result.full_scores and result.target_status=='scorable'
    assert 'effective_nodata_exceeds_threshold' in caplog.text
    target.measurement_support['effective_nodata_ratio']=.15
    target.measurement_support['sensitivity']['relief_m']['pass']=False
    with caplog.at_level(logging.WARNING):
        assert target_status(target)==('scorable',None)
    assert target.features['relief_m'].comparable is False
    assert 'relief_m excluded' in caplog.text


def test_additional_failed_check_only_gates_scoring_that_uses_that_feature():
    ds = phoenix_fixture(); target = ds.targets[0]
    before = rank(ds, target.region_id, 'regional').model_dump()
    target.measurement_support['sensitivity']['curvature_std_per_km'] = {'pass': False, 'abs_diff': .021, 'rel_diff': .4}
    target.measurement_support['thresholds']['abs']['curvature_std_per_km'] = .01
    assert gate_reason(target) is None
    after = rank(ds, target.region_id, 'regional').model_dump()
    assert [(r['id'], r['score_geo'], r['distance_z']) for r in before['full_scores']] == [(r['id'], r['score_geo'], r['distance_z']) for r in after['full_scores']]
    assert target_status(target, [*target.features, 'curvature_std_per_km']) == ('scorable', None)
    target.measurement_support['sensitivity']['relief_m']['pass'] = False
    assert gate_reason(target) is None
    assert target_status(target) == ('scorable', None)


def test_check_reports_measurement_disagreement(tmp_path):
    targets,candidates,_=generate(n_grid=0,n_reference=0)
    target=next(r for r in targets if r['region_id']=='T-01' and r['scale']=='regional')
    site=next(r for r in candidates if r['kind']=='earth_site' and r['scale']=='regional')
    for row in (target,site):
        row['data_status']='derived'
        for value in row['features'].values(): value['data_status']='derived'
    target['measurement_support']={'effective_nodata_ratio':.32,'thresholds':{'max_effective_nodata':.30}}
    path=tmp_path/'features.json';path.write_text(json.dumps({'schema_version':'2.3','records':[target,site]}))
    report=check_real_data(DataPaths(features=str(path)))
    assert report['ready']
    assert report['target_statuses']['T-01@regional']['status']=='scorable'
    target['measurement_support']={'effective_nodata_ratio':.15,'sensitivity':{'relief_m':{'pass':False}}}
    path.write_text(json.dumps({'schema_version':'2.3','records':[target,site]}))
    report=check_real_data(DataPaths(features=str(path)))
    assert report['target_statuses']['T-01@regional']['status']=='scorable'
    assert any('relief_m excluded' in item for item in report['target_statuses']['T-01@regional']['excluded_features'])


def test_method_sensitivity_explanation_aliases_and_mixed_methods(tmp_path,caplog):
    ds=phoenix_fixture();target=ds.targets[0]
    comparison=compare(ds,target)
    assert comparison['status']=='compared'
    assert comparison['n_common']>10
    assert comparison['spearman'] is not None and comparison['top_10_jaccard'] is not None
    assert comparison['spearman']<.8 and comparison['method_sensitive'] is True
    assert comparison['site_score_deltas']
    assert comparison['max_turkish_rank_shift'] is not None
    result=rank(ds,target.region_id,'regional')
    assert result.method_sensitive is True
    explanation=result.top_k[0]['explanation']
    assert explanation['target_method']=='measured_only_planefit_v1'
    assert explanation['measurement_support']['min_measured_neighbors']==6
    assert explanation['methodology_note']=='Interpolated MOLA values were not used.'
    assert explanation['target_confidence']=='medium'
    assert explanation['method_sensitive'] is True
    other=target.model_copy(deep=True);other.region_id='mars_arcadia_regional';other.method='another_method'
    ds.targets.append(other)
    with caplog.at_level(logging.WARNING):
        index=write_results(ds,tmp_path,['balanced'],3,'2026-11-14T00:00:00Z')
    assert 'mixed Mars methods' in index['warnings']
    assert index['method_sensitivity']
    aliases=list_target_ids()
    assert aliases['T-04']=='mars_phoenix' and aliases['T-05']=='mars_arcadia'
    ds.mode='real'
    assert {s.alias for s in list_targets(ds)}==set(aliases)


def test_coverage_not_scanned_and_sigma_sources():
    ds=load_dataset(DataPaths(features='processing/out/real/features.json',grid='processing/out/earth_grid.parquet'))
    status,counts=grid_inventory(ds.candidates)
    assert (status,counts['scanned'],counts['eligible'])==('regional_subset',408,216)
    missing=not_scanned_points(scanned_ids={r.region_id for r in ds.candidates if r.kind=='earth_grid'})
    assert len(missing)==2000 and all(p['score'] is None and p['status']=='not_scanned' for p in missing)
    regional=rank(ds,'moon_shackleton_regional','regional')
    assert all(v['n_samples']==216 and v['sigma_source']=='earth_robust_std' for v in regional.sigma.values())
    local=rank(ds,'moon_shackleton_local','local')
    assert all(v['n_samples']==8 and v['sigma_source']=='earth_site_robust_std' for v in local.sigma.values())
    points=heat(ds,'moon_shackleton_regional','regional')
    assert any(p.status=='not_scanned' and p.score is None for p in points)
    assert any(p.status=='not_comparable' and p.score is None for p in points)
