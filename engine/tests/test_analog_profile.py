import json
from engine import load_dataset, rank
from engine.analog_profile import characterize, read_profiles
from engine.adapters import adapt
from engine.io import merged_features
from engine.models import DataPaths
from engine.readiness import check_real_data


def pair():
    ds=load_dataset(mock=True,mock_n_grid=40,mock_profile_target=True)
    target=next(t for t in ds.targets if t.region_id=='T-04')
    candidate=next(c for c in ds.candidates if c.region_id=='S-02' and c.scale=='regional')
    row=next(r for r in rank(ds,'T-04','regional').full_scores if r['id']=='S-02')
    return ds,target,candidate,row


def test_profile_labels_and_mission_independence():
    ds,target,candidate,row=pair()
    human=characterize(ds,target,candidate,row,'human_base')
    astro=characterize(ds,target,candidate,row,'astrobiology')
    labels=lambda result:{x['name']:x['label'] for x in result['dimensions']}
    assert labels(human)==labels(astro)
    assert [x['name'] for x in human['dimensions']] != [x['name'] for x in astro['dimensions']]
    assert next(x for x in human['dimensions'] if x['name']=='water_ice')['label']=='Shared evidence type'
    assert next(x for x in human['dimensions'] if x['name']=='surface_material')['label'].startswith('Overlap:')
    assert human['overall_confidence'] in ('None','Low','Medium','High')
    assert 'score' not in human and 'percentage' not in human
    assert human['data_status']=='mock'


def test_missing_never_looks_similar():
    ds,target,candidate,row=pair()
    target.context={};candidate.context={};ds.profiles={}
    result=characterize(ds,target,candidate,None)
    labels={x['name']:x['label'] for x in result['dimensions']}
    assert labels['terrain']=='Not comparable'
    assert labels['thermal']=='Not comparable'
    assert labels['water_ice']=='Unknown'
    assert labels['surface_material']=='Unknown'
    assert labels['dust_wind']=='Not comparable'
    assert result['overall_confidence']=='None'


def test_thermal_aridity_and_polar_paths():
    ds,target,candidate,row=pair()
    dim=lambda result,key:next(x for x in result['dimensions'] if x['name']==key)
    target.context.pop('lst_absolute_min_c')
    target.context['lst_night_mean_c']['value']=-30
    assert dim(characterize(ds,target,candidate,row),'thermal')['label']=='Partly'
    candidate.context['lst_diurnal_range_c']['value']=65
    assert dim(characterize(ds,target,candidate,row),'thermal')['label']=='Similar'
    candidate.context['lst_diurnal_range_c']['value']=5
    assert dim(characterize(ds,target,candidate,row),'thermal')['label']=='Earth cannot reproduce'
    target.context['lst_absolute_min_c']={'value':-95,'source':'MOCK SOURCE','period':'MOCK PERIOD','evidence':'model'}
    candidate.context['lst_diurnal_range_c']['value']=65
    assert dim(characterize(ds,target,candidate,row),'thermal')['label']=='Earth cannot reproduce'
    candidate.context['ndvi_mean']['value']=.5
    assert dim(characterize(ds,target,candidate,row),'aridity_vegetation')['label']=='Poor'
    moon=next(t for t in ds.targets if t.region_id=='T-02' and t.scale=='regional')
    assert dim(characterize(ds,moon,candidate,row),'illumination')['label']=='Earth cannot reproduce'
    assert dim(characterize(ds,moon,candidate,row),'dust_wind')['label']=='Not applicable'


def test_unsourced_claim_rejected_and_check_lists_it(tmp_path):
    profile=tmp_path/'target_profiles.json'
    profile.write_text(json.dumps({'schema_version':'profile-1.0','records':[{'region_id':'X','kind':'target','data_status':'real','dimensions':{'water_ice':{'category':'ice','summary':'claim','evidence':'model','spatial_scope':'site','verified_by':'someone'}}}]}))
    profiles,errors=read_profiles(profile)
    assert 'unsourced claim' in errors[0] and profiles['X']['dimensions']=={}
    report=check_real_data(DataPaths(profiles=str(profile)))
    assert not report['ready'] and any('unsourced claim' in x for x in report['errors'])


