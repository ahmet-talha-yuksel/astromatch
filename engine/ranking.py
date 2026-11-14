from __future__ import annotations
import math, warnings
import numpy as np
from .models import Dataset, RankResult, TargetSummary, HeatPoint
from .io import config
from .sigma import sigma_table
from .aggregate import aggregate_matrix
from .explanations import build
from .similarity import criterion_similarity

DISCLAIMER='MOCK DATA — NOT A SCIENTIFIC RESULT'

def list_targets(ds:Dataset):
    grouped={}
    for t in ds.targets:
        grouped.setdefault(t.region_id,{'name':t.name,'body':t.body,'scales':set()})['scales'].add(t.scale)
    return [TargetSummary(region_id=k,name=v['name'],body=v['body'],scales=sorted(v['scales'])) for k,v in sorted(grouped.items())]

def haversine(a,b,c,d):
    p1,p2=math.radians(a),math.radians(c); dp=p2-p1; dl=math.radians(d-b)
    return 6371*2*math.asin(min(1,math.sqrt(math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2)))

def rank(ds:Dataset,target_id:str,scale:str,preset:str='balanced',weights:dict|None=None,k:int=20,filter_mode:str='flag') -> RankResult:
    if filter_mode not in ('flag','exclude'): raise ValueError('filter_mode must be flag or exclude')
    if k<1: raise ValueError('k must be positive')
    target=next((t for t in ds.targets if t.region_id==target_id and t.scale==scale),None)
    if target is None: raise ValueError(f'Target {target_id} at {scale} not found')
    candidates=[c for c in ds.candidates if c.scale==scale and c.body=='earth']
    if ds.mode=='real' and (target.data_status=='mock' or any(c.data_status=='mock' for c in candidates) or any(f.data_status=='mock' for f in target.features.values()) or any(f.data_status=='mock' for c in candidates for f in c.features.values())):
        raise ValueError('Real mode cannot score mock records; use --mock only for generated mock data')
    fconfig=config('features.yaml'); feats=fconfig['features']; presets=config('presets.yaml')
    if preset not in presets: raise ValueError(f'Unknown preset: {preset}')
    modifiers=weights if weights is not None else presets[preset]
    for key in modifiers:
        if key not in feats: warnings.warn(f'Unknown weight {key} ignored',stacklevel=2)
    keys=list(feats); w=np.array([float(feats[key].get('weight',1))*float(modifiers.get(key,1)) for key in keys])
    if not np.all(np.isfinite(w)) or np.any(w<0) or w.sum()<=0: raise ValueError('Weights must be finite, nonnegative, with positive sum')
    sig=sigma_table(ds,scale,feats)
    n=len(candidates); m=len(keys)
    scores=np.full((n,m),np.nan); eligible=np.zeros((n,m),bool)
    not_compared=[[] for _ in candidates]
    for j,key in enumerate(keys):
        tf=target.features.get(key)
        for i,c in enumerate(candidates):
            cf=c.features.get(key)
            reason=None
            if not tf or tf.value is None or not cf or cf.value is None: reason='missing value'
            elif not target.resolution_validated or not c.resolution_validated: reason='resolution not validated'
            elif not tf.comparable or not cf.comparable: reason='not comparable'
            if reason: not_compared[i].append({'feature':key,'reason':reason}); continue
            eligible[i,j]=True
            scores[i,j]=criterion_similarity(cf.value,tf.value,feats[key],sig[key])
    geo,arith,coverage,valid,norm=aggregate_matrix(scores,eligible,w,fconfig.get('min_features',3))
    excluded=[]; full=[]
    for i,c in enumerate(candidates):
        flags=[]; ef=c.earth_filters
        if ef.get('ndvi_mean') is not None and ef['ndvi_mean']>.3: flags.append('vegetated')
        if ef.get('precip_mm_yr') is not None and ef['precip_mm_yr']>500: flags.append('humid')
        if ef.get('land_fraction') is not None and ef['land_fraction']<.8: flags.append('coastal_or_lake')
        if not valid[i]: excluded.append({'id':c.region_id,'reason':'fewer than min_features eligible','eligible_count':int(eligible[i].sum())}); continue
        if filter_mode=='exclude' and flags: excluded.append({'id':c.region_id,'reason':'earth filter','flags':flags}); continue
        if arith[i]-geo[i]>=15: flags.append('weak_link')
        criteria={key:{'target_value':target.features[key].value,'candidate_value':c.features[key].value,'sigma':sig[key],'s_i':float(scores[i,j]),'weight':float(norm[i,j])} for j,key in enumerate(keys) if eligible[i,j] and w[j]>0}
        known_dist=min((haversine(c.lat,c.lon,a.lat,a.lon) for a in ds.known_analogs if c.lat is not None and c.lon is not None and a.lat is not None and a.lon is not None),default=None)
        row={'id':c.region_id,'name':c.name,'lat':c.lat,'lon':c.lon,'score_geo':float(geo[i]),'score_arith':float(arith[i]),'criteria_coverage':float(coverage[i]),'per_criterion':criteria,'flags':flags,'not_compared':not_compared[i],'distance_to_known_km':known_dist,'is_known':known_dist is not None and known_dist<=50,'agreement':'unavailable'}
        if ds.mode=='mock': row.update(data_status='mock',disclaimer=DISCLAIMER)
        full.append(row)
    full.sort(key=lambda r:(-r['score_geo'],r['id']))
    top=[]; separation=20 if scale=='local' else 150
    for row in full:
        if len(top)>=k: break
        if row['lat'] is not None and row['lon'] is not None and any(t['lat'] is not None and t['lon'] is not None and haversine(row['lat'],row['lon'],t['lat'],t['lon'])<separation for t in top): continue
        top.append(row)
    pct=max(1,math.ceil(len(full)*.05)); top_ids={r['id'] for r in full[:pct]}
    from .ml import analyze
    ml=analyze(target,candidates,keys,w,top_ids)
    if ml:
        for row in full: row['agreement']=ml['agreement'].get(row['id'],{}).get('agreement','unavailable')
    for row in top:
        c=next(c for c in candidates if c.region_id==row['id'])
        row['explanation']=build(target,c,row['per_criterion'],row['score_geo'],row['flags'],row['not_compared']).model_dump()
    if ds.mode=='mock':
        for row in excluded: row.update(data_status='mock',disclaimer=DISCLAIMER)
    return RankResult(target_id=target_id,scale=scale,preset=preset,top_k=top,full_scores=full,excluded=excluded,novel_candidates=[r for r in top if not r['is_known']],sigma=sig,data_status='mock' if ds.mode=='mock' else 'real',disclaimer=DISCLAIMER if ds.mode=='mock' else None)

def explain(ds,target_id,candidate_id,scale,preset='balanced'):
    result=rank(ds,target_id,scale,preset)
    row=next((r for r in result.full_scores if r['id']==candidate_id),None)
    if row is None: raise ValueError(f'Candidate {candidate_id} not ranked')
    target=next(t for t in ds.targets if t.region_id==target_id and t.scale==scale)
    candidate=next(c for c in ds.candidates if c.region_id==candidate_id and c.scale==scale)
    return build(target,candidate,row['per_criterion'],row['score_geo'],row['flags'],row['not_compared'])

def heat(ds,target_id,scale,preset='balanced'):
    result=rank(ds,target_id,scale,preset)
    return [HeatPoint(id=r['id'],lat=r['lat'],lon=r['lon'],score=round(r['score_geo'],1),data_status=result.data_status if ds.mode=='mock' else None,disclaimer=result.disclaimer) for r in result.full_scores if r['lat'] is not None and r['lon'] is not None]
