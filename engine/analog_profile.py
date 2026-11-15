"""Evidence-led, categorical characterization; independent of terrain ranking math."""
from __future__ import annotations
import json, math
from pathlib import Path
from .io import ROOT, config

PROFILE_DIMENSIONS=('water_ice','surface_material','thermal','dust_wind','illumination')
CONTEXT_KEYS=('lst_day_mean_c','lst_night_mean_c','lst_diurnal_range_c','lst_min_month_c','lst_max_month_c','lst_absolute_min_c','ndvi_mean','precip_mm_yr','diviner_day_max_c','diviner_night_min_c','diviner_mean_c','diviner_diurnal_range_c','psr_fraction')
DISCLAIMER='Characterization, not a probability. Earth cannot reproduce gravity, vacuum/thin atmosphere or radiation.'
RANK={'None':0,'Low':1,'Medium':2,'High':3}

def profile_path(value=None):
    p=Path(value or ROOT/'processing/out/real/target_profiles.json')
    return p if p.is_absolute() else ROOT/p

def read_profiles(path):
    """Return valid claims and all schema errors. Invalid claims are never served."""
    path=profile_path(path)
    if not path.exists(): return {},[]
    try: data=json.loads(path.read_text())
    except (OSError,ValueError) as exc: return {},[f'{path}: invalid profile JSON: {exc}']
    errors=[];result={}
    if not isinstance(data,dict) or data.get('schema_version')!='profile-1.0' or not isinstance(data.get('records'),list):
        return {},[f'{path}: expected profile-1.0 object with records list']
    for index,record in enumerate(data['records']):
        if not isinstance(record,dict): errors.append(f'profiles[{index}]: expected object');continue
        rid=record.get('region_id')
        if not isinstance(rid,str) or not rid: errors.append(f'profiles[{index}]: region_id required');continue
        if record.get('kind') not in ('target','earth_site'): errors.append(f'{rid}: profile kind must be target or earth_site')
        if record.get('data_status') not in ('real','mock'): errors.append(f'{rid}: profile data_status must be real or mock')
        dimensions=record.get('dimensions')
        if not isinstance(dimensions,dict): errors.append(f'{rid}: dimensions must be object');continue
        valid={}
        for name,item in dimensions.items():
            if name not in PROFILE_DIMENSIONS: errors.append(f'{rid}: unknown profile dimension {name}');continue
            if not isinstance(item,dict): errors.append(f'{rid}.{name}: expected object');continue
            source=item.get('source')
            if not isinstance(source,dict) or not isinstance(source.get('title'),str) or not source.get('title', '').strip() or not isinstance(source.get('url_or_doi'),str) or not source.get('url_or_doi','').strip():
                errors.append(f'{rid}.{name}: unsourced claim (source.title and source.url_or_doi required)');continue
            missing=[key for key in ('category','summary','evidence','spatial_scope','verified_by') if not item.get(key)]
            if missing: errors.append(f'{rid}.{name}: missing {", ".join(missing)}');continue
            if item['evidence'] not in config('profile_rules.yaml')['confidence']:
                errors.append(f'{rid}.{name}: unknown evidence tier {item["evidence"]}');continue
            if name=='surface_material' and 'minerals' in item and (not isinstance(item['minerals'],list) or not all(isinstance(x,str) for x in item['minerals'])):
                errors.append(f'{rid}.{name}: minerals must be a list of names');continue
            valid[name]=item
        result[rid]={**record,'dimensions':valid}
    return result,errors

def context_coverage(regions):
    output={}
    for kind in ('target','earth_site','earth_grid'):
        subset=[r for r in regions if r.kind==kind]
        output[kind]={'records':len(subset),'keys':{key:{'present':sum(key in r.context for r in subset),'non_null':sum(isinstance(r.context.get(key),dict) and r.context[key].get('value') is not None for r in subset)} for key in CONTEXT_KEYS}}
    return output

def profile_coverage(regions,profiles):
    output={}
    for kind in ('target','earth_site'):
        subset=[r for r in regions if r.kind==kind]
        output[kind]={'records':len(subset),'with_profile':sum(r.region_id in profiles for r in subset),'dimensions':{key:sum(key in profiles.get(r.region_id,{}).get('dimensions',{}) for r in subset) for key in PROFILE_DIMENSIONS}}
    return output

def _ctx(region,key):
    item=region.context.get(key)
    if not isinstance(item,dict) or item.get('value') is None:return None
    try:
        value=float(item['value'])
        if not math.isfinite(value):return None
    except (TypeError,ValueError):return None
    return item