def test_flattened_context_columns_are_adapted():
    row={'region_id':'C','kind':'earth_grid','body':'earth','scale':'regional','resolution_validated':True,
         'ctx__ndvi_mean__value':.08,'ctx__ndvi_mean__source':'MOCK SOURCE',
         'ctx__ndvi_mean__period':'MOCK PERIOD','ctx__ndvi_mean__evidence':'model',
         'ctx__ndvi_mean__n_valid_months':6,'ctx__ndvi_mean__warnings':'["coarse grid"]',
         'ctx__ndvi_mean__reason':'cell_not_validated'}
    region=adapt(row,configured=set())
    assert region.context['ndvi_mean']=={'value':.08,'source':'MOCK SOURCE','period':'MOCK PERIOD','evidence':'model',
                                         'n_valid_months':6,'warnings':['coarse grid'],'reason':'cell_not_validated'}


def test_other_categorical_and_terrain_paths():
    ds,target,candidate,row=pair()
    dim=lambda result,key:next(x for x in result['dimensions'] if x['name']==key)
    assert dim(characterize(ds,target,candidate,{**row,'score_percentile_scanned':50}),'terrain')['label']=='Different'
    assert dim(characterize(ds,target,candidate,{**row,'score_percentile_scanned':80}),'terrain')['label']=='Partly'
    assert dim(characterize(ds,target,candidate,{**row,'score_percentile_scanned':95}),'terrain')['label']=='Similar'
    ds.profiles[candidate.region_id]['dimensions']['water_ice']['category']='dry'
    ds.profiles[candidate.region_id]['dimensions']['surface_material']['minerals']=['quartz']
    result=characterize(ds,target,candidate,row)
    assert dim(result,'water_ice')['label']=='Different'
    assert dim(result,'surface_material')['label']=='No overlap'
    candidate.context['ndvi_mean']['value']=.2
    assert dim(characterize(ds,target,candidate,row),'aridity_vegetation')['label']=='Moderate'


def test_filled_context_switches_labels_without_code_change():
    ds,target,candidate,row=pair()
    target.context={'lst_diurnal_range_c':{'value':65,'source':'MOCK SOURCE','period':'MOCK PERIOD','evidence':'model'}}
    candidate.context={key:{'value':None,'reason':'earthdata_credentials_unavailable; no 2025 observations'} for key in ('lst_diurnal_range_c','ndvi_mean','precip_mm_yr')}
    before={d['name']:d for d in characterize(ds,target,candidate,row)['dimensions']}
    assert before['thermal']['label']==before['aridity_vegetation']['label']=='Not comparable'
    assert 'earthdata_credentials_unavailable' in before['thermal']['null_reasons'][0]
    for key,value in (('lst_diurnal_range_c',50),('ndvi_mean',.06),('precip_mm_yr',100)):
        candidate.context[key].update(value=value,source='MOCK SOURCE',period='MOCK PERIOD',evidence='model')
    after={d['name']:d for d in characterize(ds,target,candidate,row)['dimensions']}
    assert after['thermal']['label']=='Similar' and after['aridity_vegetation']['label']=='Good'


def test_actual_profile_shape_and_unverified_claims(tmp_path):
    path=tmp_path/'profiles.json'
    path.write_text(json.dumps({'schema_version':'profile-1.0','targets':[{'region_id':'mars_phoenix_regional','target_id':'T-04','dimensions':{
        'water_ice':{'category':'direct_observation','summary':'Sourced claim','evidence':'direct_measurement','spatial_scope':'site','source':{'title':'MOCK SOURCE','url_or_doi':'mock://'},'verified_by':None},
        'thermal':{'category':'unknown','summary':None,'source':None,'verified_by':None,'notes':'No surface value delivered.'}}}], 'earth_sites':[]}))
    profiles,errors=read_profiles(path)
    assert not errors
    assert profiles['mars_phoenix_regional']['dimensions']['water_ice']['verified'] is False
    assert profiles['mars_phoenix_regional']['dimensions']['thermal']['category']=='unknown'


def test_later_measured_features_keep_earlier_context(tmp_path):
    a,b=tmp_path/'a.json',tmp_path/'b.json'
    a.write_text(json.dumps([{'region_id':'moon_x_regional','processing_version':'0.3.0','context':{'surface_temp_mean_c':{'value':None,'reason':'2 cm subsurface, not surface'}}}]))
    b.write_text(json.dumps([{'region_id':'moon_x_regional','processing_version':'0.3.0','features':{'relief_m':{'value':10}}}]))
    rows,logs=merged_features([a,b])
    assert rows[0]['features']['relief_m']['value']==10
    assert rows[0]['context']['surface_temp_mean_c']['reason'].startswith('2 cm')
    assert any('carried context' in log for log in logs)
