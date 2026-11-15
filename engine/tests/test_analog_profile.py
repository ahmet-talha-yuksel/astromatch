import json
from engine import load_dataset, rank
from engine.analog_profile import characterize, read_profiles
from engine.adapters import adapt
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
         'ctx__ndvi_mean__period':'MOCK PERIOD','ctx__ndvi_mean__evidence':'model'}
    region=adapt(row,configured=set())
    assert region.context['ndvi_mean']=={'value':.08,'source':'MOCK SOURCE','period':'MOCK PERIOD','evidence':'model'}


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