def _claim(profiles,region,name):
    return profiles.get(region.region_id,{}).get('dimensions',{}).get(name)

def _source(item):
    if not item:return []
    source=item.get('source')
    if isinstance(source,dict) and source.get('title') and source.get('url_or_doi'):return [source]
    if isinstance(source,str) and source.strip():return [{'title':source,'url_or_doi':source if source.startswith(('http://','https://','mock://','doi:')) else None}]
    return []

def _confidence(items):
    cfg=config('profile_rules.yaml')['confidence']
    tiers=[cfg.get(item.get('evidence'),'None') for item in items if item]
    return min(tiers,key=lambda x:RANK[x]) if tiers else 'None'

def _dimension(name,label,target_item=None,earth_item=None,note='',extra=None):
    sources=[]
    for item in (target_item,earth_item):
        for source in _source(item):
            if source not in sources:sources.append(source)
    data={'name':name,'label':label,'target_value_or_summary':target_item.get('summary',target_item.get('value')) if target_item else None,
          'earth_value_or_summary':earth_item.get('summary',earth_item.get('value')) if earth_item else None,
          'evidence_target':target_item.get('evidence') if target_item else None,'evidence_earth':earth_item.get('evidence') if earth_item else None,
          'sources':sources,'note':note,'confidence':_confidence([target_item,earth_item]) if (target_item and earth_item) or name in ('aridity_vegetation','illumination') else 'None'}
    if extra:data.update(extra)
    return data

def characterize(ds,target,candidate,row,mission='human_base'):
    missions=config('mission_profiles.yaml')
    if mission not in missions:raise ValueError(f'Unknown mission: {mission}')
    rules=config('profile_rules.yaml');profiles=ds.profiles
    dims={}
    percentile=row.get('score_percentile_scanned') if row else None
    terrain_label='Not comparable' if percentile is None else 'Similar' if percentile>=rules['terrain']['similar_percentile_min'] else 'Partly' if percentile>=rules['terrain']['partly_percentile_min'] else 'Different'
    terrain_target={'summary':'Validated planetary topography','evidence':'orbital_remote_sensing','source':{'title':target.dem_source or 'Terrain source','url_or_doi':target.source or ''}}
    terrain_earth={'summary':'Validated Earth topography','evidence':'orbital_remote_sensing','source':{'title':candidate.dem_source or 'Terrain source','url_or_doi':candidate.source or ''}}
    dims['terrain']=_dimension('terrain',terrain_label,terrain_target if percentile is not None else None,terrain_earth if percentile is not None else None,
        'Scanned-cell percentile determines this label; raw terrain score is unchanged.',
        {'topographic_score':row.get('score_geo') if row else None,'topographic_interval':[row.get('score_ci_low'),row.get('score_ci_high')] if row else None})
    # Thermal compares matching surface quantities; Celsius offsets are converted to Kelvin.
    thermal=None
    for target_key,earth_key in rules['thermal']['comparable_pairs']:
        a,b=_ctx(target,target_key),_ctx(candidate,earth_key)
        if a and b:thermal=(target_key,earth_key,a,b);break
    cold=next((_ctx(target,key) for key in rules['thermal']['absolute_min_target_keys'] if _ctx(target,key)),None)
    earth_min=_ctx(candidate,rules['thermal']['absolute_min_earth_key'])
    if cold and earth_min and float(cold['value'])<float(earth_min['value'])-rules['thermal']['extreme_cold_margin_c']:
        dims['thermal']=_dimension('thermal','Earth cannot reproduce',cold,earth_min,'Planetary absolute surface minimum is more than 50°C below the Earth absolute minimum.')
    elif thermal:
        tk,ek,a,b=thermal
        is_range='diurnal_range' in tk
        av=float(a['value']) if is_range else float(a['value'])+273.15
        bv=float(b['value']) if is_range else float(b['value'])+273.15
        ratio=av/bv if bv>0 else math.inf
        cfg=rules['thermal']
        label='Similar' if cfg['similar_ratio_min']<=ratio<=cfg['similar_ratio_max'] else 'Partly' if cfg['partly_ratio_min']<=ratio<=cfg['partly_ratio_max'] else 'Earth cannot reproduce'
        dims['thermal']=_dimension('thermal',label,a,b,f'Compared {tk} to {ek}; ratio {ratio:.2f}.')
    else:dims['thermal']=_dimension('thermal','Not comparable',note='No matching measured surface-temperature quantity on both sides.')
    ndvi,precip=_ctx(candidate,'ndvi_mean'),_ctx(candidate,'precip_mm_yr')
    if ndvi and precip:
        cfg=rules['aridity_vegetation'];n,p=float(ndvi['value']),float(precip['value'])
        label='Good' if n<cfg['good_ndvi_max'] and p<cfg['good_precip_mm_yr_max'] else 'Moderate' if n<cfg['moderate_ndvi_max'] and p<cfg['moderate_precip_mm_yr_max'] else 'Poor'
        weakest=min((ndvi,precip),key=lambda item:RANK[config('profile_rules.yaml')['confidence'].get(item.get('evidence'),'None')])
        earth_item={'summary':f'NDVI {n:g}; precipitation {p:g} mm/year','evidence':weakest.get('evidence'),'source':None}
        dims['aridity_vegetation']=_dimension('aridity_vegetation',label,earth_item=earth_item,note='Earth-side analog quality only; no planetary vegetation comparison.')
        dims['aridity_vegetation']['sources']=list(dict.fromkeys(tuple(sorted(s.items())) for item in (ndvi,precip) for s in _source(item)))
        dims['aridity_vegetation']['sources']=[dict(x) for x in dims['aridity_vegetation']['sources']]
        dims['aridity_vegetation']['confidence']=_confidence([ndvi,precip])
    else:dims['aridity_vegetation']=_dimension('aridity_vegetation','Not comparable',note='Earth NDVI or precipitation is missing.')
    ta,ea=_claim(profiles,target,'water_ice'),_claim(profiles,candidate,'water_ice')
    label='Unknown' if not ta or not ea else 'Shared evidence type' if str(ta['category']).casefold()==str(ea['category']).casefold() else 'Different'
    dims['water_ice']=_dimension('water_ice',label,ta,ea,'Categorical evidence comparison; shared type does not establish equivalent resource abundance.')
    ta,ea=_claim(profiles,target,'surface_material'),_claim(profiles,candidate,'surface_material')
    tm={str(x).casefold():str(x) for x in ta.get('minerals',[]) } if ta else {}
    em={str(x).casefold():str(x) for x in ea.get('minerals',[]) } if ea else {}
    overlap=sorted(tm.keys()&em.keys())
    label='Unknown' if not ta or not ea or not tm or not em else f'Overlap: {", ".join(overlap)}' if overlap else 'No overlap'
    dims['surface_material']=_dimension('surface_material',label,ta,ea,'Mineral names compared case-insensitively; abundance and grain size are not assessed.')
    if target.body=='moon' and target.lat is not None and abs(target.lat)>=rules['illumination']['moon_polar_lat_min']:
        ta=_claim(profiles,target,'illumination')
        dims['illumination']=_dimension('illumination','Earth cannot reproduce',ta, note='Polar grazing Sun or permanent shadow cannot be reproduced by an Earth site.')
    else:dims['illumination']=_dimension('illumination','Not applicable',note='Special polar illumination rule applies only to Moon targets at the configured latitude.')
    if target.body=='moon':dims['dust_wind']=_dimension('dust_wind','Not applicable',note='The Moon has no atmosphere.')
    elif target.body=='mars':
        ta=_claim(profiles,target,'dust_wind')
        if ta and ndvi and precip and dims['aridity_vegetation']['label'] in ('Good','Moderate'):
            dims['dust_wind']=_dimension('dust_wind','Partly',ta,{'summary':dims['aridity_vegetation']['earth_value_or_summary'],'evidence':ndvi.get('evidence'),'source':ndvi.get('source')},'Earth aridity is only a proxy; it does not reproduce Mars atmosphere or dust dynamics.')
        else:dims['dust_wind']=_dimension('dust_wind','Not comparable',ta,note='Mars dust evidence or a dry Earth proxy is missing.')
    else:dims['dust_wind']=_dimension('dust_wind','Not applicable')
    result=[]
    for name in missions[mission]['order']:
        item=dims[name].copy();base_label='Overlap' if item['label'].startswith('Overlap:') else item['label']
        impact=missions[mission].get('impacts',{}).get(name,{}).get(base_label,'neutral')
        item['impact']=impact
        item['rationale']=missions[mission]['rationale'][name].format(label=item['label'].lower(),impact=impact)
        result.append(item)
    overall=min((item['confidence'] for item in result),key=lambda x:RANK[x]) if result else 'None'
    return {'target':{'region_id':target.region_id,'name':target.name,'body':target.body},'candidate':{'region_id':candidate.region_id,'name':candidate.name,'place':candidate.place},'mission':mission,
            'dimensions':result,'overall_confidence':overall,'disclaimer':DISCLAIMER,'data_status':ds.mode}
